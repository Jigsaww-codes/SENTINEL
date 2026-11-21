"""Regenerates the SIMULATED demo datasets (Bhopal outskirts demonstration area).
Nothing here is real incident data. Run: python data/generate_data.py"""
import csv, json
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point, LineString, mapping

OUT = Path(__file__).parent
UTM = "EPSG:32643"   # UTM 43N, metric CRS for the Bhopal region
LABEL = "SIMULATED demonstration data - not real incidents or surveyed boundaries"

populated = [  # id, name, lat, lon, class, zone radius (m)
    ("P1", "New Market area (sim)", 23.2330, 77.4340, "urban", 1800),
    ("P2", "Arera Colony area (sim)", 23.2120, 77.4330, "urban", 1500),
    ("P3", "Kolar Road area (sim)", 23.1700, 77.4170, "suburban", 1300),
]
isolated = [  # remote scrubland pockets used by the demo scenarios
    ("ISO1", "South-west scrubland (sim)", 23.1250, 77.3350, 2500),
    ("ISO2", "Southern outskirts tract (sim)", 23.1050, 77.3900, 2500),
]
incidents = [  # id, name, lat, lon, radius, aggregate count, severity 0-100
    ("INC1", "Aggregated historical-context cluster A (sim)", 23.1050, 77.3900, 1500, 14, 90),
    ("INC2", "Aggregated historical-context cluster B (sim)", 23.2330, 77.4340, 700, 5, 25),
]
roads = [
    ("RD1", "Main urban road (sim)", [(23.2290, 77.4290), (23.2330, 77.4340), (23.2420, 77.4420)]),
    ("RD2", "Kolar-link rural road (sim)", [(23.1700, 77.4170), (23.1450, 77.3800), (23.1250, 77.3600), (23.1150, 77.3450)]),
    ("RD3", "Arera link road (sim)", [(23.2120, 77.4330), (23.2290, 77.4290)]),
]

def circle(lat, lon, r):
    g = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(UTM).buffer(r, 32).to_crs("EPSG:4326")
    return mapping(g.iloc[0])

feats = []
for i, n, la, lo, c, r in populated:
    feats.append({"type": "Feature", "geometry": circle(la, lo, r), "properties": {
        "zone_id": i, "zone_type": "populated", "name": n, "context_score": 0, "simulated": True}})
for i, n, la, lo, r in isolated:
    feats.append({"type": "Feature", "geometry": circle(la, lo, r), "properties": {
        "zone_id": i, "zone_type": "isolated", "name": n, "context_score": 60, "simulated": True}})
for i, n, la, lo, r, cnt, sev in incidents:
    feats.append({"type": "Feature", "geometry": circle(la, lo, r), "properties": {
        "zone_id": i, "zone_type": "incident_history", "name": n, "context_score": sev, "simulated": True}})
for i, n, pts in roads:
    feats.append({"type": "Feature", "geometry": mapping(LineString([(lo, la) for la, lo in pts])),
                  "properties": {"zone_id": i, "zone_type": "road", "name": n, "context_score": 0, "simulated": True}})
(OUT / "geographical_zones.geojson").write_text(json.dumps(
    {"type": "FeatureCollection", "name": LABEL, "features": feats}, indent=1))

with open(OUT / "locations.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["location_id", "name", "latitude", "longitude", "settlement_class", "radius_m", "data_label"])
    for i, n, la, lo, c, r in populated: w.writerow([i, n, la, lo, c, r, LABEL])

with open(OUT / "incident_zones.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["zone_id", "name", "latitude", "longitude", "radius_m", "aggregate_incident_count", "severity", "data_label"])
    for i, n, la, lo, r, cnt, sev in incidents: w.writerow([i, n, la, lo, r, cnt, sev, LABEL])
print("generated", len(feats), "zone features")
