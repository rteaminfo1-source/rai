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


_stem_index = None   # основы слов названия (без уточнения в скобках) → [названия]; строится при первом поиске
_QUALIFIER = {"сериал": "сериал", "телесериал": "сериал", "фильм": "фильм", "кино": "фильм", "мультфильм": "мультфильм",
              "роман": "роман", "книга": "роман", "книг": "роман", "песня": "песня", "песн": "песня", "альбом": "альбом",
              "игра": "игра", "игр": "игра", "город": "город", "река": "река", "рек": "река", "группа": "группа", "групп": "группа"}


_WORKS = {"фильм", "сериал", "мультфильм", "роман", "песня", "альбом", "игра", "группа"}
_PREPS = {"на", "в", "во", "из", "у", "под", "над", "за", "при", "по", "до", "от", "с", "со"}


def candidates(text, raw=None, kind=None):
    """Темы, названные в тексте: [(оценка, название, сколько слов совпало)] — лучшие первыми.

    Важнее: длинное совпадение («Игра престолов», а не «Игра»), имя собственное (слово с большой буквы в вопросе),
    уточнение из вопроса в скобках названия («сериал» → «Игра престолов (телесериал)»). Общее слово из словаря
    («фильм», «игра») само по себе — слабое совпадение."""
    global _stem_index
    if not _manifest:
        return []
    import re
    import lexicon
    import nlp
    if _stem_index is None:
        _stem_index = {}
        for t in _titles.values():
            base = re.sub(r"\s*\([^)]*\)$", "", t)
            if "," in base:            # человек «Оппенгеймер, Роберт» — по фамилии и по «Роберт Оппенгеймер»
                last, first = [x.strip() for x in base.split(",", 1)]
                keys = [tuple(nlp.tokens(last)), tuple(nlp.tokens(first.split()[0] + " " + last)) if first else ()]
            else:
                keys = [tuple(nlp.tokens(base))]
            for key in keys:
                if key and (len(key) > 1 or len(key[0]) >= 4):
                    _stem_index.setdefault(key, []).append(t)
    words = nlp.normalize(text).split()
    stems = [nlp.stem(w) for w in words if w not in nlp.STOPWORDS]
    plain = [w for w in words if w not in nlp.STOPWORDS]
    capital = {nlp.stem(nlp.normalize(w)) for w in re.findall(r"(?<![.!?]\s)(?<!^)\b[A-ZА-ЯЁ][\w-]+", raw or "")}
    asked = {_QUALIFIER[w] for w in plain if w in _QUALIFIER} | {_QUALIFIER[s] for s in stems if s in _QUALIFIER}
    common = getattr(lexicon, "_ru_set", None)
    if common is None:
        common = lexicon._ru_set = set(lexicon.RU.split())
    raw_words = nlp.normalize(raw or text).split()
    out = []
    for size in range(min(6, len(stems)), 0, -1):
        for i in range(len(stems) - size + 1):
            titles = _stem_index.get(tuple(stems[i:i + size]))
            if not titles:
                continue
            gram = plain[i:i + size]
            for t in titles:
                score = 2.0 * size
                if any(st in capital for st in stems[i:i + size]):
                    score += 1.5
                if size == 1 and gram[0] in common and not any(st in capital for st in stems[i:i + size]):
                    score -= 1.5
                if "," in t:
                    score += 2.0 if kind == "who" else -0.5      # «кто такой Оппенгеймер» — человек, а не фильм
                q = re.search(r"\(([^)]+)\)$", t)
                if q:
                    kinds = {_QUALIFIER.get(w, _QUALIFIER.get(nlp.stem(w))) for w in nlp.normalize(q.group(1)).split()}
                    if asked & kinds:
                        score += 1.5
                    elif kinds & _WORKS:
                        score -= 2.5                 # фильм, альбом, книга — только если о них спросили («Слон (фильм)»)
                    else:
                        score -= 0.3
                # «как появилась жизнь на Земле»: слово после «на», «в», «из» — уточнение, а не тема
                if gram[0] in raw_words:
                    k = raw_words.index(gram[0])
                    if k > 0 and raw_words[k - 1] in _PREPS:
                        score -= 2.0
                if score >= 1.0:
                    out.append((score, t, size))
    out.sort(key=lambda x: -x[0])
    return out


def lookup(text, raw=None, kind=None):
    """Тема из глубоких знаний, названная в тексте: «расскажи о сериале Игра престолов» → «Игра престолов (телесериал)».
    None — такой темы нет."""
    found = candidates(text, raw, kind)
    return found[0][1] if found else None


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
