"""ИИ Rai для кода: проверка, исправление, объяснение, комментарии и генерация программ.

Всё своё, без внешних сервисов. Python разбирается настоящим разбором (модуль ast),
остальные языки — собственным лексером (скобки, строки, комментарии) и правилами.
"""

import ast
import builtins
import difflib
import json
import re
from html.parser import HTMLParser

import codelib
import moderation
import webgen

LANG_NAMES = {
    "python": "Python", "javascript": "JavaScript", "html": "HTML", "css": "CSS", "php": "PHP", "json": "JSON",
    "cpp": "C++", "c": "C", "java": "Java", "csharp": "C#", "go": "Go", "rust": "Rust", "sql": "SQL",
    "bash": "Bash", "typescript": "TypeScript", "kotlin": "Kotlin", "text": "текст",
}
EXTENSIONS = {
    "py": "python", "js": "javascript", "mjs": "javascript", "ts": "typescript", "html": "html", "htm": "html",
    "css": "css", "php": "php", "json": "json", "cpp": "cpp", "cc": "cpp", "hpp": "cpp", "c": "c", "h": "c",
    "java": "java", "cs": "csharp", "go": "go", "rs": "rust", "sql": "sql", "sh": "bash", "kt": "kotlin",
}


EXT_OF = {"python": "py", "javascript": "js", "html": "html", "css": "css", "php": "php", "json": "json", "cpp": "cpp",
          "c": "c", "java": "java", "csharp": "cs", "go": "go", "rust": "rs", "sql": "sql", "bash": "sh",
          "typescript": "ts", "kotlin": "kt", "text": "txt"}


def lang_from_filename(name):
    ext = (name or "").rsplit(".", 1)[-1].lower() if "." in (name or "") else ""
    return EXTENSIONS.get(ext, "text")


def detect_lang(code, hint=None):
    """Определить язык кода по подсказке и по самому тексту."""
    if hint and hint in LANG_NAMES and hint != "text":
        return hint
    c = code or ""
    if re.search(r"<\?php", c):
        return "php"
    if re.search(r"<!DOCTYPE html|<html|<body|<div[\s>]|<p>|<h1", c, re.I):
        return "html"
    if re.search(r"#include\s*<", c):
        return "cpp" if re.search(r"std::|cout|iostream|namespace", c) else "c"
    if re.search(r"public\s+static\s+void\s+main|System\.out\.print", c):
        return "java"
    if re.search(r"Console\.Write|using System;", c):
        return "csharp"
    if re.search(r"^\s*package main|fmt\.Print", c, re.M):
        return "go"
    if re.search(r"fn main\(\)|println!\(", c):
        return "rust"
    if re.search(r"\b(const|let|var)\s+\w+\s*=|console\.log|function\s+\w*\s*\(|=>|document\.", c):
        return "javascript"
    if re.search(r"^\s*(def |class |import |from \w+ import |print\(|if __name__)", c, re.M) or re.search(r":\s*$", c, re.M):
        return "python"
    s = c.strip()
    if s.startswith(("{", "[")):
        try:
            json.loads(s)
            return "json"
        except ValueError:
            pass
    if re.search(r"^\s*[.#]?[\w-]+\s*\{[^}]*:[^}]*\}", c, re.M):
        return "css"
    if re.search(r"^\s*(SELECT|INSERT|UPDATE|CREATE TABLE)\b", c, re.I | re.M):
        return "sql"
    return "python"


def issue(line, message, severity="warning", hint=None, col=None):
    return {"line": line, "col": col, "severity": severity, "message": message, "hint": hint}


# ================================================================== Python: проверка

SYNTAX_RU = [
    (r"expected ':'", "Не хватает двоеточия «:» в конце строки.", "После if, for, while, def, class, else, try пишется «:»."),
    (r"expected an indented block", "После строки с «:» нужен отступ (4 пробела).", "Сдвиньте строки блока вправо на 4 пробела."),
    (r"unexpected indent", "Лишний отступ в начале строки.", "Уберите пробелы в начале строки или выровняйте её с соседними."),
    (r"unindent does not match", "Отступ не совпадает с предыдущими строками.", "Используйте одинаковые отступы: 4 пробела на уровень."),
    (r"inconsistent use of tabs", "Смешаны табы и пробелы в отступах.", "Используйте только пробелы (кнопка «Исправить» заменит табы)."),
    (r"unterminated string|EOL while scanning", "Строка не закрыта кавычкой.", "Поставьте закрывающую кавычку того же вида, что и открывающая."),
    (r"unterminated triple-quoted", "Не закрыта строка в тройных кавычках.", "Добавьте \"\"\" в конце текста."),
    (r"'\(' was never closed", "Скобка «(» не закрыта.", "Добавьте «)» в конце выражения."),
    (r"'\[' was never closed", "Скобка «[» не закрыта.", "Добавьте «]»."),
    (r"'\{' was never closed", "Скобка «{» не закрыта.", "Добавьте «}»."),
    (r"unmatched '(.)'", "Лишняя закрывающая скобка.", "Проверьте, что скобки открываются и закрываются парами."),
    (r"closing parenthesis '(.)' does not match", "Закрывающая скобка не совпадает с открывающей.", "( ) [ ] { } должны быть парами."),
    (r"Missing parentheses in call to 'print'", "В Python 3 print пишется со скобками.", "Напишите print(...)"),
    (r"Perhaps you forgot a comma", "Похоже, пропущена запятая.", "Между элементами списка или аргументами нужна запятая."),
    (r"cannot assign to (function call|literal|expression)", "Сюда нельзя присвоить значение.", "Слева от «=» должно быть имя переменной. Для сравнения используйте «==»."),
    (r"invalid syntax. Maybe you meant '==' or ':='", "Похоже, в условии написано «=» вместо «==».", "Для сравнения используйте «==»."),
    (r"'return' outside function", "return можно писать только внутри функции.", None),
    (r"'break' outside loop", "break можно писать только внутри цикла.", None),
    (r"'continue' .*not properly in loop", "continue можно писать только внутри цикла.", None),
    (r"invalid character", "В коде есть недопустимый символ (например, русская буква или «умная» кавычка).", "Замените «» и “” на обычные кавычки \" или '."),
    (r"invalid decimal literal", "Число написано с ошибкой (например, имя переменной начинается с цифры).", "Имена переменных не могут начинаться с цифры."),
    (r"f-string", "Ошибка внутри f-строки.", "Проверьте фигурные скобки {} в f\"...\"."),
    (r"expected 'except' or 'finally' block", "После try нужен блок except или finally.", None),
    (r"invalid syntax", "Ошибка синтаксиса.", "Проверьте эту строку: скобки, кавычки, двоеточия, запятые."),
]

