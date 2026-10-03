"""Встроенные навыки Rai. Каждый навык: функция(text) -> ответ или None."""

import ast
import math
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


def plural(n: int, one: str, few: str, many: str) -> str:
    """1 день, 2 дня, 5 дней."""
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _days(n: int) -> str:
    return f"{n} {plural(n, 'день', 'дня', 'дней')}"


def _years(n: int) -> str:
    return f"{n} {plural(n, 'год', 'года', 'лет')}"


def _say_date(d) -> str:
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year} года"


# Праздники и сезоны: (название, месяц, день). Ищутся по началу слова.
_HOLIDAYS = [
    (r"нов\w* год\w*|нг\b", "Нового года", 1, 1),
    (r"рождеств\w*", "Рождества (7 января)", 1, 7),
    (r"(?:дня )?святого валентина|14 феврал\w* праздник|валентин\w*", "Дня святого Валентина", 2, 14),
    (r"23 феврал\w*|дн\w* защитника", "23 февраля", 2, 23),
    (r"8 марта|международн\w* женск\w*|женск\w* дн\w*", "8 Марта", 3, 8),
    (r"1 апрел\w*|дн\w* смеха", "1 апреля", 4, 1),
    (r"дн\w* космонавтики", "Дня космонавтики", 4, 12),
    (r"1 мая|первомай\w*|дн\w* труда", "1 Мая", 5, 1),
    (r"дн\w* победы|9 мая", "Дня Победы", 5, 9),
    (r"дн\w* знаний|1 сентябр\w*", "1 сентября", 9, 1),
    (r"хэллоуин\w*|хеллоуин\w*|halloween", "Хэллоуина", 10, 31),
    (r"конц\w* года", "конца года", 12, 31),
    (r"лет\w*", "лета", 6, 1),
    (r"осен\w*", "осени", 9, 1),
    (r"зим\w*", "зимы", 12, 1),
    (r"весн\w*", "весны", 3, 1),
]
_MONTH_RE = r"(январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*"
_MONTH_KEYS = ["январ", "феврал", "март", "апрел", "ма", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]


