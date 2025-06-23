import requests
from bs4 import BeautifulSoup

base_url = 'https://scrapeme.live/shop/'

response = requests.get(base_url)

if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all product containers
    products = soup.find_all('li', class_='product')

    product_details = []

    # Loop through each product to get the link
    for product in products:
        product_link = product.find('a')['href']
        
        # Send a GET request to the product page
        product_response = requests.get(product_link)
        
        if product_response.status_code == 200:
            # Parse the product page HTML
            product_soup = BeautifulSoup(product_response.text, 'html.parser')
            
            # Extract title
            title = product_soup.find('h1', class_='product_title').text
            
            # Extract description
            description = product_soup.find('div', class_='woocommerce-product-details__short-description').text.strip() if product_soup.find('div', class_='woocommerce-product-details__short-description') else 'No description available'

            # Extract Price
            price = product_soup.find('p', class_='price').text.strip()
            
           
            product_details.append({
                'url': product_link,
                'title': title,
                'description': description,
                'price': price
            })
        else:
            print(f'Failed to retrieve product page: {product_link}. Status code: {product_response.status_code}')
    
    
    for detail in product_details:
        print(f'URL: {detail["url"]}')
        print(f'Title: {detail["title"]}')
        print(f'Description: {detail["description"]}')
        print(f'Price: {detail["price"]}')
        print('---')
    print("Anzahl Shopseiten:", len(product_details))

else:
    print(f'Failed to retrieve the shop page. Status code: {response.status_code}')
