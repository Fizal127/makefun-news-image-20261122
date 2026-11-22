#!/usr/bin/env python3
"""The Day in One Image - Sunday 22 November 2026.

make.fun bounty: "Sum up 22 November's world news in one image"
(slug: news-image-20261122). Writes one 1024x1024 PNG to
/output/entry.png (or ./output/entry.png when /output is absent).

Self-contained, standard library only. A small rasterizer with an
embedded 5x7 bitmap font draws a dense one-page front page in the
style of a picture newspaper: a huge date masthead, a strip of six
big numbers, a coloured region bar, three lead stories with large
drawn illustrations (Iran's strike on Bahrain, the capture of cartel
boss "El Chapo Isidro" in Mexico, the Riemann proof checking out),
ten more stories in a grid with small drawn pictograms, a numbered
world map, a 22-item "also on" list, a date-check box and a sources
line - 35 stories in all, each one checked against reporting of
Sunday 22 November 2026. A minimal PNG encoder (zlib) writes the
bytes. No network, no clock, no randomness: the same bytes come out
on every run.
"""

import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024
PAPER = (250, 246, 236)
CARD = (255, 253, 247)
INK = (18, 18, 18)
MUTED = (96, 90, 78)
NAVY = (27, 52, 88)
RED = (196, 32, 32)
GOLD = (232, 180, 44)
TEAL = (18, 96, 88)
SKY = (58, 140, 200)
LIGHTSKY = (150, 205, 240)
DUSK = (32, 42, 96)
SUNSET = (240, 110, 50)
GREEN = (34, 139, 70)
DARKGREEN = (18, 64, 52)
SAND = (240, 200, 90)
ROYAL = (40, 80, 180)
PURPLE = (88, 52, 138)
WHITE = (255, 255, 255)
ORANGE = (240, 130, 30)
YELLOW = (250, 210, 60)
LIGHTRED = (255, 140, 120)
LIGHTBLUE = (200, 205, 225)

