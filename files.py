"""Файлы в чате Rai: страница читает их прямо в браузере (files.js) и присылает после метки [[file]] JSON —
[{name, size, ext, kind, label, lang, meta, text, tables}]. Здесь из этого собирается ответ:
что это за файл, сведения о нём, главное из содержимого (пересказ), таблица для Excel/CSV, функции и классы для кода,
список файлов для архива, расшифровка речи для звука и видео — и ответ на вопрос по содержимому файла.
"""

import json
import math
import re
from collections import Counter

import learning
import nlp

MARK = "[[file]]"
_ICONS = {"pdf": "📕", "document": "📄", "code": "💻", "text": "📄", "archive": "🗜", "audio": "🎵", "video": "🎬", "image": "🖼",
          "font": "🔤", "binary": "📦"}
_GENERIC_ASK = re.compile(r"^\s*(?:что\s+(?:в|на|это\s+за)\s+(?:этом\s+)?(?:файл|документ)\w*|расскажи\s+главное|что\s+это|"
                          r"что\s+в\s+этом\s+файле\?\s*расскажи\s+главное|прочитай|открой|посмотри)[\s?!.]*", re.I)
_SUMMARY_ASK = re.compile(r"пересказ|кратк|главн|о\s+ч[её]м|суть|резюм|summary|тезис", re.I)


def split(raw):
    """(вопрос, [файлы], остаток после файлов — например, [[screen]] с картинками) или (raw, None, "")."""
    if MARK not in (raw or ""):
        return raw, None, ""
    question, _, rest = raw.partition(MARK)
    data_part, sep, tail = rest.partition("\n[[screen]]")
    try:
        files = json.loads(data_part)
    except ValueError:
        files = None
    if isinstance(files, dict):
        files = [files]
    return question.strip(), (files if isinstance(files, list) and files else None), (sep.strip() + tail if sep else "")


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z0-9«\"(])|\n{2,}", text or "") if 25 <= len(s.strip()) <= 400]


_SERVICE_LINE = re.compile(r"^\s*(?:— Страница \d+ —|Слайд \d+:|Лист «[^»]*» \(\d+ строк\):)\s*$", re.M)


def summarize(text, n=5):
    """Пересказ: самые содержательные предложения (по частоте значимых слов), в порядке текста."""
    text = _SERVICE_LINE.sub("", text or "")
    sents = _sentences(text) or [l.strip() for l in text.splitlines() if 15 <= len(l.strip()) <= 300]
    if len(sents) <= n:
        return sents
    freq = Counter(w for s in sents for w in set(nlp.tokens(s)) if w not in nlp.GENERIC and len(w) > 3)
    if not freq:
        return sents[:n]
    top = max(freq.values())

    def score(i, s):
        words = [w for w in nlp.tokens(s) if w in freq]
        return sum(freq[w] / top for w in words) / math.sqrt(len(nlp.tokens(s)) + 1) + (0.4 if i < 3 else 0)
    best = sorted(sorted(range(len(sents)), key=lambda i: -score(i, sents[i]))[:n])
    return [sents[i] for i in best]


def answer_question(text, question, n=3):
    """Самые подходящие к вопросу места в тексте файла (или [] — ничего похожего)."""
    want = {w for w in nlp.tokens(question) if w not in nlp.GENERIC and len(w) > 2}
    if not want:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[А-ЯЁA-Z])", text or "") if len(p.strip()) >= 20]
    df = Counter(w for p in paras for w in set(nlp.tokens(p)))
    scored = []
    for i, p in enumerate(paras):
        have = set(nlp.tokens(p))
        hit = learning.soft_hit(want, have)
        if hit:
            scored.append((sum(1 / math.log(2 + df[w]) for w in hit) * len(hit) / len(want), i, p))
    scored.sort(reverse=True)
    good = [x for x in scored if x[0] >= 0.3 and len(learning.soft_hit(want, set(nlp.tokens(x[2])))) * 2 >= min(len(want), 4)]
    if not good:
        return []
    top = good[0][0]
    return [p[:600] for score, _, p in good[:n] if score >= top * 0.75]  # самое подходящее — первым


def _code_outline(text, lang):
    """Функции, классы и импорты в коде."""
    defs = re.findall(r"^\s*(?:async\s+)?(?:def|function|func|fn|fun|sub|procedure)\s+([A-Za-z_]\w*)", text, re.M)
    defs += re.findall(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\(", text, re.M)
    defs += re.findall(r"^\s*(?:public|private|protected|static|\s)*[\w<>\[\],]+\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{", text, re.M)
    classes = re.findall(r"^\s*(?:export\s+)?(?:abstract\s+)?(?:class|struct|interface|enum|trait)\s+([A-Za-z_]\w*)", text, re.M)
    imports = re.findall(r"^\s*(?:import|from|#include|using|require|use)\s+([^\s;]+)", text, re.M)
    skip = {"if", "for", "while", "switch", "catch", "return", "else"}
    defs = [d for d in dict.fromkeys(defs) if d not in skip]
    return defs[:20], list(dict.fromkeys(classes))[:12], list(dict.fromkeys(imports))[:12]


def _table_md(rows, limit_rows=8, limit_cols=6):
    rows = [r[:limit_cols] for r in rows if any(str(c).strip() for c in r)][:limit_rows + 1]
    if len(rows) < 2:
        return ""
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]
    cell = lambda c: str(c).replace("|", "/").replace("\n", " ")[:40] or " "
    head = "| " + " | ".join(cell(c) for c in rows[0]) + " |"
    return "\n".join([head, "|" + "---|" * width] + ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows[1:]])


