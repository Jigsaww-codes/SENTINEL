import time
from fastapi.testclient import TestClient
import simulation
from main import app

simulation.TICK_REAL_S = 0.02     # fast-forward for tests


def wait_done(c, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = c.get("/api/simulation/status").json()
        if st["state"] == "completed":
            return st
        time.sleep(0.1)
    raise AssertionError("simulation did not finish")


def summary(c):
    return {a["device_id"]: a["risk_level"] for a in c.get("/api/alerts").json()}


def test_full_demo_runs_twice_and_streams_events():
    with TestClient(app) as c:
        with c.websocket_connect("/ws/alerts") as ws:
            ws.receive_json()                                   # hello
            assert c.post("/api/simulation/start").json()["running"] is True
            seen = set()
            while "alert_created" not in seen or "simulation_status" not in seen:
                seen.add(ws.receive_json()["type"])
            wait_done(c)
        assert summary(c) == {"DEV-C3": "REVIEW_REQUIRED", "DEV-D4": "HIGH_PRIORITY_VERIFICATION"}
        devs = {d["device_id"]: d for d in c.get("/api/devices").json()}
        assert len(devs) == 4
        assert devs["DEV-A1"]["stationary_minutes"] == 0
        assert devs["DEV-B2"]["stationary_minutes"] >= 60 and devs["DEV-B2"]["risk_level"] == "NORMAL"
        assert devs["DEV-D4"]["reasons"] and devs["DEV-D4"]["breakdown"]["C"] >= 80
        # second run, no manual reset: start() resets demo data itself
        c.post("/api/simulation/start")
        wait_done(c)
        assert summary(c) == {"DEV-C3": "REVIEW_REQUIRED", "DEV-D4": "HIGH_PRIORITY_VERIFICATION"}
        assert len(c.get("/api/alerts").json()) == 2             # no duplicates across runs


def test_stop_and_reset():
    with TestClient(app) as c:
        simulation.TICK_REAL_S = 0.3
        c.post("/api/simulation/start")
        time.sleep(0.5)
        assert c.post("/api/simulation/stop").json()["state"] == "stopped"
        simulation.TICK_REAL_S = 0.02
        r = c.post("/api/simulation/reset").json()
        assert r["state"] == "idle"
        assert c.get("/api/devices").json() == [] and c.get("/api/alerts").json() == []
        assert c.get("/api/statistics").json()["participating_devices"] == 0
