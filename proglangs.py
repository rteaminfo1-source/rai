"""Справочник Rai по языкам программирования: что это, для чего, пример «Hello, World»."""

import re

# (название, [другие названия], год, для чего, описание, язык подсветки, пример)
LANGUAGES = [
    ("Python", ["питон", "пайтон"], 1991, "сайты, боты, ИИ, данные, автоматизация",
     "простой и универсальный язык с понятным синтаксисом на отступах", "python", 'print("Привет, мир!")'),
    ("JavaScript", ["js", "джаваскрипт", "яваскрипт"], 1995, "сайты, веб-приложения, серверы (Node.js)",
     "язык браузеров: делает страницы интерактивными", "js", 'console.log("Привет, мир!");'),
    ("TypeScript", ["ts", "тайпскрипт"], 2012, "большие веб-приложения",
     "JavaScript с типами от Microsoft: меньше ошибок в больших проектах", "ts",
     'const text: string = "Привет, мир!";\nconsole.log(text);'),
    ("Java", ["джава", "ява"], 1995, "Android, серверы, корпоративные системы",
     "строгий объектно-ориентированный язык, работает на виртуальной машине JVM", "java",
     'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Привет, мир!");\n    }\n}'),
    ("Kotlin", ["котлин"], 2011, "Android, серверы",
     "современная замена Java от JetBrains, официальный язык Android", "kotlin", 'fun main() {\n    println("Привет, мир!")\n}'),
    ("C", ["си"], 1972, "операционные системы, драйверы, микроконтроллеры",
     "низкоуровневый быстрый язык, на нём написаны Linux и Windows", "c",
     '#include <stdio.h>\n\nint main(void) {\n    printf("Привет, мир!\\n");\n    return 0;\n}'),
    ("C++", ["cpp", "си плюс плюс", "плюсы"], 1985, "игры, движки, быстрые программы",
     "C с классами и шаблонами: высокая скорость и полный контроль", "cpp",
     '#include <iostream>\n\nint main() {\n    std::cout << "Привет, мир!" << std::endl;\n}'),
    ("C#", ["csharp", "си шарп", "шарп"], 2000, "игры на Unity, программы для Windows, .NET",
     "язык Microsoft, похожий на Java", "csharp", 'using System;\n\nConsole.WriteLine("Привет, мир!");'),
    ("Go", ["golang", "голанг"], 2009, "серверы, облачные сервисы, утилиты",
     "простой и быстрый язык Google с удобной многопоточностью", "go",
     'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Привет, мир!")\n}'),
    ("Rust", ["раст"], 2010, "системные программы, быстрые и надёжные сервисы",
     "быстрый как C++, но защищает от ошибок памяти", "rust", 'fn main() {\n    println!("Привет, мир!");\n}'),
    ("Swift", ["свифт"], 2014, "приложения для iPhone, iPad и Mac",
     "язык Apple для iOS и macOS", "swift", 'print("Привет, мир!")'),
    ("Objective-C", ["objective c", "обжектив си"], 1984, "старые приложения Apple",
     "язык Apple до Swift", "objc",
     '#import <Foundation/Foundation.h>\n\nint main() {\n    NSLog(@"Привет, мир!");\n    return 0;\n}'),
    ("PHP", ["пхп"], 1995, "сайты на обычных хостингах, WordPress",
     "серверный язык для веб-страниц", "php", '<?php\necho "Привет, мир!";'),
    ("Ruby", ["руби"], 1995, "сайты (Ruby on Rails), скрипты",
     "выразительный язык, который приятно читать", "ruby", 'puts "Привет, мир!"'),
    ("Dart", ["дарт"], 2011, "мобильные приложения на Flutter",
     "язык Google для Flutter", "dart", 'void main() {\n  print("Привет, мир!");\n}'),
    ("Lua", ["луа"], 1993, "скрипты в играх (Roblox, WoW), встраивание",
     "лёгкий встраиваемый язык", "lua", 'print("Привет, мир!")'),
    ("R", ["эр"], 1993, "статистика, анализ данных, графики",
     "язык для статистиков и аналитиков", "r", 'print("Привет, мир!")'),
    ("Julia", ["джулия"], 2012, "научные расчёты, математика",
     "быстрый язык для учёных", "julia", 'println("Привет, мир!")'),
    ("MATLAB", ["матлаб"], 1984, "инженерные расчёты, матрицы",
     "среда и язык для инженеров", "matlab", "disp('Привет, мир!')"),
    ("Scala", ["скала"], 2004, "обработка больших данных (Spark), серверы",
     "сочетает ООП и функциональный стиль на JVM", "scala", 'object Main extends App {\n  println("Привет, мир!")\n}'),
    ("Haskell", ["хаскель", "хаскелл"], 1990, "исследования, надёжные программы",
     "чисто функциональный язык", "haskell", 'main :: IO ()\nmain = putStrLn "Привет, мир!"'),
    ("Elixir", ["эликсир"], 2011, "чаты, высоконагруженные сервисы",
     "функциональный язык на платформе Erlang", "elixir", 'IO.puts("Привет, мир!")'),
    ("Erlang", ["эрланг"], 1986, "телеком, мессенджеры (WhatsApp)",
     "язык для отказоустойчивых систем", "erlang", '-module(hello).\n-export([main/0]).\n\nmain() -> io:format("Привет, мир!~n").'),
    ("Clojure", ["кложур"], 2007, "серверы, обработка данных",
     "современный Lisp на JVM", "clojure", '(println "Привет, мир!")'),
    ("Lisp", ["лисп", "common lisp"], 1958, "исследования ИИ, обучение",
     "один из старейших языков, код записывается списками", "lisp", '(print "Привет, мир!")'),
    ("F#", ["fsharp", "эф шарп"], 2005, "анализ данных, финансы на .NET",
     "функциональный язык Microsoft", "fsharp", 'printfn "Привет, мир!"'),
    ("OCaml", ["окамл"], 1996, "компиляторы, финансы",
     "функциональный язык со строгими типами", "ocaml", 'print_endline "Привет, мир!"'),
    ("Perl", ["перл"], 1987, "обработка текста, старые серверные скрипты",
     "мощный язык для работы с текстом", "perl", 'print "Привет, мир!\\n";'),
    ("Pascal", ["паскаль"], 1970, "обучение программированию",
     "язык, на котором многие учились в школе", "pascal", "program Hello;\nbegin\n  writeln('Привет, мир!');\nend."),
    ("Delphi", ["делфи", "дельфи", "object pascal"], 1995, "программы для Windows",
     "развитие Pascal для настольных приложений", "delphi", "program Hello;\n{$APPTYPE CONSOLE}\nbegin\n  Writeln('Привет, мир!');\nend."),
    ("Visual Basic", ["vb", "vb.net", "бейсик", "basic", "вижуал бейсик"], 1991, "программы и макросы для Windows и Office",
     "простой язык Microsoft", "vbnet", 'Module Main\n    Sub Main()\n        Console.WriteLine("Привет, мир!")\n    End Sub\nEnd Module'),
    ("Fortran", ["фортран"], 1957, "научные и инженерные расчёты",
     "первый популярный язык высокого уровня", "fortran", "program hello\n  print *, 'Привет, мир!'\nend program hello"),
    ("COBOL", ["кобол"], 1959, "банки и старые бизнес-системы",
     "язык для деловых расчётов, до сих пор работает в банках", "cobol",
     "IDENTIFICATION DIVISION.\nPROGRAM-ID. HELLO.\nPROCEDURE DIVISION.\n    DISPLAY 'Привет, мир!'.\n    STOP RUN."),
    ("Assembly", ["ассемблер", "asm", "assembler"], 1949, "драйверы, микроконтроллеры, оптимизация",
     "язык команд процессора — ниже только машинный код", "nasm",
     "section .data\n    msg db 'Hello, World!', 10\nsection .text\n    global _start\n_start:\n    mov rax, 1\n    mov rdi, 1\n    mov rsi, msg\n    mov rdx, 14\n    syscall\n    mov rax, 60\n    xor rdi, rdi\n    syscall"),
    ("Bash", ["shell", "баш", "sh"], 1989, "автоматизация в Linux, скрипты",
     "командная оболочка Linux и macOS", "bash", 'echo "Привет, мир!"'),
    ("PowerShell", ["повершелл", "пауэршелл"], 2006, "автоматизация Windows",
     "командная оболочка Microsoft", "powershell", 'Write-Output "Привет, мир!"'),
    ("SQL", ["эскюэль", "сиквел"], 1974, "запросы к базам данных",
     "язык для работы с таблицами в базах данных", "sql", "SELECT 'Привет, мир!';"),
    ("HTML", ["хтмл"], 1993, "разметка веб-страниц",
     "язык разметки (не программирования): структура страницы", "html", "<h1>Привет, мир!</h1>"),
    ("CSS", ["цсс"], 1996, "оформление веб-страниц",
     "язык стилей: цвета, шрифты, расположение", "css", 'body::before { content: "Привет, мир!"; }'),
    ("Groovy", ["груви"], 2003, "скрипты сборки (Gradle), автоматизация",
     "динамический язык на JVM", "groovy", 'println "Привет, мир!"'),
    ("Zig", ["зиг"], 2016, "системное программирование",
     "простая современная альтернатива C", "zig",
     'const std = @import("std");\n\npub fn main() void {\n    std.debug.print("Привет, мир!\\n", .{});\n}'),
    ("Nim", ["ним"], 2008, "быстрые программы с синтаксисом как у Python",
     "компилируемый язык, похожий на Python", "nim", 'echo "Привет, мир!"'),
    ("Crystal", ["кристал"], 2014, "быстрые сервисы с синтаксисом Ruby",
     "компилируемый язык, похожий на Ruby", "crystal", 'puts "Привет, мир!"'),
    ("Solidity", ["солидити"], 2014, "смарт-контракты Ethereum",
     "язык для блокчейн-программ", "solidity",
     '// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ncontract Hello {\n    string public text = "Привет, мир!";\n}'),
    ("Prolog", ["пролог"], 1972, "логический вывод, экспертные системы",
     "логический язык: описываете факты и правила", "prolog", ":- initialization(main).\nmain :- write('Привет, мир!'), nl."),
    ("Scratch", ["скретч"], 2007, "обучение детей программированию",
     "визуальный язык из блоков от MIT", "text", "когда нажат зелёный флажок\n  сказать [Привет, мир!]"),
    ("1С", ["1c", "один эс"], 1996, "учёт, бухгалтерия, бизнес в России",
     "язык платформы 1С:Предприятие", "text", 'Сообщить("Привет, мир!");'),
    ("V", ["vlang"], 2019, "простые быстрые программы",
     "молодой компилируемый язык", "v", "fn main() {\n    println('Привет, мир!')\n}"),
    ("GDScript", ["гдскрипт"], 2014, "игры на движке Godot",
     "язык движка Godot, похож на Python", "gdscript", 'extends Node\n\nfunc _ready():\n    print("Привет, мир!")'),
]


