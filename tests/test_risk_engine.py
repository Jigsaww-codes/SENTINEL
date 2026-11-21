import pytest
import risk_engine as r
from config import DetectionSettings
from schemas import RiskLevel

S = DetectionSettings()


def test_weighted_formula_exact():
    res = r.compute_risk(100, 100, 100, 100, 100, S)
    assert res.raw_total == 100
    res = r.compute_risk(80, 60, 40, 20, 50, S)
    assert res.raw_total == pytest.approx(0.25*80 + 0.20*60 + 0.20*40 + 0.15*20 + 0.20*50)


def test_levels_boundaries():
    assert r.level_for(39.9, S) == RiskLevel.NORMAL
    assert r.level_for(40, S) == RiskLevel.REVIEW_REQUIRED
    assert r.level_for(69.9, S) == RiskLevel.REVIEW_REQUIRED
    assert r.level_for(70, S) == RiskLevel.HIGH_PRIORITY


def test_stationary_duration_alone_never_alerts():
    res = r.compute_risk(100, 0, 0, 0, 0, S)
    assert res.level == RiskLevel.NORMAL


def test_stationary_plus_night_in_populated_area_is_normal():
    res = r.compute_risk(100, 0, 0, 100, 40, S)      # raw 54 but no isolation/anomaly
    assert res.raw_total >= 40 and res.level == RiskLevel.NORMAL and res.caps_applied


def test_incident_history_alone_cannot_be_high_or_even_review():
    res = r.compute_risk(100, 0, 100, 100, 40, S)
    assert res.level == RiskLevel.NORMAL


def test_single_primary_indicator_cannot_be_high():
    res = r.compute_risk(100, 100, 0, 100, 40, S)    # raw 76 but only isolation elevated
    assert res.level == RiskLevel.REVIEW_REQUIRED and res.total <= 69


def test_two_indicators_allow_high():
    res = r.compute_risk(100, 100, 100, 100, 100, S)
    assert res.level == RiskLevel.HIGH_PRIORITY


def test_inputs_clamped_and_time_score_shape():
    assert r.compute_risk(500, -5, 0, 0, 0, S).S == 100
    assert r.time_score(2) == 100 and r.time_score(14) == 0
    assert r.time_score(23.5) > r.time_score(20) > r.time_score(15)
    assert r.stationary_score(29, 30) == 0 and r.stationary_score(90, 30) == 100
