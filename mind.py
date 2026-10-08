"""Разум Rai — собственное мышление движка, без нейросети.

Как Rai думает над вопросом:
  1. Понимает вопрос: что спрашивают (почему, как устроено, как сделать, когда, где, сколько, список, совет,
     что это, объясни), о какой теме и что именно в ней важно («почему небо *голубое*»).
  2. Составляет план: какие запросы нужны и где искать.
  3. Ищет: своя энциклопедия, глубокие знания (статьи целиком, deep.py), словарь, затем Википедия целиком,
     поиск в интернете и чтение найденных страниц (через посредник на сайте).
  4. Читает: делит тексты на предложения и оценивает каждое — совпадение слов и смысла (модель смыслов Rai,
     sense.py), признаки ответа нужного типа (причина, дата, число, место, шаги), надёжность источника.
  5. Отвечает: главное — сначала, подробности — без повторов, со ссылками на источники.
  6. Проверяет себя: есть ли в ответе причина / дата / число, покрыты ли слова вопроса, сходятся ли числа
     в разных источниках. Слабо — ищет ещё раз другими словами.
Ход мыслей виден под ответом («Как Rai думал»).
"""

import re

import deep
import encyclopedia
import net
import nlp
import online
import sense

# ------------------------------------------------------------------ уровни размышления
# Выбираются внизу чата (как модель): чем выше уровень, тем больше Rai ищет, читает и перепроверяет.
# web — искать в интернете; budget — сколько запросов в сеть; read — сколько страниц прочитать целиком;
# rounds — сколько дополнительных кругов поиска, если ответ слабый; sentences — сколько фактов в ответе;
# depth 2 — разбор по разделам статьи.
LEVELS = {
    "low": {"label": "Low", "web": False, "budget": 0, "read": 0, "rounds": 0, "sentences": 3, "depth": 1,
            "about": "мгновенно, только своя база знаний"},
    "medium": {"label": "Medium", "web": True, "budget": 4, "read": 1, "rounds": 1, "sentences": 5, "depth": 1,
               "about": "своя база + Википедия и поиск"},
    "high": {"label": "High", "web": True, "budget": 7, "read": 2, "rounds": 1, "sentences": 6, "depth": 1,
             "about": "читает найденные страницы, перепроверяет"},
    "extra": {"label": "Extra", "web": True, "budget": 11, "read": 3, "rounds": 2, "sentences": 8, "depth": 2,
              "about": "несколько кругов поиска, разбор по разделам"},
    "code": {"label": "Code", "web": True, "budget": 7, "read": 2, "rounds": 1, "sentences": 6, "depth": 1,
             "about": "сначала код: пишет программу и проверяет её запуском"},
    "ultra": {"label": "Ultra", "web": True, "budget": 16, "read": 5, "rounds": 3, "sentences": 10, "depth": 2,
              "about": "максимум: много источников, сверка, подробный отчёт"},
}
DEFAULT_LEVEL = "medium"


def level_of(name):
    return LEVELS.get((name or "").lower()) or LEVELS[DEFAULT_LEVEL]


# ------------------------------------------------------------------ понять вопрос

_FILLER_RE = re.compile(r"^\s*(?:(?:а|и|ну|так|вот|слушай|скажи(?:те)?|подскажи(?:те)?|интересно|не\s+знаешь|ты\s+знаешь|"
                        r"знаешь|рай|rai|пожалуйста|привет|короче|хочу\s+знать|хочу\s+понять|мне\s+интересно)[,!\s]+)+", re.I)
_THINK_RE = re.compile(r"^\s*(?:подумай|порассуждай|поразмышляй|исследуй|изучи|проанализируй|разберись|разбери|"
                       r"найди\s+и\s+объясни|проверь\s+и\s+объясни)(?:те)?\b[,:\s]*(?:(?:и|а\s+потом|потом)\s+"
                       r"(?:скажи|ответь|объясни)[,:\s]*)?(?:(?:над\s+тем|о\s+том|в\s+том)[,\s]*)?(?:(?:вопрос|тем[аеуы])[:\s]+)?", re.I)
_EXPLAIN_RE = re.compile(r"^\s*(?:объясни|разъясни|растолкуй|расскажи|опиши|поясни)(?:те)?(?:\s+(?:мне|нам|пожалуйста|"
                         r"подробно|подробнее|детально|развёрнуто|развернуто|простыми\s+словами|понятно|кратко|коротко|"
                         r"по\s+шагам|пошагово|всё|все))*[,:\s]+(?:(?:о|об|обо|про)\s+)?", re.I)
_DEPTH_RE = re.compile(r"(?<![а-яё])(?:подробн\w*|детальн\w*|развёрнут\w*|развернут\w*|глубоко|полностью|по\s+шагам|пошагово|"
                       r"вс[её]\s+(?:о|об|про))(?![а-яё])", re.I)
_SIMPLE_RE = re.compile(r"простыми\s+словами|для\s+(?:реб[её]нка|чайника|новичка|школьника)|понятным\s+языком|"
                        r"(?<![а-яё])(?:кратко|коротко|в\s+двух\s+словах)(?![а-яё])", re.I)

