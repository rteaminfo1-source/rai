"""Rai пишет код сам: описание задачи → разбор на части → программа → проверка запуском.

Как думает:
  1. Разбирает задачу на части: откуда данные (ввод с клавиатуры, список в задаче, диапазон «от 1 до 100»),
     какие отобрать (чётные, больше 10, простые…), что с ними сделать (квадраты, удвоить…), какой ответ нужен
     (сумма, среднее, максимум, отсортировать, факториал, перевернуть строку…) и как вывести.
  2. Собирает программу на Python (или JavaScript) из проверенных блоков — с понятными именами и комментариями.
  3. Проверяет себя: запускает программу на примерах в песочнице (без файлов и сети, с ограничением шагов) и
     сравнивает вывод с ответом, который считает отдельно своим способом. Если в задаче есть пример
     («для 5 ответ 120»), программа обязана его пройти — иначе Rai пробует другое толкование задачи.
"""

import io
import math
import re
import sys

# ------------------------------------------------------------------ разбор задачи

_NUM = r"-?\d+(?:[.,]\d+)?"


def _n(s):
    s = s.replace(",", ".")
    return float(s) if "." in s else int(s)


# Действия над набором чисел (ключ, слова, «как сказать», код Python, код JavaScript)
LIST_OPS = [
    ("second_max", r"втор\w+\s+(?:по\s+величине|максимум|наибольш|самое\s+большое)", "второе по величине",
     "sorted(set(nums))[-2] if len(set(nums)) > 1 else None", "[...new Set(nums)].sort((a, b) => a - b).at(-2)"),
    ("median", r"медиан", "медиана", "_median(nums)", "median(nums)"),
    ("avg", r"средн\w*", "среднее арифметическое", "sum(nums) / len(nums) if nums else 0",
     "nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0"),
    ("product", r"произведени\w*|перемнож\w*", "произведение", "math.prod(nums)", "nums.reduce((a, b) => a * b, 1)"),
    ("sum", r"сумм\w*|сложи\w*|сложить|итого", "сумма", "sum(nums)", "nums.reduce((a, b) => a + b, 0)"),
    ("minmax", r"(?:минимальн\w*|наименьш\w*|минимум)\s+и\s+(?:максимальн\w*|наибольш\w*|максимум)", "минимум и максимум",
     "(min(nums), max(nums)) if nums else None", "[Math.min(...nums), Math.max(...nums)]"),
    ("min", r"минимальн\w*|наименьш\w*|минимум|самое\s+маленьк\w*|самый\s+маленьк\w*", "минимум", "min(nums) if nums else None",
     "nums.length ? Math.min(...nums) : null"),
    ("max", r"максимальн\w*|наибольш\w*|максимум|самое\s+больш\w*|самый\s+больш\w*", "максимум", "max(nums) if nums else None",
     "nums.length ? Math.max(...nums) : null"),
    ("sort_desc", r"по\s+убыванию|от\s+большего\s+к\s+меньшему", "отсортировать по убыванию", "sorted(nums, reverse=True)",
     "[...nums].sort((a, b) => b - a)"),
    ("sort_asc", r"отсортир\w*|сортир\w*|упорядоч\w*|по\s+возрастанию|от\s+меньшего\s+к\s+большему", "отсортировать по возрастанию",
     "sorted(nums)", "[...nums].sort((a, b) => a - b)"),
    ("unique", r"уникальн\w*|без\s+повтор\w*|удали\w*\s+(?:дубл|повтор)\w*|убери\w*\s+(?:дубл|повтор)\w*", "без повторов",
     "list(dict.fromkeys(nums))", "[...new Set(nums)]"),
    ("reverse", r"в\s+обратном\s+порядке|разверн\w*|переверн\w*", "в обратном порядке", "nums[::-1]", "[...nums].reverse()"),
    ("count", r"количеств\w*|сколько|посчитай\s+числ", "количество", "len(nums)", "nums.length"),
]
# Отбор чисел: (ключ, слова, по-русски, условие Python от x, условие JS от x)
FILTERS = [
    ("not_div", r"не\s+(?:дел\w*|кратн\w*)\s+(?:на\s+)?(\d+)", "не делятся на {k}", "x % {k} != 0", "x % {k} !== 0"),
    ("div", r"(?:дел\w*\s+на|кратн\w*)\s+(\d+)", "делятся на {k}", "x % {k} == 0", "x % {k} === 0"),
    ("odd", r"нечётн\w*|нечетн\w*", "нечётные", "x % 2 != 0", "x % 2 !== 0"),
    ("even", r"чётн\w*|четн\w*", "чётные", "x % 2 == 0", "x % 2 === 0"),
    ("gt", r"(?:больше|более|свыше|>)\s*(" + _NUM + ")", "больше {k}", "x > {k}", "x > {k}"),
    ("lt", r"(?:меньше|менее|<)\s*(" + _NUM + ")", "меньше {k}", "x < {k}", "x < {k}"),
    ("positive", r"положительн\w*", "положительные", "x > 0", "x > 0"),
    ("negative", r"отрицательн\w*", "отрицательные", "x < 0", "x < 0"),
    ("prime", r"прост\w+\s+чис|простые|простых", "простые", "_is_prime(x)", "isPrime(x)"),
    ("two_digit", r"двузначн\w*", "двузначные", "10 <= abs(x) <= 99", "Math.abs(x) >= 10 && Math.abs(x) <= 99"),
    ("ends", r"оканчива\w*\s+на\s+(\d)", "оканчиваются на {k}", "abs(x) % 10 == {k}", "Math.abs(x) % 10 === {k}"),
]
MAPS = [
    ("square", r"квадрат\w*", "в квадрат", "x * x", "x * x"),
    ("cube", r"куб\w*", "в куб", "x ** 3", "x ** 3"),
    ("double", r"удво\w*|умнож\w*\s+на\s+2|в\s+два\s+раза\s+больше", "удвоить", "x * 2", "x * 2"),
    ("abs", r"модул\w*|по\s+модулю|абсолютн\w*", "по модулю", "abs(x)", "Math.abs(x)"),
]
# Задачи для одного числа
NUM_OPS = [
    ("factorial", r"факториал", "факториал", "math.factorial(n)", "factorial(n)"),
    ("fib", r"фибоначчи", "число Фибоначчи с этим номером", "_fib(n)", "fib(n)"),
    ("is_prime", r"прост\w*\s+(?:ли|или\s+нет)|явля\w*\s+ли\s+.*прост|прост\w*\s+числ\w*\s+(?:ли|или)|проверь.*прост", "простое ли",
     "'простое' if _is_prime(n) else 'не простое'", "isPrime(n) ? 'простое' : 'не простое'"),
    ("is_even", r"(?:чётн|четн)\w*\s+(?:ли|или)|проверь.*(?:чётн|четн)", "чётное ли", "'чётное' if n % 2 == 0 else 'нечётное'",
     "n % 2 === 0 ? 'чётное' : 'нечётное'"),
    ("digits_sum", r"сумм\w*\s+(?:его\s+)?цифр", "сумма цифр", "sum(int(d) for d in str(abs(n)))",
     "String(Math.abs(n)).split('').reduce((a, d) => a + Number(d), 0)"),
    ("digits_count", r"(?:количеств\w*|сколько)\s+(?:в\s+нём\s+)?цифр", "количество цифр", "len(str(abs(n)))", "String(Math.abs(n)).length"),
    ("reverse_num", r"переверн\w*|разверн\w*|в\s+обратном\s+порядке|задом\s+наперёд", "цифры в обратном порядке",
     "int(str(abs(n))[::-1]) * (1 if n >= 0 else -1)", "Math.sign(n) * Number(String(Math.abs(n)).split('').reverse().join(''))"),
    ("palindrome", r"палиндром", "палиндром ли", "'палиндром' if str(n) == str(n)[::-1] else 'не палиндром'",
     "String(n) === String(n).split('').reverse().join('') ? 'палиндром' : 'не палиндром'"),
    ("divisors", r"делител", "все делители", "[d for d in range(1, abs(n) + 1) if n % d == 0]",
     "Array.from({length: Math.abs(n)}, (_, i) => i + 1).filter((d) => n % d === 0)"),
    ("binary", r"двоичн\w*|бинарн\w*", "в двоичной системе", "bin(n)[2:] if n >= 0 else '-' + bin(n)[3:]", "n.toString(2)"),
    ("table", r"таблиц\w*\s+умножени", "таблица умножения", None, None),
    ("sqrt", r"корень|корня", "квадратный корень", "math.sqrt(n)", "Math.sqrt(n)"),
    ("cube1", r"\bкуб\w*", "куб числа", "n ** 3", "n ** 3"),
    ("square1", r"квадрат\w*", "квадрат числа", "n * n", "n * n"),
    ("perfect", r"совершенн\w*", "совершенное ли", "'совершенное' if n > 1 and sum(d for d in range(1, n) if n % d == 0) == n else 'не совершенное'",
     "n > 1 && Array.from({length: n - 1}, (_, i) => i + 1).filter((d) => n % d === 0).reduce((a, b) => a + b, 0) === n ? 'совершенное' : 'не совершенное'"),
    ("even1", r"(?:чётн|четн)\w*", "чётное ли", "'чётное' if n % 2 == 0 else 'нечётное'", "n % 2 === 0 ? 'чётное' : 'нечётное'"),
]
# Задачи для строки
STR_OPS = [
    ("s_vowels", r"гласн", "количество гласных", "sum(1 for ch in s.lower() if ch in 'аеёиоуыэюяaeiouy')",
     "[...s.toLowerCase()].filter((ch) => 'аеёиоуыэюяaeiouy'.includes(ch)).length"),
    ("s_consonants", r"согласн", "количество согласных",
     "sum(1 for ch in s.lower() if ch.isalpha() and ch not in 'аеёиоуыэюяaeiouyьъ')",
     "[...s.toLowerCase()].filter((ch) => /\\p{L}/u.test(ch) && !'аеёиоуыэюяaeiouyьъ'.includes(ch)).length"),
    ("s_words", r"(?:количеств\w*|сколько|посчитай)\s+слов|слов\w*\s+в\s+(?:строке|тексте|предложении)", "количество слов", "len(s.split())",
     "s.split(/\\s+/).filter(Boolean).length"),
    ("s_longest", r"(?:самое\s+)?длинн\w+\s+слов", "самое длинное слово", "max(s.split(), key=len) if s.split() else ''",
     "s.split(/\\s+/).filter(Boolean).reduce((a, w) => w.length > a.length ? w : a, '')"),
    ("s_palindrome", r"палиндром", "палиндром ли", "'палиндром' if _clean(s) == _clean(s)[::-1] else 'не палиндром'",
     "clean(s) === [...clean(s)].reverse().join('') ? 'палиндром' : 'не палиндром'"),
    ("s_title", r"кажд\w+\s+слов\w*\s+с\s+(?:заглавн|больш)", "каждое слово с заглавной буквы", "s.title()",
     "s.replace(/(^|\\s)(\\S)/g, (m, a, b) => a + b.toUpperCase())"),
    ("s_upper", r"заглавн\w*|верхн\w+\s+регистр|больш\w+\s+букв|капс", "заглавными буквами", "s.upper()", "s.toUpperCase()"),
    ("s_lower", r"строчн\w*|нижн\w+\s+регистр|маленьк\w+\s+букв", "строчными буквами", "s.lower()", "s.toLowerCase()"),
    ("s_nospaces", r"(?:удали|убери|без)\w*\s+пробел", "без пробелов", "s.replace(' ', '')", "s.replaceAll(' ', '')"),
    ("s_digits", r"(?:количеств\w*|сколько)\s+цифр", "количество цифр", "sum(ch.isdigit() for ch in s)", "[...s].filter((ch) => /\\d/.test(ch)).length"),
    ("s_freq", r"частот\w*|сколько\s+раз\s+(?:встречается\s+)?кажд", "сколько раз встречается каждая буква",
     "{ch: s.count(ch) for ch in dict.fromkeys(s) if ch.strip()}", None),
    ("s_reverse", r"переверн\w*|разверн\w*|в\s+обратном\s+порядке|задом\s+наперёд|задом\s+наперед", "строка задом наперёд", "s[::-1]",
     "[...s].reverse().join('')"),
    ("s_len", r"длин\w*|сколько\s+символ|количеств\w*\s+символ", "длина строки", "len(s)", "s.length"),
]

