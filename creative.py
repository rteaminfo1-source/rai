"""Свои картинки (SVG) и презентации Rai — без внешних сервисов.

Картинка собирается из «сцен» по словам в запросе: небо (день, закат, ночь, космос),
горы, море, лес, город, пустыня, зима, сердце, цветок, абстракция, логотип.
Презентация собирается из базы знаний Rai.
"""

import math
import random
import re
import zlib
from xml.sax.saxutils import escape

import nlp

W, H = 1200, 800

COLORS = {
    "красн": "#e10600", "алый": "#ff2a2a", "син": "#1e5bff", "голуб": "#4fc3f7",
    "зелен": "#2ecc71", "желт": "#ffd200", "оранж": "#ff7a00", "фиолет": "#8e44ad",
    "розов": "#ff5fa2", "бирюз": "#1abc9c", "золот": "#d4af37", "серебр": "#c0c0c0",
    "бел": "#f2f2f2", "черн": "#151515",
}

# Сцены: имя -> начала слов, по которым их узнаём.
SCENES = [
    ("logo", ("логотип", "лого", "эмблем", "значок")),
    ("space", ("космос", "галактик", "планет", "вселенн")),
    ("night", ("ноч", "луна", "луну", "луной", "звезд")),
    ("sunset", ("закат", "вечер")),
    ("sunrise", ("рассвет", "утро", "утрен")),
    ("winter", ("зим", "снег", "снеж", "мороз")),
    ("desert", ("пустын", "дюн", "песок")),
    ("city", ("город", "небоскреб", "улиц", "дом", "здани")),
    ("sea", ("море", "моря", "морск", "океан", "волн", "озер", "пляж", "река")),
    ("mountains", ("гора", "горы", "гору", "горн", "горах", "скал", "вершин")),
    ("forest", ("лес", "дерев", "елк", "ель", "ели", "сосн", "роща")),
    ("heart", ("сердц", "сердечк", "любов", "валентин")),
    ("flower", ("цветок", "цветы", "цветочк", "роза", "розу", "розы", "ромашк", "тюльпан")),
    ("abstract", ("абстракц", "узор", "паттерн", "геометр", "фон", "обои")),
]

_IMAGE_WORDS = re.compile(
    r"нарису|изобрази|картинк|изображени|рисун|логотип|нарисовать|арт\b|обои", re.I
)
# «Как сделать картинку?», «ты умеешь рисовать?» — это вопросы, а не просьбы.
_QUESTION = re.compile(r"^\s*(а\s+)?(как|ты умеешь|умеешь|можешь ли|что ты)\b|\bумеешь\b", re.I)


def is_image_request(text: str) -> bool:
    return bool(_IMAGE_WORDS.search(text or "")) and not _QUESTION.search(text or "")


def _words(text):
    return nlp.normalize(text).split()


def _has(words, prefixes):
    return any(w.startswith(p) for w in words for p in prefixes)


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


class _Canvas:
    def __init__(self, rnd):
        self.rnd = rnd
        self.defs = []
        self.items = []
        self._id = 0

    def uid(self, prefix):
        self._id += 1
        return f"{prefix}{self._id}"

    def gradient(self, stops, vertical=True):
        gid = self.uid("g")
        coords = 'x1="0" y1="0" x2="0" y2="1"' if vertical else 'x1="0" y1="0" x2="1" y2="0"'
        body = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        self.defs.append(f'<linearGradient id="{gid}" {coords}>{body}</linearGradient>')
        return f"url(#{gid})"

    def glow(self, color):
        gid = self.uid("r")
        self.defs.append(
            f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="0.9"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        )
        return f"url(#{gid})"

    def add(self, svg):
        self.items.append(svg)

    def svg(self, title):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f"<title>{escape(title)}</title><defs>{''.join(self.defs)}</defs>{''.join(self.items)}</svg>"
        )


# ------------------------------------------------------------------ элементы

def _sky(c, mode, accent):
    skies = {
        "day": [("0", "#2f7fd8"), ("1", "#bfe3ff")],
        "sunset": [("0", "#1b0b2e"), ("0.45", "#b3143a"), ("0.8", "#ff6a2a"), ("1", "#ffc15a")],
        "sunrise": [("0", "#2a3a7a"), ("0.55", "#ff8fa3"), ("1", "#ffe0a3")],
        "night": [("0", "#03040c"), ("1", "#141b3d")],
        "space": [("0", "#000000"), ("1", "#07030f")],
        "winter": [("0", "#8fb3d9"), ("1", "#eef5ff")],
        "desert": [("0", "#f39c4a"), ("1", "#ffe2a8")],
        "dark": [("0", "#0a0a0a"), ("1", "#1a0505")],
    }
    stops = skies.get(mode, skies["day"])
    if accent and mode in ("day", "dark"):
        stops = [(o, _mix(col, accent, 0.35)) for o, col in stops]
    c.add(f'<rect width="{W}" height="{H}" fill="{c.gradient(stops)}"/>')


def _stars(c, n, top=H):
    r = c.rnd
    parts = []
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(0, top)
        size = r.choice([0.8, 1, 1.2, 1.6, 2.2])
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{size}" fill="#fff" opacity="{r.uniform(0.4, 1):.2f}"/>')
    c.add("".join(parts))


def _sun(c, x, y, r, color):
    c.add(f'<circle cx="{x}" cy="{y}" r="{r * 3}" fill="{c.glow(color)}"/>')
    c.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')


def _moon(c, x, y, r):
    c.add(f'<circle cx="{x}" cy="{y}" r="{r * 2.6}" fill="{c.glow("#dfe8ff")}"/>')
    c.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#f4f1e6"/>')
    c.add(f'<circle cx="{x + r * 0.45}" cy="{y - r * 0.2}" r="{r * 0.9}" fill="#0b1026" opacity="0.92"/>')


def _ridge(c, base, height, color, jag):
    r = c.rnd
    pts = [(0, H)]
    x = 0
    while x <= W:
        pts.append((x, base - r.uniform(0.3, 1.0) * height))
        x += r.uniform(60, 60 + jag)
    pts += [(W, base - r.uniform(0.3, 1.0) * height), (W, H)]
    c.add(f'<polygon points="{" ".join(f"{a:.0f},{b:.0f}" for a, b in pts)}" fill="{color}"/>')


