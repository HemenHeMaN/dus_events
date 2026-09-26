"""
Scrapt die Merkur Spiel-Arena (D.Live-Eventkalender). Schreibt arena.json.

Fortuna-Düsseldorf-Spiele werden separat von scrape_fortuna.py gescrapt
(eigener Workflow) -> Einträge, die eigentlich Fortuna-Spiele sind, werden
hier rausgefiltert, damit sie nicht doppelt auftauchen.
"""
from playwright.sync_api import sync_playwright

from scrape_common import UA, dlive, is_fortuna_title, write_events_json

ARENA_URL = "https://www.merkur-spiel-arena.de/events-tickets/eventkalender"
OUT_FILE = "arena.json"


def main():
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="de-DE", user_agent=UA["User-Agent"]).new_page()
            events = dlive(page, "arena", ARENA_URL)
            browser.close()
    except Exception as e:
        print("D.Live Arena Fehler:", e)

    events = [e for e in events if not is_fortuna_title(e[2])]

    write_events_json(OUT_FILE, events, label="Arena")


if __name__ == "__main__":
    main()
