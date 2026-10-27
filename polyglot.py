"""Rai Code знает языки программирования: 50 классических задач — рабочие программы на 27 языках, без интернета.

Каждая задача описана один раз на маленьком «общем языке» (ввод, вывод, переменные, условия, циклы, функции,
массивы, строки, корень и пи), а для каждого языка есть переводчик в его синтаксис и привычки: типы, ввод
с клавиатуры, форматирование, работа со строками в UTF-8 (кириллица), индексы массивов с 0 или с 1.

    polyglot.generate("fizzbuzz на расте")          -> {"code", "lang", "filename", "title", "about", "task"}
    polyglot.generate("калькулятор", "kotlin")
    polyglot.find_lang("на си шарпе") -> "csharp";  polyglot.find_task("реши квадратное уравнение") -> "quadratic"

Языки: Python, JavaScript, TypeScript, Java, C#, C, C++, Go, Rust, Kotlin, Swift, PHP, Ruby, Lua, Dart, Pascal,
Bash, Perl, R, Scala, Julia, Visual Basic .NET, PowerShell, Groovy, Fortran, Nim, Crystal.
test_app.py собирает и запускает программы установленными компиляторами (Python, JavaScript, C, PHP, Ruby, Lua,
Perl, Bash, Pascal, Fortran) и сверяет вывод с Python; при разработке так же проверены все 50 задач на Java, C#,
C++, Go, Rust, Kotlin, Scala, Groovy, TypeScript, R, Nim и Crystal, а Swift, Dart, Julia, PowerShell и Visual Basic —
разбором синтаксиса.
"""

import re

# ====================================================================== общий язык задач
# выражения — кортежи: ("num", 5) ("flt", 1.5) ("str", "x") ("bool", True) ("var", "n") ("bin", "+", a, b)
# ("not", a) ("neg", a) ("call", "f", [args]) ("idx", arr, i) ("len", arr) ("arr", [..]) ("tofloat", a)
# ("fmt2", a) — число с двумя знаками после запятой; строки: ("rev", s) ("lower", s) ("nospace", s) ("words", s)


def num(x): return ("num", x)
def flt(x): return ("flt", float(x))
def s_(x): return ("str", x)
def v(name): return ("var", name)
def op(o, a, b): return ("bin", o, a, b)
def call(name, *args): return ("call", name, list(args))
def idx(a, i): return ("idx", a, i)
def length(a): return ("len", a)
def not_(a): return ("not", a)
def neg(a): return ("neg", a)
def tofloat(a): return ("tofloat", a)
def fmt2(a): return ("fmt2", a)
def rev(s): return ("rev", s)
def lower(s): return ("lower", s)
def nospace(s): return ("nospace", s)
def words(s): return ("words", s)
def arr(*xs): return ("arr", [num(x) for x in xs])
def sqrt(x): return ("sqrt", x)


PI = ("pi",)


TRUE, FALSE = ("bool", True), ("bool", False)


# операторы: Print/Write (части — строки или выражения), Let/Set, Input (int/float/str), If (else может быть If — это
# «иначе если»), While, For (переменная от start до stop-1), Break, Return, SetIdx, Rand (целое от lo до hi), Func
def Print(*parts): return ("print", list(parts))
def Write(*parts): return ("write", list(parts))
def Let(name, typ, e): return ("let", name, typ, e)
def Set(name, e): return ("set", name, e)
def Input(name, typ, prompt): return ("input", name, typ, prompt)
def If(cond, then, other=None): return ("if", cond, then, other or [])
def While(cond, body): return ("while", cond, body)
def For(var, start, stop, body): return ("for", var, start, stop, body)
def Break(): return ("break",)
def Return(e): return ("return", e)
def SetIdx(a, i, e): return ("setidx", a, i, e)
def Rand(name, lo, hi): return ("rand", name, lo, hi)
def Func(name, params, ret, body): return ("func", name, params, ret, body)


def Elif(*branches, other=None):
    """Цепочка «если — иначе если — иначе»: Elif((cond, body), (cond, body), other=[...])."""
    cond, body = branches[0]
    rest = [Elif(*branches[1:], other=other)] if len(branches) > 1 else (other or [])
    return If(cond, body, rest)


# ====================================================================== задачи
IS_PRIME = Func("is_prime", [("n", "int")], "bool", [
    If(op("<", v("n"), num(2)), [Return(FALSE)]),
    Let("i", "int", num(2)),
    While(op("<=", op("*", v("i"), v("i")), v("n")), [
        If(op("==", op("%", v("n"), v("i")), num(0)), [Return(FALSE)]),
        Set("i", op("+", v("i"), num(1))),
    ]),
    Return(TRUE),
])

TASKS = {}


def task(key, words_re, title, about, main, funcs=(), stdin="", expect=None):
    TASKS[key] = {"words": words_re, "title": title, "about": about, "main": main, "funcs": list(funcs),
                  "stdin": stdin, "expect": expect}


task("hello", r"привет,? мир|hello,? world|хелло|первую программу|первая программа|простейш\w* программ",
     "Привет, мир", "первая программа: выводит приветствие.",
     [Print("Привет, мир!")])

task("sum", r"сумм\w* (двух|2) чисел|сложи\w* (два|2) числа|сложени\w* (двух|2)|два числа и (выведи|выводит|найди|посчитай) (их )?сумм",
     "Сумма двух чисел", "спрашивает два числа и выводит их сумму.",
     [Input("a", "int", "Введите первое число: "), Input("b", "int", "Введите второе число: "),
      Print("Сумма: ", op("+", v("a"), v("b")))], stdin="5\n7\n", expect=["Сумма: 12"])

task("calc", r"калькулятор|calculator", "Калькулятор",
     "два числа и действие (+, -, *, /); на ноль делить не даёт.",
     [Input("a", "float", "Первое число: "), Input("oper", "str", "Действие (+, -, *, /): "), Input("b", "float", "Второе число: "),
      Elif((op("==", v("oper"), s_("+")), [Print("Результат: ", fmt2(op("+", v("a"), v("b"))))]),
           (op("==", v("oper"), s_("-")), [Print("Результат: ", fmt2(op("-", v("a"), v("b"))))]),
           (op("==", v("oper"), s_("*")), [Print("Результат: ", fmt2(op("*", v("a"), v("b"))))]),
           (op("==", v("oper"), s_("/")), [If(op("==", v("b"), flt(0)), [Print("На ноль делить нельзя")],
                                              [Print("Результат: ", fmt2(op("/", v("a"), v("b"))))])]),
           other=[Print("Неизвестное действие")])],
     stdin="7\n/\n2\n", expect=["Результат: 3.50"])

task("evenodd", r"(чет|чёт)\w* или (не|не )?(чет|чёт)|четность|чётность|(чет|чёт)н\w* ли|even.{0,8}odd",
     "Чётное или нечётное", "проверяет, чётное ли число.",
     [Input("n", "int", "Введите число: "),
      If(op("==", op("%", v("n"), num(2)), num(0)), [Print(v("n"), " — чётное")], [Print(v("n"), " — нечётное")])],
     stdin="7\n", expect=["7 — нечётное"])

task("max3", r"(наибольш|больш|максимальн|максимум)\w* из (трех|трёх|3)|max of three", "Наибольшее из трёх",
     "спрашивает три числа и находит наибольшее.",
     [Input("x", "int", "Первое число: "), Input("y", "int", "Второе число: "), Input("z", "int", "Третье число: "),
      Let("m", "int", v("x")),
      If(op(">", v("y"), v("m")), [Set("m", v("y"))]),
      If(op(">", v("z"), v("m")), [Set("m", v("z"))]),
      Print("Наибольшее: ", v("m"))], stdin="3\n9\n4\n", expect=["Наибольшее: 9"])

task("fizzbuzz", r"fizz ?buzz|физз? ?базз|физбаз", "FizzBuzz",
     "числа от 1 до 100: вместо кратных 3 — Fizz, кратных 5 — Buzz, кратных 15 — FizzBuzz.",
     [For("i", num(1), num(101), [
         Elif((op("==", op("%", v("i"), num(15)), num(0)), [Print("FizzBuzz")]),
              (op("==", op("%", v("i"), num(3)), num(0)), [Print("Fizz")]),
              (op("==", op("%", v("i"), num(5)), num(0)), [Print("Buzz")]),
              other=[Print(v("i"))])])])

task("fib", r"фибоначчи|fibonacci|фибоначи", "Числа Фибоначчи",
     "выводит первые N чисел Фибоначчи (каждое — сумма двух предыдущих).",
     [Input("n", "int", "Сколько чисел Фибоначчи вывести? "),
      Let("a", "big", num(0)), Let("b", "big", num(1)),
      For("i", num(0), v("n"), [Print(v("a")), Let("t", "big", op("+", v("a"), v("b"))), Set("a", v("b")), Set("b", v("t"))])],
     stdin="10\n", expect=["0", "1", "1", "2", "3", "5", "8", "13", "21", "34"])

task("factorial", r"факториал|factorial", "Факториал",
     "считает n! = 1 · 2 · … · n (до 20 — дальше число не помещается в 64 бита).",
     [Input("n", "int", "Введите n (0–20): "),
      If(op("<", v("n"), num(0)), [Print("Факториал отрицательного числа не определён")],
         [Print(v("n"), "! = ", call("factorial", v("n")))])],
     funcs=[Func("factorial", [("n", "int")], "big", [
         Let("r", "big", num(1)),
         For("i", num(1), op("+", v("n"), num(1)), [Set("r", op("*", v("r"), v("i")))]),
         Return(v("r"))])],
     stdin="20\n", expect=["20! = 2432902008176640000"])

task("isprime", r"(простое|простым) ли|является ли\w* .{0,20}прост|провер\w* .{0,20}прост|простот\w*|is prime",
     "Простое ли число", "проверяет, простое ли число (делится только на 1 и на себя).",
     [Input("n", "int", "Введите число: "),
      If(call("is_prime", v("n")), [Print(v("n"), " — простое число")], [Print(v("n"), " — не простое число")])],
     funcs=[IS_PRIME], stdin="97\n", expect=["97 — простое число"])

task("primes", r"простые числа|все простые|простых чисел|решето|primes", "Простые числа до N",
     "выводит все простые числа от 2 до N.",
     [Input("n", "int", "До какого числа искать простые? "),
      For("i", num(2), op("+", v("n"), num(1)), [If(call("is_prime", v("i")), [Print(v("i"))])])],
     funcs=[IS_PRIME], stdin="30\n", expect=["2", "3", "5", "7", "11", "13", "17", "19", "23", "29"])

task("reverse", r"перевер\w* строк|строк\w* (наоборот|задом)|развер\w* строк|реверс строк|reverse (a )?string|текст наоборот",
     "Строка наоборот", "переворачивает строку — правильно и для русских букв.",
     [Input("s", "str", "Введите строку: "), Print("Наоборот: ", rev(v("s")))],
     stdin="Привет мир\n", expect=["Наоборот: рим тевирП"])

task("palindrome", r"палиндром|palindrome", "Палиндром",
     "проверяет, читается ли строка одинаково с обеих сторон (без учёта пробелов и регистра).",
     [Input("s", "str", "Введите строку: "),
      Let("t", "str", lower(nospace(v("s")))),
      If(op("==", v("t"), rev(v("t"))), [Print("Это палиндром")], [Print("Это не палиндром")])],
     stdin="А роза упала на лапу Азора\n", expect=["Это палиндром"])

task("table", r"таблиц\w* умножени|multiplication table", "Таблица умножения",
     "выводит таблицу умножения для введённого числа.",
     [Input("n", "int", "Таблица умножения для числа: "),
      For("i", num(1), num(11), [Print(v("n"), " x ", v("i"), " = ", op("*", v("n"), v("i")))])],
     stdin="7\n", expect=["7 x %d = %d" % (i, 7 * i) for i in range(1, 11)])

task("arrstats", r"(сумм\w*|средн\w*) .{0,25}(массив|списк|элемент)|массив\w* .{0,20}(сумм|средн)", "Сумма и среднее массива",
     "считает сумму и среднее значение элементов массива.",
     [Let("nums", "arr", arr(5, 3, 8, 1, 9, 2)), Let("total", "int", num(0)),
      For("i", num(0), length(v("nums")), [Set("total", op("+", v("total"), idx(v("nums"), v("i"))))]),
      Print("Сумма: ", v("total")),
      Print("Среднее: ", fmt2(op("/", tofloat(v("total")), tofloat(length(v("nums"))))))],
     expect=["Сумма: 28", "Среднее: 4.67"])

task("minmax", r"(минимум|минимальн|наименьш)\w* и (максимум|максимальн|наибольш)|(максимум|максимальн|наибольш)\w* и "
               r"(минимум|минимальн|наименьш)|min.{0,6}max|max.{0,6}min", "Минимум и максимум",
     "находит наименьший и наибольший элементы массива.",
     [Let("nums", "arr", arr(5, 3, 8, 1, 9, 2)), Let("lo", "int", idx(v("nums"), num(0))), Let("hi", "int", idx(v("nums"), num(0))),
      For("i", num(1), length(v("nums")), [
          If(op("<", idx(v("nums"), v("i")), v("lo")), [Set("lo", idx(v("nums"), v("i")))]),
          If(op(">", idx(v("nums"), v("i")), v("hi")), [Set("hi", idx(v("nums"), v("i")))])]),
      Print("Минимум: ", v("lo")), Print("Максимум: ", v("hi"))], expect=["Минимум: 1", "Максимум: 9"])

task("bubble", r"пузыр|bubble|сортировк\w* (массив|списк|чисел)|отсортир\w* (массив|списк|числа)|сортировк", "Сортировка пузырьком",
     "сортирует массив по возрастанию: соседние элементы меняются местами, пока всё не встанет по порядку.",
     [Let("nums", "arr", arr(5, 3, 8, 1, 9, 2)), Let("n", "int", length(v("nums"))),
      For("i", num(0), op("-", v("n"), num(1)), [
          For("j", num(0), op("-", op("-", v("n"), num(1)), v("i")), [
              If(op(">", idx(v("nums"), v("j")), idx(v("nums"), op("+", v("j"), num(1)))), [
                  Let("t", "int", idx(v("nums"), v("j"))),
                  SetIdx(v("nums"), v("j"), idx(v("nums"), op("+", v("j"), num(1)))),
                  SetIdx(v("nums"), op("+", v("j"), num(1)), v("t"))])])]),
      Write("Отсортировано:"),
      For("i", num(0), v("n"), [Write(" ", idx(v("nums"), v("i")))]),
      Print("")], expect=["Отсортировано: 1 2 3 5 8 9"])

task("bsearch", r"(двоичн|бинарн)\w* поиск|binary search", "Двоичный поиск",
     "ищет число в отсортированном массиве, каждый раз деля его пополам.",
     [Let("nums", "arr", arr(1, 3, 5, 7, 9, 11, 13, 15)), Input("x", "int", "Какое число найти? "),
      Let("lo", "int", num(0)), Let("hi", "int", op("-", length(v("nums")), num(1))), Let("pos", "int", num(-1)),
      While(op("<=", v("lo"), v("hi")), [
          Let("mid", "int", op("//", op("+", v("lo"), v("hi")), num(2))),
          Elif((op("==", idx(v("nums"), v("mid")), v("x")), [Set("pos", v("mid")), Break()]),
               (op("<", idx(v("nums"), v("mid")), v("x")), [Set("lo", op("+", v("mid"), num(1)))]),
               other=[Set("hi", op("-", v("mid"), num(1)))])]),
      If(op(">=", v("pos"), num(0)), [Print("Нашёл на позиции ", v("pos"))], [Print("Такого числа нет")])],
     stdin="11\n", expect=["Нашёл на позиции 5"])

task("guess", r"угада\w* число|угадай|guess", "Угадай число",
     "компьютер загадывает число от 1 до 100, а вы угадываете по подсказкам «больше» и «меньше».",
     [Rand("secret", 1, 100), Let("tries", "int", num(0)),
      Print("Я загадал число от 1 до 100. Угадайте!"),
      While(TRUE, [
          Input("g", "int", "Ваш вариант: "), Set("tries", op("+", v("tries"), num(1))),
          Elif((op("<", v("g"), v("secret")), [Print("Больше!")]),
               (op(">", v("g"), v("secret")), [Print("Меньше!")]),
               other=[Print("Угадали за ", v("tries"), " попыток!"), Break()])])])

task("temp", r"цельси|фаренгейт|fahrenheit|celsius|температур\w* .{0,20}(перев|конверт)|(перев|конверт)\w* .{0,20}температур",
     "Цельсий → Фаренгейт", "переводит температуру из градусов Цельсия в Фаренгейты: F = C × 9/5 + 32.",
     [Input("cel", "float", "Температура в °C: "),
      Let("fah", "float", op("+", op("/", op("*", v("cel"), flt(9)), flt(5)), flt(32))),
      Print(fmt2(v("cel")), " °C = ", fmt2(v("fah")), " °F")], stdin="36.6\n", expect=["36.60 °C = 97.88 °F"])

task("gcd", r"\bнод\b|наибольш\w* общ\w* делител|\bgcd\b|евклид", "НОД (алгоритм Евклида)",
     "находит наибольший общий делитель двух чисел.",
     [Input("a", "int", "Первое число: "), Input("b", "int", "Второе число: "),
      Print("НОД = ", call("gcd", v("a"), v("b")))],
     funcs=[Func("gcd", [("a", "int"), ("b", "int")], "int", [
         Let("x", "int", v("a")), Let("y", "int", v("b")),
         While(op("!=", v("y"), num(0)), [Let("t", "int", op("%", v("x"), v("y"))), Set("x", v("y")), Set("y", v("t"))]),
         Return(v("x"))])],
     stdin="84\n36\n", expect=["НОД = 12"])

task("leap", r"високосн|leap year", "Високосный год",
     "проверяет, високосный ли год: делится на 4, но не на 100 — или делится на 400.",
     [Input("y", "int", "Введите год: "),
      If(op("or", op("and", op("==", op("%", v("y"), num(4)), num(0)), op("!=", op("%", v("y"), num(100)), num(0))),
            op("==", op("%", v("y"), num(400)), num(0))),
         [Print(v("y"), " — високосный")], [Print(v("y"), " — не високосный")])],
     stdin="2024\n", expect=["2024 — високосный"])

task("digits", r"сумм\w* цифр|sum of digits", "Сумма цифр числа",
     "складывает все цифры числа.",
     [Input("n", "int", "Введите число: "),
      If(op("<", v("n"), num(0)), [Set("n", neg(v("n")))]),
      Let("total", "int", num(0)),
      While(op(">", v("n"), num(0)), [Set("total", op("+", v("total"), op("%", v("n"), num(10)))), Set("n", op("//", v("n"), num(10)))]),
      Print("Сумма цифр: ", v("total"))], stdin="9876\n", expect=["Сумма цифр: 30"])

task("words", r"(посчита\w*|количеств\w*|число|сколько) слов|word count", "Сколько слов в строке",
     "считает слова в строке.",
     [Input("s", "str", "Введите текст: "), Print("Слов: ", words(v("s")))],
     stdin="Rai знает много языков\n", expect=["Слов: 4"])

task("countdown", r"обратн\w* отсч|отсчет|отсчёт|countdown", "Обратный отсчёт",
     "считает от N до 1 и пишет «Старт!».",
     [Input("n", "int", "С какого числа считать? "),
      While(op(">", v("n"), num(0)), [Print(v("n")), Set("n", op("-", v("n"), num(1)))]),
      Print("Старт!")], stdin="3\n", expect=["3", "2", "1", "Старт!"])

def _show_array(title, name="nums"):
    """Вывести массив одной строкой: «Отсортировано: 1 2 3»."""
    return [Write(title), For("i", num(0), length(v(name)), [Write(" ", idx(v(name), v("i")))]), Print("")]


task("circle", r"площад\w* круга|длин\w* окружност|окружност|circle area", "Площадь круга",
     "по радиусу считает площадь круга и длину окружности.",
     [Input("r", "float", "Радиус: "),
      Print("Площадь: ", fmt2(op("*", op("*", PI, v("r")), v("r")))),
      Print("Длина окружности: ", fmt2(op("*", op("*", flt(2), PI), v("r"))))],
     stdin="2\n", expect=["Площадь: 12.57", "Длина окружности: 12.57"])

task("quadratic", r"квадратн\w* уравнени|дискриминант|quadratic", "Квадратное уравнение",
     "решает ax² + bx + c = 0 через дискриминант.",
     [Input("a", "float", "a = "), Input("b", "float", "b = "), Input("c", "float", "c = "),
      Let("d", "float", op("-", op("*", v("b"), v("b")), op("*", op("*", flt(4), v("a")), v("c")))),
      Elif((op("==", v("a"), flt(0)), [Print("a не может быть 0 — это не квадратное уравнение")]),
           (op("<", v("d"), flt(0)), [Print("Корней нет (дискриминант меньше нуля)")]),
           (op("==", v("d"), flt(0)), [Print("Один корень: x = ", fmt2(op("/", neg(v("b")), op("*", flt(2), v("a")))))]),
           other=[Let("root", "float", sqrt(v("d"))),
                  Print("x1 = ", fmt2(op("/", op("+", neg(v("b")), v("root")), op("*", flt(2), v("a"))))),
                  Print("x2 = ", fmt2(op("/", op("-", neg(v("b")), v("root")), op("*", flt(2), v("a")))))])],
     stdin="1\n-3\n2\n", expect=["x1 = 2.00", "x2 = 1.00"])

task("bmi", r"\bимт\b|индекс\w* массы|\bbmi\b", "Индекс массы тела",
     "считает ИМТ по весу и росту и говорит, норма ли это.",
     [Input("weight", "float", "Вес, кг: "), Input("height", "float", "Рост, см: "),
      Let("h", "float", op("/", v("height"), flt(100))),
      Let("bmi", "float", op("/", v("weight"), op("*", v("h"), v("h")))),
      Print("ИМТ: ", fmt2(v("bmi"))),
      Elif((op("<", v("bmi"), flt(18.5)), [Print("Недостаток веса")]),
           (op("<", v("bmi"), flt(25)), [Print("Норма")]),
           (op("<", v("bmi"), flt(30)), [Print("Избыточный вес")]),
           other=[Print("Ожирение")])],
     stdin="70\n175\n", expect=["ИМТ: 22.86", "Норма"])

task("sumn", r"сумм\w* (всех )?(натуральн\w* )?чисел (от 1 )?до|сумм\w* от 1 до|1 \+ 2 \+|сумм\w* первых", "Сумма чисел от 1 до N",
     "складывает все числа от 1 до N.",
     [Input("n", "int", "До какого числа складывать? "), Let("total", "big", num(0)),
      For("i", num(1), op("+", v("n"), num(1)), [Set("total", op("+", v("total"), v("i")))]),
      Print("Сумма чисел от 1 до ", v("n"), ": ", v("total"))], stdin="100\n", expect=["Сумма чисел от 1 до 100: 5050"])

task("evensum", r"сумм\w* (всех )?ч[её]тн\w*", "Сумма чётных чисел",
     "складывает все чётные числа от 1 до N.",
     [Input("n", "int", "До какого числа? "), Let("total", "int", num(0)),
      For("i", num(1), op("+", v("n"), num(1)), [If(op("==", op("%", v("i"), num(2)), num(0)), [Set("total", op("+", v("total"), v("i")))])]),
      Print("Сумма чётных чисел до ", v("n"), ": ", v("total"))], stdin="10\n", expect=["Сумма чётных чисел до 10: 30"])