def _mountains(c, palette, snow):
    for i, color in enumerate(palette):
        base = 520 + i * 70
        _ridge(c, base, 260 - i * 60, color, 140)
    if snow:
        c.add(f'<rect y="{H - 90}" width="{W}" height="90" fill="#f4f8ff"/>')


def _sea(c, top, color, sun_x=None, sun_color=None):
    c.add(f'<rect y="{top}" width="{W}" height="{H - top}" fill="{c.gradient([("0", color), ("1", _mix(color, "#000000", 0.6))])}"/>')
    if sun_x is not None:
        for i in range(10):
            w = 160 - i * 12
            c.add(f'<rect x="{sun_x - w / 2:.0f}" y="{top + 12 + i * 18}" width="{w}" height="4" rx="2" fill="{sun_color}" opacity="{0.7 - i * 0.05:.2f}"/>')
    r = c.rnd
    for i in range(18):
        y = top + 20 + i * (H - top) / 18
        x = r.uniform(-50, W)
        c.add(f'<path d="M{x:.0f} {y:.0f} q30 -8 60 0 t60 0" stroke="#ffffff" stroke-opacity="0.25" fill="none" stroke-width="2"/>')


def _tree(c, x, ground, h, color):
    w = h * 0.42
    c.add(f'<rect x="{x - 4:.0f}" y="{ground - h * 0.15:.0f}" width="8" height="{h * 0.15:.0f}" fill="#2b1a0e"/>')
    for k in range(3):
        top = ground - h + k * h * 0.22
        c.add(f'<polygon points="{x:.0f},{top:.0f} {x - w * (0.6 + k * 0.2):.0f},{top + h * 0.45:.0f} '
              f'{x + w * (0.6 + k * 0.2):.0f},{top + h * 0.45:.0f}" fill="{color}"/>')


def _forest(c, ground, color, snow=False):
    r = c.rnd
    c.add(f'<rect y="{ground}" width="{W}" height="{H - ground}" fill="{"#eef4ff" if snow else _mix(color, "#000000", 0.5)}"/>')
    for layer, shade in ((0, 0.35), (1, 0.0)):
        for _ in range(16):
            h = r.uniform(120, 240) * (0.75 if layer == 0 else 1)
            _tree(c, r.uniform(0, W), ground + layer * 30, h, _mix(color, "#000000", shade))


def _city(c, ground, night, accent):
    r = c.rnd
    x = 0
    while x < W:
        w = r.uniform(60, 130)
        h = r.uniform(150, 460)
        body = "#0d0d12" if night else "#3b4252"
        c.add(f'<rect x="{x:.0f}" y="{ground - h:.0f}" width="{w - 6:.0f}" height="{h:.0f}" fill="{body}"/>')
        for wy in range(int(ground - h + 16), int(ground - 14), 26):
            for wx in range(int(x + 10), int(x + w - 20), 20):
                if r.random() < (0.45 if night else 0.2):
                    c.add(f'<rect x="{wx}" y="{wy}" width="10" height="14" fill="{accent or ("#ffd36b" if night else "#cfe7ff")}" opacity="0.9"/>')
        x += w
    c.add(f'<rect y="{ground}" width="{W}" height="{H - ground}" fill="#08080a"/>')


def _dunes(c):
    for i, color in enumerate(("#e9a24f", "#d9863a", "#c46f2a")):
        y = 520 + i * 80
        c.add(f'<path d="M0 {y} C300 {y - 90} 500 {y + 60} 800 {y - 40} S1100 {y + 30} {W} {y - 20} L{W} {H} L0 {H} Z" fill="{color}"/>')


def _snowfall(c):
    r = c.rnd
    c.add("".join(
        f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(0, H):.0f}" r="{r.uniform(1.5, 4):.1f}" fill="#fff" opacity="0.85"/>'
        for _ in range(140)
    ))


def _heart(c, color):
    fill = c.gradient([("0", _mix(color, "#ffffff", 0.25)), ("1", _mix(color, "#000000", 0.35))])
    c.add(f'<circle cx="600" cy="400" r="330" fill="{c.glow(color)}"/>')
    c.add(
        f'<path d="M600 640 C360 480 300 360 360 280 C420 200 540 220 600 320 '
        f'C660 220 780 200 840 280 C900 360 840 480 600 640 Z" fill="{fill}"/>'
    )


def _flower(c, color):
    c.add(f'<path d="M600 470 C590 560 610 650 600 800" stroke="#1f7a3a" stroke-width="16" fill="none"/>')
    c.add('<ellipse cx="660" cy="640" rx="60" ry="22" fill="#2ecc71" transform="rotate(-30 660 640)"/>')
    for k in range(8):
        a = k * math.pi / 4
        x, y = 600 + math.cos(a) * 95, 380 + math.sin(a) * 95
        c.add(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="85" ry="48" fill="{color}" opacity="0.92" '
              f'transform="rotate({math.degrees(a):.0f} {x:.0f} {y:.0f})"/>')
    c.add('<circle cx="600" cy="380" r="58" fill="#ffd200"/>')


def _abstract(c, palette):
    r = c.rnd
    for _ in range(26):
        kind = r.random()
        col = r.choice(palette)
        op = r.uniform(0.25, 0.85)
        if kind < 0.4:
            c.add(f'<circle cx="{r.uniform(0, W):.0f}" cy="{r.uniform(0, H):.0f}" r="{r.uniform(30, 220):.0f}" fill="{col}" opacity="{op:.2f}"/>')
        elif kind < 0.7:
            x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(60, 300)
            c.add(f'<rect x="{x:.0f}" y="{y:.0f}" width="{s:.0f}" height="{s * r.uniform(0.3, 1):.0f}" fill="{col}" '
                  f'opacity="{op:.2f}" transform="rotate({r.uniform(0, 90):.0f} {x:.0f} {y:.0f})"/>')
        else:
            c.add(f'<line x1="{r.uniform(0, W):.0f}" y1="{r.uniform(0, H):.0f}" x2="{r.uniform(0, W):.0f}" '
                  f'y2="{r.uniform(0, H):.0f}" stroke="{col}" stroke-width="{r.uniform(2, 14):.0f}" opacity="{op:.2f}"/>')