def _parse_date(low: str, now):
    """Дата из текста: «5 мая», «5 мая 2027», «15.06.2027», «1 января». → (date, был ли указан год) или None."""
    m = re.search(r"(\d{1,2})\s+" + _MONTH_RE + r"(?:\s+(\d{4}))?", low)
    if m:
        key = "ма" if m.group(2) in ("май", "мая") else m.group(2)
        day, month = int(m.group(1)), _MONTH_KEYS.index(key) + 1
        year = int(m.group(3)) if m.group(3) else None
    else:
        m = re.search(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b", low)
        if not m:
            return None
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else None
        if year is not None and year < 100:
            year += 2000
    try:
        return now.date().replace(year=year or now.year, month=month, day=day), year is not None
    except ValueError:
        return None


def _next(day, now, explicit_year):
    """Ближайшая такая дата: если в этом году уже прошла — в следующем."""
    if not explicit_year and day < now.date():
        try:
            return day.replace(year=day.year + 1)
        except ValueError:  # 29 февраля
            return day.replace(year=day.year + 1, day=28)
    return day


def date_math(text: str):
    """Сколько дней до даты/праздника, сколько лет прошло, какой день недели будет, через N дней, високосный год."""
    low = _low(text)
    now = _now()
    today = now.date()

    # високосный ли год
    m = re.search(r"(\d{4})\s*(?:год\w*)?\s*(?:—|-)?\s*високосн|високосн\w*\s+(?:ли\s+)?(\d{4})", low)
    if m or re.search(r"високосн\w*\s+(?:ли\s+)?(?:этот|текущий)", low):
        year = int((m.group(1) or m.group(2)) if m else today.year)
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return f"{year} год — {'високосный: в нём 366 дней, есть 29 февраля' if leap else 'не високосный: в нём 365 дней'}."

    # через N дней/недель/месяцев/лет; N дней назад
    m = re.search(r"через\s+(\d+)\s+(дн|недел|месяц|год|лет)\w*|(\d+)\s+(дн|недел|месяц|год|лет)\w*\s+назад", low)
    if m and re.search(r"какое|какой|какая|число|дат|день недели|будет|было|был", low):
        n = int(m.group(1) or m.group(3))
        unit = m.group(2) or m.group(4)
        sign = 1 if m.group(1) else -1
        if n > 100000:
            return None
        if unit in ("дн", "недел"):
            day = today + timedelta(days=sign * n * (7 if unit == "недел" else 1))
        else:
            months = n * (12 if unit in ("год", "лет") else 1) * sign
            y, mo = divmod(today.month - 1 + months, 12)
            year = today.year + y
            if not 1 <= year <= 9999:
                return None
            mo += 1
            last = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
                    31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
            day = today.replace(year=year, month=mo, day=min(today.day, last))
        span = f"{n} " + {"дн": plural(n, "день", "дня", "дней"), "недел": plural(n, "неделю", "недели", "недель"),
                          "месяц": plural(n, "месяц", "месяца", "месяцев")}.get(unit, plural(n, "год", "года", "лет"))
        when = f"Через {span} будет" if sign > 0 else f"{span.capitalize()} назад было"
        return f"{when} **{_say_date(day)}**, {_WEEKDAYS[day.weekday()]}."

    # какой день недели был/будет <дата>
    if re.search(r"день недели|какой (?:это )?день|в какой день", low):
        parsed = _parse_date(low, now)
        if parsed:
            day, _ = parsed
            verb = ("был", "был", "была", "был", "была", "была", "было")[day.weekday()] if day < today else (
                "будет" if day > today else "— это сегодня,")
            return f"{_say_date(day)} {verb} **{_WEEKDAYS[day.weekday()]}**."

    # сколько лет прошло с 1945 года / сколько лет назад был 1961 / сколько мне лет, если я родился в 2005
    m = re.search(r"сколько\s+(?:мне\s+)?лет\b.*?\b(1\d{3}|20\d{2})\b|(?:родил\w*|рождени\w*)\D{0,20}(1\d{3}|20\d{2})|(1\d{3}|20\d{2})\s*(?:года?)?\s*рождени", low)
    if m and re.search(r"сколько|лет|возраст", low):
        year = int(m.group(1) or m.group(2) or m.group(3))
        if re.search(r"родил|рождени|мне\s+лет|возраст", low):
            age = today.year - year
            if age < 0:
                return None
            return (f"Если родились в {year} году, сейчас вам **{_years(age - 1)}** или **{_years(age)}** — "
                    f"смотря, был ли уже день рождения в {today.year} году.")
        diff = today.year - year
        if diff > 0:
            return f"С {year} года прошло **{_years(diff)}** (сейчас {today.year} год)."
        if diff < 0:
            return f"До {year} года осталось **{_years(-diff)}**."
        return f"{year} год — это текущий год."

    # сколько дней до <праздника/даты>; сколько дней прошло с <даты>
    if not re.search(r"сколько\s+(?:\w+\s+)?(?:дн|недел|месяц)|сколько осталось|скоро ли|когда будет", low):
        return None
    m = re.search(r"\bдо\s+(.+)", low)
    since = re.search(r"\b(?:с|со)\s+(.+?)\s+прошло|прошло\s+(?:\w+\s+)?(?:с|со)\s+(.+)", low)
    target = (m.group(1) if m else "") or (since and (since.group(1) or since.group(2))) or ""
    target = target.strip(" ?!.")
    if not target:
        return None
    name, day = None, None
    if re.match(r"выходн", target) and today.weekday() >= 5:
        return "Выходные уже идут — отдыхайте! 🎉"
    if re.match(r"выходн|суббот", target):
        day = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
        name = "выходных (субботы)"
    elif re.match(r"конц\w* месяц", target):
        nxt = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        day, name = nxt - timedelta(days=1), "конца месяца"
    elif re.match(r"конц\w* недел", target):
        day, name = today + timedelta(days=6 - today.weekday()), "конца недели (воскресенья)"
    else:
        for i, wd in enumerate(("понедельник", "вторник", "сред", "четверг", "пятниц", "суббот", "воскресен")):
            if target.startswith(wd):
                day, name = today + timedelta(days=(i - today.weekday()) % 7 or 7), _WEEKDAYS[i] if i in (0, 1, 3) else {
                    2: "среды", 4: "пятницы", 5: "субботы", 6: "воскресенья"}[i]
                break
    if day is None:
        parsed = _parse_date(target, now)
        if parsed:
            raw, explicit = parsed
            day = raw if since else _next(raw, now, explicit)
            name = _say_date(day)
    if day is None:
        for pattern, title, month, dd in _HOLIDAYS:
            if re.match(pattern, target):
                day = _next(today.replace(month=month, day=dd), now, False)
                name = title
                break
    if day is None:
        return None
    diff = (day - today).days
    if since or diff < 0:
        diff = abs(diff)
        return f"С {name} прошло **{_days(diff)}**" + (f" (≈ {_years(diff // 365)})." if diff >= 730 else ".")
    if diff == 0:
        return f"Это сегодня — {_say_date(day)}! 🎉"
    weeks = f" — это {diff // 7} {plural(diff // 7, 'неделя', 'недели', 'недель')}" + (
        f" и {_days(diff % 7)}" if diff % 7 else "") if diff >= 14 else ""
    return f"До {name} осталось **{_days(diff)}**{weeks}. Дата: {_say_date(day)}, {_WEEKDAYS[day.weekday()]}."


def date_time(text: str):
    low = _low(text)
    now = _now()
    calc = date_math(text)
    if calc:
        return calc
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
           "дюйм": 0.0254, "фут": 0.3048, "ярд": 0.9144, "миля": 1609.344, "морская миля": 1852.0}
