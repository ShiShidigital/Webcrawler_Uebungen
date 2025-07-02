import requests
from bs4 import BeautifulSoup
import json
import time
from html import unescape
from markdownify import markdownify as md


# Basis-URL der API
base_url = "https://verbund.edeka/api/v2/career/vacancies"

# Statische Liste der weiteren HTTP-Header, falls nötig (z. B. User-Agent)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Funktion zur Extraktion der gewünschten Job-Details
def extract_job_details(job):
    return {
        "url": job.get("detailPageUrl"),
        "department": job.get("companyName"),  # Department-Information als "N/A", anpassen, wenn verfügbar
        "description": None,
        "job_title": job.get("title"),
        "level": "None",  # Basierend auf der vorherigen Struktur
        "location": [job.get("locationName"), 
                     job.get("locationStreet"),
                     job.get("locationZipCode"), 
                     job.get("locationCity")],  # Als String bereits angegeben
        "schedule": job.get("timeType") or "None"  # Default zu "None", wenn 'timeType' nicht vorhanden
    }

# Jobbeschreibungen
# Funktion zur Extraktion der Beschreibung aus dem HTML-String
def extract_description_from_html(html_content):
    try:
        description_tag = None

        # Suche nach JSON-Daten im HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        script = soup.find('script', type='application/ld+json')
        # print("Found Script:", script)

        if script:
            # print("Found JSON-LD script")
            script_content = script.string
            # print(f"Script content: {script_content}")
            if script_content:
                # Parsing der JSON-Struktur
                json_data = json.loads(script_content)
                # print(json_data)
                
                # Prüfe, ob der Typ JobPosting ist
                if json_data.get('@type') == 'JobPosting':
                    description = json_data.get('description')
                    # print(description)
                    description = unescape(description)
                    return md(description.strip())
                    
        
        # Fallback: Suchen nach einem spezifischen HTML-Tag, falls notwendig
        description_tag = soup.find("div", {"class": "job-description"})  # Beispieleingabe
        if description_tag:
            return md(description_tag.get_text(strip=True))

        return "Keine Beschreibung gefunden"
    
    except Exception as e:
        print(f"Error while extracting description: {e}")
        return "Fehler beim Abrufen der Beschreibung"



# Liste zur Sammlung aller extrahierten Job-Details
all_jobs_details = []

page = 0  # Start mit der ersten Seite
while True:
    print(f"Start collecting from page: {page}")
    time.sleep(1) # rate limit

    # URL für die aktuelle Seite
    url = f"{base_url}?page={page}&size=50"
    
    # Anfrage an die API senden
    response = requests.get(url)

    # Prüfen, ob die Anfrage erfolgreich war
    if response.status_code == 200:
        # print("Connection is there...")
        job_data = response.json()

        # Überprüfen, ob Jobs im aktuellen Batch vorhanden sind
        content = job_data.get('entries')  # Vorausgesetzt, die Jobs sind in 'content'
        # print("Content is there...")
        
        if content:
            temp_jobs = []

            for job in content:
                # Extrahierte Details für jeden Job hinzufügen
                job_info = extract_job_details(job)
                job_url = job_info.get('url')
                # print(job_url)

                # Überprüfung, ob die URL valide ist
                if job_url:
                    job_page_response = requests.get(job_url, headers=headers)
                    # print(job_page_response.status_code)
                    if job_page_response.status_code == 200:
                        job_info['description'] = extract_description_from_html(job_page_response.text)
                    else:
                        job_info['description'] = f"Fehler beim Abrufen der Seite: {job_page_response.status_code}"
                else:
                    job_info['description'] = "Keine URL vorhanden"

                temp_jobs.append(job_info)

            all_jobs_details.extend(temp_jobs)
            print(f"Total jobs collected: {len(all_jobs_details)}")


        else:
            # Keine Inhalte mehr, kannst die Schleife sicher beenden
            break

        # Seite erhöhen, um auf die nächste zu gehen
        page += 1
        if page == 20:
            break
    else:
        print(f"Fehler bei der Anfrage auf Seite {page}: {response.status_code}")
        break


# Die extrahierten Job-Daten in eine JSON-Datei schreiben
print("Start Scraping ...")
start_time = time.time()

json_file = 'edk_job_1000.json'
with open(json_file, 'w', encoding='utf-8') as f:
    print("Open file:", json_file)
    json.dump(all_jobs_details, f, ensure_ascii=False, indent=4)

print(f"Alle Jobdetails wurden erfolgreich in {json_file} gespeichert!")
end_time = time.time() 
print(f"Programm did run for {(end_time - start_time):.6f} seconds") # does not work