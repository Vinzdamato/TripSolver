# build_kb.py
# ------------------------------------------------------------
# OBIETTIVO
#   Costruire una Knowledge Base (KB) in OWL a partire dal dataset dei POI,
#   eseguire un reasoner OWL (HermiT/Pellet) per inferire l'appartenenza
#   dei punti di interesse a classi semantiche definite tramite regole,
#   e generare un CSV "arricchito" con le nuove feature booleane inferite.
#
# MOTIVAZIONE
#   Le classi semantiche (es. ItinerarioVeloce, EsperienzaImmersiva,
#   IconaGratuita) codificano conoscenza di dominio (background knowledge)
#   sotto forma di regole OWL (EquivalentTo) anziché come semplici colonne
#   calcolate "a mano": è il reasoner a inferire automaticamente
#   l'appartenenza di ciascun individuo (POI) alle classi, a partire dalle
#   sole DataProperty popolate nella A-Box. Questo è il cuore della
#   "rappresentazione e ragionamento" richiesti dal programma del corso.
#
# INPUT
#   - data/poi_bari_sample.csv
#     (vedi README per i vincoli sulle colonne richieste)
#
# OUTPUT
#   - ontology/trip_ontology.owl     : ontologia popolata (T-Box + A-Box)
#   - data/poi_enriched.csv          : dataset originale + colonne semantiche (is_*)
#
# NOTE TECNICHE
#   - Per HermiT/Pellet serve una JVM (Java) installata.
#   - Le soglie numeriche in OWL vengono espresse tramite datatype
#     restrictions (ConstrainedDatatype) per ottenere inferenza corretta
#     con Owlready2.
#
# DECISIONE DI PROGETTO: soglie data-driven, non arbitrarie
#   Le soglie di durata che definiscono VisitaRapida/EsperienzaImmersiva
#   NON sono costanti fissate a mano: vengono calcolate automaticamente
#   come 25° e 75° percentile della distribuzione di visit_duration_min
#   nel dataset corrente (vedi compute_duration_thresholds()). In questo
#   modo: (a) le classi restano sempre bilanciate rispetto ai dati a
#   disposizione, anche se il dataset viene sostituito/ampliato (es. con
#   dati OSM reali, cfr. data/SOURCES.md), e (b) la scelta è motivabile
#   in relazione con un argomento riproducibile ("il 25% delle tappe più
#   brevi/lunghe del nostro catalogo"), invece di un numero arbitrario.
#   Le soglie effettivamente usate vengono comunque stampate a schermo e
#   salvate in ontology/thresholds_used.txt per tracciabilità.
# ------------------------------------------------------------

import time
import pandas as pd
from owlready2 import (
    get_ontology, Thing, DataProperty, ObjectProperty,
    ConstrainedDatatype,
    sync_reasoner, sync_reasoner_pellet
)

# -----------------------------
# Configurazione I/O
# -----------------------------
INPUT_CSV = "data/poi_bari_sample.csv"
OUT_ENRICHED_CSV = "data/poi_enriched.csv"
OUT_OWL = "ontology/trip_ontology.owl"

SEM_FEATURES = [
    "is_VisitaRapida",
    "is_EsperienzaImmersiva",
    "is_IconaGratuita",
    "is_AltaPriorita",
    "is_AdattoMaltempo",      # indoor -> buona alternativa in caso di pioggia
    "is_DaAbbinareVicino",    # POI nel cuore di Bari Vecchia, facilmente combinabile
]

# -----------------------------
# Caricamento dataset
# -----------------------------
df = pd.read_csv(INPUT_CSV, dtype={
    "opening_hour": float,
    "closing_hour": float,
})

required_cols = {
    "id", "name", "category", "neighborhood", "lat", "lon",
    "opening_hour", "closing_hour", "visit_duration_min",
    "indoor", "free_entry", "iconic", "tourist_tier",
}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Mancano queste colonne in {INPUT_CSV}: {sorted(missing)}")

# Conversione difensiva dei tipi
df["visit_duration_min"] = df["visit_duration_min"].astype(int)
df["indoor"] = df["indoor"].astype(int)
df["free_entry"] = df["free_entry"].astype(int)
df["iconic"] = df["iconic"].astype(int)


