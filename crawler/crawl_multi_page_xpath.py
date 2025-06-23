import requests
from lxml import html

base_url = 'https://scrapeme.live/shop/'

response = requests.get(base_url)

if response.status_code == 200:
    # Parse the HTML content
    tree = html.fromstring(response.content)
    
    # Find all product titles and prices using XPath
    titles = tree.xpath('//h2[@class="woocommerce-loop-product__title"]/text()')
    prices = tree.xpath('//span[@class="woocommerce-Price-amount amount"]/text()')

    product_details = []

    # Loop through each title and corresponding price
    for title, price in zip(titles, prices):
        product_details.append({
            'title': title.strip(),
            'price': price.strip()
        })

    for detail in product_details:
        print(f'Title: {detail["title"]}')
        print(f'Price: {detail["price"]}')
        print('---')
        
else:
    print(f'Failed to retrieve the shop page. Status code: {response.status_code}')
