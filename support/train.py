"""Обучение нейросети поддержки Rai с нуля: python support/train.py

Берёт темы и примеры вопросов из support/data.json и тысячи вопросов из support/questions.json
(их собирает generate.py), дополняет их вариантами с опечатками,
лишними словами и пропусками слов, обучает двухслойную сеть (numpy, Adam, softmax)
и сохраняет её в support/model.json — его вместе с rai-support.js сайт загружает с GitHub.

Сначала сеть учится на 80% примеров и проверяется на остальных 20% (точность печатается),
затем обучается заново на всех примерах — это и есть итоговая модель.
Нужен numpy: pip install numpy (на сайте и сервере numpy не нужен).
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nn import DATA_PATH, MODEL_PATH, indices, words  # noqa: E402

QUESTIONS_PATH = os.path.join(os.path.dirname(DATA_PATH), "questions.json")

DIMS = 4096
HIDDEN = 48
EPOCHS = 30
BATCH = 128
LR = 0.005
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.05
FEATURE_DROPOUT = 0.15
HIDDEN_DROPOUT = 0.2
AUGMENT = 6          # вариантов на каждый ручной пример
AUGMENT_GEN = 2      # и на каждый вопрос из шаблонов (их и так тысячи)
SEED = 7

PREFIXES = ["здравствуйте", "привет", "подскажите", "скажите пожалуйста", "у меня вопрос", "помогите", "добрый день",
            "а", "слушайте", "извините", "вопрос"]
SUFFIXES = ["пожалуйста", "срочно", "заранее спасибо", "помогите", "очень надо", "подскажите"]


def typo(word, rng):
    if len(word) < 4:
        return word
    i = int(rng.integers(1, len(word) - 1))
    kind = int(rng.integers(0, 3))
    if kind == 0:
        return word[:i] + word[i + 1:]                          # пропущена буква
    if kind == 1:
        return word[:i - 1] + word[i] + word[i - 1] + word[i + 1:]  # переставлены соседние
    return word[:i] + word[i] + word[i:]                        # лишняя буква


def augment(text, rng, intent_id, n=None):
    """Варианты вопроса, как их пишут люди: с опечатками, вежливыми словами, без лишних слов."""
    out = [text]
    ws = words(text)
    short = intent_id in ("greeting", "thanks")
    for _ in range(AUGMENT if n is None else n):
        w = list(ws)
        if not w:
            break
        if rng.random() < 0.6:
            k = int(rng.integers(0, len(w)))
            w[k] = typo(w[k], rng)
        if len(w) >= 3 and rng.random() < 0.3:
            del w[int(rng.integers(1, len(w)))]
        if not short and rng.random() < 0.4:
            w = PREFIXES[int(rng.integers(0, len(PREFIXES)))].split() + w
        if not short and rng.random() < 0.25:
            w = w + SUFFIXES[int(rng.integers(0, len(SUFFIXES)))].split()
        out.append(" ".join(w))
    return out


def load_data(path=DATA_PATH, questions_path=QUESTIONS_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    generated = {}
    if questions_path and os.path.exists(questions_path):
        with open(questions_path, encoding="utf-8") as f:
            generated = json.load(f).get("questions", {})
    for it in data["intents"]:
        it["generated"] = list(generated.get(it["id"], []))
    return data, [it["id"] for it in data["intents"]]


def _norm(t):
    return " ".join(words(t))


def make_samples(data, ids, rng, split=None):
    """(обучающие, проверочные) пары (номера признаков, тема).

    split — доля РУЧНЫХ примеров для проверки: точность меряется только на вопросах, написанных людьми,
    которых сеть не видела (вопросы из шаблонов, совпавшие с ними, тоже убираются из обучения).
    """
    train, val = [], []
    for k, it in enumerate(data["intents"]):
        ex = list(it["examples"])
        rng.shuffle(ex)
        n_val = int(round(len(ex) * split)) if split else 0
        for e in ex[:n_val]:
            val.append((indices(e, DIMS), k, e))
        held = {_norm(e) for e in ex[:n_val]}
        for e in ex[n_val:]:
            for v in augment(e, rng, it["id"]):
                train.append((indices(v, DIMS), k, v))
        for e in it.get("generated", []):
            if _norm(e) in held:
                continue
            for v in augment(e, rng, it["id"], AUGMENT_GEN):
                train.append((indices(v, DIMS), k, v))
    return train, val


def to_matrix(batch, rng=None):
    x = np.zeros((len(batch), DIMS), dtype=np.float32)
    for r, (idx, _, _) in enumerate(batch):
        if rng is not None and len(idx) > 2:
            keep = [i for i in idx if rng.random() >= FEATURE_DROPOUT] or idx
        else:
            keep = idx
        if keep:
            x[r, keep] = 1.0 / np.sqrt(len(keep))
    return x


def forward(params, x):
    w1, b1, w2, b2 = params
    h = np.maximum(x @ w1 + b1, 0)
    z = h @ w2 + b2
    z -= z.max(axis=1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(axis=1, keepdims=True)


def train(samples, n_classes, rng, epochs=EPOCHS, log=True):
    w1 = (rng.standard_normal((DIMS, HIDDEN)) * 0.1).astype(np.float32)
    b1 = np.zeros(HIDDEN, dtype=np.float32)
    w2 = (rng.standard_normal((HIDDEN, n_classes)) * np.sqrt(2.0 / HIDDEN)).astype(np.float32)
    b2 = np.zeros(n_classes, dtype=np.float32)
    params = [w1, b1, w2, b2]
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    step = 0
    for epoch in range(epochs):
        order = rng.permutation(len(samples))
        total = 0.0
        for s in range(0, len(order), BATCH):
            batch = [samples[i] for i in order[s:s + BATCH]]
            x = to_matrix(batch, rng)
            y = np.full((len(batch), n_classes), LABEL_SMOOTHING / n_classes, dtype=np.float32)
            y[np.arange(len(batch)), [b[1] for b in batch]] += 1 - LABEL_SMOOTHING
            # прямой проход с dropout скрытого слоя
            z1 = x @ params[0] + params[1]
            h = np.maximum(z1, 0)
            mask = (rng.random(h.shape) >= HIDDEN_DROPOUT).astype(np.float32) / (1 - HIDDEN_DROPOUT)
            h *= mask
            z2 = h @ params[2] + params[3]
            z2 -= z2.max(axis=1, keepdims=True)
            p = np.exp(z2)
            p /= p.sum(axis=1, keepdims=True)
            total += float(-(y * np.log(p + 1e-9)).sum())
            # обратный проход
            dz2 = (p - y) / len(batch)
            grads = [None, None, h.T @ dz2, dz2.sum(axis=0)]
            dz1 = (dz2 @ params[2].T) * mask * (z1 > 0)
            grads[0] = x.T @ dz1
            grads[1] = dz1.sum(axis=0)
            # Adam с затуханием весов
            step += 1
            lr = LR * (0.5 * (1 + np.cos(np.pi * epoch / epochs)) * 0.9 + 0.1)
            for i, g in enumerate(grads):
                m[i] = 0.9 * m[i] + 0.1 * g
                v[i] = 0.999 * v[i] + 0.001 * g * g
                mh = m[i] / (1 - 0.9 ** step)
                vh = v[i] / (1 - 0.999 ** step)
                params[i] -= (lr * (mh / (np.sqrt(vh) + 1e-8))).astype(np.float32)
                if i in (0, 2):
                    params[i] *= (1 - lr * WEIGHT_DECAY)
        if log and (epoch % 10 == 0 or epoch == epochs - 1):
            print(f"  эпоха {epoch + 1:3d}/{epochs}: потери {total / len(samples):.4f}")
    return params


def quantize(params):
    """Первый слой → int8 с масштабом на нейрон (так модель в 4 раза меньше)."""
    w1 = params[0]
    scale = np.abs(w1).max(axis=0) / 127.0
    scale[scale == 0] = 1e-8
    q = np.clip(np.round(w1 / scale), -127, 127).astype(np.int8)
    deq = [q.astype(np.float32) * scale, params[1], params[2], params[3]]
    return q, scale, deq


def accuracy(params, samples):
    if not samples:
        return 1.0, []
    p = forward(params, to_matrix(samples))
    pred = p.argmax(axis=1)
    wrong = [(s[2], s[1], int(k), float(p[r, k])) for r, (s, k) in enumerate(zip(samples, pred)) if s[1] != k]
    return 1 - len(wrong) / len(samples), wrong


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--out", default=MODEL_PATH)
    ap.add_argument("--no-check", action="store_true", help="не проверять на отложенных примерах (быстрее)")
    args = ap.parse_args()

    data, ids = load_data(args.data)
    t0 = time.time()
    metrics = {}
    if not args.no_check:
        print("Проверка: обучение на 80% примеров…")
        rng = np.random.default_rng(SEED)
        tr, val = make_samples(data, ids, rng, split=0.2)
        params = train(tr, len(ids), rng)
        _, _, deq = quantize(params)
        acc, wrong = accuracy(deq, val)
        noisy = [(indices(v, DIMS), k, v) for _, k, e in val for v in augment(e, rng, ids[k])[1:3]]
        acc_noisy, _ = accuracy(deq, noisy)
        metrics = {"val_accuracy": round(acc, 4), "val_noisy_accuracy": round(acc_noisy, 4), "val_examples": len(val)}
        print(f"Точность на новых вопросах: {acc:.1%} ({len(val)}), с опечатками: {acc_noisy:.1%}")
        for text, k, kk, pr in wrong[:15]:
            print(f"  ✗ «{text}»: {ids[k]} → {ids[kk]} ({pr:.0%})")

    print("Итоговое обучение на всех примерах…")
    rng = np.random.default_rng(SEED)
    tr, _ = make_samples(data, ids, rng)
    params = train(tr, len(ids), rng)
    q, scale, deq = quantize(params)
    acc, _ = accuracy(deq, [(indices(e, DIMS), k, e) for k, it in enumerate(data["intents"]) for e in it["examples"]])
    metrics.update({"train_accuracy": round(acc, 4), "train_samples": len(tr),
                    "questions": sum(len(it["examples"]) + len(it.get("generated", [])) for it in data["intents"])})

    h = hashlib.sha256()
    for path in (args.data, QUESTIONS_PATH):
        if os.path.exists(path):
            with open(path, "rb") as f:
                h.update(f.read())
    data_hash = h.hexdigest()
    model = {
        "format": "rai-support-mlp-1",
        "name": "Rai Support",
        "dims": DIMS,
        "hidden": HIDDEN,
        "data_sha256": data_hash,
        "metrics": metrics,
        "intents": [{k: it[k] for k in ("id", "title", "answer", "draft", "handoff", "handoff_if", "close") if k in it} for it in data["intents"]],
        "w1": {"scale": [round(float(s), 8) for s in scale], "data": base64.b64encode(q.tobytes()).decode()},
        "b1": [round(float(x), 5) for x in deq[1]],
        "w2": [[round(float(x), 5) for x in row] for row in deq[2]],
        "b2": [round(float(x), 5) for x in deq[3]],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(args.out) / 1024
    print(f"Готово за {time.time() - t0:.0f} с: {args.out} ({size:.0f} КБ), тем: {len(ids)}, "
          f"точность на обучающих: {acc:.1%}")


if __name__ == "__main__":
    main()
