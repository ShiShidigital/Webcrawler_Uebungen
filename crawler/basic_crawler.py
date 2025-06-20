# A Basic  Cralwer for getting the Job Title and Description
# from schwarzesbrett.bremen.de

import requests
from lxml import html

print()
# HTTP-Anfrage
def request_page(url):
    print(f"Try to connect to: {url}")
    response = requests.get(url)
    print(f"Response Status Code: {response.status_code}" )

    if response.status_code == 200:
        print("--> Seite erfolgreich geladen!")
        return response.content, response.status_code
    
    else:
        print("--> Fehler beim Abrufen der Seite!")
        response_code = response.status_code

        print("\nFehlercode Analyse ...")
        moz_url = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/"
        moz_full_url = moz_url + str(response_code)
        print(f"Fehlerbeschreibung gefunden: {moz_full_url}")

        moz_response = requests.get(moz_full_url)
        # print(moz_response.status_code)

        return moz_response.content, response.status_code


def parse_html(content):
    tree = html.fromstring(content)
    return tree

def extract_statuscode_details(tree):
    page_title = tree.xpath('/html/body/div[1]/div/div[3]/main/article/header/h1/text()') # Need to add the text() to the copied stuff to get the text!!
    if page_title:
        page_title = page_title[0].strip()
    else:
        page_title = "No H1 Title"

    page_description_paragraphs = tree.xpath('/html/body/div[1]/div/div[3]/main/article/div/p')
    page_description = ""
    for paragraph in page_description_paragraphs:
        # Extrahiert nur den Text 
        text_nodes = paragraph.xpath('string()')    # liest auch Tags aus
        page_description += text_nodes.strip() + " "
    
    page_description.strip()
    print("\n Info about the Response Code from MDN \n")
    print(f"Response Code: {page_title}")
    print(f"Description: {page_description} \n")


def main():
    url = "https://schwarzesbrett.bremen.de/verkauf-angebote/rubrik/arbeitsplatzangebote.html"
    # url = "https://www.wikipedia.org/test"

    response_content, status_code = request_page(url)

    if status_code != 200:
        tree = parse_html(response_content)
        extract_statuscode_details(tree)
    else:
        tree = parse_html(response_content)
        print("HTML erfolgreich geparst")

main()