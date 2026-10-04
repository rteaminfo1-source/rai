"""Самообучение Rai — запоминает то, чего не знал, и учится на оценках.

  • выученные ответы (вопрос → ответ): Rai не знал, а ответила нейросеть — ответ запоминается; человек нажал 👍 под
    ответом — тоже. В следующий раз Rai отвечает сам, даже без нейросети и без интернета;
  • 👎 — Rai забывает этот ответ и больше его не выдаёт (вопрос попадает в «плохие»);
  • документы: что было в прочитанных файлах (files.js) — потом можно спрашивать по ним в любом чате.

Данные хранятся в браузере (localStorage) и при запуске передаются сюда (load); export() — обратно для сохранения.
"""

import math
import re
import time
from collections import Counter

import nlp

MAX_ANSWERS = 500
MAX_DOCS = 30
MAX_PARAS = 1500
MAX_DOC_CHARS = 1_500_000   # все документы вместе (≈3 МБ в памяти браузера)

_answers = []      # {"q", "a", "src", "t"}
_docs = []         # {"name", "t", "paras": [текст]}
_bad = set()       # вопросы (нормализованные), чьи ответы не понравились
_cache = {}


def _keys(text):
    return {w for w in nlp.tokens(text or "") if w not in nlp.GENERIC and w not in nlp.FILLER and len(w) > 2}


def soft_hit(want, have):
    """Какие слова вопроса есть в тексте — с учётом разных форм: «собрали»/«собрал», «бюджет»/«бюджета»
    (основа одного слова начинается с основы другого, от 4 букв)."""
    hit = want & have
    for w in want - hit:
        if len(w) >= 4 and any(len(h) >= 4 and (h.startswith(w) or w.startswith(h)) for h in have):
            hit.add(w)
    return hit


def norm(question):
    return " ".join(sorted(_keys(question)))


def load(data):
    """Загрузить выученное (из памяти браузера): {"answers": [...], "docs": [...], "bad": [...]}."""
    global _answers, _docs, _bad
    data = data if isinstance(data, dict) else {}
    _answers = [a for a in data.get("answers", []) if isinstance(a, dict) and a.get("q") and a.get("a")][-MAX_ANSWERS:]
    _docs = [d for d in data.get("docs", []) if isinstance(d, dict) and d.get("name") and d.get("paras")][-MAX_DOCS:]
    _bad = set(x for x in data.get("bad", []) if isinstance(x, str))
    _cache.clear()
    return stats()


def export():
    return {"answers": _answers, "docs": _docs, "bad": sorted(_bad)}


def stats():
    return {"answers": len(_answers), "docs": len(_docs), "doc_names": [d["name"] for d in _docs]}


def add_answer(question, answer, src="neuro"):
    """Запомнить ответ на вопрос. False — нечего запоминать (пустой вопрос или ответ)."""
    key = norm(question)
    if not key or not (answer or "").strip():
        return False
    _bad.discard(key)
    _answers[:] = [a for a in _answers if norm(a["q"]) != key]
    _answers.append({"q": question.strip()[:300], "a": answer.strip()[:4000], "src": src, "t": int(time.time())})
    del _answers[:-MAX_ANSWERS]
    return True


def forget(question):
    """👎: забыть ответ на этот вопрос и не выдавать его больше."""
    key = norm(question)
    before = len(_answers)
    _answers[:] = [a for a in _answers if norm(a["q"]) != key]
    if key:
        _bad.add(key)
    return before != len(_answers)


def is_bad(question):
    return norm(question) in _bad


def find(question):
    """Выученный ответ на такой же (или почти такой же) вопрос — {"q", "a", "src", "t"} или None."""
    want = _keys(question)
    if not want or norm(question) in _bad:
        return None
    best, best_sim = None, 0.0
    for a in _answers:
        have = _keys(a["q"])
        if not have:
            continue
        common = want & have
        sim = len(common) / len(want | have)
        if sim > best_sim:
            best, best_sim = a, sim
    # почти тот же вопрос: совпадают все значимые слова (порядок и лишнее «пожалуйста» неважны)
    return best if best and best_sim >= 0.75 else None


def _split(text):
    paras = []
    for block in re.split(r"\n\s*\n", text or ""):
        block = " ".join(block.split())
        if len(block) <= 420:
            if len(block) >= 25:
                paras.append(block)
            continue
        cur = ""
        for s in re.split(r"(?<=[.!?…])\s+", block):  # длинный абзац — кусками по нескольку предложений
            if len(cur) + len(s) > 420 and cur:
                paras.append(cur)
                cur = ""
            cur = (cur + " " + s).strip()
        if len(cur) >= 25:
            paras.append(cur)
    return paras[:MAX_PARAS]


def add_doc(name, text):
    """Запомнить документ (прочитанный файл): дальше по нему можно спрашивать в любом чате."""
    paras = _split(text)
    if not name or len(paras) < 1:
        return False
    _docs[:] = [d for d in _docs if d["name"] != name]
    _docs.append({"name": name[:120], "t": int(time.time()), "paras": paras})
    del _docs[:-MAX_DOCS]
    while len(_docs) > 1 and sum(len(p) for d in _docs for p in d["paras"]) > MAX_DOC_CHARS:
        _docs.pop(0)   # память браузера не бесконечна — старые документы уступают место новым
    _cache.clear()
    return True


def forget_doc(name):
    before = len(_docs)
    _docs[:] = [d for d in _docs if d["name"] != name]
    _cache.clear()
    return before != len(_docs)


def doc_answer(question, n=2):
    """Ответ из запомненных документов: (название файла, [подходящие абзацы]) или None."""
    want = _keys(question)
    if len(want) < 2 or not _docs:
        return None
    if "df" not in _cache:
        _cache["df"] = Counter(w for d in _docs for p in d["paras"] for w in _keys(p))
    df = _cache["df"]
    scored = []
    for d in _docs:
        for p in d["paras"]:
            hit = soft_hit(want, _keys(p))
            if len(hit) * 2 >= len(want) and len(hit) >= 2:
                scored.append((sum(1 / math.log(2 + df[w]) for w in hit) * len(hit) / len(want), d["name"], p))
    if not scored:
        return None
    scored.sort(reverse=True)
    top_score, name, _ = scored[0]
    return name, [p for s, nm, p in scored[:n] if nm == name and s >= top_score * 0.75]
