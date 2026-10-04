"""Собрать энциклопедию Rai (encyclopedia.json) — ~10 000 важнейших тем из Википедии.

Запускается на GitHub (workflow «Знания Rai»), там есть доступ к Википедии:

    python tools/build_encyclopedia.py -o encyclopedia.json

Откуда темы:
  • Wikipedia: Vital articles, уровень 4 — список из 10 000 самых важных статей, разложенных по разделам
    (люди, история, география, искусство, наука, технологии…). Для каждой берём русскую статью.
  • Дополнение про Россию и Беларусь из Wikidata: регионы, города, известные люди.
Для каждой темы: название, краткое описание (Wikidata), начало статьи (2–3 предложения), другие названия.

Тексты Википедии — CC BY-SA 4.0 (Rai указывает источник в каждом ответе), данные Wikidata — CC0.
Только стандартная библиотека Python.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "RaiKnowledgeBuilder/1.0 (https://github.com/rteaminfo1-source/rai)"
EN = "https://en.wikipedia.org/w/api.php"
RU = "https://ru.wikipedia.org/w/api.php"
WD = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
PREFIX = "Vital articles/Level 4"   # раньше было «Level/4» — эти страницы теперь перенаправления

SECTIONS = {
    "People": "Люди",
    "History": "История",
    "Geography": "География",
    "Arts": "Искусство",
    "Philosophy and religion": "Философия и религия",
    "Everyday life": "Повседневная жизнь",
    "Society and social sciences": "Общество",
    "Biology and health sciences": "Биология и медицина",
    "Physical sciences": "Естественные науки",
    "Technology": "Технологии",
    "Mathematics": "Математика",
}
EXTRA_SECTION = "Россия и Беларусь"
SPACE_SECTION = "Космос"
NEWS_SECTION = "Новое и популярное"

# Космос: статьи из категорий русской Википедии (поиск deepcat — со всеми подкатегориями), самые известные первыми.
SPACE = [
    ("Солнечная система", "Солнечная система", 400),
    ("Планеты", "Планеты", 200),
    ("Спутники планет", "Спутники планет", 250),
    ("Звёзды", "Звёзды", 1500),
    ("Галактики", "Галактики", 800),
    ("Туманности", "Туманности", 300),
    ("Звёздные скопления", "Звёздные скопления", 300),
    ("Созвездия", "Созвездия", 120),
    ("Экзопланеты", "Экзопланеты", 400),
    ("Кометы", "Кометы", 200),
    ("Астероиды", "Астероиды", 300),
    ("Чёрные дыры и квазары", "Чёрные дыры", 120),
    ("Чёрные дыры и квазары", "Квазары", 100),
    ("Космические аппараты", "Космические аппараты", 400),
    ("Космонавты", "Космонавты", 300),
    ("Астрономия", "Астрономия", 400),
]
# Не берём в «популярное за день» (бывает в самых читаемых статьях)
_NEWS_SKIP = re.compile(r"порн|эрот|xxx|секс|заглавная страница|служебная:|википедия:|список ", re.I)

# Дополнение: (подраздел, запрос SPARQL). ?item — объект, у которого есть статья в русской Википедии.
EXTRA = [
    ("Регионы России", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q43263 . FILTER NOT EXISTS { ?item wdt:P576 [] } }"""),
    ("Города России", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q7930989; wdt:P17 wd:Q159; wdt:P1082 ?pop .
          FILTER(?pop >= 12000) }"""),
    ("Области Беларуси", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q10864048; wdt:P17 wd:Q184 }"""),
    ("Города Беларуси", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q7930989; wdt:P17 wd:Q184; wdt:P1082 ?pop . FILTER(?pop >= 3000) }"""),
    ("Известные люди России и СССР", """
        SELECT ?item ?n WHERE { ?item wdt:P31 wd:Q5; wdt:P27 ?c; wikibase:sitelinks ?n .
          VALUES ?c { wd:Q159 wd:Q15180 wd:Q34266 } FILTER(?n >= 60) } ORDER BY DESC(?n) LIMIT 700"""),
    ("Известные люди Беларуси", """
        SELECT ?item ?n WHERE { ?item wdt:P31 wd:Q5; wdt:P27 wd:Q184; wikibase:sitelinks ?n . FILTER(?n >= 15) }
        ORDER BY DESC(?n) LIMIT 150"""),
]

MAX_TEXT = 420
# Время на сборку: Википедия иногда сильно замедляет ответы (429, maxlag). Когда время подходит к концу,
# оставшиеся пачки пропускаются и сохраняется то, что собрано, — лучше 13 000 тем сегодня, чем ничего.
START = time.monotonic()
BUDGET = float(os.environ.get("RAI_BUILD_MINUTES", "100")) * 60
DAYS_LIMIT = 15 * 60           # «этот день в истории» — не дольше 15 минут, остальное — из прошлой сборки
_warned = set()


def time_left():
    return BUDGET - (time.monotonic() - START)


def out_of_time(stage, reserve):
    """Пора остановить этап (оставив reserve секунд на следующие)? Сообщает об этом один раз."""
    if time_left() > reserve:
        return False
    if stage not in _warned:
        _warned.add(stage)
        log(f"  время на исходе ({int((time.monotonic() - START) // 60)} мин) — {stage}: пропускаю оставшееся")
    return True


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url, params, tries=6):
    """Запрос к API Википедии/Wikidata с повторами и паузами (вежливо: не больше ~10 запросов в секунду).
    Длинные списки названий уходят POST-ом — в адрес они не помещаются."""
    params = dict(params)
    if url in (EN, RU):
        params.update(format="json", formatversion="2", maxlag="10")
    elif url == WD:
        params.update(format="json", formatversion="2")
    else:
        params["format"] = "json"
    body = urllib.parse.urlencode(params)
    delay = 2
    for attempt in range(tries):
        try:
            headers = {"User-Agent": UA, "Accept": "application/json"}
            if url != SPARQL and len(body) > 1500:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                req = urllib.request.Request(url, data=body.encode(), headers=headers)
            else:
                req = urllib.request.Request(url + "?" + body, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(data["error"].get("code", "error") + ": " + str(data["error"].get("info", ""))[:200])
            time.sleep(0.1)
            return data
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as e:
            if attempt == tries - 1:
                raise
            log("  повтор через", delay, "с:", e)
            time.sleep(delay)
            delay *= 2


def rest(url, tries=4):
    """GET к REST API Википедии (лента дня, события дня). None — нет данных."""
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(0.05)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except (urllib.error.URLError, OSError, ValueError) as e:
            err = e
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    log("  не ответил", url, err)
    return None


def query_all(url, params):
    """action=query со всеми продолжениями (continue)."""
    params = dict(params, action="query")
    cont = {}
    while True:
        data = get(url, {**params, **cont})
        yield data
        if "continue" not in data:
            return
        cont = data["continue"]


def pmap(fn, items, workers=4):
    """fn для каждого элемента в несколько потоков (Википедия разрешает немного параллельных запросов), порядок сохраняется."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ------------------------------------------------------------------ 1. список важнейших статей
