#!/usr/bin/env python3
"""
raspberryRadar – Flight info lookup with daily cache.
Supports SkyLink API (route lookup) and AviationStack (full flight details).
Provider is selected via FLIGHTINFO_PROVIDER in config.py.

Static lookup tables (loaded once at import time):
  - iata-icao.csv     : ICAO airport code -> airport name, country code
  - countries.csv     : country code -> country name
  - icao_airlines.csv : ICAO airline code -> airline name
"""

import http.client
import requests
import json
import csv
import os
import logging
from datetime import date
from urllib.parse import urlencode

from config import (FLIGHTINFO_PROVIDER,
                    AIRPORTS_CSV, COUNTRIES_CSV, AIRLINES_CSV)
from secrets import SKYLINK_KEY, AVIATIONSTACK_KEY

BASE_DIR   = os.path.dirname(__file__)
CACHE_FILE = os.path.join(BASE_DIR, "flightinfo_cache.json")
LOG_FILE   = os.path.join(BASE_DIR, "flightinfo.log")

AIRPORTS_CSV  = os.path.join(BASE_DIR, AIRPORTS_CSV)
COUNTRIES_CSV = os.path.join(BASE_DIR, COUNTRIES_CSV)
AIRLINES_CSV  = os.path.join(BASE_DIR, AIRLINES_CSV)

# ── Logging ──────────────────────────────────────────────────
logger = logging.getLogger("flightinfo")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
logger.addHandler(fh)


