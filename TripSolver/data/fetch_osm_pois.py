# fetch_osm_pois.py
# ------------------------------------------------------------
# OBIETTIVO
#   Estrarre punti di interesse turistici REALI da OpenStreetMap (OSM)
#   per una città a scelta, tramite l'API pubblica Overpass, e salvarli
#   in un CSV con uno schema il più possibile vicino a quello atteso da
#   ontology/build_kb.py.
#
# IMPORTANTE
#   Questo script richiede accesso a Internet libero (chiama
#   https://overpass-api.de). NON è eseguibile nell'ambiente sandbox in
#   cui è stato generato il resto del progetto (rete ristretta ai soli
#   repository di pacchetti): 
#
# LICENZA DATI
#   I dati OpenStreetMap sono distribuiti con licenza ODbL: cita sempre
#   "© OpenStreetMap contributors" nella tua relazione/repository.
#
# USO
#   pip install requests
#   python data/fetch_osm_pois.py --city "Bari, Italy" --out data/poi_osm_raw.csv
#
# NOTE
#   - Il tag OSM usato per individuare i POI turistici è `tourism=*`
#     (museum, attraction, gallery, viewpoint, ...) più alcuni tag
#     affini (`historic=*`, `leisure=beach`, `amenity=place_of_worship`).
#     Puoi ampliare/restringere la query modificando OSM_FILTER.
#   - I campi `opening_hour` / `closing_hour` NON sono affidabili da OSM
#     per la maggior parte dei POI (il tag `opening_hours` è spesso
#     assente o in formato complesso, non un singolo range numerico):
#     lo script prova un parsing "best effort" del caso più semplice
#     (es. "Mo-Su 09:00-19:00") e lascia NaN altrove. Vanno SEMPRE
#     rivisti/integrati a mano per i POI principali del tuo itinerario,
#     come fatto in data/SOURCES.md per i 4 POI verificati.
#   - `visit_duration_min` non esiste su OSM: va comunque stimato/curato
#     manualmente per categoria, analogamente al dataset corrente.
# ------------------------------------------------------------

import argparse
import csv
import re
import sys
import time

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OSM_FILTER = """
  node["tourism"~"museum|attraction|gallery|viewpoint|artwork"](area.searchArea);
  node["historic"](area.searchArea);
  node["amenity"="place_of_worship"](area.searchArea);
  node["leisure"="beach_resort"](area.searchArea);
  way["tourism"~"museum|attraction|gallery"](area.searchArea);
  way["historic"](area.searchArea);
"""


def build_query(city: str) -> str:
    return f"""
    [out:json][timeout:60];
    area["name"="{city.split(',')[0].strip()}"]->.searchArea;
    (
    {OSM_FILTER}
    );
    out center tags;
    """


def parse_simple_opening_hours(raw: str):
    """Parsing best-effort di formati semplici tipo 'Mo-Su 09:00-19:00'.
    Ritorna (opening_hour, closing_hour) come float, oppure (None, None)
    se il formato non è quello atteso (caso molto comune: in tal caso
    il dato va integrato manualmente)."""
    if not raw:
        return None, None
    m = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", raw)
    if not m:
        return None, None
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    return round(h1 + m1 / 60, 2), round(h2 + m2 / 60, 2)


def fetch(city: str):
    try:
        import requests
    except ImportError:
        sys.exit("Serve il pacchetto 'requests': pip install requests")

    query = build_query(city)
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
    resp.raise_for_status()
    return resp.json().get("elements", [])


def to_rows(elements):
    rows = []
    for i, el in enumerate(elements, start=1):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue  # scarta elementi senza nome (poco utili in un itinerario)

        lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
        lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
        if lat is None or lon is None:
            continue

        category = tags.get("tourism") or tags.get("historic") or tags.get("amenity") or "altro"
        oh, ch = parse_simple_opening_hours(tags.get("opening_hours", ""))

        rows.append({
            "id": i,
            "name": name,
            "category": category,
            "neighborhood": "",  # da assegnare manualmente o via reverse-geocoding
            "lat": lat,
            "lon": lon,
            "opening_hour": oh if oh is not None else "",
            "closing_hour": ch if ch is not None else "",
            "visit_duration_min": "",   # da stimare manualmente per categoria
            "indoor": "",               # da assegnare manualmente
            "free_entry": "",           # da assegnare manualmente
            "iconic": "",                # da assegnare manualmente
            "tourist_tier": "",         # da assegnare manualmente
            "data_source": "OpenStreetMap (estrazione automatica)",
            "source_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True, help='Es. "Bari, Italy"')
    parser.add_argument("--out", default="data/poi_osm_raw.csv")
    args = parser.parse_args()

    print(f"[INFO] Interrogo Overpass API per: {args.city} ...")
    elements = fetch(args.city)
    print(f"[INFO] {len(elements)} elementi grezzi ricevuti da OSM.")

    rows = to_rows(elements)
    print(f"[INFO] {len(rows)} POI con nome e coordinate valide.")

    if not rows:
        print("[WARN] Nessun risultato: verifica il nome città o la query.")
        return

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Salvato: {args.out}")
    print("[NOTA] Completare manualmente: neighborhood, visit_duration_min, "
          "indoor, free_entry, iconic, tourist_tier (e verificare opening/closing_hour).")


if __name__ == "__main__":
    main()
