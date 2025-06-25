import scrapy

class ScrapemeSpider2(scrapy.Spider):
    name = "scrapemeSpider"
    start_urls = [
        "https://scrapeme.live/shop",
    ]

    def parse(self, response):
        # Extract product information
        products = response.xpath('//li[contains(@class, "product")]')
        for product in products:
            yield {
                'name': product.xpath('.//h2[@class="woocommerce-loop-product__title"]/text()').get(),
                'price': product.xpath('.//span[@class="woocommerce-Price-amount amount"]/text()').get(),
                'link': product.xpath('.//a/@href').get(),
            }

        # Follow pagination links
        next_page = response.xpath('//a[@class="next page-numbers"]/@href').get()
        if next_page:
            yield response.follow(next_page, self.parse)
