#!/usr/bin/env python3
"""news-image-20261121: draw one page of world news for Saturday 21 November 2026.

Pure Python 3.13 standard library. Renders a 1024x1024 PNG newspaper page
("THE WORLD IN ONE PAGE") with a hand-built 5x7 bitmap font and a tiny
software rasterizer, then writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(or /output/entry.png). Fully deterministic: no randomness, no time, no
network, no file reads. Two runs produce byte-identical output.
"""

import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024

PAPER = (247, 242, 231)
INK = (26, 26, 26)
NAVY = (31, 58, 95)
NAVY_DARK = (22, 42, 70)
RED = (176, 42, 32)
RED_DARK = (140, 30, 22)
GOLD = (201, 162, 39)
GOLD_DARK = (170, 132, 26)
GREY = (112, 108, 96)
LIGHT_GREY = (214, 208, 194)
BLUE_SKY = (173, 205, 225)
GREEN = (46, 125, 70)
ORANGE = (224, 122, 26)
YELLOW = (242, 201, 76)
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows; each row is a 5-bit number, bit 4 is
# the leftmost column. Only uppercase, digits and the punctuation the page
# needs are defined; all page text is rendered uppercase.
# ---------------------------------------------------------------------------
FONT = {
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
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
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
    "-": (0, 0, 0, 0x1F, 0, 0, 0),
    "—": (0, 0, 0, 0x1F, 0, 0, 0),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0x0A, 0, 0, 0, 0),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "·": (0, 0, 0, 0x0C, 0x0C, 0, 0),
    ">": (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    "<": (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
}


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.rect(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (yy - cy) * (yy - cy))))
            self.rect(cx - dx, yy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = math.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
                if r - t < d <= r:
                    self.set(xx, yy, c)

    def triangle(self, x0, y0, x1, y1, x2, y2, c):
        minx = max(0, min(x0, x1, x2))
        maxx = min(self.w - 1, max(x0, x1, x2))
        miny = max(0, min(y0, y1, y2))
        maxy = min(self.h - 1, max(y0, y1, y2))
        d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if d == 0:
            return
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                a = ((y1 - y2) * (xx - x2) + (x2 - x1) * (yy - y2)) / d
                b = ((y2 - y0) * (xx - x2) + (x0 - x2) * (yy - y2)) / d
                cc = 1 - a - b
                if a >= 0 and b >= 0 and cc >= 0:
                    self.set(xx, yy, c)

    def polyline(self, pts, c, t=2):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, t)

    def star(self, cx, cy, r_out, r_in, c):
        pts = []
        for i in range(10):
            r = r_out if i % 2 == 0 else r_in
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        for i in range(10):
            self.triangle(cx, cy, pts[i][0], pts[i][1],
                          pts[(i + 1) % 10][0], pts[(i + 1) % 10][1], c)


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color):
    s = s.upper()
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits >> (4 - col) & 1:
                    cv.rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 6 * scale


def draw_centered(cv, cx, y, s, scale, color):
    draw_text(cv, cx - text_width(s, scale) // 2, y, s, scale, color)


def wrap_text(text, max_width, scale):
    """Greedy word wrap. Raises if a single word cannot fit."""
    words = text.upper().split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            if text_width(word, scale) > max_width:
                raise ValueError("word too wide: " + word)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, text, max_width, scale, color, leading=None):
    if leading is None:
        leading = 7 * scale + 3 * scale
    lines = wrap_text(text, max_width, scale)
    for i, line in enumerate(lines):
        draw_text(cv, x, y + i * leading, line, scale, color)
    return y + len(lines) * leading