_MASS = {"мг": 1e-6, "г": 0.001, "кг": 1.0, "ц": 100.0, "т": 1000.0,
         "фунт": 0.45359237, "унция": 0.028349523125, "карат": 0.0002}
_TIME = {"мс": 0.001, "с": 1.0, "мин": 60.0, "ч": 3600.0, "сут": 86400.0, "нед": 604800.0, "год": 31536000.0}
_DATA = {"бит": 0.125, "байт": 1.0, "кб": 1024.0, "мб": 1024.0 ** 2, "гб": 1024.0 ** 3, "тб": 1024.0 ** 4}
_VOLUME = {"мл": 0.001, "л": 1.0, "м3": 1000.0, "галлон": 3.785411784, "стакан": 0.25, "ст. ложка": 0.015, "ч. ложка": 0.005}
_AREA = {"м2": 1.0, "км2": 1e6, "га": 1e4, "сотка": 100.0, "акр": 4046.8564224, "см2": 1e-4}
_SPEED = {"м/с": 1.0, "км/ч": 1 / 3.6, "миль/ч": 0.44704, "узел": 0.514444}
_TABLES = (_LENGTH, _MASS, _TIME, _DATA, _VOLUME, _AREA, _SPEED)
_SHORT = {"м2": "м²", "км2": "км²", "см2": "см²", "м3": "м³", "сут": "сут.", "нед": "нед.",
          "кб": "КБ", "мб": "МБ", "гб": "ГБ", "тб": "ТБ"}
# Единицы-слова склоняются: 1 миля, 2 мили, 5 миль, 2,5 мили
_FORMS = {"миля": ("миля", "мили", "миль"), "морская миля": ("морская миля", "морские мили", "морских миль"),
          "дюйм": ("дюйм", "дюйма", "дюймов"), "фут": ("фут", "фута", "футов"), "ярд": ("ярд", "ярда", "ярдов"),
          "фунт": ("фунт", "фунта", "фунтов"), "унция": ("унция", "унции", "унций"), "карат": ("карат", "карата", "карат"),
          "год": ("год", "года", "лет"), "галлон": ("галлон", "галлона", "галлонов"), "стакан": ("стакан", "стакана", "стаканов"),
          "сотка": ("сотка", "сотки", "соток"), "акр": ("акр", "акра", "акров"), "узел": ("узел", "узла", "узлов"),
          "бит": ("бит", "бита", "бит"), "байт": ("байт", "байта", "байт"),
          "ст. ложка": ("ст. ложка", "ст. ложки", "ст. ложек"), "ч. ложка": ("ч. ложка", "ч. ложки", "ч. ложек")}