_INF = r"\w+(?:ть|ться|чь|чься|сти|стись)"
_KINDS = [
    ("why", r"(?:почему|зачем|отчего|по\s+как\w+\s+причин\w*|из-за\s+чего|в\s+ч[её]м\s+причин\w*|для\s+чего|с\s+какой\s+целью|"
            r"какова\s+причина|какие\s+причины|что\s+вызывает)"),
    ("advice", r"(?:что\s+делать|как\s+быть|стоит\s+ли|нужно\s+ли|надо\s+ли|можно\s+ли|посоветуй|порекомендуй|что\s+выбрать|"
               r"как\s+лучше|что\s+лучше|какой\s+лучше|какую\s+лучше|какое\s+лучше)"),
    ("howto", r"как\s+(?:(?:мне|можно|нужно|надо|правильно|лучше|быстро|быстрее|легко|самому|самостоятельно|дома|в\s+домашних\s+условиях)\s+)*"
              + _INF + r"(?![а-яё])"),
    ("num", r"(?:сколько|как(?:ой|ая|ое|ова|ов|ово)\s+(?:высот|длин|глубин|площад|масс|вес|температур|скорост|расстоян|населен|"
            r"численност|возраст|размер|диаметр|радиус|объ[её]м|мощност|стоимост|цен)\w*|как\s+(?:далеко|долго|высоко|глубоко|быстро)(?![а-яё]))"),
    ("how", r"(?:как|каким\s+образом)\s+(?!(?:дела|ты|вы|тебя|вас|тебе|вам|зовут|жизнь|настроение|сам|сама|поживаешь|делишки)(?![а-яё]))"),
    ("when", r"(?:когда|в\s+каком\s+(?:году|веке|месяце)|какого\s+числа|в\s+какое\s+время|с\s+какого\s+(?:года|времени))(?![а-яё])"),
    ("where", r"(?:где|откуда|куда|в\s+какой\s+стране|в\s+каком\s+(?:городе|месте|регионе))(?![а-яё])"),
    ("list", r"(?:какие\s+(?:бывают|есть|существуют|основные|главные|виды|типы)|назови|перечисли|список|виды|типы|разновидности|примеры)(?![а-яё])"),
    ("what", r"(?:что\s+такое|что\s+это\s+(?:такое|за)|что\s+значит|что\s+означает|что\s+за|что\s+представляет\s+собой|"
             r"в\s+ч[её]м\s+(?:суть|смысл))(?![а-яё])"),
    ("who", r"кто(?![а-яё])"),
    ("which", r"(?:какой|какая|какое|какие|каков|какова|каково|каковы|чем|что|чего|кого|кому|кем)(?![а-яё])"),
]
_KIND_RES = [(k, re.compile(p, re.I)) for k, p in _KINDS]
_KIND_RU = {"why": "почему — ищу причину", "how": "как устроено или происходит — ищу механизм",
            "howto": "как сделать — ищу шаги", "when": "когда — ищу дату", "where": "где — ищу место",
            "num": "сколько — ищу число", "list": "список — ищу виды и примеры", "advice": "совет — ищу рекомендации",
            "what": "что это — ищу определение", "who": "кто — ищу, о ком речь", "which": "вопрос о факте",
            "explain": "объяснение — разбираю тему по частям"}
_SKIP_WORDS = {nlp.stem(w) for w in """такое это такой такая такие был была были было есть является являются ли вообще именно
    собой представляет значит означает нужно нужен нужна нужны можно надо вот всё все весь вся мне нам пожалуйста простыми словами понятно
    кратко коротко подробно подробнее детально развернуто так же тоже ещё еще""".split()}
_MEASURE = dict(encyclopedia._MEASURE, вес=("масс", "вес", "кг", "тонн", " т "), весит=("масс", "вес", "кг", "тонн", " т "),
                живет=("продолжительност", "живут", "доживают", "лет жизни", "срок жизни"),
                жив=("продолжительност", "живут", "доживают", "лет жизни", "срок жизни"),
                стоит=("руб", "долл", "$", "€", "₽", "стоимост", "цен"), сто=("руб", "долл", "$", "€", "₽", "стоимост", "цен"))
# Глаголы-«рамки» вопроса: «как *устроен* глаз», «как *работает* двигатель» — ищем не это слово, а нужные разделы статьи
_FRAME = {
    "работа": ("принцип", "работ", "устройств", "механизм", "действи", "функци"),
    "устро": ("строени", "устройств", "анатоми", "структур", "состав", "конструкци"),
    "образу": ("образовани", "происхождени", "формировани", "возникновени"),
    "появ": ("происхождени", "появлени", "возникновени", "гипотез", "образовани", "формировани"),
    "возник": ("происхождени", "возникновени", "гипотез", "образовани"),
    "размнож": ("размножени", "жизненн", "цикл", "спор"),
    "происход": ("процесс", "механизм", "причин", "происхождени"),
    "выгляд": ("описани", "внешн", "строени", "морфологи"),
    "действ": ("действи", "механизм", "принцип", "фармакологи"),
    "раст": ("рост", "развити", "выращивани"),
}
_CREATE = ("придума", "изобр", "разработ", "предлож", "созда", "основ", "автор", "открыл", "открыт", "сформулир", "патент")
_SYNONYMS = {k: _CREATE for k in ("приду", "изобр", "созда", "основ", "откры", "разра", "напис", "постр")}
_SYNONYMS.update({"питаю": ("пита", "корм", "добыч", "едят", "поеда"), "живут": ("обита", "живут", "населя", "распростран"),
                  "обита": ("обита", "живут", "населя", "распростран")})
_SUFFIX = {"why": "причина", "how": "принцип работы", "howto": "инструкция", "list": "виды", "when": "дата",
           "where": "где находится", "num": "", "advice": "советы", "what": "", "who": "", "which": "", "explain": ""}


def _content(words):
    out = []
    for w in words:
        s = nlp.stem(w)
        if w in nlp.STOPWORDS or s in nlp.GENERIC or s in nlp.FILLER or s in _SKIP_WORDS or len(w) < 2:
            continue
        out.append(w)
    return out


