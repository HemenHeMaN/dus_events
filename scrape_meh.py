"""
Scrapt die Mitsubishi Electric Halle (D.Live-Eventkalender). Schreibt meh.json.

Läuft unabhängig von den anderen Scrapern (eigener GitHub-Actions-Workflow).
"""
from playwright.sync_api import sync_playwright

from scrape_common import UA, dlive, write_events_json

MEH_URL = "https://www.mitsubishi-electric-halle.de/events-tickets/eventkalender"
OUT_FILE = "meh.json"


def main():
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="de-DE", user_agent=UA["User-Agent"]).new_page()
            events = dlive(page, "meh", MEH_URL)
            browser.close()
    except Exception as e:
        print("D.Live MEH Fehler:", e)

    write_events_json(OUT_FILE, events, label="MEH")


if __name__ == "__main__":
    main()
