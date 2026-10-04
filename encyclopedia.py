"""Энциклопедия Rai: ~10 000 важнейших тем из Википедии — отвечает без интернета.

Данные (encyclopedia.json) собирает GitHub: tools/build_encyclopedia.py, workflow «Знания Rai».
Понимает: «что такое фотосинтез», «кто такой Пушкин», «расскажи о Великой французской революции»,
«где находится Эверест», «Эйнштейн это кто», просто «Жираф», «какие разделы знаешь», «случайная тема»,
«темы раздела история». Тексты — из Википедии (CC BY-SA), источник указывается в каждом ответе.
"""

import json
import math
import os
import random
import re
import urllib.parse

import nlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH = os.environ.get("RAI_ENCYCLOPEDIA_PATH", os.path.join(BASE_DIR, "encyclopedia.json"))

_ASK_RE = re.compile(
    r"^\s*(?:а\s+|и\s+|слушай,?\s+|скажи,?\s+)?(?:"
    r"что\s+такое|что\s+это\s+такое|что\s+это\s+за|что\s+за|кто\s+так(?:ой|ая|ое|ие)|кто\s+(?:был|была|были|это)|"
    r"(?:расскажи|расскажите|поведай)(?:\s+мне)?(?:\s+(?:кратко|коротко|немного|подробно))?\s+(?:про|о|об|обо)|"
    r"что\s+(?:ты\s+)?знаешь\s+(?:про|о|об|обо)|что\s+известно\s+(?:про|о|об|обо)|"
    r"(?:информаци[яю]|инфа|справка|статья)\s+(?:про|о|об|обо)|"
    r"где\s+(?:находится|находятся|расположен[аоы]?|течёт|течет|протекает)|"
    r"кратко\s+(?:про|о|об|обо)|объясни(?:\s+мне)?(?:\s+что\s+такое)?)"
    r"\s+(.+?)[\s?!.]*$"
    r"|^\s*(.+?)\s*(?:[-—–]\s*)?(?:это\s+)?(?:кто|что)\s+(?:это|такой|такая|такое|такие)[\s?!.]*$"
    r"|^\s*(.+?)\s*[-—–]?\s*это\s+(?:кто|что)[\s?!.]*$",
    re.I,
)
_LIST_RE = re.compile(r"(?:какие|список|покажи|перечисли)\s+(?:у\s+тебя\s+)?(?:есть\s+)?(?:разделы|категори|темы)|"
                      r"энциклопеди|сколько\s+(?:ты\s+)?(?:знаешь|у\s+тебя)\s+(?:тем|категорий|статей)|(?:10|10\s?000|десять\s+тысяч)\s+(?:тем|категорий)", re.I)
_RANDOM_RE = re.compile(r"случайн\w*\s+(?:тем|стать|факт\w*\s+из\s+энциклопеди)|расскажи\s+(?:что-?нибудь|что-?то)\s+(?:новое|умное|познавательное)", re.I)
_SECTION_RE = re.compile(r"(?:темы|статьи|список)\s+(?:из\s+)?(?:раздела|категории|про)\s+(.+?)[\s?!.]*$", re.I)
# Слова-приставки, которые не меняют тему: «расскажи кратко о Пушкине подробнее»
_NOISE = {nlp.stem(w) for w in "пожалуйста подробно подробнее кратко коротко вкратце немного вообще мне нам такое такой это".split()}

_data = None          # {"sections", "cats", "items"}
_index = {}           # (основы слов) → [(приоритет, номер темы, слова названия без изменений)]
_loaded_from = None

# Окончания для имён и названий: «Менделеева/Менделеевым» → «менделеев», «Великой французской революции» →
# «велик французск революц». Общий стеммер nlp режет фамилии непоследовательно («менделеев» → «менделе»).
_ENDS = sorted("""иями ями ами ыми ими ием ией иях иям ого его ому ему ая яя ое ее ые ие ых их ый ий ой ей ою ею
                  ым им ом ем ам ям ах ях ую юю ия ию ии а я у ю е о ы и ь й""".split(), key=len, reverse=True)
_ROMAN = {"i": "перв", "ii": "втор", "iii": "трет", "iv": "четверт", "v": "пят", "vi": "шест", "vii": "седьм",
          "viii": "восьм", "ix": "девят", "x": "десят", "xi": "одиннадцат", "xii": "двенадцат"}
