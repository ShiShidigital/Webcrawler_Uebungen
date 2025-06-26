import scrapy
from lxml import html

class ShopMultipageSpider(scrapy.Spider):
    name = 'shopMultipage'
    start_urls = ['https://scrapeme.live/shop/']

    def parse(self, response):
        # Extract product information
        products = response.xpath('//li[contains(@class, "product")]')
        for product in products:
            name = product.xpath('.//h2[@class="woocommerce-loop-product__title"]/text()').get()
            page_link = self.start_urls[0] + name

            yield response.follow(page_link, self.parse_product)

        # Follow pagination links
        next_page = response.xpath('//a[@class="next page-numbers"]/@href').get()
        if next_page:
            yield response.follow(next_page, self.parse)

    
    def parse_product(self, response):
        # Extract product details from the product page
        yield {
            'name': response.xpath('/html/body/div[1]/div[2]/div/div[2]/main/div/div[2]/h1/text()').get(),
            'price': response.xpath('/html/body/div[1]/div[2]/div/div[2]/main/div/div[2]/p[1]/span/text()').get(),
            'description': ' '.join(response.xpath('//div[@class="woocommerce-product-details__short-description"]/p/text()').getall()),
            'link': response.url,
        }