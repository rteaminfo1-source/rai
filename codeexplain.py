"""Объяснение кода на любом из 27 языков: что делает каждая важная строка — по-русски и простыми словами.

Для Python есть точный разбор по синтаксическому дереву (codeai.explain_python); здесь — для остальных языков:
C, C++, C#, Java, JavaScript, TypeScript, Go, Rust, Kotlin, Swift, Dart, Scala, Groovy, PHP, Ruby, Crystal, Lua, Perl,
R, Julia, Nim, Bash, PowerShell, Pascal, Visual Basic, Fortran. Узнаём конструкции по характерным строкам:
объявления функций, циклы (с границами), условия, ввод, вывод, переменные, массивы, возврат, выход из цикла.
"""

import re

_I = re.I
_KEYWORDS = {"if", "for", "while", "switch", "return", "else", "catch", "foreach", "using", "elif", "elsif", "until", "sizeof"}


def _clip(s, n=60):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def _args(s):
    s = _clip(s, 50)
    return s if s.strip() else "без параметров"


# (регулярное выражение, функция → текст). Порядок важен: сначала узкие шаблоны.
def _fn(m):
    name, args = m.group("name"), m.group("args") if "args" in m.groupdict() else ""
    if name.lower() in _KEYWORDS:
        return None
    if name == "main" or name.lower() == "main":
        return "главная функция — с неё начинается программа"
    return f"объявляет функцию **{name}** ({_args(args)})"


def _cond(rest):
    """Условие после if / while: снимаем {, then, do, :, (( )), [[ ]] и внешние скобки; хвост однострочника отдельно."""
    rest = re.sub(r"\s*(?:\{|then|Then|do|:|;\s*then|;\s*do)\s*$", "", rest.strip())
    m = re.fullmatch(r"\(\(\s*(.+?)\s*\)\);?", rest) or re.fullmatch(r"\[\[\s*(.+?)\s*\]\];?", rest)
    if m:
        return m.group(1), ""
    if rest.startswith("("):
        depth = 0
        for k, ch in enumerate(rest):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0:
                return rest[1:k].strip(), rest[k + 1:].strip().rstrip(";").strip()
    return rest.rstrip(";").strip(), ""


def _if(m):
    cond, tail = _cond(m.group("rest"))
    if not cond:
        return None
    if tail:
        return f"если {_clip(cond, 45)} — {_clip(tail, 40)}"
    kw = m.group("kw").lower().replace(" ", "")
    return ("иначе, если " if kw != "if" else "проверяет условие: ") + _clip(cond)


def _while(m):
    cond, tail = _cond(m.group("rest"))
    if cond.lower() in ("true", "1", "$true"):
        return "бесконечный цикл — выход из него по break"
    return f"цикл, пока верно: {_clip(cond)}" if cond else None


def _range(var, a, b, inclusive):
    a, b = _clip(a, 30), _clip(b, 30)
    if var in ("_", ""):
        return f"повторяет действия для значений от {a} до {b}{' включительно' if inclusive else ' (не включая)'}"
    return f"цикл: **{var}** идёт от {a} до {b}{' включительно' if inclusive else ' (не включая)'}"


