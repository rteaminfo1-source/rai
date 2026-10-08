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


def _attr(img, key, min_p=0.5):
    for a in img.get("attrs") or []:
        if isinstance(a, dict) and a.get("key") == key and a.get("p", 0) >= min_p:
            return a.get("value")
    return None


_KIND = {"фотография": "Фото", "рисунок": "Рисунок", "картина": "Картина", "скриншот экрана": "Скриншот экрана",
         "документ с текстом": "Документ с текстом", "мультяшная картинка": "Мультяшная картинка", "3D-графика": "3D-графика",
         "схема или график": "Схема или график"}


def caption(img):
    """Одна фраза о картинке: «Фото на улице, на закате, ясно: **море**, ещё видно: пляж, небо. Людей нет.»"""
    labels = [x for x in img.get("labels") or [] if isinstance(x, dict) and x.get("ru")]
    if not labels:
        return None
    kind = _attr(img, "kind", 0.45) or "фотография"
    photo = kind == "фотография"
    head = [_KIND.get(kind, "Картинка")]
    where = _attr(img, "place", 0.65) if photo else None
    if where:
        head.append(where)
    when = []
    if photo:
        t = _attr(img, "time", 0.55)
        if t:
            when.append(t)
        if where == "на улице":
            for key, p in (("weather", 0.5), ("season", 0.55)):
                v = _attr(img, key, p)
                if v:
                    when.append(v)
    text = " ".join(head) + (", " + ", ".join(when) if when else "")
    main = labels[0]["ru"]
    rest = [x["ru"] for x in labels[1:5] if x.get("p", 0) >= 0.04 and x["ru"] != main]
    out = f"{text}: **{main}**" + (f", ещё видно: {', '.join(rest)}" if rest else "") + "."
    people = _attr(img, "people", 0.55) if photo else None
    if people:
        out += " " + people[:1].upper() + people[1:] + "."
    return out


def _is_person(title):
    return bool(encyclopedia._PERSON_RE.match(title or "") or encyclopedia._MONARCH_RE.match(title or ""))


# Вопросы о картинке: «сколько людей», «день или ночь», «какого цвета», «что за здание», «где это», «это фото или рисунок»
_Q_PEOPLE = re.compile(r"сколько\s+(?:тут\s+|здесь\s+|на\s+\w+\s+)?(?:людей|человек)|есть\s+ли\s+(?:тут\s+|здесь\s+)?(?:люди|человек)|кто\s+на\s+(?:фото|картинк|снимк)", re.I)
_Q_TIME = re.compile(r"день\s+или\s+ночь|ночь\s+или\s+день|когда\s+(?:сделан|снят|сфотограф)|время\s+суток|какое\s+время", re.I)
_Q_WEATHER = re.compile(r"какая\s+(?:тут\s+|там\s+)?погода|погода\s+на\s+(?:фото|картинк)|время\s+года|какой\s+сезон|зима\s+или\s+лето", re.I)
_Q_COLOR = re.compile(r"как(?:ого|ие|ой|ая)\s+цвет|какие\s+цвета|цвет\w*\s+(?:на\s+)?(?:фото|картинк)", re.I)
_Q_WHAT = re.compile(r"что\s+(?:это\s+)?за\s+(\w+)|как\w*\s+это\s+(\w+)|кто\s+это|что\s+это\s+(?:такое)?|где\s+(?:это|сделан|снят)|что\s+(?:за\s+)?место", re.I)
_Q_KIND = re.compile(r"(?:это\s+)?(?:фото|фотография)\s+или\s+(?:рисунок|картина|арт)|нарисован|настоящ\w*\s+(?:фото|или)|скриншот\s+или", re.I)
_PEOPLE_ANSWER = {"людей нет": "Людей на картинке не видно.", "один человек": "На картинке, похоже, один человек.",
                  "два человека": "На картинке, похоже, два человека.", "несколько человек": "На картинке несколько человек.",
                  "толпа": "На картинке много людей — толпа."}


