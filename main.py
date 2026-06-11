#!/usr/bin/env python3
"""
raspberryRadar – Main Display
Radar view of live aircraft using the OpenSky API.
Click/touch a label box to open a detail panel with AviationStack flight data.
"""

import pygame
import math
import threading
import time
from datetime import datetime

from config import (HOME_LAT, HOME_LON, HOME_NAME, RADIUS,
                    SCREEN_WIDTH, SCREEN_HEIGHT,
                    UPDATE_INTERVAL, FULLSCREEN, AVIATIONSTACK_KEY)
from api import fetch_flights, distance_km, altitude_to_fl, velocity_kmh
from flightinfo import fetch_flightinfo


# ── Colors ───────────────────────────────────────────────────
BG           = (13,  17,  23)
GRID         = (30,  65,  47)
HOME_COLOR   = (29, 158, 117)
TEXT_DIM     = (100, 130, 110)
TEXT_BRIGHT  = (93, 202, 165)
TEXT_WHITE   = (220, 235, 228)
DETAIL_BG    = (18,  28,  22)
DETAIL_BORDER= (29, 158, 117)
ACCENT       = (55, 138, 221)

def plane_color(altitude_m):
    if altitude_m > 8000:
        return (55, 138, 221)   # Blue  – cruise
    elif altitude_m > 3000:
        return (29, 158, 117)   # Green – mid altitude
    else:
        return (186, 117,  23)  # Amber – low altitude


# ── Coordinates → screen position ────────────────────────────
def latlon_to_screen(lat, lon, cx, cy, scale):
    dx = (lon - HOME_LON) * scale * math.cos(math.radians(HOME_LAT))
    dy = (lat - HOME_LAT) * scale * (-1)
    return int(cx + dx), int(cy + dy)


# ── Aircraft triangle ─────────────────────────────────────────
def draw_plane(surface, x, y, heading, color, size=10):
    rad = math.radians(heading - 90)
    tip   = (x + size     * math.cos(rad),           y + size     * math.sin(rad))
    left  = (x + size*0.5 * math.cos(rad + 2.4),     y + size*0.5 * math.sin(rad + 2.4))
    right = (x + size*0.5 * math.cos(rad - 2.4),     y + size*0.5 * math.sin(rad - 2.4))
    pygame.draw.polygon(surface, color, [tip, left, right])
    pygame.draw.polygon(surface, TEXT_WHITE, [tip, left, right], 1)


