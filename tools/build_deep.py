"""Собрать глубокие знания Rai (папка deep/) и модель смыслов «Rai Смысл» — на GitHub (workflow «Глубокие знания Rai»).

    python tools/build_deep.py -o deep

1. Знания. Для каждой темы энциклопедии (encyclopedia.json, ~15 000 тем) — статья русской Википедии целиком,
   по разделам: вступление и главные разделы (без «Примечаний», «Литературы», «Ссылок»), до ~6000 знаков на тему.
   Темы раскладываются по частям: номер части = crc32(название) % n. Каждая часть — deep/NN.json.gz около 1 МБ,
   любая часть меньше 30 МБ (проверяется). deep/manifest.json — список тем и частей.
2. Модель смыслов. На этих же текстах Rai учит свои векторы слов без нейросети: считает, какие слова встречаются
   рядом (окно ±4), переводит счёт в PPMI и сжимает матрицу разложением SVD до 100 чисел на слово. Числа
   округляются до байта (int8). Для частых слов заранее считаются ближайшие по смыслу. Итог — deep/sense.json.gz
   (несколько мегабайт, тоже меньше 30 МБ).

Если Википедия отвечает медленно и время сборки кончается, недостающие темы берутся из прошлой сборки (deep/).
Тексты Википедии — CC BY-SA 4.0 (Rai указывает источник в каждом ответе). Нужны numpy и scipy (для модели смыслов).
"""

import argparse
import base64
import concurrent.futures
import datetime
import gzip
import json
import math
import os
import re
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import build_encyclopedia as be  # noqa: E402 — те же вежливые запросы к Википедии (повторы, паузы, maxlag)
import nlp  # noqa: E402 — те же основы слов, что у движка Rai

MAX_FILE = 30 * 1024 * 1024          # ни один файл не больше 30 МБ
PART_TARGET = 1024 * 1024            # часть ≈ 1 МБ в сжатом виде — в браузере грузится быстро
LEAD_MAX, SECTION_MAX, ARTICLE_MAX, SECTIONS_MAX = 2200, 1600, 6000, 10
SKIP = re.compile(r"^(примечани|литератур|ссылки|см\. также|источник|галере|библиограф|комментари|фильмограф|дискограф|"
                  r"награды|библиография|сочинения|труды|публикации|издания|список|в культуре|в искусстве)", re.I)
START = time.monotonic()
BUDGET = float(os.environ.get("RAI_BUILD_MINUTES", "150")) * 60


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def time_left():
    return BUDGET - (time.monotonic() - START)


# ------------------------------------------------------------------ тексты

def _cut(text, limit):
    text = re.sub(r"[ \t]+", " ", text.replace("\u0301", "")).strip()   # без знаков ударения
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(".\n"), cut.rfind("! "), cut.rfind("? "))
    return cut[:end + 1] if end > limit // 3 else cut.rstrip() + "…"


def split_article(extract):
    """Текст статьи (explaintext, заголовки «== … ==») → [вступление, [[раздел, текст], …]] — главное, без хвостов."""
    parts = re.split(r"^(={2,4})\s*(.+?)\s*\1\s*$", extract or "", flags=re.M)
    lead = _cut(re.sub(r"\n{2,}", "\n", parts[0]).strip(), LEAD_MAX)
    sections, skip_level, total = [], None, len(lead)
    for k in range(1, len(parts) - 2, 3):
        level, head, body = len(parts[k]), parts[k + 1].strip(), parts[k + 2].strip()
        if skip_level and level > skip_level:
            continue
        skip_level = level if SKIP.match(head) else None
        body = re.sub(r"\n{2,}", "\n", body)
        if skip_level or len(body) < 120:
            continue
        text = _cut(body, min(SECTION_MAX, ARTICLE_MAX - total))
        if len(text) < 120:
            break
        sections.append([head, text])
        total += len(text)
        if total >= ARTICLE_MAX or len(sections) >= SECTIONS_MAX:
            break
    return [lead, sections]


def fetch_article(title):
    data = be.get(be.RU, {"action": "query", "prop": "extracts", "explaintext": 1, "exsectionformat": "wiki",
                          "titles": title, "redirects": 1})
    pages = (data.get("query") or {}).get("pages") or []
    page = pages[0] if isinstance(pages, list) and pages else {}
    if not page or page.get("missing") or not page.get("extract"):
        return None
    return split_article(page["extract"])


