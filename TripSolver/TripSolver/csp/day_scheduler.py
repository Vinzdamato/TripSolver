# day_scheduler.py
# ------------------------------------------------------------
# OBIETTIVO
#   Assegnare ogni POI selezionato a un GIORNO di un itinerario
#   multi-giorno, rispettando vincoli realistici, tramite un solver
#   CSP/CP (constraint programming) -- cfr. cap. 3 del programma
#   (Ragionamento con Vincoli).
#
# FORMULAZIONE CSP
#   Variabili:    day[p] in {0, ..., n_days-1}   per ogni POI p selezionato
#   Dominio:      i giorni dell'itinerario
#   Vincoli:
#     (1) Budget di tempo per giornata: somma delle durate di visita
#         <= max_minuti_per_giorno
#     (2) Fattibilità oraria: un POI la cui finestra di apertura non si
#         sovrappone affatto con la finestra-tipo di visita turistica
#         (TOURIST_DAY_WINDOW) viene escluso A MONTE dal CSP da
#         `filter_feasible_pois()`, con un avviso esplicito — non ha senso
#         lasciare che il solver lo assegni a un giorno se non potrà mai
#         essere visitato nell'orario in cui si gira la città.
#     (3) Distribuzione dei POI "AltaPriorita" (cfr. ontologia): non più
#         di K must-see per giorno, per evitare giornate sovraccariche
#         anche se il tempo lo permetterebbe (vincolo "soft" tradotto qui
#         in vincolo hard per semplicità -- documentare l'eventuale
#         rilassamento a vincolo soft con penalità nella relazione finale)
#     (4) Copertura: ogni POI selezionato deve essere assegnato a esattamente
#         un giorno
#   Funzione obiettivo (opzionale, rende il problema un CSP ottimizzato/CP):
#     bilanciare il carico fra giorni (minimizzare max-min del tempo
#     impiegato per giorno), per itinerari più confortevoli.
#
# DECISIONE DI PROGETTO: budget di tempo giornaliero
#   MAX_MINUTES_PER_DAY di default è 300 (5h): è un'ipotesi di
#   progetto basata su una convenzione comune nella pianificazione di
#   itinerari turistici (giornata "piena" con margine per pasti e
#   spostamenti, che NON sono inclusi in questo budget — il tempo di
#   spostamento fra tappe è gestito a parte dal modulo di ricerca A*,
#   vedi search/astar_router.py). Va ridiscussa esplicitamente in
#   relazione, motivandola rispetto al proprio scenario (es. itinerario
#   "rilassato" vs "intensivo").
#
# SOLVER
#   OR-Tools CP-SAT (https://developers.google.com/optimization/cp).
#   In alternativa è possibile usare la libreria `python-constraint`
#   per una formulazione CSP "pura" senza funzione obiettivo: la scelta
#   di CP-SAT va motivata in relazione (qui: gestisce nativamente sia i
#   vincoli sia l'ottimizzazione, evitando un secondo passaggio).
# ------------------------------------------------------------

from ortools.sat.python import cp_model

# Finestra-tipo in cui si gira la città durante un viaggio turistico
# (ipotesi di progetto: mattina-sera, ragionevole per la maggior parte
# delle città; va adattata se l'itinerario include es. vita notturna).
TOURIST_DAY_WINDOW = (9.0, 19.0)


def _is_missing(x) -> bool:
    """True per None e per NaN (es. pandas/float('nan')), senza importare pandas qui."""
    return x is None or (isinstance(x, float) and x != x)


def filter_feasible_pois(pois: list[dict], day_window: tuple = TOURIST_DAY_WINDOW):
    """Esclude i POI la cui finestra di apertura (opening_hour,
    closing_hour) non si sovrappone affatto con `day_window`: non ha
    senso farli considerare al CSP, tanto non potranno mai essere
    visitati nell'orario in cui si gira la città.

    I POI senza informazioni note sugli orari (es. "apertura su
    richiesta", cfr. Acquario di Bari in data/SOURCES.md) vengono
    inclusi per cautela, ma vanno gestiti a parte nella pianificazione
    reale (es. prenotazione preventiva).

    Ritorna: (pois_fattibili, pois_esclusi)
    """
    w_start, w_end = day_window
    feasible, excluded = [], []
    for p in pois:
        o, c = p.get("opening_hour"), p.get("closing_hour")
        if _is_missing(o) or _is_missing(c):
            feasible.append(p)  # nessuna info -> non escludiamo per cautela
            continue
        overlap = min(c, w_end) - max(o, w_start)
        if overlap > 0:
            feasible.append(p)
        else:
            excluded.append(p)
    return feasible, excluded