def _logo(c, name, accent):
    accent = accent or "#e10600"
    c.add(f'<rect width="{W}" height="{H}" fill="#0a0a0a"/>')
    c.add(f'<circle cx="600" cy="300" r="230" fill="{c.glow(accent)}"/>')
    c.add(f'<polygon points="600,150 730,375 470,375" fill="none" stroke="{accent}" stroke-width="18"/>')
    c.add(f'<circle cx="600" cy="300" r="36" fill="{accent}"/>')
    text = escape(name.upper()[:18] or "RTEAM")
    size = 120 if len(text) <= 8 else max(56, int(960 / len(text)))
    c.add(f'<text x="600" y="590" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" '
          f'font-weight="900" font-size="{size}" fill="#f4f4f4" letter-spacing="6">{text}</text>')
    c.add(f'<rect x="480" y="630" width="240" height="8" fill="{accent}"/>')


# ------------------------------------------------------------------ картинка

def make_image(prompt: str, seed=None, theme=None) -> dict:
    """Нарисовать SVG по описанию. Возвращает {"type": "image", "svg", "title", "prompt"}.

    theme — цвета презентации ({"bg", "accent", "accent2", "fg"}): картинка рисуется в них.
    """
    words = _words(prompt)
    rnd = random.Random(seed)
    c = _Canvas(rnd)
    found = [name for name, prefixes in SCENES if _has(words, prefixes)]
    accent = (theme or {}).get("accent") or next((col for p, col in COLORS.items() if _has(words, (p,))), None)
    if theme:
        a, a2, bg = theme["accent"], theme.get("accent2") or theme["accent"], theme["bg"]
        palette = [a, a2, _mix(a, "#ffffff", 0.35), _mix(a, "#000000", 0.45), _mix(bg, a, 0.25)]
    else:
        palette = [accent] if accent else []
        palette += ["#e10600", "#ff2a2a", "#7a0000", "#f2f2f2", "#1a1a1a"]

    if "logo" in found:
        m = re.search(r"(?:логотип\w*|лого|эмблем\w*|значок)\s+(?:для\s+|компании\s+|команды\s+)?(.+)", prompt, re.I)
        name = (m.group(1) if m else "Rteam").strip(" .!?«»\"'")
        _logo(c, name, accent)
        return {"type": "image", "svg": c.svg("Логотип " + name), "title": f"Логотип «{name}»", "prompt": prompt}

    if not found or found == ["abstract"]:
        if theme:
            c.add(f'<rect width="{W}" height="{H}" fill="{c.gradient([("0", theme["bg"]), ("1", _mix(theme["bg"], theme["accent"], 0.22))])}"/>')
        else:
            _sky(c, "dark", None)
        _abstract(c, palette)
        # Есть сюжет, которого нет среди сцен (например «кот»)?
        rest = [w for w in words if len(w) > 2 and not _IMAGE_WORDS.search(w)
                and w not in ("что", "нибудь", "пожалуйста", "мне", "какую", "любую", "красивую", "сделай", "создай")
                and not any(w.startswith(p) for p in COLORS)]
        return {"type": "image", "svg": c.svg("Абстракция"), "title": "Абстракция", "prompt": prompt,
                "unknown": bool(rest) and not found}

    sky = next((s for s in ("space", "night", "sunset", "sunrise", "winter", "desert") if s in found), "day")
    _sky(c, sky, accent)
    if sky in ("space", "night"):
        _stars(c, 260 if sky == "space" else 160, top=H if sky == "space" else 520)
    if sky == "space":
        for _ in range(3):
            x, y, r = rnd.uniform(150, 1050), rnd.uniform(120, 650), rnd.uniform(30, 110)
            col = rnd.choice(palette)
            c.add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{c.gradient([("0", _mix(col, "#ffffff", 0.3)), ("1", _mix(col, "#000000", 0.6))], vertical=False)}"/>')
        c.add(f'<ellipse cx="600" cy="400" rx="520" ry="120" fill="{c.glow(accent or "#b3143a")}" transform="rotate(-18 600 400)"/>')

    sun_x = rnd.choice([380, 600, 820])
    sun_color = {"sunset": "#ffb347", "sunrise": "#fff1a8", "desert": "#fff3c4", "day": "#fff6c9"}.get(sky)
    if sky == "night":
        _moon(c, rnd.choice([250, 950]), 170, 60)
    elif sun_color and sky not in ("space", "winter"):
        _sun(c, sun_x, 400 if sky in ("sunset", "sunrise") else 180, 70, sun_color)

    base_col = accent or {"sunset": "#3a0d24", "sunrise": "#4a3a6a", "night": "#0b1026",
                          "winter": "#9fb6cf", "desert": "#b35d2a"}.get(sky, "#2f5d50")
    if "mountains" in found:
        _mountains(c, [_mix(base_col, "#000000", t) for t in (0.1, 0.35, 0.6)], "winter" in found)
    if "desert" in found:
        _dunes(c)
    if "city" in found:
        _city(c, 640 if "sea" in found else 700, sky in ("night", "sunset", "space"), accent)
    if "sea" in found:
        _sea(c, 560, accent or ("#12213f" if sky == "night" else "#1d5f8a" if sky == "day" else "#3a1030"),
             sun_x if sun_color and sky in ("sunset", "sunrise", "day") else None, sun_color)
    if "forest" in found:
        _forest(c, 660, accent or ("#0f3d2a" if sky != "winter" else "#1f4d3a"), snow="winter" in found)
    if "heart" in found:
        _heart(c, accent or "#e10600")
    if "flower" in found:
        _flower(c, accent or "#ff2a2a")
    if "abstract" in found:
        _abstract(c, palette)
    if "winter" in found:
        if not {"mountains", "forest"} & set(found):
            c.add(f'<path d="M0 640 C300 600 700 690 {W} 620 L{W} {H} L0 {H} Z" fill="#f4f8ff"/>')
        _snowfall(c)

    names = {"space": "космос", "night": "ночь", "sunset": "закат", "sunrise": "рассвет", "winter": "зима",
             "desert": "пустыня", "city": "город", "sea": "море", "mountains": "горы", "forest": "лес",
             "heart": "сердце", "flower": "цветок", "abstract": "абстракция"}
    title = ", ".join(names[f] for f in found if f in names).capitalize()
    return {"type": "image", "svg": c.svg(title), "title": title, "prompt": prompt}


# ------------------------------------------------------------------ презентация

_SLIDES_WORDS = re.compile(r"презентаци|слайд", re.I)
_SLIDES_FILLER = re.compile(
    r"\b(пожалуйста|сделай|создай|подготовь|сгенерируй|собери|напиши|нужна|нужно|мне|презентаци\w*|"
    r"слайд\w*|на|тему|теме|про|о|об|по|для|короткую|большую|подробную)\b",
    re.I,
)