task("average", r"средн\w* (арифметическ\w* )?(из |для )?(n|н|нескольк\w*|введ\w*|чисел)|среднее арифметическое", "Среднее арифметическое",
     "спрашивает, сколько чисел, читает их и считает среднее.",
     [Input("n", "int", "Сколько чисел? "), Let("total", "float", flt(0)),
      For("i", num(0), v("n"), [Input("x", "float", "Число: "), Set("total", op("+", v("total"), v("x")))]),
      If(op(">", v("n"), num(0)), [Print("Среднее: ", fmt2(op("/", v("total"), tofloat(v("n")))))], [Print("Чисел нет")])],
     stdin="4\n2\n4\n6\n9\n", expect=["Среднее: 5.25"])

task("maxinput", r"(наибольш|максимальн|максимум)\w* из (n|н|нескольк\w*|введ\w*|\d+) (чисел|числа)", "Наибольшее из введённых",
     "читает N чисел и находит наибольшее.",
     [Input("n", "int", "Сколько чисел? "), Let("best", "int", num(0)),
      For("i", num(0), v("n"), [Input("x", "int", "Число: "),
                                If(op("or", op("==", v("i"), num(0)), op(">", v("x"), v("best"))), [Set("best", v("x"))])]),
      Print("Наибольшее: ", v("best"))], stdin="4\n3\n9\n-2\n7\n", expect=["Наибольшее: 9"])

task("binary", r"двоичн\w* (систем|запис|вид|код)|в двоичн|перев\w* .{0,25}двоичн|decimal to binary|binary number", "Число в двоичной системе",
     "переводит число в двоичную запись.",
     [Input("n", "int", "Число (0 и больше): "),
      If(op("==", v("n"), num(0)), [Print("0")], [
          Let("p", "int", num(1)),
          While(op("<=", op("*", v("p"), num(2)), v("n")), [Set("p", op("*", v("p"), num(2)))]),
          While(op(">", v("p"), num(0)), [Write(op("%", op("//", v("n"), v("p")), num(2))), Set("p", op("//", v("p"), num(2)))]),
          Print("")])], stdin="10\n", expect=["1010"])

task("power", r"возв\w* в степень|степен\w* числа|в степени|power of", "Степень числа",
     "возводит число в целую степень умножением.",
     [Input("x", "int", "Число: "), Input("k", "int", "Степень (0 и больше): "), Let("res", "big", num(1)),
      For("i", num(0), v("k"), [Set("res", op("*", v("res"), v("x")))]),
      Print(v("x"), "^", v("k"), " = ", v("res"))], stdin="2\n10\n", expect=["2^10 = 1024"])

task("stars", r"звезд|звёзд|треугольник\w* из|пирамид|ёлочк|елочк|stars? (triangle|pattern)", "Треугольник из звёздочек",
     "рисует треугольник из звёздочек высотой N.",
     [Input("n", "int", "Высота: "),
      For("i", num(1), op("+", v("n"), num(1)), [For("j", num(0), v("i"), [Write("*")]), Print("")])],
     stdin="3\n", expect=["*", "**", "***"])

task("perfect", r"совершенн\w* числ|perfect number", "Совершенное число",
     "проверяет, равно ли число сумме своих делителей (как 6 = 1 + 2 + 3).",
     [Input("n", "int", "Введите число: "), Let("total", "int", num(0)),
      For("i", num(1), v("n"), [If(op("==", op("%", v("n"), v("i")), num(0)), [Set("total", op("+", v("total"), v("i")))])]),
      If(op("and", op("==", v("total"), v("n")), op(">", v("n"), num(0))), [Print(v("n"), " — совершенное число")],
         [Print(v("n"), " — не совершенное число")])], stdin="28\n", expect=["28 — совершенное число"])

task("collatz", r"коллатц|сиракуз|3n ?\+ ?1|collatz", "Гипотеза Коллатца",
     "чётное число делит пополам, нечётное — умножает на 3 и прибавляет 1, пока не дойдёт до 1.",
     [Input("n", "int", "Начальное число: "), Let("steps", "int", num(0)), Write(v("n")),
      While(op(">", v("n"), num(1)), [
          If(op("==", op("%", v("n"), num(2)), num(0)), [Set("n", op("//", v("n"), num(2)))],
             [Set("n", op("+", op("*", num(3), v("n")), num(1)))]),
          Set("steps", op("+", v("steps"), num(1))), Write(" ", v("n"))]),
      Print(""), Print("Шагов: ", v("steps"))], stdin="6\n", expect=["6 3 10 5 16 8 4 2 1", "Шагов: 8"])

task("hms", r"секунд\w* в (час|минут)|(час|минут)\w* и секунд|перев\w* секунд|hh:mm:ss", "Секунды в часы и минуты",
     "переводит секунды в часы, минуты и секунды.",
     [Input("s", "int", "Сколько секунд? "),
      Let("h", "int", op("//", v("s"), num(3600))), Let("m", "int", op("//", op("%", v("s"), num(3600)), num(60))),
      Let("sec", "int", op("%", v("s"), num(60))),
      Print(v("h"), " ч ", v("m"), " мин ", v("sec"), " с")], stdin="3725\n", expect=["1 ч 2 мин 5 с"])

task("percent", r"процент\w* от|% от|посчита\w* процент|percentage", "Процент от числа",
     "считает, сколько составляет p процентов от числа.",
     [Input("x", "float", "Число: "), Input("p", "float", "Процент: "),
      Print(fmt2(v("p")), "% от ", fmt2(v("x")), " = ", fmt2(op("/", op("*", v("x"), v("p")), flt(100))))],
     stdin="200\n15\n", expect=["15.00% от 200.00 = 30.00"])

task("divisors", r"(все )?делител\w* числа|найд\w* делител|список делител|divisors", "Делители числа",
     "выводит все делители числа.",
     [Input("n", "int", "Введите число: "), Write("Делители ", v("n"), ":"),
      For("i", num(1), op("+", v("n"), num(1)), [If(op("==", op("%", v("n"), v("i")), num(0)), [Write(" ", v("i"))])]),
      Print("")], stdin="12\n", expect=["Делители 12: 1 2 3 4 6 12"])

task("primefactors", r"(простые )?множител|разлож\w* (на|числа)|факторизац|prime factor", "Разложение на простые множители",
     "раскладывает число на простые множители.",
     [Input("n", "int", "Введите число (больше 1): "), Write(v("n"), " ="), Let("d", "int", num(2)),
      While(op("<=", op("*", v("d"), v("d")), v("n")), [
          While(op("==", op("%", v("n"), v("d")), num(0)), [Write(" ", v("d")), Set("n", op("//", v("n"), v("d")))]),
          Set("d", op("+", v("d"), num(1)))]),
      If(op(">", v("n"), num(1)), [Write(" ", v("n"))]), Print("")], stdin="360\n", expect=["360 = 2 2 2 3 3 5"])

task("revnum", r"(число|цифр\w*) (наоборот|в обратном порядке)|перевер\w* число|reverse (a )?number", "Число наоборот",
     "записывает цифры числа в обратном порядке.",
     [Input("n", "int", "Введите число: "), Let("r", "big", num(0)),
      While(op(">", v("n"), num(0)), [Set("r", op("+", op("*", v("r"), num(10)), op("%", v("n"), num(10)))),
                                       Set("n", op("//", v("n"), num(10)))]),
      Print("Наоборот: ", v("r"))], stdin="12345\n", expect=["Наоборот: 54321"])

task("lcm", r"\bнок\b|наименьш\w* общ\w* кратн|\blcm\b", "НОК двух чисел",
     "находит наименьшее общее кратное через НОД.",
     [Input("a", "int", "Первое число: "), Input("b", "int", "Второе число: "),
      Print("НОК = ", op("*", op("//", v("a"), call("gcd", v("a"), v("b"))), v("b")))],
     funcs=[TASKS["gcd"]["funcs"][0]], stdin="4\n6\n", expect=["НОК = 12"])

task("triangle", r"существует ли треугольник|треугольник\w* (существ|со сторон)|неравенств\w* треугольник", "Существует ли треугольник",
     "проверяет, можно ли сложить треугольник из трёх отрезков.",
     [Input("x", "int", "Первая сторона: "), Input("y", "int", "Вторая сторона: "), Input("z", "int", "Третья сторона: "),
      If(op("and", op("and", op(">", op("+", v("x"), v("y")), v("z")), op(">", op("+", v("x"), v("z")), v("y"))),
            op(">", op("+", v("y"), v("z")), v("x"))),
         [Print("Треугольник существует")], [Print("Треугольника не существует")])],
     stdin="3\n4\n5\n", expect=["Треугольник существует"])

task("grade", r"оценк\w* по балл|балл\w* в оценк|перев\w* балл|grade", "Оценка по баллам",
     "переводит баллы (0–100) в школьную оценку.",
     [Input("score", "int", "Сколько баллов (0–100)? "),
      Elif((op(">=", v("score"), num(90)), [Print("Отлично (5)")]),
           (op(">=", v("score"), num(75)), [Print("Хорошо (4)")]),
           (op(">=", v("score"), num(50)), [Print("Удовлетворительно (3)")]),
           other=[Print("Неудовлетворительно (2)")])], stdin="80\n", expect=["Хорошо (4)"])

task("rect", r"площад\w* (и периметр )?прямоугольник|периметр\w* прямоугольник|rectangle", "Прямоугольник",
     "считает площадь и периметр прямоугольника.",
     [Input("a", "float", "Длина: "), Input("b", "float", "Ширина: "),
      Print("Площадь: ", fmt2(op("*", v("a"), v("b")))), Print("Периметр: ", fmt2(op("*", flt(2), op("+", v("a"), v("b")))))],
     stdin="3\n4.5\n", expect=["Площадь: 13.50", "Периметр: 15.00"])

task("selection", r"сортировк\w* выбор|selection sort", "Сортировка выбором",
     "каждый раз находит наименьший из оставшихся элементов и ставит его на место.",
     [Let("nums", "arr", arr(5, 3, 8, 1, 9, 2)), Let("n", "int", length(v("nums"))),
      For("i", num(0), op("-", v("n"), num(1)), [
          Let("m", "int", v("i")),
          For("j", op("+", v("i"), num(1)), v("n"), [If(op("<", idx(v("nums"), v("j")), idx(v("nums"), v("m"))), [Set("m", v("j"))])]),
          Let("t", "int", idx(v("nums"), v("i"))), SetIdx(v("nums"), v("i"), idx(v("nums"), v("m"))), SetIdx(v("nums"), v("m"), v("t"))])]
     + _show_array("Отсортировано:"), expect=["Отсортировано: 1 2 3 5 8 9"])

task("linsearch", r"линейн\w* поиск|найд\w* (элемент|число) в массиве|поиск в массиве|есть ли (число|элемент) в массиве|linear search",
     "Поиск в массиве", "ищет число в массиве перебором.",
     [Let("nums", "arr", arr(5, 3, 8, 1, 9, 2)), Input("x", "int", "Какое число найти? "), Let("pos", "int", num(-1)),
      For("i", num(0), length(v("nums")), [If(op("==", idx(v("nums"), v("i")), v("x")), [Set("pos", v("i")), Break()])]),
      If(op(">=", v("pos"), num(0)), [Print("Нашёл на позиции ", v("pos"))], [Print("Такого числа нет")])],
     stdin="8\n", expect=["Нашёл на позиции 2"])

task("arrreverse", r"перевер\w* массив|массив\w* (наоборот|в обратном)|разверн\w* массив|reverse (an )?array", "Массив наоборот",
     "переставляет элементы массива в обратном порядке.",
     [Let("nums", "arr", arr(5, 3, 8, 1, 9, 2)), Let("n", "int", length(v("nums"))),
      For("i", num(0), op("//", v("n"), num(2)), [
          Let("t", "int", idx(v("nums"), v("i"))),
          SetIdx(v("nums"), v("i"), idx(v("nums"), op("-", op("-", v("n"), num(1)), v("i")))),
          SetIdx(v("nums"), op("-", op("-", v("n"), num(1)), v("i")), v("t"))])] + _show_array("Наоборот:"),
     expect=["Наоборот: 2 9 1 8 3 5"])

task("countpos", r"(сколько|количеств\w*|посчита\w*) (положительн|отрицательн)", "Положительные и отрицательные",
     "считает положительные, отрицательные числа и нули в массиве.",
     [Let("nums", "arr", arr(5, -3, 8, 0, -1, 9)), Let("plus", "int", num(0)), Let("minus", "int", num(0)), Let("zeros", "int", num(0)),
      For("i", num(0), length(v("nums")), [
          Elif((op(">", idx(v("nums"), v("i")), num(0)), [Set("plus", op("+", v("plus"), num(1)))]),
               (op("<", idx(v("nums"), v("i")), num(0)), [Set("minus", op("+", v("minus"), num(1)))]),
               other=[Set("zeros", op("+", v("zeros"), num(1)))])]),
      Print("Положительных: ", v("plus")), Print("Отрицательных: ", v("minus")), Print("Нулей: ", v("zeros"))],
     expect=["Положительных: 3", "Отрицательных: 2", "Нулей: 1"])

task("dice", r"кубик|игральн\w* кост|бросок|dice", "Бросок кубика",
     "бросает игральный кубик — случайное число от 1 до 6.",
     [Rand("roll", 1, 6), Print("Выпало: ", v("roll"))])

# Порядок проверки: сначала узкие задачи, потом общие («сортировка» — после «пузырька»)
ORDER = ["hello", "fizzbuzz", "fib", "factorial", "quadratic", "circle", "bmi", "primefactors", "perfect", "collatz", "isprime",
         "primes", "palindrome", "reverse", "revnum", "arrreverse", "table", "minmax", "countpos", "maxinput", "average",
         "arrstats", "bsearch", "linsearch", "selection", "bubble", "guess", "dice", "temp", "lcm", "gcd", "leap", "digits",
         "evensum", "sumn", "binary", "power", "stars", "hms", "percent", "divisors", "triangle", "grade", "rect", "words",
         "countdown", "max3", "evenodd", "sum", "calc"]


# Слова, занятые хотя бы в одном из языков (ключевые слова и встроенные имена): переменные и функции задач их не используют
RESERVED = set("""base object string params event checked fixed lock out ref operator val var fun when is in end begin type set
file label with nil program mod div and or not to do of step next error rem loop match def let const func proc case default new
this self super class struct enum interface package import export from as use mut impl trait where move sealed mixin late
required final dynamic input args result real print len list dict str int float max min sum range char byte short long double
bool boolean void null true false none elif elsif unless until then fi done esac local function return break continue goto try
catch throw finally yield async await static public private protected go chan select defer map line num exit sizeof""".split())


# ====================================================================== обход программы и типы
STMT_KINDS = {"print", "write", "let", "set", "input", "if", "while", "for", "break", "return", "setidx", "rand", "func"}
EXPR_KINDS = {"num", "flt", "str", "bool", "var", "bin", "not", "neg", "call", "idx", "len", "arr", "tofloat", "fmt2",
              "rev", "lower", "nospace", "words", "sqrt", "pi"}
CMP = {"==", "!=", "<", "<=", ">", ">="}
_ARITH = {"+", "-", "*", "%", "//"}


def walk(x):
    """Все операторы и выражения внутри x (вглубь)."""
    if isinstance(x, tuple):
        if x and isinstance(x[0], str) and (x[0] in STMT_KINDS or x[0] in EXPR_KINDS):
            yield x
        for y in x[1:]:
            yield from walk(y)
    elif isinstance(x, list):
        for y in x:
            yield from walk(y)


def uses(stmts, kind, typ=None):
    """Есть ли в программе узел этого вида (для ввода — и этого типа)."""
    return any(n[0] == kind and (typ is None or n[2] == typ) for n in walk(stmts))


def var_used(stmts, name):
    return any(n[0] == "var" and n[1] == name for n in walk(stmts))


def etype(e, types, funcs):
    k = e[0]
    if k in ("num", "idx", "len", "words"):
        return "int"
    if k in ("flt", "tofloat", "sqrt", "pi"):
        return "float"
    if k in ("str", "fmt2", "rev", "lower", "nospace"):
        return "str"
    if k == "bool" or k == "not":
        return "bool"
    if k == "var":
        return types.get(e[1], "int")
    if k == "arr":
        return "arr"
    if k == "neg":
        return etype(e[1], types, funcs)
    if k == "call":
        return funcs[e[1]][3]
    o = e[1]                                  # bin
    if o == "/":
        return "float"
    if o in _ARITH:
        ta, tb = etype(e[2], types, funcs), etype(e[3], types, funcs)
        if "float" in (ta, tb):
            return "float"
        if "str" in (ta, tb):
            return "str"
        return "big" if "big" in (ta, tb) else "int"
    return "bool"


def collect_types(stmts, types):
    """Типы всех переменных функции — для языков, где их объявляют заранее (Pascal, Fortran)."""
    for s in stmts:
        k = s[0]
        if k in ("let", "input"):
            types.setdefault(s[1], s[2])
        elif k in ("for", "rand"):
            types.setdefault(s[1], "int")
        if k == "if":
            collect_types(s[2], types)
            collect_types(s[3], types)
        elif k == "while":
            collect_types(s[2], types)
        elif k == "for":
            collect_types(s[4], types)
    return types


def mutated(stmts, elements=True):
    """Переменные, которые меняются после объявления (им нужен var / let mut, остальным — val / const).

    elements=False — изменение элементов массива не в счёт (в JavaScript, Kotlin, Scala, Dart массив по ссылке:
    const nums = [...] можно менять поэлементно); в Rust и Swift — в счёт."""
    out, seen = set(), set()

    def go(ss):
        for s in ss:
            k = s[0]
            if k == "set":
                out.add(s[1])
            elif k == "input":
                if s[1] in seen:
                    out.add(s[1])
                seen.add(s[1])
            elif k in ("let", "rand"):
                seen.add(s[1])
            elif k == "setidx" and elements:
                out.add(s[1][1])
            elif k == "if":
                go(s[2])
                go(s[3])
            elif k == "while":
                go(s[2])
            elif k == "for":
                go(s[4])
    go(stmts)
    return out


def add_const(e, k):
    """e + k с упрощением: (n - 1) + 1 → n, n - 1 - i - 1 → n - i - 2 (массивы с 1, включительные границы циклов)."""
    const, terms = k, []

    def flat(x, sign):
        nonlocal const
        if x[0] == "bin" and x[1] in ("+", "-"):
            flat(x[2], sign)
            flat(x[3], sign if x[1] == "+" else -sign)
        elif x[0] == "num":
            const += sign * x[1]
        else:
            terms.append((sign, x))
    flat(e, 1)
    if not terms:
        return num(const)
    if terms[0][0] < 0:                       # -i + 5 → 5 - i
        out, rest = (num(const), terms) if const else (neg(terms[0][1]), terms[1:])
        const = 0 if out[0] == "num" else const
    else:
        out, rest = terms[0][1], terms[1:]
    for sign, x in rest:
        out = op("+" if sign > 0 else "-", out, x)
    if const:
        out = op("+" if const > 0 else "-", out, num(abs(const)))
    return out


class Env:
    """Переменные функции: типы (на всю функцию) и что уже объявлено в этом блоке."""

    def __init__(self, types, declared=(), mut=frozenset(), loops=(), ret=None, fn=None):
        self.types, self.declared, self.mut = types, set(declared), mut
        self.loops, self.ret, self.fn = list(loops), ret, fn

    def inner(self, loop=None):
        return Env(self.types, self.declared, self.mut, self.loops + ([loop] if loop else []), self.ret, self.fn)


C_OPS = {"==": "==", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">=", "+": "+", "-": "-", "*": "*", "/": "/",
         "//": "/", "%": "%", "and": "&&", "or": "||"}
C_PREC = {"or": 1, "and": 2, "==": 3, "!=": 3, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6, "//": 6,
          "%": 6}
ATOM = 9