def _num(x) -> str:
    """Число по-русски: 62,14 · 1 000 000 · 0,000125."""
    if abs(x - round(x)) < 1e-9 and abs(x) < 1e15:
        return f"{int(round(x)):,}".replace(",", " ")
    digits = 4 if abs(x) >= 0.01 else min(int(-math.floor(math.log10(abs(x)))) + 3, 15)
    text = f"{x:.{digits}f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _name(unit, value) -> str:
    forms = _FORMS.get(unit)
    if not forms:
        return _SHORT.get(unit, unit)
    if abs(value - round(value)) > 1e-9:
        return "морской мили" if unit == "морская миля" else forms[1]
    return plural(int(round(value)), *forms)


# Порядок важен: длинные названия раньше коротких («миллилитр» раньше «мил[я]», «килобайт» раньше «кило»).
_UNIT_ALIASES = {
    "миллисекунд": "мс", "миллиметр": "мм", "миллиграмм": "мг", "миллилитр": "мл",
    "сантиметр": "см", "дециметр": "дм", "километр": "км", "метр": "м",
    "морск": "морская миля", "дюйм": "дюйм", "фут": "фут", "ярд": "ярд", "мил": "миля",
    "килобайт": "кб", "мегабайт": "мб", "гигабайт": "гб", "терабайт": "тб",
    "грамм": "г", "килограмм": "кг", "кило": "кг", "центнер": "ц", "тонн": "т", "фунт": "фунт", "унци": "унция",
    "карат": "карат", "секунд": "с", "сек": "с", "минут": "мин", "мин": "мин", "час": "ч", "сут": "сут",
    "дня": "сут", "день": "сут", "дней": "сут", "дне": "сут", "недел": "нед", "год": "год", "лет": "год",
    "бит": "бит", "байт": "байт",
    "литр": "л", "галлон": "галлон", "стакан": "стакан", "гектар": "га", "сотк": "сотка", "сото": "сотка", "акр": "акр",
    "узл": "узел", "узел": "узел",
    "цельси": "c", "фаренгейт": "f", "кельвин": "k",
}
_EXACT_UNITS = {"кб": "кб", "мб": "мб", "гб": "гб", "тб": "тб", "kb": "кб", "mb": "мб", "gb": "гб", "tb": "тб",
                "л": "л", "мл": "мл", "га": "га", "с": "с", "ч": "ч", "мин": "мин", "мс": "мс",
                "м2": "м2", "м²": "м2", "кв м": "м2", "км2": "км2", "км²": "км2", "м3": "м3", "м³": "м3", "куб м": "м3",
                "км/ч": "км/ч", "кмч": "км/ч", "м/с": "м/с", "миль/ч": "миль/ч", "mph": "миль/ч",
                "c": "c", "f": "f", "k": "k", "°c": "c", "°f": "f", "°": "c"}


def _unit(word: str):
    word = word.strip(". ")
    if word in _EXACT_UNITS:
        return _EXACT_UNITS[word]
    for table in _TABLES:
        if word in table:
            return word
    if re.fullmatch(r"(?:квадратн\w*|кв\.?)\s*(?:метр\w*|м)", word):
        return "м2"
    if re.fullmatch(r"(?:квадратн\w*|кв\.?)\s*(?:километр\w*|км)", word):
        return "км2"
    if re.fullmatch(r"(?:кубическ\w*|куб\.?)\s*(?:метр\w*|м)", word):
        return "м3"
    if re.fullmatch(r"(?:километр\w*|км)\s*(?:в|/)\s*(?:час\w*|ч)", word):
        return "км/ч"
    if re.fullmatch(r"(?:метр\w*|м)\s*(?:в|/)\s*(?:секунд\w*|с|сек)", word):
        return "м/с"
    for prefix, unit in _UNIT_ALIASES.items():
        if word.startswith(prefix):
            return unit
    return None


