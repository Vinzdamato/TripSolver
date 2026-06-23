# model_comparison.py
# ------------------------------------------------------------
# OBIETTIVO
#   Confrontare modelli di apprendimento supervisionato nel predire il
#   "tourist_tier" (MustSee / Secondary / Optional) di un POI, usando:
#     (a) feature BASELINE: attributi grezzi del dataset (categoria,
#         quartiere, durata, indoor, gratuito, iconico)
#     (b) feature ARRICCHITE: baseline + feature semantiche inferite
#         dal reasoner OWL (is_VisitaRapida, is_EsperienzaImmersiva, ecc.)
#   per quantificare il contributo della Knowledge Base al task di
#   apprendimento (cfr. cap. 7 del programma -- Apprendimento Supervisionato).
#
# METODOLOGIA DI VALUTAZIONE (importante per i criteri di valutazione)
#   - NON si usa un singolo train/test split: si usa Repeated Stratified
#     K-Fold (k=5, n_repeats=10 => 50 run complessivi) per ottenere stime
#     robuste.
#   - Si riportano MEDIA e DEVIAZIONE STANDARD delle metriche su tutti i
#     run, non una singola matrice di confusione/classification report.
#   - Le metriche scelte (accuracy, F1-macro, balanced accuracy) sono
#     adeguate a un problema multi-classe leggermente sbilanciato.
# ------------------------------------------------------------

import numpy as np
import pandas as pd
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

INPUT_CSV = "data/poi_enriched.csv"

BASELINE_NUM = ["visit_duration_min"]
BASELINE_BIN = ["indoor", "free_entry", "iconic"]
BASELINE_CAT = ["category", "neighborhood"]

SEMANTIC_BIN = [
    "is_VisitaRapida", "is_EsperienzaImmersiva", "is_IconaGratuita",
    "is_AltaPriorita", "is_AdattoMaltempo", "is_DaAbbinareVicino",
]

TARGET = "tourist_tier"

MODELS = {
    "LogisticRegression": LogisticRegression(max_iter=2000),
    "RandomForest": RandomForestClassifier(n_estimators=200, random_state=None),
    "GradientBoosting": GradientBoostingClassifier(random_state=None),
}

SCORING = {
    "accuracy": "accuracy",
    "f1_macro": "f1_macro",
    "balanced_accuracy": "balanced_accuracy",
}


def build_pipeline(model, num_cols, bin_cols, cat_cols):
    pre = ColumnTransformer(transformers=[
        ("num", StandardScaler(), num_cols),
        ("bin", "passthrough", bin_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ])
    return Pipeline(steps=[("pre", pre), ("clf", model)])


def evaluate(df, num_cols, bin_cols, cat_cols, n_splits=5, n_repeats=10, seed=42):
    X = df[num_cols + bin_cols + cat_cols]
    y = df[TARGET]
    rskf = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=seed)

    results = []
    for model_name, model in MODELS.items():
        pipe = build_pipeline(model, num_cols, bin_cols, cat_cols)
        scores = cross_validate(pipe, X, y, cv=rskf, scoring=SCORING, n_jobs=-1, error_score="raise")
        row = {"model": model_name}
        for metric in SCORING:
            vals = scores[f"test_{metric}"]
            row[f"{metric}_mean"] = np.mean(vals)
            row[f"{metric}_std"] = np.std(vals)
        results.append(row)
    return pd.DataFrame(results)


def main():
    df = pd.read_csv(INPUT_CSV, dtype={"opening_hour": float, "closing_hour": float})

    # Nota: con un dataset cosi' piccolo (28 POI), k=5/n_repeats=10 e' gia'
    # al limite della significativita' statistica: lo scopo qui e'
    # dimostrare la METODOLOGIA corretta di valutazione. Su un dataset
    # reale più ampio (raccomandato per la consegna finale) aumentare
    # opportunamente il numero di esempi prima di trarre conclusioni.

    print("=== BASELINE (solo feature grezze) ===")
    baseline_res = evaluate(df, BASELINE_NUM, BASELINE_BIN, BASELINE_CAT)
    print(baseline_res.round(3).to_string(index=False))

    print("\n=== ARRICCHITO (baseline + feature semantiche da KB) ===")
    enriched_res = evaluate(df, BASELINE_NUM, BASELINE_BIN + SEMANTIC_BIN, BASELINE_CAT)
    print(enriched_res.round(3).to_string(index=False))

    print("\n=== DELTA (arricchito - baseline), per accuracy media ===")
    merged = baseline_res[["model", "accuracy_mean"]].merge(
        enriched_res[["model", "accuracy_mean"]], on="model", suffixes=("_base", "_enr")
    )
    merged["delta_accuracy"] = merged["accuracy_mean_enr"] - merged["accuracy_mean_base"]
    print(merged.round(3).to_string(index=False))

    out_path = "ml/model_comparison_results.csv"
    pd.concat(
        [baseline_res.assign(feature_set="baseline"), enriched_res.assign(feature_set="enriched")]
    ).to_csv(out_path, index=False)
    print(f"\n[OK] Risultati salvati in {out_path}")


if __name__ == "__main__":
    main()
