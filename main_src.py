# main_src.py -- renderer for "THE WORLD IN ONE DAY", Sunday 22 November 2026.
# A dense newspaper front page drawn from scratch with a tiny rasterizer,
# an embedded 5x7 bitmap font, hand-drawn illustrations and a minimal PNG
# encoder. Standard library only, no network, no clock: running it twice
# produces byte-identical output.
#
# Layout (1024 x 1024):
#   masthead + date line + tagline
#   strip of six big numbers
#   coloured region bar (7 regions, story counts)
#   three lead stories with large drawn illustrations
#   ten more stories in a grid with small pictograms
#   numbered world map + 22-item "also on" list
#   date-check box + sources line

import math
import struct
import zlib

W, H = 1024, 1024

# --- palette ---------------------------------------------------------------
PAPER = (250, 246, 236)      # warm newsprint
PANEL = (238, 232, 216)      # panel background
INK = (20, 20, 22)           # near-black
GREY = (112, 109, 100)       # secondary text
WHITE = (255, 255, 255)
RED = (178, 34, 34)
BLUE = (31, 73, 125)
TEAL = (14, 110, 110)
GOLD = (196, 138, 24)
GREEN = (46, 125, 50)
PURPLE = (103, 58, 140)
ORANGE = (196, 90, 20)
SKY = (183, 214, 232)
SEA = (28, 78, 128)
SAND = (216, 206, 178)       # map land
LAND_LINE = (120, 110, 85)
OCEAN = (170, 205, 225)
BOARD = (30, 80, 55)         # chalkboard green
DUSK1 = (250, 214, 165)
DUSK2 = (232, 178, 120)
GROUND = (150, 110, 70)


# --- tiny raster canvas ----------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.pix = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pix[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        span = (x1 - x0) * 3
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.pix[i:i + span] = row

    def frame(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def hline(self, x0, x1, y, c):
        if x1 < x0:
            x0, x1 = x1, x0
        self.rect(x0, y, x1 - x0 + 1, 1, c)

    def vline(self, x, y0, y1, c):
        if y1 < y0:
            y0, y1 = y1, y0
        self.rect(x, y0, 1, y1 - y0 + 1, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def tline(self, x0, y0, x1, y1, c):
        # a line about 2 px thick, drawn as four offset copies
        self.line(x0, y0, x1, y1, c)
        self.line(x0 + 1, y0, x1 + 1, y1, c)
        self.line(x0, y0 + 1, x1, y1 + 1, c)
        self.line(x0 + 1, y0 + 1, x1 + 1, y1 + 1, c)

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c):
        # 1 px outline circle, drawn parametrically
        steps = max(24, r * 8)
        for i in range(steps):
            a = 2.0 * math.pi * i / steps
            self.set(cx + int(r * math.cos(a)), cy + int(r * math.sin(a)), c)

    def poly(self, pts, c):
        # scanline fill, even-odd rule
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa = int(xs[i])
                xb = int(xs[i + 1])
                self.rect(xa, y, xb - xa + 1, 1, c)

    def polyline(self, pts, c):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c)

    # --- text --------------------------------------------------------------
    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s:
            g = FONT[ch]
            for r in range(7):
                row = g[r]
                for col in range(5):
                    if row[col] == '#':
                        self.rect(cx + col * scale, y + r * scale,
                                  scale, scale, c)
            cx += 6 * scale

    def text_w(self, s, scale):
        if not s:
            return 0
        return len(s) * 6 * scale - scale

    def centre(self, x, y, w, s, scale, c):
        tw = self.text_w(s, scale)
        self.text(x + (w - tw) // 2, y, s, scale, c)

    def wrap(self, s, scale, maxw):
        # greedy word wrap; a single word wider than maxw is an error
        lines = []
        cur = ''
        for wd in s.split(' '):
            if self.text_w(wd, scale) > maxw:
                raise ValueError('word too wide for box: ' + wd)
            t = wd if not cur else cur + ' ' + wd
            if self.text_w(t, scale) <= maxw:
                cur = t
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, scale, maxw, c, leading=2):
        # draw a wrapped paragraph; returns the y just below the last line
        lines = self.wrap(s, scale, maxw)
        step = 7 * scale + leading
        for i, ln in enumerate(lines):
            self.text(x, y + i * step, ln, scale, c)
        return y + len(lines) * step