# ---------------------------------------------------------------------------
# Flags and pictograms
# ---------------------------------------------------------------------------
def draw_lead_art(cv, x, y, w, h):
    """Night raid in Sinaloa: desert mountains, helicopter, gold badge."""
    cv.rect(x, y, w, h, NAVY_DARK)
    # stars
    for sx, sy in ((28, 22), (70, 44), (120, 18), (170, 40), (220, 24),
                   (270, 48), (320, 20), (48, 70), (250, 74), (340, 60)):
        cv.rect(x + sx, y + sy, 3, 3, WHITE)
    # crescent moon
    cv.circle(x + w - 56, y + 46, 24, YELLOW)
    cv.circle(x + w - 64, y + 40, 20, NAVY_DARK)
    # helicopter silhouette
    hx, hy = x + 52, y + 78
    cv.rect(hx, hy, 84, 22, INK)
    cv.rect(hx + 78, hy + 6, 62, 6, INK)
    cv.rect(hx + 132, hy - 6, 8, 16, INK)
    cv.hline(hx - 18, hy - 8, 120, INK, 3)
    cv.line(hx + 12, hy + 22, hx + 2, hy + 40, INK, 3)
    cv.line(hx + 68, hy + 22, hx + 78, hy + 40, INK, 3)
    cv.circle(hx + 30, hy + 11, 6, YELLOW)
    # mountains
    base = y + h - 96
    cv.triangle(x, base + 88, x + 120, base - 10, x + 250, base + 88, INK)
    cv.triangle(x + 170, base + 88, x + 300, base - 34, x + w, base + 88, INK)
    # ground
    cv.rect(x, base + 88 - 6, w, 6, INK)
    # big gold badge with star
    bx, by = x + w - 108, base - 58
    cv.circle(bx, by, 52, GOLD)
    cv.ring(bx, by, 52, GOLD_DARK, 3)
    cv.star(bx, by, 38, 16, NAVY_DARK)
    draw_text(cv, bx - 34, by + 58, "SINALOA", 1, YELLOW)


def draw_chart_icon(cv, x, y, s):
    cv.rect(x, y, s, s, WHITE)
    cv.rect(x, y, s, s, INK)  # placeholder overwritten below
    cv.rect(x + 2, y + 2, s - 4, s - 4, WHITE)
    for gy in range(y + 16, y + s - 8, 16):
        cv.hline(x + 8, gy, s - 16, LIGHT_GREY, 1)
    pts = [(x + 10, y + 22), (x + 28, y + 30), (x + 44, y + 26),
           (x + 60, y + 48), (x + 76, y + 58), (x + 88, y + 78)]
    cv.polyline(pts, RED, 3)
    cv.triangle(x + 88, y + 78, x + 76, y + 74, x + 84, y + 88, RED)
    cv.hline(x + 6, y + s - 8, s - 12, INK, 2)
    cv.vline(x + 6, y + 8, s - 16, INK, 2)


def draw_bag_icon(cv, x, y, s):
    cv.rect(x, y, s, s, (238, 232, 214))
    cv.rect(x + 24, y + 30, 40, 28, (120, 40, 90))
    cv.rect(x + 24, y + 30, 40, 7, (90, 28, 68))
    cv.line(x + 34, y + 30, x + 34, y + 18, INK, 3)
    cv.line(x + 54, y + 30, x + 54, y + 18, INK, 3)
    cv.hline(x + 34, y + 18, 20, INK, 3)
    draw_text(cv, x + 32, y + 40, "WB", 2, WHITE)


def draw_blast_icon(cv, x, y, s):
    cv.rect(x, y, s, s, (52, 52, 58))
    cx, cy = x + s // 2, y + s // 2 - 8
    for k in range(12):
        a = k * math.pi / 6
        x1 = int(cx + 14 * math.cos(a))
        y1 = int(cy + 14 * math.sin(a))
        x2 = int(cx + 42 * math.cos(a + 0.18))
        y2 = int(cy + 42 * math.sin(a + 0.18))
        cv.triangle(cx, cy, x1, y1, x2, y2, ORANGE if k % 2 else YELLOW)
    cv.circle(cx, cy, 12, RED_DARK)
    # buildings below
    cv.rect(x + 8, y + s - 26, 18, 26, BLACK)
    cv.rect(x + 32, y + s - 34, 22, 34, BLACK)
    cv.rect(x + 60, y + s - 22, 20, 22, BLACK)