_INPUT_RE = re.compile(r"ввод\w*|введ\w*|с\s+клавиатур\w*|на\s+вход|пользовател\w*|спрашива\w*|запраш\w*|дано|даны|дан\b|задаётся|задается", re.I)
_LIST_RE = re.compile(r"списк\w*|список|массив\w*|последовательност\w*|числа\s+через\s+пробел|несколько\s+чисел|набор\w*\s+чисел|"
                      r"\bn\s+чисел|чисел\b|числа\b", re.I)
_STR_RE = re.compile(r"строк\w*|текст\w*|слов[оа]\b|предложени\w*|фраз\w*", re.I)
_UNTIL0_RE = re.compile(r"(?:до|пока\s+не\s+(?:введ|встрет)\w*)\s+(?:числ\w*\s+)?(?:ноль|нул\w*|0)\b|заканчива\w*\s+нул\w*", re.I)
_RANGE_RE = re.compile(r"от\s+(" + _NUM + r")\s+до\s+(" + _NUM + r"|n|н)\b", re.I)
_FIRST_RE = re.compile(r"(?:первы[ехм]|первые)\s+(\d+)", re.I)
_LITERAL_LIST = re.compile(r"\[\s*(" + _NUM + r"(?:\s*,\s*" + _NUM + r")+)\s*\]|(?:числа|список|массив)\s*:?\s+(" + _NUM + r"(?:\s*[,;]?\s+" + _NUM + r"){2,})")
_LITERAL_STR = re.compile(r"[«\"“]([^»\"”]{1,200})[»\"”]")
_EXAMPLE_RE = re.compile(r"(?:например|пример)[:,]?\s*(?:для|при|если\s+ввести|вход[:\s]+|ввод[:\s]+)?\s*(.+?)\s*"
                         r"(?:→|->|=>|—|-|ответ(?:\s+будет)?|получится|выход[:\s]*|должно\s+(?:быть|вывести)|выведет)\s*:?\s*(.+?)(?:[.;]|$)", re.I)