def understand(text):
    """Разбор вопроса: {"kind", "depth", "simple", "topic", "focus", "aspect", "subject", "web_q", "wiki_q"}."""
    raw = " ".join((text or "").split())
    low = raw.lower().replace("ё", "е")
    s = _FILLER_RE.sub("", low)
    think = bool(_THINK_RE.match(s))
    s = _THINK_RE.sub("", s, count=1)
    explain = bool(_EXPLAIN_RE.match(s))
    s = _FILLER_RE.sub("", _EXPLAIN_RE.sub("", s, count=1))
    kind, head, rest = None, "", s
    for name, rx in _KIND_RES:
        m = rx.match(s)
        if m:
            kind, head, rest = name, s[:m.end()].strip(), s[m.end():]
            break
    if (not kind or kind == "which") and (explain or think) and not head.startswith(("что", "чем", "как")):
        kind, head, rest = "explain", "", s
    depth = 2 if (think or _DEPTH_RE.search(low)) else 1
    simple = bool(_SIMPLE_RE.search(low))
    rest = _SIMPLE_RE.sub(" ", _DEPTH_RE.sub(" ", rest))
    rest = " ".join(rest.strip(" ,.?!:;-—").split())
    words = re.findall(r"[a-zа-я0-9]+(?:-[a-zа-я0-9]+)*", rest)
    content = _content(words)
    topic, topic_words = None, set()
    if content and encyclopedia._data:
        who = "who" if kind == "who" else None
        hits = encyclopedia._mentions(" ".join(content), limit=3, kind=who) or \
            encyclopedia._mentions(" ".join(content), limit=3, kind=who, aliases=True)
        for n, used in hits:
            item = encyclopedia._data["items"][n]
            names = set(nlp.tokens(item[0] + " " + " ".join(item[4] if len(item) > 4 else [])))
            stems = {nlp.stem(w) for w in used}
            if stems & names:          # «слон» — не город Слоним: основы слов должны совпасть по-настоящему
                topic, topic_words = item[0], stems
                break
    if not topic and content and deep.ready():
        topic = deep.title_of(" ".join(content)) or deep.lookup(" ".join(content))
        if topic:
            named = set(nlp.tokens(re.sub(r"\s*\([^)]*\)$", "", topic)))
            topic_words = {nlp.stem(w) for w in content if nlp.stem(w) in named} or {nlp.stem(w) for w in content}
    frame = []
    for w in content:
        st = nlp.stem(w)
        if st not in topic_words and kind in ("how", "howto", "why", "which", "explain"):
            key = next((k for k in _FRAME if st.startswith(k)), None)
            if key:
                frame += list(_FRAME[key])
    focus = [nlp.stem(w) for w in content if not (frame and nlp.stem(w) not in topic_words and
                                                   any(nlp.stem(w).startswith(k) for k in _FRAME))] or [nlp.stem(w) for w in content]
    aspect = [w for w in content if nlp.stem(w) not in topic_words and
              not (frame and any(nlp.stem(w).startswith(k) for k in _FRAME))]
    subject = re.sub(r"\s*\([^)]*\)$", "", topic) if topic else " ".join(content)
    web_q = (head + " " + rest).strip()
    if kind in ("explain", "what", "who") or not web_q:
        web_q = " ".join(content) or rest
    measure = None
    if kind == "num":
        for key, signs in _MEASURE.items():
            if any(f.startswith(key) for f in focus):
                measure = signs
                break
    return {"kind": kind, "depth": depth, "measure": measure, "frame": frame, "simple": simple, "topic": topic, "topic_stems": topic_words,
            "focus": list(dict.fromkeys(focus)), "aspect": aspect, "subject": subject, "rest": rest,
            "web_q": web_q[:200], "wiki_q": (topic or " ".join(content) or rest)[:150], "think": think, "explain": explain}


def wants(text):
    """Вопрос, над которым стоит подумать (а не «привет» или «спасибо»)."""
    p = understand(text)
    return bool(p["kind"]) and bool(p["focus"]) and len(" ".join(p["focus"])) >= 3


_NOT_MIND = re.compile(r"анекдот|шутк|стих|сказк|загадк|песн|рассказ\w*\s+(?:про|о)\s+(?:себя|тебя)|"
                       r"\d\s*[-+*/^=]\s*\d|уравнени|реши\b|погод|курс\w*\s+(?:доллар|евро|валют)|переведи", re.I)


def explicit(text):
    """Просят подумать или объяснить подробно: «подумай…», «исследуй…», «объясни подробно…»."""
    if _NOT_MIND.search(text or ""):
        return False            # шутки, стихи, задачи с числами, погода — у своих инструментов
    p = understand(text)
    return bool(p["focus"]) and (p["think"] or (p["depth"] > 1 and p["kind"] is not None) or
                                 (p["explain"] and p["kind"] in ("why", "how", "howto", "explain")))


def richer(text, title):
    """Глубокие знания знают о теме больше, чем короткая статья энциклопедии, а вопрос — не о простом факте."""
    p = understand(text)
    return deep.ready() and bool(deep.title_of(title)) and p["kind"] in ("why", "how", "howto", "list", "explain", "advice", "which")


# ------------------------------------------------------------------ источники

def _doc(title, text, url="", src="", w=1.0, lead=False, section=""):
    return {"title": title, "text": text or "", "url": url, "src": src, "w": w, "lead": lead, "section": section}


def _overlap(words, text):
    return len(set(words) & set(nlp.tokens(text)))


def _sections(title, lead, sections, url, src, focus, limit, w=1.0):
    """Вступление + разделы, где больше всего слов вопроса (весь текст длинной статьи не нужен)."""
    out = [_doc(title, lead, url, src, w, lead=True)] if lead else []
    ranked = sorted(sections, key=lambda s: -(2 * _overlap(focus, s["title"]) + _overlap(focus, s["text"][:3000])))
    for sec in ranked[:limit]:
        out.append(_doc(f"{title}: {sec['title']}", sec["text"][:6000], url, src, w * 0.95, section=sec["title"]))
    return out


_JUNK = re.compile(r"cookie|подпиш|реклам|©|войти|регистрац|корзин|скидк|купить|оформить|доставк|₽|\$|читайте\s+также|"
                   r"поделиться|комментар|лайк|подписчик|newsletter|javascript|меню|главная\s+страница", re.I)


def _page_doc(page, query_words, url, w=0.85):
    keep = []
    for para in re.split(r"\n\s*\n|\n", page.get("text") or ""):
        para = " ".join(para.split())
        if 50 <= len(para) <= 1200 and not _JUNK.search(para) and (not query_words or set(query_words) & set(nlp.tokens(para))):
            keep.append(para)
    text = "\n".join(keep)[:5000]
    if len(text) < 200:
        return None
    title = re.split(r"\s+[|—–-]\s+", (page.get("title") or url).strip())[0][:80]
    return _doc(title, text, url, "сайт", w)


class _Net:
    """Интернет с бюджетом: не больше N запросов, после первой ошибки связи — дальше без сети."""

    def __init__(self, on, budget):
        self.on, self.left, self.offline = on, budget, False

    def __call__(self, fn, *args, **kw):
        if not self.on or self.offline or self.left <= 0:
            return None
        self.left -= 1
        try:
            return fn(*args, **kw)
        except net.NetError:
            self.offline = True
            return None