_PERSON_RE = re.compile(r"^[^,()]+,\s*[^,()]+(?:\s*\([^)]*\))?$")


def _norm(word):
    if word in _ROMAN:
        return _ROMAN[word]
    if len(word) <= 3 or not re.fullmatch(r"[а-я]+", word):
        return word
    for end in _ENDS:
        if word.endswith(end) and len(word) - len(end) >= 3:
            return word[:-len(end)]
    return word


def _words(text):
    return tuple(nlp.normalize(text).split())


def _key(text):
    return tuple(_norm(w) for w in _words(text))


def _names(title, aliases):
    """Все названия темы с приоритетами: 0 — само название, 1 — без уточнения в скобках, 2 — другие имена."""
    yield title, 0
    base = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    if base != title:
        yield base, 1
    # «Пушкин, Александр Сергеевич» → «Александр Сергеевич Пушкин», «Александр Пушкин», «Пушкин»
    m = re.match(r"^([^,]+),\s*([^,]+)$", base)
    if m:
        last, first = m.group(1).strip(), m.group(2).strip()
        yield f"{first} {last}", 1
        parts = first.split()
        if len(parts) >= 2:
            yield f"{parts[0]} {last}", 1
        yield last, 1          # просто фамилия: из однофамильцев победит самый известный
    for a in aliases:
        yield a, 2


def load(data=None, path=None):
    """Загрузить энциклопедию из словаря или файла. Без файла Rai просто работает без неё."""
    global _data, _index, _loaded_from
    if data is None:
        path = path or PATH
        if not os.path.exists(path):
            return 0
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _loaded_from = path
    index = {}
    for i, item in enumerate(data.get("items", [])):
        title, aliases = item[0], item[4] if len(item) > 4 else []
        for name, prio in _names(title, aliases):
            key = _key(name)
            if not key or (len(key) == 1 and (len(key[0]) < 3 or key[0] in nlp.STOPWORDS or nlp.stem(key[0]) in nlp.GENERIC)):
                continue
            cands = index.setdefault(key, [])
            if not any(c[1] == i for c in cands):
                cands.append((prio, i, _words(name)))
    _data, _index = data, index
    return len(data.get("items", []))


def count():
    return len(_data["items"]) if _data else 0


def _item(i):
    title, desc, cat, text = _data["items"][i][:4]
    section_no, cat_name = _data["cats"][cat]
    return {"title": title, "desc": desc, "section": _data["sections"][section_no], "cat": cat_name, "text": text}


def _is_person(i):
    return bool(_PERSON_RE.match(_data["items"][i][0]))


def _best(key, raw, kind=None):
    """Лучшая тема для ключа: точная форма слов, кто/что, известность (в скольких Википедиях есть статья)."""
    cands = _index.get(key)
    if not cands:
        return None

    def score(c):
        prio, i, words = c
        item = _data["items"][i]
        pop = item[5] if len(item) > 5 else 0
        s = prio - 2 * math.log10(pop + 1)
        if words == raw:
            s -= 1                       # «Пушкин» — точно поэт, а не «Пушкино»
        if kind == "who":
            s += -2 if _is_person(i) else 1
        elif kind == "what":
            s += 1 if _is_person(i) else 0
        return s
    return min(cands, key=score)


def lookup(subject, kind=None):
    """Тема по названию в любом падеже: «Пушкине», «великой французской революции». None — нет такой.
    kind: "who" — спрашивают про человека, "what" — про предмет или место."""
    if not _data:
        return None
    raw = _words(subject)
    words = _key(subject)
    if not words:
        return None
    keep = [j for j, w in enumerate(words) if nlp.stem(raw[j]) not in _NOISE]
    variants = [(words, raw), (tuple(words[j] for j in keep), tuple(raw[j] for j in keep))]
    for key, r in variants:
        hit = _best(key, r, kind)
        if hit:
            return _item(hit[1])
    # Одно лишнее слово по краям длинного названия: «расскажи о великой французской революции 1789»
    key, r = variants[1]
    if len(key) >= 3:
        for k2, r2 in ((key[:-1], r[:-1]), (key[1:], r[1:])):
            hit = _best(k2, r2, kind)
            if hit and hit[0] <= 1:
                return _item(hit[1])
    return None


