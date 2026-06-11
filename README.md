# raspberryRadar

A real-time flight radar display for the Raspberry Pi. Shows all aircraft flying over your location using live data from the OpenSky Network, rendered as a dark radar screen with Pygame.

---

## Features

- Live aircraft positions updated every 15 seconds (configurable)
- Radar-style display with range rings and heading indicators
- Color-coded altitude layers (blue / green / amber)
- Click or tap any aircraft label to open a detail panel
- Detail panel shows ICAO, callsign, country, altitude, speed, heading, and distance from home
- Optional flight plan data (origin, destination, times, aircraft type) via AviationStack API
- Daily cache for flight plan lookups — each callsign queried at most once per day
- Autostart on boot via systemd

---

## Files

| File | Description |
|---|---|
| `config.py` | All user settings: coordinates, radius, resolution, API keys |
| `api.py` | OpenSky Network API query and helper functions |
| `main.py` | Pygame radar display — main entry point |
| `flightinfo.py` | AviationStack flight plan lookup with daily cache |
| `install.sh` | Installs all dependencies on Raspberry Pi OS |
| `autostart.sh` | Registers a systemd service for autostart on boot |

---

## Quick Start

### 1. Copy files to the Pi

Via network:
```bash
scp -r raspberryRadar/ pi@<IP-ADDRESS>:~/
```
Or copy via USB stick.

### 2. Run the installer

```bash
cd ~/raspberryRadar
bash install.sh
```

### 3. Set your coordinates

```bash
nano config.py
```

Set `HOME_LAT` and `HOME_LON` to your GPS coordinates.
You can find them by right-clicking your house in Google Maps — the first line shown is your coordinates.

### 4. Launch

```bash
python3 main.py
```

Press `ESC` or `Q` to quit. Press either key once to close an open detail panel, twice to exit the app.

### 5. Enable autostart (optional)

```bash
bash autostart.sh
```

The radar will now launch automatically on every boot.

Manage the service:
```bash
sudo systemctl start raspberryradar
sudo systemctl stop raspberryradar
sudo systemctl status raspberryradar
```

---

## Configuration (`config.py`)

| Parameter | Default | Description |
|---|---|---|
| `HOME_LAT` | `51.4365` | Home latitude (decimal degrees) |
| `HOME_LON` | `6.9147` | Home longitude (decimal degrees) |
| `HOME_NAME` | `"HOME"` | Label shown at radar center |
| `RADIUS` | `0.15` | Search radius in degrees (~17 km) |
| `UPDATE_INTERVAL` | `15` | Seconds between OpenSky API refreshes |
| `SCREEN_WIDTH` | `800` | Display width in pixels |
| `SCREEN_HEIGHT` | `480` | Display height in pixels |
| `FULLSCREEN` | `False` | `True` for fullscreen, `False` for windowed |
| `OPENSKY_USER` | `""` | OpenSky username (optional) |
| `OPENSKY_PASS` | `""` | OpenSky password (optional) |
| `AVIATIONSTACK_KEY` | `""` | AviationStack API key (optional) |

**Radius guide:**

| RADIUS value | Approximate coverage |
|---|---|
| `0.15` | ~17 km — your immediate area |
| `0.5` | ~55 km — regional |
| `0.8` | ~89 km — wide area |
| `1.0` | ~111 km — maximum recommended |

---

## Color Legend

| Color | Altitude |
|---|---|
| Blue | Above 8,000 m — cruise altitude |
| Green | 3,000 – 8,000 m — mid altitude |
| Amber | Below 3,000 m — low altitude / approach |

---

## APIs

### OpenSky Network (required)
Provides live aircraft positions, altitude, speed, and heading.

- Free to use without an account (rate-limited)
- Free account at https://opensky-network.org/ increases the request limit
- Set `OPENSKY_USER` and `OPENSKY_PASS` in `config.py` to use your account

Example query for your location:
```
https://opensky-network.org/api/states/all?lamin=51.28&lamax=51.59&lomin=6.76&lomax=7.06
```

### AviationStack (optional)
Provides flight plan data: origin, destination, scheduled and actual times, aircraft type.

- Free plan: 500 requests/month (no credit card required)
- Sign up at https://aviationstack.com/
- Set `AVIATIONSTACK_KEY` in `config.py` to enable
- Results are cached daily — each flight is only looked up once per day
- Leave the key empty to run in position-only mode

API calls and responses are logged to `aviationstack.log` for debugging.

---

## Recommended Display Resolutions

| Display | `SCREEN_WIDTH` | `SCREEN_HEIGHT` |
|---|---|---|
| 7" Waveshare HDMI | 800 | 480 |
| 5" Waveshare HDMI | 800 | 480 |
| 10" standard HDMI | 1280 | 800 |
| PC testing (windowed) | 800 | 600 |

---

## Troubleshooting

**No aircraft visible**
- Check your internet connection on the Pi
- Increase `RADIUS` in `config.py` — a small radius may show no traffic
- OpenSky may occasionally be slow to respond; the display shows `● LOADING...` while waiting

**Flight plan data not loading**
- Check `aviationstack.log` for error details
- Delete `flightinfo_cache.json` to force a fresh lookup
- The AviationStack free plan only returns data for currently active flights

**Display too small / text hard to read**
- Use a 7" display instead of 5" for the same 800×480 resolution
- Increase font sizes in `main.py` if needed