KNOWN_CALLS = {
    "print": "выводит на экран", "input": "спрашивает у пользователя текст", "int": "превращает в целое число",
    "float": "превращает в дробное число", "str": "превращает в строку", "len": "считает длину",
    "range": "перебирает числа", "open": "открывает файл", "sum": "складывает элементы", "sorted": "сортирует",
    "max": "находит максимум", "min": "находит минимум", "round": "округляет", "abs": "берёт модуль числа",
    "list": "делает список", "dict": "делает словарь", "set": "делает множество", "enumerate": "нумерует элементы",
    "zip": "склеивает последовательности попарно", "map": "применяет функцию к каждому элементу",
    "filter": "отбирает элементы", "isinstance": "проверяет тип", "reversed": "переворачивает",
    "random.randint": "выбирает случайное целое число", "random.choice": "выбирает случайный элемент",
    "time.sleep": "делает паузу", "json.loads": "разбирает JSON", "json.dumps": "превращает в JSON",
}

SHADOWED = {"list", "dict", "str", "int", "float", "input", "print", "id", "type", "sum", "max", "min", "len",
            "sorted", "set", "tuple", "range", "open", "map", "filter", "next", "iter", "object", "format", "all", "any"}


class _Names(ast.NodeVisitor):
    """Собрать все определённые и использованные имена (приближённо, без областей видимости)."""

    def __init__(self):
        self.defined = set()
        self.loaded = []   # (имя, строка)
        self.imports = {}  # имя -> строка
        self.loaded_set = set()

    def _target(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                self.defined.add(n.id)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.loaded.append((node.id, node.lineno))
            self.loaded_set.add(node.id)
        else:
            self.defined.add(node.id)

    def visit_Attribute(self, node):
        self.generic_visit(node)

    def visit_Import(self, node):
        for a in node.names:
            name = (a.asname or a.name).split(".")[0]
            self.defined.add(name)
            self.imports[name] = node.lineno

    def visit_ImportFrom(self, node):
        for a in node.names:
            if a.name == "*":
                self.defined.add("*")
                continue
            name = a.asname or a.name
            self.defined.add(name)
            self.imports[name] = node.lineno

    def visit_FunctionDef(self, node):
        self.defined.add(node.name)
        for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
            self.defined.add(a.arg)
        if node.args.vararg:
            self.defined.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.defined.add(node.args.kwarg.arg)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        for a in node.args.args:
            self.defined.add(a.arg)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.defined.add(node.name)
        self.generic_visit(node)

    def visit_Global(self, node):
        self.defined.update(node.names)

    visit_Nonlocal = visit_Global

    def visit_MatchAs(self, node):
        if node.name:
            self.defined.add(node.name)
        self.generic_visit(node)


def _syntax_issue(err):
    msg = str(err.msg or "")
    for pattern, ru, hint in SYNTAX_RU:
        if re.search(pattern, msg):
            return issue(err.lineno or 1, ru, "error", hint, err.offset)
    return issue(err.lineno or 1, "Ошибка в коде: " + msg, "error", None, err.offset)


def _is_input_call(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input"


def check_python(code, deep=True):
    """Проверить код на Python. Возвращает список замечаний (ошибки, предупреждения, советы)."""
    issues = []
    lines = (code or "").split("\n")
    for i, line in enumerate(lines, 1):
        indent = re.match(r"[ \t]*", line).group(0)
        if " " in indent and "\t" in indent:
            issues.append(issue(i, "В отступе смешаны пробелы и табы.", "warning", "Используйте только пробелы."))
    try:
        tree = ast.parse(code or "")
    except SyntaxError as e:
        issues.append(_syntax_issue(e))
        return issues
    if not deep:
        return issues

    names = _Names()
    names.visit(tree)
    known = names.defined | set(dir(builtins)) | {"__name__", "__file__", "__doc__"}
    if "*" not in names.defined:
        reported = set()
        for name, line in names.loaded:
            if name not in known and name not in reported:
                reported.add(name)
                close = difflib.get_close_matches(name, list(known - set(dir(builtins))) + list(SHADOWED), n=1, cutoff=0.75)
                hint = f"Возможно, вы имели в виду «{close[0]}»." if close else "Объявите переменную или импортируйте модуль до использования."
                issues.append(issue(line, f"Имя «{name}» нигде не определено — будет ошибка NameError.", "error", hint))
    for name, line in names.imports.items():
        if name not in names.loaded_set and not re.search(r"\b" + re.escape(name) + r"\.", code):
            issues.append(issue(line, f"Модуль или имя «{name}» импортировано, но не используется.", "info", "Уберите лишний import."))

    input_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_input_call(node.value):
            input_vars.update(t.id for t in node.targets if isinstance(t, ast.Name))
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 1)
        if isinstance(node, ast.Compare):
            for op, right in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, ast.Constant) and right.value is None:
                    issues.append(issue(line, "Сравнение с None через «==».", "info", "Пишите «is None» / «is not None»."))
                if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(right, ast.Constant) and isinstance(right.value, (int, str)) and not isinstance(right.value, bool):
                    issues.append(issue(line, "«is» сравнивает объекты, а не значения.", "warning", "Для чисел и строк используйте «==»."))
            parts = [node.left] + list(node.comparators)
            if any(isinstance(p, ast.Name) and p.id in input_vars for p in parts) and \
                    any(isinstance(p, ast.Constant) and isinstance(p.value, (int, float)) and not isinstance(p.value, bool) for p in parts):
                issues.append(issue(line, "input() возвращает строку, а она сравнивается с числом.", "error",
                                    "Оберните ввод в int(): x = int(input(...))."))
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv, ast.Add)):
            sides = (node.left, node.right)
            if any(isinstance(p, ast.Name) and p.id in input_vars for p in sides) and \
                    any(isinstance(p, ast.Constant) and isinstance(p.value, (int, float)) and not isinstance(p.value, bool) for p in sides):
                issues.append(issue(line, "С результатом input() считают как с числом, а это строка.", "error",
                                    "Преобразуйте: int(input(...)) или float(input(...))."))
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and isinstance(node.right, ast.Constant) and node.right.value == 0:
                issues.append(issue(line, "Деление на ноль.", "error", "Проверьте делитель."))
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(issue(line, "Голый «except:» ловит вообще все ошибки, даже Ctrl+C.", "warning", "Пишите «except Exception:» или конкретную ошибку."))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.args.defaults + node.args.kw_defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    issues.append(issue(line, f"Изменяемое значение по умолчанию в функции «{node.name}».", "warning",
                                        "Пишите «=None» и создавайте список/словарь внутри функции."))
            if node.name in SHADOWED:
                issues.append(issue(line, f"Функция «{node.name}» перекрывает встроенную функцию Python.", "warning", "Выберите другое имя."))
            _unused_locals(node, issues)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name) and t.id in SHADOWED:
                    issues.append(issue(line, f"Переменная «{t.id}» перекрывает встроенную функцию {t.id}().", "warning",
                                        f"Назовите иначе, например «my_{t.id}»."))
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            inner = list(ast.walk(node))
            if not any(isinstance(n, (ast.Break, ast.Return, ast.Raise)) for n in inner) and \
                    not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("exit", "quit") for n in inner):
                issues.append(issue(line, "Бесконечный цикл while True без break.", "warning", "Добавьте условие выхода: break."))
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and \
                node.iter.func.id == "range" and len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Call) and \
                isinstance(node.iter.args[0].func, ast.Name) and node.iter.args[0].func.id == "len":
            issues.append(issue(line, "range(len(...)) можно заменить на enumerate().", "info", "for i, item in enumerate(items):"))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"\{[A-Za-z_]\w*\}", node.value):
            used = re.findall(r"\{([A-Za-z_]\w*)\}", node.value)
            if any(u in names.defined for u in used) and not _inside_fstring(tree, node) and ".format" not in code:
                issues.append(issue(line, "В строке есть {переменная}, но строка не f-строка.", "info", "Добавьте f перед кавычкой: f\"...\"."))
        for body_name in ("body", "orelse", "finalbody"):
            body = getattr(node, body_name, None)
            if isinstance(body, list):
                for i, stmt in enumerate(body[:-1]):
                    if isinstance(stmt, (ast.Return, ast.Break, ast.Continue, ast.Raise)):
                        issues.append(issue(body[i + 1].lineno, "Этот код никогда не выполнится: выше стоит "
                                            + type(stmt).__name__.lower() + ".", "warning", "Удалите его или перенесите выше."))
                        break
    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append(issue(i, f"Длинная строка ({len(line)} символов).", "info", "Разбейте её на несколько строк."))
    return _dedupe(issues)