def compute_duration_thresholds(durations: pd.Series, low_q=0.25, high_q=0.75, round_to=5):
    """Calcola le soglie per VisitaRapida (<= low_q percentile) ed
    EsperienzaImmersiva (>= high_q percentile), arrotondate per
    leggibilità. Ritorna (soglia_rapida, soglia_immersiva)."""
    low = durations.quantile(low_q)
    high = durations.quantile(high_q)
    low = int(round(low / round_to) * round_to)
    high = int(round(high / round_to) * round_to)
    if low >= high:  # guardia di sicurezza su dataset molto piccoli/uniformi
        low, high = low_q_fallback(durations)
    return low, high


def low_q_fallback(durations):
    return int(durations.min()), int(durations.max())


SOGLIA_VISITA_RAPIDA, SOGLIA_ESPERIENZA_IMMERSIVA = compute_duration_thresholds(
    df["visit_duration_min"]
)
print(
    f"[INFO] Soglie data-driven calcolate sul dataset corrente: "
    f"VisitaRapida <= {SOGLIA_VISITA_RAPIDA} min (p25), "
    f"EsperienzaImmersiva >= {SOGLIA_ESPERIENZA_IMMERSIVA} min (p75)"
)

# -----------------------------
# Costruzione ontologia (T-Box)
# -----------------------------
onto = get_ontology("http://example.org/trip_kb.owl")

with onto:

    class PointOfInterest(Thing):
        pass

    class Neighborhood(Thing):
        pass

    # --- Data properties ---
    class hasDurationMin(DataProperty):
        domain = [PointOfInterest]
        range = [int]

    class isIndoor(DataProperty):
        domain = [PointOfInterest]
        range = [int]  # 0/1

    class isFree(DataProperty):
        domain = [PointOfInterest]
        range = [int]  # 0/1

    class isIconic(DataProperty):
        domain = [PointOfInterest]
        range = [int]  # 0/1

    # --- Object property: collega il POI al suo quartiere ---
    class locatedIn(ObjectProperty):
        domain = [PointOfInterest]
        range = [Neighborhood]

    # -----------------------------
    # Classi definite (regole OWL) - "cuore" della KB
    # -----------------------------

    class VisitaRapida(PointOfInterest):
        # Tappa breve, inseribile facilmente in un itinerario fitto:
        # soglia = 25° percentile della durata nel dataset corrente
        # (calcolata sopra in SOGLIA_VISITA_RAPIDA)
        equivalent_to = [
            PointOfInterest & hasDurationMin.some(
                ConstrainedDatatype(int, max_inclusive=SOGLIA_VISITA_RAPIDA)
            )
        ]

    class EsperienzaImmersiva(PointOfInterest):
        # Visita lunga e "da vivere con calma":
        # soglia = 75° percentile della durata nel dataset corrente
        # (calcolata sopra in SOGLIA_ESPERIENZA_IMMERSIVA)
        equivalent_to = [
            PointOfInterest & hasDurationMin.some(
                ConstrainedDatatype(int, min_inclusive=SOGLIA_ESPERIENZA_IMMERSIVA)
            )
        ]

    class IconaGratuita(PointOfInterest):
        # Luogo iconico e ad accesso gratuito: combinazione non banale,
        # utile per itinerari "low-budget" senza rinunciare alle attrazioni clou
        equivalent_to = [
            PointOfInterest & isIconic.value(1) & isFree.value(1)
        ]

    class AdattoMaltempo(PointOfInterest):
        # Indoor: buona alternativa/riserva in caso di maltempo
        equivalent_to = [
            PointOfInterest & isIndoor.value(1)
        ]

    class AltaPriorita(PointOfInterest):
        # Classe composta: iconico E (visita rapida O esperienza immersiva)
        # -> rappresenta i POI da inserire quasi certamente in ogni itinerario,
        #    a prescindere dal tempo a disposizione del turista
        equivalent_to = [
            PointOfInterest & isIconic.value(1) & (VisitaRapida | EsperienzaImmersiva)
        ]

# -----------------------------
# Popolamento A-Box (individui)
# -----------------------------
neighborhoods = {}
for n in df["neighborhood"].unique():
    neighborhoods[n] = onto.Neighborhood(f"nbh_{n}")

