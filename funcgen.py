"""Небольшие функции по описанию: «функция, которая считает среднее списка», «проверка високосного года».

Каждая функция — на Python и JavaScript, с примером вызова, чтобы код сразу запускался во вкладке Code.
"""

import re

F = []  # (слова, название, python, javascript)


def fn(words, title, python, javascript):
    F.append((words, title, python.strip() + "\n", javascript.strip() + "\n"))


fn(r"средн|average|mean", "Среднее арифметическое", '''
def average(numbers):
    """Среднее арифметическое списка чисел."""
    if not numbers:
        raise ValueError("список пуст")
    return sum(numbers) / len(numbers)


print(average([4, 8, 15, 16, 23, 42]))  # 18.0
''', '''
function average(numbers) {
  if (!numbers.length) throw new Error("массив пуст");
  return numbers.reduce((a, b) => a + b, 0) / numbers.length;
}

console.log(average([4, 8, 15, 16, 23, 42])); // 18
''')

fn(r"медиан|median", "Медиана", '''
def median(numbers):
    """Медиана: середина отсортированного списка."""
    s = sorted(numbers)
    n = len(s)
    if n == 0:
        raise ValueError("список пуст")
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


print(median([7, 1, 3, 9]))  # 5.0
''', '''
function median(numbers) {
  const s = [...numbers].sort((a, b) => a - b), mid = Math.floor(s.length / 2);
  if (!s.length) throw new Error("массив пуст");
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

console.log(median([7, 1, 3, 9])); // 5
''')

fn(r"сумм\w* цифр|sum of digits", "Сумма цифр числа", '''
def digit_sum(n):
    """Сумма цифр целого числа."""
    return sum(int(d) for d in str(abs(n)))


print(digit_sum(2026))  # 10
''', '''
function digitSum(n) {
  return String(Math.abs(n)).split("").reduce((s, d) => s + Number(d), 0);
}

console.log(digitSum(2026)); // 10
''')

fn(r"сумм|sum\b", "Сумма чисел", '''
def total(numbers):
    """Сумма всех чисел списка."""
    result = 0
    for x in numbers:
        result += x
    return result


print(total([1, 2, 3, 4, 5]))  # 15
''', '''
function total(numbers) {
  return numbers.reduce((sum, x) => sum + x, 0);
}

console.log(total([1, 2, 3, 4, 5])); // 15
''')

fn(r"максим|миним|наибольш|наименьш|\bmax\b|\bmin\b", "Максимум и минимум", '''
def min_max(numbers):
    """Наименьшее и наибольшее число списка (без встроенных min/max)."""
    if not numbers:
        raise ValueError("список пуст")
    lo = hi = numbers[0]
    for x in numbers[1:]:
        if x < lo:
            lo = x
        if x > hi:
            hi = x
    return lo, hi


print(min_max([3, -2, 17, 8]))  # (-2, 17)
''', '''
function minMax(numbers) {
  if (!numbers.length) throw new Error("массив пуст");
  return [Math.min(...numbers), Math.max(...numbers)];
}

console.log(minMax([3, -2, 17, 8])); // [ -2, 17 ]
''')

fn(r"гласн|vowel", "Подсчёт гласных", '''
VOWELS = set("аеёиоуыэюяaeiouy")


def count_vowels(text):
    """Сколько гласных букв в строке (русских и английских)."""
    return sum(1 for ch in text.lower() if ch in VOWELS)


print(count_vowels("Привет, мир!"))  # 3
''', '''
function countVowels(text) {
  return (text.toLowerCase().match(/[аеёиоуыэюяaeiouy]/g) || []).length;
}

console.log(countVowels("Привет, мир!")); // 3
''')

fn(r"чётн|четн|нечетн|нечётн|even|odd", "Чётные и нечётные числа", '''
def split_even_odd(numbers):
    """Разделить числа на чётные и нечётные."""
    even = [x for x in numbers if x % 2 == 0]
    odd = [x for x in numbers if x % 2 != 0]
    return even, odd


even, odd = split_even_odd(range(1, 11))
print("Чётные:", even)    # [2, 4, 6, 8, 10]
print("Нечётные:", odd)  # [1, 3, 5, 7, 9]
''', '''
function splitEvenOdd(numbers) {
  return [numbers.filter((x) => x % 2 === 0), numbers.filter((x) => x % 2 !== 0)];
}

const [even, odd] = splitEvenOdd([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
console.log("Чётные:", even, "Нечётные:", odd);
''')