# --- embedded 5x7 bitmap font ----------------------------------------------
# Each glyph is 7 rows of 5 cells; '#' is ink, '.' is blank.
FONT = {
'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
'a': (".....", ".....", ".###.", "....#", ".####", "#...#", ".###."),
'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".###."),
'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
'f': ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
'g': (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
'i': (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
'j': (".....", "...#.", ".....", "..##.", "...#.", "...#.", ".##.."),
'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
'p': (".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
'q': (".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
't': (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
'u': (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".###."),
'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
'w': (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
'y': (".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
'0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
'1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
'2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
'3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
'4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
'5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
'6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
'7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
'8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
'9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
'.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
',': (".....", ".....", ".....", ".....", ".....", ".##..", ".#..."),
':': (".....", ".....", ".##..", ".##..", ".....", ".##..", ".##.."),
';': (".....", ".....", ".##..", ".##..", ".....", ".##..", ".#..."),
'!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
'?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
"'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
'"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
'-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
'(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
'/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
'%': ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
'$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
'&': (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
'+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
'=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
'*': (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
'#': (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
'@': (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
'<': ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
'>': (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
'_': (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
'[': (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
']': (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
'|': ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
'~': (".....", ".....", ".##.#", "#.#..", ".....", ".....", "....."),
'^': ("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
'`': ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
'{': ("...##", "..#..", "..#..", ".##..", "..#..", "..#..", "...##"),
'}': ("##...", "..#..", "..#..", "..##.", "..#..", "..#..", "##..."),
}

# --- small pictograms (44 x 44, centred on cx, cy) -------------------------
def pic_globe(c, cx, cy):
    c.circle(cx, cy, 18, BLUE)
    c.circle(cx, cy, 15, SKY)
    c.hline(cx - 15, cx + 15, cy, BLUE)
    c.vline(cx, cy - 15, cy + 15, BLUE)
    c.poly([(cx - 6, cy - 8), (cx + 2, cy - 12), (cx + 8, cy - 4),
            (cx + 2, cy + 2), (cx - 8, cy)], GREEN)
    c.poly([(cx - 2, cy + 6), (cx + 8, cy + 4), (cx + 10, cy + 12),
            (cx, cy + 14), (cx - 8, cy + 10)], GREEN)


def pic_blast(c, cx, cy):
    c.rect(cx - 18, cy + 6, 12, 12, GREY)
    c.rect(cx + 6, cy + 10, 12, 8, GREY)
    for dx, dy in [(-14, -12), (0, -16), (14, -12), (-16, 0), (16, 0),
                   (-12, 10), (12, 10)]:
        c.line(cx, cy, cx + dx, cy + dy, ORANGE)
    c.circle(cx, cy, 7, GOLD)
    c.circle(cx, cy, 4, RED)


def pic_ship(c, cx, cy):
    c.poly([(cx - 18, cy + 2), (cx + 16, cy + 2), (cx + 10, cy + 12),
            (cx - 12, cy + 12)], INK)
    c.rect(cx - 4, cy - 8, 10, 10, WHITE)
    c.rect(cx + 8, cy - 14, 4, 6, RED)
    c.line(cx - 18, cy + 16, cx + 18, cy + 16, SEA)
    c.line(cx - 14, cy + 18, cx + 14, cy + 18, SEA)
    c.poly([(cx + 2, cy - 18), (cx + 6, cy - 10), (cx - 2, cy - 10)], ORANGE)
    c.poly([(cx + 5, cy - 16), (cx + 8, cy - 10), (cx + 2, cy - 10)], GOLD)


def pic_cricket(c, cx, cy):
    for dx in (-8, 0, 8):
        c.vline(cx + dx, cy - 14, cy + 6, GOLD)
    c.hline(cx - 10, cx + 10, cy - 14, GOLD)
    c.tline(cx - 14, cy + 12, cx + 2, cy - 10, INK)
    c.circle(cx + 14, cy + 10, 5, RED)


def pic_f1(c, cx, cy):
    c.rect(cx - 18, cy - 2, 30, 7, RED)
    c.poly([(cx - 6, cy - 2), (cx + 2, cy - 10), (cx + 10, cy - 10),
            (cx + 12, cy - 2)], RED)
    c.poly([(cx + 12, cy - 2), (cx + 18, cy - 2), (cx + 18, cy + 5),
            (cx + 12, cy + 5)], INK)
    c.circle(cx - 10, cy + 8, 5, INK)
    c.circle(cx + 10, cy + 8, 5, INK)
    c.circle(cx - 10, cy + 8, 2, WHITE)
    c.circle(cx + 10, cy + 8, 2, WHITE)
    c.line(cx + 16, cy - 16, cx + 16, cy - 2, INK)
    for i in range(2):
        for j in range(2):
            if (i + j) % 2 == 0:
                c.rect(cx + 16, cy - 16 + j * 4, 4, 4, INK)
            else:
                c.rect(cx + 20, cy - 16 + j * 4, 4, 4, INK)


def pic_missile(c, cx, cy):
    c.poly([(cx - 14, cy + 12), (cx - 4, cy + 12), (cx - 4, cy - 12),
            (cx - 9, cy - 16), (cx - 14, cy - 12)], GREY)
    c.poly([(cx - 9, cy - 16), (cx - 4, cy - 12), (cx - 14, cy - 12)], RED)
    c.line(cx - 16, cy + 16, cx + 4, cy - 4, ORANGE)
    c.line(cx - 12, cy + 18, cx + 8, cy - 2, GOLD)
    c.poly([(cx + 2, cy - 14), (cx + 14, cy - 16), (cx + 16, cy - 4),
            (cx + 8, cy + 6), (cx - 2, cy - 2)], BLUE)
    c.poly([(cx + 5, cy - 12), (cx + 12, cy - 13), (cx + 13, cy - 5),
            (cx + 8, cy + 2), (cx + 1, cy - 3)], WHITE)


def pic_bottle(c, cx, cy):
    c.rect(cx - 6, cy - 16, 12, 6, TEAL)
    c.rect(cx - 4, cy - 10, 8, 4, TEAL)
    c.rect(cx - 8, cy - 6, 16, 22, TEAL)
    c.rect(cx - 8, cy + 2, 16, 8, WHITE)
    c.poly([(cx + 10, cy + 14), (cx + 18, cy + 14), (cx + 14, cy + 4)], GOLD)
    c.text(cx + 12, cy + 8, "!", 1, INK)


def pic_laptop(c, cx, cy):
    c.rect(cx - 16, cy - 10, 32, 20, INK)
    c.rect(cx - 13, cy - 7, 26, 14, (120, 200, 220))
    c.rect(cx - 20, cy + 10, 40, 4, INK)
    c.rect(cx - 4, cy - 2, 8, 8, GOLD)
    c.line(cx - 4, cy - 6, cx - 4, cy - 2, GOLD)
    c.line(cx + 4, cy - 6, cx + 4, cy - 2, GOLD)
    c.line(cx - 4, cy - 6, cx + 4, cy - 6, GOLD)


def pic_hospital(c, cx, cy):
    c.rect(cx - 18, cy - 18, 36, 36, WHITE)
    c.frame(cx - 18, cy - 18, 36, 36, RED, 2)
    c.rect(cx - 4, cy - 14, 8, 28, RED)
    c.rect(cx - 14, cy - 4, 28, 8, RED)
    c.rect(cx - 14, cy + 8, 28, 4, INK)
    c.line(cx - 14, cy + 12, cx - 14, cy + 16, INK)
    c.line(cx + 14, cy + 12, cx + 14, cy + 16, INK)


def pic_cart(c, cx, cy):
    c.poly([(cx - 14, cy - 10), (cx + 12, cy - 10), (cx + 8, cy + 6),
            (cx - 10, cy + 6)], GOLD)
    c.line(cx - 16, cy - 14, cx - 12, cy - 10, INK)
    c.circle(cx - 6, cy + 12, 3, INK)
    c.circle(cx + 6, cy + 12, 3, INK)
    c.rect(cx + 2, cy - 18, 14, 14, BLUE)
    c.rect(cx + 5, cy - 15, 8, 8, WHITE)
    c.rect(cx + 8, cy - 12, 2, 2, BLUE)


# --- lead illustrations (324 x 120) -----------------------------------------
def illo_tanker(c, x, y):
    c.rect(x, y, 324, 72, SKY)
    c.rect(x, y + 72, 324, 48, SEA)
    for wy in (y + 82, y + 94, y + 106):
        for i in range(12):
            c.hline(x + 8 + i * 27, x + 20 + i * 27, wy, WHITE)
    # tanker hull and superstructure
    c.poly([(x + 20, y + 78), (x + 180, y + 78), (x + 170, y + 100),
            (x + 30, y + 100)], INK)
    c.rect(x + 28, y + 96, 144, 4, RED)
    c.rect(x + 130, y + 52, 44, 26, WHITE)
    c.rect(x + 150, y + 42, 14, 12, RED)
    c.vline(x + 60, y + 58, y + 78, INK)
    # oil derrick on the right
    c.line(x + 245, y + 72, x + 258, y + 28, INK)
    c.line(x + 271, y + 72, x + 258, y + 28, INK)
    c.hline(x + 248, x + 268, y + 58, INK)
    c.hline(x + 251, x + 265, y + 44, INK)
    # explosion starburst
    for dx, dy in [(-16, -14), (0, -20), (16, -14), (-20, 0), (20, 0),
                   (-14, 12), (14, 12)]:
        c.line(x + 258, y + 40, x + 258 + dx, y + 40 + dy, ORANGE)
    c.circle(x + 258, y + 40, 9, GOLD)
    c.circle(x + 258, y + 40, 5, RED)
    # missile streaks
    c.line(x + 60, y + 8, x + 240, y + 34, ORANGE)
    c.line(x + 110, y + 2, x + 246, y + 30, GOLD)
    c.circle(x + 240, y + 34, 3, WHITE)
    c.circle(x + 246, y + 30, 3, WHITE)


def illo_heli(c, x, y):
    c.rect(x, y, 324, 40, DUSK1)
    c.rect(x, y + 40, 324, 40, DUSK2)
    c.rect(x, y + 80, 324, 40, GROUND)
    c.circle(x + 282, y + 26, 12, (255, 240, 180))
    c.poly([(x + 10, y + 80), (x + 60, y + 30), (x + 110, y + 80)],
           (120, 90, 70))
    c.poly([(x + 70, y + 80), (x + 130, y + 45), (x + 190, y + 80)],
           (100, 75, 60))
    # searchlight cone
    c.poly([(x + 150, y + 62), (x + 118, y + 112), (x + 182, y + 112)],
           (255, 244, 190))
    # helicopter
    c.rect(x + 120, y + 42, 70, 18, (40, 40, 44))
    c.circle(x + 122, y + 51, 9, (40, 40, 44))
    c.rect(x + 190, y + 48, 52, 6, (40, 40, 44))
    c.poly([(x + 238, y + 48), (x + 248, y + 34), (x + 248, y + 54)],
           (40, 40, 44))
    c.vline(x + 152, y + 36, y + 42, (40, 40, 44))
    c.rect(x + 102, y + 34, 108, 3, (40, 40, 44))
    c.hline(x + 128, x + 182, y + 64, (40, 40, 44))
    c.vline(x + 132, y + 60, y + 64, (40, 40, 44))
    c.vline(x + 178, y + 60, y + 64, (40, 40, 44))
    c.rect(x + 138, y + 46, 14, 8, SKY)


def illo_board(c, x, y):
    c.rect(x, y, 324, 120, BOARD)
    c.frame(x, y, 324, 120, (150, 110, 70), 4)
    c.text(x + 44, y + 12, "ZETA FUNCTION", 1, WHITE)
    # axes
    c.hline(x + 30, x + 300, y + 92, WHITE)
    c.vline(x + 40, y + 14, y + 92, WHITE)
    # two rising curves
    c.polyline([(x + 45, y + 88), (x + 80, y + 80), (x + 110, y + 68),
                (x + 140, y + 54), (x + 170, y + 38), (x + 200, y + 22),
                (x + 230, y + 12)], WHITE)
    c.polyline([(x + 45, y + 86), (x + 90, y + 76), (x + 140, y + 58),
                (x + 190, y + 38), (x + 240, y + 24)], (150, 220, 170))
    # big green check
    c.tline(x + 252, y + 66, x + 266, y + 86, (90, 210, 100))
    c.tline(x + 266, y + 86, x + 300, y + 38, (90, 210, 100))
    c.text(x + 16, y + 100, "17,000,000 LINES CHECKED", 1, GOLD)

# --- numbered world map ------------------------------------------------------
# Rough continent outlines in (lon, lat); projected equirectangular.
CONTINENTS = [
    # North America
    [(-168, 66), (-145, 70), (-128, 71), (-112, 68), (-96, 69), (-88, 66),
     (-82, 66), (-76, 62), (-65, 60), (-60, 55), (-55, 52), (-60, 47),
     (-66, 45), (-70, 42), (-74, 39), (-76, 35), (-80, 32), (-81, 26),
     (-84, 30), (-89, 29), (-91, 19), (-97, 16), (-94, 17), (-88, 14),
     (-84, 10), (-80, 9), (-83, 9), (-90, 14), (-95, 16), (-100, 18),
     (-105, 20), (-108, 23), (-112, 28), (-117, 33), (-122, 37),
     (-124, 42), (-124, 48), (-130, 55), (-140, 60), (-152, 58),
     (-158, 58), (-165, 60), (-168, 66)],
    # South America
    [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-72, -18),
     (-70, -22), (-70, -30), (-72, -37), (-73, -44), (-71, -50),
     (-68, -54), (-66, -55), (-63, -50), (-60, -43), (-57, -38),
     (-52, -32), (-48, -27), (-41, -23), (-38, -17), (-35, -9),
     (-35, -6), (-40, -3), (-44, -2), (-50, 0), (-53, 4), (-58, 7),
     (-62, 9), (-68, 11), (-73, 11), (-77, 11), (-79, 9)],
    # Greenland
    [(-55, 60), (-50, 60), (-44, 60), (-40, 63), (-32, 68), (-25, 70),
     (-20, 73), (-22, 76), (-35, 77), (-50, 76), (-58, 74), (-60, 70),
     (-55, 60)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 44), (-4, 48), (-1, 50), (2, 51), (4, 53),
     (7, 54), (8, 57), (10, 59), (13, 56), (18, 56), (21, 55), (23, 58),
     (25, 60), (28, 61), (30, 62), (30, 66), (28, 70), (25, 71),
     (20, 70), (15, 68), (12, 65), (8, 62), (5, 60), (5, 58), (0, 57),
     (-3, 54), (-5, 50), (-8, 48), (-10, 44), (-10, 36)],
    # Africa
    [(-6, 35), (-10, 31), (-14, 28), (-17, 22), (-17, 15), (-16, 12),
     (-12, 8), (-8, 5), (-4, 5), (2, 6), (6, 4), (9, 4), (12, 0),
     (12, -4), (13, -8), (12, -12), (13, -17), (14, -22), (15, -27),
     (17, -32), (19, -35), (25, -34), (28, -33), (32, -29), (35, -24),
     (36, -19), (40, -15), (40, -10), (41, -5), (44, -1), (48, 0),
     (51, 2), (51, 10), (48, 11), (44, 11), (43, 12), (41, 13),
     (39, 15), (38, 18), (37, 21), (36, 25), (34, 28), (32, 31),
     (30, 32), (26, 32), (22, 33), (18, 33), (14, 34), (11, 34),
     (10, 37), (6, 37), (0, 36), (-6, 35)],
    # Asia
    [(30, 70), (45, 71), (60, 72), (75, 73), (90, 75), (105, 74),
     (120, 73), (135, 72), (150, 71), (162, 70), (170, 67), (178, 65),
     (178, 62), (170, 60), (162, 61), (158, 58), (155, 55), (150, 52),
     (142, 50), (141, 46), (140, 42), (136, 42), (132, 42), (129, 40),
     (127, 39), (124, 38), (122, 37), (120, 34), (120, 30), (118, 25),
     (114, 22), (110, 20), (108, 18), (106, 16), (105, 10), (103, 8),
     (101, 7), (100, 10), (98, 14), (96, 16), (94, 17), (92, 21),
     (90, 22), (88, 22), (86, 20), (83, 18), (80, 15), (78, 10),
     (77, 8), (76, 10), (75, 15), (73, 20), (70, 22), (67, 24),
     (64, 25), (61, 25), (58, 26), (56, 27), (54, 26), (52, 27),
     (50, 29), (49, 30), (48, 30), (48, 35), (47, 38), (44, 39),
     (42, 40), (40, 41), (38, 41), (36, 36), (34, 36), (32, 36),
     (30, 37), (30, 42), (30, 48), (30, 55), (30, 62), (30, 70)],
    # Australia
    [(113, -22), (114, -28), (115, -33), (118, -35), (122, -34),
     (126, -32), (129, -32), (132, -32), (134, -33), (136, -35),
     (138, -35), (140, -38), (143, -39), (146, -39), (149, -37),
     (150, -35), (153, -32), (153, -28), (151, -24), (149, -20),
     (146, -19), (144, -15), (142, -11), (140, -13), (138, -15),
     (136, -12), (134, -12), (132, -12), (130, -13), (128, -14),
     (126, -14), (124, -15), (122, -17), (120, -19), (117, -20),
     (114, -21), (113, -22)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (50, -20), (47, -24), (44, -25),
     (43, -21), (44, -16)],
]

# small islands drawn as dots: (lon, lat, radius)
ISLANDS = [(-2, 54, 2), (167, -45, 3), (174, -41, 3), (139, 35, 2),
           (141, 38, 2), (143, 42, 2), (100, -2, 2), (110, -6, 2),
           (120, -4, 2), (130, -3, 2), (140, -4, 2)]

# numbered story dots: (number, lon, lat)
DOTS = [(1, 50, 26), (2, -107, 25), (3, -124, 40), (4, 27, 36),
        (5, 34, 49), (6, 21, 59), (7, 174, -41), (8, -114, 35),
        (9, 43, 15), (10, 94, 25), (11, -77, 39), (12, -48, -15),
        (13, 37, 31)]


def draw_map(c, mx, my, mw, mh):
    c.rect(mx, my, mw, mh, OCEAN)
    c.frame(mx, my, mw, mh, INK, 1)
    for cont in CONTINENTS:
        pts = [(mx + int((lon + 180) / 360 * mw),
                my + int((90 - lat) / 180 * mh)) for lon, lat in cont]
        c.poly(pts, SAND)
        c.polyline(pts + [pts[0]], LAND_LINE)
    for lon, lat, r in ISLANDS:
        x = mx + int((lon + 180) / 360 * mw)
        y = my + int((90 - lat) / 180 * mh)
        c.circle(x, y, r, SAND)
    for num, lon, lat in DOTS:
        x = mx + int((lon + 180) / 360 * mw)
        y = my + int((90 - lat) / 180 * mh)
        c.circle(x, y, 6, RED)
        c.ring(x, y, 6, WHITE)
        label = str(num)
        c.text(x - c.text_w(label, 1) // 2, y - 3, label, 1, WHITE)


# --- the day's news ----------------------------------------------------------
# Every story happened, or was first reported, on Sunday 22 November 2026.
# Headlines and summaries are written here in my own words; the source
# beside each story is the wire or paper that carried it.

BIG_NUMBERS = [
    ("11", "KILLED IN THE", "SINALOA RAID"),
    ("720/9", "INDIA'S RECORD", "TEST TOTAL"),
    ("186", "DRONES FIRED AT", "UKRAINE"),
    ("$90", "OIL NEAR $90 AS", "GULF TENSIONS RISE"),
    ("24", "DEAD AS MOURNERS'", "BOAT SINKS, NIGERIA"),
    ("17M", "LINES OF LEAN CODE", "CHECK RIEMANN PROOF"),
]

REGIONS = [
    ("EUROPE", 10, BLUE),
    ("ASIA", 3, RED),
    ("MIDEAST", 9, ORANGE),
    ("AFRICA", 1, GREEN),
    ("AMERICAS", 7, PURPLE),
    ("OCEANIA", 2, TEAL),
    ("GLOBAL", 3, GREY),
]

LEADS = [
    (1, "Iran hits Bahrain; tankers struck off Hormuz",
     "Iran struck a civilian industrial site in Bahrain late on Saturday, "
     "Bahrain says, and two oil tankers were hit near the Strait of "
     "Hormuz. Oil held near $90 a barrel as Gulf tensions rose.",
     "REUTERS", illo_tanker),
    (2, "Mexico seizes 'El Chapo Isidro'; 11 killed",
     "Special forces arrested cartel boss Fausto Isidro Meza Flores in "
     "Sinaloa. Seven gunmen and four soldiers died in the raid. He was "
     "on the FBI's most-wanted list.",
     "AP", illo_heli),
    (3, "The Riemann proof checks out",
     "Anthropic's Levent Alpoge, working with Claude, claimed a proof on "
     "Friday. On Saturday, Lean checkers verified 17 million lines of "
     "Lean code.",
     "BLOOMBERG", illo_board),
]

GRID = [
    (4, "COP31's second day of overtime",
     "Still no text; fossil fuels divide the room.", "AFP", pic_globe),
    (5, "Missile kills boy and medic in Kryvyi Rih",
     "A second strike hit rescuers; 58 hurt.", "BBC", pic_blast),
    (6, "Drones set Russian ship Sparta II ablaze",
     "It drifted into Finnish waters.", "REUTERS", pic_ship),
    (7, "India pile up a record 720/9",
     "Rahul 136, Pant 128; NZ 119/2 at stumps.", "AP", pic_cricket),
    (8, "Verstappen wins a Vegas thriller",
     "Norris 2nd by 0.6s; Piastri 3rd; 35 lead changes.", "BBC", pic_f1),
    (9, "Saudis stop three Houthi missiles",
     "Hodeidah port struck in reply.", "AL JAZEERA", pic_missile),
    (10, "Toxic drink kills 11 in Manipur",
     "More than 180 are in hospital.", "AP", pic_bottle),
    (11, "FBI crime database hacked",
     "The NCIC system was breached.", "REUTERS", pic_laptop),
    (12, "Bolsonaro in intensive care",
     "A bowel obstruction put him in ICU.", "AFP", pic_hospital),
    (13, "Amazon nears a $7.5bn AI deal",
     "Target: Israeli startup Decart.", "BLOOMBERG", pic_cart),
]

ALSO = [
    "Hartha power station fire kills 4",
    "Mourners' boat sinks, 24 dead",
    "Denmark expels Russian attache",
    "UN agrees autonomous weapons rules",
    "Leeds stun Chelsea 4-1",
    "St Johns River breaks 73-yr record",
    "Israeli strikes go on in Gaza",
    "Aoun blames Israel and Iran",
    "Burnham eyes rejoining the EU",
    "EU proposes a digital tax",
    "Trump: report Congress requests",
    "China renews UN bid to blacklist BLA",
    "Pakistan says 15 militants killed",
    "British swimmer braves Hormuz",
    "Bondi rescuers marry",
    "WHO warns on antibiotic resistance",
    "Egypt-born Palestinians still foreign",
    "EU plastic export ban in force",
    "Man City stumble, Arsenal held",
    "Coalition strikes Hodeidah port",
    "Drone hits block in Vyshhorod",
    "IBM shows off a 520-qubit chip",
]

DATE_CHECK_LEFT = ("LEFT OUT AS 21 NOV NEWS: EU-INDONESIA TRADE DEAL "
                   "SIGNED IN BRUSSELS; FRIDAY'S US STOCK SELL-OFF.")
DATE_CHECK_NOTYET = ("NOT YET HAPPENED, SO NOT SHOWN: ANY FINAL COP31 TEXT; "
                     "THE LAST DAY OF THE WELLINGTON TEST.")
SOURCES = ("SOURCES: REUTERS - AP - BBC - AFP - BLOOMBERG - AL JAZEERA - "
           "THE GUARDIAN - ALL STORIES DATED 22 NOVEMBER 2026")

# --- layout ------------------------------------------------------------------
def draw_lines(c, x, y, s, scale, maxw, maxlines, color, leading=2):
    # wrapped text with a hard cap on lines; returns the y below the last line
    lines = c.wrap(s, scale, maxw)
    assert len(lines) <= maxlines, (s, lines)
    step = 7 * scale + leading
    for i, ln in enumerate(lines):
        c.text(x, y + i * step, ln, scale, color)
    return y + len(lines) * step


def _check_chars():
    # every string the page prints must exist in the embedded font
    texts = ["THE WORLD IN ONE DAY", "SUNDAY 22 NOVEMBER 2026",
             "Thirty-five stories from one day on Earth - every one of "
             "them 22 November 2026", "THE DAY ON THE MAP",
             "Red numbers mark stories 1-13.", "ALSO ON 22 NOVEMBER",
             "DATE CHECK", DATE_CHECK_LEFT, DATE_CHECK_NOTYET, SOURCES,
             "ZETA FUNCTION", "17,000,000 LINES CHECKED", "!"]
    for num, l1, l2 in BIG_NUMBERS:
        texts += [num, l1, l2]
    for name, count, _col in REGIONS:
        texts.append(name + " " + str(count))
    for _n, head, deck, src, _fn in LEADS:
        texts += [head, deck, src + " - 22 NOV 2026"]
    for _n, head, deck, src, _fn in GRID:
        texts += [head, deck, src + " - 22 NOV"]
    texts += ALSO
    for t in texts:
        for ch in t:
            assert ch in FONT, "missing glyph: " + repr(ch)


def render(path):
    _check_chars()
    c = Canvas(W, H, PAPER)

    # masthead
    c.rect(0, 0, W, 8, INK)
    c.text(214, 16, "THE WORLD IN ONE DAY", 5, INK)
    c.text(306, 58, "SUNDAY 22 NOVEMBER 2026", 3, INK)
    c.rect(306, 84, 411, 3, RED)
    c.text(290, 94, "Thirty-five stories from one day on Earth - every one "
                    "of them 22 November 2026", 1, GREY)
    c.rect(8, 108, 1008, 3, INK)

    # six big numbers
    for i, (num, l1, l2) in enumerate(BIG_NUMBERS):
        x = 8 + i * 169
        c.rect(x, 118, 165, 68, WHITE)
        c.frame(x, 118, 165, 68, INK, 1)
        c.centre(x, 126, 165, num, 4, RED)
        c.centre(x, 158, 165, l1, 1, INK)
        c.centre(x, 167, 165, l2, 1, INK)

    # region bar
    for i, (name, count, col) in enumerate(REGIONS):
        x = 8 + i * 144
        c.rect(x, 194, 144, 28, col)
        c.centre(x, 204, 144, name + " " + str(count), 1, WHITE)
    c.rect(8, 230, 1008, 3, INK)

    # three lead stories
    for i, (num, head, deck, src, fn) in enumerate(LEADS):
        x = 8 + i * 342
        fn(c, x, 240)
        c.frame(x, 240, 324, 124, INK, 1)
        c.circle(x + 16, 256, 12, RED)
        c.ring(x + 16, 256, 12, WHITE)
        c.text(x + 11, 249, str(num), 2, WHITE)
        draw_lines(c, x, 372, head, 2, 324, 2, INK)
        draw_lines(c, x, 408, deck, 1, 324, 4, INK)
        c.text(x, 450, src + " - 22 NOV 2026", 1, GREY)
    c.rect(8, 470, 1008, 3, INK)

    # ten grid stories
    for i, (num, head, deck, src, fn) in enumerate(GRID):
        cx = 8 + (i % 5) * 202
        cy = 482 + (i // 5) * 104
        fn(c, cx + 98, cy + 24)
        c.circle(cx + 10, cy + 10, 7, RED)
        c.ring(cx + 10, cy + 10, 7, WHITE)
        label = str(num)
        c.text(cx + 10 - c.text_w(label, 1) // 2, cy + 7, label, 1, WHITE)
        draw_lines(c, cx, cy + 50, head, 1, 196, 2, INK)
        draw_lines(c, cx, cy + 70, deck, 1, 196, 2, GREY)
        c.text(cx, cy + 90, src + " - 22 NOV", 1, GREY)
    c.rect(8, 694, 1008, 3, INK)

    # numbered world map (left) and the also-on list (right)
    c.text(8, 706, "THE DAY ON THE MAP", 2, INK)
    c.text(516, 706, "ALSO ON 22 NOVEMBER", 2, INK)
    draw_map(c, 8, 726, 492, 192)
    c.text(8, 922, "Red numbers mark stories 1-13.", 1, GREY)
    for i, item in enumerate(ALSO):
        col = 0 if i < 11 else 1
        row = i if i < 11 else i - 11
        x = 516 if col == 0 else 772
        y = 726 + row * 17
        c.rect(x, y + 1, 6, 6, RED)
        c.text(x + 12, y, item, 1, INK)
    c.rect(8, 938, 1008, 3, INK)

    # date-check box
    c.frame(8, 950, 1008, 38, INK, 1)
    c.text(20, 958, "DATE CHECK", 2, RED)
    c.text(150, 961, DATE_CHECK_LEFT, 1, INK)
    c.text(20, 976, DATE_CHECK_NOTYET, 1, INK)

    # sources footer
    c.centre(0, 998, W, SOURCES, 1, GREY)

    write_png(path, c)


# --- minimal PNG encoder (no ancillary chunks, fully deterministic) ----------
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    return out + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)


def write_png(path, c):
    raw = bytearray()
    stride = c.w * 3
    for yy in range(c.h):
        raw.append(0)  # filter: none
        raw += c.pix[yy * stride:(yy + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", c.w, c.h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