pois = []
for _, row in df.iterrows():
    p = onto.PointOfInterest(f"poi_{int(row['id'])}")
    p.hasDurationMin = [int(row["visit_duration_min"])]
    p.isIndoor = [int(row["indoor"])]
    p.isFree = [int(row["free_entry"])]
    p.isIconic = [int(row["iconic"])]
    p.locatedIn = [neighborhoods[row["neighborhood"]]]
    pois.append(p)

# -----------------------------
# Ragionamento automatico (DL reasoner)
# -----------------------------
def run_reasoner():
    start = time.time()
    try:
        sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True)
        used = "pellet"
    except Exception as e:
        print(f"[WARN] Pellet fallito ({type(e).__name__}: {e}). Provo HermiT (sync_reasoner)...")
        sync_reasoner()
        used = "hermit"
    elapsed = time.time() - start
    return used, elapsed


reasoner_used, reasoning_time = run_reasoner()
print(f"[INFO] Reasoner usato: {reasoner_used} | tempo: {reasoning_time:.2f}s")

# -----------------------------
# "DaAbbinareVicino": non e' una classe DL ma una feature spaziale
# derivata (densita' di POI nel raggio di 300 m) -- la calcoliamo qui
# in modo esplicito, separata dal ragionamento OWL, per mostrare la
# differenza fra conoscenza codificabile in DL (soglie su attributi,
# combinazioni booleane) e conoscenza che richiede calcolo numerico
# (qui solo come arricchimento aggiuntivo, documentarne la scelta).
# -----------------------------
from math import radians, sin, cos, sqrt, atan2

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

coords = df[["id", "lat", "lon"]].set_index("id")
near_count = {}
for i, r1 in coords.iterrows():
    c = 0
    for j, r2 in coords.iterrows():
        if i == j:
            continue
        if haversine_m(r1.lat, r1.lon, r2.lat, r2.lon) <= 300:
            c += 1
    near_count[i] = c

# -----------------------------
# Estrazione feature semantiche
# -----------------------------
def inferred(instance, cls) -> int:
    return 1 if cls in instance.INDIRECT_is_a else 0

rows = []
for poi_id, p in zip(df["id"], pois):
    rows.append({
        "is_VisitaRapida": inferred(p, onto.VisitaRapida),
        "is_EsperienzaImmersiva": inferred(p, onto.EsperienzaImmersiva),
        "is_IconaGratuita": inferred(p, onto.IconaGratuita),
        "is_AltaPriorita": inferred(p, onto.AltaPriorita),
        "is_AdattoMaltempo": inferred(p, onto.AdattoMaltempo),
        "is_DaAbbinareVicino": 1 if near_count[poi_id] >= 2 else 0,
    })

df_sem = pd.DataFrame(rows)

print("[INFO] Conteggi feature inferite (devono essere > 0 per almeno alcune):")
print(df_sem.sum().sort_values(ascending=False))

# -----------------------------
# Salvataggio output
# -----------------------------
df_enriched = pd.concat([df.reset_index(drop=True), df_sem], axis=1)
df_enriched.to_csv(OUT_ENRICHED_CSV, index=False)
onto.save(file=OUT_OWL, format="rdfxml")

with open("ontology/thresholds_used.txt", "w") as f:
    f.write(
        f"Soglie data-driven calcolate sul dataset {INPUT_CSV} (eseguito il {time.strftime('%Y-%m-%d %H:%M')}):\n"
        f"  VisitaRapida: durata <= {SOGLIA_VISITA_RAPIDA} min (25 percentile)\n"
        f"  EsperienzaImmersiva: durata >= {SOGLIA_ESPERIENZA_IMMERSIVA} min (75 percentile)\n"
        f"  Reasoner usato: {reasoner_used} | tempo di ragionamento: {reasoning_time:.2f}s\n"
        f"  n. POI nel dataset: {len(df)}\n"
    )

print(f"[OK] Salvato dataset arricchito: {OUT_ENRICHED_CSV} ({len(df_enriched)} righe)")
print(f"[OK] Salvata ontologia: {OUT_OWL}")
print(f"[OK] Soglie tracciate in: ontology/thresholds_used.txt")
