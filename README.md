# Лабораторная: Scrapy + Playwright

## Установка
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium

## Запуск
    python run_spider.py --spider news --keywords "ПНИПУ,магистратура" --days 7 --output news_pstu.json
    python run_spider.py --spider ecommerce --category "ноутбуки" --stores "wildberries,ozon" --output prices.csv

Доп. опции: `--limit 100`, `--max-pages 5`, `--log-level DEBUG`.

## Проверка результата
    jq '.[] | {title, url}' news_pstu.json
    python -c "import pandas as pd; df=pd.read_json('news_pstu.json'); print(df.shape, df.url.duplicated().sum())"

## Архитектура
- `spiders/news_spider.py` — статика (SSR, habr.com): обход ленты /ru/articles/ (поиск Habr закрыт в robots.txt), пагинация останавливается на старых датах; фильтр по ключевым словам и дате — в `FilterPipeline`.
- `spiders/ecommerce_spider.py` — SPA через Playwright (wait_for_selector + прокрутка для lazy-load); селекторы магазинов в словаре `STORES`.
- `pipelines.py`: Cleaning (ftfy, пробелы, lower, числа) -> Filter (--days) -> Validation (title/url) -> Duplication (по URL).
- `settings.py`: RETRY_ENABLED, RETRY_TIMES, DOWNLOAD_DELAY, AUTOTHROTTLE, ROBOTSTXT_OBEY.
- Логи: `self.logger` в пауках, статистика Scrapy + итоги в `run_spider.py`.

## Если ecommerce-паук дал 0 товаров
1. Смотрите лог: `Forbidden by robots.txt` -> запустите с `--ignore-robots` (учебный запуск, малая нагрузка, помните про ToS сайтов).
2. Паук сам сохраняет `data/debug/<store>_*.html` и `.png` — откройте: если там «Доступ ограничен»/капча, это antibot; пробуйте `--headed`.
3. WB: паук берёт данные из JSON-запросов самой страницы (XHR к wb.ru), при их отсутствии — из DOM без привязки к CSS-классам. Ozon: только DOM по структуре.

## Частые ошибки запуска
- `Executable doesn't exist ... chromium` — не скачан браузер: `playwright install chromium` (в том же venv).

- `Forbidden by robots.txt` у новостного паука — путь закрыт; не используйте разделы поиска, либо другой сайт (lenta.ru, РБК).

## Диагностика
- `scraped 0 items` — селекторы (откройте страницу в браузере, DevTools) или antibot/капча.
- `Forbidden by robots.txt` — сайт запрещает путь; решение — другой сайт/раздел (менять ROBOTSTXT_OBEY — на свой риск).
- `HTTP 429` — уменьшить CONCURRENT_REQUESTS, увеличить DOWNLOAD_DELAY.

## Cron (ежедневный мониторинг)
    0 9 * * * cd /path/to/scrapy_lab && venv/bin/python run_spider.py --spider ecommerce --category "ноутбуки" --output data/prices_$(date +\%F).csv

## Docker
    docker build -t scrapy-lab .
    docker run --rm -v $(pwd)/data:/app/data scrapy-lab --spider news --keywords "ПНИПУ" --output data/news.json

## Redis (опционально)
`pip install scrapy-redis`, раскомментировать блок в `settings.py`, запустить несколько инстансов с одним REDIS_URL.
