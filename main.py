#!/usr/bin/env python3
"""
news-image-20261125 — "The Day in News", Wednesday 25 November 2026.

Renders a single 1024x1024 PNG summarising the day's world news using ONLY the
Python standard library (no Pillow). The PNG is hand-encoded with zlib + struct
+ binascii.crc32, and all text is drawn from an embedded 5x7 bitmap font.

Run:  python3 main.py
Out:  /output/entry.png   (1024x1024, whole valid PNG)
"""
import os
import struct
import zlib
import binascii

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette ---
INK = (18, 20, 26)        # near-black background
PAPER = (238, 236, 228)   # warm newsprint
ACCENT = (196, 46, 46)    # masthead red
GREY = (128, 128, 128)    # footer grey

# ------------------------------------------------------------- 5x7 bitmap ---
# Each glyph: 7 rows, 5 bits wide (MSB = leftmost pixel).
FONT = {
    ' ': [0b00000]*7,
    'A': [0b01110,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001],
    'B': [0b11110,0b10001,0b10001,0b11110,0b10001,0b10001,0b11110],
    'C': [0b01110,0b10001,0b10000,0b10000,0b10000,0b10001,0b01110],
    'D': [0b11100,0b10010,0b10001,0b10001,0b10001,0b10010,0b11100],
    'E': [0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b11111],
    'F': [0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b10000],
    'G': [0b01110,0b10001,0b10000,0b10111,0b10001,0b10001,0b01111],
    'H': [0b10001,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001],
    'I': [0b01110,0b00100,0b00100,0b00100,0b00100,0b00100,0b01110],
    'J': [0b00111,0b00010,0b00010,0b00010,0b00010,0b10010,0b01100],
    'K': [0b10001,0b10010,0b10100,0b11000,0b10100,0b10010,0b10001],
    'L': [0b10000,0b10000,0b10000,0b10000,0b10000,0b10000,0b11111],
    'M': [0b10001,0b11011,0b10101,0b10101,0b10001,0b10001,0b10001],
    'N': [0b10001,0b11001,0b10101,0b10011,0b10001,0b10001,0b10001],
    'O': [0b01110,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110],
    'P': [0b11110,0b10001,0b10001,0b11110,0b10000,0b10000,0b10000],
    'Q': [0b01110,0b10001,0b10001,0b10001,0b10101,0b10010,0b01101],
    'R': [0b11110,0b10001,0b10001,0b11110,0b10100,0b10010,0b10001],
    'S': [0b01111,0b10000,0b10000,0b01110,0b00001,0b00001,0b11110],
    'T': [0b11111,0b00100,0b00100,0b00100,0b00100,0b00100,0b00100],
    'U': [0b10001,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110],
    'V': [0b10001,0b10001,0b10001,0b10001,0b10001,0b01010,0b00100],
    'W': [0b10001,0b10001,0b10001,0b10101,0b10101,0b11011,0b10001],
    'X': [0b10001,0b10001,0b01010,0b00100,0b01010,0b10001,0b10001],
    'Y': [0b10001,0b10001,0b01010,0b00100,0b00100,0b00100,0b00100],
    'Z': [0b11111,0b00001,0b00010,0b00100,0b01000,0b10000,0b11111],
    '0': [0b01110,0b10001,0b10011,0b10101,0b11001,0b10001,0b01110],
    '1': [0b00100,0b01100,0b00100,0b00100,0b00100,0b00100,0b01110],
    '2': [0b01110,0b10001,0b00001,0b00010,0b00100,0b01000,0b11111],
    '3': [0b11111,0b00010,0b00100,0b00010,0b00001,0b10001,0b01110],
    '4': [0b00010,0b00110,0b01010,0b10010,0b11111,0b00010,0b00010],
    '5': [0b11111,0b10000,0b11110,0b00001,0b00001,0b10001,0b01110],
    '6': [0b00110,0b01000,0b10000,0b11110,0b10001,0b10001,0b01110],
    '7': [0b11111,0b00001,0b00010,0b00100,0b01000,0b01000,0b01000],
    '8': [0b01110,0b10001,0b10001,0b01110,0b10001,0b10001,0b01110],
    '9': [0b01110,0b10001,0b10001,0b01111,0b00001,0b00010,0b01100],
    '.': [0,0,0,0,0,0b00100,0b00100],
    ',': [0,0,0,0,0b00100,0b00100,0b01000],
    ':': [0,0b00100,0b00100,0,0b00100,0b00100,0],
    ';': [0,0b00100,0b00100,0,0b00100,0b00100,0b01000],
    '-': [0,0,0,0b11111,0,0,0],
    '+': [0,0b00100,0b00100,0b11111,0b00100,0b00100,0],
    '%': [0b11001,0b11010,0b00010,0b00100,0b01000,0b01011,0b10011],
    '/': [0b00001,0b00001,0b00010,0b00100,0b01000,0b10000,0b10000],
    "'": [0b00100,0b00100,0b01000,0,0,0,0],
    '"': [0b01010,0b01010,0,0,0,0,0],
    '!': [0b00100,0b00100,0b00100,0b00100,0b00100,0,0b00100],
    '?': [0b01110,0b10001,0b00001,0b00010,0b00100,0,0b00100],
    '(': [0b00010,0b00100,0b01000,0b01000,0b01000,0b00100,0b00010],
    ')': [0b01000,0b00100,0b00010,0b00010,0b00010,0b00100,0b01000],
    '$': [0b00100,0b01111,0b10100,0b01110,0b00101,0b11110,0b00100],
    '&': [0b01100,0b10010,0b10100,0b01000,0b10101,0b10010,0b01101],
    '#': [0b01010,0b01010,0b11111,0b01010,0b11111,0b01010,0b01010],
    '@': [0b01110,0b10001,0b10111,0b10101,0b10111,0b10000,0b01110],
    '*': [0,0b00100,0b10101,0b01110,0b10101,0b00100,0],
    '=': [0,0,0b11111,0,0b11111,0,0],
}