PATTERNS = [
    # ---------------- функции
    (r"^\s*(?:pub\s+)?fn\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)", _fn),                                         # Rust
    (r"^\s*func\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)", _fn),                                                   # Go, Swift
    (r"^\s*(?:private\s+|public\s+|internal\s+)?fun\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)", _fn),               # Kotlin
    (r"^\s*proc\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)", _fn),                                                   # Nim
    (r"^\s*(?P<name>[\w.]+)\s*<-\s*function\s*\((?P<args>[^)]*)\)", _fn),                                       # R
    (r"^\s*(?:Public\s+|Private\s+|Shared\s+)*(?:Function|Sub)\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)", _fn),     # VB
    (r"^\s*(?:function|procedure)\s+(?P<name>\w+)\s*(?:\((?P<args>[^)]*)\))?\s*(?::\s*\w+)?\s*;", _fn),          # Pascal
    (r"^\s*(?:[\w()]+\s+)?function\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*(?:result\(\w+\))?\s*$", _fn),        # Fortran, Julia, Lua
    (r"^\s*(?:local\s+)?function\s+(?P<name>[\w.:-]+)\s*\((?P<args>[^)]*)\)", _fn),                            # Lua, JS, PHP, PowerShell
    (r"^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)", _fn),
    (r"^\s*def\s+(?P<name>\w+[?!]?)\s*(?:\((?P<args>[^)]*)\))?", _fn),                                         # Ruby, Crystal, Scala
    (r"^\s*sub\s+(?P<name>\w+)", lambda m: f"объявляет функцию **{m.group('name')}** (параметры — в @_)"),         # Perl
    (r"^\s*(?P<name>[\w-]+)\s*\(\)\s*\{", _fn),                                                                # Bash
    (r"^\s*(?!(?:if|else|while|for|return|switch|case|elif|elsif|elseif|until|unless|do|loop|when|match|new|throw|echo|print|"
     r"say|puts|not|and|or|in|of|await|yield)\b)(?:(?:static|public|private|protected|inline|final|override|virtual|async)\s+)*"
     r"(?:[\w:<>\[\],*&]+\s+)+(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*\{?\s*$", _fn),                              # C, C++, Java, C#, Dart
    # ---------------- классы и модули
    (r"^\s*(?:public\s+|final\s+|abstract\s+|data\s+)*(?:class|struct|object|Module)\s+(\w+)",
     lambda m: f"объявляет {'модуль' if 'Module' in m.group(0) else 'класс'} **{m.group(1)}**"),
    (r"^\s*program\s+(\w+)", lambda m: f"начало программы {m.group(1)}"),
    (r"^\s*package\s+main\b", lambda m: "пакет main — запускаемая программа"),
    # ---------------- подключения
    (r"^\s*#include\s*[<\"](.+?)[>\"]", lambda m: f"подключает библиотеку {m.group(1)}"),
    (r"^\s*use\s+(.+?);\s*$", lambda m: f"подключает {_clip(m.group(1), 40)}"),
    (r"^\s*(?:import|using|use|uses|Imports|require|require_relative)\s+(?!\()['\"]?([\w.:/{}, *]+?)['\"]?;?\s*$",
     lambda m: f"подключает {_clip(m.group(1), 40)}"),
    (r"^\s*import\s*\(\s*$", lambda m: "подключает пакеты (список ниже)"),
    (r"^\s*implicit none", lambda m: "все переменные нужно объявлять явно"),
    (r"^\s*(?:use\s+strict|use\s+warnings)", lambda m: "строгий режим: ошибки видны сразу"),
    # ---------------- циклы с границами
    (r"for\s*\(\s*(?:int|let|var|auto|long|size_t|double)?\s*\$?(\w+)\s*=\s*([^;]+);\s*\$?\w+\s*(<=|<|-le|-lt)\s*([^;]+);",
     lambda m: _range(m.group(1), m.group(2), m.group(4), m.group(3) in ("<=", "-le"))),                       # C-подобные, PowerShell
    (r"for\s*\(\(\s*(\w+)\s*=\s*([^;]+);\s*\w+\s*(<=|<)\s*([^;]+);",
     lambda m: _range(m.group(1), m.group(2), m.group(4), m.group(3) == "<=")),                                 # Bash
    (r"for\s+(\w+)\s*:=\s*(.+?);\s*\w+\s*(<=|<)\s*(.+?);", lambda m: _range(m.group(1), m.group(2), m.group(4), m.group(3) == "<=")),  # Go
    (r"for\s+(\w+)\s*:=\s*(.+?)\s+to\s+(.+?)\s+do\b", lambda m: _range(m.group(1), m.group(2), m.group(3), True)),   # Pascal
    (r"For\s+(\w+)(?:\s+As\s+\w+)?\s*=\s*(.+?)\s+To\s+(.+?)\s*$", lambda m: _range(m.group(1), m.group(2), m.group(3), True)),  # VB
    (r"^\s*do\s+(\w+)\s*=\s*([^,]+),\s*(.+?)\s*$", lambda m: _range(m.group(1), m.group(2), m.group(3), True)),          # Fortran
    (r"for\s+(\w+)\s*=\s*([^,]+),\s*(.+?)\s+do\b", lambda m: _range(m.group(1), m.group(2), m.group(3), True)),          # Lua
    (r"for\s+my\s+\$(\w+)\s*\((.+?)\s*\.\.\s*(.+?)\)", lambda m: _range(m.group(1), m.group(2), m.group(3), True)),      # Perl
    (r"for\s*\(?\s*(\w+)\s+in\s+stride\(from:\s*(.+?),\s*to:\s*(.+?),", lambda m: _range(m.group(1), m.group(2), m.group(3), False)),  # Swift
    (r"for\s*\(?\s*(\w+)\s+(?:in|<-)\s+(.+?)\s*(\.\.<|\.\.=|\.\.\.|\.\.|until|to)\s*(.+?)\)?\s*[{:]?\s*$",
     lambda m: _range(m.group(1), m.group(2), m.group(4), m.group(3) in ("..=", "...", "..", "to"))),       # Rust, Kotlin, Swift, Scala, Nim
    (r"for\s*\(?\s*(\w+)\s+in\s+seq_len\((.+)\)\s*(-\s*1)?\)", lambda m: _range(m.group(1), "0" if m.group(3) else "1",
                                                                               m.group(2) + (" − 1" if m.group(3) else ""), True)),  # R
    (r"for\s*\(?\s*(\w+)\s+in\s+([^:\s]+):(.+?)\)?\s*\{?\s*$", lambda m: _range(m.group(1), m.group(2), m.group(3), True)),    # Julia, R
    (r"\((.+?)(\.\.\.?)(.+?)\)\.each\s+do\s*\|(\w+)\|", lambda m: _range(m.group(4), m.group(1), m.group(3), m.group(2) == "..")),  # Ruby
    (r"(\w+)\.times\s+do", lambda m: f"повторяет действия {m.group(1)} раз"),
    (r"^\s*for\s+(\w+)\s+in\s+range\((.+)\)", lambda m: f"цикл: **{m.group(1)}** перебирает range({_clip(m.group(2), 30)})"),
    (r"^\s*for\s+(?!.*:=)(?!.*\brange\b)(?!.*\bin\b)([^;{]+?)\s*\{\s*$", lambda m: f"цикл, пока верно: {_clip(m.group(1))}"),  # Go
    (r"^\s*(?:for|foreach)\s*\(?(.+?)\)?\s*\{?\s*$", lambda m: f"цикл по {_clip(m.group(1), 50)}"),
    # ---------------- бесконечные циклы и while
    (r"^\s*(?:loop\s*\{|loop\s+do|repeat\s*\{|while\s*\(?\s*(?:true|True|1|\$true)\s*\)?\s*(?:\{|do|:)?|for\s*\{|do)\s*$",
     lambda m: "бесконечный цикл — выход из него по break"),
    (r"^\s*(?:do\s+)?(?:while|While)\b(?P<rest>.+)$", _while),
    # ---------------- условия
    (r"^\s*(?:\}\s*)?(?P<kw>else\s*if|elif|elsif|elseif|ElseIf|if|If)\b(?P<rest>.+)$", _if),
    (r"^\s*(?:\}\s*)?(?:else|Else)\s*(?:\{|:)?\s*$", lambda m: "иначе — другая ветка"),
    # ---------------- выход из цикла и возврат
    (r"^\s*(?:break|last|Exit\s+(?:While|For|Do)|exit|Break)\s*[;)]?\s*$", lambda m: "досрочно выходит из цикла"),
    (r"^\s*(?:return|Return)\s+(.+?);?\s*$", lambda m: f"возвращает результат: {_clip(m.group(1), 50)}"),
    (r"^\s*Exit\((.+)\);?\s*$", lambda m: f"возвращает результат: {_clip(m.group(1), 50)}"),
    (r"^\s*Result\s*:=\s*(.+?);?\s*$", lambda m: f"результат функции: {_clip(m.group(1), 50)}"),
    # ---------------- ввод
    (r"(?:read_?(?:int|line|double|float|real|text)|read(?:Int|Line|Double|Float|Text)|Read(?:Int|Text|Double|Real)|ask)\s*\(\s*"
     r"(['\"])(.*?)\1", lambda m: f"спрашивает у пользователя: «{_clip(m.group(2), 50).strip()}»"),
    (r"read\s+-r?p\s+\"(.*?)\"\s+(\w+)", lambda m: f"спрашивает «{_clip(m.group(1), 40).strip()}» и запоминает ответ в {m.group(2)}"),
    (r"\b(?:scanf|cin\s*>>|Console\.ReadLine|readLine\(\)|readln\(|ReadLn|readline\(|gets\b|io\.read|stdin\.readLine|"
     r"read\(\*|readLines\(|Read-Host|<STDIN>|fgets\()", lambda m: "читает строку, которую ввёл пользователь"),
    # ---------------- вывод
    (r"^\s*(?:print|write\s*\(\s*\*\s*,)\s*'\([^']*\)'\s*,?\s*(?:advance='no'\s*\))?\s*(.*)$",
     lambda m: f"выводит на экран: {_clip(m.group(1), 50) or 'пустую строку'}"),                                     # Fortran
    (r"(?:System\.out\.print(?:ln)?|Console\.Write(?:Line)?|console\.log|fmt\.Print(?:ln|f)?|std::cout\s*<<|Write-Host|WriteLn|"
     r"io\.write|stdout\.write|println!?|printf|print!?|puts|say|echo|cat|Write)(?![\w-])\s*(?:-NoNewline\s+)?\(?\s*(.*?)\)?;?\s*$",
     lambda m: f"выводит на экран: {_clip(m.group(1), 50) or 'пустую строку'}"),
    # ---------------- случайные числа
    (r"\b(?:rand|random|Random|Get-Random|RANDOM|random_int|randint|sample)\b", lambda m: "загадывает случайное число"),
    # ---------------- массивы
    (r"(?:vec!\[|intArrayOf\(|Array\(|@\(|\bc\(|\[\s*-?\d+\s*,|\{\s*-?\d+\s*,|=\s*\(\s*-?\d+\s+-?\d+)", lambda m: "создаёт массив чисел"),
    # ---------------- переменные
    (r"^\s*(?:let\s+mut|let|var|val|const|final|my|local|auto|Dim)\s+\$?(\w+)(?:\s*(?::|As)\s*[\w<>\[\]]+)?\s*:?=\s*(.+?);?\s*$",
     lambda m: f"переменная **{m.group(1)}** = {_clip(m.group(2), 50)}"),
    (r"^\s*(?:int|long|long long|double|float|bool|boolean|char|string|String|std::string|auto|var|Integer|Int64)\s+(\w+)\s*=\s*(.+?);?\s*$",
     lambda m: f"переменная **{m.group(1)}** = {_clip(m.group(2), 50)}"),
    (r"^\s*\[?\w*\]?\$(\w+)\s*=\s*(.+?);?\s*$", lambda m: f"переменная **{m.group(1)}** = {_clip(m.group(2), 50)}"),
    (r"^\s*(\w+)\s*(?::=|<-)\s*(.+?);?\s*$", lambda m: f"**{m.group(1)}** = {_clip(m.group(2), 50)}"),
    (r"^\s*(\w+)\s*([+\-*/])=\s*(.+?);?\s*$", lambda m: f"{'прибавляет к' if m.group(2) == '+' else 'меняет'} **{m.group(1)}**: "
                                                       f"{m.group(2)}= {_clip(m.group(3), 40)}"),
    (r"^\s*(\w+)\+\+;?\s*$|^\s*Inc\((\w+)\);?\s*$|^\s*\(\(\s*(\w+)\+\+\s*\)\)\s*$|^\s*inc\s+(\w+)\s*$",
     lambda m: f"увеличивает **{next(g for g in m.groups() if g)}** на 1"),
    (r"^\s*(\w+(?:\[[^\]]+\]|\([^)]+\))?)\s*=\s*(.+?);?\s*$", lambda m: f"**{m.group(1)}** = {_clip(m.group(2), 50)}"),
]
_COMPILED = [(re.compile(p), f) for p, f in PATTERNS]

