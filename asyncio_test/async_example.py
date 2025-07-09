import asyncio
import httpx
import time 
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# asynchrone Funktion
async def fetch_url(client: httpx.AsyncClient, url: str, delay: float = 0):
    """
    Simuliert das Abrufen einer URL asynchron.
    """
    logging.info(f"Starte Abruf von: {url} (Delay: {delay}s)")
    try:
        # await, wartet auf eine I/O-Operation
        # Während httpx.get() auf Antwort wartet, kann Event Loop andere Coroutinen ausführen.
        await asyncio.sleep(delay)  # Simuliert Netzwerk Latenz
        response = await client.get(url, timeout=5)
        response.raise_for_status() # Löst HTTPError für 4xx/5xx Statuscodes aus.
        logging.info(f"Fertig mit Abruf von: {url} (Status: {response.status_code})")
        return f"Erfolg: {url} (Datenlänge: {len(response.text)})"
    except httpx.HTTPError as e:
        logging.error(f"HTTP Fehler bei {url}: {e}")
        return f"Fehler: {url} - {e}"
    except asyncio.TimeoutError:
        logging.error(f"Timeout bei {url}")
        return f"Fehler: {url} - Timeout"
    except Exception as e:
        logging.error(f"Unerwarteter Fehler bei {url}: {e}")
        return f"Fehler: {url} - {e}"
    

# Hauptfunktion, die alle asynchronen Operationen startet
async def main():
    start_time = time.time()
    logging.info("Starte asynchrones Beispielprogramm...")

    urls = [
        "https://www.google.com",
        "https://www.yahoo.com",
        "https://www.bing.com",
        # Beispiele für Fehler/Timeouts (können Fehler werfen, wenn sie nicht existieren oder sehr langsam sind)
        "https://httpstat.us/500", # Serverfehler
        "https://jfdlskjflkdjflaskjfdls.com", # Nicht existierende Domain
        "https://httpstat.us/200?sleep=8000" # Simulierter Timeout
    ]

    # Asynchroner HTTP-Client Kontextmanager
    async with httpx.AsyncClient() as client:
        # Hier starten wir alle fetch_url Coroutinen gleichzeitig.
        # asyncio.gather wartet, bis alle Coroutinen abgeschlossen sind und sammelt ihre Ergebnisse.
        # Die Coroutinen laufen nicht parallel auf separaten CPU-Kernen, sondern gleichzeitig im selben Thread.
        # Wenn eine Coroutine auf I/O wartet (wie eine Netzwerkanfrage), gibt sie die Kontrolle an den Event Loop zurück,
        # der dann eine andere Coroutine ausführen kann.
        tasks = [fetch_url(client, url) for url in urls]
        tasks.append(fetch_url(client, "https://www.python.org", delay=3))
        tasks.append(fetch_url(client, "https://docs.python.org", delay=1))

        results = await asyncio.gather(*tasks)

    logging.info("\n--- Ergebnisse ---")
    for result in results:
        logging.info(result)

    end_time = time.time()
    logging.info(f"Asynchrones Beispielprogramm beendet. Laufzeit: {end_time - start_time:.2f} Sekunden.")


if __name__ == "__main__":
    asyncio.run(main())