_HEAD_RE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")
_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
_SKIP_NS = ("file:", "image:", "category:", "wikipedia:", "template:", "help:", "portal:", "user:", "wp:", "special:")


def clean_heading(text):
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)   # [[Статья|подпись]] → подпись
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\(\s*\d[\d,]*\s*(?:articles?)?\s*\)", "", text)
    text = re.sub(r"'{2,}", "", text)
    return re.sub(r"\s+", " ", text).strip(" :")


def parse_vital(wikitext, default_cat):
    """[(категория, статья)] из разметки страницы Vital articles: пункты списков «# [[Статья]]» под заголовками."""
    out, heads = [], {}
    for line in wikitext.splitlines():
        m = _HEAD_RE.match(line.strip())
        if m:
            level = len(m.group(1))
            heads = {k: v for k, v in heads.items() if k < level}
            name = clean_heading(m.group(2))
            if name:
                heads[level] = name
            continue
        if not re.match(r"^\s*[#*:]", line):
            continue
        for link in _LINK_RE.findall(line):
            target = link.strip()
            if not target or target.startswith(":") or target.lower().startswith(_SKIP_NS):
                continue
            levels = sorted(heads)
            cat = " / ".join(heads[k] for k in levels[:2]) if levels else default_cat
            out.append((cat, target.replace("_", " ")))
            break
    return out


CAT_ROOT = "Category:Wikipedia level-4 vital articles by topic"


