# verify_setup.py
# ------------------------------------------------------------
# Esegue l'intera pipeline TripSolver e genera un report
# (verification_report.txt) con i risultati di ciascuno step.
#
# Uso:
#   python verify_setup.py
# ------------------------------------------------------------

import subprocess
import sys
import re
import platform
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
REPORT = []


def log(line=""):
    print(line)
    REPORT.append(str(line))


def run_step(title, cmd, timeout=300):
    log(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    try:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        output = (result.stdout or "") + (result.stderr or "")
        ok = result.returncode == 0
    except FileNotFoundError as e:
        output = f"[ERRORE] Comando non trovato: {e}"
        ok = False
    except subprocess.TimeoutExpired:
        output = f"[ERRORE] Timeout dopo {timeout}s"
        ok = False
    log(output.strip())
    log(f"\n[{'OK' if ok else 'FALLITO'}] {title}")
    return output, ok


def main():
    log("REPORT DI VERIFICA TRIPSOLVER")
    log(f"Generato il: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Sistema: {platform.system()} {platform.release()} | Python {platform.python_version()}")

    log("\n--- Verifica tipo colonne opening_hour/closing_hour nel CSV ---")
    try:
        import pandas as pd
        df_test = pd.read_csv(ROOT / "data" / "poi_bari_sample.csv",
                              dtype={"opening_hour": float, "closing_hour": float})
        oh_type = str(df_test["opening_hour"].dtype)
        log(f"  opening_hour dtype: {oh_type}  ({'OK' if oh_type == 'float64' else 'ATTENZIONE: non e float64'})")
    except Exception as e:
        log(f"  [ATTENZIONE] {e}")

    log("\n--- Verifica Java (richiesto dal reasoner OWL) ---")
    try:
        java_v = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10)
        log((java_v.stderr or java_v.stdout).strip())
    except FileNotFoundError:
        log("[ATTENZIONE] Java non trovato nel PATH: il reasoner OWL non potra' funzionare. "
            "Installa un JDK/JRE 11+ (es. adoptium.net).")

    out1, ok1 = run_step("1/4 — ontology/build_kb.py", [sys.executable, "ontology/build_kb.py"])
    m = re.search(r"Reasoner usato:\s*(\w+)", out1)
    if m:
        reasoner = m.group(1).upper()
        log(f"\n>>> REASONER USATO: {reasoner}")
        if reasoner == "PELLET":
            log(">>> Pellet ha funzionato correttamente.")
        elif reasoner == "HERMIT":
            log(">>> Pellet non disponibile (incompatibilita' Java): fallback su HermiT.")
            log(">>> Comportamento atteso e documentato nel paragrafo 2.3.2.")
    else:
        log("\n>>> ATTENZIONE: impossibile determinare il reasoner usato.")

    out2, ok2 = run_step("2/4 — ml/model_comparison.py (Esperimento A)",
                         [sys.executable, "ml/model_comparison.py"])
    out3, ok3 = run_step("3/4 — ml/low_data_scenario.py (Esperimento B)",
                         [sys.executable, "ml/low_data_scenario.py"], timeout=600)
    out4, ok4 = run_step("4/4 — demo/run_demo.py", [sys.executable, "demo/run_demo.py"])

    log(f"\n\n{'=' * 70}\nRIEPILOGO\n{'=' * 70}")
    steps = [("build_kb.py", ok1), ("model_comparison.py", ok2),
             ("low_data_scenario.py", ok3), ("run_demo.py", ok4)]
    for name, ok in steps:
        log(f"  [{'OK' if ok else 'FALLITO'}] {name}")

    if all(ok for _, ok in steps):
        log("\nTutti gli script sono andati a buon fine.")
        log("I risultati ML possono variare leggermente fra esecuzioni diverse:")
        log("random_state non e' fissato nei modelli ensemble (cfr. par. 5.4).")
    else:
        log("\nAlmeno uno step e' fallito: controlla l'output sopra per i dettagli.")

    report_path = ROOT / "verification_report.txt"
    report_path.write_text("\n".join(REPORT), encoding="utf-8")
    print(f"\nReport completo salvato in: {report_path}")


if __name__ == "__main__":
    main()
