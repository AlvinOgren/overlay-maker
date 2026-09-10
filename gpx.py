"""GPX parsing and elapsed-time sampling. No network or file writes."""
from __future__ import annotations
import bisect
import math
import statistics
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

MAX_BYTES = 20 * 1024 * 1024
GAP_SECONDS = 10.0
METRICS = {
    "speed": {"label": "Hastighet", "unit": "km/h", "icon": "speed", "derived": True},
    "hr": {"label": "Puls", "unit": "bpm", "icon": "heart"},
    "power": {"label": "Effekt", "unit": "W", "icon": "bolt"},
    "cad": {"label": "Kadens", "unit": "rpm", "icon": "cadence"},
    "elapsed": {"label": "Elapsed time", "unit": "", "icon": "clock", "derived": True},
    "distance": {"label": "Distans", "unit": "km", "icon": "distance", "derived": True},
    "ele": {"label": "Höjd", "unit": "m", "icon": "mountain"},
    "temp": {"label": "Temperatur", "unit": "°C", "icon": "temperature"},
}


def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def numeric(value, minimum=None, maximum=None):
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(result):
        return None
    if minimum is not None and result < minimum or maximum is not None and result > maximum:
        return None
    return result


def metres(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlon = math.radians(b["lon"] - a["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def parse_gpx(data: bytes, filename="aktivitet.gpx"):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Välj en GPX-fil som är högst 20 MB.")
    # Do not permit declarations/entities, including in UTF-16 input.
    compact = data.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in compact or b"<!ENTITY" in compact:
        raise ValueError("XML med DTD eller egna entiteter stöds inte.")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError("Filen kunde inte läsas som GPX/XML.") from error
    if local(root.tag) != "gpx":
        raise ValueError("Filen är inte en GPX-fil.")
    segments = [el for el in root.iter() if local(el.tag) == "trkseg"]
    if not segments:
        segments = [root]
    points, skipped, gaps, outliers, missing_position = [], 0, [], 0, 0
    tz_assumed = False
    for segment_id, segment in enumerate(segments):
        for node in segment.iter():
            if local(node.tag) not in {"trkpt", "rtept"}:
                continue
            fields = {}
            for child in node.iter():
                if child is not node and child.text and child.text.strip():
                    fields[local(child.tag)] = child.text.strip()
            try:
                stamp = datetime.fromisoformat(fields.get("time", "").replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                    tz_assumed = True
                timestamp = stamp.timestamp()
            except (ValueError, OverflowError):
                skipped += 1
                continue
            if points and timestamp <= points[-1]["timestamp"]:
                skipped += 1
                continue
            point = {
                "timestamp": timestamp, "segment": segment_id,
                "lat": numeric(node.get("lat"), -90, 90),
                "lon": numeric(node.get("lon"), -180, 180),
                "ele": numeric(fields.get("ele"), -1500, 15000),
                "hr": numeric(fields.get("hr", fields.get("heartrate")), 1, 300),
                "power": numeric(fields.get("power", fields.get("watts")), 0, 10000),
                "cad": numeric(fields.get("cad", fields.get("cadence")), 0, 400),
                "temp": numeric(fields.get("atemp", fields.get("temp", fields.get("temperature"))), -100, 100),
                "speed": None, "distance": 0.0,
            }
            if point["lat"] is None or point["lon"] is None:
                missing_position += 1
            if points:
                previous = points[-1]
                dt = timestamp - previous["timestamp"]
                point["distance"] = previous["distance"]
                continuous = segment_id == previous["segment"] and dt <= GAP_SECONDS
                if not continuous:
                    gaps.append((previous["timestamp"], timestamp))
                if continuous and all(p[k] is not None for p in (previous, point) for k in ("lat", "lon")):
                    delta = metres(previous, point)
                    if delta / dt <= 100:
                        point["speed"] = delta / dt * 3.6
                        point["distance"] += delta / 1000
                    else:
                        outliers += 1
            points.append(point)
            if len(points) > 200000:
                raise ValueError("Filen innehåller för många mätpunkter (max 200 000).")
    if len(points) < 2:
        raise ValueError("Minst två mätpunkter med stigande tidsstämplar behövs.")
    start = points[0]["timestamp"]
    duration = points[-1]["timestamp"] - start
    if duration <= 0 or duration > 7 * 86400:
        raise ValueError("Aktivitetens tidslinje måste vara längre än noll och högst sju dygn.")
    for point in points:
        point["t"] = point["timestamp"] - start
        del point["timestamp"]
    availability = {}
    for key, meta in METRICS.items():
        count = len(points) if key == "elapsed" else sum(p.get(key) is not None for p in points)
        if key == "distance" and not any(p["speed"] is not None for p in points):
            count = 0
        availability[key] = {**meta, "available": count > 0, "count": count, "total": len(points)}
    warnings = []
    if gaps:
        warnings.append(f"{len(gaps)} avbrott eller segmentgränser. Sensorvärden visas som streck mellan dessa punkter; elapsed time fortsätter.")
    if skipped:
        warnings.append(f"{skipped} punkter saknade giltig tid eller hade samma/tidigare tidsstämpel och hoppades över.")
    if outliers:
        warnings.append(f"{outliers} orimliga GPS-förflyttningar uteslöts från hastighet och distans.")
    if missing_position:
        warnings.append(f"{missing_position} punkter saknade giltig position.")
    if tz_assumed:
        warnings.append("Tidsstämplar utan tidszon tolkades som UTC.")
    return {
        "name": str(filename).replace("\\", "/").rsplit("/", 1)[-1][:160],
        "start_utc": datetime.fromtimestamp(start, timezone.utc).isoformat(),
        "duration": duration, "points": points, "times": [p["t"] for p in points],
        "count": len(points), "distance": points[-1]["distance"],
        "gaps": [[a - start, b - start] for a, b in gaps],
        "metrics": availability, "warnings": warnings,
    }


def public_activity(activity):
    return {k: v for k, v in activity.items() if k not in {"points", "times"}}


def sample(activity, elapsed):
    """Interpolate only across <=10 s in one segment, never fill missing fields."""
    t = min(max(float(elapsed), 0), activity["duration"])
    values = {key: None for key in METRICS}
    values["elapsed"] = t
    idx = bisect.bisect_right(activity["times"], t) - 1
    left = activity["points"][max(0, idx)]
    if abs(left["t"] - t) < 1e-7:
        values.update({key: left.get(key) for key in METRICS if key != "elapsed"})
        return values
    if idx + 1 >= len(activity["points"]):
        return values
    right = activity["points"][idx + 1]
    dt = right["t"] - left["t"]
    if dt > GAP_SECONDS or left["segment"] != right["segment"]:
        return values
    fraction = (t - left["t"]) / dt
    for key in METRICS:
        if key == "elapsed":
            continue
        a, b = left.get(key), right.get(key)
        if a is not None and b is not None:
            values[key] = a + (b - a) * fraction
    return values
