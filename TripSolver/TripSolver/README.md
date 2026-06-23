# TripSolver: Pianificatore Ibrido di Itinerari Turistici

**Autore:** [Nome Cognome] - [Matricola] **Corso:** Ingegneria della Conoscenza (ICon) - A.A. 2025/2026

## Descrizione del Progetto
TripSolver è un sistema ibrido che integra **Ontologie (Knowledge Base in OWL)**, **Ricerca in Spazi di Stati (A\*)**, **Ragionamento con Vincoli (CSP)** e modelli di **Machine Learning (Apprendimento Supervisionato)**. L'obiettivo è pianificare itinerari turistici multi-giorno a partire da un catalogo di punti di interesse (POI), dimostrando come il ragionamento simbolico (es. l'inferenza di POI ad *Alta Priorità* o *Adatti al Maltempo*) possa guidare sia la selezione/schedulazione delle tappe sia il miglioramento delle feature usate dai modelli predittivi, in particolare in scenari con pochi dati a disposizione sul singolo POI (low-data).

## Struttura della Repository
- `data/`: dataset dei POI (originale e arricchito dalla KB), `SOURCES.md` (fonti e metodologia di raccolta dati), `fetch_osm_pois.py` (estrazione live da OpenStreetMap, da eseguire in locale).
- `docs/`: documentazione dettagliata del progetto (piano di progetto, mappatura sui criteri di valutazione).
- `ontology/`: `build_kb.py` — creazione dell'ontologia, soglie **data-driven** (percentili della distribuzione reale, non costanti arbitrarie) e inferenza tramite reasoner (Pellet/HermiT); `thresholds_used.txt` generato ad ogni esecuzione per tracciabilità.
- `search/`: `astar_router.py` — ricerca A* nello spazio degli stati per l'ordinamento ottimo del percorso di visita giornaliero.
- `csp/`: `day_scheduler.py` — CSP/CP-SAT per l'assegnazione dei POI ai giorni, con vincolo di **fattibilità oraria** (esclude POI incompatibili con la finestra turistica) e budget di tempo giornaliero motivato.
- `ml/`: `model_comparison.py` (confronto baseline vs arricchito, media±dev.std su più run) e `low_data_scenario.py` (scenario "low-data": il vantaggio della KB in funzione della quantità di dati di training disponibili, su due modelli con capacità diverse).
- `demo/`: `run_demo.py` — demo end-to-end da terminale che genera un itinerario completo.

## Installazione ed Esecuzione
1. Clonare il repository.
2. Installare le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
3. **Verificare che tutto funzioni sul proprio computer** (consigliato prima di studiare la documentazione, ed essenziale prima della consegna):
   ```bash
   python verify_setup.py
   ```
   Esegue l'intera pipeline in sequenza e genera `verification_report.txt`. In particolare segnala esplicitamente **quale reasoner OWL viene usato sulla tua macchina** (Pellet o HermiT): la documentazione descrive un fallback Pellet→HermiT osservato nell'ambiente in cui è stato scritto il progetto, che sul tuo PC potrebbe non verificarsi. Lo script te lo dice chiaramente, così sai se il §2.3.2 va aggiornato prima di doverlo spiegare a voce.
4. Eseguire la pipeline, in ordine (oppure direttamente tramite `verify_setup.py` sopra):
   ```bash
   python ontology/build_kb.py        # costruisce la KB, esegue il reasoner, genera poi_enriched.csv
   python ml/model_comparison.py      # confronto baseline vs arricchito (split standard)
   python ml/low_data_scenario.py     # confronto baseline vs arricchito al variare dei dati disponibili
   python demo/run_demo.py            # genera un itinerario di esempio su 3 giorni
   ```

**Nota:** il reasoner OWL richiede una JVM (Java) installata sul sistema.

## Stato delle personalizzazioni richieste prima della consegna
Le quattro aree segnalate come da personalizzare sono state affrontate così:

1. **Dataset** — *ampliato ulteriormente: 20/28 POI (71%) ora con dato sugli orari tracciato e motivato* (in `data/poi_bari_sample.csv`, colonne `data_source`/`source_url`, dettagli completi in `data/SOURCES.md`). La ricerca ha corretto **quattro stime iniziali effettivamente sbagliate** (Orto Botanico chiuso nel weekend; Acquario di Bari su prenotazione, non orario fisso; Palazzo Mincuzzi chiuso al pubblico dal dic. 2024, non più negozio visitabile; Stadio San Nicola senza orari di visita turistica regolari), corretto la modellazione di vie/piazze pubbliche erroneamente trattate come istituzioni con orario (Strada delle Orecchiette, Via Sparano), e riconosciuto un caso di apertura dichiaratamente irregolare (Chiesa di San Gregorio) invece di inventare un orario fittizio. Restano 8 POI su stima dichiarata. È incluso `data/fetch_osm_pois.py` per un'estrazione OSM completa (da eseguire sul tuo computer).
2. **Soglie dell'ontologia** — *risolto.* `VisitaRapida` ed `EsperienzaImmersiva` non usano più soglie fisse (20/60 min): sono calcolate automaticamente come 25°/75° percentile della distribuzione di `visit_duration_min` nel dataset corrente (`compute_duration_thresholds()` in `build_kb.py`), così restano motivate e si auto-adattano se il dataset cambia.
3. **Vincoli del CSP** — *risolto.* Il budget di 300 min/giorno è motivato esplicitamente (convenzione di pianificazione turistica, escluso tempo di spostamento gestito separatamente da A*). È stato inoltre implementato il vincolo di fattibilità oraria, prima solo dichiarato nei commenti: `filter_feasible_pois()` esclude (con avviso esplicito) i POI la cui finestra di apertura non si sovrappone alla finestra turistica tipo (9:00–19:00).
4. **Valutazione ML "low-data"** — *risolto.* `ml/low_data_scenario.py` confronta baseline vs arricchito al variare della dimensione del training set (6→22 esempi, 30 ripetizioni per punto, media±dev.std), su due modelli (RandomForest e LogisticRegression). Il risultato empirico sul dataset di esempio è discusso direttamente nei commenti dello script: il vantaggio della KB dipende dal modello (più visibile su un modello lineare, che non può ricostruire da sé le soglie non lineari che invece un albero apprende nativamente dai dati grezzi) — un'osservazione metodologica difendibile da riportare in relazione, più onesta di un generico "la KB migliora sempre i risultati".

Per i dettagli completi su ciascuna scelta di progetto da documentare in relazione, vedi `docs/PROJECT_PLAN.md`.