SCALE = 2          # font pixel scale for body
HEAD_SCALE = 4     # scale for big numbers/masthead sub


def text_pixels(s):
    """Yield (x, y) pixel offsets for string s at scale=1."""
    cx = 0
    for ch in s.upper():
        rows = FONT.get(ch, FONT['?'])
        for ry, bits in enumerate(rows):
            for rx in range(5):
                if bits >> (4 - rx) & 1:
                    yield (cx + rx, ry)
        cx += 6
    return


def text_w(s, scale=SCALE):
    return (6 * len(s) - 1) * scale


def draw_text(buf, s, x, y, color, scale=SCALE):
    for px, py in text_pixels(s):
        fx, fy = x + px * scale, y + py * scale
        for dy in range(scale):
            row = fy + dy
            if 0 <= row < HEIGHT:
                base = row * WIDTH
                for dx in range(scale):
                    col = fx + dx
                    if 0 <= col < WIDTH:
                        buf[base + col] = color


def wrap(s, max_px, scale=SCALE):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if text_w(cand, scale) <= max_px or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def encode_png(raw, width, height):
    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", binascii.crc32(body) & 0xffffffff))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    stride = width * 3
    scan = b"".join(b"\x00" + raw[y*stride:(y+1)*stride] for y in range(height))
    idat = zlib.compress(scan, 9)
    return (sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat)
            + chunk(b"IEND", b""))


def render():
    buf = [INK] * (WIDTH * HEIGHT)

    # --- top rule + masthead -------------------------------------------
    for x in range(WIDTH):
        for y in range(0, 14):
            buf[y * WIDTH + x] = ACCENT

    mast = "THE DAY IN NEWS"
    ms = 7
    mw = text_w(mast, ms)
    draw_text(buf, mast, (WIDTH - mw) // 2, 46, PAPER, ms)

    sub = "WEDNESDAY 25 NOVEMBER 2026"
    ss = 3
    sw = text_w(sub, ss)
    draw_text(buf, sub, (WIDTH - sw) // 2, 120, ACCENT, ss)

    # divider under masthead
    for x in range(60, WIDTH - 60):
        buf[168 * WIDTH + x] = PAPER

    # --- headlines ------------------------------------------------------
    stories = [
        ("WORLD", "GUKEH DRAWS SINDAROV IN OPENER OF WORLD CHESS CHAMPIONSHIP"),
        ("TECH", "NVIDIA REINSTATES JENSEN HUANG AS CEO AFTER TRUMP INTERVENES"),
        ("CLIMATE", "COP31 ENDS IN DEADLOCK AS FOSSIL FUEL DEAL COLLAPSES"),
        ("SPORTS", "VAIBHAV SOORYAVANSHI HITS 28-BALL CENTURY WITH 22 SIXES"),
        ("SPACE", "CHINA PICKS PAKISTANI ASTRONAUT FOR SHENZHOU-24 MISSION"),
        ("ECONOMY", "ANTHROPIC IPO SOARS IN MARKET DEBUT, HITS TRILLION-DOLLAR VALUE"),
        ("ASIA", "INDIA AND NEPAL FLAG OFF FIRST AYODHYA-JANAKPUR TRAIN LINK"),
        ("US", "RUSSIA PLANS TO LAUNCH NUCLEAR-ARMED SATELLITE, REPORTS SAY"),
    ]

    y = 196
    left = 70
    maxw = WIDTH - 2 * left
    line_h = 10 * SCALE
    for tag, headline in stories:
        # tag pill
        tagw = text_w(tag, 2)
        for yy in range(y, y + 20):
            for xx in range(left - 8, left + tagw + 8):
                if 0 <= xx < WIDTH:
                    buf[yy * WIDTH + xx] = ACCENT
        draw_text(buf, tag, left, y + 4, PAPER, 2)

        ly = y + 28
        for line in wrap(headline, maxw, SCALE):
            draw_text(buf, line, left, ly, PAPER, SCALE)
            ly += line_h
        y = ly + 16

    # --- footer ---------------------------------------------------------
    foot_top = HEIGHT - 70
    for x in range(60, WIDTH - 60):
        buf[foot_top * WIDTH + x] = PAPER
    foot = "ONE IMAGE * EVERY STORY * 25 NOV 2026"
    fw = text_w(foot, 2)
    draw_text(buf, foot, (WIDTH - fw) // 2, foot_top + 18, GREY, 2)

    # pack to bytes
    raw = bytearray(WIDTH * HEIGHT * 3)
    for i, (r, g, b) in enumerate(buf):
        raw[i*3] = r
        raw[i*3+1] = g
        raw[i*3+2] = b
    return encode_png(bytes(raw), WIDTH, HEIGHT)


def main():
    png = render()
    out_dir = "/output"
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "entry.png")
    with open(out, "wb") as f:
        f.write(png)
    print("wrote", out, len(png), "bytes",
          "%dx%d" % (WIDTH, HEIGHT))


if __name__ == "__main__":
    main()
