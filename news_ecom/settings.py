BOT_NAME = "news_ecom"
SPIDER_MODULES = ["news_ecom.spiders"]
NEWSPIDER_MODULE = "news_ecom.spiders"

# Вежливость к сайтам
ROBOTSTXT_OBEY = True
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2
DOWNLOAD_DELAY_JITTER = 0.5
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 20
DOWNLOAD_TIMEOUT = 30

# Обработка ошибок
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]

# Pipelines: порядок = очистка -> фильтр -> валидация -> дубликаты
ITEM_PIPELINES = {
    "news_ecom.pipelines.CleaningPipeline": 100,
    "news_ecom.pipelines.FilterPipeline": 200,
    "news_ecom.pipelines.ValidationPipeline": 300,
    "news_ecom.pipelines.DuplicationPipeline": 400,
}

# Playwright (используется только запросами с meta["playwright"]=True)
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
# DOWNLOAD_HANDLERS для Playwright задан в EcommerceSpider.custom_settings,
# чтобы новостной паук не запускал браузер.
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 45_000
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "locale": "ru-RU",
        "timezone_id": "Europe/Moscow",
        "viewport": {"width": 1366, "height": 900},
    }
}

FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "INFO"

# Redis (опционально, scrapy-redis) — распределённая очередь:
# SCHEDULER = "scrapy_redis.scheduler.Scheduler"
# DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
# SCHEDULER_PERSIST = True
# REDIS_URL = "redis://localhost:6379/0"
