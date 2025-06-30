import scrapy
from edk_crawler.items import EdkCrawlerItem


class EdkSpider(scrapy.Spider):
    name = "edk_jobs"
    allowed_domain = ['www.edeka.de']
    start_urls = ['https://verbund.edeka/karriere/stellenbörse/#/']

    def parse(self, response):
        self.logger.info("Extrahiere Seite: %s", response.url)

        job_posts = response.css('.o-job-board__results-l__wrapper')

        if not job_posts:
            self.logger.warning("Keine Jobs gefunden mit XPath.")
            return


        for job in job_posts:
            item = EdkCrawlerItem()

            item['title'] = job.css('a.o-job-board__results-l__title-body::text').get()
            item['company'] = job.css('div.o-job-board__results-l__company-body::text').get()
            item['location'] = job.css('div.o-job-board__results-l__location-body::text').get()
            item['url'] = job.css('div.o-job-board__results-l__title-body::attr(href)').get()
            yield scrapy.Request(response.urljoin(item['url']), callback=self.parse_job)

        next_page = None
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    
    def parse_job(self, response):
        item = EdkCrawlerItem()
        item['description'] = response.css('.o-m201-job-copy__inner::text').getall()
        yield item