def gather(plan, web=True, local=None, budget=6, trace=None, read_pages=None):
    """Собрать тексты по плану: своя база, затем интернет. [doc], {"photo", "offline"}."""
    trace = trace if trace is not None else []
    focus = plan["focus"]
    docs, own, extra = [], [], {"photo": None, "offline": False}
    if plan["topic"] and encyclopedia._data:
        t = encyclopedia.lookup(plan["topic"]) or {}
        if t.get("title") == plan["topic"]:
            docs.append(_doc(t["title"], t["text"], encyclopedia.page_url(t["title"]), "Энциклопедия Rai", 1.0, lead=True))
            own.append(t["title"])
            if t.get("image"):
                extra["photo"] = {"url": t["image"], "title": t["title"], "source": encyclopedia.page_url(t["title"])}
    art = deep.find(plan["topic"] or plan["subject"]) if deep.ready() else None
    if art:
        docs = [d for d in docs if d["title"] != art["title"]]
        docs += _sections(art["title"], art["lead"], art["sections"], art["url"], "Знания Rai", focus,
                          limit=6 if plan["depth"] > 1 else 4)
        own.append(f"{art['title']} (статья целиком, {len(art['sections'])} разделов)")
    for d in local or []:
        docs.append(_doc(d.get("title", ""), d.get("text", ""), d.get("url", ""), d.get("src", "Словарь Rai"), 0.9, lead=True))
        own.append(d.get("title", ""))
    trace.append({"kind": "search", "query": "своя база: энциклопедия, глубокие знания, словарь", "found": own})

    use = _Net(web, budget)
    if web:
        found = []
        page = None if art else use(online.wiki_page, plan["wiki_q"])
        if page and online._relevant(plan["wiki_q"], page["title"] + " " + page["lead"][:800]):
            docs += _sections(page["title"], page["lead"], page["sections"], page["link"], "Википедия", focus,
                              limit=6 if plan["depth"] > 1 else 4)
            found.append(page["title"] + " — Википедия")
            if page.get("image") and not extra["photo"]:
                extra["photo"] = {"url": page["image"], "title": page["title"], "source": page["link"]}
        # то, о чём именно спрашивают, может быть отдельной статьёй: «почему небо голубое» → рассеяние света
        if plan["aspect"] and plan["kind"] in ("why", "how", "which", "num", "when", "where") and plan["topic"]:
            q = " ".join(plan["aspect"] + [plan["subject"]])
            art2 = use(online.web_article, q)
            if art2 and all(art2["title"] != d["title"].split(":")[0] for d in docs) and \
                    online._relevant(" ".join(plan["aspect"]), art2["title"] + " " + art2["text"]):
                docs.append(_doc(art2["title"], art2["text"], art2["link"], "Википедия", 0.95, lead=True))
                found.append(art2["title"] + " — Википедия")
        results = use(online.web_results, plan["web_q"], 8) or []
        relevant = [r for r in results if online._relevant(plan["web_q"], r["title"] + " " + r.get("snippet", ""))]
        for r in relevant[:6]:
            if r.get("snippet"):
                docs.append(_doc(online._md(r["title"]), r["snippet"], online._safe_url(r["url"]), "поиск", 0.7))
        if relevant:
            trace.append({"kind": "search", "query": plan["web_q"], "found": [online._md(r["title"]) for r in relevant[:5]]})
        read = 0
        for r in relevant:
            if read >= (read_pages if read_pages is not None else (3 if plan["depth"] > 1 else 2)) or "wikipedia.org" in r["url"]:
                continue
            page = use(net.read, r["url"])
            if not page:
                continue
            d = _page_doc(page, focus, online._safe_url(r["url"]))
            if d:
                docs.append(d)
                read += 1
                trace.append({"kind": "open", "query": r["url"], "found": [d["title"]]})
        if found:
            trace.append({"kind": "search", "query": "Википедия: " + plan["wiki_q"], "found": found})
        extra["offline"] = use.offline
    extra["net"] = use
    return docs, extra


# ------------------------------------------------------------------ читать и оценивать

_CAUSE_RE = encyclopedia._CAUSE_RE
_HOW_RE = re.compile(r"(?<![а-яё])(?:работа\w*|происход\w*|основан\w*|использу\w*|состо\w*|превраща\w*|переда\w*|за\s+сч[её]т|"
                     r"принцип\w*|механизм\w*|процесс\w*|сначала|затем|после\s+этого|в\s+результате|образу\w*|возника\w*|"
                     r"при\s+этом|поступа\w*|выделя\w*|поглоща\w*|преобразу\w*|движ\w*|вращ\w*|нагрева\w*)(?![а-яё])", re.I)
_DEF_RE = re.compile(r"\s[—–]\s|(?<![а-яё])(?:это|явля\w+|называ\w+|представля\w+\s+собой)(?![а-яё])", re.I)
_DATE_RE = re.compile(r"(?<!\d)(?:1[0-9]{3}|20[0-9]{2}|[1-9][0-9]{2})(?!\d)(?:\s*(?:год|г\.))?|\b[IVXL]+\s+(?:век|в\.)", re.I)
_PLACE_RE = re.compile(r"(?<![а-яё])(?:располож\w*|находит\w*|протека\w*|столиц\w*|страны|материк\w*|континент\w*|океан\w*|"
                       r"регион\w*|север\w*|юг\w*|запад\w*|восток\w*|област\w*|побережь\w*|остров\w*)(?![а-яё])|"
                       r"(?<![а-яё])(?:в|на|у)\s+[А-ЯЁ][а-яё]+", re.I)
_LISTY_RE = re.compile(r"(?<![а-яё])(?:различа\w+|выделя\w+|бывают|дел(?:ят|ится|ятся)\s+на|включа\w+|относ\w+|виды|типы|"
                       r"разновидност\w+|классифик\w+|например|такие\s+как|среди\s+них)(?![а-яё])|:\s*[а-яё]", re.I)
_ADVICE_RE = re.compile(r"(?<![а-яё])(?:нужно|надо|следует|стоит|рекоменду\w+|советуют|важно|лучше|необходимо|полезно|нельзя|"
                        r"старайтесь|попробуйте|избегайте|помогает|поможет|помогут|желательно|обязательно|достаточно)(?![а-яё])", re.I)
_WARN_RE = re.compile(r"(?<![а-яё])(?:нельзя|опасн\w*|осторожн\w*|не\s+следует|не\s+стоит|не\s+рекоменду\w*|к\s+врачу|"
                      r"вред\w*|риск\w*|запрещ\w*)(?![а-яё])", re.I)
_STEP_RE = re.compile(r"^\s*(?:\d{1,2}[.)]\s|[-•–]\s|шаг\s+\d+|сначала|затем|после\s+этого|далее|наконец|в\s+конце)", re.I)
_BAD_SENT = re.compile(r"(?:cookie|подпиш|©|войти|зарегистр|реклам|читайте\s+также|источник:|фото:|https?://|\.ru\b|"
                       r"\.com\b|ISBN|стр\.\s*\d|см\.\s+также|ru\.wikipedia)", re.I)


def _sentences(doc):
    out = []
    for block in doc["text"].split("\n"):
        for k, s in enumerate(encyclopedia._sentences(block)):
            s = encyclopedia.tidy(" ".join(s.split()))
            if 25 <= len(s) <= 520 and not _BAD_SENT.search(s) and re.search(r"[а-яёa-z]{3}", s, re.I):
                out.append(s)
    return out


