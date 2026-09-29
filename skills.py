"""Встроенные навыки Rai. Каждый навык: функция(text) -> ответ или None."""

import ast
import operator
import os
import random
import re
import secrets
import string
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None


def _now() -> datetime:
    tz_name = os.environ.get("RAI_TZ", "Europe/Moscow")
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now(timezone(timedelta(hours=3)))


def _low(text: str) -> str:
    return (text or "").lower().replace("ё", "е").strip()


# ---------------------------------------------------------------- калькулятор

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_WORD_OPS = [
    (r"умножить на|умножь на|помножить на", "*"),
    (r"разделить на|раздели на|поделить на|делить на", "/"),
    (r"в степени", "**"),
    (r"плюс", "+"),
    (r"минус", "-"),
    (r"(?<=\d)\s*[хx×]\s*(?=\d)", "*"),
    (r"÷|:", "/"),
    (r"\^", "**"),
]


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 10**6):
            raise ValueError("слишком большая степень")
        return _OPS[type(node.op)](left, right)
    raise ValueError("недопустимое выражение")


def _fmt(num) -> str:
    if isinstance(num, float):
        if num.is_integer() and abs(num) < 1e15:
            return str(int(num))
        return f"{num:.10g}"
    return str(num)


def calculator(text: str):
    low = _low(text)
    sqrt = re.search(r"(?:квадратный\s+)?корень\s+(?:из\s+)?(-?\d+(?:[.,]\d+)?)", low)
    if sqrt:
        value = float(sqrt.group(1).replace(",", "."))
        if value < 0:
            return "Корень из отрицательного числа в действительных числах не существует."
        return f"√{_fmt(value)} = {_fmt(value ** 0.5)}"

    percent = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:от)\s*(\d+(?:[.,]\d+)?)", low)
    if percent:
        p, base = (float(x.replace(",", ".")) for x in percent.groups())
        return f"{_fmt(p)}% от {_fmt(base)} = {_fmt(base * p / 100)}"

    expr = re.sub(r"^(сколько будет|сколько|посчитай|вычисли|реши|calc|calculate)\s*", "", low)
    expr = expr.rstrip("?=! ")
    for pattern, repl in _WORD_OPS:
        expr = re.sub(pattern, repl, expr)
    expr = expr.replace(",", ".")
    if not re.fullmatch(r"[\d\s.+\-*/%()]+", expr or "x"):
        return None
    if not re.search(r"\d", expr) or not re.search(r"\d\s*[+\-*/%]", expr):
        return None
    try:
        result = _eval_node(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return "На ноль делить нельзя."
    except (ValueError, SyntaxError, TypeError, OverflowError):
        return None
    return f"{expr.strip()} = {_fmt(result)}"


# ---------------------------------------------------------------- дата и время

_WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
_MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def date_time(text: str):
    low = _low(text)
    now = _now()
    if re.search(r"который час|сколько времени|текущее время|время сейчас|какое время", low):
        return f"Сейчас {now:%H:%M}."
    if re.search(r"день недели|какой сегодня день", low):
        return f"Сегодня {_WEEKDAYS[now.weekday()]}."
    if re.search(r"какое сегодня число|какое число|сегодняшняя дата|какая дата|какой сегодня год|какой год", low):
        return (
            f"Сегодня {now.day} {_MONTHS[now.month - 1]} {now.year} года, "
            f"{_WEEKDAYS[now.weekday()]}."
        )
    return None


# ---------------------------------------------------------------- конвертер

_LENGTH = {"мм": 0.001, "см": 0.01, "дм": 0.1, "м": 1.0, "км": 1000.0,
           "дюйм": 0.0254, "фут": 0.3048, "ярд": 0.9144, "миля": 1609.344}
_MASS = {"мг": 1e-6, "г": 0.001, "кг": 1.0, "ц": 100.0, "т": 1000.0,
         "фунт": 0.45359237, "унция": 0.028349523125}
_SHORT = {"миля": "миль", "дюйм": "дюйм.", "фут": "фут.", "ярд": "ярд.", "фунт": "фунт.", "унция": "унц."}
_UNIT_ALIASES = {
    "миллиметр": "мм", "сантиметр": "см", "дециметр": "дм", "метр": "м", "километр": "км",
    "дюйм": "дюйм", "фут": "фут", "ярд": "ярд", "мил": "миля",
    "миллиграмм": "мг", "грамм": "г", "килограмм": "кг", "центнер": "ц", "тонн": "т",
    "фунт": "фунт", "унци": "унция",
    "цельси": "c", "фаренгейт": "f", "кельвин": "k",
}


def _unit(word: str):
    word = word.strip(". ")
    if word in _LENGTH or word in _MASS or word in ("c", "f", "k", "°c", "°f"):
        return word.lstrip("°")
    for prefix, unit in _UNIT_ALIASES.items():
        if word.startswith(prefix):
            return unit
    return None


def converter(text: str):
    low = _low(text)
    m = re.search(
        r"(-?\d+(?:[.,]\d+)?)\s*(°?[a-zа-я]+)\.?\s+(?:в|to|=)\s+(°?[a-zа-я]+)", low
    )
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    src, dst = _unit(m.group(2)), _unit(m.group(3))
    if not src or not dst:
        return None
    for table in (_LENGTH, _MASS):
        if src in table and dst in table:
            result = value * table[src] / table[dst]
            return f"{_fmt(value)} {_SHORT.get(src, src)} = {_fmt(round(result, 6))} {_SHORT.get(dst, dst)}"
    temps = {"c", "f", "k"}
    if src in temps and dst in temps:
        c = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[src]
        result = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[dst]
        names = {"c": "°C", "f": "°F", "k": "K"}
        return f"{_fmt(value)} {names[src]} = {_fmt(round(result, 2))} {names[dst]}"
    return "Эти единицы нельзя перевести друг в друга."


# ---------------------------------------------------------------- случайность

def randomness(text: str):
    low = _low(text)
    if re.search(r"монет", low) and re.search(r"подбрось|брось|кинь|подкинь", low):
        return random.choice(["Выпал орёл.", "Выпала решка."])
    if re.search(r"кубик", low) and re.search(r"брось|кинь|подкинь", low):
        return f"На кубике выпало {random.randint(1, 6)}."
    m = re.search(r"случайн\w* число(?:\s+от\s+(-?\d+)\s+до\s+(-?\d+))?", low)
    if m:
        a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (1, 100)
        if a > b:
            a, b = b, a
        return f"Случайное число от {a} до {b}: {random.randint(a, b)}."
    m = re.search(r"выбери\s*(?:из|между)?\s*:?\s*(.+)", low)
    if m and re.search(r",| или ", m.group(1)):
        options = [o.strip(" ?.!") for o in re.split(r",| или ", m.group(1)) if o.strip(" ?.!")]
        if len(options) >= 2:
            return f"Я выбираю: {random.choice(options)}."
    return None


# ---------------------------------------------------------------- пароли

def password(text: str):
    low = _low(text)
    if not re.search(r"пароль|password", low) or not re.search(r"сгенер|придумай|создай|generate|нов", low):
        return None
    m = re.search(r"(\d+)", low)
    length = min(max(int(m.group(1)) if m else 16, 8), 64)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)):
            return f"Надёжный пароль ({length} символов): {pwd}"


