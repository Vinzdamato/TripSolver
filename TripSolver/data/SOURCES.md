# Fonti dei dati e metodologia di raccolta

## Stato attuale del dataset (`poi_bari_sample.csv`)
Il dataset contiene 28 POI di Bari. Per **20 di essi (71%)** il dato sugli
**orari di apertura** è ora tracciato e motivato — verificato tramite
ricerca web, corretto rispetto a una stima iniziale errata, oppure
classificato come "non applicabile" perché si tratta di uno spazio
pubblico (via, piazza, lungomare, spiaggia) sempre accessibile, non di
un'istituzione con orario. Per gli **8 restanti** orari/durate sono
ancora **stime dichiarate** basate sulla categoria del luogo. Questa
distinzione è tracciata esplicitamente nelle colonne `data_source` e
`source_url` del CSV.

| POI | Orari | Fonte |
|---|---|---|
| Basilica di San Nicola | Lun–Sab 6:30–20:30 (riferimento; domenica chiude alle 22:00, non modellato) | basilicasannicola.it/sez/9/232/orari |
| Castello Svevo | 8:30–19:30 (chiuso il mercoledì, non modellato nel CSP attuale) | ariannazappia.it/cosa-visitare-a-bari |
| Cattedrale di San Sabino | 8:00–20:00 (chiusura a pranzo 13:00–16:00 non modellata) | excelsiorbari.it/la-cattedrale-di-bari |
| Pinacoteca Metropolitana | Mar–Sab 9:00–19:00 (domenica orario ridotto 9:00–13:00, non modellato) | pinacotecabari.it/index.php/info/orari-di-visita |
| Museo Archeologico Santa Scolastica | Mar–Sab 9:00–19:00, Dom/festivi 9:00–13:00, chiuso lunedì (semplificato a 9–19) | facebook.com/Museodisantascolastica |
| Teatro Margherita | Tutti i giorni 10:00–22:00 (ingresso libero all'edificio fuori orario mostre; con mostra in corso, biglietto 5–10€) | cestee.it/destinazione/italia/bari/teatro-margherita |
| Orto Botanico Università di Bari | **Lun–Ven 8:30–13:30, chiuso sabato/domenica/festivi** (correzione: la stima iniziale lo dava aperto tutti i giorni) | uniba.it/it/ricerca/altre-strutture/museo-orto-botanico |
| Acquario di Bari | **"Apertura su richiesta"**, NON un orario fisso giornaliero (correzione: la stima iniziale ipotizzava erroneamente 10–18 tutti i giorni) | isprambiente.gov.it (fonte ufficiale ISPRA) |
| Museo Civico | Lun–Ven 9:30–18:30 (weekend ridotto 9:30–13:30, non modellato) | museocivicobari.it |
| Chiesa di San Gregorio | **Apertura IRREGOLARE/LIMITATA**, nessun orario fisso pubblicato (recensioni multiple concordanti su chiusure impreviste) | tripadvisor.it (recensioni multiple) |
| Palazzo Mincuzzi | **Ex-negozio Benetton chiuso da dic. 2024**; oggi visitabile solo dall'esterno/facciata (correzione: la stima iniziale lo dava aperto come negozio 9–19) | theaboutmagazine.it/palazzo-mincuzzi-bari |
| Stadio San Nicola | **Nessun orario di visita turistica regolare**; accessibile soprattutto in occasione di eventi/partite (correzione rispetto alla stima iniziale 10–17) | it.wikipedia.org/wiki/Stadio_San_Nicola |
| Fortino Sant'Antonio | Area esterna 8:00–tramonto; aree interne solo durante eventi/mostre (non modellato) | audiala.com/it/italia/bari/fortino-santantonio |
| Strada delle Orecchiette, Via Sparano | **Non applicabile**: vie pubbliche sempre accessibili (corretto da una finestra-tipo "da negozio" 9–19/9–20, incoerente con Lungomare/Arco Basso già modellati come 0–24) | — (correzione di modellazione, non di fonte) |
| Lungomare Nazario Sauro, Arco Basso e Bari Vecchia, Piazza del Ferrarese, Spiaggia Pane e Pomodoro, Spiaggia di Torre Quetta | **Non applicabile**: spazi pubblici urbani, accessibili 24/24 per natura | — (nessuna verifica necessaria) |

**Correzioni emerse dalla ricerca (non solo "affinamenti"):** in **quattro
casi** la stima iniziale era effettivamente sbagliata, non solo
imprecisa: l'Orto Botanico è aperto solo nei giorni feriali; l'Acquario
di Bari richiede prenotazione e non ha orario fisso; Palazzo Mincuzzi
non è più un negozio visitabile dal 2024; lo Stadio San Nicola non ha
orari di visita turistica regolari. A questi si aggiunge un quinto caso,
di natura diversa: Chiesa di San Gregorio ha apertura dichiaratamente
irregolare secondo più fonti indipendenti, quindi non le è stato
assegnato un orario fittizio. È un buon promemoria del perché le linee
guida del corso chiedono di non basarsi su dati non verificati: anche
stime "plausibili" possono essere semplicemente sbagliate, non solo
imprecise — e a volte la risposta onesta è "non c'è un orario fisso",
non un numero approssimativo.

**Limite dichiarato:** il modello dati attuale (`opening_hour`,
`closing_hour`) rappresenta una **singola finestra giornaliera**, quindi
non cattura chiusure infrasettimanali (es. Castello Svevo il mercoledì,
Orto Botanico nel weekend) né doppie finestre con pausa pranzo (es.
Cattedrale). È una semplificazione consapevole, da discutere
esplicitamente in relazione come limite del sistema — un'estensione
naturale sarebbe modellare gli orari come lista di intervalli per
giorno della settimana.

Le **durate di visita** (`visit_duration_min`) non sono dati "ufficiali"
reperibili (i siti istituzionali non pubblicano tempi medi di visita):
sono stime basate su prassi turistica tipica per categoria di luogo,
analoghe a quelle che un autore di una guida turistica indicherebbe.
Vanno trattate come ipotesi di progetto, non come fatti verificati.

## I restanti 8 POI da verificare
Teatro Petruzzelli, Mercato del Pesce, Parco 2 Giugno, Chiesa Russa di
San Nicola, Teatro Kursaal Santalucia, Palazzo della Provincia, Foro
Boario, Basilica Santa Maria del Buon Consiglio. Per questi la ricerca
web non ha restituito orari ufficiali affidabili nel tempo disponibile;
restano stime ragionevoli per categoria, dichiarate come tali.

## Come ottenere un dataset interamente reale (raccomandato prima della consegna)
Il sandbox in cui è stato generato questo scaffold non ha accesso alla
rete pubblica (solo a repository di pacchetti), quindi non è stato
possibile interrogare direttamente OpenStreetMap da qui. È però incluso
uno script pronto all'uso, **eseguibile sul tuo computer** (dove l'accesso
a Internet non è ristretto), che effettua un'estrazione live dei POI di
una città a scelta tramite l'API Overpass di OpenStreetMap:

```bash
python data/fetch_osm_pois.py --city "Bari, Italy" --out data/poi_osm_raw.csv
```

Vedi `data/fetch_osm_pois.py` per i dettagli. I dati OpenStreetMap sono
distribuiti con licenza **ODbL** (Open Database License): è consentito
l'uso, anche in un progetto accademico, citando "© OpenStreetMap
contributors" come richiesto dalla licenza.

Dopo l'estrazione, lo schema delle colonne andrà allineato a quello
atteso da `ontology/build_kb.py` (vedi colonne richieste in cima allo
script), e gli orari di apertura — spesso assenti o incompleti su OSM
per molti POI minori — andranno integrati manualmente per i luoghi
principali (come fatto qui per gli 8 POI sopra elencati).
