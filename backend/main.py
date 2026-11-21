"""SENTINEL API. Run: uvicorn main:app --reload --port 8000   (docs at /docs)"""
import asyncio
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import alerts as alert_svc
import detection
import geo_analysis
import location_processor as lp
from connectivity import sim_link
from pydantic import BaseModel, Field
import validation
from simulation import engine
from config import CORS_ORIGINS, settings
from database import get_db, init_db
from models import Alert, DeviceLocation, DeviceSession, GeographicalZone
from schemas import (AlertOut, AlertStatus, AlertStatusUpdate, DeviceOut, LocationResult,
                     LocationUpdate, StatisticsOut)
from websocket_manager import manager

START_TIME = datetime.now(timezone.utc)


def _seed_zones():
    from database import SessionLocal
    with SessionLocal() as db:
        if db.query(GeographicalZone).count() == 0:
            db.add_all(GeographicalZone(**r) for r in geo_analysis.zone_records())
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_zones()
    detection.detector.fit_synthetic()
    worker = asyncio.create_task(sim_link.worker())
    yield
    worker.cancel()


app = FastAPI(
    title="SENTINEL API",
    description="Satellite-Enabled AI Surveillance and Emergency Location Intelligence System. "
                "Decision-support only: every alert requires human verification; no automated dispatch.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health", tags=["system"], summary="Backend health")
def health():
    return {"status": "ok", "version": app.version,
            "uptime_s": (datetime.now(timezone.utc) - START_TIME).total_seconds(),
            "settings": settings.as_dict()}


@app.post("/api/location", response_model=LocationResult, tags=["ingest"],
          summary="Receive a consent-based location update and run the detection pipeline")
async def post_location(update: LocationUpdate, db: Session = Depends(get_db)):
    if not update.consent:
        raise HTTPException(403, "Device has not consented to location sharing")
    try:
        result, events = alert_svc.process_location(db, update)
    except lp.LocationValidationError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    for etype, data in events:
        await manager.broadcast(etype, data)
    return result


@app.get("/api/devices", response_model=list[DeviceOut], tags=["devices"])
def get_devices(db: Session = Depends(get_db)):
    out = []
    for s in db.query(DeviceSession).all():
        last = (db.query(DeviceLocation).filter_by(device_id=s.device_id)
                .order_by(DeviceLocation.timestamp.desc()).first())
        if last:
            out.append(DeviceOut(device_id=s.device_id, latitude=last.latitude,
                                 longitude=last.longitude, timestamp=last.timestamp,
                                 accuracy=last.accuracy, source=last.source,
                                 consent=s.consent_status,
                                 reasons=alert_svc.latest_state.get(s.device_id, {}).get("reasons", []),
                                 breakdown=alert_svc.latest_state.get(s.device_id, {}).get("breakdown") or None,
                                 **{k: alert_svc.latest_state.get(s.device_id, {}).get(k, d)
                                    for k, d in (("stationary_minutes", 0), ("risk_score", 0),
                                                 ("risk_level", "NORMAL"))}))
    return out


@app.get("/api/alerts", response_model=list[AlertOut], tags=["alerts"])
def get_alerts(status: AlertStatus | None = None, db: Session = Depends(get_db)):
    return alert_svc.list_alerts(db, status.value if status else None)


@app.get("/api/alerts/{alert_id}", response_model=AlertOut, tags=["alerts"])
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    return a


@app.patch("/api/alerts/{alert_id}", response_model=AlertOut, tags=["alerts"],
           summary="Human reviewer updates verification status")