def schedule_days(pois: list[dict], n_days: int, max_minutes_per_day: int = 300,
                   max_alta_priorita_per_day: int = 3,
                   day_window: tuple = TOURIST_DAY_WINDOW):
    """
    pois: lista di dict, ciascuno con almeno le chiavi:
          'id', 'visit_duration_min', 'is_AltaPriorita' (0/1)
          (opzionali: 'opening_hour', 'closing_hour' per il vincolo (2))
    Ritorna: dict {day_index: [poi_id, ...]} oppure None se infeasible.
    I POI esclusi per incompatibilità oraria vengono segnalati a schermo
    e NON compaiono nel piano restituito.
    """
    pois, excluded = filter_feasible_pois(pois, day_window)
    if excluded:
        nomi = [p.get("id") for p in excluded]
        print(f"[WARN] {len(excluded)} POI esclusi per incompatibilità oraria "
              f"con la finestra turistica {day_window}: id={nomi}")

    model = cp_model.CpModel()
    n = len(pois)
    ids = [p["id"] for p in pois]

    # Variabile di decisione: day_var[i] = giorno assegnato al POI i
    day_var = {pid: model.NewIntVar(0, n_days - 1, f"day_{pid}") for pid in ids}

    # Variabili indicatrici assigned[i][d] per poter sommare le durate per giorno
    assigned = {}
    for p in pois:
        pid = p["id"]
        for d in range(n_days):
            assigned[(pid, d)] = model.NewBoolVar(f"assign_{pid}_{d}")
        model.AddExactlyOne(assigned[(pid, d)] for d in range(n_days))
        # Collega assigned[i][d] alla variabile day_var[i]
        for d in range(n_days):
            model.Add(day_var[pid] == d).OnlyEnforceIf(assigned[(pid, d)])
            model.Add(day_var[pid] != d).OnlyEnforceIf(assigned[(pid, d)].Not())

    # Vincolo (1): budget di tempo per giornata
    for d in range(n_days):
        model.Add(
            sum(assigned[(p["id"], d)] * int(p["visit_duration_min"]) for p in pois)
            <= max_minutes_per_day
        )

    # Vincolo (3): max N "AltaPriorita" per giorno (evita giornate-maratona)
    for d in range(n_days):
        model.Add(
            sum(assigned[(p["id"], d)] * int(p["is_AltaPriorita"]) for p in pois)
            <= max_alta_priorita_per_day
        )

    # Obiettivo: bilanciare il carico fra giorni (minimizzare la differenza
    # fra il giorno più carico e quello più scarico) per itinerari più
    # confortevoli -- in alternativa si potrebbe massimizzare la copertura
    # se non tutti i POI devono necessariamente essere inclusi.
    day_load = []
    for d in range(n_days):
        load = model.NewIntVar(0, max_minutes_per_day, f"load_{d}")
        model.Add(
            load == sum(assigned[(p["id"], d)] * int(p["visit_duration_min"]) for p in pois)
        )
        day_load.append(load)
    max_load = model.NewIntVar(0, max_minutes_per_day, "max_load")
    min_load = model.NewIntVar(0, max_minutes_per_day, "min_load")
    model.AddMaxEquality(max_load, day_load)
    model.AddMinEquality(min_load, day_load)
    model.Minimize(max_load - min_load)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    result = {d: [] for d in range(n_days)}
    for p in pois:
        d = solver.Value(day_var[p["id"]])
        result[d].append(p["id"])
    return result


if __name__ == "__main__":
    # Mini esempio autonomo per verificare il modulo in isolamento.
    demo_pois = [
        {"id": 1, "visit_duration_min": 45, "is_AltaPriorita": 1},
        {"id": 2, "visit_duration_min": 60, "is_AltaPriorita": 1},
        {"id": 3, "visit_duration_min": 30, "is_AltaPriorita": 0},
        {"id": 4, "visit_duration_min": 60, "is_AltaPriorita": 1},
        {"id": 5, "visit_duration_min": 40, "is_AltaPriorita": 0},
        {"id": 6, "visit_duration_min": 90, "is_AltaPriorita": 0},
    ]
    plan = schedule_days(demo_pois, n_days=2, max_minutes_per_day=180)
    print("Piano per giorno:", plan)