def _numbers(sentence):
    """Числа с единицами: [(значение, единица)] — для сверки источников."""
    out = []
    for m in re.finditer(r"(\d[\d\s ]*(?:[.,]\d+)?)\s*(млрд|млн|тыс\.?|миллиард\w*|миллион\w*|тысяч\w*)?\s*"
                         r"(км²|км2|км/ч|км/с|м/с|км|см|мм|м|кг|г|тонн\w*|т|°C|°|%|лет|год\w*|чел\w*|жител\w*|световых\s+лет|а\.\s*е\.)?", sentence):
        digits = re.sub(r"[\s ]", "", m.group(1)).replace(",", ".")
        try:
            value = float(digits)
        except ValueError:
            continue
        mult = (m.group(2) or "").lower()
        value *= 1e9 if mult.startswith(("млрд", "миллиард")) else 1e6 if mult.startswith(("млн", "миллион")) else \
            1e3 if mult.startswith(("тыс", "тысяч")) else 1
        unit = (m.group(3) or "").lower()
        if unit or mult:
            out.append((value, re.sub(r"\W.*", "", unit)[:5]))
    return out


def _aspect_words(plan, docs):
    """О чём именно спрашивают — основы слов + близкие: свой словарь синонимов и модель смыслов (среди слов
    найденных текстов: «вымерли» ≈ «вымирание», «светит» ≈ «отражает»). {основа: вес}."""
    out = {}
    for w in plan["aspect"]:
        st = nlp.stem(w)
        out[st] = 1.0
        for syn in _SYNONYMS.get(st[:5], ()):
            out.setdefault(syn, 0.8)
    if out and sense.ready():
        vocab = set()
        for d in docs[:40]:
            vocab.update(nlp.tokens(d["text"][:6000]))
        for st in list(out):
            if out[st] < 1.0:
                continue
            base = sense._word_vec(st)
            if base is None:
                continue
            norm = sum(x * x for x in base) ** 0.5 or 1
            for v in vocab:
                if v in out or len(v) < 4:
                    continue
                vec = sense._word_vec(v)
                if vec is None:
                    continue
                cos = sum(a * b for a, b in zip(base, vec)) / (norm * (sum(x * x for x in vec) ** 0.5 or 1))
                # близкие по смыслу соседи по теме («архозавр» рядом с «вымерли») — не то; берём другие формы того же
                # слова («вымирание», «вымершие») и очень близкие по смыслу слова
                same_root = len(st) >= 5 and v[:3] == st[:3] and cos >= 0.6
                if same_root or cos >= 0.75:
                    out[v] = round(min(0.8, cos), 2)
    return out


def _causal(sent, words):
    """Есть ли в предложении причина. «В результате извержения возник остров» — это следствие извержения,
    а не его причина: слово вопроса сразу после «в результате / из-за / благодаря» не считается."""
    found = False
    for m in _CAUSE_RE.finditer(sent):
        after = set(nlp.tokens(sent[m.end():m.end() + 30])[:2])
        if words and _hit(after, words) >= 0.55 and m.group(0).lower().startswith(("в результат", "вследстви", "из-за", "благодаря")):
            continue
        found = True
    return found


def _hit(stems, words):
    """Вес совпадения слов предложения со словами вопроса (точно, по началу основы — «вымерл»/«вымер»)."""
    best = 0.0
    for w, weight in words.items():
        if w in stems or (len(w) >= 5 and any(x.startswith(w[:5]) for x in stems)):
            best = max(best, weight)
    return best


# Предложение, которое без предыдущего не понять: «Такой двигатель…», «Благодаря этому…», «Кроме того…»
_ANAPHORA_RE = re.compile(r"^(?:так(?:ой|ая|ое|ие|им|их|ом)|эт(?:от|а|о|и|им|ого|ой|ом|у)|благодаря\s+этому|поэтому|таким\s+образом|"
                          r"кроме\s+того|например|к\s+примеру|при\s+этом|однако|также|тем\s+не\s+менее|в\s+то\s+же\s+время|"
                          r"он[аио]?|они|его|её|их|там|здесь|тогда|затем|впоследствии|также)(?![а-яё])", re.I)
_NAME_RE = re.compile(r"(?<!^)(?<![.!?]\s)\b[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)?")


def _score(sent, doc, idx, plan, qvec):
    st = set(nlp.tokens(sent))
    focus, topic = set(plan["focus"]), plan["topic_stems"]
    aspect = plan.get("aspect_words") or {nlp.stem(w): 1.0 for w in plan["aspect"]}
    f = len(focus & st)
    a = _hit(st, aspect) if aspect else 0.0
    sec = (doc.get("section") or "").lower()
    frame = plan.get("frame") or ()
    in_frame = bool(frame) and any(x in sec for x in frame)
    if not f and not a and not in_frame and not (doc["lead"] and idx == 0):
        return None
    s = 1.0 * f + 3.0 * a + (0.4 if topic & st else 0)
    if in_frame:
        s += 2.5                                   # раздел «Строение», «Принцип работы», «Происхождение»…
    elif frame and any(x in sent.lower() for x in frame):
        s += 1.0
    if aspect and not a and plan["kind"] not in ("what", "explain", "list"):
        s -= 1.5                                   # предложение не о том, что спрашивают
    kind = plan["kind"]
    if kind == "why":
        s += (2.5 if a >= 0.55 or not aspect else 0.3) if _causal(sent, aspect) else 0
    elif kind == "how":
        s += 1.5 if _HOW_RE.search(sent) else 0
        s += 2.0 if idx == 0 and doc["lead"] else 0
    elif kind in ("howto", "advice"):
        s += 2.0 if _ADVICE_RE.search(sent) else 0
        s += 1.0 if _STEP_RE.match(sent) else 0
    elif kind == "when":
        s += 3.0 if _DATE_RE.search(sent) else -1
    elif kind == "num":
        s += 3.0 if _numbers(sent) else (0.5 if re.search(r"\d", sent) else -1.5)
        signs = plan.get("measure")
        if signs:
            low = sent.lower()
            s += 2.5 if any(m in low for m in signs) else -2.0
    elif kind == "where":
        s += 2.0 if _PLACE_RE.search(sent) else 0
    elif kind == "list":
        s += 2.5 if _LISTY_RE.search(sent) else 0
        s += 0.5 * min(4, sent.count(","))
    elif kind in ("what", "who", "explain", "which"):
        s += 2.0 if idx == 0 and doc["lead"] else 0
        s += 1.0 if _DEF_RE.search(sent[:120]) and idx < 2 else 0
        if kind == "who" and a and _NAME_RE.search(sent):
            s += 2.0                               # «кто изобрёл телефон» — нужно имя
        if kind == "who" and sec and _NAME_RE.fullmatch(doc["section"].strip()):
            s += 1.0
    if qvec is not None:
        s += 4.0 * max(0.0, sense.cosine(qvec, sense.vector(sent)) - 0.15)
    s -= 0.04 * idx
    if _ANAPHORA_RE.match(sent):
        s -= 1.2
    if sent.rstrip().endswith(":"):
        s -= 2.5                                   # «…основана на следующих преобразованиях:» — список потерян
    n = len(sent)
    s -= 2.0 if n < 40 else 1.2 if n > 380 else 0
    return s * doc["w"]


