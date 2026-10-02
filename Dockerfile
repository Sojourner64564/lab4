FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium
COPY . .
ENTRYPOINT ["python", "run_spider.py"]
# Пример:
#   docker build -t scrapy-lab .
#   docker run --rm -v $(pwd)/data:/app/data scrapy-lab \
#       --spider news --keywords "ПНИПУ,магистратура" --days 7 --output data/news_pstu.json