# ====================================================================== переводчик: общая часть
class Emitter:
    key = name = ext = ""
    file = None                       # имя файла, если не main.<ext>
    fn_style = "snake"                # snake / camel / pascal
    ind = "    "
    T, F = "true", "false"
    NOT, NOT_PREC = "!", 7
    OPS, PREC = C_OPS, C_PREC
    INC = "{x}++"                     # x = x + 1
    ADD = "{x} {o}= {e}"              # x = x + e, x = x * e (None — нет составного присваивания)
    RENAME = {}                       # имена функций, занятые в языке встроенными

    def __init__(self, prog):
        self.prog = prog
        self.funcs = {f[1]: f for f in prog["funcs"]}
        self.helpers, self.imports = [], []

    # ---- служебное
    def use(self, *names):
        for n in names:
            if n not in self.helpers:
                self.helpers.append(n)

    def imp(self, *names):
        for n in names:
            if n not in self.imports:
                self.imports.append(n)

    def fname(self, name):
        name = self.RENAME.get(name, name)
        parts = name.split("_")
        if self.fn_style == "camel":
            return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])
        if self.fn_style == "pascal":
            return "".join(p[:1].upper() + p[1:] for p in parts)
        return name

    def v(self, name):
        return name

    def typ(self, e, env):
        return etype(e, env.types, self.funcs)

    def str_lit(self, s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    def flt_lit(self, x):
        return repr(float(x))

    def L(self, d, text):
        return self.ind * d + text

    # ---- выражения
    def expr(self, e, env, prec=0):
        text, p = self.ex(e, env)
        return f"({text})" if p < prec else text

    def ex(self, e, env):
        k = e[0]
        if k == "num":
            return str(e[1]), (ATOM if e[1] >= 0 else 7)
        if k == "flt":
            return self.flt_lit(e[1]), (ATOM if e[1] >= 0 else 7)
        if k == "str":
            return self.str_lit(e[1]), ATOM
        if k == "bool":
            return (self.T if e[1] else self.F), ATOM
        if k == "var":
            return self.v(e[1]), ATOM
        if k == "bin":
            return self.binary(e, env)
        if k == "not":
            return self.NOT + self.expr(e[1], env, self.NOT_PREC + 1), self.NOT_PREC
        if k == "neg":
            return "-" + self.expr(e[1], env, 8), 7
        if k == "call":
            return self.call(e, env), ATOM
        return getattr(self, "x_" + k)(e, env)

    def call(self, e, env):
        return f"{self.fname(e[1])}({', '.join(self.expr(a, env) for a in e[2])})"

    def binary(self, e, env):
        o, a, b = e[1], e[2], e[3]
        special = self.bin_special(o, a, b, env)
        if special:
            return special
        p = self.PREC[o]
        return f"{self.side(a, env, o, p, False)} {self.OPS[o]} {self.side(b, env, o, p, True)}", p

    def side(self, x, env, o, p, right):
        need = p + 1 if right or o in CMP else p
        # скобки для ясности: (a && b) || c, (a < b) == c
        if x[0] == "bin" and ((o == "or" and x[1] == "and") or (o in CMP and x[1] in CMP)):
            need = 99
        return self.expr(x, env, need)

    def bin_special(self, o, a, b, env):
        return None

    def x_tofloat(self, e, env):
        return self.ex(e[1], env)

    SQRT, PI = "sqrt({x})", "3.141592653589793"
    MATH = ()                         # что подключить, если нужны корень или пи

    def x_sqrt(self, e, env):
        self.imp(*self.MATH)
        if self.SQRT.startswith("{x}."):
            return self.SQRT.format(x=self.expr(e[1], env, ATOM)), ATOM
        return self.SQRT.format(x=self.expr(e[1], env)), ATOM

    def x_pi(self, e, env):
        self.imp(*self.MATH)
        return self.PI, ATOM

    # ---- операторы
    def block(self, stmts, env, d):
        out = []
        for s in stmts:
            out += getattr(self, "s_" + s[0])(s, env, d)
        return out

    def s_set(self, s, env, d):
        name, e = s[1], s[2]
        if e[0] == "bin" and e[1] in ("+", "-", "*") and e[2] == ("var", name) and not self.bin_special(*e[1:], env):
            if e[1] == "+" and e[3] == ("num", 1) and self.INC:
                return [self.L(d, self.end(self.INC.format(x=self.v(name))))]
            if self.ADD and (e[1] != "+" or self.typ(e[3], env) != "str"):
                return [self.L(d, self.end(self.ADD.format(x=self.v(name), o=e[1], e=self.expr(e[3], env))))]
        return [self.L(d, self.end(self.assign(name, self.expr(e, env))))]

    def assign(self, name, value):
        return f"{self.v(name)} = {value}"

    def end(self, text):
        return text

    def chain(self, s):
        """Цепочка if / else if / else: [(cond, body), ...], else-body."""
        branches, other = [(s[1], s[2])], s[3]
        while len(other) == 1 and other[0][0] == "if":
            branches.append((other[0][1], other[0][2]))
            other = other[0][3]
        return branches, other

    def forever(self, cond):
        return cond == ("bool", True)

    def program(self):
        raise NotImplementedError

    def render(self):
        return self.program().rstrip() + "\n"


def _print_parts(parts):
    """Части вывода: ("lit", текст) / ("expr", выражение) / ("fmt2", выражение); соседние строки склеены."""
    out = []
    for p in parts:
        if isinstance(p, str):
            if not p:
                continue
            if out and out[-1][0] == "lit":
                out[-1] = ("lit", out[-1][1] + p)
            else:
                out.append(("lit", p))
        elif p[0] == "str":
            if out and out[-1][0] == "lit":
                out[-1] = ("lit", out[-1][1] + p[1])
            else:
                out.append(("lit", p[1]))
        elif p[0] == "fmt2":
            out.append(("fmt2", p[1]))
        else:
            out.append(("expr", p))
    return out


# ---------------------------------------------------------------------- языки с фигурными скобками
class Braces(Emitter):
    semi = ";"
    paren_cond = True                 # if (x) — со скобками; Go, Rust, Swift — без
    allman = False                    # фигурная скобка на новой строке (C#)

    def end(self, text):
        return text + self.semi

    def cond(self, e, env):
        c = self.expr(e, env)
        return f"({c})" if self.paren_cond else c

    def opener(self, head, d):
        if self.allman:
            return [self.L(d, head), self.L(d, "{")]
        return [self.L(d, head + " {")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            head = ("if " if i == 0 else "else if ") + self.cond(c, env)
            if i and not self.allman:
                out[-1] = out[-1] + " " + head + " {"
            else:
                out += self.opener(head, d)
            out += self.block(body, env.inner(), d + 1)
            out.append(self.L(d, "}"))
        if other:
            if self.allman:
                out += [self.L(d, "else"), self.L(d, "{")]
            else:
                out[-1] += " else {"
            out += self.block(other, env.inner(), d + 1)
            out.append(self.L(d, "}"))
        return out

    def while_head(self, c, env):
        return "while " + ("(true)" if self.paren_cond and self.forever(c) else self.cond(c, env))

    def s_while(self, s, env, d):
        return self.opener(self.while_head(s[1], env), d) + self.block(s[2], env.inner("while"), d + 1) + [self.L(d, "}")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1], s[2], s[3], s[4]
        env.types[name] = "int"
        inner = env.inner("for")
        inner.declared.add(name)
        return self.opener(self.for_head(name, a, b, env, body), d) + self.block(body, inner, d + 1) + [self.L(d, "}")]

    def for_head(self, name, a, b, env, body):
        x = self.v(name)
        return f"for ({self.decl_int()} {x} = {self.expr(a, env)}; {self.upto(x, b, env)}; {x}++)"

    def upto(self, x, b, env, lt="<", le="<="):
        """Условие цикла: i < n, а вместо i < n + 1 — i <= n."""
        if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
            return f"{x} {le} {self.expr(b[2], env, C_PREC['+'])}"
        return f"{x} {lt} {self.expr(b, env, C_PREC['+'])}"

    def decl_int(self):
        return "int"

    def s_break(self, s, env, d):
        return [self.L(d, self.end("break"))]

    def s_return(self, s, env, d):
        return [self.L(d, self.end("return " + self.expr(s[1], env)))]

    def s_setidx(self, s, env, d):
        return [self.L(d, self.end(f"{self.expr(s[1], env, ATOM)}[{self.index(s[2], env)}] = {self.expr(s[3], env)}"))]

    def index(self, i, env):
        return self.expr(i, env)

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.index(e[2], env)}]", ATOM

    def s_let(self, s, env, d):
        name, typ, e = s[1], s[2], s[3]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, self.end(self.declare(name, typ, e, env)))]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], s[3]
        value = self.read(typ, prompt, env)
        if name in env.declared:
            return [self.L(d, self.end(self.assign(name, value)))]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, self.end(self.declare_value(name, typ, value, env)))]

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        env.declared.add(s[1])
        return [self.L(d, self.end(self.declare_value(s[1], "int", self.random(s[2], s[3]), env)))]

    def declare(self, name, typ, e, env):
        return self.declare_value(name, typ, self.expr(e, env), env)

    def s_print(self, s, env, d):
        return [self.L(d, self.end(self.out(_print_parts(s[1]), env, True)))]

    def s_write(self, s, env, d):
        return [self.L(d, self.end(self.out(_print_parts(s[1]), env, False)))]

    def body_of(self, f, d=1):
        """Тело функции: строки с отступом d."""
        name, params, ret, body = f[1], f[2], f[3], f[4]
        types = {p: t for p, t in params}
        env = Env(types, declared=[p for p, _ in params], mut=mutated(body, self.ELEMENTS), ret=ret, fn=name)
        return self.block(body, env, d)

    ELEMENTS = True                   # меняется элемент массива — переменная тоже «изменяемая» (Rust, Swift)

    def main_env(self):
        return Env({}, mut=mutated(self.prog["main"], self.ELEMENTS))


# ====================================================================== Python
class Python(Emitter):
    key, name, ext = "python", "Python", "py"
    SQRT, PI, MATH = "math.sqrt({x})", "math.pi", ("import math",)
    T, F = "True", "False"
    NOT, NOT_PREC = "not ", 2.5
    OPS = dict(C_OPS, **{"//": "//", "and": "and", "or": "or"})
    PREC = dict(C_PREC, **{"==": 4, "!=": 4})
    INC = None
    HINT = {"int": "int", "big": "int", "float": "float", "str": "str", "bool": "bool", "arr": "list[int]"}

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(e[2], env)}]", ATOM

    def x_len(self, e, env):
        return f"len({self.expr(e[1], env)})", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f'f"{{{self.expr(e[1], env)}:.2f}}"', ATOM

    def x_rev(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[::-1]", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.lower()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.replace(" ", "")', ATOM

    def x_words(self, e, env):
        return f"len({self.expr(e[1], env, ATOM)}.split())", ATOM

    def block(self, stmts, env, d):
        out = Emitter.block(self, stmts, env, d)
        return out or [self.L(d, "pass")]

    def out(self, parts, env, end):
        tail = "" if end else ', end=""'
        if not parts:
            return f"print({tail[2:]})"
        if len(parts) == 1 and parts[0][0] == "lit":
            return f"print({self.str_lit(parts[0][1])}{tail})"
        if len(parts) == 1 and parts[0][0] == "expr":
            return f"print({self.expr(parts[0][1], env)}{tail})"
        body, quote = "", '"'
        for kind, x in parts:
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace("{", "{{").replace("}", "}}")
            else:
                hole = self.expr(x, env)
                if '"' in hole:
                    quote = "'"
                body += "{" + hole + (":.2f}" if kind == "fmt2" else "}")
        return f"print(f{quote}{body.replace(quote, chr(92) + quote)}{quote}{tail})"

    def s_print(self, s, env, d):
        return [self.L(d, self.out(_print_parts(s[1]), env, True))]

    def s_write(self, s, env, d):
        return [self.L(d, self.out(_print_parts(s[1]), env, False))]

    def s_let(self, s, env, d):
        env.types[s[1]] = s[2]
        return [self.L(d, f"{s[1]} = {self.expr(s[3], env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        env.types[name] = typ
        value = {"int": f"int(input({prompt}))", "float": f'float(input({prompt}).replace(",", "."))'}.get(typ, f"input({prompt})")
        return [self.L(d, f"{name} = {value}")]

    def s_rand(self, s, env, d):
        self.imp("import random")
        env.types[s[1]] = "int"
        return [self.L(d, f"{s[1]} = random.randint({s[2]}, {s[3]})")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "elif ") + self.expr(c, env) + ":"))
            out += self.block(body, env, d + 1)
        if other:
            out.append(self.L(d, "else:"))
            out += self.block(other, env, d + 1)
        return out

    def s_while(self, s, env, d):
        c = "True" if self.forever(s[1]) else self.expr(s[1], env)
        return [self.L(d, f"while {c}:")] + self.block(s[2], env, d + 1)

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        var = name if var_used(body, name) else "_"
        rng = self.expr(b, env) if a == ("num", 0) else f"{self.expr(a, env)}, {self.expr(b, env)}"
        return [self.L(d, f"for {var} in range({rng}):")] + self.block(body, env, d + 1)

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        return [self.L(d, "return " + self.expr(s[1], env))]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(s[2], env)}] = {self.expr(s[3], env)}")]

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params})
            args = ", ".join(f"{p}: {self.HINT[t]}" for p, t in params)
            funcs.append(f"def {name}({args}) -> {self.HINT[ret]}:\n" + "\n".join(self.block(body, env, 1)))
        main = "\n".join(self.block(self.prog["main"], Env({}), 0))
        head = "\n".join(self.imports)
        parts = ([head] if head else []) + funcs + [main]
        return "\n\n\n".join(parts)


# ====================================================================== JavaScript / TypeScript
class JavaScript(Braces):
    key, name, ext = "javascript", "JavaScript", "js"
    SQRT, PI = "Math.sqrt({x})", "Math.PI"
    fn_style = "camel"
    ind = "  "
    OPS = dict(C_OPS, **{"==": "===", "!=": "!=="})
    ELEMENTS = False
    line_declared = wrote = False
    writes_left = 0

    def flt_lit(self, x):
        return str(int(x)) if float(x).is_integer() else repr(float(x))

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"Math.floor({self.expr(a, env, 6)} / {self.expr(b, env, 7)})", ATOM
        return None

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.length", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toFixed(2)", ATOM

    def x_rev(self, e, env):
        return f'[...{self.expr(e[1], env, ATOM)}].reverse().join("")', ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toLowerCase()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.split(" ").join("")', ATOM

    def x_words(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.split(/\\s+/).filter(Boolean).length", ATOM

    def template(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "lit":
            return self.str_lit(parts[0][1])
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        body = ""
        for kind, x in parts:
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
            else:
                body += "${" + self.expr(("fmt2", x) if kind == "fmt2" else x, env) + "}"
        return "`" + body + "`"

    # console.log всегда переводит строку, поэтому «вывод без перевода строки» копится в переменной line:
    # write → line += …, а print выводит накопленное и очищает line, если дальше (или в том же цикле) снова пишут.
    def block(self, stmts, env, d):
        out = []
        for s in stmts:
            if not self.line_declared and s[0] != "write" and uses([s], "write"):
                out.append(self.L(d, 'let line = "";'))      # первый вывод без перевода строки — внутри цикла или if
                self.line_declared = True
            out += getattr(self, "s_" + s[0])(s, env, d)
        return out

    def s_print(self, s, env, d):
        parts = _print_parts(s[1])
        if not self.wrote:
            return [self.L(d, f"console.log({self.template(parts, env) if parts else ''});")]
        out = [self.L(d, f"console.log(line + {self.template(parts, env)});" if parts else "console.log(line);")]
        if env.loops or self.writes_left:
            out.append(self.L(d, 'line = "";'))
        if not env.loops:
            self.wrote = False
        return out

    def s_write(self, s, env, d):
        parts = _print_parts(s[1])
        text = self.template(parts, env)
        self.wrote = True
        self.writes_left -= 1
        if not self.line_declared:
            self.line_declared = True
            if len(parts) == 1 and parts[0][0] == "expr" and self.typ(parts[0][1], env) != "str":
                text = f"String({text})"                   # line — строка, даже если первым выводится число
            return [self.L(d, f"let line = {text};")]
        return [self.L(d, f"line += {text};")]

    def declare_value(self, name, typ, value, env):
        return f"{'let' if name in env.mut else 'const'} {self.v(name)} = {value}"

    def read(self, typ, prompt, env):
        self.use("ask")
        p = self.str_lit(prompt)
        return {"int": f"parseInt(ask({p}), 10)", "float": f'parseFloat(ask({p}).replace(",", "."))'}.get(typ, f"ask({p})")

    def random(self, lo, hi):
        return f"Math.floor(Math.random() * {hi - lo + 1}) + {lo}"

    def decl_int(self):
        return "let"

    def func_head(self, name, params, ret):
        return f"function {self.fname(name)}({', '.join(p for p, _ in params)})"

    HELPERS = {
        "ask": '''// Ввод с клавиатуры: в браузере (и в Rai Code), Deno и Bun — prompt(), в Node.js — строка из консоли
function ask(question) {
  if (typeof prompt === "function") return prompt(question) ?? "";
  process.stdout.write(question);
  const fs = require("fs");
  const byte = Buffer.alloc(1);
  const bytes = [];
  try {
    while (fs.readSync(0, byte, 0, 1) === 1 && byte[0] !== 10) bytes.push(byte[0]);
  } catch (e) {
    // ввод закончился
  }
  return Buffer.from(bytes).toString("utf8").replace(/\\r$/, "");
}''',
    }

    def program(self):
        funcs = []
        self.line_declared = self.wrote = False
        self.writes_left = sum(1 for n in walk(self.prog["main"]) if n[0] == "write")
        for f in self.prog["funcs"]:
            funcs.append("\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"]))
        main = "\n".join(self.block(self.prog["main"], self.main_env(), 0))
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(helpers + funcs + [main])


class TypeScript(JavaScript):
    key, name, ext = "typescript", "TypeScript", "ts"
    TS = {"int": "number", "big": "number", "float": "number", "str": "string", "bool": "boolean", "arr": "number[]"}

    def x_rev(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.split("").reverse().join("")', ATOM

    def func_head(self, name, params, ret):
        args = ", ".join(f"{p}: {self.TS[t]}" for p, t in params)
        return f"function {self.fname(name)}({args}): {self.TS[ret]}"

    def declare_value(self, name, typ, value, env):
        kw = "let" if name in env.mut else "const"
        if typ == "arr":
            return f"{kw} {name}: number[] = {value}"
        return f"{kw} {name} = {value}"

    HELPERS = {
        "ask": '''// Ввод с клавиатуры: в браузере, Deno и Bun — prompt(), в Node.js — строка из консоли
function ask(question: string): string {
  const g: any = globalThis;
  if (typeof g.prompt === "function") return g.prompt(question) ?? "";
  g.process.stdout.write(question);
  const fs = eval("require")("fs");
  const byte = g.Buffer.alloc(1);
  const bytes: number[] = [];
  try {
    while (fs.readSync(0, byte, 0, 1) === 1 && byte[0] !== 10) bytes.push(byte[0]);
  } catch (e) {
    // ввод закончился
  }
  return g.Buffer.from(bytes).toString("utf8").replace(/\\r$/, "");
}''',
    }


# ====================================================================== C
class C(Braces):
    key, name, ext = "c", "C", "c"
    SQRT, MATH = "sqrt({x})", ("math.h",)
    CT = {"int": "int", "big": "long long", "float": "double", "bool": "bool"}
    FMT = {"int": "%d", "big": "%lld", "float": "%g", "str": "%s", "bool": "%d"}

    def bin_special(self, o, a, b, env):
        if o in ("==", "!=") and self.typ(a, env) == "str":
            return f"strcmp({self.expr(a, env)}, {self.expr(b, env)}) {o} 0", 3
        return None

    def x_tofloat(self, e, env):
        return f"(double){self.expr(e[1], env, 8)}", 7

    def x_len(self, e, env):
        a = self.expr(e[1], env, ATOM)
        return f"(int)(sizeof {a} / sizeof {a}[0])", 7

    def x_rev(self, e, env):
        self.use("reverse")
        return f"reverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        self.use("to_lower")
        return f"to_lower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        self.use("remove_spaces")
        return f"remove_spaces({self.expr(e[1], env)})", ATOM

    def x_words(self, e, env):
        self.use("count_words")
        return f"count_words({self.expr(e[1], env)})", ATOM

    def x_fmt2(self, e, env):
        raise ValueError("fmt2 в C — только в выводе")

    def out(self, parts, env, newline):
        fmt, args = "", []
        for kind, x in parts:
            if kind == "lit":
                fmt += x.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
            elif kind == "fmt2":
                fmt += "%.2f"
                args.append(self.expr(x, env))
            else:
                fmt += self.FMT[self.typ(x, env)]
                args.append(self.expr(x, env))
        fmt += "\\n" if newline else ""
        return f'printf("{fmt}"' + "".join(", " + a for a in args) + ")"

    def declare_value(self, name, typ, value, env):
        if typ == "str":
            return f"char {name}[1024];\n{self.ind * self.depth}strcpy({name}, {value})"
        return f"{self.CT[typ]} {name} = {value}"

    def s_let(self, s, env, d):
        name, typ, e = s[1], s[2], s[3]
        env.types[name] = typ
        env.declared.add(name)
        if typ == "arr":
            return [self.L(d, f"int {name}[] = {{{', '.join(self.expr(x, env) for x in e[1])}}};")]
        if typ == "str":
            self.imp("string.h")
            return [self.L(d, f"char {name}[1024];"), self.L(d, f"strcpy({name}, {self.expr(e, env)});")]
        if typ == "bool":
            self.imp("stdbool.h")
        return [self.L(d, f"{self.CT[typ]} {name} = {self.expr(e, env)};")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        if typ == "str":
            self.use("read_line")
            env.types[name] = typ
            pre = [] if name in env.declared else [self.L(d, f"char {name}[1024];")]
            env.declared.add(name)
            return pre + [self.L(d, f"read_line({prompt}, {name}, sizeof {name});")]
        self.use("read_int" if typ == "int" else "read_double")
        value = f"read_int({prompt})" if typ == "int" else f"read_double({prompt})"
        if name in env.declared:
            return [self.L(d, f"{name} = {value};")]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, f"{self.CT[typ]} {name} = {value};")]

    def s_rand(self, s, env, d):
        self.imp("stdlib.h", "time.h")
        env.types[s[1]] = "int"
        env.declared.add(s[1])
        return [self.L(d, "srand((unsigned)time(NULL));"), self.L(d, f"int {s[1]} = rand() % {s[3] - s[2] + 1} + {s[2]};")]

    HELPERS = {
        "read_int": ("stdlib.h", '''int read_int(const char *prompt) {
    char line[256];
    printf("%s", prompt);
    fflush(stdout);
    if (!fgets(line, sizeof line, stdin)) return 0;
    return atoi(line);
}'''),
        "read_double": ("stdlib.h", '''double read_double(const char *prompt) {
    char line[256];
    printf("%s", prompt);
    fflush(stdout);
    if (!fgets(line, sizeof line, stdin)) return 0;
    for (char *p = line; *p; p++)
        if (*p == ',') *p = '.';   /* 36,6 тоже подходит */
    return atof(line);
}'''),
        "read_line": ("string.h", '''void read_line(const char *prompt, char *buf, size_t size) {
    printf("%s", prompt);
    fflush(stdout);
    if (!fgets(buf, (int)size, stdin)) buf[0] = '\\0';
    buf[strcspn(buf, "\\r\\n")] = '\\0';
}'''),
        "reverse": ("string.h", '''/* Строка наоборот по символам UTF-8 — русские буквы не ломаются */
char *reverse(const char *s) {
    static char out[1024];
    size_t n = strlen(s), i = 0;
    if (n >= sizeof out) n = sizeof out - 1;
    out[n] = '\\0';
    while (i < n) {
        unsigned char c = (unsigned char)s[i];
        size_t len = c >= 0xF0 ? 4 : c >= 0xE0 ? 3 : c >= 0xC0 ? 2 : 1;
        if (i + len > n) len = n - i;
        memcpy(out + n - i - len, s + i, len);
        i += len;
    }
    return out;
}'''),
        "to_lower": ("string.h", '''/* Строчные буквы: латиница и кириллица в UTF-8 */
char *to_lower(const char *s) {
    static char out[1024];
    size_t i = 0;
    for (; s[i] && i < sizeof out - 2; i++) {
        unsigned char c = (unsigned char)s[i], next = (unsigned char)s[i + 1];
        if (c >= 'A' && c <= 'Z') {
            out[i] = (char)(c + 32);
        } else if (c == 0xD0 && next >= 0x90 && next <= 0x9F) {          /* А–П */
            out[i] = (char)0xD0;
            out[++i] = (char)(next + 0x20);
        } else if (c == 0xD0 && next >= 0xA0 && next <= 0xAF) {          /* Р–Я */
            out[i] = (char)0xD1;
            out[++i] = (char)(next - 0x20);
        } else if (c == 0xD0 && next == 0x81) {                          /* Ё */
            out[i] = (char)0xD1;
            out[++i] = (char)0x91;
        } else {
            out[i] = (char)c;
        }
    }
    out[i] = '\\0';
    return out;
}'''),
        "remove_spaces": ("string.h", '''char *remove_spaces(const char *s) {
    static char out[1024];
    size_t j = 0;
    for (size_t i = 0; s[i] && j < sizeof out - 1; i++)
        if (s[i] != ' ') out[j++] = s[i];
    out[j] = '\\0';
    return out;
}'''),
        "count_words": ("ctype.h", '''int count_words(const char *s) {
    int count = 0, in_word = 0;
    for (; *s; s++) {
        if (isspace((unsigned char)*s)) in_word = 0;
        else if (!in_word) { in_word = 1; count++; }
    }
    return count;
}'''),
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.CT[t]} {p}" for p, t in params) or "void"
        if ret == "bool" or any(t == "bool" for _, t in params):
            self.imp("stdbool.h")
        return f"{self.CT[ret]} {self.fname(name)}({args})"

    def program(self):
        self.depth = 1
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 1)
        if uses(self.prog["main"] + self.prog["funcs"], "bool"):
            self.imp("stdbool.h")
        helpers = []
        for h in self.helpers:
            header, code = self.HELPERS[h]
            self.imp(header)
            helpers.append(code)
        order = ["math.h", "stdio.h", "stdlib.h", "string.h", "ctype.h", "stdbool.h", "time.h"]
        incs = "\n".join(f"#include <{h}>" for h in order if h == "stdio.h" or h in self.imports)
        if "math.h" in self.imports:
            incs = "/* Сборка: gcc main.c -o main -lm  (-lm подключает математику: sqrt) */\n" + incs
        body = "\n".join(["int main(void) {"] + main + ["    return 0;", "}"])
        return "\n\n".join([incs] + helpers + funcs + [body])


