# json_to_markdown_converter.py

import json
import os
import re # Für die Bereinigung von Dateinamen
import logging

# Konfiguriere das Logging-System für dieses Skript
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JsonToMarkdownConverter:
    """
    Eine Klasse zum Konvertieren einer JSON-Datei mit Jobdaten in separate
    Markdown-Dateien.
    """
    def __init__(self, input_json_filename='edk_job_data.json', output_markdown_dir='markdown_jobs'):
        """
        Initialisiert den Konverter.
        :param input_json_filename: Der Pfad zur JSON-Datei, die die Jobdaten enthält.
        :param output_markdown_dir: Das Verzeichnis, in dem die Markdown-Dateien gespeichert werden.
        """
        self.input_json_filename = input_json_filename
        self.output_markdown_dir = output_markdown_dir
        self.job_data = [] # Hier werden die JSON-Daten geladen

    def _load_job_data(self):
        """
        Lädt die Jobdaten aus der angegebenen JSON-Datei.
        """
        if not os.path.exists(self.input_json_filename):
            logging.error(f"Eingabe-JSON-Datei '{self.input_json_filename}' nicht gefunden. Bitte zuerst scrapen.")
            return False

        try:
            with open(self.input_json_filename, 'r', encoding='utf-8') as f:
                self.job_data = json.load(f)
            logging.info(f"Jobdaten erfolgreich aus '{self.input_json_filename}' geladen.")
            if not self.job_data:
                logging.warning("JSON-Datei enthält keine Jobdaten.")
                return False
            return True
        except json.JSONDecodeError as e:
            logging.error(f"Fehler beim Parsen der JSON-Datei '{self.input_json_filename}': {e}")
            return False
        except Exception as e:
            logging.error(f"Unerwarteter Fehler beim Laden der JSON-Datei '{self.input_json_filename}': {e}")
            return False

    def _sanitize_filename(self, text, max_length=150):
        """
        Bereinigt einen Text für die Verwendung als Dateiname.
        Entfernt ungültige Zeichen und kürzt die Länge.
        """
        # Ersetze ungültige Zeichen durch Unterstriche
        sanitized = re.sub(r'[\\/:*?"<>|]', '-', text)
        # Ersetze ungültige Zeichen durch Leerzeichen
        sanitized = sanitized.replace('/', '-').replace('\\', '-')
        
        # Entferne führende/nachfolgende Leerzeichen und ersetze mehrere Leerzeichen durch eines
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Kürze den Namen, falls er zu lang ist
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Ein finaler Check, um sicherzustellen, dass nicht nur Leerzeichen übrig sind
        if not sanitized:
            return "untitled"
            
        return sanitized

    def convert_and_save(self):
        """
        Führt den Konvertierungsprozess von JSON zu Markdown aus.
        """
        if not self._load_job_data():
            return

        # Erstelle das Ausgabe-Verzeichnis, falls es nicht existiert
        if not os.path.exists(self.output_markdown_dir):
            os.makedirs(self.output_markdown_dir)
            logging.info(f"Ausgabeverzeichnis für Markdown erstellt: '{self.output_markdown_dir}'")
        else:
            logging.info(f"Ausgabeverzeichnis für Markdown existiert bereits: '{self.output_markdown_dir}'")

        logging.info(f"Beginne mit dem Speichern von {len(self.job_data)} Jobs als Markdown-Dateien.")
        for i, job in enumerate(self.job_data):
            job_title = job.get('job_title', f'Unbenannter Job {i}')
            location = job.get('location', 'Unbekannt')
            
            # Dateiname bilden und bereinigen
            filename_base = self._sanitize_filename(f"{job_title} - {location}")
            # Fallback, falls der bereinigte Name leer wird
            if not filename_base:
                filename_base = f"job_{i}"

            file_path = os.path.join(self.output_markdown_dir, f"{filename_base}.md")

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {job_title}\n\n")
                    f.write(f"**Standort:** {job.get('location', 'Unbestimmt')}\n")
                    f.write(f"**Abteilung:** {job.get('department', 'Unbestimmt')}\n")
                    f.write(f"**URL:** {job.get('url', 'Nicht verfügbar')}\n")
                    f.write(f"**Zeitart:** {job.get('schedule', 'Unbestimmt')}\n\n")
                    f.write("---\n\n") # Trennlinie

                    f.write("## Beschreibung\n\n")
                    # Python wandelt hier die '\n' Escape-Sequenzen beim Laden des JSON automatisch um.
                    f.write(job.get('description', 'Keine Beschreibung vorhanden.'))
                    f.write("\n") # Sicherstellen, dass am Ende ein Umbruch ist

                logging.info(f"Job '{job_title}' als Markdown gespeichert: {file_path}")
            except IOError as e:
                logging.error(f"Fehler beim Speichern von Markdown für '{job_title}' in '{file_path}': {e}")
            except Exception as e:
                logging.error(f"Unerwarteter Fehler beim Schreiben von Markdown für '{job_title}': {e}")

        logging.info("Speichern der Markdown-Dateien abgeschlossen.")

# Dieser Block wird ausgeführt, wenn das Skript direkt gestartet wird
if __name__ == "__main__":
    logging.info("Start der JSON-zu-Markdown-Konvertierung.")
    
    # Hier kannst du anpassen, welche JSON-Datei gelesen und wohin gespeichert werden soll
    converter = JsonToMarkdownConverter(
        input_json_filename='edk_job_data.json', 
        output_markdown_dir='markdown_jobs'
    )
    converter.convert_and_save()
    
    logging.info("JSON-zu-Markdown-Konvertierung beendet.")
