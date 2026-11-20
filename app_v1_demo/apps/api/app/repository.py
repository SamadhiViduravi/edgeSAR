from pathlib import Path
from .models import Scenario

ROOT = Path(__file__).resolve().parents[3]


def load_scenario() -> Scenario:
    return Scenario.model_validate_json((ROOT / "scenarios/urban-disaster.json").read_text())