def _inside_fstring(tree, target):
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr) and any(v is target for v in ast.walk(node)):
            return True
    return False


def _unused_locals(func, issues):
    assigned, loaded = {}, set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                assigned.setdefault(node.id, node.lineno)
            else:
                loaded.add(node.id)
    globals_ = {n for node in ast.walk(func) if isinstance(node, (ast.Global, ast.Nonlocal)) for n in node.names}
    for name, line in assigned.items():
        if name not in loaded and not name.startswith("_") and name not in globals_:
            issues.append(issue(line, f"Переменная «{name}» в функции «{func.name}» получает значение, но не используется.",
                                "info", "Уберите её или используйте."))


def _dedupe(items):
    seen, out = set(), []
    for it in items:
        key = (it["line"], it["message"])
        if key not in seen:
            seen.add(key)
            out.append(it)
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(out, key=lambda x: (order[x["severity"]], x["line"] or 0))


# ================================================================== другие языки: проверка

PAIRS = {")": "(", "]": "[", "}": "{"}


def check_brackets(code, lang):
    """Скобки и кавычки с учётом строк и комментариев (JS, PHP, C, C++, Java, C#, Go, Rust, CSS, TS…)."""
    issues, stack = [], []
    i, line, n = 0, 1, len(code)
    line_comment = "#" if lang in ("bash", "python") else "//"
    while i < n:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if ch == "\n":
            line += 1
        elif code.startswith(line_comment, i) or (lang == "php" and ch == "#"):
            while i < n and code[i] != "\n":
                i += 1
            continue
        elif ch == "/" and nxt == "*":
            end = code.find("*/", i + 2)
            if end == -1:
                issues.append(issue(line, "Комментарий /* не закрыт.", "error", "Добавьте */."))
                break
            line += code.count("\n", i, end)
            i = end + 2
            continue
        elif ch in "\"'`" and lang != "css" or (lang == "css" and ch in "\"'"):
            quote, start_line = ch, line
            i += 1
            while i < n and code[i] != quote:
                if code[i] == "\\":
                    i += 1
                elif code[i] == "\n":
                    if quote != "`":
                        issues.append(issue(start_line, f"Строка с кавычкой {quote} не закрыта.", "error", f"Добавьте закрывающую {quote}."))
                        break
                    line += 1
                i += 1
            if i >= n:
                issues.append(issue(start_line, f"Строка с кавычкой {quote} не закрыта до конца файла.", "error", None))
        elif ch in "([{":
            stack.append((ch, line))
        elif ch in ")]}":
            if not stack:
                issues.append(issue(line, f"Лишняя закрывающая скобка «{ch}».", "error", "Уберите её или добавьте открывающую."))
            elif stack[-1][0] != PAIRS[ch]:
                issues.append(issue(line, f"Скобка «{ch}» закрывает «{stack[-1][0]}» из строки {stack[-1][1]}.", "error",
                                    "Проверьте порядок скобок."))
                stack.pop()
            else:
                stack.pop()
        i += 1
    for ch, ln in stack[-3:]:
        issues.append(issue(ln, f"Скобка «{ch}» не закрыта.", "error", "Добавьте закрывающую скобку."))
    return issues


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "!doctype"}
OPTIONAL_CLOSE = {"p", "li", "td", "th", "tr", "option", "dt", "dd", "thead", "tbody", "html", "head", "body"}


