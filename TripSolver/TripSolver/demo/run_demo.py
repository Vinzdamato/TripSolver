# run_demo.py
# ------------------------------------------------------------
# Orchestratore end-to-end: KB (ontologia+reasoner) -> CSP (assegnazione
# POI ai giorni) -> Ricerca A* (ordine di visita ottimo per ogni giorno)
# -> stampa di un itinerario leggibile.
#
# Prerequisito: aver già eseguito `python ontology/build_kb.py` almeno
# una volta, in modo che data/poi_enriched.csv esista.
#
# Esecuzione: python demo/run_demo.py
# ------------------------------------------------------------

import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from csp.day_scheduler import schedule_days
from search.astar_router import astar_route

ENRICHED_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "poi_enriched.csv")

N_DAYS = 3
MAX_MINUTES_PER_DAY = 300          # vedi rationale in csp/day_scheduler.py
MAX_ALTA_PRIORITA_PER_DAY = 3
# Selezione dei POI da includere nell'itinerario: MustSee + Secondary.
# Con il budget di 300 min/giorno su 3 giorni il CSP è feasible per
# l'intero dataset di esempio. Un'estensione naturale del progetto è una
# selezione "knapsack-like" che massimizzi priorità/interesse sotto vincolo
# di budget totale di tempo disponibile (vedi docs/PROJECT_PLAN.md).
TIER_INCLUDE = {"MustSee", "Secondary"}


def main():
    if not os.path.exists(ENRICHED_CSV):
        print("[ERRORE] data/poi_enriched.csv non trovato.")
        print("Esegui prima: python ontology/build_kb.py")
        sys.exit(1)

    df = pd.read_csv(ENRICHED_CSV, dtype={"opening_hour": float, "closing_hour": float})
    df = df[df["tourist_tier"].isin(TIER_INCLUDE)].copy()
    print(f"[INFO] POI selezionati per l'itinerario: {len(df)}")

    pois_for_csp = df[[
        "id", "visit_duration_min", "is_AltaPriorita", "opening_hour", "closing_hour"
    ]].to_dict("records")
    plan = schedule_days(
        pois_for_csp,
        n_days=N_DAYS,
        max_minutes_per_day=MAX_MINUTES_PER_DAY,
        max_alta_priorita_per_day=MAX_ALTA_PRIORITA_PER_DAY,
    )

    if plan is None:
        print("[ERRORE] Il CSP è risultato infeasible con i vincoli correnti.")
        print("Prova ad aumentare N_DAYS o MAX_MINUTES_PER_DAY.")
        sys.exit(1)

    coords_lookup = df.set_index("id")[["lat", "lon"]].apply(tuple, axis=1).to_dict()
    name_lookup = df.set_index("id")["name"].to_dict()
    duration_lookup = df.set_index("id")["visit_duration_min"].to_dict()

    print("\n" + "=" * 60)
    print(" ITINERARIO PROPOSTO ".center(60, "="))
    print("=" * 60)

    for d in range(N_DAYS):
        poi_ids = plan[d]
        if not poi_ids:
            continue
        day_coords = {pid: coords_lookup[pid] for pid in poi_ids}
        start = poi_ids[0]
        order, total_dist_m = astar_route(day_coords, start_id=start)
        total_visit_min = sum(duration_lookup[pid] for pid in order)

        print(f"\n--- Giorno {d + 1} ---")
        for i, pid in enumerate(order, 1):
            print(f"  {i}. {name_lookup[pid]}  ({duration_lookup[pid]} min)")
        print(f"  Distanza a piedi stimata fra le tappe: {total_dist_m/1000:.2f} km")
        print(f"  Tempo totale di visita: {total_visit_min} min (~{total_visit_min/60:.1f} h)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
