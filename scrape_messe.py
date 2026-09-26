"""
Scrapt die Messe-Düsseldorf-Übersicht (Eigentermine über requests, mit
Playwright-Fallback für JS-gerenderte Inhalte). Schreibt messe.json.

Läuft unabhängig von den anderen Scrapern (eigener GitHub-Actions-Workflow).
"""
import re
import datetime as dt
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrape_common import UA, write_events_json

MESSE_URL = "https://www.messe-duesseldorf.de/de/messen_und_events/messen_national_und_international"
OUT_FILE = "messe.json"

GERMAN_DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
DAY_RE = r"(?:täglich|Mo|Di|Mi|Do|Fr|Sa|So)(?:\s*-\s*(?:Mo|Di|Mi|Do|Fr|Sa|So))?"
DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s*-\s*(\d{2})\.(\d{2})\.(\d{4}))?")


def parse_opening_hours(lines):
    hours = {}
    for line in lines:
        m = re.match(
            r"^(täglich|Mo|Di|Mi|Do|Fr|Sa|So)(?:\s*-\s*(Mo|Di|Mi|Do|Fr|Sa|So))?\s*:\s*"
            r"(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})$",
            line,
        )
        if not m:
            continue
        d1, d2, sh, sm, eh, em = m.groups()
        start, end = f"{int(sh):02d}:{sm}", f"{int(eh):02d}:{em}"
        if d1 == "täglich":
            for d in GERMAN_DAYS:
                hours[d] = (start, end)
        elif d2:
            i1, i2 = GERMAN_DAYS.index(d1), GERMAN_DAYS.index(d2)
            for i in range(i1, i2 + 1):
                hours[GERMAN_DAYS[i]] = (start, end)
        else:
            hours[d1] = (start, end)
    return hours


def expand_to_daily_rows(start_iso, end_iso, name, hours):
    d0 = dt.date.fromisoformat(start_iso)
    d1 = dt.date.fromisoformat(end_iso) if end_iso else d0
    rows, cur = [], d0
    while cur <= d1:
        wd = GERMAN_DAYS[cur.weekday()]
        note = f"{hours[wd][0]}–{hours[wd][1]} Uhr" if wd in hours else ""
        row = [cur.isoformat(), "", name, "messe"]
        if note:
            row.append(note)
        rows.append(row)
        cur += dt.timedelta(days=1)
    return rows


def parse_messe(html):
    soup = BeautifulSoup(html, "html.parser")
    out, seen_names = [], set()
    for li in soup.find_all("li"):
        lines = [l.strip() for l in li.get_text("\n", strip=True).split("\n") if l.strip()]
        text = "\n".join(lines)
        m = DATE_RE.search(text)

        if not m and "Veranstaltungsort" in text:
            m_single = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
            m_bis = re.search(r"bis\s+(\d{1,2})\.(\d{1,2})\.", text, re.IGNORECASE)
            if m_single:
                start = f"{m_single[3]}-{m_single[2]}-{m_single[1]}"
                if m_bis:
                    end_day = m_bis[1].zfill(2)
                    end_month = m_bis[2].zfill(2)
                    end_year = m_single[3]
                    end = f"{end_year}-{end_month}-{end_day}"
                else:
                    end = start

                name = lines[0] if lines else "Messe"
                if (name, start) in seen_names:
                    continue
                seen_names.add((name, start))

                out.append([start, end if end != start else "", name, "messe"])
                continue

        if not m or "Veranstaltungsort" not in text or not lines or DATE_RE.match(lines[0]):
            continue

        name = lines[0]
        start = f"{m[3]}-{m[2]}-{m[1]}"
        end = f"{m[6]}-{m[5]}-{m[4]}" if m[4] else start
        if (name, start) in seen_names:
            continue
        seen_names.add((name, start))

        hour_lines = []
        if "Öffnungszeiten:" in lines:
            for l in lines[lines.index("Öffnungszeiten:") + 1:]:
                if re.match("^" + DAY_RE + r"\s*:", l) or l == "täglich:":
                    hour_lines.append(l)
                elif l.endswith(":"):
                    break
        hours = parse_opening_hours(hour_lines)

        if hours:
            out.extend(expand_to_daily_rows(start, end, name, hours))
        else:
            out.append([start, end if end != start else "", name, "messe"])
    return out


def main():
    events = []
    try:
        events = parse_messe(requests.get(MESSE_URL, headers=UA, timeout=30).text)
    except Exception as e:
        print("Messe requests Fehler:", e)

    if not events:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_context(locale="de-DE", user_agent=UA["User-Agent"]).new_page()
                page.goto(MESSE_URL, wait_until="networkidle")
                events = parse_messe(page.content())
                browser.close()
        except Exception as e:
            print("Messe Playwright Fehler:", e)

    write_events_json(OUT_FILE, events, label="Messe")


if __name__ == "__main__":
    main()
