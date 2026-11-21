"""Built-in validation suite: runs labelled cases through the REAL pipeline and reports expected vs actual.
Shown on the AI Analytics page as false-positive testing."""
from datetime import datetime, timedelta
from typing import List

import location_processor as lp
import pipeline
from config import DetectionSettings
from schemas import RiskLevel as L


def _utc(h, m=0):
    return datetime(2026, 11, 21, h, m) - lp.IST


def _hist(lat, lon, start, minutes, step=5, move=False):
    out = []
    for i in range(0, minutes + 1, step):
        j = 0.00004 * ((i // step) % 3)
        out.append(lp.Fix(lat + j + (0.0006 * (i // step) if move else 0), lon + j, start + timedelta(minutes=i)))
    return out


# name, history, set of acceptable levels, why it matters
CASES = [
    ("A. Moving through populated area", _hist(23.2300, 77.4300, _utc(11), 60, move=True), {L.NORMAL}, "Moving devices are not evaluated"),
    ("B. Stationary 60 min, populated, daytime", _hist(23.2330, 77.4340, _utc(13), 60), {L.NORMAL}, "Ordinary presence must stay normal"),
    ("B2. Stationary 2 h, populated, 01:00 (at home)", _hist(23.2120, 77.4330, _utc(1), 120), {L.NORMAL}, "Night-time alone must not alert"),
    ("E. Stationary 90 min in populated area with incident history", _hist(23.2330, 77.4340, _utc(13), 90), {L.NORMAL}, "Incident history alone is context only"),
    ("F. Isolated, only 20 min", _hist(23.1250, 77.3350, _utc(22), 20), {L.NORMAL}, "Below the stationary threshold"),
    ("C. Stationary 60 min, isolated, 23:00", _hist(23.1250, 77.3350, _utc(22), 60), {L.REVIEW_REQUIRED}, "Remote + long dwell: review, not high"),
    ("D. Stationary 60 min, isolated + incident context", _hist(23.1050, 77.3900, _utc(22, 30), 60), {L.HIGH_PRIORITY}, "Multiple independent indicators"),
]


def run_suite(settings: DetectionSettings) -> List[dict]:
    out = []
    for name, hist, ok, why in CASES:
        a = pipeline.analyse(hist, settings)
        out.append({"case": name, "expected": sorted(x.value for x in ok), "actual": a.risk_level.value,
                    "risk_score": a.risk_score, "passed": a.risk_level in ok, "why": why,
                    "stationary_minutes": round(a.stationary_minutes)})
    return out
