from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

def main():
    # Optionen für Firefox Browser
    firefox_options = Options()
    # firefox_options.headless = True # im hintergrund ohne GUI

    # Initialisierung
    driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), options=firefox_options)

    try:
        # Webseite öffnen
        driver.get('https://verbund.edeka/karriere/stellenbörse/')

        # Ausgabe des gesamten HTML codes
        html_source = driver.page_source

        # Nur Teilinhalt ausgeben
        print(html_source[:1000])

    finally:
        # Browser schließen
        driver.quit()

if __name__ == "__main__":
    main()