_WANT = [
    ("table", r"таблиц\w*"),
    ("quote", r"цитат\w*|высказывани\w*"),
    ("timeline", r"хронолог\w*|по годам|даты|датами|лента времени|таймлайн\w*"),
    ("stats", r"цифр\w*|статистик\w*|числа|числами"),
    ("code", r"пример\w* кода|с кодом|код\w* пример\w*"),
    ("summary", r"вывод\w*|итог\w*"),
]
_NO_PICS = re.compile(r"\bбез (?:картин\w*|фото\w*|изображени\w*|иллюстраци\w*)", re.I)
_PHOTOS = re.compile(r"\b(?:фото\w*|картин\w*|изображени\w*|иллюстраци\w*)", re.I)
_COUNT = re.compile(r"(?:\bна|\bиз|\bв)?\s*(\d{1,2})\s*(?:-?ти|-?и|-?х)?\s*слайд\w*", re.I)
_COMPARE = re.compile(r"сравн\w*\s+([а-яёa-z0-9 -]{2,40}?)\s+(?:и|с|со|vs)\s+([а-яёa-z0-9 -]{2,40}?)(?=[,.;!?]|\s+(?:и|в|на|с|со|для)\s|$)", re.I)
_SECTIONS = re.compile(
    r"(?:раздел\w*|включи\w*|добавь\w*|расскажи\w*|обязательно|пункт\w*|план\w*|темы|части|где будет|чтобы было)"
    r"\s*(?:про|о|об|:|—|-)?\s*(?:про|о|об)?\s*([^.;!?]{3,200})", re.I)
_SECTION_JUNK = re.compile(r"^(?:и|а|также|ещё|еще|про|о|об|с|со)\s+", re.I)


def parse_deck_request(text: str) -> dict:
    """Что просят в презентации: тему, число слайдов, разделы, таблицу/цитату/хронологию/цифры/сравнение, фото.

    Возвращает {"topic", "count", "sections", "want", "compare", "pictures", "rest"}; rest — текст без этих указаний
    (из него берутся тема и цвета).
    """
    raw = text or ""
    rest = raw
    count = None
    m = _COUNT.search(rest)
    if m:
        count = max(3, min(20, int(m.group(1))))
        rest = rest[:m.start()] + " " + rest[m.end():]
    compare = None
    m = _COMPARE.search(rest)
    if m:
        compare = [m.group(1).strip(), m.group(2).strip()]
        rest = rest[:m.start()] + " " + rest[m.end():]
    sections = []
    m = _SECTIONS.search(rest)
    if m:
        body = m.group(1)
        parts = [p for p in re.split(r"\s*(?:,|;|\s+и\s+|\s+а также\s+)\s*", body) if p.strip()]
        for p in parts:
            p = _SECTION_JUNK.sub("", p.strip(" .:-—")).strip()
            if p and not any(re.fullmatch(rx, p, re.I) for _, rx in _WANT) and not _PHOTOS.fullmatch(p):
                sections.append(p[:60])
        rest = rest[:m.start()] + " " + rest[m.end():]
    want = set()
    for kind, rx in _WANT:
        if re.search(r"\b(?:" + rx + r")", raw, re.I):
            want.add(kind)
            rest = re.sub(r"(?:\bс\s+|\bи\s+)?\b(?:" + rx + r")", " ", rest, flags=re.I)
    if compare:
        want.add("compare")
    pictures = "none" if _NO_PICS.search(raw) else "photo"
    rest = _NO_PICS.sub(" ", rest)
    rest = re.sub(r"(?:\bс\s+|\bи\s+)?\b(?:фото\w*|картин\w*|изображени\w*|иллюстраци\w*)(?:\s+из\s+интернета)?", " ", rest, flags=re.I)
    rest = re.sub(r"\s+(?:и|с|со)\s*(?=[,.!?]|$)", " ", rest)
    rest = re.sub(r"\s{2,}", " ", rest).strip(" ,.")
    return {"topic": slides_topic(rest), "count": count, "sections": sections[:8], "want": want,
            "compare": compare, "pictures": pictures, "rest": rest}


def is_slides_request(text: str) -> bool:
    return bool(_SLIDES_WORDS.search(text or "")) and not _QUESTION.search(text or "")


# Цвета для презентаций: начало слова -> цвет. Длинные варианты раньше коротких.
DECK_COLORS = [
    ("темно-син", "#0b1f4d"), ("темно-зелен", "#0f3d2e"), ("темно-красн", "#7a0a16"), ("светло-син", "#93c5fd"),
    ("светло-зелен", "#86efac"), ("черн", "#0b0b0c"), ("графит", "#1f2937"), ("бел", "#ffffff"),
    ("красн", "#e10600"), ("алый", "#ff2a2a"), ("бордов", "#7a0a16"), ("малинов", "#be185d"),
    ("розов", "#ec4899"), ("персик", "#fdba74"), ("оранж", "#f97316"), ("желт", "#facc15"),
    ("золот", "#d4af37"), ("бежев", "#e8d9c0"), ("коричн", "#7c4a2d"), ("салатов", "#84cc16"),
    ("мятн", "#34d399"), ("изумруд", "#10b981"), ("зелен", "#16a34a"), ("бирюз", "#14b8a6"),
    ("голуб", "#38bdf8"), ("син", "#1e5bff"), ("индиго", "#4f46e5"), ("фиолет", "#7c3aed"),
    ("лаванд", "#a78bfa"), ("сирен", "#a855f7"), ("серебр", "#c0c0c0"), ("сер", "#6b7280"),
    ("неон", "#39ff14"),
]
_STYLE_WORDS = ("тонах", "тона", "тон", "цветах", "цвете", "цвета", "цвет", "цветом", "стиле", "стиль", "фоне", "фон",
                "фоном", "акцент", "акцентом", "акцентами", "палитре", "палитра", "гамме", "оттенках", "оттенки",
                "цветами", "светлая", "светлой", "светлом", "темная", "темной", "темном")


def _color_of(word):
    w = word.lower().replace("ё", "е")
    if re.fullmatch(r"#(?:[0-9a-f]{6}|[0-9a-f]{3})", w):
        return "#" + "".join(ch * 2 for ch in w[1:]) if len(w) == 4 else w
    for prefix, hex_ in DECK_COLORS:
        if w.startswith(prefix) and not w.startswith("серд") and not w.startswith("серв") and not w.startswith("сери"):
            return hex_
    return None