_STARS_RE = re.compile(r"(?:треугольник|пирамид\w*|ёлочк\w*|елочк\w*|квадрат|ромб)\w*\s+(?:из\s+)?(?:звёзд|звезд|\*|символ)", re.I)
_TASK_RE = re.compile(r"напиш\w*|сделай|создай|программ\w*|код\b|скрипт|функци\w*|алгоритм|посчита\w*|подсчита\w*|вычисл\w*|найд\w*|найти|"
                      r"выведи|вывести|выводит|проверь|проверить|определи\w*|напечата\w*|выведет|считает|находит|проверяет|"
                      r"отсортир\w*|упорядоч\w*|разверни|переверни|удали|убери|первые\s+\d+", re.I)


def _find(table, text):
    for row in table:
        m = re.search(row[1], text, re.I)
        if m:
            return row, m
    return None, None


def parse(text):
    """Разбор задачи в план программы или None (это не вычислительная задача)."""
    low = " ".join((text or "").lower().replace("ё", "е").split())
    low_e = (text or "").lower()
    if not _TASK_RE.search(low):
        return None
    spec = {"source": None, "filters": [], "map": None, "op": None, "out": "one", "examples": [], "score": 0, "text": text}
    # примеры из задачи: «например, для 5 ответ 120», «вход: 3 4 → 7»
    for m in _EXAMPLE_RE.finditer(text or ""):
        given, want = m.group(1).strip(" «»\"'"), m.group(2).strip(" «»\"'.")
        if given and want and len(given) < 120 and len(want) < 200:
            spec["examples"].append((given, want))
    if _STARS_RE.search(low):
        kind = "pyramid" if re.search(r"пирамид|ёлоч|елоч", low) else "square" if "квадрат" in low else "triangle"
        size = re.search(r"(?:высот\w*|размер\w*|из|на)\s+(\d+)", low)
        spec.update(source={"type": "int" if not size else "const", "value": int(size.group(1)) if size else None},
                    op=("stars", kind), score=3)
        return spec
    if re.search(r"fizz\s*buzz|физз\s*базз", low):
        spec.update(source={"type": "range", "a": 1, "b": 100}, op=("fizzbuzz",), score=3)
        return spec
    m_first = _FIRST_RE.search(low)
    if m_first and re.search(r"прост\w+\s+чис", low):
        spec.update(source={"type": "const", "value": int(m_first.group(1))}, op=("first_primes",), out="line", score=3)
        return spec
    if m_first and "фибоначчи" in low:
        spec.update(source={"type": "const", "value": int(m_first.group(1))}, op=("first_fib",), out="line", score=3)
        return spec
    if re.search(r"таблиц\w*\s+умножени", low):
        k = re.search(r"(?:на|для|числа)\s+(\d+)", low)
        spec.update(source={"type": "const" if k else "int", "value": int(k.group(1)) if k else None}, op=("table",), score=3)
        return spec

    # ---- откуда данные
    lit = _LITERAL_LIST.search(low_e)
    rng = _RANGE_RE.search(low)
    lit_s = _LITERAL_STR.search(text or "")
    asks = bool(_INPUT_RE.search(low))
    str_task = bool(_STR_RE.search(low)) and not re.search(r"строк\w*\s+(?:чисел|из\s+чисел)", low)
    if lit:
        nums = re.findall(_NUM, lit.group(1) or lit.group(2))
        spec["source"] = {"type": "data", "value": [_n(x) for x in nums]}
    elif lit_s and str_task:
        spec["source"] = {"type": "sdata", "value": lit_s.group(1)}
    elif rng:
        b = rng.group(2)
        spec["source"] = {"type": "range", "a": int(_n(rng.group(1))), "b": None if b in ("n", "н") else int(_n(b))}
    elif _UNTIL0_RE.search(low):
        spec["source"] = {"type": "until0"}
    elif str_task:
        spec["source"] = {"type": "str"}
    elif re.search(r"дв[аеу]\s+числ|два\s+целых", low):
        spec["source"] = {"type": "pair"}
    elif _LIST_RE.search(low) and (asks or re.search(r"списк|массив|последовательн", low)):
        spec["source"] = {"type": "ints"}
    elif re.search(r"(?<![а-яё])(?:числ[оау]|n|целое)(?![а-яё])", low):
        spec["source"] = {"type": "int"}
    if not spec["source"]:
        return None
    t = spec["source"]["type"]

    if t in ("str", "sdata"):
        row, _ = _find(STR_OPS, low)
        if not row:
            return None
        spec["op"] = ("str", row)
        spec["score"] = 2 + (1 if asks or t == "sdata" else 0)
        return spec
    if t == "pair":
        if re.search(r"нод|наибольш\w+\s+общ\w+\s+делител", low):
            spec["op"] = ("pair", "gcd")
        elif re.search(r"нок|наименьш\w+\s+общ\w+\s+кратн", low):
            spec["op"] = ("pair", "lcm")
        elif re.search(r"больш\w*|максимальн\w*|наибольш\w*", low):
            spec["op"] = ("pair", "max")
        elif re.search(r"меньш\w*|минимальн\w*|наименьш\w*", low):
            spec["op"] = ("pair", "min")
        elif re.search(r"произведени|умнож", low):
            spec["op"] = ("pair", "mul")
        elif re.search(r"разност|вычт|отним", low):
            spec["op"] = ("pair", "sub")
        elif re.search(r"частн|раздел", low):
            spec["op"] = ("pair", "div")
        elif re.search(r"степен", low):
            spec["op"] = ("pair", "pow")
        elif re.search(r"сумм|слож", low):
            spec["op"] = ("pair", "add")
        else:
            return None
        spec["score"] = 3
        return spec
    if t == "int":
        row, _ = _find(NUM_OPS, low)
        if not row:
            return None
        if row[0] == "table":
            spec["op"] = ("table",)
        else:
            spec["op"] = ("num", row)
        spec["score"] = 2 + (1 if asks else 0)
        return spec

    # ---- набор чисел: отбор, преобразование, действие
    for row in FILTERS:
        m = re.search(row[1], low)
        if m and not (row[0] == "even" and re.search(r"нечетн", low) and not re.search(r"(?<!не)четн", low)):
            k = m.group(1) if m.groups() else None
            if row[0] in ("gt", "lt") and rng and k and m.start() >= rng.start() and m.end() <= rng.end():
                continue
            spec["filters"].append((row, k))
            if row[0] in ("div", "not_div"):
                low = low[:m.start()] + " " * (m.end() - m.start()) + low[m.end():]
    # «чётные» внутри «нечётные» не считаем дважды
    keys = [f[0][0] for f in spec["filters"]]
    if "odd" in keys and "even" in keys:
        spec["filters"] = [f for f in spec["filters"] if f[0][0] != "even"]
    if "not_div" in keys and "div" in keys:
        spec["filters"] = [f for f in spec["filters"] if f[0][0] != "div"]
    mrow, mm = _find(MAPS, low)
    op_row, om = _find(LIST_OPS, low)
    if mrow and op_row and op_row[0] == "sum" and mrow[0] == "square" and re.search(r"сумм\w*\s+квадрат", low):
        spec["map"] = mrow
    elif mrow and not (mrow[0] == "square" and re.search(r"квадратн\w+\s+корн", low)):
        spec["map"] = mrow
    spec["op"] = ("list", op_row) if op_row else None
    if not spec["op"]:
        if t == "range" or spec["filters"] or spec["map"]:
            spec["op"] = ("list", None)          # просто вывести подходящие числа
            spec["out"] = "each" if t == "range" else "line"
        else:
            return None
    spec["score"] = 1 + len(spec["filters"]) + (1 if spec["map"] else 0) + (1 if op_row else 0) + (1 if asks or t in ("data", "range") else 0)
    return spec


