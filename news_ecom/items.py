import scrapy


class NewsItem(scrapy.Item):
    source = scrapy.Field()
    title = scrapy.Field()
    url = scrapy.Field()
    published_at = scrapy.Field()
    author = scrapy.Field()
    summary = scrapy.Field()
    keyword = scrapy.Field()
    scraped_at = scrapy.Field()


class ProductItem(scrapy.Item):
    store = scrapy.Field()
    title = scrapy.Field()
    brand = scrapy.Field()
    price = scrapy.Field()
    rating = scrapy.Field()
    reviews = scrapy.Field()
    url = scrapy.Field()
    category = scrapy.Field()
    scraped_at = scrapy.Field()