# ── Static lookup tables ──────────────────────────────────────
def _load_airports():
    """
    Loads iata-icao.csv into a dict: ICAO -> {"name": ..., "country_code": ...}
    CSV columns: country_code, region_name, iata, icao, airport, latitude, longitude
    """
    table = {}
    try:
        with open(AIRPORTS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                icao = (row.get("icao") or "").strip()
                if not icao:
                    continue
                table[icao] = {
                    "name":         (row.get("airport") or "").strip(),
                    "country_code": (row.get("country_code") or "").strip(),
                }
        logger.info(f"Loaded {len(table)} airports from {AIRPORTS_CSV}")
    except Exception as e:
        logger.error(f"Could not load {AIRPORTS_CSV}: {e}")
    return table


def _load_countries():
    """
    Loads countries.csv into a dict: country_code -> country_name
    CSV columns: Countryname, Code
    """
    table = {}
    try:
        with open(COUNTRIES_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("Code") or "").strip()
                name = (row.get("Countryname") or "").strip()
                if code:
                    table[code] = name
        logger.info(f"Loaded {len(table)} countries from {COUNTRIES_CSV}")
    except Exception as e:
        logger.error(f"Could not load {COUNTRIES_CSV}: {e}")
    return table


def _load_airlines():
    """
    Loads icao_airlines.csv into a dict: ICAO -> airline name.
    CSV columns: IATA, ICAO, Airline, Call sign, Country/Region, Comments
    If an ICAO code appears multiple times (e.g. defunct duplicates),
    the first non-empty, non-"defunct" entry wins.
    """
    table = {}
    try:
        with open(AIRLINES_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                icao = (row.get("ICAO") or "").strip()
                name = (row.get("Airline") or "").strip()
                comments = (row.get("Comments") or "").strip().lower()
                if not icao or not name:
                    continue
                if icao in table:
                    continue  # keep first entry
                if "defunct" in comments:
                    # store but prefer a later non-defunct entry if one exists
                    table.setdefault(icao, name)
                    continue
                table[icao] = name
        logger.info(f"Loaded {len(table)} airlines from {AIRLINES_CSV}")
    except FileNotFoundError:
        logger.warning(f"{AIRLINES_CSV} not found – airline names will show ICAO codes only")
    except Exception as e:
        logger.error(f"Could not load {AIRLINES_CSV}: {e}")
    return table


_AIRPORTS  = _load_airports()
_COUNTRIES = _load_countries()
_AIRLINES  = _load_airlines()


def airport_name(icao_code):
    """Returns the airport name for an ICAO code, or the code itself if unknown."""
    entry = _AIRPORTS.get((icao_code or "").upper().strip())
    return entry["name"] if entry and entry["name"] else (icao_code or "–")


def country_name(country_code):
    """Returns the country name for a country code, or the code itself if unknown."""
    return _COUNTRIES.get((country_code or "").upper().strip(), country_code or "–")


def airline_name(icao_code):
    """Returns the airline name for an ICAO airline code, or the code itself if unknown."""
    return _AIRLINES.get((icao_code or "").upper().strip(), icao_code or "–")


# ── Cache ─────────────────────────────────────────────────────
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


# ── SkyLink ───────────────────────────────────────────────────
def _fetch_skylink(cs):
    """
    Fetches route info from SkyLink API /routes/callsign/{callsign}.
    Returns a normalized dict or None.

    Example response:
    {"callsign":"EWG5B","callsign_prefix":"EWG","airline_code":"EWG",
     "departure_icao":"EDDL","arrival_icao":"LHBP",
     "airports":["EDDL","LHBP"],"confidence":"high","source":"vrs"}
    """
    if not SKYLINK_KEY:
        logger.warning("No SKYLINK_KEY set in config.py – skipping lookup")
        return None

    logger.info(f"SkyLink API CALL → GET /routes/callsign/{cs}")

    try:
        conn = http.client.HTTPSConnection("skylink-api.p.rapidapi.com")
        headers = {
            "x-rapidapi-key":  SKYLINK_KEY,
            "x-rapidapi-host": "skylink-api.p.rapidapi.com",
            "Content-Type":    "application/json"
        }
        conn.request("GET", f"/routes/callsign/{cs}", headers=headers)
        res  = conn.getresponse()
        body = res.read().decode("utf-8")

        logger.info(f"SkyLink HTTP Status: {res.status}")
        logger.debug(f"SkyLink Response Body: {body[:1000]}")

        if res.status != 200:
            logger.error(f"SkyLink HTTP error {res.status}")
            return None

        data = json.loads(body)

        dep_icao = data.get("departure_icao") or ""
        arr_icao = data.get("arrival_icao")   or ""
        airline_code = data.get("airline_code") or data.get("callsign_prefix") or ""

        dep_country = _AIRPORTS.get(dep_icao.upper(), {}).get("country_code", "")
        arr_country = _AIRPORTS.get(arr_icao.upper(), {}).get("country_code", "")

        result = {
            "flight_number": cs,
            "airline":       airline_name(airline_code),
            "origin_iata":   "",
            "origin_name":   airport_name(dep_icao),
            "origin_country": country_name(dep_country),
            "dest_iata":     "",
            "dest_name":     airport_name(arr_icao),
            "dest_country":  country_name(arr_country),
            "actual_dep":    "–",
            "estimated_arr": "–",
            "scheduled_dep": "–",
            "scheduled_arr": "–",
            "aircraft_type": "–",
        }

        logger.info(f"SkyLink success: {result}")
        return result

    except Exception as e:
        logger.exception(f"SkyLink connection error: {e}")
        return None


# ── SkyLink: aircraft lookup ──────────────────────────────────
def _fetch_skylink_aircraft(icao24):
    """
    Fetches aircraft info from SkyLink API /aircraft/icao24/{icao24}.
    Returns the manufacturer_and_model string, or None.

    Example response:
    {"query":"4CAE7D","found":true,"aircraft":{"registration":"EI-FFA",
     "icao24":"4CAE7D","icao_type":"B738","type_name":"737-8K5",
     "manufacturer":"Boeing","manufacturer_and_model":"Boeing 737-8K5", ...}}
    """
    if not SKYLINK_KEY or not icao24:
        return None

    icao24 = icao24.strip().upper()
    logger.info(f"SkyLink API CALL → GET /aircraft/icao24/{icao24}?photos=false")

    try:
        conn = http.client.HTTPSConnection("skylink-api.p.rapidapi.com")
        headers = {
            "x-rapidapi-key":  SKYLINK_KEY,
            "x-rapidapi-host": "skylink-api.p.rapidapi.com",
            "Content-Type":    "application/json"
        }
        conn.request("GET", f"/aircraft/icao24/{icao24}?photos=false", headers=headers)
        res  = conn.getresponse()
        body = res.read().decode("utf-8")

        logger.info(f"SkyLink aircraft HTTP Status: {res.status}")
        logger.debug(f"SkyLink aircraft Response Body: {body[:1000]}")

        if res.status != 200:
            logger.error(f"SkyLink aircraft HTTP error {res.status}")
            return None

        data = json.loads(body)
        if not data.get("found"):
            logger.info(f"SkyLink: aircraft {icao24} not found in database")
            return None

        aircraft = data.get("aircraft") or {}
        model = aircraft.get("manufacturer_and_model")
        logger.info(f"SkyLink aircraft success: {model}")
        return model

    except Exception as e:
        logger.exception(f"SkyLink aircraft connection error: {e}")
        return None


# ── AviationStack ─────────────────────────────────────────────
def _fetch_aviationstack(cs):
    """
    Fetches flight info from AviationStack /v1/flights.
    Returns a normalized dict or None.
    """
    if not AVIATIONSTACK_KEY:
        logger.warning("No AVIATIONSTACK_KEY set in config.py – skipping lookup")
        return None

    base_url = "https://api.aviationstack.com/v1/flights"
    attempts = [
        {"flight_icao": cs},
        {"flight_iata": cs},
    ]

    for params in attempts:
        params["access_key"] = AVIATIONSTACK_KEY
        params["limit"] = 1

        full_url = base_url + "?" + urlencode(params)
        logger.info(f"AviationStack API CALL → {full_url}")

        try:
            resp = requests.get(base_url, params=params, timeout=10)
            logger.info(f"AviationStack HTTP Status: {resp.status_code}")
            logger.debug(f"AviationStack Response Body: {resp.text[:1000]}")

            if resp.status_code != 200:
                logger.error(f"AviationStack HTTP error {resp.status_code}")
                continue

            data = resp.json()

            if "error" in data:
                err = data["error"]
                logger.error(f"AviationStack API error: code={err.get('code')} message={err.get('message')}")
                break

            flights = data.get("data", [])
            if not flights:
                logger.info(f"AviationStack: no flights found with params={params}")
                continue

            f   = flights[0]
            dep = f.get("departure") or {}
            arr = f.get("arrival")   or {}
            ac  = f.get("aircraft")  or {}
            al  = f.get("airline")   or {}

            result = {
                "flight_number": cs,
                "airline":       al.get("name")     or "–",
                "origin_iata":   dep.get("iata")    or "",
                "origin_name":   dep.get("airport") or "–",
                "origin_country": "",
                "dest_iata":     arr.get("iata")    or "",
                "dest_name":     arr.get("airport") or "–",
                "dest_country":  "",
                "scheduled_dep": _fmt_time(dep.get("scheduled")),
                "actual_dep":    _fmt_time(dep.get("actual") or dep.get("estimated")),
                "scheduled_arr": _fmt_time(arr.get("scheduled")),
                "estimated_arr": _fmt_time(arr.get("estimated")),
                "aircraft_type": ac.get("iata") or ac.get("icao") or "–",
            }
            logger.info(f"AviationStack success: {result}")
            return result

        except Exception as e:
            logger.exception(f"AviationStack connection error: {e}")
            break

    return None


# ── Public entry point ────────────────────────────────────────
def fetch_flightinfo(callsign, icao24=None):
    """
    Returns a flight info dict for the given callsign, or None on failure.
    Uses the provider configured in config.py (FLIGHTINFO_PROVIDER).
    Results are cached for the current day.

    icao24 (optional): the aircraft's ICAO24 transponder address, used to
    look up the aircraft type via SkyLink's aircraft database.
    """
    cs = callsign.strip().upper()
    if not cs or cs == "N/A":
        logger.info(f"Empty or invalid callsign: '{callsign}' – skipped")
        return None

    if cs in _cache:
        logger.info(f"Cache hit for {cs}: {_cache[cs]}")
        return _cache[cs]

    provider = FLIGHTINFO_PROVIDER.lower().strip()
    logger.info(f"Using provider: {provider} for callsign: {cs}")

    if provider == "skylink":
        result = _fetch_skylink(cs)
        if result and icao24:
            aircraft_model = _fetch_skylink_aircraft(icao24)
            if aircraft_model:
                result["aircraft_type"] = aircraft_model
    elif provider == "aviationstack":
        result = _fetch_aviationstack(cs)
    else:
        logger.error(f"Unknown FLIGHTINFO_PROVIDER: '{provider}' – must be 'skylink' or 'aviationstack'")
        result = None

    _cache[cs] = result
    _save_cache(_cache)
    logger.info(f"Saved to cache: {cs} → {result}")
    return result


# ── Helpers ───────────────────────────────────────────────────
def _fmt_time(iso_str):
    """ISO 8601 → HH:MM UTC, or '–' if empty."""
    if not iso_str:
        return "–"
    try:
        return iso_str[11:16] + " UTC"
    except Exception:
        return "–"
