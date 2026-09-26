"""
Scrapt Fortuna-Düsseldorf-Spiele von fussballdaten.de. Schreibt fortuna.json.

Läuft unabhängig von scrape_arena.py (eigener GitHub-Actions-Workflow).
Die Events tragen venue="arena", damit sie in der index.html im selben
Filter wie die Merkur Spiel-Arena auftauchen.
"""
import re
import requests
from bs4 import BeautifulSoup

from scrape_common import UA, write_events_json

FORTUNA_URL = "https://www.fussballdaten.de/vereine/fortuna-duesseldorf/spielplan/"
OUT_FILE = "fortuna.json"


def fortuna():
    soup = BeautifulSoup(requests.get(FORTUNA_URL, headers=UA, timeout=30).text, "html.parser")
    games = {}
    for a in soup.select("a[title]"):
        m = re.match(r"Fortuna Düsseldorf - (.+?) \| (\d{2})\.(\d{2})\.(\d{4}) \| (.+?) \|", a["title"])
        if not m:
            continue
        g = games.setdefault(a["href"], {"opp": m[1], "date": f"{m[4]}-{m[3]}-{m[2]}", "comp": m[5], "time": None})
        t = re.search(r"(\d{2}:\d{2})\s*Uhr", a.get_text())
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
        events = fortuna()
    except Exception as e:
        print("Fortuna Fehler:", e)

    write_events_json(OUT_FILE, events, label="Fortuna")


if __name__ == "__main__":
    main()
