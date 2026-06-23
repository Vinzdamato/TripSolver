# low_data_scenario.py
# ------------------------------------------------------------
# OBIETTIVO
#   Le linee guida del corso segnalano che un confronto baseline vs
#   arricchito su uno split "standard" può non mostrare un vantaggio
#   chiaro della KB (specie su un dataset piccolo come quello incluso).
#   Questo script replica l'idea del progetto di riferimento
#   (HeartNeuroSy, scenario di "screening a basso costo"): valutare il
#   confronto in funzione della QUANTITA' di dati etichettati
#   disponibili in fase di training, per verificare l'ipotesi che le
#   feature semantiche derivate dalla KB aiutino di più quando si hanno
#   pochi esempi (es. catalogo POI appena avviato, prima fase di
#   raccolta dati) rispetto a quando se ne hanno molti.
#
# METODOLOGIA
#   Per ciascuna dimensione del training set in TRAIN_SIZES:
#     - si ripete N_REPEATS volte un campionamento casuale (stratificato
#       per classe quando possibile) di quella dimensione dal dataset
#     - si allena il modello su baseline vs arricchito e si valuta sul
#       resto del dataset (test set = tutto ciò che non è in training)
#     - si riportano media e deviazione standard dell'accuracy sui
#       N_REPEATS run, NON un singolo risultato
#
# LIMITE DICHIARATO
#   Con soli 28 POI nel dataset di esempio, le dimensioni di training
#   più piccole (es. 6-8 esempi) producono stime ad alta varianza: lo
#   scopo qui è dimostrare la metodologia sperimentale corretta. Su un
#   dataset reale più ampio (raccomandato, cfr. data/SOURCES.md) questo
#   stesso script produce risultati più stabili e interpretabili.
# ------------------------------------------------------------

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

INPUT_CSV = "data/poi_enriched.csv"
TARGET = "tourist_tier"

BASELINE_NUM = ["visit_duration_min"]
BASELINE_BIN = ["indoor", "free_entry", "iconic"]
BASELINE_CAT = ["category", "neighborhood"]
SEMANTIC_BIN = [
    "is_VisitaRapida", "is_EsperienzaImmersiva", "is_IconaGratuita",
    "is_AltaPriorita", "is_AdattoMaltempo", "is_DaAbbinareVicino",
]

TRAIN_SIZES = [6, 10, 14, 18, 22]   # numero di esempi etichettati disponibili
N_REPEATS = 30
SEED_BASE = 1000

# NOTA METODOLOGICA IMPORTANTE
#   Le feature semantiche qui sono soglie sulla stessa colonna grezza
#   (visit_duration_min) già disponibile al modello. Un classificatore
#   ad albero (RandomForest) può imparare DA SOLO queste soglie dai dati
#   grezzi, quindi trae poco vantaggio da una feature che le rende
#   esplicite. Un modello LINEARE (LogisticRegression), invece, non può
#   rappresentare nativamente una soglia non lineare su una feature
#   continua: per lui la feature pre-calcolata dalla KB è informazione
#   genuinamente più accessibile. Per questo lo script confronta
#   ENTRAMBI i modelli: il punto non è "la KB vince sempre", ma "il
#   vantaggio della KB dipende dalla capacità del modello a valle di
#   ricostruire da sé quella stessa conoscenza" — un'osservazione che
#   vale la pena discutere esplicitamente in relazione.

CLASSIFIERS = {
    "RandomForest": lambda: RandomForestClassifier(n_estimators=200, random_state=None),
    "LogisticRegression": lambda: LogisticRegression(max_iter=2000),
}


def build_pipeline(clf_name, num_cols, bin_cols, cat_cols):
    pre = ColumnTransformer(transformers=[
        ("num", StandardScaler(), num_cols),
        ("bin", "passthrough", bin_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ])
    return Pipeline(steps=[("pre", pre), ("clf", CLASSIFIERS[clf_name]())])


def run_one(df, train_size, clf_name, bin_cols, seed):
    X = df[BASELINE_NUM + bin_cols + BASELINE_CAT]
    y = df[TARGET]
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, train_size=train_size, stratify=y, random_state=seed
        )
    except ValueError:
        # stratificazione impossibile con classi troppo rare per quel train_size
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, train_size=train_size, random_state=seed
        )
    pipe = build_pipeline(clf_name, BASELINE_NUM, bin_cols, BASELINE_CAT)
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    return accuracy_score(y_test, y_pred), f1_score(y_test, y_pred, average="macro", zero_division=0)


def main():
    df = pd.read_csv(INPUT_CSV, dtype={"opening_hour": float, "closing_hour": float})
    rows = []

    for clf_name in CLASSIFIERS:
        for train_size in TRAIN_SIZES:
            for feature_set, bin_cols in [("baseline", BASELINE_BIN),
                                           ("enriched", BASELINE_BIN + SEMANTIC_BIN)]:
                accs, f1s = [], []
                for r in range(N_REPEATS):
                    acc, f1 = run_one(df, train_size, clf_name, bin_cols, seed=SEED_BASE + r)
                    accs.append(acc)
                    f1s.append(f1)
                rows.append({
                    "classifier": clf_name,
                    "train_size": train_size,
                    "feature_set": feature_set,
                    "accuracy_mean": np.mean(accs),
                    "accuracy_std": np.std(accs),
                    "f1_macro_mean": np.mean(f1s),
                    "f1_macro_std": np.std(f1s),
                })

    results = pd.DataFrame(rows)
    print("=== Accuracy media ± dev.std, baseline vs arricchito, per modello e dimensione del training set ===")
    print(results.round(3).to_string(index=False))

    for clf_name in CLASSIFIERS:
        sub = results[results["classifier"] == clf_name]
        pivot = sub.pivot(index="train_size", columns="feature_set", values="accuracy_mean")
        pivot["delta_enriched_minus_baseline"] = pivot["enriched"] - pivot["baseline"]
        print(f"\n=== Delta di accuracy (arricchito - baseline) — {clf_name} ===")
        print(pivot.round(3).to_string())

    out_path = "ml/low_data_scenario_results.csv"
    results.to_csv(out_path, index=False)
    print(f"\n[OK] Risultati salvati in {out_path}")
    print("\n[NOTA] Confronta il pattern fra RandomForest e LogisticRegression: se il")
    print("vantaggio della KB è più marcato per il modello lineare, è coerente con la")
    print("nota metodologica sopra. Con un dataset reale più ampio questo confronto")
    print("sarà più stabile e significativo statisticamente.")


if __name__ == "__main__":
    main()