def old_texts(out_dir):
    """Тексты прошлой сборки: {название: статья} — на случай, если не хватит времени."""
    path = os.path.join(out_dir, "manifest.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            n = json.load(f)["n"]
        out = {}
        for k in range(n):
            with gzip.open(os.path.join(out_dir, f"{k:02d}.json.gz"), "rt", encoding="utf-8") as f:
                out.update(json.load(f))
        return out
    except (OSError, ValueError, KeyError):
        return {}


def collect(titles, previous, workers=5):
    """{название: статья} для всех тем: из Википедии, а не успели — из прошлой сборки."""
    out, failed = {}, 0
    reserve = 25 * 60                      # оставить время на модель смыслов и запись
    batch = 200
    for i in range(0, len(titles), batch):
        if time_left() < reserve:
            log(f"  время на исходе — беру {len(titles) - i} тем из прошлой сборки")
            for t in titles[i:]:
                if t in previous:
                    out[t] = previous[t]
            break
        chunk = titles[i:i + batch]

        def one(t):
            try:
                return t, fetch_article(t)
            except Exception as e:  # noqa: BLE001 — одна тема не должна ронять всю сборку
                log("  не получилось:", t, e)
                return t, None
        with concurrent.futures.ThreadPoolExecutor(workers) as ex:
            for t, art in ex.map(one, chunk):
                if art and (art[0] or art[1]):
                    out[t] = art
                elif t in previous:
                    out[t] = previous[t]
                else:
                    failed += 1
        if (i // batch) % 10 == 0:
            log(f"  статьи: {min(i + batch, len(titles))} из {len(titles)} ({len(out)} есть) · {int((time.monotonic() - START) / 60)} мин")
    log(f"статей: {len(out)}, не нашлось: {failed}")
    return out


def write_parts(articles, out_dir):
    """Разложить статьи по частям ≈1 МБ (crc32 названия) и записать; ни один файл не больше 30 МБ."""
    raw = sum(len(json.dumps(a, ensure_ascii=False).encode("utf-8")) for a in articles.values())
    n = max(4, math.ceil(raw * 0.3 / PART_TARGET))
    parts = [{} for _ in range(n)]
    for title, art in articles.items():
        parts[zlib.crc32(title.encode("utf-8")) % n][title] = art
    os.makedirs(out_dir, exist_ok=True)
    for old in os.listdir(out_dir):
        if re.fullmatch(r"\d{2,3}\.json\.gz", old):
            os.remove(os.path.join(out_dir, old))
    sizes = []
    for k, part in enumerate(parts):
        data = gzip.compress(json.dumps(part, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9, mtime=0)
        if len(data) * 4 / 3 + 4096 > MAX_FILE:   # на сайте часть лежит в .php текстом (base64) — и он меньше 30 МБ
            raise SystemExit(f"часть {k} слишком большая ({len(data)} байт) — увеличьте число частей")
        with open(os.path.join(out_dir, f"{k:02d}.json.gz"), "wb") as f:
            f.write(data)
        sizes.append(len(data))
    manifest = {"version": 1, "built": datetime.date.today().isoformat(), "source": "Википедия (CC BY-SA 4.0)",
                "n": n, "count": len(articles), "sizes": sizes, "titles": sorted(articles)}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))
    log(f"частей: {n}, всего {round(sum(sizes) / 1048576, 1)} МБ, самая большая {round(max(sizes) / 1048576, 2)} МБ")
    return manifest


# ------------------------------------------------------------------ модель смыслов

def corpus(articles, encyclopedia_items):
    """Тексты для обучения: статьи целиком + энциклопедия. Генератор списков основ слов (по абзацам)."""
    for lead, sections in articles.values():
        for block in [lead] + [t for _, t in sections]:
            for para in block.split("\n"):
                toks = nlp.tokens(para)
                if len(toks) >= 4:
                    yield toks
    for item in encyclopedia_items:
        toks = nlp.tokens(item[3])
        if len(toks) >= 4:
            yield toks


def train_sense(paragraphs, vocab_size=40000, dim=100, window=4, min_count=5, related=6):
    """PPMI + SVD → {"dim", "words", "vectors": base64(int8), "related"}."""
    import numpy as np
    from scipy import sparse
    from scipy.sparse.linalg import svds
    from collections import Counter

    paras = list(paragraphs)
    counts = Counter(t for p in paras for t in p)
    words = [w for w, c in counts.most_common(vocab_size) if c >= min_count and not w.isdigit() and len(w) >= 2]
    index = {w: i for i, w in enumerate(words)}
    V = len(words)
    log(f"модель смыслов: абзацев {len(paras)}, слов в словаре {V}")
    seq = []
    for p in paras:
        seq.extend(index.get(t, -1) for t in p)
        seq.append(-2)                                  # граница абзаца
    ids = np.array(seq, dtype=np.int64)
    rows, cols, vals = [], [], []
    for d in range(1, window + 1):
        a, b = ids[:-d], ids[d:]
        ok = (a >= 0) & (b >= 0)
        # граница абзаца между словами — не соседи
        if d > 1:
            bad = np.zeros(len(ids), dtype=bool)
            bad[ids == -2] = True
            csum = np.concatenate([[0], np.cumsum(bad)])
            ok &= (csum[d:len(ids)] - csum[1:len(ids) - d + 1]) == 0
        keys = a[ok] * V + b[ok]
        uniq, cnt = np.unique(keys, return_counts=True)
        w = cnt / d
        rows += [uniq // V, uniq % V]
        cols += [uniq % V, uniq // V]
        vals += [w, w]
    M = sparse.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(V, V)).tocsr()
    M.sum_duplicates()
    total = M.sum()
    row = np.asarray(M.sum(axis=1)).ravel()
    col = np.asarray(M.sum(axis=0)).ravel() ** 0.75
    col = col / col.sum()
    M = M.tocoo()
    pmi = np.log((M.data / total) / ((row[M.row] / total) * col[M.col]))
    keep = pmi > 0
    P = sparse.csr_matrix((pmi[keep], (M.row[keep], M.col[keep])), shape=(V, V))
    log(f"  PPMI: {P.nnz} ненулевых, SVD до {dim} измерений…")
    U, S, _ = svds(P.astype(np.float64), k=dim)
    vec = U * np.sqrt(S)
    vec /= np.linalg.norm(vec, axis=1, keepdims=True) + 1e-9
    q = np.clip(np.round(vec * 127), -127, 127).astype(np.int8)
    # ближайшие по смыслу для частых слов (считаются заранее — в браузере перебор всех слов был бы долгим)
    near = {}
    top = min(V, 20000)
    for start in range(0, top, 2000):
        block = vec[start:start + 2000] @ vec.T
        for k in range(block.shape[0]):
            block[k, start + k] = -1
        best = np.argpartition(-block, related, axis=1)[:, :related]
        for k in range(block.shape[0]):
            order = best[k][np.argsort(-block[k, best[k]])]
            near[str(start + k)] = [int(j) for j in order if block[k, j] > 0.35]
    near = {k: v for k, v in near.items() if v}
    return {"version": 1, "built": datetime.date.today().isoformat(), "corpus": f"{len(paras)} абзацев Википедии",
            "dim": dim, "words": words, "vectors": base64.b64encode(q.tobytes()).decode("ascii"), "related": near}


def write_sense(model, out_dir):
    data = gzip.compress(json.dumps(model, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9, mtime=0)
    if len(data) * 4 / 3 + 4096 > MAX_FILE:
        raise SystemExit(f"модель смыслов слишком большая ({len(data)} байт)")
    with open(os.path.join(out_dir, "sense.json.gz"), "wb") as f:
        f.write(data)
    log(f"модель смыслов: {len(model['words'])} слов × {model['dim']}, {round(len(data) / 1048576, 1)} МБ")


# ------------------------------------------------------------------ всё вместе

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out", default=os.path.join(ROOT, "deep"))
    parser.add_argument("--encyclopedia", default=os.path.join(ROOT, "encyclopedia.json"))
    parser.add_argument("--limit", type=int, default=0, help="только первые N тем (для проверки)")
    parser.add_argument("--no-fetch", action="store_true", help="не ходить в Википедию: только модель смыслов на прошлых текстах")
    args = parser.parse_args()
    with open(args.encyclopedia, encoding="utf-8") as f:
        enc = json.load(f)
    items = enc["items"][:args.limit] if args.limit else enc["items"]
    titles = list(dict.fromkeys(it[0] for it in items))
    previous = old_texts(args.out)
    log(f"тем: {len(titles)}, из прошлой сборки: {len(previous)}")
    articles = {t: previous[t] for t in titles if t in previous} if args.no_fetch else collect(titles, previous)
    if len(articles) < (20 if args.limit else 1000):
        sys.exit(f"слишком мало статей ({len(articles)}) — прошлая сборка не тронута")
    write_parts(articles, args.out)
    write_sense(train_sense(corpus(articles, items), vocab_size=8000 if args.limit else 40000), args.out)
    log(f"готово за {int((time.monotonic() - START) / 60)} мин")


if __name__ == "__main__":
    main()