# ====================================================================== C++
class Cpp(Braces):
    key, name, ext = "cpp", "C++", "cpp"
    SQRT, MATH = "std::sqrt({x})", ("cmath",)
    CT = {"int": "int", "big": "long long", "float": "double", "str": "std::string", "bool": "bool", "arr": "std::vector<int>"}

    def x_tofloat(self, e, env):
        return f"static_cast<double>({self.expr(e[1], env)})", ATOM

    def x_len(self, e, env):
        return f"static_cast<int>({self.expr(e[1], env, ATOM)}.size())", ATOM

    def x_arr(self, e, env):
        return "{" + ", ".join(self.expr(x, env) for x in e[1]) + "}", ATOM

    def x_rev(self, e, env):
        self.use("reverse_utf8")
        return f"reverse_utf8({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        self.use("to_lower")
        return f"to_lower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        self.use("remove_spaces")
        return f"remove_spaces({self.expr(e[1], env)})", ATOM

    def x_words(self, e, env):
        self.use("count_words")
        return f"count_words({self.expr(e[1], env)})", ATOM

    def x_fmt2(self, e, env):
        self.use("fmt2")
        return f"fmt2({self.expr(e[1], env)})", ATOM

    def out(self, parts, env, newline):
        items = []
        for kind, x in parts:
            if kind == "lit":
                items.append(self.str_lit(x))
            elif kind == "fmt2":
                self.imp("iomanip")
                items.append(f"std::fixed << std::setprecision(2) << {self.expr(x, env, 5)}")
            else:
                items.append(self.expr(x, env, 5))
        if newline:
            if items and items[-1].startswith('"'):
                items[-1] = items[-1][:-1] + '\\n"'
            else:
                items.append('"\\n"')
        return "std::cout << " + " << ".join(items)

    def declare_value(self, name, typ, value, env):
        return f"{self.CT[typ]} {name} = {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "read_int", "float": "read_double"}.get(typ, "read_line")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def s_rand(self, s, env, d):
        self.imp("random")
        env.types[s[1]] = "int"
        env.declared.add(s[1])
        return [self.L(d, "std::mt19937 rng(std::random_device{}());"),
                self.L(d, f"int {s[1]} = std::uniform_int_distribution<int>({s[2]}, {s[3]})(rng);")]

    HELPERS = {
        "read_line": ((), '''std::string read_line(const std::string& prompt) {
    std::cout << prompt;
    std::string line;
    std::getline(std::cin, line);
    return line;
}'''),
        "read_int": ((), '''int read_int(const std::string& prompt) {
    return std::stoi(read_line(prompt));
}'''),
        "read_double": (("algorithm",), '''double read_double(const std::string& prompt) {
    std::string line = read_line(prompt);
    std::replace(line.begin(), line.end(), ',', '.');   // 36,6 тоже подходит
    return std::stod(line);
}'''),
        "reverse_utf8": ((), '''// Строка наоборот по символам UTF-8 — русские буквы не ломаются
std::string reverse_utf8(const std::string& s) {
    std::string out;
    for (size_t i = 0; i < s.size();) {
        unsigned char c = s[i];
        size_t len = c >= 0xF0 ? 4 : c >= 0xE0 ? 3 : c >= 0xC0 ? 2 : 1;
        out.insert(0, s.substr(i, len));
        i += len;
    }
    return out;
}'''),
        "to_lower": ((), '''// Строчные буквы: латиница и кириллица в UTF-8
std::string to_lower(const std::string& s) {
    std::string out;
    for (size_t i = 0; i < s.size(); i++) {
        unsigned char c = s[i], next = i + 1 < s.size() ? s[i + 1] : 0;
        if (c >= 'A' && c <= 'Z') {
            out += static_cast<char>(c + 32);
        } else if (c == 0xD0 && next >= 0x90 && next <= 0x9F) {         // А–П
            out += static_cast<char>(0xD0);
            out += static_cast<char>(next + 0x20);
            i++;
        } else if (c == 0xD0 && next >= 0xA0 && next <= 0xAF) {         // Р–Я
            out += static_cast<char>(0xD1);
            out += static_cast<char>(next - 0x20);
            i++;
        } else if (c == 0xD0 && next == 0x81) {                         // Ё
            out += static_cast<char>(0xD1);
            out += static_cast<char>(0x91);
            i++;
        } else {
            out += static_cast<char>(c);
        }
    }
    return out;
}'''),
        "remove_spaces": ((), '''std::string remove_spaces(std::string s) {
    s.erase(std::remove(s.begin(), s.end(), ' '), s.end());
    return s;
}'''),
        "count_words": (("sstream",), '''int count_words(const std::string& s) {
    std::istringstream in(s);
    std::string word;
    int count = 0;
    while (in >> word) count++;
    return count;
}'''),
        "fmt2": (("iomanip", "sstream"), '''std::string fmt2(double x) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(2) << x;
    return out.str();
}'''),
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.CT[t]} {p}" for p, t in params)
        return f"{self.CT[ret]} {self.fname(name)}({args})"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 1)
        if "remove_spaces" in self.helpers:
            self.imp("algorithm")
        if "read_int" in self.helpers or "read_double" in self.helpers:
            self.helpers.insert(0, "read_line") if "read_line" not in self.helpers else None
            self.helpers.remove("read_line")
            self.helpers.insert(0, "read_line")
        helpers = []
        for h in self.helpers:
            libs, code = self.HELPERS[h]
            self.imp(*libs)
            helpers.append(code)
        need = {"iostream", "string"} | set(self.imports)
        if any(t == "arr" for t in collect_types(self.prog["main"], {}).values()):
            need.add("vector")
        order = ["algorithm", "cmath", "iomanip", "iostream", "random", "sstream", "string", "vector"]
        incs = "\n".join(f"#include <{h}>" for h in order if h in need)
        body = "\n".join(["int main() {"] + main + ["    return 0;", "}"])
        return "\n\n".join([incs] + helpers + funcs + [body])



# ====================================================================== Java
class Java(Braces):
    key, name, ext, file = "java", "Java", "java", "Main.java"
    SQRT, PI = "Math.sqrt({x})", "Math.PI"
    fn_style = "camel"
    JT = {"int": "int", "big": "long", "float": "double", "str": "String", "bool": "boolean", "arr": "int[]"}

    def bin_special(self, o, a, b, env):
        if o in ("==", "!=") and self.typ(a, env) == "str":
            eq = f"{self.expr(a, env, ATOM)}.equals({self.expr(b, env)})"
            return (eq, ATOM) if o == "==" else ("!" + eq, 7)
        return None

    def x_tofloat(self, e, env):
        return f"(double) {self.expr(e[1], env, 8)}", 7

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.length", ATOM

    def x_arr(self, e, env):
        return "{" + ", ".join(self.expr(x, env) for x in e[1]) + "}", ATOM

    def x_fmt2(self, e, env):
        return f'String.format("%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"new StringBuilder({self.expr(e[1], env)}).reverse().toString()", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toLowerCase()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.replace(" ", "")', ATOM

    def x_words(self, e, env):
        self.use("countWords")
        return f"countWords({self.expr(e[1], env)})", ATOM

    def concat(self, parts, env, plus=" + "):
        """Склейка строки для println: числа в скобках, чтобы "a" + (x + y) не стало "a" + x + y."""
        items = []
        for kind, x in parts:
            if kind == "lit":
                items.append(self.str_lit(x))
            else:
                items.append(self.expr(("fmt2", x) if kind == "fmt2" else x, env, 6))
        if len(items) > 1 and parts[0][0] != "lit" and parts[1][0] != "lit":
            items.insert(0, '""')
        return plus.join(items)

    def out(self, parts, env, newline):
        return f"System.out.{'println' if newline else 'print'}({self.concat(parts, env)})"

    def declare_value(self, name, typ, value, env):
        return f"{self.JT[typ]} {name} = {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "readInt", "float": "readDouble"}.get(typ, "readLine")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        self.imp("java.util.Random")
        return f"new Random().nextInt({hi - lo + 1}) + {lo}"

    HELPERS = {
        "readLine": """    static String readLine(String prompt) {
        System.out.print(prompt);
        return IN.hasNextLine() ? IN.nextLine() : "";
    }""",
        "readInt": """    static int readInt(String prompt) {
        return Integer.parseInt(readLine(prompt).trim());
    }""",
        "readDouble": """    static double readDouble(String prompt) {
        return Double.parseDouble(readLine(prompt).trim().replace(',', '.'));   // 36,6 тоже подходит
    }""",
        "countWords": """    static int countWords(String s) {
        String t = s.trim();
        return t.isEmpty() ? 0 : t.split("\\\\s+").length;
    }""",
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.JT[t]} {p}" for p, t in params)
        return f"static {self.JT[ret]} {self.fname(name)}({args})"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 1) + self.body_of(f, 2) + [self.L(1, "}")])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 2)
        reading = [h for h in self.helpers if h.startswith("read")]
        if reading and "readLine" not in reading:
            self.helpers.insert(0, "readLine")
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "readLine")]
        head = []
        if reading:
            self.imp("java.util.Scanner")
        imports = "\n".join(f"import {i};" for i in sorted(self.imports))
        cls = ["public class Main {"]
        if reading:
            cls.append("    static final Scanner IN = new Scanner(System.in);\n")
        body = "\n\n".join(helpers + funcs + ["\n".join([self.L(1, "public static void main(String[] args) {")] + main + [self.L(1, "}")])])
        return (imports + "\n\n" if imports else "") + "\n".join(cls) + ("\n" if not reading else "") + body + "\n}"


# ====================================================================== C#
class CSharp(Braces):
    key, name, ext, file = "csharp", "C#", "cs", "Program.cs"
    SQRT, PI = "Math.Sqrt({x})", "Math.PI"
    fn_style = "pascal"
    allman = True
    CT = {"int": "int", "big": "long", "float": "double", "str": "string", "bool": "bool", "arr": "int[]"}

    def x_tofloat(self, e, env):
        return f"(double){self.expr(e[1], env, 8)}", 7

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.Length", ATOM

    def x_arr(self, e, env):
        return "{ " + ", ".join(self.expr(x, env) for x in e[1]) + " }", ATOM

    def x_fmt2(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.ToString("F2")', ATOM

    def x_rev(self, e, env):
        self.use("Reverse")
        return f"Reverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.ToLower()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.Replace(" ", "")', ATOM

    def x_words(self, e, env):
        return (f"{self.expr(e[1], env, ATOM)}.Split(new[] {{ ' ', '\\t' }}, StringSplitOptions.RemoveEmptyEntries).Length",
                ATOM)

    def out(self, parts, env, newline):
        fn = "Console.WriteLine" if newline else "Console.Write"
        if not parts:
            return fn + "()"
        if len(parts) == 1 and parts[0][0] == "lit":
            return f"{fn}({self.str_lit(parts[0][1])})"
        if len(parts) == 1 and parts[0][0] == "expr":
            return f"{fn}({self.expr(parts[0][1], env)})"
        body = ""
        for kind, x in parts:
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace('"', '\\"').replace("{", "{{").replace("}", "}}")
            else:
                body += "{" + self.expr(x, env, 1) + (":F2}" if kind == "fmt2" else "}")
        return f'{fn}($"{body}")'

    def declare_value(self, name, typ, value, env):
        return f"{self.CT[typ]} {name} = {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "ReadInt", "float": "ReadDouble"}.get(typ, "ReadLine")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        return f"new Random().Next({lo}, {hi + 1})"

    HELPERS = {
        "ReadLine": """    static string ReadLine(string prompt)
    {
        Console.Write(prompt);
        return Console.ReadLine() ?? "";
    }""",
        "ReadInt": """    static int ReadInt(string prompt)
    {
        return int.Parse(ReadLine(prompt).Trim());
    }""",
        "ReadDouble": """    static double ReadDouble(string prompt)
    {
        // 36,6 и 36.6 подходят при любых настройках Windows
        return double.Parse(ReadLine(prompt).Trim().Replace(',', '.'), CultureInfo.InvariantCulture);
    }""",
        "Reverse": """    static string Reverse(string s)
    {
        char[] chars = s.ToCharArray();
        Array.Reverse(chars);
        return new string(chars);
    }""",
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.CT[t]} {p}" for p, t in params)
        return f"static {self.CT[ret]} {self.fname(name)}({args})"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 1) + self.body_of(f, 2) + [self.L(1, "}")])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 2)
        reading = [h for h in self.helpers if h.startswith("Read")]
        if reading and "ReadLine" not in reading:
            self.helpers.insert(0, "ReadLine")
        usings = ["System"] + (["System.Globalization"] if "ReadDouble" in self.helpers else [])
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "ReadLine")]
        body = "\n\n".join(helpers + funcs + ["\n".join([self.L(1, "static void Main()"), self.L(1, "{")] + main + [self.L(1, "}")])])
        return "\n".join(f"using {u};" for u in usings) + "\n\nclass Program\n{\n" + body + "\n}"


# ====================================================================== Go
class Go(Braces):
    key, name, ext = "go", "Go", "go"
    SQRT, PI, MATH = "math.Sqrt({x})", "math.Pi", ("math",)
    fn_style = "camel"
    ind = "\t"
    semi = ""
    paren_cond = False
    GT = {"int": "int", "big": "int", "float": "float64", "str": "string", "bool": "bool", "arr": "[]int"}
    VERB = {"int": "%d", "big": "%d", "float": "%v", "str": "%s", "bool": "%t"}

    def x_tofloat(self, e, env):
        return f"float64({self.expr(e[1], env)})", ATOM

    def x_len(self, e, env):
        return f"len({self.expr(e[1], env)})", ATOM

    def x_arr(self, e, env):
        return "[]int{" + ", ".join(self.expr(x, env) for x in e[1]) + "}", ATOM

    def x_fmt2(self, e, env):
        return f'fmt.Sprintf("%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        self.use("reverse")
        return f"reverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        self.imp("strings")
        return f"strings.ToLower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        self.imp("strings")
        return f'strings.ReplaceAll({self.expr(e[1], env)}, " ", "")', ATOM

    def x_words(self, e, env):
        self.imp("strings")
        return f"len(strings.Fields({self.expr(e[1], env)}))", ATOM

    def out(self, parts, env, newline):
        if all(k == "lit" for k, _ in parts) or not parts:
            text = "".join(x for _, x in parts)
            return f"fmt.Println({self.str_lit(text)})" if newline else f"fmt.Print({self.str_lit(text)})"
        if len(parts) == 1 and parts[0][0] == "expr":
            return f"fmt.{'Println' if newline else 'Print'}({self.expr(parts[0][1], env)})"
        fmt, args = "", []
        for kind, x in parts:
            if kind == "lit":
                fmt += x.replace("%", "%%")
            else:
                fmt += "%.2f" if kind == "fmt2" else self.VERB[self.typ(x, env)]
                args.append(self.expr(x, env))
        return f"fmt.Printf({self.str_lit(fmt + chr(10) if newline else fmt)}".replace("\n", "\\n") + "".join(", " + a for a in args) + ")"

    def declare_value(self, name, typ, value, env):
        return f"{name} := {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "readInt", "float": "readFloat"}.get(typ, "readLine")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        self.imp("math/rand")
        return f"rand.Intn({hi - lo + 1}) + {lo}"

    def while_head(self, c, env):
        return "for" if self.forever(c) else "for " + self.expr(c, env)

    def for_head(self, name, a, b, env, body):
        return f"for {name} := {self.expr(a, env)}; {self.upto(name, b, env)}; {name}++"

    HELPERS = {
        "readLine": (("bufio", "os", "strings"), """var reader = bufio.NewReader(os.Stdin)

func readLine(prompt string) string {
	fmt.Print(prompt)
	line, _ := reader.ReadString('\\n')
	return strings.TrimRight(line, "\\r\\n")
}"""),
        "readInt": (("strconv",), """func readInt(prompt string) int {
	n, _ := strconv.Atoi(strings.TrimSpace(readLine(prompt)))
	return n
}"""),
        "readFloat": (("strconv",), """func readFloat(prompt string) float64 {
	text := strings.ReplaceAll(strings.TrimSpace(readLine(prompt)), ",", ".") // 36,6 тоже подходит
	x, _ := strconv.ParseFloat(text, 64)
	return x
}"""),
        "reverse": ((), """// Строка наоборот: по символам (rune), чтобы русские буквы не ломались
func reverse(s string) string {
	r := []rune(s)
	for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
		r[i], r[j] = r[j], r[i]
	}
	return string(r)
}"""),
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{p} {self.GT[t]}" for p, t in params)
        return f"func {self.fname(name)}({args}) {self.GT[ret]}"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 1)
        reading = [h for h in self.helpers if h.startswith("read")]
        if reading and "readLine" not in reading:
            self.helpers.insert(0, "readLine")
        helpers = []
        for h in sorted(self.helpers, key=lambda h: h != "readLine"):
            libs, code = self.HELPERS[h]
            self.imp(*libs)
            helpers.append(code)
        imps = sorted({"fmt"} | set(self.imports))
        head = "package main\n\n" + (f'import "{imps[0]}"' if len(imps) == 1 else "import (\n" + "\n".join(f'\t"{i}"' for i in imps) + "\n)")
        return "\n\n".join([head] + helpers + funcs + ["\n".join(["func main() {"] + main + ["}"])])


