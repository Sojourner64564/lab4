import re  # noqa: F401
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import scrapy

from ..items import ProductItem

# Классы вёрстки WB/Ozon часто меняются, поэтому паук НЕ использует CSS-классы карточек.
#  * Wildberries: ловим JSON-ответы, которые сама SPA запрашивает у wb.ru (XHR),
#    а если их нет — разбираем DOM.
#  * Ozon: разбираем DOM по структуре — ищем ссылки на товары и поднимаемся к
#    «карточке» (ближайший предок, содержащий только один товар).
STORES = {
    "wildberries": {
        "search_url": "https://www.wildberries.ru/catalog/0/search.aspx?page={page}&sort=popular&search={q}",
        "link_selector": "a[href*='/detail.aspx']",
        "link_re": r"/catalog/\d+/detail\.aspx",
        "api_hosts": ("wb.ru",),
    },
    "ozon": {
        "search_url": "https://www.ozon.ru/search/?text={q}&from_global=true&deny_category_prediction=true&page={page}",
        "link_selector": "a[href*='/product/']",
        "link_re": r"/product/[^/?#]+",
        "api_hosts": (),
    },
}

ANTIBOT_MARKERS = ("доступ ограничен", "access denied", "captcha", "antibot", "подтвердите, что вы не робот")

# Универсальный разбор DOM без привязки к классам.
DOM_JS = r"""
(cfg) => {
  const linkRe = new RegExp(cfg.linkRe);
  const priceRe = /\d[\d\s\u00a0\u2009]*\s*₽/;
  const ratingRe = /^\d[.,]\d$/;
  const reviewsRe = /(\d[\d\s\u00a0]*)\s*(оценк|отзыв)/i;
  const out = new Map();
  for (const a of document.querySelectorAll('a[href]')) {
    const m = a.href.match(linkRe);
    if (!m || out.has(m[0])) continue;
    let card = a;
    for (let i = 0; i < 8 && card.parentElement && card.parentElement !== document.body; i++) {
      const p = card.parentElement;
      const keys = new Set();
      for (const x of p.querySelectorAll('a[href]')) {
        const mm = x.href.match(linkRe);
        if (mm) keys.add(mm[0]);
      }
      if (keys.size > 1) break;
      card = p;
    }
    const lines = (card.innerText || '').split('\n')
      .map(s => s.replace(/\u00a0/g, ' ').trim()).filter(Boolean);
    const price = lines.find(l => priceRe.test(l)) || null;
    const rating = lines.find(l => ratingRe.test(l)) || null;
    const rl = lines.find(l => reviewsRe.test(l)) || null;
    const img = card.querySelector('img[alt]');
    let title = a.getAttribute('aria-label') || (img && img.alt) || '';
    if (!title) {
      title = lines.filter(l => !priceRe.test(l) && !ratingRe.test(l) && l.length > 8)
        .sort((x, y) => y.length - x.length)[0] || '';
    }
    let brand = null;
    if (title.includes(' / ')) { [brand, title] = [title.split(' / ')[0], title.split(' / ').slice(1).join(' / ')]; }
    out.set(m[0], {
      url: a.href.split('?')[0].split('#')[0],
      title, brand, price, rating, reviews: rl,
    });
  }
  return Array.from(out.values());
}
"""


