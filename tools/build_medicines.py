"""Собрать базу лекарств Rai (medicines.json) — все действующие вещества с кодом АТХ из Wikidata.

Запускается на GitHub (workflow «Лекарства Rai»), там есть доступ к Wikidata и Википедии:

    python tools/build_medicines.py -o medicines.json

Для каждого вещества: русское и английское название, другие названия, краткое описание, коды АТХ, группа,
от чего применяют (Wikidata P2175), торговые названия (P3780 — препараты с этим веществом), рецептурный статус
по странам (P3493 с уточнением страны) и начало статьи русской Википедии.

Данные Wikidata — CC0, тексты Википедии — CC BY-SA 4.0 (Rai указывает источник). Только стандартная библиотека Python.
"""

import argparse
import concurrent.futures
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "RaiMedicinesBuilder/1.0 (https://github.com/rteaminfo1-source/rai)"
WD = "https://www.wikidata.org/w/api.php"
RU = "https://ru.wikipedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"


def fetch_json(url, params=None, tries=5):
    """GET → JSON, с повторами при ошибках и ограничениях скорости."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            wait = 5 * (attempt + 1)
            if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                wait = int(e.headers.get("Retry-After") or 30)
            print(f"  повтор через {wait} с: {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("не получилось: " + url[:120])


def atc_items():
    """{Q-id: [коды АТХ]} — все элементы Wikidata с кодом АТХ (P267)."""
    data = fetch_json(SPARQL, {"query": "SELECT ?item ?atc WHERE { ?item wdt:P267 ?atc . }", "format": "json"})
    out = {}
    for row in data["results"]["bindings"]:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        out.setdefault(qid, []).append(row["atc"]["value"])
    return out


def entities(ids, props="labels|aliases|descriptions|claims|sitelinks", langs="ru|en"):
    """wbgetentities пачками по 50 (параллельно)."""
    ids = list(dict.fromkeys(ids))
    chunks = [ids[i:i + 50] for i in range(0, len(ids), 50)]
    out = {}

    def one(chunk):
        return fetch_json(WD, {"action": "wbgetentities", "ids": "|".join(chunk), "props": props, "languages": langs,
                               "sitefilter": "ruwiki", "format": "json"}).get("entities", {})
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        for part in pool.map(one, chunks):
            out.update(part)
    return out


def label(ent, lang="ru"):
    for lg in (lang, "en") if lang == "ru" else (lang,):
        v = (ent.get("labels") or {}).get(lg, {}).get("value")
        if v:
            return v
    return ""


def claim_ids(ent, prop):
    out = []
    for c in (ent.get("claims") or {}).get(prop, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and v.get("id"):
            out.append((v["id"], c.get("qualifiers") or {}))
    return out


def extracts(titles):
    """Начало статей русской Википедии (до 3 предложений), пачками по 20."""
    titles = list(dict.fromkeys(titles))
    out = {}

    def one(chunk):
        data = fetch_json(RU, {"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "exsentences": 3,
                               "exlimit": 20, "redirects": 1, "titles": "|".join(chunk), "format": "json"})
        res = {}
        for page in (data.get("query", {}).get("pages") or {}).values():
            if page.get("extract"):
                res[page["title"]] = page["extract"]
        for r in data.get("query", {}).get("redirects", []):   # заголовок мог поменяться
            if r.get("to") in res:
                res[r["from"]] = res[r["to"]]
        return res
    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        for part in pool.map(one, [titles[i:i + 20] for i in range(0, len(titles), 20)]):
            out.update(part)
    return out


def clean(text, limit=520):
    text = re.sub(r"\s*\([^()]*(?:лат\.|англ\.|МНН|IUPAC|ИЮПАК)[^()]*\)", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    return cut[:cut.rfind(". ") + 1] if ". " in cut else cut.rstrip() + "…"


def build(limit=0):
    t0 = time.time()
    atc = atc_items()
    ids = list(atc)[:limit] if limit else list(atc)
    print(f"веществ с кодом АТХ: {len(ids)}", file=sys.stderr)
    ents = entities(ids)
    refs = set()
    for e in ents.values():
        for prop in ("P2175", "P279", "P3780", "P3493"):
            for qid, quals in claim_ids(e, prop):
                refs.add(qid)
                for q in quals.get("P1001", []):     # страна (applies to jurisdiction)
                    v = q.get("datavalue", {}).get("value")
                    if isinstance(v, dict) and v.get("id"):
                        refs.add(v["id"])
    print(f"связанных элементов: {len(refs)}", file=sys.stderr)
    names = {qid: label(e) for qid, e in entities(list(refs), props="labels").items()}
    ru_titles = {qid: e["sitelinks"]["ruwiki"]["title"] for qid, e in ents.items() if (e.get("sitelinks") or {}).get("ruwiki")}
    texts = extracts(list(ru_titles.values()))
    print(f"статей русской Википедии: {len(texts)}", file=sys.stderr)

    items = []
    for qid in ids:
        e = ents.get(qid)
        if not e or "missing" in e:
            continue
        ru, en = label(e, "ru"), (e.get("labels") or {}).get("en", {}).get("value", "")
        if not ru and not en:
            continue
        aliases = [a["value"] for lg in ("ru", "en") for a in (e.get("aliases") or {}).get(lg, [])]
        uses = [names.get(q) for q, _ in claim_ids(e, "P2175")]
        classes = [names.get(q) for q, _ in claim_ids(e, "P279")]
        brands = [names.get(q) for q, _ in claim_ids(e, "P3780")]
        rx = {}
        for q, quals in claim_ids(e, "P3493"):
            for j in quals.get("P1001", []):
                v = j.get("datavalue", {}).get("value")
                if isinstance(v, dict) and names.get(v.get("id")) and names.get(q):
                    rx[names[v["id"]]] = names[q]
        item = {"id": qid, "n": ru or en, "en": en, "al": list(dict.fromkeys(a for a in aliases if a and len(a) < 60))[:10],
                "d": (e.get("descriptions") or {}).get("ru", {}).get("value", ""), "atc": atc[qid][:4],
                "cls": [c for c in dict.fromkeys(classes) if c][:4], "for": [u for u in dict.fromkeys(uses) if u][:12],
                "brands": [b for b in dict.fromkeys(brands) if b and b.lower() not in (ru.lower(), en.lower())][:15], "rx": rx}
        title = ru_titles.get(qid)
        if title and texts.get(title):
            item["x"] = clean(texts[title])
        items.append({k: v for k, v in item.items() if v not in ("", [], {})})
    items.sort(key=lambda it: (0 if it.get("x") else 1, 0 if it["n"] != it.get("en") else 1, it["n"].lower()))
    print(f"готово: {len(items)} препаратов за {round(time.time() - t0)} с", file=sys.stderr)
    return {"built": datetime.date.today().isoformat(), "source": "Wikidata (CC0), Википедия (CC BY-SA 4.0)", "items": items}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out", default="medicines.json")
    parser.add_argument("--limit", type=int, default=0, help="только первые N веществ (для проверки)")
    args = parser.parse_args()
    data = build(args.limit)
    if len(data["items"]) < (50 if args.limit else 1000):
        sys.exit(f"слишком мало препаратов ({len(data['items'])}) — файл не перезаписан")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("записано:", args.out)


if __name__ == "__main__":
    main()
