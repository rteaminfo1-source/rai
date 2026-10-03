"""Сто с лишним точных функций Rai — без интернета и нейросети.

Математика, финансы, здоровье, время, текст и генераторы — здесь; справочник — facts.py, игры — games.py.
Каждая функция регистрируется декоратором @tool и получает (text, low, session); возвращает ответ или None.
Порядок регистрации = порядок проверки: узкие функции раньше общих.
"""

import base64
import binascii
import hashlib
import math
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction

import skills

TOOLS = []


def tool(cat, title, example):
    def deco(fn):
        TOOLS.append({"cat": cat, "title": title, "example": example, "fn": fn})
        return fn
    return deco


def find(text, session=None):
    """(ответ, раздел) первой сработавшей функции или (None, None)."""
    low = skills._low(text)
    for t in TOOLS:
        try:
            reply = t["fn"](text, low, session if session is not None else {})
        except (ValueError, ZeroDivisionError, OverflowError, ArithmeticError, IndexError, KeyError):
            reply = None
        if reply:
            return reply, t["cat"]
    return None, None


def run(text, session=None):
    """Ответ первой сработавшей функции или None."""
    return find(text, session)[0]


def catalog():
    """Список всех функций по разделам (для «все функции»)."""
    out, cats = [], {}
    for t in TOOLS:
        cats.setdefault(t["cat"], []).append(t)
    for cat, items in cats.items():
        out.append(f"### {cat} ({len(items)})\n" + "\n".join(f"- **{t['title']}** — «{t['example']}»" for t in items))
    return (f"## Мои функции: {len(TOOLS)}\n\nВсё работает сразу и без интернета — просто напишите, как в примере.\n\n"
            + "\n\n".join(out))


# ---------------------------------------------------------------- помощники
NUM = r"-?\d+(?:[.,]\d+)?"
num = skills._num  # 1 234,56


def f(s):
    return float(str(s).replace(",", ".").replace(" ", ""))


def nums(low):
    return [f(x) for x in re.findall(NUM, low)]


def ints(low):
    return [int(x) for x in re.findall(r"(?<![\d.,])\d+(?![.,]\d)", low)]


def money(x):
    """12345.6 → «12 345,60», 12000 → «12 000»."""
    x = round(x, 2)
    text = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return text[:-3] if text.endswith(",00") else text


def rub(x):
    return money(x) + " ₽"


def is_int(x):
    return abs(x - round(x)) < 1e-9


# ================================================================ МАТЕМАТИКА
CAT_MATH = "Математика"

_POW = str.maketrans({"²": "^2", "³": "^3", "×": "*", "·": "*", "−": "-", "–": "-", "÷": "/"})


def _poly_eval(expr, x):
    """Значение выражения с x (только числа, x, + - * / ^ и скобки)."""
    import ast
    node = ast.parse(expr, mode="eval")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return Fraction(n.value).limit_denominator(10 ** 9) if isinstance(n.value, float) else Fraction(n.value)
        if isinstance(n, ast.Name) and n.id == "x":
            return x
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
            if isinstance(n.op, ast.Pow) and b.denominator == 1 and 0 <= b <= 3:
                return a ** int(b)
        raise ValueError("bad")
    return ev(node)


def _fr(x):
    """Дробь красиво: 3, -1/2, √ не трогаем."""
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


@tool(CAT_MATH, "Уравнения (линейные и квадратные)", "реши уравнение x^2 - 5x + 6 = 0")
def equation(text, low, s):
    if not re.search(r"уравнени|реши|найди x|найди х|чему равен x", low) or "=" not in low:
        return None
    expr = low.translate(_POW)
    expr = re.sub(r"^.*?(?=[-\d(x]*x)", "", expr.replace("х", "x"), count=1) if "x" in expr.replace("х", "x") else ""
    expr = expr.replace("х", "x")
    if "x" not in expr or expr.count("=") != 1:
        return None
    left, right = expr.split("=")
    right = re.split(r"[^\dx+\-*/^().,\s]", right)[0]
    left = re.sub(r"[^\dx+\-*/^().,\s]", "", left)
    side = f"({left})-({right})".replace("^", "**").replace(",", ".")
    side = re.sub(r"(\d|\))\s*(x|\()", r"\1*\2", side)
    side = re.sub(r"x\s*\(", "x*(", side)
    vals = {k: _poly_eval(side, Fraction(k)) for k in (-1, 0, 1, 2, 3)}
    c = vals[0]
    b = (vals[1] - vals[-1]) / 2
    a = (vals[1] + vals[-1]) / 2 - c
    if any(abs(a * k * k + b * k + c - vals[k]) > Fraction(1, 10 ** 9) for k in (2, 3)):
        return None  # степень больше 2
    if a == 0:
        if b == 0:
            return "Уравнение верно при любом x." if c == 0 else "Решений нет: x сокращается, а равенство неверное."
        root = -c / b
        return f"**Линейное уравнение:** {_fr(b)}·x {'+' if c >= 0 else '−'} {_fr(abs(c))} = 0\n\nx = {_fr(-c)} / {_fr(b)}\n\n**Ответ: x = {_fr(root)}**" + (
            f" ≈ {num(round(float(root), 6))}" if root.denominator != 1 else "")
    d = b * b - 4 * a * c
    head = (f"**Квадратное уравнение:** a = {_fr(a)}, b = {_fr(b)}, c = {_fr(c)}\n\n"
            f"Дискриминант: D = b² − 4ac = {_fr(b * b)} {'−' if 4 * a * c >= 0 else '+'} {_fr(abs(4 * a * c))} = **{_fr(d)}**\n\n")
    if d < 0:
        re_, im = -b / (2 * a), math.sqrt(-float(d)) / (2 * float(a))
        return head + f"D < 0 — действительных корней нет.\n\nКомплексные: x = {num(round(float(re_), 6))} ± {num(round(abs(im), 6))}i"
    if d == 0:
        return head + f"D = 0 — один корень: x = −b / 2a\n\n**Ответ: x = {_fr(-b / (2 * a))}**"
    sq = math.isqrt(d.numerator) if d.denominator == 1 and math.isqrt(d.numerator) ** 2 == d.numerator else None
    if sq is not None:
        x1, x2 = (-b + sq) / (2 * a), (-b - sq) / (2 * a)
        return head + f"√D = {sq}\n\nx₁ = (−b + √D) / 2a = **{_fr(x1)}**\n\nx₂ = (−b − √D) / 2a = **{_fr(x2)}**\n\n**Ответ: x₁ = {_fr(x1)}, x₂ = {_fr(x2)}**"
    r = math.sqrt(float(d))
    x1, x2 = (-float(b) + r) / (2 * float(a)), (-float(b) - r) / (2 * float(a))
    return head + f"x = (−b ± √D) / 2a\n\n**Ответ: x₁ ≈ {num(round(x1, 6))}, x₂ ≈ {num(round(x2, 6))}**"


def _is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def _factors(n):
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


@tool(CAT_MATH, "Простое ли число", "97 простое число?")
def prime(text, low, s):
    m = re.search(r"(\d+)\D{0,25}прост|прост\w*\D{0,25}?(\d+)", low)
    if not m or re.search(r"множител|разлож|делител|до \d|первые", low):
        return None
    n = int(m.group(1) or m.group(2))
    if n > 10 ** 12:
        return None
    if _is_prime(n):
        return f"**{n} — простое число**: делится только на 1 и на себя."
    if n < 2:
        return f"{n} — не простое и не составное (простые числа начинаются с 2)."
    fs = _factors(n)
    return f"**{n} — составное число**: {n} = {' × '.join(map(str, fs))}. Наименьший делитель — {fs[0]}."


@tool(CAT_MATH, "Разложение на простые множители", "разложи 360 на множители")
def factorize(text, low, s):
    if not re.search(r"разлож|множител", low):
        return None
    n = ints(low)
    if not n or n[0] < 2 or n[0] > 10 ** 12:
        return None
    fs = _factors(n[0])
    grouped = {}
    for p in fs:
        grouped[p] = grouped.get(p, 0) + 1
    pretty = " · ".join(f"{p}^{k}" if k > 1 else str(p) for p, k in grouped.items())
    return f"**{n[0]} = {' × '.join(map(str, fs))}**" + (f"\n\nКороче: {pretty}" if any(k > 1 for k in grouped.values()) else "")


