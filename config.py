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

# OpenSky credentials (optional – increases request limit)
# Free account at https://opensky-network.org/
OPENSKY_USER = ""
OPENSKY_PASS = ""

# AviationStack API key for flight plan data (route, times, aircraft type)
# Free account at https://aviationstack.com/
# Leave empty to disable this feature
AVIATIONSTACK_KEY = ""
