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
PREFIX = "Vital articles/Level/4"

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

# Дополнение: (подраздел, запрос SPARQL). ?item — объект, у которого есть статья в русской Википедии.
EXTRA = [
    ("Регионы России", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q43263 . FILTER NOT EXISTS { ?item wdt:P576 [] } }"""),
    ("Города России", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q7930989; wdt:P17 wd:Q159; wdt:P1082 ?pop .
          FILTER(?pop >= 40000) }"""),
    ("Области Беларуси", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31 wd:Q209077 }"""),
    ("Города Беларуси", """
        SELECT DISTINCT ?item WHERE { ?item wdt:P31/wdt:P279* wd:Q515; wdt:P17 wd:Q184; wdt:P1082 ?pop . FILTER(?pop >= 15000) }"""),
    ("Известные люди России и СССР", """
        SELECT ?item ?n WHERE { ?item wdt:P31 wd:Q5; wdt:P27 ?c; wikibase:sitelinks ?n .
          VALUES ?c { wd:Q159 wd:Q15180 wd:Q34266 } FILTER(?n >= 60) } ORDER BY DESC(?n) LIMIT 700"""),
    ("Известные люди Беларуси", """
        SELECT ?item ?n WHERE { ?item wdt:P31 wd:Q5; wdt:P27 wd:Q184; wikibase:sitelinks ?n . FILTER(?n >= 15) }
        ORDER BY DESC(?n) LIMIT 150"""),
]

MAX_TEXT = 420


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def get(url, params, tries=6):
    """GET к API Википедии/Wikidata с повторами и паузами (вежливо: не больше ~10 запросов в секунду)."""
    params = dict(params)
    if url != SPARQL:
        params.update(format="json", formatversion="2", maxlag="5")
    else:
        params["format"] = "json"
    full = url + "?" + urllib.parse.urlencode(params)
    delay = 2
    for attempt in range(tries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("error", {}).get("code") == "maxlag":
                raise RuntimeError("maxlag")
            time.sleep(0.1)
            return data
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as e:
            if attempt == tries - 1:
                raise
            log("  повтор через", delay, "с:", e)
            time.sleep(delay)
            delay *= 2


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
        if not re.match(r"^\s*[#*]", line):
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


def vital_articles():
    titles = []
    for data in query_all(EN, {"list": "allpages", "apnamespace": 4, "apprefix": PREFIX + "/", "aplimit": "max"}):
        titles += [p["title"] for p in data["query"]["allpages"]]
    pages = [t for t in titles if not re.search(r"Removed|Archive|Statistics|Header|Template|Count|Talk|Sandbox|Tally", t, re.I)]
    log("страниц Vital articles:", len(pages))
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
                for cat, article in parse_vital(page["revisions"][0]["slots"]["main"]["content"], sub):
                    if len(parts) > 1 and not cat.startswith(sub):
                        cat = sub + " / " + cat if cat != sub else sub
                    key = article.lower()
                    if key not in seen:
                        seen.add(key)
                        result.append((section, cat, article))
    log("важнейших статей:", len(result))
    return result


def ru_titles(en_titles):
    """Английское название → русская статья (через межъязыковые ссылки)."""
    found = {}
    for batch in chunks(en_titles, 50):
        rename = {}
        for data in query_all(EN, {"prop": "langlinks", "lllang": "ru", "lllimit": "max", "redirects": 1, "titles": "|".join(batch)}):
            q = data["query"]
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
        data = get(WD, {"action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks", "sitefilter": "ruwiki"})
        for qid in batch:
            link = data.get("entities", {}).get(qid, {}).get("sitelinks", {}).get("ruwiki")
            if link:
                titles.append(link["title"])
    return titles


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
    """Русские статьи: {название: (текст, id Wikidata)}."""
    pages = {}
    for batch in chunks(titles, 20):
        for data in query_all(RU, {"prop": "extracts|pageprops", "exintro": 1, "explaintext": 1, "exlimit": 20,
                                   "ppprop": "wikibase_item", "redirects": 1, "titles": "|".join(batch)}):
            q = data["query"]
            for page in q.get("pages", []):
                if page.get("missing"):
                    continue
                cur = pages.setdefault(page["title"], ["", None])
                if page.get("extract"):
                    cur[0] = page["extract"]
                if page.get("pageprops", {}).get("wikibase_item"):
                    cur[1] = page["pageprops"]["wikibase_item"]
            for r in q.get("redirects", []) + q.get("normalized", []):
                pages.setdefault("→" + r["from"], r["to"])
    return pages


def wikidata(qids):
    """{id: (описание, [другие названия])} на русском."""
    out = {}
    for batch in chunks(sorted(set(qids)), 50):
        data = get(WD, {"action": "wbgetentities", "ids": "|".join(batch), "props": "descriptions|aliases", "languages": "ru"})
        for qid, e in data.get("entities", {}).items():
            desc = e.get("descriptions", {}).get("ru", {}).get("value", "")
            aliases = [a["value"] for a in e.get("aliases", {}).get("ru", [])]
            out[qid] = (desc, aliases)
    return out


# ------------------------------------------------------------------ сборка
def build(limit=None):
    topics = vital_articles()
    if limit:
        topics = topics[:limit]
    ru = ru_titles([a for _, _, a in topics])
    log("есть в русской Википедии:", len({a for _, _, a in topics if a in ru}), "из", len(topics))
    wanted = [(SECTIONS[s], c, ru[a]) for s, c, a in topics if a in ru]
    if not limit:
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

    sections = list(SECTIONS.values()) + [EXTRA_SECTION]
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
        key = (section, cat)
        if key not in cat_index:
            cat_index[key] = len(cats)
            cats.append([sections.index(section), cat])
        aliases = [a for a in aliases if 2 <= len(a) <= 40 and a != real][:6]
        items.append([real, desc, cat_index[key], text, aliases])
    return {
        "version": datetime.date.today().isoformat(),
        "source": "Википедия (Vital articles, уровень 4; русские статьи) и Wikidata",
        "license": "Тексты — CC BY-SA 4.0 (Википедия), описания — CC0 (Wikidata)",
        "sections": sections,
        "cats": cats,
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "encyclopedia.json"))
    parser.add_argument("--limit", type=int, help="только первые N тем (для проверки)")
    args = parser.parse_args()
    data = build(args.limit)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log("Готово:", len(data["items"]), "тем,", len(data["cats"]), "подразделов →", args.output,
        f"({os.path.getsize(args.output) // 1024} КБ)")
    print(len(data["items"]))


if __name__ == "__main__":
    main()
