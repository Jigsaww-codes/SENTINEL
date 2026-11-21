"""Central configuration. All detection thresholds are configurable via env / runtime settings."""
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "data"


@dataclass
class DetectionSettings:
    stationary_radius_m: float = float(os.getenv("STATIONARY_RADIUS_M", 30))
    stationary_duration_min: float = float(os.getenv("STATIONARY_DURATION_MIN", 30))
    review_threshold: float = float(os.getenv("REVIEW_THRESHOLD", 40))
    high_threshold: float = float(os.getenv("HIGH_THRESHOLD", 70))

    def as_dict(self):
        return asdict(self)


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'sentinel.db'}")
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]

# Risk weights: R = 0.25S + 0.20I + 0.20C + 0.15T + 0.20M
RISK_WEIGHTS = {"S": 0.25, "I": 0.20, "C": 0.20, "T": 0.15, "M": 0.20}

settings = DetectionSettings()