def _jaccard(a, b):
    return len(a & b) / (len(a | b) or 1)


def rank(docs, plan):
    """Все предложения всех текстов с оценкой: [{"text", "score", "doc", "pos", "stems"}] — лучшие первыми."""
    qvec = sense.vector(" ".join(plan["focus"]), stems=plan["focus"]) if sense.ready() else None
    plan["aspect_words"] = _aspect_words(plan, docs)
    out = []
    for d_no, doc in enumerate(docs):
        for idx, sent in enumerate(_sentences(doc)):
            sc = _score(sent, doc, idx, plan, qvec)
            if sc is not None:
                out.append({"text": sent, "score": sc, "doc": d_no, "pos": idx, "stems": set(nlp.tokens(sent))})
    out.sort(key=lambda x: -x["score"])
    return out


def select(cands, n, min_score=1.5):
    """Лучшие предложения без повторов: каждое следующее — сильное и непохожее на уже выбранные."""
    chosen, pool = [], cands[:200]
    while pool and len(chosen) < n:
        best, best_val = None, None
        for c in pool:
            sim = max((_jaccard(c["stems"], x["stems"]) for x in chosen), default=0.0)
            if sim > 0.55 or any(c["text"] == x["text"] for x in chosen):
                continue
            val = c["score"] - 3.0 * sim
            if best_val is None or val > best_val:
                best, best_val = c, val
        if best is None or best_val < min_score:
            break
        chosen.append(best)
        pool.remove(best)
    return chosen


# ------------------------------------------------------------------ ответ и проверка

def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _sources(docs, used):
    seen, out = set(), []
    for c in used:
        d = docs[c["doc"]]
        url = d["url"]
        if not url or url in seen:
            continue
        seen.add(url)
        name = d["title"].split(":")[0]
        if d["src"] in ("Википедия", "Знания Rai", "Энциклопедия Rai"):
            name += " — Википедия"
        out.append(f"[{online._md(name)}]({url})")
    return out[:5]


def _agree(chosen, docs):
    """Сверка чисел: одно и то же число из разных источников — подтверждено; разные — расходятся."""
    seen = []
    for c in chosen[:4]:
        for value, unit in _numbers(c["text"])[:2]:
            seen.append((value, unit, docs[c["doc"]]["url"] or docs[c["doc"]]["title"]))
    if len(seen) < 2:
        return None
    first = seen[0]
    same = {src for v, u, src in seen if u == first[1] and abs(v - first[0]) <= abs(first[0]) * 0.03}
    if len(same) >= 2:
        return ("ok", len(same))
    other = next((x for x in seen[1:] if x[1] == first[1] and x[2] != first[2]), None)
    return ("diff", other) if other else None


def _check(plan, chosen, docs):
    """Самопроверка ответа: (уверенность 0..1, [строки для «Как Rai думал»])."""
    notes = []
    if not chosen:
        return 0.0, ["⚠️ Подходящих предложений не нашлось"]
    top = chosen[:3]
    covered = set().union(*(c["stems"] for c in top)) & set(plan["focus"])
    cov = len(covered) / (len(plan["focus"]) or 1)
    notes.append(("✅" if cov >= 0.6 else "⚠️") + f" Слова вопроса в ответе: {len(covered)} из {len(plan['focus'])}")
    main = " ".join(c["text"] for c in chosen[:2])
    kind = plan["kind"]
    words = plan.get("aspect_words") or {}
    because = [c for c in chosen[:3] if _causal(c["text"], words) and (not words or _hit(c["stems"], words) >= 0.55)]
    signs = plan.get("measure")
    numeric = [c for c in chosen[:2] if _numbers(c["text"]) and (not signs or any(m in c["text"].lower() for m in signs))]
    checks = {"why": (because, "есть объяснение причины", "прямой причины в текстах нет"),
              "when": (_DATE_RE.search(main), "есть дата", "точной даты не нашёл"),
              "num": (numeric, "есть число", "точного числа не нашёл"),
              "where": (_PLACE_RE.search(main), "есть место", "точного места не нашёл"),
              "howto": (len(chosen) >= 2, "есть шаги", "шагов мало"),
              "list": (len(chosen) >= 3, "есть пункты", "пунктов мало")}
    ok = True
    # «кто придумал теорию струн», «чем питаются ежи» — в ответе должно быть то, о чём именно спрашивают
    if words and kind not in ("what", "explain", "list"):
        hit = max((_hit(c["stems"], words) for c in chosen[:2]), default=0.0)
        ok = hit >= 0.55
        notes.append(("✅ Есть ответ именно на «" if ok else "⚠️ Нет ответа именно на «") + " ".join(plan["aspect"]) + "»")
    if kind in checks:
        good_kind, good, bad = checks[kind]
        ok = ok and bool(good_kind)
        notes.append(("✅ Ответ на вопрос: " + good) if ok else ("⚠️ " + _cap(bad)))
    sources = {docs[c["doc"]]["url"] or docs[c["doc"]]["title"] for c in chosen}
    notes.append(("✅" if len(sources) >= 2 else "•") + f" Источников в ответе: {len(sources)}")
    agree = _agree(chosen, docs) if kind in ("num", "when", "which") else None
    if agree and agree[0] == "ok":
        notes.append(f"✅ Число совпадает в {agree[1]} источниках")
    elif agree:
        notes.append("⚠️ Источники называют разные числа — показываю оба")
    strength = min(1.0, top[0]["score"] / 6.0)
    material = min(1.0, len(chosen) / 3)
    conf = 0.35 * cov + 0.25 * (1.0 if ok else 0.0) + 0.15 * strength + 0.1 * min(1.0, len(sources) / 2) + 0.15 * material
    if agree and agree[0] == "ok":
        conf = min(1.0, conf + 0.05)
    clar = re.search(r"\(([^)]+)\)$", plan.get("topic") or "")
    if clar and not set(nlp.tokens(clar.group(1))) & set(plan["focus"]):
        conf -= 0.25               # «Трава (фармацевтика)» на вопрос про траву на лугу — тема, скорее всего, не та
        notes.append("⚠️ Тема в базе — «" + plan["topic"] + "», возможно, не та")
    if not ok:
        conf = min(conf, 0.3)      # на сам вопрос ответа нет — лучше честно поискать дальше, чем отвечать не о том
    return round(conf, 2), notes