class _HtmlCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.issues = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "img" and not any(k == "alt" for k, _ in attrs):
            self.issues.append(issue(self.getpos()[0], "У картинки <img> нет alt.", "info", "Добавьте alt=\"описание\" — это важно для доступности."))
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                for t, ln in self.stack[k + 1:]:
                    if t not in OPTIONAL_CLOSE:
                        self.issues.append(issue(ln, f"Тег <{t}> не закрыт.", "error", f"Добавьте </{t}> перед </{tag}>."))
                del self.stack[k:]
                return
        self.issues.append(issue(self.getpos()[0], f"Лишний закрывающий тег </{tag}>.", "error", "Уберите его или добавьте открывающий."))


def check_html(code):
    p = _HtmlCheck()
    try:
        p.feed(code or "")
        p.close()
    except Exception as e:  # noqa: BLE001 — сломанный HTML не должен ронять проверку
        return [issue(1, f"HTML не удалось разобрать: {e}", "error")]
    for t, ln in p.stack:
        if t not in OPTIONAL_CLOSE:
            p.issues.append(issue(ln, f"Тег <{t}> не закрыт.", "error", f"Добавьте </{t}>."))
    if "<!doctype" not in (code or "").lower() and "<html" in (code or "").lower():
        p.issues.append(issue(1, "Нет строки <!DOCTYPE html>.", "info", "Добавьте её в самое начало файла."))
    return p.issues


def check_code(code, lang, deep=True):
    lang = detect_lang(code, lang)
    if lang == "python":
        return lang, check_python(code, deep)
    if lang == "json":
        try:
            json.loads(code)
            return lang, []
        except json.JSONDecodeError as e:
            return lang, [issue(e.lineno, "Ошибка в JSON: " + {
                "Expecting ',' delimiter": "пропущена запятая", "Expecting property name enclosed in double quotes":
                "ключ должен быть в двойных кавычках (и без запятой после последнего элемента)",
                "Expecting value": "ожидалось значение", "Extra data": "лишний текст после JSON"}.get(e.msg, e.msg), "error", None, e.colno)]
    if lang == "html":
        issues = check_html(code)
        for m in re.finditer(r"<script[^>]*>(.*?)</script>", code, re.S | re.I):
            offset = code.count("\n", 0, m.start(1))
            for it in check_brackets(m.group(1), "javascript"):
                it["line"] += offset
                issues.append(it)
        return lang, _dedupe(issues)
    issues = check_brackets(code, lang)
    if lang in ("javascript", "typescript"):
        for i, line in enumerate(code.split("\n"), 1):
            clean = re.sub(r"(\"[^\"]*\"|'[^']*'|`[^`]*`|//.*)", "", line)
            if re.search(r"[^=!<>]==[^=]", clean):
                issues.append(issue(i, "«==» сравнивает с приведением типов.", "info", "Используйте «===»."))
            if re.search(r"\bvar\s", clean):
                issues.append(issue(i, "«var» устарел.", "info", "Используйте let или const."))
    if lang == "php" and "<?php" not in code:
        issues.append(issue(1, "Нет открывающего тега <?php.", "warning", "Начните файл с <?php"))
    return lang, _dedupe(issues)


# ================================================================== Python: исправление

BLOCK_START = re.compile(r"^(\s*)(if|elif|else|for|while|def|class|try|except|finally|with|async def|async for|async with)\b(.*)$")


def fix_python(code):
    """Безопасно исправить частые ошибки. Возвращает (новый код, список изменений)."""
    changes = []
    lines = (code or "").replace("\r\n", "\n").split("\n")
    out = []
    depth = 0  # внутри скобок строки продолжаются — двоеточие не ставим
    for i, line in enumerate(lines, 1):
        new = line
        m = re.match(r"^[ \t]+", new)
        if m and "\t" in m.group(0):
            new = m.group(0).replace("\t", "    ") + new[m.end():]
            changes.append(f"строка {i}: табы в отступе заменены на пробелы")
        if new != new.rstrip():
            new = new.rstrip()
        stripped = new.strip()
        code_part = re.sub(r"(\"[^\"]*\"|'[^']*')", "", stripped.split("#")[0]).rstrip()
        if depth == 0:
            pm = re.match(r"^(\s*)print\s+(?![\s(=.])(.+)$", new)
            if pm and not stripped.startswith("print("):
                new = f"{pm.group(1)}print({pm.group(2).rstrip()})"
                changes.append(f"строка {i}: print без скобок → print(...)")
            bm = BLOCK_START.match(new)
            if bm and code_part and not code_part.endswith((":", "\\", ",", "(", "[", "{")) and \
                    not re.search(r"\blambda\b", code_part) and not re.match(r"^\s*(else|try|finally)\s*\w", new):
                word = bm.group(2)
                if word in ("else", "try", "finally") and code_part.strip() != word:
                    pass
                else:
                    comment = ""
                    if "#" in new and not re.search(r"[\"'].*#.*[\"']", new):
                        new, comment = new.split("#", 1)[0].rstrip(), "  #" + new.split("#", 1)[1]
                    new = new + ":" + comment
                    changes.append(f"строка {i}: добавлено двоеточие после «{word}»")
        eq = re.sub(r"(\S)\s*==\s*None\b", r"\1 is None", new)
        eq = re.sub(r"(\S)\s*!=\s*None\b", r"\1 is not None", eq)
        if eq != new:
            new = eq
            changes.append(f"строка {i}: «== None» → «is None»")
        if re.match(r"^\s*except\s*:\s*(#.*)?$", new):
            new = re.sub(r"except\s*:", "except Exception:", new, count=1)
            changes.append(f"строка {i}: «except:» → «except Exception:»")
        depth += code_part.count("(") + code_part.count("[") + code_part.count("{")
        depth -= code_part.count(")") + code_part.count("]") + code_part.count("}")
        depth = max(depth, 0)
        out.append(new)
    fixed = "\n".join(out)
    if fixed.strip() and not fixed.endswith("\n"):
        fixed += "\n"
    # одна незакрытая скобка в конце строки — частая ошибка новичков
    for _ in range(3):
        try:
            ast.parse(fixed)
            break
        except SyntaxError as e:
            msg = e.msg or ""
            m = re.search(r"'([(\[{])' was never closed", msg)
            if not m or not e.lineno:
                break
            ls = fixed.split("\n")
            idx = e.lineno - 1
            closer = {"(": ")", "[": "]", "{": "}"}[m.group(1)]
            ls[idx] = ls[idx].rstrip() + closer
            fixed = "\n".join(ls)
            changes.append(f"строка {e.lineno}: закрыта скобка «{m.group(1)}»")
    return fixed, changes


