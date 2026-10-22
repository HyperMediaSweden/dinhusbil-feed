#!/usr/bin/env python3
"""Bygger Adnami-feeds (XML + JSON) för Din Husbil från Empori DSO-API:et.

Körs av GitHub Actions varje timme. Skriver till docs/, som publiceras via GitHub Pages:
  docs/feed-<anläggning>.xml   – husbilar i lager, format som Hedins DataFeedWatch-feed
  docs/feed-<anläggning>.json  – samma data som JSON
docs/img/<artikelnr>.jpg      – produktfoto med bannerremsan bortskuren (image_url pekar hit)
  docs/index.html, docs/status.json – översikt och senaste körning
"""
import io, json, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from PIL import Image

API = "https://dinhusbil.dso.empori.se/dsoApi/v1/objects"
UA = {"User-Agent": "Mozilla/5.0 (HyperMedia feed-bygge)"}
FILIALER = ["Frillesås", "Jönköping", "Växjö", "Bockara"]
TYP = 2            # 2 = husbil, 1 = husvagn, 3 = bil
MAX_RADER = 50     # Adnamis tak
OUT = Path(__file__).parent / "docs"
IMG_DIR = OUT / "img"
PAGES_URL = "https://hypermediasweden.github.io/dinhusbil-feed"
BEHALL_HOJD = 0.81   # Din Husbils foton har en bannerremsa med logotyper längst ned (~18 %) som beskärs bort
BILD_BREDD = 1150

FUEL = {0: "", 1: "Bensin", 2: "Diesel"}
GEARBOX = {0: "Manuell", 1: "Automat"}
CONDITION = {1: "Ny", 2: "Begagnad"}
CATEGORY = {
    "Integrated": "Helintegrerad", "Half integrated": "Halvintegrerad",
    "Half integrated with roofbed": "Halvintegrerad med takbädd",
    "Van": "Plåtis", "Alcove": "Alkov", "Other": "Övrig",
    "Single axle": "Enkelaxlad", "Double axle": "Boggie",
}


def slug(s):
    return s.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")


def sek(n):
    return f"{int(round(n)):,}".replace(",", " ") + " SEK"


def fetch(filial):
    url = API + "?" + urllib.parse.urlencode({"type": TYP, "filials": filial})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)["items"]


def bild(i):
    """Hämtar första produktfotot, beskär bort bannerremsan och sparar en kopia i docs/img/.
    Returnerar den publika URL:en, eller Emporis original-URL om något går fel."""
    src = (i.get("images") or [""])[0]
    if not src:
        return ""
    namn = f'{i.get("articleNr")}.jpg'
    dest = IMG_DIR / namn
    try:
        if not dest.exists():
            url = src.split("?")[0] + f"?mw={BILD_BREDD}&mh=768&q=92&sf=1"
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                im = Image.open(io.BytesIO(r.read())).convert("RGB")
            im = im.crop((0, 0, im.width, int(im.height * BEHALL_HOJD)))
            im.save(dest, "JPEG", quality=85, optimize=True)
        return f"{PAGES_URL}/img/{namn}"
    except Exception as e:
        print(f"  bild misslyckades för {i.get('articleNr')}: {e}")
        return src


def rad(i):
    pris = i.get("price") or 0
    kampanj = i.get("salePrice") or 0
    har_kampanj = 0 < kampanj < pris
    visat = kampanj if har_kampanj else pris
    skick = CONDITION.get(i.get("condition"), "")
    bransle = FUEL.get(i.get("fuel"), "")
    vaxel = GEARBOX.get(i.get("gearbox"), "")
    return {
        "vehicle_id": i.get("articleNr"),
        "title": f'{i["brand"]} {i["model"]}'.strip(),
        "make": i.get("brand"),
        "model": i.get("model"),
        "year": i.get("year"),
        "body_style": CATEGORY.get(i.get("category"), i.get("category")),
        "condition": skick,
        "mileage": f'{i.get("milage", 0)} mil',
        "fuel_type": bransle,
        "transmission": vaxel,
        "beds": i.get("beds"),
        "price": sek(visat),
        "regular_price": sek(pris) if har_kampanj else "",
        "campaign": "Kampanjpris" if har_kampanj else "",
        "text": f'{i.get("year")} · {skick} · {i.get("milage", 0)} mil · {bransle} · {vaxel}',
        "length": f'{i.get("length")} cm' if i.get("length") else "",
        "details": " · ".join(x for x in [
            f'Längd {i.get("length")} cm' if i.get("length") else "",
            f'{i.get("beds")} sovplatser' if i.get("beds") else "",
            f'Årsmodell {i.get("year")}' if i.get("year") else "",
            skick, f'{i.get("milage", 0)} mil', bransle, vaxel] if x),
        "region": i.get("filial"),
        "image_url": bild(i),
        "image_url_original": (i.get("images") or [""])[0],
        "url": f'https://dinhusbil.nu/husbilar?item={i["uniqueId"]}',
        "_sort": visat,
    }


def skriv_xml(rows, path):
    delar = ['<?xml version="1.0" encoding="UTF-8" ?>', "<Products>"]
    for r in rows:
        delar.append("<Product>" + "".join(f"<{k}><![CDATA[{'' if v is None else v}]]></{k}>" for k, v in r.items()) + "</Product>")
    delar.append("</Products>")
    path.write_text("\n".join(delar) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    IMG_DIR.mkdir(exist_ok=True)
    anvanda = set()
    nu = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")
    status = {"updated": nu, "source": API, "feeds": {}}
    for filial in FILIALER:
        items = [i for i in fetch(filial) if not i.get("isSold")]
        rows = sorted((rad(i) for i in items), key=lambda r: r["_sort"])[:MAX_RADER]
        for r in rows:
            del r["_sort"]
            anvanda.add(Path(r["image_url"]).name)
        s = slug(filial)
        skriv_xml(rows, OUT / f"feed-{s}.xml")
        (OUT / f"feed-{s}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        status["feeds"][filial] = {"count": len(rows), "xml": f"feed-{s}.xml", "json": f"feed-{s}.json"}
        print(f"{filial}: {len(rows)} husbilar")

    # Rensa bilder för fordon som inte längre finns i lagret
    for f in IMG_DIR.glob("*.jpg"):
        if f.name not in anvanda:
            f.unlink()

    (OUT / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    rader = "".join(
        f'<tr><td>{f}</td><td>{d["count"]}</td><td><a href="{d["xml"]}">{d["xml"]}</a></td><td><a href="{d["json"]}">{d["json"]}</a></td></tr>'
        for f, d in status["feeds"].items())
    (OUT / "index.html").write_text(f"""<!doctype html><html lang="sv"><head><meta charset="utf-8">
<title>Din Husbil – Adnami-feeds</title>
<style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:8px;border-bottom:1px solid #ddd}}</style></head>
<body><h1>Din Husbil – Adnami-feeds</h1>
<p>Husbilar i lager per anläggning, hämtade från dinhusbil.nu (Empori DSO) varje timme.<br>Senast uppdaterad: <b>{nu}</b></p>
<table><tr><th>Anläggning</th><th>Antal</th><th>XML</th><th>JSON</th></tr>{rader}</table>
<p>Fält: title, price, image_url, url (mappas i Adnami), samt make, model, year, condition, mileage, fuel_type, transmission, beds, regular_price, campaign, text, region.</p>
</body></html>""", encoding="utf-8")


if __name__ == "__main__":
    main()
