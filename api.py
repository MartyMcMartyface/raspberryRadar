#!/usr/bin/env python3
"""
raspberryRadar – OpenSky API
Fetches live aircraft data within the configured radius.
"""

import requests
import math
from config import HOME_LAT, HOME_LON, RADIUS, OPENSKY_USER, OPENSKY_PASS


def fetch_flights():
    """
    Returns a list of aircraft within the configured radius.
    Each aircraft is a dict with: icao, callsign, country, lat, lon,
    altitude (m), velocity (m/s), heading (degrees).
    """
    lat_min = HOME_LAT - RADIUS
    lat_max = HOME_LAT + RADIUS
    lon_min = HOME_LON - RADIUS
    lon_max = HOME_LON + RADIUS

    url = (
        f"https://opensky-network.org/api/states/all"
        f"?lamin={lat_min}&lamax={lat_max}"
        f"&lomin={lon_min}&lomax={lon_max}"
    )

    try:
        if OPENSKY_USER and OPENSKY_PASS:
            resp = requests.get(url, auth=(OPENSKY_USER, OPENSKY_PASS), timeout=10)
        else:
            resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            print(f"API error: {resp.status_code}")
            return []

        data = resp.json()
        if not data or not data.get("states"):
            return []

        flights = []
        for s in data["states"]:
            # OpenSky state vector fields:
            # 0=icao24, 1=callsign, 2=origin_country, 5=lon, 6=lat,
            # 7=baro_altitude, 9=velocity, 10=heading
            if s[6] is None or s[5] is None:
                continue
            flights.append({
                "icao":     s[0],
                "callsign": (s[1] or "N/A").strip(),
                "country":  s[2] or "",
                "lat":      s[6],
                "lon":      s[5],
                "altitude": s[7] or 0,      # meters
                "velocity": s[9] or 0,      # m/s
                "heading":  s[10] or 0,     # degrees
            })
        return flights

    except Exception as e:
        print(f"Connection error: {e}")
        return []


def distance_km(lat1, lon1, lat2, lon2):
    """Haversine distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def altitude_to_fl(meters):
    """Meters → Flight Level (rounded to nearest 10)."""
    if meters <= 0:
        return "GND"
    fl = round(meters * 3.28084 / 100 / 10) * 10
    return f"FL{fl:03d}"


def velocity_kmh(ms):
    """m/s → km/h."""
    return round(ms * 3.6)
