import time
from fastapi.testclient import TestClient
from config import settings
import connectivity as cn
import validation
from main import app
from tests_util import fresh_link  # noqa

ALERT = {"alert_id": 1, "device_id": "DEV-D4", "latitude": 23.105, "longitude": 77.39,
         "risk_level": "HIGH_PRIORITY_VERIFICATION", "risk_score": 85.7}


def force_visibility(link, visible):
    # place the monotonic clock inside / outside the simulated pass window
    period = cn.PASS_PERIOD_S
    link._t0 = time.monotonic() - (period * 0.25 if visible else period * 0.75)


def test_packet_is_compact():
    link = fresh_link()
    p = link.enqueue(ALERT)
    assert p.size_bytes <= cn.MAX_PACKET_BYTES and p.payload.startswith("SNT|DEV-D4|23.1050|77.3900|H|85")


def test_online_delivers_over_network_not_satellite():
    link = fresh_link()
    p = link.enqueue(ALERT)
    assert p.channel == "NETWORK" and p.status == "DELIVERED_NETWORK"


def test_offline_queues_retries_then_transmits():
    link = fresh_link(); link.set_mode("OFFLINE")
    p = link.enqueue(ALERT)
    assert p.status == "QUEUED" and p.channel == "SATELLITE_SIMULATED"
    force_visibility(link, False); link.tick()
    assert p.status == "RETRYING" and p.attempts == 1 and p.next_attempt_at > time.monotonic()
    link.tick()                                    # backoff not elapsed -> no extra attempt
    assert p.attempts == 1
    p.next_attempt_at = 0; force_visibility(link, True); link.tick()
    assert p.status == "TRANSMITTED" and p.attempts == 2


def test_offline_fails_after_retry_budget():
    link = fresh_link(); link.set_mode("OFFLINE")
    p = link.enqueue(ALERT)
    for _ in range(cn.MAX_ATTEMPTS):
        p.next_attempt_at = 0; force_visibility(link, False); link.tick()
    assert p.status == "FAILED"


def test_queue_flushes_when_network_returns():
    link = fresh_link(); link.set_mode("OFFLINE")
    p = link.enqueue(ALERT); link.set_mode("ONLINE"); link.tick()
    assert p.status == "DELIVERED_NETWORK"


def test_validation_suite_has_no_false_positives():
    res = validation.run_suite(settings)
    assert len(res) >= 7 and all(r["passed"] for r in res), [r for r in res if not r["passed"]]


def test_api_outage_flow_and_settings():
    with TestClient(app) as c:
        snap = c.post("/api/connectivity/network", json={"status": "OFFLINE"}).json()
        assert snap["network"]["status"] == "OFFLINE" and snap["satellite_fallback"]["simulated"] is True
        assert c.post("/api/connectivity/network", json={"status": "BROKEN"}).status_code == 422
        c.post("/api/simulation/reset")
        c.post("/api/connectivity/network", json={"status": "ONLINE"})
        an = c.get("/api/analytics").json()
        assert an["model"]["status"] == "trained" and all(t["passed"] for t in an["false_positive_tests"])
        assert {x["status"] for x in c.get("/api/connectivity").json()["capabilities"]} >= {"REAL", "SIMULATED", "FUTURE_HARDWARE"}
        bad = {"stationary_radius_m": 30, "stationary_duration_min": 30, "review_threshold": 70, "high_threshold": 40}
        assert c.put("/api/settings", json=bad).status_code == 422
        ok = {**bad, "review_threshold": 40, "high_threshold": 70}
        assert c.put("/api/settings", json=ok).json()["stationary_duration_min"] == 30