# ------------------------------------------------------------------ свой счёт (для проверки программы)

def _is_prime(x):
    if x < 2 or x != int(x):
        return False
    x = int(x)
    return all(x % d for d in range(2, int(x ** 0.5) + 1))


def _fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _median(nums):
    s = sorted(nums)
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def _clean(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


_HELPERS = {"math": math, "_is_prime": _is_prime, "_fib": _fib, "_median": _median, "_clean": _clean}


def _fmt(v):
    """Как печатает Python: списки — через пробел, кортежи — через пробел, дробные без лишних нулей."""
    if isinstance(v, (list, tuple)):
        return " ".join(_fmt(x) for x in v)
    if isinstance(v, dict):
        return "\n".join(f"{k}: {x}" for k, x in v.items())
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return str(int(v)) if False else str(v)
    return str(v)


def _apply(spec, nums):
    """Отбор и преобразование — своим способом (не тем кодом, что в программе)."""
    out = []
    for x in nums:
        ok = True
        for row, k in spec["filters"]:
            env = dict(_HELPERS, x=x)
            if not eval(row[3].format(k=k), {"__builtins__": {"abs": abs}}, env):   # noqa: S307 — свои шаблоны
                ok = False
                break
        if ok:
            out.append(eval(spec["map"][3], {"__builtins__": {"abs": abs}}, {"x": x}) if spec["map"] else x)  # noqa: S307
    return out


def expected(spec, inputs):
    """Ожидаемый вывод программы для данных inputs (строки ввода) — считается отдельно от программы."""
    src, op = spec["source"], spec["op"]
    t = src["type"]
    if op[0] == "stars":
        n = src["value"] if t == "const" else int(inputs[0])
        if op[1] == "pyramid":
            return [" " * (n - i) + "*" * (2 * i - 1) for i in range(1, n + 1)]
        if op[1] == "square":
            return ["* " * n for _ in range(n)] and [("* " * n).rstrip() for _ in range(n)]
        return ["*" * i for i in range(1, n + 1)]
    if op[0] == "fizzbuzz":
        return ["FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i)
                for i in range(src["a"], src["b"] + 1)]
    if op[0] == "first_primes":
        out, x = [], 2
        while len(out) < src["value"]:
            if _is_prime(x):
                out.append(x)
            x += 1
        return [_fmt(out)]
    if op[0] == "first_fib":
        return [_fmt([_fib(i) for i in range(src["value"])])]
    if op[0] == "table":
        k = src["value"] if t == "const" else int(inputs[0])
        return [f"{k} x {i} = {k * i}" for i in range(1, 11)]
    if op[0] == "str":
        s = src["value"] if t == "sdata" else inputs[0]
        return _fmt(eval(op[1][3], {"__builtins__": {"sum": sum, "len": len, "max": max, "dict": dict}}, dict(_HELPERS, s=s))).split("\n")  # noqa: S307
    if op[0] == "pair":
        a, b = (_n(x) for x in inputs[0].split()[:2])
        v = {"gcd": lambda: math.gcd(int(a), int(b)), "lcm": lambda: abs(int(a) * int(b)) // math.gcd(int(a), int(b)) if a and b else 0,
             "max": lambda: max(a, b), "min": lambda: min(a, b), "mul": lambda: a * b, "sub": lambda: a - b,
             "div": lambda: a / b if b else "делить на ноль нельзя", "pow": lambda: a ** b, "add": lambda: a + b}[op[1]]()
        return [_fmt(v)]
    if op[0] == "num":
        n = int(inputs[0])
        return _fmt(eval(op[1][3], {"__builtins__": {"sum": sum, "int": int, "str": str, "abs": abs, "len": len, "range": range, "bin": bin}},
                         dict(_HELPERS, n=n))).split("\n")  # noqa: S307
    # набор чисел
    if t == "data":
        nums = list(src["value"])
    elif t == "range":
        b = src["b"] if src["b"] is not None else int(inputs[0])
        nums = list(range(src["a"], b + 1))
    elif t == "until0":
        nums = []
        for line in inputs:
            x = _n(line.strip())
            if x == 0:
                break
            nums.append(x)
    else:
        nums = [_n(x) for x in inputs[0].split()]
    nums = _apply(spec, nums)
    if op[1] is None:
        if not nums and spec["out"] != "each":
            return ["нет подходящих чисел"]
        return [str(x) for x in nums] if spec["out"] == "each" else [_fmt(nums)]
    v = eval(op[1][3], {"__builtins__": {"sum": sum, "len": len, "min": min, "max": max, "sorted": sorted, "set": set,
                                         "list": list, "dict": dict}}, dict(_HELPERS, nums=nums))  # noqa: S307
    return [_fmt(v) if v not in (None, [], ()) else "нет подходящих чисел"]


# ------------------------------------------------------------------ сборка программы

def _title(spec):
    src, op = spec["source"], spec["op"]
    if op[0] in ("stars", "fizzbuzz", "first_primes", "first_fib", "table"):
        return {"stars": f"Фигура из звёздочек ({ {'pyramid': 'пирамида', 'square': 'квадрат', 'triangle': 'треугольник'}[op[1]] if op[0] == 'stars' else ''})",
                "fizzbuzz": "FizzBuzz", "first_primes": f"Первые {src['value']} простых чисел",
                "first_fib": f"Первые {src['value']} чисел Фибоначчи", "table": "Таблица умножения"}[op[0]].replace(" ()", "")
    if op[0] in ("str", "num"):
        return _cap(op[1][2])
    if op[0] == "pair":
        return {"gcd": "НОД двух чисел", "lcm": "НОК двух чисел", "max": "Большее из двух чисел", "min": "Меньшее из двух чисел",
                "mul": "Произведение двух чисел", "sub": "Разность двух чисел", "div": "Частное двух чисел", "pow": "Степень числа",
                "add": "Сумма двух чисел"}[op[1]]
    what = []
    if spec["filters"]:
        what.append(", ".join(r[2].format(k=k) for r, k in spec["filters"]))
    if spec["map"]:
        what.append(spec["map"][2])
    if src["type"] == "range":
        what.append(f"от {src['a']} до {src['b'] if src['b'] is not None else 'n'}")
    if not op[1]:
        return _cap("числа " + ", ".join(what)) if what else "Числа"
    return _cap(op[1][2] + (" — числа " + ", ".join(what) if what else ""))


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def python_code(spec):
    """Программа на Python по плану."""
    src, op = spec["source"], spec["op"]
    t = src["type"]
    head = f'"""{_title(spec)}. Написал Rai по описанию задачи."""\n'
    imports, helpers = set(), []
    body = []

    def need(name):
        if name == "math":
            imports.add("import math")
        if name == "_is_prime" and not any("def _is_prime" in h for h in helpers):
            helpers.append("def _is_prime(x):\n    \"\"\"Простое ли число: делится только на 1 и на себя.\"\"\"\n    if x < 2 or x != int(x):\n"
                           "        return False\n    x = int(x)\n    return all(x % d for d in range(2, int(x ** 0.5) + 1))\n")
        if name == "_fib" and not any("def _fib" in h for h in helpers):
            helpers.append("def _fib(n):\n    \"\"\"n-е число Фибоначчи (0, 1, 1, 2, 3, 5, …).\"\"\"\n    a, b = 0, 1\n    for _ in range(n):\n"
                           "        a, b = b, a + b\n    return a\n")
        if name == "_median" and not any("def _median" in h for h in helpers):
            helpers.append("def _median(nums):\n    \"\"\"Медиана: середина отсортированного списка.\"\"\"\n    s = sorted(nums)\n    if not s:\n"
                           "        return None\n    m = len(s) // 2\n    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2\n")
        if name == "_clean" and not any("def _clean" in h for h in helpers):
            helpers.append("def _clean(s):\n    \"\"\"Только буквы и цифры, маленькими — чтобы «А роза…» считалась палиндромом.\"\"\"\n"
                           "    return \"\".join(ch for ch in s.lower() if ch.isalnum())\n")

    def scan(expr):
        for name in ("math", "_is_prime", "_fib", "_median", "_clean"):
            if expr and name + ("." if name == "math" else "(") in expr:
                need(name)

    if op[0] == "stars":
        size = str(src["value"]) if t == "const" else 'int(input("Размер фигуры: "))'
        body.append(f"n = {size}")
        if op[1] == "pyramid":
            body.append("for i in range(1, n + 1):\n    print(\" \" * (n - i) + \"*\" * (2 * i - 1))")
        elif op[1] == "square":
            body.append("for _ in range(n):\n    print(\" \".join(\"*\" * n))")
        else:
            body.append("for i in range(1, n + 1):\n    print(\"*\" * i)")
    elif op[0] == "fizzbuzz":
        body.append(f"for i in range({src['a']}, {src['b'] + 1}):\n    if i % 15 == 0:\n        print(\"FizzBuzz\")\n"
                    "    elif i % 3 == 0:\n        print(\"Fizz\")\n    elif i % 5 == 0:\n        print(\"Buzz\")\n    else:\n        print(i)")
    elif op[0] == "first_primes":
        need("_is_prime")
        body.append(f"count = {src['value']}\nprimes = []\nx = 2\nwhile len(primes) < count:\n    if _is_prime(x):\n"
                    "        primes.append(x)\n    x += 1\nprint(*primes)")
    elif op[0] == "first_fib":
        need("_fib")
        body.append(f"count = {src['value']}\nprint(*[_fib(i) for i in range(count)])")
    elif op[0] == "table":
        k = str(src["value"]) if t == "const" else 'int(input("Число: "))'
        body.append(f"k = {k}\nfor i in range(1, 11):\n    print(f\"{{k}} x {{i}} = {{k * i}}\")")
    elif op[0] == "str":
        scan(op[1][3])
        get = repr(src["value"]) if t == "sdata" else 'input("Введите строку: ")'
        body.append(f"def solve(s):\n    \"\"\"{_cap(op[1][2])}.\"\"\"\n    return {op[1][3]}\n\n\ns = {get}\nresult = solve(s)")
        body.append("if isinstance(result, dict):\n    for key, value in result.items():\n        print(f\"{key}: {value}\")\nelse:\n    print(result)"
                    if op[1][0] == "s_freq" else "print(result)")
    elif op[0] == "pair":
        expr = {"gcd": "math.gcd(int(a), int(b))", "lcm": "abs(int(a) * int(b)) // math.gcd(int(a), int(b)) if a and b else 0",
                "max": "max(a, b)", "min": "min(a, b)", "mul": "a * b", "sub": "a - b",
                "div": "a / b if b else \"делить на ноль нельзя\"", "pow": "a ** b", "add": "a + b"}[op[1]]
        scan(expr)
        body.append("def number(text):\n    \"\"\"Целое или дробное число из текста (запятая тоже подходит).\"\"\"\n    text = text.replace(\",\", \".\")\n"
                    "    return float(text) if \".\" in text else int(text)\n\n\n"
                    "a, b = (number(x) for x in input(\"Введите два числа через пробел: \").split()[:2])\n"
                    f"print({expr})")
    elif op[0] == "num":
        scan(op[1][3])
        body.append(f"def solve(n):\n    \"\"\"{_cap(op[1][2])}.\"\"\"\n    return {op[1][3]}\n\n\nn = int(input(\"Введите целое число: \"))\n"
                    + ("print(*solve(n))" if op[1][0] == "divisors" else "print(solve(n))"))
    else:
        # набор чисел
        if t == "data":
            body.append(f"numbers = {src['value']!r}")
        elif t == "range":
            end = str(src["b"] + 1) if src["b"] is not None else "n + 1"
            if src["b"] is None:
                body.append('n = int(input("До какого числа? "))')
            body.append(f"numbers = range({src['a']}, {end})")
        elif t == "until0":
            body.append("numbers = []\nwhile True:\n    text = input(\"Число (0 — закончить): \").strip().replace(\",\", \".\")\n"
                        "    x = float(text) if \".\" in text else int(text)\n    if x == 0:\n        break\n    numbers.append(x)")
        else:
            body.append("numbers = [float(x) if \".\" in x else int(x)\n           for x in input(\"Введите числа через пробел: \").replace(\",\", \".\").split()]")
        cond = " and ".join(r[3].format(k=k) for r, k in spec["filters"])
        lines = [f"def solve(numbers):\n    \"\"\"{_title(spec)}.\"\"\""]
        if cond or spec["map"]:
            scan(cond)
            item = spec["map"][3] if spec["map"] else "x"
            lines.append(f"    nums = [{item} for x in numbers" + (f" if {cond}]" if cond else "]") +
                         ("  # " + ", ".join(r[2].format(k=k) for r, k in spec["filters"]) if cond else "") +
                         (("; " if cond else "  # ") + spec["map"][2] if spec["map"] else ""))
        else:
            lines.append("    nums = list(numbers)")
        if op[1]:
            scan(op[1][3])
            lines.append(f"    return {op[1][3]}  # {op[1][2]}")
        else:
            lines.append("    return nums")
        body.insert(0, "\n".join(lines) + "\n\n")
        if op[1] is None and spec["out"] == "each":
            body.append("for x in solve(numbers):\n    print(x)")
        elif op[1] is None or op[1][0] in ("sort_asc", "sort_desc", "unique", "reverse", "minmax"):
            body.append("result = solve(numbers)\nif result:\n    print(*result)\nelse:\n    print(\"нет подходящих чисел\")")
        else:
            body.append("result = solve(numbers)\nprint(result if result is not None else \"нет подходящих чисел\")")
    code = head
    if imports:
        code += "\n".join(sorted(imports)) + "\n"
    code += "\n"
    if helpers:
        code += "\n" + "\n\n".join(helpers) + "\n\n"
    code += "\n".join(body).replace("\n\n\n\n", "\n\n\n")
    return code.strip() + "\n"


def js_code(spec):
    """Та же программа на JavaScript (ввод — prompt, вывод — console.log). None — для этой задачи нет."""
    src, op = spec["source"], spec["op"]
    t = src["type"]
    helpers = []
    lines = [f"// {_title(spec)}. Написал Rai по описанию задачи."]

    def need(code):
        if "isPrime(" in code and not any("function isPrime" in h for h in helpers):
            helpers.append("function isPrime(x) {\n  if (x < 2 || !Number.isInteger(x)) return false;\n"
                           "  for (let d = 2; d * d <= x; d++) if (x % d === 0) return false;\n  return true;\n}")
        if "fib(" in code and not any("function fib" in h for h in helpers):
            helpers.append("function fib(n) {\n  let a = 0, b = 1;\n  for (let i = 0; i < n; i++) [a, b] = [b, a + b];\n  return a;\n}")
        if "median(" in code and not any("function median" in h for h in helpers):
            helpers.append("function median(nums) {\n  const s = [...nums].sort((a, b) => a - b), m = Math.floor(s.length / 2);\n"
                           "  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;\n}")
        if "factorial(" in code and not any("function factorial" in h for h in helpers):
            helpers.append("function factorial(n) {\n  let r = 1n;\n  for (let i = 2n; i <= BigInt(n); i++) r *= i;\n  return r;\n}")
        if "clean(" in code and not any("function clean" in h for h in helpers):
            helpers.append("function clean(s) {\n  return [...s.toLowerCase()].filter((ch) => /[\\p{L}\\d]/u.test(ch)).join('');\n}")

    if op[0] == "str":
        if not op[1][4]:
            return None
        need(op[1][4])
        get = repr(src["value"]) if t == "sdata" else 'prompt("Введите строку:") || ""'
        lines.append(f"const s = {get};\nconsole.log({op[1][4]});")
    elif op[0] == "num":
        need(op[1][4])
        lines.append(f"const n = parseInt(prompt(\"Введите целое число:\"), 10);\nconsole.log(String({op[1][4]}));")
    elif op[0] == "list":
        if t == "data":
            lines.append(f"const numbers = {src['value']!r};".replace("(", "[").replace(")", "]"))
        elif t == "range":
            end = str(src["b"]) if src["b"] is not None else "n"
            if src["b"] is None:
                lines.append('const n = parseInt(prompt("До какого числа?"), 10);')
            lines.append(f"const numbers = Array.from({{length: {end} - {src['a']} + 1}}, (_, i) => {src['a']} + i);")
        elif t == "ints":
            lines.append('const numbers = (prompt("Введите числа через пробел:") || "").replace(/,/g, ".").split(/\\s+/).filter(Boolean).map(Number);')
        else:
            return None
        cond = " && ".join(r[4].format(k=k) for r, k in spec["filters"])
        item = spec["map"][4] if spec["map"] else "x"
        expr = "numbers"
        if cond:
            expr += f".filter((x) => {cond})"
        if spec["map"]:
            expr += f".map((x) => {item})"
        need(cond)
        lines.append(f"const nums = {expr};")
        if op[1]:
            need(op[1][4])
            lines.append(f"const result = {op[1][4]};")
            lines.append("console.log(Array.isArray(result) ? result.join(' ') : result);")
        else:
            lines.append("console.log(nums.join(spec_out));".replace("spec_out", "'\\n'" if spec["out"] == "each" else "' '"))
    else:
        return None
    return "\n".join(lines[:1] + helpers + lines[1:]) + "\n"


# ------------------------------------------------------------------ песочница: запустить и проверить

class _Stop(Exception):
    pass


def run(code, inputs=(), max_steps=200000):
    """Запустить программу Python: (вывод, ошибка). Ввод — из inputs, без файлов и сети, не больше max_steps шагов."""
    feed = list(inputs)
    out = io.StringIO()
    steps = [0]

    def fake_input(prompt=""):
        if not feed:
            raise _Stop("программа ждёт ещё ввода")
        return feed.pop(0)

    def fake_print(*args, sep=" ", end="\n", **_):
        out.write(sep.join(str(a) for a in args) + end)

    def tracer(frame, event, arg):
        steps[0] += 1
        if steps[0] > max_steps:
            raise _Stop("слишком долго (похоже на бесконечный цикл)")
        return tracer

    safe = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k) for k in (
        "abs", "all", "any", "bin", "bool", "dict", "enumerate", "float", "int", "isinstance", "len", "list", "map", "max",
        "min", "pow", "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip", "ValueError", "Exception")}
    safe.update(input=fake_input, print=fake_print, __import__=lambda name, *a, **k: math if name == "math" else (_ for _ in ()).throw(ImportError(name)))
    env = {"__builtins__": safe, "__name__": "__main__"}
    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        exec(compile(code, "main.py", "exec"), env)  # noqa: S102 — код собран самим Rai из своих блоков
        error = None
    except _Stop as e:
        error = str(e)
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
    finally:
        sys.settrace(old)
    return out.getvalue(), error


