"""Location ingestion -> analysis -> alert lifecycle. Alerts are decision support only:
creating one never dispatches anyone; a human reviewer must verify via PATCH /api/alerts/{id}."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import location_processor as lp
import pipeline
from connectivity import sim_link
from config import settings
from models import Alert, DeviceLocation, DeviceSession
from schemas import AlertOut, LocationResult, LocationUpdate, RiskLevel

OPEN_STATUSES = ("NEW", "ACKNOWLEDGED", "UNDER_REVIEW")
CLOSED_STATUSES = ("DISMISSED", "RESOLVED")
SAME_PLACE_M = 100.0           # alerts within this distance for the same device are one situation
HISTORY_HOURS = 6
RANK = {RiskLevel.NORMAL.value: 0, RiskLevel.REVIEW_REQUIRED.value: 1, RiskLevel.HIGH_PRIORITY.value: 2}

# Latest analysis per device (feeds GET /api/devices); rebuilt as updates arrive.
latest_state: Dict[str, dict] = {}


def list_alerts(db: Session, status: str | None = None):
    q = db.query(Alert).order_by(Alert.created_at.desc())
    if status:
        q = q.filter(Alert.status == status)
    return q.all()


def _naive_utc(ts: datetime) -> datetime:
    return ts.replace(tzinfo=None) if ts.tzinfo is None else ts.astimezone(timezone.utc).replace(tzinfo=None)


def _history(db: Session, device_id: str) -> List[lp.Fix]:
    rows = (db.query(DeviceLocation).filter_by(device_id=device_id)
            .order_by(DeviceLocation.timestamp.desc()).limit(500).all())
    return [lp.Fix(r.latitude, r.longitude, r.timestamp, r.accuracy, r.source) for r in reversed(rows)]


def process_location(db: Session, u: LocationUpdate) -> Tuple[LocationResult, List[Tuple[str, dict]]]:
    """Returns (result, events-to-broadcast). Raises lp.LocationValidationError for bad sequences."""
    events: List[Tuple[str, dict]] = []
    ts = _naive_utc(u.timestamp)
    session = db.get(DeviceSession, u.device_id)
    if session is None:
        session = DeviceSession(device_id=u.device_id, consent_status=True)
        db.add(session)
        db.flush()
    prior = _history(db, u.device_id)
    new_fix = lp.Fix(u.latitude, u.longitude, ts, u.accuracy, u.source.value)
    if any(f.ts == ts for f in prior):
        return LocationResult(accepted=False, duplicate=True, device_id=u.device_id,
                              message="Duplicate event ignored"), events
    lp.validate_update(prior[-1] if prior else None, new_fix)
    db.add(DeviceLocation(device_id=u.device_id, latitude=u.latitude, longitude=u.longitude,
                          timestamp=ts, accuracy=u.accuracy, source=u.source.value))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return LocationResult(accepted=False, duplicate=True, device_id=u.device_id,
                              message="Duplicate event ignored"), events

    cutoff = ts - timedelta(hours=HISTORY_HOURS)
    hist = [f for f in prior if f.ts >= cutoff] + [new_fix]
    a = pipeline.analyse(hist, settings)
    alert_id = None
    if a.evaluated and a.risk_level != RiskLevel.NORMAL:
        alert, ev = _upsert_alert(db, u, a, ts)
        alert_id = alert.alert_id if alert else None
        if ev:
            events.append(ev)
    db.commit()

    latest_state[u.device_id] = {"stationary_minutes": round(a.stationary_minutes, 1),
                                 "risk_score": a.risk_score, "risk_level": a.risk_level.value,
                                 "reasons": a.reasons, "breakdown": a.breakdown, "geo": a.geo,
                                 "anomaly_score": a.anomaly_score, "feature_contributions": a.feature_contributions,
                                 "source": u.source.value, "accuracy": u.accuracy}
    events.append(("device_update", {"device_id": u.device_id, "latitude": u.latitude,
                                     "longitude": u.longitude, "timestamp": ts.isoformat(),
                                     **{k: latest_state[u.device_id][k] for k in
                                        ("stationary_minutes", "risk_score", "risk_level")}}))
    return LocationResult(accepted=True, device_id=u.device_id,
                          stationary_minutes=round(a.stationary_minutes, 1), risk_score=a.risk_score,
                          risk_level=a.risk_level.value, alert_id=alert_id,
                          message="Processed" if a.evaluated else a.reasons[0]), events


def _upsert_alert(db: Session, u: LocationUpdate, a: pipeline.Analysis, ts: datetime):
    """One alert per device per situation. Escalations update it; reviewed ones aren't re-raised."""
    q = db.query(Alert).filter_by(device_id=u.device_id).order_by(Alert.created_at.desc())
    near = lambda al: lp.haversine_m(al.latitude, al.longitude, u.latitude, u.longitude) <= SAME_PLACE_M
    existing = next((al for al in q.all() if near(al)), None)
    if existing:
        if existing.status in CLOSED_STATUSES:
            return existing, None                      # human already decided; don't re-raise
        prev_level, prev_score = existing.risk_level, existing.risk_score
        existing.stationary_minutes = round(a.stationary_minutes, 1)      # evidence always stays current
        existing.risk_score, existing.risk_level = a.risk_score, a.risk_level.value
        existing.reasons, existing.breakdown = a.reasons, a.breakdown
        escalated = RANK[a.risk_level.value] > RANK[prev_level]
        if escalated or abs(a.risk_score - prev_score) >= 5:               # broadcast only meaningful change
            return existing, ("alert_updated", {**AlertOut.model_validate(existing).model_dump(mode="json"),
                                                "escalated": escalated})
        return existing, None
    al = Alert(device_id=u.device_id, latitude=round(u.latitude, 4), longitude=round(u.longitude, 4),
               risk_score=a.risk_score, risk_level=a.risk_level.value, reasons=a.reasons,
               status="NEW", created_at=ts, stationary_minutes=round(a.stationary_minutes, 1),
               breakdown=a.breakdown)
    db.add(al)
    db.flush()
    out = AlertOut.model_validate(al).model_dump(mode="json")
    sim_link.enqueue(out)      # compact emergency packet: network now, or queued for (simulated) satellite
    return al, ("alert_created", out)
