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

def make_image(prompt: str, seed=None) -> dict:
    """Нарисовать SVG по описанию. Возвращает {"type": "image", "svg", "title", "prompt"}."""
    words = _words(prompt)
    rnd = random.Random(seed)
    c = _Canvas(rnd)
    found = [name for name, prefixes in SCENES if _has(words, prefixes)]
    accent = next((col for p, col in COLORS.items() if _has(words, (p,))), None)
    palette = [accent] if accent else []
    palette += ["#e10600", "#ff2a2a", "#7a0000", "#f2f2f2", "#1a1a1a"]

    if "logo" in found:
        m = re.search(r"(?:логотип\w*|лого|эмблем\w*|значок)\s+(?:для\s+|компании\s+|команды\s+)?(.+)", prompt, re.I)
        name = (m.group(1) if m else "Rteam").strip(" .!?«»\"'")
        _logo(c, name, accent)
        return {"type": "image", "svg": c.svg("Логотип " + name), "title": f"Логотип «{name}»", "prompt": prompt}

    if not found or found == ["abstract"]:
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


def is_slides_request(text: str) -> bool:
    return bool(_SLIDES_WORDS.search(text or "")) and not _QUESTION.search(text or "")


def slides_topic(text: str) -> str:
    topic = _SLIDES_FILLER.sub(" ", text or "")
    return re.sub(r"\s+", " ", topic).strip(" .,!?:;«»\"'")


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
        s = re.sub(r"^([•\-*]|\d+[.)])\s*", "", s)
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


def make_slides(topic: str, intents: list, max_slides: int = 6) -> dict:
    """Собрать презентацию по теме из статей базы знаний."""
    title = topic[:1].upper() + topic[1:] if topic else "Презентация"
    slides = [{"kind": "title", "title": title, "subtitle": "Rai · Rteam"}]

    for intent in intents:
        text = intent["answers"][0].replace("{name}", "")
        if intent.get("more"):
            text += "\n\n" + intent["more"]
        heading = intent.get("title", title)
        for seg in _split_segments(text):
            if len(slides) >= max_slides - 1:
                break
            if seg[0] == "code" and seg[2].strip():
                slides.append({"kind": "code", "title": heading + ": пример", "lang": seg[1], "code": seg[2]})
            elif seg[0] == "table":
                cells = _table(seg[1])
                if cells:
                    slides.append({"kind": "table", "title": heading, "rows": cells})
            elif seg[0] == "text":
                items = [b for b in _bullets(seg[1]) if not b.endswith(":") or len(b) > 40]
                for k in range(0, len(items), 5):
                    if len(slides) >= max_slides - 1:
                        break
                    slides.append({"kind": "bullets", "title": heading, "bullets": items[k:k + 5]})

    template = len(slides) == 1
    if template:
        # Нет знаний по теме — даём структуру, которую нужно заполнить своим текстом.
        for head in ("Введение", "Главная идея", "Примеры", "Выводы"):
            slides.append({"kind": "bullets", "title": head,
                           "bullets": [f"Здесь будет ваш текст о теме «{title}».", "Замените этот пункт своим."]})
    slides.append({"kind": "end", "title": "Спасибо за внимание!", "subtitle": "Вопросы?"})
    _decorate(slides, topic or title)
    return {"type": "slides", "title": title, "slides": slides, "template": template}


TRANSITIONS = ["fade", "slide", "zoom", "wipe"]


def _decorate(slides, topic):
    """Картинки на обложку и на слайды с текстом, переходы между слайдами."""
    seed = zlib.crc32(topic.encode("utf-8"))
    slides[0]["image"] = make_image(topic, seed=seed)["svg"]
    with_text = [s for s in slides if s["kind"] == "bullets" and len(s["bullets"]) <= 4]
    for k, slide in enumerate(with_text[:3]):
        slide["image"] = make_image(f"{topic} {slide['title']}", seed=seed + k + 1)["svg"]
    for k, slide in enumerate(slides):
        slide["transition"] = TRANSITIONS[k % len(TRANSITIONS)]


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