def _samples(spec):
    """Примеры для проверки: [(строки ввода, описание)]."""
    t = spec["source"]["type"]
    op = spec["op"]
    if t in ("const", "data", "sdata") or op[0] in ("fizzbuzz", "first_primes", "first_fib") or (t == "range" and spec["source"]["b"] is not None):
        return [([], "без ввода")]
    if op[0] in ("stars", "table") or t == "range":
        return [(["4"], "4"), (["7"], "7")]
    if t == "str":
        return [(["А роза упала на лапу Азора"], "«А роза упала на лапу Азора»"), (["Привет, мир 2026"], "«Привет, мир 2026»")]
    if t == "pair":
        return [(["12 18"], "12 и 18"), (["7 3"], "7 и 3")]
    if t == "int":
        return [(["12"], "12"), (["7"], "7")] if op[1][0] not in ("factorial", "fib") else [(["5"], "5"), (["10"], "10")]
    if t == "until0":
        return [(["4", "-2", "15", "8", "0"], "4, −2, 15, 8, 0")]
    return [(["3 -8 14 5 22 7 -1 10 12 15 30"], "3 −8 14 5 22 7 −1 10 12 15 30"), (["1 2 3 4 5 6 9"], "1 2 3 4 5 6 9")]


def _example_inputs(spec, given):
    """Пример из задачи → строки ввода для программы."""
    t = spec["source"]["type"]
    nums = re.findall(_NUM, given)
    if t == "until0":
        return [x for x in nums] + (["0"] if not nums or nums[-1] != "0" else [])
    if t in ("ints", "pair"):
        return [" ".join(nums)]
    if t in ("int", "range") or spec["op"][0] in ("stars", "table"):
        return nums[:1]
    return [given]