def draw_scales_icon(cv, x, y, s):
    cv.rect(x, y, s, s, (238, 232, 214))
    cx = x + s // 2
    cv.vline(cx, y + 14, 56, INK, 3)
    cv.hline(cx - 30, y + 22, 60, INK, 3)
    cv.circle(cx, y + 14, 4, INK)
    for dx in (-30, 30):
        cv.line(cx + dx, y + 22, cx + dx - 10, y + 52, INK, 2)
        cv.line(cx + dx, y + 22, cx + dx + 10, y + 52, INK, 2)
        cv.triangle(cx + dx - 12, y + 52, cx + dx + 12, y + 52, cx + dx, y + 64, GOLD_DARK)
    cv.rect(cx - 18, y + s - 14, 36, 6, INK)


def draw_globe_icon(cv, x, y, s):
    cv.rect(x, y, s, s, (226, 240, 232))
    cx, cy = x + s // 2, y + s // 2
    cv.circle(cx, cy, 30, (64, 140, 190))
    cv.circle(cx - 10, cy - 8, 10, GREEN)
    cv.circle(cx + 12, cy + 10, 12, GREEN)
    cv.circle(cx + 6, cy - 14, 6, GREEN)
    cv.ring(cx, cy, 30, INK, 2)
    cv.circle(x + s - 12, y + 10, 7, YELLOW)


def draw_ball_icon(cv, x, y, s):
    cv.rect(x, y, s, s, (226, 240, 232))
    cx, cy = x + s // 2, y + s // 2
    rx, ry = 34, 22
    for yy in range(cy - ry, cy + ry + 1):
        dx = int(rx * math.sqrt(max(0, 1 - ((yy - cy) / ry) ** 2)))
        cv.rect(cx - dx, yy, 2 * dx + 1, 1, (150, 60, 40))
    cv.line(cx - 24, cy - 13, cx + 24, cy + 13, WHITE, 2)
    cv.line(cx - 8, cy - 14, cx - 2, cy - 2, WHITE, 2)
    cv.line(cx + 2, cy - 2, cx + 8, cy + 10, WHITE, 2)
    cv.line(cx + 12, cy + 2, cx + 18, cy + 14, WHITE, 2)