def _norm(text):
    return (text or "").lower().replace("ё", "е")


_NAMES = []
for entry in LANGUAGES:
    for alias in [entry[0]] + entry[1]:
        _NAMES.append((_norm(alias), entry))
_NAMES.sort(key=lambda x: -len(x[0]))

_CONTEXT = r"(?:язык\w*(?: программирования)?|на|про|о|об|что такое|hello world на|пример\w* на|код\w* на)\s+"


def find_language(text: str, strict_short=True):
    low = _norm(text)
    for alias, entry in _NAMES:
        pattern = r"(?<![\w+#])" + re.escape(alias) + r"(?![\w+#])"
        if len(alias) <= 2 and strict_short:
            pattern = _CONTEXT + pattern  # «c», «r», «v», «go»: только в явном контексте
        if re.search(pattern, low):
            return entry
    return None


_LIST_RE = re.compile(r"(какие|список|перечисли|все)\s+(?:ты\s+)?(?:знаешь\s+)?языки? программирования|"
                      r"языки программирования (?:ты )?знаешь|сколько языков программирования", re.I)
_CODE_RE = re.compile(r"hello,? world|привет,? мир|пример\w* кода|пример\w* на|код на|напиши на|программ\w* на|"
                      r"как вывести|как написать", re.I)
