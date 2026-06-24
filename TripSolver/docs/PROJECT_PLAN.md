# TripSolver — Piano di Progetto

*Pianificatore ibrido di itinerari turistici — Ingegneria della Conoscenza (Icon)*

Questo documento è pensato come scaletta di lavoro e, in buona parte,
come base diretta per la relazione finale da consegnare. Segue la
struttura richiesta dalle linee guida del corso (focus sulle scelte
tecniche e sulla valutazione del sistema, non su definizioni standard).

---

## 1. Obiettivo del progetto

Costruire un sistema di supporto alla pianificazione di itinerari
turistici multi-giorno che combini **rappresentazione della conoscenza**,
**ricerca/ragionamento** e **apprendimento**, dimostrando in modo
esplicito come le tre componenti si integrino in un'unica pipeline e
quale valore aggiunto porti ciascuna.

## 2. Argomenti del programma affrontati

| Capitolo programma | Componente del progetto |
|---|---|
| 2 — Ricerca di soluzioni in spazi di stati | `search/astar_router.py`: formulazione del routing giornaliero come ricerca A* nello spazio (POI corrente, insieme visitati) |
| 3 — Ragionamento con vincoli | `csp/day_scheduler.py`: CSP/CP per l'assegnazione dei POI ai giorni (CP-SAT) |
| 5/6 — Rappresentazione relazionale, Knowledge Graph e Ontologie | `ontology/build_kb.py`: T-Box/A-Box OWL, classi definite (`equivalent_to`), reasoner DL |
| 7 — Apprendimento Supervisionato | `ml/model_comparison.py`: confronto modelli, baseline vs feature semantiche |
| 9 — Ragionamento su modelli di conoscenza incerta *(estensione opzionale, vedi §6)* | rete bayesiana per gestire incertezza su meteo/affollamento |

Non è necessario coprire tutti e dieci i capitoli: le linee guida
chiedono di toccare **diversi** argomenti in modo approfondito, non tutti
superficialmente. Questa tabella copre già 4-5 capitoli con un livello di
dettaglio reale (non semplici definizioni).

## 3. Architettura del sistema

```
                 ┌───────────────────────┐
   poi.csv  ───▶ │  Ontologia OWL +       │ ──▶ poi_enriched.csv
   (A-Box)       │  reasoner DL           │      (+ feature semantiche)
                 │  (rappresentazione/    │
                 │   ragionamento)        │
                 └───────────┬───────────┘
                              │
              ┌───────────────┴────────────────┐
              ▼                                  ▼
   ┌─────────────────────┐          ┌─────────────────────────┐
   │ CSP (CP-SAT)         │          │ Apprendimento supervis.  │
   │ assegna i POI ai     │          │ baseline vs arricchito   │
   │ giorni rispettando   │          │ (valutazione su più run) │
   │ vincoli di tempo/    │          └─────────────────────────┘
   │ priorità             │
   └──────────┬───────────┘
              ▼
   ┌─────────────────────┐
   │ A* (per ogni giorno) │
   │ ordina la visita     │
   │ minimizzando la      │
   │ distanza percorsa    │
   └──────────┬───────────┘
              ▼
        Itinerario finale
```

## 4. Dettaglio dei moduli e decisioni di progetto da motivare in relazione

### 4.1 Rappresentazione (ontologia)
- Perché modellare le proprietà come classi definite (`equivalent_to`)
  invece di colonne calcolate "a mano" in pandas: il vantaggio è che il
  reasoner verifica automaticamente la **consistenza logica** delle
  definizioni e permette di derivare classi **composte** (es.
  `AltaPriorita = Iconico ∧ (VisitaRapida ∨ EsperienzaImmersiva)`) senza
  scrivere codice procedurale ad-hoc per ogni combinazione.
- **Soglie data-driven (già implementato):** le soglie di
  `VisitaRapida`/`EsperienzaImmersiva` sono calcolate automaticamente
  come 25°/75° percentile della distribuzione di `visit_duration_min`
  nel dataset corrente (`compute_duration_thresholds()`), non più
  costanti arbitrarie. Riportare in relazione il valore numerico
  effettivamente usato (salvato in `ontology/thresholds_used.txt` ad
  ogni esecuzione) e discutere perché un criterio percentile è più
  difendibile di una soglia fissata "a sensazione".
- Evitare l'errore segnalato nelle linee guida di usare l'ontologia come
  "DB con regole banali": le classi `AltaPriorita` e `DaAbbinareVicino`
  qui non sono singoli attributi del dataset originale, ma derivano da
  combinazione di più proprietà e (per `DaAbbinareVicino`) da un calcolo
  geometrico — vale la pena, in relazione, discutere esplicitamente
  *quali* classi sono "vera" inferenza simbolica e quali sono feature
  engineering tradizionale, per mostrare consapevolezza della differenza.

### 4.2 Ricerca (A*)
- Motivare la scelta dell'euristica (MST sui nodi non visitati + arco
  minimo dal nodo corrente): è ammissibile, quindi A* è ottimo; va
  discusso il costo computazionale (ricalcolo dell'MST ad ogni nodo
  espanso) e l'eventuale ottimizzazione (es. memoizzazione).
- Discutere il limite di scalabilità (spazio degli stati O(n·2ⁿ)) e
  giustificare il numero massimo di POI per giorno scelto nel progetto.
