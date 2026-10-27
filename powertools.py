"""Ещё 150+ точных функций Rai — без интернета и без нейросети.

Математика+ (матрицы, системы уравнений, производные, интегралы, статистика), физика и химия (закон Ома,
энергия, молярная масса), финансы (инфляция, окупаемость, налоги), здоровье и спорт, питомцы, даты (Пасха,
фаза Луны, рабочие дни), текст, программисту (JSON, подсети, cron, HTTP-коды, ИНН, СНИЛС), дом и ремонт,
кухня, учёба, развлечения и конвертеры.

Функции регистрируются в toolbox.TOOLS после основных (порядок = порядок проверки). Несколько узких функций
встают ПЕРЕД слишком общими старыми (например «сумма чисел от 1 до 100» — раньше, чем «сумма списка»).
Каждая функция защищена: любая ошибка внутри = «не моё», а не падение чата.
"""

import calendar
import colorsys
import html
import ipaddress
import json
import math
import random
import re
import secrets
import statistics
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction

import skills
from toolbox import NUM, TOOLS, f, ints, is_int, money, nums, rub

num = skills._num


def ptool(cat, title, example, before=None, invent=False, early=False):
    """Регистрация функции (как toolbox.tool), но с защитой от ошибок и возможностью встать перед старой функцией."""
    def deco(fn):
        def safe(text, low, s):
            try:
                return fn(text, low, s)
            except Exception:  # noqa: BLE001 — любая ошибка в разборе = функция не подходит
                return None
        safe.__name__ = fn.__name__
        safe.__doc__ = fn.__doc__
        entry = {"cat": cat, "title": title, "example": example, "fn": safe, "invent": invent, "early": early}
        idx = next((i for i, t in enumerate(TOOLS) if t["title"] == before), None) if before else None
        if idx is None:
            TOOLS.append(entry)
        else:
            TOOLS.insert(idx, entry)
        return safe
    return deco


def invent_tool(text, session=None):
    """«Придумай кличку / название / имя / ник» — точные генераторы раньше общей «выдумки» (talk.invent)."""
    low = skills._low(text)
    for t in TOOLS:
        if t.get("invent"):
            reply = t["fn"](text, low, session if session is not None else {})
            if reply:
                return reply
    return None


def early_tool(text, session=None):
    """Расчёты с единицами («электричество 2000 вт 3 часа в день», «бензин на 300 км») — раньше конвертера единиц
    и разговорных советов: иначе «3 часа в день» конвертер поймёт как «часы в сутки»."""
    low = skills._low(text)
    for t in TOOLS:
        if t.get("early"):
            reply = t["fn"](text, low, session if session is not None else {})
            if reply:
                return reply
    return None


# «Придумай ник» — старая функция toolbox тоже генератор: раньше её перехватывала общая «выдумка»
for _t in TOOLS:
    if _t["title"] == "Ник для игр и соцсетей":
        _t["invent"] = True


# ---------------------------------------------------------------- помощники
_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _sup(n):
    return str(n).translate(_SUP)


def _frac(q):
    q = Fraction(q)
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def _r(x, d=2):
    """Округлить и записать по-русски."""
    return num(round(x, d))


def _payload(text):
    """Текст после первого двоеточия: «в верхний регистр: привет» → «привет»."""
    i = text.find(":")
    return text[i + 1:].strip() if i >= 0 else ""


def _kw(low, *keys):
    """Число после ключевого слова: _kw(low, "радиус") для «радиус 5», «радиус = 5», «радиусом 5»."""
    for k in keys:
        m = re.search(k + r"\w*\s*(?:=|-|:|равн\w*)?\s*(" + NUM + ")", low)
        if m:
            return f(m.group(1))
    return None


def _dur(hours):
    """3,75 ч → «3 ч 45 мин»."""
    total = int(round(hours * 60))
    h, m = divmod(total, 60)
    if h and m:
        return f"{h} ч {m} мин"
    return f"{h} ч" if h else f"{m} мин"


def _secs(sec):
    """Секунды → «2 мин 5 с», «3 ч 10 мин», «5 лет»."""
    sec = float(sec)
    if sec < 1:
        return "меньше секунды"
    for size, name in ((31_557_600 * 1000, "тыс. лет"), (31_557_600, "лет"), (86_400, "дн"), (3600, "ч")):
        if sec >= size:
            v = sec / size
            if name in ("лет", "тыс. лет") and v >= 1e6:
                return "дольше, чем существует Вселенная" if v > 1.4e10 else f"≈ {num(round(v, -3))} {name}"
            if name == "ч":
                h, rem = divmod(int(sec), 3600)
                return f"{h} ч {rem // 60} мин"
            return f"≈ {num(round(v, 1))} {name}"
    m, s = divmod(int(round(sec)), 60)
    return f"{m} мин {s} с" if m else f"{s} с"


_MONTH_STEMS = [("январ", 1), ("феврал", 2), ("март", 3), ("апрел", 4), ("ма", 5), ("июн", 6), ("июл", 7),
                ("август", 8), ("сентябр", 9), ("октябр", 10), ("ноябр", 11), ("декабр", 12)]
