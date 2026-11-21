"""Isolation Forest anomaly detection (scikit-learn) over six features, trained on SYNTHETIC baseline data.

Features: stationary_minutes, movement_frequency, isolation_score, road_distance_m,
          incident_score, time_score.
Output: anomaly score 0-100 (the 'M' input of the risk engine) + per-feature contributions
(occlusion: how much the score drops when that feature is replaced by the baseline median)."""
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ["stationary_minutes", "movement_frequency", "isolation_score",
            "road_distance_m", "incident_score", "time_score"]
MIN_TRAIN_ROWS = 50


def synthetic_baseline(n: int = 2000, seed: int = 7) -> pd.DataFrame:
    """Plausible everyday behaviour. Long dwell in populated areas (home/work) at any hour is NORMAL;
    long dwell in remote, road-poor, high-context places is rare, so it isolates easily."""
    rng = np.random.default_rng(seed)
    rows = []
    def add(k, stat, mov, iso, road, inc, tim):
        for _ in range(k):
            rows.append([stat(), mov(), iso(), road(), inc(), tim()])
    day = lambda: float(np.clip(rng.normal(25, 25), 0, 100))
    anyt = lambda: float(rng.uniform(0, 100))
    # commuting / moving, populated
    add(int(n * .50), lambda: rng.exponential(6), lambda: rng.uniform(.5, 1), lambda: rng.beta(1.5, 8) * 40,
        lambda: rng.exponential(120), lambda: rng.beta(1, 6) * 60, day)
    # dwelling in populated places (home, work, cafe), any time
    add(int(n * .32), lambda: rng.uniform(30, 600), lambda: rng.uniform(0, .12), lambda: rng.beta(1.5, 8) * 40,
        lambda: rng.exponential(150), lambda: rng.beta(1, 6) * 60, anyt)
    # legitimate rural travel / short stops on outskirts
    add(int(n * .15), lambda: rng.uniform(0, 45), lambda: rng.uniform(.3, 1), lambda: rng.uniform(35, 80),
        lambda: rng.uniform(100, 1000), lambda: rng.beta(1, 8) * 40, day)
    # rare remote long-dwell outliers (keep model aware that such points are sparse)
    add(int(n * .03), lambda: rng.uniform(30, 240), lambda: rng.uniform(0, .1), lambda: rng.uniform(60, 100),
        lambda: rng.uniform(300, 2500), lambda: rng.uniform(0, 100), anyt)
    return pd.DataFrame(rows, columns=FEATURES)


class AnomalyDetector:
    def __init__(self, n_estimators: int = 200, contamination: float = 0.03, seed: int = 42):
        self.model = IsolationForest(n_estimators=n_estimators, contamination=contamination,
                                     random_state=seed)
        self.trained = False
        self.train_rows = 0
        self.medians: Dict[str, float] = {}
        self.r_lo = self.r_hi = 0.0

    def fit(self, df: pd.DataFrame | None = None):
        """Works on any dataset size: too-small inputs are topped up with the synthetic baseline."""
        if df is None or len(df) < MIN_TRAIN_ROWS:
            base = synthetic_baseline(500)
            df = base if df is None else pd.concat([df[FEATURES], base], ignore_index=True)
        X = df[FEATURES].astype(float)
        self.model.set_params(max_samples=min(256, len(X)))
        self.model.fit(X.values)
        raw = -self.model.score_samples(X.values)
        self.r_lo = float(np.median(raw))
        self.r_hi = float(np.percentile(raw, 99.5))
        self.medians = X.median().to_dict()
        self.train_rows = len(X)
        self.trained = True
        return self

    def fit_synthetic(self):
        return self.fit(synthetic_baseline())

    def _anomaly(self, vec: List[float]) -> float:
        raw = float(-self.model.score_samples(np.array([vec]))[0])
        return float(np.clip(100 * (raw - self.r_lo) / (self.r_hi - self.r_lo + 1e-9), 0, 100))

    def score(self, feats: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        if not self.trained:
            self.fit_synthetic()
        vec = [float(feats[f]) for f in FEATURES]
        full = self._anomaly(vec)
        drops = {}
        for i, f in enumerate(FEATURES):
            alt = list(vec); alt[i] = self.medians[f]
            drops[f] = max(0.0, full - self._anomaly(alt))
        tot = sum(drops.values())
        contrib = {f: round(100 * v / tot, 1) if tot > 0 else 0.0 for f, v in drops.items()}
        return round(full, 1), contrib

    def info(self) -> dict:
        return {"name": "IsolationForest (scikit-learn)", "status": "trained" if self.trained else "untrained",
                "n_estimators": self.model.n_estimators, "contamination": self.model.contamination,
                "training_rows": self.train_rows, "training_data": "SYNTHETIC baseline", "features": FEATURES}


detector = AnomalyDetector()
