import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import ftfy
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from .utils import parse_iso

_WS = re.compile(r"\s+")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def clean_text(value):
    """ftfy (битые кодировки) + замена nbsp + схлопывание пробелов + strip."""
    if not isinstance(value, str):
        return value
    value = ftfy.fix_text(value).replace("\xa0", " ")
    return _WS.sub(" ", value).strip() or None


def to_number(value):
    """'89 990 ₽' -> 89990.0, '4,8' -> 4.8, 'None' -> None."""
    if value is None or isinstance(value, (int, float)):
        return value
    s = re.sub(r"[\s\u00a0\u2009]", "", str(value)).replace(",", ".")
    m = _NUM.search(s)
    return float(m.group()) if m else None


class _CrawlerPipeline:
    """База: Scrapy 2.19+ не передаёт spider в process_item, берём его из crawler."""

    def __init__(self, crawler):
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def inc(self, key):
        self.crawler.stats.inc_value(key)


class CleaningPipeline(_CrawlerPipeline):
    """Кодировки, пробелы, регистр служебных полей, приведение чисел."""

    LOWER_FIELDS = ("store", "keyword")
    NUMERIC_FIELDS = ("price", "rating")

    def process_item(self, item):
        ad = ItemAdapter(item)
        for field in ad.field_names():
            ad[field] = clean_text(ad.get(field))
        for field in self.LOWER_FIELDS:
            if ad.get(field):
                ad[field] = ad[field].lower()
        for field in self.NUMERIC_FIELDS:
            if field in ad.field_names():
                ad[field] = to_number(ad.get(field))
        if "reviews" in ad.field_names():
            n = to_number(ad.get("reviews"))
            ad["reviews"] = int(n) if n is not None else None
        if ad.get("title"):  # Wildberries: "/ название"
            ad["title"] = ad["title"].lstrip("/ ").strip()
        return item


class FilterPipeline(_CrawlerPipeline):
    """Новости: отбрасывает старше --days дней и без ключевых слов (title+summary)."""

    def process_item(self, item):
        spider = self.crawler.spider
        ad = ItemAdapter(item)

        days = getattr(spider, "days", None)
        published = ad.get("published_at")
        if days is not None and published:
            dt = parse_iso(published)
            if dt and dt < datetime.now(timezone.utc) - timedelta(days=days):
                self.inc("pipeline/dropped_old")
                raise DropItem(f"Старше {days} дн.: {published}")

        keywords = [k.lower() for k in getattr(spider, "keywords", [])]
        if keywords and "keyword" in ad.field_names():
            text = f"{ad.get('title') or ''} {ad.get('summary') or ''}".lower()
            matched = [k for k in keywords if k in text]
            if not matched:
                self.inc("pipeline/dropped_no_keyword")
                raise DropItem("Нет ключевых слов")
            ad["keyword"] = ", ".join(matched)
        return item


class ValidationPipeline(_CrawlerPipeline):
    """Отбрасывает записи без title/url."""

    REQUIRED = ("title", "url")

    def process_item(self, item):
        ad = ItemAdapter(item)
        for field in self.REQUIRED:
            if not ad.get(field):
                self.inc("pipeline/dropped_invalid")
                raise DropItem(f"Нет поля '{field}'")
        if not ad["url"].startswith("http"):
            self.inc("pipeline/dropped_invalid")
            raise DropItem(f"Некорректный url: {ad['url']}")
        if "price" in ad.field_names() and ad.get("price") is not None and ad["price"] <= 0:
            ad["price"] = None
        return item


class DuplicationPipeline(_CrawlerPipeline):
    """Дубликаты по нормализованному URL (без query и fragment)."""

    def __init__(self, crawler):
        super().__init__(crawler)
        self.seen = set()

    @staticmethod
    def key(url):
        p = urlsplit(url)
        return f"{p.netloc.lower()}{p.path.rstrip('/')}"

    def process_item(self, item):
        k = self.key(ItemAdapter(item)["url"])
        if k in self.seen:
            self.inc("pipeline/dropped_duplicate")
            raise DropItem(f"Дубликат: {k}")
        self.seen.add(k)
        return item
