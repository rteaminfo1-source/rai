"""Глубокие знания Rai: статьи Википедии целиком, по разделам — тысячи тем, разбитые на части.

Собирает GitHub (tools/build_deep.py → папка deep/):
  • manifest.json — какие темы есть, сколько частей, размеры;
  • NN.json.gz — сами тексты: {"Название": ["вступление", [["Раздел", "текст"], …]]}.
Тема попадает в часть по номеру crc32(название) % n, поэтому, чтобы прочитать одну тему, нужна одна часть
(около 1 МБ), а не вся база. Любой файл — меньше 30 МБ (сборщик это проверяет).

В браузере части лежат на сайте (deep/NN.php) и догружаются по одной, когда нужна тема из этой части;
на сервере (app.py) и в тестах — читаются из папки deep/.
"""

import gzip
import json
import os
import zlib

import net

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get("RAI_DEEP_DIR", os.path.join(BASE_DIR, "deep"))
URL = ""          # в браузере: откуда брать части, например "deep/" → deep/07.php
MAX_PARTS = 8     # сколько частей держать в памяти одновременно
MAX_FILE = 30 * 1024 * 1024

_manifest = None
_titles = {}      # название в нижнем регистре → название
_parts = {}       # номер части → {название: [вступление, [[раздел, текст], …]]}
_order = []       # порядок загрузки частей (старые выгружаются)
_failed = set()   # части, которые не загрузились (не пробуем снова в этом сеансе)


def _key(title):
    return " ".join((title or "").lower().replace("ё", "е").split())


def load_manifest(data=None):
    """Загрузить список тем. Без него глубоких знаний просто нет. Возвращает число тем."""
    global _manifest, _titles, _stem_index
    if data is None:
        path = os.path.join(DIR, "manifest.json")
        if not os.path.exists(path):
            return 0
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    if isinstance(data, str):
        data = json.loads(data)
    if not data or not data.get("n") or not data.get("titles"):
        return 0
    _manifest = data
    _titles = {_key(t): t for t in data["titles"]}
    _stem_index = None
    _parts.clear()
    _order.clear()
    _failed.clear()
    return len(_titles)


def ready():
    return bool(_manifest)


def count():
    return len(_titles)


def part_of(title, n=None):
    """Номер части, в которой лежит тема (так же считает сборщик)."""
    return zlib.crc32(title.encode("utf-8")) % (n or _manifest["n"])


def title_of(name):
    """Точное название темы, если она есть в глубоких знаниях, иначе None."""
    return _titles.get(_key(name)) if _manifest else None


def _read_part(n):
    if URL:
        # Python в браузере читает часть синхронным запросом (сайт отдаёт её сжатой — браузер распакует сам)
        text = net._xhr(URL + f"{n:02d}.php")
        return json.loads(text)
    path = os.path.join(DIR, f"{n:02d}.json.gz")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _part(n):
    if n in _parts:
        return _parts[n]
    if n in _failed:
        return None
    try:
        data = _read_part(n)
    except (OSError, ValueError, net.NetError, ImportError):
        _failed.add(n)
        return None
    _parts[n] = data
    _order.append(n)
    while len(_order) > MAX_PARTS:
        _parts.pop(_order.pop(0), None)
    return data


def article(name):
    """Статья целиком: {"title", "lead", "sections": [{"title", "text"}], "url"} или None."""
    title = title_of(name)
    if not title:
        return None
    data = _part(part_of(title))
    raw = (data or {}).get(title)
    if not raw:
        return None
    lead, sections = raw[0], raw[1] if len(raw) > 1 else []
    import encyclopedia
    clean = lambda t: (t or "").replace("\u0301", "")   # ударения («Компью́тер») мешают узнавать слова
    return {"title": title, "lead": clean(lead), "sections": [{"title": h, "text": clean(t)} for h, t in sections if t],
            "url": encyclopedia.page_url(title)}


_stem_index = None   # основы слов названия (без уточнения в скобках) → название; строится при первом поиске


def lookup(text):
    """Тема из глубоких знаний, названная в тексте: «расскажи о сериале Игра престолов» → «Игра престолов».
    Ищет самые длинные совпадения основ слов. None — такой темы нет."""
    global _stem_index
    if not _manifest:
        return None
    import re
    import nlp
    if _stem_index is None:
        _stem_index = {}
        for t in _titles.values():
            key = tuple(nlp.tokens(re.sub(r"\s*\([^)]*\)$", "", t)))
            if key and (len(key) > 1 or len(key[0]) >= 4):
                _stem_index.setdefault(key, t)
    words = nlp.tokens(text)
    for size in range(min(6, len(words)), 0, -1):
        for i in range(len(words) - size + 1):
            hit = _stem_index.get(tuple(words[i:i + size]))
            if hit:
                return hit
    return None


def find(subject):
    """Статья о теме по названию в любом падеже («пушкине», «французской революции») или None."""
    if not _manifest or not (subject or "").strip():
        return None
    exact = article(subject)
    if exact:
        return exact
    import encyclopedia
    import nlp
    found = encyclopedia.lookup(subject)
    if not found:
        other = lookup(subject)          # темы сверх энциклопедии: избранные, хорошие, популярные статьи
        return article(other) if other else None
    # «слон» — не город Слоним: основы слов названия и вопроса должны совпасть по-настоящему
    want, have = set(nlp.tokens(subject)), set(nlp.tokens(found["title"]))
    return article(found["title"]) if not want or want & have else None


def stats():
    return {"topics": count(), "parts": (_manifest or {}).get("n", 0), "loaded": sorted(_parts),
            "built": (_manifest or {}).get("built")}
