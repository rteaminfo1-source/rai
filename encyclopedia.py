"""Энциклопедия Rai: ~10 000 важнейших тем из Википедии — отвечает без интернета.

Данные (encyclopedia.json) собирает GitHub: tools/build_encyclopedia.py, workflow «Знания Rai».
Понимает: «что такое фотосинтез», «кто такой Пушкин», «расскажи о Великой французской революции»,
«где находится Эверест», «Эйнштейн это кто», просто «Жираф», «какие разделы знаешь», «случайная тема»,
«темы раздела космос», «что было в этот день», «что было 12 апреля», «что сейчас популярно», «статья дня».
К теме — её картинка из Википедии. Тексты — из Википедии (CC BY-SA), источник указывается в каждом ответе.
GitHub обновляет энциклопедию каждый день: события, популярные темы.
"""

import datetime

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
_RANDOM_SECTION_RE = re.compile(r"(?:из|про|раздела|о)\s+(космос\w*|истори\w*|географи\w*|люд\w*|искусств\w*|науки?|технологи\w*|математик\w*|биологи\w*|росси\w*)", re.I)
_SECTION_RE = re.compile(r"(?:темы|статьи|список)\s+(?:из\s+)?(?:раздела|категории|про)\s+(.+?)[\s?!.]*$", re.I)
# Слова-приставки, которые не меняют тему: «расскажи кратко о Пушкине подробнее»
_NOISE = {nlp.stem(w) for w in "пожалуйста подробно подробнее кратко коротко вкратце немного вообще мне нам такое такой это".split()}

CAT_RU = {}  # английские подразделы списка важнейших статей → по-русски (заполнено в конце файла)

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
_MONARCH_RE = re.compile(r"^([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s+[IVX]+$")
_RULER_RE = re.compile(r"\b(?:император|императрица|король|королева|царь|царица|князь|княгиня|султан|фараон|папа\s+римский|"
                       r"правител|монарх|полководец)", re.I)


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
    # «Наполеон I», «Пётр I», «Елизавета II» → «Наполеон», «Пётр»: из тёзок победит самый известный
    m = _MONARCH_RE.match(base)
    if m:
        yield m.group(1), 1
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
    item = _data["items"][i]
    title, desc, cat, text = item[:4]
    section_no, cat_name = _data["cats"][cat]
    image = item[6] if len(item) > 6 else ""
    return {"title": title, "desc": desc, "section": _data["sections"][section_no], "cat": cat_ru(cat_name), "text": text,
            "image": image_url(image) if image else None}


def image_url(filename, width=640):
    """Картинка с Викисклада по имени файла (уменьшенная копия)."""
    return ("https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename.replace(" ", "_"))
            + f"?width={width}")


def page_url(title):
    return "https://ru.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))


def cat_ru(name):
    """Подразделы списка важнейших статей названы по-английски — переводим по частям («Writers / Russian»);
    «Chemistry: General» → «Химия — общее»."""
    if not name:
        return name
    out = []
    for part in name.split(" / "):
        part = re.sub(r"<[^>]+>", "", part).strip()
        general = re.search(r":\s*General$", part)
        base = re.sub(r":\s*General$", "", part)
        ru = CAT_RU.get(base, base)
        out.append(ru + (" — общее" if general else ""))
    # «Космос → Космос / …» — повтор раздела не нужен
    return " / ".join(dict.fromkeys(out))


def _is_person(i):
    """Человек: «Фамилия, Имя» или правитель с номером («Наполеон I», «Елизавета II»)."""
    title, desc = _data["items"][i][0], _data["items"][i][1]
    return bool(_PERSON_RE.match(title) or (_MONARCH_RE.match(title) and _RULER_RE.search(desc or _data["items"][i][3][:200])))


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
    url = page_url(t["title"])
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
    news = _data.get("news") or {}
    days = len(_data.get("days") or {})
    extra = (f"\n\nЕщё: «что было в этот день» ({days} дней истории)" if days else "") + \
            (f", «что сейчас популярно» (обновлено {news['date']})" if news.get("date") else "")
    return (f"## Энциклопедия Rai: {count():,} тем".replace(",", " ") +
            f" в {len(rows)} разделах и {len(_data['cats'])} подразделах\n\n| Раздел | Тем | Например |\n|---|---|---|\n" +
            "\n".join(rows) +
            "\n\nСпрашивайте: «что такое …», «кто такой …», «расскажи о …», «где находится …» или просто название. "
            "«Темы раздела история» — список, «случайная тема» — что-нибудь новое. Работает без интернета." + extra)


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
                    found.append({"title": t["title"], "text": t["text"], "url": page_url(t["title"])})
                    used.update(range(i, i + size))
            if len(found) >= limit:
                return found
    return found


def answer(text, explicit_only=False):
    """Текст ответа энциклопедии или None (см. reply)."""
    r = reply(text, explicit_only)
    return r["text"] if r else None


def reply(text, explicit_only=False):
    """Ответ энциклопедии: {"text", "photo": {"url", "title", "source"} или None} или None.
    explicit_only — только на прямой вопрос («что такое…», «кто такой…»)."""
    if not _data:
        return None
    special = day_events(text) or popular(text)
    if special:
        return {"text": special, "photo": None}
    t = find(text, explicit_only)
    if isinstance(t, str):
        return {"text": t, "photo": None}
    if not t:
        return None
    photo = {"url": t["image"], "title": t["title"], "source": page_url(t["title"])} if t["image"] else None
    return {"text": _render(t), "photo": photo}


