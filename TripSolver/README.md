# TripSolver: Pianificatore Ibrido di Itinerari Turistici

**Autore:** Vincenzo D'Amato - 804738 **Corso:** Ingegneria della Conoscenza (Icon) - A.A. 2025/2026

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
3. **Verificare che tutto funzioni sul proprio computer**:
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

