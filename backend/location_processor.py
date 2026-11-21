"""Haversine distance, movement history, stationary duration, update validation."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt
from typing import List, Optional, Tuple

EARTH_RADIUS_M = 6371008.8
MAX_PLAUSIBLE_SPEED_MS = 70.0      # ~250 km/h: faster implies a GNSS glitch / teleport
IST = timedelta(hours=5, minutes=30)


class LocationValidationError(ValueError):
    pass


@dataclass
class Fix:
    """One position fix. `ts` is naive UTC."""
    lat: float
    lon: float
    ts: datetime
    accuracy: Optional[float] = None
    source: str = "GNSS"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    dphi, dlmb = p2 - p1, radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def validate_update(prev: Optional[Fix], new: Fix) -> None:
    """Raises LocationValidationError for out-of-order or physically implausible updates."""
    if prev is None:
        return
    if new.ts <= prev.ts:
        raise LocationValidationError("Out-of-order or duplicate timestamp")
    dt = (new.ts - prev.ts).total_seconds()
    speed = haversine_m(prev.lat, prev.lon, new.lat, new.lon) / dt
    if speed > MAX_PLAUSIBLE_SPEED_MS:
        raise LocationValidationError(f"Implausible speed {speed:.0f} m/s between updates")


def stationary_minutes(history: List[Fix], radius_m: float) -> float:
    """Minutes the device has stayed within `radius_m` of its latest position (history ascending)."""
    if len(history) < 2:
        return 0.0
    latest = history[-1]
    earliest = latest
    for fx in reversed(history[:-1]):
        if haversine_m(fx.lat, fx.lon, latest.lat, latest.lon) <= radius_m:
            earliest = fx
        else:
            break
    return (latest.ts - earliest.ts).total_seconds() / 60.0


def movement_features(history: List[Fix], window_min: float = 60.0, step_move_m: float = 10.0) -> dict:
    """movement_frequency: share of recent consecutive updates showing real displacement (0-1)."""
    if len(history) < 2:
        return {"movement_frequency": 0.0, "mean_speed_ms": 0.0, "n_updates": len(history)}
    cutoff = history[-1].ts - timedelta(minutes=window_min)
    recent = [f for f in history if f.ts >= cutoff] or history[-2:]
    moves, speeds = 0, []
    for a, b in zip(recent, recent[1:]):
        d = haversine_m(a.lat, a.lon, b.lat, b.lon)
        dt = max((b.ts - a.ts).total_seconds(), 1)
        speeds.append(d / dt)
        moves += d > step_move_m
    n = max(len(recent) - 1, 1)
    return {"movement_frequency": moves / n, "mean_speed_ms": sum(speeds) / len(speeds), "n_updates": len(recent)}


def local_hour(ts_utc: datetime) -> float:
    """Local (IST) decimal hour for a naive-UTC timestamp."""
    t = ts_utc + IST
    return t.hour + t.minute / 60.0