def find(text, explicit_only=False):
    """Тема из вопроса (словарь _item), готовый текст (каталог, список раздела) или None."""
    if not _data:
        return None
    if _LIST_RE.search(text):
        return catalog()
    if _RANDOM_RE.search(text):
        m = _RANDOM_SECTION_RE.search(text)
        pool = range(count())
        if m:
            want = _key(m.group(1))
            secs = [s for s, name in enumerate(_data["sections"]) if want and want[0] in _key(name)]
            if secs:
                pool = [i for i, it in enumerate(_data["items"]) if _data["cats"][it[2]][0] in secs]
        return _item(random.choice(list(pool)))
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
        return lookup(subject, kind)
    if explicit_only:
        return None
    # Просто название темы: «Жираф», «Пётр Первый», «теория относительности»
    clean = text.strip(" \t\n?!.")
    if 0 < len(clean.split()) <= 6:
        return lookup(clean)
    return None


# ------------------------------------------------------------------ этот день, популярное, статья дня
_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
_DAY_RE = re.compile(r"(?:что\s+(?:было|произошло|случилось)|события|этот\s+день|в\s+этот\s+день|день\s+в\s+истории|"
                     r"какие\s+события)", re.I)
_DATE_RE = re.compile(r"\b(\d{1,2})\s+(" + "|".join(m[:3] for m in _MONTHS) + r")[а-я]*", re.I)
_POPULAR_RE = re.compile(r"(?:что|о\s+ч[её]м)\s+(?:сейчас\s+|сегодня\s+)?(?:популярн|обсужда|чита[ею]т|говорят|ищут)|"
                         r"популярн\w*\s+(?:сегодня|сейчас|за\s+день|темы|статьи)|что\s+нового\s+в\s+мире|тренды?\s+дня", re.I)
_FEATURED_RE = re.compile(r"стать[яюи]\s+дня|избранн\w+\s+стать", re.I)


def day_events(text, today=None):
    """«Что было в этот день», «что произошло 12 апреля», «события 9 мая»."""
    days = (_data or {}).get("days") or {}
    if not days or not _DAY_RE.search(text):
        return None
    today = today or datetime.date.today()
    m = _DATE_RE.search(text)
    if m:
        month = next(i for i, name in enumerate(_MONTHS, 1) if name.startswith(m.group(2).lower()[:3]))
        day = int(m.group(1))
    elif re.search(r"этот\s+день|сегодня|день\s+в\s+истории", text, re.I):
        month, day = today.month, today.day
    else:
        return None
    events = days.get(f"{month:02d}-{day:02d}")
    if not events:
        return None
    lines = [f"- **{y}** — {e}" for y, e in events[:10]]
    return (f"## {day} {_MONTHS[month - 1]} в истории\n\n" + "\n".join(lines) +
            "\n\n📚 По материалам [Википедии](https://ru.wikipedia.org/wiki/" + urllib.parse.quote(f"{day}_{_MONTHS[month - 1]}") + ") (CC BY-SA)")


def popular(text):
    """Что больше всего читают в Википедии (обновляется каждый день) и статья дня."""
    news = (_data or {}).get("news") or {}
    if _FEATURED_RE.search(text) and news.get("featured"):
        title, extract = news["featured"]
        return f"## Статья дня: {title}\n\n{extract}\n\n📚 [Читать в Википедии]({page_url(title)}) (CC BY-SA)"
    if not _POPULAR_RE.search(text) or not news.get("popular"):
        return None
    date = news.get("date") or ""
    try:
        d = datetime.date.fromisoformat(date)
        when = f"{d.day} {_MONTHS[d.month - 1]}"
    except ValueError:
        when = "вчера"
    rows = []
    for title, views, extract in news["popular"][:10]:
        short = extract.split(". ")[0][:160] if extract else ""
        rows.append(f"- **[{title}]({page_url(title)})** — {views:,} просмотров".replace(",", " ") + (f". {short}" if short else ""))
    return (f"## О чём читали {when}\n\nСамые читаемые статьи русской Википедии — я обновляю этот список каждый день:\n\n" +
            "\n".join(rows) + "\n\nСпросите про любую: «расскажи о …».")


# ------------------------------------------------------------------ вопросы: когда, где, сколько, почему, как
# «Когда родился Гагарин», «сколько лет прожил Пушкин», «где родился Наполеон», «какой высоты Эверест»,
# «почему Луна светит», «как работает интернет», «чем знаменит Тесла» — точный ответ из статьи о теме:
# даты жизни разбираются, а в остальном выбирается предложение, которое отвечает именно на этот вопрос.
_Q_RE = re.compile(
    r"^\s*(?:а\s+|и\s+|слушай,?\s+|скажи,?\s+|подскажи,?\s+|не\s+знаешь,?\s+|интересно,?\s+)?(?P<w>"
    r"когда|в\s+каком\s+(?:году|веке)|где|откуда|"
    r"сколько|какой\s+(?:высоты|длины|глубины|площади|величины|массы|ширины|толщины|возраст)|"
    r"какова?\s+(?:высота|длина|глубина|площадь|масса|население|температура|ширина|скорость|численность)|"
    r"какое\s+(?:население|расстояние)|"
    r"почему|зачем|отчего|для\s+чего|"
    r"как\s+(?:работает|работают|устроен[аоы]?|появил\w*|образ\w*|возник\w*|действует|получа\w*|умер\w*|погиб\w*)|"
    r"кем\s+(?:был|была|были|было|является|работал\w*)|чем\s+(?:знаменит\w*|известен|известна|известно|известны|прославил\w*))"
    r"\b\s*(?P<rest>.*?)[\s?!.]*$", re.I)
_SENT_RE = re.compile(r"(?<=[.!?])(?<![\s(][А-ЯЁA-Z]\.)(?<!\sг\.)(?<!\sвв\.)(?<!\sгг\.)\s+(?=[А-ЯЁA-Z«\"(])")
_CAUSE_RE = re.compile(r"\b(?:потому|поскольку|так\s+как|из-за|вследствие|благодаря|поэтому|причин\w*|в\s+результате|"
                       r"объясняется|связан\w*\s+с|за\s+сч[её]т|чтобы|для\s+того)\b", re.I)