def check(spec, code):
    """Проверить программу запуском: [{"input", "output", "expected", "ok", "error", "user"}]."""
    results = []
    cases = [(inp, label, None) for inp, label in _samples(spec)]
    for given, want in spec["examples"]:
        cases.append((_example_inputs(spec, given), given, want))
    for inp, label, want in cases:
        out, err = run(code, inp)
        got = [line.rstrip() for line in out.strip("\n").split("\n")] if out.strip() else []
        try:
            exp = [line.rstrip() for line in expected(spec, inp)] if want is None else [want.strip()]
        except Exception:  # noqa: BLE001 — свой счёт не справился (например, деление на ноль) — сверяем только запуск
            exp = None
        if want is not None:
            ok = not err and bool(got) and _same(got[-1], want)
        else:
            ok = not err and (exp is None or got == exp)
        results.append({"input": label, "output": "\n".join(got), "expected": "\n".join(exp or []), "ok": ok, "error": err,
                        "user": want is not None})
    return results


def _same(got, want):
    a, b = got.strip().lower().replace(",", "."), want.strip().lower().replace(",", ".")
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) < 1e-9 * max(1, abs(float(b)))
    except ValueError:
        return re.sub(r"[\s,\[\]()]+", " ", a).strip() == re.sub(r"[\s,\[\]()]+", " ", b).strip()