def vital_from_categories():
    """[(раздел, статья)] из категорий «Wikipedia level-4 vital articles in …» (туда попадают страницы обсуждения)."""
    subcats = []
    for data in query_all(EN, {"list": "categorymembers", "cmtitle": CAT_ROOT, "cmtype": "subcat", "cmlimit": "max"}):
        subcats += [m["title"] for m in data["query"]["categorymembers"]]
    log("подкатегорий важнейших статей:", len(subcats), subcats[:15])
    out = []
    for cat in subcats:
        tail = cat.split(" in ", 1)[1] if " in " in cat else ""
        section = next((k for k in SECTIONS if tail.lower() == k.lower()), None)
        if not section:
            section = next((k for k in SECTIONS if k.split()[0].lower()[:5] in tail.lower()), None)  # «Biological…»
        if not section:
            log("  пропускаю категорию", cat)
            continue
        n, queue, seen_cats = 0, [cat], {cat}
        while queue:  # и вложенные категории («… in People (Writers)»)
            current = queue.pop()
            for data in query_all(EN, {"list": "categorymembers", "cmtitle": current, "cmlimit": "max", "cmnamespace": "1|0|14"}):
                for m in data["query"]["categorymembers"]:
                    if m["ns"] == 14:
                        if m["title"] not in seen_cats and len(seen_cats) < 60:
                            seen_cats.add(m["title"])
                            queue.append(m["title"])
                        continue
                    title = m["title"].split(":", 1)[1] if m["title"].startswith("Talk:") else m["title"]
                    out.append((section, title))
                    n += 1
        log(" ", cat, "→", section, n)
    return out


def vital_articles():
    titles = []
    for data in query_all(EN, {"list": "allpages", "apnamespace": 4, "apprefix": PREFIX + "/", "aplimit": "max",
                               "apfilterredir": "nonredirects"}):
        titles += [p["title"] for p in data["query"]["allpages"]]
    pages = [t for t in titles if not re.search(r"Removed|Archive|Statistics|Header|Template|Count|Talk|Sandbox|Tally", t, re.I)]
    log("страниц Vital articles:", len(pages), pages[:60])
    result, seen = [], set()
    for batch in chunks(pages, 20):
        for data in query_all(EN, {"prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": "|".join(batch)}):
            for page in data["query"]["pages"]:
                if not page.get("revisions"):
                    continue
                rest = page["title"].split(PREFIX + "/", 1)[1]
                parts = rest.split("/")
                section = parts[0]
                if section not in SECTIONS:
                    continue
                sub = " / ".join(parts[1:]) or section
                text = page["revisions"][0]["slots"]["main"]["content"]
                found = parse_vital(text, sub)
                log("  ", page["title"], "→", len(found), "" if found else repr(text[:600]))
                for cat, article in found:
                    if len(parts) > 1 and not cat.startswith(sub):
                        cat = sub + " / " + cat if cat != sub else sub
                    key = article.lower()
                    if key not in seen:
                        seen.add(key)
                        result.append((section, cat, article))
    log("важнейших статей по страницам:", len(result))
    # Страницы могли поменять разметку — добираем по категориям (раздел без подраздела)
    try:
        extra = vital_from_categories()
    except Exception as e:
        log("категории не прочитались:", e)
        extra = []
    for section, article in extra:
        key = article.lower()
        if key not in seen:
            seen.add(key)
            result.append((section, section, article))
    log("важнейших статей всего:", len(result))
    return result


def ru_titles(en_titles):
    """Английское название → русская статья (через межъязыковые ссылки)."""
    found = {}

    def fetch(batch):
        try:
            return batch, list(query_all(EN, {"prop": "langlinks", "lllang": "ru", "lllimit": "max", "redirects": 1, "titles": "|".join(batch)}))
        except Exception as e:
            log("  пропускаю пачку из", len(batch), "названий:", e)
            return batch, []
    for batch, responses in pmap(fetch, list(chunks(en_titles, 50))):
        rename = {}
        for data in responses:
            q = data.get("query", {})
            for n in q.get("normalized", []) + q.get("redirects", []):
                rename[n["from"]] = n["to"]
            for page in q.get("pages", []):
                for ll in page.get("langlinks", []):
                    if ll.get("lang") == "ru":
                        found[page["title"]] = ll["title"]
        for t in batch:
            final = t
            for _ in range(3):
                final = rename.get(final, final)
            if final in found:
                found[t] = found[final]
    return found