_UNIT_RE = re.compile(r"\d[\d\s,.]*\s*(?:м|км|метр\w*|километр\w*|чел\w*|жител\w*|кг|тонн\w*|т|°|градус\w*|%|млн|млрд|тыс\w*|"
                      r"км²|км2|кв\.|га|лет|год\w*|световых|а\.\s*е\.|км/[чс]|м/с)\b", re.I)
_MONTH_GEN = "|".join(_MONTHS)
_Q_WORD_RE = re.compile(r"^(?:высот|длин|глубин|площад|насел|жител|масс|вес|температур|скорост|расстоян|численност|возраст|"
                        r"лет$|год|родил|рожд|умер|умир|погиб|скончал|прожил|жил|работа|устро|появил|возник|образова|"
                        r"находи|располож|основа|изобр|придума|открыл|знамени|извест|прославил|был|была|было|были|являе|"
                        r"сейчас|всего|примерно|на\s|в$|во$|на$|у$|с$|из$|до$|от$)")
_DATE = r"(?:около\s+|ок\.\s+)?(?:\d{1,2}(?:\s*\[\d{1,2}\])?\s+(?:" + _MONTH_GEN + r")(?:\s*\[[^\]]*\])?\s+)?\d{3,4}(?:\s*\[\d{3,4}\])?(?:\s*(?:года|г\.))?(?:\s+до\s+н\.\s*э\.)?"
_LIFE_RE = re.compile(r"(?<![\w\d])(?P<b>" + _DATE + r")(?:,\s*(?P<bp>[^—–;]+?))?\s+[—–]\s+(?P<d>" + _DATE + r")(?:,\s*(?P<dp>[^;]+?))?\s*$", re.I)
_BORN_RE = re.compile(r"(?:род\.|родил(?:ся|ась))\s*(?P<b>" + _DATE + r")(?:,\s*(?P<bp>[^;]+?))?\s*$", re.I)
_DATE_PART_RE = re.compile(r"^(?P<date>(?:около\s+|ок\.\s+)?(?:\d{1,2}\s+(?:" + _MONTH_GEN + r")\s*(?:\[[^\]]*\]\s*)?)?\d{3,4}(?:\s*\[[^\]]*\])?"
                           r"(?:\s*(?:года|г\.|до\s+н\.\s*э\.))?)\s*(?:,\s*(?P<place>.+))?$", re.I)
_MEASURE = {"высот": ("высот", "высок", "метр", " м"), "длин": ("длин", "протяж", "км"), "глубин": ("глубин",),
            "площад": ("площад", "км²", "км2"), "насел": ("насел", "жител", "чел"), "жител": ("насел", "жител", "чел"),
            "масс": ("масс", "вес", "кг", "тонн"), "температур": ("температур", "°", "градус"), "скорост": ("скорост", "км/", "м/с"),
            "расстоян": ("расстоян", "км", "световых"), "численност": ("численност", "насел", "чел"), "возраст": ("возраст", "лет")}


def _mentions(query, limit=2, kind=None, aliases=False):
    """Темы, названные в тексте (сначала длинные названия): [(номер темы, слова из текста)].
    kind="who" — при равных названиях предпочитать человека («Пушкин» — поэт, а не город Пушкино).
    aliases — одно слово может быть и другим именем темы («Эверест» → Джомолунгма)."""
    if not _data:
        return []
    words, raw = _key(query), _words(query)
    found, used = [], set()
    for size in range(min(6, len(words)), 0, -1):
        for i in range(len(words) - size + 1):
            if any(j in used for j in range(i, i + size)):
                continue
            hit = _best(tuple(words[i:i + size]), tuple(raw[i:i + size]), kind)
            if hit and (size > 1 or hit[0] <= (2 if aliases else 1)) and nlp.stem(raw[i]) not in nlp.GENERIC:
                if all(n != hit[1] for n, _ in found):
                    found.append((hit[1], set(raw[i:i + size])))
                    used.update(range(i, i + size))
            if len(found) >= limit:
                return found
    return found


_ABBR = {"англ", "лат", "нем", "фр", "франц", "греч", "др", "араб", "кит", "трад", "упр", "букв", "род", "ок", "см", "т", "е",
         "г", "гг", "в", "вв", "н", "э", "им", "св", "ст", "яп", "исп", "итал", "тиб", "палл", "санскр", "евр", "укр", "белор",
         "польск", "непальск", "перс", "тур", "инд", "хинди", "груз", "арм", "азерб", "каз", "тат", "башк", "шв", "норв", "фин",
         "венг", "чеш", "рум", "болг", "серб", "дат", "голл", "нидерл", "порт", "кор", "вьетн", "монг", "мн", "ед", "ч", "англо",
         "e", "g", "i", "vs", "пр", "проч"}


def _sentences(text):
    """Предложения: точка внутри скобок и после сокращений («англ.», «лат.», «т. е.», «г.») — не конец предложения."""
    out, cur, depth = [], [], 0
    text = text or ""
    for k, ch in enumerate(text):
        cur.append(ch)
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif ch in ".!?" and depth == 0:
            nxt = text[k + 1:k + 3]
            if not (nxt[:1] == " " and (nxt[1:2].isupper() or nxt[1:2] in "«\"(")) and k + 1 < len(text):
                continue
            word = re.search(r"([\wё]+)$", "".join(cur[:-1]))
            if ch == "." and word and (word.group(1).lower() in _ABBR or (len(word.group(1)) == 1 and word.group(1).isupper())):
                continue
            out.append("".join(cur).strip())
            cur = []
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return [x for x in out if x]