# 5x7 bitmap font: each glyph is 7 rows of 5 bits (MSB = left column).
# All copy is rendered in capitals, broadsheet-headline style.
GLYPHS = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ";": (0, 0x0C, 0, 0, 0x0C, 0x04, 0x08),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x06, 0x04, 0, 0x04),
    "-": (0, 0, 0, 0x0E, 0, 0, 0),
    "\u2014": (0, 0, 0, 0x1F, 0, 0, 0),
    "\u2013": (0, 0, 0, 0x1F, 0, 0, 0),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "\u2019": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    '"': (0x0A, 0x0A, 0x0A, 0, 0, 0, 0),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "%": (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "+": (0, 0x04, 0x04, 0x0E, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    "*": (0, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0),
    "\u2022": (0, 0, 0x0C, 0x0C, 0x0C, 0, 0),
    "\u00b7": (0, 0, 0, 0x0C, 0, 0, 0),
    "[": (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    "]": (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    "<": (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    ">": (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
}

# The day's news, Sunday 22 November 2026. Facts as reported that day.
# Every number below was checked against reporting of 22 November 2026;
# figures that could not be verified were dropped or softened. Saturday
# events are shown only where they were first reported on Sunday.
KICKER_LEFT = "The World in One Day"
KICKER_RIGHT = (
    "35 stories \u00b7 7 regions \u00b7 Every one dated Sunday 22 November 2026"
)
MASTHEAD = "Sunday 22 November 2026"
SUBHEAD = [
    "Iran hits Bahrain \u00b7 Mexico seizes 'El Chapo Isidro'",
    "Riemann proof checks out \u00b7 COP31 stuck in overtime",
]
STATS = [
    ("11", "Killed in Sinaloa raid", "7 gunmen, 4 soldiers"),
    ("720/9", "India's record Test total", "in Wellington"),
    ("186", "Drones fired at Ukraine", "161 shot down"),
    ("$90", "Oil near $90 a barrel", "as Gulf tensions rise"),
    ("24", "Dead as a boat sinks", "in southern Nigeria"),
    ("17M", "Lines of Lean code checked", "for the Riemann proof"),
]
REGIONS = [
    ("Europe", 9, NAVY),
    ("Asia", 3, RED),
    ("Mideast", 7, (200, 150, 30)),
    ("Africa", 2, GREEN),
    ("Americas", 7, PURPLE),
    ("Oceania", 2, TEAL),
    ("Global", 5, (90, 90, 90)),
]
LEADS = [
    {
        "num": 1,
        "place": "Bahrain \u00b7 Gulf",
        "banner": "Bahrain",
        "credit": "Bahrain says \u00b7 One Turn",
        "headline": "Iran hits Bahrain; tankers struck off Hormuz",
        "summary": (
            "Iran struck a civilian industrial site in Bahrain late "
            "Saturday, Bahrain says, and two oil tankers were hit "
            "near the Strait of Hormuz. Oil held near $90. (One Turn)"
        ),
    },
    {
        "num": 2,
        "place": "Guasave, Mexico \u00b7 Justice",
        "banner": "El Chapo Isidro",
        "credit": "Forces say \u00b7 One Turn",
        "headline": "Mexico seizes 'El Chapo Isidro'; 11 killed",
        "summary": (
            "Special forces arrested cartel boss Fausto Isidro Meza "
            "Flores in Sinaloa. Seven gunmen and four soldiers died "
            "in the operation. He was on the FBI's most wanted list. "
            "(One Turn)"
        ),
    },
    {
        "num": 3,
        "place": "San Francisco \u00b7 Science",
        "banner": "Riemann: proved?",
        "credit": "Lean checkers \u00b7 WSJ",
        "headline": "The Riemann proof checks out",
        "summary": (
            "A claim to prove the Riemann hypothesis, posted Friday "
            "by Anthropic's Levent Alpoge with Claude, passed its "
            "machine check on Saturday: 17 million lines of Lean "
            "code verified. (WSJ)"
        ),
    },
]
GRID = [
    {
        "num": 4, "place": "Antalya \u00b7 Climate",
        "banner": "COP31: overtime", "credit": "Day 2 of overtime \u00b7 One Turn",
        "headline": "COP31's second day of overtime",
        "summary": "Still no text; fossil fuels divide the room.",
        "pic": "cop",
    },
    {
        "num": 5, "place": "Kryvyi Rih \u00b7 War",
        "banner": "Kryvyi Rih hit", "credit": "Toll rises \u00b7 Kyiv Post",
        "headline": "Missile kills boy and medic",
        "summary": "A second strike hit rescuers; 58 hurt.",
        "pic": "kryvyi",
    },
    {
        "num": 6, "place": "Gulf of Finland \u00b7 War",
        "banner": "Sparta II ablaze", "credit": "Finland says \u00b7 Reuters",
        "headline": "Drones set a Russian ship ablaze",
        "summary": "It drifted into Finnish waters.",
        "pic": "sparta",
    },
    {
        "num": 7, "place": "Wellington \u00b7 Cricket",
        "banner": "India: 720/9", "credit": "Day four \u00b7 ESPN",
        "headline": "India pile up a record 720/9",
        "summary": "Rahul 136, Pant 128; NZ 119/2 at stumps.",
        "pic": "wellington",
    },
    {
        "num": 8, "place": "Las Vegas \u00b7 Motor racing",
        "banner": "Verstappen wins", "credit": "35 lead changes \u00b7 F1",
        "headline": "Verstappen wins a Vegas thriller",
        "summary": "Norris 2nd by 0.6s; Piastri 3rd.",
        "pic": "vegas",
    },
    {
        "num": 9, "place": "Riyadh \u00b7 Conflict",
        "banner": "Riyadh: 3 stopped", "credit": "Coalition says \u00b7 One Turn",
        "headline": "Saudis stop three Houthi missiles",
        "summary": "Hodeidah port struck in reply.",
        "pic": "riyadh",
    },
    {
        "num": 10, "place": "Manipur \u00b7 Health",
        "banner": "Manipur: bad drink", "credit": "Chief minister \u00b7 One Turn",
        "headline": "Toxic drink kills 11 in Manipur",
        "summary": "More than 180 are in hospital.",
        "pic": "manipur",
    },
    {
        "num": 11, "place": "Washington \u00b7 Cyber",
        "banner": "FBI: database hit", "credit": "Trump confirms \u00b7 CNBC",
        "headline": "FBI crime database hacked",
        "summary": "The NCIC system was breached.",
        "pic": "fbi",
    },
    {
        "num": 12, "place": "Brasilia \u00b7 Politics",
        "banner": "Bolsonaro: ICU", "credit": "Reported \u00b7 One Turn",
        "headline": "Bolsonaro in intensive care",
        "summary": "A bowel obstruction put him in ICU.",
        "pic": "bolsonaro",
    },
    {
        "num": 13, "place": "Tel Aviv \u00b7 Business",
        "banner": "Amazon: $7.5bn", "credit": "Near a deal \u00b7 Crypto Briefing",
        "headline": "Amazon nears a $7.5bn AI deal",
        "summary": "Target: Israeli startup Decart.",
        "pic": "amazon",
    },
]
ALSO = [
    ("14", "Basra", "Fire at Hartha power station kills four", "Iraqi media"),
    ("15", "S. Nigeria", "Mourners' boat sinks; 24 dead", "One Turn"),
    ("16", "Copenhagen", "Denmark expels a Russian attache", "One Turn"),
    ("17", "Geneva", "UN agrees autonomous weapons rules", "Daily Persp."),
    ("18", "London", "Leeds stun Chelsea 4-1 at the Bridge", "Sky Sports"),
    ("19", "Cocoa, Fla.", "St Johns River breaks 73-year record", "One Turn"),
    ("20", "Gaza", "Israeli strikes go on; aid vehicle hit", "One Turn"),
    ("21", "Beirut", "Aoun blames Israel and Iran for threats", "One Turn"),
    ("22", "London", "Burnham eyes rejoining the EU", "One Turn"),
    ("23", "Brussels", "EU proposes a digital tax", "Daily Persp."),
    ("24", "Washington", "Trump: report Congress requests", "One Turn"),
    ("25", "New York", "China renews UN bid to blacklist BLA", "iqmia"),
    ("26", "Mastung", "Pakistan says 15 militants killed", "iqmia"),
    ("27", "Hormuz", "British swimmer braves the strait", "Daily Persp."),
    ("28", "Sydney", "Bondi rescuers marry by the beach", "News Media Hse"),
    ("29", "Geneva", "WHO warns on antibiotic resistance", "Daily Edition"),
    ("30", "Cairo", "Egypt-born Palestinians still foreigners", "Daily Ed."),
    ("31", "Brussels", "EU plastic export ban in force", "Daily Edition"),
    ("32", "Newcastle", "Man City stumble; Arsenal held", "iqmia"),
    ("33", "Hodeidah", "Coalition strikes the Houthi port", "One Turn"),
    ("34", "Vyshhorod", "Drone hits a five-storey block; 2 hurt", "h.ua"),
    ("35", "Armonk", "IBM shows off a 520-qubit chip", "iqmia"),
]
DATE_CHECK = (
    "Left out as Saturday 21 November's news: the EU-Indonesia trade "
    "deal signed in Brussels and Friday's US stock sell-off. Not yet "
    "happened, so not shown: any final COP31 text and the last day of "
    "the Wellington Test."
)
FOOTER = (
    "Every story here happened, or was first reported, on "
    "Sunday 22 November 2026. Officials' counts are attributed."
)
SOURCES_LINE = "Sources named beside each story \u00b7 Original drawings"


class Canvas:
    """An RGB raster with a few drawing primitives."""

    def __init__(self):
        self.buf = bytearray(bytes(PAPER) * (W * H))

    def rect(self, x, y, w, h, color):
        x0 = max(x, 0)
        y0 = max(y, 0)
        x1 = min(x + w, W)
        y1 = min(y + h, H)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * W + x0) * 3
            self.buf[i:i + len(row)] = row

    def hline(self, x0, x1, y, color, t=1):
        self.rect(x0, y, x1 - x0, t, color)

    def vline(self, x, y0, y1, color, t=1):
        self.rect(x, y0, t, y1 - y0, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        """Bresenham line, with a square brush of side t."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.rect(x, y, t, t, color)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle_outline(self, cx, cy, r, color, t=2):
        """Midpoint circle outline."""
        x, y, d = 0, r, 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y),
                           (cx + x, cy - y), (cx - x, cy - y),
                           (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.rect(px, py, t, t, color)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def disc(self, cx, cy, r, color):
        """Filled circle, scanline by scanline."""
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - half, cy + dy, 2 * half + 1, 1, color)

    def half_disc_right(self, cx, cy, r, color):
        """Right half of a filled circle."""
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.rect(cx, cy + dy, half + 1, 1, color)

    def ellipse(self, cx, cy, rx, ry, color):
        """Filled ellipse."""
        for dy in range(-ry, ry + 1):
            half = int(rx * (1 - (dy * dy) / (ry * ry)) ** 0.5)
            self.rect(cx - half, cy + dy, 2 * half + 1, 1, color)

    def ellipse_outline(self, cx, cy, rx, ry, color, t=2):
        """Ellipse outline from its scanline chords."""
        for dy in range(-ry, ry + 1):
            half = int(rx * (1 - (dy * dy) / (ry * ry)) ** 0.5)
            self.rect(cx - half, cy + dy, t, t, color)
            self.rect(cx + half, cy + dy, t, t, color)
        for dx in range(-rx, rx + 1):
            half = int(ry * (1 - (dx * dx) / (rx * rx)) ** 0.5)
            self.rect(cx + dx, cy - half, t, t, color)
            self.rect(cx + dx, cy + half, t, t, color)

    def poly(self, pts, color):
        """Filled polygon, scanline fill with integer math."""
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(xs[i], y, xs[i + 1] - xs[i] + 1, 1, color)

    def burst(self, cx, cy, r, color, core=None):
        """Eight-point starburst: four diamonds plus a bright core."""
        self.poly([(cx - r, cy), (cx, cy - r // 3),
                   (cx + r, cy), (cx, cy + r // 3)], color)
        self.poly([(cx, cy - r), (cx + r // 3, cy),
                   (cx, cy + r), (cx - r // 3, cy)], color)
        d = int(r * 0.7)
        self.poly([(cx - d, cy - d), (cx + d // 3, cy - d // 3),
                   (cx + d, cy + d), (cx - d // 3, cy + d // 3)], color)
        self.poly([(cx + d, cy - d), (cx + d // 3, cy - d // 3),
                   (cx - d, cy + d), (cx - d // 3, cy + d // 3)], color)
        if core is not None:
            self.disc(cx, cy, max(2, r // 3), core)


def outline(cv, x, y, w, h, color, t=2):
    cv.rect(x, y, w, t, color)
    cv.rect(x, y + h - t, w, t, color)
    cv.rect(x, y, t, h, color)
    cv.rect(x + w - t, y, t, h, color)


def text_width(s, scale):
    return len(s) * 6 * scale


def draw_text(cv, x, y, s, scale, color):
    """Draw upper-cased bitmap text; returns the x after the last glyph."""
    cx = x
    for ch in s.upper():
        glyph = GLYPHS.get(ch, GLYPHS["?"])
        for r in range(7):
            bits = glyph[r]
            if not bits:
                continue
            for c in range(5):
                if (bits >> (4 - c)) & 1:
                    cv.rect(cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def draw_centered(cv, y, s, scale, color):
    x = (W - text_width(s.upper(), scale)) // 2
    draw_text(cv, x, y, s, scale, color)


def wrap_text(s, max_w, scale):
    """Greedy word wrap of upper-cased text to a pixel width."""
    words = s.upper().split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_width(trial, scale) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        while text_width(word, scale) > max_w:
            n = max(1, max_w // (6 * scale))
            lines.append(word[:n])
            word = word[n:]
        cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, max_w, lines, scale, color, leading=3):
    for line in lines:
        draw_text(cv, x, y, line, scale, color)
        y += 7 * scale + leading
    return y


def draw_story(cv, x, y, width, story, head_scale=3, tag_color=NAVY,
               leading=3, stat_color=None):
    y = draw_block(cv, x, y, width, [story["tag"]], 2, tag_color, 4)
    y = draw_block(cv, x, y, width,
                   wrap_text(story["headline"], width, head_scale),
                   head_scale, INK, leading)
    y = draw_block(cv, x, y, width,
                   wrap_text(story["summary"], width, 2), 2, INK, leading)
    if story.get("stat"):
        y = draw_block(cv, x, y + 2, width, [story["stat"]], 2,
                       stat_color or MUTED, leading)
    return y


def draw_text_right(cv, right_x, y, s, scale, color):
    """Draw text ending at right_x."""
    x = right_x - text_width(s.upper(), scale)
    draw_text(cv, x, y, s, scale, color)
    return x


def label_banner(cv, x, y, text, scale):
    """Red label banner with white text; returns its width."""
    pad = 6 if scale == 2 else 4
    w = text_width(text, scale) + 2 * pad
    h = 7 * scale + 6
    cv.rect(x, y, w, h, RED)
    draw_text(cv, x + pad, y + 3, text, scale, WHITE)
    return w


def credit_strip(cv, x, y, w, text):
    """Black strip with a white credit line."""
    cv.rect(x, y, w, 14, INK)
    draw_text(cv, x + 6, y + 4, text, 1, WHITE)


def num_disc(cv, cx, cy, num, r=7):
    """Red disc with a white number."""
    cv.disc(cx, cy, r, RED)
    s = str(num)
    draw_text(cv, cx - 3 * len(s), cy - 3, s, 1, WHITE)


def arrow_left(cv, x, cy, length, color):
    cv.line(x + length, cy, x + 10, cy, color, 3)
    cv.poly([(x, cy), (x + 10, cy - 6), (x + 10, cy + 6)], color)


def arrow_right(cv, x, cy, length, color):
    cv.line(x, cy, x + length - 10, cy, color, 3)
    cv.poly([(x + length, cy), (x + length - 10, cy - 6),
             (x + length - 10, cy + 6)], color)


# --- Story illustrations -------------------------------------------------

def ill_bahrain(cv, x, y, w, h):
    """The Gulf at dusk: a strait between two shores, an industrial
    site in flames on the island, two tankers on the water, a missile
    trail falling from the sky and an oil-price tag."""
    cv.rect(x, y, w, h, DUSK)
    for fx, fy in ((0.08, 0.10), (0.25, 0.20), (0.45, 0.08),
                   (0.70, 0.15), (0.92, 0.10), (0.58, 0.26),
                   (0.18, 0.36)):
        cv.rect(x + int(fx * w), y + int(fy * h), 2, 2, WHITE)
    # Sea: deep blue with lighter wave lines.
    cv.rect(x, y + 66, w, h - 66, NAVY)
    for wy in (78, 96, 118, 140):
        for wx in range(10, w - 20, 44):
            cv.hline(x + wx, x + wx + 22, y + wy, LIGHTBLUE, 2)
    # Bahrain island: tan shore with towers and tanks.
    cv.poly([(x, y + 66), (x + 40, y + 40), (x + 120, y + 30),
             (x + 200, y + 44), (x + 260, y + 66)], SAND)
    for tx in (70, 100, 130):
        cv.rect(x + tx, y + 18, 8, 26, INK)
        cv.rect(x + tx - 3, y + 12, 14, 6, INK)
    for tx in (170, 205):
        cv.ellipse(x + tx, y + 34, 14, 10, WHITE)
        cv.rect(x + tx - 14, y + 34, 28, 10, WHITE)
    # Flames on the industrial site.
    cv.burst(x + 105, y + 30, 16, ORANGE, core=YELLOW)
    cv.burst(x + 185, y + 38, 11, YELLOW, core=RED)
    # Missile trail from the top right.
    cv.line(x + w - 20, y + 6, x + 190, y + 34, ORANGE, 4)
    cv.line(x + w - 20, y + 6, x + 190, y + 34, WHITE, 2)
    # Two tankers on the water.
    for sx, sy, sw in ((30, 118, 90), (190, 138, 100)):
        cv.rect(x + sx, y + sy, sw, 14, INK)
        cv.rect(x + sx + 12, y + sy - 12, 22, 12, RED)
        cv.rect(x + sx + sw - 20, y + sy - 8, 12, 8, WHITE)
        cv.rect(x + sx, y + sy + 14, sw, 3, (200, 200, 210))
    # Oil price tag.
    cv.rect(x + w - 108, y + h - 26, 100, 20, GOLD)
    draw_text(cv, x + w - 102, y + h - 22, "Oil $90", 1, INK)


def ill_sinaloa(cv, x, y, w, h):
    """A desert raid at sunset: orange sky, purple mountains, a
    helicopter overhead, army trucks on the road and soldiers."""
    cv.rect(x, y, w, h, SUNSET)
    cv.disc(x + 268, y + 22, 14, GOLD)
    cv.poly([(x, y + 78), (x + 60, y + 40), (x + 120, y + 78),
             (x + 190, y + 34), (x + 250, y + 78), (x + w, y + 58),
             (x + w, y + h), (x, y + h)], PURPLE)
    cv.rect(x, y + 92, w, h - 92, (210, 170, 90))
    cv.rect(x, y + 92, w, 3, (120, 80, 40))
    # Helicopter.
    hx, hy = x + 90, y + 30
    cv.ellipse(hx, hy, 26, 8, INK)
    cv.rect(hx - 34, hy - 2, 68, 3, INK)
    cv.rect(hx + 24, hy - 4, 16, 3, INK)
    cv.rect(hx - 30, hy + 6, 4, 10, INK)
    cv.rect(hx + 22, hy + 6, 4, 10, INK)
    # Army trucks on the road.
    for tx in (30, 150):
        cv.rect(x + tx, y + 118, 52, 16, (40, 90, 50))
        cv.rect(x + tx + 52, y + 122, 16, 12, (40, 90, 50))
        cv.rect(x + tx + 56, y + 124, 8, 7, LIGHTBLUE)
        for wx in (tx + 10, tx + 34, tx + 60):
            cv.disc(x + wx, y + 136, 5, INK)
    # Soldiers.
    for sx in (250, 272, 294):
        cv.disc(x + sx, y + 112, 5, NAVY)
        cv.rect(x + sx - 7, y + 118, 14, 22, NAVY)
        cv.rect(x + sx + 6, y + 120, 10, 3, INK)
    # "11" marker: the raid's death toll.
    cv.rect(x + 12, y + h - 26, 96, 20, RED)
    draw_text(cv, x + 18, y + h - 22, "11 killed", 1, WHITE)


def ill_riemann(cv, x, y, w, h):
    """The Riemann proof: a dark board, the zeta zeros lined up on
    one vertical line, a green check, and a ticker of the 17 million
    lines of Lean code that were verified."""
    cv.rect(x, y, w, h, (24, 30, 40))
    for gy in (y + 30, y + 64, y + 98, y + 132):
        cv.hline(x + 8, x + w - 8, gy, (52, 62, 78), 1)
    # The critical line: one straight vertical line of gold.
    lx = x + 150
    cv.line(lx, y + 12, lx, y + h - 52, GOLD, 4)
    # Zeros as white dots sitting on the line.
    for zy in (22, 44, 62, 84, 102, 122, 140):
        cv.disc(lx, y + zy, 4, WHITE)
    # One stray dot off the line, crossed out: the old fear.
    cv.disc(x + 196, y + 52, 4, LIGHTRED)
    cv.line(x + 188, y + 44, x + 204, y + 60, LIGHTRED, 3)
    cv.line(x + 204, y + 44, x + 188, y + 60, LIGHTRED, 3)
    # Green check over the line.
    cv.line(x + 236, y + 60, x + 252, y + 76, GREEN, 6)
    cv.line(x + 252, y + 76, x + 286, y + 34, GREEN, 6)
    # Prime numbers row at the top.
    draw_text(cv, x + 12, y + 10, "2 3 5 7 11 13 17 19 23", 1, LIGHTBLUE)
    draw_text(cv, x + 12, y + 24, "Zeta zeros on one line", 1, WHITE)
    # Ticker: the Lean check.
    cv.rect(x + 12, y + h - 34, w - 24, 24, (52, 62, 78))
    draw_text(cv, x + 18, y + h - 28, "17,000,000 lines of Lean: checked",
              1, WHITE)


# --- Grid pictograms (190x52 each) -------------------------------------

def pic_cop(cv, x, y, w, h):
    """A globe split in two: green half, orange half, a white crack
    down the middle and arrows pulling apart."""
    cv.rect(x, y, w, h, SAND)
    cx, cy, r = x + w // 2, y + h // 2, 20
    cv.disc(cx, cy, r, GREEN)
    cv.half_disc_right(cx, cy, r, ORANGE)
    for dy in (-8, 8):
        half = int((r * r - dy * dy) ** 0.5)
        cv.hline(cx - half, cx + half, cy + dy, WHITE, 2)
    cv.ellipse_outline(cx, cy, 6, r, WHITE, 2)
    cv.circle_outline(cx, cy, r, INK, 2)
    cv.line(cx - 2, cy - r + 2, cx + 3, cy - 8, WHITE, 2)
    cv.line(cx + 3, cy - 8, cx - 3, cy, WHITE, 2)
    cv.line(cx - 3, cy, cx + 3, cy + 8, WHITE, 2)
    cv.line(cx + 3, cy + 8, cx - 2, cy + r - 2, WHITE, 2)
    arrow_left(cv, x + 10, cy, 26, GREEN)
    arrow_right(cv, x + w - 36, cy, 26, RED)


def pic_kryvyi(cv, x, y, w, h):
    """A shelled apartment block with a red-cross ambulance."""
    cv.rect(x, y, w, h, DUSK)
    cv.rect(x + 18, y + 6, 52, h - 6, (120, 120, 130))
    for wy in (12, 24, 36):
        for wx in (26, 44):
            cv.rect(x + wx, y + wy, 10, 8, YELLOW)
    cv.burst(x + 58, y + 10, 9, ORANGE, core=YELLOW)
    cv.line(x + 30, y + 6, x + 30, y + h, INK, 2)
    cv.rect(x + 92, y + 30, 70, 14, WHITE)
    cv.rect(x + 162, y + 33, 16, 11, WHITE)
    cv.rect(x + 92, y + 30, 70, 3, RED)
    cv.rect(x + 120, y + 33, 4, 8, RED)
    cv.rect(x + 117, y + 36, 10, 3, RED)
    for wx in (104, 126, 150, 170):
        cv.disc(x + wx, y + 46, 4, INK)


def pic_sparta(cv, x, y, w, h):
    """A cargo ship burning on a grey sea, drones overhead."""
    cv.rect(x, y, w, 22, LIGHTSKY)
    cv.rect(x, y + 22, w, h - 22, (40, 80, 120))
    for wy in (30, 40):
        for wx in range(8, w - 16, 36):
            cv.hline(x + wx, x + wx + 18, y + wy, LIGHTBLUE, 2)
    cv.rect(x + 46, y + 30, 100, 12, INK)
    cv.rect(x + 58, y + 18, 20, 12, RED)
    cv.rect(x + 120, y + 22, 12, 8, WHITE)
    cv.burst(x + 68, y + 16, 10, ORANGE, core=YELLOW)
    cv.burst(x + 132, y + 24, 7, YELLOW, core=RED)
    for dx, dy in ((150, 8), (172, 12)):
        cv.rect(x + dx, y + dy, 8, 3, INK)
        cv.line(x + dx - 3, y + dy - 2, x + dx + 11, y + dy - 2, INK, 1)
        cv.line(x + dx - 3, y + dy + 4, x + dx + 11, y + dy + 4, INK, 1)


def pic_wellington(cv, x, y, w, h):
    """A cricket bat meets the ball on a green pitch."""
    cv.rect(x, y, w, h, GREEN)
    cv.rect(x + 12, y + 8, w - 24, h - 16, (120, 200, 120))
    for sx in (150, 156, 162):
        cv.rect(x + sx, y + 28, 3, 18, YELLOW)
    cv.rect(x + 148, y + 26, 18, 2, YELLOW)
    cv.line(x + 96, y + 12, x + 122, y + 40, (200, 160, 90), 8)
    cv.line(x + 96, y + 12, x + 122, y + 40, (140, 100, 50), 2)
    cv.disc(x + 128, y + 44, 4, RED)
    draw_text(cv, x + 12, y + h - 12, "720/9", 1, WHITE)


def pic_vegas(cv, x, y, w, h):
    """A race car under the lights with a checkered flag."""
    cv.rect(x, y, w, h, (24, 30, 40))
    cv.rect(x, y + 34, w, h - 34, (60, 60, 70))
    for lx in (20, 60, 100, 140, 170):
        cv.rect(x + lx, y + 6, 3, 3, GOLD)
    cv.rect(x + 30, y + 22, 90, 12, RED)
    cv.rect(x + 42, y + 14, 34, 8, RED)
    cv.rect(x + 48, y + 16, 22, 5, LIGHTBLUE)
    for wx in (42, 72, 104):
        cv.disc(x + wx, y + 36, 5, INK)
        cv.disc(x + wx, y + 36, 2, WHITE)
    for fy in range(4):
        for fx in range(4):
            if (fx + fy) % 2 == 0:
                cv.rect(x + 148 + fx * 8, y + 8 + fy * 8, 8, 8, WHITE)
            else:
                cv.rect(x + 148 + fx * 8, y + 8 + fy * 8, 8, 8, INK)
    cv.line(x + 148, y + 40, x + 148, y + 46, INK, 2)


def pic_riyadh(cv, x, y, w, h):
    """An interceptor climbs to meet three incoming missiles."""
    cv.rect(x, y, w, h, DUSK)
    for fx, fy in ((20, 8), (60, 14), (120, 6), (170, 12)):
        cv.rect(x + fx, y + fy, 2, 2, WHITE)
    cv.rect(x, y + 40, w, h - 40, (30, 40, 60))
    for tx in (30, 60, 90):
        cv.line(x + tx, y + 46, x + tx - 8, y + 30, LIGHTRED, 3)
        cv.disc(x + tx - 9, y + 29, 3, LIGHTRED)
    cv.line(x + 150, y + 46, x + 165, y + 10, GOLD, 4)
    cv.line(x + 150, y + 46, x + 165, y + 10, WHITE, 2)
    cv.burst(x + 166, y + 10, 9, YELLOW, core=WHITE)
    cv.disc(x + 150, y + 46, 4, GOLD)


def pic_manipur(cv, x, y, w, h):
    """A hospital cross beside a tipped bottle."""
    cv.rect(x, y, w, h, (250, 240, 220))
    cv.rect(x + 20, y + 8, 36, 36, WHITE)
    cv.rect(x + 34, y + 12, 8, 28, RED)
    cv.rect(x + 24, y + 22, 28, 8, RED)
    cv.rect(x + 84, y + 16, 14, 26, GREEN)
    cv.rect(x + 88, y + 10, 6, 6, GREEN)
    cv.line(x + 98, y + 30, x + 130, y + 42, LIGHTBLUE, 3)
    cv.ellipse(x + 138, y + 42, 14, 4, LIGHTBLUE)
    draw_text(cv, x + 120, y + 10, "11 dead", 1, RED)


def pic_fbi(cv, x, y, w, h):
    """A computer screen flashing a breach warning."""
    cv.rect(x, y, w, h, (40, 50, 70))
    cv.rect(x + 56, y + 8, 78, 34, (20, 25, 35))
    outline(cv, x + 56, y + 8, 78, 34, LIGHTBLUE, 2)
    draw_text(cv, x + 64, y + 14, "Breach", 1, LIGHTRED)
    draw_text(cv, x + 64, y + 26, "NCIC", 1, WHITE)
    cv.rect(x + 88, y + 42, 14, 4, (120, 120, 130))
    cv.rect(x + 78, y + 46, 34, 3, (120, 120, 130))
    cv.poly([(x + 162, y + 12), (x + 172, y + 32), (x + 152, y + 32)],
            YELLOW)
    draw_text(cv, x + 160, y + 22, "!", 1, INK)


def pic_bolsonaro(cv, x, y, w, h):
    """A hospital bed with a drip and a red cross."""
    cv.rect(x, y, w, h, (240, 245, 250))
    cv.rect(x + 16, y + 30, 90, 6, (120, 120, 130))
    for lx in (20, 100):
        cv.rect(x + lx, y + 36, 4, 12, (120, 120, 130))
    cv.ellipse(x + 30, y + 28, 10, 4, (200, 180, 140))
    cv.rect(x + 118, y + 8, 8, 34, (120, 120, 130))
    cv.ellipse(x + 122, y + 12, 8, 6, LIGHTBLUE)
    cv.line(x + 122, y + 18, x + 122, y + 28, LIGHTBLUE, 2)
    cv.rect(x + 150, y + 10, 28, 28, WHITE)
    cv.rect(x + 161, y + 14, 6, 20, RED)
    cv.rect(x + 154, y + 21, 20, 6, RED)


def pic_amazon(cv, x, y, w, h):
    """A shopping cart carrying a computer chip."""
    cv.rect(x, y, w, h, (250, 240, 210))
    cv.poly([(x + 30, y + 14), (x + 130, y + 14), (x + 122, y + 40),
             (x + 40, y + 40)], ORANGE)
    cv.line(x + 30, y + 14, x + 22, y + 6, ORANGE, 3)
    for wx in (56, 100):
        cv.disc(x + wx, y + 46, 4, INK)
    cv.rect(x + 150, y + 12, 28, 28, (30, 60, 120))
    for px in (154, 164, 174):
        for py in (16, 26, 36):
            cv.rect(x + px, y + py, 4, 4, GOLD)
    draw_text(cv, x + 142, y + 44, "$7.5bn", 1, INK)


# --- Numbered world map --------------------------------------------------

CONTINENTS = [
    # North America (lon, lat) outline, schematic.
    [(-168, 66), (-140, 70), (-125, 72), (-110, 68), (-95, 70),
     (-80, 70), (-65, 60), (-55, 52), (-60, 45), (-70, 42),
     (-75, 35), (-80, 26), (-85, 20), (-90, 12), (-95, 16),
     (-100, 20), (-105, 22), (-115, 28), (-125, 40), (-125, 48),
     (-135, 58), (-155, 58), (-165, 60)],
    # Greenland.
    [(-55, 60), (-40, 64), (-30, 68), (-25, 70), (-35, 76),
     (-55, 75), (-60, 70)],
    # South America.
    [(-80, 10), (-75, 5), (-70, 10), (-60, 5), (-50, 0),
     (-40, -5), (-35, -10), (-40, -20), (-50, -30), (-60, -35),
     (-70, -40), (-75, -50), (-70, -55), (-75, -45), (-70, -30),
     (-80, -20), (-80, -5)],
    # Africa.
    [(-17, 15), (-10, 30), (0, 35), (10, 37), (20, 32), (30, 31),
     (35, 28), (40, 15), (45, 11), (50, 10), (45, 0), (40, -10),
     (35, -20), (30, -30), (20, -35), (15, -30), (10, -20),
     (12, -10), (8, 0), (5, 5), (-5, 5), (-15, 5)],
    # Eurasia.
    [(-10, 36), (-5, 44), (-2, 48), (0, 50), (5, 55), (10, 58),
     (18, 56), (25, 60), (30, 65), (40, 68), (50, 70), (60, 70),
     (70, 72), (90, 75), (110, 75), (130, 72), (150, 70),
     (170, 66), (180, 65), (170, 60), (160, 55), (145, 45),
     (140, 40), (130, 35), (125, 30), (120, 25), (110, 20),
     (105, 10), (100, 8), (95, 15), (90, 22), (82, 12),
     (80, 13), (75, 10), (70, 20), (65, 25), (60, 25),
     (55, 26), (50, 29), (45, 30), (40, 36), (35, 36),
     (30, 36), (25, 40), (20, 40), (15, 44), (10, 44),
     (5, 40), (0, 38)],
    # Australia.
    [(113, -22), (114, -30), (115, -35), (120, -34), (130, -32),
     (140, -38), (145, -38), (150, -37), (153, -32), (153, -27),
     (146, -19), (142, -11), (135, -12), (132, -12), (126, -14),
     (122, -17), (114, -20)],
    # Britain, Japan, New Zealand, Madagascar, Indonesia (schematic).
    [(-5, 50), (-2, 53), (0, 52), (1, 51), (-3, 50)],
    [(130, 31), (135, 34), (140, 38), (142, 42), (145, 44),
     (142, 45), (140, 40), (135, 35), (130, 33)],
    [(167, -45), (170, -42), (174, -40), (177, -38), (175, -37),
     (172, -40), (168, -44)],
    [(43, -12), (47, -15), (50, -17), (47, -25), (44, -24),
     (43, -16)],
    [(95, 5), (105, 0), (115, -5), (125, -8), (135, -5),
     (140, -8), (130, -2), (120, 0), (110, 5), (100, 2)],
]
# Story number -> (lon, lat, dx, dy) for the map dots.
# The dx/dy nudges spread the dots where the news clusters (Europe,
# the Gulf, the US east coast) so the numbers stay legible at this size.
MAP_DOTS = [
    (1, 50.6, 26.2, -11, -8), (2, -108.5, 25.6, -1, 8),
    (3, -122.4, 37.8, -8, -8), (4, 30.7, 36.9, -12, -11),
    (5, 33.4, 47.9, 12, -10), (6, 27.0, 60.0, 14, -12),
    (7, 174.8, -41.3, 0, -1), (8, -115.1, 36.2, 7, -6),
    (9, 46.7, 24.6, 5, 3), (10, 93.9, 24.8, 0, 0),
    (11, -77.0, 38.9, -7, -7), (12, -47.9, -15.8, 0, 0),
    (13, 34.8, 32.1, 17, -12), (14, 47.8, 30.5, 19, 18),
    (15, 6.5, 5.5, 0, 0), (16, 12.6, 55.7, -5, -14),
    (17, 6.1, 46.2, -18, 14), (18, -0.19, 51.48, -16, -2),
    (19, -80.7, 28.4, -1, 16), (20, 34.5, 31.5, -9, 12),
    (21, 35.5, 33.9, 3, -18), (22, -0.1, 51.5, -6, 12),
    (23, 4.4, 50.8, 4, -11), (24, -77.0, 38.9, 9, 7),
    (25, -74.0, 40.7, 11, -13), (26, 66.9, 29.8, 21, -12),
    (27, 56.5, 26.6, 15, -7), (28, 151.2, -33.9, -3, -6),
    (29, 6.1, 46.2, 8, 16), (30, 31.2, 30.0, -16, 2),
    (31, 4.4, 50.8, 12, 7), (32, -1.6, 55.0, -12, -13),
    (33, 42.8, 14.8, -6, 11), (34, 30.5, 50.5, 8, 16),
    (35, -73.7, 41.1, 20, 3),
]


def draw_map(cv, x, y, w, h):
    """Numbered world map: tan continents on a navy sea."""
    cv.rect(x, y, w, h, NAVY)

    def lonlat(lon, lat):
        px = x + int((lon + 170) / 360 * w)
        py = y + int((80 - lat) / 140 * h)
        return px, py

    for cont in CONTINENTS:
        cv.poly([lonlat(lon, lat) for lon, lat in cont], SAND)
    for num, lon, lat, dx, dy in MAP_DOTS:
        cx, cy = lonlat(lon, lat)
        cx += dx
        cy += dy
        cv.disc(cx, cy, 7, RED)
        s = str(num)
        draw_text(cv, cx - 3 * len(s), cy - 3, s, 1, WHITE)


def encode_png(w, h, rgb):
    raw = bytearray()
    stride = w * 3
    for yy in range(h):
        raw.append(0)
        raw += rgb[yy * stride:(yy + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def render():
    cv = Canvas()
    MX, RX = 16, 1008
    # Kicker line and rules.
    draw_text(cv, MX, 8, KICKER_LEFT, 1, RED)
    draw_text_right(cv, RX, 8, KICKER_RIGHT, 1, INK)
    cv.rect(MX, 22, 992, 3, INK)
    # Masthead and subhead.
    draw_centered(cv, 30, MASTHEAD, 6, INK)
    for i, line in enumerate(SUBHEAD):
        draw_centered(cv, 78 + i * 16, line, 2, MUTED)
    cv.rect(MX, 112, 992, 2, INK)
    # Stat strip: six big numbers with red bars.
    stat_x = MX
    for (num, cap1, cap2), wcol in zip(
            STATS, [166, 165, 165, 165, 165, 166]):
        cv.rect(stat_x, 118, 3, 50, RED)
        draw_text(cv, stat_x + 8, 120, num, 3, INK)
        draw_text(cv, stat_x + 8, 147, cap1, 1, MUTED)
        draw_text(cv, stat_x + 8, 156, cap2, 1, MUTED)
        stat_x += wcol
    # Region bar: segment widths proportional to the story counts.
    total = sum(n for _, n, _ in REGIONS)
    bounds = [MX]
    cum = 0
    for _, n, _ in REGIONS:
        cum += n
        bounds.append(MX + round(992 * cum / total))
    for (name, n, color), x0, x1 in zip(REGIONS, bounds, bounds[1:]):
        cv.rect(x0, 172, x1 - x0, 16, color)
        label = name.upper() + " " + str(n)
        tx = x0 + (x1 - x0 - text_width(label, 1)) // 2
        draw_text(cv, tx, 176, label, 1, WHITE)
    # Three lead stories.
    lead_ills = (ill_bahrain, ill_sinaloa, ill_riemann)
    lead_x = [MX, 351, 686]
    for lead, x0, ill in zip(LEADS, lead_x, lead_ills):
        ill(cv, x0, 194, 322, 168)
        label_banner(cv, x0, 194, lead["banner"], 2)
        credit_strip(cv, x0, 348, 322, lead["credit"])
        num_disc(cv, x0 + 7, 369, lead["num"])
        draw_text(cv, x0 + 18, 366, lead["place"], 1, RED)
        y = draw_block(cv, x0, 384, 322,
                       wrap_text(lead["headline"], 322, 2), 2, INK, 3)
        draw_block(cv, x0, y + 4, 322,
                   wrap_text(lead["summary"], 322, 1), 1, INK, 3)
    # Ten more stories in a 2x5 grid.
    grid_pics = {
        "cop": pic_cop, "kryvyi": pic_kryvyi, "sparta": pic_sparta,
        "wellington": pic_wellington, "vegas": pic_vegas,
        "riyadh": pic_riyadh, "manipur": pic_manipur, "fbi": pic_fbi,
        "bolsonaro": pic_bolsonaro, "amazon": pic_amazon,
    }
    for i, story in enumerate(GRID):
        row, col = divmod(i, 5)
        gx = MX + col * 200
        gy = 460 + row * 138
        grid_pics[story["pic"]](cv, gx, gy, 190, 52)
        label_banner(cv, gx, gy, story["banner"], 1)
        credit_strip(cv, gx, gy + 38, 190, story["credit"])
        draw_text(cv, gx, gy + 58, str(story["num"]) + " ", 1, RED)
        draw_text(cv, gx + 18, gy + 58, story["place"], 1, INK)
        y = draw_block(cv, gx, gy + 72, 190,
                       wrap_text(story["headline"], 190, 2), 2, INK, 3)
        draw_block(cv, gx, y + 2, 190,
                   wrap_text(story["summary"], 190, 1), 1, INK, 3)
    # Map and the 22-item list.
    draw_text(cv, MX, 734, "Where it happened", 2, INK)
    draw_text(cv, 262, 734,
              "Also on Sunday 22 November \u2014 22 more stories", 2, INK)
    draw_map(cv, MX, 754, 230, 140)
    draw_text(cv, MX, 898, "Numbers match the stories above.", 1, MUTED)
    for i, (num, place, text, src) in enumerate(ALSO):
        col, row = divmod(i, 11)
        ax = 262 + col * 374
        ay = 754 + row * 12
        draw_text(cv, ax, ay, num + " " + place, 1, RED)
        nx = ax + text_width(num + " " + place + " ", 1)
        nx = draw_text(cv, nx, ay, text, 1, INK)
        draw_text(cv, nx + 6, ay, "(" + src + ")", 1, MUTED)
    # Date check and footer.
    outline(cv, MX, 910, 992, 50, RED, 2)
    draw_text(cv, 26, 916, "Date check", 2, RED)
    draw_block(cv, 26, 934, 960,
               wrap_text(DATE_CHECK, 960, 1), 1, INK, 3)
    draw_centered(cv, 970, FOOTER, 1, MUTED)
    draw_centered(cv, 984, SOURCES_LINE, 1, MUTED)
    return cv


def main():
    cv = render()
    data = encode_png(W, H, cv.buf)
    base = "/output" if os.path.isdir("/output") else "output"
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %dx%d)"
          % (path, len(data), W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
