"""Run the whole pipeline end to end:  python run_pipeline.py"""
import subprocess
import sys
import time

STEPS = [
    # ("Ingest prices and FX", ["src/<your_phase1_script>.py"]),  # add your Phase 1 entry point here
    ("Generate synthetic trades", ["src/generate_trades.py"]),
    ("Raw -> cleaned", ["src/run_sql.py", "cleaned"]),
    ("Cleaned -> analytics", ["src/run_sql.py", "analytics"]),
    ("Run tests", ["-m", "pytest", "-q"]),
]


def main() -> None:
    for name, args in STEPS:
        print(f"\n=== {name} ===")
        start = time.time()
        result = subprocess.run([sys.executable, *args])
        if result.returncode != 0:
            sys.exit(f"FAILED at step: {name}")
        print(f"({time.time() - start:.1f}s)")
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()