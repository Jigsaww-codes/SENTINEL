"""Emergency-communication fallback. EVERYTHING HERE IS A SIMULATION: no satellite hardware or service
is contacted. It demonstrates the queue -> transmit -> retry logic that a satellite-capable device
(e.g. a NavIC/GNSS receiver paired with a satellite messenger) would run when cellular is unavailable.

Model: when network mode is OFFLINE, each new alert's compact location packet is queued. A worker tries to
send it over the simulated satellite link, which is only 'visible' during periodic pass windows. Failed
attempts back off exponentially (max 5 attempts)."""
import asyncio, threading, time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List

from websocket_manager import manager

PASS_PERIOD_S = 8.0       # simulated satellite visibility: link up for the first half of each period
MAX_ATTEMPTS = 5
BACKOFF_S = [0, 2, 4, 8, 16]
MAX_PACKET_BYTES = 64


@dataclass
class Packet:
    packet_id: int
    alert_id: int
    payload: str
    size_bytes: int
    channel: str                     # SATELLITE_SIMULATED | NETWORK
    status: str = "QUEUED"           # QUEUED | RETRYING | TRANSMITTED | DELIVERED_NETWORK | FAILED
    attempts: int = 0
    next_attempt_at: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_note: str = ""


class ConnectivitySimulator:
    def __init__(self):
        self.mode = "ONLINE"                 # ONLINE | OFFLINE
        self.queue: List[Packet] = []
        self._lock = threading.Lock()
        self._seq = 0
        self._t0 = time.monotonic()

    def link_visible(self) -> bool:
        return ((time.monotonic() - self._t0) % PASS_PERIOD_S) < PASS_PERIOD_S / 2

    def set_mode(self, mode: str):
        self.mode = mode

    def encode(self, alert) -> str:
        # compact packet: ID | lat | lon | level code | score | HHMM  (well under 64 bytes)
        code = {"HIGH_PRIORITY_VERIFICATION": "H", "REVIEW_REQUIRED": "R"}.get(alert["risk_level"], "N")
        return f"SNT|{alert['device_id']}|{alert['latitude']:.4f}|{alert['longitude']:.4f}|{code}|{int(alert['risk_score'])}"

    def enqueue(self, alert: dict) -> Packet:
        payload = self.encode(alert)
        with self._lock:
            self._seq += 1
            online = self.mode == "ONLINE"
            p = Packet(self._seq, alert["alert_id"], payload, len(payload.encode()),
                       "NETWORK" if online else "SATELLITE_SIMULATED",
                       status="DELIVERED_NETWORK" if online else "QUEUED",
                       last_note="Sent over conventional network" if online else "Queued: no network")
            self.queue.append(p)
            self.queue = self.queue[-30:]
        return p

    def tick(self) -> bool:
        """One worker pass. Returns True if any packet changed state."""
        changed, now = False, time.monotonic()
        with self._lock:
            for p in self.queue:
                if p.status not in ("QUEUED", "RETRYING") or now < p.next_attempt_at:
                    continue
                if self.mode == "ONLINE":              # network came back: deliver normally
                    p.status, p.channel, p.last_note, changed = "DELIVERED_NETWORK", "NETWORK", "Network restored: delivered", True
                    continue
                p.attempts += 1
                changed = True
                if self.link_visible():
                    p.status, p.last_note = "TRANSMITTED", f"Sent via simulated satellite on attempt {p.attempts}"
                elif p.attempts >= MAX_ATTEMPTS:
                    p.status, p.last_note = "FAILED", "No satellite pass within retry budget"
                else:
                    p.status = "RETRYING"
                    p.next_attempt_at = now + BACKOFF_S[min(p.attempts, len(BACKOFF_S) - 1)]
                    p.last_note = f"No satellite in view; retry {p.attempts}/{MAX_ATTEMPTS - 1} in {BACKOFF_S[min(p.attempts, 4)]} s"
        return changed

    def clear(self):
        with self._lock:
            self.queue.clear()

    def snapshot(self, devices_by_source: Dict[str, int], avg_accuracy) -> dict:
        with self._lock:
            q = [asdict(p) for p in reversed(self.queue)]
        return {
            "gnss": {"status": "ACTIVE" if devices_by_source else "WAITING_FOR_DATA",
                     "sources_in_use": devices_by_source, "avg_accuracy_m": avg_accuracy,
                     "accepted_fields": ["latitude", "longitude", "timestamp", "source", "accuracy"],
                     "constellations": ["GPS", "NavIC / IRNSS (India regional)"]},
            "network": {"status": self.mode},
            "satellite_fallback": {"simulated": True, "link_visible": self.link_visible(),
                                   "state": "ACTIVE" if self.mode == "OFFLINE" else "STANDBY",
                                   "pass_period_s": PASS_PERIOD_S, "max_attempts": MAX_ATTEMPTS,
                                   "max_packet_bytes": MAX_PACKET_BYTES, "queue": q},
            "capabilities": CAPABILITIES,
        }

    async def worker(self):
        while True:
            await asyncio.sleep(1.0)
            if await asyncio.to_thread(self.tick):
                await manager.broadcast("connectivity", {"changed": True})


CAPABILITIES = [
    {"name": "Accept GNSS / NavIC-sourced coordinates with accuracy metadata", "status": "REAL",
     "detail": "POST /api/location validates source, accuracy and timestamp. Software only."},
    {"name": "Stationary detection, geographic context, ML scoring, alerts", "status": "REAL",
     "detail": "Runs on whatever coordinates it receives."},
    {"name": "Device location feed in this demo", "status": "SIMULATED",
     "detail": "Four scripted devices; no live phones or receivers connected."},
    {"name": "Satellite emergency messaging (queue, pass windows, retry)", "status": "SIMULATED",
     "detail": "Logic is real; the satellite link is a timer-based model. No satellite is contacted."},
    {"name": "NavIC-capable receiver on the device", "status": "FUTURE_HARDWARE",
     "detail": "Requires NavIC/L5-S chipset phones or modules; not used in this prototype."},
    {"name": "Satellite imagery for settlement / terrain analysis", "status": "FUTURE_DATA",
     "detail": "Prototype uses simulated zones. Real land-cover or OSM extracts would replace data/*.geojson."},
]

sim_link = ConnectivitySimulator()
