"""Pure analysis pipeline: list[Fix] -> Analysis. DB / alert logic wraps this in alerts.py."""
from dataclasses import dataclass, field
from typing import List

import detection
import geo_analysis
import location_processor as lp
import risk_engine as re_
from config import DetectionSettings
from schemas import RiskLevel


@dataclass
class Analysis:
    stationary_minutes: float
    evaluated: bool                 # False when below the stationary threshold
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.NORMAL
    reasons: List[str] = field(default_factory=list)
    breakdown: dict = field(default_factory=dict)
    geo: dict = field(default_factory=dict)
    anomaly_score: float = 0.0
    feature_contributions: dict = field(default_factory=dict)


def analyse(history: List[lp.Fix], s: DetectionSettings) -> Analysis:
    latest = history[-1]
    minutes = lp.stationary_minutes(history, s.stationary_radius_m)
    if minutes < s.stationary_duration_min:
        return Analysis(minutes, False, reasons=[f"Not stationary long enough ({minutes:.0f} of "
                                                 f"{s.stationary_duration_min:.0f} min) or moving"])
    geo = geo_analysis.analyse(latest.lat, latest.lon, latest.ts)
    hour = lp.local_hour(latest.ts)
    T = re_.time_score(hour)
    mv = lp.movement_features(history)
    feats = {"stationary_minutes": minutes, "movement_frequency": mv["movement_frequency"],
             "isolation_score": geo.isolation_score, "road_distance_m": geo.road_distance_m,
             "incident_score": geo.incident_score, "time_score": T}
    M, contrib = detection.detector.score(feats)
    S = re_.stationary_score(minutes, s.stationary_duration_min)
    risk = re_.compute_risk(S, geo.isolation_score, geo.incident_score, T, M, s)
    top = [k for k, v in sorted(contrib.items(), key=lambda kv: -kv[1]) if v > 0]
    return Analysis(minutes, True, risk.total, risk.level,
                    re_.build_reasons(minutes, s.stationary_radius_m, geo, hour, risk, top),
                    risk.as_dict(), geo.__dict__, M, contrib)