async def patch_alert(alert_id: int, body: AlertStatusUpdate, db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(404, "Alert not found")
    a.status = body.status.value
    if body.note is not None:
        a.response_note = body.note
    if body.welfare_check_considered is not None:
        a.welfare_check_considered = body.welfare_check_considered
    db.commit()
    await manager.broadcast("alert_updated", AlertOut.model_validate(a).model_dump(mode="json"))
    return a


def _geo_bucket(a) -> str:
    b = a.breakdown or {}
    iso, inc = (b.get("I", 0) >= 50), (b.get("C", 0) >= 50)
    return "Isolated + incident context" if iso and inc else "Isolated" if iso else "Incident context" if inc else "Populated / other"


def _anomaly_stats() -> dict:
    st = [v for v in alert_svc.latest_state.values()]
    ev = [v["breakdown"]["M"] for v in st if v.get("breakdown")]
    return {"devices_tracked": len(st), "devices_evaluated": len(ev),
            "devices_flagged": sum(v["risk_level"] != "NORMAL" for v in st),
            "mean_anomaly_score": round(sum(ev) / len(ev), 1) if ev else 0}


@app.get("/api/statistics", response_model=StatisticsOut, tags=["dashboard"])
def statistics(db: Session = Depends(get_db)):
    al = db.query(Alert).all()
    trend = Counter(a.created_at.strftime("%H:%M") for a in al)
    return StatisticsOut(
        participating_devices=db.query(DeviceSession).count(),
        unusual_stationary_patterns=len(al),
        pending_alerts=sum(a.status in ("NEW", "ACKNOWLEDGED", "UNDER_REVIEW") for a in al),
        high_priority_alerts=sum(a.risk_level == "HIGH_PRIORITY_VERIFICATION" for a in al),
        resolved_alerts=sum(a.status == "RESOLVED" for a in al),
        alert_trend=[{"time": k, "alerts": v} for k, v in sorted(trend.items())],
        risk_distribution=dict(Counter(a.risk_level for a in al)),
        geo_distribution=dict(Counter(_geo_bucket(a) for a in al)),
        anomaly_stats=_anomaly_stats(),
    )


@app.get("/api/zones", tags=["geo"], summary="Geographical context zones (GeoJSON features)")
def zones(db: Session = Depends(get_db)):
    feats = [{"type": "Feature", "geometry": z.geometry,
              "properties": {"zone_id": z.zone_id, "zone_type": z.zone_type,
                             "name": z.name, "context_score": z.context_score}}
             for z in db.query(GeographicalZone).all()]
    return {"type": "FeatureCollection", "features": feats}


@app.get("/api/analytics", tags=["ai"], summary="AI model status, feature contributions, false-positive tests")
def analytics():
    st = alert_svc.latest_state
    ev = [v for v in st.values() if v.get("feature_contributions")]
    feats = sorted({f for v in ev for f in v["feature_contributions"]})
    avg = [{"feature": f, "contribution_pct": round(sum(v["feature_contributions"][f] for v in ev) / len(ev), 1)}
           for f in feats] if ev else []
    return {"model": detection.detector.info(), "settings": settings.as_dict(),
            "anomalies": sum(v["risk_level"] != "NORMAL" for v in st.values()),
            "feature_contributions": sorted(avg, key=lambda x: -x["contribution_pct"]),
            "latest_by_device": {d: {k: v.get(k) for k in ("risk_score", "risk_level", "breakdown", "reasons",
                                                           "anomaly_score", "feature_contributions")}
                                 for d, v in st.items()},
            "false_positive_tests": validation.run_suite(settings)}


@app.get("/api/connectivity", tags=["space"], summary="GNSS/NavIC metadata + network + satellite fallback (SIMULATED)")
def connectivity():
    src, acc = Counter(), []
    for v in alert_svc.latest_state.values():
        src[v.get("source", "GNSS")] += 1
        if v.get("accuracy") is not None:
            acc.append(v["accuracy"])
    return sim_link.snapshot(dict(src), round(sum(acc) / len(acc), 1) if acc else None)


class NetworkMode(BaseModel):
    status: str = Field(..., pattern="^(ONLINE|OFFLINE)$")


@app.post("/api/connectivity/network", tags=["space"], summary="Simulate a cellular outage (OFFLINE) or restore it")
async def set_network(body: NetworkMode):
    sim_link.set_mode(body.status)
    await manager.broadcast("connectivity", {"network": body.status})
    return connectivity()


class SettingsIn(BaseModel):
    stationary_radius_m: float = Field(..., ge=5, le=500)
    stationary_duration_min: float = Field(..., ge=1, le=600)
    review_threshold: float = Field(..., ge=1, le=99)
    high_threshold: float = Field(..., ge=2, le=100)


@app.get("/api/settings", tags=["system"])
def get_settings():
    return settings.as_dict()


@app.put("/api/settings", tags=["system"], summary="Change detection thresholds at runtime")
def put_settings(body: SettingsIn):
    if body.high_threshold <= body.review_threshold:
        raise HTTPException(422, "High-priority threshold must be above the review threshold")
    for k, v in body.model_dump().items():
        setattr(settings, k, v)
    return settings.as_dict()


@app.post("/api/simulation/start", tags=["simulation"],
          summary="Start the 4-device demo (resets previous demo data first, so it is repeatable)")
async def sim_start():
    return await engine.start()


@app.post("/api/simulation/stop", tags=["simulation"], summary="Stop the running simulation")
async def sim_stop():
    return await engine.stop()


@app.post("/api/simulation/reset", tags=["simulation"], summary="Reset Demo: clear devices, locations and alerts")
async def sim_reset():
    return await engine.reset()


@app.get("/api/simulation/status", tags=["simulation"])
def sim_status():
    return engine.status()


@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_json({"type": "hello", "data": {"message": "SENTINEL alert stream connected"}})
        while True:
            await ws.receive_text()   # keep-alive; clients don't send commands
    except WebSocketDisconnect:
        manager.disconnect(ws)