_ABOUT_RE = re.compile(r"что такое|что за|расскажи (?:про|о|об)|язык\w*\s|для чего|зачем", re.I)


def describe(entry, with_code=True):
    name, _, year, use, desc, lang, code = entry
    text = f"**{name}** ({year}) — {desc}.\n\n**Для чего:** {use}."
    if with_code:
        text += f"\n\n**Hello, World на {name}:**\n\n```{lang}\n{code}\n```"
    return text


def answer(text: str):
    """Ответ про язык программирования или None."""
    if _LIST_RE.search(text):
        rows = "\n".join(f"| **{e[0]}** | {e[2]} | {e[3]} |" for e in LANGUAGES)
        return (f"## Языки программирования, которые я знаю ({len(LANGUAGES)})\n\n"
                f"| Язык | Год | Для чего |\n|---|---|---|\n{rows}\n\n"
                "Спросите про любой: «что такое Rust», «hello world на Go».")
    entry = find_language(text)
    if not entry:
        return None
    if _CODE_RE.search(text):
        name, _, _, _, _, lang, code = entry
        return f"**Hello, World на {name}:**\n\n```{lang}\n{code}\n```"
    if _ABOUT_RE.search(text) or _norm(text).strip(" ?!.") in [_norm(a) for a in [entry[0]] + entry[1]]:
        return describe(entry)
    return None