def _render(t):
    url = "https://ru.wikipedia.org/wiki/" + urllib.parse.quote(t["title"].replace(" ", "_"))
    head = f"### {t['title']}"
    if t["desc"]:
        head += f"\n*{t['desc'][:1].upper() + t['desc'][1:]}*"
    where = t["section"] if t["cat"] in ("", t["section"]) else f"{t['section']} → {t['cat']}"
    return f"{head}\n\n{t['text']}\n\n📚 {where} · по материалам [Википедии]({url}) (CC BY-SA)"


def catalog():
    if not _data:
        return None
    per = {}
    for item in _data["items"]:
        s = _data["cats"][item[2]][0]
        per.setdefault(s, []).append(item[0])
    rows = []
    for s, name in enumerate(_data["sections"]):
        titles = per.get(s, [])
        if titles:
            sample = ", ".join(random.Random(s).sample(titles, min(4, len(titles))))
            rows.append(f"| **{name}** | {len(titles)} | {sample} |")
    return (f"## Энциклопедия Rai: {count():,} тем".replace(",", " ") +
            f" в {len(rows)} разделах и {len(_data['cats'])} подразделах\n\n| Раздел | Тем | Например |\n|---|---|---|\n" +
            "\n".join(rows) +
            "\n\nСпрашивайте: «что такое …», «кто такой …», «расскажи о …», «где находится …» или просто название. "
            "«Темы раздела история» — список, «случайная тема» — что-нибудь новое. Работает без интернета.")


def section_list(name):
    if not _data:
        return None
    want = _key(name)
    for s, sec in enumerate(_data["sections"]):
        if want and (_key(sec)[:len(want)] == want or want[0] in _key(sec)):
            titles = [it[0] for it in _data["items"] if _data["cats"][it[2]][0] == s]
            pick = sorted(random.sample(titles, min(30, len(titles))))
            return (f"## {sec}: {len(titles)} тем\n\nНапример: " + ", ".join(pick) +
                    "\n\nСпросите про любую: «расскажи о …».")
    return None


def context(query, limit=2):
    """Темы, которые упомянуты в вопросе, — подсказка для нейросети: [{"title", "text", "url"}]."""
    if not _data:
        return []
    words, raw = _key(query), _words(query)
    found, used = [], set()
    for size in range(min(6, len(words)), 0, -1):          # сначала длинные названия: «великая французская революция»
        for i in range(len(words) - size + 1):
            if any(j in used for j in range(i, i + size)):
                continue
            hit = _best(tuple(words[i:i + size]), tuple(raw[i:i + size]))
            if hit and (size > 1 or hit[0] <= 1) and nlp.stem(raw[i]) not in nlp.GENERIC:
                t = _item(hit[1])
                if all(t["title"] != f["title"] for f in found):
                    url = "https://ru.wikipedia.org/wiki/" + urllib.parse.quote(t["title"].replace(" ", "_"))
                    found.append({"title": t["title"], "text": t["text"], "url": url})
                    used.update(range(i, i + size))
            if len(found) >= limit:
                return found
    return found


def answer(text, explicit_only=False):
    """Ответ энциклопедии или None. explicit_only — только на прямой вопрос («что такое…», «кто такой…»)."""
    if not _data:
        return None
    if _LIST_RE.search(text):
        return catalog()
    if _RANDOM_RE.search(text):
        return _render(_item(random.randrange(count())))
    m = _SECTION_RE.search(text)
    if m:
        found = section_list(m.group(1))
        if found:
            return found
    m = _ASK_RE.match(text)
    subject = next((g for g in m.groups() if g), None) if m else None
    if subject:
        low = text.lower()
        kind = "who" if re.search(r"\bкто\b", low) else ("what" if re.search(r"\bчто\s+(?:такое|это|за)\b|\bгде\b", low) else None)
        t = lookup(subject, kind)
        return _render(t) if t else None
    if explicit_only:
        return None
    # Просто название темы: «Жираф», «Пётр Первый», «теория относительности»
    clean = text.strip(" \t\n?!.")
    if 0 < len(clean.split()) <= 6:
        t = lookup(clean)
        if t:
            return _render(t)
    return None


load()
