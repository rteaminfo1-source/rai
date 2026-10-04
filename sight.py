"""Зрение Rai: ответ «что на картинке» по тому, что увидела модель в браузере (vision.js).

Страница присылает после метки [[vision]] JSON: для каждой картинки — понятия с уверенностью
({"ru", "p", "group"}), основные цвета, яркость и тон. Здесь из этого собирается ответ: что изображено, что ещё
видно, цвета и освещение; про животное, растение, достопримечательность или космос — справка из энциклопедии.
"""

import json
import re

import encyclopedia

MARK = "[[vision]]"
_ABOUT_GROUPS = {"Животные", "Растения", "Космос", "Город и здания", "Еда и напитки", "Транспорт", "Природа"}
_GENERIC = {"еда", "природа", "пейзаж", "город", "человек", "животные", "дом", "небо", "фрукты", "овощи", "цветы",
            "дерево", "птица", "рыба", "машина", "скриншот", "документ", "рисунок", "картина", "интерьер"}


def split(raw):
    """(текст до метки, данные зрения или None)."""
    text, _, vis = (raw or "").partition(MARK)
    try:
        data = json.loads(vis) if vis.strip() else None
    except ValueError:
        data = None
    if isinstance(data, dict):
        data = [data]
    return text, (data if isinstance(data, list) and data else None)


def _pct(p):
    return f"{round(p * 100)}%" if p >= 0.01 else "<1%"


def describe(data, question=""):
    """Markdown «что на картинке» или None, если модель ничего уверенно не увидела."""
    blocks = []
    for n, img in enumerate(data[:4], 1):
        labels = [x for x in img.get("labels") or [] if isinstance(x, dict) and x.get("ru")]
        if not labels:
            continue
        main = labels[0]
        rest = [x["ru"] for x in labels[1:6] if x.get("p", 0) >= 0.03]
        head = f"## Что на картинке{f' {n}' if len(data) > 1 else ''}"
        lines = [head, "", f"Похоже на: **{main['ru']}**" + (f" — ещё вижу: {', '.join(rest)}." if rest else ".")]
        table = [f"| {x['ru']} | {x.get('group', '')} | {_pct(x.get('p', 0))} |" for x in labels[:6]]
        lines += ["", "| Что вижу | Раздел | Уверенность |", "|---|---|---|"] + table
        look = []
        colors = [c["name"] for c in img.get("colors") or [] if isinstance(c, dict) and c.get("name")]
        if colors:
            look.append("цвета: " + ", ".join(colors[:4]))
        if img.get("tone"):
            look.append(img["tone"] + " тона")
        if img.get("light"):
            look.append(img["light"] + " картинка")
        if look:
            lines += ["", "🎨 " + " · ".join(look)]
        # справка: животное, растение, планета, здание…
        for x in labels[:3]:
            if x.get("group") in _ABOUT_GROUPS and x["ru"].lower() not in _GENERIC and x.get("p", 0) >= 0.12:
                t = encyclopedia.lookup(re.sub(r"\s+(вблизи|из космоса|с кольцами)$", "", x["ru"]))
                if t:
                    first = re.split(r"(?<=[.!?])\s+", t["text"])[0]
                    lines += ["", f"💡 **{t['title']}**: {first} [Подробнее]({encyclopedia.page_url(t['title'])})"]
                    break
        blocks.append("\n".join(lines))
    if not blocks:
        return None
    note = ("\n\n*Распознаёт модель CLIP прямо в вашем браузере — картинка никуда не отправляется. "
            "Это догадка по сотням понятий: небо, солнце, люди, животные, еда, транспорт, здания, скриншоты и др.*")
    return "\n\n".join(blocks) + note


def summary(data):
    """Короткая строка для нейросети: что видно на картинках."""
    parts = []
    for n, img in enumerate(data[:4], 1):
        labels = [f"{x['ru']} ({_pct(x.get('p', 0))})" for x in (img.get("labels") or [])[:6] if isinstance(x, dict) and x.get("ru")]
        colors = ", ".join(c["name"] for c in (img.get("colors") or [])[:3] if isinstance(c, dict) and c.get("name"))
        if labels:
            parts.append(f"Картинка {n}: " + ", ".join(labels) + (f"; цвета: {colors}" if colors else "") +
                         (f"; {img['light']}" if img.get("light") else ""))
    return "\n".join(parts)
