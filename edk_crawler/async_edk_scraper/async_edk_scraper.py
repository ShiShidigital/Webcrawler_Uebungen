# async_scraper.py

import asyncio
from typing import Optional
import httpx 
from bs4 import BeautifulSoup
import json 
import time 
from html import unescape
from markdownify import markdownify as md
import logging 


# Konfiguration Logging System
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AsyncEdekaJobScraper:
    """
    Asynchrone Klasse zum Scrapen der Edeka Verbund API
    """

    # Konstanten
    BASE_API_URL = "https://verbund.edeka/api/v2/career/vacancies"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    PAGE_SIZE = 50  # Anzahl der Jobs pro API-Anfrage
    
    # Hier starten wir ohne expliziten Delay, da Asyncio eh nicht blockiert.
    API_LIST_REQUEST_DELAY_SECONDS = 0.0 
    
    # Maximale Anzahl gleichzeitig aktiver HTTP-Anfragen für die Detailseiten.
    MAX_CONCURRENT_DETAIL_REQUESTS = 30 


    def __init__(self, output_json_filename='edk_job_data.json'):
        """
        Konstruktor
        """
        self.output_json_filename = output_json_filename
        self.all_jobs_details = []
        self._request_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_DETAIL_REQUESTS)
        self.failed_details = []    # Seiten mit Fehlern
        self.missed_descriptions = []   # Jobs ohne Beschreibung


    async def _make_request(self, client: httpx.AsyncClient, url: str, method: str = "GET", params: dict = None,
                            delay: bool = False, use_semaphore: bool = False, job_meta_data: Optional[dict] = None) -> httpx.Response:
        """
        Asynchrone Helferfunktion zum Senden von HTTP-Anfragen.
        : param job_meta_data: Metadaten des Jobs, falls Detailanfrage für Fehlerprotokollierung
        """
        if delay:
            await asyncio.sleep(self.API_LIST_REQUEST_DELAY_SECONDS)

        if use_semaphore:
            await self._request_semaphore.acquire()

        response = None
        try:
            response = await client.request(method, url, params=params, headers=self.HEADERS, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP Fehler bei {url}: Status {e.response.status_code} - Text: {e.response.text}"
            logging.error(error_msg)
            if job_meta_data:
                self.failed_details.append({"url": url, "job_title": job_meta_data.get('job_title', 'N/A'), "error": error_msg, "type": "HTTP_STATUS_ERROR"})
        except httpx.RequestError as e:
            error_msg = f"Request Fehler bei {url}: {e}"
            logging.error(error_msg)
            if job_meta_data:
                self.failed_jobs.append({"url": url, "job_title": job_meta_data.get('job_title', 'N/A'), "error": error_msg, "type": "REQUEST_ERROR"})
        except Exception as e: # Fängt allgemeine Fehler ab
            error_msg = f"Unerwarteter Fehler bei Anfrage an {url}: {e}"
            logging.error(error_msg, exc_info=True)
            if job_meta_data:
                self.failed_jobs.append({"url": url, "job_title": job_meta_data.get('job_title', 'N/A'), "error": error_msg, "type": "UNEXPECTED_ERROR"})
        finally:
            if use_semaphore: # Semaphore immer freigeben
                self._request_semaphore.release()
        return response # Gibt None zurück, wenn ein Fehler auftrat
    

    def _extract_job_summary(self, job_data: dict) -> dict:
        """
        Extrahiert die Zusammenfassung der Jobdetails aus den API-Daten.
        (Diese Funktion ist synchron, da sie keine await-Aufrufe benötigt)
        """
        location_parts = [
            job_data.get("locationName", "N/A"),
            job_data.get("locationStreet", ""),
            job_data.get("locationZipCode", ""),
            job_data.get("locationCity", "")
        ]
        # Filtern von None/leeren Strings und Zusammenfügen mit Komma
        location = ", ".join(filter(None, location_parts)).strip()

        return {
            "url": job_data.get("detailPageUrl"),
            "department": job_data.get("companyName", "N/A"),
            "description": None, # Wird später gefüllt
            "job_title": job_data.get("title", "Kein Titel vorhanden"),
            "level": job_data.get("level", "Unbestimmt"),
            "location": location,
            "schedule": job_data.get("timeType", "Vollzeit/Teilzeit")
        }
    

    def _extract_description_from_html(self, html_content: str, job_meta_data: Optional[dict] = None) -> str:
        """
        Extraktion der JobBeschreibung aus dem HTML-String.
        Wandelt HTML in reines Markdown um.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            description_found = False
            description_text = "Keine detaillierte Beschreibung gefunden."

            # 1. Versuch JSON-LD
            script = soup.find('script', type='application/ld+json')
            if script and script.string:
                try:
                    json_data = json.loads(script.string)
                    if json_data.get('@type') == 'JobPosting':
                        description = json_data.get('description')
                        if description:
                            md_content = md(
                                unescape(description),
                                heading_style="ATX",
                                strong_em_with_underscores=False,
                                wrap=True
                            ).strip() # .strip() entfernt führende/hintere Whitespaces
                            description_found = True
                            return md_content
                except json.JSONDecodeError as e:
                    logging.warning(f"Fehler beim Parsen von JSON-LD: {e}")
                except Exception as e:
                    logging.warning(f"Allgemeiner Fehler beim Verarbeiten der Beschreibung aus JSON-LD: {e}")

            # 2. Fallback: Suche nach einem spezifischen Div
            description_div = soup.find("div", {"class": "job-description"})
            if description_div:
                md_content = md(
                    unescape(str(description_div)), # str() holt HTML-Inhalt
                    heading_style="ATX",
                    strong_em_with_underscores=False,
                    wrap=True
                ).strip()
                description_found = True
                return md_content

            logging.warning("Keine Jobbeschreibung gefunden.")
            return "Keine Beschreibung gefunden."

        except Exception as e:
            error_msg = f"Fehler beim Extrahieren der Beschreibung: {e}"
            logging.error(error_msg, exc_info=True)
            description_text = "Fehler beim Abrufen der Beschreibung."
            if job_meta_data:
                self.missed_descriptions.append({"url": job_meta_data.get('url', 'N/A'), "job_title": job_meta_data.get('job_title', 'N/A'), "error": error_msg, "type": "DESCRIPTION_EXTRACTION_ERROR"})

            return description_text
        finally:
            # Keine Beschreibung aber auch kein Fehler
            if not description_found and job_meta_data and description_text == "Keine Beschreibung gefunden.":
                self.missed_descriptions.append({"url": job_meta_data.get('url', 'N/A'), "job_title": job_meta_data.get('job_title', 'N/A'), "error": "Beschreibung nicht im HTML gefunden-", "type": "DESCRIPTION_NOT_FOUND"})

        
    async def _process_job_detail(self, client: httpx.AsyncClient, job_summary: dict) -> dict:
        """
        Wird von Tasks parallel ausgeführt
        """
        original_title = job_summary.get('job_title', 'Unbekannt')
        job_url = job_summary.get('url')

        job_meta_data_for_error_logging = {k: v for k, v in job_summary.items() if k in ['job_title', 'url']}

        if job_url:
            logging.debug(f"Hole Beschreibung für: {original_title} ({job_url})")
            detail_response = await self._make_request(client, job_url, use_semaphore=True, job_meta_data=job_meta_data_for_error_logging)

            if detail_response:
                job_summary['description'] = self._extract_description_from_html(detail_response.text, job_meta_data_for_error_logging)
            else:
                job_summary['description'] = "Fehler: Detailseite nicht abrufbar."
        else:
            logging.warning(f"Job '{original_title}' hat keine Detail-URL.")
            job_summary['description'] = "Keine JobURL verfügbar."
            
            # Fehlerprotokollierung 
            self.failed_details.append({"url": "N/A", "job_title": original_title, "error": "Keine Seiten-URL vorhanden.", "type": "MISSING_URL"})
        
        return job_summary


    async def fetch_all_jobs(self):
        """
        Startet den Hauptprozess des Job-Scrapings asynchron.
        """
        page = 0
        logging.info("Starte asynchronen Job-Scraping-Prozess...")

        async with httpx.AsyncClient() as client:   # Initialisierung
            while True:
                url = f"{self.BASE_API_URL}?page={page}&size={self.PAGE_SIZE}"
                logging.info(f"Sammle Daten von Seite: {page} (URL: {url})")

                response = await self._make_request(client, url, delay=True)

                if response is None:
                    logging.error(f"Fehler beim Abrufen der Seite {page}. Abbruch.")
                    break

                try:
                    job_data = response.json()
                except json.JSONDecodeError as e:
                    logging.error(f"Fehler beim Parsen der JSON-Antwort von Seite {page}: {e} - Kein gültiges JSON?")
                    break

                entries = job_data.get('entries')
                if not entries:
                    logging.info(f"Keine weiteren Jobs auf Seite {page} gefunden. Beende das Scrapen.")
                    break
        
                tasks = []
                for job in entries:
                    job_summary = self._extract_job_summary(job)
                    tasks.append(self._process_job_detail(client, job_summary))

                processed_jobs = await asyncio.gather(*tasks)

                self.all_jobs_details.extend(processed_jobs)

                logging.info(f"Bisher gesammelte Jobs: {len(self.all_jobs_details)}")

                page += 1
                # TESTLIMIT --- 
                if page >= 1000: 
                    logging.info(f"Test-Limit erreicht. Beende Scrapen.")
                    break

    def save_failed_details(self, filename='failed_job_details.json'):
        """
        Speichert die Liste der fehlgeschlagenen Detail-Anfragen in einer JSON-Datei.
        """
        if not self.failed_details:
            logging.info("Keine fehlgeschlagenen Detailseiten zum Speichern gefunden.")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.failed_details, f, ensure_ascii=False, indent=4)
            logging.info(f"Fehlgeschlagene Detailseiten erfolgreich in '{filename}' gespeichert!")
        except IOError as e:
            logging.error(f"Fehler beim Speichern der Datei '{filename}': {e}")
            
    def save_missed_descriptions(self, filename='missed_descriptions.json'):
        """
        Speichert die Liste der Jobs, bei denen die Beschreibung nicht gefunden/extrahiert werden konnte.
        """
        if not self.missed_descriptions:
            logging.info("Keine Jobs mit fehlenden Beschreibungen zum Speichern gefunden.")
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.missed_descriptions, f, ensure_ascii=False, indent=4)
            logging.info(f"Jobs mit fehlenden Beschreibungen erfolgreich in '{filename}' gespeichert!")
        except IOError as e:
            logging.error(f"Fehler beim Speichern der Datei '{filename}': {e}")


    def save_to_json(self):
        """
        Speichert die gesammelten Jobdetails in einer JSON-Datei.
        (Diese Funktion ist synchron)
        """
        if not self.all_jobs_details:
            logging.warning("Keine Jobdaten zum Speichern vorhanden.")
            return
        try:
            with open(self.output_json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_jobs_details, f, ensure_ascii=False, indent=4)
            logging.info(f"Alle Jobdetails wurden erfolgreich in {self.output_json_filename} gespeichert!")
        except IOError as e:
            logging.error(f"Fehler beim Speichern der Datei '{self.output_json_filename}': {e}")


if __name__ == "__main__":
    start_time = time.time()
    logging.info("Programm Start")

    scraper = AsyncEdekaJobScraper()

    asyncio.run(scraper.fetch_all_jobs()) # Startet die asynchrone Hauptfunktion

    scraper.save_to_json() # Speichert die Daten synchron
    scraper.save_failed_details() # NEU: Fehlgeschlagene Detailanfragen speichern
    scraper.save_missed_descriptions() # NEU: Fehlende/fehlerhafte Beschreibungen speichern


    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Programm beendet. Laufzeit: {duration:.2f} Sekunden.")