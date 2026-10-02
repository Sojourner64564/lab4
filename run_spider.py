#!/usr/bin/env python
"""CLI для запуска пауков.

  python run_spider.py --spider news --keywords "ПНИПУ,магистратура" --days 7 --output news_pstu.json
  python run_spider.py --spider ecommerce --category "ноутбуки" --stores "wildberries,ozon" --output prices.csv
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "news_ecom.settings")

from scrapy.crawler import CrawlerProcess  # noqa: E402
from scrapy.utils.project import get_project_settings  # noqa: E402

from news_ecom.items import NewsItem, ProductItem  # noqa: E402
from news_ecom.spiders.ecommerce_spider import STORES, EcommerceSpider  # noqa: E402
from news_ecom.spiders.news_spider import NewsSpider  # noqa: E402

FORMATS = {".json": "json", ".csv": "csv", ".jl": "jsonlines", ".xml": "xml"}


def build_parser():
    p = argparse.ArgumentParser(description="Scrapy: новости (статика) и e-commerce (Playwright)")
    p.add_argument("--spider", required=True, choices=["news", "ecommerce"])
    p.add_argument("--output", help="файл экспорта (.json / .csv / .jl / .xml)")
    p.add_argument("--limit", type=int, default=200, help="остановиться после N items (0 = без лимита)")
    p.add_argument("--max-pages", type=int, default=None, help="страниц выдачи на запрос/магазин")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--headed", action="store_true", help="показать окно браузера (отладка antibot)")
    p.add_argument("--ignore-robots", action="store_true",
                   help="не учитывать robots.txt (только для учебного запуска, с малой нагрузкой)")
    g = p.add_argument_group("news")
    g.add_argument("--keywords", default="", help="через запятую")
    g.add_argument("--days", type=int, default=7)
    g = p.add_argument_group("ecommerce")
    g.add_argument("--category", default="ноутбуки")
    g.add_argument("--stores", default="wildberries", help=f"через запятую: {', '.join(STORES)}")
    return p


def main():
    args = build_parser().parse_args()

    if args.spider == "news":
        spider_cls, item_cls = NewsSpider, NewsItem
        output = Path(args.output or "news.json")
        kwargs = {"keywords": args.keywords, "days": args.days}
        kwargs["max_pages"] = args.max_pages or 20
    else:
        spider_cls, item_cls = EcommerceSpider, ProductItem
        output = Path(args.output or "prices.csv")
        kwargs = {"category": args.category, "stores": args.stores}
        kwargs["max_pages"] = args.max_pages or 3

    fmt = FORMATS.get(output.suffix.lower())
    if not fmt:
        sys.exit(f"Неподдерживаемое расширение '{output.suffix}'. Доступно: {', '.join(FORMATS)}")
    output.parent.mkdir(parents=True, exist_ok=True)

    feed = {"format": fmt, "encoding": "utf-8", "overwrite": True, "fields": list(item_cls.fields)}
    if fmt == "json":
        feed["indent"] = 2

    settings = get_project_settings()
    settings.set("FEEDS", {str(output): feed})
    settings.set("LOG_LEVEL", args.log_level.upper())
    if args.limit:
        settings.set("CLOSESPIDER_ITEMCOUNT", args.limit)
    if args.headed:
        settings.set("PLAYWRIGHT_LAUNCH_OPTIONS", {"headless": False})
    if args.ignore_robots:
        settings.set("ROBOTSTXT_OBEY", False)

    process = CrawlerProcess(settings)
    crawler = process.create_crawler(spider_cls)
    process.crawl(crawler, **kwargs)
    process.start()

    stats = crawler.stats.get_stats()
    saved = stats.get("item_scraped_count", 0)
    print("\n===== Итоги =====")
    print(f"Запросов:        {stats.get('downloader/request_count', 0)}")
    print(f"Сохранено items: {saved}  -> {output}")
    print(f"Повторов (retry): {stats.get('retry/count', 0)}")
    print(f"Ошибок логов:    {stats.get('log_count/ERROR', 0)}")
    for k in ("dropped_old", "dropped_no_keyword", "dropped_invalid", "dropped_duplicate"):
        print(f"{k:<17}{stats.get('pipeline/' + k, 0)}")
    if saved == 0:
        print("scraped 0 items — проверьте селекторы / robots.txt / капчу в логах")
        sys.exit(1)


if __name__ == "__main__":
    main()