# ====================================================================== Rust
class Rust(Braces):
    key, name, ext = "rust", "Rust", "rs"
    SQRT, PI = "{x}.sqrt()", "std::f64::consts::PI"
    paren_cond = False
    INC = None
    RT = {"int": "i64", "big": "i64", "float": "f64", "str": "String", "bool": "bool", "arr": "Vec<i64>"}

    def index(self, i, env):
        return f"{self.expr(i, env, 8)} as usize"

    def x_tofloat(self, e, env):
        return f"{self.expr(e[1], env, 8)} as f64", 8

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.len() as i64", 8

    def x_arr(self, e, env):
        return "vec![" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f'format!("{{:.2}}", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.chars().rev().collect::<String>()", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.to_lowercase()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.replace(" ", "")', ATOM

    def x_words(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.split_whitespace().count() as i64", 8

    def bin_special(self, o, a, b, env):
        # строка == строка: в Rust String сравнивается с &str и String одинаково
        return None

    def out(self, parts, env, newline):
        mac = "println!" if newline else "print!"
        fmt, args = "", []
        for kind, x in parts:
            if kind == "lit":
                fmt += x.replace("\\", "\\\\").replace('"', '\\"').replace("{", "{{").replace("}", "}}")
            else:
                fmt += "{:.2}" if kind == "fmt2" else "{}"
                args.append(self.expr(x, env))
        if not fmt and newline:
            return "println!()"
        return f'{mac}("{fmt}"' + "".join(", " + a for a in args) + ")"

    def declare_value(self, name, typ, value, env):
        mut = "mut " if name in env.mut else ""
        if typ in ("int", "big") and re.fullmatch(r"-?\d+", value):
            return f"let {mut}{name}: i64 = {value}"
        return f"let {mut}{name} = {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "read_int", "float": "read_float"}.get(typ, "read_line")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        self.use("random_range")
        return f"random_range({lo}, {hi})"

    def while_head(self, c, env):
        return "loop" if self.forever(c) else "while " + self.expr(c, env)

    def for_head(self, name, a, b, env, body):
        var = name if var_used(body, name) else "_"
        if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
            return f"for {var} in {self.expr(a, env, 6)}..={self.expr(b[2], env, 6)}"
        return f"for {var} in {self.expr(a, env, 6)}..{self.expr(b, env, 6)}"

    HELPERS = {
        "read_line": (("std::io::{self, Write}",), """fn read_line(prompt: &str) -> String {
    print!("{}", prompt);
    io::stdout().flush().unwrap();
    let mut line = String::new();
    io::stdin().read_line(&mut line).unwrap();
    line.trim_end().to_string()
}"""),
        "read_int": ((), """fn read_int(prompt: &str) -> i64 {
    read_line(prompt).trim().parse().expect("нужно целое число")
}"""),
        "read_float": ((), """fn read_float(prompt: &str) -> f64 {
    // 36,6 тоже подходит
    read_line(prompt).trim().replace(',', ".").parse().expect("нужно число")
}"""),
        "random_range": (("std::collections::hash_map::RandomState", "std::hash::{BuildHasher, Hasher}"),
                         """// Случайное число от lo до hi без внешних библиотек: RandomState каждый раз берёт новый случайный ключ
fn random_range(lo: i64, hi: i64) -> i64 {
    let r = RandomState::new().build_hasher().finish();
    lo + (r % (hi - lo + 1) as u64) as i64
}"""),
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{p}: {self.RT[t]}" for p, t in params)
        return f"fn {name}({args}) -> {self.RT[ret]}"

    def s_return(self, s, env, d):
        return [self.L(d, f"return {self.expr(s[1], env)};")]

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 1)
        reading = [h for h in self.helpers if h.startswith("read")]
        if reading and "read_line" not in reading:
            self.helpers.insert(0, "read_line")
        helpers = []
        for h in sorted(self.helpers, key=lambda h: h != "read_line"):
            libs, code = self.HELPERS[h]
            self.imp(*libs)
            helpers.append(code)
        uses_ = "\n".join(f"use {u};" for u in sorted(self.imports))
        return "\n\n".join(([uses_] if uses_ else []) + helpers + funcs + ["\n".join(["fn main() {"] + main + ["}"])])


# ====================================================================== Kotlin
class Kotlin(Braces):
    key, name, ext, file = "kotlin", "Kotlin", "kt", "Main.kt"
    SQRT, PI, MATH = "sqrt({x})", "PI", ("kotlin.math.PI", "kotlin.math.sqrt")
    fn_style = "camel"
    semi = ""
    ELEMENTS = False
    KT = {"int": "Int", "big": "Long", "float": "Double", "str": "String", "bool": "Boolean", "arr": "IntArray"}

    def x_tofloat(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toDouble()", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.size", ATOM

    def x_arr(self, e, env):
        return "intArrayOf(" + ", ".join(self.expr(x, env) for x in e[1]) + ")", ATOM

    def x_fmt2(self, e, env):
        return f'"%.2f".format({self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.reversed()", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.lowercase()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.replace(" ", "")', ATOM

    def x_words(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.split(Regex("\\\\s+")).count {{ it.isNotEmpty() }}', ATOM

    def template(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "expr" and self.typ(parts[0][1], env) == "str":
            return self.expr(parts[0][1], env)
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        body = ""
        for i, (kind, x) in enumerate(parts):
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
            elif kind == "expr" and x[0] == "var":
                nxt = parts[i + 1][1][:1] if i + 1 < len(parts) and parts[i + 1][0] == "lit" else ""
                body += "${" + x[1] + "}" if re.match(r"\w", nxt) else "$" + x[1]
            else:
                body += "${" + self.expr(("fmt2", x) if kind == "fmt2" else x, env) + "}"
        return '"' + body + '"'

    def out(self, parts, env, newline):
        fn = "println" if newline else "print"
        return f"{fn}({self.template(parts, env) if parts else ''})"

    def declare_value(self, name, typ, value, env):
        kw = "var" if name in env.mut else "val"
        if typ == "big" and re.fullmatch(r"-?\d+", value):
            value += "L"
        return f"{kw} {name} = {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "readInt", "float": "readDouble"}.get(typ, "readText")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        return f"({lo}..{hi}).random()"

    def for_head(self, name, a, b, env, body):
        if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
            return f"for ({name} in {self.expr(a, env)}..{self.expr(b[2], env, 6)})"
        return f"for ({name} in {self.expr(a, env)} until {self.expr(b, env, 6)})"

    HELPERS = {
        "readText": """fun readText(prompt: String): String {
    print(prompt)
    return readLine() ?: ""
}""",
        "readInt": """fun readInt(prompt: String): Int = readText(prompt).trim().toInt()""",
        "readDouble": """fun readDouble(prompt: String): Double = readText(prompt).trim().replace(',', '.').toDouble()   // 36,6 тоже подходит""",
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{p}: {self.KT[t]}" for p, t in params)
        return f"fun {self.fname(name)}({args}): {self.KT[ret]}"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 1)
        if any(h.startswith("read") for h in self.helpers) and "readText" not in self.helpers:
            self.helpers.insert(0, "readText")
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "readText")]
        imports = ["\n".join(f"import {i}" for i in sorted(self.imports))] if self.imports else []
        return "\n\n".join(imports + helpers + funcs + ["\n".join(["fun main() {"] + main + ["}"])])



# ====================================================================== PHP
class PHP(Braces):
    key, name, ext = "php", "PHP", "php"
    PI = "M_PI"
    fn_style = "camel"
    INC = "{x}++"

    def v(self, name):
        return "$" + name

    def str_lit(self, s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"intdiv({self.expr(a, env)}, {self.expr(b, env)})", ATOM
        if o in ("==", "!=") and self.typ(a, env) == "str":
            return f"{self.expr(a, env, 4)} {o}= {self.expr(b, env, 4)}", 3
        return None

    def x_tofloat(self, e, env):
        return f"(float) {self.expr(e[1], env, 8)}", 7

    def x_len(self, e, env):
        return f"count({self.expr(e[1], env)})", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f"sprintf('%.2f', {self.expr(e[1], env)})", ATOM

    def x_rev(self, e, env):
        return f"implode('', array_reverse(mb_str_split({self.expr(e[1], env)})))", ATOM

    def x_lower(self, e, env):
        return f"mb_strtolower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        return f"str_replace(' ', '', {self.expr(e[1], env)})", ATOM

    def x_words(self, e, env):
        return f"count(preg_split('/\\s+/u', trim({self.expr(e[1], env)}), -1, PREG_SPLIT_NO_EMPTY))", ATOM

    def out(self, parts, env, newline):
        items = []
        for kind, x in parts:
            items.append(self.str_lit(x) if kind == "lit" else self.expr(("fmt2", x) if kind == "fmt2" else x, env))
        if newline:
            if items and items[-1].startswith('"'):
                items[-1] = items[-1][:-1] + '\\n"'
            else:
                items.append('"\\n"')
        return "echo " + ", ".join(items)

    def declare_value(self, name, typ, value, env):
        return f"${name} = {value}"

    def read(self, typ, prompt, env):
        self.use("ask")
        p = self.str_lit(prompt)
        return {"int": f"(int) ask({p})", "float": f"(float) str_replace(',', '.', ask({p}))"}.get(typ, f"ask({p})")

    def random(self, lo, hi):
        return f"random_int({lo}, {hi})"

    def s_if(self, s, env, d):
        return [l.replace("} else if (", "} elseif (") for l in Braces.s_if(self, s, env, d)]

    def for_head(self, name, a, b, env, body):
        x = self.v(name)
        return f"for ({x} = {self.expr(a, env)}; {self.upto(x, b, env)}; {x}++)"

    HELPERS = {"ask": """function ask(string $prompt): string
{
    echo $prompt;
    return trim((string) fgets(STDIN));
}"""}
    PT = {"int": "int", "big": "int", "float": "float", "str": "string", "bool": "bool", "arr": "array"}

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.PT[t]} ${p}" for p, t in params)
        return f"function {self.fname(name)}({args}): {self.PT[ret]}"

    def program(self):
        funcs = ["\n".join([self.func_head(f[1], f[2], f[3]), "{"] + self.body_of(f) + ["}"]) for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 0)
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "<?php\n\n" + "\n\n".join(helpers + funcs + ["\n".join(main)])


# ====================================================================== Ruby
class Ruby(Emitter):
    key, name, ext = "ruby", "Ruby", "rb"
    SQRT, PI = "Math.sqrt({x})", "Math::PI"
    ind = "  "
    INC = None
    OPS = dict(C_OPS, **{"//": "/"})

    def fname(self, name):
        return name[3:] + "?" if name.startswith("is_") else name

    def str_lit(self, s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("#{", "\\#{") + '"'

    def x_tofloat(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.to_f", ATOM

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(e[2], env)}]", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.size", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f"format('%.2f', {self.expr(e[1], env)})", ATOM

    def x_rev(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.reverse", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.downcase", ATOM

    def x_nospace(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.delete(' ')", ATOM

    def x_words(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.split.size", ATOM

    def template(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        body = ""
        for kind, x in parts:
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace('"', '\\"').replace("#{", "\\#{")
            else:
                body += "#{" + self.expr(("fmt2", x) if kind == "fmt2" else x, env) + "}"
        return '"' + body + '"'

    def s_print(self, s, env, d):
        parts = _print_parts(s[1])
        return [self.L(d, "puts " + self.template(parts, env) if parts else "puts")]

    def s_write(self, s, env, d):
        return [self.L(d, "print " + self.template(_print_parts(s[1]), env))]

    def s_let(self, s, env, d):
        env.types[s[1]] = s[2]
        return [self.L(d, f"{s[1]} = {self.expr(s[3], env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], s[3]
        env.types[name] = typ
        value = {"int": "gets.to_i", "float": "gets.to_s.tr(',', '.').to_f"}.get(typ, "gets.to_s.chomp")
        return [self.L(d, "print " + self.str_lit(prompt)), self.L(d, f"{name} = {value}")]

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        return [self.L(d, f"{s[1]} = rand({s[2]}..{s[3]})")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "elsif ") + self.expr(c, env)))
            out += self.block(body, env, d + 1)
        if other:
            out.append(self.L(d, "else"))
            out += self.block(other, env, d + 1)
        return out + [self.L(d, "end")]

    def s_while(self, s, env, d):
        head = "loop do" if self.forever(s[1]) else "while " + self.expr(s[1], env)
        return [self.L(d, head)] + self.block(s[2], env, d + 1) + [self.L(d, "end")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        if not var_used(body, name) and a == ("num", 0):
            head = f"{self.expr(b, env, ATOM)}.times do"
        else:
            last = add_const(b, -1)
            head = f"({self.expr(a, env)}..{self.expr(last, env, 6)}).each do |{name}|"
        return [self.L(d, head)] + self.block(body, env, d + 1) + [self.L(d, "end")]

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        return [self.L(d, "return " + self.expr(s[1], env))]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(s[2], env)}] = {self.expr(s[3], env)}")]

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            lines = self.block(body, Env({p: t for p, t in params}), 1)
            if lines and lines[-1].startswith(self.ind + "return "):
                lines[-1] = self.ind + lines[-1][len(self.ind) + 7:]     # последнее значение — и есть результат
            funcs.append("\n".join([f"def {self.fname(name)}({', '.join(p for p, _ in params)})"] + lines + ["end"]))
        main = self.block(self.prog["main"], Env({}), 0)
        return "\n\n".join(funcs + ["\n".join(main)])


# ====================================================================== Lua
class Lua(Emitter):
    key, name, ext = "lua", "Lua", "lua"
    SQRT, PI = "math.sqrt({x})", "math.pi"
    ind = "  "
    INC = ADD = None
    T, F = "true", "false"
    NOT, NOT_PREC = "not ", 7
    OPS = dict(C_OPS, **{"!=": "~=", "and": "and", "or": "or"})

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"math.floor({self.expr(a, env, 6)} / {self.expr(b, env, 7)})", ATOM
        return None

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(add_const(e[2], 1), env)}]", ATOM

    def x_len(self, e, env):
        return f"#{self.expr(e[1], env, ATOM)}", 7

    def x_arr(self, e, env):
        return "{" + ", ".join(self.expr(x, env) for x in e[1]) + "}", ATOM

    def x_fmt2(self, e, env):
        return f'string.format("%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        self.use("reverse")
        return f"reverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        self.use("lower")
        return f"lower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        return f'({self.expr(e[1], env, ATOM)}:gsub(" ", ""))', ATOM

    def x_words(self, e, env):
        self.use("count_words")
        return f"count_words({self.expr(e[1], env)})", ATOM

    def concat(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        items = []
        for kind, x in parts:
            items.append(self.str_lit(x) if kind == "lit" else self.expr(("fmt2", x) if kind == "fmt2" else x, env, 6))
        return " .. ".join(items)

    def s_print(self, s, env, d):
        parts = _print_parts(s[1])
        return [self.L(d, f"print({self.concat(parts, env) if parts else ''})")]

    def s_write(self, s, env, d):
        items = [self.str_lit(x) if k == "lit" else self.expr(("fmt2", x) if k == "fmt2" else x, env) for k, x in _print_parts(s[1])]
        return [self.L(d, f"io.write({', '.join(items)})")]

    def s_let(self, s, env, d):
        env.types[s[1]] = s[2]
        return [self.L(d, f"local {s[1]} = {self.expr(s[3], env)}")]

    def s_set(self, s, env, d):
        return [self.L(d, f"{s[1]} = {self.expr(s[2], env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], s[3]
        local = "" if name in env.declared else "local "
        env.declared.add(name)
        env.types[name] = typ
        value = {"int": "tonumber(io.read())", "float": 'tonumber((io.read():gsub(",", ".")))'}.get(typ, "io.read()")
        return [self.L(d, f"io.write({self.str_lit(prompt)})"), self.L(d, f"{local}{name} = {value}")]

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        return [self.L(d, "math.randomseed(os.time())"), self.L(d, f"local {s[1]} = math.random({s[2]}, {s[3]})")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "elseif ") + self.expr(c, env) + " then"))
            out += self.block(body, env.inner(), d + 1)
        if other:
            out.append(self.L(d, "else"))
            out += self.block(other, env.inner(), d + 1)
        return out + [self.L(d, "end")]

    def s_while(self, s, env, d):
        c = "true" if self.forever(s[1]) else self.expr(s[1], env)
        return [self.L(d, f"while {c} do")] + self.block(s[2], env.inner(), d + 1) + [self.L(d, "end")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        var = name if var_used(body, name) else "_"
        inner = env.inner()
        inner.declared.add(name)
        return ([self.L(d, f"for {var} = {self.expr(a, env)}, {self.expr(add_const(b, -1), env)} do")] +
                self.block(body, inner, d + 1) + [self.L(d, "end")])

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        return [self.L(d, "return " + self.expr(s[1], env))]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(add_const(s[2], 1), env)}] = {self.expr(s[3], env)}")]

    HELPERS = {
        "reverse": """-- Строка наоборот по символам UTF-8 (string.reverse переворачивает байты и ломает русские буквы)
local function reverse(s)
  local chars = {}
  for _, code in utf8.codes(s) do
    table.insert(chars, 1, utf8.char(code))
  end
  return table.concat(chars)
end""",
        "lower": """-- Строчные буквы, включая русские (string.lower понимает только латиницу)
local function lower(s)
  local out = {}
  for _, c in utf8.codes(s) do
    if (c >= 65 and c <= 90) or (c >= 0x410 and c <= 0x42F) then
      c = c + 32
    elseif c == 0x401 then
      c = 0x451
    end
    out[#out + 1] = utf8.char(c)
  end
  return table.concat(out)
end""",
        "count_words": """local function count_words(s)
  local count = 0
  for _ in s:gmatch("%S+") do
    count = count + 1
  end
  return count
end""",
    }

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params}, declared=[p for p, _ in params])
            funcs.append("\n".join([f"local function {name}({', '.join(p for p, _ in params)})"] + self.block(body, env, 1) + ["end"]))
        main = self.block(self.prog["main"], Env({}), 0)
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(helpers + funcs + ["\n".join(main)])


# ====================================================================== Perl
class Perl(Braces):
    key, name, ext = "perl", "Perl", "pl"

    def v(self, name):
        return "$" + name

    def str_lit(self, s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("@", "\\@") + '"'

    T, F = "1", "0"
    PERL_OPS = {"==": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"int({self.expr(a, env, 6)} / {self.expr(b, env, 7)})", ATOM
        if o in self.PERL_OPS and self.typ(a, env) == "str":
            return f"{self.expr(a, env, 4)} {self.PERL_OPS[o]} {self.expr(b, env, 4)}", 3
        return None

    def x_idx(self, e, env):
        return f"${e[1][1]}[{self.expr(e[2], env)}]", ATOM

    def x_len(self, e, env):
        return f"scalar(@{e[1][1]})", ATOM

    def x_arr(self, e, env):
        return "(" + ", ".join(self.expr(x, env) for x in e[1]) + ")", ATOM

    def x_fmt2(self, e, env):
        return f'sprintf("%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"scalar reverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        return f"lc({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        return f"{self.expr(e[1], env, ATOM)} =~ s/ //gr", 4

    def x_words(self, e, env):
        return f"scalar(() = {self.expr(e[1], env, ATOM)} =~ /\\S+/g)", ATOM

    def call(self, e, env):
        return f"{e[1]}({', '.join(self.expr(a, env) for a in e[2])})"

    def out(self, parts, env, newline):
        items = [self.str_lit(x) if k == "lit" else self.expr(("fmt2", x) if k == "fmt2" else x, env) for k, x in parts]
        if newline:
            return "say " + ", ".join(items) if items else 'say ""'
        return "print " + ", ".join(items)

    def s_let(self, s, env, d):
        name, typ, e = s[1], s[2], s[3]
        env.types[name] = typ
        env.declared.add(name)
        if typ == "arr":
            return [self.L(d, f"my @{name} = {self.expr(e, env)};")]
        return [self.L(d, f"my ${name} = {self.expr(e, env)};")]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"${s[1][1]}[{self.expr(s[2], env)}] = {self.expr(s[3], env)};")]

    def declare_value(self, name, typ, value, env):
        return f"my ${name} = {value}"

    def read(self, typ, prompt, env):
        self.use("ask")
        p = self.str_lit(prompt)
        return {"int": f"int(ask({p}))", "float": f"ask({p}) =~ tr/,/./r"}.get(typ, f"ask({p})")

    def random(self, lo, hi):
        return f"int(rand({hi - lo + 1})) + {lo}"

    def s_break(self, s, env, d):
        return [self.L(d, "last;")]

    def s_if(self, s, env, d):
        out = Braces.s_if(self, s, env, d)
        return [l.replace("} else if (", "} elsif (") for l in out]

    def while_head(self, c, env):
        return "while (1)" if self.forever(c) else "while " + self.cond(c, env)

    def for_head(self, name, a, b, env, body):
        return f"for my ${name} ({self.expr(a, env)} .. {self.expr(add_const(b, -1), env, 6)})"

    HELPERS = {"ask": """sub ask {
    my ($prompt) = @_;
    print $prompt;
    my $line = <STDIN> // '';
    chomp $line;
    return $line;
}"""}

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            params = ", ".join("$" + p for p, _ in f[2])
            funcs.append("\n".join([f"sub {f[1]} {{", f"    my ({params}) = @_;"] + self.body_of(f) + ["}"]))
        main = self.block(self.prog["main"], self.main_env(), 0)
        head = "use strict;\nuse warnings;\nuse utf8;\nuse feature 'say';\nuse open qw(:std :encoding(UTF-8));\n\n$| = 1;   # подсказки ввода видны сразу"
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join([head] + helpers + funcs + ["\n".join(main)])



# ====================================================================== Bash
class Bash(Emitter):
    key, name, ext = "bash", "Bash", "sh"

    def dq(self, s):
        """Текст внутри двойных кавычек."""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")

    # ---- целые и логические выражения внутри (( )) и $(( ))
    def ar(self, e, env, prec=0):
        text, p = self.ar_(e, env)
        return f"({text})" if p < prec else text

    def ar_(self, e, env):
        k = e[0]
        if k == "num":
            return str(e[1]), (ATOM if e[1] >= 0 else 7)
        if k == "bool":
            return ("1" if e[1] else "0"), ATOM
        if k == "var":
            return e[1], ATOM
        if k == "idx":
            return f"{e[1][1]}[{self.ar(e[2], env)}]", ATOM
        if k == "len":
            return "${#" + e[1][1] + "[@]}", ATOM
        if k in ("call", "words"):
            return self.word(e, env), ATOM
        if k == "not":
            return "!" + self.ar(e[1], env, 8), 7
        if k == "neg":
            return "-" + self.ar(e[1], env, 8), 7
        if k == "tofloat":
            return self.ar_(e[1], env)
        o, a, b = e[1], e[2], e[3]
        p = C_PREC[o]
        need_a = p if o not in CMP else p + 1
        if a[0] == "bin" and ((o == "or" and a[1] == "and") or (o in CMP and a[1] in CMP)):
            need_a = 99
        need_b = p + 1
        if b[0] == "bin" and ((o == "or" and b[1] == "and") or (o in CMP and b[1] in CMP)):
            need_b = 99
        return f"{self.ar(a, env, need_a)} {C_OPS[o]} {self.ar(b, env, need_b)}", p

    # ---- значение как слово командной строки (внутри "...")
    def word(self, e, env, nxt=""):
        k = e[0]
        t = etype(e, env.types, self.funcs)
        if k == "str":
            return self.dq(e[1])
        if k == "var":
            if t == "arr":
                return "${" + e[1] + "[*]}"
            return "${" + e[1] + "}" if re.match(r"[\w\[]", nxt) else "$" + e[1]
        if k == "idx":
            return "${" + e[1][1] + "[" + self.ar(e[2], env) + "]}"
        if k == "len":
            return "${#" + e[1][1] + "[@]}"
        if k == "call":
            args = " ".join(f'"{self.word(a, env)}"' for a in e[2])
            return f"$({self.fname(e[1])} {args})"
        if k == "rev":
            self.use("reverse")
            return f'$(reverse "{self.word(e[1], env)}")'
        if k == "lower" and e[1][0] == "var":
            return "${" + e[1][1] + ",,}"
        if k == "nospace" and e[1][0] == "var":
            return "${" + e[1][1] + "// /}"
        if k == "words":
            self.use("count_words")
            return f'$(count_words "{self.word(e[1], env)}")'
        if k == "fmt2":
            return '$(awk "BEGIN { printf \\"%.2f\\", ' + self.fx(e[1], env) + ' }")'
        if t == "float":
            return '$(awk "BEGIN { print ' + self.fx(e, env) + ' }")'
        if k in ("lower", "nospace"):
            raise ValueError("Bash: lower/nospace — только от переменной")
        return "$((" + self.ar(e, env) + "))"

    # ---- дробные выражения: считает awk
    def fx(self, e, env, prec=0):
        k = e[0]
        if k in ("num", "flt"):
            x = e[1]
            return str(int(x)) if float(x).is_integer() else repr(float(x))
        if k in ("var", "idx", "len", "call"):
            return self.word(e, env)
        if k == "tofloat":
            return self.fx(e[1], env, prec)
        if k == "sqrt":
            return f"sqrt({self.fx(e[1], env)})"
        if k == "pi":
            return "atan2(0, -1)"
        if k == "neg":
            return f"-({self.fx(e[1], env)})"           # -($b): при b = -3 получится -(-3), а не --3
        o, a, b = e[1], e[2], e[3]
        p = C_PREC[o]
        ops = dict(C_OPS, **{"//": "/"})
        text = f"{self.fx(a, env, p)} {ops[o]} {self.fx(b, env, p + 1)}"
        if o == "//":
            text = f"int({text})"
        return f"({text})" if p < prec else text

    # ---- условие для if / while
    def cond(self, e, env):
        k = e[0]
        if k == "call" and self.funcs[e[1]][3] == "bool":
            return f"{self.fname(e[1])} " + " ".join(f'"{self.word(a, env)}"' for a in e[2])
        if k == "not" and not self.arith_ok(e[1], env):
            return "! " + self.cond(e[1], env)
        if k == "bin" and e[1] in ("and", "or") and not (self.arith_ok(e[2], env) and self.arith_ok(e[3], env)):
            return f"{self.cond(e[2], env)} {C_OPS[e[1]]} {self.cond(e[3], env)}"
        if k == "bin" and e[1] in CMP:
            ta = etype(e[2], env.types, self.funcs)
            if ta == "str":
                op_ = "==" if e[1] == "==" else "!="
                return f'[[ {self.word(e[2], env)} {op_} "{self.word(e[3], env)}" ]]'
            if "float" in (ta, etype(e[3], env.types, self.funcs)):
                return 'awk "BEGIN { exit !(' + self.fx(e, env) + ') }"'
        return "(( " + self.ar(e, env) + " ))"

    def arith_ok(self, e, env):
        return not any(n[0] in ("str", "flt", "sqrt", "pi") or (n[0] == "var" and env.types.get(n[1]) in ("str", "float")) or
                       (n[0] == "call" and self.funcs[n[1]][3] == "bool") for n in walk([e]))

    # ---- операторы
    def assign_line(self, name, e, env, local=False):
        t = etype(e, env.types, self.funcs)
        pre = "local " if local else ""
        if e[0] == "arr":
            return f"{pre}{name}=(" + " ".join(self.ar(x, env) for x in e[1]) + ")"
        if e[0] == "num" or (e[0] == "var" and t != "arr"):
            value = str(e[1]) if e[0] == "num" else "$" + e[1]
        elif t in ("str", "float") or e[0] in ("call", "idx", "len"):
            value = self.word(e, env)
            if e[0] == "str":
                value = f'"{value}"'
        else:
            value = "$((" + self.ar(e, env) + "))"
        return f"{pre}{name}={value}"

    def s_let(self, s, env, d):
        name, typ, e = s[1], s[2], s[3]
        env.types[name] = typ
        local = env.fn is not None
        if typ == "str" and e[0] in ("lower", "nospace") and e[1][0] != "var":
            # t=${s// /} и затем t=${t,,}: в bash подстановки не вкладываются друг в друга
            steps, x = [], e
            while x[0] in ("lower", "nospace"):
                steps.append(x[0])
                x = x[1]
            out = [self.L(d, self.assign_line(name, x, env, local))]
            for st in reversed(steps):
                out.append(self.L(d, f"{name}=${{{name},,}}" if st == "lower" else f"{name}=${{{name}// /}}"))
            return out
        return [self.L(d, self.assign_line(name, e, env, local))]

    def s_set(self, s, env, d):
        name, e = s[1], s[2]
        t = etype(e, env.types, self.funcs)
        if t in ("int", "big", "bool") and e[0] == "bin" and e[2] == ("var", name) and e[1] in ("+", "-", "*"):
            if e[1] == "+" and e[3] == ("num", 1):
                return [self.L(d, f"(( {name}++ ))")]
            return [self.L(d, f"(( {name} {e[1]}= {self.ar(e[3], env)} ))")]
        return [self.L(d, self.assign_line(name, e, env))]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], s[3]
        env.types[name] = typ
        out = [self.L(d, f'read -rp "{self.dq(prompt)}" {name}')]
        if typ == "float":
            out.append(self.L(d, f"{name}=${{{name}/,/.}}   # 36,6 тоже подходит"))
        return out

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        return [self.L(d, f"{s[1]}=$(( RANDOM % {s[3] - s[2] + 1} + {s[2]} ))")]

    def text(self, parts, env):
        out = ""
        for i, (kind, x) in enumerate(parts):
            if kind == "lit":
                out += self.dq(x)
            else:
                nxt = parts[i + 1][1][:1] if i + 1 < len(parts) and parts[i + 1][0] == "lit" else ""
                out += self.word(("fmt2", x) if kind == "fmt2" else x, env, nxt)
        return out

    def s_print(self, s, env, d):
        parts = _print_parts(s[1])
        return [self.L(d, f'echo "{self.text(parts, env)}"' if parts else "echo")]

    def s_write(self, s, env, d):
        return [self.L(d, f'echo -n "{self.text(_print_parts(s[1]), env)}"')]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "elif ") + self.cond(c, env) + "; then"))
            out += self.block(body, env, d + 1) or [self.L(d + 1, ":")]
        if other:
            out.append(self.L(d, "else"))
            out += self.block(other, env, d + 1)
        return out + [self.L(d, "fi")]

    def s_while(self, s, env, d):
        c = "true" if self.forever(s[1]) else self.cond(s[1], env)
        return [self.L(d, f"while {c}; do")] + self.block(s[2], env, d + 1) + [self.L(d, "done")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
            test = f"{name} <= {self.ar(b[2], env, 5)}"
        else:
            test = f"{name} < {self.ar(b, env, 5)}"
        return ([self.L(d, f"for (({name} = {self.ar(a, env)}; {test}; {name}++)); do")] + self.block(body, env, d + 1) +
                [self.L(d, "done")])

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        if env.ret == "bool":
            return [self.L(d, "return " + ("0" if s[1] == ("bool", True) else "1" if s[1] == ("bool", False)
                                          else f"$(( !({self.ar(s[1], env)}) ))"))]
        value = self.word(s[1], env) if s[1][0] != "var" else "$" + s[1][1]
        return [self.L(d, f'echo "{value}"'), self.L(d, "return")]

    def s_setidx(self, s, env, d):
        idx = self.ar(s[2], env).replace(" ", "")
        e = s[3]
        value = "$" + e[1] if e[0] == "var" else self.word(e, env) if e[0] == "idx" else "$((" + self.ar(e, env) + "))"
        return [self.L(d, f"{s[1][1]}[{idx}]={value}")]

    HELPERS = {
        "reverse": """# Строка наоборот (по буквам — русские тоже)
reverse() {
    local s=$1 out="" i
    for ((i = ${#s} - 1; i >= 0; i--)); do
        out+=${s:i:1}
    done
    echo "$out"
}""",
        "count_words": """count_words() {
    local -a words
    read -ra words <<< "$1"
    echo "${#words[@]}"
}""",
    }

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params}, ret=ret, fn=name)
            args = " ".join(f"{p}=${i + 1}" for i, (p, _) in enumerate(params))
            loops = sorted({n[1] for n in walk(body) if n[0] == "for"})
            if loops:
                args += " " + " ".join(loops)          # счётчики циклов — тоже свои, а не общие
            lines = self.block(body, env, 1)
            if len(lines) >= 2 and lines[-1].strip() == "return" and lines[-2].strip().startswith("echo "):
                lines.pop()
            funcs.append("\n".join([f"{self.fname(name)}() {{", self.L(1, f"local {args}")] + lines + ["}"]))
        main = self.block(self.prog["main"], Env({}), 0)
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(["#!/usr/bin/env bash"] + helpers + funcs + ["\n".join(main)])