- Confrontare (anche solo qualitativamente, con un piccolo esperimento)
  A* con una baseline più semplice (nearest-neighbor greedy) su alcune
  istanze, per mostrare l'effettivo guadagno in qualità della soluzione
  e il costo in tempo di calcolo — ottimo materiale per la sezione di
  valutazione.

### 4.3 Ragionamento con vincoli (CSP)
- Motivare la scelta di CP-SAT rispetto a un solver CSP "puro" (es.
  `python-constraint`): qui si sfrutta la possibilità di esprimere anche
  una funzione obiettivo (bilanciamento del carico fra giorni) insieme ai
  vincoli, evitando un secondo passaggio di ottimizzazione.
- **Già implementato:** il vincolo di fattibilità oraria (`filter_feasible_pois()`)
  esclude esplicitamente, con avviso, i POI la cui finestra di apertura
  non si sovrappone alla finestra turistica tipo (9:00–19:00, parametro
  `TOURIST_DAY_WINDOW`). Sul dataset di esempio attuale nessun POI viene
  escluso (nessuno ha orari del tutto incompatibili): è un buon punto da
  verificare/discutere quando si userà un dataset reale più eterogeneo
  (es. locali notturni, mercati mattutini).
- Il budget di 300 min/giorno è una scelta motivata (giornata turistica
  "piena", tempo di spostamento gestito separatamente da A*) ma resta
  comunque un'ipotesi di progetto: discuterla esplicitamente rispetto al
  proprio scenario (itinerario "rilassato" vs "intensivo") rafforza la
  relazione.
- Documentare la differenza fra i vincoli "hard" (budget di tempo,
  copertura) e quelli che sono trattati come hard ma che
  concettualmente sono "soft" (es. max POI prioritari/giorno): discutere
  come si potrebbero rilassare con penalità nella funzione obiettivo.
- Riportare, per istanze di dimensione crescente (numero di POI/giorni),
  il tempo di risoluzione del solver — utile per mostrare di aver
  valutato la scalabilità, non solo la correttezza.

### 4.4 Apprendimento supervisionato
- Il modulo `ml/model_comparison.py` è già impostato secondo la
  metodologia corretta richiesta dalle linee guida (Repeated Stratified
  K-Fold, **media ± deviazione standard**, niente singola confusion
  matrix). Da estendere/adattare quando si sostituisce il dataset
  giocattolo con dati reali e più numerosi.
- **Già implementato:** `ml/low_data_scenario.py` confronta baseline vs
  arricchito al variare della dimensione del training set (6→22 esempi,
  30 ripetizioni per punto), su due modelli (RandomForest,
  LogisticRegression). Risultato osservato sul dataset di esempio: il
  vantaggio della KB è piccolo e non sempre positivo con RandomForest
  (un albero può apprendere da solo le soglie su `visit_duration_min`),
  mentre è più sistematicamente positivo nei regimi a pochi dati con
  LogisticRegression (un modello lineare non può rappresentare
  nativamente quelle soglie). Questo è un risultato onesto e
  difendibile da riportare in relazione — più convincente di un
  generico "la KB migliora sempre le metriche", che peraltro le linee
  guida invitano a non dare per scontato.
- Riportare anche un confronto di costo computazionale/training time fra
  i modelli, se rilevante per la propria narrazione.

## 5. Cosa evitare (richiami diretti alle linee guida)
- Non limitarsi a "scaricare un dataset standard e allenare un modello":
  qui il dataset POI va costruito/curato (vedi README), e la parte di
  ragionamento simbolico+CSP+ricerca deve avere un peso reale nella
  relazione, non essere un contorno.
- Non inserire screenshot di codice o output nella documentazione: usare
  tabelle testuali (come quelle generate da `model_comparison.py`).
- Non riportare un'unica matrice di confusione/classification report da
  un solo run: usare le tabelle media±dev.std già prodotte dallo script.
- Non includere definizioni "da manuale" di A*, CSP, OWL ecc.: la
  relazione deve concentrarsi sulle **scelte specifiche** fatte in questo
  progetto (soglie, euristiche, vincoli, iperparametri) e sulla loro
  valutazione.

## 6. Estensione opzionale: ragionamento sotto incertezza (cap. 9)

Per coprire anche il tema dell'incertezza, si può aggiungere una rete
bayesiana (es. con `pgmpy`) che modella la probabilità che una giornata
di visite sia "a rischio" (es. variabili: previsione meteo, giorno della
settimana, affollamento atteso) e che influenzi la scelta di quali POI
indoor tenere come riserva (sfruttando la classe ontologica
`AdattoMaltempo` già presente nel progetto come evidenza osservabile
collegata al nodo "meteo" della rete). Questa estensione non è inclusa
nel codice fornito ma si innesta naturalmente sulla pipeline esistente.

## 7. Scaletta suggerita per la relazione finale
1. Introduzione e obiettivo (breve, no contesto generico su AI)
2. Argomenti del programma affrontati (tabella §2)
3. Architettura della pipeline (diagramma §3)
4. Rappresentazione: descrizione KB, classi definite, esempio di
   inferenza, discussione su complessità/espressività (è un criterio di
   valutazione esplicito: "soffermandosi sulla KB del proprio KBS:
   rappresentazione, uso, valutazione della complessità")
5. Ricerca: formulazione del problema, euristica, valutazione
6. CSP: formulazione, vincoli, valutazione
7. Apprendimento: setup sperimentale, risultati (tabelle media±std),
   discussione critica (quando/perché la KB aiuta o non aiuta)
8. Conclusioni e limiti del sistema
9. (Eventuale) Estensione con ragionamento sotto incertezza
