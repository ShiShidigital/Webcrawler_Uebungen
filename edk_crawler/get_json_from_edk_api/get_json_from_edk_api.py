import requests
from bs4 import BeautifulSoup
import json
import time
from html import unescape
from markdownify import markdownify as md
import logging 

# Format Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class EdkJobScraper:
    """ 
    Klasse zum Scrapen von Jobangebten der Edeka Verbund API.
    """

    # Konstanten
    BASE_API_URL = "https://verbund.edeka/api/v2/career/vacancies"
    # Statische Liste der weiteren HTTP-Header, falls nötig (z. B. User-Agent)
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    PAGE_SIZE = 50
    REQUEST_DELAY_SECONDS = 1


    # Konstruktor
    def __init__(self, output_json_filename='edk_job_data.json'):
        self.output_json_filename = output_json_filename
        self.all_jobs_details = []

    def _make_request(self, url, method="GET", params=None):
        """
        Private Helfermethode zum senden der HTTP-Anfragen. Fehlerbehandlung
        """
        try:
            time.sleep(self.REQUEST_DELAY_SECONDS)
            # flexibler für GET/POST
            response = requests.request(method, url, headers=self.HEADERS, params=params, timeout=10)
            response.raise_for_status()  # Wirft automatisch Fehler
            return response
        
        except requests.exceptions.HTTPError as e:
            # Fehler mit logging protokollieren anstatt mit print()
            logging.error(f"HTTP Fehler bei {url}: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Verbindungsfehler bei {url}: {e}")
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeoit bei {url}: {e}")
        except requests.exceptions.RequestException as e:
            # Fängt alle anderen Fehler ab
            logging.error(f"Allgemeiner Fehler bei Anfrage an {url}: {e}")
        return None 


    def extract_job_summary(self, job_data):
        """
        Extrahiert die Zusammenfassung der Jobdetails aus den API-Daten.
        """
        location_parts = [
            job_data.get("locationName", "N/A"),
            job_data.get("locationStreet", ""),
            job_data.get("locationZipCode", ""), 
            job_data.get("locationCity", "")
        ]
        location = ", ".join(filter(None, location_parts)).strip()

        return {
            "url": job_data.get("detailPageUrl"),
            "department": job_data.get("companyName", "N/A"), 
            "description": None,
            "job_title": job_data.get("title", "Kein Title vorhanden"),
            "level": job_data.get("level", "Unbestimmt"), 
            "location": location,
            "schedule": job_data.get("timeType", "Vollzeit/Teilzeit")
        }

    
    def _extract_description_from_html(self, html_content):
        """
        Extraktion der JobBeschreibung aus dem HTML-String
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 1. Versuch JSON-LD
            script = soup.find('script', type='application/ld+json')
            # print("Found Script:", script)
            if script and script.string:
                try:
                    json_data = json.loads(script.string)
                    # print(json_data)

                    # Prüfe, ob der Typ JobPosting ist
                    if json_data.get('@type') == 'JobPosting':
                        description = json_data.get('description')
                        # print(description)
                        if description:
                            return md(unescape(description).strip())
                except json.JSONDecodeError as e:
                    logging.warning(f"Fehler beim parsen von JSON-LD: {e}")
                except Exception as e:
                    logging.warning(f"Allgemeiner Fehler beim Verarbeiten von JSON-LD: {e}")

            #2. Fallback: Suche nach einem spezifischen Div
            description_div = soup.find("div", {"class": "job-description"})  # Beispieleingabe
            if description_div:
                return md(description_div.get_text(strip=True))

            # Wenn beides fehlschlägt
            logging.warning("Keine Jobbeschreibung gefunden.")
            return "Keine Beschreibung gefunden"
        
        except Exception as e:
            logging.warning(f"Error while extracting description: {e}")
            return "Fehler beim Abrufen der Beschreibung"


    def fetch_all_jobs(self):
        """
        Startet den Hauptprozess des Job-Scrapings.
        """
        page = 0
        logging.info("Starte Job-Scraping-Prozess...")

        while True:
            # URL für die aktuelle Seite
            url = f"{self.BASE_API_URL}?page={page}&size={self.PAGE_SIZE}"
            logging.info(f"Sammle Daten von Seite: {page} (URL: {url})")

            response = self._make_request(url)

            if response is None:  # Prüfen, ob Error
                logging.error(f"Fehler beim Abrufen der Seite {page}. Abbruch")

            try:    # TEST ob wirklich JSON zurück kommt
                job_data = response.json()
            except json.JSONDecodeError as e:
                logging.error(f"Fehler beim Parsen der JSON-Antwort von Seite {page}: {e} - Kein gültiges JSON?")
                break


            entries = job_data.get('entries')  
            
            if not entries:
                logging.info(f"Keine weiteren Jobs auf Seite {page} gefunden. Beende das Scrapen.")
                break

            current_page_jobs = []
            for job in entries:
                # Extrahierte Details für jeden Job hinzufügen
                job_info = self.extract_job_summary(job)
                job_url = job_info.get('url')
                # print(job_url)

                # Überprüfung, ob die URL valide ist
                if job_url:
                    logging.info(f"Hole Details für: {job_info['job_title']} ({job_url})")
                    detail_response = self._make_request(job_url)

                    if detail_response:
                        job_info['description'] = self._extract_description_from_html(detail_response.text)
                    else:
                        job_info['description'] = "Fehler beim Abrufen der JobSeite"
                else:
                    logging.warning(f"Job '{job_info.get('job_title', 'Unbekannt')}' hat keine Jobseiten URL")
                    job_info['description'] = "Keine Job-URL vorhanden"

                current_page_jobs.append(job_info)

            self.all_jobs_details.extend(current_page_jobs)
            logging.info(f"Bisher gesammelte Jobs: {len(self.all_jobs_details)}")

            page += 1

            # TESTLAUF!!! Raus nehmen im Betrieb!
            if page >= 2:
                logging.info(f"Test-Limit erreicht. Beende Scrapen.")
                break

        logging.info(f"Scraping beendet. Insgesamt {len(self.all_jobs_details)} Jobs gesammelt.")


    def save_to_json(self):
        if not self.all_jobs_details: # Prüfen ob Daten gesammelt wurden
            logging.warning("Keine Jobdaten zum Speichern vorhanden.")
            return 
        
        try:
            with open(self.output_json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_jobs_details, f, ensure_ascii=False, indent=4)
            logging.info(f"Alle Jobdetails wurden erfolgreich in {self.output_json_filename} gespeichert!")
        except IOError as e:
            logging.error(f"Fehler beim speichern der Datei '{self.output_json_filename}': {e}")


if __name__ == "__main__":
    start_time = time.time()
    logging.info("Programm Start")

    scraper = EdkJobScraper()

    # Starte Hauptprozess
    scraper.fetch_all_jobs()
    # Daten speichern
    scraper.save_to_json()

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Programm beenet. Laufzeit: {duration:.2f} Sekunden.")