def _in_order(items, docs):
    """Подробности — в том порядке, в каком они идут в источниках (так текст связнее)."""
    return sorted(items, key=lambda c: (c["doc"], c["pos"]))


def _lead_definition(plan, docs):
    """Первое предложение статьи о теме («Компьютер — устройство…») — лучшее «Суть» для «как работает…»."""
    topic = plan["topic_stems"]
    for d_no, doc in enumerate(docs):
        if not doc["lead"] or doc["section"]:
            continue
        sents = _sentences(doc)
        if sents and topic & set(nlp.tokens(sents[0])) and _DEF_RE.search(sents[0][:160]):
            return {"text": sents[0], "score": 0, "doc": d_no, "pos": 0, "stems": set(nlp.tokens(sents[0]))}
    return None


def compose(plan, chosen, docs):
    """Текст ответа из выбранных предложений — по типу вопроса."""
    kind = plan["kind"]
    first, rest = chosen[0], chosen[1:]
    lines = []
    if kind == "why":
        words = plan.get("aspect_words") or {}
        cause = next((c for c in chosen[:4] if _causal(c["text"], words) and (not words or _hit(c["stems"], words) >= 0.55)),
                     next((c for c in chosen[:3] if _causal(c["text"], words)), first))
        rest = [c for c in chosen if c is not cause]
        lines.append(f"**Коротко:** {cause['text']}")
        if rest:
            lines.append("**Почему так:**\n" + "\n".join(f"- {c['text']}" for c in _in_order(rest, docs)))
    elif kind == "how":
        lead = _lead_definition(plan, docs)
        if lead and all(lead["text"] != c["text"] for c in chosen):
            chosen = [lead] + chosen
            first, rest = chosen[0], chosen[1:]
        define = next((c for c in chosen if docs[c["doc"]]["lead"] and c["pos"] == 0 and _DEF_RE.search(c["text"][:120])),
                      next((c for c in chosen[:4] if _DEF_RE.search(c["text"][:120]) and c["pos"] == 0), first))
        rest = [c for c in chosen if c is not define]
        lines.append(f"**Суть:** {define['text']}")
        if rest:
            lines.append("**Как это работает:**\n" + "\n".join(f"{k}. {c['text']}" for k, c in enumerate(_in_order(rest, docs), 1)))
    elif kind in ("howto", "advice"):
        steps = [c for c in chosen if not _WARN_RE.search(c["text"])]
        warn = [c for c in chosen if _WARN_RE.search(c["text"])]
        title = "Что делать" if kind == "howto" else "Что советуют"
        if steps:
            lines.append(f"**{title}:**\n" + "\n".join(f"{k}. {re.sub(_STEP_RE, '', c['text']).strip()}"
                                                       for k, c in enumerate(steps, 1)))
        if warn:
            lines.append("**Важно:**\n" + "\n".join(f"- ⚠️ {c['text']}" for c in warn))
    elif kind in ("when", "where", "num"):
        lines.append(f"**Ответ:** {first['text']}")
        agree = _agree(chosen, docs)
        if agree and agree[0] == "diff":
            other = next((c for c in rest if any(v == agree[1][0] for v, _ in _numbers(c["text"]))), None)
            if other:
                lines.append(f"**В другом источнике иначе:** {other['text']}")
                rest = [c for c in rest if c is not other]
        if rest:
            lines.append("**Ещё по теме:**\n" + "\n".join(f"- {c['text']}" for c in _in_order(rest[:4], docs)))
    elif kind == "list":
        lines.append(first["text"])
        if rest:
            lines.append("**Главное:**\n" + "\n".join(f"- {c['text']}" for c in rest))
    else:  # what, who, which, explain
        lead = [first] + [c for c in rest[:1] if c["doc"] == first["doc"] and abs(c["pos"] - first["pos"]) == 1]
        rest = [c for c in rest if c not in lead]
        lines.append(" ".join(c["text"] for c in sorted(lead, key=lambda c: c["pos"])))
        if rest:
            lines.append("**Главное:**\n" + "\n".join(f"- {c['text']}" for c in _in_order(rest, docs)))
    return "\n\n".join(lines)


def _by_sections(plan, docs, used, limit=4):
    """Подробный разбор: лучшие разделы статьи с 1–2 главными предложениями каждый."""
    out = []
    taken = {c["text"] for c in used}
    for d_no, doc in enumerate(docs):
        if not doc["section"] or len(out) >= limit:
            continue
        sents = [s for s in _sentences(doc) if s not in taken]
        if not sents:
            continue
        pick = sorted(sents[:8], key=lambda s: -(_overlap(plan["focus"], s) + (1 if sents.index(s) == 0 else 0)))[:2]
        pick.sort(key=sents.index)
        out.append(f"### {_cap(doc['section'])}\n" + " ".join(pick))
    return out


def _alt_queries(plan):
    """Другие слова для следующих кругов поиска: близкие по смыслу (модель Rai Смысл), уточнение по типу вопроса."""
    words = [plan["subject"]] + [w for f in plan["focus"][:2] for w in sense.related(f, 2)]
    first = " ".join(dict.fromkeys(x for x in words + [_SUFFIX.get(plan["kind"], "")] if x)).strip()
    out = [first, plan["web_q"] + " объяснение простыми словами", plan["subject"] + " подробно"]
    return [q for q in dict.fromkeys(out) if q.strip()]


