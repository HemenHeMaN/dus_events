"""
Scrapt die offizielle DEG-Seite nach Heimspielen (im PSD Bank Dome).
Schreibt deg.json.

Läuft unabhängig von scrape_dome.py (eigener GitHub-Actions-Workflow).
Die Events tragen venue="dome", damit sie in der index.html im selben
Filter wie der PSD Bank Dome auftauchen.
"""
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrape_common import UA, write_events_json

DEG_URL = "https://www.deg-eishockey.de/saison/spielplan/"
OUT_FILE = "deg.json"


def deg(page):
    page.goto(DEG_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2000)

    soup = BeautifulSoup(page.content(), "html.parser")
    out = []
    seen = set()

    for el in soup.select("tr, li, .game, .match, [class*='spiel']"):
        text = el.get_text(" | ", strip=True)
        m_date = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
        if not m_date:
            continue
        date_iso = f"{m_date[3]}-{m_date[2]}-{m_date[1]}"

        is_home = False
        if (re.search(r"\bHeim\b|\bH\b", text, re.IGNORECASE) and not re.search(r"\bAuswärts\b|\bA\b", text, re.IGNORECASE)) or \
           ("PSD Bank Dome" in text or "PSD BANK DOME" in text):
            is_home = True

        if not is_home:
            continue

        m_time = re.search(r"(\d{2}:\d{2})\s*Uhr", text)
        time_str = m_time[1] if m_time else ""
        note = f"Beginn: {time_str} Uhr" if time_str else "Beginn noch offen"

        opponent = ""
        parts = [p.strip() for p in text.split("|") if p.strip()]
        for p in parts:
            if "DEG" not in p and "Düsseldorf" not in p and not re.search(r"\d", p) and len(p) > 2 and "Dome" not in p and "Heim" not in p:
                opponent = p
                break
        if not opponent:
            opponent = "Heimspiel"

        title = f"DEG - {opponent}"

        if (date_iso, time_str) in seen:
            continue
        seen.add((date_iso, time_str))

        out.append([date_iso, "", title, "dome", note])

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