def sparql_ru(query):
    """Объекты Wikidata из запроса → их русские статьи."""
    data = get(SPARQL, {"query": "PREFIX wd: <http://www.wikidata.org/entity/>\n" + query})
    ids = [b["item"]["value"].rsplit("/", 1)[1] for b in data["results"]["bindings"]]
    titles = []
    for batch in chunks(ids, 50):
        data = get(WD, {"action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks", "sitefilter": "ruwiki"}, tries=8)
        for qid in batch:
            link = data.get("entities", {}).get(qid, {}).get("sitelinks", {}).get("ruwiki")
            if link:
                titles.append(link["title"])
    return titles


def search_category(cat, limit):
    """Статьи из категории русской Википедии со всеми подкатегориями, самые известные (больше ссылок) первыми."""
    titles = []
    for query in (f'deepcat:"{cat}"', f'incategory:"{cat}"'):
        offset = 0
        try:
            while len(titles) < limit:
                data = get(RU, {"action": "query", "list": "search", "srsearch": query, "srnamespace": 0,
                                "srlimit": min(500, limit - len(titles)), "sroffset": offset,
                                "srsort": "incoming_links_desc", "srprop": "", "srinfo": ""})
                hits = [h["title"] for h in data.get("query", {}).get("search", [])]
                titles += [t for t in hits if t not in titles]
                if "continue" not in data or not hits:
                    break
                offset = data["continue"]["sroffset"]
        except Exception as e:
            log("  поиск", query, "не удался:", e)
        if titles:
            break
    return titles[:limit]


def _valid(m, d):
    try:
        datetime.date(2024, m, d)
        return True
    except ValueError:
        return False


def on_this_day(previous=None):
    """«Этот день в истории»: {"ММ-ДД": [[год, событие], …]} на все 366 дней (русская Википедия).
    Дни, которые не успели загрузиться, берутся из прошлой сборки (previous)."""
    days = {}
    dates = [(m, d) for m in range(1, 13) for d in range(1, 32) if _valid(m, d)]
    if rest("https://api.wikimedia.org/feed/v1/wikipedia/ru/onthisday/events/01/01") is None:
        log("  «этот день в истории» недоступен на русском")
        return dict(previous or {})
    t0 = time.monotonic()

    def fetch(md):
        if time.monotonic() - t0 > DAYS_LIMIT or out_of_time("этот день", BUDGET * 0.6):
            return None
        return rest(f"https://api.wikimedia.org/feed/v1/wikipedia/ru/onthisday/events/{md[0]:02d}/{md[1]:02d}")
    feeds = pmap(fetch, dates)
    for (month, day), data in zip(dates, feeds):
        events = []
        for ev in (data or {}).get("events", []):
            text = clean_extract(ev.get("text", ""))
            if ev.get("year") and 15 <= len(text) <= 300:
                events.append([ev["year"], text])
        events.sort(key=lambda e: -e[0])
        key = f"{month:02d}-{day:02d}"
        if events:
            days[key] = events[:12]
        elif (previous or {}).get(key):
            days[key] = previous[key]
    log("событий по дням:", sum(len(v) for v in days.values()), f"(загрузка {int(time.monotonic() - t0)} с)")
    return days


def today_feed():
    """Что читают в русской Википедии (за вчера) и статья дня: {"date", "popular": [[название, просмотры, кратко]], "featured"}."""
    day = datetime.date.today() - datetime.timedelta(days=1)
    data = rest(f"https://api.wikimedia.org/feed/v1/wikipedia/ru/featured/{day:%Y/%m/%d}") or {}
    popular = []
    for a in (data.get("mostread") or {}).get("articles", []):
        title = a.get("normalizedtitle") or a.get("title", "").replace("_", " ")
        info = (a.get("description") or "") + " " + (a.get("extract") or "")
        if not title or _NEWS_SKIP.search(title + " " + info):
            continue
        popular.append([title, a.get("views", 0), clean_extract(a.get("extract") or "")[:300]])
    featured = None
    tfa = data.get("tfa")
    if tfa:
        featured = [tfa.get("normalizedtitle") or tfa.get("title", "").replace("_", " "), clean_extract(tfa.get("extract") or "")]
    log("популярное за", day, ":", len(popular), "статей; статья дня:", featured[0] if featured else "—")
    return {"date": day.isoformat(), "popular": popular[:40], "featured": featured}