# ====================================================================== Pascal (Free Pascal, Lazarus, Delphi)
class Pascal(Emitter):
    key, name, ext = "pascal", "Pascal", "pas"
    SQRT, PI = "Sqrt({x})", "Pi"
    fn_style = "pascal"
    ind = "  "
    T, F = "True", "False"
    NOT, NOT_PREC = "not ", 7
    OPS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">=", "+": "+", "-": "-", "*": "*", "/": "/",
           "//": "div", "%": "mod", "and": "and", "or": "or"}
    PREC = {"or": 5, "and": 6, "==": 3, "!=": 3, "<": 3, "<=": 3, ">": 3, ">=": 3, "+": 5, "-": 5, "*": 6, "/": 6,
            "//": 6, "%": 6}
    PT = {"int": "Integer", "big": "Int64", "float": "Double", "str": "string", "bool": "Boolean"}

    def str_lit(self, s):
        return "'" + s.replace("'", "''") + "'"

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(e[2], env)}]", ATOM

    def x_len(self, e, env):
        return f"Length({self.expr(e[1], env)})", ATOM

    def x_fmt2(self, e, env):
        self.imp("SysUtils")
        return f"FormatFloat('0.00', {self.expr(e[1], env)})", ATOM

    def x_rev(self, e, env):
        self.use("ReverseUtf8")
        return f"ReverseUtf8({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        self.use("LowerUtf8")
        return f"LowerUtf8({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        self.imp("SysUtils")
        return f"StringReplace({self.expr(e[1], env)}, ' ', '', [rfReplaceAll])", ATOM

    def x_words(self, e, env):
        self.use("CountWords")
        return f"CountWords({self.expr(e[1], env)})", ATOM

    def side(self, x, env, o, p, right):
        if o in ("and", "or") and x[0] == "bin" and x[1] in CMP:
            return "(" + self.expr(x, env) + ")"
        return Emitter.side(self, x, env, o, p, right)

    # Операторы возвращают строки без «;» в конце — точки с запятой ставит block (перед else их быть не может)
    def block(self, stmts, env, d):
        out = []
        for s in stmts:
            lines = getattr(self, "s_" + s[0])(s, env, d)
            if lines:
                lines[-1] += ";"
                out += lines
        return out

    def branch(self, body, env, d):
        """Тело if / while / for: один простой оператор — без begin/end, иначе begin … end."""
        if len(body) == 1 and body[0][0] not in ("if", "while", "for"):
            return getattr(self, "s_" + body[0][0])(body[0], env, d + 1)
        return [self.L(d, "begin")] + self.block(body, env, d + 1) + [self.L(d, "end")]

    def s_print(self, s, env, d, fn="WriteLn"):
        items = []
        for kind, x in _print_parts(s[1]):
            if kind == "lit":
                items.append(self.str_lit(x))
            elif kind == "fmt2":
                items.append(self.expr(x, env, 1) + ":0:2")
            else:
                items.append(self.expr(x, env))
        return [self.L(d, f"{fn}({', '.join(items)})" if items else self.L(0, fn))]

    def s_write(self, s, env, d):
        return self.s_print(s, env, d, "Write")

    def s_let(self, s, env, d):
        if s[2] == "arr":
            return []                        # массив объявлен вместе со значениями в разделе var
        return [self.L(d, f"{s[1]} := {self.expr(s[3], env)}")]

    def assign(self, name, value):
        return f"{name} := {value}"

    def s_set(self, s, env, d):
        name, e = s[1], s[2]
        if e[0] == "bin" and e[1] == "+" and e[2] == ("var", name) and e[3] == ("num", 1):
            return [self.L(d, f"Inc({name})")]
        return [self.L(d, f"{name} := {self.expr(e, env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], s[3]
        if typ == "float":
            self.use("ReadReal")
            return [self.L(d, f"{name} := ReadReal({self.str_lit(prompt)})")]
        out = [self.L(d, f"Write({self.str_lit(prompt)});"), self.L(d, f"ReadLn({name})")]
        return out

    def s_rand(self, s, env, d):
        return [self.L(d, "Randomize;"), self.L(d, f"{s[1]} := Random({s[3] - s[2] + 1}) + {s[2]}")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "else if ") + self.expr(c, env) + " then"))
            out += self.branch(body, env, d)
        if other:
            out.append(self.L(d, "else"))
            out += self.branch(other, env, d)
        return out

    def s_while(self, s, env, d):
        c = "True" if self.forever(s[1]) else self.expr(s[1], env)
        return [self.L(d, f"while {c} do")] + self.branch(s[2], env, d)

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        return [self.L(d, f"for {name} := {self.expr(a, env)} to {self.expr(add_const(b, -1), env)} do")] + self.branch(body, env, d)

    def s_break(self, s, env, d):
        return [self.L(d, "Break")]

    def s_return(self, s, env, d):
        if getattr(env, "last", None) is s:
            return [self.L(d, f"Result := {self.expr(s[1], env)}")]
        return [self.L(d, f"Exit({self.expr(s[1], env)})")]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(s[2], env)}] := {self.expr(s[3], env)}")]

    def var_section(self, types, arrays, skip=()):
        groups = {}
        for name, t in types.items():
            if name in skip or t == "arr":
                continue
            groups.setdefault(self.PT[t], []).append(name)
        lines = [f"  {', '.join(names)}: {t};" for t, names in groups.items()]
        for name, items in arrays:
            lines.append(f"  {name}: array[0..{len(items) - 1}] of Integer = ({', '.join(str(x[1]) for x in items)});")
        return ["var"] + lines if lines else []

    HELPERS = {
        "ReadReal": """function ReadReal(const prompt: string): Double;
var
  line: string;
  code: Integer;
begin
  Write(prompt);
  ReadLn(line);
  Val(StringReplace(Trim(line), ',', '.', []), Result, code);   { 36,6 тоже подходит }
end;""",
        "ReverseUtf8": """{ Строка наоборот по символам UTF-8 — русские буквы не ломаются }
function ReverseUtf8(const s: string): string;
var
  i, len: Integer;
begin
  Result := '';
  i := 1;
  while i <= Length(s) do
  begin
    if Ord(s[i]) >= $F0 then len := 4
    else if Ord(s[i]) >= $E0 then len := 3
    else if Ord(s[i]) >= $C0 then len := 2
    else len := 1;
    Result := Copy(s, i, len) + Result;
    i := i + len;
  end;
end;""",
        "LowerUtf8": """{ Строчные буквы: латиница и кириллица в UTF-8 }
function LowerUtf8(const s: string): string;
var
  i: Integer;
  c, next: Byte;
begin
  Result := '';
  i := 1;
  while i <= Length(s) do
  begin
    c := Ord(s[i]);
    if i < Length(s) then next := Ord(s[i + 1]) else next := 0;
    if (c >= Ord('A')) and (c <= Ord('Z')) then
      Result := Result + Chr(c + 32)
    else if (c = $D0) and (next >= $90) and (next <= $9F) then       { А–П }
    begin
      Result := Result + Chr($D0) + Chr(next + $20);
      Inc(i);
    end
    else if (c = $D0) and (next >= $A0) and (next <= $AF) then       { Р–Я }
    begin
      Result := Result + Chr($D1) + Chr(next - $20);
      Inc(i);
    end
    else if (c = $D0) and (next = $81) then                          { Ё }
    begin
      Result := Result + Chr($D1) + Chr($91);
      Inc(i);
    end
    else
      Result := Result + s[i];
    Inc(i);
  end;
end;""",
        "CountWords": """function CountWords(const s: string): Integer;
var
  i: Integer;
  inWord: Boolean;
begin
  Result := 0;
  inWord := False;
  for i := 1 to Length(s) do
    if s[i] in [' ', #9] then
      inWord := False
    else if not inWord then
    begin
      inWord := True;
      Inc(Result);
    end;
end;""",
    }

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params}, ret=ret, fn=name)
            env.last = body[-1] if body and body[-1][0] == "return" else None
            lines = self.block(body, env, 1)
            types = collect_types(body, {})
            args = "; ".join(f"{p}: {self.PT[t]}" for p, t in params)
            funcs.append("\n".join([f"function {self.fname(name)}({args}): {self.PT[ret]};"] +
                                   self.var_section(types, [], skip=[p for p, _ in params]) + ["begin"] + lines + ["end;"]))
        main = self.block(self.prog["main"], Env({}), 1)
        types = collect_types(self.prog["main"], {})
        arrays = [(s[1], s[3][1]) for s in self.prog["main"] if s[0] == "let" and s[2] == "arr"]
        if "ReadReal" in self.helpers:
            self.imp("SysUtils")
        head = "program Main;\n\n{$mode objfpc}{$H+}"
        if self.imports:
            head += "\n\nuses\n  " + ", ".join(self.imports) + ";"
        helpers = [self.HELPERS[h] for h in self.helpers]
        body = "\n".join(self.var_section(types, arrays) + ["begin"] + main + ["end."])
        return "\n\n".join([head] + helpers + funcs + [body])



# ====================================================================== Scala
class Scala(Braces):
    key, name, ext, file = "scala", "Scala", "scala", "Main.scala"
    SQRT, PI = "math.sqrt({x})", "math.Pi"
    fn_style = "camel"
    ind = "  "
    semi = ""
    INC = None
    ELEMENTS = False
    ST = {"int": "Int", "big": "Long", "float": "Double", "str": "String", "bool": "Boolean", "arr": "Array[Int]"}

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}({self.expr(e[2], env)})", ATOM

    def x_tofloat(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toDouble", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.length", ATOM

    def x_arr(self, e, env):
        return "Array(" + ", ".join(self.expr(x, env) for x in e[1]) + ")", ATOM

    def x_fmt2(self, e, env):
        return f'"%.2f".format({self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.reverse", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toLowerCase", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.replace(" ", "")', ATOM

    def x_words(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.trim.split("\\\\s+").count(_.nonEmpty)', ATOM

    def template(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        if all(k == "lit" for k, _ in parts):
            return self.str_lit("".join(x for _, x in parts))
        fmt = any(k == "fmt2" for k, _ in parts)
        body = ""
        for i, (kind, x) in enumerate(parts):
            if kind == "lit":
                lit = x.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$")
                body += lit.replace("%", "%%") if fmt else lit
            elif kind == "fmt2":
                body += "${" + self.expr(x, env) + "}%.2f"
            elif x[0] == "var":
                nxt = parts[i + 1][1][:1] if i + 1 < len(parts) and parts[i + 1][0] == "lit" else ""
                body += "${" + x[1] + "}" if re.match(r"\w", nxt) else "$" + x[1]
            else:
                body += "${" + self.expr(x, env) + "}"
        return ("f" if fmt else "s") + '"' + body + '"'

    def out(self, parts, env, newline):
        return f"{'println' if newline else 'print'}({self.template(parts, env) if parts else ''})"

    def declare_value(self, name, typ, value, env):
        kw = "var" if name in env.mut else "val"
        if typ == "big" and re.fullmatch(r"-?\d+", value):
            return f"{kw} {name}: Long = {value}"
        return f"{kw} {name} = {value}"

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}({self.expr(s[2], env)}) = {self.expr(s[3], env)}")]

    def read(self, typ, prompt, env):
        fn = {"int": "readInt", "float": "readDouble"}.get(typ, "readText")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        return f"scala.util.Random.nextInt({hi - lo + 1}) + {lo}"

    def for_head(self, name, a, b, env, body):
        if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
            return f"for ({name} <- {self.expr(a, env)} to {self.expr(b[2], env, 6)})"
        return f"for ({name} <- {self.expr(a, env)} until {self.expr(b, env, 6)})"

    def s_break(self, s, env, d):
        return [self.L(d, "break()")]

    def s_for(self, s, env, d):
        if self.breaks(s[4]):
            self.imp("scala.util.control.Breaks._")
            return [self.L(d, "breakable {")] + Braces.s_for(self, s, env, d + 1) + [self.L(d, "}")]
        return Braces.s_for(self, s, env, d)

    def s_while(self, s, env, d):
        lines = Braces.s_while(self, s, env, d + (1 if self.breaks(s[2]) else 0))
        if self.breaks(s[2]):
            self.imp("scala.util.control.Breaks._")
            return [self.L(d, "breakable {")] + lines + [self.L(d, "}")]
        return lines

    def breaks(self, body):
        """Есть ли break именно у этого цикла (не во вложенных)."""
        for s in body:
            if s[0] == "break":
                return True
            if s[0] == "if" and (self.breaks(s[2]) or self.breaks(s[3])):
                return True
        return False

    HELPERS = {
        "readText": """  def readText(prompt: String): String = {
    print(prompt)
    Option(StdIn.readLine()).getOrElse("")
  }""",
        "readInt": """  def readInt(prompt: String): Int = readText(prompt).trim.toInt""",
        "readDouble": """  def readDouble(prompt: String): Double = readText(prompt).trim.replace(',', '.').toDouble   // 36,6 тоже подходит""",
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{p}: {self.ST[t]}" for p, t in params)
        return f"def {self.fname(name)}({args}): {self.ST[ret]} ="

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 1) + self.body_of(f, 2) + [self.L(1, "}")])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 2)
        if any(h.startswith("read") for h in self.helpers):
            self.imp("scala.io.StdIn")
            if "readText" not in self.helpers:
                self.helpers.insert(0, "readText")
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "readText")]
        imports = "\n".join(f"import {i}" for i in sorted(self.imports))
        body = "\n\n".join(helpers + funcs + ["\n".join([self.L(1, "def main(args: Array[String]): Unit = {")] + main + [self.L(1, "}")])])
        return (imports + "\n\n" if imports else "") + "object Main {\n" + body + "\n}"


# ====================================================================== Groovy
class Groovy(Java):
    key, name, ext, file = "groovy", "Groovy", "groovy", None
    semi = ""

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"{self.expr(a, env, ATOM)}.intdiv({self.expr(b, env)})", ATOM
        return None

    def x_tofloat(self, e, env):
        return f"({self.expr(e[1], env, 8)} as double)", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_rev(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.reverse()", ATOM

    def x_words(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.trim().split(/\\s+/).findAll {{ it }}.size()", ATOM

    def x_fmt2(self, e, env):
        return f"String.format('%.2f', {self.expr(e[1], env)})", ATOM

    def str_lit(self, s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'

    def out(self, parts, env, newline):
        fn = "println" if newline else "print"
        if not parts:
            return fn + "()"
        if len(parts) == 1 and parts[0][0] == "expr":
            return f"{fn} {self.expr(parts[0][1], env)}"
        body = ""
        for i, (kind, x) in enumerate(parts):
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
            elif kind == "expr" and x[0] == "var":
                nxt = parts[i + 1][1][:1] if i + 1 < len(parts) and parts[i + 1][0] == "lit" else ""
                body += "${" + x[1] + "}" if re.match(r"[\w.\[]", nxt) else "$" + x[1]
            else:
                body += "${" + self.expr(("fmt2", x) if kind == "fmt2" else x, env) + "}"
        return f'{fn} "{body}"'

    def random(self, lo, hi):
        return f"new Random().nextInt({hi - lo + 1}) + {lo}"

    HELPERS = {
        "readLine": """String readLine(String prompt) {
    print prompt
    return scanner.hasNextLine() ? scanner.nextLine() : ""
}""",
        "readInt": """int readInt(String prompt) {
    return Integer.parseInt(readLine(prompt).trim())
}""",
        "readDouble": """double readDouble(String prompt) {
    return Double.parseDouble(readLine(prompt).trim().replace(',', '.'))   // 36,6 тоже подходит
}""",
    }

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.JT[t]} {p}" for p, t in params)
        return f"{self.JT[ret]} {self.fname(name)}({args})"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 0)
        reading = [h for h in self.helpers if h.startswith("read")]
        head = []
        if reading:
            if "readLine" not in reading:
                self.helpers.insert(0, "readLine")
            head = ["import groovy.transform.Field\n\n@Field Scanner scanner = new Scanner(System.in)"]
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "readLine")]
        return "\n\n".join(head + helpers + funcs + ["\n".join(main)])