def answer(img, question):
    """Прямой ответ на вопрос о картинке (одна-две фразы) или None — тогда просто описание."""
    q = (question or "").strip()
    if not q:
        return None
    labels = [x for x in img.get("labels") or [] if isinstance(x, dict) and x.get("ru")]
    if _Q_PEOPLE.search(q):
        people = _attr(img, "people", 0.35)
        if people:
            return _PEOPLE_ANSWER.get(people, people) + " Кто это — по лицу не определяю."
    if _Q_TIME.search(q):
        t = _attr(img, "time", 0.4)
        if t:
            return {"днём": "Снято днём.", "ночью": "Снято ночью или в темноте.", "на закате или рассвете": "Снято на закате или рассвете."}.get(t, t)
    if _Q_WEATHER.search(q):
        parts = [x for x in (_attr(img, "weather", 0.4), _attr(img, "season", 0.4)) if x]
        if parts:
            return "Похоже: " + ", ".join(parts) + "."
    if _Q_COLOR.search(q):
        colors = [c["name"] for c in img.get("colors") or [] if isinstance(c, dict) and c.get("name")]
        if colors:
            return "Основные цвета: " + ", ".join(colors[:4]) + (f"; {img['tone']} тона" if img.get("tone") else "") + "."
    if _Q_KIND.search(q):
        kind = _attr(img, "kind", 0.4)
        if kind:
            return f"Это {kind}" + (" — не фотография." if kind != "фотография" else ".")
    if _Q_WHAT.search(q):
        known = [k for k in img.get("known") or [] if isinstance(k, dict) and k.get("title") and not _is_person(k["title"])]
        if known:
            k = known[0]
            sure = "очень похоже" if k.get("by") in ("photo", "both") else "похоже"
            return f"Это, {sure}, **{k['title']}**."
        if labels:
            return f"Похоже на **{labels[0]['ru']}**" + (f" (уверенность {_pct(labels[0].get('p', 0))})." if labels[0].get("p") else ".")
    return None


def describe(data, question=""):
    """Markdown «что на картинке» или None, если модель ничего уверенно не увидела."""
    blocks = []
    for n, img in enumerate(data[:4], 1):
        labels = [x for x in img.get("labels") or [] if isinstance(x, dict) and x.get("ru")]
        if not labels:
            continue
        head = f"## Что на картинке{f' {n}' if len(data) > 1 else ''}"
        reply = answer(img, question)
        lines = [head, ""] + ([f"**Ответ:** {reply}", ""] if reply else []) + [caption(img)]
        # конкретная вещь из энциклопедии: по сходству с фото из статьи или по названию (людей не узнаём)
        info_done = False
        for k in [x for x in img.get("known") or [] if isinstance(x, dict) and x.get("title")][:2]:
            if _is_person(k["title"]):
                continue
            how = {"photo": "очень похоже на фото из статьи", "both": "и по виду, и по фото из статьи"}.get(k.get("by"), "по виду")
            t = encyclopedia.lookup(k["title"])
            first = encyclopedia.tidy(encyclopedia._sentences(t["text"])[0]) if t and t.get("text") else ""
            lines += ["", f"🔎 **Узнал: {k['title']}** ({how})" + (f" — {first}" if first else "") +
                      f" [Подробнее]({encyclopedia.page_url(k['title'])})"]
            info_done = True
            break
        regions = [r for r in img.get("regions") or [] if isinstance(r, dict) and r.get("ru")]
        if regions:
            lines += ["", "🧩 **По частям:** " + "; ".join(f"{r['where']} — {r['ru']}" for r in regions[:5]) + "."]
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
        view = _attr(img, "view", 0.6)
        if view and _attr(img, "kind", 0.45) in (None, "фотография"):
            look.append(view)
        if look:
            lines += ["", "🎨 " + " · ".join(look)]
        # справка: животное, растение, планета, здание…
        for x in labels[:3]:
            if info_done:
                break
            if x.get("group") in _ABOUT_GROUPS and x["ru"].lower() not in _GENERIC and x.get("p", 0) >= 0.12:
                t = encyclopedia.lookup(re.sub(r"\s+(вблизи|из космоса|с кольцами)$", "", x["ru"]))
                if t:
                    first = encyclopedia.tidy(encyclopedia._sentences(t["text"])[0])
                    lines += ["", f"💡 **{t['title']}**: {first} [Подробнее]({encyclopedia.page_url(t['title'])})"]
                    break
        blocks.append("\n".join(lines))
    if not blocks:
        return None
    note = ("\n\n*Распознаёт зрение Rai прямо в вашем браузере — картинка никуда не отправляется. Rai узнаёт сотни понятий "
            "и тысячи конкретных вещей из своей энциклопедии; людей по лицу не узнаёт.*")
    return "\n\n".join(blocks) + note


def summary(data):
    """Короткая строка для нейросети: что видно на картинках."""
    parts = []
    for n, img in enumerate(data[:4], 1):
        labels = [f"{x['ru']} ({_pct(x.get('p', 0))})" for x in (img.get("labels") or [])[:6] if isinstance(x, dict) and x.get("ru")]
        colors = ", ".join(c["name"] for c in (img.get("colors") or [])[:3] if isinstance(c, dict) and c.get("name"))
        if labels:
            known = [k["title"] for k in img.get("known") or [] if isinstance(k, dict) and k.get("title") and not _is_person(k["title"])]
            parts.append(f"Картинка {n}: " + (caption(img) or "").replace("**", "") + " Понятия: " + ", ".join(labels) +
                         (f"; узнал: {known[0]}" if known else "") + (f"; цвета: {colors}" if colors else ""))
    return "\n".join(parts)
