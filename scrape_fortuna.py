"""
Scrapt Fortuna-Düsseldorf-Heimspiele von fussballdaten.de. Schreibt fortuna.json.

Läuft unabhängig von scrape_arena.py (eigener GitHub-Actions-Workflow).
Die Events tragen venue="arena", damit sie in der index.html im selben
Filter wie die Merkur Spiel-Arena auftauchen.

Nutzt Playwright statt reinem requests.get(), weil fussballdaten.de bei
einfachen HTTP-Requests offenbar eine Schutz-/Challenge-Seite statt der
echten Spielplan-Seite ausliefert (leeres a[title]-Ergebnis).
"""
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrape_common import UA, write_events_json

FORTUNA_URL = "https://www.fussballdaten.de/vereine/fortuna-duesseldorf/spielplan/"
OUT_FILE = "fortuna.json"


def fortuna(page):
    page.goto(FORTUNA_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)

    soup = BeautifulSoup(page.content(), "html.parser")
    games = {}
    for a in soup.select("a[title]"):
        title = a.get("title", "")
        # Nur Heimspiele: Titel beginnt mit "Fortuna Düsseldorf - <Gegner> | <Datum> | <Wettbewerb> | ..."
        m = re.match(r"Fortuna Düsseldorf - (.+?) \| (\d{2})\.(\d{2})\.(\d{4}) \| (.+?) \|", title)
        if not m:
            continue
        href = a.get("href", title)
        g = games.setdefault(href, {"opp": m[1], "date": f"{m[4]}-{m[3]}-{m[2]}", "comp": m[5], "time": None})
        t = re.search(r"(\d{1,2}:\d{2})\s*Uhr", a.get_text())
        if t:
            g["time"] = t[1]

    out = []
    for g in games.values():
        pokal = "DFB" in g["comp"]
        note = f"Anstoß: {g['time']} Uhr" if g["time"] else "Anstoß noch offen"
        out.append([g["date"], "", f"Fortuna – {g['opp']}", "arena", ("DFB-Pokal, " if pokal else "") + note])
    return out


def main():
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="de-DE", user_agent=UA["User-Agent"]).new_page()
            events = fortuna(page)
            browser.close()
    except Exception as e:
        print("Fortuna Fehler:", e)

    write_events_json(OUT_FILE, events, label="Fortuna")


if __name__ == "__main__":
    main()
