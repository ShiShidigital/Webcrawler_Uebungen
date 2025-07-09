# get_json_from_edk_api.py
import requests
from bs4 import BeautifulSoup
import json
import time
from html import unescape
from markdownify import markdownify as md
import logging 
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


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
    REQUEST_DELAY_SECONDS = 0.2
    MAX_CONCURRENT_DETAIL_REQUESTS =30  # gleichzeitige Detailanfragen (Threads), evtl ändern

    # Semaphore, um die anzahl der gleichzeitig aktiven HTTP-Anfragen zu begrenzen
    _request_semaphore = threading.Semaphore(MAX_CONCURRENT_DETAIL_REQUESTS)

    # Konstruktor
    def __init__(self, output_json_filename='edk_job_data.json'):
        self.output_json_filename = output_json_filename
        self.all_jobs_details = []


    def _make_request(self, url, method="GET", params=None, delay=False, use_semaphore=False):
        """
        Private Helfermethode zum senden der HTTP-Anfragen. Fehlerbehandlung.
        :param delay: Wenn True, wird REQUEST_DELAY_SECONDS angewendet.
        :param use_semaphore: Wenn True, wird das Request-Semaphore verwendet
        """
        if delay:
            time.sleep(self.REQUEST_DELAY_SECONDS)

        # Get a Token from Semaphore, wait if all Tokens are taken.
        if use_semaphore:
            self._request_semaphore.acquire() # Token nehmen

        response = None
        try:
            response = requests.request(method, url, headers=self.HEADERS, params=params, timeout=30)
            response.raise_for_status()  # Wirft automatisch Fehler
            response.encoding = 'utf-8' # Umlaute
            return response     # Erfolgreiche Antwort
        
        except requests.exceptions.HTTPError as e:
            # Fehler mit logging protokollieren anstatt mit print()
            status_code = e.response.status_code if e.response else 'N/A'
            response_text = e.response.text if e.response else 'N/A'
            logging.error(f"HTTP Fehler bei {url}: Status: {status_code} -Text:  {response_text}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Verbindungsfehler bei {url}: {e}")
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout bei {url}: {e}")
        except requests.exceptions.RequestException as e:
            # Fängt alle anderen Fehler ab
            logging.error(f"Allgemeiner Fehler bei Anfrage an {url}: {e}")
        finally:
            # Immer Token freigeben
            if use_semaphore:
                self._request_semaphore.release()

        return response # Wenn Fehler, dann none


    def _extract_job_summary(self, job_data):
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
            "job_title": job_data.get("title", "Kein Titel vorhanden"),
            "level": job_data.get("level", "Unbestimmt"), 
            "location": location,
            "schedule": job_data.get("timeType", "Vollzeit/Teilzeit")
        }

    
    def _extract_description_from_html(self, html_content):
        """
        Extraktion der JobBeschreibung aus dem HTML-String, 
        Verbesserte Mardown-Ausgabe + Zeichenkodierung
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            description_text = "Keine detaillierte Beschreibung gefunden"

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
                            description_text = md(unescape(description), heading_style="ATX", strong_em_with_underscores=False, wrap=True).strip()
                            return description_text
                except json.JSONDecodeError as e:
                    logging.warning(f"Fehler beim parsen von JSON-LD: {e}")
                except Exception as e:
                    logging.warning(f"Allgemeiner Fehler beim Verarbeiten von JSON-LD: {e}")

            #2. Fallback: Suche nach einem spezifischen Div
            description_div = soup.find("div", {"class": "job-description"})  # Beispieleingabe
            if description_div:
                raw_html_from_div = str(description_div)
                description_text = md(unescape(raw_html_from_div), heading_style="ATX", strong_em_with_underscores=False, wrap=True).strip()
                return description_text

            # Wenn beides fehlschlägt
            logging.warning("Keine Jobbeschreibung gefunden.")
            return "Keine Beschreibung gefunden"
        
        except Exception as e:
            logging.warning(f"Error while extracting description: {e}")
            return "Fehler beim Abrufen der Beschreibung"


    def _process_job_detail(self, job_summary):
        """
        Wird von den Threads parallel ausgeführt
        """
        original_title = job_summary.get('job_title', 'Unbekannt')
        job_url = job_summary.get('url')

        if job_url:
            # Verwendung der Semaphore für Detailanfrage
            logging.debug(f"Hole Beschreibung für: {original_title} ({job_url})")
            detail_response = self._make_request(job_url, use_semaphore=True)

            if detail_response:
                job_summary['description'] = self._extract_description_from_html(detail_response.text)
            else:
                job_summary['description'] = "Fehler: Detailseite nicht abrufbar."
        else:
            logging.warning(f"Job '{original_title}' hat keine Detail-URL.")
            job_summary['description'] = "Keine JobURL verfügbar."
        
        return job_summary


    def fetch_all_jobs(self):
        """
        Startet den Hauptprozess des Job-Scrapings.
        """
        page = 0
        logging.info("Starte Job-Scraping-Prozess...")

        logging.getLogger().setLevel(logging.INFO) # Setzt INFO Level für allgeimene Logs
        # logging.getLogger().setLevel(logging.DEBUG) # Setzt DEBUG Level für detailiertere Logs
        

        while True:
            # URL für die aktuelle Seite
            url = f"{self.BASE_API_URL}?page={page}&size={self.PAGE_SIZE}"
            logging.info(f"Sammle Daten von Seite: {page} (URL: {url})")

            response = self._make_request(url, delay=True)

            if response is None:  # Prüfen, ob Error
                logging.error(f"Fehler beim Abrufen der Seite {page}. Abbruch")
                break

            try:    # TEST ob wirklich JSON zurück kommt
                job_data = response.json()
            except json.JSONDecodeError as e:
                logging.error(f"Fehler beim Parsen der JSON-Antwort von Seite {page}: {e} - Kein gültiges JSON?")
                break

            entries = job_data.get('entries')  
            if not entries:
                logging.info(f"Keine weiteren Jobs auf Seite {page} gefunden. Beende das Scrapen.")
                break

            # Batch-Verarbeitung der Detailseiten mit ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_DETAIL_REQUESTS) as executor:
                job_summaries_to_process = [self._extract_job_summary(job) for job in entries]

                # Sende Aufgaben an den Executor
                futures = {executor.submit(self._process_job_detail, job_summary): job_summary for job_summary in job_summaries_to_process}

                # Warte auf die Ergebnisse
                for future in as_completed(futures):
                    original_job_summary = futures[future]
                    try:
                        updated_job_summary = future.result()
                        self.all_jobs_details.append(updated_job_summary)
                    except Exception as e:
                        logging.error(f"Job-Beschreibung Verarbeitung für '{original_job_summary.get('job_title', 'Unbekannt')}' Fehler: {e}", exc_info=True)

            logging.info(f"Bisher gesammelte Jobs: {len(self.all_jobs_details)}")

            page += 1
            # TESTLAUF!!! Raus nehmen im Betrieb!
            # if page >= 20:
            #    logging.info(f"Test-Limit erreicht. Beende Scrapen.")
            #    break

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
    logging.info(f"Programm beendet. Laufzeit: {duration:.2f} Sekunden.")