_MONTH_RE = r"(январ\w*|феврал\w*|март\w*|апрел\w*|ма[йяе]|июн\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)"
_MONTH_GEN = ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
_MONTH_NOM = ["", "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
_WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def _month_num(word):
    for stem, n in _MONTH_STEMS:
        if word.startswith(stem):
            return n
    return None


def _today():
    return skills._now().date()


def _dates(low):
    """Все даты из текста по порядку: «1 марта 2026», «01.03.2026», «2026-03-01», «сегодня», «завтра»."""
    today = _today()
    found = []
    pat = (r"(\d{4})-(\d{1,2})-(\d{1,2})|(?<![\d.])(\d{1,2})[./](\d{1,2})[./](\d{2,4})(?![\d.])|(?<!\d)(\d{1,2})\s+"
           + _MONTH_RE + r"(?:\s+(\d{4}))?")
    for m in re.finditer(pat, low):
        try:
            if m.group(1):
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            elif m.group(4):
                y = int(m.group(6))
                d = date(y + 2000 if y < 100 else y, int(m.group(5)), int(m.group(4)))
            else:
                d = date(int(m.group(9)) if m.group(9) else today.year, _month_num(m.group(8)), int(m.group(7)))
            found.append((m.start(), d))
        except (ValueError, TypeError):
            continue
    for word, shift in (("позавчера", -2), ("вчера", -1), ("сегодня", 0), ("послезавтра", 2), ("завтра", 1)):
        for m in re.finditer(r"(?<![а-я])" + word + r"(?![а-я])", low):
            found.append((m.start(), today + timedelta(days=shift)))
    found.sort(key=lambda x: x[0])
    return [d for _, d in found]


def _say(d):
    return f"{d.day} {_MONTH_GEN[d.month]} {d.year}"


def _plural(n, one, few, many):
    """Склонение: 1 год, 2 года, 5 лет; для дробных — «1,5 года»."""
    if abs(n - round(n)) > 1e-9:
        return few
    return skills.plural(int(round(n)), one, few, many)


# ================================================================ МАТЕМАТИКА+
CAT_M = "Математика+"


@ptool(CAT_M, "Упростить квадратный корень", "упрости корень из 72", before="Простое ли число")
def simplify_root(text, low, s):
    m = re.search(r"упрости\w*\s+(?:квадратн\w*\s+)?корень\s+(?:из\s+)?(\d+)", low)
    if not m:
        return None
    n = int(m.group(1))
    if n < 1 or n > 10 ** 12:
        return None
    out, rest, k = 1, n, 2
    while k * k <= rest:
        while rest % (k * k) == 0:
            rest //= k * k
            out *= k
        k += 1
    if rest == 1:
        return f"√{n} = **{out}** — это точный квадрат ({out}² = {n})."
    if out == 1:
        return f"√{n} не упрощается: под корнем нет множителей-квадратов. √{n} ≈ {num(math.sqrt(n))}"
    return f"√{n} = √({out * out} · {rest}) = **{out}√{rest}** ≈ {num(math.sqrt(n))}"


def _divisor_sum(n):
    """Сумма собственных делителей (без самого числа)."""
    if n < 2:
        return 0
    total, i = 1, 2
    while i * i <= n:
        if n % i == 0:
            total += i
            if i != n // i:
                total += n // i
        i += 1
    return total


@ptool(CAT_M, "Совершенное число", "28 совершенное число?")
def perfect(text, low, s):
    m = re.search(r"(\d+)\D{0,20}совершенн|совершенн\w*\s+(?:ли\s+)?(?:число\s+)?(\d+)", low)
    if not m:
        return None
    n = int(m.group(1) or m.group(2))
    if n > 10 ** 10:
        return None
    d = _divisor_sum(n)
    if d == n and n > 1:
        return f"**Да**, {n} — совершенное число: сумма его делителей (кроме самого числа) равна {n}."
    kind = "избыточное" if d > n else "недостаточное"
    return (f"**Нет**, {n} — не совершенное ({kind}): сумма собственных делителей = {num(d)}. "
            "Совершенные числа: 6, 28, 496, 8128, 33 550 336…")


@ptool(CAT_M, "Число Армстронга (нарциссическое)", "153 число армстронга?")
def armstrong(text, low, s):
    m = re.search(r"(\d+)\D{0,20}(?:армстронг|нарцисс)|армстронг\w*\s+(?:ли\s+)?(\d+)", low)
    if not m:
        return None
    digits = m.group(1) or m.group(2)
    k = len(digits)
    total = sum(int(c) ** k for c in digits)
    parts = " + ".join(f"{c}{_sup(k)}" for c in digits)
    if total == int(digits):
        return f"**Да**, {digits} — число Армстронга: {parts} = {total}."
    return f"**Нет**: {parts} = {num(total)} ≠ {digits}. Числа Армстронга: 153, 370, 371, 407, 1634, 8208…"


def _sieve(n):
    flags = bytearray([1]) * (n + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, int(n ** 0.5) + 1):
        if flags[i]:
            flags[i * i::i] = bytearray(len(range(i * i, n + 1, i)))
    return [i for i, v in enumerate(flags) if v]


@ptool(CAT_M, "Простые числа до N", "простые числа до 50")
def primes_upto(text, low, s):
    m = re.search(r"прост\w*\s+(?:числ\w*\s+)?(?:до|меньше|не\s+больше|в\s+пределах)\s+(\d+)", low)
    if not m:
        return None
    n = int(m.group(1))
    if n < 2 or n > 1_000_000:
        return None
    ps = _sieve(n)
    more = " … (показаны первые 100)" if len(ps) > 100 else ""
    return f"Простых чисел до {num(n)}: **{num(len(ps))}**\n\n" + ", ".join(map(str, ps[:100])) + more


@ptool(CAT_M, "Первые N простых чисел", "первые 10 простых чисел")
def first_primes(text, low, s):
    m = re.search(r"первы[ехй]\s+(\d+)\s+прост", low)
    if not m:
        return None
    k = int(m.group(1))
    if k < 1 or k > 2000:
        return None
    limit = max(30, int(k * (math.log(k + 1) + math.log(math.log(k + 2) + 1) + 3)))
    ps = _sieve(limit)[:k]
    return f"Первые {k} простых чисел:\n\n" + ", ".join(map(str, ps)) + f"\n\nСумма: {num(sum(ps))}"


@ptool(CAT_M, "Треугольник Паскаля", "треугольник паскаля 6 строк")
def pascal(text, low, s):
    if not re.search(r"треугольник\w*\s+паскал", low):
        return None
    k = ints(low)
    n = k[0] if k else 6
    if n < 1 or n > 15:
        return None
    rows, row = [], [1]
    for _ in range(n):
        rows.append(row)
        row = [1] + [row[i] + row[i + 1] for i in range(len(row) - 1)] + [1]
    width = len("  ".join(map(str, rows[-1])))
    lines = ["  ".join(map(str, r)).center(width) for r in rows]
    return (f"Треугольник Паскаля, {n} {_plural(n, 'строка', 'строки', 'строк')}:\n```\n" + "\n".join(lines) + "\n```\n"
            "Каждое число — сумма двух над ним; строка n — коэффициенты (a + b)ⁿ.")


def _param(low, names):
    for nm in names:
        m = re.search(r"(?<![a-zа-я])" + nm + r"\s*=\s*(" + NUM + ")", low)
        if m:
            return f(m.group(1))
    return None


@ptool(CAT_M, "Арифметическая прогрессия", "арифметическая прогрессия a1=2 d=3 n=10")
def arith_prog(text, low, s):
    if not re.search(r"арифметическ\w*\s+прогресс", low):
        return None
    a1, d, n = _param(low, ["a1", "а1"]), _param(low, ["d", "д"]), _param(low, ["n", "н"])
    if a1 is None or d is None or n is None or n < 1 or not is_int(n) or n > 10 ** 7:
        return None
    n = int(n)
    an = a1 + (n - 1) * d
    sn = (a1 + an) * n / 2
    first = ", ".join(num(a1 + i * d) for i in range(min(n, 8))) + ("…" if n > 8 else "")
    return (f"Арифметическая прогрессия: a₁ = {num(a1)}, d = {num(d)}, n = {n}\n\n"
            f"- n-й член: aₙ = a₁ + (n − 1)·d = **{num(an)}**\n"
            f"- сумма первых n членов: Sₙ = (a₁ + aₙ)·n / 2 = **{num(sn)}**\n"
            f"- первые члены: {first}")


@ptool(CAT_M, "Геометрическая прогрессия", "геометрическая прогрессия b1=2 q=3 n=5")
def geom_prog(text, low, s):
    if not re.search(r"геометрическ\w*\s+прогресс", low):
        return None
    b1, q, n = _param(low, ["b1", "б1", "a1", "а1"]), _param(low, ["q"]), _param(low, ["n", "н"])
    if b1 is None or q is None or n is None or n < 1 or not is_int(n) or n > 2000:
        return None
    n = int(n)
    bn = b1 * q ** (n - 1)
    sn = b1 * n if q == 1 else b1 * (q ** n - 1) / (q - 1)
    inf = f"\n- сумма бесконечной прогрессии (|q| < 1): S = b₁ / (1 − q) = **{num(b1 / (1 - q))}**" if abs(q) < 1 else ""
    first = ", ".join(num(b1 * q ** i) for i in range(min(n, 8))) + ("…" if n > 8 else "")
    return (f"Геометрическая прогрессия: b₁ = {num(b1)}, q = {num(q)}, n = {n}\n\n"
            f"- n-й член: bₙ = b₁·qⁿ⁻¹ = **{num(bn)}**\n"
            f"- сумма первых n членов: **{num(sn)}**{inf}\n"
            f"- первые члены: {first}")


@ptool(CAT_M, "Сумма чисел от a до b (формула Гаусса)", "сумма всех чисел от 1 до 100", before="Сумма, максимум и минимум списка")
def sum_range(text, low, s):
    m = re.search(r"сумм\w*\s+(?:всех\s+)?(?:целых\s+|натуральн\w*\s+|четн\w*\s+|нечетн\w*\s+)?(?:чис\w*\s+)?от\s+(-?\d+)\s+до\s+(-?\d+)", low)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    if a > b:
        a, b = b, a
    if b - a > 10 ** 15:
        return None
    kind = "нечётных" if "нечетн" in low else "чётных" if "четн" in low else ""
    if kind:
        par = 1 if kind == "нечётных" else 0
        first = a if a % 2 == par else a + 1
        last = b if b % 2 == par else b - 1
        if first > last:
            return f"Между {a} и {b} нет {kind} чисел."
        cnt = (last - first) // 2 + 1
        return f"Сумма {kind} чисел от {a} до {b}: **{num((first + last) * cnt // 2)}** ({num(cnt)} чисел: от {first} до {last})."
    cnt = b - a + 1
    return (f"Сумма чисел от {a} до {b}: **{num((a + b) * cnt // 2)}**\n\n"
            f"Формула Гаусса: (первое + последнее) · количество / 2 = ({a} + {b}) · {num(cnt)} / 2.")


# ---- матрицы
def _matrices(text):
    """Все матрицы вида [[1,2],[3,4]] из текста (дробные числа — через точку: 1.5)."""
    out = []
    for m in re.finditer(r"\[\s*\[[^\[\]]*\](?:\s*[,;]?\s*\[[^\[\]]*\])*\s*\]", text):
        rows = re.findall(r"\[([^\[\]]*)\]", m.group(0)[1:-1])
        mat = [[Fraction(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", r)] for r in rows]
        if mat and mat[0] and all(len(r) == len(mat[0]) for r in mat):
            out.append(mat)
    return out


def _mat_str(m):
    cells = [[_frac(x) for x in r] for r in m]
    w = max(len(c) for r in cells for c in r)
    return "```\n" + "\n".join("[ " + "  ".join(c.rjust(w) for c in r) + " ]" for r in cells) + "\n```"


def _det(m):
    a = [row[:] for row in m]
    n = len(a)
    det = Fraction(1)
    for c in range(n):
        p = next((r for r in range(c, n) if a[r][c] != 0), None)
        if p is None:
            return Fraction(0)
        if p != c:
            a[c], a[p] = a[p], a[c]
            det = -det
        det *= a[c][c]
        for r in range(c + 1, n):
            k = a[r][c] / a[c][c]
            for j in range(c, n):
                a[r][j] -= k * a[c][j]
    return det


def _inverse(m):
    n = len(m)
    a = [row[:] + [Fraction(int(i == j)) for j in range(n)] for i, row in enumerate(m)]
    for c in range(n):
        p = next((r for r in range(c, n) if a[r][c] != 0), None)
        if p is None:
            return None
        a[c], a[p] = a[p], a[c]
        pv = a[c][c]
        a[c] = [x / pv for x in a[c]]
        for r in range(n):
            if r != c and a[r][c] != 0:
                k = a[r][c]
                a[r] = [x - k * y for x, y in zip(a[r], a[c])]
    return [row[n:] for row in a]


@ptool(CAT_M, "Определитель матрицы", "определитель матрицы [[1,2],[3,4]]")
def determinant(text, low, s):
    if not re.search(r"определител|детерминант|\bdet\b", low):
        return None
    ms = _matrices(text)
    if not ms:
        return None
    m = ms[0]
    if len(m) != len(m[0]):
        return "Определитель есть только у квадратной матрицы (n×n)."
    if len(m) > 8:
        return None
    d = _det(m)
    tail = " — матрица вырожденная, обратной у неё нет." if d == 0 else ""
    return f"Матрица {len(m)}×{len(m)}:\n{_mat_str(m)}\nОпределитель: **{_frac(d)}**{tail}"


@ptool(CAT_M, "Обратная матрица", "обратная матрица [[2,1],[5,3]]")
def inverse_matrix(text, low, s):
    if not re.search(r"обратн\w*\s+матриц", low):
        return None
    ms = _matrices(text)
    if not ms or len(ms[0]) != len(ms[0][0]) or len(ms[0]) > 6:
        return None
    inv = _inverse(ms[0])
    if inv is None:
        return "Обратной матрицы нет: определитель равен 0 (матрица вырожденная)."
    return f"A⁻¹ =\n{_mat_str(inv)}\nПроверка: A · A⁻¹ = E (единичная матрица)."


@ptool(CAT_M, "Умножение матриц", "умножь матрицы [[1,2],[3,4]] и [[5,6],[7,8]]")
def mat_mul(text, low, s):
    if not re.search(r"(?:умнож|перемнож|произведени)\w*\s+(?:двух\s+)?матриц", low):
        return None
    ms = _matrices(text)
    if len(ms) < 2:
        return None
    a, b = ms[0], ms[1]
    if len(a[0]) != len(b):
        return f"Нельзя перемножить: в первой матрице {len(a[0])} столбца(ов), а во второй {len(b)} строк(и) — должно совпадать."
    res = [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]
    return f"A × B ({len(a)}×{len(a[0])} на {len(b)}×{len(b[0])}) =\n{_mat_str(res)}"


@ptool(CAT_M, "Транспонировать матрицу", "транспонируй матрицу [[1,2,3],[4,5,6]]")
def transpose(text, low, s):
    if not re.search(r"транспонир", low):
        return None
    ms = _matrices(text)
    if not ms:
        return None
    t = [list(col) for col in zip(*ms[0])]
    return f"Транспонированная матрица ({len(t)}×{len(t[0])}):\n{_mat_str(t)}"


# ---- системы линейных уравнений
def _lin(side):
    """«2x - 3y + 4» → ({'x': 2, 'y': -3}, 4)."""
    side = side.replace(" ", "")
    if not side:
        return None
    if side[0] not in "+-":
        side = "+" + side
    coefs, const = {}, Fraction(0)
    pos = 0
    for m in re.finditer(r"([+-])([^+-]+)", side):
        if m.start() != pos:
            return None
        pos = m.end()
        k = -1 if m.group(1) == "-" else 1
        t = re.fullmatch(r"(\d+(?:\.\d+)?(?:/\d+)?)?\*?([xyz])?", m.group(2))
        if not t or (t.group(1) is None and t.group(2) is None):
            return None
        c = Fraction(t.group(1)) if t.group(1) else Fraction(1)
        if t.group(2):
            coefs[t.group(2)] = coefs.get(t.group(2), 0) + k * c
        else:
            const += k * c
    return (coefs, const) if pos == len(side) else None


@ptool(CAT_M, "Система линейных уравнений (2–3 неизвестных)", "реши систему 2x+y=5, x-y=1", before="Уравнения (линейные и квадратные)")
def lin_system(text, low, s):
    if not re.search(r"систем", low) or low.count("=") < 2:
        return None
    body = re.sub(r"^.*?систем\w*(?:\s+уравнени\w*)?\s*:?", "", low, count=1)
    body = body.replace("х", "x").replace("у", "y").replace("−", "-").replace("–", "-")
    eqs = [e.strip(" .") for e in re.split(r";|\n|\s+и\s+|,\s+|,(?=[-\dxyz])", body) if "=" in e]
    if not 2 <= len(eqs) <= 3:
        return None
    rows = []
    for e in eqs:
        left, _, right = e.partition("=")
        L, R = _lin(left), _lin(right)
        if not L or not R:
            return None
        coefs = dict(L[0])
        for v, c in R[0].items():
            coefs[v] = coefs.get(v, 0) - c
        rows.append((coefs, R[1] - L[1]))
    names = sorted({v for c, _ in rows for v in c})
    if len(names) != len(rows) or len(names) < 2:
        return None
    a = [[Fraction(c.get(v, 0)) for v in names] + [Fraction(b)] for c, b in rows]
    n = len(names)
    for col in range(n):
        p = next((r for r in range(col, n) if a[r][col] != 0), None)
        if p is None:
            return "У системы нет единственного решения: уравнения зависимы (решений бесконечно много) или противоречат друг другу (решений нет)."
        a[col], a[p] = a[p], a[col]
        pv = a[col][col]
        a[col] = [x / pv for x in a[col]]
        for r in range(n):
            if r != col and a[r][col] != 0:
                k = a[r][col]
                a[r] = [x - k * y for x, y in zip(a[r], a[col])]
    sol = {v: a[i][n] for i, v in enumerate(names)}
    answer = ", ".join(f"{v} = {_frac(sol[v])}" for v in names)
    approx = "" if all(q.denominator == 1 for q in sol.values()) else " (≈ " + ", ".join(f"{v} ≈ {num(float(sol[v]))}" for v in names) + ")"
    return f"Система:\n" + "\n".join(f"- {e}" for e in eqs) + f"\n\n**Ответ: {answer}**{approx}\n\nПроверено подстановкой во все уравнения."


@ptool(CAT_M, "Расстояние между точками и середина отрезка", "расстояние между точками (1,2) и (4,6)")
def distance(text, low, s):
    if not re.search(r"расстояни\w*\s+между\s+точк|длин\w*\s+отрезк|середин\w*\s+отрезк", low):
        return None
    pts = re.findall(r"\(\s*(-?\d+(?:\.\d+)?)\s*[;,]\s*(-?\d+(?:\.\d+)?)(?:\s*[;,]\s*(-?\d+(?:\.\d+)?))?\s*\)", text)
    if len(pts) < 2:
        return None
    p, q = ([float(v) for v in pt if v != ""] for pt in pts[:2])
    if len(p) != len(q):
        return None
    d = math.sqrt(sum((x - y) ** 2 for x, y in zip(p, q)))
    mid = "(" + "; ".join(num((x + y) / 2) for x, y in zip(p, q)) + ")"
    exact = sum((x - y) ** 2 for x, y in zip(p, q))
    root = f" = √{num(exact)}" if not is_int(d) else ""
    return f"Расстояние между точками: **{num(d)}**{root}\n\nСередина отрезка: {mid}\n\nФормула: d = √((x₂−x₁)² + (y₂−y₁)²{' + (z₂−z₁)²' if len(p) == 3 else ''})"


@ptool(CAT_M, "Площадь трапеции", "площадь трапеции основания 3 и 5 высота 4")
def trapezoid(text, low, s):
    if not re.search(r"площад\w*\s+трапеци", low):
        return None
    xs = nums(low)
    if len(xs) < 3:
        return None
    a, b, h = xs[:3]
    return f"Площадь трапеции = (a + b) / 2 · h = ({num(a)} + {num(b)}) / 2 · {num(h)} = **{num((a + b) / 2 * h)}**"


@ptool(CAT_M, "Площадь ромба", "площадь ромба диагонали 6 и 8")
def rhombus(text, low, s):
    if not re.search(r"площад\w*\s+ромб", low):
        return None
    xs = nums(low)
    if "диагонал" in low and len(xs) >= 2:
        return f"Площадь ромба = d₁ · d₂ / 2 = {num(xs[0])} · {num(xs[1])} / 2 = **{num(xs[0] * xs[1] / 2)}**"
    if "угол" in low and len(xs) >= 2:
        return f"Площадь ромба = a² · sin α = {num(xs[0])}² · sin {num(xs[1])}° = **{_r(xs[0] ** 2 * math.sin(math.radians(xs[1])), 3)}**"
    if len(xs) >= 2:
        return f"Площадь ромба = сторона · высота = {num(xs[0])} · {num(xs[1])} = **{num(xs[0] * xs[1])}**"
    return None


@ptool(CAT_M, "Площадь параллелограмма", "площадь параллелограмма основание 5 высота 3")
def parallelogram(text, low, s):
    if not re.search(r"площад\w*\s+параллелограмм", low):
        return None
    xs = nums(low)
    if len(xs) < 2:
        return None
    if "угол" in low and len(xs) >= 3:
        return (f"Площадь = a · b · sin α = {num(xs[0])} · {num(xs[1])} · sin {num(xs[2])}° = "
                f"**{_r(xs[0] * xs[1] * math.sin(math.radians(xs[2])), 3)}**")
    return f"Площадь параллелограмма = основание · высота = {num(xs[0])} · {num(xs[1])} = **{num(xs[0] * xs[1])}**"


def _radius(low):
    r = _kw(low, "радиус", r"\br")
    if r is None:
        d = _kw(low, "диаметр")
        r = d / 2 if d is not None else None
    return r


@ptool(CAT_M, "Объём и площадь конуса", "объём конуса радиус 3 высота 4")
def cone(text, low, s):
    if not re.search(r"(?:объем|площад)\w*\s+(?:поверхност\w*\s+)?конус", low):
        return None
    r, h = _radius(low), _kw(low, "высот", r"\bh")
    if r is None or h is None:
        xs = nums(low)
        if len(xs) < 2:
            return None
        r, h = xs[:2]
    l = math.hypot(r, h)
    v = math.pi * r * r * h / 3
    return (f"Конус: r = {num(r)}, h = {num(h)}\n\n- объём V = π·r²·h / 3 = **{_r(v, 3)}**\n"
            f"- образующая l = √(r² + h²) = {_r(l, 3)}\n- боковая поверхность π·r·l = {_r(math.pi * r * l, 3)}\n"
            f"- полная поверхность π·r·(r + l) = {_r(math.pi * r * (r + l), 3)}")


@ptool(CAT_M, "Объём пирамиды", "объём пирамиды площадь основания 9 высота 4")
def pyramid(text, low, s):
    if not re.search(r"объем\w*\s+(?:правильн\w*\s+)?(?:четырехугольн\w*\s+|треугольн\w*\s+)?пирамид", low):
        return None
    h = _kw(low, "высот")
    base = _kw(low, r"площад\w*\s+основани")
    if base is None:
        a = _kw(low, r"сторон\w*\s+основани", "сторон")
        if a is not None:
            base = a * a if "треуг" not in low else math.sqrt(3) / 4 * a * a
    if base is None or h is None:
        return None
    return f"Объём пирамиды V = S·h / 3 = {_r(base, 3)} · {num(h)} / 3 = **{_r(base * h / 3, 3)}**"


@ptool(CAT_M, "Площадь поверхности шара (сферы)", "площадь поверхности шара радиус 2")
def sphere_area(text, low, s):
    if not re.search(r"площад\w*\s+(?:поверхност\w*\s+)?(?:шара|сфер)", low):
        return None
    r = _radius(low)
    if r is None:
        xs = nums(low)
        r = xs[0] if xs else None
    if r is None:
        return None
    return f"Площадь сферы S = 4·π·r² = 4·π·{num(r)}² = **{_r(4 * math.pi * r * r, 3)}**"


@ptool(CAT_M, "Объём параллелепипеда (коробки)", "объём параллелепипеда 2 на 3 на 4")
def cuboid(text, low, s):
    if not re.search(r"объем\w*\s+(?:прямоугольн\w*\s+)?(?:параллелепипед|коробк|ящик|контейнер|комнат|кузов)", low):
        return None
    xs = nums(low)
    if len(xs) < 3:
        return None
    a, b, c = xs[:3]
    return (f"Объём = a · b · c = {num(a)} · {num(b)} · {num(c)} = **{num(a * b * c)}**\n\n"
            f"Площадь поверхности: 2·(ab + bc + ac) = {num(2 * (a * b + b * c + a * c))}")


_NGON = [("двенадцатиугольник", 12), ("десятиугольник", 10), ("девятиугольник", 9), ("восьмиугольник", 8),
         ("семиугольник", 7), ("шестиугольник", 6), ("пятиугольник", 5), ("четырехугольник", 4), ("треугольник", 3),
         ("прямоугольник", 4), ("квадрат", 4)]


@ptool(CAT_M, "Углы и диагонали многоугольника", "сумма углов шестиугольника", before="Сумма, максимум и минимум списка")
def polygon(text, low, s):
    if not re.search(r"угл|диагонал", low) or not re.search(r"угольник|квадрат", low) or "площад" in low:
        return None
    m = re.search(r"(\d+)\s*-?\s*(?:ти|ми|и)?угольник", low)
    n = int(m.group(1)) if m else next((k for name, k in _NGON if name in low), None)
    if not n or n < 3 or n > 10000:
        return None
    total = (n - 2) * 180
    return (f"{n}-угольник:\n\n- сумма внутренних углов: (n − 2)·180° = **{num(total)}°**\n"
            f"- угол правильного {n}-угольника: **{_r(total / n, 2)}°**\n"
            f"- внешний угол правильного: {_r(360 / n, 2)}°\n- число диагоналей: n·(n − 3)/2 = {num(n * (n - 3) // 2)}")


@ptool(CAT_M, "Градусы ↔ радианы", "90 градусов в радианах")
def deg_rad(text, low, s):
    m = re.search(r"(" + NUM + r")\s*(?:°|градус\w*)\s+(?:в|это\s+сколько)\s+радиан", low)
    if m:
        x = f(m.group(1))
        q = Fraction(x / 180).limit_denominator(720)
        pi = ""
        if abs(float(q) * 180 - x) < 1e-9 and q != 0:
            top = "π" if q.numerator == 1 else ("−π" if q.numerator == -1 else f"{q.numerator}π")
            pi = f" = {top}" + (f"/{q.denominator}" if q.denominator != 1 else "")
        return f"{num(x)}° = **{num(math.radians(x))} рад**{pi}"
    m = re.search(r"(" + NUM + r")?\s*(π|пи)?\s*(?:/\s*(\d+))?\s*рад\w*\s+(?:в|это\s+сколько)\s+градус", low)
    if m and (m.group(1) or m.group(2)):
        x = f(m.group(1)) if m.group(1) else 1.0
        if m.group(2):
            x *= math.pi
        if m.group(3):
            x /= int(m.group(3))
        return f"{num(x)} рад = **{num(math.degrees(x))}°**"
    return None


@ptool(CAT_M, "Стандартное отклонение и дисперсия", "стандартное отклонение 2 4 4 4 5 5 7 9", before="Среднее арифметическое")
def stdev(text, low, s):
    if not re.search(r"стандартн\w*\s+отклонени|среднеквадратичн|дисперси|\bсигм", low):
        return None
    xs = nums(low)
    if len(xs) < 2:
        return None
    mean = statistics.fmean(xs)
    return (f"Для {len(xs)} чисел (среднее {_r(mean, 4)}):\n\n"
            f"- стандартное отклонение генеральной совокупности σ = **{_r(statistics.pstdev(xs), 4)}**\n"
            f"- выборочное стандартное отклонение s = **{_r(statistics.stdev(xs), 4)}**\n"
            f"- дисперсия: σ² = {_r(statistics.pvariance(xs), 4)}, выборочная s² = {_r(statistics.variance(xs), 4)}")


@ptool(CAT_M, "Мода — самое частое значение", "мода 1 2 2 3 3 3")
def mode(text, low, s):
    if not re.search(r"(?:^|\s)мод[аыуе]\b", low):
        return None
    xs = nums(low)
    if len(xs) < 3:
        return None
    modes = statistics.multimode(xs)
    cnt = xs.count(modes[0])
    if cnt == 1:
        return "Моды нет: все значения встречаются по одному разу."
    return f"Мода: **{', '.join(num(m) for m in modes)}** (встречается {cnt} {_plural(cnt, 'раз', 'раза', 'раз')})."


@ptool(CAT_M, "Размах ряда чисел", "размах 3 9 1 7")
def spread(text, low, s):
    if not re.search(r"\bразмах\b", low):
        return None
    xs = nums(low)
    if len(xs) < 2:
        return None
    return f"Размах = максимум − минимум = {num(max(xs))} − {num(min(xs))} = **{num(max(xs) - min(xs))}**"


# ---- многочлены: производная и интеграл
def _poly(expr):
    e = expr.lower().replace(" ", "").replace("х", "x").replace("−", "-").replace("–", "-")
    e = e.replace("²", "^2").replace("³", "^3").replace("**", "^").replace("*", "").replace(",", ".")
    e = e.strip("?.!;:")
    e = re.sub(r"^(?:f\(x\)|y)=", "", e)
    e = re.sub(r"dx$", "", e)
    if not e or not re.fullmatch(r"[0-9x^+\-./()]+", e) or "x" not in e:
        return None
    e = e.replace("(", "").replace(")", "")
    if e[0] not in "+-":
        e = "+" + e
    coefs, pos = {}, 0
    for m in re.finditer(r"([+-])([^+-]+)", e):
        if m.start() != pos:
            return None
        pos = m.end()
        t = re.fullmatch(r"(\d+(?:\.\d+)?(?:/\d+)?)?(x(?:\^(\d+))?)?", m.group(2))
        if not t or (t.group(1) is None and t.group(2) is None):
            return None
        c = Fraction(t.group(1)) if t.group(1) else Fraction(1)
        p = (int(t.group(3)) if t.group(3) else 1) if t.group(2) else 0
        if p > 50:
            return None
        coefs[p] = coefs.get(p, 0) + (-c if m.group(1) == "-" else c)
    return coefs if pos == len(e) else None


def _poly_str(c):
    terms = []
    for p in sorted(c, reverse=True):
        k = Fraction(c[p])
        if k == 0:
            continue
        a = abs(k)
        if p == 0:
            body = _frac(a)
        else:
            coef = "" if a == 1 else (_frac(a) if a.denominator == 1 else f"({_frac(a)})")
            body = coef + "x" + (_sup(p) if p != 1 else "")
        terms.append(("-" if k < 0 else "+", body))
    if not terms:
        return "0"
    out = ("−" if terms[0][0] == "-" else "") + terms[0][1]
    for sign, body in terms[1:]:
        out += (" − " if sign == "-" else " + ") + body
    return out


@ptool(CAT_M, "Производная многочлена", "производная x^3 + 2x^2 - x")
def derivative(text, low, s):
    m = re.search(r"(втор\w*\s+)?производн\w*\s*(?:от\s+|функции\s+)?(.+)$", low)
    if not m:
        return None
    c = _poly(m.group(2))
    if not c:
        return None
    d = {p - 1: k * p for p, k in c.items() if p > 0}
    if m.group(1):
        d2 = {p - 1: k * p for p, k in d.items() if p > 0}
        return f"f(x) = {_poly_str(c)}\n\nf′(x) = {_poly_str(d)}\n\nf″(x) = **{_poly_str(d2)}**"
    return f"f(x) = {_poly_str(c)}\n\nf′(x) = **{_poly_str(d)}**\n\nПравило: (xⁿ)′ = n·xⁿ⁻¹, производная числа = 0."


@ptool(CAT_M, "Интеграл многочлена (неопределённый и определённый)", "интеграл x^2 + 3x")
def integral(text, low, s):
    m = re.search(r"(?:неопределенн\w*\s+|определенн\w*\s+)?интеграл\w*\s*(?:от\s+)?(.+)$", low)
    if not m:
        return None
    expr, lim = m.group(1), None
    mm = re.search(r"\s+от\s+(" + NUM + r")\s+до\s+(" + NUM + r")\s*$", expr)
    if mm:
        lim = (Fraction(mm.group(1).replace(",", ".")), Fraction(mm.group(2).replace(",", ".")))
        expr = expr[:mm.start()]
    c = _poly(expr)
    if not c:
        return None
    F = {p + 1: Fraction(k) / (p + 1) for p, k in c.items()}
    out = f"∫ ({_poly_str(c)}) dx = **{_poly_str(F)} + C**"
    if lim:
        val = sum(k * (lim[1] ** p - lim[0] ** p) for p, k in F.items())
        approx = "" if val.denominator == 1 else f" ≈ {num(float(val))}"
        out += f"\n\nОпределённый интеграл от {_frac(lim[0])} до {_frac(lim[1])}: F({_frac(lim[1])}) − F({_frac(lim[0])}) = **{_frac(val)}**{approx}"
    return out + "\n\nПравило: ∫xⁿ dx = xⁿ⁺¹/(n + 1) + C."


@ptool(CAT_M, "Гипотеза Коллатца (3n + 1)", "коллатц 27")
def collatz(text, low, s):
    if not re.search(r"коллатц|сиракуз|3n\s*\+\s*1", low):
        return None
    k = [x for x in ints(low) if x not in (3, 1)] or ints(low)
    if not k or k[0] < 1 or k[0] > 10 ** 15:
        return None
    n, steps, top, seq = k[0], 0, k[0], [k[0]]
    while n != 1 and steps < 100000:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
        top = max(top, n)
        if len(seq) < 25:
            seq.append(n)
    tail = " → …" if steps >= 25 else ""
    return (f"Последовательность Коллатца для {k[0]}: **{num(steps)} шагов** до 1, максимум — {num(top)}.\n\n"
            + " → ".join(map(str, seq)) + tail +
            "\n\nПравило: чётное делим на 2, нечётное умножаем на 3 и прибавляем 1.")


@ptool(CAT_M, "Научная (стандартная) запись числа", "123456789 в научной записи")
def sci_notation(text, low, s):
    m = (re.search(r"(-?\d[\d\s]*(?:[.,]\d+)?)\s+(?:в\s+)?(?:научн|стандартн|экспоненциальн)\w*\s+(?:запис|вид|форм)", low)
         or re.search(r"(?:научн|стандартн|экспоненциальн)\w*\s+(?:запис|вид|форм)\w*\s*:?\s*(-?\d[\d\s]*(?:[.,]\d+)?)", low))
    if not m:
        return None
    x = f(m.group(1).replace(" ", ""))
    if x == 0:
        return "0 = 0 × 10⁰"
    e = int(math.floor(math.log10(abs(x))))
    mant = x / 10 ** e
    return f"{num(x)} = **{num(round(mant, 6))} × 10{_sup(e)}** (в программах: {mant:.6g}e{e})"


@ptool(CAT_M, "Десятичная дробь в обыкновенную (и периодическая)", "0,375 в обыкновенную дробь", before="Точные дроби")
def dec_to_frac(text, low, s):
    if not re.search(r"(?:обыкновенн|прост|несократим)\w*\s+дроб|в\s+виде\s+дроби", low):
        return None
    m = re.search(r"(-?)(\d+)[.,](\d*)\((\d+)\)", low)
    if m:  # периодическая: 0,1(6)
        sign, whole, pre, per = m.groups()
        a = int(whole + pre + per) - int(whole + pre)
        b = int("9" * len(per) + "0" * len(pre))
        q = Fraction(a, b) * (-1 if sign else 1)
        return f"{m.group(0)} = **{_frac(q)}** (периодическая дробь)"
    m = re.search(r"-?\d+[.,]\d+", low)
    if not m:
        return None
    q = Fraction(m.group(0).replace(",", "."))
    whole = ""
    if abs(q) > 1 and q.denominator != 1:
        w = int(q)
        whole = f" = {w} целых {_frac(abs(q - w))}"
    return f"{m.group(0)} = **{_frac(q)}**{whole}"


@ptool(CAT_M, "Дробь в проценты", "3/8 в процентах")
def frac_to_pct(text, low, s):
    m = re.search(r"(\d+)\s*/\s*(\d+)\s+(?:это\s+сколько\s+|в\s+)?процент", low)
    if m and int(m.group(2)):
        a, b = int(m.group(1)), int(m.group(2))
        return f"{a}/{b} = {num(a / b)} = **{num(a / b * 100)}%**"
    m = re.search(r"(\d+[.,]\d+)\s+(?:это\s+сколько\s+|в\s+)процент", low)
    if m:
        x = f(m.group(1))
        return f"{m.group(1)} = **{num(x * 100)}%**"
    return None


@ptool(CAT_M, "Скорость, время и расстояние", "время в пути 300 км при скорости 75 км/ч", early=True)
def motion(text, low, s):
    if not re.search(r"скорост|расстояни|врем\w*\s+в\s+пути|за\s+сколько\s+(?:доеду|дойду|проеду|долечу)|сколько\s+(?:ехать|идти|лететь|плыть)|проед|пролет", low):
        return None
    if re.search(r"печат|набор|интернет|скачив|загрузк|мбит|звук|свет", low):
        return None
    dm = re.search(r"(" + NUM + r")\s*(км|м|миль)(?![/\w])", low)
    vm = re.search(r"(" + NUM + r")\s*(км/ч|км\s+в\s+час|м/с|узл\w*)", low)
    tm = re.search(r"(" + NUM + r")\s*(час\w*|ч|мин\w*|сек\w*|с)(?![а-я/])", low)
    dist = f(dm.group(1)) * (1.609344 if dm.group(2) == "миль" else 0.001 if dm.group(2) == "м" else 1) if dm else None
    speed = None
    if vm:
        speed = f(vm.group(1)) * (3.6 if vm.group(2) == "м/с" else 1.852 if vm.group(2).startswith("узл") else 1)
    tt = None
    if tm:
        u = tm.group(2)
        tt = f(tm.group(1)) / (60 if u.startswith("мин") else 3600 if u.startswith("сек") or u == "с" else 1)
    known = sum(x is not None for x in (dist, speed, tt))
    if known < 2:
        return None
    if dist is not None and speed is not None and speed > 0:
        return f"Время в пути = расстояние / скорость = {num(dist)} км / {num(speed)} км/ч = **{_dur(dist / speed)}**"
    if speed is not None and tt is not None:
        return f"Расстояние = скорость · время = {num(speed)} км/ч · {_dur(tt)} = **{_r(speed * tt, 2)} км**"
    if dist is not None and tt:
        v = dist / tt
        return f"Скорость = расстояние / время = {num(dist)} км / {_dur(tt)} = **{_r(v, 2)} км/ч** ({_r(v / 3.6, 2)} м/с)"
    return None


@ptool(CAT_M, "Разделить в пропорции (по долям)", "раздели 1000 в пропорции 2:3", before="Пропорция (найти x)")
def prop_split(text, low, s):
    m = re.search(r"(?:раздел|подел|распредел)\w*\s+(" + NUM + r")\s*(?:\S+\s+)?(?:в\s+(?:пропорци|отношени)\w*|пропорционально)\s+([\d\s:,.к]+)", low)
    if not m:
        return None
    total = f(m.group(1))
    shares = [f(x) for x in re.findall(r"\d+(?:[.,]\d+)?", m.group(2).replace(" к ", ":"))]
    if len(shares) < 2 or sum(shares) <= 0:
        return None
    unit = total / sum(shares)
    parts = [unit * x for x in shares]
    return (f"{num(total)} в пропорции {':'.join(num(x) for x in shares)}:\n\n" +
            "\n".join(f"- {i + 1}-я часть: **{_r(p, 2)}**" for i, p in enumerate(parts)) +
            f"\n\nОдна доля = {num(total)} / {num(sum(shares))} = {_r(unit, 4)}")


@ptool(CAT_M, "Вероятность: схема Бернулли (k успехов из n)", "вероятность 2 успехов из 5 при p=0,3")
def binomial(text, low, s):
    m = re.search(r"вероятност\w*\s+(?:ровно\s+|не\s+менее\s+|хотя\s+бы\s+|не\s+более\s+)?(\d+)\s+\w+\s+из\s+(\d+)", low)
    if not m:
        return None
    k, n = int(m.group(1)), int(m.group(2))
    pm = re.search(r"\bp\s*=\s*(" + NUM + r")|вероятност\w*\s+(?:успеха\s+)?(" + NUM + r")\s*%", low)
    if pm:
        p = f(pm.group(1)) if pm.group(1) else f(pm.group(2)) / 100
    elif re.search(r"монет|орл|решк", low):
        p = 0.5
    elif re.search(r"кубик|шестерк|кост", low):
        p = 1 / 6
    else:
        return None
    if not (0 <= p <= 1) or k > n or n > 1000:
        return None
    pk = lambda i: math.comb(n, i) * p ** i * (1 - p) ** (n - i)  # noqa: E731
    exact = pk(k)
    atleast = sum(pk(i) for i in range(k, n + 1))
    atmost = sum(pk(i) for i in range(0, k + 1))
    return (f"n = {n} испытаний, p = {num(p)}:\n\n- ровно {k}: P = C({n},{k})·p^{k}·(1−p)^{n - k} = **{_r(exact * 100, 3)}%**\n"
            f"- не менее {k}: {_r(atleast * 100, 3)}%\n- не более {k}: {_r(atmost * 100, 3)}%")


# ================================================================ ФИЗИКА И ХИМИЯ
CAT_S = "Физика и химия"
G = 9.80665


def _volts(low):
    m = re.search(r"(" + NUM + r")\s*(?:киловольт\w*|кв(?![а-я]))", low)
    if m:
        return f(m.group(1)) * 1000
    m = re.search(r"(" + NUM + r")\s*(?:вольт\w*|в)(?![a-zа-я])", low)
    return f(m.group(1)) if m else None


def _amps(low):
    m = re.search(r"(" + NUM + r")\s*(?:миллиампер\w*|ма)(?![a-zа-я])", low)
    if m:
        return f(m.group(1)) / 1000
    m = re.search(r"(" + NUM + r")\s*(?:ампер\w*|а)(?![a-zа-я])", low)
    return f(m.group(1)) if m else None


def _ohms(low):
    m = re.search(r"(" + NUM + r")\s*(ком|мом|ом)(?![a-zа-я])", low)
    if not m:
        return None
    return f(m.group(1)) * {"ком": 1e3, "мом": 1e6, "ом": 1}[m.group(2)]


def _watts(low):
    m = re.search(r"(" + NUM + r")\s*(квт|киловатт\w*|вт|ватт\w*)(?![a-zа-я·*]|\s*[·*]?\s*ч)", low)
    if not m:
        return None
    return f(m.group(1)) * (1000 if m.group(2).startswith("к") else 1)


@ptool(CAT_S, "Закон Ома: ток, напряжение, сопротивление", "ток при напряжении 220 в и сопротивлении 100 ом")
def ohm(text, low, s):
    if not re.search(r"(?<![а-я])ток|напряжени|сопротивлени|закон\w*\s+ома", low) or re.search(r"формул|мощност|соединени", low):
        return None
    U, I, R = _volts(low), _amps(low), _ohms(low)
    if sum(x is not None for x in (U, I, R)) < 2:
        return None
    if U is not None and R:
        I = U / R
        return f"Ток I = U / R = {num(U)} В / {num(R)} Ом = **{_r(I, 4)} А**\n\nМощность P = U·I = {_r(U * I, 2)} Вт"
    if I is not None and R is not None:
        U = I * R
        return f"Напряжение U = I · R = {num(I)} А · {num(R)} Ом = **{_r(U, 3)} В**\n\nМощность P = U·I = {_r(U * I, 2)} Вт"
    if U is not None and I:
        R = U / I
        return f"Сопротивление R = U / I = {num(U)} В / {num(I)} А = **{_r(R, 3)} Ом**\n\nМощность P = U·I = {_r(U * I, 2)} Вт"
    return None


@ptool(CAT_S, "Электрическая мощность (P = U·I)", "мощность при напряжении 220 в и токе 5 а")
def el_power(text, low, s):
    if not re.search(r"мощност", low) or re.search(r"работ\w*\s+\d|дж|кондиционер", low):
        return None
    U, I, R = _volts(low), _amps(low), _ohms(low)
    if U is not None and I is not None:
        P = U * I
    elif I is not None and R is not None:
        P = I * I * R
    elif U is not None and R:
        P = U * U / R
    else:
        return None
    return f"Мощность P = **{_r(P, 2)} Вт** ({_r(P / 1000, 3)} кВт)\n\nФормулы: P = U·I = I²·R = U²/R"


@ptool(CAT_S, "Сколько стоит электричество для прибора", "сколько стоит электричество 2000 вт 3 часа в день по 6 рублей", early=True)
def el_cost(text, low, s):
    if not re.search(r"электричеств|электроэнерги|квт\W*ч|киловатт|сколько\s+(?:мотает|нагорит|наматывает|потребляет)", low):
        return None
    P = _watts(low)
    hm = re.search(r"(" + NUM + r")\s*(?:час\w*|ч)(?![а-я])", low)
    pm = re.search(r"(?:по|тариф\w*|цен\w*)\s*(" + NUM + r")\s*(?:руб|₽|р\b|коп)?|(" + NUM + r")\s*(?:руб\w*|₽)\s*(?:за\s+)?(?:квт|киловатт)", low)
    if P is None or not hm:
        return None
    hours = f(hm.group(1))
    day = P / 1000 * hours
    out = (f"Прибор {num(P)} Вт · {num(hours)} ч в день:\n\n- в день: **{_r(day, 3)} кВт·ч**\n"
           f"- в месяц (30 дней): {_r(day * 30, 2)} кВт·ч\n- в год: {_r(day * 365, 1)} кВт·ч")
    if pm:
        price = f(pm.group(1) or pm.group(2))
        out += (f"\n\nПри тарифе {num(price)} ₽ за кВт·ч: **{rub(day * price)} в день**, "
                f"{rub(day * price * 30)} в месяц, {rub(day * price * 365)} в год.")
    return out


def _mass_kg(low):
    m = re.search(r"(" + NUM + r")\s*(кг|килограмм\w*|г|гр|грамм\w*|т|тонн\w*)(?![a-zа-я/])", low)
    if not m:
        m2 = re.search(r"масс\w*\s*(?:=|-)?\s*(" + NUM + ")", low)
        return f(m2.group(1)) if m2 else None
    k = {"к": 1, "г": 0.001, "т": 1000}[m.group(2)[0]]
    return f(m.group(1)) * k


def _speed_ms(low):
    m = re.search(r"(" + NUM + r")\s*(м/с|км/ч|км\s+в\s+час)", low)
    if not m:
        m2 = re.search(r"скорост\w*\s*(?:=|-)?\s*(" + NUM + ")", low)
        return f(m2.group(1)) if m2 else None
    return f(m.group(1)) / (3.6 if m.group(2) != "м/с" else 1)


@ptool(CAT_S, "Кинетическая энергия", "кинетическая энергия масса 2 кг скорость 3 м/с")
def kinetic(text, low, s):
    if not re.search(r"кинетическ\w*\s+энерги", low):
        return None
    m, v = _mass_kg(low), _speed_ms(low)
    if m is None or v is None:
        return None
    e = m * v * v / 2
    return f"Кинетическая энергия E = m·v²/2 = {num(m)} кг · ({_r(v, 3)} м/с)² / 2 = **{_r(e, 3)} Дж**"


@ptool(CAT_S, "Потенциальная энергия", "потенциальная энергия масса 2 кг высота 10 м")
def potential(text, low, s):
    if not re.search(r"потенциальн\w*\s+энерги", low):
        return None
    m = _mass_kg(low)
    h = _kw(low, "высот")
    if h is None:
        hm = re.search(r"(" + NUM + r")\s*м(?![a-zа-я/])", low)
        h = f(hm.group(1)) if hm else None
    if m is None or h is None:
        return None
    return f"Потенциальная энергия E = m·g·h = {num(m)} · 9,81 · {num(h)} = **{_r(m * G * h, 2)} Дж**"


_GRAVITY = [("меркури", "Меркурии", 3.70), ("венер", "Венере", 8.87), ("лун", "Луне", 1.62), ("марс", "Марсе", 3.71),
            ("юпитер", "Юпитере", 24.79), ("сатурн", "Сатурне", 10.44), ("уран", "Уране", 8.69),
            ("нептун", "Нептуне", 11.15), ("плутон", "Плутоне", 0.62), ("солнц", "Солнце", 274.0)]


@ptool(CAT_S, "Сколько я буду весить на других планетах", "сколько я буду весить на Марсе при весе 70 кг")
def planet_weight(text, low, s):
    if not re.search(r"весил|вес\w*|сколько\s+(?:буду\s+)?(?:я\s+)?(?:буду\s+)?весить", low):
        return None
    if not re.search(r"(?:на|на\s+других)\s+(?:меркури|венер|лун|марс|юпитер|сатурн|уран(?![а-я]{3})|нептун|плутон|солнц|планет)", low):
        return None
    wm = re.search(r"(" + NUM + r")\s*(?:кг|килограмм)", low)
    w = f(wm.group(1)) if wm else None
    if w is None:
        return None
    rows = [(name, w * g / G) for stem, name, g in _GRAVITY if re.search(r"на\s+" + stem, low)]
    if not rows:
        rows = [(name, w * g / G) for _, name, g in _GRAVITY]
    head = f"На Земле {num(w)} кг. Весы покажут:\n\n"
    return head + "\n".join(f"- на {name}: **{_r(x, 1)} кг**" for name, x in rows) + "\n\nМасса тела не меняется — меняется сила тяжести."


@ptool(CAT_S, "Плотность, масса и объём", "плотность масса 10 кг объём 2 м3")
def density(text, low, s):
    if not re.search(r"плотност", low):
        return None
    rho_m = re.search(r"(" + NUM + r")\s*(кг/м3|кг/м³|г/см3|г/см³|г/мл|кг/л)", low)
    rho = None
    if rho_m:
        rho = f(rho_m.group(1)) * (1000 if rho_m.group(2) in ("г/см3", "г/см³", "г/мл", "кг/л") else 1)
    m_ = re.search(r"(" + NUM + r")\s*(кг|г|т)(?![a-zа-я/])", low)
    mass = f(m_.group(1)) * {"кг": 1, "г": 0.001, "т": 1000}[m_.group(2)] if m_ else None
    v_ = re.search(r"(" + NUM + r")\s*(м3|м³|куб\w*\s*м\w*|л|литр\w*|см3|см³|мл)(?![a-zа-я/])", low)
    vol = None
    if v_:
        u = v_.group(2)
        vol = f(v_.group(1)) * (1 if u in ("м3", "м³") or u.startswith("куб") else 0.001 if u in ("л",) or u.startswith("литр") else 1e-6)
    if mass is not None and vol:
        r = mass / vol
        return f"Плотность ρ = m / V = {num(mass)} кг / {num(vol)} м³ = **{_r(r, 3)} кг/м³** ({_r(r / 1000, 4)} г/см³)"
    if rho is not None and vol is not None:
        return f"Масса m = ρ · V = {num(rho)} кг/м³ · {num(vol)} м³ = **{_r(rho * vol, 3)} кг**"
    if rho and mass is not None:
        return f"Объём V = m / ρ = {num(mass)} кг / {num(rho)} кг/м³ = **{_r(mass / rho, 5)} м³** ({_r(mass / rho * 1000, 3)} л)"
    return None


@ptool(CAT_S, "Свободное падение с высоты", "время падения с высоты 20 м")
def free_fall(text, low, s):
    if not re.search(r"падени|падать|упад|брос\w*\s+с\s+высот|с\s+высоты", low):
        return None
    hm = re.search(r"(" + NUM + r")\s*(?:м|метр\w*)(?![a-zа-я/])", low)
    if not hm:
        return None
    h = f(hm.group(1))
    t = math.sqrt(2 * h / G)
    v = G * t
    return (f"Падение с высоты {num(h)} м (без сопротивления воздуха):\n\n- время: **{_r(t, 2)} с**\n"
            f"- скорость у земли: **{_r(v, 2)} м/с** ({_r(v * 3.6, 1)} км/ч)\n\nФормулы: t = √(2h/g), v = g·t")


@ptool(CAT_S, "Давление (сила на площадь и в воде)", "давление сила 100 н площадь 2 м2")
def pressure(text, low, s):
    if not re.search(r"давлени", low) or re.search(r"артериальн|\d+\s*(?:на|/)\s*\d+\s*(?:мм|$)", low):
        return None
    dm = re.search(r"глубин\w*\s*(" + NUM + r")|(" + NUM + r")\s*м\w*\s+(?:глубин|под\s+водой)", low)
    if dm:
        h = f(dm.group(1) or dm.group(2))
        p = 1000 * G * h
        return (f"На глубине {num(h)} м в пресной воде: гидростатическое давление ρgh = **{_r(p / 1000, 2)} кПа** "
                f"({_r(p / 101325, 3)} атм), вместе с атмосферой — {_r((p + 101325) / 101325, 3)} атм.")
    fm = re.search(r"(" + NUM + r")\s*(кн|н|ньютон\w*)(?![a-zа-я])", low)
    am = re.search(r"(" + NUM + r")\s*(м2|м²|кв\.?\s*м|см2|см²|мм2|мм²)", low)
    if not fm or not am:
        return None
    F = f(fm.group(1)) * (1000 if fm.group(2) == "кн" else 1)
    A = f(am.group(1)) * (1e-4 if am.group(2).startswith("см") else 1e-6 if am.group(2).startswith("мм") else 1)
    p = F / A
    return f"Давление p = F / S = {num(F)} Н / {num(A)} м² = **{_r(p, 3)} Па** ({_r(p / 1000, 4)} кПа)"


@ptool(CAT_S, "Механическая работа и мощность", "мощность работа 600 дж за 2 с")
def mech_power(text, low, s):
    if not re.search(r"мощност|работ", low):
        return None
    jm = re.search(r"(" + NUM + r")\s*(кдж|дж|джоул\w*)(?![a-zа-я])", low)
    tm = re.search(r"(" + NUM + r")\s*(с|сек\w*|мин\w*|ч|час\w*)(?![a-zа-я])", low)
    if jm and tm:
        A = f(jm.group(1)) * (1000 if jm.group(2) == "кдж" else 1)
        u = tm.group(2)
        t = f(tm.group(1)) * (60 if u.startswith("мин") else 3600 if u.startswith("ч") else 1)
        return f"Мощность N = A / t = {num(A)} Дж / {num(t)} с = **{_r(A / t, 3)} Вт**"
    fm = re.search(r"(" + NUM + r")\s*(н|ньютон\w*)(?![a-zа-я])", low)
    sm = re.search(r"(" + NUM + r")\s*(м|метр\w*)(?![a-zа-я/])", low)
    if fm and sm and "работ" in low:
        A = f(fm.group(1)) * f(sm.group(1))
        return f"Работа A = F · s = {num(f(fm.group(1)))} Н · {num(f(sm.group(1)))} м = **{_r(A, 3)} Дж**"
    return None


@ptool(CAT_S, "Ускорение и разгон", "ускорение от 0 до 100 км/ч за 5 секунд")
def acceleration(text, low, s):
    if not re.search(r"ускорени|разгон", low):
        return None
    m = re.search(r"от\s+(" + NUM + r")\s+до\s+(" + NUM + r")\s*(км/ч|м/с)", low)
    tm = re.search(r"за\s+(" + NUM + r")\s*(?:с|сек)", low)
    if not m or not tm:
        return None
    k = 1 / 3.6 if m.group(3) == "км/ч" else 1
    v0, v1, t = f(m.group(1)) * k, f(m.group(2)) * k, f(tm.group(1))
    if t <= 0:
        return None
    a = (v1 - v0) / t
    return (f"Ускорение a = (v − v₀) / t = **{_r(a, 3)} м/с²** ({_r(a / G, 3)} g)\n\n"
            f"Путь за время разгона: (v₀ + v)/2 · t = {_r((v0 + v1) / 2 * t, 1)} м")


_ATOMIC = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998,
    "Ne": 20.180, "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45,
    "Ar": 39.948, "K": 39.098, "Ca": 40.078, "Sc": 44.956, "Ti": 47.867, "V": 50.942, "Cr": 51.996, "Mn": 54.938,
    "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ga": 69.723, "Ge": 72.630, "As": 74.922,
    "Se": 78.971, "Br": 79.904, "Kr": 83.798, "Rb": 85.468, "Sr": 87.62, "Y": 88.906, "Zr": 91.224, "Nb": 92.906,
    "Mo": 95.95, "Tc": 98.0, "Ru": 101.07, "Rh": 102.91, "Pd": 106.42, "Ag": 107.87, "Cd": 112.41, "In": 114.82,
    "Sn": 118.71, "Sb": 121.76, "Te": 127.60, "I": 126.90, "Xe": 131.29, "Cs": 132.91, "Ba": 137.33, "La": 138.91,
    "Ce": 140.12, "Pr": 140.91, "Nd": 144.24, "Pm": 145.0, "Sm": 150.36, "Eu": 151.96, "Gd": 157.25, "Tb": 158.93,
    "Dy": 162.50, "Ho": 164.93, "Er": 167.26, "Tm": 168.93, "Yb": 173.05, "Lu": 174.97, "Hf": 178.49, "Ta": 180.95,
    "W": 183.84, "Re": 186.21, "Os": 190.23, "Ir": 192.22, "Pt": 195.08, "Au": 196.97, "Hg": 200.59, "Tl": 204.38,
    "Pb": 207.2, "Bi": 208.98, "Po": 209.0, "At": 210.0, "Rn": 222.0, "Fr": 223.0, "Ra": 226.0, "Ac": 227.0,
    "Th": 232.04, "Pa": 231.04, "U": 238.03,
}


def _formula(src):
    """«H2SO4», «Ca(OH)2», «CuSO4·5H2O» → {элемент: количество}."""
    src = src.replace("[", "(").replace("]", ")").replace("*", "·").replace(".", "·")
    total = {}
    for part in src.split("·"):
        m = re.match(r"(\d+)(.*)", part)
        k, body = (int(m.group(1)), m.group(2)) if m else (1, part)
        counts, pos = _parse_group(body, 0)
        if pos != len(body) or not counts:
            return None
        for el, c in counts.items():
            total[el] = total.get(el, 0) + c * k
    return total


def _parse_group(s, i):
    out = {}
    while i < len(s):
        ch = s[i]
        if ch == "(":
            inner, i = _parse_group(s, i + 1)
            if i >= len(s) or s[i] != ")":
                return {}, -1
            i += 1
            m = re.match(r"\d+", s[i:])
            k = int(m.group(0)) if m else 1
            i += len(m.group(0)) if m else 0
            for el, c in inner.items():
                out[el] = out.get(el, 0) + c * k
        elif ch == ")":
            return out, i
        else:
            m = re.match(r"([A-Z][a-z]?)(\d*)", s[i:])
            if not m or m.group(1) not in _ATOMIC:
                return {}, -1
            out[m.group(1)] = out.get(m.group(1), 0) + (int(m.group(2)) if m.group(2) else 1)
            i += len(m.group(0))
    return out, i


@ptool(CAT_S, "Молярная масса вещества", "молярная масса H2SO4")
def molar_mass(text, low, s):
    if not re.search(r"(?:молярн|молекулярн)\w*\s+масс", low):
        return None
    m = re.search(r"масс\w*\s+(?:вещества\s+)?([A-Z][A-Za-z0-9()\[\]·.*]*)", text)
    if not m:
        return None
    comp = _formula(m.group(1).rstrip(".·"))
    if not comp:
        return None
    total = sum(_ATOMIC[el] * c for el, c in comp.items())
    parts = "\n".join(f"- {el}: {c} × {num(_ATOMIC[el])} = {_r(_ATOMIC[el] * c, 3)} ({_r(_ATOMIC[el] * c / total * 100, 2)}%)"
                      for el, c in comp.items())
    return f"Молярная масса {m.group(1)}: **{_r(total, 2)} г/моль**\n\n{parts}"


_EL_RU = [("водород", "H"), ("гели", "He"), ("лити", "Li"), ("бериллий", "Be"), ("бор", "B"), ("углерод", "C"),
          ("азот", "N"), ("кислород", "O"), ("фтор", "F"), ("натри", "Na"), ("магни", "Mg"), ("алюмини", "Al"),
          ("кремни", "Si"), ("фосфор", "P"), ("сер", "S"), ("хлор", "Cl"), ("кали", "K"), ("кальци", "Ca"),
          ("хром", "Cr"), ("марган", "Mn"), ("желез", "Fe"), ("никел", "Ni"), ("мед", "Cu"), ("цинк", "Zn"),
          ("бром", "Br"), ("серебр", "Ag"), ("йод", "I"), ("бари", "Ba"), ("золот", "Au"), ("ртут", "Hg"), ("свин", "Pb")]


@ptool(CAT_S, "Массовая доля элемента в веществе", "массовая доля кислорода в H2O")
def mass_fraction(text, low, s):
    if not re.search(r"массов\w*\s+дол", low):
        return None
    fm = re.findall(r"\b([A-Z][A-Za-z0-9()\[\]·]*\d[A-Za-z0-9()\[\]·]*|[A-Z][a-z]?[A-Z][A-Za-z0-9()]*)\b", text)
    if not fm:
        return None
    formula = fm[-1]
    comp = _formula(formula)
    if not comp:
        return None
    em = re.search(r"дол\w*\s+([A-Z][a-z]?)\b", text)
    el = em.group(1) if em else None
    if el is None:
        wm = re.search(r"дол\w*\s+([а-я]+)", low)
        if wm:
            el = next((sym for stem, sym in _EL_RU if wm.group(1).startswith(stem)), None)
    if el not in comp:
        return None
    total = sum(_ATOMIC[e] * c for e, c in comp.items())
    part = _ATOMIC[el] * comp[el]
    return f"Массовая доля {el} в {formula}: ω = {comp[el]}·{num(_ATOMIC[el])} / {_r(total, 3)} = **{_r(part / total * 100, 2)}%**"


@ptool(CAT_S, "Резисторы: последовательное и параллельное соединение", "параллельное соединение 10 ом и 20 ом")
def resistors(text, low, s):
    if not re.search(r"(?:параллельн|последовательн)\w*", low) or not re.search(r"\bом|резистор|сопротивлен", low):
        return None
    vals = [f(x) * {"ком": 1e3, "мом": 1e6}.get(u, 1) for x, u in re.findall(r"(" + NUM + r")\s*(ком|мом|ом)?(?![\d])", low) if x]
    vals = [v for v in vals if v > 0]
    if len(vals) < 2:
        return None
    if "параллельн" in low:
        R = 1 / sum(1 / v for v in vals)
        return f"Параллельно {', '.join(num(v) for v in vals)} Ом: 1/R = Σ 1/Rᵢ → **R = {_r(R, 3)} Ом**"
    return f"Последовательно: R = {' + '.join(num(v) for v in vals)} = **{num(sum(vals))} Ом**"


@ptool(CAT_S, "Сколько энергии нагреть воду (и время чайника)", "сколько энергии нужно чтобы нагреть 2 литра воды с 20 до 100 градусов", early=True)
def heat_water(text, low, s):
    if not re.search(r"нагре|вскипят|закипит|подогре", low) or not re.search(r"вод", low):
        return None
    vm = re.search(r"(" + NUM + r")\s*(л|литр\w*|мл|кг)(?![a-zа-я])", low)
    tm = re.search(r"(?:с|от)\s+(" + NUM + r")\s*(?:°|градус\w*)?\s+до\s+(" + NUM + ")", low)
    if not vm:
        return None
    mass = f(vm.group(1)) / (1000 if vm.group(2) == "мл" else 1)
    t0, t1 = (f(tm.group(1)), f(tm.group(2))) if tm else (20.0, 100.0)
    q = 4186 * mass * (t1 - t0)
    P = _watts(low) or 2000
    return (f"Нагреть {num(mass)} кг воды с {num(t0)} до {num(t1)} °C: Q = c·m·Δt = 4186 · {num(mass)} · {num(t1 - t0)} = "
            f"**{_r(q / 1000, 1)} кДж** ({_r(q / 3.6e6, 3)} кВт·ч)\n\nЧайник {num(P)} Вт справится примерно за "
            f"{_secs(q / (P * 0.85))} (с учётом потерь ~15%).")


@ptool(CAT_S, "Длина волны и частота", "длина волны частота 100 мгц")
def wavelength(text, low, s):
    if not re.search(r"длин\w*\s+волн|частот\w*\s+волн", low):
        return None
    c = 299_792_458
    fm = re.search(r"(" + NUM + r")\s*(ггц|мгц|кгц|гц)", low)
    if fm:
        hz = f(fm.group(1)) * {"ггц": 1e9, "мгц": 1e6, "кгц": 1e3, "гц": 1}[fm.group(2)]
        lam = c / hz
        shown = f"{_r(lam, 4)} м" if lam >= 1 else f"{_r(lam * 100, 4)} см" if lam >= 0.01 else f"{_r(lam * 1000, 4)} мм"
        return f"Длина волны λ = c / f = 299 792 458 / {num(hz)} = **{shown}**"
    lm = re.search(r"(" + NUM + r")\s*(нм|мм|см|м)(?![a-zа-я])", low)
    if lm:
        lam = f(lm.group(1)) * {"нм": 1e-9, "мм": 1e-3, "см": 1e-2, "м": 1}[lm.group(2)]
        hz = c / lam
        return f"Частота f = c / λ = **{num(round(hz / 1e6, 3))} МГц** ({num(hz)} Гц)"
    return None


# ================================================================ ФИНАНСЫ+
CAT_F = "Финансы+"


def _amount(low):
    """Главная сумма в запросе: число с «руб/₽/р» или самое большое число."""
    m = re.search(r"(\d[\d\s]*(?:[.,]\d+)?)\s*(?:тыс\w*\s*)?(?:руб\w*|₽|р\b)", low)
    if m:
        v = f(m.group(1).replace(" ", ""))
        return v * 1000 if re.search(re.escape(m.group(1)) + r"\s*тыс", low) else v
    xs = [x for x in nums(low)]
    return max(xs) if xs else None


def _years(low):
    m = re.search(r"(" + NUM + r")\s*(лет|год\w*|г\.)(?![а-я])", low)
    if m:
        return f(m.group(1))
    m = re.search(r"(" + NUM + r")\s*(месяц\w*|мес)(?![а-я])", low)
    return f(m.group(1)) / 12 if m else None


@ptool(CAT_F, "Инфляция: сколько будут стоить деньги", "100000 рублей через 5 лет при инфляции 8%")
def inflation(text, low, s):
    if not re.search(r"инфляци", low):
        return None
    rm = re.search(r"(" + NUM + r")\s*%", low)
    amount, years = _amount(low), _years(low)
    if not rm or amount is None or years is None:
        return None
    r = f(rm.group(1)) / 100
    real = amount / (1 + r) ** years
    need = amount * (1 + r) ** years
    return (f"При инфляции {num(r * 100)}% в год за {num(years)} {_plural(years, 'год', 'года', 'лет')}:\n\n"
            f"- {rub(amount)} сегодня будут «весить» как **{rub(real)}** (покупательная способность −{_r((1 - real / amount) * 100, 1)}%)\n"
            f"- чтобы купить то же, что сейчас на {rub(amount)}, понадобится **{rub(need)}**")


@ptool(CAT_F, "Окупаемость вложений", "окупаемость вложения 500000 при доходе 25000 в месяц")
def payback(text, low, s):
    if not re.search(r"окуп", low):
        return None
    xs = nums(low)
    if len(xs) < 2:
        return None
    inv = _kw(low, "вложени", "инвестици", "стоимост", "затрат", "вложил", "потрат") or max(xs)
    inc = _kw(low, "доход", "прибыл", "экономи", "выручк", "заработ")
    if inc is None:
        inc = min(xs)
    if inc <= 0:
        return None
    per_year = bool(re.search(r"в\s+год|ежегодно|годов", low))
    months = inv / inc * (12 if per_year else 1)
    return (f"Вложение {rub(inv)}, доход {rub(inc)} {'в год' if per_year else 'в месяц'}:\n\n"
            f"Окупится за **{_r(months, 1)} мес.** (≈ {_r(months / 12, 2)} {_plural(months / 12, 'год', 'года', 'лет')}). "
            f"Годовая доходность — {_r((inc * (1 if per_year else 12)) / inv * 100, 1)}%.")


_FX = [(r"доллар\w*|\$|usd", "$"), (r"евро|€|eur", "€"), (r"юан\w*|cny|rmb", "¥"), (r"тенге|kzt", "₸"),
       (r"фунт\w*|gbp", "£"), (r"(?:бел\w*\s+)?рубл\w*|руб|₽|rub|byn", "₽"), (r"лир\w*|try", "₺"),
       (r"гривн\w*|uah", "₴"), (r"йен\w*|иен\w*|jpy", "¥"), (r"дирхам\w*|aed", "AED"), (r"сум\w*|uzs", "сум"),
       (r"драм\w*|amd", "֏"), (r"лари|gel", "₾"), (r"бат\w*|thb", "฿")]


@ptool(CAT_F, "Пересчёт валюты по своему курсу", "1000 долларов по курсу 92,5")
def fx_rate(text, low, s):
    m = re.search(r"(" + NUM + r")\s*([^\d\s]+(?:\s+рубл\w*)?)\s+по\s+курсу\s+(" + NUM + ")", low)
    if not m:
        return None
    amount, cur, rate = f(m.group(1)), m.group(2), f(m.group(3))
    sym = next((sy for rx, sy in _FX if re.fullmatch(rx, cur)), None)
    if sym is None or rate <= 0:
        return None
    if sym == "₽" and "бел" not in cur:
        return f"{rub(amount)} по курсу {num(rate)} = **{money(amount / rate)}** единиц валюты"
    return f"{money(amount)} {sym} × {num(rate)} = **{rub(amount * rate)}**"


@ptool(CAT_F, "Бюджет по правилу 50/30/20", "распредели зарплату 80000 по правилу 50/30/20", before="Зарплата на руки после НДФЛ")
def budget_503020(text, low, s):
    if not re.search(r"50\s*/\s*30\s*/\s*20|правил\w*\s+(?:бюджет|50)|распредел\w*\s+(?:зарплат|доход|бюджет|деньг)", low):
        return None
    clean = re.sub(r"50\s*/\s*30\s*/\s*20", " ", low)
    xs = [x for x in nums(clean) if x > 100]
    if not xs:
        return None
    a = xs[0]
    return (f"Бюджет {rub(a)} по правилу 50/30/20:\n\n- 50% — обязательное (жильё, еда, транспорт, кредиты): **{rub(a * 0.5)}**\n"
            f"- 30% — желания (развлечения, кафе, покупки): **{rub(a * 0.3)}**\n"
            f"- 20% — накопления и подушка безопасности: **{rub(a * 0.2)}**\n\n"
            f"Подушка на 6 месяцев: {rub(a * 0.5 * 6)} (через {_r(a * 0.5 * 6 / (a * 0.2), 1)} мес. при откладывании 20%).")


@ptool(CAT_F, "Сколько откладывать, чтобы накопить", "сколько откладывать в месяц чтобы накопить 300000 за 2 года")
def save_goal(text, low, s):
    if not re.search(r"накопит|накоплю|откладыват|копить\s+на|сколько\s+копить", low):
        return None
    years = None
    m = re.search(r"за\s+(" + NUM + r")\s*(лет|год\w*|месяц\w*|мес)", low)
    if m:
        years = f(m.group(1)) / (12 if m.group(2).startswith("мес") else 1)
    goal = _kw(low, "накопить", "накоплю", "сумм", r"копить\s+на") or _amount(low)
    if not goal or not years:
        return None
    n = round(years * 12)
    if n < 1:
        return None
    rm = re.search(r"(?:под|доходност\w*|ставк\w*)\s*(" + NUM + r")\s*%", low)
    plain = goal / n
    out = f"Цель {rub(goal)} за {n} мес.:\n\n- без процентов: **{rub(plain)} в месяц**"
    if rm:
        r = f(rm.group(1)) / 100 / 12
        pmt = goal * r / ((1 + r) ** n - 1)
        out += f"\n- на вкладе под {num(f(rm.group(1)))}% годовых: **{rub(pmt)} в месяц** (проценты добавят {rub(goal - pmt * n)})"
    return out + f"\n- в неделю: {rub(goal / (years * 52))}, в день: {rub(goal / (years * 365))}"


@ptool(CAT_F, "Зарплата в час, день и год", "зарплата 90000 в месяц сколько в час", before="Зарплата на руки после НДФЛ")
def hourly_wage(text, low, s):
    if not re.search(r"зарплат|оклад|получаю|доход", low) or not re.search(r"в\s+час|за\s+час|в\s+день|за\s+день|в\s+год|за\s+год|почасов|в\s+минуту", low):
        return None
    xs = [x for x in nums(low) if x >= 100]
    if not xs:
        return None
    a = xs[0]
    per = "час" if re.search(r"(?:в|за)\s+час", low) and re.search(r"\d\s*(?:руб\w*|₽)?\s*(?:в|за)\s+час", low) else "месяц"
    month = a * 164.4 if per == "час" else a
    return (f"Зарплата {rub(month)} в месяц (40 ч в неделю, ≈ 164 рабочих часа и 21 рабочий день в месяц):\n\n"
            f"- в час: **{rub(month / 164.4)}**\n- в день: **{rub(month / 21)}**\n- в год: **{rub(month * 12)}**\n"
            f"- в минуту работы: {rub(month / 164.4 / 60)}\n\nНа руки после НДФЛ 13%: {rub(month * 0.87)} в месяц.")


@ptool(CAT_F, "Что выгоднее: цена за кг, литр или штуку", "что выгоднее 1,5 л за 120 или 2 л за 150")
def better_price(text, low, s):
    if not re.search(r"выгодн|дешевл", low):
        return None
    pairs = re.findall(r"(" + NUM + r")\s*(кг|г|гр|л|мл|шт\w*|штук\w*|рулон\w*|таблет\w*)?\s*(?:за|по)\s*(" + NUM + ")", low)
    if len(pairs) < 2:
        return None
    rows = []
    for qty, unit, price in pairs:
        q, p = f(qty), f(price)
        if q <= 0:
            return None
        base = {"г": ("кг", 1000), "гр": ("кг", 1000), "мл": ("л", 1000)}.get(unit, (unit or "шт", 1))
        rows.append((p / (q / base[1]), f"{qty} {unit or 'шт'} за {num(p)} ₽", base[0]))
    best = min(rows, key=lambda r: r[0])
    worst = max(rows, key=lambda r: r[0])
    lines = "\n".join(f"- {label}: **{rub(per)} за {u}**" for per, label, u in rows)
    gain = (1 - best[0] / worst[0]) * 100 if worst[0] else 0
    return f"{lines}\n\nВыгоднее: **{best[1]}** — дешевле на {_r(gain, 1)}% за единицу."


@ptool(CAT_F, "Простые проценты", "простые проценты 100000 под 10% на 3 года", before="Простое ли число")
def simple_interest(text, low, s):
    if not re.search(r"прост\w*\s+процент", low):
        return None
    rm = re.search(r"(" + NUM + r")\s*%", low)
    p, t = _amount(low), _years(low)
    if not rm or p is None or t is None:
        return None
    r = f(rm.group(1)) / 100
    i = p * r * t
    return f"Простые проценты: {rub(p)} · {num(r * 100)}% · {num(t)} г. = **{rub(i)}** дохода, итого {rub(p + i)}."


@ptool(CAT_F, "ROI — доходность вложений", "roi вложил 100000 получил 130000")
def roi(text, low, s):
    if not re.search(r"\broi\b|рентабельност|доходност\w*\s+(?:вложени|инвестиц)|вложил\D+\d[\d\s]*\D+(?:получил|вернул|продал)", low):
        return None
    inv = _kw(low, "вложил", "вложени", "потратил", "инвестировал", "купил", "затрат")
    ret = _kw(low, "получил", "вернул", "продал", "выручк", "доход")
    if not inv or ret is None:
        return None
    r = (ret - inv) / inv * 100
    out = f"ROI = (доход − вложения) / вложения = ({rub(ret)} − {rub(inv)}) / {rub(inv)} = **{_r(r, 2)}%**"
    yrs = _years(low)
    if yrs and yrs > 0 and ret > 0:
        out += f"\n\nВ пересчёте на год (за {num(yrs)} г.): {_r(((ret / inv) ** (1 / yrs) - 1) * 100, 2)}% годовых."
    return out


@ptool(CAT_F, "Отпускные (примерный расчёт)", "отпускные при зарплате 60000 за 14 дней", before="Зарплата на руки после НДФЛ")
def vacation_pay(text, low, s):
    if not re.search(r"отпускн", low):
        return None
    dm = re.search(r"(\d+)\s*(?:календарн\w*\s+)?(?:дн|день|дня|дней)", low)
    xs = [x for x in nums(low) if x >= 1000]
    if not dm or not xs:
        return None
    sal, days = xs[0], int(dm.group(1))
    avg = sal / 29.3
    pay = avg * days
    return (f"Средний дневной заработок: {rub(sal)} / 29,3 = {rub(avg)}\n\nОтпускные за {days} {_plural(days, 'день', 'дня', 'дней')}: "
            f"**{rub(pay)}** до НДФЛ, на руки ≈ **{rub(pay * 0.87)}**\n\n"
            "Расчёт примерный: если все 12 месяцев отработаны полностью, а премии учитываются в зарплате.")


@ptool(CAT_F, "Бензин на поездку", "бензин на 300 км расход 8 л на 100 по 55 рублей", early=True)
def trip_fuel(text, low, s):
    if not re.search(r"бензин|топлив|дизел|солярк|расход\w*\s+\d", low):
        return None
    dm = re.search(r"(" + NUM + r")\s*км(?![/\w])", low)
    cm = re.search(r"(" + NUM + r")\s*(?:л|литр\w*)\s*(?:на|/)\s*100", low)
    pm = re.search(r"по\s+(" + NUM + r")|(" + NUM + r")\s*(?:руб\w*|₽|р)\s*(?:за\s+)?(?:л|литр)", low)
    if not dm or not cm:
        return None
    km, cons = f(dm.group(1)), f(cm.group(1))
    liters = km * cons / 100
    out = f"{num(km)} км при расходе {num(cons)} л/100 км: **{_r(liters, 1)} л** топлива"
    if pm:
        price = f(pm.group(1) or pm.group(2))
        out += f" × {num(price)} ₽ = **{rub(liters * price)}**"
        pp = re.search(r"на\s+(\d+)\s+(?:человек|чел|пассажир)", low)
        if pp and int(pp.group(1)) > 0:
            out += f"\n\nНа каждого из {pp.group(1)}: {rub(liters * price / int(pp.group(1)))}"
        if "туда и обратно" in low:
            out += f"\n\nТуда и обратно: {rub(liters * price * 2)}"
    return out


@ptool(CAT_F, "Подписки: сколько в год", "подписка 299 в месяц сколько в год")
def subscriptions(text, low, s):
    if not re.search(r"подписк", low):
        return None
    xs = [x for x in nums(low) if x >= 1]
    if not xs:
        return None
    month = sum(xs) if re.search(r"подписк\w*\s+[\d\s,и]+(?:руб\w*|₽)?\s*(?:,|и)", low) and len(xs) > 1 else xs[0]
    return (f"Подписки {rub(month)} в месяц — это **{rub(month * 12)} в год**, {rub(month * 12 * 5)} за 5 лет "
            f"и {rub(month * 12 * 10)} за 10 лет.")


@ptool(CAT_F, "Рассрочка: платёж в месяц", "рассрочка 30000 на 6 месяцев")
def installment(text, low, s):
    if not re.search(r"рассрочк|долями|сплит|частями", low):
        return None
    mm = re.search(r"на\s+(\d+)\s*(месяц\w*|мес|недел\w*|платеж\w*|част\w*)", low)
    if not mm:
        return None
    n, unit = int(mm.group(1)), mm.group(2)
    if n < 1:
        return None
    xs = [x for x in nums(low) if x != n]
    if not xs:
        return None
    total = max(xs)
    first = _kw(low, r"первоначальн\w*\s+взнос", r"первый\s+взнос", "взнос") or 0
    pay = (total - first) / n
    per = "в неделю" if unit.startswith("недел") else "за платёж" if unit.startswith(("платеж", "част")) else "в месяц"
    return (f"Рассрочка {rub(total)}" + (f", первый взнос {rub(first)}" if first else "") +
            f": **{rub(pay)} {per}** × {n}. Без процентов переплаты нет — проверьте, нет ли платы за услугу.")


@ptool(CAT_F, "Налог самозанятого (НПД)", "налог самозанятого с 50000")
def npd(text, low, s):
    if not re.search(r"самозанят|\bнпд\b", low):
        return None
    xs = [x for x in nums(low) if x not in (4, 6)]
    if not xs:
        return None
    a = xs[0]
    return (f"Налог самозанятого с дохода {rub(a)}:\n\n- от физлиц (4%): **{rub(a * 0.04)}**, остаётся {rub(a * 0.96)}\n"
            f"- от компаний и ИП (6%): **{rub(a * 0.06)}**, остаётся {rub(a * 0.94)}\n\n"
            "Новым самозанятым даётся вычет 10 000 ₽: пока он не исчерпан, ставки 3% и 4%. Лимит дохода — 2,4 млн ₽ в год.")


@ptool(CAT_F, "Налог по УСН (6% или 15%)", "налог усн 6% с дохода 1000000")
def usn(text, low, s):
    if not re.search(r"\bусн\b|упрощенк", low):
        return None
    xs = [x for x in nums(low) if x not in (6, 15)]
    if not xs:
        return None
    income = max(xs)
    if re.search(r"15\s*%|доходы?\s+минус\s+расход", low):
        exp = _kw(low, "расход") or (sorted(xs)[-2] if len(xs) > 1 else 0)
        base = max(income - exp, 0)
        tax = max(base * 0.15, income * 0.01)
        return (f"УСН «доходы минус расходы» 15%: ({rub(income)} − {rub(exp)}) × 15% = **{rub(base * 0.15)}**\n\n"
                f"Минимальный налог 1% от доходов — {rub(income * 0.01)}; к уплате: **{rub(tax)}**.")
    return (f"УСН «доходы» 6%: {rub(income)} × 6% = **{rub(income * 0.06)}**\n\n"
            "ИП может уменьшить налог на уплаченные страховые взносы (без работников — до 100%).")


@ptool(CAT_F, "Сколько сэкономлю, если не тратить", "если не тратить 200 рублей в день сколько сэкономлю за год")
def habit_savings(text, low, s):
    if not re.search(r"сэконом|не\s+тратить|не\s+буду\s+тратить|отказаться\s+от|брошу", low):
        return None
    xs = [x for x in nums(low) if x > 0]
    if not xs:
        return None
    a = xs[0]
    per = 1 if re.search(r"в\s+день|ежедневно|каждый\s+день", low) else 7 if re.search(r"в\s+неделю", low) else 30.4 if re.search(r"в\s+месяц", low) else 1
    day = a / per
    return (f"Если не тратить {rub(a)} {'в день' if per == 1 else 'в неделю' if per == 7 else 'в месяц'}:\n\n"
            f"- за месяц: **{rub(day * 30.4)}**\n- за год: **{rub(day * 365)}**\n- за 5 лет: {rub(day * 365 * 5)}\n"
            f"- за 10 лет: {rub(day * 365 * 10)} (а на вкладе под 10% — около {rub(day * 30.4 * (((1 + 0.1 / 12) ** 120 - 1) / (0.1 / 12)))})")


# ================================================================ ЗДОРОВЬЕ И СПОРТ
CAT_H = "Здоровье и спорт"


@ptool(CAT_H, "Процент жира в теле (формула ВМС США)", "процент жира мужчина рост 180 талия 85 шея 38")
def body_fat(text, low, s):
    if not re.search(r"(?:процент|доля|уровень)\w*\s+жира|жир\w*\s+в\s+(?:теле|организме)", low):
        return None
    h, waist, neck, hip = _kw(low, "рост"), _kw(low, "тали"), _kw(low, r"ше[яиюей]"), _kw(low, r"бед(?:р|ер)")
    if not h or not waist or not neck:
        return None
    female = bool(re.search(r"женщ|девушк|\bжен\b|девочк", low))
    if female:
        if not hip:
            return "Для женщин формуле нужен ещё обхват бёдер: «процент жира женщина рост 165 талия 70 шея 32 бёдра 95»."
        bf = 495 / (1.29579 - 0.35004 * math.log10(waist + hip - neck) + 0.22100 * math.log10(h)) - 450
        scale = [(14, "необходимый минимум"), (21, "спортсменки"), (25, "хорошая форма"), (32, "норма"), (999, "выше нормы")]
    else:
        bf = 495 / (1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(h)) - 450
        scale = [(6, "необходимый минимум"), (14, "спортсмены"), (18, "хорошая форма"), (25, "норма"), (999, "выше нормы")]
    level = next(name for top, name in scale if bf < top)
    return (f"Процент жира (формула ВМС США): **{_r(bf, 1)}%** — {level}.\n\n"
            "Точность ±3–4%. Обхваты меряйте утром: талию — на уровне пупка, шею — под кадыком.")


@ptool(CAT_H, "Темп бега и прогноз на дистанции", "темп бега 10 км за 50 минут", early=True)
def run_pace(text, low, s):
    if not re.search(r"темп|пробежал|пробегу|забег|марафон|бег\w*\s+\d", low):
        return None
    if re.search(r"полумарафон", low):
        km = 21.0975
    elif re.search(r"марафон", low):
        km = 42.195
    else:
        dm = re.search(r"(" + NUM + r")\s*(км|м)(?![/\w])", low)
        if not dm:
            return None
        km = f(dm.group(1)) / (1000 if dm.group(2) == "м" else 1)
    tm = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", low)
    if tm:
        minutes = int(tm.group(1)) * 60 + int(tm.group(2)) + int(tm.group(3)) / 60
    else:
        hm = re.search(r"(\d+)\s*(?:час|ч)\w*", low)
        mm = re.search(r"(\d+)\s*(?:мин)\w*", low)
        sm = re.search(r"(\d+)\s*(?:сек)\w*", low)
        minutes = (int(hm.group(1)) * 60 if hm else 0) + (int(mm.group(1)) if mm else 0) + (int(sm.group(1)) / 60 if sm else 0)
    if not km or minutes <= 0:
        return None
    pace = minutes / km
    pm, ps = divmod(int(round(pace * 60)), 60)

    def predict(d):
        t = minutes * (d / km) ** 1.06
        h, rest = divmod(int(round(t * 60)), 3600)
        return f"{h}:{rest // 60:02d}:{rest % 60:02d}" if h else f"{rest // 60}:{rest % 60:02d}"
    return (f"Дистанция {num(km)} км за {_dur(minutes / 60)}:\n\n- темп: **{pm}:{ps:02d} мин/км**\n"
            f"- скорость: **{_r(km / (minutes / 60), 2)} км/ч**\n\nПрогноз (формула Ригеля): 5 км — {predict(5)}, "
            f"10 км — {predict(10)}, полумарафон — {predict(21.0975)}, марафон — {predict(42.195)}.")


_MET = [(r"скакалк", "прыжки на скакалке", 12.3), (r"быстр\w*\s+(?:ходьб|шаг)|скандинавск", "быстрая ходьба", 5.0),
        (r"(?<![а-я])бег|бегать|пробежк", "бег (~10 км/ч)", 9.8), (r"ходьб|прогулк|гулять|пешком|шаг", "ходьба", 3.5),
        (r"велосипед|велик|велотренаж", "велосипед", 7.5), (r"плаван|плавать|бассейн", "плавание", 8.0),
        (r"йог", "йога", 2.5), (r"танц", "танцы", 5.5), (r"футбол", "футбол", 7.0), (r"баскетбол", "баскетбол", 6.5),
        (r"волейбол", "волейбол", 4.0), (r"теннис", "теннис", 7.3), (r"лыж", "лыжи", 7.0), (r"коньк|конек", "коньки", 7.0),
        (r"силов|штанг|тренажер|качалк|гантел|приседан|отжиман", "силовая тренировка", 6.0),
        (r"бокс|единоборств", "бокс", 9.0), (r"уборк|пылесос", "уборка", 3.3), (r"лестниц|ступен", "подъём по лестнице", 8.0),
        (r"растяжк|стретчинг", "растяжка", 2.3), (r"гребл|байдарк", "гребля", 7.0), (r"сон|спать", "сон", 0.95)]


@ptool(CAT_H, "Сколько калорий сжигает активность", "сколько калорий сжигает бег 30 минут при весе 70", early=True)
def activity_kcal(text, low, s):
    if not re.search(r"сжига|сжечь|сжег|сжиг|тратит|потрат|расходу", low) or not re.search(r"калори|ккал", low):
        return None
    act = next(((name, met) for rx, name, met in _MET if re.search(rx, low)), None)
    if not act:
        return None
    hm = re.search(r"(" + NUM + r")\s*(?:час|ч)(?![а-я])", low)
    mm = re.search(r"(" + NUM + r")\s*мин", low)
    hours = (f(hm.group(1)) if hm else 0) + (f(mm.group(1)) / 60 if mm else 0) or 1
    wm = re.search(r"(?:вес\w*|вешу)\s*(" + NUM + r")|(" + NUM + r")\s*кг", low)
    w = f(wm.group(1) or wm.group(2)) if wm else 70
    kcal = act[1] * w * hours
    return (f"{act[0].capitalize()}, {_dur(hours)}, вес {num(w)} кг: **≈ {num(round(kcal))} ккал** "
            f"(MET {num(act[1])} × вес × часы).\n\nЭто примерно {_r(kcal / 96, 1)} бананов или {_r(kcal / 550 * 100, 0)} г шоколада.")


@ptool(CAT_H, "Шаги в километры и обратно", "10000 шагов это сколько км", early=True)
def steps(text, low, s):
    h = _kw(low, "рост")
    stride = h * 0.415 / 100 if h and h > 100 else 0.75
    m = re.search(r"(\d[\d\s]*)\s*шаг", low)
    if m and re.search(r"км|километр|метр|сколько|расстояни", low):
        n = int(m.group(1).replace(" ", ""))
        km = n * stride / 1000
        return (f"{num(n)} шагов ≈ **{_r(km, 2)} км** (шаг {_r(stride * 100, 0)} см)\n\n"
                f"Это ≈ {_dur(n / 100 / 60)} ходьбы и {num(round(n * 0.04))} ккал.")
    m = re.search(r"сколько\s+шагов\s+(?:в|за)\s+(" + NUM + r")\s*(км|километр\w*|м|метр\w*)", low)
    if m:
        dist = f(m.group(1)) * (1000 if m.group(2).startswith("к") else 1)
        return f"{num(dist / 1000)} км ≈ **{num(round(dist / stride))} шагов** (шаг {_r(stride * 100, 0)} см)"
    return None


@ptool(CAT_H, "Норма белка в день", "сколько белка в день при весе 70")
def protein(text, low, s):
    if not re.search(r"белк|протеин", low) or not re.search(r"норм|в\s+день|сколько\s+(?:нужно|надо)|суточн|при\s+весе", low):
        return None
    wm = re.search(r"(?:вес\w*|вешу)\s*(" + NUM + r")|(" + NUM + r")\s*кг", low)
    if not wm:
        return None
    w = f(wm.group(1) or wm.group(2))
    return (f"Белок в день при весе {num(w)} кг:\n\n- обычная жизнь: **{num(round(w * 0.8))}–{num(round(w * 1.0))} г** (0,8–1 г/кг)\n"
            f"- активный спорт: {num(round(w * 1.2))}–{num(round(w * 1.6))} г\n- набор мышц: {num(round(w * 1.6))}–{num(round(w * 2.2))} г\n\n"
            "Ориентир: 100 г куриной грудки ≈ 24 г белка, яйцо ≈ 7 г, 100 г творога 5% ≈ 17 г.")


@ptool(CAT_H, "Предполагаемая дата родов (ПДР)", "срок родов если последние месячные 1 марта 2026")
def due_date(text, low, s):
    if not re.search(r"(?:дат\w*|срок\w*)\s+родов|\bпдр\b|когда\s+рожать", low):
        return None
    ds = _dates(low)
    if not ds:
        return None
    lmp = ds[0]
    edd = lmp + timedelta(days=280)
    days = (_today() - lmp).days
    now = ""
    if 0 <= days <= 300:
        wk, dd = divmod(days, 7)
        tri = 1 if wk < 13 else 2 if wk < 28 else 3
        now = f"\n\nСейчас срок: **{wk} нед. {dd} дн.** ({tri}-й триместр)."
    return (f"Первый день последних месячных: {_say(lmp)}\n\nПредполагаемая дата родов (правило Негеле, +280 дней): **{_say(edd)}**{now}\n\n"
            "Это ориентир: точный срок определяет врач по УЗИ. Рожают в срок с 38 по 42 неделю.")


@ptool(CAT_H, "Соотношение талии и бёдер", "соотношение талии и бёдер 80 и 100")
def whr(text, low, s):
    if not re.search(r"(?:соотношени|отношени|индекс)\w*\s+тали\w*\s+(?:и|к)\s+бед(?:р|ер)", low):
        return None
    xs = nums(low)
    if len(xs) < 2 or xs[1] <= 0:
        return None
    r = xs[0] / xs[1]
    female = bool(re.search(r"женщ|девушк|\bжен\b", low))
    limit = 0.85 if female else 0.90
    verdict = "в норме" if r <= limit else "выше нормы ВОЗ — повод следить за питанием и движением"
    return (f"Талия / бёдра = {num(xs[0])} / {num(xs[1])} = **{_r(r, 2)}** — {verdict}.\n\n"
            "Норма ВОЗ: для женщин до 0,85, для мужчин до 0,90.")


_SLEEP = [(0.25, "новорождённым (0–3 мес.)", "14–17 ч"), (1, "младенцам (4–11 мес.)", "12–15 ч"), (3, "детям 1–2 лет", "11–14 ч"),
          (6, "детям 3–5 лет", "10–13 ч"), (14, "детям 6–13 лет", "9–11 ч"), (18, "подросткам 14–17 лет", "8–10 ч"),
          (26, "взрослым 18–25 лет", "7–9 ч"), (65, "взрослым 26–64 лет", "7–9 ч"), (200, "людям старше 65", "7–8 ч")]


@ptool(CAT_H, "Сколько нужно спать по возрасту", "сколько нужно спать в 15 лет")
def sleep_need(text, low, s):
    if not re.search(r"сколько\s+(?:часов\s+)?(?:нужно\s+|надо\s+|должен\s+|должна\s+|положено\s+)?спать|норм\w*\s+сна", low):
        return None
    m = re.search(r"(\d+)\s*(лет|год\w*|месяц\w*|мес)", low)
    if m:
        age = int(m.group(1)) / (12 if m.group(2).startswith("мес") else 1)
    elif re.search(r"взросл", low):
        age = 30
    elif re.search(r"подрост|школьник", low):
        age = 15
    elif re.search(r"пожил|пенсионер", low):
        age = 70
    else:
        return None
    who, hours = next((w, h) for top, w, h in _SLEEP if age < top)
    return f"По рекомендациям Национального фонда сна (США) {who} нужно спать **{hours}** в сутки."


# ================================================================ ПИТОМЦЫ
CAT_P = "Питомцы"


@ptool(CAT_P, "Возраст собаки по-человечески", "собаке 5 лет сколько по-человечески")
def dog_age(text, low, s):
    if not re.search(r"собак|(?<![а-я])пес|пса|щен", low) or not re.search(r"человеч|по-нашему|в\s+человеческих", low):
        return None
    m = re.search(r"(" + NUM + r")\s*(лет|год\w*|месяц\w*|мес)", low)
    if not m:
        return None
    age = f(m.group(1)) / (12 if m.group(2).startswith("мес") else 1)
    if age <= 0 or age > 30:
        return None
    human = 16 * math.log(age) + 31 if age >= 1 else age * 31
    return (f"Собаке {num(age)} {_plural(age, 'год', 'года', 'лет')} — это примерно **{num(round(human))} {_plural(round(human), 'человеческий год', 'человеческих года', 'человеческих лет')}** "
            f"(формула учёных UCSD: 16·ln(возраст) + 31).\n\nСтарое правило «×7» дало бы {num(round(age * 7))}. "
            "Крупные породы стареют быстрее мелких.")


@ptool(CAT_P, "Возраст кошки по-человечески", "кошке 3 года сколько по-человечески")
def cat_age(text, low, s):
    if not re.search(r"кошк|(?<![а-я])кот|котенк|котик", low) or not re.search(r"человеч|по-нашему|в\s+человеческих", low):
        return None
    m = re.search(r"(" + NUM + r")\s*(лет|год\w*|месяц\w*|мес)", low)
    if not m:
        return None
    age = f(m.group(1)) / (12 if m.group(2).startswith("мес") else 1)
    if age <= 0 or age > 35:
        return None
    human = age * 15 if age <= 1 else 15 + (age - 1) * 9 if age <= 2 else 24 + (age - 2) * 4
    return (f"Кошке {num(age)} {_plural(age, 'год', 'года', 'лет')} — это примерно **{num(round(human))} {_plural(round(human), 'человеческий год', 'человеческих года', 'человеческих лет')}**.\n\n"
            "Шкала ветеринаров: 1 год = 15 лет, 2 года = 24, дальше +4 за каждый год.")


# ================================================================ ДАТЫ И ВРЕМЯ+
CAT_T = "Даты и время+"


@ptool(CAT_T, "Сколько дней между датами", "сколько дней между 1 марта 2026 и 1 июня 2026")
def days_between(text, low, s):
    if not re.search(r"(?:сколько|число)\s+(?:дней|недель|суток)\s+(?:между|с|от)|между\s+датами|разниц\w*\s+(?:между\s+)?дат", low):
        return None
    ds = _dates(low)
    if len(ds) < 2:
        return None
    a, b = ds[0], ds[1]
    days = abs((b - a).days)
    wk, rest = divmod(days, 7)
    incl = " Включая обе даты — на 1 больше." if "включ" not in low else ""
    return (f"Между {_say(a)} и {_say(b)}: **{num(days)} {_plural(days, 'день', 'дня', 'дней')}** "
            f"({wk} нед. {rest} дн., ≈ {_r(days / 30.44, 1)} мес.).{incl}")


def _easter_catholic(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    n = h + l - 7 * m + 114
    return date(y, n // 31, n % 31 + 1)


def _easter_orthodox(y):
    a, b, c = y % 4, y % 7, y % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    n = d + e + 114
    return date(y, n // 31, n % 31 + 1) + timedelta(days=y // 100 - y // 400 - 2)


@ptool(CAT_T, "Дата Пасхи, Масленицы и Троицы", "когда пасха в 2027")
def easter(text, low, s):
    if not re.search(r"пасх|масленниц|масленица|троиц|вербн\w*\s+воскресен", low):
        return None
    ys = [y for y in ints(low) if 1583 <= y <= 4099]
    y = ys[0] if ys else _today().year
    o, c = _easter_orthodox(y), _easter_catholic(y)
    wd = _WEEKDAYS
    return (f"**{y} год:**\n\n- Православная Пасха: **{_say(o)}**\n- Католическая Пасха: **{_say(c)}**" +
            (" (в этом году совпадают)" if o == c else "") +
            f"\n- Масленица: {_say(o - timedelta(days=55))} — {_say(o - timedelta(days=49))} "
            f"(Прощёное воскресенье)\n- Вербное воскресенье: {_say(o - timedelta(days=7))}\n"
            f"- Троица: {_say(o + timedelta(days=49))}\n\nПасха всегда в {wd[6]}.")


_SYN = 29.530588853
_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_PHASES = [(1.84566, "🌑 новолуние"), (5.53699, "🌒 растущий серп"), (9.22831, "🌓 первая четверть"),
           (12.91963, "🌔 растущая Луна"), (16.61096, "🌕 полнолуние"), (20.30228, "🌖 убывающая Луна"),
           (23.99361, "🌗 последняя четверть"), (27.68493, "🌘 убывающий серп"), (99, "🌑 новолуние")]


@ptool(CAT_T, "Фаза Луны на дату", "фаза луны сегодня")
def moon(text, low, s):
    if not re.search(r"фаз\w*\s+лун|лунн\w*\s+(?:день|фаз|календар|сутк)|полнолуни|новолуни|какая\s+(?:сегодня\s+|завтра\s+)?луна|растущ\w*\s+лун|убывающ\w*\s+лун", low):
        return None
    ds = _dates(low)
    d = ds[0] if ds else _today()
    dt = datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc)
    age = ((dt - _NEW_MOON).total_seconds() / 86400) % _SYN
    name = next(n for top, n in _PHASES if age < top)
    light = (1 - math.cos(2 * math.pi * age / _SYN)) / 2 * 100
    to_full = (14.765 - age) % _SYN
    to_new = (_SYN - age) % _SYN
    return (f"{_say(d)}: **{name}**, освещено ≈ {_r(light, 0)}%, лунный возраст {_r(age, 1)} сут.\n\n"
            f"- ближайшее полнолуние: {_say(d + timedelta(days=round(to_full)))}\n"
            f"- ближайшее новолуние: {_say(d + timedelta(days=round(to_new)))}\n\nТочность расчёта — около суток.")


@ptool(CAT_T, "Сколько прошло года (в процентах)", "сколько процентов года прошло")
def year_progress(text, low, s):
    if not re.search(r"(?:процент\w*|часть|доля|сколько)\s+(?:от\s+)?года\s+(?:уже\s+)?(?:прошл|позади|осталось)|прогресс\s+года|сколько\s+(?:прошло|осталось)\s+(?:от\s+)?года", low):
        return None
    d = _today()
    total = 366 if calendar.isleap(d.year) else 365
    passed = d.timetuple().tm_yday
    pct = passed / total * 100
    bar = "▓" * int(pct // 5) + "░" * (20 - int(pct // 5))
    return (f"{d.year} год: прошло **{_r(pct, 1)}%** ({passed} из {total} дней)\n\n{bar}\n\n"
            f"До Нового года: {total - passed} {_plural(total - passed, 'день', 'дня', 'дней')}.")


@ptool(CAT_T, "Unix-время (timestamp)", "unix timestamp 1700000000")
def unix_time(text, low, s):
    if not re.search(r"\bunix|timestamp|юникс|\bepoch|эпох\w*\s+unix|таймстамп", low):
        return None
    m = re.search(r"(?<!\d)(\d{9,13})(?!\d)", low)
    if m:
        ts = int(m.group(1))
        ms = len(m.group(1)) == 13
        if ms:
            ts /= 1000
        u = datetime.fromtimestamp(ts, tz=timezone.utc)
        msk = u + timedelta(hours=3)
        return (f"{m.group(1)}{' (миллисекунды)' if ms else ''} =\n\n- **{u:%d.%m.%Y %H:%M:%S} UTC**\n"
                f"- {msk:%d.%m.%Y %H:%M:%S} по Москве\n- {_WEEKDAYS[u.weekday()]}")
    ds = _dates(low)
    if ds:
        d = ds[0]
        ts = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
        return f"{_say(d)} 00:00 UTC = **{ts}** (в миллисекундах: {ts * 1000})"
    now = datetime.now(timezone.utc)
    return f"Сейчас unix-время: **{int(now.timestamp())}** ({now:%d.%m.%Y %H:%M:%S} UTC)"


_RU_HOLIDAYS = {(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4)}


@ptool(CAT_T, "Рабочие дни в месяце", "сколько рабочих дней в ноябре 2026")
def workdays(text, low, s):
    if not re.search(r"рабоч\w*\s+(?:дн|дней)|рабочих\s+дней", low):
        return None
    mm = re.search(_MONTH_RE, low)
    if not mm:
        return None
    month = _month_num(mm.group(1))
    ys = [y for y in ints(low) if 1900 <= y <= 2200]
    year = ys[0] if ys else _today().year
    days = calendar.monthrange(year, month)[1]
    week = sum(1 for d in range(1, days + 1) if date(year, month, d).weekday() < 5)
    hol = [d for d in range(1, days + 1) if (month, d) in _RU_HOLIDAYS and date(year, month, d).weekday() < 5]
    work = week - len(hol)
    note = f" (минус праздники: {', '.join(str(d) for d in hol)})" if hol else ""
    return (f"{_MONTH_NOM[month].capitalize()} {year}: **{work} {_plural(work, 'рабочий день', 'рабочих дня', 'рабочих дней')}**{note}, "
            f"{days - work} выходных и праздничных, {work * 8} {_plural(work * 8, 'рабочий час', 'рабочих часа', 'рабочих часов')} при 40-часовой неделе.\n\n"
            "Переносы выходных по постановлению правительства могут менять число на ±1–2 дня.")


@ptool(CAT_T, "Номер дня в году", "какой по счёту день года 15 марта")
def day_of_year(text, low, s):
    if not re.search(r"(?:какой|номер)\s+(?:по\s+счету\s+)?день\s+(?:в\s+)?году|по\s+счету\s+день|день\s+года", low):
        return None
    ds = _dates(low)
    d = ds[0] if ds else _today()
    n = d.timetuple().tm_yday
    total = 366 if calendar.isleap(d.year) else 365
    return f"{_say(d)} — **{n}-й день года**, до конца года ещё {total - n} {_plural(total - n, 'день', 'дня', 'дней')}."


def _times(low):
    return [(int(h), int(m), int(sec or 0)) for h, m, sec in re.findall(r"(\d{1,3}):(\d{2})(?::(\d{2}))?", low)]


def _hm(total_sec):
    sign = "−" if total_sec < 0 else ""
    total_sec = abs(int(total_sec))
    h, rest = divmod(total_sec, 3600)
    m, sec = divmod(rest, 60)
    return f"{sign}{h}:{m:02d}" + (f":{sec:02d}" if sec else "")


@ptool(CAT_T, "Сложить или вычесть время (чч:мм)", "сложи время 1:45 и 2:30")
def add_times(text, low, s):
    if not re.search(r"слож\w*\s+(?:время|часы|минуты)|сумм\w*\s+(?:времен|часов)|вычти\s+(?:время|из)|\d:\d{2}\s*[+-]\s*\d{1,3}:\d{2}", low):
        return None
    ts = _times(low)
    if len(ts) < 2:
        return None
    secs = [h * 3600 + m * 60 + sec for h, m, sec in ts]
    minus = bool(re.search(r"вычт|минус|\d:\d{2}\s*-\s*\d", low))
    total = secs[0] - sum(secs[1:]) if minus else sum(secs)
    return f"{(' − ' if minus else ' + ').join(_hm(x) for x in secs)} = **{_hm(total)}** ({_r(total / 3600, 2)} ч)"


@ptool(CAT_T, "Интервал между двумя временами", "интервал между 9:15 и 17:40")
def time_interval(text, low, s):
    if not re.search(r"(?:интервал|промежуток|разниц\w*|сколько\s+(?:часов|минут)|длительност\w*)\s+(?:времени\s+)?(?:между|с|от)\s+\d{1,2}[:.]\d{2}", low):
        return None
    ts = re.findall(r"(\d{1,2})[:.](\d{2})", low)
    if len(ts) < 2:
        return None
    a = int(ts[0][0]) * 60 + int(ts[0][1])
    b = int(ts[1][0]) * 60 + int(ts[1][1])
    night = b < a
    diff = (b - a) % (24 * 60)
    return (f"С {ts[0][0]}:{ts[0][1]} до {ts[1][0]}:{ts[1][1]}" + (" (через полночь)" if night else "") +
            f": **{diff // 60} ч {diff % 60} мин** ({num(diff)} мин)")


_GENERATIONS = [(1927, "Величайшее поколение"), (1945, "Молчаливое поколение"), (1964, "Бэби-бумеры"),
                (1980, "Поколение X"), (1996, "Миллениалы (поколение Y)"), (2012, "Поколение Z (зумеры)"),
                (2024, "Поколение Альфа"), (9999, "Поколение Бета")]


@ptool(CAT_T, "Поколение по году рождения", "какое поколение 1998 год")
def generation(text, low, s):
    if not re.search(r"поколени", low):
        return None
    ys = [y for y in ints(low) if 1900 <= y <= 2100]
    if not ys:
        return None
    y = ys[0]
    name = next(n for top, n in _GENERATIONS if y <= top)
    return f"{y} год рождения — **{name}**.\n\nГраницы условные (по классификации Pew Research Center)."


# ================================================================ ТЕКСТ+
CAT_X = "Текст+"


def _words(t):
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9]+(?:[-'][A-Za-zА-Яа-яЁё0-9]+)*", t)


@ptool(CAT_X, "Самое длинное слово в тексте", "самое длинное слово в: Привет, это проверка необыкновеннейшего текста")
def longest_word(text, low, s):
    if not re.search(r"сам(?:ое|ые|ый|ая)\s+длинн\w*\s+слов", low):
        return None
    ws = _words(_payload(text))
    if not ws:
        return None
    top = max(len(w) for w in ws)
    best = sorted({w for w in ws if len(w) == top})
    return f"Самое длинное слово: **{', '.join(best)}** ({top} {_plural(top, 'буква', 'буквы', 'букв')})"


_STOP = set("и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем всех никогда можно при наконец два об другой хоть после над больше тот через эти нас про всего них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть том нельзя такой им более всегда конечно всю между the a an of to and in is it".split())


@ptool(CAT_X, "Частота слов в тексте", "частота слов: мама мыла раму мама мыла окно")
def word_freq(text, low, s):
    if not re.search(r"частот\w*\s+слов|частотност|какие\s+слова\s+(?:чаще|встречаются)|повторяющ\w*\s+слов", low):
        return None
    ws = [w.lower().replace("ё", "е") for w in _words(_payload(text))]
    if len(ws) < 2:
        return None
    keep = [w for w in ws if w not in _STOP and len(w) > 1] or ws
    counts = {}
    for w in keep:
        counts[w] = counts.get(w, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    return (f"Слов всего: {len(ws)}, разных: {len(set(ws))}\n\n| Слово | Раз |\n|---|---|\n" +
            "\n".join(f"| {w} | {c} |" for w, c in top) + "\n\nСлужебные слова (и, в, на…) не считаются.")


@ptool(CAT_X, "Убрать лишние пробелы", "убери лишние пробелы: привет    мир  !")
def squeeze(text, low, s):
    if not re.search(r"(?:убери|удали|почисти)\w*\s+(?:лишние|двойные|все\s+лишние)\s+пробел", low):
        return None
    p = _payload(text)
    if not p:
        return None
    out = re.sub(r"\s+([,.!?;:])", r"\1", re.sub(r"[ \t]+", " ", p)).strip()
    return f"```\n{out}\n```"


@ptool(CAT_X, "ВЕРХНИЙ регистр", "в верхний регистр: привет мир")
def upper(text, low, s):
    if not re.search(r"верхн\w*\s+регистр|заглавными\s+буквами|большими\s+буквами|капсом|капслоком", low):
        return None
    p = _payload(text)
    return f"```\n{p.upper()}\n```" if p else None


@ptool(CAT_X, "нижний регистр", "в нижний регистр: ПРИВЕТ МИР")
def lower(text, low, s):
    if not re.search(r"нижн\w*\s+регистр|строчными\s+буквами|маленькими\s+буквами", low):
        return None
    p = _payload(text)
    return f"```\n{p.lower()}\n```" if p else None


_TR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
       "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
       "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}


def _latin(word):
    return "".join(_TR.get(c, c) for c in word.lower())


def _code_words(p):
    p = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", p)
    return [_latin(w) for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", p)]


@ptool(CAT_X, "snake_case и CONSTANT_CASE", "в snake_case: Hello World Text")
def snake(text, low, s):
    if not re.search(r"snake[_ ]?case|змеин\w*\s+регистр|constant[_ ]?case|screaming", low):
        return None
    ws = _code_words(_payload(text))
    if not ws:
        return None
    out = "_".join(ws)
    return f"snake_case: `{out}`\n\nCONSTANT_CASE: `{out.upper()}`"


@ptool(CAT_X, "camelCase и PascalCase", "в camelCase: hello world text")
def camel(text, low, s):
    if not re.search(r"camel[_ ]?case|верблюж\w*|pascal[_ ]?case", low):
        return None
    ws = _code_words(_payload(text))
    if not ws:
        return None
    pascal = "".join(w.capitalize() for w in ws)
    return f"camelCase: `{pascal[0].lower() + pascal[1:]}`\n\nPascalCase: `{pascal}`"


def _items(p):
    sep = "\n" if "\n" in p else ";" if ";" in p else "," if "," in p else " "
    return [x.strip() for x in p.split(sep) if x.strip()]


@ptool(CAT_X, "Отсортировать список", "отсортируй по алфавиту: груша, яблоко, банан")
def sort_list(text, low, s):
    if not re.search(r"(?:отсортируй|сортируй|упорядоч\w*|расставь)\s+(?:\w+\s+)?(?:по\s+алфавиту|по\s+возрастанию|по\s+убыванию|в\s+алфавитном)", low):
        return None
    items = _items(_payload(text))
    if len(items) < 2:
        return None
    rev = bool(re.search(r"убыван|обратн", low))
    try:
        res = sorted(items, key=lambda x: f(x), reverse=rev)
    except ValueError:
        res = sorted(items, key=lambda x: x.lower().replace("ё", "е"), reverse=rev)
    return "\n".join(f"{i + 1}. {x}" for i, x in enumerate(res))


@ptool(CAT_X, "Убрать повторы из списка", "убери повторы: яблоко, груша, яблоко, слива")
def dedup(text, low, s):
    if not re.search(r"(?:убери|удали)\w*\s+(?:все\s+)?(?:повтор|дубл|одинаков)", low):
        return None
    items = _items(_payload(text))
    if len(items) < 2:
        return None
    seen, out = set(), []
    for x in items:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return f"Без повторов ({len(out)} из {len(items)}): " + ", ".join(out)


@ptool(CAT_X, "Статистика текста и время чтения", "статистика текста: Это первый абзац. Это второе предложение!")
def text_stats(text, low, s):
    if not re.search(r"(?:статистик|анализ)\w*\s+текста|сколько\s+(?:времени\s+)?(?:читать|займет\s+чтение)|время\s+чтения|за\s+сколько\s+прочита", low):
        return None
    p = _payload(text)
    if not p:
        return None
    ws = _words(p)
    sent = len([x for x in re.split(r"[.!?…]+", p) if x.strip()])
    paras = len([x for x in re.split(r"\n\s*\n", p) if x.strip()])
    return (f"| Показатель | Значение |\n|---|---|\n| Символов с пробелами | {len(p)} |\n"
            f"| Символов без пробелов | {len(re.sub(r'[ ]', '', p))} |\n| Слов | {len(ws)} |\n| Предложений | {sent} |\n"
            f"| Абзацев | {paras} |\n| Средняя длина слова | {_r(sum(map(len, ws)) / max(len(ws), 1), 1)} |\n"
            f"| Время чтения (~180 слов/мин) | {_secs(len(ws) / 180 * 60)} |\n| Время произнесения (~130 слов/мин) | {_secs(len(ws) / 130 * 60)} |")


_SHORT = {"и", "в", "во", "на", "по", "с", "со", "для", "от", "до", "из", "о", "об", "к", "ко", "у", "за", "при", "of", "and", "the", "for"}


@ptool(CAT_X, "Аббревиатура из слов", "аббревиатура: Организация Объединённых Наций")
def acronym(text, low, s):
    if not re.search(r"аббревиатур|акроним|сократи\s+(?:до|в)\s+(?:первых\s+)?букв", low):
        return None
    ws = [w for w in _words(_payload(text)) if w.lower() not in _SHORT]
    if len(ws) < 2:
        return None
    return f"Аббревиатура: **{''.join(w[0].upper() for w in ws)}**"


_REV = [("shch", "щ"), ("sch", "щ"), ("yo", "ё"), ("zh", "ж"), ("kh", "х"), ("ts", "ц"), ("ch", "ч"), ("sh", "ш"),
        ("yu", "ю"), ("ya", "я"), ("ye", "е"), ("ju", "ю"), ("ja", "я"), ("a", "а"), ("b", "б"), ("v", "в"), ("w", "в"),
        ("g", "г"), ("d", "д"), ("e", "е"), ("z", "з"), ("i", "и"), ("j", "й"), ("k", "к"), ("l", "л"), ("m", "м"),
        ("n", "н"), ("o", "о"), ("p", "п"), ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"), ("f", "ф"), ("h", "х"),
        ("c", "к"), ("q", "к"), ("x", "кс"), ("'", "ь")]
_VOWELS_LAT = set("aeiouy")


def _to_cyr(word):
    w, out, i = word, [], 0
    while i < len(w):
        low_rest = w[i:].lower()
        if low_rest[0] == "y":
            prev = w[i - 1].lower() if i else ""
            nxt = low_rest[1:2]
            if nxt in ("o", "u", "a", "e"):
                pass
            elif not prev or prev in _VOWELS_LAT:
                out.append("й" if w[i].islower() else "Й")
                i += 1
                continue
            else:
                out.append("ы" if w[i].islower() else "Ы")
                i += 1
                continue
        for lat, cyr in _REV:
            if low_rest.startswith(lat):
                out.append(cyr.upper() if w[i].isupper() and cyr else cyr)
                i += len(lat)
                break
        else:
            out.append(w[i])
            i += 1
    return "".join(out)


@ptool(CAT_X, "Латиница в кириллицу (обратный транслит)", "латиница в кириллицу: privet kak dela", before="Транслитерация (как в загранпаспорте)")
def to_cyrillic(text, low, s):
    if not re.search(r"в\s+кириллиц|кириллицей|(?:из|с|обратн\w*)\s+транслит|латиниц\w*\s+в\s+русск|транслит\w*\s+(?:в|на)\s+русск", low):
        return None
    p = _payload(text)
    if not p or not re.search(r"[A-Za-z]", p):
        return None
    return "```\n" + re.sub(r"[A-Za-z']+", lambda m: _to_cyr(m.group(0)), p) + "\n```"


_COMMON_PW = {"123456", "password", "123456789", "12345678", "qwerty", "111111", "12345", "123123", "qwerty123", "1q2w3e",
              "1234567", "000000", "iloveyou", "1234", "abc123", "password1", "admin", "qwertyuiop", "654321", "555555",
              "666666", "7777777", "123321", "zaq12wsx", "йцукен", "пароль", "1qaz2wsx", "dragon", "monkey", "football",
              "letmein", "1q2w3e4r", "qwe123", "admin123", "12345678910", "привет"}


@ptool(CAT_X, "Проверить надёжность пароля", "проверь пароль Qwerty123")
def password_strength(text, low, s):
    if not re.search(r"(?:провер|оцен)\w*\s+(?:надежност\w*\s+|сложност\w*\s+)?парол|надежн\w*\s+ли\s+(?:мой\s+)?парол|(?:надежен|надежный|сложный)\s+ли\s+парол|сложност\w*\s+парол", low):
        return None
    p = _payload(text)
    if not p:
        m = re.search(r"парол\w*\s+(\S+)", text, re.I)
        p = m.group(1) if m else ""
    p = p.strip("«»\"'")
    if not p:
        return None
    pool = 0
    pool += 26 if re.search(r"[a-z]", p) else 0
    pool += 26 if re.search(r"[A-Z]", p) else 0
    pool += 10 if re.search(r"\d", p) else 0
    pool += 33 if re.search(r"[а-яё]", p) else 0
    pool += 33 if re.search(r"[А-ЯЁ]", p) else 0
    pool += 33 if re.search(r"[^A-Za-zА-Яа-яЁё0-9]", p) else 0
    bits = len(p) * math.log2(max(pool, 2))
    if p.lower() in _COMMON_PW or len(set(p)) <= 2:
        bits = min(bits, 10)
    if re.fullmatch(r"(.)\1+|\d+|[a-zа-я]+", p.lower()):
        bits *= 0.7
    levels = [(28, "🔴 очень слабый"), (36, "🟠 слабый"), (60, "🟡 средний"), (80, "🟢 сильный"), (9999, "🟢 очень сильный")]
    level = next(name for top, name in levels if bits < top)
    crack = 2 ** bits / 2 / 1e10
    tips = []
    if len(p) < 12:
        tips.append("сделайте длиннее — от 12 символов")
    if not re.search(r"[A-ZА-ЯЁ]", p):
        tips.append("добавьте заглавные буквы")
    if not re.search(r"\d", p):
        tips.append("добавьте цифры")
    if not re.search(r"[^A-Za-zА-Яа-яЁё0-9]", p):
        tips.append("добавьте символы (!, #, _)")
    masked = p[0] + "•" * (len(p) - 2) + p[-1] if len(p) > 2 else "•" * len(p)
    return (f"Пароль {masked} ({len(p)} символов): **{level}**, энтропия ≈ {_r(bits, 0)} бит.\n\n"
            f"Подбор на мощном компьютере (10 млрд вариантов/с): {_secs(crack)}.\n\n" +
            ("Как улучшить: " + ", ".join(tips) + "." if tips else "Хороший пароль. Не используйте его на нескольких сайтах.") +
            "\n\nПроверка идёт прямо на вашем устройстве — пароль никуда не отправляется.")


_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-zА-Яа-я0-9.\-]+\.(?:[A-Za-z]{2,}|рф)")
_EMAIL_TYPO = {"gmial.com": "gmail.com", "gmai.com": "gmail.com", "gamil.com": "gmail.com", "gmail.ru": "gmail.com",
               "mail.ry": "mail.ru", "maill.ru": "mail.ru", "yandex.ry": "yandex.ru", "yadex.ru": "yandex.ru",
               "hotmial.com": "hotmail.com", "outlok.com": "outlook.com", "yaho.com": "yahoo.com", "bk.ry": "bk.ru"}


@ptool(CAT_X, "Проверить e-mail", "проверь email ivan.petrov@mail.ru")
def email_check(text, low, s):
    if not re.search(r"(?:провер|валид)\w*\s+(?:e-?mail|имейл|емейл|почт\w*|адрес\w*\s+(?:почты|e-?mail))", low):
        return None
    m = re.search(r"\S+@\S+", text)
    if not m:
        return None
    addr = m.group(0).strip(".,;:!?»\"'")
    if not _EMAIL.fullmatch(addr) or ".." in addr or addr.startswith("."):
        return f"**{addr}** — некорректный адрес: проверьте «@», точку перед доменом и отсутствие пробелов."
    dom = addr.split("@")[1].lower()
    if dom in _EMAIL_TYPO:
        return f"Формат верный, но похоже на опечатку: **{dom}** → может быть **{_EMAIL_TYPO[dom]}**?"
    return f"✅ **{addr}** — формат адреса правильный. (Существует ли ящик — так не проверить, только письмом.)"


@ptool(CAT_X, "Извлечь e-mail, ссылки, телефоны, числа из текста", "извлеки email из: пишите на a@b.ru или support@rai.app")
def extract(text, low, s):
    m = re.search(r"(?:извлеки|вытащи|выпиши|достань|собери)\w*\s+(?:все\s+)?(e-?mail\w*|имейл\w*|почт\w*|ссылк\w*|url\w*|телефон\w*|номер\w*|числа|цифры|хэштег\w*|хештег\w*|тег\w*|упоминани\w*)", low)
    p = _payload(text)
    if not m or not p:
        return None
    kind = m.group(1)
    if kind.startswith(("e", "имейл", "почт")):
        found, name = _EMAIL.findall(p), "Адреса e-mail"
    elif kind.startswith(("ссылк", "url")):
        found, name = re.findall(r"https?://[^\s)>\]]+|www\.[^\s)>\]]+", p), "Ссылки"
    elif kind.startswith(("телефон", "номер")):
        found, name = [x.strip() for x in re.findall(r"(?:\+7|8|\+\d{1,3})[\s(\-]*\d{3}[\s)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", p)], "Телефоны"
    elif kind.startswith(("хэштег", "хештег", "тег")):
        found, name = re.findall(r"#[\wА-Яа-яЁё]+", p), "Хэштеги"
    elif kind.startswith("упоминани"):
        found, name = re.findall(r"(?<![\w.])@[\w.]+", p), "Упоминания"
    else:
        found, name = re.findall(NUM, p), "Числа"
    if not found:
        return f"{name}: в тексте не нашёл."
    uniq = list(dict.fromkeys(found))
    return f"{name} ({len(uniq)}):\n\n" + "\n".join(f"- {x}" for x in uniq)


_LOREM = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore "
          "magna aliqua ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo "
          "consequat duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur").split()
_FISH = ["Равным образом новая модель организационной деятельности требует от нас анализа направлений прогрессивного развития.",
         "Повседневная практика показывает, что начало повседневной работы по формированию позиции играет важную роль.",
         "Не следует, однако, забывать, что рамки и место обучения кадров способствуют подготовке и реализации новых предложений.",
         "Таким образом, укрепление и развитие структуры позволяет оценить значение системы обучения кадров.",
         "Значимость этих проблем настолько очевидна, что дальнейшее развитие различных форм деятельности требует внимания.",
         "Разнообразный и богатый опыт консультации с широким активом обеспечивает широкому кругу участников новые возможности.",
         "Идейные соображения высшего порядка, а также постоянный рост и сфера нашей активности влияют на итоговые решения.",
         "С другой стороны, сложившаяся структура организации представляет собой интересный эксперимент проверки модели."]


@ptool(CAT_X, "Текст-«рыба» и Lorem ipsum", "рыба текст на 40 слов")
def filler(text, low, s):
    latin = bool(re.search(r"lorem|ipsum|лорем", low))
    if not latin and not re.search(r"рыб\w*\s+текст|текст[- ]рыб|текст-заглушк|текст\w*\s+заполнител|заглушк\w*\s+текст|рыбу\s+(?:на|для)", low):
        return None
    wm = re.search(r"(\d+)\s*слов", low)
    pm = re.search(r"(\d+)\s*абзац", low)
    if latin:
        n = min(int(wm.group(1)), 500) if wm else 50
        words = [_LOREM[i % len(_LOREM)] for i in range(n)]
        body = " ".join(words).capitalize() + "."
        return body if not pm else "\n\n".join([body] * min(int(pm.group(1)), 10))
    paras = min(int(pm.group(1)), 10) if pm else 1
    out = []
    for _ in range(paras):
        sents = random.sample(_FISH, 4)
        out.append(" ".join(sents))
    body = "\n\n".join(out)
    if wm:
        words = body.split()
        n = min(int(wm.group(1)), 500)
        while len(words) < n:
            words += random.choice(_FISH).split()
        body = " ".join(words[:n]).rstrip(",.") + "."
    return body


_NATO = {"A": "Alfa", "B": "Bravo", "C": "Charlie", "D": "Delta", "E": "Echo", "F": "Foxtrot", "G": "Golf", "H": "Hotel",
         "I": "India", "J": "Juliett", "K": "Kilo", "L": "Lima", "M": "Mike", "N": "November", "O": "Oscar", "P": "Papa",
         "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango", "U": "Uniform", "V": "Victor", "W": "Whiskey",
         "X": "X-ray", "Y": "Yankee", "Z": "Zulu", "0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
         "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Niner"}
_RU_PHON = {"А": "Анна", "Б": "Борис", "В": "Василий", "Г": "Григорий", "Д": "Дмитрий", "Е": "Елена", "Ё": "Ёлка",
            "Ж": "Женя", "З": "Зинаида", "И": "Иван", "Й": "Иван краткий", "К": "Константин", "Л": "Леонид",
            "М": "Михаил", "Н": "Николай", "О": "Ольга", "П": "Павел", "Р": "Роман", "С": "Семён", "Т": "Татьяна",
            "У": "Ульяна", "Ф": "Фёдор", "Х": "Харитон", "Ц": "Цапля", "Ч": "Человек", "Ш": "Шура", "Щ": "Щука",
            "Ъ": "твёрдый знак", "Ы": "еры", "Ь": "мягкий знак", "Э": "Эхо", "Ю": "Юрий", "Я": "Яков"}


@ptool(CAT_X, "Продиктовать по буквам (NATO и русский алфавит)", "по буквам nato: RAI")
def spell(text, low, s):
    if not re.search(r"по\s+буквам|фонетическ\w*\s+алфавит|\bnato\b|натовск|продиктуй", low):
        return None
    p = _payload(text)
    if not p:
        m = re.search(r"(?:по\s+буквам|продиктуй)\s+(\S+)", text, re.I)
        p = m.group(1) if m else ""
    if not p:
        return None
    out = []
    for ch in p.upper():
        if ch in _NATO:
            out.append(f"{ch} — {_NATO[ch]}")
        elif ch in _RU_PHON:
            out.append(f"{ch} — {_RU_PHON[ch]}")
        elif ch.strip():
            out.append(f"{ch}")
    return "\n".join(out) if out else None


_FLIP = dict(zip("abcdefghijklmnopqrstuvwxyz1234567890?!.,'\"()[]{}<>_",
                 "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎzƖᄅƐㄣϛ9ㄥ860¿¡˙'„\",)(][}{><‾"))


@ptool(CAT_X, "Текст вверх ногами", "перевёрнутым текстом: hello world")
def upside_down(text, low, s):
    if not re.search(r"перевернут\w*\s+(?:текст|шрифт)|вверх\s+ногами|кверху\s+ногами", low):
        return None
    p = _payload(text)
    if not p:
        return None
    return "".join(_FLIP.get(c, _FLIP.get(c.lower(), c)) for c in reversed(p))


@ptool(CAT_X, "Зачёркнутый текст для соцсетей", "зачеркни текст: старая цена 1000")
def strike(text, low, s):
    if not re.search(r"зачеркн", low):
        return None
    p = _payload(text)
    return "".join(c + "\u0336" if c.strip() else c for c in p) if p else None


def _math_alpha(p, upper0, lower0, digit0=None):
    out = []
    for c in p:
        if "A" <= c <= "Z":
            out.append(chr(upper0 + ord(c) - 65))
        elif "a" <= c <= "z":
            out.append(chr(lower0 + ord(c) - 97))
        elif digit0 and "0" <= c <= "9":
            out.append(chr(digit0 + ord(c) - 48))
        else:
            out.append(c)
    return "".join(out)


@ptool(CAT_X, "Жирный и курсивный шрифт для соцсетей", "жирным шрифтом: Rai 2026")
def fancy_font(text, low, s):
    m = re.search(r"(жирн|курсив)\w*\s*(?:шрифт\w*|текст\w*|буквам\w*)?", low)
    if not m or not re.search(r"(?:жирн|курсив)\w*\s*(?:шрифт\w*|текст\w*|буквам\w*)?\s*(?:для\s+\w+\s*)?:", low):
        return None
    p = _payload(text)
    if not p:
        return None
    if m.group(1) == "жирн":
        out = _math_alpha(p, 0x1D400, 0x1D41A, 0x1D7CE)
    else:
        out = _math_alpha(p, 0x1D434, 0x1D44E).replace(chr(0x1D44E + 7), "ℎ")
    note = "\n\nКириллица в таких шрифтах Юникода не поддерживается — латиница и цифры станут жирными/курсивом." if re.search(r"[А-Яа-яЁё]", p) else ""
    return out + note


@ptool(CAT_X, "Каждое предложение с заглавной буквы", "предложения с заглавной буквы: привет. как дела? всё хорошо")
def sentence_case(text, low, s):
    if not re.search(r"предложени\w*\s+с\s+(?:заглавн|больш)|исправь\s+регистр|с\s+заглавн\w*\s+букв\w*\s+(?:в\s+)?(?:начале\s+)?предложени", low):
        return None
    p = _payload(text)
    if not p:
        return None
    out = re.sub(r"(^\s*|[.!?…]\s+)([a-zа-яё])", lambda m: m.group(1) + m.group(2).upper(), p.lower())
    return f"```\n{out}\n```"


@ptool(CAT_X, "Убрать знаки препинания", "убери знаки препинания: Привет, мир! Как дела?")
def strip_punct(text, low, s):
    if not re.search(r"(?:убери|удали)\w*\s+(?:все\s+)?(?:знаки\s+препинания|пунктуаци)", low):
        return None
    p = _payload(text)
    if not p:
        return None
    return "```\n" + re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", p)).strip() + "\n```"


@ptool(CAT_X, "Перемешать буквы или слова", "перемешай буквы: привет")
def shuffle(text, low, s):
    m = re.search(r"перемешай\s+(?:все\s+)?(буквы|слова|символы|строки)", low)
    p = _payload(text)
    if not m or not p:
        return None
    if m.group(1) == "слова":
        ws = p.split()
        random.shuffle(ws)
        return " ".join(ws)
    if m.group(1) == "строки":
        ls = [x for x in p.splitlines() if x.strip()]
        random.shuffle(ls)
        return "\n".join(ls)
    chars = list(p)
    random.shuffle(chars)
    return "".join(chars)


# ================================================================ ПРОГРАММИСТУ
CAT_D = "Программисту"


def _json_payload(text):
    p = _payload(text)
    if not p:
        m = re.search(r"json\s+(.+)$", text, re.I | re.S)
        p = m.group(1) if m else ""
    return p.strip().strip("`")


@ptool(CAT_D, "JSON: проверить и красиво отформатировать", 'отформатируй json: {"name":"Rai","tags":["ai","offline"]}')
def json_format(text, low, s):
    if not re.search(r"(?:отформатир|форматир|красив\w*|провер\w*|валидир\w*|разбери|почини)\w*\s+(?:мой\s+|этот\s+)?json", low):
        return None
    p = _json_payload(text)
    if not p:
        return None
    try:
        data = json.loads(p)
    except json.JSONDecodeError as e:
        return f"❌ Ошибка в JSON: строка {e.lineno}, столбец {e.colno} — {e.msg}.\n\nЧастые причины: одинарные кавычки, лишняя запятая в конце, ключ без кавычек."
    return "✅ JSON корректный:\n```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```"


@ptool(CAT_D, "JSON в одну строку (минификация)", 'сожми json: {\n  "a": 1,\n  "b": [1, 2]\n}')
def json_min(text, low, s):
    if not re.search(r"(?:сожми|минифицир\w*|минимизир\w*|в\s+одну\s+строку|ужми)\s*(?:\w+\s+)?json|json\s+в\s+одну\s+строку", low):
        return None
    p = _json_payload(text)
    if not p:
        return None
    try:
        data = json.loads(p)
    except json.JSONDecodeError as e:
        return f"❌ Ошибка в JSON: строка {e.lineno}, столбец {e.colno} — {e.msg}."
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"```json\n{out}\n```\n{len(p)} → {len(out)} символов."


@ptool(CAT_D, "Битовые операции (AND, OR, XOR, сдвиги)", "5 xor 3")
def bitwise(text, low, s):
    m = re.search(r"(\d+)\s*(xor|and|or|nand|nor|<<|>>|побитов\w*\s+(?:и|или)|исключающ\w*\s+или)\s*(\d+)", low)
    if not m:
        return None
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    if a > 2 ** 64 or b > 2 ** 64:
        return None
    if op in ("and",) or op.endswith(" и"):
        r, sym = a & b, "AND"
    elif op in ("or",) or (op.endswith("или") and "исключ" not in op):
        r, sym = a | b, "OR"
    elif op == "xor" or "исключ" in op:
        r, sym = a ^ b, "XOR"
    elif op == "nand":
        r, sym = ~(a & b) & (2 ** max(a.bit_length(), b.bit_length(), 1) - 1), "NAND"
    elif op == "nor":
        r, sym = ~(a | b) & (2 ** max(a.bit_length(), b.bit_length(), 1) - 1), "NOR"
    elif op == "<<":
        if b > 256:
            return None
        r, sym = a << b, "<<"
    else:
        r, sym = a >> b, ">>"
    w = max(a.bit_length(), b.bit_length(), r.bit_length(), 1)
    if sym in ("<<", ">>"):
        return f"{a} {sym} {b} = **{r}**\n```\n{a:0{w}b}\n{r:0{w}b}\n```"
    return f"{a} {sym} {b} = **{r}**\n```\n  {a:0{w}b}  ({a})\n  {b:0{w}b}  ({b})\n= {r:0{w}b}  ({r})\n```"


@ptool(CAT_D, "Права доступа chmod", "chmod 755")
def chmod(text, low, s):
    if not re.search(r"chmod|права\s+(?:доступа|на\s+файл)|unix[- ]?права", low):
        return None
    m = re.search(r"(?<!\d)([0-7]{3,4})(?!\d)", low)
    names = ("владелец", "группа", "остальные")
    if m:
        digits = m.group(1)[-3:]
        rows, sym = [], ""
        for who, d in zip(names, digits):
            d = int(d)
            p = ("r" if d & 4 else "-") + ("w" if d & 2 else "-") + ("x" if d & 1 else "-")
            sym += p
            can = [x for x, bit in (("чтение", 4), ("запись", 2), ("выполнение", 1)) if d & bit] or ["ничего"]
            rows.append(f"- {who}: {p} — {', '.join(can)}")
        return f"chmod {m.group(1)} = **{sym}**\n\n" + "\n".join(rows)
    m = re.search(r"([r-][w-][x-][r-][w-][x-][r-][w-][x-])", low)
    if m:
        p = m.group(1)
        octal = "".join(str((4 if p[i] == "r" else 0) + (2 if p[i + 1] == "w" else 0) + (1 if p[i + 2] == "x" else 0)) for i in (0, 3, 6))
        return f"{p} = **chmod {octal}**"
    return None


@ptool(CAT_D, "Подсеть IPv4/IPv6 (CIDR) и маска", "подсеть 192.168.1.0/24")
def subnet(text, low, s):
    m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})\s*/\s*(\d{1,2})(?!\d)", low)
    if not m:
        mm = re.search(r"маск\w*\s+(\d{1,3}(?:\.\d{1,3}){3})", low)
        if mm:
            pref = ipaddress.IPv4Network("0.0.0.0/" + mm.group(1)).prefixlen
            return f"Маска {mm.group(1)} = **/{pref}** — {num(2 ** (32 - pref))} адресов, {num(max(2 ** (32 - pref) - 2, 0))} для хостов."
        return None
    net = ipaddress.ip_network(m.group(1) + "/" + m.group(2), strict=False)
    hosts = net.num_addresses - 2 if net.prefixlen < 31 else net.num_addresses
    first = net.network_address + (1 if net.prefixlen < 31 else 0)
    last = net.broadcast_address - (1 if net.prefixlen < 31 else 0)
    return (f"Сеть **{net}**\n\n| Параметр | Значение |\n|---|---|\n| Маска | {net.netmask} |\n| Wildcard | {net.hostmask} |\n"
            f"| Адрес сети | {net.network_address} |\n| Широковещательный | {net.broadcast_address} |\n"
            f"| Хосты | {first} — {last} |\n| Адресов для хостов | {num(hosts)} |\n"
            f"| Тип | {'частная (локальная)' if net.is_private else 'публичная'} |")


_KNOWN_IP = {"8.8.8.8": "Google Public DNS", "8.8.4.4": "Google Public DNS", "1.1.1.1": "Cloudflare DNS",
             "1.0.0.1": "Cloudflare DNS", "77.88.8.8": "Яндекс.DNS", "77.88.8.1": "Яндекс.DNS", "9.9.9.9": "Quad9 DNS",
             "127.0.0.1": "этот компьютер (localhost)", "0.0.0.0": "«все адреса» / не назначен", "192.168.0.1": "типичный адрес роутера",
             "192.168.1.1": "типичный адрес роутера", "10.0.0.1": "типичный адрес роутера"}


@ptool(CAT_D, "Информация об IP-адресе", "что за ip 8.8.8.8")
def ip_info(text, low, s):
    if not re.search(r"\bip\b|айпи|ip-адрес|ип\s*адрес|ipv[46]", low):
        return None
    m = re.search(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d./])|((?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4})", low)
    if not m:
        return None
    ip = ipaddress.ip_address(m.group(1) or m.group(2))
    kind = ("loopback (этот компьютер)" if ip.is_loopback else "частный — локальная сеть" if ip.is_private else
            "multicast" if ip.is_multicast else "зарезервирован" if ip.is_reserved else "link-local" if ip.is_link_local else
            "публичный — в интернете")
    rows = [f"- версия: IPv{ip.version}", f"- тип: {kind}"]
    if ip.version == 4:
        first = int(str(ip).split(".")[0])
        cls = "A" if first < 128 else "B" if first < 192 else "C" if first < 224 else "D (multicast)" if first < 240 else "E"
        rows.append(f"- класс: {cls}")
        rows.append(f"- в двоичном: {'.'.join(f'{int(o):08b}' for o in str(ip).split('.'))}")
    rows.append(f"- обратная зона DNS: {ip.reverse_pointer}")
    known = _KNOWN_IP.get(str(ip))
    return f"**{ip}**" + (f" — {known}" if known else "") + "\n\n" + "\n".join(rows)


_HTTP = {
    100: ("Continue", "сервер получил заголовки, можно слать тело запроса"),
    101: ("Switching Protocols", "переход на другой протокол (например WebSocket)"),
    200: ("OK", "всё хорошо, запрос выполнен"), 201: ("Created", "ресурс создан"), 202: ("Accepted", "принято, выполнится позже"),
    204: ("No Content", "успешно, но ответ пустой"), 206: ("Partial Content", "отдана часть файла (докачка, видео)"),
    301: ("Moved Permanently", "адрес переехал навсегда — обновите ссылку"), 302: ("Found", "временный редирект"),
    303: ("See Other", "смотрите другой адрес (после отправки формы)"), 304: ("Not Modified", "не изменилось — берите из кэша"),
    307: ("Temporary Redirect", "временный редирект с сохранением метода"), 308: ("Permanent Redirect", "постоянный редирект с сохранением метода"),
    400: ("Bad Request", "неверный запрос — проверьте параметры и формат"), 401: ("Unauthorized", "нужен вход или токен"),
    402: ("Payment Required", "нужна оплата"), 403: ("Forbidden", "доступ запрещён — прав не хватает"),
    404: ("Not Found", "страницы нет — проверьте адрес"), 405: ("Method Not Allowed", "этот метод (GET/POST) тут не разрешён"),
    406: ("Not Acceptable", "сервер не может отдать в нужном формате"), 408: ("Request Timeout", "запрос шёл слишком долго"),
    409: ("Conflict", "конфликт — ресурс уже изменён или существует"), 410: ("Gone", "удалено навсегда"),
    413: ("Payload Too Large", "слишком большой файл или тело запроса"), 414: ("URI Too Long", "слишком длинный адрес"),
    415: ("Unsupported Media Type", "неподдерживаемый формат данных"), 418: ("I'm a teapot", "я чайник — шуточный код"),
    422: ("Unprocessable Entity", "данные понятны, но не прошли проверку"), 425: ("Too Early", "слишком рано, повторите позже"),
    429: ("Too Many Requests", "слишком много запросов — подождите"), 431: ("Request Header Fields Too Large", "слишком большие заголовки (часто — куки)"),
    451: ("Unavailable For Legal Reasons", "недоступно по юридическим причинам"),
    500: ("Internal Server Error", "ошибка на сервере — смотрите логи"), 501: ("Not Implemented", "сервер этого не умеет"),
    502: ("Bad Gateway", "прокси получил плохой ответ от сервера за ним"), 503: ("Service Unavailable", "сервер перегружен или на обслуживании"),
    504: ("Gateway Timeout", "сервер за прокси не ответил вовремя"), 505: ("HTTP Version Not Supported", "неподдерживаемая версия HTTP"),
    507: ("Insufficient Storage", "на сервере закончилось место"), 508: ("Loop Detected", "бесконечный цикл на сервере"),
    511: ("Network Authentication Required", "нужно войти в сеть (Wi-Fi в кафе, отеле)"),
    520: ("Unknown Error (Cloudflare)", "сервер сайта ответил непонятно"), 521: ("Web Server Is Down (Cloudflare)", "сервер сайта выключен"),
    522: ("Connection Timed Out (Cloudflare)", "сервер сайта не отвечает"), 523: ("Origin Is Unreachable (Cloudflare)", "сервер сайта недоступен"),
    524: ("A Timeout Occurred (Cloudflare)", "сервер сайта слишком долго отвечал"), 525: ("SSL Handshake Failed (Cloudflare)", "ошибка SSL на сервере"),
    526: ("Invalid SSL Certificate (Cloudflare)", "недействительный сертификат на сервере"),
}


@ptool(CAT_D, "HTTP-коды ответов: что значат", "http код 404")
def http_code(text, low, s):
    if not re.search(r"\bhttp|ошибк\w*|код\w*\s+(?:ответа|состояния|статуса)|статус\w*|response", low):
        return None
    m = re.search(r"(?<!\d)([1-5]\d\d)(?!\d)", low)
    if not m or int(m.group(1)) not in _HTTP:
        return None
    code = int(m.group(1))
    name, what = _HTTP[code]
    group = {1: "информационный", 2: "успех", 3: "перенаправление", 4: "ошибка клиента", 5: "ошибка сервера"}[code // 100]
    return f"**HTTP {code} {name}** — {what}.\n\nГруппа {code // 100}xx: {group}."


_CRON_MACRO = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *", "@weekly": "0 0 * * 0",
               "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *"}
_CRON_DOW = ["воскресенье", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def _cron_part(v, unit, names=None):
    def nm(x):
        return names[int(x)] if names and x.isdigit() and int(x) < len(names) else x
    if v == "*":
        return None
    if v.startswith("*/"):
        return f"каждые {v[2:]} {unit}"
    if "," in v:
        return ", ".join(nm(x) for x in v.split(","))
    if "-" in v:
        a, b = v.split("-", 1)
        return f"с {nm(a)} по {nm(b)}"
    return nm(v)


@ptool(CAT_D, "Расшифровка cron-расписания", "cron */5 * * * *")
def cron(text, low, s):
    if not re.search(r"\bcron|крон\w*|crontab", low):
        return None
    mm = re.search(r"@(?:yearly|annually|monthly|weekly|daily|midnight|hourly|reboot)", low)
    if mm:
        if mm.group(0) == "@reboot":
            return "**@reboot** — запуск один раз при старте системы."
        expr = _CRON_MACRO[mm.group(0)]
    else:
        m = re.search(r"([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-?lw]+)\s+([\d*/,\-a-z]+)\s+([\d*/,\-a-z?l#]+)", low)
        if not m:
            return None
        expr = " ".join(m.groups())
    mi, ho, dom, mon, dow = expr.split()
    parts = []
    if mi.isdigit() and ho.isdigit():
        parts.append(f"в {int(ho):02d}:{int(mi):02d}")
    else:
        if mi == "*":
            parts.append("каждую минуту")
        else:
            parts.append(f"минуты: {_cron_part(mi, 'мин.')}" if not mi.startswith("*/") else _cron_part(mi, "мин."))
        if ho != "*":
            parts.append(f"часы: {_cron_part(ho, 'ч')}" if not ho.startswith("*/") else _cron_part(ho, "ч"))
    if dom != "*":
        parts.append(f"числа месяца: {_cron_part(dom, 'дн.')}" if not dom.startswith("*/") else _cron_part(dom, "дн."))
    if mon != "*":
        parts.append(f"месяцы: {_cron_part(mon, 'мес.', _MONTH_NOM)}")
    if dow != "*":
        if dow in ("1-5", "mon-fri"):
            parts.append("по будням (пн–пт)")
        elif dow in ("0,6", "6,0", "6-7", "sat,sun"):
            parts.append("по выходным")
        else:
            parts.append(f"дни недели: {_cron_part(dow, 'дн.', _CRON_DOW)}")
    if dom == "*" and dow == "*" and (mi.isdigit() and ho.isdigit()):
        parts.append("каждый день")
    return f"`{expr}` — **{', '.join(parts).rstrip('.')}**.\n\nПоля: минута, час, день месяца, месяц, день недели (0 и 7 — воскресенье)."


@ptool(CAT_D, "Проверить регулярное выражение", r"регулярка \d+ на тексте abc123 и x45")
def regex_test(text, low, s):
    m = re.search(r"(?:регулярк\w*|регулярн\w*\s+выражени\w*|regex|regexp)\s+(.+?)\s+(?:на|в|для)\s+(?:тексте|строке)\s*:?\s*(.+)$", text, re.I | re.S)
    if not m:
        return None
    pat, sample = m.group(1).strip("`'\" "), m.group(2)[:500]
    if len(pat) > 200 or re.search(r"\([^)]*[+*][^)]*\)\s*[+*{]", pat):
        return "Слишком сложный шаблон: вложенные повторы вида (a+)+ могут «зависнуть». Упростите выражение."
    try:
        rx = re.compile(pat)
    except re.error as e:
        return f"❌ Ошибка в регулярном выражении: {e}"
    found = [mm for mm, _ in zip(rx.finditer(sample), range(30))]
    if not found:
        return f"Шаблон `{pat}` — совпадений нет."
    rows = [f"- `{x.group(0)}`" + (f" → группы: {', '.join(repr(g) for g in x.groups())}" if x.groups() else "") for x in found]
    return f"Шаблон `{pat}` — совпадений: **{len(found)}**\n\n" + "\n".join(rows)


@ptool(CAT_D, "Случайный токен / секретный ключ", "сгенерируй токен 32")
def token(text, low, s):
    if not re.search(r"(?:сгенерир|создай|придумай|дай|нужен|нужна)\w*\s+(?:мне\s+)?(?:случайн\w*\s+)?(?:токен|api[- ]?ключ|секретн\w*\s+(?:ключ|строк)|secret|соль|nonce|hex-?строк|ключ\s+для\s+api)", low):
        return None
    k = [x for x in ints(low) if 8 <= x <= 256]
    n = k[0] if k else 32
    hx = secrets.token_hex((n + 1) // 2)[:n]
    url = secrets.token_urlsafe(n)[:n]
    return (f"Случайный токен ({n} {_plural(n, 'символ', 'символа', 'символов')}), создан криптографически стойким генератором прямо на устройстве:\n\n"
            f"- hex: `{hx}`\n- base64url: `{url}`")


_SIZE = {"б": 1, "кб": 1024, "мб": 1024 ** 2, "гб": 1024 ** 3, "тб": 1024 ** 4, "kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3, "tb": 1024 ** 4}


@ptool(CAT_D, "Сколько скачивается файл", "сколько качать 4 гб при 100 мбит", early=True)
def download_time(text, low, s):
    if not re.search(r"(?:сколько|за\s+сколько|время)\s+(?:будет\s+)?(?:качат|скачиват|загружат|скачает|загрузит|скачать|загрузить|закачать|отправ)|скорост\w*\s+скачиван", low):
        return None
    sm = re.search(r"(" + NUM + r")\s*(тб|гб|мб|кб|tb|gb|mb|kb)(?![/a-zа-я])", low)
    vm = re.search(r"(" + NUM + r")\s*(гбит|мбит|кбит|gbps|mbps|kbps|мб/с|mb/s|кб/с|kb/s)", low)
    if not sm or not vm:
        return None
    size = f(sm.group(1)) * _SIZE[sm.group(2)]
    unit = vm.group(2)
    bps = f(vm.group(1)) * {"гбит": 1e9, "gbps": 1e9, "мбит": 1e6, "mbps": 1e6, "кбит": 1e3, "kbps": 1e3}.get(unit, 0) / 8
    if not bps:
        bps = f(vm.group(1)) * (1024 ** 2 if unit in ("мб/с", "mb/s") else 1024)
    if bps <= 0:
        return None
    t = size / bps
    return (f"{sm.group(1)} {sm.group(2).upper()} при {vm.group(1)} {unit}: **{_secs(t)}** в идеале "
            f"(реальная скорость обычно на 10–20% ниже: ≈ {_secs(t * 1.15)}).\n\n"
            f"Скорость {vm.group(1)} {unit} = {_r(bps / 1024 ** 2, 2)} МБ/с.")


_PAPER = {"a0": (84.1, 118.9), "a1": (59.4, 84.1), "a2": (42.0, 59.4), "a3": (29.7, 42.0), "a4": (21.0, 29.7),
          "a5": (14.8, 21.0), "a6": (10.5, 14.8)}


@ptool(CAT_D, "Пиксели для печати (DPI)", "сколько пикселей a4 при 300 dpi")
def dpi(text, low, s):
    if not re.search(r"\bdpi\b|\bppi\b|точек\s+на\s+дюйм", low):
        return None
    dm = re.search(r"(\d+)\s*(?:dpi|ppi|точек)", low)
    d = int(dm.group(1)) if dm else 300
    pm = re.search(r"(?<![a-z])(a[0-6])(?![0-9])", low.replace("а", "a"))
    if pm:
        w, h = _PAPER[pm.group(1)]
        name = pm.group(1).upper()
    else:
        sm = re.search(r"(" + NUM + r")\s*(?:на|x|х|×)\s*(" + NUM + r")\s*(см|мм|пикс|px)", low)
        if not sm:
            return None
        a, b, u = f(sm.group(1)), f(sm.group(2)), sm.group(3)
        if u in ("пикс", "px"):
            return f"{num(a)}×{num(b)} px при {d} DPI = **{_r(a / d * 2.54, 1)} × {_r(b / d * 2.54, 1)} см**"
        w, h = (a / 10, b / 10) if u == "мм" else (a, b)
        name = f"{num(a)}×{num(b)} {u}"
    pw, ph = round(w / 2.54 * d), round(h / 2.54 * d)
    return f"{name} ({num(w)}×{num(h)} см) при {d} DPI = **{pw} × {ph} пикселей** ({_r(pw * ph / 1e6, 1)} Мп)"


_RATIOS = [(16 / 9, "16:9 (HD, Full HD, 4K)"), (4 / 3, "4:3"), (3 / 2, "3:2 (фото)"), (21 / 9, "21:9 (ультраширокий)"),
           (16 / 10, "16:10"), (1, "1:1 (квадрат)"), (9 / 16, "9:16 (вертикальное видео, Stories, Reels)"), (5 / 4, "5:4"), (4 / 5, "4:5 (пост Instagram)")]


@ptool(CAT_D, "Соотношение сторон экрана и картинки", "соотношение сторон 1920 на 1080")
def aspect(text, low, s):
    if not re.search(r"соотношени\w*\s+сторон|aspect\s*ratio|пропорци\w*\s+(?:экрана|картинки|изображени|видео|кадра)|формат\s+кадра", low):
        return None
    m = re.search(r"(\d+)\s*(?:x|х|×|на|:|\*)\s*(\d+)", low)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    if not a or not b:
        return None
    g = math.gcd(a, b)
    near = min(_RATIOS, key=lambda r: abs(r[0] - a / b))
    exact = abs(near[0] - a / b) < 1e-9
    close = f" — {near[1]}" if exact else f" ≈ {near[1]}" if abs(near[0] - a / b) < 0.02 else ""
    return f"{a}×{b}: соотношение **{a // g}:{b // g}**{close} (= {_r(a / b, 4)} : 1)"


def _hex(c):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@ptool(CAT_D, "Контраст цветов (доступность WCAG)", "контраст #000000 и #ffffff", before="Цвета: HEX ↔ RGB")
def contrast(text, low, s):
    if not re.search(r"контраст", low):
        return None
    cs = re.findall(r"#([0-9a-f]{6}|[0-9a-f]{3})(?![0-9a-f])", low)
    if len(cs) < 2:
        return None
    l1, l2 = sorted((_lum(_hex(cs[0])), _lum(_hex(cs[1]))), reverse=True)
    ratio = (l1 + 0.05) / (l2 + 0.05)
    ok = lambda x: "✅" if ratio >= x else "❌"  # noqa: E731
    return (f"Контраст #{cs[0]} и #{cs[1]}: **{_r(ratio, 2)} : 1**\n\n- {ok(4.5)} AA, обычный текст (≥ 4,5)\n"
            f"- {ok(3)} AA, крупный текст (≥ 3)\n- {ok(7)} AAA, обычный текст (≥ 7)\n- {ok(4.5)} AAA, крупный текст (≥ 4,5)")


@ptool(CAT_D, "Цвет HEX → HSL, HSV и CMYK", "#ff8800 в hsl", before="Цвета: HEX ↔ RGB")
def hex_hsl(text, low, s):
    if not re.search(r"\bhsl|\bhsv|\bhsb|\bcmyk", low):
        return None
    m = re.search(r"#([0-9a-f]{6}|[0-9a-f]{3})(?![0-9a-f])", low)
    if not m:
        return None
    r, g, b = _hex(m.group(1))
    h, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    k = 1 - max(r, g, b) / 255
    cmyk = (0, 0, 0, 100) if k == 1 else tuple(round((1 - x / 255 - k) / (1 - k) * 100) for x in (r, g, b)) + (round(k * 100),)
    return (f"#{m.group(1).upper()}:\n\n- RGB: rgb({r}, {g}, {b})\n- HSL: **hsl({round(h * 360)}, {round(sat * 100)}%, {round(l * 100)}%)**\n"
            f"- HSV/HSB: {round(hh * 360)}°, {round(ss * 100)}%, {round(vv * 100)}%\n- CMYK: {cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%")


_COLOR_NAMES = [("бирюз", "#30D5C8", "бирюзовый"), ("красн", "#FF0000", "красный"), ("алый", "#FF2400", "алый"),
                ("бордов", "#800000", "бордовый"), ("оранж", "#FFA500", "оранжевый"), ("персик", "#FFDAB9", "персиковый"),
                ("желт", "#FFFF00", "жёлтый"), ("золот", "#FFD700", "золотой"), ("лаймов", "#00FF00", "лаймовый"),
                ("салатов", "#99FF99", "салатовый"), ("оливков", "#808000", "оливковый"), ("изумруд", "#50C878", "изумрудный"),
                ("мятн", "#98FF98", "мятный"), ("зелен", "#008000", "зелёный"), ("голуб", "#42AAFF", "голубой"),
                ("небесн", "#87CEEB", "небесно-голубой"), ("темно-син", "#00008B", "тёмно-синий"), ("син", "#0000FF", "синий"),
                ("индиго", "#4B0082", "индиго"), ("фиолет", "#8B00FF", "фиолетовый"), ("сиренев", "#C8A2C8", "сиреневый"),
                ("лавандов", "#E6E6FA", "лавандовый"), ("пурпур", "#800080", "пурпурный"), ("малинов", "#DC143C", "малиновый"),
                ("розов", "#FFC0CB", "розовый"), ("корич", "#964B00", "коричневый"), ("бежев", "#F5F5DC", "бежевый"),
                ("шоколад", "#D2691E", "шоколадный"), ("серебр", "#C0C0C0", "серебряный"), ("сер", "#808080", "серый"),
                ("черн", "#000000", "чёрный"), ("бел", "#FFFFFF", "белый"), ("хаки", "#806B2A", "хаки"), ("коралл", "#FF7F50", "коралловый")]


@ptool(CAT_D, "Код цвета по названию", "hex код бирюзового цвета")
def color_by_name(text, low, s):
    if not re.search(r"(?:hex|rgb|код\w*)\s+(?:код\w*\s+)?(?:\w+\s+)?цвет|цвет\w*\s+(?:\w+\s+)?(?:в\s+hex|в\s+rgb|код)", low):
        return None
    found = next(((hx, name) for stem, hx, name in _COLOR_NAMES if re.search(r"(?<![а-я])" + stem, low)), None)
    if not found:
        return None
    hx, name = found
    r, g, b = _hex(hx)
    return f"{name.capitalize()}: **{hx}** = rgb({r}, {g}, {b})"


@ptool(CAT_D, "Экранировать и разэкранировать HTML", "экранируй html: <b>Привет & пока</b>")
def html_escape(text, low, s):
    p = _payload(text)
    if not p:
        return None
    if re.search(r"разэкранир|unescape|декодир\w*\s+html|html[- ]?сущност\w*\s+в\s+текст", low):
        return "```\n" + html.unescape(p) + "\n```"
    if re.search(r"экранир\w*\s+(?:html|теги|спецсимвол)|html[- ]?(?:сущност|entities|escape)|escape\s+html", low):
        return "```\n" + html.escape(p) + "\n```"
    return None


def _ver(v):
    m = re.fullmatch(r"v?(\d+(?:\.\d+)*)(?:-([0-9a-z.]+))?", v)
    nums_ = [int(x) for x in m.group(1).split(".")]
    nums_ += [0] * (4 - len(nums_))
    return (nums_, m.group(2))


@ptool(CAT_D, "Сравнить версии (semver)", "какая версия новее 1.10.0 или 1.9.3")
def semver(text, low, s):
    if not re.search(r"(?:какая|что|котор\w*)\s+(?:версия\s+)?(?:новее|старше|свежее|больше|позже)|верси\w*\s+(?:новее|старше)", low):
        return None
    vs = re.findall(r"(?<![\w.])(v?\d+(?:\.\d+){1,3}(?:-[0-9a-z.]+)?)(?![\w.])", low)
    if len(vs) < 2:
        return None
    a, b = vs[0], vs[1]
    va, vb = _ver(a), _ver(b)
    if va[0] == vb[0]:
        if va[1] == vb[1]:
            return f"Версии {a} и {b} одинаковые."
        newer = a if (va[1] is None) or (vb[1] is not None and va[1] > vb[1]) else b
    else:
        newer = a if va[0] > vb[0] else b
    return (f"Новее: **{newer}**\n\nСравниваются числа по порядку (1.10 > 1.9, потому что 10 > 9), "
            "а предрелиз (-beta, -rc) старше финальной версии.")


def _digits(low, n):
    for m in re.finditer(r"[\d\s\-]{%d,}" % n, low):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) >= n:
            return d
    return ""


@ptool(CAT_D, "Проверка ИНН (контрольная сумма)", "проверь инн 7707083893")
def inn(text, low, s):
    if not re.search(r"(?<![а-я])инн(?![а-я])", low):
        return None
    m = re.search(r"(?<!\d)(\d{10}|\d{12})(?!\d)", low)
    if not m:
        return None
    d = [int(c) for c in m.group(1)]

    def cs(coef, digs):
        return sum(c * x for c, x in zip(coef, digs)) % 11 % 10
    if len(d) == 10:
        ok = cs([2, 4, 10, 3, 5, 9, 4, 6, 8], d) == d[9]
        who = "организации (10 цифр)"
    else:
        ok = (cs([7, 2, 4, 10, 3, 5, 9, 4, 6, 8], d) == d[10] and cs([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8], d) == d[11])
        who = "физлица или ИП (12 цифр)"
    verdict = "✅ контрольные цифры сходятся" if ok else "❌ контрольные цифры НЕ сходятся — в номере опечатка"
    return (f"ИНН {m.group(1)} — {who}: **{verdict}**.\n\nКод региона налоговой: {m.group(1)[:2]}. "
            "Проверка суммы не доказывает, что ИНН выдан, — это делает сервис ФНС.")


@ptool(CAT_D, "Проверка СНИЛС", "проверь снилс 112-233-445 95")
def snils(text, low, s):
    if not re.search(r"снилс", low):
        return None
    d = _digits(low, 11)
    if len(d) != 11:
        return None
    total = sum(int(c) * (9 - i) for i, c in enumerate(d[:9]))
    check = total if total < 100 else 0 if total in (100, 101) else total % 101
    check = 0 if check == 100 else check
    ok = check == int(d[9:])
    return f"СНИЛС {d[:3]}-{d[3:6]}-{d[6:9]} {d[9:]}: **{'✅ контрольное число верное' if ok else '❌ контрольное число не сходится'}** (должно быть {check:02d})."


def _ean_ok(d):
    total = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(d[:-1]))
    return (10 - total % 10) % 10 == int(d[-1]), (10 - total % 10) % 10


@ptool(CAT_D, "Проверка ISBN книги", "проверь isbn 978-5-17-090327-6")
def isbn(text, low, s):
    if not re.search(r"\bisbn", low):
        return None
    raw = re.sub(r"[^\dx]", "", low.split("isbn", 1)[1])
    if len(raw) == 13:
        ok, chk = _ean_ok(raw)
    elif len(raw) == 10:
        total = sum((10 - i) * (10 if c == "x" else int(c)) for i, c in enumerate(raw))
        ok, chk = total % 11 == 0, None
    else:
        return None
    return f"ISBN {raw.upper()}: **{'✅ контрольная цифра верная' if ok else '❌ контрольная цифра не сходится'}**" + (f" (должна быть {chk})" if chk is not None and not ok else "") + "."


_EAN_COUNTRY = [((0, 19), "США и Канада"), ((300, 379), "Франция"), ((400, 440), "Германия"), ((450, 459), "Япония"),
                ((460, 469), "Россия"), ((471, 471), "Тайвань"), ((476, 476), "Азербайджан"), ((477, 477), "Литва"),
                ((481, 481), "Беларусь"), ((482, 482), "Украина"), ((484, 484), "Молдова"), ((485, 485), "Армения"),
                ((486, 486), "Грузия"), ((487, 487), "Казахстан"), ((489, 489), "Гонконг"), ((490, 499), "Япония"),
                ((500, 509), "Великобритания"), ((520, 521), "Греция"), ((590, 590), "Польша"), ((690, 699), "Китай"),
                ((729, 729), "Израиль"), ((750, 750), "Мексика"), ((789, 790), "Бразилия"), ((800, 839), "Италия"),
                ((840, 849), "Испания"), ((859, 859), "Чехия"), ((869, 869), "Турция"), ((870, 879), "Нидерланды"),
                ((880, 880), "Южная Корея"), ((885, 885), "Таиланд"), ((890, 890), "Индия"), ((893, 893), "Вьетнам"),
                ((978, 979), "книги (ISBN)")]


@ptool(CAT_D, "Проверка штрихкода EAN-13 и страна", "проверь штрихкод 4600000000008")
def ean13(text, low, s):
    if not re.search(r"штрих-?код|ean|barcode", low):
        return None
    d = _digits(low, 13)
    if len(d) != 13:
        return None
    ok, chk = _ean_ok(d)
    prefix = int(d[:3])
    country = next((c for (a, b), c in _EAN_COUNTRY if a <= prefix <= b), "неизвестно")
    return (f"Штрихкод {d}: **{'✅ контрольная цифра верная' if ok else f'❌ контрольная цифра должна быть {chk}'}**.\n\n"
            f"Префикс {d[:3]}: {country} — это страна регистрации компании, а не обязательно страна производства.")


# ================================================================ ДОМ И РЕМОНТ
CAT_HOME = "Дом и ремонт"


def _room(low):
    m = re.search(r"(" + NUM + r")\s*(?:м\s*)?(?:на|x|х|×|\*)\s*(" + NUM + ")", low)
    return (f(m.group(1)), f(m.group(2))) if m else None


@ptool(CAT_HOME, "Сколько рулонов обоев нужно", "сколько рулонов обоев комната 4 на 5 высота 2,7")
def wallpaper(text, low, s):
    if not re.search(r"обо[ияе]", low):
        return None
    room = _room(low)
    if not room:
        return None
    h = _kw(low, "высот", "потол") or 2.7
    roll_w = 1.06 if re.search(r"1[.,]06|метров\w*\s+обо|широк", low) else 0.53
    roll_l = 10.05
    per = 2 * (room[0] + room[1])
    win = _kw(low, "окн") or 0
    door = _kw(low, "двер") or 0
    eff = max(per - win * 1.2 - door * 0.8, 0)
    strips = math.ceil(eff / roll_w)
    per_roll = max(int(roll_l // (h + 0.1)), 1)
    rolls = math.ceil(strips / per_roll)
    return (f"Комната {num(room[0])}×{num(room[1])} м, высота {num(h)} м, рулон {num(roll_w)}×{num(roll_l)} м:\n\n"
            f"- периметр: {num(per)} м, полос нужно: {strips}\n- полос из рулона: {per_roll}\n"
            f"- **рулонов: {rolls}** (+1 про запас = {rolls + 1})\n\nС крупным рисунком (раппорт) берите ещё 1–2 рулона.")


@ptool(CAT_HOME, "Сколько плитки нужно", "сколько плитки на пол 3 на 4 плитка 30 на 30")
def tiles(text, low, s):
    if not re.search(r"плитк|кафел|керамогранит", low):
        return None
    tm = re.search(r"плитк\w*\s+(?:размером\s+)?(" + NUM + r")\s*(?:на|x|х|×)\s*(" + NUM + r")", low)
    if not tm:
        return None
    before = low[:tm.start()]
    am = re.search(r"(" + NUM + r")\s*(?:м2|м²|кв\.?\s*м|квадрат)", low)
    if am:
        area = f(am.group(1))
    else:
        room = _room(before)
        if not room:
            return None
        area = room[0] * room[1]
    tw, th = f(tm.group(1)), f(tm.group(2))
    if tw > 5:  # сантиметры
        tw, th = tw / 100, th / 100
    reserve = 0.15 if "диагонал" in low else 0.10
    cnt = math.ceil(area / (tw * th) * (1 + reserve))
    return (f"Площадь {_r(area, 2)} м², плитка {num(tw * 100)}×{num(th * 100)} см:\n\n- **{cnt} плиток** с запасом {int(reserve * 100)}% "
            f"({_r(area * (1 + reserve), 2)} м²)\n- клей: ≈ {math.ceil(area * 5 / 25)} {_plural(math.ceil(area * 5 / 25), 'мешок', 'мешка', 'мешков')} по 25 кг (5 кг/м²)")


@ptool(CAT_HOME, "Сколько краски нужно", "сколько краски на 40 м2 в 2 слоя")
def paint(text, low, s):
    if not re.search(r"краск", low):
        return None
    am = re.search(r"(" + NUM + r")\s*(?:м2|м²|кв\.?\s*м|квадрат)", low)
    if am:
        area = f(am.group(1))
    else:
        room = _room(low)
        h = _kw(low, "высот")
        if not room:
            return None
        area = 2 * (room[0] + room[1]) * h if h else room[0] * room[1]
    cm = re.search(r"(\d+)\s*сло", low)
    coats = int(cm.group(1)) if cm else 2
    lo, hi = area * coats * 0.10, area * coats * 0.15
    return (f"{_r(area, 1)} м² в {coats} {_plural(coats, 'слой', 'слоя', 'слоёв')}: **≈ {_r(lo, 1)}–{_r(hi, 1)} л краски** "
            f"(расход 0,10–0,15 л/м² на слой).\n\nЭто {math.ceil(hi / 2.7)} {_plural(math.ceil(hi / 2.7), 'банка', 'банки', 'банок')} по 2,7 л или "
            f"{math.ceil(hi / 9)} {_plural(math.ceil(hi / 9), 'ведро', 'ведра', 'вёдер')} по 9 л. "
            "Точный расход — на банке.")


@ptool(CAT_HOME, "Сколько ламината или паркета нужно", "сколько упаковок ламината на 18 м2 в упаковке 2,13")
def laminate(text, low, s):
    if not re.search(r"ламинат|паркет|кварцвинил|spc", low):
        return None
    pm = re.search(r"(?:в\s+(?:одной\s+)?упаковк\w*|упаковк\w*\s+по)\s*(" + NUM + r")(?:\s*(?:м2|м²|кв\.?\s*м))?", low)
    pack = f(pm.group(1)) if pm else 2.0
    rest = low[:pm.start()] + " " + low[pm.end():] if pm else low
    am = re.search(r"(" + NUM + r")\s*(?:м2|м²|кв\.?\s*м|квадрат)", rest)
    room = _room(rest)
    area = f(am.group(1)) if am else (room[0] * room[1] if room else None)
    if not area or pack <= 0:
        return None
    reserve = 0.15 if "диагонал" in low else 0.07
    packs = math.ceil(area * (1 + reserve) / pack)
    return (f"{_r(area, 2)} м² + {int(reserve * 100)}% на подрезку = {_r(area * (1 + reserve), 2)} м²\n\n"
            f"**{packs} упаковок** по {num(pack)} м² (всего {_r(packs * pack, 2)} м²). Подложки — {_r(area * 1.1, 1)} м².")


@ptool(CAT_HOME, "Какой мощности нужен кондиционер", "какой кондиционер на 20 м2")
def aircon(text, low, s):
    if not re.search(r"кондиционер|сплит", low):
        return None
    am = re.search(r"(" + NUM + r")\s*(?:м2|м²|кв\.?\s*м|квадрат|метр)", low)
    if not am:
        return None
    area = f(am.group(1))
    h = _kw(low, "высот", "потол") or 2.75
    q = 40 if re.search(r"солнечн|юг|мансард|последн\w*\s+этаж", low) else 35
    people = int(_kw(low, "человек", "люд") or 1)
    kw = area * h * q / 1000 + 0.1 * max(people - 1, 0) + 0.1
    models = [(2.1, "07"), (2.6, "09"), (3.5, "12"), (5.3, "18"), (7.0, "24"), (8.8, "30"), (10.5, "36")]
    pick = next((m for p, m in models if p >= kw), "36+")
    return (f"Комната {num(area)} м², потолок {num(h)} м: нужно **≈ {_r(kw, 2)} кВт холода** → кондиционер класса **«{pick}»**.\n\n"
            "Классы: 07 — 2,1 кВт, 09 — 2,6, 12 — 3,5, 18 — 5,3, 24 — 7,0 кВт.")


@ptool(CAT_HOME, "Сколько бетона нужно", "сколько бетона на фундамент 10 на 0,4 на 0,8")
def concrete(text, low, s):
    if not re.search(r"бетон|стяжк", low):
        return None
    xs = [x for x in nums(low)]
    if "стяжк" in low:
        am = re.search(r"(" + NUM + r")\s*(?:м2|м²|кв\.?\s*м)", low)
        tm = re.search(r"(" + NUM + r")\s*(см|мм)", low)
        if not am or not tm:
            return None
        v = f(am.group(1)) * f(tm.group(1)) / (100 if tm.group(2) == "см" else 1000)
    else:
        if len(xs) < 3:
            return None
        v = xs[0] * xs[1] * xs[2]
    v5 = v * 1.05
    return (f"Объём: **{_r(v, 3)} м³**, с запасом 5% — **{_r(v5, 2)} м³** бетона.\n\n"
            f"Если месить самому (М200): цемента ≈ {math.ceil(v5 * 280 / 50)} {_plural(math.ceil(v5 * 280 / 50), 'мешок', 'мешка', 'мешков')} по 50 кг, "
            f"песка ≈ {_r(v5 * 0.8, 1)} т, щебня ≈ {_r(v5 * 1.1, 1)} т.")


@ptool(CAT_HOME, "Площадь стен, пола и потолка комнаты", "площадь стен комнаты 4 на 5 высота 2,7")
def wall_area(text, low, s):
    if not re.search(r"площад\w*\s+(?:стен|пола|потолк|комнат)", low):
        return None
    room = _room(low)
    h = _kw(low, "высот", "потол")
    if not room:
        return None
    a, b = room
    floor = a * b
    out = f"Комната {num(a)}×{num(b)} м:\n\n- пол и потолок: **{_r(floor, 2)} м²** каждый\n- периметр: {num(2 * (a + b))} м"
    if h:
        walls = 2 * (a + b) * h
        win, door = _kw(low, "окн") or 0, _kw(low, "двер") or 0
        net = walls - win * 1.8 - door * 1.6
        out += f"\n- стены: **{_r(walls, 2)} м²**" + (f" (без окон и дверей ≈ {_r(net, 2)} м²)" if win or door else "")
        out += f"\n- объём: {_r(floor * h, 2)} м³"
    return out


@ptool(CAT_HOME, "Сколько секций радиатора отопления", "сколько секций радиатора на 20 м2")
def radiator(text, low, s):
    if not re.search(r"секци|радиатор|батаре\w*\s+отоплени", low):
        return None
    am = re.search(r"(" + NUM + r")\s*(?:м2|м²|кв\.?\s*м|квадрат)", low)
    if not am:
        return None
    area = f(am.group(1))
    sec = 150 if "чугун" in low else 190 if "алюмин" in low else 180
    need = area * 100 * (1.2 if re.search(r"углов|торцев", low) else 1)
    n = math.ceil(need / sec)
    return (f"{num(area)} м² × 100 Вт/м²{' × 1,2 (угловая)' if need > area * 100 else ''} = {num(round(need))} Вт тепла\n\n"
            f"**{n} секций** по {sec} Вт ({'чугун' if sec == 150 else 'алюминий' if sec == 190 else 'биметалл'}). Для потолков выше 2,7 м — больше.")


@ptool(CAT_HOME, "Объём аквариума, бассейна или бочки", "объём аквариума 60 на 30 на 40 см")
def tank_volume(text, low, s):
    if not re.search(r"(?:объем|сколько\s+литров|сколько\s+воды)\w*\s+(?:в\s+|у\s+)?(?:аквариум|бассейн|бак|бочк|ванн|емкост|резервуар|кастрюл)", low):
        return None
    xs = nums(low)
    cyl = bool(re.search(r"диаметр|бочк|кастрюл|круглый|радиус", low))
    unit_m = bool(re.search(r"\d\s*м(?![а-я])", low)) and not re.search(r"\d\s*см", low)
    k = 1000 if unit_m else 0.001  # м³→л или см³→л
    if cyl and len(xs) >= 2:
        d = xs[0] * (2 if "радиус" in low else 1)
        v = math.pi * (d / 2) ** 2 * xs[1] * k
    elif len(xs) >= 3:
        v = xs[0] * xs[1] * xs[2] * k
    else:
        return None
    return f"Объём: **{_r(v, 1)} л** ({_r(v / 1000, 3)} м³). Вода весит столько же килограммов — {_r(v, 0)} кг."


# ================================================================ КУХНЯ
CAT_FOOD = "Кухня"

_FOOD = [(r"(?<![а-я])сок", "Сок апельсиновый", 45, 0.7, 0.2, 10.4, None),
         (r"яблок", "Яблоко", 47, 0.4, 0.4, 9.8, 180), (r"банан", "Банан", 96, 1.5, 0.5, 21.0, 120),
         (r"апельсин", "Апельсин", 43, 0.9, 0.2, 8.1, 150), (r"мандарин", "Мандарин", 38, 0.8, 0.2, 7.5, 70),
         (r"груш", "Груша", 47, 0.4, 0.3, 10.3, 170), (r"виноград", "Виноград", 72, 0.6, 0.6, 15.4, None),
         (r"клубник", "Клубника", 41, 0.8, 0.4, 7.5, None), (r"арбуз", "Арбуз", 27, 0.6, 0.1, 5.8, None),
         (r"авокадо", "Авокадо", 160, 2.0, 14.7, 1.8, 150), (r"огур", "Огурец", 15, 0.8, 0.1, 2.8, 120),
         (r"помидор|томат", "Помидор", 20, 1.1, 0.2, 3.7, 120), (r"морков", "Морковь", 35, 1.3, 0.1, 6.9, 80),
         (r"капуст", "Капуста белокочанная", 27, 1.8, 0.1, 4.7, None),
         (r"фри(?![а-я])", "Картофель фри", 312, 3.4, 15.0, 41.0, None),
         (r"картоф|картошк", "Картофель варёный", 82, 2.0, 0.4, 16.7, 100),
         (r"гречк|гречнев", "Гречка варёная", 110, 4.2, 1.1, 21.3, None), (r"(?<![а-я])рис", "Рис варёный", 116, 2.2, 0.5, 24.9, None),
         (r"овсянк|овсян\w*\s+каш|геркулес", "Овсянка на воде", 88, 3.0, 1.7, 15.0, None),
         (r"макарон|спагетти", "Макароны варёные", 112, 3.5, 0.4, 23.2, None),
         (r"пельмен", "Пельмени варёные", 248, 11.9, 12.4, 23.0, None),
         (r"ржан\w*\s+хлеб|черн\w*\s+хлеб|бородинск", "Хлеб ржаной", 210, 6.6, 1.2, 40.0, 30),
         (r"хлеб|батон", "Хлеб белый", 265, 7.6, 3.2, 49.0, 30),
         (r"грудк|куриное\s+филе|филе\s+куриц", "Куриная грудка", 113, 23.6, 1.9, 0.4, None),
         (r"куриц|курин", "Курица", 190, 16.0, 14.0, 0.0, None), (r"говядин", "Говядина", 187, 18.9, 12.4, 0.0, None),
         (r"свинин", "Свинина", 259, 16.0, 21.6, 0.0, None), (r"лосос|семг|форел", "Лосось / сёмга", 208, 20.0, 13.0, 0.0, None),
         (r"тун[ец]", "Тунец в собственном соку", 96, 21.0, 1.0, 0.0, None),
         (r"яйц|яиц|яйко", "Яйцо куриное", 157, 12.7, 10.9, 0.7, 55), (r"кефир", "Кефир 1%", 40, 3.0, 1.0, 4.0, None),
         (r"молок", "Молоко 2,5%", 52, 2.8, 2.5, 4.7, None), (r"творог", "Творог 5%", 121, 17.2, 5.0, 1.8, None),
         (r"йогурт", "Йогурт натуральный 1,5%", 57, 4.1, 1.5, 5.9, None), (r"сметан", "Сметана 20%", 206, 2.8, 20.0, 3.2, None),
         (r"(?<![а-я])сыр(?:а|е|ом|ы|ах)?(?![а-я])", "Сыр твёрдый", 363, 23.4, 30.0, 0.0, None),
         (r"сливочн\w*\s+масл", "Масло сливочное", 748, 0.5, 82.5, 0.8, None),
         (r"(?:подсолнечн|оливков|растительн)\w*\s+масл", "Масло растительное", 899, 0.0, 99.9, 0.0, None),
         (r"сахар", "Сахар", 398, 0.0, 0.0, 99.7, None), (r"(?<![а-я])мед(?:а|у|ом)?(?![а-я])", "Мёд", 304, 0.8, 0.0, 81.5, None),
         (r"(?:горьк|черн)\w*\s+шоколад", "Шоколад горький", 539, 6.2, 35.4, 48.2, None),
         (r"шоколад", "Шоколад молочный", 550, 6.9, 35.7, 52.4, None), (r"арахис", "Арахис", 551, 26.3, 45.2, 9.9, None),
         (r"орех", "Грецкие орехи", 654, 15.2, 65.2, 7.0, None), (r"колбас", "Колбаса варёная", 257, 12.8, 22.2, 1.5, None),
         (r"сосиск", "Сосиски", 266, 11.0, 23.9, 1.6, 50), (r"пицц", "Пицца (в среднем)", 250, 10.0, 10.0, 30.0, None),
         (r"бургер", "Гамбургер", 254, 13.0, 11.0, 27.0, 110), (r"(?<![а-я])кол[аыу](?![а-я])|пепси", "Кола", 42, 0.0, 0.0, 10.6, None),
         (r"майонез", "Майонез 67%", 627, 2.4, 67.0, 3.9, None)]


@ptool(CAT_FOOD, "Калорийность и КБЖУ продуктов", "калорийность банана")
def food_kcal(text, low, s):
    if not re.search(r"калорийност|кбжу|сколько\s+(?:калори\w*|ккал|белк\w*|жир\w*|углевод\w*)\s+(?:в|у)\s+", low):
        return None
    item = next((row for row in _FOOD if re.search(row[0], low)), None)
    if not item:
        return None
    _, name, kcal, p, fat, c, piece = item
    gm = re.search(r"(" + NUM + r")\s*(г|гр|грамм\w*|кг)(?![а-я])", low)
    grams = f(gm.group(1)) * (1000 if gm and gm.group(2) == "кг" else 1) if gm else None
    pm = re.search(r"(\d+)\s*(?:шт|штук)", low) or re.search(r"(?<![\d.,])(\d+)\s+(?:" + item[0] + ")", low)
    if not grams and pm and piece:
        grams = int(pm.group(1)) * piece
    out = f"**{name}**, на 100 г: {kcal} ккал · белки {num(p)} г · жиры {num(fat)} г · углеводы {num(c)} г"
    if grams:
        k = grams / 100
        out += f"\n\nНа {num(grams)} г: **{num(round(kcal * k))} ккал** · Б {_r(p * k, 1)} · Ж {_r(fat * k, 1)} · У {_r(c * k, 1)}"
    elif piece:
        out += f"\n\n1 шт. ≈ {piece} г ≈ **{num(round(kcal * piece / 100))} ккал**"
    return out + "\n\nДанные примерные (справочные таблицы), у разных марок отличаются."


@ptool(CAT_FOOD, "Пересчитать рецепт на другое число порций", "пересчитай рецепт с 4 на 6 порций: мука 300 г, молоко 500 мл, яйца 2 шт")
def recipe_scale(text, low, s):
    if not re.search(r"(?:пересчита|пересчет|увелич|уменьш|умнож)\w*\s+рецепт|рецепт\w*\s+(?:на|с)\s+\d+\s+(?:на\s+\d+\s+)?порци", low):
        return None
    head = low.split(":", 1)[0]
    m = re.search(r"с\s+(\d+)\s+(?:до|на)\s+(\d+)", head) or re.search(r"на\s+(\d+)\s+порци\w*,?\s*(?:а\s+)?нужно\s+на\s+(\d+)", head)
    if m:
        k = int(m.group(2)) / int(m.group(1))
    else:
        km = re.search(r"в\s+(" + NUM + r")\s+раз", head)
        if not km:
            return None
        k = f(km.group(1))
        if "уменьш" in head:
            k = 1 / k
    body = _payload(text)
    if not body:
        return None
    out = re.sub(NUM, lambda mm: _r(f(mm.group(0)) * k, 1), body)
    return f"Коэффициент × {_r(k, 3)}:\n\n" + "\n".join(f"- {x.strip()}" for x in re.split(r"[,;\n]", out) if x.strip())


_MEASURES = [("мук", "Мука пшеничная", 160, 130, 25, 10), (r"сахарн\w*\s+пудр", "Сахарная пудра", 180, 140, 25, 10),
             ("сахар", "Сахар", 200, 180, 25, 10), ("сол", "Соль", 325, 260, 30, 10), ("рис", "Рис", 240, 180, 25, 8),
             ("греч", "Гречка", 210, 165, 25, 8), ("овсян|хлопь", "Овсяные хлопья", 90, 70, 12, 4),
             ("вод", "Вода", 250, 200, 18, 5), ("молок", "Молоко", 255, 204, 18, 5), ("сметан", "Сметана", 250, 210, 25, 10),
             ("масл", "Масло растительное", 230, 190, 17, 5), ("мед", "Мёд", 325, 260, 30, 12),
             ("крахмал", "Крахмал", 200, 160, 30, 10), ("какао", "Какао", 130, 100, 15, 6), ("манк|манн", "Манная крупа", 200, 160, 25, 8)]


@ptool(CAT_FOOD, "Кулинарные меры: стакан и ложка в граммах", "сколько грамм в стакане муки")
def kitchen_measures(text, low, s):
    if not re.search(r"(?:грамм|г)\w*\s+(?:[а-я]+\s+){0,2}(?:в\s+)?(?:одном\s+|одной\s+)?(?:стакан|столов\w*\s+ложк|чайн\w*\s+ложк|ложк)|(?:стакан|ложк)\w*\s+\w+\s+(?:это\s+)?сколько\s+грамм", low):
        return None
    item = next((m for m in _MEASURES if re.search(m[0], low)), None)
    if not item:
        return None
    _, name, cup250, cup200, tbsp, tsp = item
    return (f"**{name}** (примерно, без горки):\n\n| Мера | Граммы |\n|---|---|\n| Стакан 250 мл | {cup250} г |\n"
            f"| Гранёный стакан 200 мл | {cup200} г |\n| Столовая ложка | {tbsp} г |\n| Чайная ложка | {tsp} г |")


_COOK = [(r"яиц|яйц", "Яйца (после закипания)", "всмятку — 3 мин, «в мешочек» — 5–6 мин, вкрутую — 8–10 мин", None),
         (r"греч", "Гречка", "15–20 мин под крышкой на слабом огне", "1 : 2"),
         (r"бур\w*\s+рис", "Бурый рис", "30–40 мин", "1 : 2,5"), (r"(?<![а-я])рис", "Рис", "15–20 мин", "1 : 2 (пропаренный 1 : 2,5)"),
         (r"пшен", "Пшено", "20–25 мин", "1 : 2,5"), (r"перловк", "Перловка", "50–60 мин (лучше замочить на ночь)", "1 : 3"),
         (r"овсянк|овсян|геркулес", "Овсянка (хлопья)", "5–10 мин", "1 : 2–3"), (r"булгур", "Булгур", "15 мин", "1 : 2"),
         (r"кускус", "Кускус", "залить кипятком и накрыть на 5 мин", "1 : 1,5"), (r"киноа", "Киноа", "15 мин", "1 : 2"),
         (r"чечевиц", "Чечевица", "красная — 15 мин, зелёная — 30–40 мин", "1 : 2,5"),
         (r"горох", "Горох", "1–1,5 ч (после замачивания)", "1 : 3"), (r"фасол", "Фасоль", "1–1,5 ч (после замачивания на ночь)", "1 : 3"),
         (r"макарон|спагетти", "Макароны", "8–12 мин (смотрите упаковку)", "1 л воды на 100 г"),
         (r"пельмен", "Пельмени", "5–7 мин после всплытия", None), (r"вареник", "Вареники", "4–5 мин после всплытия", None),
         (r"картоф|картошк", "Картофель", "целиком 20–25 мин, кусочками 15 мин", None),
         (r"свекл", "Свёкла", "1–2 ч (в зависимости от размера)", None), (r"морков", "Морковь", "20–30 мин целиком", None),
         (r"кукуруз", "Кукуруза", "молодая — 20–30 мин, зрелая — до 1,5–2 ч", None),
         (r"брокколи|цветн\w*\s+капуст", "Брокколи / цветная капуста", "5–7 мин", None),
         (r"куриц\w*\s+грудк|грудк|филе", "Куриная грудка", "20–25 мин", None), (r"куриц", "Курица целиком", "40–60 мин", None),
         (r"говядин", "Говядина", "1,5–2 ч", None), (r"свинин", "Свинина", "1–1,5 ч", None),
         (r"креветк", "Креветки", "сырые — 2–3 мин, варёно-мороженые — 1 мин", None), (r"сосиск", "Сосиски", "3–5 мин", None),
         (r"кальмар", "Кальмары", "1–2 мин (дольше — станут резиновыми)", None), (r"гриб", "Грибы", "20–30 мин", None)]


@ptool(CAT_FOOD, "Сколько варить: время и пропорции", "сколько варить гречку")
def cook_time(text, low, s):
    if not re.search(r"сколько\s+(?:минут\s+|времени\s+)?(?:варит|готовит|кипятит)|как\s+долго\s+варить|время\s+варки|сколько\s+воды\s+на", low):
        return None
    item = next((c for c in _COOK if re.search(c[0], low)), None)
    if not item:
        return None
    _, name, t, ratio = item
    return f"**{name}**: {t}." + (f"\n\nПропорция крупы и воды: {ratio}." if ratio else "")


_PARTY = [(r"шашлык|мяс", "Мяса для шашлыка (сырого)", 0.35, "кг"), (r"пицц", "Пиццы 30 см (8 кусков)", 0.4, "шт."),
          (r"торт", "Торта", 0.15, "кг"), (r"салат", "Салатов", 0.2, "кг"), (r"гарнир|картош", "Гарнира", 0.2, "кг"),
          (r"хлеб|лаваш", "Хлеба", 0.1, "кг"), (r"фрукт", "Фруктов", 0.25, "кг"),
          (r"напит|сок|вод|лимонад|газировк", "Безалкогольных напитков", 1.0, "л"), (r"чипс|снек|закуск", "Закусок", 0.1, "кг")]


@ptool(CAT_FOOD, "Сколько еды и напитков на компанию", "сколько мяса на шашлык на 10 человек")
def party_food(text, low, s):
    m = re.search(r"на\s+(\d+)\s*(?:человек|чел|гост|персон|взросл)", low)
    if not m or not re.search(r"сколько|скольк|рассчита", low) or re.search(r"сч[её]т|чаев|скидк", low):
        return None
    n = int(m.group(1))
    if n < 1 or n > 10000:
        return None
    items = [row for row in _PARTY if re.search(row[0], low)]
    if not items:
        return None
    lines = []
    for _, name, per, unit in items:
        total = per * n
        lines.append(f"- {name}: **{_r(math.ceil(total) if unit == 'шт.' else total, 1)} {unit}** ({num(per)} {unit} на человека)")
    return f"На {n} {_plural(n, 'человека', 'человек', 'человек')}:\n\n" + "\n".join(lines) + "\n\nЕсли еды много разной — каждой позиции можно на 20–30% меньше."


# ================================================================ УЧЁБА
CAT_EDU = "Учёба"


@ptool(CAT_EDU, "Оценка по баллам или проценту", "оценка за 17 из 20")
def grade(text, low, s):
    m = re.search(r"(?:оценк\w*|отметк\w*)\s+(?:за\s+)?(\d+)\s+(?:из|балл\w*\s+из)\s+(\d+)|(\d+)\s+(?:балл\w*\s+)?из\s+(\d+)\D{0,30}(?:оценк|отметк)", low)
    if not m:
        return None
    a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
    if not b or a > b:
        return None
    pct = a / b * 100
    g = 5 if pct >= 85 else 4 if pct >= 65 else 3 if pct >= 45 else 2
    return (f"{a} из {b} = **{_r(pct, 1)}%** → оценка **«{g}»** по частой школьной шкале "
            "(85% — «5», 65% — «4», 45% — «3»).\n\nУ разных учителей и экзаменов шкалы отличаются.")


@ptool(CAT_EDU, "Сколько пятёрок нужно для нужной оценки", "сколько пятерок нужно чтобы вышла 5 если оценки 4 4 5 3")
def need_grades(text, low, s):
    if not re.search(r"сколько\s+(?:нужно\s+|надо\s+)?(?:пятерок|пятерки|четверок|четверки)|чтобы\s+(?:вышла|выйти|вышло|была|получилась)\s+(?:5|4|пятерка|четверка|пять|четыре)", low):
        return None
    gm = re.search(r"(?:оценк\w*|отметк\w*|сейчас|есть|у\s+меня)\s*:?\s*((?:[2-5][\s,]+)+[2-5])", low)
    if not gm:
        return None
    grades = [int(x) for x in re.findall(r"[2-5]", gm.group(1))]
    target = 4 if re.search(r"вышла\s+4|вышло\s+4|четверк|четыре", low) and not re.search(r"пятерок|пятерки", low.split("чтобы")[-1] if "чтобы" in low else "") else 5
    if re.search(r"(?:вышла|выйти|была|получилась)\s+(?:4|четверка|четыре)", low):
        target = 4
    elif re.search(r"(?:вышла|выйти|была|получилась)\s+(?:5|пятерка|пять)", low):
        target = 5
    add = 4 if re.search(r"четверок|четверки", low) else 5
    thr = target - 0.5
    avg = sum(grades) / len(grades)
    if avg >= thr:
        return f"Сейчас средний балл {_r(avg, 2)} — уже выходит «{target}» (нужно от {num(thr)})."
    if add <= thr:
        return f"Оценками «{add}» до «{target}» не дотянуть: нужен средний балл от {num(thr)}."
    k = math.ceil((thr * len(grades) - sum(grades)) / (add - thr) - 1e-9)
    return (f"Сейчас средний балл **{_r(avg, 2)}** ({len(grades)} {_plural(len(grades), 'оценка', 'оценки', 'оценок')}). Чтобы вышла «{target}» (средний от {num(thr)}), "
            f"нужно ещё **{k} {_plural(k, 'оценка', 'оценки', 'оценок')} «{add}»** подряд.")


@ptool(CAT_EDU, "Скорость печати", "скорость печати 300 знаков за 2 минуты")
def typing_speed(text, low, s):
    if not re.search(r"скорост\w*\s+(?:печати|набора)|знаков\s+в\s+минуту|слов\s+в\s+минуту", low):
        return None
    cm = re.search(r"(\d+)\s*(?:знак|символ|удар)", low)
    wm = re.search(r"(\d+)\s*слов", low)
    tm = re.search(r"за\s+(" + NUM + r")\s*(мин|сек)", low)
    if not tm or not (cm or wm):
        return None
    mins = f(tm.group(1)) / (60 if tm.group(2) == "сек" else 1)
    if mins <= 0:
        return None
    cpm = int(cm.group(1)) / mins if cm else int(wm.group(1)) * 6 / mins
    level = "новичок" if cpm < 100 else "средний уровень" if cpm < 200 else "хорошо" if cpm < 300 else "профессионал"
    return f"Скорость: **{num(round(cpm))} знаков/мин** (≈ {num(round(cpm / 6))} слов/мин) — {level}."


@ptool(CAT_EDU, "Средний балл в GPA и обратно", "перевести средний балл 4,5 в gpa")
def gpa(text, low, s):
    if not re.search(r"\bgpa\b", low):
        return None
    xs = [x for x in nums(low) if 0 <= x <= 5]
    if not xs:
        return None
    x = xs[0]
    if re.search(r"gpa\s+" + NUM.replace("-?", "") + r"\s+в\s+(?:пяти|5)", low) or re.search(r"из\s+gpa|gpa\s+в\s+(?:пятибалльн|оценк)", low):
        return f"GPA {num(x)} ≈ **{_r(x + 1 if x >= 2 else x / 2 + 2, 2)}** по пятибалльной шкале (примерно)."
    g = x - 1 if x >= 3 else max((x - 2) * 2, 0)
    return f"Средний балл {num(x)} ≈ **GPA {_r(g, 2)}** из 4,0 (примерно: 5 → 4,0, 4 → 3,0, 3 → 2,0). Точный пересчёт задаёт вуз."


@ptool(CAT_EDU, "Сколько страниц в тексте", "сколько страниц 10000 знаков")
def pages(text, low, s):
    if not re.search(r"сколько\s+(?:это\s+)?(?:страниц|листов)|(?:знаков|символов|слов)\s+(?:это\s+)?сколько\s+(?:листов|страниц)|авторск\w*\s+лист", low):
        return None
    m = re.search(r"(\d[\d\s]*)\s*(знак|символ|слов)", low)
    if not m:
        return None
    n = int(m.group(1).replace(" ", ""))
    chars = n * 7 if m.group(2) == "слов" else n
    word = {"знак": ("знак", "знака", "знаков"), "символ": ("символ", "символа", "символов"), "слов": ("слово", "слова", "слов")}[m.group(2)]
    return (f"{num(n)} {_plural(n, *word)}: ≈ **{_r(chars / 1800, 1)} стр.** A4 (14 пт, 1,5 интервал) или "
            f"{_r(chars / 3000, 1)} стр. (12 пт, одинарный)\n\nАвторских листов: {_r(chars / 40000, 2)} (1 а.л. = 40 000 знаков).")


# ================================================================ РАЗВЛЕЧЕНИЯ И ГЕНЕРАТОРЫ
CAT_FUN = "Развлечения и генераторы"

_PETS = [(r"кош|кис", ["Мурка", "Муся", "Багира", "Алиса", "Маруся", "Белла", "Ника", "Соня", "Ириска", "Луна", "Симба", "Пуша"]),
         (r"кот|котенк|котик", ["Барсик", "Мурзик", "Тимофей", "Васька", "Персик", "Симба", "Лео", "Мартин", "Кекс", "Феликс", "Граф", "Тигра"]),
         (r"собак|пес|пса|щен", ["Рекс", "Бим", "Лаки", "Джек", "Граф", "Тайсон", "Марс", "Бади", "Лора", "Белка", "Найда", "Чара"]),
         (r"хомяк|хомячк", ["Пушок", "Бублик", "Хрум", "Орешек", "Пончик", "Ириска", "Шустрик", "Хома"]),
         (r"попуга", ["Кеша", "Гоша", "Рио", "Чика", "Кузя", "Ара", "Сенька", "Пико"]),
         (r"рыбк|рыб", ["Немо", "Дори", "Золотце", "Пузырь", "Блеск", "Аква", "Капитан", "Жемчужина"]),
         (r"кролик|крольчих", ["Банни", "Пуш", "Ушастик", "Снежок", "Кроша", "Морковка", "Тедди", "Зефир"]),
         (r"черепах", ["Тортила", "Шелли", "Флеш", "Кама", "Донателло", "Леонардо", "Тихоня", "Панцирь"])]


@ptool(CAT_FUN, "Кличка для питомца", "придумай кличку для кота", invent=True)
def pet_name(text, low, s):
    if not re.search(r"кличк|(?:имя|назвать)\s+(?:для\s+)?(?:моего\s+|моей\s+|нашего\s+|нашей\s+)?(?:кот|кош|собак|пс|щен|хомяк|попуга|рыбк|кролик|черепах|питомц)", low):
        return None
    names = next((ns for rx, ns in _PETS if re.search(rx, low)), _PETS[1][1] + _PETS[2][1])
    pick = random.sample(names, min(6, len(names)))
    return "Варианты клички: **" + "**, **".join(pick) + "**.\n\nНапишите ещё раз — предложу другие."


_BIZ = [(r"кофе", ["Зерно & Пар", "Бодрое утро", "Арабика Хаус", "Чашка счастья", "Кофейная станция", "Пенка", "Брю Лаб", "Тёплые руки"]),
        (r"пекар|выпеч|булоч", ["Тёплый хлеб", "Корочка", "Булки & Ко", "Хлебная лавка", "Мука и Мёд", "Круассан", "Печь", "Пышка"]),
        (r"цвет|флорист|букет", ["Пион", "Ботаника", "Цветочный ветер", "Флёр", "Букетная", "Сад на окне", "Лаванда", "Бутон"]),
        (r"барбер|парикмахер|салон\w*\s+красот", ["Бритва", "Острый стиль", "Борода и Ко", "Чистый срез", "Gentleman", "Ножницы", "Стрижка 24", "Лоск"]),
        (r"it|айти|разработ|программ|стартап|приложени", ["Кодрум", "Нейрон", "Bitwise", "Облако 9", "Квант", "Байтлаб", "Инфинити", "Вектор"]),
        (r"магазин\w*\s+одежд|одежд|бренд", ["Нить", "Шов", "Ткань", "Северный стиль", "Капсула", "Оверсайз", "Кроение", "Базис"]),
        (r"кафе|ресторан|бистро|столов", ["Вкусный двор", "Тарелка", "Огонёк", "Казан", "Сытый гость", "Пряность", "Ложка", "Кухня на углу"]),
        (r"канал|блог|ютуб|youtube|тикток|подкаст", ["Просто о сложном", "Голова в облаках", "Минутка знаний", "Вечерний разговор", "Без фильтров", "Точка зрения", "На волне", "Лайфхак ТВ"])]
_BIZ_A = ["Нова", "Альфа", "Вектор", "Грань", "Эра", "Сфера", "Импульс", "Орбита", "Лайт", "Мост"]
_BIZ_B = ["Групп", "Лаб", "Про", "Плюс", "Сити", "Тек", "Хаб", "Point", "Studio", "Маркет"]


@ptool(CAT_FUN, "Название для бизнеса, канала или проекта", "придумай название для кофейни", invent=True)
def biz_name(text, low, s):
    if not re.search(r"(?:придума|предлож|подбер|нужно)\w*\s+(?:\d+\s+)?(?:\w+\s+)?(?:название|имя|нейминг)\s+(?:для\s+)?(?:моей\s+|моего\s+|нашей\s+|нашего\s+)?(?:кофе|пекар|магазин|компан|бренд|кафе|ресторан|салон|барбер|студи|канал|блог|бизнес|стартап|приложени|групп|команд|проект|цвет|флорист|it|айти|подкаст|ютуб|бистро|выпеч|одежд)", low):
        return None
    names = next((ns for rx, ns in _BIZ if re.search(rx, low)), None)
    if names is None:
        names = [a + b for a in random.sample(_BIZ_A, 4) for b in random.sample(_BIZ_B, 2)]
    pick = random.sample(names, min(6, len(names)))
    return ("Варианты названия:\n\n" + "\n".join(f"- **{n}**" for n in pick) +
            "\n\nПеред запуском проверьте, что название не занято (поиск, домен, товарные знаки).")


_COUNTRIES = [("Россия", "Москва", "RU"), ("Беларусь", "Минск", "BY"), ("Казахстан", "Астана", "KZ"), ("Армения", "Ереван", "AM"),
              ("Грузия", "Тбилиси", "GE"), ("Узбекистан", "Ташкент", "UZ"), ("Финляндия", "Хельсинки", "FI"), ("Швеция", "Стокгольм", "SE"),
              ("Норвегия", "Осло", "NO"), ("Дания", "Копенгаген", "DK"), ("Германия", "Берлин", "DE"), ("Франция", "Париж", "FR"),
              ("Италия", "Рим", "IT"), ("Испания", "Мадрид", "ES"), ("Португалия", "Лиссабон", "PT"), ("Великобритания", "Лондон", "GB"),
              ("Ирландия", "Дублин", "IE"), ("Нидерланды", "Амстердам", "NL"), ("Швейцария", "Берн", "CH"), ("Австрия", "Вена", "AT"),
              ("Польша", "Варшава", "PL"), ("Чехия", "Прага", "CZ"), ("Венгрия", "Будапешт", "HU"), ("Греция", "Афины", "GR"),
              ("Турция", "Анкара", "TR"), ("Египет", "Каир", "EG"), ("Марокко", "Рабат", "MA"), ("Кения", "Найроби", "KE"),
              ("Китай", "Пекин", "CN"), ("Япония", "Токио", "JP"), ("Южная Корея", "Сеул", "KR"), ("Индия", "Нью-Дели", "IN"),
              ("Таиланд", "Бангкок", "TH"), ("Вьетнам", "Ханой", "VN"), ("Индонезия", "Джакарта", "ID"), ("Австралия", "Канберра", "AU"),
              ("Новая Зеландия", "Веллингтон", "NZ"), ("США", "Вашингтон", "US"), ("Канада", "Оттава", "CA"), ("Мексика", "Мехико", "MX"),
              ("Бразилия", "Бразилиа", "BR"), ("Аргентина", "Буэнос-Айрес", "AR"), ("Чили", "Сантьяго", "CL"), ("Перу", "Лима", "PE"),
              ("Куба", "Гавана", "CU"), ("ОАЭ", "Абу-Даби", "AE"), ("Монголия", "Улан-Батор", "MN"), ("Исландия", "Рейкьявик", "IS")]


@ptool(CAT_FUN, "Случайная страна", "случайная страна")
def random_country(text, low, s):
    if not re.search(r"случайн\w*\s+(?:страна|страну|страны|государств)|выбери\s+(?:мне\s+)?(?:случайную\s+)?страну|куда\s+(?:бы\s+)?(?:поехать|съездить)\s+наугад", low):
        return None
    name, cap, iso = random.choice(_COUNTRIES)
    flag = "".join(chr(0x1F1E6 + ord(c) - 65) for c in iso)
    return f"{flag} **{name}** — столица {cap}.\n\nНапишите ещё раз, чтобы выпала другая."


_TAROT = [("Шут", "новое начало, спонтанность, свобода"), ("Маг", "воля, мастерство, сила намерения"),
          ("Верховная Жрица", "интуиция, тайна, внутренний голос"), ("Императрица", "изобилие, забота, творчество"),
          ("Император", "порядок, структура, ответственность"), ("Иерофант", "традиции, учёба, наставник"),
          ("Влюблённые", "выбор, гармония, отношения"), ("Колесница", "движение вперёд, победа, контроль"),
          ("Сила", "мягкая сила, терпение, смелость"), ("Отшельник", "поиск себя, уединение, мудрость"),
          ("Колесо Фортуны", "перемены, удача, циклы"), ("Справедливость", "честность, баланс, последствия"),
          ("Повешенный", "пауза, новый взгляд, отпустить"), ("Смерть", "конец этапа и начало нового"),
          ("Умеренность", "баланс, спокойствие, мера"), ("Дьявол", "соблазны, привычки, зависимость"),
          ("Башня", "внезапные перемены, освобождение"), ("Звезда", "надежда, вдохновение, исцеление"),
          ("Луна", "сомнения, иллюзии, интуиция"), ("Солнце", "радость, успех, ясность"),
          ("Суд", "переосмысление, пробуждение, итоги"), ("Мир", "завершение, целостность, достижение")]


@ptool(CAT_FUN, "Карта таро дня (для развлечения)", "вытяни карту таро")
def tarot(text, low, s):
    if not re.search(r"таро|вытяни\s+(?:мне\s+)?карт", low):
        return None
    name, meaning = random.choice(_TAROT)
    rev = random.random() < 0.25
    return (f"🃏 **{name}**" + (" (перевёрнутая)" if rev else "") + f" — {meaning}" + (", но с препятствиями" if rev else "") +
            ".\n\nЭто развлечение, а не предсказание: решения принимайте сами 🙂")


_DINNER = ["паста карбонара", "гречка с курицей и грибами", "плов", "запечённая рыба с овощами", "омлет с сыром и помидорами",
           "домашняя пицца на лаваше", "куриные котлеты с пюре", "суп-лапша", "рис с овощами и яйцом (как в Азии)",
           "шакшука", "тушёная капуста с колбасками", "сырники", "салат «Цезарь»", "тефтели в томатном соусе",
           "овощное рагу", "блины с начинкой", "фаршированные перцы", "куриные крылышки в духовке", "лагман", "драники"]


@ptool(CAT_FUN, "Что приготовить: идеи блюд", "что приготовить на ужин")
def dinner_idea(text, low, s):
    if not re.search(r"что\s+(?:бы\s+)?(?:приготовить|сварить|поесть|съесть)\s*(?:на\s+(?:ужин|обед|завтрак|перекус))?\s*[?!.]*$|идеи?\s+(?:для\s+)?(?:ужина|обеда|завтрака)", low):
        return None
    pick = random.sample(_DINNER, 4)
    return "Идеи:\n\n" + "\n".join(f"- {p[0].upper() + p[1:]}" for p in pick) + "\n\nНапишите «рецепт <блюдо>», если нужен рецепт."


_EMOJI = {"кот": "🐱", "кошк": "🐈", "собак": "🐶", "пес": "🐕", "сердц": "❤️", "любов": "❤️", "огон": "🔥", "солнц": "☀️",
          "лун": "🌙", "звезд": "⭐", "дожд": "🌧️", "снег": "❄️", "радуг": "🌈", "цвет": "🌸", "роз": "🌹", "дерев": "🌳",
          "ракет": "🚀", "машин": "🚗", "самолет": "✈️", "поезд": "🚆", "дом": "🏠", "деньг": "💰", "подар": "🎁", "праздн": "🎉",
          "торт": "🎂", "пицц": "🍕", "кофе": "☕", "чай": "🍵", "пив": "🍺", "яблок": "🍎", "банан": "🍌", "мяч": "⚽",
          "музык": "🎵", "книг": "📚", "компьютер": "💻", "телефон": "📱", "смех": "😂", "радост": "😄", "груст": "😢",
          "злост": "😡", "страх": "😱", "думат": "🤔", "сон": "😴", "спорт": "🏋️", "игр": "🎮", "школ": "🏫", "работ": "💼",
          "врем": "⏰", "мир": "🌍", "земл": "🌍", "мор": "🌊", "гор": "⛰️", "лес": "🌲", "пчел": "🐝", "бабочк": "🦋",
          "рыб": "🐟", "птиц": "🐦", "единорог": "🦄", "дракон": "🐉", "приве": "👋", "ок": "👌", "класс": "👍", "сил": "💪",
          "идея": "💡", "успех": "🏆", "побед": "🏆", "учеб": "🎓", "здоров": "💚", "ии": "🤖", "робот": "🤖", "космос": "🌌"}


@ptool(CAT_FUN, "Эмодзи для слова", "эмодзи для слова кот")
def emoji(text, low, s):
    m = re.search(r"(?:эмодзи|эмоджи|смайл\w*|emoji)\s+(?:для\s+)?(?:слова\s+)?[«\"]?([а-я]+)", low)
    if not m:
        return None
    w = m.group(1)
    hits = [e for stem, e in _EMOJI.items() if w.startswith(stem) or (len(w) > 3 and stem.startswith(w[:4]))]
    if not hits:
        return None
    return f"{w}: " + " ".join(dict.fromkeys(hits))


@ptool(CAT_FUN, "Счастливый ли билет", "билет 123321 счастливый?")
def lucky_ticket(text, low, s):
    if not re.search(r"счастлив", low) or not re.search(r"билет", low):
        return None
    m = re.search(r"(?<!\d)(\d{6})(?!\d)", low)
    if not m:
        return None
    d = [int(c) for c in m.group(1)]
    a, b = sum(d[:3]), sum(d[3:])
    piter = sum(d[0::2]) == sum(d[1::2])
    return (f"Билет {m.group(1)}: {d[0]}+{d[1]}+{d[2]} = {a}, {d[3]}+{d[4]}+{d[5]} = {b} → "
            + ("**🎉 счастливый (московский)!** Говорят, его надо съесть 🙂" if a == b else "**не счастливый** по-московски")
            + (" Зато счастливый по-питерски (суммы чётных и нечётных позиций равны)." if piter and a != b else ""))


@ptool(CAT_FUN, "Число судьбы (нумерология, для развлечения)", "число судьбы 12.03.1995")
def destiny(text, low, s):
    if not re.search(r"числ\w*\s+(?:судьбы|жизненного\s+пути)|нумерологи", low):
        return None
    ds = _dates(low)
    if not ds:
        return None
    n = sum(int(c) for c in ds[0].strftime("%d%m%Y"))
    while n > 9 and n not in (11, 22):
        n = sum(int(c) for c in str(n))
    meaning = {1: "лидер, самостоятельность", 2: "дипломат, партнёрство", 3: "творчество, общение", 4: "надёжность, порядок",
               5: "свобода, перемены", 6: "забота, семья", 7: "мудрость, поиск истины", 8: "успех, сила, деньги",
               9: "гуманизм, щедрость", 11: "интуиция, вдохновение", 22: "мастер-строитель, большие цели"}[n]
    return f"Число судьбы для {_say(ds[0])}: **{n}** — {meaning}.\n\nНумерология — развлечение, научных подтверждений у неё нет."


_ACTIVITIES = ["выйти на прогулку и сфотографировать 5 интересных деталей", "приготовить блюдо, которое никогда не пробовали",
               "посмотреть документальный фильм о космосе", "собрать пазл или сыграть в настольную игру", "написать письмо себе в будущее",
               "начать учить 10 слов на новом языке", "устроить уборку под любимую музыку", "нарисовать что-нибудь, даже если «не умеете»",
               "сделать 20-минутную тренировку", "позвонить старому другу", "посадить растение", "научиться новому трюку с кубиком Рубика",
               "прочитать 30 страниц книги", "сходить в музей или на выставку", "сделать плейлист на настроение",
               "попробовать медитацию 10 минут", "собрать модель в Rai: «сделай 3д модель …»", "написать короткий рассказ"]


@ptool(CAT_FUN, "Идея, чем заняться", "идея чем заняться", early=True)
def activity_idea(text, low, s):
    if not re.search(r"(?:идея|идеи|подскажи|посоветуй|придумай)\s+(?:мне\s+)?(?:чем\s+заняться|занятие|что\s+(?:мне\s+)?(?:поделать|сделать\s+сегодня))", low):
        return None
    pick = random.sample(_ACTIVITIES, 3)
    return "Чем заняться:\n\n" + "\n".join(f"- {p[0].upper() + p[1:]}" for p in pick)


_CROC = ["самолёт", "жираф", "зубная щётка", "фотограф", "радуга", "пылесос", "космонавт", "балерина", "светофор", "крокодил",
         "снеговик", "барабан", "вратарь", "гамак", "лифт", "водопад", "дирижёр", "пингвин", "компас", "акробат", "кенгуру",
         "микроволновка", "телескоп", "ниндзя", "сёрфинг", "пожарный", "вертолёт", "маятник", "фокусник", "медуза", "робот",
         "ёжик", "скрипка", "палатка", "парашют", "библиотекарь", "селфи", "мыльный пузырь", "дракон", "пчела"]


@ptool(CAT_FUN, "Слово для игры «Крокодил» или «Шляпа»", "слово для крокодила")
def crocodile(text, low, s):
    if not re.search(r"слов\w*\s+для\s+(?:игры\s+)?(?:в\s+)?(?:крокодил|шляп|алиас|alias)|загадай\s+слово\s+для|крокодил\w*\s+слово", low):
        return None
    k = [x for x in ints(low) if 1 < x <= 20]
    n = k[0] if k else 1
    pick = random.sample(_CROC, n)
    return "Слово: **" + "**, **".join(pick) + "**\n\nПоказывайте без слов и звуков 🙂"


_TRUTH = ["Какой самый смешной случай был у тебя в школе?", "Чего ты боялся в детстве?", "Какую суперсилу ты бы выбрал?",
          "Какая песня у тебя сейчас на повторе?", "Какое твоё самое странное увлечение?", "О чём ты мечтаешь в этом году?",
          "Какую еду ты ни за что не стал бы есть?", "Кем ты хотел стать в детстве?"]
_DARE = ["Изобрази любое животное 30 секунд", "Расскажи стишок с выражением", "Сделай 10 приседаний", "Скажи скороговорку 3 раза быстро",
         "Говори следующие 2 минуты как робот", "Нарисуй портрет соседа за 30 секунд", "Спой припев любой песни", "Станцуй 15 секунд без музыки"]


@ptool(CAT_FUN, "Правда или действие", "правда или действие")
def truth_or_dare(text, low, s):
    if not re.search(r"правда\s+или\s+действие", low):
        return None
    if re.search(r"(?<![а-я])действие\s*$|^действие", low.replace("правда или действие", "").strip()):
        return f"💥 **Действие:** {random.choice(_DARE)}"
    return f"🤔 **Правда:** {random.choice(_TRUTH)}\n\n💥 **Действие:** {random.choice(_DARE)}\n\nВыбирайте!"


_FORTUNE = ["Сегодня стоит начать то, что давно откладывали.", "Хорошая новость придёт оттуда, откуда не ждёте.",
            "Маленький шаг сегодня — большой результат через месяц.", "Улыбнитесь незнакомцу — день станет лучше.",
            "Ваша идея лучше, чем кажется. Попробуйте.", "Скоро вы узнаете что-то, что вас вдохновит.",
            "Не бойтесь спросить — ответ вас порадует.", "Сегодня удачный день, чтобы научиться новому.",
            "Терпение принесёт плоды раньше, чем вы думаете.", "Кто-то рядом очень ценит вашу помощь."]


@ptool(CAT_FUN, "Предсказание на день (печенье с предсказанием)", "предсказание на сегодня", before="Магический шар")
def fortune(text, low, s):
    if not re.search(r"предсказани|печень\w*\s+с\s+предсказ|что\s+меня\s+ждет\s+(?:сегодня|завтра)", low) or re.search(r"погод|курс|матч|выбор|акци", low):
        return None
    return f"🥠 {random.choice(_FORTUNE)}"


_SYL_A = ["Ар", "Эл", "Тал", "Мир", "Сил", "Кай", "Рон", "Лис", "Вал", "Дор", "Эр", "Ил", "Фе", "Гал", "Тор", "Ур"]
_SYL_B = ["ан", "ве", "ри", "до", "ла", "ми", "ор", "эн", "ис", "ар", "ин", "ал"]
_END = {"эльф": ["эль", "ион", "иэль", "ас", "андриэль"], "орк": ["ак", "грох", "муг", "тар", "заг"], "гном": ["ин", "бур", "дин", "грим", "ок"],
        "маг": ["иус", "ар", "орн", "ель", "иан"], "дракон": ["акс", "оргон", "ракс", "атор", "ирис"]}


@ptool(CAT_FUN, "Имя для персонажа (фэнтези)", "придумай имя для персонажа эльфа", invent=True)
def fantasy_name(text, low, s):
    if not re.search(r"(?:имя|имена)\s+(?:для\s+)?(?:моего\s+)?(?:персонаж|героя|героини|эльф|орк|гном|мага|дракон|рыцар|фэнтези)", low):
        return None
    race = next((r for r in _END if r in low), None)
    ends = _END.get(race, sum(_END.values(), []))
    out = {random.choice(_SYL_A) + random.choice(_SYL_B) + random.choice(ends) for _ in range(12)}
    return ("Имена" + (f" для расы «{race}»" if race else "") + ": **" + "**, **".join(sorted(out)[:6]) + "**")


# ================================================================ КОНВЕРТЕРЫ+
CAT_C = "Конвертеры+"


@ptool(CAT_C, "Расход топлива: л/100 км ↔ mpg", "8 л/100км в mpg", early=True)
def mpg(text, low, s):
    m = re.search(r"(" + NUM + r")\s*(?:л|литр\w*)\s*(?:/|на)\s*100\s*км\w*\s+в\s+(?:mpg|мил)", low)
    if m:
        x = f(m.group(1))
        return f"{num(x)} л/100 км = **{_r(235.215 / x, 1)} mpg (США)** = {_r(282.481 / x, 1)} mpg (Великобритания)"
    m = re.search(r"(" + NUM + r")\s*mpg\s+в\s+(?:л|литр)", low)
    if m:
        x = f(m.group(1))
        return f"{num(x)} mpg (США) = **{_r(235.215 / x, 2)} л/100 км** (если mpg британские — {_r(282.481 / x, 2)} л/100 км)"
    return None


@ptool(CAT_C, "Типографские пункты, пиксели и em", "12 pt в px", early=True)
def pt_px(text, low, s):
    m = re.search(r"(" + NUM + r")\s*(pt|пт|пункт\w*|px|пикс\w*|em|rem)\s+в\s+(pt|пт|пункт\w*|px|пикс\w*|em|rem)", low)
    if not m:
        return None
    x, a, b = f(m.group(1)), m.group(2), m.group(3)
    to_px = {"pt": 96 / 72, "пт": 96 / 72, "px": 1, "em": 16, "rem": 16}
    ka = to_px.get(a, 96 / 72 if a.startswith("пункт") else 1)
    kb = to_px.get(b, 96 / 72 if b.startswith("пункт") else 1)
    res = x * ka / kb
    return f"{num(x)} {a} = **{_r(res, 3)} {b}** (1 pt = 1,333 px при 96 DPI; 1 em = 16 px по умолчанию)"


_SHOES = [(35, 2.5, 3.5, 5, 22.5), (36, 3.5, 4.5, 6, 23), (37, 4, 5, 6.5, 23.5), (38, 5, 6, 7.5, 24), (39, 6, 7, 8.5, 25),
          (40, 6.5, 7.5, 9, 25.5), (41, 7, 8, 9.5, 26), (42, 8, 9, 10.5, 27), (43, 9, 10, 11.5, 27.5), (44, 9.5, 10.5, 12, 28),
          (45, 10.5, 11.5, 13, 29), (46, 11, 12, 13.5, 29.5), (47, 12, 13, 14.5, 30.5)]


@ptool(CAT_C, "Размер обуви: EU, UK, US, см", "размер обуви 42 в американский")
def shoe_size(text, low, s):
    if not re.search(r"размер\w*\s+(?:обуви|ноги|кроссовок|ботинок|туфель|стопы)|обувн\w*\s+размер", low):
        return None
    k = [x for x in nums(low) if 30 <= x <= 50]
    if not k:
        return None
    eu = round(k[0])
    row = next((r for r in _SHOES if r[0] == eu), None)
    if not row:
        return None
    return (f"EU {row[0]}:\n\n| Система | Размер |\n|---|---|\n| UK | {num(row[1])} |\n| US мужской | {num(row[2])} |\n"
            f"| US женский | {num(row[3])} |\n| Длина стопы | ≈ {num(row[4])} см |\n| Российский | ≈ {row[0] - 1} |\n\n"
            "Российский размер обычно на 1 меньше европейского. Надёжнее всего — мерить длину стопы.")


_CLOTHES_W = {40: "XXS", 42: "XS", 44: "S", 46: "M", 48: "L", 50: "XL", 52: "XXL", 54: "3XL", 56: "4XL"}
_CLOTHES_M = {44: "XS", 46: "S", 48: "M", 50: "L", 52: "XL", 54: "XXL", 56: "3XL", 58: "4XL", 60: "5XL"}


@ptool(CAT_C, "Размер одежды: российский ↔ международный", "размер одежды 48 мужской в международный")
def clothes_size(text, low, s):
    if not re.search(r"размер\w*\s+(?:одежд|футболк|рубашк|куртк|плать|брюк|джинс|костюм)", low):
        return None
    k = [int(x) for x in nums(low) if 38 <= x <= 62 and int(x) % 2 == 0]
    if not k:
        m = re.search(r"\b(xxs|xs|s|m|l|xl|xxl|3xl|4xl)\b", low)
        if not m:
            return None
        sz = m.group(1).upper()
        w = [r for r, v in _CLOTHES_W.items() if v == sz]
        mm = [r for r, v in _CLOTHES_M.items() if v == sz]
        return f"{sz}: женский российский **{w[0] if w else '—'}**, мужской российский **{mm[0] if mm else '—'}**."
    ru = k[0]
    female = bool(re.search(r"женск|жен\b|девочк|девушк|плать", low))
    male = bool(re.search(r"мужск|муж\b|мальчик|парн", low))
    rows = []
    if not male:
        rows.append(f"- женский RU {ru} = **{_CLOTHES_W.get(ru, '—')}** (EU {ru - 6})")
    if not female:
        rows.append(f"- мужской RU {ru} = **{_CLOTHES_M.get(ru, '—')}** (EU {ru})")
    return "\n".join(rows) + "\n\nУ разных брендов сетки отличаются — смотрите таблицу на сайте магазина."


_BEAUFORT = [(0.3, 0, "штиль"), (1.6, 1, "тихий"), (3.4, 2, "лёгкий"), (5.5, 3, "слабый"), (8.0, 4, "умеренный"), (10.8, 5, "свежий"),
             (13.9, 6, "сильный"), (17.2, 7, "крепкий"), (20.8, 8, "очень крепкий"), (24.5, 9, "шторм"), (28.5, 10, "сильный шторм"),
             (32.7, 11, "жестокий шторм"), (999, 12, "ураган")]


@ptool(CAT_C, "Сила ветра по шкале Бофорта", "ветер 15 м/с по бофорту")
def beaufort(text, low, s):
    if not re.search(r"бофорт|(?:сила|баллов|балла)\s+ветра|ветер\s+\d+\s*(?:м/с|км/ч)\s+это", low):
        return None
    m = re.search(r"(" + NUM + r")\s*(м/с|км/ч)", low)
    if not m:
        return None
    v = f(m.group(1)) / (3.6 if m.group(2) == "км/ч" else 1)
    top, b, name = next(r for r in _BEAUFORT if v < r[0])
    return f"Ветер {_r(v, 1)} м/с ({_r(v * 3.6, 0)} км/ч): **{b} баллов по Бофорту — {name}**."


@ptool(CAT_C, "24-часовой ↔ 12-часовой формат (AM/PM)", "15:30 в 12-часовой формат")
def time12(text, low, s):
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", low)
    if not m or not re.search(r"12[- ]?часов|24[- ]?часов|\bam\b|\bpm\b|двенадцатичасов|двадцатичетырехчасов", low):
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if h > 23 or mi > 59:
        return None
    if ap:
        h24 = (h % 12) + (12 if ap == "pm" else 0)
        return f"{h}:{mi:02d} {ap.upper()} = **{h24:02d}:{mi:02d}**"
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h:02d}:{mi:02d} = **{h12}:{mi:02d} {ap}**" + (" (полдень)" if h == 12 and mi == 0 else " (полночь)" if h == 0 and mi == 0 else "")


@ptool(CAT_C, "Скорость интернета: Мбит/с ↔ МБ/с", "100 мбит в мегабайты в секунду", early=True)
def net_speed(text, low, s):
    m = re.search(r"(" + NUM + r")\s*(мбит|mbps|мегабит\w*|гбит|gbps)\w*(?:/с)?\s+в\s+(?:мб|мегабайт|mb)", low)
    if m:
        x = f(m.group(1)) * (1000 if m.group(2) in ("гбит", "gbps") else 1)
        return f"{m.group(1)} {m.group(2)}/с = **{_r(x / 8, 2)} МБ/с** (1 байт = 8 бит). Файл 1 ГБ скачается ≈ за {_secs(1024 / (x / 8))}."
    m = re.search(r"(" + NUM + r")\s*(?:мб/с|mb/s|мегабайт\w*\s+в\s+секунду)\s+в\s+(?:мбит|мегабит|mbps)", low)
    if m:
        x = f(m.group(1))
        return f"{m.group(1)} МБ/с = **{_r(x * 8, 2)} Мбит/с**"
    return None


_OLD = [("верст", "верста", 1066.8, "м"), ("сажен", "сажень", 2.1336, "м"), ("аршин", "аршин", 0.7112, "м"), ("локт", "локоть", 0.4445, "м"),
        ("пяд", "пядь", 0.1778, "м"), ("вершк", "вершок", 0.04445, "м"), ("вершок", "вершок", 0.04445, "м"), ("пуд", "пуд", 16.38, "кг"),
        ("фунт", "фунт (русский)", 0.40951, "кг"), ("золотник", "золотник", 0.004266, "кг"), ("ведр", "ведро", 12.3, "л"),
        (r"миля\s+морск|морск\w*\s+мил", "морская миля", 1852, "м"), ("лиг", "лига (сухопутная)", 4828, "м"), ("ярд", "ярд", 0.9144, "м"),
        ("фут", "фут", 0.3048, "м"), ("дюйм", "дюйм", 0.0254, "м")]


@ptool(CAT_C, "Старинные меры: верста, аршин, пуд…", "сколько метров в версте")
def old_measures(text, low, s):
    if not re.search(r"верст|сажен|аршин|локт\w*\s|пяд|вершк|вершок|(?<![а-я])пуд|золотник|(?<![а-я])лиг[аеи]", low):
        return None
    item = next((o for o in _OLD if re.search(o[0], low)), None)
    if not item:
        return None
    _, name, val, unit = item
    k = [x for x in nums(low)]
    n = k[0] if k else 1
    shown = f"{_r(val * n, 4)} {unit}"
    if unit == "м" and val * n >= 1000:
        shown += f" ({_r(val * n / 1000, 4)} км)"
    if unit == "м" and val * n < 1:
        shown = f"{_r(val * n * 100, 3)} см"
    return f"{num(n)} × {name} = **{shown}**"