def _lum(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def slides_topic(text: str) -> str:
    """Тема презентации без служебных слов и без цветов («про космос в синих тонах» -> «космос»)."""
    words = re.findall(r"#[0-9a-fA-F]{3,6}|[\w-]+|[«»\"',.:;!?]", text or "")
    drop = [False] * len(words)
    for i, w in enumerate(words):
        low = w.lower().replace("ё", "е")
        parts = low.split("-")
        if _color_of(low) or all(_color_of(p) for p in parts if p) and len(parts) > 1 or low in _STYLE_WORDS:
            drop[i] = True
    for i, w in enumerate(words):  # «в», «на», «с», «и» рядом с цветами тоже убираем
        if w.lower() in ("в", "на", "с", "и", ",", "а") and (
                (i + 1 < len(words) and drop[i + 1]) or (i > 0 and drop[i - 1] and i + 1 < len(words) and drop[i + 1])):
            drop[i] = True
    kept = " ".join(w for w, d in zip(words, drop) if not d)
    topic = _SLIDES_FILLER.sub(" ", kept)
    topic = re.sub(r"\s+([,.:;!?»])", r"\1", topic)
    return re.sub(r"\s+", " ", topic).strip(" .,!?:;«»\"'-")


_NOT_ACCUSATIVE = {"кенгуру", "рагу", "баку", "шоу", "какаду", "перу", "гну", "табу", "кунг-фу", "фу", "ушу", "суши"}


def nominative(topic: str) -> str:
    """Тема после «про» — в именительный падеж для заголовка: «историю древнего рима» -> «история древнего рима».

    Меняем только начальные прилагательные и первое существительное женского рода (винительный -у/-ю),
    остальное (родительный падеж и т. п.) оставляем как есть.
    """
    words = (topic or "").split(" ")
    for i, w in enumerate(words):
        low = w.lower()
        if not re.fullmatch(r"[а-яё-]{3,}", low) or low in _NOT_ACCUSATIVE:
            break
        if low.endswith(("ую", "юю")):  # новую -> новая, древнюю -> древняя
            words[i] = w[:-2] + ("ая" if low.endswith("ую") else "яя")
            continue
        if low.endswith("ию"):  # историю -> история
            words[i] = w[:-1] + "я"
        elif re.search(r"[бвгджзклмнпрстфхцчшщ]у$", low):  # экономику -> экономика
            words[i] = w[:-1] + "а"
        break
    return " ".join(words)


def deck_theme(text: str) -> dict:
    """Цвета презентации из слов пользователя: «в синих тонах», «чёрно-золотая», «фон белый, акцент фиолетовый»."""
    low = (text or "").lower().replace("ё", "е")
    tokens = re.findall(r"#[0-9a-f]{3,6}|[a-zа-я]+(?:-[a-zа-я]+)*", low)
    colors = []  # (цвет, это фон?)
    for i, tok in enumerate(tokens):
        # «тёмно-синий» — один цвет, «чёрно-золотой» — два цвета
        found = [_color_of(tok)] if _color_of(tok) and tok.startswith(("темно-", "светло-")) else \
            [_color_of(p) for p in tok.split("-")] if "-" in tok else [_color_of(tok)]
        near = tokens[max(0, i - 2):i] + tokens[i + 1:i + 2]
        for col in found:
            if col:
                colors.append((col, any(t.startswith("фон") for t in near)))
    bg = next((c for c, is_bg in colors if is_bg), None)
    rest = [c for c, is_bg in colors if not is_bg and c != bg]
    if not bg:
        extreme = [c for c in rest if _lum(c) < 0.12 or _lum(c) > 0.85]
        if extreme and (len(rest) > 1 or not re.search(r"акцент", low)):
            bg = extreme[0]
            rest.remove(bg)
    if not bg:
        bg = "#ffffff" if re.search(r"светл|бел", low) else "#0b0b0c"
    accent = rest[0] if rest else ("#e10600" if _lum(bg) > 0.5 else "#ff2a2a")
    accent2 = rest[1] if len(rest) > 1 else _mix(accent, "#ffffff" if _lum(bg) < 0.5 else "#000000", 0.35)
    dark = _lum(bg) < 0.5
    fg = "#f5f3f3" if dark else "#141414"
    # акцент должен читаться на фоне: слишком близкий цвет чуть сдвигаем
    if abs(_lum(accent) - _lum(bg)) < 0.18:
        accent = _mix(accent, "#ffffff" if dark else "#000000", 0.45)
    return {"bg": bg, "fg": fg, "accent": accent, "accent2": accent2,
            "muted": _mix(fg, bg, 0.42), "surface": _mix(bg, fg, 0.07), "line": _mix(bg, fg, 0.16),
            "on_accent": "#111111" if _lum(accent) > 0.6 else "#ffffff", "custom": bool(colors)}


def _split_segments(text):
    """Разбить markdown-текст на блоки: ("code", lang, код) / ("table", строки) / ("text", строки)."""
    segs, buf, lines = [], [], text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            if buf:
                segs.append(("text", buf)); buf = []
            lang = line.strip()[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            segs.append(("code", lang, "\n".join(code)))
        elif line.strip().startswith("|"):
            if buf:
                segs.append(("text", buf)); buf = []
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            segs.append(("table", rows))
            continue
        else:
            buf.append(line)
        i += 1
    if buf:
        segs.append(("text", buf))
    return segs


def _bullets(lines):
    items = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^(?:[•\-*]\s+|\d+[.)]\s*)", "", s)
        s = s.replace("**", "")
        if s.startswith("#"):
            s = s.lstrip("# ")
        if len(s) > 160:
            items += [p.strip() + ("" if p.strip().endswith((".", "!", "?")) else ".")
                      for p in re.split(r"(?<=[.!?])\s+", s) if p.strip()]
        else:
            items.append(s)
    return items


def _table(rows):
    cells = []
    for row in rows:
        parts = [p.strip() for p in row.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", p) for p in parts if p):
            continue
        cells.append(parts)
    return cells


def _sentences(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ0-9«\"(])", text) if len(p.strip()) > 2]


def _short(text, limit=110):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:—- ") + "…"


_YEAR = re.compile(r"(?<![\d.,])((?:1[0-9]|20)[0-9]{2})(?:\s*(?:[-–—]\s*(?:(?:1[0-9]|20)[0-9]{2})|г\.|гг\.|год[ауе]?|годах?|х))?(?![\d%])", re.I)
_UNIT = r"(?:%|процент\w*|млн|млрд|трлн|тыс\.?|км/ч|км|кг|м|°C|°|ГБ|МБ|ТБ|раз\w*|×|x|₽|\$|€|руб\.?|лет|ч|мин|сек|мс)"
_NUMBER = re.compile(r"(?<![\w.,])(~|≈|более |около |до |свыше )?(\d(?:[\d\s ]*\d)?(?:[.,]\d+)?)\s?(" + _UNIT + r")?(?![\w])", re.I)


def _as_timeline(items):
    """Пункты с годами → события хронологии [{date, text}] (или None)."""
    if not 3 <= len(items) <= 6:
        return None
    out = []
    for it in items:
        plain = it.replace("**", "")
        m = _YEAR.search(plain)
        if not m or m.start() > 40:
            return None
        text = (plain[:m.start()] + plain[m.end():]).strip()
        text = re.sub(r"^(?:[Вв]о?|[Сс]|[Кк])\s+(?=[,—–:-]|\s|$)", "", text)
        text = re.sub(r"^[\s,—–:.-]+", "", text).strip()
        if len(text) < 3:
            return None
        date = re.sub(r"\s*(?:г\.|гг\.|год\w*|х)$", "", plain[m.start():m.end()].strip(), flags=re.I)
        out.append({"date": date, "text": _short(text[:1].upper() + text[1:], 90)})
    return out


def _as_stats(items):
    """Пункты с крупными числами → «цифры» [{value, label}] (или None)."""
    if not 3 <= len(items) <= 4:
        return None
    out = []
    for it in items:
        plain = it.replace("**", "")
        m = next((m for m in _NUMBER.finditer(plain)
                  if m.group(3) or float(m.group(2).replace(" ", "").replace(" ", "").replace(",", ".")) >= 10), None)
        if not m or _YEAR.fullmatch(m.group(0).strip()) and not m.group(3):
            return None
        pre = (m.group(1) or "").strip().lower()
        value = m.group(2).strip() + ("" if not m.group(3) else ("" if m.group(3) in "%×" else " ") + m.group(3))
        value = ("≈ " + value) if pre in ("~", "≈", "около") else ("до " + value) if pre == "до" else (value + "+") if pre else value
        if len(value) > 14:
            return None
        out.append({"value": value, "label": _short(plain.rstrip("."), 90)})
    return out


def web_blocks(title, text, first=False):
    """Раздел статьи из интернета (сплошной текст) → блоки слайдов: факт, пункты, хронология, цифры."""
    text = re.sub(r"\[\d+\]|\[источник не указан[^\]]*\]", "", text or "")
    sents = [x for x in _sentences(text) if 25 <= len(x) <= 260 and not x.endswith(":")]
    blocks = []
    if not sents:
        return blocks
    used = set()
    dated = [x for x in sents if _YEAR.search(x) and _YEAR.search(x).start() < 60]
    if len(dated) >= 3:
        items = _as_timeline(dated[:6])
        if items:
            items.sort(key=lambda it: int(re.match(r"\d{4}", it["date"]).group()) if re.match(r"\d{4}", it["date"]) else 0)
            blocks.append({"kind": "timeline", "title": title, "items": items})
            used.update(dated[:6])
    numeric = [x for x in sents if x not in used and _as_stats([x, x, x])]
    if len(numeric) >= 3:
        items = _as_stats(numeric[:3] if len(numeric) < 4 else numeric[:4])
        if items:
            blocks.append({"kind": "stats", "title": title, "items": items})
            used.update(numeric[:4])
    rest = [x for x in sents if x not in used]
    if first and rest and len(rest[0]) >= 40:
        blocks.insert(0, {"kind": "fact", "title": title, "text": _short(rest[0], 260)})
        rest = rest[1:]
    if len(rest) >= 2:
        blocks.append({"kind": "bullets", "title": title, "bullets": [_short(x, 170) for x in rest[:4]]})
    elif rest and not blocks:
        blocks.append({"kind": "fact", "title": title, "text": _short(rest[0], 260)})
    return blocks


def extra_blocks(want, material, quote=None, compare=None):
    """Слайды, которые попросили отдельно: таблица, цитата, сравнение, хронология, цифры.

    material — все уже собранные блоки (из них строится таблица). Возвращает (блоки, чего не нашлось).
    """
    out, missing = [], []
    kinds = {b["kind"] for b in material}
    if "compare" in want:
        if compare:
            out.append(compare)
        else:
            missing.append("сравнение")
    if "quote" in want:
        if quote:
            out.append({"kind": "quote", "title": "", "text": quote["text"], "author": quote.get("author", "")})
        else:
            missing.append("цитату")
    for kind, name in (("timeline", "хронологию"), ("stats", "цифры")):
        if kind in want and kind not in kinds:
            missing.append(name)
    if "table" in want:
        src = next((b for b in material if b["kind"] in ("timeline", "stats")), None)
        if src and src["kind"] == "timeline":
            rows = [["Год", "Событие"]] + [[x["date"], x["text"]] for x in src["items"]]
        elif src:
            rows = [["Показатель", "Значение"]] + [[x["label"], x["value"]] for x in src["items"]]
        else:
            heads = [(b["title"], b.get("text") or (b.get("bullets") or [""])[0]) for b in material if b["kind"] in ("fact", "bullets")]
            seen, rows = set(), [["Раздел", "Коротко"]]
            for t, line in heads:
                if t not in seen and line:
                    seen.add(t)
                    rows.append([t, _short(line.rstrip("."), 90)])
            rows = rows[:7]
        if len(rows) > 2:
            out.append({"kind": "table", "title": (src or {}).get("title") or "Коротко о главном", "rows": rows})
        else:
            missing.append("таблицу")
    return out, missing


def _article_blocks(article):
    """Разобрать статью на блоки для слайдов: факт, пункты, код, таблицы."""
    text = article["answers"][0].replace("{name}", "")
    if article.get("more"):
        text += "\n\n" + article["more"]
    # Фразы Rai о себе («Я работаю на нём») на слайдах лишние
    text = re.sub(r"(?:(?<=[.!?])|^)\s*(?:[А-ЯЁ][а-яё]+,\s+)?(?:[Яя]|[Мм]еня|[Мм]не|[Мм]огу)\s[^.!?\n]*[.!?]", "", text, flags=re.M)
    heading = article.get("title") or "Главное"
    blocks = []
    first = True
    for seg in _split_segments(text):
        if seg[0] == "code" and seg[2].strip():
            blocks.append({"kind": "code", "title": heading + ": пример", "lang": seg[1], "code": seg[2]})
        elif seg[0] == "table":
            cells = _table(seg[1])
            if len(cells) > 1:
                blocks.append({"kind": "table", "title": heading, "rows": cells[:8]})
        else:
            items = [b for b in _bullets(seg[1]) if not (b.endswith(":") and len(b) < 40)
                     and b.strip(" .").lower() != heading.lower()]
            if first and items and 25 <= len(items[0]) <= 200 and not items[0].startswith("|"):
                blocks.append({"kind": "fact", "title": heading, "text": items[0]})
                items = items[1:]
            first = False
            timeline = _as_timeline(items) if len(items) <= 6 else None
            if timeline:
                blocks.append({"kind": "timeline", "title": heading, "items": timeline})
                continue
            if len(items) == 1:  # один пункт — это факт, а не список
                prev = blocks[-1] if blocks else None
                if prev and prev["kind"] == "fact" and len(prev["text"]) + len(items[0]) <= 260:
                    prev["text"] += " " + items[0]
                elif 25 <= len(items[0]) <= 220:
                    blocks.append({"kind": "fact", "title": heading, "text": items[0]})
                continue
            size = math.ceil(len(items) / math.ceil(len(items) / 4)) if items else 4  # 5 -> 3+2, а не 4+1
            for k in range(0, len(items), size):
                chunk = items[k:k + size]
                stats = _as_stats(chunk)
                if stats:
                    blocks.append({"kind": "stats", "title": heading, "items": stats})
                else:
                    blocks.append({"kind": "bullets", "title": heading, "bullets": chunk})
    for b in blocks:  # статьи словаря начинаются с маленькой буквы («пространство за пределами…»)
        if b.get("text"):
            b["text"] = _cap(b["text"])
        if b.get("bullets"):
            b["bullets"] = [_cap(x) for x in b["bullets"]]
    return blocks


def _cap(text):
    return text[:1].upper() + text[1:] if text[:1].islower() else text


def _spread(slides):
    """Не ставить подряд однотипные слайды с кодом, таблицами, цифрами: чередуем с остальными."""
    out = list(slides)
    for i in range(1, len(out)):
        if out[i]["kind"] == out[i - 1]["kind"] and out[i]["kind"] in ("code", "table", "stats", "timeline", "fact"):
            j = next((j for j in range(i + 1, len(out)) if out[j]["kind"] != out[i]["kind"]), None)
            if j is not None:
                out.insert(i, out.pop(j))
    return out


def make_slides(topic: str, articles: list, max_slides: int = 8, theme=None, photo=None, extras=None, photos=None,
                pictures="photo") -> dict:
    """Собрать презентацию: обложка, план, факты, пункты с картинками, код, таблицы, итоги, финал.

    articles — статьи ({"title", "answers": [текст], "more"?}) из базы знаний, словаря или интернета.
    theme — цвета (см. deck_theme). photo — адрес настоящей фотографии по теме (например, из Википедии).
    Возвращает None, если материала нет: пустых «шаблонов для заполнения» Rai не делает.
    """
    if not articles:
        return None
    theme = theme or deck_theme("")
    title = topic[:1].upper() + topic[1:] if topic else articles[0].get("title", "Презентация")
    lead = next((s for a in articles for s in _sentences(a["answers"][0].replace("{name}", "").replace("**", ""))
                 if 20 <= len(s) <= 160 and not s.startswith(("|", "`", "#"))), "")
    slides = [{"kind": "title", "title": title, "subtitle": _short(lead, 120)}]

    blocks_per_article = [a["blocks"] if a.get("blocks") is not None else _article_blocks(a) for a in articles]
    headings = list(dict.fromkeys(a.get("title") for a, b in zip(articles, blocks_per_article) if b and a.get("title")))
    if len(headings) >= 3:
        slides.append({"kind": "agenda", "title": "План", "items": headings[:6]})
    if photo:
        slides.append({"kind": "photo", "title": title, "photo": photo, "caption": _short(lead, 140)})

    # Берём блоки по очереди из каждой статьи, чтобы презентация не застревала на одной теме
    extras = list(extras or [])
    budget = max_slides - len(slides) - 2 - len(extras)  # оставляем место на итоги, финал и заказанные слайды
    queues = [list(b) for b in blocks_per_article]
    while budget > 0 and any(queues):
        for q in queues:
            if q and budget > 0:
                slides.append(q.pop(0))
                budget -= 1

    head = sum(1 for x in slides if x["kind"] in ("title", "agenda", "photo"))
    body = _spread(slides[head:])
    for n, extra in enumerate(extras):  # заказанные слайды — равномерно по презентации
        body.insert(min(len(body), (n + 1) * max(1, len(body)) // (len(extras) + 1) + n), extra)
    slides = slides[:head] + body
    agenda = next((x for x in slides if x["kind"] == "agenda"), None)
    if agenda:  # в плане — только то, что действительно есть на слайдах
        titles = list(dict.fromkeys(re.sub(r": пример$", "", x["title"]) for x in body
                                    if x.get("title") and x["kind"] not in ("quote", "summary", "end")))
        if len(titles) >= 3:
            agenda["items"] = titles[:6]
        else:
            slides.remove(agenda)

    takeaways = []
    for blocks in blocks_per_article:
        for b in blocks:
            line = b.get("text") or (b.get("bullets") or [None])[0]
            if line:
                takeaways.append(_cap(_short(line.rstrip("."), 90)))
                break
    if len(takeaways) >= 2:
        slides.append({"kind": "summary", "title": "Главное", "items": takeaways[:4]})
    slides.append({"kind": "end", "title": "Спасибо за внимание!", "subtitle": title})
    if pictures == "none":
        slides = [s for s in slides if s["kind"] != "photo"]
        for k, s in enumerate(slides):
            s["transition"] = TRANSITIONS[k % len(TRANSITIONS)]
    else:
        _decorate(slides, topic or title, theme)
        _add_photos(slides, photos or [], photo)
    return {"type": "slides", "title": title, "slides": slides, "theme": theme}


TRANSITIONS = ["fade", "slide", "zoom", "wipe", "rise"]


def _add_photos(slides, photos, main=None):
    """Настоящие фотографии из интернета: обложка, пункты, факты, цитата, финал (рисунок остаётся запасным)."""
    queue = [p["url"] if isinstance(p, dict) else p for p in photos]
    queue = [u for u in dict.fromkeys(queue) if isinstance(u, str) and u.startswith("https://")]
    if main and main in queue:
        queue.remove(main)
    cover = main or (queue.pop(0) if queue else None)
    if cover:
        slides[0]["pic"] = cover
    for s in slides[1:]:
        if not queue:
            break
        if s["kind"] in ("bullets", "fact", "quote") and s.get("image") or s["kind"] == "quote":
            s["pic"] = queue.pop(0)
    if queue and slides[-1]["kind"] == "end":
        slides[-1]["pic"] = queue.pop(0)
    elif cover and slides[-1]["kind"] == "end":
        slides[-1]["pic"] = cover


def _decorate(slides, topic, theme):
    """Картинки в цветах темы, чередование сторон, переходы между слайдами."""
    seed = zlib.crc32(topic.encode("utf-8"))
    slides[0]["image"] = make_image(topic, seed=seed, theme=theme)["svg"]
    side = 0
    for k, slide in enumerate(slides):
        slide["transition"] = TRANSITIONS[k % len(TRANSITIONS)]
        if slide["kind"] == "bullets" and len(slide["bullets"]) <= 4 and side < 6:
            slide["image"] = make_image(f"{topic} {slide['title']}", seed=seed + k, theme=theme)["svg"]
            slide["side"] = "left" if side % 2 else "right"
            side += 1
        if slide["kind"] in ("fact", "end"):
            slide["image"] = make_image(topic, seed=seed + 100 + k, theme=theme)["svg"]


# ------------------------------------------------------------------ погода

def _cloud(c, x, y, s, color, opacity=1.0):
    c.add(f'<g opacity="{opacity:.2f}" fill="{color}">'
          f'<ellipse cx="{x}" cy="{y}" rx="{95 * s:.0f}" ry="{42 * s:.0f}"/>'
          f'<circle cx="{x - 45 * s:.0f}" cy="{y - 18 * s:.0f}" r="{42 * s:.0f}"/>'
          f'<circle cx="{x + 20 * s:.0f}" cy="{y - 38 * s:.0f}" r="{55 * s:.0f}"/>'
          f'<circle cx="{x + 70 * s:.0f}" cy="{y - 10 * s:.0f}" r="{36 * s:.0f}"/></g>')


def weather_card(city: str, temp: str, desc: str, kind: str, is_day: bool, extra: str = "") -> dict:
    """Картинка погоды: небо, солнце/луна, облака, дождь, снег, гроза, туман + температура."""
    rnd = random.Random(f"{city}{desc}{is_day}")
    c = _Canvas(rnd)
    if kind in ("rain", "storm"):
        sky = [("0", "#1b2230"), ("1", "#3b4658")] if kind == "rain" else [("0", "#120c1c"), ("1", "#2c2340")]
    elif kind == "snow":
        sky = [("0", "#7f93ab"), ("1", "#d9e4f0")] if is_day else [("0", "#1a2233"), ("1", "#3a4a63")]
    elif kind in ("cloudy", "fog"):
        sky = [("0", "#5b6573"), ("1", "#aab3bf")] if is_day else [("0", "#15181f"), ("1", "#2c323d")]
    else:
        sky = [("0", "#1f6fd1"), ("1", "#9fd3ff")] if is_day else [("0", "#03040c"), ("1", "#1a2150")]
    c.add(f'<rect width="{W}" height="{H}" fill="{c.gradient(sky)}"/>')

    if not is_day and kind in ("clear", "partly"):
        _stars(c, 120, top=H)
    if kind in ("clear", "partly"):
        if is_day:
            _sun(c, 860, 250, 95, "#ffd54a")
        else:
            _moon(c, 860, 240, 80)
    if kind in ("partly", "cloudy", "rain", "storm", "snow", "fog"):
        shade = "#f2f4f7" if kind in ("partly",) or (kind == "snow" and is_day) else "#7d8796" if kind == "cloudy" else "#4a5262"
        clouds = 2 if kind == "partly" else 4
        for k in range(clouds):
            _cloud(c, 620 + k * 150 - (clouds - 2) * 60, 230 + (k % 2) * 60, 1.4 - k * 0.1, shade, 0.95)
    if kind in ("rain", "storm"):
        c.add("".join(
            f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x - 14:.0f}" y2="{y + 38:.0f}" stroke="#9cc8ff" stroke-width="3" '
            f'stroke-linecap="round" opacity="0.8"/>'
            for x, y in ((rnd.uniform(420, 1150), rnd.uniform(320, 760)) for _ in range(70))))
    if kind == "storm":
        c.add('<polygon points="840,300 780,450 830,450 790,590 900,410 845,410 890,300" fill="#ffe14a"/>')
    if kind == "snow":
        _snowfall(c)
    if kind == "fog":
        for k in range(7):
            y = 330 + k * 60
            c.add(f'<rect x="{rnd.uniform(-100, 300):.0f}" y="{y}" width="{rnd.uniform(700, 1100):.0f}" height="22" '
                  f'rx="11" fill="#ffffff" opacity="0.35"/>')

    # панель с текстом в стиле Rai
    c.add('<rect x="40" y="40" width="560" height="720" rx="28" fill="#0b0b0c" opacity="0.78"/>')
    c.add('<rect x="40" y="740" width="560" height="20" rx="0" fill="#e10600"/>')
    c.add(f'<text x="80" y="130" font-family="Arial, sans-serif" font-size="44" font-weight="700" fill="#f3f1f1">{escape(city[:22])}</text>')
    c.add(f'<text x="72" y="400" font-family="Arial Black, Arial, sans-serif" font-size="210" font-weight="900" fill="#ffffff">{escape(temp)}</text>')
    c.add(f'<text x="80" y="490" font-family="Arial, sans-serif" font-size="46" fill="#ff4a4a">{escape(desc[:26])}</text>')
    c.add(f'<text x="80" y="560" font-family="Arial, sans-serif" font-size="34" fill="#c9c3c7">{escape(extra[:34])}</text>')
    c.add('<text x="80" y="700" font-family="Arial, sans-serif" font-size="26" fill="#9b9599">Rai · погода</text>')
    return {"type": "image", "svg": c.svg(f"Погода: {city}"), "title": f"Погода: {city}, {temp}", "prompt": desc}
