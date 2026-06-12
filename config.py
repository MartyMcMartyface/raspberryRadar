#!/usr/bin/env python3
# ============================================================
#  raspberryRadar – Configuration
#  Edit these values before first launch.
# ============================================================

# Your home GPS coordinates (decimal degrees)
HOME_LAT = 51.436531528928946
HOME_LON = 6.914741907068714

# Label shown at the center of the radar
HOME_NAME = "HOME"

# Search radius in degrees (~1 degree ≈ 111 km)
# 0.5 = ~55 km radius, 1.0 = ~110 km radius
RADIUS = 0.15

# Seconds between OpenSky API refreshes
UPDATE_INTERVAL = 15

# Display resolution – match your screen
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 480

# Fullscreen mode: True = fullscreen, False = windowed (useful for testing)
FULLSCREEN = False

# ── Secrets ───────────────────────────────────────────────────
# Path to the JSON file holding all API keys and OpenSky OAuth2 credentials.
# See secrets.template.json for the expected structure.
# This file is gitignored and must be created locally.
SECRETS_FILE = "secrets.json"

# ── Flight info provider ─────────────────────────────────────
# Choose which API to use for flight plan details (route, times, aircraft)
# Options: "skylink" or "aviationstack"
FLIGHTINFO_PROVIDER = "skylink"

# ── Static lookup tables (CSV files in the project folder) ───
# ICAO airport code -> airport name, country code
AIRPORTS_CSV = "iata-icao.csv"

# Country code -> country name
COUNTRIES_CSV = "countries.csv"

# ICAO airline code -> airline name
AIRLINES_CSV = "icao_airlines.csv"
