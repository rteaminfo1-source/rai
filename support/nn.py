"""Нейросеть поддержки Rai: признаки текста и ответ обученной сети (чистый Python, без библиотек).

Как устроена сеть
-----------------
Текст → признаки → двухслойная нейросеть (перцептрон) → вероятность каждой темы (intent).

1. Признаки. Текст переводится в нижний регистр (ё → е) и делится на слова [a-zа-я0-9]+.
   Для каждого слова берутся: слово целиком (w:), его начало из 5 букв (s:, если слово длиннее 5),
   буквенные тройки слова с краями «<слово>» (c:) и пары соседних слов по 5 букв (b:).
   Буквенные тройки делают сеть устойчивой к опечаткам и окончаниям («заявку», «заявки»).
   Каждый признак хешируется FNV-1a (32 бита, по кодам символов) в одну из DIMS ячеек.
2. Вход сети — вектор длины DIMS: 1/√n в ячейках найденных признаков (n — их число), остальное 0.
3. Скрытый слой: HIDDEN нейронов, ReLU. Веса первого слоя хранятся в int8 с масштабом на нейрон.
4. Выход: по нейрону на тему, softmax → вероятности.

Ровно то же самое делает support/rai-support.js в браузере — сайт загружает его и model.json прямо с GitHub.
Обучение: python support/train.py (нужен numpy), результат — support/model.json.
"""

import base64
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "model.json")
DATA_PATH = os.path.join(HERE, "data.json")

_WORD_RE = re.compile(r"[a-zа-я0-9]+")


def normalize(text: str) -> str:
    return str(text or "").lower().replace("ё", "е")


def words(text: str):
    return _WORD_RE.findall(normalize(text))


def features(text: str):
    """Строковые признаки текста (см. описание в начале файла)."""
    ws = words(text)
    feats = set()
    for i, w in enumerate(ws):
        feats.add("w:" + w)
        if len(w) > 5:
            feats.add("s:" + w[:5])
        if len(w) >= 2:
            g = "<" + w + ">"
            for j in range(len(g) - 2):
                feats.add("c:" + g[j:j + 3])
        if i + 1 < len(ws):
            feats.add("b:" + w[:5] + "_" + ws[i + 1][:5])
    return feats


def fnv1a(s: str) -> int:
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def indices(text: str, dims: int):
    """Номера ячеек входного вектора, в которых стоит признак (по возрастанию)."""
    return sorted({fnv1a(f) % dims for f in features(text)})


class Model:
    """Обученная сеть из model.json."""

    def __init__(self, path: str = MODEL_PATH):
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        self.meta = m
        self.dims, self.hidden = m["dims"], m["hidden"]
        self.intents = m["intents"]
        self.ids = [it["id"] for it in self.intents]
        raw = base64.b64decode(m["w1"]["data"])
        scale = m["w1"]["scale"]
        h = self.hidden
        # int8 → float: строка i — веса признака i для всех нейронов скрытого слоя
        self.w1 = [[(b - 256 if b > 127 else b) * scale[j] for j, b in enumerate(raw[i * h:(i + 1) * h])]
                   for i in range(self.dims)]
        self.b1, self.w2, self.b2 = m["b1"], m["w2"], m["b2"]

    def probs(self, text: str):
        """Вероятности тем: список того же порядка, что self.ids."""
        idx = indices(text, self.dims)
        if not idx:
            return [1.0 if i == "other" else 0.0 for i in self.ids]
        s = 1.0 / math.sqrt(len(idx))
        hid = list(self.b1)
        for i in idx:
            row = self.w1[i]
            for j in range(self.hidden):
                hid[j] += s * row[j]
        hid = [v if v > 0 else 0.0 for v in hid]
        logits = list(self.b2)
        for j, v in enumerate(hid):
            if v:
                row = self.w2[j]
                for k in range(len(logits)):
                    logits[k] += v * row[k]
        top = max(logits)
        ex = [math.exp(v - top) for v in logits]
        total = sum(ex)
        return [v / total for v in ex]

    def predict(self, text: str, top: int = 3):
        """[(тема, вероятность), …] — самые вероятные темы."""
        p = self.probs(text)
        order = sorted(range(len(p)), key=lambda k: -p[k])[:top]
        return [(self.ids[k], p[k]) for k in order]

    def intent(self, intent_id: str):
        return next((it for it in self.intents if it["id"] == intent_id), None)


_model = None


def model() -> Model:
    global _model
    if _model is None:
        _model = Model()
    return _model


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "как подать заявку в команду"
    for tid, p in model().predict(q):
        print(f"{p:6.1%}  {tid}")