# ── Word wrap ─────────────────────────────────────────────────
def wrap_text(font, text, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else [text]


# ── Detail panel ──────────────────────────────────────────────
def draw_detail_box(surface, flight, flightinfo, loading_info,
                    screen_w, screen_h, font_title, font_body, font_small):
    PAD       = 20
    LABEL_W   = 100
    COL_GAP   = 10
    MAX_BOX_W = screen_w - 40
    LINE_H    = 24
    TITLE_H   = 50

    cs    = flight["callsign"] or flight["icao"]
    fl    = altitude_to_fl(flight["altitude"])
    spd   = velocity_kmh(flight["velocity"])
    hdg   = int(flight["heading"])
    alt_m = int(flight["altitude"])
    alt_ft= int(flight["altitude"] * 3.28084)
    dist  = distance_km(HOME_LAT, HOME_LON, flight["lat"], flight["lon"])

    def compass(h):
        return ["N","NE","E","SE","S","SW","W","NW"][round(h / 45) % 8]

    # ── Base rows (always shown) ──────────────────────────────
    rows = [
        ("ICAO",         flight["icao"].upper(),                          TEXT_WHITE),
        ("Callsign",     cs,                                               TEXT_WHITE),
        ("Country",      flight["country"],                                TEXT_WHITE),
        ("Flight Level", fl,                                               TEXT_WHITE),
        ("Altitude",     f"{alt_m} m  /  {alt_ft} ft",                    TEXT_WHITE),
        ("Speed",        f"{spd} km/h",                                    TEXT_WHITE),
        ("Heading",      f"{hdg}°  {compass(hdg)}",                        TEXT_WHITE),
        ("Position",     f"{flight['lat']:.4f}°N  {flight['lon']:.4f}°E", TEXT_WHITE),
        ("Distance",     f"{dist:.1f} km from {HOME_NAME}",               TEXT_WHITE),
    ]

    # ── Flight plan rows (AviationStack) ─────────────────────
    if AVIATIONSTACK_KEY:
        rows.append(("─" * 12, "", TEXT_DIM))

        if loading_info:
            rows.append(("Route", "Loading flight data...", TEXT_DIM))
        elif flightinfo:
            fi = flightinfo
            orig = f"{fi['origin_iata']}  {fi['origin_name']}"
            dest = f"{fi['dest_iata']}  {fi['dest_name']}"
            rows += [
                ("From",          orig,                       ACCENT),
                ("To",            dest,                       ACCENT),
                ("Airline",       fi["airline"],              TEXT_WHITE),
                ("Aircraft",      fi["aircraft_type"] or "–", TEXT_WHITE),
                ("Dep. scheduled",fi["scheduled_dep"],        TEXT_WHITE),
                ("Dep. actual",   fi["actual_dep"],           TEXT_WHITE),
                ("Arr. scheduled",fi["scheduled_arr"],        TEXT_WHITE),
                ("Arr. estimated",fi["estimated_arr"],        TEXT_WHITE),
            ]
        else:
            rows.append(("Route", "No data available", TEXT_DIM))

    # ── Calculate box width ───────────────────────────────────
    min_w = font_title.size(cs)[0] + PAD * 2
    val_w = max((font_body.size(v)[0] for _, v, _ in rows if v and v[0] != "─"), default=100)
    W     = max(min_w, min(PAD + LABEL_W + COL_GAP + val_w + PAD, MAX_BOX_W))
    val_max_w = W - PAD - LABEL_W - COL_GAP - PAD

    # ── Prepare rows with word wrap ───────────────────────────
    prepared = []
    for label, value, color in rows:
        if label.startswith("─"):
            prepared.append(("sep", [], TEXT_DIM))
        else:
            lines = wrap_text(font_body, value, val_max_w) if value else [""]
            prepared.append((label, lines, color))

    total_lines = sum(1 if t == "sep" else len(lines) for t, lines, _ in prepared)
    H = TITLE_H + total_lines * LINE_H + 30

    x = max(10, (screen_w - W) // 2)
    y = max(10, (screen_h - H) // 2)

    # ── Draw box ──────────────────────────────────────────────
    pygame.draw.rect(surface, DETAIL_BG,     (x, y, W, H), border_radius=10)
    pygame.draw.rect(surface, DETAIL_BORDER, (x, y, W, H), 2, border_radius=10)

    surface.blit(font_title.render(cs, True, TEXT_WHITE), (x + PAD, y + 14))
    pygame.draw.line(surface, DETAIL_BORDER,
                     (x + 10, y + TITLE_H - 4), (x + W - 10, y + TITLE_H - 4), 1)

    cursor_y = y + TITLE_H + 4
    for label, lines, color in prepared:
        if label == "sep":
            pygame.draw.line(surface, GRID,
                             (x + PAD, cursor_y + LINE_H // 2),
                             (x + W - PAD, cursor_y + LINE_H // 2), 1)
            cursor_y += LINE_H
            continue
        surface.blit(font_small.render(label, True, TEXT_DIM), (x + PAD, cursor_y + 2))
        for line in lines:
            surface.blit(font_body.render(line, True, color),
                         (x + PAD + LABEL_W + COL_GAP, cursor_y))
            cursor_y += LINE_H

    hint = font_small.render("Tap to close", True, TEXT_DIM)
    surface.blit(hint, (x + W // 2 - hint.get_width() // 2, y + H - 20))

    return pygame.Rect(x, y, W, H)


# ── Main app ──────────────────────────────────────────────────
class FlightradarApp:
    def __init__(self):
        pygame.init()
        flags = pygame.FULLSCREEN if FULLSCREEN else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption("raspberryRadar")
        pygame.mouse.set_visible(not FULLSCREEN)

        self.font_title = pygame.font.SysFont("monospace", 20, bold=True)
        self.font_lg    = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_md    = pygame.font.SysFont("monospace", 13, bold=True)
        self.font_sm    = pygame.font.SysFont("monospace", 11)
        self.font_xs    = pygame.font.SysFont("monospace", 10)

        self.cx = SCREEN_WIDTH  // 2
        self.cy = SCREEN_HEIGHT // 2
        self.max_px = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 2 - 30
        self.scale  = self.max_px / RADIUS

        self.flights      = []
        self.last_update  = "–"
        self.loading      = True
        self.selected     = None
        self.label_rects  = []

        # Flight info state
        self.flightinfo   = None    # currently loaded flight plan info
        self.loading_info = False   # currently fetching?

        self._start_update_thread()

    def _start_update_thread(self):
        def loop():
            while True:
                self.flights     = fetch_flights()
                self.last_update = datetime.now().strftime("%H:%M:%S")
                self.loading     = False
                time.sleep(UPDATE_INTERVAL)
        threading.Thread(target=loop, daemon=True).start()

    def _load_flightinfo(self, callsign):
        """Fetch flight plan data in a background thread."""
        self.flightinfo   = None
        self.loading_info = True
        def _fetch():
            self.flightinfo   = fetch_flightinfo(callsign)
            self.loading_info = False
        threading.Thread(target=_fetch, daemon=True).start()

    # ── Hit test ──────────────────────────────────────────────
    def _flight_at(self, mx, my):
        # Check label boxes first (larger click target)
        for rect, f in self.label_rects:
            if rect.collidepoint(mx, my):
                return f
        # Fallback: aircraft triangle
        for f in self.flights:
            x, y = latlon_to_screen(f["lat"], f["lon"],
                                    self.cx, self.cy, self.scale)
            if math.hypot(mx - x, my - y) < 14:
                return f
        return None

    # ── Grid ──────────────────────────────────────────────────
    def draw_grid(self):
        for r in [0.25, 0.5, 0.75, 1.0]:
            px = int(self.max_px * r)
            pygame.draw.circle(self.screen, GRID, (self.cx, self.cy), px, 1)
            km = int(RADIUS * r * 111)
            self.screen.blit(
                self.font_xs.render(f"{km}km", True, GRID),
                (self.cx + px + 4, self.cy - 8))

        pygame.draw.line(self.screen, GRID,
                         (self.cx - self.max_px, self.cy),
                         (self.cx + self.max_px, self.cy), 1)
        pygame.draw.line(self.screen, GRID,
                         (self.cx, self.cy - self.max_px),
                         (self.cx, self.cy + self.max_px), 1)

        pygame.draw.circle(self.screen, HOME_COLOR, (self.cx, self.cy), 6)
        self.screen.blit(
            self.font_sm.render(HOME_NAME, True, HOME_COLOR),
            (self.cx + 10, self.cy + 4))

    # ── Aircraft ──────────────────────────────────────────────
    def draw_flights(self):
        self.label_rects = []

        for f in self.flights:
            x, y = latlon_to_screen(f["lat"], f["lon"],
                                    self.cx, self.cy, self.scale)
            if math.hypot(x - self.cx, y - self.cy) > self.max_px:
                continue

            color = plane_color(f["altitude"])

            if self.selected and self.selected["icao"] == f["icao"]:
                pygame.draw.circle(self.screen, color, (x, y), 16, 1)

            draw_plane(self.screen, x, y, f["heading"], color, size=10)

            fl  = altitude_to_fl(f["altitude"])
            spd = velocity_kmh(f["velocity"])
            cs  = f["callsign"] or f["icao"]

            BOX_W, BOX_H = 122, 44
            box_x = x + 14
            box_y = y - 12
            if box_x + BOX_W > SCREEN_WIDTH:  box_x = x - BOX_W - 14
            if box_y + BOX_H > SCREEN_HEIGHT: box_y = y - BOX_H - 4
            if box_y < 0:                     box_y = y + 14

            rect = pygame.Rect(box_x - 3, box_y - 3, BOX_W, BOX_H)
            pygame.draw.rect(self.screen, (13, 30, 22), rect, border_radius=5)
            pygame.draw.rect(self.screen, color,        rect, 1, border_radius=5)

            self.screen.blit(self.font_lg.render(cs, True, TEXT_BRIGHT), (box_x, box_y))
            self.screen.blit(self.font_sm.render(f"{fl} · {spd}km/h", True, TEXT_DIM),
                             (box_x, box_y + 19))

            self.label_rects.append((rect, f))

    # ── Status bar ────────────────────────────────────────────
    def draw_statusbar(self):
        live_col = HOME_COLOR if not self.loading else (140, 90, 20)
        self.screen.blit(
            self.font_md.render("● LIVE" if not self.loading else "● LOADING...",
                                True, live_col), (12, 8))
        self.screen.blit(
            self.font_sm.render(f"{HOME_LAT:.4f}°N  {HOME_LON:.4f}°E",
                                True, TEXT_DIM), (100, 10))
        self.screen.blit(
            self.font_sm.render(f"{len(self.flights)} aircraft · {int(RADIUS*111)}km",
                                True, TEXT_DIM), (SCREEN_WIDTH - 190, 10))
        self.screen.blit(
            self.font_xs.render(f"Updated: {self.last_update}", True, TEXT_DIM),
            (12, SCREEN_HEIGHT - 15))

        for i, (txt, col) in enumerate([("■ >8000m", (55,138,221)),
                                         ("■ >3000m", (29,158,117)),
                                         ("■ <3000m", (186,117,23))]):
            self.screen.blit(self.font_xs.render(txt, True, col),
                             (SCREEN_WIDTH - 90, SCREEN_HEIGHT - 15 - i * 14))

    # ── Main loop ─────────────────────────────────────────────
    def run(self):
        clock   = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        if self.selected:
                            self.selected     = None
                            self.flightinfo   = None
                            self.loading_info = False
                        else:
                            running = False

                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    if event.type == pygame.FINGERDOWN:
                        mx = int(event.x * SCREEN_WIDTH)
                        my = int(event.y * SCREEN_HEIGHT)
                    else:
                        mx, my = event.pos

                    if self.selected:
                        self.selected     = None
                        self.flightinfo   = None
                        self.loading_info = False
                    else:
                        hit = self._flight_at(mx, my)
                        if hit:
                            self.selected = hit
                            self._load_flightinfo(hit["callsign"])

            self.screen.fill(BG)
            self.draw_grid()
            self.draw_flights()
            self.draw_statusbar()

            if self.selected:
                match = next((f for f in self.flights
                              if f["icao"] == self.selected["icao"]), None)
                if match:
                    self.selected = match
                draw_detail_box(
                    self.screen, self.selected,
                    self.flightinfo, self.loading_info,
                    SCREEN_WIDTH, SCREEN_HEIGHT,
                    self.font_title, self.font_md, self.font_sm)

            pygame.display.flip()
            clock.tick(30)

        pygame.quit()


if __name__ == "__main__":
    FlightradarApp().run()
