#!/usr/bin/env python3
"""
raspberryRadar – OpenSky API
Fetches live aircraft data within the configured radius.
Uses OAuth2 client credentials flow for authentication.
Token is fetched automatically and refreshed before expiry.
"""

import requests
import math
from datetime import datetime, timedelta
from config import HOME_LAT, HOME_LON, RADIUS
from secrets import OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET

# ── OAuth2 token endpoint ─────────────────────────────────────
TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
TOKEN_REFRESH_MARGIN = 60   # refresh token this many seconds before expiry


class _TokenManager:
    """Fetches and caches an OAuth2 Bearer token for OpenSky."""

    def __init__(self):
        self._token      = None
        self._expires_at = None
        self._client_id     = OPENSKY_CLIENT_ID
        self._client_secret = OPENSKY_CLIENT_SECRET

    def get_token(self):
        """Returns a valid Bearer token, refreshing if needed."""
        if not self._client_id or not self._client_secret:
            return None
        if self._token and self._expires_at and datetime.now() < self._expires_at:
            return self._token
        return self._refresh()

    def _refresh(self):
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "grant_type":    "client_credentials",
                    "client_id":     self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            resp.raise_for_status()
            data            = resp.json()
            self._token     = data["access_token"]
            expires_in      = data.get("expires_in", 1800)
            self._expires_at = datetime.now() + timedelta(
                seconds=expires_in - TOKEN_REFRESH_MARGIN
            )
            print(f"OpenSky token refreshed, valid for {expires_in}s")
            return self._token
        except Exception as e:
            print(f"OpenSky token refresh failed: {e}")
            self._token = None
            return None

    def headers(self):
        """Returns Authorization headers dict, or empty dict for anonymous access."""
        token = self.get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


# Single shared token manager instance
_token_manager = _TokenManager()


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
        resp = requests.get(url, headers=_token_manager.headers(), timeout=10)

        if resp.status_code == 429:
            print("OpenSky rate limit reached (429) – retrying next interval")
            return []
        if resp.status_code != 200:
            print(f"OpenSky API error: {resp.status_code}")
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
        print(f"OpenSky connection error: {e}")
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