fn(r"\bнод\b|\bнок\b|общ\w* делител|общ\w* кратн|gcd|lcm", "НОД и НОК", '''
def gcd(a, b):
    """Наибольший общий делитель (алгоритм Евклида)."""
    while b:
        a, b = b, a % b
    return abs(a)


def lcm(a, b):
    """Наименьшее общее кратное."""
    return abs(a * b) // gcd(a, b) if a and b else 0


print(gcd(48, 18), lcm(4, 6))  # 6 12
''', '''
function gcd(a, b) {
  while (b) [a, b] = [b, a % b];
  return Math.abs(a);
}
const lcm = (a, b) => (a && b ? Math.abs(a * b) / gcd(a, b) : 0);

console.log(gcd(48, 18), lcm(4, 6)); // 6 12
''')

fn(r"високосн|leap", "Високосный год", '''
def is_leap(year):
    """Високосный: делится на 4, но не на 100 — или делится на 400."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


for y in (1900, 2000, 2024, 2026):
    print(y, "високосный" if is_leap(y) else "обычный")
''', '''
function isLeap(year) {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

for (const y of [1900, 2000, 2024, 2026]) console.log(y, isLeap(y) ? "високосный" : "обычный");
''')

fn(r"количеств\w* цифр|сколько цифр", "Количество цифр в числе", '''
def count_digits(n):
    """Сколько цифр в целом числе."""
    return len(str(abs(int(n))))


print(count_digits(-12345))  # 5
''', '''
const countDigits = (n) => String(Math.abs(Math.trunc(n))).length;

console.log(countDigits(-12345)); // 5
''')

fn(r"уникальн|дубликат|повтор|без повтор|unique|duplicate", "Уникальные элементы", '''
def unique(items):
    """Убрать повторы, сохранив порядок."""
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def duplicates(items):
    """Элементы, которые встречаются больше одного раза."""
    return sorted({x for x in items if items.count(x) > 1})


data = [3, 1, 3, 2, 1, 5]
print(unique(data))      # [3, 1, 2, 5]
print(duplicates(data))  # [1, 3]
''', '''
const unique = (items) => [...new Set(items)];
const duplicates = (items) => [...new Set(items.filter((x, i) => items.indexOf(x) !== i))];

const data = [3, 1, 3, 2, 1, 5];
console.log(unique(data), duplicates(data));
''')

fn(r"цезар|шифр|caesar|зашифр", "Шифр Цезаря", '''
RU = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
EN = "abcdefghijklmnopqrstuvwxyz"


def caesar(text, shift):
    """Сдвинуть каждую букву на shift позиций (русский и английский алфавит)."""
    out = []
    for ch in text:
        for abc in (RU, EN):
            low = ch.lower()
            if low in abc:
                new = abc[(abc.index(low) + shift) % len(abc)]
                out.append(new.upper() if ch.isupper() else new)
                break
        else:
            out.append(ch)
    return "".join(out)


secret = caesar("Привет, Rai!", 3)
print(secret)              # Тулезх, Udl!
print(caesar(secret, -3))  # Привет, Rai!
''', '''
const ABC = ["абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "abcdefghijklmnopqrstuvwxyz"];

function caesar(text, shift) {
  return [...text].map((ch) => {
    const low = ch.toLowerCase();
    for (const abc of ABC) {
      const i = abc.indexOf(low);
      if (i >= 0) {
        const c = abc[(((i + shift) % abc.length) + abc.length) % abc.length];
        return ch === low ? c : c.toUpperCase();
      }
    }
    return ch;
  }).join("");
}

const secret = caesar("Привет, Rai!", 3);
console.log(secret, "→", caesar(secret, -3));
''')

fn(r"двоичн|бинарн\w* (?:вид|систем|запис)|в двоичн|binary|систем\w* счислен", "Перевод в двоичную систему", '''
def to_binary(n):
    """Перевести целое число в двоичную запись (без bin())."""
    if n == 0:
        return "0"
    sign, n, bits = "-" if n < 0 else "", abs(n), []
    while n:
        bits.append(str(n % 2))
        n //= 2
    return sign + "".join(reversed(bits))


print(to_binary(42))           # 101010
print(int("101010", 2))        # обратно: 42
print(format(255, "x"))        # в шестнадцатеричную: ff
''', '''
const toBinary = (n) => n.toString(2);

console.log(toBinary(42));            // 101010
console.log(parseInt("101010", 2));   // 42
console.log((255).toString(16));      // ff
''')

fn(r"возраст|age", "Возраст по дате рождения", '''
from datetime import date


def age(birthday, today=None):
    """Полных лет на сегодня."""
    today = today or date.today()
    years = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        years -= 1
    return years


print(age(date(2008, 5, 17)))
''', '''
function age(birthday, today = new Date()) {
  let years = today.getFullYear() - birthday.getFullYear();
  const m = today.getMonth() - birthday.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birthday.getDate())) years--;
  return years;
}

console.log(age(new Date(2008, 4, 17)));
''')