def think(text, web=True, depth=None, local=None, budget=None, min_conf=0.3, level=None):
    """Подумать над вопросом: {"text", "confidence", "trace", "photo", "kind", "level"} или None (не получилось).

    level — уровень размышления (LEVELS): low, medium, high, extra, code, ultra.
    """
    lv = level_of(level)
    web = web and lv["web"]
    budget = lv["budget"] if budget is None else budget
    plan = understand(text)
    if not plan["kind"] or not plan["focus"]:
        return None
    plan["depth"] = max(plan["depth"], depth or 1, lv["depth"])
    trace = [{"kind": "think", "text": (
        f"**Уровень:** {lv['label']} — {lv['about']}.\n\n"
        f"**Понял вопрос:** {_KIND_RU.get(plan['kind'], plan['kind'])}.\n\n"
        f"**Тема:** {plan['topic'] or plan['subject'] or '—'}" +
        (f"; **важно:** {' '.join(plan['aspect'])}" if plan["aspect"] and plan["topic"] else "") + ".\n\n"
        "**План:** своя база знаний → " + ("Википедия → поиск в интернете → чтение страниц → " if web else "") +
        "оценить каждое предложение → собрать ответ → проверить" + (" → если слабо, искать ещё" if web and lv["rounds"] else "") + ".")}]
    docs, extra = gather(plan, web=web, local=local, budget=budget, trace=trace, read_pages=lv["read"])
    if not docs:
        return None
    cands = rank(docs, plan)
    n = lv["sentences"] if not plan["simple"] else min(3, lv["sentences"])
    chosen = select(cands, n)
    conf, notes = _check(plan, chosen, docs)
    # Слабо — ещё круги: другие слова (близкие по смыслу из модели Rai) и уточнение по типу вопроса
    use = extra["net"]
    for k, alt in enumerate(_alt_queries(plan)[:lv["rounds"]]):
        if conf >= (0.8 if lv["rounds"] > 1 else 0.55) or not web or use.offline or use.left <= 0:
            break
        more = [_doc(p["title"], p["text"], p["url"], "сайт", 0.85)
                for p in use(online.web_material, alt, 2, tuple(d["url"] for d in docs)) or []]
        if not more:
            continue
        trace.append({"kind": "search", "query": f"{alt} (круг {k + 2}: ответ был слабым)", "found": [d["title"] for d in more]})
        docs += more
        cands = rank(docs, plan)
        again = select(cands, n)
        conf2, notes2 = _check(plan, again, docs)
        if conf2 > conf:
            chosen, conf, notes = again, conf2, notes2
    trace.append({"kind": "read", "text": f"Прочитал {len(docs)} текстов: {len(cands)} предложений по теме, "
                                          f"выбрал {len(chosen)} лучших" + (" (по словам и по смыслу — модель Rai Смысл)." if sense.ready() else ".")})
    trace.append({"kind": "check", "text": "\n".join(notes) + f"\n\nУверенность: {int(conf * 100)}%"})
    if not chosen or conf < min_conf:
        return None
    body = compose(plan, chosen, docs)
    if plan["depth"] > 1 and plan["kind"] in ("explain", "what", "who", "how", "which", "list"):
        parts = _by_sections(plan, docs, chosen, limit=6 if lv is LEVELS["ultra"] else 4)
        if parts:
            body += "\n\n**Подробнее по разделам:**\n\n" + "\n\n".join(parts)
    src = _sources(docs, chosen)
    if src:
        body += "\n\n**Источники:** " + " · ".join(src)
    sure = "высокая" if conf >= 0.75 else "средняя" if conf >= 0.55 else "низкая — проверьте по ссылкам"
    body += f"\n\n*🧠 Rai Разум · {lv['label']}: продумал сам — уверенность {sure}.*"
    return {"text": body, "confidence": conf, "trace": trace, "photo": extra["photo"], "kind": plan["kind"],
            "offline": extra["offline"], "level": lv["label"]}


# ------------------------------------------------------------------ исследование темы (для презентаций)

_ANGLES = {
    "person": ["биография", "достижения", "интересные факты"],
    "place": ["история", "география", "достопримечательности", "интересные факты"],
    "event": ["причины", "ход событий", "итоги", "значение"],
    "nature": ["описание", "особенности", "интересные факты"],
    "tech": ["как работает", "история создания", "применение", "интересные факты"],
    "general": ["история", "особенности", "интересные факты"],
}


def topic_type(title, text=""):
    """Человек, место, событие, природа, техника — от этого зависит план исследования."""
    low = (title + " " + text[:300]).lower()
    if encyclopedia._PERSON_RE.match(title or ""):
        return "person"
    if re.search(r"(?<![а-яё])(?:войн\w*|революци\w*|битв\w*|восстани\w*|реформ\w*|кризис\w*|переворот\w*|сражени\w*)", low):
        return "event"
    if re.search(r"(?<![а-яё])(?:город|стран\w*|государств\w*|столиц\w*|остров\w*|рек[аи]|озер\w*|гор[аы]|област\w*|регион\w*|материк\w*)(?![а-яё])", low):
        return "place"
    if re.search(r"(?<![а-яё])(?:животн\w*|растени\w*|вид\w*\s+\w+|млекопитающ\w*|птиц\w*|рыб\w*|насеком\w*|планет\w*|звезд\w*|галактик\w*)(?![а-яё])", low):
        return "nature"
    if re.search(r"(?<![а-яё])(?:устройств\w*|технологи\w*|машин\w*|программ\w*|двигател\w*|компьютер\w*|систем\w*|язык\s+программ\w*)", low):
        return "tech"
    return "general"


def research(topic, web=True, want=(), budget=6):
    """Исследовать тему для презентации: статьи по разделам из своей базы и интернета + поиск по сторонам темы.

    [{"title", "text", "url", "src"}], заметки (что сделано). Без интернета — глубокие знания Rai.
    """
    notes, out = [], []
    art = deep.find(topic) if deep.ready() else None
    if art:
        notes.append(f"статья «{art['title']}» целиком из знаний Rai")
        out.append({"title": art["title"], "text": art["lead"], "url": art["url"], "src": "Знания Rai", "lead": True})
        for sec in art["sections"]:
            out.append({"title": sec["title"], "text": sec["text"], "url": art["url"], "src": "Знания Rai"})
    if not web:
        return out, notes
    use = _Net(web, budget)
    kind = topic_type(topic, art["lead"] if art else "")
    angles = [a for a in want if a] + _ANGLES[kind]
    seen = {d["url"] for d in out}
    got = 0
    for angle in dict.fromkeys(angles):
        if use.left <= 0 or use.offline or got >= 4:
            break
        for p in use(online.web_material, f"{topic} {angle}", 1, tuple(seen)) or []:
            seen.add(p["url"])
            out.append({"title": _cap(angle), "text": p["text"], "url": p["url"], "src": "сайт", "site": p["title"]})
            got += 1
    if got:
        notes.append(f"прочитал {got} сайт" + ("а" if 2 <= got <= 4 else "ов" if got >= 5 else ""))
    return out, notes