# «км/ч», «квадратных метров», «кубических метров», «метров в секунду» — единицы из двух слов
_UNIT_WORD = (r"(?:(?:квадратн\w*|кв\.?|кубическ\w*|куб\.?)\s+[a-zа-я]+|(?:километр\w*|км)\s*(?:/|в\s+)(?:час\w*|ч)\b|"
              r"(?:метр\w*|м)\s*(?:/|в\s+)(?:секунд\w*|сек|с)\b|(?:морск\w*\s+мил\w*)|"
              r"миль/ч|°?[a-zа-я]+[23²³]?(?:/[a-zа-я]+)?)")


def _convert(value, src, dst):
    for table in _TABLES:
        if src in table and dst in table:
            result = value * table[src] / table[dst]
            note = " (в високосном году — 366 дней)" if "год" in (src, dst) and "сут" in (src, dst) else ""
            return f"{_num(value)} {_name(src, value)} = **{_num(result)}** {_name(dst, result)}{note}"
    temps = {"c", "f", "k"}
    if src in temps and dst in temps:
        c = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[src]
        result = {"c": c, "f": c * 9 / 5 + 32, "k": c + 273.15}[dst]
        names = {"c": "°C", "f": "°F", "k": "K"}
        return f"{_num(value)} {names[src]} = **{_num(round(result, 2))}** {names[dst]}"
    return None


def converter(text: str):
    low = _low(text)
    # «сколько секунд в часе», «сколько в часе секунд», «сколько метров в километре», «сколько грамм в фунте»
    m = (re.search(r"сколько\s+(" + _UNIT_WORD + r")\s+(?:в|во)\s+(?:(одн\w*|\d+(?:[.,]\d+)?)\s+)?(" + _UNIT_WORD + r")\s*\??$", low)
         or re.search(r"сколько\s+(?:в|во)\s+(?:(одн\w*|\d+(?:[.,]\d+)?)\s+)?(" + _UNIT_WORD + r")\s+(" + _UNIT_WORD + r")\s*\??$", low))
    if m:
        if m.re.pattern.startswith(r"сколько\s+(?:в"):
            count, src, dst = m.group(1), m.group(2), m.group(3)
        else:
            dst, count, src = m.group(1), m.group(2), m.group(3)
        src_u, dst_u = _unit(src), _unit(dst)
        if src_u and dst_u and src_u != dst_u:
            value = float(count.replace(",", ".")) if count and count[0].isdigit() else 1.0
            return _convert(value, src_u, dst_u)
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(" + _UNIT_WORD + r")\.?\s+(?:в|во|to|=|->|→)\s+(" + _UNIT_WORD + r")", low)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    src, dst = _unit(m.group(2)), _unit(m.group(3))
    if not src or not dst:
        return None
    return _convert(value, src, dst) or "Эти единицы нельзя перевести друг в друга."


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


# ---------------------------------------------------------------- таблицы

def times_table(text: str):
    low = _low(text)
    m = re.search(r"таблиц\w* умножения(?:\s+(?:на|для))?\s*(\d+)?", low)
    if not m:
        return None
    n = int(m.group(1)) if m.group(1) else None
    if n is not None:
        if not 1 <= n <= 1000:
            return None
        rows = "\n".join(f"| {n} × {k} | **{n * k}** |" for k in range(1, 11))
        return f"### Таблица умножения на {n}\n\n| Пример | Ответ |\n|---|---|\n{rows}"
    head = "| × | " + " | ".join(str(k) for k in range(1, 10)) + " |"
    sep = "|---" * 10 + "|"
    body = "\n".join(
        f"| **{a}** | " + " | ".join(str(a * b) for b in range(1, 10)) + " |" for a in range(1, 10)
    )
    return f"### Таблица умножения\n\n{head}\n{sep}\n{body}"


