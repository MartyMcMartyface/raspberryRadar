#!/usr/bin/env python3
"""
raspberryRadar – Secrets loader
Loads all API keys and OpenSky OAuth2 credentials from a single JSON file
(path configured via SECRETS_FILE in config.py).

Expected structure (see secrets.template.json):
{
  "opensky": {"clientId": "...", "clientSecret": "..."},
  "skylink_key": "...",
  "aviationstack_key": "..."
}

If the file is missing or a key is absent, empty values are returned and
the corresponding feature is disabled (anonymous OpenSky access, no
flight info lookups).
"""

import json
import os

from config import SECRETS_FILE

BASE_DIR    = os.path.dirname(__file__)
SECRETS_PATH = os.path.join(BASE_DIR, SECRETS_FILE)


def _load_secrets():
    try:
        with open(SECRETS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {SECRETS_PATH} not found. "
              f"Copy secrets.template.json to {SECRETS_FILE} and fill in your keys.")
        return {}
    except Exception as e:
        print(f"Warning: could not read {SECRETS_PATH}: {e}")
        return {}


_secrets = _load_secrets()

# OpenSky OAuth2 credentials
OPENSKY_CLIENT_ID     = (_secrets.get("opensky") or {}).get("clientId", "")
OPENSKY_CLIENT_SECRET = (_secrets.get("opensky") or {}).get("clientSecret", "")

# Flight info provider keys
SKYLINK_KEY       = _secrets.get("skylink_key", "")
AVIATIONSTACK_KEY = _secrets.get("aviationstack_key", "")
