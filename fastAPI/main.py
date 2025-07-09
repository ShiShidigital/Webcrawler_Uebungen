# main.py
from fastapi import FastAPI, Query, HTTPException, status 
from pydantic import BaseModel, Field 
import random 
import string 
import logging
from typing import List, Optional, Union


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# 1. FastAPI-Instanz erstellen, 'app' ist Hauptobjekt.
app = FastAPI(
    title="Passwort Generator API",
    description="Eine einfache API zum Generieren von sicheren Passwörtern.",
    version="1.0.0"
)

# 2. Zeichensets definieren
CHAR_SETS = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "special": string.punctuation # Sonderzeichen
}

# 3. Pydantic-Modell für die Antwort in JSON
class PasswordResponse(BaseModel):
    """
    Modell für die Antwort des Passwortgenerators.
    """
    password: str = Field(..., description="Das generierte Passwort")
    length: int = Field(..., description="Länge des Passworts")
    chars_used: str = Field(..., description="Verwendete Zeichentypen")

# 4. Pydantic Modell für die Jobdaten
# Modell für einen einzelnen Job-Eintrag
class EdekaJob(BaseModel):
    url: Optional[str] = None # Optional, da es "Keine URL vorhanden" geben könnte
    department: Optional[str] = None
    description: Optional[str] = None # Dieses Feld enthält das Markdown
    job_title: str # Ein JobTitel sollte immer vorhanden sein
    level: Optional[str] = None # Optional, da es "None" oder "Unbestimmt" sein kann
    # location kann ein String oder eine Liste von Strings sein (je nachdem, wie du es ursprünglich gescrapt hast)
    # Hier nehmen wir an, es ist ein String (der JOINED String aus dem Scraper).
    location: Optional[str] = None
    schedule: Optional[str] = None

# Antwortmodel für Bestätigung
class ImportResponse(BaseModel):
    status: str 
    message: str 
    imported_count: int = 0

# Speicherung importierter Daten in Liste
# In echt in einer Datenbank
_imported_jobs_storage = []

@app.post(
        "/jobs/import",
        response_model=ImportResponse,
        summary="Importiert eine Liste von Edk-Job Daten.",
        description="""
    Dieser Endpunkt empfängt eine JSON-Payload, die eine Liste von Edk-Jobdaten enthält.
    Die Daten werden validiert und simuliert gespeichert.
    """
)
async def import_jobs(job_list_data: List[EdekaJob]): # Hier wird das Pydantic-Modell als Type-Hint verwendet
    """
    Empfängt die Jobdaten und simuliert die speicherung.
    """
    logging.info(f"Anfrage zum Importieren von {len(job_list_data)} Jobs enthalten")

    imported_count = 0
    for job_data in job_list_data:
        # Hier würde die Logik zur Verarbeitung jedes Jobs stehen:
        # - Datenbank-Speicherung
        # - Überprüfung auf Duplikate
        # - Weitere Verarbeitung, z.B. Indexierung für eine Suche
        
        # logging.info(f"DEBUGGING DESCRIPTION for job '{job_data.job_title}':\n---START---\n{job_data.description}\n---ENDE---")
        # Für diese Übung: Füge den Job einfach zu unserem simulierten Speicher hinzu
        _imported_jobs_storage.append(job_data.dict()) # .dict() konvertiert Pydantic-Modell zurück in ein Python-Dictionary
        imported_count += 1
        # logging.debug(f"Job {job_data.job_title} importiert.") # Nur für Debugging

    logging.info(f"Erfolgreich {imported_count} Jobs importiert.")

    return {
        "status": "success",
        "message": f"Erfolgreich {imported_count} Jobs importiert.",
        "imported_count": imported_count
    }

# Endpunkt um die importierten Jobs anzuzeigen
@app.get("/jobs/all", response_model=List[EdekaJob], summary="Gibt alle importierten Jobs zurück.")
async def get_all_imported_jobs():
    return _imported_jobs_storage


# 5. API-Route definieren
# Decorator, welcher der FastAPI sagt: Wenn eine GET-Anfrage an 
# '/generate-password" geht, dann rufe die Funktion darunter auf
@app.get(
    "/generate-password",
    response_model=PasswordResponse,
    summary="Generiert ein sicheres Passwort mit angepassten Optionen",
    description="""
    Diese Endpunkt ermöglicht es, ein zufälliges Passwort zu generieren.
    Sie können die Länge sowie die Art der Zeichen (Kleinbuchstaben, Großbuchstaben, Ziffern, Sonderzeichen)
    beeinflussen. Standardmäßig werden alle Zeichentypen verwendet.
    """
)
async def generate_password(
    length: int = Query(
        default=12,     # Standardlänge
        ge=4,   #Mindestlänge
        le=128,     #Maximale Länge 
        description="Die gewünschte Länge des Passworts. Zwischen 4 und 128 Zeichen."
    ),
    include_lower: bool = Query(True, description="Sollen Kleinbuchstaben (a-z) enthalten sein?"),
    include_upper: bool = Query(True, description="Sollen Großbuchstaben (A-Z) enthalten sein?"),
    include_digits: bool = Query(True, description="Sollen Ziffern (0-9) enthalten sein?"),
    include_special: bool = Query(True, description="Sollen Sonderzeichen (!@#$...) enthalten sein?"),  
):
    """
    Generiert ein zufälliges Passwort.
    """
    logging.info(f"Anfrage zum Generieren eines Passworts: Länge={length}, Lower={include_lower}, Upper={include_upper}, Digits={include_digits}, Specials={include_special}")

    # 6. Zeichenpool basierend auf Anfrageparameter zusammenstellen
    char_pool = ""
    chars_used_info = [] 

    if include_lower:
        char_pool += CHAR_SETS["lower"]
        chars_used_info.append("lower")
    if include_upper:
        char_pool += CHAR_SETS["upper"]
        chars_used_info.append("upper")
    if include_digits:
        char_pool += CHAR_SETS["digits"]
        chars_used_info.append("digits")
    if include_special:
        char_pool += CHAR_SETS["special"]
        chars_used_info.append("special")

    # 7. Fehlerbehandlung
    if not char_pool:
        logging.warning("Kein Zeichentyp ausgewählt.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mindestens ein Zeichentyp muss ausgewäht werden."
        )

    # 8. Passwort generieren
    password = ''.join(random.choice(char_pool) for _ in range(length))
    logging.info("Passwort erfolgreich generiert.")

    # 9. Antwort zurückgeben
    return {
        "password": password,
        "length": length,
        "chars_used": ", ".join(chars_used_info) if chars_used_info else "none"
    }
    
    # FastAPI fügt von sich aus einen Endpunkt für Dokumenatation hinzu

