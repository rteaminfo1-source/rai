"""Rai понимает текст, набранный не на той раскладке, и слова с опечатками.

    fix("ghbdtn rfr ltkf")      → «привет как дела»        (английская раскладка вместо русской)
    fix("погода vbycr")         → «погода минск»           (одно слово не на той раскладке)
    fix("рудщ цщкдв")           → «hello world»            (русская раскладка вместо английской)
    fix("пагода в минске")      → «погода в минске»        (опечатка)

Словарь: lexicon.py (частые слова) + все русские слова из текстов самого Rai (база знаний, словарь, стихи,
справочник, игры). Формы слов узнаются по основе (nlp.stem), поэтому «приготовила» — тоже известное слово.
Исправляем осторожно: только неизвестные слова, только похожие (1–2 буквы разницы), первую букву не меняем,
имена с большой буквы в середине фразы не трогаем, команды с «сырым» текстом (Морзе, Base64, транслит…) — тоже.
"""

import glob
import os
import re
from collections import Counter

import lexicon
import nlp

BASE = os.path.dirname(os.path.abspath(__file__))

_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>~&?/^$#@"
_RU = "йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ?,.:;№\""
TO_RU = str.maketrans(_EN, _RU)
TO_EN = str.maketrans(_RU[:66], _EN[:66])

_CYR = re.compile(r"[а-яё]", re.I)
_LAT = re.compile(r"[a-z]", re.I)
# команды, где текст — «сырые» данные: его не исправляем
_RAW_RE = re.compile(r"транслит|латиниц|раскладк|морзе|base\s*64|бейс\s*64|\bmd5\b|\bsha|цезар|переверни|заглавными|"
                     r"прописными|строчными|большими буквами|маленькими буквами|сколько\s+(?:слов|символов|букв|гласн|согласн)|"
                     r"палиндром|анаграм|хеш|```|https?://|www\.|\S+@\S+\.\S+|\[\[(?:screen|link-data)\]\]", re.I)

# сленг и сокращения не «исправляем»: «ваще» — не «ваше», «норм» — не «нора»
SLANG = set("""
ваще щас щя чо че чё норм нормас спс пасиб пж пжл плз плиз пожалуйсто кароч короч оч прив здрасте здрасьте мб хз лан
ладн окей окс пон понял кек лол рофл имхо кста кстате тож тоже тыщ тыща инет комп ноут телек видос прога проги
скока скоко стока чета чето шо ща щаз пасибки спасибки приветик пока-пока хай бро братан чел челик кринж краш вайб
""".split())

_lex = None


def _build():
    """Слова и их частоты: словарь lexicon.py (вес 50) + тексты Rai."""
    global _lex
    freq = Counter()
    for w in lexicon.RU.split():
        freq[w.replace("ё", "е")] += 50
    files = [f for f in glob.glob(os.path.join(BASE, "*.py")) if not f.endswith(("test_app.py", "fake_net.py", "lexicon.py", "fixer.py", "places.py", "encyclopedia.py"))]
    files += [os.path.join(BASE, n) for n in ("knowledge.json", "glossary.json")]
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                freq.update(re.findall(r"[а-я]+", fh.read().lower().replace("ё", "е")))
        except OSError:
            continue
    words = {w: c for w, c in freq.items() if len(w) >= 2}
    stems = {nlp.stem(w) for w in words}
    index = {}
    for w, c in words.items():
        index.setdefault(w[0], []).append((w, c))
    for lst in index.values():
        lst.sort(key=lambda x: (-x[1], x[0]))
    en = set(lexicon.EN.split())
    _lex = {"words": words, "stems": stems, "index": index, "en": en}
    return _lex


def lex():
    return _lex or _build()


def known(word):
    """Известное русское слово (или его форма)."""
    w = word.lower().replace("ё", "е")
    L = lex()
    return w in L["words"] or w in nlp.COMMON or w in nlp.STOPWORDS or (len(w) > 3 and nlp.stem(w) in L["stems"])


