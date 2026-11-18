"""V7.1 offline release gate: source, model wiring and safety invariants.

No broker connection, Supabase writes or internet calls.
"""
import ast
from pathlib import Path

from forecast_engine import model_flags, latest_completed_position
from signal_models import MODEL_LABELS
from research_multimarket import FX_MARKETS

REQUIRED_FILES = (
    "app.py", "signal_models.py", "forecast_engine.py",
    "collect_predictions.py", "evaluate_predictions.py",
    "prediction_store.py", "prediction_tracking.py",
    "prediction_monitor.py", "forward_evidence.py",
    "research_multimarket.py", "research_robustness.py",
    "research_release_audit.py",
)


def check_release(root="."):
    root = Path(root)
    problems = []
    for filename in REQUIRED_FILES:
        target = root / filename
        if not target.is_file():
            problems.append(f"Missing release module: {filename}")
            continue
        try:
            ast.parse(target.read_text(encoding="utf-8"), filename=filename)
        except (SyntaxError, UnicodeDecodeError) as exc:
            problems.append(f"Invalid Python file: {filename}: {exc}")

    if len(MODEL_LABELS) != 9:
        problems.append("Expected nine independently versioned research models")
    if len(set(MODEL_LABELS)) != len(MODEL_LABELS):
        problems.append("Duplicate model version identifiers")
    if len(set(MODEL_LABELS.values())) != len(MODEL_LABELS):
        problems.append("Duplicate strategy display labels")
    if len(FX_MARKETS) != 15:
        problems.append("FX research market list differs from validated test scope")

    app_file = root / "app.py"
    collector_file = root / "collect_predictions.py"
    if app_file.exists():
        app = app_file.read_text(encoding="utf-8")
        if 'APP_VERSION = "V8.4 Signal Research"' not in app:
            problems.append("App release label has not been finalized")
        if 'latest_signal(' not in app or 'model_flags(' not in app:
            problems.append("Terminal is not wired to the shared signal engine")
        if "prediction_exists(" not in app:
            problems.append("Manual save lacks exact duplicate guard")
        if "list_predictions_paginated(" not in app:
            problems.append("History lacks paginated reads")
        if "NOT VALIDATED" not in app:
            problems.append("Unverified predictor caution missing from UI")
    if collector_file.exists():
        collector = collector_file.read_text(encoding="utf-8")
        if "latest_signal(" not in collector:
            problems.append("Collector diverges from shared signal engine")
        if "prediction_exists(" not in collector:
            problems.append("Collector lacks exact persisted duplicate lookup")
    if problems:
        raise RuntimeError("\n".join(problems))
    return {
        "release": "V8.4",
        "registered_research_models": len(MODEL_LABELS),
        "fx_benchmark_markets": len(FX_MARKETS),
        "source_modules_checked": len(REQUIRED_FILES),
        "validated_models": 0,
        "status": "STATIC_RELEASE_GATE_PASSED",
    }


if __name__ == "__main__":
    print(check_release())
    print("Static check and offline tests do NOT certify live data reliability,")
    print("broker execution, model accuracy, or Streamlit Cloud deployment.")