def _top_parens(text):
    """Первые скобки после названия — там у людей даты и места жизни (вложенные скобки убираем)."""
    start = text.find("(")
    if start < 0 or start > 160:
        return None
    depth, out = 0, []
    for ch in text[start:]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        elif depth == 1:
            out.append(ch)
    return re.sub(r"\s+([,)])", r"\1", re.sub(r"\s{2,}", " ", "".join(out))).strip()


def _parse_date(s):
    """«26 мая [6 июня] 1799» → (1799, 6, 6, «6 июня 1799 (26 мая по старому стилю)»); «1452» → (1452, None, None, «1452»)."""
    s = re.sub(r"\s*(?:года|г\.)$", "", s.strip())
    m = re.match(r"^(?:около\s+|ок\.\s+)?(\d{1,2})\s+(\w+)\s*\[(\d{1,2})\s+(\w+)(?:\s+(\d{3,4}))?\]\s*(\d{3,4})?(?:\s*\[(\d{3,4})\])?$", s)
    if m:
        d_old, m_old, d_new, m_new, y_in, y_out, y_br = m.groups()
        y_new = int(y_in or y_br or y_out)
        if m_new in _MONTHS:
            text = f"{d_new} {m_new} {y_new} (по старому стилю — {d_old} {m_old})"
            return y_new, _MONTHS.index(m_new) + 1, int(d_new), text
    m = re.match(r"^(?:около\s+|ок\.\s+)?(\d{1,2})\s*\[(\d{1,2})\]\s+(\w+)\s+(\d{3,4})$", s)
    if m and m.group(3) in _MONTHS:          # «6 [18] декабря 1878» — старый [новый] стиль в одном месяце
        d_old, d_new, mon, y = m.groups()
        return int(y), _MONTHS.index(mon) + 1, int(d_new), f"{d_new} {mon} {y} (по старому стилю — {d_old} {mon})"
    m = re.match(r"^(?:около\s+|ок\.\s+)?(?:(\d{1,2})\s+(\w+)\s+)?(\d{3,4})(\s+до\s+н\.\s*э\.)?$", s)
    if not m:
        return None
    d, mon, y, bc = m.groups()
    if mon and mon not in _MONTHS:
        return None
    text = f"{d} {mon} {y}" if mon else y
    if bc:
        return -int(y), None, None, text + " до н. э."
    return int(y), (_MONTHS.index(mon) + 1 if mon else None), (int(d) if d else None), text


def life(title_or_text):
    """Даты жизни человека из начала статьи: {"born", "born_place", "died", "died_place", "age", "alive"} или None.
    Ищет «дата, место — дата, место» (или «род. дата, место») в первых скобках: перед датами бывает что угодно —
    «нем. Albert Einstein», «фамилия при рождении — Джугашвили; …»."""
    inner = _top_parens(title_or_text)
    if not inner:
        return None
    m, alive = None, False
    for part in reversed(inner.split(";")):        # даты — обычно в последней части после «;»
        m = _LIFE_RE.search(part.strip())
        if m:
            break
        m = _BORN_RE.search(part.strip())
        if m:
            alive = True
            break
    if not m:
        return None
    b = _parse_date(m.group("b"))
    if not b:
        return None
    out = {"born": b, "born_place": (m.group("bp") or "").strip(" ,"), "died": None, "died_place": "", "alive": alive}
    if not alive:
        out["died"] = _parse_date(m.group("d"))
        out["died_place"] = (m.group("dp") or "").strip(" ,")
        if not out["died"]:
            return None
    end = out["died"]
    if alive:
        t = datetime.date.today()
        end = (t.year, t.month, t.day, "")
    if b[0] > 0 and end[0] > 0:
        age = end[0] - b[0]
        if b[1] and end[1] and (end[1], end[2] or 1) < (b[1], b[2] or 1):
            age -= 1
        out["age"] = age if (b[1] and end[1]) else f"{age - 1}–{age}"
    else:
        out["age"] = None
    return out


_FOREIGN_RE = re.compile(r"\s*\((?=[^()]*\b(?:англ|лат|нем|фр|франц|греч|др\.-греч|араб|кит|тиб|яп|исп|итал|непальск|МФА|копт|егип|"
                         r"перс|санскр|евр|ивр|кор|вьетн|монг|тур|груз|арм|польск|чеш|венг|шв|норв|фин|порт|голл|нидерл|"
                         r"укр|белор|каз|узб|тат|хинди)\b)[^()]*(?:\([^()]*\)[^()]*)*\)")


def tidy(sentence):
    """Без скобок с написанием на других языках: «Джомолунгма (тиб. …, кит. …) — …» → «Джомолунгма — …»."""
    return re.sub(r"\s{2,}", " ", _FOREIGN_RE.sub("", sentence)).replace(" ,", ",").strip()


def _years(n):
    if isinstance(n, str):
        return n + " лет"
    tail = "лет" if 11 <= n % 100 <= 14 else {1: "год", 2: "года", 3: "года", 4: "года"}.get(n % 10, "лет")
    return f"{n} {tail}"


def _short_name(title):
    if _PERSON_RE.match(title):
        base = re.sub(r"\s*\([^)]*\)$", "", title)
        last, first = [x.strip() for x in base.split(",", 1)]
        return f"{first.split()[0]} {last}"
    return re.sub(r"\s*\([^)]*\)$", "", title)