# ====================================================================== R
class R(Emitter):
    key, name, ext, file = "r", "R", "R", "main.R"
    PI = "pi"
    ind = "  "
    T, F = "TRUE", "FALSE"
    INC = ADD = None
    OPS = dict(C_OPS, **{"//": "%/%", "%": "%%"})
    PREC = dict(C_PREC, **{"//": 6.5, "%": 6.5})

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(add_const(e[2], 1), env)}]", ATOM

    def x_len(self, e, env):
        return f"length({self.expr(e[1], env)})", ATOM

    def x_arr(self, e, env):
        return "c(" + ", ".join(self.expr(x, env) for x in e[1]) + ")", ATOM

    def x_fmt2(self, e, env):
        return f'sprintf("%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f'paste(rev(strsplit({self.expr(e[1], env)}, "")[[1]]), collapse = "")', ATOM

    def x_lower(self, e, env):
        return f"tolower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        return f'gsub(" ", "", {self.expr(e[1], env)}, fixed = TRUE)', ATOM

    def x_words(self, e, env):
        return f'length(strsplit(trimws({self.expr(e[1], env)}), "\\\\s+")[[1]])', ATOM

    def cat(self, parts, env, newline):
        items = []
        for kind, x in parts:
            if kind == "lit":
                items.append(self.str_lit(x))
            else:
                items.append(self.expr(("fmt2", x) if kind == "fmt2" else x, env))
        if newline:
            if items and items[-1].startswith('"'):
                items[-1] = items[-1][:-1] + '\\n"'
            else:
                items.append('"\\n"')
        if len(items) == 1:
            return f"cat({items[0]})"
        return f'cat({", ".join(items)}, sep = "")'

    def s_print(self, s, env, d):
        return [self.L(d, self.cat(_print_parts(s[1]), env, True))]

    def s_write(self, s, env, d):
        return [self.L(d, self.cat(_print_parts(s[1]), env, False))]

    def s_let(self, s, env, d):
        env.types[s[1]] = s[2]
        return [self.L(d, f"{s[1]} <- {self.expr(s[3], env)}")]

    def s_set(self, s, env, d):
        return [self.L(d, f"{s[1]} <- {self.expr(s[2], env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        self.use("ask")
        env.types[name] = typ
        value = {"int": f"as.integer(ask({prompt}))",
                 "float": f'as.numeric(sub(",", ".", ask({prompt}), fixed = TRUE))'}.get(typ, f"ask({prompt})")
        return [self.L(d, f"{name} <- {value}")]

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        return [self.L(d, f"{s[1]} <- sample({s[2]}:{s[3]}, 1)")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            head = f"if ({self.expr(c, env)}) {{"
            if i:
                out[-1] += " else " + head
            else:
                out.append(self.L(d, head))
            out += self.block(body, env, d + 1)
            out.append(self.L(d, "}"))
        if other:
            out[-1] += " else {"
            out += self.block(other, env, d + 1)
            out.append(self.L(d, "}"))
        return out

    def s_while(self, s, env, d):
        head = "repeat {" if self.forever(s[1]) else f"while ({self.expr(s[1], env)}) {{"
        return [self.L(d, head)] + self.block(s[2], env, d + 1) + [self.L(d, "}")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        last = add_const(b, -1)
        if a[0] == "num" and last[0] == "num":
            rng = f"{a[1]}:{last[1]}"
        elif a == ("num", 1):
            rng = f"seq_len({self.expr(last, env)})"
        elif a == ("num", 0):
            rng = f"seq_len({self.expr(b, env)}) - 1"
        else:
            rng = f"seq({self.expr(a, env)}, length.out = max(0, {self.expr(add_const(op('-', b, a), 0), env)}))"
        return [self.L(d, f"for ({name} in {rng}) {{")] + self.block(body, env, d + 1) + [self.L(d, "}")]

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        return [self.L(d, f"return({self.expr(s[1], env)})")]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(add_const(s[2], 1), env)}] <- {self.expr(s[3], env)}")]

    HELPERS = {"ask": """# Ввод: в RStudio и консоли R — readline(), при запуске Rscript — строка из стандартного ввода
if (!interactive()) input <- file("stdin", open = "r")
ask <- function(prompt) {
  if (interactive()) return(readline(prompt))
  cat(prompt)
  readLines(input, n = 1)
}"""}

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            lines = self.block(body, Env({p: t for p, t in params}), 1)
            if lines and lines[-1].startswith(self.ind + "return("):
                lines[-1] = self.ind + lines[-1][len(self.ind) + 7:-1]    # последнее значение — и есть результат
            funcs.append("\n".join([f"{name} <- function({', '.join(p for p, _ in params)}) {{"] + lines + ["}"]))
        main = self.block(self.prog["main"], Env({}), 0)
        head = ["options(scipen = 999)   # большие числа — целиком, без 1e+05"]
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(head + helpers + funcs + ["\n".join(main)])



# ====================================================================== Swift
class Swift(Braces):
    key, name, ext = "swift", "Swift", "swift"
    PI = "Double.pi"
    fn_style = "camel"
    semi = ""
    paren_cond = False
    INC = None

    def x_tofloat(self, e, env):
        return f"Double({self.expr(e[1], env)})", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.count", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f'String(format: "%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"String({self.expr(e[1], env, ATOM)}.reversed())", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.lowercased()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.replacingOccurrences(of: " ", with: "")', ATOM

    def x_words(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.split(whereSeparator: {{ $0 == " " || $0 == "\\t" }}).count', ATOM

    def call(self, e, env):
        return f"{self.fname(e[1])}({', '.join(self.expr(a, env) for a in e[2])})"

    def template(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        body = ""
        for kind, x in parts:
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace('"', '\\"')
            else:
                body += "\\(" + self.expr(("fmt2", x) if kind == "fmt2" else x, env) + ")"
        return '"' + body + '"'

    def out(self, parts, env, newline):
        text = self.template(parts, env) if parts else ""
        return f"print({text})" if newline else f'print({text}, terminator: "")'

    def declare_value(self, name, typ, value, env):
        return f"{'var' if name in env.mut else 'let'} {name} = {value}"

    def read(self, typ, prompt, env):
        fn = {"int": "readInt", "float": "readDouble"}.get(typ, "readText")
        self.use(fn)
        return f"{fn}({self.str_lit(prompt)})"

    def random(self, lo, hi):
        return f"Int.random(in: {lo}...{hi})"

    def for_head(self, name, a, b, env, body):
        var = name if var_used(body, name) else "_"
        static = not any(n[0] == "var" for n in walk([a, b]))       # границы без переменных — диапазон не перевернётся
        if static or (a == ("num", 0) and b[0] == "len"):
            if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
                return f"for {var} in {self.expr(a, env, 6)}...{self.expr(b[2], env, 6)}"
            return f"for {var} in {self.expr(a, env, 6)}..<{self.expr(b, env, 6)}"
        # stride не падает, если конец меньше начала (например, ввели 0)
        return f"for {var} in stride(from: {self.expr(a, env)}, to: {self.expr(b, env)}, by: 1)"

    HELPERS = {
        "readText": """func readText(_ prompt: String) -> String {
    print(prompt, terminator: "")
    fflush(stdout)
    return readLine() ?? ""
}""",
        "readInt": """func readInt(_ prompt: String) -> Int {
    return Int(readText(prompt).trimmingCharacters(in: .whitespaces)) ?? 0
}""",
        "readDouble": """func readDouble(_ prompt: String) -> Double {
    let text = readText(prompt).trimmingCharacters(in: .whitespaces)
    return Double(text.replacingOccurrences(of: ",", with: ".")) ?? 0   // 36,6 тоже подходит
}""",
    }
    SW = {"int": "Int", "big": "Int", "float": "Double", "str": "String", "bool": "Bool", "arr": "[Int]"}

    def func_head(self, name, params, ret):
        args = ", ".join(f"_ {p}: {self.SW[t]}" for p, t in params)
        return f"func {self.fname(name)}({args}) -> {self.SW[ret]}"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 0)
        if any(h.startswith("read") for h in self.helpers) and "readText" not in self.helpers:
            self.helpers.insert(0, "readText")
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "readText")]
        return "\n\n".join(["import Foundation"] + helpers + funcs + ["\n".join(main)])


# ====================================================================== Dart
class Dart(Braces):
    key, name, ext = "dart", "Dart", "dart"
    PI, MATH = "pi", ("dart:math",)
    fn_style = "camel"
    ind = "  "
    ELEMENTS = False
    DT = {"int": "int", "big": "int", "float": "double", "str": "String", "bool": "bool", "arr": "List<int>"}

    def str_lit(self, s):
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$") + "'"

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"{self.expr(a, env, 6)} ~/ {self.expr(b, env, 7)}", 6
        return None

    def x_tofloat(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toDouble()", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.length", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toStringAsFixed(2)", ATOM

    def x_rev(self, e, env):
        return f"String.fromCharCodes({self.expr(e[1], env, ATOM)}.runes.toList().reversed)", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.toLowerCase()", ATOM

    def x_nospace(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.replaceAll(' ', '')", ATOM

    def x_words(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.trim().split(RegExp(r'\\s+')).where((w) => w.isNotEmpty).length", ATOM

    def template(self, parts, env):
        if len(parts) == 1 and parts[0][0] == "expr" and self.typ(parts[0][1], env) == "str":
            return self.expr(parts[0][1], env)
        if len(parts) == 1 and parts[0][0] == "expr":
            return self.expr(parts[0][1], env)
        body = ""
        for i, (kind, x) in enumerate(parts):
            if kind == "lit":
                body += x.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$")
            elif kind == "expr" and x[0] == "var":
                nxt = parts[i + 1][1][:1] if i + 1 < len(parts) and parts[i + 1][0] == "lit" else ""
                body += "${" + x[1] + "}" if re.match(r"\w", nxt) else "$" + x[1]
            else:
                body += "${" + self.expr(("fmt2", x) if kind == "fmt2" else x, env) + "}"
        return "'" + body + "'"

    def out(self, parts, env, newline):
        if newline:
            return f"print({self.template(parts, env) if parts else chr(39) * 2})"
        self.imp("dart:io")
        return f"stdout.write({self.template(parts, env)})"

    def declare_value(self, name, typ, value, env):
        return f"{'var' if name in env.mut else 'final'} {name} = {value}"

    def read(self, typ, prompt, env):
        self.use("ask")
        p = self.str_lit(prompt)
        return {"int": f"int.parse(ask({p}).trim())",
                "float": f"double.parse(ask({p}).trim().replaceAll(',', '.'))"}.get(typ, f"ask({p})")

    def random(self, lo, hi):
        self.imp("dart:math")
        return f"Random().nextInt({hi - lo + 1}) + {lo}"

    def decl_int(self):
        return "var"

    HELPERS = {"ask": """String ask(String prompt) {
  stdout.write(prompt);
  return stdin.readLineSync() ?? '';
}"""}

    def func_head(self, name, params, ret):
        args = ", ".join(f"{self.DT[t]} {p}" for p, t in params)
        return f"{self.DT[ret]} {self.fname(name)}({args})"

    def program(self):
        funcs = ["\n".join(self.opener(self.func_head(f[1], f[2], f[3]), 0) + self.body_of(f) + ["}"])
                 for f in self.prog["funcs"]]
        main = self.block(self.prog["main"], self.main_env(), 1)
        if self.helpers:
            self.imp("dart:io")
        imports = "\n".join(f"import '{i}';" for i in sorted(self.imports))
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(([imports] if imports else []) + helpers + funcs + ["\n".join(["void main() {"] + main + ["}"])])


# ====================================================================== Julia
class Julia(Emitter):
    key, name, ext = "julia", "Julia", "jl"
    PI = "pi"
    INC = None
    RENAME = {"factorial": "my_factorial", "gcd": "my_gcd"}     # factorial и gcd в Julia уже есть встроенные

    def str_lit(self, s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"div({self.expr(a, env)}, {self.expr(b, env)})", ATOM
        return None

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(add_const(e[2], 1), env)}]", ATOM

    def x_len(self, e, env):
        return f"length({self.expr(e[1], env)})", ATOM

    def x_arr(self, e, env):
        return "[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        self.imp("Printf")
        return f'@sprintf("%.2f", {self.expr(e[1], env)})', ATOM

    def x_rev(self, e, env):
        return f"reverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        return f"lowercase({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        return f'replace({self.expr(e[1], env)}, " " => "")', ATOM

    def x_words(self, e, env):
        return f"length(split({self.expr(e[1], env)}))", ATOM

    def items(self, parts, env):
        return [self.str_lit(x) if k == "lit" else self.expr(("fmt2", x) if k == "fmt2" else x, env) for k, x in parts]

    def s_print(self, s, env, d):
        return [self.L(d, f"println({', '.join(self.items(_print_parts(s[1]), env))})")]

    def s_write(self, s, env, d):
        return [self.L(d, f"print({', '.join(self.items(_print_parts(s[1]), env))})")]

    def s_let(self, s, env, d):
        env.types[s[1]] = s[2]
        return [self.L(d, f"{s[1]} = {self.expr(s[3], env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        self.use("ask")
        env.types[name] = typ
        value = {"int": f"parse(Int, strip(ask({prompt})))",
                 "float": f'parse(Float64, replace(strip(ask({prompt})), "," => "."))'}.get(typ, f"ask({prompt})")
        return [self.L(d, f"{name} = {value}")]

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        return [self.L(d, f"{s[1]} = rand({s[2]}:{s[3]})")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "elseif ") + self.expr(c, env)))
            out += self.block(body, env, d + 1)
        if other:
            out.append(self.L(d, "else"))
            out += self.block(other, env, d + 1)
        return out + [self.L(d, "end")]

    def s_while(self, s, env, d):
        c = "true" if self.forever(s[1]) else self.expr(s[1], env)
        return [self.L(d, f"while {c}")] + self.block(s[2], env, d + 1) + [self.L(d, "end")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        last = add_const(b, -1)
        var = name if var_used(body, name) else "_"
        return ([self.L(d, f"for {var} in {self.expr(a, env, 6)}:{self.expr(last, env, 6)}")] + self.block(body, env, d + 1) +
                [self.L(d, "end")])

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        return [self.L(d, "return " + self.expr(s[1], env))]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(add_const(s[2], 1), env)}] = {self.expr(s[3], env)}")]

    HELPERS = {"ask": """function ask(prompt)
    print(prompt)
    flush(stdout)
    return readline()
end"""}

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            funcs.append("\n".join([f"function {self.fname(name)}({', '.join(p for p, _ in params)})"] +
                                   self.block(body, Env({p: t for p, t in params}), 1) + ["end"]))
        main = self.block(self.prog["main"], Env({}), 1)
        head = [f"using {i}" for i in self.imports]
        helpers = [self.HELPERS[h] for h in self.helpers]
        # код в функции main: в скрипте Julia переменные внутри циклов иначе стали бы «чужими»
        return "\n\n".join(head + helpers + funcs + ["\n".join(["function main()"] + main + ["end"]), "main()"])


# ====================================================================== PowerShell
class PowerShell(Braces):
    key, name, ext = "powershell", "PowerShell", "ps1"
    SQRT, PI = "[math]::Sqrt({x})", "[math]::PI"
    semi = ""
    T, F = "$true", "$false"
    NOT, NOT_PREC = "-not ", 7
    OPS = {"==": "-eq", "!=": "-ne", "<": "-lt", "<=": "-le", ">": "-gt", ">=": "-ge", "+": "+", "-": "-", "*": "*",
           "/": "/", "//": "/", "%": "%", "and": "-and", "or": "-or"}

    def fname(self, name):
        if name.startswith("is_"):
            return "Test-" + "".join(p.title() for p in name[3:].split("_"))
        return "Get-" + "".join(p.title() for p in name.split("_"))

    def v(self, name):
        return "$" + name

    def str_lit(self, s):
        return '"' + s.replace("`", "``").replace('"', '`"').replace("$", "`$") + '"'

    def bin_special(self, o, a, b, env):
        if o == "//":
            return f"[math]::Floor({self.expr(a, env, 6)} / {self.expr(b, env, 7)})", ATOM
        return None

    def call(self, e, env):
        args = " ".join(self.expr(a, env, ATOM) for a in e[2])
        return f"({self.fname(e[1])} {args})"

    def x_tofloat(self, e, env):
        return f"[double]{self.expr(e[1], env, ATOM)}", 7

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(e[2], env)}]", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.Count", ATOM

    def x_arr(self, e, env):
        return "@(" + ", ".join(self.expr(x, env) for x in e[1]) + ")", ATOM

    def x_fmt2(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.ToString("F2")', ATOM

    def x_rev(self, e, env):
        self.use("Get-Reversed")
        return f"(Get-Reversed {self.expr(e[1], env, ATOM)})", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.ToLower()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.Replace(" ", "")', ATOM

    def x_words(self, e, env):
        return f"@({self.expr(e[1], env, ATOM)} -split '\\s+' | Where-Object {{ $_ }}).Count", ATOM

    def cond(self, e, env):
        if e[0] == "call":
            return "(" + self.call(e, env)[1:-1] + ")"
        return f"({self.expr(e, env)})"

    def text(self, parts, env):
        body = ""
        for i, (kind, x) in enumerate(parts):
            if kind == "lit":
                body += x.replace("`", "``").replace('"', '`"').replace("$", "`$")
            elif kind == "expr" and x[0] == "var":
                nxt = parts[i + 1][1][:1] if i + 1 < len(parts) and parts[i + 1][0] == "lit" else ""
                body += "${" + x[1] + "}" if re.match(r"[\w:\[.]", nxt) else "$" + x[1]
            else:
                inner = self.expr(("fmt2", x) if kind == "fmt2" else x, env)
                if inner.startswith("(") and inner.endswith(")") and x[0] == "call":
                    inner = inner[1:-1]
                body += "$(" + inner + ")"
        return '"' + body + '"'

    def out(self, parts, env, newline):
        return ("Write-Host " if newline else "Write-Host -NoNewline ") + (self.text(parts, env) if parts else '""')

    def declare_value(self, name, typ, value, env):
        if typ == "big" and re.fullmatch(r"-?\d+", value):
            return f"[long]${name} = {value}"
        return f"${name} = {value}"

    def assign(self, name, value):
        return f"${name} = {value}"

    def read(self, typ, prompt, env):
        self.use("Read-Text")
        p = self.str_lit(prompt)
        return {"int": f"[int](Read-Text {p})", "float": f'[double]((Read-Text {p}).Replace(",", "."))'}.get(typ, f"Read-Text {p}")

    def random(self, lo, hi):
        return f"Get-Random -Minimum {lo} -Maximum {hi + 1}"

    def while_head(self, c, env):
        return "while ($true)" if self.forever(c) else "while " + self.cond(c, env)

    def for_head(self, name, a, b, env, body):
        x = "$" + name
        return f"for ({x} = {self.expr(a, env)}; {self.upto(x, b, env, '-lt', '-le')}; {x}++)"

    def s_if(self, s, env, d):
        return [l.replace("} else if (", "} elseif (") for l in Braces.s_if(self, s, env, d)]

    HELPERS = {
        "Read-Text": """function Read-Text([string]$Prompt) {
    Write-Host -NoNewline $Prompt
    return [Console]::ReadLine()
}""",
        "Get-Reversed": """function Get-Reversed([string]$Text) {
    $chars = $Text.ToCharArray()
    [array]::Reverse($chars)
    return -join $chars
}""",
    }
    PT = {"int": "[int]", "big": "[long]", "float": "[double]", "str": "[string]", "bool": "[bool]", "arr": "[int[]]"}

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            args = ", ".join(f"{self.PT[t]}${p}" for p, t in f[2])
            funcs.append("\n".join([f"function {self.fname(f[1])}({args}) {{"] + self.body_of(f) + ["}"]))
        main = self.block(self.prog["main"], self.main_env(), 0)
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(helpers + funcs + ["\n".join(main)])


# ====================================================================== Visual Basic .NET
class VisualBasic(Emitter):
    key, name, ext, file = "vbnet", "Visual Basic .NET", "vb", "Program.vb"
    SQRT, PI = "Math.Sqrt({x})", "Math.PI"
    fn_style = "pascal"
    T, F = "True", "False"
    NOT, NOT_PREC = "Not ", 2.5
    INC = "{x} += 1"
    ADD = "{x} {o}= {e}"
    OPS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">=", "+": "+", "-": "-", "*": "*", "/": "/",
           "//": "\\", "%": "Mod", "and": "AndAlso", "or": "OrElse"}
    PREC = {"or": 1, "and": 2, "==": 3, "!=": 3, "<": 3, "<=": 3, ">": 3, ">=": 3, "+": 5, "-": 5, "%": 5.5, "//": 5.7,
            "*": 6, "/": 6}
    VT = {"int": "Integer", "big": "Long", "float": "Double", "str": "String", "bool": "Boolean", "arr": "Integer()"}

    def str_lit(self, s):
        return '"' + s.replace('"', '""') + '"'

    def x_tofloat(self, e, env):
        return f"CDbl({self.expr(e[1], env)})", ATOM

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}({self.expr(e[2], env)})", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.Length", ATOM

    def x_arr(self, e, env):
        return "{" + ", ".join(self.expr(x, env) for x in e[1]) + "}", ATOM

    def x_fmt2(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.ToString("F2")', ATOM

    def x_rev(self, e, env):
        return f"StrReverse({self.expr(e[1], env)})", ATOM

    def x_lower(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.ToLower()", ATOM

    def x_nospace(self, e, env):
        return f'{self.expr(e[1], env, ATOM)}.Replace(" ", "")', ATOM

    def x_words(self, e, env):
        return f'Text.RegularExpressions.Regex.Matches({self.expr(e[1], env)}, "\\S+").Count', ATOM

    def concat(self, parts, env):
        items = [self.str_lit(x) if k == "lit" else self.expr(("fmt2", x) if k == "fmt2" else x, env, ATOM) for k, x in parts]
        return " & ".join(items)

    def s_print(self, s, env, d):
        parts = _print_parts(s[1])
        return [self.L(d, f"Console.WriteLine({self.concat(parts, env) if parts else ''})")]

    def s_write(self, s, env, d):
        return [self.L(d, f"Console.Write({self.concat(_print_parts(s[1]), env)})")]

    def s_let(self, s, env, d):
        name, typ, e = s[1], s[2], s[3]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, f"Dim {name} As {self.VT[typ]} = {self.expr(e, env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        fn = {"int": "ReadInt", "float": "ReadDouble"}.get(typ, "ReadText")
        self.use(fn)
        if name in env.declared:
            return [self.L(d, f"{name} = {fn}({prompt})")]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, f"Dim {name} As {self.VT[typ]} = {fn}({prompt})")]

    def s_rand(self, s, env, d):
        env.types[s[1]] = "int"
        env.declared.add(s[1])
        return [self.L(d, f"Dim {s[1]} As Integer = New Random().Next({s[2]}, {s[3] + 1})")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("If " if i == 0 else "ElseIf ") + self.expr(c, env) + " Then"))
            out += self.block(body, env.inner(), d + 1)
        if other:
            out.append(self.L(d, "Else"))
            out += self.block(other, env.inner(), d + 1)
        return out + [self.L(d, "End If")]

    def s_while(self, s, env, d):
        c = "True" if self.forever(s[1]) else self.expr(s[1], env)
        return [self.L(d, f"While {c}")] + self.block(s[2], env.inner("While"), d + 1) + [self.L(d, "End While")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        inner = env.inner("For")
        inner.declared.add(name)
        return ([self.L(d, f"For {name} As Integer = {self.expr(a, env)} To {self.expr(add_const(b, -1), env)}")] +
                self.block(body, inner, d + 1) + [self.L(d, "Next")])

    def s_break(self, s, env, d):
        return [self.L(d, "Exit " + (env.loops[-1] if env.loops else "While"))]

    def s_return(self, s, env, d):
        return [self.L(d, "Return " + self.expr(s[1], env))]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}({self.expr(s[2], env)}) = {self.expr(s[3], env)}")]

    HELPERS = {
        "ReadText": """    Function ReadText(prompt As String) As String
        Console.Write(prompt)
        Dim line As String = Console.ReadLine()
        If line Is Nothing Then line = ""
        Return line
    End Function""",
        "ReadInt": """    Function ReadInt(prompt As String) As Integer
        Return Integer.Parse(ReadText(prompt).Trim())
    End Function""",
        "ReadDouble": """    Function ReadDouble(prompt As String) As Double
        ' 36,6 и 36.6 подходят при любых настройках Windows
        Return Double.Parse(ReadText(prompt).Trim().Replace(",", "."), Globalization.CultureInfo.InvariantCulture)
    End Function""",
    }

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params}, declared=[p for p, _ in params], ret=ret, fn=name)
            args = ", ".join(f"{p} As {self.VT[t]}" for p, t in params)
            funcs.append("\n".join([self.L(1, f"Function {self.fname(name)}({args}) As {self.VT[ret]}")] + self.block(body, env, 2) +
                                   [self.L(1, "End Function")]))
        main = self.block(self.prog["main"], Env({}), 2)
        if any(h.startswith("Read") for h in self.helpers) and "ReadText" not in self.helpers:
            self.helpers.insert(0, "ReadText")
        helpers = [self.HELPERS[h] for h in sorted(self.helpers, key=lambda h: h != "ReadText")]
        body = "\n\n".join(helpers + funcs + ["\n".join([self.L(1, "Sub Main()")] + main + [self.L(1, "End Sub")])])
        return "Imports System\n\nModule Program\n" + body + "\nEnd Module"



