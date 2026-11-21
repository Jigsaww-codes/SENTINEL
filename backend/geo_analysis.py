"""Geographical context: isolation, road access, incident-history context, zone membership.
Uses GeoPandas/Shapely in UTM 43N (metres). Data: data/*.csv|geojson (SIMULATED unless replaced)."""
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import List

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union

from config import DATA_DIR

UTM = "EPSG:32643"
POP_FAR_M = 3000.0     # >= this far from any settlement => fully isolated on that axis
ROAD_FAR_M = 1000.0


@dataclass
class GeoContext:
    populated_distance_m: float
    road_distance_m: float
    isolation_score: float          # I, 0-100
    incident_score: float           # C, 0-100 (context only, never an accusation)
    in_populated_zone: bool
    in_isolated_zone: bool
    in_incident_zone: bool
    is_isolated: bool
    zones: List[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load():
    z = gpd.read_file(DATA_DIR / "geographical_zones.geojson").set_crs("EPSG:4326", allow_override=True).to_crs(UTM)
    loc = pd.read_csv(DATA_DIR / "locations.csv")
    inc = pd.read_csv(DATA_DIR / "incident_zones.csv")
    to_pts = lambda df: gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs="EPSG:4326").to_crs(UTM)
    return {
        "zones": z,
        "roads": unary_union(z[z.zone_type == "road"].geometry.values),
        "populated_polys": z[z.zone_type == "populated"],
        "isolated_polys": z[z.zone_type == "isolated"],
        "incident_polys": z[z.zone_type == "incident_history"],
        "settlements": to_pts(loc),
        "incidents": to_pts(inc),
    }


def _pt(lat, lon):
    return gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(UTM).iloc[0]


def analyse(lat: float, lon: float, when: datetime | None = None) -> GeoContext:
    d = _load()
    p = _pt(lat, lon)
    pop_d = float(d["settlements"].distance(p).min())
    road_d = float(d["roads"].distance(p))
    in_pop = bool(d["populated_polys"].contains(p).any())
    in_iso = bool(d["isolated_polys"].contains(p).any())

    # Isolation I: weighted settlement distance + road distance; populated zones cap it low.
    I = 100 * (0.6 * min(pop_d / POP_FAR_M, 1) + 0.4 * min(road_d / ROAD_FAR_M, 1))
    if in_pop:
        I = min(I, 15.0)
    if in_iso:
        I = max(I, 80.0)

    # Historical context C: strongest severity-weighted proximity to an aggregate incident zone.
    C, in_inc = 0.0, False
    for _, r in d["incidents"].iterrows():
        dist = float(r.geometry.distance(p))
        C = max(C, float(r.severity) * max(0.0, 1 - (dist / (1.5 * r.radius_m)) ** 2))
        in_inc = in_inc or dist <= r.radius_m

    names = [str(n) for n in d["zones"][d["zones"].contains(p)].name.tolist()]
    return GeoContext(round(pop_d, 1), round(road_d, 1), round(I, 1), round(C, 1),
                      in_pop, in_iso, in_inc, bool(I >= 60 or in_iso), names)


def zone_records():
    """Rows for seeding the GeographicalZones table (GeoJSON geometry kept in WGS84)."""
    z = _load()["zones"].to_crs("EPSG:4326")
    return [{"zone_id": r.zone_id, "zone_type": r.zone_type, "name": r["name"],
             "geometry": r.geometry.__geo_interface__, "context_score": float(r.context_score)}
            for _, r in z.iterrows()]