def _dist(a, b, limit):
    """Расстояние Дамерау — Левенштейна (перестановка соседних букв = 1 ошибка), с ранним выходом."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        best = i
        for j in range(1, len(b) + 1):
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, prev2[j - 2] + 1)
            cur[j] = v
            best = min(best, v)
        if best > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def suggest(word):
    """Похожее известное слово для слова с опечаткой или None."""
    w = word.lower().replace("ё", "е")
    if len(w) < 4 or not re.fullmatch(r"[а-я]+", w) or w in SLANG or known(w):
        return None
    limit = 1 if len(w) < 10 else 2  # две ошибки — только в длинных словах
    best, best_key = None, None
    for cand, freq in lex()["index"].get(w[0], ()):
        if freq < 2:  # список отсортирован по частоте: дальше только слова, встреченные один раз, — на них не исправляем
            break
        if abs(len(cand) - len(w)) > limit or len(cand) < 4:  # «лает» не превращаем в «лет»
            continue
        if len(w) <= 5 and cand[-1] != w[-1]:  # в коротких словах опечатка не на краях: «пака» → «пока», но «маск» ≠ «маска»
            continue
        d = _dist(w, cand, limit)
        if d > limit:
            continue
        key = (d, -freq)
        if best_key is None or key < best_key:
            best, best_key = cand, key
    return best


def _clean(token):
    return re.sub(r"^[^\wа-яё]+|[^\wа-яё]+$", "", token.lower().replace("ё", "е"))


def _known_or_close(word):
    w = _clean(word)
    return bool(w) and re.fullmatch(r"[а-я\-]+", w) is not None and (known(w) or suggest(w) is not None)


def _is_english(token):
    w = re.sub(r"[^a-z']", "", token.lower())
    return bool(w) and (w in lex()["en"] or w.rstrip("s") in lex()["en"])


def _layout(text):
    """Неверная раскладка: вся фраза или отдельные слова. Возвращает текст (исправленный или прежний)."""
    words = text.split()
    if not words:
        return text
    lat = bool(_LAT.search(text))
    cyr = bool(_CYR.search(text))
    if lat and not cyr:
        latin_words = [w for w in words if _LAT.search(w)]
        conv = [w.translate(TO_RU) for w in latin_words]
        ru = sum(_known_or_close(c) for c in conv)
        en = sum(_is_english(w) for w in latin_words)
        if latin_words and ru * 2 >= len(latin_words) and ru > en:
            # настоящие английские слова (python, google…) оставляем как есть
            return " ".join(w if not _LAT.search(w) or (_is_english(w) and not _known_or_close(w.translate(TO_RU)))
                            else w.translate(TO_RU) for w in words)
        return text
    if cyr and not lat:
        conv = [w.translate(TO_EN) for w in words]
        en = sum(_is_english(c) for c in conv)
        ru = sum(_known_or_close(w) for w in words)
        if en * 2 >= len(words) and ru == 0:
            return " ".join(conv)
        return text
    # смешанный текст: латинские слова, которые на русской раскладке — известные русские слова
    out = []
    for w in words:
        if _LAT.search(w) and not _CYR.search(w) and not re.search(r"\d", w) and not _is_english(w):
            c = w.translate(TO_RU)
            if _known_or_close(c) and len(_clean(c)) >= 2:
                out.append(c)
                continue
        out.append(w)
    return " ".join(out)


def _typos(text):
    out = []
    first = True
    for token in re.split(r"(\s+)", text):
        m = re.fullmatch(r"([«\"'(]*)([А-Яа-яЁё]+)([.,!?:;»\"')]*)", token)
        if not m or not token.strip():
            out.append(token)
            continue
        pre, word, post = m.groups()
        fixed = None
        name_like = word[0].isupper() and not first
        if not name_like:
            fixed = suggest(word)
        if fixed:
            fixed = fixed.capitalize() if word[0].isupper() else fixed
            out.append(pre + fixed + post)
        else:
            out.append(token)
        first = bool(re.search(r"[.!?]$", token))
    return "".join(out)


def fix(text):
    """Исправить раскладку и опечатки. Возвращает (текст, что сделано: None | "layout" | "typos" | "both")."""
    if not text or len(text) > 600 or _RAW_RE.search(text):
        return text, None
    fixed = _layout(text.strip())
    layout = fixed != text.strip()
    if _RAW_RE.search(fixed):  # после раскладки стало командой с «сырым» текстом
        return fixed, "layout" if layout else None
    corrected = _typos(fixed) if _CYR.search(fixed) else fixed
    typos = corrected != fixed
    kind = "both" if layout and typos else "layout" if layout else "typos" if typos else None
    return (corrected if kind else text), kind