def _life_answer(word, rest, t):
    """Ответ про даты жизни: когда родился/умер, где родился/умер, сколько лет прожил / сколько лет сейчас."""
    info = life(t["text"])
    if not info:
        return None
    name = _short_name(t["title"])
    low = rest.lower()
    died_q = re.search(r"\b(?:умер|умерла|погиб|погибла|скончал\w*|не\s+стало|смерт)", low) or re.match(r"как\s+(?:умер|погиб)", word)
    born_q = re.search(r"\b(?:родил\w*|рожд|появил\w*\s+на\s+свет)", low)
    age_q = re.match(r"сколько", word) and re.search(r"\b(?:лет|год)", low)
    if age_q:
        if info["age"] is None:
            return None
        if info["alive"]:
            return f"**{name}** родил{_fem(t, 'ась', 'ся')} {info['born'][3]} — сейчас {_fem(t, 'ей', 'ему')} **{_years(info['age'])}**."
        return (f"**{name}** прожил{_fem(t)} **{_years(info['age'])}**: {info['born'][3]} — {info['died'][3]}."
                if info["died"] else None)
    if word.startswith("когда") or word.startswith("в каком"):
        if died_q:
            if info["alive"]:
                return f"{name} жив{_fem(t, 'а')} — родил{_fem(t, 'ась', 'ся')} {info['born'][3]}."
            return f"**{name}** умер{_fem(t, 'ла')} **{info['died'][3]}**" + (f" ({info['died_place']})." if info["died_place"] else ".") if info["died"] else None
        if born_q or not rest.strip():
            return f"**{name}** родил{_fem(t, 'ась', 'ся')} **{info['born'][3]}**" + (f" ({info['born_place']})." if info["born_place"] else ".")
        return None
    if word in ("где", "откуда"):
        if died_q and info["died_place"]:
            return f"Место смерти — **{info['died_place']}** ({name}, {info['died'][3]})."
        if (born_q or word == "откуда") and info["born_place"]:
            return f"Место рождения — **{info['born_place']}** ({name}, {info['born'][3]})."
    return None


def _fem(t, fem="а", masc=""):
    """Окончание по полу: в описании женщины первое слово — «русская», «советская», «американская»…
    или она императрица, королева, царица, княгиня."""
    desc = t.get("desc") or ""
    first = desc.split(" ", 1)[0]
    head = desc + " " + (t.get("text") or "")[:300]
    female = re.fullmatch(r"\w+(?:ая|яя)", first) or re.search(r"\b(?:[Ии]мператрица|[Кк]оролева|[Цц]арица|[Кк]нягиня|[Гг]ерцогиня|"
                                                             r"[Пп]ринцесса|[Сс]амодержица)\b", head)
    return fem if female else masc


def _score(sentence, kind, content, measure, idx):
    low = sentence.lower()
    stems = {nlp.stem(w) for w in re.findall(r"[а-яёa-z0-9]+", low)}
    s = len(content & stems) * 2.0
    if kind == "when":
        s += 2.5 if re.search(r"\b(?:1[0-9]{3}|20[0-9]{2}|[1-9][0-9]{2})\b|\b[IVX]+\s+век", sentence) else 0
        s += 1 if re.search(_MONTH_GEN, low) else 0
    elif kind == "num":
        s += 2 if re.search(r"\d", sentence) else 0
        s += 1.5 if _UNIT_RE.search(sentence) else 0
        if measure:
            s += 3 if any(m in low for m in measure) else -2
    elif kind == "where":
        s += 2 if re.search(r"\b(?:располож\w*|находит\w*|расположен\w*|протека\w*|в\s+[А-ЯЁ]\w+|на\s+[А-ЯЁ]\w+|"
                            r"столиц\w*|страны|материк\w*|континент\w*|океан\w*|регион\w*)", sentence) else 0
    elif kind == "why":
        s += 3 if _CAUSE_RE.search(sentence) else 0
    elif kind in ("how", "who"):
        s += 2 if idx == 0 else 0
    return s - idx * 0.15


def _kind(word):
    w = word.lower()
    if w.startswith(("когда", "в каком")):
        return "when"
    if w in ("где", "откуда"):
        return "where"
    if w.startswith(("сколько", "какой", "какова", "каков", "какое")):
        return "num"
    if w in ("почему", "зачем", "отчего", "для чего"):
        return "why"
    if w.startswith("как"):
        return "how"
    return "who"


def question(text):
    """Ответ на вопрос о теме энциклопедии: {"text", "photo", "title"} или None (тогда отвечает кто-то другой)."""
    if not _data:
        return None
    m = _Q_RE.match(text or "")
    if not m or not m.group("rest").strip():
        return None
    word, rest = re.sub(r"\s+", " ", m.group("w").lower()), m.group("rest")
    about_life = bool(re.search(r"\b(?:родил\w*|рожд\w*|умер\w*|погиб\w*|скончал\w*|прожил\w*|жил|жила)\b", rest, re.I)
                      or re.match(r"кем|чем|как\s+(?:умер|погиб)", word))
    # тема — не слова вопроса («высоты», «родился», «жителей»), и имена собственные важнее: «какой высоты Эверест»
    subject = " ".join(w for w in re.findall(r"[\w-]+", rest) if not _Q_WORD_RE.match(w.lower())) or rest
    who = "who" if about_life or word.startswith(("сколько", "кем", "чем")) else None
    hits = _mentions(subject, limit=3, kind=who) or _mentions(subject, limit=3, kind=who, aliases=True)
    if not hits:
        return None
    proper = {nlp.normalize(w) for w in re.findall(r"\b[А-ЯЁA-Z][\w-]*", subject)}
    n, topic_words = next((h for h in hits if h[1] & proper), hits[0])
    t = _item(n)
    kind = _kind(word)
    answer = life_answer = _life_answer(word, rest, t) if _is_person(n) else None
    if not answer and about_life and not re.match(r"кем|чем", word):
        if not _is_person(n):
            return None          # «когда умер Эверест» — не про человека, не выдумываем
        answer = tidy(_sentences(t["text"])[0])   # даты не разобрались — первое предложение, где они обычно и есть
    if not answer:
        # кем был / как умер у человека без дат — не отвечаем общим текстом
        content = {nlp.stem(w) for w in _words(rest) if w not in topic_words} - nlp.GENERIC - nlp.FILLER - {nlp.stem(w) for w in nlp.STOPWORDS}
        content -= {nlp.stem(w) for w in ("было", "была", "был", "есть", "это", "всего", "примерно", "лет", "год")} if kind != "num" else set()
        measure = None
        for key, signs in _MEASURE.items():
            if key in word or any(nlp.stem(w).startswith(key) for w in _words(rest)):
                measure = signs
                break
        if kind == "num" and not measure and not content:
            return None
        sents = _sentences(t["text"])
        if not sents:
            return None
        ranked = sorted(((_score(x, kind, content, measure, i), i) for i, x in enumerate(sents)), reverse=True)
        best, i = ranked[0]
        need = {"when": 2.5, "num": 3.5, "where": 2.0, "why": 3.0, "how": 1.5, "who": 1.5}[kind]
        if best < need:
            return None
        if kind in ("how", "who"):
            answer = tidy(" ".join(sents[:2]))
        else:
            answer = tidy(sents[i])
            name = _short_name(t["title"])
            if i and not set(_key(name)) & set(_key(answer)):   # «Высота — 8848 м.» — добавим, о чём речь
                answer = f"**{name}:** {answer}"
    url = page_url(t["title"])
    photo = {"url": t["image"], "title": t["title"], "source": url} if t["image"] else None
    body = f"{answer}\n\n📚 Из статьи «{t['title']}» · [Википедия]({url}) (CC BY-SA)"
    return {"text": body, "photo": photo, "title": t["title"], "life": bool(life_answer)}


