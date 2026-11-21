"""Four-device demo simulation. Every update goes through the REAL pipeline (alerts.process_location):
no risk score is scripted. Time is accelerated: one tick = 5 simulated minutes.

DEV-A1  moving along a populated road          -> never stationary
DEV-B2  stationary at a populated location     -> evaluated, stays NORMAL (false-positive guard)
DEV-C3  stationary in an isolated location     -> REVIEW REQUIRED
DEV-D4  stationary, isolated + incident context-> HIGH PRIORITY verification
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from sqlalchemy import delete

import alerts as alert_svc
import location_processor as lp
from connectivity import sim_link
from database import SessionLocal
from models import Alert, DeviceLocation, DeviceSession
from schemas import LocationUpdate
from websocket_manager import manager

TICK_SIM_MIN = 5          # simulated minutes per tick
TOTAL_TICKS = 14          # 65 simulated minutes (60 min of stationary time after arrival)
TICK_REAL_S = 1.2         # real seconds per tick
START_LOCAL_HOUR = 21.5   # 21:30 IST on the simulated clock

ROAD = [(23.2290, 77.4290), (23.2330, 77.4340), (23.2420, 77.4420)]     # matches data/ RD1


def _along(path: List[Tuple[float, float]], frac: float) -> Tuple[float, float]:
    segs = [(a, b, lp.haversine_m(*a, *b)) for a, b in zip(path, path[1:])]
    target, total = frac * sum(s[2] for s in segs), 0
    for a, b, d in segs:
        if total + d >= target:
            t = (target - total) / d
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        total += d
    return path[-1]


def _jitter(tick: int) -> Tuple[float, float]:
    j = 0.00004 * (tick % 3)          # ~4 m GNSS noise: stays inside the 30 m radius
    return j, -j


def _arrive(start, site):
    """Device drives/walks in from `start`, arrives at tick 1, then stays put."""
    def pos(tick):
        if tick == 0:
            return start
        j = _jitter(tick)
        return site[0] + j[0], site[1] + j[1]
    return pos


def _walk(tick):
    ping = (tick * 0.07) % 2
    return _along(ROAD, ping if ping <= 1 else 2 - ping)


DEVICES: Dict[str, dict] = {
    "DEV-A1": dict(pos=_walk, source="GPS", accuracy=8, label="Moving along populated road"),
    "DEV-B2": dict(pos=_arrive((23.2120, 77.4330), (23.2330, 77.4340)), source="GNSS", accuracy=6,
                   label="Stationary at populated location"),
    "DEV-C3": dict(pos=_arrive((23.1150, 77.3450), (23.1250, 77.3350)), source="NAVIC", accuracy=5,
                   label="Stationary at isolated location"),
    "DEV-D4": dict(pos=_arrive((23.1450, 77.3800), (23.1050, 77.3900)), source="NAVIC", accuracy=5,
                   label="Stationary at isolated location with incident context"),
}


def reset_demo_data() -> None:
    with SessionLocal() as db:
        for m in (Alert, DeviceLocation, DeviceSession):
            db.execute(delete(m))
        db.commit()
    alert_svc.latest_state.clear()
    sim_link.clear()


class SimulationEngine:
    def __init__(self):
        self.task: asyncio.Task | None = None
        self.tick = 0
        self.sim_time: datetime | None = None
        self.state = "idle"       # idle | running | completed | stopped

    def status(self) -> dict:
        return {"running": self.state == "running", "state": self.state, "tick": self.tick,
                "total_ticks": TOTAL_TICKS, "sim_time_ist": (self.sim_time + lp.IST).strftime("%H:%M")
                if self.sim_time else None,
                "devices": {k: v["label"] for k, v in DEVICES.items()}}

    async def _emit(self):
        await manager.broadcast("simulation_status", self.status())

    async def start(self) -> dict:
        if self.state == "running":
            return self.status()
        await self.reset(broadcast=False)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        self.sim_time = today + timedelta(hours=START_LOCAL_HOUR) - lp.IST
        self.tick, self.state = 0, "running"
        self.task = asyncio.create_task(self._run())
        await self._emit()
        return self.status()

    async def stop(self) -> dict:
        if self.task and not self.task.done():
            self.task.cancel()
        if self.state == "running":
            self.state = "stopped"
        await self._emit()
        return self.status()

    async def reset(self, broadcast: bool = True) -> dict:
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.sleep(0)
        await asyncio.to_thread(reset_demo_data)
        self.tick, self.sim_time, self.state = 0, None, "idle"
        if broadcast:
            await manager.broadcast("reset", {})
            await self._emit()
        return self.status()

    def _step(self, tick: int, t: datetime):
        out = []
        with SessionLocal() as db:
            for dev, cfg in DEVICES.items():
                lat, lon = cfg["pos"](tick)
                u = LocationUpdate(device_id=dev, latitude=lat, longitude=lon, timestamp=t.replace(tzinfo=timezone.utc),
                                   accuracy=cfg["accuracy"], source=cfg["source"], consent=True)
                try:
                    _, events = alert_svc.process_location(db, u)
                    out += events
                except lp.LocationValidationError:
                    db.rollback()
        return out

    async def _run(self):
        try:
            while self.tick < TOTAL_TICKS:
                t = self.sim_time + timedelta(minutes=TICK_SIM_MIN * self.tick)
                for etype, data in await asyncio.to_thread(self._step, self.tick, t):
                    await manager.broadcast(etype, data)
                self.tick += 1
                await self._emit()
                await asyncio.sleep(TICK_REAL_S)
            self.state = "completed"
            await self._emit()
        except asyncio.CancelledError:
            pass


engine = SimulationEngine()
