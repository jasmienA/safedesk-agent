import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
KB_DIR = ROOT / "kb"
RESULTS_DIR = ROOT / "results"

# The fake world "today". Fixed so refund-window checks give the same answer every run.
TODAY = date(2026, 11, 11)

CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "")
SPECIALIST_MODEL = os.getenv("SPECIALIST_MODEL", "")
LLM_TEMPERATURE = os.getenv("LLM_TEMPERATURE", "")  # leave empty if your model rejects temperature
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "6"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))

REFUND_CAP = 500.0
REFUND_WINDOW_DAYS = 90


def require_models():
    missing = [n for n, v in (("CLASSIFIER_MODEL", CLASSIFIER_MODEL), ("SPECIALIST_MODEL", SPECIALIST_MODEL)) if not v]
    if missing:
        raise RuntimeError(
            f"Set {', '.join(missing)} in your .env file (see .env.example). "
            "Pick model names from the current list at platform.openai.com/docs/models."
        )
