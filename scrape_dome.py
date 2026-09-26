"""
Scrapt den PSD Bank Dome (D.Live-Eventkalender). Schreibt dome.json.

DEG-Heimspiele werden separat von scrape_deg.py gescrapt (eigener Workflow)
-> Einträge, die eigentlich DEG-Spiele sind, werden hier rausgefiltert
(umlaut-sicher erkannt), damit sie nicht doppelt auftauchen.
"""
from playwright.sync_api import sync_playwright

from scrape_common import UA, dlive, is_deg_title, write_events_json

DOME_URL = "https://www.psd-bank-dome.de/events-tickets/eventkalender"
OUT_FILE = "dome.json"


def main():
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="de-DE", user_agent=UA["User-Agent"]).new_page()
            events = dlive(page, "dome", DOME_URL)
            browser.close()
    except Exception as e:
        print("D.Live Dome Fehler:", e)

    events = [e for e in events if not is_deg_title(e[2])]

    write_events_json(OUT_FILE, events, label="Dome")


if __name__ == "__main__":
    main()
