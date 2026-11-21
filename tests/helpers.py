from datetime import datetime, timedelta
import location_processor as lp

def utc(h, m=0, day=21):
    """Build a naive-UTC datetime from a LOCAL (IST) clock time."""
    return datetime(2026, 11, day, h, m) - lp.IST

def history(lat, lon, start, minutes, step=5, move=False):
    out = []
    for i in range(0, minutes + 1, step):
        j = 0.00004 * ((i // step) % 3)   # ~4 m GPS jitter
        out.append(lp.Fix(lat + j + (0.0006 * (i // step) if move else 0), lon + j, start + timedelta(minutes=i)))
    return out

SCENARIOS = {
    "A": dict(lat=23.2300, lon=77.4300, start=utc(11), minutes=60, move=True),    # moving, populated
    "B": dict(lat=23.2330, lon=77.4340, start=utc(13), minutes=60),               # stationary, populated
    "C": dict(lat=23.1250, lon=77.3350, start=utc(22), minutes=60),               # stationary, isolated
    "D": dict(lat=23.1050, lon=77.3900, start=utc(22, 30), minutes=60),           # isolated + incident context
}