# ------------------------------------------------------------------ подразделы по-русски
CAT_RU.update({
    "Sexuality and gender": "Сексуальность и гендер",
    "Machinery and tools": "Машины и инструменты",
    "Abrahamic religions": "Авраамические религии",
    "Academic journals": "Научные журналы",
    "Actors": "Актёры",
    "Africa": "Африка",
    "Agriculture": "Сельское хозяйство",
    "Agronomy and horticulture": "Агрономия и садоводство",
    "Air": "Воздушный транспорт",
    "Algebra": "Алгебра",
    "Americas": "Америка",
    "Ammunition": "Боеприпасы",
    "Analytical chemistry": "Аналитическая химия",
    "Anatomy and morphology": "Анатомия и морфология",
    "Ancient": "Древний мир",
    "Animal": "Животные",
    "Animal husbandry": "Животноводство",
    "Animal ontogeny": "Развитие животных",
    "Animal reproduction": "Размножение животных",
    "Animal-powered transport": "Гужевой транспорт",
    "Animals": "Животные",
    "Animators and puppeteers": "Аниматоры и кукольники",
    "Anthropology": "Антропология",
    "Architecture": "Архитектура",
    "Armour": "Доспехи",
    "Artillery and siege": "Артиллерия и осадные орудия",
    "Arts": "Искусство",
    "Asia": "Азия",
    "Astronomical objects": "Астрономические объекты",
    "Astronomy": "Астрономия",
    "Atomic, molecular and optical physics": "Атомная, молекулярная и оптическая физика",
    "Auxiliary historical sciences": "Вспомогательные исторические дисциплины",
    "Aviation": "Авиация",
    "Banking and finance": "Банки и финансы",
    "Basic concepts": "Основные понятия",
    "Basics": "Основы",
    "Biochemistry and molecular biology": "Биохимия и молекулярная биология",
    "Biological processes and physiology": "Биологические процессы и физиология",
    "Biological reproduction": "Размножение",
    "Biology": "Биология",
    "Biology and health sciences": "Биология и медицина",
    "Biotechnology": "Биотехнологии",
    "Bodies of water": "Водоёмы",
    "Botany": "Ботаника",
    "Building materials": "Строительные материалы",
    "Buildings and infrastructure": "Здания и инфраструктура",
    "Business and economics": "Бизнес и экономика",
    "Businesspeople": "Предприниматели",
    "Calculus and analysis": "Математический анализ",
    "Cartography": "Картография",
    "Celestial mechanics and astrometry": "Небесная механика и астрометрия",
    "Cell biology": "Клеточная биология",
    "Cell processes": "Процессы в клетке",
    "Cellular division": "Деление клеток",
    "Chemical bonds": "Химические связи",
    "Chemical reactions": "Химические реакции",
    "Chemical substances": "Химические вещества",
    "Chemistry": "Химия",
    "Cinema by country": "Кино по странам",
    "Cities": "Города",
    "Clothing and fashion": "Одежда и мода",
    "Colonial empires": "Колониальные империи",
    "Color": "Цвет",
    "Comedians": "Комики",
    "Companies": "Компании",
    "Components": "Компоненты",
    "Computer hardware": "Компьютерное железо",
    "Computer science": "Информатика",
    "Computer scientists": "Учёные-информатики",
    "Computer software": "Программное обеспечение",
    "Computing and information technology": "Компьютеры и ИТ",
    "Concepts": "Понятия",
    "Concepts and forms": "Понятия и формы",
    "Condensed matter physics": "Физика конденсированного состояния",
    "Continents": "Континенты",
    "Cooking and eating": "Кулинария и еда",
    "Cooking, food and drink": "Кулинария, еда и напитки",
    "Countries": "Страны",
    "Countries and other regions": "Страны и регионы",
    "Crewed spacecraft": "Пилотируемые космические корабли",
    "Crime": "Преступность",
    "Criminals": "Преступники",
    "Cryptography": "Криптография",
    "Cuisine": "Кухня",
    "Cultural venues": "Культурные места",
    "Culture": "Культура",
    "Dancers and choreographers": "Танцоры и хореографы",
    "Data storage": "Хранение данных",
    "Deserts": "Пустыни",
    "Development": "Развитие",
    "Devices": "Устройства",
    "Dharmic religions": "Дхармические религии",
    "Diagnostic technologies": "Диагностика",
    "Directors": "Режиссёры",
    "Directors, producers and screenwriters": "Режиссёры, продюсеры и сценаристы",
    "Disciplines": "Дисциплины",
    "Discrete mathematics": "Дискретная математика",
    "Drinks": "Напитки",
    "Drugs and pharmacology": "Лекарства и фармакология",
    "Early modern": "Раннее Новое время",
    "Earth": "Земля",
    "Earth science": "Науки о Земле",
    "Earth science and physical geography": "Науки о Земле и физическая география",
    "Eastern folklore": "Восточный фольклор",
    "Eastern religions": "Восточные религии",
    "Ecology": "Экология",
    "Economists": "Экономисты",
    "Education": "Образование",
    "Educational institutions": "Учебные заведения",
    "Electromagnetism": "Электромагнетизм",
    "Electronics": "Электроника",
    "Emotions and traits": "Эмоции и черты характера",
    "Employment": "Работа и занятость",
    "Energy and fuel": "Энергия и топливо",
    "Engineering": "Инженерия",
    "Entertainers": "Артисты",
    "Entertainment": "Развлечения",
    "Equipment": "Снаряжение",
    "Ethnic groups": "Народы",
    "Ethnology": "Этнология",
    "Ethology": "Этология",
    "Europe": "Европа",
    "Europe and Russia": "Европа и Россия",
    "Evolution": "Эволюция",
    "Explorers": "Путешественники и исследователи",
    "Explosive weapons": "Взрывчатое оружие",
    "Fabrics and fibers": "Ткани и волокна",
    "Family and kinship": "Семья и родство",
    "Family members": "Члены семьи",
    "Family, kinship and interpersonal relationships": "Семья, родство и отношения",
    "Festivals, holidays, and observances": "Праздники и памятные дни",
    "Fictional and legendary characters": "Вымышленные и легендарные персонажи",
    "Film and television": "Кино и телевидение",
    "Film and television festival and awards": "Кинофестивали и премии",
    "Film and television genres": "Жанры кино и телевидения",
    "Film, television, and games": "Кино, телевидение и игры",
    "Filmmaking": "Кинопроизводство",
    "Food types": "Виды еды",
    "Food, water and health": "Еда, вода и здоровье",
    "Forests": "Леса",
    "Forms": "Формы",
    "Forms of government": "Формы правления",
    "Fortification": "Фортификация",
    "Fungi": "Грибы",
    "Fungus": "Грибы",
    "Furniture and interior design": "Мебель и интерьер",
    "Galactic astronomy and extragalactic astronomy": "Галактики и внегалактическая астрономия",
    "Genetics and taxonomy": "Генетика и систематика",
    "Geometry": "Геометрия",
    "Governmental organizations": "Государственные организации",
    "Ground-based observatories": "Наземные обсерватории",
    "Groups": "Группы",
    "Health and fitness": "Здоровье и фитнес",
    "Health, medicine and disease": "Здоровье, медицина и болезни",
    "Historians and archaeologists": "Историки и археологи",
    "Historical cities": "Исторические города",
    "History by continent and region": "История по континентам и регионам",
    "History by country": "История по странам",
    "History by subject matter": "История по темам",
    "History of art": "История искусства",
    "History of games and sport": "История игр и спорта",
    "History of philosophy and religion": "История философии и религии",
    "History of science and technology": "История науки и техники",
    "History of society and the social sciences": "История общества и общественных наук",
    "Hosts and performers": "Ведущие и исполнители",
    "Household items": "Предметы быта",
    "Housing": "Жильё",
    "Ideology and political theory": "Идеологии и политическая теория",
    "Imaging": "Визуализация",
    "Incendiary weapons": "Зажигательное оружие",
    "Individual sports": "Индивидуальные виды спорта",
    "Industry": "Промышленность",
    "Infrastructure": "Инфраструктура",
    "Infrastructure by type": "Инфраструктура по видам",
    "Institutions and professions": "Учреждения и профессии",
    "International organizations": "Международные организации",
    "Internet": "Интернет",
    "Internet media": "Интернет-СМИ",
    "Interpersonal relations": "Отношения между людьми",
    "Interpersonal relationships": "Отношения между людьми",
    "Inventors and engineers": "Изобретатели и инженеры",
    "Islands": "Острова",
    "Issues": "Проблемы общества",
    "Jazz": "Джаз",
    "Journalists": "Журналисты",
    "Land relief": "Рельеф",
    "Language": "Язык",
    "Language families": "Языковые семьи",
    "Law": "Право",
    "Libraries": "Библиотеки",
    "Linguists": "Лингвисты",
    "Literature": "Литература",
    "Literature and drama": "Литература и драматургия",
    "Literatures by language and area": "Литература по языкам и регионам",
    "Machinery": "Машины и механизмы",
    "Magazines": "Журналы",
    "Maritime transport": "Морской транспорт",
    "Marriage and parenting": "Брак и воспитание детей",
    "Mass media": "СМИ",
    "Material and chemical": "Материалы и химия",
    "Mathematicians": "Математики",
    "Measurement": "Измерения",
    "Measurement systems": "Системы мер",
    "Mechanics": "Механика",
    "Media and communication": "СМИ и коммуникации",
    "Medical technology": "Медицинская техника",
    "Medicine": "Медицина",
    "Melee weapons": "Холодное оружие",
    "Metallurgy": "Металлургия",
    "Military": "Военное дело",
    "Military aviation": "Военная авиация",
    "Military leaders and theorists": "Полководцы и военные теоретики",
    "Military technology": "Военная техника",
    "Modern": "Новейшее время",
    "Morbidity": "Болезни",
    "Mountain peaks": "Горные вершины",
    "Music": "Музыка",
    "Music genres and forms": "Музыкальные жанры и формы",
    "Musical instruments": "Музыкальные инструменты",
    "Musicians and composers": "Музыканты и композиторы",
    "Mythology": "Мифология",
    "Natural disasters": "Стихийные бедствия",
    "Naval warfare": "Морская война",
    "Navigation": "Навигация",
    "Navigation and timekeeping": "Навигация и измерение времени",
    "Networks": "Сети",
    "Newspapers": "Газеты",
    "Non-Western art": "Незападное искусство",
    "Non-Western art music": "Незападная академическая музыка",
    "Non-governmental organizations": "Негосударственные организации",
    "Nuclear physics": "Ядерная физика",
    "Oceania": "Океания",
    "Operating systems": "Операционные системы",
    "Optical instruments": "Оптические приборы",
    "Optical technology": "Оптические технологии",
    "Optics": "Оптика",
    "Organelles and other cell parts": "Органеллы и части клетки",
    "Organisms": "Организмы",
    "Other": "Другое",
    "Other eukaryotes": "Другие эукариоты",
    "Other hydrologic features": "Другие водные объекты",
    "Other religions": "Другие религии",
    "Other visual arts": "Другие изобразительные искусства",
    "Others": "Другие",
    "Parks and preserves": "Парки и заповедники",
    "Particle physics": "Физика элементарных частиц",
    "Peninsulas": "Полуострова",
    "Performing arts": "Исполнительские искусства",
    "Philosophers": "Философы",
    "Philosophers, historians, political and social scientists": "Философы, историки, политологи и социологи",
    "Philosophical branches, approaches and concepts": "Разделы, подходы и понятия философии",
    "Philosophical schools and traditions": "Философские школы и традиции",
    "Philosophy": "Философия",
    "Philosophy by region and period": "Философия по регионам и эпохам",
    "Physical cosmology": "Космология",
    "Physical geography": "Физическая география",
    "Physics": "Физика",
    "Planetary science": "Планетология",
    "Plant anatomy": "Анатомия растений",
    "Plant cells": "Клетки растений",
    "Plant reproduction": "Размножение растений",
    "Plants": "Растения",
    "Political writers": "Политические писатели",
    "Politicians and leaders": "Политики и правители",
    "Politics": "Политика",
    "Politics and government": "Политика и государство",
    "Popular music": "Популярная музыка",
    "Post-classical": "Средние века",
    "Pre-modern figures": "Деятели до Нового времени",
    "Prehistory": "Доисторическая эпоха",
    "Preparation and serving": "Приготовление и подача",
    "Producers and executives": "Продюсеры и руководители",
    "Programming": "Программирование",
    "Programs": "Программы",
    "Projectile weapons": "Метательное и стрелковое оружие",
    "Prokaryotes": "Прокариоты",
    "Psychologists": "Психологи",
    "Psychology": "Психология",
    "Psychology schools": "Школы психологии",
    "Rebels, revolutionaries and activists": "Бунтари, революционеры и активисты",
    "Regions and country subdivisions": "Регионы и административные единицы",
    "Religion and spirituality": "Религия и духовность",
    "Religious figures": "Религиозные деятели",
    "Research methods": "Методы исследования",
    "Residential and housing units": "Жилые помещения",
    "Road transport": "Автомобильный транспорт",
    "Rooms and spaces": "Комнаты и помещения",
    "Science basics": "Основы науки",
    "Scientists, inventors and mathematicians": "Учёные, изобретатели и математики",
    "Separation processes": "Процессы разделения",
    "Services and institutions": "Службы и учреждения",
    "Social scientists": "Обществоведы",
    "Social status": "Социальный статус",
    "Societal adaptations": "Общественные адаптации",
    "Society": "Общество",
    "Society and social sciences": "Общество и общественные науки",
    "Sociology": "Социология",
    "Space": "Космос",
    "Specific documents": "Документы",
    "Specific films": "Фильмы",
    "Specific languages": "Языки",
    "Specific musical works": "Музыкальные произведения",
    "Specific structures": "Сооружения",
    "Specific television shows": "Телепередачи",
    "Specific works": "Произведения",
    "Specific works of fiction": "Художественные произведения",
    "Specific works of nonfiction": "Документальные произведения",
    "Specific works of poetry": "Поэтические произведения",
    "Sports": "Спорт",
    "Sports and recreation": "Спорт и отдых",
    "Sports figures": "Спортсмены",
    "Stages of life": "Этапы жизни",
    "State structure and administration": "Государственное устройство и управление",
    "Statistics and probability": "Статистика и теория вероятностей",
    "Stellar astronomy": "Звёздная астрономия",
    "Styles": "Стили",
    "Subjects": "Темы",
    "Superheroes": "Супергерои",
    "Team sports": "Командные виды спорта",
    "Techniques": "Техники",
    "Technology": "Технологии",
    "Television": "Телевидение",
    "Textiles": "Текстиль",
    "Thermodynamics": "Термодинамика",
    "Timekeeping": "Измерение времени",
    "Tools": "Инструменты",
    "Trains": "Поезда",
    "Transport": "Транспорт",
    "Transportation": "Транспорт",
    "Uncrewed spacecraft": "Беспилотные космические аппараты",
    "United Nations organizations": "Организации ООН",
    "Units of measurement": "Единицы измерения",
    "Urban studies and planning": "Урбанистика и градостроительство",
    "User interface": "Пользовательский интерфейс",
    "Visual artists": "Художники",
    "Visual arts": "Изобразительное искусство",
    "War and military": "Война и армия",
    "Warfare by type": "Виды военных действий",
    "Wars by type": "Войны по видам",
    "Water": "Вода",
    "Waves": "Волны",
    "Weapons of mass destruction": "Оружие массового поражения",
    "Western art music": "Западная академическая музыка",
    "Western folklore": "Западный фольклор",
    "Western painters and illustrators": "Западные художники и иллюстраторы",
    "Writers": "Писатели",
    "Writing systems": "Системы письма",
    "Zoology": "Зоология",
})


load()