@tool(CAT_MATH, "Делители числа", "делители числа 36")
def divisors(text, low, s):
    if not re.search(r"делител", low) or re.search(r"общ|нод|наибольш", low):
        return None
    n = ints(low)
    if not n or n[0] < 1 or n[0] > 10 ** 10:
        return None
    n = n[0]
    small = [d for d in range(1, math.isqrt(n) + 1) if n % d == 0]
    alld = sorted(set(small + [n // d for d in small]))
    return f"**Делители {n}** ({len(alld)} шт.): {', '.join(map(str, alld))}\n\nСумма делителей: {sum(alld)}."


@tool(CAT_MATH, "НОД — наибольший общий делитель", "нод 48 и 180")
def gcd_(text, low, s):
    if not re.search(r"\bнод\b|наибольш\w* общ\w* делител|\bgcd\b", low):
        return None
    n = ints(low)
    if len(n) < 2:
        return None
    g = 0
    for x in n:
        g = math.gcd(g, x)
    return f"**НОД({', '.join(map(str, n))}) = {g}**"


@tool(CAT_MATH, "НОК — наименьшее общее кратное", "нок 4 и 6")
def lcm_(text, low, s):
    if not re.search(r"\bнок\b|наименьш\w* общ\w* кратн|\blcm\b", low):
        return None
    n = ints(low)
    if len(n) < 2 or 0 in n:
        return None
    l = 1
    for x in n:
        l = l * x // math.gcd(l, x)
    return f"**НОК({', '.join(map(str, n))}) = {l}**"


@tool(CAT_MATH, "Факториал", "факториал 10")
def factorial(text, low, s):
    m = re.search(r"факториал\w*\s*(?:числа\s*)?(\d+)|(\d+)\s*!", low)
    if not m:
        return None
    n = int(m.group(1) or m.group(2))
    if n > 1000:
        return "Слишком большое число: факториал больше 1000! займёт тысячи цифр."
    v = math.factorial(n)
    digits = len(str(v))
    shown = str(v) if digits <= 60 else str(v)[:30] + "…" + f" ({digits} цифр)"
    return f"**{n}! = {shown}**" + ("" if n > 12 else f"\n\n{n}! = " + (" × ".join(map(str, range(1, n + 1))) if n else "1 по определению"))


@tool(CAT_MATH, "Числа Фибоначчи", "15-е число фибоначчи")
def fibonacci(text, low, s):
    if "фибоначч" not in low:
        return None
    n = ints(low)
    seq = [0, 1]
    if re.search(r"\bдо\s+\d", low) and n:
        while seq[-1] + seq[-2] <= n[0] and len(seq) < 200:
            seq.append(seq[-1] + seq[-2])
        return f"**Числа Фибоначчи до {n[0]}:** {', '.join(map(str, seq))}"
    if n and n[0] <= 1000:
        k = n[0]
        a, b = 0, 1
        for _ in range(k):
            a, b = b, a + b
        return f"**{k}-е число Фибоначчи = {a}**\n\n(считаем с F₀ = 0, F₁ = 1; каждое число — сумма двух предыдущих)"
    while len(seq) < 20:
        seq.append(seq[-1] + seq[-2])
    return "**Первые 20 чисел Фибоначчи:** " + ", ".join(map(str, seq))


@tool(CAT_MATH, "Корень любой степени", "корень 3 степени из 27")
def nroot(text, low, s):
    m = (re.search(r"корень\s+(\d+)[\s-]*(?:й|ой|ей)?\s*степени\s+(?:из\s+)?(" + NUM + ")", low)
         or re.search(r"(кубическ)\w*\s+корень\s+(?:из\s+)?(" + NUM + ")", low))
    if not m:
        return None
    k = 3 if m.group(1).startswith("куб") else int(m.group(1))
    x = f(m.group(2))
    if k < 2:
        return None
    if x < 0 and k % 2 == 0:
        return "Корень чётной степени из отрицательного числа в действительных числах не существует."
    r = math.copysign(abs(x) ** (1 / k), x)
    if is_int(round(r, 9)) and round(round(r)) ** k == x:
        r = round(r)
    return f"**{'∛' if k == 3 else str(k) + '√'}{num(x)} = {num(round(r, 8))}**"


@tool(CAT_MATH, "Квадрат и куб числа", "15 в квадрате")
def square(text, low, s):
    m = re.search(r"(" + NUM + r")\s+в\s+(квадрате|кубе)|(квадрат|куб)\s+числа\s+(" + NUM + ")", low)
    if not m:
        return None
    x = f(m.group(1) or m.group(4))
    p = 2 if (m.group(2) or m.group(3)).startswith("квадрат") else 3
    return f"**{num(x)}{'²' if p == 2 else '³'} = {num(round(x ** p, 10))}**"


@tool(CAT_MATH, "Логарифмы", "логарифм 8 по основанию 2")
def logarithm(text, low, s):
    m = re.search(r"логарифм\w*\s+(?:числа\s+)?(" + NUM + r")\s+по\s+основани\w*\s+(" + NUM + ")", low)
    if m:
        x, b = f(m.group(1)), f(m.group(2))
    else:
        m = re.search(r"\blog\s*(\d+)\s*\(?\s*(" + NUM + r")|\b(ln|lg)\s*\(?\s*(" + NUM + r")|(натуральн|десятичн)\w*\s+логарифм\w*\s+(?:числа\s+)?(" + NUM + ")", low)
        if not m:
            return None
        if m.group(1):
            b, x = f(m.group(1)), f(m.group(2))
        elif m.group(3):
            b, x = (math.e if m.group(3) == "ln" else 10), f(m.group(4))
        else:
            b, x = (math.e if m.group(5).startswith("натур") else 10), f(m.group(6))
    if x <= 0 or b <= 0 or b == 1:
        return "Логарифм определён только для положительных чисел и основания больше 0 (не равного 1)."
    r = math.log(x) / math.log(b)
    name = "ln" if b == math.e else ("lg" if b == 10 else f"log₍{num(b)}₎")
    return f"**{name} {num(x)} = {num(round(r, 8))}**" + (f"\n\nПотому что {num(b)}^{num(round(r))} = {num(x)}" if is_int(round(r, 9)) and b != math.e else "")


@tool(CAT_MATH, "Синус, косинус, тангенс", "синус 30 градусов")
def trig(text, low, s):
    m = re.search(r"\b(синус|косинус|тангенс|котангенс|sin|cos|tg|tan|ctg|cot)\w*\s*\(?\s*(" + NUM + r")\s*(°|градус\w*|рад\w*)?", low)
    if not m:
        return None
    fn = {"синус": "sin", "косинус": "cos", "тангенс": "tg", "котангенс": "ctg", "tan": "tg", "cot": "ctg"}.get(m.group(1), m.group(1))
    v = f(m.group(2))
    rad = m.group(3) and m.group(3).startswith("рад")
    a = v if rad else math.radians(v)
    if fn in ("tg", "ctg") and not rad:
        if (fn == "tg" and v % 180 == 90) or (fn == "ctg" and v % 180 == 0):
            return f"{fn} {num(v)}° не существует (деление на ноль)."
    val = {"sin": math.sin, "cos": math.cos, "tg": math.tan, "ctg": lambda t: 1 / math.tan(t)}[fn](a)
    exact = {0.5: "1/2", -0.5: "−1/2", 0.866025: "√3/2", -0.866025: "−√3/2", 0.707107: "√2/2", -0.707107: "−√2/2",
             1.732051: "√3", -1.732051: "−√3", 0.57735: "√3/3", -0.57735: "−√3/3"}.get(round(val, 6))
    unit = " рад" if rad else "°"
    return f"**{fn} {num(v)}{unit} = {num(round(val, 6) + 0.0)}**" + (f" = {exact}" if exact else "")


_BASES = {"двоичн": 2, "троичн": 3, "четверичн": 4, "восьмеричн": 8, "десятичн": 10, "шестнадцатеричн": 16, "двенадцатеричн": 12}


def _base_of(word):
    for k, v in _BASES.items():
        if word.startswith(k):
            return v
    m = re.match(r"(\d+)", word)
    return int(m.group(1)) if m else None


def _to_base(n, b):
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        return "0"
    out, neg = "", n < 0
    n = abs(n)
    while n:
        out = digits[n % b] + out
        n //= b
    return "-" + out if neg else out


@tool(CAT_MATH, "Системы счисления", "переведи 255 в шестнадцатеричную")
def bases(text, low, s):
    if not re.search(r"двоичн|троичн|восьмеричн|шестнадцатеричн|десятичн|систем\w* счислени|основани\w* \d", low):
        return None
    m = re.search(r"([0-9a-f]+)\s*(?:из\s+(\w+)\s+)?(?:систем\w*\s+)?(?:в|во)\s+(\w+)", low)
    if not m:
        return None
    raw, src_w, dst_w = m.group(1), m.group(2), m.group(3)
    src = _base_of(src_w) if src_w else (16 if re.search(r"[a-f]", raw) else 10)
    dst = _base_of(dst_w) if dst_w else None
    if dst is None:
        mm = re.search(r"основани\w*\s+(\d+)", low)
        dst = int(mm.group(1)) if mm else None
    if not src or not dst or not (2 <= src <= 36 and 2 <= dst <= 36):
        return None
    value = int(raw, src)
    res = _to_base(value, dst)
    src_n = {2: "двоичной", 8: "восьмеричной", 10: "десятичной", 16: "шестнадцатеричной"}.get(src, f"{src}-ичной")
    dst_n = {2: "двоичную", 8: "восьмеричную", 10: "десятичную", 16: "шестнадцатеричную"}.get(dst, f"{dst}-ичную")
    return f"**{raw.upper()}₍{src}₎ = {res}₍{dst}₎**\n\nИз {src_n} в {dst_n} систему." + (
        f" В десятичной: {value}." if 10 not in (src, dst) else "")


_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
          (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n):
    out = ""
    for v, r in _ROMAN:
        while n >= v:
            out += r
            n -= v
    return out


def from_roman(r):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(r):
        v = vals[ch]
        total += -v if i + 1 < len(r) and vals[r[i + 1]] > v else v
    return total


@tool(CAT_MATH, "Римские цифры", "2026 римскими цифрами")
def roman(text, low, s):
    if not re.search(r"римск|арабск", low):
        return None
    m = re.search(r"\b([IVXLCDM]+)\b", text)
    if m and (re.search(r"арабск|переведи|что значит|сколько", low) or not re.search(r"\d", low)):
        r = m.group(1)
        v = from_roman(r)
        if to_roman(v) != r:
            return f"«{r}» — неправильная запись римского числа. Правильно было бы: {to_roman(v)} = {v}."
        return f"**{r} = {v}**"
    n = ints(low)
    if not n:
        return None
    if not 1 <= n[0] <= 3999:
        return "Римскими цифрами обычно записывают числа от 1 до 3999."
    return f"**{n[0]} = {to_roman(n[0])}**"


_ONES_M = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_ONES_F = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать",
          "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]
_SCALES = [("", "", "", False), ("тысяча", "тысячи", "тысяч", True), ("миллион", "миллиона", "миллионов", False),
           ("миллиард", "миллиарда", "миллиардов", False), ("триллион", "триллиона", "триллионов", False)]


def _triad(n, female):
    words = []
    words.append(_HUNDREDS[n // 100])
    t = n % 100
    if 10 <= t < 20:
        words.append(_TEENS[t - 10])
    else:
        words.append(_TENS[t // 10])
        words.append((_ONES_F if female else _ONES_M)[t % 10])
    return [w for w in words if w]


def words(n, female=False):
    """Число прописью: 1 234 → «одна тысяча двести тридцать четыре»."""
    if n == 0:
        return "ноль"
    if n < 0:
        return "минус " + words(-n, female)
    parts, i = [], 0
    while n and i < len(_SCALES):
        n, tri = divmod(n, 1000)
        if tri:
            one, few, many, fem = _SCALES[i]
            w = _triad(tri, fem if i else female)
            if i:
                w.append(skills.plural(tri, one, few, many))
            parts = w + parts
        i += 1
    return " ".join(parts)


@tool(CAT_MATH, "Сумма прописью (рубли и копейки)", "15250,50 рублей прописью")
def money_words(text, low, s):
    m = re.search(r"(\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:руб\w*|₽|р\.)\s*(?:\d+\s*коп\w*\s*)?прописью|прописью\s+(\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:руб|₽)", low)
    if not m:
        return None
    v = f((m.group(1) or m.group(2)).strip())
    r = int(v)
    k = int(round((v - r) * 100))
    if r >= 10 ** 15:
        return None
    w = words(r)
    return (f"**{money(v)} ₽** — {w[0].upper() + w[1:]} {skills.plural(r, 'рубль', 'рубля', 'рублей')} "
            f"{k:02d} {skills.plural(k, 'копейка', 'копейки', 'копеек')}")


@tool(CAT_MATH, "Число прописью", "123456 прописью")
def number_words(text, low, s):
    if not re.search(r"прописью|словами|буквами", low) or re.search(r"руб|₽", low):
        return None
    n = re.search(r"-?\d[\d\s]*", low)
    if not n:
        return None
    v = int(n.group(0).replace(" ", ""))
    if abs(v) >= 10 ** 15:
        return None
    w = words(v)
    return f"**{num(v)}** — {w}"


def _geom_nums(low):
    return [f(x) for x in re.findall(NUM, low)]


@tool(CAT_MATH, "Площадь и длина окружности круга", "площадь круга радиус 5")
def circle(text, low, s):
    if not re.search(r"круг|окружност", low) or not re.search(r"площад|длин", low):
        return None
    m = re.search(r"(радиус|диаметр)\w*\s*(?:=|равн\w*)?\s*(" + NUM + ")", low)
    if not m:
        return None
    r = f(m.group(2)) / (2 if m.group(1) == "диаметр" else 1)
    if "площад" in low:
        return f"**Площадь круга** S = πr² = π · {num(r)}² ≈ **{num(round(math.pi * r * r, 4))}**"
    return f"**Длина окружности** C = 2πr = 2π · {num(r)} ≈ **{num(round(2 * math.pi * r, 4))}**"


@tool(CAT_MATH, "Площадь и периметр прямоугольника и квадрата", "площадь прямоугольника 3 на 4")
def rectangle(text, low, s):
    m = re.search(r"(площад|периметр)\w*\s+(прямоугольник|квадрат)\w*", low)
    if not m:
        return None
    v = _geom_nums(low)
    if m.group(2) == "квадрат" and v:
        a = v[0]
        return f"**Квадрат со стороной {num(a)}:** площадь = a² = **{num(a * a)}**, периметр = 4a = **{num(4 * a)}**"
    if len(v) < 2:
        return None
    a, b = v[0], v[1]
    return f"**Прямоугольник {num(a)} × {num(b)}:** площадь = a·b = **{num(a * b)}**, периметр = 2(a + b) = **{num(2 * (a + b))}**"


@tool(CAT_MATH, "Площадь треугольника", "площадь треугольника со сторонами 3 4 5")
def triangle(text, low, s):
    if not re.search(r"площад\w*\s+треугольник", low):
        return None
    v = _geom_nums(low)
    if re.search(r"сторон", low) and len(v) >= 3:
        a, b, c = v[:3]
        p = (a + b + c) / 2
        sq = p * (p - a) * (p - b) * (p - c)
        if sq <= 0:
            return "Треугольника с такими сторонами не бывает: каждая сторона должна быть меньше суммы двух других."
        return f"**По формуле Герона:** p = {num(p)}, S = √(p(p−a)(p−b)(p−c)) = **{num(round(math.sqrt(sq), 4))}**"
    if re.search(r"основани|высот", low) and len(v) >= 2:
        return f"**S = ½ · a · h = ½ · {num(v[0])} · {num(v[1])} = {num(v[0] * v[1] / 2)}**"
    return None


@tool(CAT_MATH, "Объём куба", "объём куба со стороной 4")
def cube(text, low, s):
    if not re.search(r"объ[её]м\w*\s+куб", low):
        return None
    v = _geom_nums(low)
    if not v:
        return None
    return f"**Объём куба** V = a³ = {num(v[0])}³ = **{num(v[0] ** 3)}**, площадь поверхности = 6a² = {num(6 * v[0] ** 2)}"


@tool(CAT_MATH, "Объём шара", "объём шара радиус 3")
def sphere(text, low, s):
    if not re.search(r"объ[её]м\w*\s+(шар|сфер)", low):
        return None
    m = re.search(r"(радиус|диаметр)\w*\s*(?:=|равн\w*)?\s*(" + NUM + ")", low)
    if not m:
        return None
    r = f(m.group(2)) / (2 if m.group(1) == "диаметр" else 1)
    return f"**Объём шара** V = 4/3 · πr³ ≈ **{num(round(4 / 3 * math.pi * r ** 3, 4))}**, площадь поверхности = 4πr² ≈ {num(round(4 * math.pi * r * r, 4))}"


@tool(CAT_MATH, "Объём цилиндра", "объём цилиндра радиус 2 высота 5")
def cylinder(text, low, s):
    if not re.search(r"объ[её]м\w*\s+цилиндр", low):
        return None
    r = re.search(r"радиус\w*\s*(" + NUM + ")", low)
    h = re.search(r"высот\w*\s*(" + NUM + ")", low)
    if not r or not h:
        return None
    rv, hv = f(r.group(1)), f(h.group(1))
    return f"**Объём цилиндра** V = πr²h = π · {num(rv)}² · {num(hv)} ≈ **{num(round(math.pi * rv * rv * hv, 4))}**"


@tool(CAT_MATH, "Теорема Пифагора", "гипотенуза катеты 3 и 4")
def pythagoras(text, low, s):
    if not re.search(r"гипотенуз|катет", low):
        return None
    v = _geom_nums(low)
    if len(v) < 2:
        return None
    if re.search(r"найди катет|чему равен катет|второй катет|катет,? если", low) or re.search(r"гипотенуз\w*\s*(?:=|равн\w*)?\s*" + NUM, low):
        c, a = max(v[:2]), min(v[:2])
        if c <= a:
            return None
        return f"**Катет** b = √(c² − a²) = √({num(c)}² − {num(a)}²) = **{num(round(math.sqrt(c * c - a * a), 6))}**"
    a, b = v[0], v[1]
    return f"**Гипотенуза** c = √(a² + b²) = √({num(a)}² + {num(b)}²) = **{num(round(math.hypot(a, b), 6))}**"


def _list_nums(low):
    body = re.sub(r",\s+", " ", low)
    body = re.sub(r"(\d),(?=\d+,)", r"\1 ", body)
    return [f(x) for x in re.findall(NUM, body)]


@tool(CAT_MATH, "Среднее арифметическое", "среднее 3 5 7 10")
def mean(text, low, s):
    if not re.search(r"средн\w*(?:\s+арифметическ\w*)?(?:\s+значени\w*)?(?:\s+чисел)?", low) or re.search(r"средн\w* (?:бал|зарплат|скорост)", low) and len(_list_nums(low)) < 2:
        return None
    if not re.search(r"\bсредн", low):
        return None
    v = _list_nums(low)
    if len(v) < 2:
        return None
    return f"**Среднее = {num(round(sum(v) / len(v), 6))}**\n\nСумма {num(sum(v))} ÷ {len(v)} чисел."


@tool(CAT_MATH, "Медиана", "медиана 1 3 2 8 5")
def median(text, low, s):
    if "медиан" not in low:
        return None
    v = sorted(_list_nums(low))
    if not v:
        return None
    n = len(v)
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
    return f"**Медиана = {num(med)}**\n\nПо порядку: {', '.join(num(x) for x in v)}"


@tool(CAT_MATH, "Сумма, максимум и минимум списка", "максимум из 4 17 9 23")
def minmax(text, low, s):
    m = re.search(r"\b(максимум|минимум|наибольш\w*|наименьш\w*|сумм\w*)\b(?:\s+(?:из|чисел|числа))?", low)
    if not m or re.search(r"прописью|процент|кредит|вклад", low):
        return None
    v = _list_nums(low)
    if len(v) < 3:
        return None
    w = m.group(1)
    if w.startswith(("максимум", "наибольш")):
        return f"**Максимум: {num(max(v))}** (минимум — {num(min(v))})"
    if w.startswith(("минимум", "наименьш")):
        return f"**Минимум: {num(min(v))}** (максимум — {num(max(v))})"
    return f"**Сумма: {num(round(sum(v), 10))}** ({len(v)} чисел, среднее {num(round(sum(v) / len(v), 6))})"


@tool(CAT_MATH, "Точные дроби", "1/2 + 1/3 дробью")
def fractions_(text, low, s):
    if not re.search(r"дроб", low):
        return None
    expr = re.sub(r"[^\d+\-*/() ]", " ", low.translate(_POW)).strip()
    if not re.search(r"\d+\s*/\s*\d+", expr):
        return None
    expr = re.sub(r"\s+", "", expr)
    if not re.fullmatch(r"[\d+\-*/()]+", expr):
        return None
    v = _poly_eval(expr, Fraction(0))
    whole = ""
    if v.denominator != 1 and abs(v) > 1:
        w, r = divmod(abs(v.numerator), v.denominator)
        whole = f" = {'-' if v < 0 else ''}{w} целых {r}/{v.denominator}"
    return f"**{expr} = {_fr(v)}**{whole}" + ("" if v.denominator == 1 else f" ≈ {num(round(float(v), 6))}")


@tool(CAT_MATH, "Округление", "округли 3,14159 до 2 знаков")
def rounding(text, low, s):
    m = re.search(r"округли\w*\s+(" + NUM + r")(?:\s+до\s+(\d+)\s*(?:знак|цифр|после)|\s+до\s+(десятых|сотых|тысячных|целых|десятков|сотен|тысяч))?", low)
    if not m:
        return None
    v = f(m.group(1))
    if m.group(2):
        k = int(m.group(2))
    else:
        k = {"десятых": 1, "сотых": 2, "тысячных": 3, "целых": 0, "десятков": -1, "сотен": -2, "тысяч": -3}.get(m.group(3) or "целых")
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-k)
    res = Decimal(str(v)).quantize(q, rounding=ROUND_HALF_UP) if k >= 0 else (Decimal(str(v)) / q).quantize(Decimal(1), rounding=ROUND_HALF_UP) * q
    return f"**{m.group(1)} ≈ {num(float(res))}**"


@tool(CAT_MATH, "Чётное или нечётное", "12345 чётное?")
def parity(text, low, s):
    m = re.search(r"(-?\d+)\s*(?:—|-|это)?\s*(?:ч[её]тн|неч[её]тн)|(?:ч[её]тн|неч[её]тн)\w*\s+(?:ли\s+)?(?:число\s+)?(-?\d+)", low)
    if not m:
        return None
    n = int(m.group(1) or m.group(2))
    return f"**{n} — {'чётное' if n % 2 == 0 else 'нечётное'}** число."


@tool(CAT_MATH, "Сколько процентов составляет число", "сколько процентов 30 от 120")
def percent_of(text, low, s):
    m = re.search(r"(?:сколько|какой)\s+процент\w*\s+(?:составляет\s+)?(" + NUM + r")\s+от\s+(" + NUM + ")", low)
    if not m:
        return None
    a, b = f(m.group(1)), f(m.group(2))
    return f"**{num(a)} — это {num(round(a / b * 100, 4))}% от {num(b)}**"


@tool(CAT_MATH, "На сколько процентов изменилось", "на сколько процентов 120 больше 100")
def percent_change(text, low, s):
    m = re.search(r"на\s+сколько\s+процент\w*\s+(" + NUM + r")\s+(больше|меньше)\s+(" + NUM + ")", low)
    if m:
        a, b = f(m.group(1)), f(m.group(3))
        ch = (a - b) / b * 100
        return f"**{num(a)} {'больше' if ch >= 0 else 'меньше'} {num(b)} на {num(round(abs(ch), 4))}%**"
    m = re.search(r"(?:изменени\w*|рост|разниц\w*)\s+(?:в\s+процентах\s+)?(?:с|от)\s+(" + NUM + r")\s+до\s+(" + NUM + ")", low)
    if m:
        b, a = f(m.group(1)), f(m.group(2))
        ch = (a - b) / b * 100
        return f"**С {num(b)} до {num(a)}: {'+' if ch >= 0 else '−'}{num(round(abs(ch), 4))}%**"
    return None


@tool(CAT_MATH, "Увеличить или уменьшить на процент", "увеличь 2000 на 15%")
def percent_add(text, low, s):
    m = re.search(r"(увелич|уменьш|прибав|отним|вычт)\w*\s+(" + NUM + r")\s+на\s+(" + NUM + r")\s*%", low)
    if not m:
        return None
    v, p = f(m.group(2)), f(m.group(3))
    up = m.group(1).startswith(("увелич", "прибав"))
    res = v * (1 + p / 100) if up else v * (1 - p / 100)
    return f"**{num(v)} {'+' if up else '−'} {num(p)}% = {num(round(res, 4))}** ({'+' if up else '−'}{num(round(v * p / 100, 4))})"


# ================================================================ ФИНАНСЫ
CAT_MONEY = "Деньги"


def _term_months(low):
    m = re.search(r"на\s+(" + NUM + r")\s*(год|лет|мес)", low)
    if not m:
        return None
    n = f(m.group(1))
    return int(round(n * 12)) if m.group(2) in ("год", "лет") else int(round(n))


@tool(CAT_MONEY, "Кредит и ипотека: платёж и переплата", "кредит 500000 под 12% на 5 лет")
def loan(text, low, s):
    if not re.search(r"кредит|ипотек|займ|рассрочк", low):
        return None
    sm = re.search(r"(?:кредит|ипотек|займ)\w*\s+(?:на\s+)?(\d[\d\s]*(?:[.,]\d+)?)\s*(?:тыс|млн|руб|₽)?", low)
    rate = re.search(r"(?:под|ставк\w*)\s+(" + NUM + r")\s*%", low)
    months = _term_months(low)
    if not sm or not rate or not months:
        return None
    P = f(sm.group(1))
    if re.search(r"(\d)\s*млн", low):
        P *= 1_000_000
    elif re.search(r"(\d)\s*тыс", low):
        P *= 1000
    r = f(rate.group(1)) / 100 / 12
    pay = P / months if r == 0 else P * r / (1 - (1 + r) ** -months)
    total = pay * months
    return (f"## Кредит {rub(P)} под {num(f(rate.group(1)))}% на {months} мес.\n\n"
            f"| | |\n|---|---|\n| **Ежемесячный платёж** | **{rub(pay)}** |\n| Всего выплатите | {rub(total)} |\n"
            f"| Переплата | {rub(total - P)} ({num(round((total - P) / P * 100, 1))}%) |\n\n"
            "*Аннуитетный платёж (одинаковый каждый месяц), без страховок и комиссий банка.*")


@tool(CAT_MONEY, "Вклад со сложным процентом", "вклад 100000 под 10% на 3 года")
def deposit(text, low, s):
    if not re.search(r"вклад|депозит|накоплени|сложн\w* процент", low):
        return None
    sm = re.search(r"(\d[\d\s]*(?:[.,]\d+)?)\s*(?:руб|₽)?\s+под\s+(" + NUM + r")\s*%", low)
    months = _term_months(low)
    if not sm or not months:
        return None
    P, rate = f(sm.group(1)), f(sm.group(2)) / 100
    monthly = re.search(r"ежемесячн|каждый месяц|капитализац", low)
    total = P * (1 + rate / 12) ** months if monthly else P * (1 + rate) ** (months / 12)
    add = re.search(r"пополн\w*\s+(?:на\s+)?(\d[\d\s]*)\s*(?:руб|₽)?\s*(?:в|каждый)\s+месяц", low)
    extra = ""
    if add:
        a = f(add.group(1))
        mr = rate / 12
        total = P * (1 + mr) ** months + a * (((1 + mr) ** months - 1) / mr if mr else months)
        extra = f", пополнения {rub(a)} в месяц"
        P += a * months
    return (f"## Вклад под {num(rate * 100)}% на {months} мес.\n\nВложено: {rub(P)}{extra}\n\n**Будет: {rub(total)}**, доход {rub(total - P)}\n\n"
            f"*{'Капитализация каждый месяц' if monthly or add else 'Проценты начисляются раз в год'}; налог на проценты не учтён.*")


@tool(CAT_MONEY, "Скидка: сколько заплатить", "2000 со скидкой 15%")
def discount(text, low, s):
    m = (re.search(r"(" + NUM + r")\s*(?:руб\w*|₽)?\s+со\s+скидк\w*\s+(" + NUM + r")\s*%", low)
         or re.search(r"скидк\w*\s+(" + NUM + r")\s*%\s+(?:на|от|с)\s+(" + NUM + ")", low))
    if not m:
        return None
    a, b = f(m.group(1)), f(m.group(2))
    price, pct = (a, b) if "со скидк" in low else (b, a)
    return f"**Цена со скидкой {num(pct)}%: {rub(price * (1 - pct / 100))}**\n\nЭкономия: {rub(price * pct / 100)} (было {rub(price)})."


@tool(CAT_MONEY, "НДС: начислить или выделить", "ндс от 12000")
def vat(text, low, s):
    if not re.search(r"\bндс\b|\bvat\b", low):
        return None
    v = [x for x in nums(low)]
    rate = re.search(r"(" + NUM + r")\s*%", low)
    r = f(rate.group(1)) if rate else 22.0
    amounts = [x for x in v if not rate or x != r]
    if not amounts:
        return None
    a = amounts[0]
    note = "" if rate else "\n\n*Ставка 22% — основная в России с 1 января 2026 года (в Беларуси — 20%). Другую ставку напишите: «ндс 20% от …».*"
    if re.search(r"выдел|в том числе|включ|из суммы|внутри", low):
        tax = a * r / (100 + r)
        return f"**В сумме {rub(a)} НДС {num(r)}% = {rub(tax)}**\n\nБез НДС: {rub(a - tax)}." + note
    return f"**НДС {num(r)}% от {rub(a)} = {rub(a * r / 100)}**\n\nИтого с НДС: {rub(a * (1 + r / 100))}." + note


@tool(CAT_MONEY, "Зарплата на руки после НДФЛ", "зарплата 100000 на руки")
def salary(text, low, s):
    if not re.search(r"зарплат|оклад|ндфл|на руки", low):
        return None
    v = nums(low)
    if not v:
        return None
    a = v[0]
    if re.search(r"чтобы\s+на\s+руки|до\s+вычета\s+чтобы|сколько\s+(?:нужно\s+)?(?:начислить|грязными)", low):
        return f"**Чтобы получить на руки {rub(a)}, начислить нужно {rub(a / 0.87)}**\n\n(НДФЛ 13% — при доходе до 2,4 млн ₽ в год.)"
    return (f"**На руки: {rub(a * 0.87)}** из {rub(a)}\n\nНДФЛ 13% = {rub(a * 0.13)}.\n\n"
            "*В России с 2025 года ставка растёт с доходом: 13% до 2,4 млн ₽ в год, 15% — до 5 млн, 18% — до 20 млн, 20% — до 50 млн, дальше 22%.*")


@tool(CAT_MONEY, "Разделить счёт и чаевые", "счёт 3500 на 4 человек чаевые 10%")
def split_bill(text, low, s):
    m = re.search(r"(?:сч[её]т|чек|разделить|раздели|поделить|подели)\w*\s+(" + NUM + r")\s*(?:руб\w*|₽)?\s+на\s+(\d+)\s*(?:человек|чел|друз|гост)", low)
    tip = re.search(r"чаев\w*\s+(" + NUM + r")\s*%|(" + NUM + r")\s*%\s+чаев", low)
    if not m and not tip:
        return None
    if not m:
        v = nums(low)
        total = v[0] if v else 0
        p = f(tip.group(1) or tip.group(2))
        return f"**Чаевые {num(p)}% от {rub(total)} = {rub(total * p / 100)}**, итого {rub(total * (1 + p / 100))}."
    total, people = f(m.group(1)), int(m.group(2))
    p = f(tip.group(1) or tip.group(2)) if tip else 0
    full = total * (1 + p / 100)
    return (f"**С каждого: {rub(full / people)}**\n\nСчёт {rub(total)}" + (f" + чаевые {num(p)}% ({rub(total * p / 100)}) = {rub(full)}" if p else "")
            + f" на {people} {skills.plural(people, 'человека', 'человек', 'человек')}.")


@tool(CAT_MONEY, "Наценка и маржа", "наценка 30% на 1000")
def markup(text, low, s):
    m = re.search(r"наценк\w*\s+(" + NUM + r")\s*%\s+(?:на|к)\s+(" + NUM + ")", low)
    if m:
        p, c = f(m.group(1)), f(m.group(2))
        price = c * (1 + p / 100)
        return f"**Цена с наценкой {num(p)}%: {rub(price)}**\n\nПрибыль с единицы {rub(price - c)}, маржа {num(round((price - c) / price * 100, 2))}%."
    m = re.search(r"(?:закупк\w*|себестоимост\w*)\s+(" + NUM + r").{0,30}?(?:продаж\w*|цена)\s+(" + NUM + ")", low)
    if m and re.search(r"наценк|марж", low):
        c, p = f(m.group(1)), f(m.group(2))
        return f"**Наценка {num(round((p - c) / c * 100, 2))}%, маржа {num(round((p - c) / p * 100, 2))}%**, прибыль {rub(p - c)}."
    return None


# ================================================================ ЗДОРОВЬЕ
CAT_HEALTH = "Здоровье"


def _height_weight(low):
    h = re.search(r"(?:рост\w*\s*)(" + NUM + r")|(" + NUM + r")\s*(?:см|сантиметр)", low)
    w = re.search(r"(?:вес\w*\s*)(" + NUM + r")|(" + NUM + r")\s*(?:кг|килограмм)", low)
    if not h or not w:
        return None, None
    hv, wv = f(h.group(1) or h.group(2)), f(w.group(1) or w.group(2))
    if hv < 3:
        hv *= 100  # 1,8 м
    return hv, wv


@tool(CAT_HEALTH, "Индекс массы тела (ИМТ)", "имт рост 180 вес 75")
def bmi(text, low, s):
    if not re.search(r"\bимт\b|индекс\w* массы|\bbmi\b", low):
        return None
    h, w = _height_weight(low)
    if not h:  # «калькулятор ИМТ» — это просьба о программе, а не расчёт
        return "Напишите рост и вес, например: «имт рост 175 вес 70»." if re.search(r"посчитай|рассчитай|какой у меня|мой\s+имт|узнать", low) else None
    v = w / (h / 100) ** 2
    zone = ("недостаток веса" if v < 18.5 else "норма" if v < 25 else "избыточный вес" if v < 30 else "ожирение")
    lo, hi = 18.5 * (h / 100) ** 2, 24.9 * (h / 100) ** 2
    return (f"**ИМТ = {num(round(v, 1))} — {zone}**\n\nНорма для роста {num(h)} см: от {num(round(lo, 1))} до {num(round(hi, 1))} кг.\n\n"
            "*ИМТ не учитывает мышцы и возраст — это ориентир, а не диагноз.*")


@tool(CAT_HEALTH, "Нормальный вес для роста", "нормальный вес при росте 170")
def normal_weight(text, low, s):
    m = re.search(r"(?:нормальн|идеальн|здоров)\w*\s+вес\w*\s+(?:при|для)?\s*(?:рост\w*\s+)?(" + NUM + ")", low)
    if not m:
        return None
    h = f(m.group(1))
    if h < 3:
        h *= 100
    lo, hi = 18.5 * (h / 100) ** 2, 24.9 * (h / 100) ** 2
    return f"**При росте {num(h)} см нормальный вес — от {num(round(lo, 1))} до {num(round(hi, 1))} кг** (ИМТ 18,5–24,9)."


@tool(CAT_HEALTH, "Сколько воды пить в день", "сколько воды пить при весе 70")
def water(text, low, s):
    if not re.search(r"сколько\s+(?:нужно\s+)?(?:воды|жидкости)\s+(?:нужно\s+)?(?:пить|выпивать)|норма\s+воды", low):
        return None
    v = nums(low)
    if not v:
        return "Обычно взрослому нужно 30–35 мл воды на 1 кг веса в день. Напишите вес: «сколько воды пить при весе 70»."
    w = v[0]
    return f"**При весе {num(w)} кг — около {num(round(w * 0.03, 1))}–{num(round(w * 0.035, 1))} л в день** (30–35 мл на кг), в жару и при спорте — больше."


@tool(CAT_HEALTH, "Норма калорий в день", "норма калорий женщина 25 лет 165 см 55 кг")
def calories(text, low, s):
    if not re.search(r"калори|ккал", low) or not re.search(r"норм|сколько\s+(?:нужно|надо)|суточн|в день", low):
        return None
    h, w = _height_weight(low)
    age = re.search(r"(\d+)\s*(?:лет|год)", low)
    if not h or not age:
        return "Напишите пол, возраст, рост и вес: «норма калорий мужчина 30 лет 180 см 80 кг»."
    a = int(age.group(1))
    female = bool(re.search(r"женщ|девушк|девочк|жен\b|\bж\b", low))
    bmr = 10 * w + 6.25 * h - 5 * a + (-161 if female else 5)
    rows = "\n".join(f"| {name} | **{num(round(bmr * k / 10) * 10)} ккал** |" for name, k in
                     (("Покой (базовый обмен)", 1), ("Сидячая работа", 1.2), ("Спорт 1–3 раза в неделю", 1.375),
                      ("Спорт 3–5 раз", 1.55), ("Каждый день", 1.725)))
    return (f"## Норма калорий ({'женщина' if female else 'мужчина'}, {a} {skills.plural(a, 'год', 'года', 'лет')}, {num(h)} см, {num(w)} кг)\n\n"
            f"| Активность | В день |\n|---|---|\n{rows}\n\nЧтобы худеть — на 10–20% меньше, чтобы набирать — на 10–15% больше. *Формула Миффлина — Сан Жеора.*")


@tool(CAT_HEALTH, "Пульсовые зоны для тренировок", "пульсовые зоны 30 лет")
def heart_zones(text, low, s):
    if not re.search(r"пульс", low) or not re.search(r"зон|максимальн|тренир|жиросжиг", low):
        return None
    age = ints(low)
    if not age:
        return "Напишите возраст: «пульсовые зоны 30 лет»."
    mx = 220 - age[0]
    zones = [("1 — разминка", 50, 60), ("2 — жиросжигание", 60, 70), ("3 — аэробная", 70, 80), ("4 — анаэробная", 80, 90), ("5 — максимум", 90, 100)]
    rows = "\n".join(f"| {n} | {round(mx * a / 100)}–{round(mx * b / 100)} |" for n, a, b in zones)
    return f"**Максимальный пульс ≈ {mx} уд/мин** (220 − возраст)\n\n| Зона | Пульс, уд/мин |\n|---|---|\n{rows}"


@tool(CAT_HEALTH, "Циклы сна: когда лечь и встать", "во сколько лечь спать если вставать в 7:00")
def sleep_cycles(text, low, s):
    m = re.search(r"(?:вставать|встать|проснуться|подъ[её]м)\w*\s+(?:в|к)\s+(\d{1,2})(?:[:.](\d{2}))?", low)
    if m and re.search(r"лечь|ложиться|засыпать|уснуть|спать", low):
        wake = datetime(2000, 1, 2, int(m.group(1)) % 24, int(m.group(2) or 0))
        times = [(wake - timedelta(minutes=90 * c + 15)).strftime("%H:%M") + f" ({c} {skills.plural(c, 'цикл', 'цикла', 'циклов')}, {c * 1.5:g} ч)".replace(".", ",")
                 for c in (6, 5, 4)]
        return "**Чтобы проснуться в " + wake.strftime("%H:%M") + " бодрым, ложитесь в:**\n\n- " + "\n- ".join(times) + \
            "\n\nСон идёт циклами по ~90 минут; проснуться между циклами легче. Учтено ~15 минут на засыпание."
    m = re.search(r"(?:лягу|ложусь|засну|усну)\w*\s+(?:в\s+(\d{1,2})(?:[:.](\d{2}))?|сейчас)", low)
    if m and re.search(r"встать|вставать|просыпаться|будильник", low):
        if m.group(1):
            bed = datetime(2000, 1, 1, int(m.group(1)) % 24, int(m.group(2) or 0))
        else:
            now = skills._now()
            bed = datetime(2000, 1, 1, now.hour, now.minute)
        times = [(bed + timedelta(minutes=90 * c + 15)).strftime("%H:%M") + f" ({c * 1.5:g} ч сна)".replace(".", ",") for c in (4, 5, 6)]
        return "**Будильник лучше поставить на:**\n\n- " + "\n- ".join(times) + "\n\nТак вы проснётесь между циклами сна (по ~90 минут)."
    return None


# ================================================================ ВРЕМЯ
CAT_TIME = "Время и даты"


def _last_sunday(year, month):
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _nth_sunday(year, month, n):
    d = date(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _dst(rule, utc):
    y = utc.year
    if rule == "eu":
        start = datetime(y, 3, _last_sunday(y, 3).day, 1, tzinfo=timezone.utc)
        end = datetime(y, 10, _last_sunday(y, 10).day, 1, tzinfo=timezone.utc)
        return start <= utc < end
    if rule == "us":  # 2:00 по местному ≈ 7:00 UTC (для восточного побережья; разница в часах для запада несущественна)
        start = datetime(y, 3, _nth_sunday(y, 3, 2).day, 7, tzinfo=timezone.utc)
        end = datetime(y, 11, _nth_sunday(y, 11, 1).day, 6, tzinfo=timezone.utc)
        return start <= utc < end
    if rule == "au":  # Сидней: с первого воскресенья октября до первого воскресенья апреля
        start = datetime(y, 10, _nth_sunday(y, 10, 1).day, 16, tzinfo=timezone.utc) - timedelta(days=1)
        end = datetime(y, 4, _nth_sunday(y, 4, 1).day, 16, tzinfo=timezone.utc) - timedelta(days=1)
        return utc >= start or utc < end
    return False


# город: (название, смещение от UTC в часах, правило летнего времени)
CITIES_TZ = {
    "москв": ("Москва", 3, None), "питер": ("Санкт-Петербург", 3, None), "петербург": ("Санкт-Петербург", 3, None),
    "минск": ("Минск", 3, None), "казан": ("Казань", 3, None), "калининград": ("Калининград", 2, None),
    "самар": ("Самара", 4, None), "екатеринбург": ("Екатеринбург", 5, None), "челябинск": ("Челябинск", 5, None),
    "омск": ("Омск", 6, None), "новосибирск": ("Новосибирск", 7, None), "красноярск": ("Красноярск", 7, None),
    "иркутск": ("Иркутск", 8, None), "якутск": ("Якутск", 9, None), "владивосток": ("Владивосток", 10, None),
    "хабаровск": ("Хабаровск", 10, None), "магадан": ("Магадан", 11, None), "камчат": ("Петропавловск-Камчатский", 12, None),
    "киев": ("Киев", 2, "eu"), "кишин": ("Кишинёв", 2, "eu"), "рига": ("Рига", 2, "eu"), "риге": ("Рига", 2, "eu"),
    "вильнюс": ("Вильнюс", 2, "eu"), "таллин": ("Таллин", 2, "eu"), "хельсинки": ("Хельсинки", 2, "eu"), "афин": ("Афины", 2, "eu"),
    "астан": ("Астана", 5, None), "алмат": ("Алматы", 5, None), "ташкент": ("Ташкент", 5, None), "бишкек": ("Бишкек", 6, None),
    "душанбе": ("Душанбе", 5, None), "тбилиси": ("Тбилиси", 4, None), "ереван": ("Ереван", 4, None), "баку": ("Баку", 4, None),
    "стамбул": ("Стамбул", 3, None), "анкар": ("Анкара", 3, None), "дуба": ("Дубай", 4, None),
    "лондон": ("Лондон", 0, "eu"), "дублин": ("Дублин", 0, "eu"), "лиссабон": ("Лиссабон", 0, "eu"),
    "париж": ("Париж", 1, "eu"), "берлин": ("Берлин", 1, "eu"), "рим": ("Рим", 1, "eu"), "мадрид": ("Мадрид", 1, "eu"),
    "варшав": ("Варшава", 1, "eu"), "праг": ("Прага", 1, "eu"), "вен": ("Вена", 1, "eu"), "амстердам": ("Амстердам", 1, "eu"),
    "барселон": ("Барселона", 1, "eu"), "стокгольм": ("Стокгольм", 1, "eu"), "осло": ("Осло", 1, "eu"),
    "дели": ("Нью-Дели", 5.5, None), "мумба": ("Мумбаи", 5.5, None), "бангкок": ("Бангкок", 7, None), "ханой": ("Ханой", 7, None),
    "пекин": ("Пекин", 8, None), "шанха": ("Шанхай", 8, None), "гонконг": ("Гонконг", 8, None), "сингапур": ("Сингапур", 8, None),
    "токио": ("Токио", 9, None), "сеул": ("Сеул", 9, None), "сидне": ("Сидней", 10, "au"), "мельбурн": ("Мельбурн", 10, "au"),
    "нью-йорк": ("Нью-Йорк", -5, "us"), "нью йорк": ("Нью-Йорк", -5, "us"), "вашингтон": ("Вашингтон", -5, "us"),
    "торонто": ("Торонто", -5, "us"), "майами": ("Майами", -5, "us"), "чикаго": ("Чикаго", -6, "us"), "денвер": ("Денвер", -7, "us"),
    "лос-анджелес": ("Лос-Анджелес", -8, "us"), "лос анджелес": ("Лос-Анджелес", -8, "us"), "сан-франциско": ("Сан-Франциско", -8, "us"),
    "мехико": ("Мехико", -6, None), "сан-паулу": ("Сан-Паулу", -3, None), "рио": ("Рио-де-Жанейро", -3, None),
    "буэнос": ("Буэнос-Айрес", -3, None),
}


def _city_time(word, utc):
    for key, (name, off, rule) in CITIES_TZ.items():
        if word.startswith(key) or (len(key) > 4 and key in word):
            o = off + (1 if rule and _dst(rule, utc) else 0)
            return name, o, utc + timedelta(hours=o)
    return None


def _fmt_off(o):
    h = int(abs(o))
    mins = int(round((abs(o) - h) * 60))
    return f"UTC{'+' if o >= 0 else '−'}{h}" + (f":{mins:02d}" if mins else "")


@tool(CAT_TIME, "Время в городах мира", "который час в Токио")
def world_time(text, low, s):
    m = re.search(r"(?:который\s+час|сколько\s+(?:сейчас\s+)?времени|какое\s+время|время)\s+(?:сейчас\s+)?в\s+([а-яё\- ]+)", low)
    if not m or re.search(r"разниц", low):
        return None
    utc = datetime.now(timezone.utc)
    found = _city_time(m.group(1).strip(), utc)
    if not found:
        return None
    name, off, local = found
    msk = utc + timedelta(hours=3)
    diff = off - 3
    d = "" if diff == 0 else f" — на {num(abs(diff))} {skills.plural(int(abs(diff)) if is_int(diff) else 2, 'час', 'часа', 'часов')} {'больше' if diff > 0 else 'меньше'}, чем в Москве"
    day = "" if local.date() == msk.date() else (" (там уже завтра)" if local.date() > msk.date() else " (там ещё вчера)")
    return f"**{name}: {local:%H:%M}**{day}, {_fmt_off(off)}{d}."


@tool(CAT_TIME, "Разница во времени между городами", "разница во времени между Москвой и Нью-Йорком")
def time_diff(text, low, s):
    m = re.search(r"разниц\w*\s+(?:во\s+времени\s+)?(?:между\s+)?([а-яё\- ]+?)\s+и\s+([а-яё\- ]+)", low)
    if not m:
        return None
    utc = datetime.now(timezone.utc)
    a, b = _city_time(m.group(1).strip(), utc), _city_time(m.group(2).strip(), utc)
    if not a or not b:
        return None
    diff = b[1] - a[1]
    if diff == 0:
        return f"**Разницы нет:** {a[0]} и {b[0]} — {a[2]:%H:%M}."
    return (f"**Разница — {num(abs(diff))} ч.** Сейчас: {a[0]} — {a[2]:%H:%M}, {b[0]} — {b[2]:%H:%M} "
            f"({b[0]} {'впереди' if diff > 0 else 'позади'}).")


_ZODIAC = [((1, 20), "Водолей ♒"), ((2, 19), "Рыбы ♓"), ((3, 21), "Овен ♈"), ((4, 20), "Телец ♉"), ((5, 21), "Близнецы ♊"),
           ((6, 21), "Рак ♋"), ((7, 23), "Лев ♌"), ((8, 23), "Дева ♍"), ((9, 23), "Весы ♎"), ((10, 23), "Скорпион ♏"),
           ((11, 22), "Стрелец ♐"), ((12, 22), "Козерог ♑")]


@tool(CAT_TIME, "Знак зодиака по дате", "знак зодиака 5 мая")
def zodiac(text, low, s):
    if not re.search(r"знак\w* зодиак|по гороскопу|зодиак", low) or re.search(r"китайск|восточн", low):
        return None
    parsed = skills._parse_date(low, skills._now())
    if not parsed:
        return None
    d = parsed[0]
    sign = "Козерог ♑"
    for (mm, dd), name in _ZODIAC:
        if (d.month, d.day) >= (mm, dd):
            sign = name
    return f"**{d.day} {skills._MONTHS[d.month - 1]} — {sign}**"


_CHINESE = ["Крысы", "Быка", "Тигра", "Кролика", "Дракона", "Змеи", "Лошади", "Козы", "Обезьяны", "Петуха", "Собаки", "Свиньи"]
_ELEMENTS = ["Дерева", "Огня", "Земли", "Металла", "Воды"]


@tool(CAT_TIME, "Китайский гороскоп по году", "китайский гороскоп 2008")
def chinese(text, low, s):
    if not re.search(r"китайск|восточн|год\s+(?:какого\s+)?(?:животного|кого)|чей\s+год|символ\w*\s+(?:\d{4}\s+)?года", low):
        return None
    y = re.search(r"\b(1[89]\d\d|20\d\d|2100)\b", low)
    year = int(y.group(1)) if y else skills._now().year
    animal = _CHINESE[(year - 4) % 12]
    element = _ELEMENTS[((year - 4) % 10) // 2]
    return (f"**{year} — год {animal}** (стихия {element}).\n\n*По китайскому календарю год начинается не 1 января, а в китайский "
            "Новый год — между 21 января и 20 февраля.*")


@tool(CAT_TIME, "Сколько дней я прожил", "сколько дней я прожил, если родился 5 мая 2008")
def days_lived(text, low, s):
    if not re.search(r"прожил|прожила|сколько\s+мне\s+дней|мой\s+возраст\s+в\s+дн", low):
        return None
    parsed = skills._parse_date(low, skills._now())
    if not parsed or not parsed[1]:
        return "Напишите дату рождения полностью: «сколько дней я прожил, если родился 5 мая 2008»."
    born = parsed[0]
    today = skills._now().date()
    days = (today - born).days
    if days < 0:
        return None
    return (f"**Вы прожили {num(days)} {skills.plural(days, 'день', 'дня', 'дней')}** — это около {num(days // 7)} недель, "
            f"{num(days * 24)} часов. Следующий круглый рубеж — {num((days // 1000 + 1) * 1000)} дней, "
            f"{skills._say_date(born + timedelta(days=(days // 1000 + 1) * 1000))}.")


@tool(CAT_TIME, "Какой век", "какой век 1812 год")
def century(text, low, s):
    m = re.search(r"(?:как\w*\s+век|в\s+каком\s+веке|век)\D{0,20}(\d{1,4})|(\d{1,4})\s*(?:год\w*)?\s*[—-]?\s*(?:это\s+)?как\w*\s+век", low)
    if not m or not re.search(r"век", low):
        return None
    y = int(m.group(1) or m.group(2))
    if y < 1 or y > 3000:
        return None
    c = (y - 1) // 100 + 1
    return f"**{y} год — {to_roman(c)} ({c}-й) век** ({(c - 1) * 100 + 1}–{c * 100} годы)."


@tool(CAT_TIME, "Сколько дней в месяце", "сколько дней в феврале 2028")
def month_days(text, low, s):
    m = re.search(r"сколько\s+дней\s+в\s+(январ|феврал|март|апрел|ма[йея]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*(?:\s+(\d{4}))?", low)
    if not m:
        return None
    key = "ма" if m.group(1).startswith("ма") and not m.group(1).startswith("мар") else m.group(1)
    months = ["январ", "феврал", "март", "апрел", "ма", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]
    mo = months.index(key) + 1
    year = int(m.group(2)) if m.group(2) else skills._now().year
    nxt = date(year + (mo == 12), mo % 12 + 1, 1)
    n = (nxt - date(year, mo, 1)).days
    name = ["январе", "феврале", "марте", "апреле", "мае", "июне", "июле", "августе", "сентябре", "октябре", "ноябре", "декабре"][mo - 1]
    return f"**В {name} {year} года {n} {skills.plural(n, 'день', 'дня', 'дней')}**" + (" (год високосный)" if mo == 2 and n == 29 else "")


@tool(CAT_TIME, "Номер недели в году", "какая сейчас неделя года")
def week_number(text, low, s):
    if not re.search(r"(?:какая|номер)\s+(?:сейчас\s+)?недел\w*(?:\s+(?:года|в году))?|сколько\s+недель\s+прошло", low):
        return None
    d = skills._now().date()
    w = d.isocalendar()[1]
    return f"**Сейчас {w}-я неделя {d.year} года** (по ISO, неделя начинается с понедельника)."


# ================================================================ ТЕКСТ
CAT_TEXT = "Текст"

_TRANSLIT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k",
             "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
             "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "ie", "ы": "y", "ь": "", "э": "e", "ю": "iu", "я": "ia"}


def _body(text, words_re):
    """Текст после команды: «транслит: Привет» → «Привет»."""
    m = re.search(words_re + r"\w*\s*(?:текст\w*|слов\w*|фраз\w*)?\s*[:—-]?\s*(.+)", text, re.I | re.S)
    return m.group(1).strip().strip("«»\"'") if m else ""


@tool(CAT_TEXT, "Транслитерация (как в загранпаспорте)", "транслит Иванов Пётр")
def translit(text, low, s):
    if not re.search(r"транслит|латиниц", low):
        return None
    body = _body(text, r"(?:транслит(?:ерац\w*)?|латиниц\w*|переведи на латиниц\w*|напиши латиниц\w*)")
    if not body:
        return None
    out = ""
    for ch in body:
        t = _TRANSLIT.get(ch.lower())
        if t is None:
            out += ch
        else:
            out += t.capitalize() if ch.isupper() else t
    return f"**{out}**\n\n*Правила загранпаспорта РФ (ИКАО): Ж → ZH, Х → KH, Ц → TS, Щ → SHCH, Ю → IU, Я → IA.*"


@tool(CAT_TEXT, "Исправить раскладку клавиатуры", "исправь раскладку ghbdtn vbh")
def layout(text, low, s):
    if not re.search(r"раскладк|не на той раскладке|переключи раскладку", low):
        return None
    body = _body(text, r"раскладк\w*")
    if not body:
        return None
    en = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>~"
    ru = "йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ"
    latin = sum(ch in en for ch in body) >= sum(ch in ru for ch in body)
    table = str.maketrans(en, ru) if latin else str.maketrans(ru, en)
    return f"**{body.translate(table)}**"


_MORSE = {"а": ".-", "б": "-...", "в": ".--", "г": "--.", "д": "-..", "е": ".", "ж": "...-", "з": "--..", "и": "..", "й": ".---",
          "к": "-.-", "л": ".-..", "м": "--", "н": "-.", "о": "---", "п": ".--.", "р": ".-.", "с": "...", "т": "-", "у": "..-",
          "ф": "..-.", "х": "....", "ц": "-.-.", "ч": "---.", "ш": "----", "щ": "--.-", "ъ": "--.--", "ы": "-.--", "ь": "-..-",
          "э": "..-..", "ю": "..--", "я": ".-.-"}
_MORSE_EN = {"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.", "g": "--.", "h": "....", "i": "..", "j": ".---",
             "k": "-.-", "l": ".-..", "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.", "s": "...", "t": "-",
             "u": "..-", "v": "...-", "w": ".--", "x": "-..-", "y": "-.--", "z": "--.."}
_MORSE_NUM = {"0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
              "8": "---..", "9": "----.", ".": "......", ",": ".-.-.-", "?": "..--..", "!": "--..--"}


@tool(CAT_TEXT, "Азбука Морзе: зашифровать", "азбукой морзе SOS")
def morse_encode(text, low, s):
    if "морзе" not in low:
        return None
    body = _body(text, r"морзе")
    if not body or re.fullmatch(r"[.\-/\s·—]+", body):
        return None
    out = []
    for word in body.lower().split():
        out.append(" ".join(_MORSE.get(ch) or _MORSE_EN.get(ch) or _MORSE_NUM.get(ch, "") for ch in word.replace("ё", "е")).strip())
    return "**" + " / ".join(w for w in out if w) + "**\n\nТочка — короткий сигнал, тире — длинный, «/» — пробел между словами."


@tool(CAT_TEXT, "Азбука Морзе: расшифровать", "расшифруй морзе ... --- ...")
def morse_decode(text, low, s):
    m = re.search(r"([.\-·—]+(?:\s+[.\-·—/]+)+|[.\-]{2,})\s*$", text.strip())
    if not m or not re.search(r"морзе|расшифр|переведи", low):
        return None
    code = m.group(1).replace("·", ".").replace("—", "-")
    russian = bool(re.search(r"русск|кириллиц", low))
    rev = {v: k for k, v in (_MORSE if russian else _MORSE_EN).items()}
    rev.update({v: k for k, v in _MORSE_NUM.items()})
    words_ = []
    for w in re.split(r"\s*/\s*|\s{3,}", code):
        words_.append("".join(rev.get(c, "?") for c in w.split()))
    res = " ".join(words_).upper()
    return f"**{res}**" + ("" if russian else "\n\n*Расшифровал латиницей. Для русских букв напишите «расшифруй морзе по-русски …».*")


@tool(CAT_TEXT, "Палиндром ли слово", "шалаш палиндром?")
def palindrome(text, low, s):
    if "палиндром" not in low:
        return None
    body = re.sub(r"(?i)\b(?:явля\w*|ли|это|слово|фраза|палиндром\w*|проверь|является)\b", " ", text)
    body = body.strip(" ?!.:—-«»\"")
    letters = re.sub(r"[^a-zа-яё0-9]", "", body.lower().replace("ё", "е"))
    if len(letters) < 2:
        return "Палиндром — слово или фраза, которые читаются одинаково в обе стороны: «шалаш», «А роза упала на лапу Азора»."
    ok = letters == letters[::-1]
    return f"**«{body}» — {'палиндром' if ok else 'не палиндром'}**" + ("" if ok else f": наоборот читается «{body[::-1]}».")


@tool(CAT_TEXT, "Гласные и согласные", "сколько гласных в слове молоко")
def vowels(text, low, s):
    m = re.search(r"сколько\s+(гласн|согласн|букв\w*\s+и\s+звук)\w*\s+(?:букв\s+)?в\s+(?:слове\s+|фразе\s+)?[«\"]?([а-яё\- ]+)", low)
    if not m:
        return None
    w = m.group(2).strip(" »\"")
    vs = [c for c in w if c in "аеёиоуыэюя"]
    cs = [c for c in w if c in "бвгджзйклмнпрстфхцчшщ"]
    return f"**«{w}»: гласных {len(vs)}** ({', '.join(vs)}), **согласных {len(cs)}**, слогов {len(vs)}."


@tool(CAT_TEXT, "Анаграммы", "являются ли анаграммами апельсин и спаниель")
def anagram(text, low, s):
    if "анаграм" not in low:
        return None
    m = re.search(r"([а-яёa-z]+)\s+и\s+([а-яёa-z]+)\s*\??$", low)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    ok = sorted(a.replace("ё", "е")) == sorted(b.replace("ё", "е"))
    return f"**«{a}» и «{b}» — {'анаграммы' if ok else 'не анаграммы'}**" + (": одни и те же буквы в другом порядке." if ok else ".")


_RU_ABC = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
_EN_ABC = "abcdefghijklmnopqrstuvwxyz"


def _caesar(body, shift):
    out = ""
    for ch in body:
        lo = ch.lower()
        for abc in (_RU_ABC, _EN_ABC):
            if lo in abc:
                c = abc[(abc.index(lo) + shift) % len(abc)]
                out += c.upper() if ch.isupper() else c
                break
        else:
            out += ch
    return out


@tool(CAT_TEXT, "Шифр Цезаря: зашифровать", "зашифруй шифром цезаря привет сдвиг 3")
def caesar_enc(text, low, s):
    if "цезар" not in low or re.search(r"расшифр|дешифр", low) or not re.search(r"зашифр|шифруй|закодир", low) \
            or re.search(r"\bна\s+(?:python|питон|javascript|js|c\+\+|java|php)|программ|код\b|функци", low):
        return None
    m = re.search(r"сдвиг\w*\s*(-?\d+)", low)
    shift = int(m.group(1)) if m else 3
    body = re.sub(r"(?i)\s*(?:со\s+)?сдвиг\w*\s*-?\d+", "", _body(text, r"цезар\w*"))
    if not body:
        return None
    return f"**{_caesar(body, shift)}**\n\nШифр Цезаря, сдвиг {shift}: каждая буква заменена на стоящую через {shift} по алфавиту."


@tool(CAT_TEXT, "Шифр Цезаря: расшифровать", "расшифруй цезаря тулезх сдвиг 3")
def caesar_dec(text, low, s):
    if "цезар" not in low or not re.search(r"расшифр|дешифр", low):
        return None
    m = re.search(r"сдвиг\w*\s*(-?\d+)", low)
    shift = int(m.group(1)) if m else 3
    body = re.sub(r"(?i)\s*(?:со\s+)?сдвиг\w*\s*-?\d+", "", _body(text, r"цезар\w*"))
    if not body:
        return None
    return f"**{_caesar(body, -shift)}**\n\n(сдвиг {shift} назад)"


@tool(CAT_TEXT, "Каждое слово с заглавной", "каждое слово с большой буквы: иван петров")
def title_case(text, low, s):
    if not re.search(r"кажд\w* слов\w* с (?:большой|заглавной)|с заглавной каждое", low):
        return None
    body = re.split(r"[:—]\s*", text, maxsplit=1)
    if len(body) < 2 or not body[1].strip():
        return None
    return "**" + " ".join(w[:1].upper() + w[1:].lower() for w in body[1].split()) + "**"


@tool(CAT_TEXT, "Слова в обратном порядке", "переставь слова в обратном порядке: я люблю код")
def reverse_words(text, low, s):
    if not re.search(r"слова\s+в\s+обратном\s+порядке|обратн\w+\s+порядк\w*\s+слов", low):
        return None
    body = re.split(r"[:—]\s*", text, maxsplit=1)
    if len(body) < 2 or not body[1].strip():
        return None
    return "**" + " ".join(reversed(body[1].split())) + "**"


@tool(CAT_TEXT, "Base64: закодировать", "base64 привет")
def b64_encode(text, low, s):
    if not re.search(r"base\s*64|бейс\s*64", low) or re.search(r"раскодир|декодир|расшифр|decode", low):
        return None
    body = re.split(r"(?i)base\s*64|бейс\s*64", text, maxsplit=1)[1].strip(" :—-")
    body = re.sub(r"(?i)^(?:закодируй|кодир\w*|encode)\s*", "", body)
    if not body:
        return None
    return f"`{base64.b64encode(body.encode('utf-8')).decode()}`"


@tool(CAT_TEXT, "Base64: раскодировать", "раскодируй base64 0L/RgNC40LLQtdGC")
def b64_decode(text, low, s):
    if not re.search(r"base\s*64|бейс\s*64", low) or not re.search(r"раскодир|декодир|расшифр|decode", low):
        return None
    m = re.search(r"([A-Za-z0-9+/=]{4,})\s*$", text.strip())
    if not m:
        return None
    try:
        return f"**{base64.b64decode(m.group(1), validate=True).decode('utf-8')}**"
    except (binascii.Error, UnicodeDecodeError):
        return "Это не похоже на правильный Base64 (или внутри не текст)."


@tool(CAT_TEXT, "Хеши MD5, SHA-1, SHA-256", "sha256 привет")
def hashes(text, low, s):
    m = re.search(r"\b(md5|sha-?1|sha-?256|sha-?512)\b\s*(?:хеш\w*|от|для)?\s*[:—-]?\s*(.+)", text, re.I | re.S)
    if not m:
        return None
    algo = m.group(1).lower().replace("-", "")
    body = m.group(2).strip().strip("«»\"'")
    if not body:
        return None
    h = hashlib.new(algo, body.encode("utf-8")).hexdigest()
    return f"**{algo.upper()}** от «{body}»:\n\n`{h}`"


@tool(CAT_TEXT, "Буквы алфавита", "какая по счёту буква ж")
def alphabet(text, low, s):
    m = re.search(r"(?:какая\s+по\s+сч[её]ту|номер)\s+(?:буква|буквы)\s+[«\"]?([а-яёa-z])\b", low) or re.search(r"буква\s+[«\"]?([а-яёa-z])[»\"]?\s+(?:какая\s+)?по\s+сч[её]ту", low)
    if m:
        ch = m.group(1)
        abc = _RU_ABC if ch in _RU_ABC else _EN_ABC
        return f"**«{ch.upper()}» — {abc.index(ch) + 1}-я буква** {'русского' if abc is _RU_ABC else 'английского'} алфавита (всего {len(abc)})."
    if re.search(r"(?:русский|английский|латинский)\s+алфавит|сколько\s+букв\s+в\s+(?:русском|английском)", low):
        en = re.search(r"английск|латинск", low)
        abc = _EN_ABC if en else _RU_ABC
        return f"**{'Английский' if en else 'Русский'} алфавит — {len(abc)} {skills.plural(len(abc), 'буква', 'буквы', 'букв')}:**\n\n" + " ".join(c.upper() for c in abc)
    return None


# ================================================================ ГЕНЕРАТОРЫ
CAT_GEN = "Генераторы"


@tool(CAT_GEN, "UUID", "сгенерируй uuid")
def gen_uuid(text, low, s):
    if not re.search(r"\buuid\b|\bguid\b", low):
        return None
    n = min(max(ints(low)[0] if ints(low) else 1, 1), 20)
    return "\n".join(f"`{uuid.uuid4()}`" for _ in range(n))


@tool(CAT_GEN, "Случайный цвет", "случайный цвет")
def random_color(text, low, s):
    if not re.search(r"случайн\w*\s+цвет|придумай\s+цвет|рандомн\w*\s+цвет", low):
        return None
    r, g, b = (random.randint(0, 255) for _ in range(3))
    return f"**#{r:02X}{g:02X}{b:02X}** — rgb({r}, {g}, {b})"


@tool(CAT_GEN, "Цвета: HEX ↔ RGB", "#ff8800 в rgb")
def color_convert(text, low, s):
    m = re.search(r"rgb\s*\(?\s*(\d{1,3})\s*,?\s*(\d{1,3})\s*,?\s*(\d{1,3})\s*\)?", low)
    if m and re.search(r"hex|#|шестнадцатеричн", low):
        r, g, b = (min(255, int(x)) for x in m.groups())
        return f"**rgb({r}, {g}, {b}) = #{r:02X}{g:02X}{b:02X}**"
    m = re.search(r"(?:#|hex\s*)([0-9a-f]{6}|[0-9a-f]{3})\b", low)
    if m and re.search(r"\brgb\b|в\s+ргб|цвет", low):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"**#{h.upper()} = rgb({r}, {g}, {b})**"
    return None


_NICK_A = ["Тихий", "Быстрый", "Ночной", "Лунный", "Огненный", "Северный", "Космо", "Кибер", "Пиксельный", "Неоновый", "Хитрый", "Снежный"]
_NICK_B = ["Волк", "Лис", "Кот", "Ворон", "Дракон", "Феникс", "Тигр", "Енот", "Призрак", "Самурай", "Рыцарь", "Барс"]
_NICK_EN = ["Shadow", "Pixel", "Neon", "Frost", "Storm", "Nova", "Cyber", "Lunar", "Blaze", "Echo", "Rogue", "Zen"]
_NICK_EN2 = ["Wolf", "Fox", "Raven", "Tiger", "Ghost", "Byte", "Hawk", "Viper", "Knight", "Panda", "Comet", "Ninja"]


@tool(CAT_GEN, "Ник для игр и соцсетей", "придумай ник")
def nickname(text, low, s):
    if not re.search(r"(?:придумай|сгенерируй|дай|нужен)\s+(?:мне\s+)?(?:\w+\s+)?(?:ник|никнейм|псевдоним)", low):
        return None
    out = [f"{random.choice(_NICK_A)}{random.choice(_NICK_B)}" for _ in range(3)] + \
          [f"{random.choice(_NICK_EN)}{random.choice(_NICK_EN2)}{random.randint(1, 99)}" for _ in range(4)]
    return "**Варианты ника:**\n\n" + "\n".join(f"- {n}" for n in out) + "\n\nНе понравилось — напишите ещё раз."


@tool(CAT_GEN, "Кубики (2d6, 3d20…)", "брось 2d6")
def dice(text, low, s):
    m = re.search(r"\b(\d{0,2})\s*[dдк]\s*(\d{1,3})\b", low)
    if m and re.search(r"брос|кин|кубик|dice|ролл|roll", low):
        k, sides = int(m.group(1) or 1), int(m.group(2))
    else:
        m = re.search(r"(?:брось|кинь|подбрось)\s+(\d+)\s+кубик", low)
        if not m:
            return None
        k, sides = int(m.group(1)), 6
    if not 1 <= k <= 50 or not 2 <= sides <= 1000:
        return None
    rolls = [random.randint(1, sides) for _ in range(k)]
    return f"🎲 **{' + '.join(map(str, rolls))} = {sum(rolls)}**" if k > 1 else f"🎲 **{rolls[0]}** (из {sides})"


@tool(CAT_GEN, "Числа для лотереи", "числа для лотереи 6 из 45")
def lottery(text, low, s):
    m = re.search(r"(\d+)\s+из\s+(\d+)", low)
    if not m or not re.search(r"лотере|лото|билет|угада", low):
        return None
    k, n = int(m.group(1)), int(m.group(2))
    if not 1 <= k <= n <= 100:
        return None
    return f"🍀 **{', '.join(map(str, sorted(random.sample(range(1, n + 1), k))))}**\n\n*Случайные числа — шансы у любых комбинаций одинаковые.*"
