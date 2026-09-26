"""
Gemeinsame Hilfsfunktionen für alle einzelnen Scraper (scrape_arena.py,
scrape_dome.py, scrape_meh.py, scrape_messe.py).

Jeder einzelne Scraper importiert daraus, was er braucht, läuft aber als
eigener, unabhängiger Prozess mit eigener JSON-Ausgabedatei.
"""
import json
import re
import pathlib
import datetime as dt

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
TODAY = dt.datetime.now().date().isoformat()

JS_DETAIL = r"""() => {
    const body = document.body ? document.body.innerText : "";

    const get = label => {
        // Erlaubt optional das Wort "ab" nach dem Label (z.B. "Einlass ab 18:00")
        const re = new RegExp(label + "(?:\\s+ab)?\\s*:?\\s*(\\d{1,2}[:.]\\d{2})", "i");
        const m = body.match(re);
        return m ? m[1].replace(".", ":") + " Uhr" : "";
    };

    const einlass = get("Einlass");
    const beginn  = get("Beginn");
    const ende    = get("Ende");

    const parts = [];
    if (einlass) parts.push("Einlass: " + einlass);
    if (beginn)  parts.push("Beginn: " + beginn);
    if (ende)    parts.push("Ende: " + ende);

    return parts.join(" | ");
}"""

JS_CALENDAR = r"""els => els.map(e => {
    let n = e;
    for (let i = 0; i < 7; i++) {
        n = n.parentElement;
        if (!n) break;
        // Alle Überschriften im Block einsammeln, um z.B. Künstler + Moderation zu kombinieren
        const headings = n.querySelectorAll('h1,h2,h3,h4,h5');
        if (headings && headings.length > 0) {
            const texts = Array.from(headings).map(h => h.innerText.trim()).filter(Boolean);
            if (texts.length > 0) {
                // Mehrere gefundene Titel sauber mit " / " verknüpfen
                return [e.href, texts.join(' / ')];
            }
        }
    }
    return [e.href, ""];
})"""


def slug_title(slug):
    return re.sub(r"-\d{2}-\d{2}-\d{4}$", "", slug).replace("-", " ").title()


def normalize(s):
    """Normalisiert Umlaute/ß für Umlaut-unabhängige Textvergleiche."""
    if not s:
        return ""
    repl = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


def is_deg_title(title):
    """Erkennt Titel, die sich auf die Düsseldorfer EG (Eishockey) beziehen,
    unabhängig von Umlaut-Schreibweise."""
    t = normalize(title)
    return bool(re.search(r"\bDEG\b", title)) or "Duesseldorfer EG" in t


def is_fortuna_title(title):
    return "Fortuna" in title


def detail_time(page, href):
    try:
        page.goto(href, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(700)
        return page.evaluate(JS_DETAIL)
    except Exception as e:
        print("Detailseite Fehler:", href, e)
        return ""


def dlive(page, venue, url):
    """Scrapt einen D.Live-Eventkalender (Arena / Dome / MEH) inkl. Zeiten
    von den jeweiligen Detailseiten."""
    page.goto(url, wait_until="networkidle", timeout=60000)

    try:
        page.wait_for_selector('a[href]', timeout=5000)
        page.wait_for_timeout(1500)
    except Exception:
        pass

    for _ in range(40):
        btn = page.get_by_text("Mehr Events anzeigen")
        if btn.count() == 0 or not btn.first.is_visible():
            break
        try:
            btn.first.click(force=True)
            page.wait_for_timeout(1500)
        except Exception:
            break

    links = page.eval_on_selector_all('a[href]', JS_CALENDAR)

    found = {}
    for href, title in links:
        if not href:
            continue

        slug = href.rstrip("/").split("/")[-1]
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})$", slug)
        if not m:
            continue

        date = f"{m[3]}-{m[2]}-{m[1]}"
        title = title.strip() if title else slug_title(slug)
        found[href] = (date, title)

    out = []
    print(venue, "-", len(found), "Termine gefunden")

    for href, (date, title) in found.items():
        uhrzeit = detail_time(page, href)
        out.append([date, "", title, venue, uhrzeit])

    return out


def write_events_json(path, events, label=""):
    """Schreibt die events.json einer einzelnen Quelle. Fällt bei leerer
    Ergebnisliste auf die vorherige Datei zurück, damit ein einzelner
    Scrape-Fehler die Webseite nicht leerräumt."""
    out = pathlib.Path(path)
    old = []
    if out.exists():
        try:
            old = json.loads(out.read_text(encoding="utf-8")).get("events", [])
        except Exception:
            old = []

    if not events and old:
        print(f"{label}: keine neuen Events gefunden, behalte alten Stand ({len(old)} Events)")
        events = old

    events = [e for e in events if (e[1] or e[0]) >= TODAY]
    events = sorted({json.dumps(e, ensure_ascii=False) for e in events})
    events = sorted((json.loads(e) for e in events), key=lambda e: (e[0], e[2]))

    out.write_text(json.dumps({"updated": TODAY, "events": events}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{label}: {len(events)} Events geschrieben nach {out}")