# ------------------------------------------------------------------ 2. тексты статей
_ABBR = ("г", "гг", "в", "вв", "др", "т", "е", "н", "э", "лат", "англ", "нем", "фр", "франц", "греч", "др.-греч", "ок", "им",
         "ст", "род", "см", "напр", "т.е", "т.н", "св", "кн", "ул", "пр", "млн", "млрд", "тыс", "км", "м", "р", "араб", "исп",
         "итал", "кит", "яп", "укр", "белор", "польск", "тур", "перс", "санскр", "ивр", "нидерл", "швед", "норв", "дат", "фин")


def sentences(text):
    """Разбить русский текст на предложения, не ломая «А. С. Пушкин», «1799 г.», «лат.»."""
    parts, start = [], 0
    for m in re.finditer(r"[.!?…]\s+(?=[«\"(]?[A-ZА-ЯЁ0-9])", text):
        before = text[start:m.start() + 1]
        word = re.search(r"([\w.-]+)\.$", before)
        if word and (word.group(1).lower() in _ABBR or (len(word.group(1)) == 1 and word.group(1).isupper())):
            continue
        parts.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def clean_extract(text):
    text = text.replace("́", "").replace("̀", "").replace("\xa0", " ")
    text = re.sub(r"\[[^\]]*\]", "", text)                       # транскрипции [ˈæ…], сноски
    text = re.sub(r"\(\s*[;,]\s*", "(", text)
    text = re.sub(r"\s*[;,]\s*\)", ")", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    out = ""
    for s in sentences(text):
        if out and len(out) + len(s) > MAX_TEXT:
            break
        out = (out + " " + s).strip()
    if len(out) > MAX_TEXT + 200:
        out = out[:MAX_TEXT + 200].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"
    return out


def ru_pages(titles):
    """Русские статьи: {название: [текст, id Wikidata, картинка (файл на Викискладе), число других языков]}."""
    pages = {}
    batches = list(chunks(titles, 20))

    def fetch(item):
        n, batch = item
        if out_of_time("тексты статей", 6 * 60):   # 6 минут — на описания из Wikidata и сохранение
            return []
        if n % 100 == 0:
            log("  тексты статей:", n * 20, "из", len(titles), f"({int((time.monotonic() - START) // 60)} мин)")
        try:
            return list(query_all(RU, {"prop": "extracts|pageprops|pageimages|langlinkscount", "exintro": 1, "explaintext": 1, "exlimit": 20,
                                       "ppprop": "wikibase_item", "piprop": "name", "pilicense": "free", "pilimit": 20,
                                       "redirects": 1, "titles": "|".join(batch)}))
        except Exception as e:
            log("  пропускаю пачку из", len(batch), "статей:", e)
            return []
    for responses in pmap(fetch, list(enumerate(batches))):
        for data in responses:
            q = data.get("query", {})
            for page in q.get("pages", []):
                if page.get("missing"):
                    continue
                cur = pages.setdefault(page["title"], ["", None, "", 0])
                if page.get("extract"):
                    cur[0] = page["extract"]
                if page.get("pageprops", {}).get("wikibase_item"):
                    cur[1] = page["pageprops"]["wikibase_item"]
                if page.get("pageimage"):
                    cur[2] = page["pageimage"]
                if page.get("langlinkscount"):
                    cur[3] = page["langlinkscount"]  # в скольких ещё Википедиях есть статья — мера известности
            for r in q.get("redirects", []) + q.get("normalized", []):
                pages.setdefault("→" + r["from"], r["to"])
    return pages


def wikidata(qids):
    """{id: (описание, [другие названия])} на русском. Сбой Wikidata не останавливает сборку — тема будет без описания."""
    out = {}

    def fetch(batch):
        if out_of_time("описания Wikidata", 90):
            return {}
        try:
            return get(WD, {"action": "wbgetentities", "ids": "|".join(batch), "props": "descriptions|aliases", "languages": "ru"}, tries=8)
        except Exception as e:
            log("  Wikidata не ответила для", len(batch), "тем:", e)
            return {}
    for data in pmap(fetch, list(chunks(sorted(set(qids)), 50))):
        for qid, e in data.get("entities", {}).items():
            desc = e.get("descriptions", {}).get("ru", {}).get("value", "")
            aliases = [a["value"] for a in e.get("aliases", {}).get("ru", [])]
            out[qid] = (desc, aliases)
    return out


# ------------------------------------------------------------------ сборка
def build(limit=None, previous=None):
    topics = vital_articles()
    if limit:
        topics = topics[:limit]
    ru = ru_titles([a for _, _, a in topics])
    log("есть в русской Википедии:", len({a for _, _, a in topics if a in ru}), "из", len(topics))
    # астрономия из важнейших статей — тоже в раздел «Космос»
    wanted = [(SPACE_SECTION if re.search(r"Astronom|Space|Solar System", c) else SECTIONS[s], c, ru[a]) for s, c, a in topics if a in ru]
    feed, days = {"date": None, "popular": [], "featured": None}, {}
    if not limit:
        feed = today_feed()
        wanted += [(NEWS_SECTION, "Популярное за день", t) for t, _, _ in feed["popular"]]
        if feed["featured"]:
            wanted.append((NEWS_SECTION, "Статья дня", feed["featured"][0]))
        for cat, root, n in SPACE:
            titles = search_category(root, n)
            log(SPACE_SECTION, "/", cat + ":", len(titles))
            wanted += [(SPACE_SECTION, cat, t) for t in titles]
        days = on_this_day((previous or {}).get("days"))
        for cat, query in EXTRA:
            try:
                titles = sparql_ru(query)
                log(cat + ":", len(titles))
                wanted += [(EXTRA_SECTION, cat, t) for t in titles]
            except Exception as e:  # дополнение необязательно
                log("пропускаю", cat, e)

    seen, uniq = set(), []
    for item in wanted:
        if item[2] not in seen:
            seen.add(item[2])
            uniq.append(item)
    pages = ru_pages([t for _, _, t in uniq])
    resolve = lambda t: pages.get("→" + t, t)
    qids = [pages[resolve(t)][1] for _, _, t in uniq if isinstance(pages.get(resolve(t)), list) and pages[resolve(t)][1]]
    wd = wikidata(qids)

    sections = list(SECTIONS.values()) + [SPACE_SECTION, EXTRA_SECTION, NEWS_SECTION]
    cats, cat_index, items, done = [], {}, [], set()
    for section, cat, title in uniq:
        real = resolve(title)
        page = pages.get(real)
        if not isinstance(page, list) or real in done:
            continue
        text = clean_extract(page[0])
        if len(text) < 40:
            continue
        done.add(real)
        desc, aliases = wd.get(page[1], ("", []))
        pop = page[3] + 1 if len(page) > 3 else 0
        key = (section, cat)
        if key not in cat_index:
            cat_index[key] = len(cats)
            cats.append([sections.index(section), cat])
        aliases = [a for a in aliases if 2 <= len(a) <= 40 and a != real][:6]
        items.append([real, desc, cat_index[key], text, aliases, pop, page[2] if len(page) > 2 else ""])
    return {
        "version": datetime.date.today().isoformat(),
        "source": "Википедия (Vital articles, уровень 4; русские статьи) и Wikidata",
        "license": "Тексты — CC BY-SA 4.0 (Википедия), описания — CC0 (Wikidata)",
        "sections": sections,
        "cats": cats,
        "items": items,
        "days": days,
        "news": feed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "encyclopedia.json"))
    parser.add_argument("--limit", type=int, help="только первые N тем (для проверки)")
    args = parser.parse_args()
    previous = None
    if os.path.exists(args.output):        # прошлая сборка — запас для того, что сегодня не успело загрузиться
        try:
            with open(args.output, encoding="utf-8") as f:
                previous = json.load(f)
        except ValueError:
            previous = None
    data = build(args.limit, previous)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log("Готово:", len(data["items"]), "тем,", len(data["cats"]), "подразделов →", args.output,
        f"({os.path.getsize(args.output) // 1024} КБ)")
    print(len(data["items"]))


if __name__ == "__main__":
    main()
