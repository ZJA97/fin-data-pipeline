"""Run the whole pipeline end to end:  python run_pipeline.py

Exit codes (read by the GitHub Actions workflow):
  0  everything passed
  1  a step crashed or ingestion failed -> workflow retries, then alerts
  2  all steps ran but found data problems -> workflow alerts, no retry
"""
import subprocess
import sys
import time

OK, CRASH, FINDINGS = 0, 1, 2

# (name, args, exit codes that mean "ran fine but found problems")
STEPS = [
    ("Ingest prices + FX (yfinance), raw checks", ["-m", "pipeline.run"], {2}),
    ("Generate synthetic trades", ["src/generate_trades.py"], set()),
    ("Raw -> cleaned", ["src/run_sql.py", "cleaned"], set()),
    ("Cleaned -> analytics", ["src/run_sql.py", "analytics"], set()),
    ("Run tests", ["-m", "pytest", "-q"], {1}),
    ("Ingest Tiingo prices", ["src/ingest_tiingo.py"], set()),
    ("Reconcile + data quality", ["src/reconcile.py"], {2}),
    ("Export results", ["src/export_results.py"], set()),
]


def main() -> int:
    findings = []
    for name, args, finding_codes in STEPS:
        print(f"\n=== {name} ===")
        start = time.time()
        code = subprocess.run([sys.executable, *args]).returncode
        print(f"({time.time() - start:.1f}s)")
        if code == 0:
            continue
        if code in finding_codes:
            findings.append(name)  # keep going: later steps may add more detail
            continue
        print(f"CRASHED at step: {name} (exit code {code})")
        return CRASH
    if findings:
        print("\nPipeline finished with problems in: " + ", ".join(findings))
        return FINDINGS
    print("\nPipeline complete.")
    return OK


if __name__ == "__main__":
    sys.exit(main())