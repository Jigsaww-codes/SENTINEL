from datetime import timedelta
from fastapi.testclient import TestClient
from main import app
from helpers import utc, SCENARIOS

PAYLOAD = {"device_id": "DEV-T-01", "latitude": 23.26, "longitude": 77.41,
           "timestamp": "2026-11-21T10:00:00Z", "accuracy": 5, "source": "NAVIC"}


def feed(c, device, key, step=5):
    sc, out = SCENARIOS[key], []
    for i in range(0, sc["minutes"] + 1, step):
        j = 0.00004 * ((i // step) % 3)
        body = {"device_id": device, "latitude": sc["lat"] + j + (0.0006 * (i // step) if sc.get("move") else 0),
                "longitude": sc["lon"] + j, "source": "SIMULATED",
                "timestamp": (sc["start"] + timedelta(minutes=i)).isoformat() + "Z"}
        out.append(c.post("/api/location", json=body).json())
    return out


def test_health_and_docs():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "ok"
        assert c.get("/docs").status_code == 200


def test_location_duplicate_validation_consent():
    with TestClient(app) as c:
        assert c.post("/api/location", json=PAYLOAD).json()["accepted"] is True
        assert c.post("/api/location", json=PAYLOAD).json()["duplicate"] is True
        assert c.post("/api/location", json={**PAYLOAD, "latitude": 999}).status_code == 422
        assert c.post("/api/location", json={**PAYLOAD, "consent": False,
                                             "timestamp": "2026-11-21T10:06:00Z"}).status_code == 403
        old = {**PAYLOAD, "timestamp": "2026-11-21T09:00:00Z"}          # out of order
        assert c.post("/api/location", json=old).status_code == 422


def test_four_scenarios_end_to_end():
    with TestClient(app) as c, c.websocket_connect("/ws/alerts") as ws:
        assert ws.receive_json()["type"] == "hello"
        for dev, key in (("DEV-A", "A"), ("DEV-B", "B"), ("DEV-C", "C"), ("DEV-D", "D")):
            feed(c, dev, key)
        alerts = {a["device_id"]: a for a in c.get("/api/alerts").json()}
        assert set(alerts) == {"DEV-C", "DEV-D"}                         # A and B raise nothing
        assert alerts["DEV-C"]["risk_level"] == "REVIEW_REQUIRED"
        assert alerts["DEV-D"]["risk_level"] == "HIGH_PRIORITY_VERIFICATION"
        assert len(c.get("/api/alerts").json()) == 2                      # duplicate prevention: one per situation
        assert alerts["DEV-D"]["breakdown"]["contributions"] and alerts["DEV-D"]["reasons"]
        devs = {d["device_id"]: d for d in c.get("/api/devices").json()}
        assert devs["DEV-B"]["risk_level"] == "NORMAL" and devs["DEV-D"]["risk_score"] >= 70
        types = []
        while True:   # websocket received alert events live
            try:
                types.append(ws.receive_json()["type"])
            except Exception:
                break
            if "alert_created" in types and types.count("alert_created") == 2:
                break
        assert types.count("alert_created") == 2


def test_alert_review_workflow_and_no_reraise():
    with TestClient(app) as c:
        feed(c, "DEV-D2", "D")
        a = next(x for x in c.get("/api/alerts").json() if x["device_id"] == "DEV-D2")
        r = c.patch(f"/api/alerts/{a['alert_id']}", json={"status": "UNDER_REVIEW", "note": "calling contact",
                                                         "welfare_check_considered": True})
        assert r.json()["status"] == "UNDER_REVIEW" and r.json()["welfare_check_considered"] is True
        c.patch(f"/api/alerts/{a['alert_id']}", json={"status": "DISMISSED"})
        n = len(c.get("/api/alerts").json())
        sc = SCENARIOS["D"]
        last = sc["start"] + timedelta(minutes=sc["minutes"] + 5)
        c.post("/api/location", json={"device_id": "DEV-D2", "latitude": sc["lat"], "longitude": sc["lon"],
                                      "timestamp": last.isoformat() + "Z"})
        assert len(c.get("/api/alerts").json()) == n                      # dismissed -> not re-raised
        assert c.patch(f"/api/alerts/{a['alert_id']}", json={"status": "BOGUS"}).status_code == 422


def test_endpoints_shape():
    with TestClient(app) as c:
        assert c.get("/api/alerts/99999").status_code == 404
        s = c.get("/api/statistics").json()
        assert "participating_devices" in s and "risk_distribution" in s
        z = c.get("/api/zones").json()
        assert z["type"] == "FeatureCollection" and len(z["features"]) >= 8
        assert c.get("/api/analytics").json()["model"]["status"] == "trained"
        assert c.get("/api/connectivity").json()["satellite_fallback"]["simulated"] is True