# ====================================================================== Fortran
class Fortran(Emitter):
    key, name, ext, file = "fortran", "Fortran", "f90", "main.f90"
    PI = "acos(-1.0d0)"
    INC = ADD = None
    T, F = ".true.", ".false."
    NOT, NOT_PREC = ".not. ", 2.5
    OPS = {"==": "==", "!=": "/=", "<": "<", "<=": "<=", ">": ">", ">=": ">=", "+": "+", "-": "-", "*": "*", "/": "/",
           "//": "/", "%": "mod", "and": ".and.", "or": ".or."}
    FT = {"int": "integer", "big": "integer(8)", "float": "real(8)", "str": "character(len=256)", "bool": "logical"}
    FMT = {"int": "I0", "big": "I0", "float": "G0", "str": "A", "bool": "L1"}

    def str_lit(self, s):
        return "'" + s.replace("'", "''") + "'"

    def flt_lit(self, x):
        return repr(float(x)) + "d0"

    def bin_special(self, o, a, b, env):
        if o == "%":
            return f"mod({self.expr(a, env)}, {self.expr(b, env)})", ATOM
        if o in ("==", "!=") and self.typ(a, env) == "str":
            return f"trim({self.expr(a, env)}) {self.OPS[o]} trim({self.expr(b, env)})", 3
        return None

    def x_tofloat(self, e, env):
        return f"real({self.expr(e[1], env)}, 8)", ATOM

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}({self.expr(e[2], env)})", ATOM

    def x_len(self, e, env):
        return f"size({self.expr(e[1], env)})", ATOM

    def x_rev(self, e, env):
        self.use("reverse")
        return f"reverse(trim({self.expr(e[1], env)}))", ATOM

    def x_lower(self, e, env):
        self.use("to_lower")
        return f"to_lower({self.expr(e[1], env)})", ATOM

    def x_nospace(self, e, env):
        self.use("remove_spaces")
        return f"remove_spaces({self.expr(e[1], env)})", ATOM

    def x_words(self, e, env):
        self.use("count_words")
        return f"count_words({self.expr(e[1], env)})", ATOM

    def x_fmt2(self, e, env):
        raise ValueError("fmt2 в Fortran — только в выводе")

    def write(self, parts, env, newline):
        fmts, items = [], []
        for kind, x in parts:
            if kind == "lit":
                fmts.append("A")
                items.append(self.str_lit(x))
            elif kind == "fmt2":
                fmts.append("F0.2")
                items.append(self.expr(x, env))
            else:
                t = self.typ(x, env)
                fmts.append(self.FMT[t])
                items.append(f"trim({self.expr(x, env)})" if t == "str" and x[0] == "var" else self.expr(x, env))
        if not items:
            return "print '(A)', ''"
        fmt = "'(" + ", ".join(fmts) + ")'"
        if newline:
            return f"print {fmt}, " + ", ".join(items)
        return f"write(*, {fmt}, advance='no') " + ", ".join(items)

    def s_print(self, s, env, d):
        return [self.L(d, self.write(_print_parts(s[1]), env, True))]

    def s_write(self, s, env, d):
        return [self.L(d, self.write(_print_parts(s[1]), env, False))]

    def s_let(self, s, env, d):
        if s[2] == "arr":
            return []                      # массив объявлен вместе со значениями
        return [self.L(d, f"{s[1]} = {self.expr(s[3], env)}")]

    def s_set(self, s, env, d):
        return [self.L(d, f"{s[1]} = {self.expr(s[2], env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], s[3]
        if typ == "float":
            self.use("read_real")
            return [self.L(d, f"{name} = read_real({self.str_lit(prompt)})")]
        return [self.L(d, f"write(*, '(A)', advance='no') {self.str_lit(prompt)}"),
                self.L(d, f"read(*, {chr(39) + '(A)' + chr(39) if typ == 'str' else '*'}) {name}")]

    def s_rand(self, s, env, d):
        self.use("random_int")
        return [self.L(d, "call random_seed()"), self.L(d, f"{s[1]} = random_int({s[2]}, {s[3]})")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if (" if i == 0 else "else if (") + self.expr(c, env) + ") then"))
            out += self.block(body, env, d + 1)
        if other:
            out.append(self.L(d, "else"))
            out += self.block(other, env, d + 1)
        return out + [self.L(d, "end if")]

    def s_while(self, s, env, d):
        head = "do" if self.forever(s[1]) else f"do while ({self.expr(s[1], env)})"
        return [self.L(d, head)] + self.block(s[2], env, d + 1) + [self.L(d, "end do")]

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        return ([self.L(d, f"do {name} = {self.expr(a, env)}, {self.expr(add_const(b, -1), env)}")] +
                self.block(body, env, d + 1) + [self.L(d, "end do")])

    def s_break(self, s, env, d):
        return [self.L(d, "exit")]

    def s_return(self, s, env, d):
        out = [self.L(d, f"{env.fn} = {self.expr(s[1], env)}")]
        if getattr(env, "last", None) is not s:
            out.append(self.L(d, "return"))
        return out

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}({self.expr(s[2], env)}) = {self.expr(s[3], env)}")]

    def decls(self, types, arrays, d, skip=()):
        out = []
        for name, t in types.items():
            if name not in skip and t != "arr":
                out.append(self.L(d, f"{self.FT[t]} :: {name}"))
        for name, items in arrays:
            vals = ", ".join(str(x[1]) for x in items)
            out.append(self.L(d, f"integer :: {name}(0:{len(items) - 1}) = [{vals}]"))
        return out

    HELPERS = {
        "read_real": """    real(8) function read_real(prompt)
        character(len=*), intent(in) :: prompt
        character(len=64) :: line
        integer :: i
        write(*, '(A)', advance='no') prompt
        read(*, '(A)') line
        do i = 1, len_trim(line)
            if (line(i:i) == ',') line(i:i) = '.'   ! 36,6 тоже подходит
        end do
        read(line, *) read_real
    end function read_real""",
        "random_int": """    integer function random_int(lo, hi)
        integer, intent(in) :: lo, hi
        real :: r
        call random_number(r)
        random_int = lo + int(r * (hi - lo + 1))
    end function random_int""",
        "reverse": """    ! Строка наоборот по символам UTF-8 — русские буквы не ломаются
    function reverse(s) result(out)
        character(len=*), intent(in) :: s
        character(len=len(s)) :: out
        integer :: i, n, k
        n = len(s)
        i = 1
        do while (i <= n)
            k = 1
            if (iachar(s(i:i)) >= 240) then
                k = 4
            else if (iachar(s(i:i)) >= 224) then
                k = 3
            else if (iachar(s(i:i)) >= 192) then
                k = 2
            end if
            k = min(k, n - i + 1)
            out(n - i - k + 2:n - i + 1) = s(i:i + k - 1)
            i = i + k
        end do
    end function reverse""",
        "to_lower": """    ! Строчные буквы: латиница и кириллица в UTF-8
    function to_lower(s) result(out)
        character(len=*), intent(in) :: s
        character(len=len(s)) :: out
        integer :: i, c, nxt
        out = s
        i = 1
        do while (i <= len(s))
            c = iachar(s(i:i))
            nxt = 0
            if (i < len(s)) nxt = iachar(s(i + 1:i + 1))
            if (c >= 65 .and. c <= 90) then
                out(i:i) = achar(c + 32)
            else if (c == 208 .and. nxt >= 144 .and. nxt <= 159) then      ! А–П
                out(i + 1:i + 1) = achar(nxt + 32)
                i = i + 1
            else if (c == 208 .and. nxt >= 160 .and. nxt <= 175) then      ! Р–Я
                out(i:i + 1) = achar(209) // achar(nxt - 32)
                i = i + 1
            else if (c == 208 .and. nxt == 129) then                       ! Ё
                out(i:i + 1) = achar(209) // achar(145)
                i = i + 1
            end if
            i = i + 1
        end do
    end function to_lower""",
        "remove_spaces": """    function remove_spaces(s) result(out)
        character(len=*), intent(in) :: s
        character(len=len(s)) :: out
        integer :: i, j
        out = ''
        j = 0
        do i = 1, len_trim(s)
            if (s(i:i) /= ' ') then
                j = j + 1
                out(j:j) = s(i:i)
            end if
        end do
    end function remove_spaces""",
        "count_words": """    integer function count_words(s)
        character(len=*), intent(in) :: s
        integer :: i
        logical :: in_word
        count_words = 0
        in_word = .false.
        do i = 1, len_trim(s)
            if (s(i:i) == ' ') then
                in_word = .false.
            else if (.not. in_word) then
                in_word = .true.
                count_words = count_words + 1
            end if
        end do
    end function count_words""",
    }

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params}, ret=ret, fn=name)
            env.last = body[-1] if body and body[-1][0] == "return" else None
            lines = self.block(body, env, 2)
            types = collect_types(body, {})
            head = [self.L(1, f"{self.FT[ret]} function {name}({', '.join(p for p, _ in params)})")]
            head += [self.L(2, f"{self.FT[t]}, intent(in) :: {p}") for p, t in params]
            head += self.decls(types, [], 2, skip=[p for p, _ in params])
            funcs.append("\n".join(head + lines + [self.L(1, f"end function {name}")]))
        main = self.block(self.prog["main"], Env({}), 1)
        types = collect_types(self.prog["main"], {})
        arrays = [(s[1], s[3][1]) for s in self.prog["main"] if s[0] == "let" and s[2] == "arr"]
        helpers = [self.HELPERS[h] for h in self.helpers]
        out = ["program main", self.L(1, "implicit none")] + self.decls(types, arrays, 1) + [""] + main
        if helpers or funcs:
            out += ["", "contains", ""] + ["\n\n".join(helpers + funcs)]
        return "\n".join(out + ["end program main"])


# ====================================================================== Nim
class Nim(Emitter):
    key, name, ext = "nim", "Nim", "nim"
    PI, MATH = "PI", ("math",)
    fn_style = "camel"
    ind = "  "
    INC = "inc {x}"
    T, F = "true", "false"
    NOT, NOT_PREC = "not ", 7
    OPS = dict(C_OPS, **{"//": "div", "%": "mod", "and": "and", "or": "or"})
    NT = {"int": "int", "big": "int", "float": "float", "str": "string", "bool": "bool", "arr": "seq[int]"}

    def x_tofloat(self, e, env):
        return f"float({self.expr(e[1], env)})", ATOM

    def x_idx(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}[{self.expr(e[2], env)}]", ATOM

    def x_len(self, e, env):
        return f"{self.expr(e[1], env, ATOM)}.len", ATOM

    def x_arr(self, e, env):
        return "@[" + ", ".join(self.expr(x, env) for x in e[1]) + "]", ATOM

    def x_fmt2(self, e, env):
        self.imp("strutils")
        return f"formatFloat({self.expr(e[1], env)}, ffDecimal, 2)", ATOM

    def x_rev(self, e, env):
        self.imp("unicode")
        return f"{self.expr(e[1], env, ATOM)}.reversed", ATOM

    def x_lower(self, e, env):
        self.imp("unicode")
        return f"{self.expr(e[1], env, ATOM)}.toLower", ATOM

    def x_nospace(self, e, env):
        self.imp("strutils")
        return f'{self.expr(e[1], env, ATOM)}.replace(" ", "")', ATOM

    def x_words(self, e, env):
        self.imp("strutils")
        return f"{self.expr(e[1], env, ATOM)}.splitWhitespace.len", ATOM

    def items(self, parts, env):
        return [self.str_lit(x) if k == "lit" else self.expr(("fmt2", x) if k == "fmt2" else x, env) for k, x in parts]

    def s_print(self, s, env, d):
        items = self.items(_print_parts(s[1]), env)
        return [self.L(d, "echo " + ", ".join(items) if items else 'echo ""')]

    def s_write(self, s, env, d):
        return [self.L(d, f"stdout.write({', '.join(self.items(_print_parts(s[1]), env))})")]

    def s_let(self, s, env, d):
        name, typ, e = s[1], s[2], s[3]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, f"{'var' if name in env.mut else 'let'} {name} = {self.expr(e, env)}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        self.use("ask")
        self.imp("strutils")
        value = {"int": f"parseInt(ask({prompt}).strip)", "float": f'parseFloat(ask({prompt}).strip.replace(",", "."))'}.get(
            typ, f"ask({prompt})")
        if name in env.declared:
            return [self.L(d, f"{name} = {value}")]
        env.types[name] = typ
        env.declared.add(name)
        return [self.L(d, f"{'var' if name in env.mut else 'let'} {name} = {value}")]

    def s_rand(self, s, env, d):
        self.imp("random")
        env.types[s[1]] = "int"
        return [self.L(d, "randomize()"), self.L(d, f"let {s[1]} = rand({s[2]} .. {s[3]})")]

    def s_set(self, s, env, d):
        name, e = s[1], s[2]
        if e[0] == "bin" and e[2] == ("var", name) and e[1] in ("+", "-", "*"):
            if e[1] == "+" and e[3] == ("num", 1):
                return [self.L(d, f"inc {name}")]
            return [self.L(d, f"{name} {e[1]}= {self.expr(e[3], env)}")]
        return [self.L(d, f"{name} = {self.expr(e, env)}")]

    def s_if(self, s, env, d):
        branches, other = self.chain(s)
        out = []
        for i, (c, body) in enumerate(branches):
            out.append(self.L(d, ("if " if i == 0 else "elif ") + self.expr(c, env) + ":"))
            out += self.block(body, env.inner(), d + 1)
        if other:
            out.append(self.L(d, "else:"))
            out += self.block(other, env.inner(), d + 1)
        return out

    def s_while(self, s, env, d):
        c = "true" if self.forever(s[1]) else self.expr(s[1], env)
        return [self.L(d, f"while {c}:")] + self.block(s[2], env.inner(), d + 1)

    def s_for(self, s, env, d):
        name, a, b, body = s[1:]
        env.types[name] = "int"
        var = name if var_used(body, name) else "_"
        if b[0] == "bin" and b[1] == "+" and b[3] == ("num", 1):
            rng = f"{self.expr(a, env)} .. {self.expr(b[2], env)}"
        else:
            rng = f"{self.expr(a, env)} ..< {self.expr(b, env)}"
        inner = env.inner()
        inner.declared.add(name)
        return [self.L(d, f"for {var} in {rng}:")] + self.block(body, inner, d + 1)

    def s_break(self, s, env, d):
        return [self.L(d, "break")]

    def s_return(self, s, env, d):
        return [self.L(d, "return " + self.expr(s[1], env))]

    def s_setidx(self, s, env, d):
        return [self.L(d, f"{self.expr(s[1], env, ATOM)}[{self.expr(s[2], env)}] = {self.expr(s[3], env)}")]

    HELPERS = {"ask": """proc ask(prompt: string): string =
  stdout.write(prompt)
  stdout.flushFile()
  result = stdin.readLine()"""}

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            env = Env({p: t for p, t in params}, declared=[p for p, _ in params], mut=mutated(body))
            args = ", ".join(f"{p}: {self.NT[t]}" for p, t in params)
            funcs.append("\n".join([f"proc {self.fname(name)}({args}): {self.NT[ret]} ="] + self.block(body, env, 1)))
        main = self.block(self.prog["main"], Env({}, mut=mutated(self.prog["main"])), 0)
        head = ["import " + ", ".join(sorted(self.imports))] if self.imports else []
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(head + helpers + funcs + ["\n".join(main)])


# ====================================================================== Crystal
class Crystal(Ruby):
    key, name, ext = "crystal", "Crystal", "cr"
    OPS = dict(C_OPS, **{"//": "//"})
    CT = {"int": "Int32", "big": "Int64", "float": "Float64", "str": "String", "bool": "Bool", "arr": "Array(Int32)"}

    def x_fmt2(self, e, env):
        return f'"%.2f" % {self.expr(e[1], env, ATOM)}', 6

    def s_let(self, s, env, d):
        env.types[s[1]] = s[2]
        value = self.expr(s[3], env)
        if s[2] == "big" and re.fullmatch(r"-?\d+", value):
            value += "_i64"                     # 64 бита: иначе 20! переполнит Int32
        return [self.L(d, f"{s[1]} = {value}")]

    def s_input(self, s, env, d):
        name, typ, prompt = s[1], s[2], self.str_lit(s[3])
        self.use("ask")
        env.types[name] = typ
        value = {"int": f"ask({prompt}).strip.to_i", "float": f'ask({prompt}).strip.tr(",", ".").to_f'}.get(typ, f"ask({prompt})")
        return [self.L(d, f"{name} = {value}")]

    HELPERS = {"ask": """def ask(prompt)
  print prompt
  STDOUT.flush
  gets.to_s.chomp
end"""}

    def program(self):
        funcs = []
        for f in self.prog["funcs"]:
            name, params, ret, body = f[1:]
            lines = self.block(body, Env({p: t for p, t in params}), 1)
            if lines and lines[-1].startswith(self.ind + "return "):
                lines[-1] = self.ind + lines[-1][len(self.ind) + 7:]
            args = ", ".join(f"{p} : {self.CT[t]}" for p, t in params)
            funcs.append("\n".join([f"def {self.fname(name)}({args}) : {self.CT[ret]}"] + lines + ["end"]))
        main = self.block(self.prog["main"], Env({}), 0)
        helpers = [self.HELPERS[h] for h in self.helpers]
        return "\n\n".join(helpers + funcs + ["\n".join(main)])


# ====================================================================== API
def _subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _subclasses(sub)


LANGS = {}       # ключ языка → переводчик (заполняется в конце файла)

# Как узнать язык в просьбе (с падежами: «на питоне», «на расте», «на си шарпе») и как запустить программу.
# Порядок важен: C++ и C# раньше C, TypeScript раньше JavaScript, JavaScript раньше Java.
LANG_INFO = [
    ("cpp", r"c\+\+|с\+\+|\bcpp\b|си\s*плюс\s*плюс\w*|\bплюс(?:ах|ы)\b", "g++ main.cpp -o main && ./main"),
    ("csharp", r"c#|с#|\bc\s*sharp\b|csharp|си\s*шарп\w*|\bшарп\w*", "dotnet new console, вставьте код в Program.cs и dotnet run"),
    ("typescript", r"typescript|тайпскрипт\w*|\bts\b", "npx tsx main.ts (или tsc main.ts && node main.js)"),
    ("javascript", r"javascript|джаваскрипт\w*|яваскрипт\w*|\bjs\b|node\.?js|\bна\s+ноде\b", "node main.js — или прямо здесь, кнопкой «Запустить»"),
    ("java", r"\bjava\b|\bджав[аеуы]\b", "java Main.java"),
    ("kotlin", r"kotlin|котлин\w*", "kotlinc Main.kt -include-runtime -d main.jar && java -jar main.jar"),
    ("python", r"python|питон\w*|пайтон\w*|\bpy\b", "python main.py — или прямо здесь, кнопкой «Запустить»"),
    ("go", r"golang|голанг\w*|\bна\s+go\b|\bязыке?\s+go\b|\bgo\s+lang\b", "go run main.go"),
    ("rust", r"\brust\b|\bраст(?:е|а|у|ом)?\b", "rustc main.rs && ./main"),
    ("swift", r"\bswift\b|свифт\w*", "swift main.swift"),
    ("php", r"\bphp\b|\bпхп\b", "php main.php"),
    ("ruby", r"\bruby\b|\bруби\b", "ruby main.rb"),
    ("lua", r"\blua\b|\bлуа\b", "lua main.lua"),
    ("dart", r"\bdart\b|\bдарт(?:е|а|у)?\b", "dart run main.dart"),
    ("pascal", r"pascal|паскал\w*|delphi|делфи|дельфи|lazarus|лазарус\w*", "fpc main.pas && ./main (или откройте в Lazarus / PascalABC.NET)"),
    ("vbnet", r"visual\s*basic|vb\.?net|\bvb\b|вижуал\s*бейсик\w*|бейсик\w*|\bbasic\b", "dotnet new console -lang VB, вставьте код в Program.vb и dotnet run"),
    ("powershell", r"powershell|пауэр\s*шелл\w*|пов[еэ]р\s*шелл\w*|\bps1\b", "pwsh main.ps1"),
    ("bash", r"\bbash\b|\bбаш[еу]?\b|\bshell\b|\bшелл\w*|\bsh\b", "bash main.sh"),
    ("perl", r"\bperl\b|\bперл\w*", "perl main.pl"),
    ("r", r"\b(?:на|языке?|в)\s+r\b|\brscript\b|\brstudio\b|\bязык\w*\s+эр\b", "Rscript main.R (или откройте в RStudio)"),
    ("julia", r"\bjulia\b|\bджули[ия]\b", "julia main.jl"),
    ("scala", r"\bscala\b|\b(?:на|языке?)\s+скал[аеу]\b", "scala Main.scala"),
    ("groovy", r"groovy|груви", "groovy main.groovy"),
    ("fortran", r"fortran|фортран\w*", "gfortran main.f90 -o main && ./main"),
    ("nim", r"\bnim\b|\b(?:на|языке?)\s+ним[еу]?\b", "nim c -r main.nim"),
    ("crystal", r"\bcrystal\b|\b(?:на|языке?)\s+кристал\w*", "crystal run main.cr"),
    ("c", r"\b(?:на|языке?)\s+(?:c|си)\b(?![+#])|\bansi\s+c\b|\bc99\b|\bc11\b", "gcc main.c -o main && ./main"),
]
RUN_HINT = {k: run for k, _, run in LANG_INFO}
_LANG_RES = [(k, re.compile(p, re.I)) for k, p, _ in LANG_INFO]


def find_lang(text):
    """Язык программирования из просьбы: «fizzbuzz на расте» → "rust"."""
    low = (text or "").lower().replace("ё", "е")
    for key, rx in _LANG_RES:
        if rx.search(low):
            return key
    return None


_TASK_RES = {k: re.compile(TASKS[k]["words"], re.I) for k in ORDER}


def find_task(text):
    """Какую классическую задачу просят: «посчитай сумму двух чисел» → "sum"."""
    low = (text or "").lower().replace("ё", "е")
    for key in ORDER:
        if _TASK_RES[key].search(low):
            return key
    return None


def program(task, lang):
    """Программа задачи на языке: {"code", "lang", "filename", "title", "about"}."""
    t = TASKS[task]
    em = LANGS[lang]({"main": t["main"], "funcs": t["funcs"]})
    return {"code": em.render(), "lang": lang, "filename": em.file or f"main.{em.ext}", "title": t["title"],
            "about": f"**{t['title']}** на {em.name} — {t['about']}\n\nКак запустить: `{RUN_HINT[lang]}`",
            "task": task}


def generate(text, lang=None):
    """Программа по просьбе на нужном языке или None (задача не из списка или язык неизвестен)."""
    lang = find_lang(text) or lang
    task = find_task(text)
    if not task or lang not in LANGS:
        return None
    return program(task, lang)


def names():
    return [LANGS[k].name for k, _, _ in LANG_INFO if k in LANGS]


COMMENT = {"python": "#", "ruby": "#", "perl": "#", "r": "#", "julia": "#", "nim": "#", "crystal": "#", "bash": "#",
           "powershell": "#", "lua": "--", "vbnet": "'", "fortran": "!"}


def skeleton(task_text, lang):
    """Рабочая заготовка под любую задачу на языке: запускается и показывает, куда писать логику."""
    em = LANGS[lang]({"main": [Print("Заготовка Rai Code: " + task_text)], "funcs": []})
    code = em.render()
    c = COMMENT.get(lang, "//")
    note = f"{c} {task_text}\n{c} TODO: здесь логика задачи — напишите в Rai Code, что добавить, и Rai допишет\n\n"
    for head in ("<?php\n\n", "#!/usr/bin/env bash\n\n"):
        if code.startswith(head):
            return {"code": head + note + code[len(head):], "filename": em.file or f"main.{em.ext}", "lang": lang}
    return {"code": note + code, "filename": em.file or f"main.{em.ext}", "lang": lang}


LANGS.update({c.key: c for c in _subclasses(Emitter) if c.key})
