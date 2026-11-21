import pytest
from datetime import timedelta
import location_processor as lp
from helpers import history, utc


def test_haversine_known_distances():
    assert lp.haversine_m(23.0, 77.0, 23.0, 77.0) == 0
    assert lp.haversine_m(0, 0, 1, 0) == pytest.approx(111195, rel=1e-3)       # 1 deg latitude
    # 0.01 deg longitude at 23.26N ~ 1.0227 km
    assert lp.haversine_m(23.2599, 77.4126, 23.2599, 77.4226) == pytest.approx(1022.5, rel=5e-3)
    # symmetry
    a = lp.haversine_m(23.26, 77.41, 23.10, 77.39)
    assert a == pytest.approx(lp.haversine_m(23.10, 77.39, 23.26, 77.41))


def test_stationary_duration_with_jitter():
    h = history(23.1250, 77.3350, utc(22), 60)
    assert lp.stationary_minutes(h, 30) == pytest.approx(60)


def test_moving_device_not_stationary():
    h = history(23.23, 77.43, utc(11), 60, move=True)
    assert lp.stationary_minutes(h, 30) == 0


def test_stationary_resets_after_departure():
    h = history(23.1250, 77.3350, utc(22), 30)
    h.append(lp.Fix(23.1350, 77.3450, h[-1].ts + timedelta(minutes=5)))   # moved ~1.5 km
    h += [lp.Fix(23.1350, 77.3450, h[-1].ts + timedelta(minutes=5 * i)) for i in (1, 2)]
    assert lp.stationary_minutes(h, 30) == pytest.approx(10)


def test_validation_rejects_out_of_order_and_teleport():
    a = lp.Fix(23.0, 77.0, utc(10))
    with pytest.raises(lp.LocationValidationError):
        lp.validate_update(a, lp.Fix(23.0, 77.0, utc(10)))
    with pytest.raises(lp.LocationValidationError):
        lp.validate_update(a, lp.Fix(24.0, 77.0, utc(10) + timedelta(seconds=30)))   # ~111 km in 30 s
    lp.validate_update(a, lp.Fix(23.001, 77.0, utc(10) + timedelta(minutes=2)))      # fine


def test_local_hour_is_ist():
    assert lp.local_hour(utc(2, 30)) == pytest.approx(2.5)
