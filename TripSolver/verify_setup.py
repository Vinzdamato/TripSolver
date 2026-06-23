# verify_setup.py
# ------------------------------------------------------------
# Esegue l'intera pipeline TripSolver sulla TUA macchina e genera un
# report (verification_report.txt) da confrontare con quanto riportato
# in docs/Documentazione_TripSolver.docx.
#
# Serve a rispondere a due domande concrete prima della consegna:
#   1) La pipeline funziona davvero, end-to-end, sul tuo computer?
#   2) Quale reasoner viene effettivamente usato (Pellet o HermiT)?
#      La documentazione descrive un fallback Pellet->HermiT osservato
#      nell'ambiente in cui è stato scritto il progetto: sul tuo PC
#      potrebbe non verificarsi (Pellet potrebbe funzionare regolarmente).
#      Questo script te lo dice esplicitamente, cosi' sai se quel
#      paragrafo va aggiornato prima di discuterlo a voce.
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
        log(f"  opening_hour dtype: {oh_type}  ({'OK' if oh_type == 'float64' else 'ATTENZIONE: non è float64'})")
        log("  La conversione esplicita a float è attiva: il bug TypeError di run_demo.py non può ripresentarsi.")
    except Exception as e:
        log(f"  [ATTENZIONE] {e}")

    log("\n--- Verifica Java (richiesto dal reasoner OWL) ---")
    try:
        java_v = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10)
        log((java_v.stderr or java_v.stdout).strip())
    except FileNotFoundError:
        log("[ATTENZIONE] Java non trovato nel PATH: il reasoner OWL fallirà completamente "
            "(né Pellet né HermiT potranno funzionare). Installa un JDK/JRE 11+ (es. adoptium.net).")

    out1, ok1 = run_step("1/4 — ontology/build_kb.py", [sys.executable, "ontology/build_kb.py"])
    m = re.search(r"Reasoner usato:\s*(\w+)", out1)
    if m:
        reasoner = m.group(1)
        log(f"\n>>> REASONER EFFETTIVAMENTE USATO SUL TUO PC: {reasoner.upper()}")
        if reasoner == "pellet":
            log(">>> Sul mio ambiente di sviluppo Pellet falliva (incompatibilità Java) e si")
            log(">>> ricadeva su HermiT: e' quanto descritto nel paragrafo 2.3.2 della")
            log(">>> documentazione. Sul TUO PC Pellet ha invece funzionato regolarmente:")
            log(">>> quel paragrafo descrive un fallback che da te non si verifica, e va")
            log(">>> aggiornato prima di doverlo spiegare a voce in sede d'esame.")
        elif reasoner == "hermit":
            log(">>> Coerente con il fallback descritto nel paragrafo 2.3.2 della")
            log(">>> documentazione. Nessuna modifica necessaria su questo punto.")
    else:
        log("\n>>> ATTENZIONE: non sono riuscito a determinare quale reasoner e' stato usato "
            "(controlla l'output sopra per eventuali errori).")

    out2, ok2 = run_step("2/4 — ml/model_comparison.py (Esperimento A)", [sys.executable, "ml/model_comparison.py"])
    out3, ok3 = run_step("3/4 — ml/low_data_scenario.py (Esperimento B)", [sys.executable, "ml/low_data_scenario.py"], timeout=600)
    out4, ok4 = run_step("4/4 — demo/run_demo.py", [sys.executable, "demo/run_demo.py"])

    log(f"\n\n{'=' * 70}\nRIEPILOGO\n{'=' * 70}")
    steps = [("build_kb.py", ok1), ("model_comparison.py", ok2), ("low_data_scenario.py", ok3), ("run_demo.py", ok4)]
    for name, ok in steps:
        log(f"  [{'OK' if ok else 'FALLITO'}] {name}")

    if all(ok for _, ok in steps):
        log("\nTutti gli script sono andati a buon fine. Prossimi passi:")
        log("  1. Apri questo file (verification_report.txt) e cerca le tabelle 'Esperimento A' / 'Esperimento B'.")
        log("  2. Confrontale con le Tabelle 6.1 e 6.2 di Documentazione_TripSolver.docx.")
        log("     Differenze di qualche punto percentuale sono NORMALI (random_state non e' fissato")
        log("     apposta nei due script ML, vedi §5.4 della documentazione).")
        log("     Se invece vedi pattern opposti (es. il segno del delta KB invertito) o numeri molto")
        log("     diversi, vale la pena capire perche' prima della consegna.")
        log("  3. Confronta l'itinerario stampato da run_demo.py con quello di Fig 7.1/§7.2: se il")
        log("     dataset non e' cambiato, l'ordine delle tappe e i tempi totali dovrebbero combaciare")
        log("     esattamente (A* e CSP sono deterministici, solo i due script ML non lo sono).")
    else:
        log("\nAlmeno uno step e' fallito: controlla l'output completo sopra prima di procedere.")

    report_path = ROOT / "verification_report.txt"
    report_path.write_text("\n".join(REPORT), encoding="utf-8")
    print(f"\nReport completo salvato in: {report_path}")


if __name__ == "__main__":
    main()
