from datetime import datetime, timedelta, timezone

import scrapy

from ..items import NewsItem
from ..utils import parse_iso


class NewsSpider(scrapy.Spider):
    """Статический паук (SSR): лента статей habr.com.

    Поиск Habr закрыт в robots.txt, поэтому обходим обычную ленту
    /ru/articles/ (новые сверху) и фильтруем по ключевым словам и дате
    в FilterPipeline. Пагинация останавливается, когда страница целиком
    старше --days дней.
    """

    name = "news"
    allowed_domains = ["habr.com"]
    FEED_URL = "https://habr.com/ru/articles/page{page}/"

    def __init__(self, keywords="", days=7, max_pages=20, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        self.keywords = keywords
        self.days = int(days)
        self.max_pages = int(max_pages)
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=self.days)

    def _initial(self):
        yield scrapy.Request(
            self.FEED_URL.format(page=1),
            callback=self.parse,
            errback=self.on_error,
            cb_kwargs={"page": 1},
        )

    def start_requests(self):  # Scrapy < 2.13
        yield from self._initial()

    async def start(self):  # Scrapy >= 2.13
        for req in self._initial():
            yield req

    def parse(self, response, page):
        cards = response.css("article.tm-articles-list__item")
        if not cards:
            self.logger.warning("Нет карточек на %s — проверьте селекторы", response.url)
            return

        has_fresh = False
        for card in cards:
            published = card.css("time::attr(datetime)").get()
            dt = parse_iso(published)
            if dt is None or dt >= self.cutoff:
                has_fresh = True
            href = card.css("a.tm-title__link::attr(href)").get()
            yield NewsItem(
                source="habr.com",
                title=card.css("a.tm-title__link span::text").get()
                or " ".join(card.css("h2 ::text").getall()),
                url=response.urljoin(href) if href else None,
                published_at=published,
                author=card.css("a.tm-user-info__username::text").get(),
                summary=" ".join(card.css(".article-formatted-body ::text").getall())[:500],
                scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )

        self.logger.info("Страница %d: %d карточек", page, len(cards))
        if has_fresh and page < self.max_pages:
            yield scrapy.Request(
                self.FEED_URL.format(page=page + 1),
                callback=self.parse,
                errback=self.on_error,
                cb_kwargs={"page": page + 1},
            )

    def on_error(self, failure):
        self.logger.error("Ошибка запроса %s: %r", failure.request.url, failure.value)
