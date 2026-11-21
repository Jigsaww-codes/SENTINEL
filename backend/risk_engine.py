"""Explainable risk scoring:  R = 0.25*S + 0.20*I + 0.20*C + 0.15*T + 0.20*M   (all inputs 0-100).

Guard rails (demo thresholds, NOT validated crime probabilities):
  * 'Elevated' = indicator >= 50.  T (time of day) and C (incident history) only AMPLIFY.
  * Unless isolation (I) or the Isolation-Forest anomaly (M) is elevated, the score is capped at 39:
    stationary duration, night-time, or a crime-zone score alone can never raise an alert.
  * HIGH-PRIORITY needs >= 2 elevated among I, C, M (never time alone) AND R >= 70.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List

from config import RISK_WEIGHTS, DetectionSettings
from schemas import RiskLevel

ELEVATED = 50.0
CONTEXT_KEYS = ("I", "C", "T", "M")   # reported as "elevated"
PRIMARY_KEYS = ("I", "M")             # at least one must be elevated to raise any alert
HIGH_KEYS = ("I", "C", "M")           # at least two must be elevated for HIGH priority
NAMES = {"S": "stationary duration", "I": "geographical isolation", "C": "historical incident context",
         "T": "unusual time of day", "M": "movement/feature anomaly"}


@dataclass
class RiskResult:
    S: float; I: float; C: float; T: float; M: float
    raw_total: float
    total: float
    level: RiskLevel
    contributions: Dict[str, float]
    elevated: List[str]
    caps_applied: List[str] = field(default_factory=list)

    def as_dict(self):
        return {"S": self.S, "I": self.I, "C": self.C, "T": self.T, "M": self.M,
                "raw_total": self.raw_total, "total": self.total, "level": self.level.value,
                "contributions": self.contributions, "elevated": self.elevated,
                "caps_applied": self.caps_applied, "weights": RISK_WEIGHTS}


def stationary_score(minutes: float, threshold_min: float) -> float:
    """0 below the configured threshold; scales to 100 at 3x the threshold."""
    if minutes < threshold_min:
        return 0.0
    return min(100.0, 100.0 * minutes / (3 * threshold_min))


def time_score(hour: float) -> float:
    """Unusual-time score from local hour: 100 at 02:00, 0 at 14:00 (smooth, wraps midnight)."""
    x = 0.5 + 0.5 * math.cos(2 * math.pi * (hour - 2.0) / 24.0)
    return round(100.0 * x ** 1.5, 1)


def level_for(score: float, s: DetectionSettings) -> RiskLevel:
    if score >= s.high_threshold:
        return RiskLevel.HIGH_PRIORITY
    if score >= s.review_threshold:
        return RiskLevel.REVIEW_REQUIRED
    return RiskLevel.NORMAL


def compute_risk(S, I, C, T, M, s: DetectionSettings) -> RiskResult:
    vals = {"S": S, "I": I, "C": C, "T": T, "M": M}
    vals = {k: max(0.0, min(100.0, float(v))) for k, v in vals.items()}
    contrib = {k: round(RISK_WEIGHTS[k] * vals[k], 2) for k in vals}
    raw = round(sum(contrib.values()), 1)
    elevated = [k for k in CONTEXT_KEYS if vals[k] >= ELEVATED]
    total, caps = raw, []
    primary = [k for k in PRIMARY_KEYS if vals[k] >= ELEVATED]
    high_n = len([k for k in HIGH_KEYS if vals[k] >= ELEVATED])
    if not primary and total > s.review_threshold - 1:
        total = s.review_threshold - 1
        caps.append("Neither isolation nor a feature anomaly is elevated: duration, time of day or "
                    "incident history alone cannot raise an alert")
    elif high_n < 2 and total > s.high_threshold - 1:
        total = s.high_threshold - 1
        caps.append("Fewer than two of isolation / incident context / anomaly are elevated: cannot be high priority")
    total = round(total, 1)
    return RiskResult(**vals, raw_total=raw, total=total, level=level_for(total, s),
                      contributions=contrib, elevated=elevated, caps_applied=caps)


def build_reasons(minutes: float, radius_m: float, geo, hour: float, r: RiskResult,
                  top_features: List[str]) -> List[str]:
    out = [f"Stationary within {radius_m:.0f} m for {minutes:.0f} min"]
    if r.I >= ELEVATED:
        out.append(f"Isolated location: {geo.populated_distance_m/1000:.1f} km from nearest settlement, "
                   f"{geo.road_distance_m/1000:.1f} km from nearest road")
    if r.C >= ELEVATED:
        out.append("Inside/near a historical incident-context zone (aggregate, simulated data; context only)")
    if r.T >= ELEVATED:
        out.append(f"Unusual hour of day ({int(hour):02d}:{int((hour % 1) * 60):02d} IST)")
    if r.M >= ELEVATED:
        out.append("Feature combination unusual vs. baseline (Isolation Forest)"
                   + (f"; driven by {', '.join(top_features[:2])}" if top_features else ""))
    out += r.caps_applied
    return out
