"""Смысл Rai — своя модель значений слов, обучена на GitHub на текстах Википедии (tools/build_deep.py).

Каждая основа слова (как её режет nlp.stem) — вектор из нескольких десятков чисел. Слова, которые встречаются
в похожем окружении («врач» и «доктор», «планета» и «орбита»), получают близкие векторы. Обучение — без нейросети:
счёт совместной встречаемости слов (PPMI) и сжатие матрицы (SVD), затем числа округляются до байта (int8).

Rai сравнивает по смыслу вопрос и предложения из найденных текстов (а не только по совпадению слов) и
расширяет поиск близкими словами. Нет модели — всё работает по словам, просто чуть хуже.
"""

import base64
import json
import math
from array import array

import nlp

_dim = 0
_words = []          # основы слов, от частых к редким
_index = {}          # основа → номер
_vecs = None         # array('b'): номер * _dim … — вектор слова (int8, уже нормирован)
_related = {}        # основа → [близкие основы] (посчитано при обучении)
_info = {}


def load(data):
    """Загрузить модель: {"dim", "words", "vectors": base64(int8), "related": {номер: [номера]}}. Число слов."""
    global _dim, _words, _index, _vecs, _related, _info
    if isinstance(data, (str, bytes)):
        data = json.loads(data)
    dim, words = int(data.get("dim") or 0), list(data.get("words") or [])
    raw = base64.b64decode(data.get("vectors") or "")
    if not dim or not words or len(raw) != dim * len(words):
        return 0
    vecs = array("b")
    vecs.frombytes(raw)
    _dim, _words, _vecs = dim, words, vecs
    _index = {w: i for i, w in enumerate(words)}
    _related = {}
    for k, near in (data.get("related") or {}).items():
        i = int(k)
        if 0 <= i < len(words):
            _related[words[i]] = [words[j] for j in near if 0 <= j < len(words)]
    _info = {"dim": dim, "words": len(words), "built": data.get("built"), "corpus": data.get("corpus")}
    return len(words)


def load_file(path):
    """Загрузить модель из файла (sense.json.gz из папки deep/). 0 — файла нет."""
    import gzip
    import os
    if not os.path.exists(path):
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return load(json.load(f))


def ready():
    return _vecs is not None


def info():
    return dict(_info)


def _word_vec(stem):
    i = _index.get(stem)
    if i is None:
        return None
    return _vecs[i * _dim:(i + 1) * _dim]


def _weight(stem):
    """Редкие слова важнее частых: вес растёт с номером в списке (список отсортирован по частоте)."""
    i = _index.get(stem, len(_words))
    return math.log(20 + i) / math.log(20 + len(_words))


def vector(text, stems=None):
    """Смысл текста — средний вектор его слов (с весами). None — модель не знает ни одного слова."""
    if not ready():
        return None
    acc = [0.0] * _dim
    total = 0.0
    for s in (stems if stems is not None else nlp.tokens(text)):
        if s in nlp.GENERIC:
            continue
        v = _word_vec(s)
        if v is None:
            continue
        w = _weight(s)
        for k in range(_dim):
            acc[k] += w * v[k]
        total += w
    if not total:
        return None
    norm = math.sqrt(sum(x * x for x in acc)) or 1.0
    return [x / norm for x in acc]


def cosine(a, b):
    if a is None or b is None:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def similarity(text_a, text_b):
    return cosine(vector(text_a), vector(text_b))


def related(word, limit=5):
    """Близкие по смыслу основы слов: «планет» → [«орбит», «спутник», …]."""
    stem = word if word in _index else nlp.stem(nlp.normalize(word))
    return _related.get(stem, [])[:limit]
