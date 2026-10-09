"""Картинки для красивого установщика Rai (NSIS) — без сторонних библиотек.

Делает три 24-битных BMP в desktop/build:
  • installerSidebar.bmp  (164×314) — левая панель мастера установки,
  • uninstallerSidebar.bmp (164×314) — то же для удаления,
  • installerHeader.bmp    (150×57)  — шапка на страницах мастера.

Фон — фирменный градиент Rai (красный → розовый → фиолетовый), поверх — логотип «Rai» своим
пиксельным шрифтом. Запускается скриптом prepare.js перед сборкой; можно и руками:
    python desktop/scripts/make_installer_art.py
"""

import os
import struct

BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build")

# Фирменные цвета Rai (как в вебе: --red #ff2d2d, --pink #ff3d81, --violet #8b5cff), (r,g,b)
STOPS = [(0.0, (255, 45, 45)), (0.5, (255, 61, 129)), (1.0, (139, 92, 255))]
DARK = (14, 14, 22)

# Пиксельный шрифт 5×7 для логотипа (только нужные буквы)
FONT = {
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "a": ["00000", "00000", "01110", "00001", "01111", "10001", "01111"],
    "i": ["00100", "00000", "01100", "00100", "00100", "00100", "01110"],
}


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(t):
    """Цвет градиента в точке 0..1."""
    for i in range(len(STOPS) - 1):
        t0, c0 = STOPS[i]
        t1, c1 = STOPS[i + 1]
        if t <= t1:
            return _lerp(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0)
    return STOPS[-1][1]


def _canvas(w, h, diag=True):
    """Пиксели [y][x] = (r,g,b) с диагональным градиентом + лёгкое затемнение к низу."""
    px = [[(0, 0, 0)] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            t = (x / max(1, w - 1) + y / max(1, h - 1)) / 2 if diag else y / max(1, h - 1)
            r, g, b = _gradient(min(1.0, t))
            shade = 1.0 - 0.18 * (y / max(1, h - 1))      # мягко темнее книзу
            px[y][x] = (round(r * shade), round(g * shade), round(b * shade))
    return px


def _text(px, text, x0, y0, scale, color=(255, 255, 255), spacing=1):
    """Нарисовать строку пиксельным шрифтом."""
    x = x0
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            x += (5 + spacing) * scale
            continue
        for ry, row in enumerate(glyph):
            for rx, bit in enumerate(row):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            px_y, px_x = y0 + ry * scale + dy, x + rx * scale + dx
                            if 0 <= px_y < len(px) and 0 <= px_x < len(px[0]):
                                px[px_y][px_x] = color
        x += (5 + spacing) * scale


def _dot_strip(px, x0, y0, w, color, gap=6, size=3):
    """Декоративная строчка из точек (под логотипом)."""
    x = x0
    while x < x0 + w:
        for dy in range(size):
            for dx in range(size):
                if 0 <= y0 + dy < len(px) and 0 <= x + dx < len(px[0]):
                    px[y0 + dy][x + dx] = color
        x += gap


def _write_bmp(path, px):
    h, w = len(px), len(px[0])
    row_pad = (-w * 3) % 4
    raw = bytearray()
    for y in range(h - 1, -1, -1):          # BMP хранит строки снизу вверх
        for x in range(w):
            r, g, b = px[y][x]
            raw += bytes((b & 255, g & 255, r & 255))
        raw += b"\x00" * row_pad
    size = 54 + len(raw)
    header = struct.pack("<2sIHHI", b"BM", size, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(raw), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + raw)


def _logo_sidebar(w, h):
    px = _canvas(w, h, diag=True)
    _text(px, "Rai", 28, 150, 7, (255, 255, 255))      # крупный логотип по центру
    _dot_strip(px, 28, 215, 108, (255, 255, 255), gap=10, size=4)
    return px


def _logo_header(w, h):
    px = _canvas(w, h, diag=True)
    _text(px, "Rai", 10, 16, 3, (255, 255, 255))
    return px


def main():
    os.makedirs(BUILD, exist_ok=True)
    side = _logo_sidebar(164, 314)
    _write_bmp(os.path.join(BUILD, "installerSidebar.bmp"), side)
    _write_bmp(os.path.join(BUILD, "uninstallerSidebar.bmp"), side)
    _write_bmp(os.path.join(BUILD, "installerHeader.bmp"), _logo_header(150, 57))
    print("Картинки установщика готовы:", os.path.normpath(BUILD))


if __name__ == "__main__":
    main()