fn(r"площад|периметр|area", "Площади фигур", '''
import math


def circle_area(r):
    return math.pi * r ** 2


def rectangle_area(a, b):
    return a * b


def triangle_area(a, b, c):
    """Формула Герона по трём сторонам."""
    p = (a + b + c) / 2
    return math.sqrt(p * (p - a) * (p - b) * (p - c))


print(f"Круг r=3: {circle_area(3):.2f}")
print(f"Прямоугольник 4×5: {rectangle_area(4, 5)}")
print(f"Треугольник 3-4-5: {triangle_area(3, 4, 5)}")
''', '''
const circleArea = (r) => Math.PI * r ** 2;
const rectangleArea = (a, b) => a * b;
function triangleArea(a, b, c) {
  const p = (a + b + c) / 2;
  return Math.sqrt(p * (p - a) * (p - b) * (p - c));
}

console.log(circleArea(3).toFixed(2), rectangleArea(4, 5), triangleArea(3, 4, 5));
''')

fn(r"степен|корен|квадратн\w* корн|power|sqrt", "Степень и корень", '''
def power(base, exp):
    """Возвести в целую степень быстрым возведением."""
    if exp < 0:
        return 1 / power(base, -exp)
    result = 1
    while exp:
        if exp & 1:
            result *= base
        base *= base
        exp >>= 1
    return result


def sqrt(x, eps=1e-12):
    """Квадратный корень методом Ньютона."""
    if x < 0:
        raise ValueError("корень из отрицательного числа")
    guess = x or 1.0
    while abs(guess * guess - x) > eps * max(1, x):
        guess = (guess + x / guess) / 2
    return guess


print(power(2, 10), sqrt(2))  # 1024 1.414…
''', '''
const power = (base, exp) => base ** exp;
function sqrt(x) {
  if (x < 0) throw new Error("корень из отрицательного числа");
  let g = x || 1;
  for (let i = 0; i < 50; i++) g = (g + x / g) / 2;
  return g;
}

console.log(power(2, 10), sqrt(2));
''')

fn(r"делител|divisor", "Делители числа", '''
def divisors(n):
    """Все делители числа по возрастанию."""
    small, big = [], []
    i = 1
    while i * i <= n:
        if n % i == 0:
            small.append(i)
            if i != n // i:
                big.append(n // i)
        i += 1
    return small + big[::-1]


print(divisors(36))  # [1, 2, 3, 4, 6, 9, 12, 18, 36]
''', '''
function divisors(n) {
  const small = [], big = [];
  for (let i = 1; i * i <= n; i++) {
    if (n % i === 0) { small.push(i); if (i !== n / i) big.unshift(n / i); }
  }
  return small.concat(big);
}

console.log(divisors(36));
''')

fn(r"анаграм|anagram", "Проверка анаграмм", '''
def is_anagram(a, b):
    """Слова из одних и тех же букв (без учёта пробелов и регистра)."""
    clean = lambda s: sorted(s.lower().replace(" ", "").replace("ё", "е"))
    return clean(a) == clean(b)


print(is_anagram("апельсин", "спаниель"))  # True
''', '''
const clean = (s) => s.toLowerCase().replace(/\\s/g, "").split("").sort().join("");
const isAnagram = (a, b) => clean(a) === clean(b);

console.log(isAnagram("апельсин", "спаниель")); // true
''')

fn(r"заглавн|больш\w* букв|capitaliz|title case", "Каждое слово с заглавной буквы", '''
def capitalize_words(text):
    """Каждое слово — с большой буквы."""
    return " ".join(w[:1].upper() + w[1:] for w in text.split(" "))


print(capitalize_words("москва — столица россии"))  # Москва — Столица России
''', '''
const capitalizeWords = (text) => text.split(" ").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

console.log(capitalizeWords("москва — столица россии"));
''')

fn(r"длинн\w* слов|longest word", "Самое длинное слово", '''
import re


def longest_word(text):
    words = re.findall(r"[\\w-]+", text)
    return max(words, key=len) if words else ""


print(longest_word("Rai умеет писать программы и сайты"))  # программы
''', '''
function longestWord(text) {
  const words = text.match(/[\\p{L}\\d-]+/gu) || [];
  return words.reduce((a, b) => (b.length > a.length ? b : a), "");
}

console.log(longestWord("Rai умеет писать программы и сайты"));
''')