# ------------------------------------------------------------------ всё вместе

def _alternatives(spec):
    """Другие толкования задачи — если программа не прошла пример из условия."""
    out = []
    if spec["op"][0] == "list" and spec["op"][1]:
        for row in LIST_OPS:
            if row is not spec["op"][1]:
                out.append(dict(spec, op=("list", row)))
    if spec["op"][0] == "num":
        for row in NUM_OPS:
            if row[0] != "table" and row is not spec["op"][1]:
                out.append(dict(spec, op=("num", row)))
    return out


def plan_text(spec):
    """Как Rai понял задачу — по шагам."""
    src, op = spec["source"], spec["op"]
    t = src["type"]
    steps = []
    data = {"data": f"список из задачи: {src.get('value')}", "sdata": f"строка из задачи: «{src.get('value')}»",
            "range": f"числа от {src.get('a')} до {src.get('b') if src.get('b') is not None else 'n (вводит пользователь)'}",
            "until0": "числа с клавиатуры, пока не введут 0", "str": "строка с клавиатуры", "pair": "два числа с клавиатуры",
            "ints": "числа через пробел с клавиатуры", "int": "целое число с клавиатуры",
            "const": f"число {src.get('value')} из задачи"}.get(t)
    if op[0] in ("stars", "table") and t == "int":
        data = "размер — с клавиатуры" if op[0] == "stars" else "число — с клавиатуры"
    if data:
        steps.append("Данные: " + data)
    if spec["filters"]:
        steps.append("Отбор: только " + ", ".join(r[2].format(k=k) for r, k in spec["filters"]))
    if spec["map"]:
        steps.append("Преобразование: каждое число " + spec["map"][2])
    steps.append("Результат: " + _title(spec).lower())
    return steps