# ---------------------------------------------------------------- столицы

CAPITALS = {
    "россия": "Москва", "украина": "Киев", "беларусь": "Минск", "белоруссия": "Минск", "казахстан": "Астана",
    "узбекистан": "Ташкент", "киргизия": "Бишкек", "кыргызстан": "Бишкек", "таджикистан": "Душанбе",
    "туркменистан": "Ашхабад", "азербайджан": "Баку", "армения": "Ереван", "грузия": "Тбилиси",
    "молдова": "Кишинёв", "молдавия": "Кишинёв", "латвия": "Рига", "литва": "Вильнюс", "эстония": "Таллин",
    "польша": "Варшава", "германия": "Берлин", "франция": "Париж", "италия": "Рим", "испания": "Мадрид",
    "португалия": "Лиссабон", "великобритания": "Лондон", "англия": "Лондон", "ирландия": "Дублин",
    "нидерланды": "Амстердам", "голландия": "Амстердам", "бельгия": "Брюссель", "швейцария": "Берн",
    "австрия": "Вена", "чехия": "Прага", "словакия": "Братислава", "венгрия": "Будапешт", "румыния": "Бухарест",
    "болгария": "София", "сербия": "Белград", "хорватия": "Загреб", "греция": "Афины", "турция": "Анкара",
    "швеция": "Стокгольм", "норвегия": "Осло", "финляндия": "Хельсинки", "дания": "Копенгаген",
    "исландия": "Рейкьявик", "сша": "Вашингтон", "америка": "Вашингтон", "канада": "Оттава",
    "мексика": "Мехико", "бразилия": "Бразилиа", "аргентина": "Буэнос-Айрес", "чили": "Сантьяго",
    "перу": "Лима", "колумбия": "Богота", "куба": "Гавана", "китай": "Пекин", "япония": "Токио",
    "корея": "Сеул", "южная корея": "Сеул", "северная корея": "Пхеньян", "индия": "Нью-Дели",
    "пакистан": "Исламабад", "иран": "Тегеран", "ирак": "Багдад", "израиль": "Иерусалим",
    "саудовская аравия": "Эр-Рияд", "оаэ": "Абу-Даби", "египет": "Каир", "египта": "Каир",
    "марокко": "Рабат", "нигерия": "Абуджа", "кения": "Найроби", "юар": "Претория",
    "австралия": "Канберра", "новая зеландия": "Веллингтон", "таиланд": "Бангкок", "вьетнам": "Ханой",
    "индонезия": "Джакарта", "монголия": "Улан-Батор", "афганистан": "Кабул", "сирия": "Дамаск",
}


def capital(text: str):
    low = _low(text)
    m = re.search(r"столиц\w*\s+(?:страны\s+|государства\s+)?([а-я -]+?)[?!.]*$", low)
    if not m:
        return None
    import nlp  # локальный импорт: skills не зависит от nlp при загрузке
    want = [nlp.stem(w) for w in m.group(1).split()]
    for country, city in sorted(CAPITALS.items(), key=lambda kv: -len(kv[0])):
        parts = [nlp.stem(w) for w in country.split()]
        if want[:len(parts)] == parts:
            return f"Столица — **{city}**."
    return None


SKILLS = {
    "calc": calculator,
    "time": date_time,
    "convert": converter,
    "random": randomness,
    "password": password,
    "text": text_tools,
    "table": times_table,
    "capital": capital,
}

# Порядок проверки: сначала узкие навыки, калькулятор — после конвертера.
ORDER = ["text", "table", "capital", "password", "time", "convert", "random", "calc"]


def run(text: str, allowed) -> str:
    for name in ORDER:
        if name in allowed:
            answer = SKILLS[name](text)
            if answer:
                return answer
    return None