# ================================================================== Python: объяснение

def _src(node):
    try:
        text = ast.unparse(node)
    except Exception:  # noqa: BLE001
        return "…"
    return text if len(text) <= 60 else text[:57] + "…"


def _call_name(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else _src(f.value)
        return f"{base}.{f.attr}"
    return _src(f)


def _describe_value(v):
    if isinstance(v, ast.Constant):
        if isinstance(v.value, str):
            return f"строку «{v.value[:40]}»"
        if isinstance(v.value, bool):
            return "True (истина)" if v.value else "False (ложь)"
        if v.value is None:
            return "None (пусто)"
        return f"число {v.value}"
    if isinstance(v, ast.List):
        return f"список из {len(v.elts)} элементов" if v.elts else "пустой список"
    if isinstance(v, ast.Dict):
        return f"словарь из {len(v.keys)} пар" if v.keys else "пустой словарь"
    if isinstance(v, ast.Tuple):
        return f"кортеж из {len(v.elts)} значений"
    if isinstance(v, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        return f"список, собранный в одну строку ({_src(v)})"
    if isinstance(v, ast.DictComp):
        return "словарь, собранный в одну строку"
    if isinstance(v, ast.Call):
        name = _call_name(v)
        what = KNOWN_CALLS.get(name)
        if name == "int" and v.args and isinstance(v.args[0], ast.Call) and _call_name(v.args[0]) == "input":
            return "число, которое ввёл пользователь"
        return f"результат {name}(…)" + (f" — {what}" if what else "")
    if isinstance(v, ast.BinOp):
        return f"результат выражения {_src(v)}"
    if isinstance(v, ast.Lambda):
        return "короткую функцию lambda"
    return _src(v)


def _describe(node):
    if isinstance(node, ast.Import):
        return "подключает модуль " + ", ".join(a.name for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return f"берёт из модуля {node.module} " + ", ".join(a.name for a in node.names)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = ", ".join(a.arg for a in node.args.args)
        doc = ast.get_docstring(node)
        ret = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))
        text = f"объявляет функцию {node.name}({args})" + (" — возвращает результат" if ret else "")
        return text + (f". Описание: {doc.splitlines()[0].rstrip('.')}" if doc else "")
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(_src(b) for b in node.bases)
        methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return f"объявляет класс {node.name}" + (f" (наследует {bases})" if bases else "") + \
            (f" с методами: {', '.join(methods)}" if methods else "")
    if isinstance(node, ast.Assign):
        targets = ", ".join(_src(t) for t in node.targets)
        return f"сохраняет в {targets} {_describe_value(node.value)}"
    if isinstance(node, ast.AugAssign):
        ops = {ast.Add: "увеличивает", ast.Sub: "уменьшает", ast.Mult: "умножает", ast.Div: "делит"}
        return f"{ops.get(type(node.op), 'изменяет')} {_src(node.target)} на {_src(node.value)}"
    if isinstance(node, ast.AnnAssign):
        return f"объявляет {_src(node.target)} типа {_src(node.annotation)}"
    if isinstance(node, ast.For):
        it = node.iter
        if isinstance(it, ast.Call) and _call_name(it) == "range":
            a = [_src(x) for x in it.args]
            if len(a) == 1:
                span = f"от 0 до {a[0]} (не включая)"
            elif len(a) == 2:
                span = f"от {a[0]} до {a[1]} (не включая)"
            elif len(a) == 3:
                span = f"от {a[0]} до {a[1]} с шагом {a[2]}"
            else:
                span = ""
            return f"цикл: {_src(node.target)} перебирает числа {span}"
        return f"цикл: для каждого {_src(node.target)} из {_src(it)}"
    if isinstance(node, ast.While):
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            return "бесконечный цикл (выход через break)"
        return f"цикл, пока верно {_src(node.test)}"
    if isinstance(node, ast.If):
        text = f"проверяет условие {_src(node.test)}"
        if node.orelse:
            text += ", иначе выполняет другую ветку"
        return text
    if isinstance(node, ast.Try):
        caught = ", ".join(_src(h.type) if h.type else "любую ошибку" for h in node.handlers)
        return f"пробует выполнить код и перехватывает {caught or 'ошибки'}"
    if isinstance(node, ast.With):
        items = node.items[0]
        if isinstance(items.context_expr, ast.Call) and _call_name(items.context_expr) == "open":
            mode = next((_src(a) for a in items.context_expr.args[1:2]), "'r'")
            action = "для записи" if "w" in mode or "a" in mode else "для чтения"
            return f"открывает файл {_src(items.context_expr.args[0]) if items.context_expr.args else ''} {action} (закроется сам)"
        return f"работает с {_src(items.context_expr)} и сам всё закрывает"
    if isinstance(node, ast.Return):
        return f"возвращает {_src(node.value)}" if node.value else "выходит из функции"
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        name = _call_name(node.value)
        if name == "print":
            return "выводит на экран " + (", ".join(_src(a) for a in node.value.args) or "пустую строку")
        what = KNOWN_CALLS.get(name)
        return f"вызывает {name}(…)" + (f" — {what}" if what else "")
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return "строка-описание (docstring)"
    if isinstance(node, ast.Break):
        return "прерывает цикл"
    if isinstance(node, ast.Continue):
        return "переходит к следующему шагу цикла"
    if isinstance(node, ast.Raise):
        return f"вызывает ошибку {_src(node.exc)}" if node.exc else "пробрасывает ошибку дальше"
    if isinstance(node, ast.Pass):
        return "ничего не делает (заглушка)"
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        return "использует внешнюю переменную " + ", ".join(node.names)
    if isinstance(node, ast.Delete):
        return "удаляет " + ", ".join(_src(t) for t in node.targets)
    if isinstance(node, ast.Assert):
        return f"проверяет, что {_src(node.test)}"
    return _src(node)


def _walk_statements(body, depth=0, max_depth=2):
    for node in body:
        yield node, depth
        if depth < max_depth:
            for field in ("body", "orelse", "handlers", "finalbody"):
                child = getattr(node, field, None)
                if isinstance(child, list) and child and not isinstance(node, ast.ClassDef) or \
                        (isinstance(node, ast.ClassDef) and field == "body"):
                    if field == "handlers":
                        for h in child:
                            yield from _walk_statements(h.body, depth + 1, max_depth)
                    elif isinstance(child, list):
                        yield from _walk_statements(child, depth + 1, max_depth)


def explain_python(code):
    try:
        tree = ast.parse(code or "")
    except SyntaxError as e:
        it = _syntax_issue(e)
        return f"Код не получается разобрать: строка {it['line']} — {it['message']} {it['hint'] or ''}\n\nСначала исправьте ошибку (кнопка «Исправить»)."
    lines = []
    for node, depth in _walk_statements(tree.body):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and depth > 0:
            continue
        pad = "  " * depth
        lines.append(f"{pad}- **строка {node.lineno}:** {_describe(node)}.")
    funcs = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    loops = sum(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree))
    stats = [f"строк: {len(code.strip().splitlines())}"]
    if funcs:
        stats.append(f"функций: {funcs}")
    if classes:
        stats.append(f"классов: {classes}")
    if loops:
        stats.append(f"циклов: {loops}")
    uses_input = any(isinstance(n, ast.Call) and _call_name(n) == "input" for n in ast.walk(tree))
    summary = "Программа спрашивает данные у пользователя." if uses_input else ""
    return "### Что делает этот код\n\n" + "\n".join(lines[:80]) + \
        ("\n\n*(показаны первые 80 шагов)*" if len(lines) > 80 else "") + \
        f"\n\n**Итого:** {', '.join(stats)}. {summary}".rstrip()