def draw_ski_icon(cv, x, y, s):
    cv.rect(x, y, s, s, (226, 240, 232))
    cv.triangle(x + 4, y + s - 14, x + 34, y + 16, x + 62, y + s - 14, WHITE)
    cv.triangle(x + 36, y + s - 14, x + 58, y + 32, x + 64, y + s - 14, (200, 214, 226))
    cv.circle(x + 34, y + 16, 4, YELLOW)
    cv.line(x + 48, y + 40, x + 56, y + 48, RED, 3)
    cv.line(x + 56, y + 48, x + 52, y + 54, RED, 3)
    cv.hline(x + 44, y + 54, 14, INK, 3)


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------
def draw_page():
    cv = Canvas(W, H, PAPER)
    mx = 36

    # Masthead bar
    cv.rect(0, 0, W, 56, NAVY)
    draw_centered(cv, W // 2, 16, "SATURDAY · 21 NOVEMBER 2026", 3, WHITE)

    # Title
    draw_centered(cv, W // 2, 74, "THE WORLD IN ONE PAGE", 6, INK)
    draw_centered(cv, W // 2, 124, "THE DAY'S NEWS FROM EVERY CORNER OF THE GLOBE",
                  2, GREY)
    cv.hline(mx, 146, W - 2 * mx, INK, 3)
    cv.hline(mx, 152, W - 2 * mx, INK, 1)

    # ---- Lead story ----
    draw_text(cv, mx, 172, "MEXICO", 2, RED)
    draw_para(cv, mx, 200,
              "MEXICO CAPTURES 'EL CHAPO ISIDRO'",
              566, 4, INK, leading=36)
    draw_para(cv, mx, 292,
              "FBI MOST-WANTED CARTEL BOSS FAUSTO ISIDRO MEZA FLORES "
              "SEIZED IN A MILITARY RAID IN SINALOA.",
              566, 2, INK, leading=20)
    draw_para(cv, mx, 372,
              "ANNOUNCED SATURDAY MORNING AFTER THE FRIDAY-NIGHT OPERATION.",
              566, 2, GREY, leading=20)
    draw_text(cv, mx, 452, "SINALOA, MEXICO — SATURDAY", 1, GREY)
    draw_lead_art(cv, 622, 172, 366, 296)
    draw_centered(cv, 622 + 183, 478, "THE RAID IN SINALOA THAT CAUGHT EL CHAPO ISIDRO", 1, GREY)

    cv.hline(mx, 508, W - 2 * mx, INK, 2)

    # ---- Four stories, 2 x 2 grid ----
    cells = [
        ("MARKETS", draw_chart_icon,
         "MARKETS PLUNGE AS AI SELLOFF SPREADS",
         "S&P 500 -3.7%, NASDAQ -5.3% ON FRIDAY. NVIDIA -14% ON A "
         "REPORT OF AN SEC ACCOUNTING PROBE. WORST WEEK SINCE 2020."),
        ("UKRAINE", draw_blast_icon,
         "RUSSIAN MISSILE HITS ZELENSKYY'S HOMETOWN",
         "STRIKE ON KRYVYI RIH KILLS 2 — A 7-YEAR-OLD BOY AND A "
         "PARAMEDIC — AND WOUNDS 42."),
        ("FRANCE", draw_globe_icon,
         "COST-OF-LIVING MARCHES DRAW 82,500",
         "INTERIOR MINISTRY COUNTS 82,500 MARCHERS NATIONWIDE, 21,500 "
         "IN PARIS. TURNOUT DOWN ON LAST WEEK."),
        ("JUSTICE", draw_scales_icon,
         "DEPARDIEU AND HOUELLEBECQ INVESTIGATED",
         "PARIS PROSECUTOR OPENS A JUDICIAL INVESTIGATION INTO THE "
         "ACTOR AND THE AUTHOR OVER ALLEGED SEXUAL OFFENCES."),
    ]
    col_w = 464
    row_h = 148
    for idx, (kicker, icon, head, cap) in enumerate(cells):
        cx = mx + (idx % 2) * (col_w + 24)
        cy = 528 + (idx // 2) * row_h
        draw_text(cv, cx, cy, kicker, 1, RED)
        icon(cv, cx, cy + 16, 96)
        tx = cx + 112
        tw = col_w - 112
        end = draw_para(cv, tx, cy + 16, head, tw, 2, INK, leading=20)
        draw_para(cv, tx, end + 6, cap, tw, 1, INK, leading=11)
        if idx % 2 == 0:
            cv.vline(cx + col_w + 12, cy, row_h - 16, LIGHT_GREY, 1)
    cv.hline(mx, 812, W - 2 * mx, INK, 2)

    # ---- Also today ----
    draw_text(cv, mx, 830, "ALSO TODAY", 2, RED)
    briefs = [
        (draw_bag_icon,
         "WILDBERRIES CHIEF TATYANA KIM STEPS DOWN DAYS AFTER EU "
         "SANCTIONS. ALEXEI KULIKOV IS NAMED NEW CEO."),
        (draw_ball_icon,
         "IRELAND BEAT SOUTH AFRICA 20-17 IN RUGBY. THE SPRINGBOKS "
         "STILL BOOK A NATIONS CHAMPIONSHIP FINAL."),
        (draw_ski_icon,
         "LARA COLTURI WINS THE GURGL SLALOM — HER FIRST WORLD CUP "
         "WIN, AND ALBANIA'S FIRST."),
    ]
    bw = 296
    for i, (icon, text) in enumerate(briefs):
        bx = mx + i * (bw + 24)
        icon(cv, bx, 862, 64)
        draw_para(cv, bx + 76, 862, text, bw - 76, 1, INK, leading=11)

    # Footer
    cv.hline(mx, 962, W - 2 * mx, INK, 1)
    draw_centered(cv, W // 2, 976, "THE WORLD IN ONE PAGE · SATURDAY 21 NOVEMBER 2026",
                  1, GREY)
    return cv


# ---------------------------------------------------------------------------
# PNG encoding (filter 0, fixed zlib level: byte-identical every run)
# ---------------------------------------------------------------------------
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw.extend(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = draw_page()
    data = encode_png(cv)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    sys.stdout.write("wrote %s (%d bytes)\n" % (path, len(data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