fn(r"вложенн\w* спис|flatten|плоск\w* спис", "Развернуть вложенный список", '''
def flatten(items):
    """[1, [2, [3, 4]], 5] -> [1, 2, 3, 4, 5]"""
    result = []
    for x in items:
        if isinstance(x, (list, tuple)):
            result.extend(flatten(x))
        else:
            result.append(x)
    return result


print(flatten([1, [2, [3, 4]], 5]))
''', '''
const flatten = (items) => items.flat(Infinity);

console.log(flatten([1, [2, [3, 4]], 5]));
''')

fn(r"пересечени|общие элемент|intersection", "Общие элементы двух списков", '''
def common(a, b):
    """Элементы, которые есть в обоих списках (в порядке первого)."""
    other = set(b)
    return [x for x in dict.fromkeys(a) if x in other]


print(common([1, 2, 3, 4], [3, 4, 5]))  # [3, 4]
''', '''
const common = (a, b) => [...new Set(a)].filter((x) => b.includes(x));

console.log(common([1, 2, 3, 4], [3, 4, 5]));
''')

fn(r"секунд\w* в (?:час|минут)|формат\w* времен|чч:мм", "Секунды в часы и минуты", '''
def hms(seconds):
    """3725 -> '01:02:05'"""
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return f"{h:02}:{m:02}:{s:02}"


print(hms(3725))
''', '''
function hms(seconds) {
  const h = Math.floor(seconds / 3600), m = Math.floor((seconds % 3600) / 60), s = seconds % 60;
  return [h, m, s].map((x) => String(x).padStart(2, "0")).join(":");
}

console.log(hms(3725)); // 01:02:05
''')

fn(r"\bмил[ьия]|километр|km|miles", "Километры и мили", '''
KM_IN_MILE = 1.609344


def km_to_miles(km):
    return km / KM_IN_MILE


def miles_to_km(miles):
    return miles * KM_IN_MILE


print(f"{km_to_miles(10):.2f} миль, {miles_to_km(26.2):.1f} км")
''', '''
const KM_IN_MILE = 1.609344;
const kmToMiles = (km) => km / KM_IN_MILE;
const milesToKm = (mi) => mi * KM_IN_MILE;

console.log(kmToMiles(10).toFixed(2), milesToKm(26.2).toFixed(1));
''')

fn(r"поменя\w* (?:местами )?переменн|swap", "Поменять значения переменных", '''
a, b = 5, 10
a, b = b, a  # в Python — одной строкой
print(a, b)  # 10 5
''', '''
let a = 5, b = 10;
[a, b] = [b, a];
console.log(a, b); // 10 5
''')

fn(r"провер\w* (?:почт|email|e-mail)|валидн\w* (?:почт|email)|email valid", "Проверка адреса почты", '''
import re

EMAIL = re.compile(r"^[\\w.+-]+@[\\w-]+(\\.[\\w-]+)+$")


def is_email(text):
    return bool(EMAIL.match(text.strip()))


for s in ("rai@rteam.info", "не почта", "a@b"):
    print(s, "→", is_email(s))
''', '''
const isEmail = (s) => /^[\\w.+-]+@[\\w-]+(\\.[\\w-]+)+$/.test(s.trim());

for (const s of ["rai@rteam.info", "не почта", "a@b"]) console.log(s, "→", isEmail(s));
''')

fn(r"переверн\w* слов|слова в обратн|reverse words", "Слова в обратном порядке", '''
def reverse_words(text):
    return " ".join(reversed(text.split()))


print(reverse_words("Rai пишет код"))  # код пишет Rai
''', '''
const reverseWords = (text) => text.split(/\\s+/).reverse().join(" ");

console.log(reverseWords("Rai пишет код"));
''')

_TRIGGER = re.compile(r"функци|программ|код|скрипт|напиши|алгоритм|как (?:посчитать|найти|проверить|перевести|узнать)|"
                      r"посчита|найти|проверк|провер|перевед|function|script|метод")


def generate(prompt, lang=None):
    """Функция по описанию: {"code", "lang", "filename", "title", "about"} или None.

    Короткие просьбы («шифр цезаря на js») подходят и без слов «функция» / «напиши».
    """
    low = (prompt or "").lower().replace("ё", "е")
    if not _TRIGGER.search(low) and len(low) > 50:
        return None
    for words, title, python, javascript in F:
        if re.search(words, low):
            use_js = lang in ("javascript", "typescript")
            note = ""
            if lang and lang not in ("python", "javascript", "typescript", "html"):
                note = "\n\nНа этом языке шаблона пока нет — написал на Python."
            code = javascript if use_js else python
            return {"code": code, "lang": "javascript" if use_js else "python",
                    "filename": "main.js" if use_js else "main.py", "title": title,
                    "about": f"**{title}** — функция с примером вызова. Нажмите «Открыть в Code» и «Запустить».{note}"}
    return None
