import pandas as pd
import detection as d
import pipeline
from config import DetectionSettings
from schemas import RiskLevel
from helpers import history, SCENARIOS

S = DetectionSettings()
d.detector.fit_synthetic()


def run(key):
    return pipeline.analyse(history(**SCENARIOS[key]), S)


def test_model_trains_on_tiny_dataset():
    tiny = pd.DataFrame([[40, .05, 10, 100, 5, 20]] * 3, columns=d.FEATURES)
    m = d.AnomalyDetector().fit(tiny)
    score, contrib = m.score(dict(zip(d.FEATURES, [40, .05, 10, 100, 5, 20])))
    assert 0 <= score <= 100 and m.trained


def test_isolated_long_dwell_scores_more_anomalous_than_populated():
    pop, _ = d.detector.score(dict(stationary_minutes=60, movement_frequency=0, isolation_score=5,
                                   road_distance_m=80, incident_score=0, time_score=10))
    iso, contrib = d.detector.score(dict(stationary_minutes=60, movement_frequency=0, isolation_score=100,
                                         road_distance_m=2500, incident_score=90, time_score=85))
    assert iso > pop + 40
    assert abs(sum(contrib.values()) - 100) < 1.5


def test_scenario_A_moving_is_not_evaluated():
    a = run("A")
    assert not a.evaluated and a.risk_level == RiskLevel.NORMAL and a.risk_score == 0


def test_scenario_B_stationary_populated_is_normal():
    a = run("B")
    assert a.evaluated and a.risk_level == RiskLevel.NORMAL and a.breakdown["I"] < 20


def test_scenario_C_isolated_needs_review_but_not_high():
    a = run("C")
    assert a.risk_level == RiskLevel.REVIEW_REQUIRED and a.breakdown["I"] >= 80 and a.breakdown["C"] < 10


def test_scenario_D_isolated_with_incident_context_is_high():
    a = run("D")
    assert a.risk_level == RiskLevel.HIGH_PRIORITY and a.breakdown["C"] >= 80
    assert any("incident-context" in r for r in a.reasons) and any("km from nearest" in r for r in a.reasons)


def test_ordering_B_lt_C_lt_D():
    assert run("B").risk_score < run("C").risk_score < run("D").risk_score


def test_night_at_home_in_populated_area_is_not_flagged():
    from helpers import utc
    a = pipeline.analyse(history(23.2120, 77.4330, utc(1), 120), S)
    assert a.risk_level == RiskLevel.NORMAL and a.breakdown["T"] > 90