def comment_python(code):
    """Добавить комментарии на русском над строками кода (где их ещё нет)."""
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        return None
    lines = code.split("\n")
    notes = {}
    for node, _ in _walk_statements(tree.body, max_depth=3):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        notes.setdefault(node.lineno, _describe(node))
    out = []
    for i, line in enumerate(lines, 1):
        prev = out[-1].strip() if out else ""
        if i in notes and not prev.startswith("#") and line.strip():
            indent = re.match(r"\s*", line).group(0)
            note = notes[i]
            out.append(f"{indent}# {note[:1].upper()}{note[1:]}")
        out.append(line)
    return "\n".join(out)


def explain_generic(code, lang):
    """Объяснение для других языков: структура (функции, классы, циклы, условия)."""
    lines = (code or "").split("\n")
    found = []
    patterns = [
        (r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", "объявляет функцию {0}({1})"),
        (r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", "объявляет стрелочную функцию {0}({1})"),
        (r"^\s*(?:public|private|protected|static|\s)*function\s+(\w+)\s*\(([^)]*)\)", "объявляет функцию {0}({1})"),
        (r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+)*class\s+(\w+)", "объявляет класс {0}"),
        (r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*(.+?);?\s*$", "сохраняет в {0} значение {1}"),
        (r"^\s*\$(\w+)\s*=\s*(.+?);\s*$", "сохраняет в ${0} значение {1}"),
        (r"^\s*for\s*\((.+)\)", "цикл for ({0})"),
        (r"^\s*foreach\s*\((.+)\)", "перебирает элементы ({0})"),
        (r"^\s*while\s*\((.+)\)", "цикл, пока верно {0}"),
        (r"^\s*if\s*\((.+)\)", "проверяет условие {0}"),
        (r"^\s*}\s*else", "иначе — другая ветка"),
        (r"console\.log\((.+)\)", "выводит в консоль {0}"),
        (r"^\s*echo\s+(.+?);", "выводит на страницу {0}"),
        (r"document\.(?:getElementById|querySelector)\((.+?)\)", "находит элемент страницы {0}"),
        (r"addEventListener\(\s*['\"](\w+)['\"]", "реагирует на событие «{0}»"),
        (r"fetch\((.+?)[,)]", "делает запрос к серверу {0}"),
        (r"^\s*#include\s*<(.+)>", "подключает библиотеку {0}"),
        (r"^\s*import\s+(.+?);?$", "подключает {0}"),
        (r"^\s*return\s+(.+?);?$", "возвращает {0}"),
        (r"(?:System\.out\.println|cout\s*<<|printf|fmt\.Println|println!)\s*\(?(.+?)\)?;?\s*$", "выводит на экран {0}"),
    ]
    for i, line in enumerate(lines, 1):
        for pattern, text in patterns:
            m = re.search(pattern, line)
            if m:
                parts = [g[:50] for g in m.groups()]
                found.append(f"- **строка {i}:** {text.format(*parts)}.")
                break
    if lang == "html":
        tags = re.findall(r"<(h[1-6]|p|img|a|form|input|button|ul|ol|table|nav|header|footer|section|script|style)\b", code, re.I)
        counts = {}
        for t in tags:
            counts[t.lower()] = counts.get(t.lower(), 0) + 1
        names = {"h1": "главный заголовок", "p": "абзацы", "img": "картинки", "a": "ссылки", "form": "формы",
                 "input": "поля ввода", "button": "кнопки", "ul": "списки", "ol": "нумерованные списки",
                 "table": "таблицы", "nav": "меню", "header": "шапка", "footer": "подвал", "section": "разделы",
                 "script": "скрипты JavaScript", "style": "стили CSS"}
        parts = [f"{names.get(t, t)} ({c})" for t, c in counts.items()]
        title = re.search(r"<title>(.*?)</title>", code, re.I | re.S)
        head = f"Страница «{title.group(1).strip()}»" if title else "HTML-страница"
        return f"### Что в этой странице\n\n{head}. Состав: " + (", ".join(parts) if parts else "простая разметка") + "."
    if not found:
        return f"Это код на {LANG_NAMES.get(lang, lang)} ({len(lines)} строк). Подробное построчное объяснение я делаю для Python; " \
               "для этого языка показываю структуру, когда в коде есть функции, циклы и условия."
    return f"### Что делает этот код ({LANG_NAMES.get(lang, lang)})\n\n" + "\n".join(found[:60])


def explain(code, lang=None):
    lang = detect_lang(code, lang)
    return explain_python(code) if lang == "python" else explain_generic(code, lang)


# ================================================================== отчёты

SEVERITY = {"error": "ошибка", "warning": "предупреждение", "info": "совет"}


def report(issues, lang):
    if not issues:
        return f"Проверил код на {LANG_NAMES.get(lang, lang)}: **ошибок не нашёл**."
    errors = sum(1 for i in issues if i["severity"] == "error")
    warns = sum(1 for i in issues if i["severity"] == "warning")
    tips = sum(1 for i in issues if i["severity"] == "info")
    head = f"Проверил код на {LANG_NAMES.get(lang, lang)}: ошибок — **{errors}**, предупреждений — **{warns}**, советов — **{tips}**."
    rows = ["| Строка | Что не так | Как исправить |", "|---|---|---|"]
    for it in issues[:40]:
        mark = {"error": "**Ошибка.** ", "warning": "", "info": "*Совет.* "}[it["severity"]]
        rows.append(f"| {it['line'] or '—'} | {mark}{it['message'].replace('|', '/')} | {(it['hint'] or '').replace('|', '/')} |")
    return head + "\n\n" + "\n".join(rows)


# ================================================================== запросы в чате

_ACTIONS = [
    ("fix", r"исправ|почин|пофикс|fix\b"),
    ("comment", r"прокомментир|комментари|добавь коммент"),
    ("explain", r"объясн|что делает|как работает|разбери|поясни|расскажи.*код"),
    ("check", r"провер|найди ошиб|есть ли ошиб|почему не работает|ошибк|баг|debug|отлад|review|ревью"),
    ("generate", r"напиши|создай|сделай|сгенерир|придумай|нужен код|нужна программ|пример кода|покажи код|код для|программ[уа] для"),
]

_FENCE = re.compile(r"```(\w+)?\n?(.*?)```", re.S)


def extract_code(text):
    """Код из сообщения: в ```…``` или, если сообщение само похоже на код, всё целиком."""
    m = _FENCE.search(text or "")
    if m:
        return m.group(2).strip("\n"), (m.group(1) or "").lower() or None
    lines = [l for l in (text or "").split("\n") if l.strip()]
    codeish = [l for l in lines if re.search(r"[=(){};:<>\[\]]|^\s{2,}|^\s*(def|for|if|while|import|print|return|class|function|const|let|var)\b", l)]
    if len(lines) >= 2 and len(codeish) >= max(2, len(lines) * 0.6):
        first_code = next(i for i, l in enumerate(text.split("\n")) if l in codeish)
        return "\n".join(text.split("\n")[first_code:]), None
    return None, None


def wants(text, action):
    pattern = dict(_ACTIONS)[action]
    return bool(re.search(pattern, (text or "").lower()))


def action_of(text):
    low = (text or "").lower()
    for action, pattern in _ACTIONS:
        if re.search(pattern, low):
            return action
    return None


_STRONG_SITE = re.compile(r"сайт|лендинг|landing|визитк|портфолио|website|homepage")
_BUILD_VERB = re.compile(r"(?:^|\b)(?:напиши|написать|сделай|сделать|создай|создать|сгенерируй|запрограммируй|закодь|собери|"
                         r"нужен|нужна|нужно|хочу|разработай|сверстай|сверстать|make|create|build|write)\b")
_BUILD_NOUN = re.compile(r"сайт|лендинг|страниц|визитк|портфолио|приложени|игр[аушы]|программ|бот[аы]?\b|скрипт|\bкод\b|калькулятор|"
                         r"конвертер|часы|таймер|секундомер|галере|пианино|синтезатор|рисовалк|рисовани|функци|класс|парсер|сервер|"
                         r"виджет|тетрис|змейк|2048|пинг|понг|арканоид|туду|todo|список дел|анкет|форм[уа]|викторин|тест\b|app\b|game\b")
_NOT_CODE = re.compile(r"презентац|слайд|картин|рисунок|нарисуй|архив|логотип|фото(?!галере)")


def wants_site(text):
    """Просьба сделать сайт (а не программу, игру или страницу-инструмент)."""
    low = (text or "").lower().replace("ё", "е")
    if _STRONG_SITE.search(low):
        return True
    return webgen.is_site_request(low) and codelib.find_task(low) in (None, "page", "hello")


def is_build_request(text):
    """«Сделай сайт кофейни», «напиши игру тетрис», «создай приложение погоды» — просьба написать код."""
    low = (text or "").lower().replace("ё", "е")
    if _NOT_CODE.search(low) and not _STRONG_SITE.search(low):
        return False
    return bool(_BUILD_VERB.search(low) and _BUILD_NOUN.search(low)) or bool(re.match(r"^\s*(?:сайт|лендинг|игра)\s", low))


def known_program(text):
    """Короткая просьба, которая называет знакомую программу: «калькулятор ИМТ», «шифр цезаря на js»."""
    low = (text or "").lower().replace("ё", "е").strip()
    if len(low) > 60 or re.search(r"\?|^(?:что|как|кто|зачем|почему|где|когда|сколько)\b", low):
        return False
    # Только явные названия программ: «пароль от wifi», «прогноз погоды», «курс валют» — это вопросы, а не заказ кода
    task = codelib.find_task(low)
    if task in _NAMED_PROGRAMS or (task and codelib.lang_from_text(low)):
        return True
    fn_ok = codelib.funcgen.generate(low) is not None
    return fn_ok and bool(codelib.funcgen._TRIGGER.search(low) or codelib.lang_from_text(low))


_NAMED_PROGRAMS = {"tetris", "pong", "breakout", "g2048", "paint", "piano", "memory", "gallery", "bmi", "snake", "tictactoe",
                   "guess", "rps", "calculator", "fizzbuzz", "discord"}


def site_result(spec, answer):
    return {"answer": answer, "code": webgen.render(spec), "lang": "html", "filename": "index.html",
            "title": "Сайт «" + spec["title"] + "»", "site": True}


def run_action(action, code, lang=None, prompt=""):
    """Выполнить действие над кодом. Возвращает {"answer", "code"?, "lang", "filename"?}."""
    # Сайт, приложение или программу на запрещённую тему (наркотики, фишинг, вирусы…) Rai не делает
    if action == "generate":
        bad = moderation.forbidden_build(prompt)
        if bad:
            return {"answer": bad["answer"], "lang": "html", "forbidden": bad["category"]}
    if action == "edit" or (action == "generate" and code and webgen.spec_from_html(code) and webgen.is_edit(prompt)):
        spec = webgen.spec_from_html(code)
        if not spec:
            return {"answer": "Править словами умею сайты, которые собрал сам. Опишите новый сайт — соберу.", "lang": "html"}
        spec, done = webgen.edit_spec(spec, prompt)
        if not done:
            return {"answer": "Не понял правку. " + webgen.EDIT_HELP, "lang": "html"}
        return dict(site_result(spec, f"Сделано: {done}.\n\n{webgen.summary(spec)}"), changed=True)
    if action == "generate" and wants_site(prompt):
        spec = webgen.new_spec(prompt)
        return site_result(spec, webgen.summary(spec) + "\n\n" + webgen.EDIT_HELP)
    if action == "generate":
        code = ""
    lang = detect_lang(code, lang) if code else (lang or "python")
    if action == "check":
        lang, issues = check_code(code, lang)
        return {"answer": report(issues, lang), "lang": lang, "issues": issues}
    if action == "fix":
        if lang != "python":
            lang, issues = check_code(code, lang)
            return {"answer": "Автоисправление умею для Python. Вот что нашёл в коде:\n\n" + report(issues, lang), "lang": lang}
        fixed, changes = fix_python(code)
        issues = check_python(fixed)
        left = [i for i in issues if i["severity"] == "error"]
        text = ("**Исправил:**\n\n" + "\n".join(f"- {c}" for c in changes)) if changes else "Автоматически исправлять было нечего."
        if left:
            text += "\n\n**Осталось исправить вручную:**\n\n" + report(left, "python").split("\n\n", 1)[1]
        elif changes:
            text += "\n\nТеперь ошибок нет."
        return {"answer": text, "code": fixed, "lang": "python", "changed": bool(changes)}
    if action == "explain":
        return {"answer": explain(code, lang), "lang": lang}
    if action == "comment":
        if lang != "python":
            return {"answer": "Комментарии автоматически добавляю в код на Python.", "lang": lang}
        commented = comment_python(code)
        if commented is None:
            return {"answer": "В коде есть синтаксическая ошибка — сначала исправьте её (кнопка «Исправить»).", "lang": lang}
        return {"answer": "Добавил комментарии к строкам кода.", "code": commented, "lang": "python", "changed": True}
    if action == "generate":
        found = codelib.generate(prompt, lang)
        if not found:
            return {"answer": codelib.help_text(), "lang": lang}
        return {"answer": found["about"], "code": found["code"], "lang": found["lang"], "filename": found["filename"],
                "title": found["title"]}
    return {"answer": "Не понял, что сделать с кодом. Могу: проверить, исправить, объяснить, прокомментировать, написать.",
            "lang": lang}


def chat(text, version=None, state=None):
    """Код в обычном чате: проверка/объяснение вставленного кода или генерация по просьбе. None — не про код.

    state — память чата: там лежит последний собранный сайт, чтобы «добавь раздел цены» правило именно его.
    """
    state = state if state is not None else {}
    code, lang = extract_code(text)
    action = action_of(text)
    # Запрещённый заказ (магазин наркотиков, фишинг, вирусы, казино на деньги…) — вежливый отказ, диалог продолжается.
    # Правила требуют именно заказ («сделай/напиши сайт/программу…»), поэтому вопросы («что такое фишинг») не задевают.
    if not code:
        bad = moderation.forbidden_build(text)
        if bad:
            return {"answer": bad["answer"], "lang": "html", "forbidden": bad["category"]}
    if not code and state.get("site") and webgen.is_edit(text) and not wants_site(text):
        spec, done = webgen.edit_spec(state["site"], text)
        if done:
            state["site"] = spec
            return site_result(spec, f"Сделано: {done}.\n\n{webgen.summary(spec)}")
    if not code and wants_site(text) and (is_build_request(text) or action == "generate"):
        spec = webgen.new_spec(text)
        state["site"] = spec
        return site_result(spec, webgen.summary(spec) + "\n\nОткройте «Просмотр» или вкладку Code. " + webgen.EDIT_HELP)
    if code:
        action = action if action in ("fix", "explain", "comment", "check") else "check"
        result = run_action(action, code, lang)
        if action == "check" and not result.get("issues"):
            result["answer"] += "\n\n" + explain(code, result["lang"])
        return result
    if re.search(r"^\s*(а\s+)?(что такое|что это|кто такой|зачем|почему|для чего|чем отличается|сравни)", (text or "").lower()):
        return None  # вопрос о понятии, а не просьба написать код
    if action is None and codelib.find_task(text) and codelib.lang_from_text(text) and len(text) < 80:
        action = "generate"  # «калькулятор на c++»
    if (action is None or action == "check") and (is_build_request(text) or known_program(text)):
        action = "generate"
    if action == "generate" and (codelib.find_task(text) or codelib.funcgen.generate(text)) or action == "generate" and re.search(r"код|программ|скрипт|функци|игр|бот|сайт|страниц|калькулятор|hello|приложени|класс\b|алгоритм|сортировк|парсер|сервер|таймер|html|python|питон|javascript|js\b|php|c\+\+|java\b", (text or "").lower()):
        result = run_action("generate", "", codelib.lang_from_text(text) or "python", text)
        return result if result.get("code") else None
    return None