# ---------------------------------------------------------------- текст

def text_tools(text: str):
    m = re.match(r"\s*(сколько (?:слов|символов|букв) в|посчитай (?:слова|символы) в|переверни|"
                 r"заглавными|большими буквами|маленькими буквами|строчными)\s*(?:текст)?\s*:?\s*(.+)",
                 text, re.I | re.S)
    if not m:
        return None
    cmd, body = _low(m.group(1)), m.group(2).strip().strip("«»\"'")
    if not body:
        return None
    if cmd.startswith(("сколько", "посчитай")):
        words = len(re.findall(r"\w+", body))
        letters = sum(ch.isalpha() for ch in body)
        return f"Слов: {words}, символов: {len(body)}, букв: {letters}."
    if cmd == "переверни":
        return body[::-1]
    if cmd in ("заглавными", "большими буквами"):
        return body.upper()
    return body.lower()


SKILLS = {
    "calc": calculator,
    "time": date_time,
    "convert": converter,
    "random": randomness,
    "password": password,
    "text": text_tools,
}

# Порядок проверки: сначала узкие навыки, калькулятор — после конвертера.
ORDER = ["text", "password", "time", "convert", "random", "calc"]


def run(text: str, allowed) -> str:
    for name in ORDER:
        if name in allowed:
            answer = SKILLS[name](text)
            if answer:
                return answer
    return None