def iter_wb_products(obj):
    """Рекурсивно ищет в JSON словари-товары WB (разные версии API вкладывают их по-разному)."""
    if isinstance(obj, dict):
        if "id" in obj and "name" in obj and any(k in obj for k in ("sizes", "salePriceU", "priceU")):
            yield obj
        else:
            for v in obj.values():
                yield from iter_wb_products(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_wb_products(v)


def wb_price(p):
    for s in p.get("sizes") or []:
        price = s.get("price") or {}
        for k in ("product", "total", "basic"):
            if price.get(k):
                return price[k] / 100
    for k in ("salePriceU", "priceU"):
        if p.get(k):
            return p[k] / 100
    return None


class EcommerceSpider(scrapy.Spider):
    """Динамический паук (SPA): страницы рендерятся Playwright'ом."""

    name = "ecommerce"
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
    }

    def __init__(self, category="ноутбуки", stores="wildberries", max_pages=3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(stores, str):
            stores = [s.strip().lower() for s in stores.split(",") if s.strip()]
        unknown = [s for s in stores if s not in STORES]
        if unknown:
            raise ValueError(f"Неизвестные магазины: {unknown}. Доступны: {list(STORES)}")
        self.category = category
        self.stores = stores
        self.max_pages = int(max_pages)
        self._captured = {}

    # ---------- запросы ----------
    def _initial(self):
        for store in self.stores:
            cfg = STORES[store]
            for page in range(1, self.max_pages + 1):
                url = cfg["search_url"].format(q=quote_plus(self.category), page=page)
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    errback=self.on_error,
                    cb_kwargs={"store": store},
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_init_callback": self.init_page,
                    },
                )

    def start_requests(self):  # Scrapy < 2.13
        yield from self._initial()

    async def start(self):  # Scrapy >= 2.13
        for req in self._initial():
            yield req

    async def init_page(self, page, request):
        """Подписка на ответы ДО загрузки страницы: собираем JSON, который запрашивает SPA."""
        store = request.cb_kwargs.get("store")
        hosts = STORES[store]["api_hosts"]
        bucket = self._captured.setdefault(id(page), [])
        if not hosts:
            return

        async def on_response(resp):
            try:
                if resp.status != 200 or not any(h in resp.url for h in hosts):
                    return
                if "json" not in (resp.headers.get("content-type") or ""):
                    return
                bucket.append(await resp.json())
            except Exception:
                pass

        page.on("response", on_response)

    # ---------- разбор ----------
    async def parse(self, response, store):
        page = response.meta["playwright_page"]
        cfg = STORES[store]
        try:
            try:
                await page.wait_for_selector(cfg["link_selector"], timeout=25_000)
            except Exception:
                self.logger.warning("%s: ссылки на товары не появились за 25 с (%s)", store, response.url)
            for _ in range(6):  # lazy-load
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)

            rows, source = [], "dom"
            captured = self._captured.pop(id(page), [])
            if store == "wildberries":
                rows = self._rows_from_wb_json(captured)
                if rows:
                    source = "api"
            if not rows:
                rows = await page.evaluate(DOM_JS, {"linkRe": cfg["link_re"]})

            self.logger.info("%s: %d товаров (%s) на %s", store, len(rows), source, response.url)
            if not rows:
                await self._dump_debug(page, store)

            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for r in rows:
                yield ProductItem(store=store, category=self.category, scraped_at=now, **r)
        finally:
            await page.close()

    @staticmethod
    def _rows_from_wb_json(payloads):
        rows, seen = [], set()
        for payload in payloads:
            for p in iter_wb_products(payload):
                pid = p["id"]
                if pid in seen:
                    continue
                seen.add(pid)
                rows.append({
                    "title": p.get("name"),
                    "brand": p.get("brand"),
                    "price": wb_price(p),
                    "rating": p.get("reviewRating") or p.get("nmReviewRating") or p.get("rating"),
                    "reviews": p.get("feedbacks") or p.get("nmFeedbacks") or p.get("feedbacksCount"),
                    "url": f"https://www.wildberries.ru/catalog/{pid}/detail.aspx",
                })
        return rows

    async def _dump_debug(self, page, store):
        """Если 0 товаров — сохраняем HTML и скриншот, чтобы понять причину."""
        folder = Path("data/debug")
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%H%M%S")
        html = await page.content()
        (folder / f"{store}_{stamp}.html").write_text(html, encoding="utf-8")
        try:
            await page.screenshot(path=str(folder / f"{store}_{stamp}.png"))
        except Exception:
            pass
        if any(m in html.lower() for m in ANTIBOT_MARKERS):
            self.logger.error("%s: похоже на antibot/капчу. Смотрите %s. Попробуйте --headed", store, folder)
        else:
            self.logger.error("%s: товаров нет, разметка не распознана. Дамп: %s", store, folder)

    async def on_error(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self._captured.pop(id(page), None)
        self.logger.error("Ошибка запроса %s: %r", failure.request.url, failure.value)