_COMMENT = re.compile(r"^\s*(?://|#(?!include|!)|--|'|!|\{[^$]|\(\*|/\*|\*)")
_INPUT = re.compile(r"scanf|cin\s*>>|ReadLine|readLine|readln|ReadLn|readline|gets\b|io\.read|read\s+-r|read\(\*|readLines|"
                    r"Read-Host|<STDIN>|fgets|input\(|read_?(?:int|line|double|float|real)|read(?:Int|Double|Text)|\bask\(", _I)


def explain(code, lang_name="", run_hint="", lang=""):
    """Построчное объяснение: «- **строка 5:** цикл: i идёт от 1 до 100 включительно.» и итог."""
    lines = (code or "").split("\n")
    found, funcs, loops, conds = [], 0, 0, 0
    for i, line in enumerate(lines, 1):
        if not line.strip() or _COMMENT.match(line) or re.match(r"^\s*[{}()\[\];,]*\s*$", line):
            continue
        if re.match(r"^\s*(?:end|End\b|fi|done|next|Next|end\s+\w+|End\s+\w+|\}\s*\)?;?)\s*$", line):
            continue
        for rx, fn in _COMPILED:
            m = rx.search(line)
            if not m:
                continue
            text = fn(m)
            if not text:
                continue
            if lang == "rust" and " включительно" in text and re.search(r"\.\.(?![=.<])", m.group(0)):
                text = text.replace(" включительно", " (не включая)")      # в Rust a..b — без b, a..=b — с b
            if text.startswith("объявляет функцию") or text.startswith("главная функция"):
                funcs += 1
            elif text.startswith(("цикл", "повторяет", "бесконечный")):
                loops += 1
            elif text.startswith("проверяет условие"):
                conds += 1
            depth = len(re.match(r"\s*", line.replace("\t", "    ")).group(0)) // 4
            found.append("  " * min(depth, 4) + f"- **строка {i}:** {text}" + ("" if text.endswith((".", "…")) else "."))
            break
    if not found:
        return None
    stats = [f"строк: {len([l for l in lines if l.strip()])}"]
    if funcs:
        stats.append(f"функций: {funcs}")
    if loops:
        stats.append(f"циклов: {loops}")
    if conds:
        stats.append(f"условий: {conds}")
    extra = " Программа спрашивает данные у пользователя." if _INPUT.search(code or "") else ""
    head = f"### Что делает этот код ({lang_name})" if lang_name else "### Что делает этот код"
    text = head + "\n\n" + "\n".join(found[:80]) + ("\n\n*(показаны первые 80 шагов)*" if len(found) > 80 else "")
    text += f"\n\n**Итого:** {', '.join(stats)}.{extra}"
    if run_hint:
        text += f"\n\n**Как запустить:** `{run_hint}`"
    return text
