"""
Scrapt die offizielle DEG-Spielplan-Seite und filtert Heimspiele (im PSD Bank
Dome) heraus. Schreibt deg.json.

Läuft unabhängig von scrape_dome.py (eigener GitHub-Actions-Workflow).
Die Events tragen venue="deg" (eigener Filter-Button in der index.html).

Seitenstruktur (Stand der Analyse): Der vollständige Saisonkalender listet
pro Spiel eine feste Zeilenfolge:
    "21."  "August"  "Freitag,"  "19.30 Uhr"  "SCB"  "2-4"  "DEG"
(Tag, Monat, Wochentag, Uhrzeit, Team1, Ergebnis/---, Team2). Das ZUERST
genannte Team ist das Heimteam. Es gibt zusätzlich einen Ticker oben auf der
Seite mit ähnlichen, aber anders strukturierten Einträgen ("Spieltag N ...");
der Zeilen-Scan unten erkennt gezielt nur das feste 4er-Präfix
Tag/Monat/Wochentag/Uhrzeit und ignoriert den Ticker automatisch, da dieser
kein Wochentag-Komma-Muster enthält.
"""
import re
import datetime as dt
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrape_common import UA, write_events_json

DEG_URL = "https://www.deg-eishockey.de/saison/spielplan/"
OUT_FILE = "deg.json"

MONTHS = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
    "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}
WEEKDAYS = {"Montag,", "Dienstag,", "Mittwoch,", "Donnerstag,", "Freitag,", "Samstag,", "Sonntag,"}
DAY_RE = re.compile(r"^\d{1,2}\.$")
TIME_RE = re.compile(r"^(\d{1,2})[.:](\d{2})\s*Uhr$")


def season_year_for_month(month_num):
    """DEL2-Saisons laufen über den Jahreswechsel (Aug-Mai). Ordnet einem
    Monat das richtige Kalenderjahr relativ zum heutigen Datum zu."""
    now = dt.datetime.now()
    season_start_year = now.year if now.month >= 7 else now.year - 1
    return season_start_year if month_num >= 7 else season_start_year + 1


def deg(page):
    page.goto(DEG_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)

    soup = BeautifulSoup(page.content(), "html.parser")
    lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]

    out = []
    seen = set()

    for i in range(len(lines) - 6):
        if not DAY_RE.match(lines[i]):
            continue
        if lines[i + 1] not in MONTHS:
            continue
        if lines[i + 2] not in WEEKDAYS:
            continue
        m_time = TIME_RE.match(lines[i + 3])
        if not m_time:
            continue

        day = int(lines[i][:-1])
        month_num = MONTHS[lines[i + 1]]
        year = season_year_for_month(month_num)
        time_str = f"{m_time[1]}:{m_time[2]}"

        team1 = lines[i + 4]
        team2 = lines[i + 6]

        # Nur Heimspiele: DEG steht als erstes Team.
        if team1 != "DEG":
            continue
        opponent = team2

        try:
            date_iso = dt.date(year, month_num, day).isoformat()
        except ValueError:
            continue

        key = (date_iso, time_str, opponent)
        if key in seen:
            continue
        seen.add(key)

        title = f"DEG - {opponent}"
        note = f"Beginn: {time_str} Uhr"
        out.append([date_iso, "", title, "deg", note])

    return out


def main():
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="de-DE", user_agent=UA["User-Agent"]).new_page()
            events = deg(page)
            browser.close()
    except Exception as e:
        print("DEG Fehler:", e)

    write_events_json(OUT_FILE, events, label="DEG")


if __name__ == "__main__":
    main()