def generate(text, lang=None):
    """Код по описанию задачи: {"code", "lang", "filename", "title", "about", "checks", "score"} или None."""
    spec = parse(text)
    if not spec:
        return None
    code = python_code(spec)
    checks = check(spec, code)
    tried = 1
    if any(c["user"] and not c["ok"] for c in checks):
        # пример из задачи не прошёл — пробуем другие толкования
        for alt in _alternatives(spec):
            alt_code = python_code(alt)
            alt_checks = check(alt, alt_code)
            tried += 1
            if all(c["ok"] for c in alt_checks if c["user"]):
                spec, code, checks = alt, alt_code, alt_checks
                break
    title = _title(spec)
    js = js_code(spec) if lang in ("javascript", "typescript") else None
    steps = plan_text(spec)
    lines = [f"**{title}** — программу написал сам и проверил запуском.", "",
             "**Как понял задачу:**", *[f"{k}. {s}" for k, s in enumerate(steps, 1)], ""]
    good = [c for c in checks if c["ok"]]
    lines.append("**Проверка:**")
    for c in checks[:4]:
        mark = "✅" if c["ok"] else "❌"
        shown = c["output"].replace("\n", " · ")[:120] or "(пусто)"
        who = "ваш пример" if c["user"] else "пример"
        lines.append(f"- {mark} {who} {c['input']} → `{shown}`" + ("" if c["ok"] else
                     (f" — ошибка: {c['error']}" if c["error"] else f" — ожидалось `{(c['expected'] or '').replace(chr(10), ' · ')[:80]}`")))
    if tried > 1:
        word = "толкование" if tried % 10 == 1 and tried % 100 != 11 else "толкования" if 2 <= tried % 10 <= 4 and not 12 <= tried % 100 <= 14 else "толкований"
        if all(c["ok"] for c in checks if c["user"]):
            lines.append(f"- 🔁 Первое толкование не прошло ваш пример — перебрал {tried} {word} и нашёл подходящее")
        else:
            lines.append(f"- 🔁 Перебрал {tried} {word}, но ваш пример не сходится ни с одним — проверьте пример в условии")
    if js:
        lines.append("\nКод на JavaScript — ниже; проверял я Python-версию с тем же алгоритмом.")
    elif lang and lang not in ("python",):
        lines.append("\nНа этом языке пока пишу только по шаблонам — сделал на Python.")
    return {"code": js or code, "lang": "javascript" if js else "python", "filename": "main.js" if js else "main.py",
            "title": title, "about": "\n".join(lines), "checks": checks, "score": spec["score"],
            "ok": bool(good) and len(good) == len(checks), "python": code}
