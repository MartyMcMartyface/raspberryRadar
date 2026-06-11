#!/usr/bin/env python3
"""
raspberryRadar – AviationStack flight plan lookup with daily cache.
Fetches route, times, and aircraft type by callsign.
Each callsign is queried at most once per day.
"""

import requests
import json
import os
import logging
from datetime import date
from urllib.parse import urlencode

from config import AVIATIONSTACK_KEY

CACHE_FILE = os.path.join(os.path.dirname(__file__), "flightinfo_cache.json")
LOG_FILE   = os.path.join(os.path.dirname(__file__), "aviationstack.log")

# ── Logging ──────────────────────────────────────────────────
logger = logging.getLogger("aviationstack")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
logger.addHandler(fh)


def _load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") == str(date.today()):
            return data.get("flights", {})
    except Exception:
        pass
    return {}


def _save_cache(flights_cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"date": str(date.today()), "flights": flights_cache}, f)
    except Exception:
        pass


_cache = _load_cache()


def fetch_flightinfo(callsign):
    """
    Returns a dict with flight plan information, or None on error / no result.
    Fields: origin_iata, origin_name, dest_iata, dest_name,
            scheduled_dep, actual_dep, scheduled_arr, estimated_arr,
            aircraft_type, airline
    """
    if not AVIATIONSTACK_KEY:
        logger.warning("No AVIATIONSTACK_KEY set in config.py – skipping lookup")
        return None

    cs = callsign.strip().upper()
    if not cs or cs == "N/A":
        logger.info(f"Empty or invalid callsign: '{callsign}' – skipped")
        return None

    if cs in _cache:
        logger.info(f"Cache hit for {cs}: {_cache[cs]}")
        return _cache[cs]

    base_url = "https://api.aviationstack.com/v1/flights"

    attempts = [
        {"flight_icao": cs},
        {"flight_iata": cs},
    ]

    result = None
    for params in attempts:
        params["access_key"] = AVIATIONSTACK_KEY
        params["limit"] = 1

        full_url = base_url + "?" + urlencode(params)
        logger.info(f"API CALL → {full_url}")

        try:
            resp = requests.get(base_url, params=params, timeout=10)
            logger.info(f"HTTP Status: {resp.status_code}")
            logger.debug(f"Response Body: {resp.text[:1000]}")

            if resp.status_code != 200:
                logger.error(f"HTTP error {resp.status_code}")
                continue

            data = resp.json()

            if "error" in data:
                err = data["error"]
                logger.error(f"API error: code={err.get('code')} message={err.get('message')}")
                break

            flights = data.get("data", [])
            if not flights:
                logger.info(f"No flights found with params={params}")
                continue

            f   = flights[0]
            dep = f.get("departure") or {}
            arr = f.get("arrival")   or {}
            ac  = f.get("aircraft")  or {}
            al  = f.get("airline")   or {}

            result = {
                "origin_iata":   dep.get("iata")    or "–",
                "origin_name":   dep.get("airport") or "–",
                "dest_iata":     arr.get("iata")    or "–",
                "dest_name":     arr.get("airport") or "–",
                "scheduled_dep": _fmt_time(dep.get("scheduled")),
                "actual_dep":    _fmt_time(dep.get("actual") or dep.get("estimated")),
                "scheduled_arr": _fmt_time(arr.get("scheduled")),
                "estimated_arr": _fmt_time(arr.get("estimated")),
                "aircraft_type": ac.get("iata") or ac.get("icao") or "–",
                "airline":       al.get("name") or "–",
            }
            logger.info(f"Success: {result}")
            break

        except Exception as e:
            logger.exception(f"Connection error: {e}")
            break

    _cache[cs] = result
    _save_cache(_cache)
    logger.info(f"Saved to cache: {cs} → {result}")
    return result


def _fmt_time(iso_str):
    """ISO 8601 → HH:MM UTC, or '–' if empty."""
    if not iso_str:
        return "–"
    try:
        return iso_str[11:16] + " UTC"
    except Exception:
        return "–"