def _csv_rows(text):
    lines = [l for l in (text or "").splitlines() if l.strip()][:40]
    if len(lines) < 2:
        return []
    sep = max([";", ",", "\t", "|"], key=lambda d: sum(l.count(d) for l in lines[:5]))
    return [[c.strip().strip('"') for c in l.split(sep)] for l in lines]


def describe_one(f, question=""):
    name, kind, label = f.get("name") or "файл", f.get("kind") or "binary", f.get("label") or "файл"
    meta = {k: v for k, v in (f.get("meta") or {}).items() if v not in (None, "")}
    text = f.get("text") or ""
    lines = [f"### {_ICONS.get(kind, '📎')} {name}", f"**{label[:1].upper() + label[1:]}**" + (f" · {meta.pop('размер')}" if "размер" in meta else "")]
    sha = meta.pop("SHA-256", "")
    info = [f"- {k[:1].upper() + k[1:]}: {v}" for k, v in meta.items() if k != "ошибка чтения"]
    if info:
        lines += ["", *info]
    if meta.get("ошибка чтения"):
        lines += ["", f"⚠️ Прочитать полностью не получилось: {meta['ошибка чтения']}"]

    asked = question and not _GENERIC_ASK.fullmatch(question) and not _SUMMARY_ASK.search(question)
    if asked and text:
        found = answer_question(text, question)
        if found:
            lines += ["", "**Ответ по файлу:**", ""] + [f"> {p}" for p in found]
        else:
            lines += ["", f"В файле не нашёл ничего про «{question[:80]}». Включите **Rai Нейро** — нейросеть прочитает файл целиком и ответит своими словами."]

    ext = (f.get("ext") or "").lower()
    if kind == "code":
        defs, classes, imports = _code_outline(text, f.get("lang"))
        lines += ["", f"Язык: **{f.get('lang') or ext}**."]
        if classes:
            lines.append("Классы: " + ", ".join(f"`{c}`" for c in classes))
        if defs:
            lines.append("Функции: " + ", ".join(f"`{d}`" for d in defs))
        if imports:
            lines.append("Подключает: " + ", ".join(f"`{i}`" for i in imports))
        if not asked:
            preview = "\n".join(text.splitlines()[:25])
            lines += ["", f"```{(f.get('lang') or ext).split()[0].lower()}\n{preview}\n```",
                      "Могу объяснить код, найти ошибки или улучшить — откройте его во вкладке **Code** или напишите «проверь код»."]
    elif f.get("tables") or ext in ("csv", "tsv"):
        tables = f.get("tables") or [{"name": name, "rows": _csv_rows(text)}]
        for t in tables[:3]:
            rows = t.get("rows") or []
            md = _table_md(rows)
            if md:
                lines += ["", f"**{t.get('name') or 'Таблица'}** — {len(rows)} строк, {max(len(r) for r in rows)} столбцов:", "", md]
    elif kind == "archive":
        listing = text.split("\n\n")[0].splitlines()[1:16]
        if listing:
            lines += ["", "Внутри:", *[f"- {x}" for x in listing]]
    elif kind in ("audio", "video"):
        if text:
            lines += ["", "**Расшифровка речи:**", "", f"> {text[:1500]}" + ("…" if len(text) > 1500 else "")]
        elif kind == "audio":
            lines += ["", "Речь расшифровать не получилось (нет слов или запись не открылась)."]
    elif ext in ("json", "jsonl", "ipynb") and text and not asked:
        try:
            data = json.loads(text if ext != "jsonl" else text.splitlines()[0])
        except ValueError:
            data = None
        if isinstance(data, dict):
            lines += ["", "Ключи: " + ", ".join(f"`{k}`" for k in list(data)[:20])]
        elif isinstance(data, list):
            lines += ["", f"Список из {len(data)} элементов" + (f", у элементов ключи: {', '.join(f'`{k}`' for k in list(data[0])[:12])}"
                                                               if data and isinstance(data[0], dict) else "")]
        lines += ["", f"```json\n{text[:1200]}\n```"]
    elif kind == "document" and ext in ("pptx", "odp", "ppt") and text and not asked:
        slides = [b.strip() for b in re.split(r"\n*Слайд \d+:\n", "\n" + text) if b.strip()]
        if slides:
            lines += ["", "**Слайды:**", *[f"{i}. " + " — ".join(x.strip() for x in sl.splitlines()[:3] if x.strip())[:160]
                                           for i, sl in enumerate(slides[:12], 1)]]
    elif kind in ("document", "pdf", "text") and text and not asked:
        main = summarize(text, 5)
        if main:
            lines += ["", "**Главное:**", *[f"- {s}" for s in main]]
        words = len(re.findall(r"\w+", text))
        if words > 30:
            lines.append(f"\n*Всего ~{words} слов — около {max(1, round(words / 180))} мин чтения.*")
    elif kind == "binary" and not text:
        lines += ["", "Это не текстовый файл — содержимое прочитать нельзя, но вот что о нём известно."]
    if sha and kind in ("binary", "archive", "font"):
        lines.append(f"\nSHA-256: `{sha[:16]}…` (для проверки, что файл не изменён)")
    return "\n".join(lines)


def describe(files, question=""):
    """Ответ про прикреплённые файлы."""
    parts = [describe_one(f, question) for f in files[:6]]
    note = ("\n\n*Файлы прочитаны прямо в вашем браузере — на сервер они не отправлялись. Rai запомнил документы: можно спрашивать "
            "по ним и в других чатах.*")
    return "\n\n---\n\n".join(parts) + note
