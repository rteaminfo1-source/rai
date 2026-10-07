"""Библиотека программ Rai: рабочий код по описанию на Python, JavaScript, HTML, PHP, C++, Java.

Каждая задача: слова, по которым её узнать, название, пояснение и код для нескольких языков.
"""

import re

LANG_WORDS = [
    ("html", r"\bhtml\b|веб-?страниц|страниц[уа]|сайт|в браузере|лендинг"),
    ("javascript", r"javascript|джаваскрипт|\bjs\b|node|нод"),
    ("typescript", r"typescript|\bts\b"),
    ("php", r"\bphp\b|пхп"),
    ("cpp", r"c\+\+|cpp|си плюс плюс|плюсах"),
    ("csharp", r"c#|си шарп|csharp"),
    ("java", r"\bjava\b|джав[аеу]"),
    ("python", r"python|питон|пайтон|\bpy\b"),
]

EXT = {"python": "py", "javascript": "js", "html": "html", "php": "php", "cpp": "cpp", "java": "java", "csharp": "cs"}


def lang_from_text(text):
    low = (text or "").lower()
    for lang, pattern in LANG_WORDS:
        if re.search(pattern, low):
            return lang
    return None


T = {}


def task(key, words, title, about, **codes):
    T[key] = {"words": words, "title": title, "about": about, "codes": codes}


# ------------------------------------------------------------------ задачи
task("snake", r"змейк|snake", "Игра «Змейка»",
     "Классическая змейка: стрелки или WASD — управление, пробел — пауза. Съедайте красные клетки и не врезайтесь в себя.",
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Змейка</title>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b0b0c; color: #f3f1f1; font: 16px system-ui, sans-serif; }
  canvas { background: #151517; border: 2px solid #e10600; border-radius: 8px; max-width: 95vw; }
  p { text-align: center; }
</style>
</head>
<body>
<div>
  <p>Счёт: <b id="score">0</b> · Рекорд: <b id="best">0</b></p>
  <canvas id="game" width="400" height="400"></canvas>
  <p>Стрелки / WASD — управление, пробел — пауза</p>
</div>
<script>
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const size = 20, cells = canvas.width / size;
let snake, dir, nextDir, food, score, paused = false;
let best = 0;
try { best = Number(localStorage.getItem("snake-best") || 0); } catch (e) { /* рекорд не сохранится */ }
document.getElementById("best").textContent = best;

function reset() {
  snake = [{x: 10, y: 10}, {x: 9, y: 10}, {x: 8, y: 10}];
  dir = nextDir = {x: 1, y: 0};
  score = 0;
  document.getElementById("score").textContent = score;
  placeFood();
}

function placeFood() {
  do {
    food = {x: Math.floor(Math.random() * cells), y: Math.floor(Math.random() * cells)};
  } while (snake.some(p => p.x === food.x && p.y === food.y));
}

function step() {
  if (paused) return;
  dir = nextDir;
  const head = {x: (snake[0].x + dir.x + cells) % cells, y: (snake[0].y + dir.y + cells) % cells};
  if (snake.some(p => p.x === head.x && p.y === head.y)) {
    if (score > best) { best = score; try { localStorage.setItem("snake-best", best); } catch (e) { /* без сохранения */ } document.getElementById("best").textContent = best; }
    alert("Игра окончена! Счёт: " + score);
    reset();
    return;
  }
  snake.unshift(head);
  if (head.x === food.x && head.y === food.y) {
    score++;
    document.getElementById("score").textContent = score;
    placeFood();
  } else {
    snake.pop();
  }
  draw();
}

function draw() {
  ctx.fillStyle = "#151517";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ff2a2a";
  ctx.fillRect(food.x * size + 2, food.y * size + 2, size - 4, size - 4);
  snake.forEach((p, i) => {
    ctx.fillStyle = i === 0 ? "#3ccf7a" : "#2a9d5c";
    ctx.fillRect(p.x * size + 1, p.y * size + 1, size - 2, size - 2);
  });
}

document.addEventListener("keydown", e => {
  const keys = {ArrowUp: [0, -1], KeyW: [0, -1], ArrowDown: [0, 1], KeyS: [0, 1],
                ArrowLeft: [-1, 0], KeyA: [-1, 0], ArrowRight: [1, 0], KeyD: [1, 0]};
  if (e.code === "Space") { paused = !paused; e.preventDefault(); return; }
  const k = keys[e.code];
  if (k && (k[0] !== -dir.x || k[1] !== -dir.y)) {
    nextDir = {x: k[0], y: k[1]};
    e.preventDefault();
  }
});

reset();
draw();
setInterval(step, 120);
</script>
</body>
</html>
''',
     python='''import random
import os
import time

# Упрощённая консольная змейка: ход — команда (w/a/s/d + Enter), q — выход.
W, H = 15, 10
snake = [(5, 5), (4, 5), (3, 5)]
direction = (1, 0)
food = (10, 5)
score = 0


def draw():
    os.system("cls" if os.name == "nt" else "clear")
    for y in range(H):
        row = ""
        for x in range(W):
            if (x, y) == snake[0]:
                row += "@"
            elif (x, y) in snake:
                row += "o"
            elif (x, y) == food:
                row += "*"
            else:
                row += "."
        print(row)
    print(f"Счёт: {score}. Ход: w/a/s/d, выход: q")


moves = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
while True:
    draw()
    key = input("> ").strip().lower()
    if key == "q":
        break
    if key in moves:
        direction = moves[key]
    head = ((snake[0][0] + direction[0]) % W, (snake[0][1] + direction[1]) % H)
    if head in snake:
        print(f"Игра окончена! Счёт: {score}")
        break
    snake.insert(0, head)
    if head == food:
        score += 1
        while food in snake:
            food = (random.randrange(W), random.randrange(H))
    else:
        snake.pop()
    time.sleep(0.05)
''')

task("tictactoe", r"крестики|нолики|tic.?tac", "Крестики-нолики",
     "Крестики-нолики на двоих: ходите по очереди, побеждает тот, кто первым соберёт три в ряд.",
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Крестики-нолики</title>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b0b0c; color: #f3f1f1; font: 18px system-ui, sans-serif; }
  .board { display: grid; grid-template-columns: repeat(3, 90px); gap: 6px; margin: 16px auto; }
  button.cell { width: 90px; height: 90px; font-size: 44px; font-weight: 800; background: #151517; color: #fff; border: 1px solid #2a2a2e; border-radius: 12px; cursor: pointer; }
  button.cell:hover { border-color: #e10600; }
  #status { text-align: center; min-height: 1.5em; }
  #restart { display: block; margin: 0 auto; padding: 10px 18px; background: #e10600; color: #fff; border: 0; border-radius: 10px; font-size: 16px; cursor: pointer; }
</style>
</head>
<body>
<div>
  <p id="status">Ходит X</p>
  <div class="board" id="board"></div>
  <button id="restart">Заново</button>
</div>
<script>
const lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
let cells, player, over;
const board = document.getElementById("board");
const status = document.getElementById("status");

function start() {
  cells = Array(9).fill("");
  player = "X";
  over = false;
  status.textContent = "Ходит X";
  board.innerHTML = "";
  cells.forEach((_, i) => {
    const b = document.createElement("button");
    b.className = "cell";
    b.onclick = () => move(i, b);
    board.append(b);
  });
}

function move(i, button) {
  if (over || cells[i]) return;
  cells[i] = player;
  button.textContent = player;
  const win = lines.find(l => l.every(k => cells[k] === player));
  if (win) {
    status.textContent = "Победил " + player + "!";
    over = true;
  } else if (cells.every(Boolean)) {
    status.textContent = "Ничья!";
    over = true;
  } else {
    player = player === "X" ? "O" : "X";
    status.textContent = "Ходит " + player;
  }
}

document.getElementById("restart").onclick = start;
start();
</script>
</body>
</html>
''',
     python='''board = [" "] * 9
lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def show():
    for r in range(3):
        print(" | ".join(board[r * 3:r * 3 + 3]))
        if r < 2:
            print("--+---+--")


player = "X"
for turn in range(9):
    show()
    while True:
        choice = input(f"Ходит {player}. Номер клетки 1-9: ")
        if choice.isdigit() and 1 <= int(choice) <= 9 and board[int(choice) - 1] == " ":
            break
        print("Так нельзя, выберите свободную клетку.")
    board[int(choice) - 1] = player
    if any(all(board[i] == player for i in line) for line in lines):
        show()
        print(f"Победил {player}!")
        break
    player = "O" if player == "X" else "X"
else:
    show()
    print("Ничья!")
''')

task("guess", r"угада|загада", "Игра «Угадай число»",
     "Компьютер загадывает число от 1 до 100, а вы угадываете. После каждой попытки — подсказка «больше» или «меньше».",
     python='''import random

secret = random.randint(1, 100)
tries = 0
print("Я загадал число от 1 до 100. Угадайте!")

while True:
    text = input("Ваш вариант: ")
    if not text.isdigit():
        print("Введите целое число.")
        continue
    guess = int(text)
    tries += 1
    if guess < secret:
        print("Больше!")
    elif guess > secret:
        print("Меньше!")
    else:
        print(f"Угадали за {tries} попыток!")
        break
''',
     javascript='''const secret = Math.floor(Math.random() * 100) + 1;
let tries = 0;

while (true) {
  const text = prompt("Я загадал число от 1 до 100. Ваш вариант:");
  if (text === null) break;
  const guess = Number(text);
  tries++;
  if (!Number.isInteger(guess)) {
    alert("Введите целое число.");
  } else if (guess < secret) {
    alert("Больше!");
  } else if (guess > secret) {
    alert("Меньше!");
  } else {
    alert(`Угадали за ${tries} попыток!`);
    break;
  }
}
''',
     cpp='''#include <iostream>
#include <cstdlib>
#include <ctime>

int main() {
    std::srand(std::time(nullptr));
    int secret = std::rand() % 100 + 1;
    int guess = 0, tries = 0;
    std::cout << "Я загадал число от 1 до 100. Угадайте!" << std::endl;
    while (guess != secret) {
        std::cout << "Ваш вариант: ";
        std::cin >> guess;
        tries++;
        if (guess < secret) std::cout << "Больше!" << std::endl;
        else if (guess > secret) std::cout << "Меньше!" << std::endl;
    }
    std::cout << "Угадали за " << tries << " попыток!" << std::endl;
    return 0;
}
''',
     java='''import java.util.Random;
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        int secret = new Random().nextInt(100) + 1;
        Scanner in = new Scanner(System.in);
        int tries = 0;
        System.out.println("Я загадал число от 1 до 100. Угадайте!");
        while (true) {
            System.out.print("Ваш вариант: ");
            int guess = in.nextInt();
            tries++;
            if (guess < secret) System.out.println("Больше!");
            else if (guess > secret) System.out.println("Меньше!");
            else { System.out.println("Угадали за " + tries + " попыток!"); break; }
        }
    }
}
''')

task("calculator", r"калькулятор|calculator", "Калькулятор",
     "Калькулятор: введите два числа и операцию (+, -, *, /). Деление на ноль обрабатывается.",
     python='''def calculate(a, op, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ZeroDivisionError("на ноль делить нельзя")
        return a / b
    raise ValueError(f"неизвестная операция {op}")


print("Калькулятор. Пустая строка — выход.")
while True:
    first = input("Первое число: ")
    if not first:
        break
    try:
        a = float(first)
        op = input("Операция (+ - * /): ").strip()
        b = float(input("Второе число: "))
        print("Ответ:", calculate(a, op, b))
    except ValueError as e:
        print("Ошибка:", e)
    except ZeroDivisionError as e:
        print("Ошибка:", e)
''',
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Калькулятор</title>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b0b0c; font: 20px system-ui, sans-serif; }
  .calc { background: #151517; padding: 16px; border-radius: 18px; width: 280px; border: 1px solid #2a2a2e; }
  #display { width: 100%; box-sizing: border-box; font-size: 32px; text-align: right; padding: 12px; border: 0; border-radius: 10px; background: #0b0b0c; color: #fff; margin-bottom: 12px; }
  .keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  button { padding: 16px 0; font-size: 20px; border: 0; border-radius: 10px; background: #26262a; color: #fff; cursor: pointer; }
  button.op { background: #e10600; }
  button.wide { grid-column: span 2; }
</style>
</head>
<body>
<div class="calc">
  <input id="display" readonly value="0">
  <div class="keys" id="keys"></div>
</div>
<script>
const display = document.getElementById("display");
const layout = ["C", "(", ")", "/", "7", "8", "9", "*", "4", "5", "6", "-", "1", "2", "3", "+", "0", ".", "="];
let expr = "";

function press(key) {
  if (key === "C") expr = "";
  else if (key === "=") {
    try {
      if (!/^[\\d+\\-*/().\\s]+$/.test(expr)) throw new Error();
      expr = String(Function('"use strict"; return (' + expr + ')')());
    } catch (e) {
      expr = "";
      display.value = "Ошибка";
      return;
    }
  } else expr += key;
  display.value = expr || "0";
}

layout.forEach(key => {
  const b = document.createElement("button");
  b.textContent = key;
  if ("/*-+=".includes(key)) b.className = "op";
  if (key === "0") b.className = "wide";
  b.onclick = () => press(key);
  document.getElementById("keys").append(b);
});
document.addEventListener("keydown", e => {
  if (/^[\\d+\\-*/().]$/.test(e.key)) press(e.key);
  if (e.key === "Enter") press("=");
  if (e.key === "Escape" || e.key === "Backspace") press("C");
});
</script>
</body>
</html>
''',
     cpp='''#include <iostream>

int main() {
    double a, b;
    char op;
    std::cout << "Введите выражение, например 2 + 3: ";
    std::cin >> a >> op >> b;
    switch (op) {
        case '+': std::cout << a + b << std::endl; break;
        case '-': std::cout << a - b << std::endl; break;
        case '*': std::cout << a * b << std::endl; break;
        case '/':
            if (b == 0) std::cout << "На ноль делить нельзя" << std::endl;
            else std::cout << a / b << std::endl;
            break;
        default: std::cout << "Неизвестная операция" << std::endl;
    }
    return 0;
}
''',
     javascript='''function calculate(a, op, b) {
  switch (op) {
    case "+": return a + b;
    case "-": return a - b;
    case "*": return a * b;
    case "/":
      if (b === 0) throw new Error("на ноль делить нельзя");
      return a / b;
    default: throw new Error("неизвестная операция " + op);
  }
}

console.log(calculate(2, "+", 3));   // 5
console.log(calculate(10, "/", 4));  // 2.5
console.log(calculate(6, "*", 7));   // 42
''')

task("fizzbuzz", r"fizz|физз", "FizzBuzz",
     "Числа от 1 до 100: вместо кратных 3 — Fizz, кратных 5 — Buzz, кратных 15 — FizzBuzz.",
     python='''for i in range(1, 101):
    if i % 15 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)
''',
     javascript='''for (let i = 1; i <= 100; i++) {
  if (i % 15 === 0) console.log("FizzBuzz");
  else if (i % 3 === 0) console.log("Fizz");
  else if (i % 5 === 0) console.log("Buzz");
  else console.log(i);
}
''',
     php='''<?php
for ($i = 1; $i <= 100; $i++) {
    if ($i % 15 === 0) echo "FizzBuzz\\n";
    elseif ($i % 3 === 0) echo "Fizz\\n";
    elseif ($i % 5 === 0) echo "Buzz\\n";
    else echo $i . "\\n";
}
''',
     cpp='''#include <iostream>

int main() {
    for (int i = 1; i <= 100; i++) {
        if (i % 15 == 0) std::cout << "FizzBuzz\\n";
        else if (i % 3 == 0) std::cout << "Fizz\\n";
        else if (i % 5 == 0) std::cout << "Buzz\\n";
        else std::cout << i << "\\n";
    }
}
''',
     java='''public class Main {
    public static void main(String[] args) {
        for (int i = 1; i <= 100; i++) {
            if (i % 15 == 0) System.out.println("FizzBuzz");
            else if (i % 3 == 0) System.out.println("Fizz");
            else if (i % 5 == 0) System.out.println("Buzz");
            else System.out.println(i);
        }
    }
}
''')

task("fibonacci", r"фибоначч|fibonacci", "Числа Фибоначчи",
     "Первые N чисел Фибоначчи: каждое следующее — сумма двух предыдущих.",
     python='''def fibonacci(n):
    """Вернуть список из первых n чисел Фибоначчи."""
    numbers = []
    a, b = 0, 1
    for _ in range(n):
        numbers.append(a)
        a, b = b, a + b
    return numbers


print(fibonacci(15))
''',
     javascript='''function fibonacci(n) {
  const numbers = [];
  let a = 0, b = 1;
  for (let i = 0; i < n; i++) {
    numbers.push(a);
    [a, b] = [b, a + b];
  }
  return numbers;
}

console.log(fibonacci(15).join(", "));
''',
     cpp='''#include <iostream>

int main() {
    long long a = 0, b = 1;
    for (int i = 0; i < 15; i++) {
        std::cout << a << " ";
        long long next = a + b;
        a = b;
        b = next;
    }
    std::cout << std::endl;
}
''',
     java='''public class Main {
    public static void main(String[] args) {
        long a = 0, b = 1;
        for (int i = 0; i < 15; i++) {
            System.out.print(a + " ");
            long next = a + b;
            a = b;
            b = next;
        }
    }
}
''',
     php='''<?php
function fibonacci(int $n): array {
    $numbers = [];
    [$a, $b] = [0, 1];
    for ($i = 0; $i < $n; $i++) {
        $numbers[] = $a;
        [$a, $b] = [$b, $a + $b];
    }
    return $numbers;
}

echo implode(", ", fibonacci(15));
''')

task("factorial", r"факториал|factorial", "Факториал",
     "Факториал n! = 1 · 2 · … · n. Два способа: циклом и рекурсией.",
     python='''def factorial(n):
    """Факториал циклом."""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def factorial_recursive(n):
    """Факториал рекурсией."""
    return 1 if n <= 1 else n * factorial_recursive(n - 1)


for n in (0, 1, 5, 10):
    print(f"{n}! = {factorial(n)} = {factorial_recursive(n)}")
''',
     javascript='''const factorial = n => (n <= 1 ? 1 : n * factorial(n - 1));

[0, 1, 5, 10].forEach(n => console.log(`${n}! = ${factorial(n)}`));
''',
     cpp='''#include <iostream>

unsigned long long factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

int main() {
    for (int n : {0, 1, 5, 10}) std::cout << n << "! = " << factorial(n) << std::endl;
}
''',
     java='''public class Main {
    static long factorial(int n) {
        return n <= 1 ? 1 : n * factorial(n - 1);
    }

    public static void main(String[] args) {
        for (int n : new int[]{0, 1, 5, 10}) System.out.println(n + "! = " + factorial(n));
    }
}
''')

task("prime", r"прост\w* числ|prime", "Простые числа",
     "Проверка числа на простоту и список простых чисел до 100 (решето Эратосфена).",
     python='''def is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def primes_up_to(limit):
    """Решето Эратосфена."""
    sieve = [True] * (limit + 1)
    sieve[0:2] = [False, False]
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    return [i for i, ok in enumerate(sieve) if ok]


print(is_prime(97), is_prime(100))
print(primes_up_to(100))
''',
     javascript='''function isPrime(n) {
  if (n < 2) return false;
  for (let i = 2; i * i <= n; i++) if (n % i === 0) return false;
  return true;
}

const primes = [];
for (let n = 2; n <= 100; n++) if (isPrime(n)) primes.push(n);
console.log(primes.join(", "));
''',
     cpp='''#include <iostream>

bool isPrime(int n) {
    if (n < 2) return false;
    for (int i = 2; i * i <= n; i++) if (n % i == 0) return false;
    return true;
}

int main() {
    for (int n = 2; n <= 100; n++) if (isPrime(n)) std::cout << n << " ";
    std::cout << std::endl;
}
''')

task("sort", r"сортир|sort|пузырьк", "Сортировка",
     "Сортировка пузырьком (чтобы понять алгоритм) и встроенная сортировка (для работы).",
     python='''def bubble_sort(items):
    """Сортировка пузырьком: меняем соседей местами, пока список не упорядочится."""
    items = list(items)
    for end in range(len(items) - 1, 0, -1):
        swapped = False
        for i in range(end):
            if items[i] > items[i + 1]:
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True
        if not swapped:
            break
    return items


numbers = [5, 3, 8, 1, 9, 2]
print("Пузырьком:", bubble_sort(numbers))
print("Встроенная:", sorted(numbers))
print("По убыванию:", sorted(numbers, reverse=True))
''',
     javascript='''function bubbleSort(items) {
  const a = [...items];
  for (let end = a.length - 1; end > 0; end--) {
    let swapped = false;
    for (let i = 0; i < end; i++) {
      if (a[i] > a[i + 1]) {
        [a[i], a[i + 1]] = [a[i + 1], a[i]];
        swapped = true;
      }
    }
    if (!swapped) break;
  }
  return a;
}

const numbers = [5, 3, 8, 1, 9, 2];
console.log("Пузырьком:", bubbleSort(numbers));
console.log("Встроенная:", [...numbers].sort((x, y) => x - y));
''',
     cpp='''#include <algorithm>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> numbers = {5, 3, 8, 1, 9, 2};
    std::sort(numbers.begin(), numbers.end());
    for (int n : numbers) std::cout << n << " ";
    std::cout << std::endl;
}
''')

task("binary_search", r"бинарн|двоичн\w* поиск|binary search", "Бинарный поиск",
     "Быстрый поиск в отсортированном списке: каждый шаг отбрасывает половину.",
     python='''def binary_search(items, target):
    """Индекс target в отсортированном списке или -1."""
    low, high = 0, len(items) - 1
    while low <= high:
        mid = (low + high) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


data = [1, 3, 5, 7, 9, 11, 13]
print(binary_search(data, 9))   # 4
print(binary_search(data, 4))   # -1
''',
     javascript='''function binarySearch(items, target) {
  let low = 0, high = items.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (items[mid] === target) return mid;
    if (items[mid] < target) low = mid + 1;
    else high = mid - 1;
  }
  return -1;
}

console.log(binarySearch([1, 3, 5, 7, 9, 11, 13], 9)); // 4
''')

task("files", r"файл|file", "Чтение и запись файла",
     "Запись текста в файл, дозапись и чтение построчно.",
     python='''from pathlib import Path

path = Path("notes.txt")

# Записать (файл создастся или перезапишется)
path.write_text("Первая строка\\nВторая строка\\n", encoding="utf-8")

# Дописать в конец
with path.open("a", encoding="utf-8") as f:
    f.write("Третья строка\\n")

# Прочитать построчно
with path.open(encoding="utf-8") as f:
    for number, line in enumerate(f, 1):
        print(number, line.rstrip())
''',
     javascript='''// Node.js
const fs = require("fs");

fs.writeFileSync("notes.txt", "Первая строка\\nВторая строка\\n", "utf8");
fs.appendFileSync("notes.txt", "Третья строка\\n", "utf8");

const lines = fs.readFileSync("notes.txt", "utf8").trim().split("\\n");
lines.forEach((line, i) => console.log(i + 1, line));
''',
     php='''<?php
$path = __DIR__ . "/notes.txt";
file_put_contents($path, "Первая строка\\nВторая строка\\n");
file_put_contents($path, "Третья строка\\n", FILE_APPEND);

foreach (file($path, FILE_IGNORE_NEW_LINES) as $i => $line) {
    echo ($i + 1) . " " . $line . "\\n";
}
''')

task("http", r"http.?запрос|запрос к|api|fetch|скачать страниц|requests|получить данные с сайта", "HTTP-запрос к API",
     "Запрос к открытому API и разбор JSON-ответа (пример — курс валют).",
     python='''import json
import urllib.request

url = "https://open.er-api.com/v6/latest/USD"
with urllib.request.urlopen(url, timeout=10) as response:
    data = json.loads(response.read().decode("utf-8"))

print("1 доллар =", data["rates"]["RUB"], "рублей")
print("1 доллар =", data["rates"]["EUR"], "евро")
''',
     javascript='''async function main() {
  const response = await fetch("https://open.er-api.com/v6/latest/USD");
  if (!response.ok) throw new Error("Ошибка " + response.status);
  const data = await response.json();
  console.log("1 доллар =", data.rates.RUB, "рублей");
  console.log("1 доллар =", data.rates.EUR, "евро");
}

main().catch(err => console.error(err.message));
''',
     php='''<?php
$json = file_get_contents("https://open.er-api.com/v6/latest/USD");
$data = json_decode($json, true);
echo "1 доллар = " . $data["rates"]["RUB"] . " рублей\\n";
''')

task("server", r"сервер|server|бэкенд|backend|flask", "Простой веб-сервер",
     "Минимальный веб-сервер: отвечает на запросы и отдаёт JSON по адресу /api/hello.",
     python='''from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/hello":
            body = json.dumps({"message": "Привет от сервера!"}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        else:
            body = "<h1>Сервер работает</h1><p>Попробуйте /api/hello</p>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


print("Сервер: http://localhost:8000")
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
''',
     javascript='''// Node.js: node server.js
const http = require("http");

http.createServer((req, res) => {
  if (req.url === "/api/hello") {
    res.writeHead(200, {"Content-Type": "application/json; charset=utf-8"});
    res.end(JSON.stringify({message: "Привет от сервера!"}));
  } else {
    res.writeHead(200, {"Content-Type": "text/html; charset=utf-8"});
    res.end("<h1>Сервер работает</h1><p>Попробуйте /api/hello</p>");
  }
}).listen(8000, () => console.log("Сервер: http://localhost:8000"));
''',
     php='''<?php
// Запуск: php -S localhost:8000 index.php
header("Content-Type: application/json; charset=utf-8");
$path = parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH);
if ($path === "/api/hello") {
    echo json_encode(["message" => "Привет от сервера!"], JSON_UNESCAPED_UNICODE);
} else {
    http_response_code(404);
    echo json_encode(["error" => "Не найдено"], JSON_UNESCAPED_UNICODE);
}
''')

task("telegram", r"телеграм|telegram|\bбот", "Телеграм-бот",
     "Эхо-бот для Telegram. Получите токен у @BotFather, установите библиотеку: pip install pyTelegramBotAPI.",
     python='''import os

import telebot  # pip install pyTelegramBotAPI

# Токен от @BotFather. Храните его в переменной окружения, а не в коде.
bot = telebot.TeleBot(os.environ["BOT_TOKEN"])


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message, "Привет! Я бот. Напишите что-нибудь — я повторю.")


@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, f"Вы написали: {message.text}")


print("Бот запущен")
bot.infinity_polling()
''')

task("todo", r"todo|туду|список дел|задач", "Список дел",
     "Список дел в браузере: добавление, отметка «сделано», удаление. Задачи сохраняются в браузере.",
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Список дел</title>
<style>
  body { margin: 0; background: #0b0b0c; color: #f3f1f1; font: 17px system-ui, sans-serif; display: flex; justify-content: center; padding: 40px 16px; }
  .app { width: 100%; max-width: 480px; }
  h1 { margin: 0 0 16px; }
  form { display: flex; gap: 8px; }
  input { flex: 1; padding: 12px; border-radius: 10px; border: 1px solid #2a2a2e; background: #151517; color: #fff; font: inherit; }
  button { padding: 12px 16px; border: 0; border-radius: 10px; background: #e10600; color: #fff; font: inherit; cursor: pointer; }
  ul { list-style: none; padding: 0; }
  li { display: flex; align-items: center; gap: 10px; padding: 12px; border-bottom: 1px solid #2a2a2e; }
  li.done span { text-decoration: line-through; color: #777; }
  li span { flex: 1; }
  li button { background: transparent; color: #999; padding: 4px 8px; }
</style>
</head>
<body>
<div class="app">
  <h1>Список дел</h1>
  <form id="form"><input id="text" placeholder="Новая задача" required><button>Добавить</button></form>
  <ul id="list"></ul>
</div>
<script>
let todos = [];
try { todos = JSON.parse(localStorage.getItem("todos") || "[]"); } catch (e) { /* начнём с пустого списка */ }

function save() { try { localStorage.setItem("todos", JSON.stringify(todos)); } catch (e) { /* список живёт до перезагрузки */ } }

function render() {
  const list = document.getElementById("list");
  list.innerHTML = "";
  todos.forEach((t, i) => {
    const li = document.createElement("li");
    if (t.done) li.className = "done";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = t.done;
    box.onchange = () => { t.done = box.checked; save(); render(); };
    const text = document.createElement("span");
    text.textContent = t.text;
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => { todos.splice(i, 1); save(); render(); };
    li.append(box, text, del);
    list.append(li);
  });
}

document.getElementById("form").onsubmit = e => {
  e.preventDefault();
  const input = document.getElementById("text");
  todos.push({text: input.value.trim(), done: false});
  input.value = "";
  save();
  render();
};
render();
</script>
</body>
</html>
''')

task("timer", r"таймер|секундомер|timer|stopwatch|часы|clock", "Секундомер и часы",
     "Страница с часами и секундомером: старт, пауза, сброс.",
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Секундомер</title>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b0b0c; color: #f3f1f1; font: 18px system-ui, sans-serif; text-align: center; }
  #clock { color: #999; }
  #time { font: 700 64px/1.2 ui-monospace, monospace; margin: 12px 0 20px; }
  button { padding: 12px 20px; margin: 0 4px; border: 0; border-radius: 10px; font: inherit; cursor: pointer; background: #26262a; color: #fff; }
  #start { background: #e10600; }
</style>
</head>
<body>
<div>
  <div id="clock"></div>
  <div id="time">00:00.00</div>
  <button id="start">Старт</button><button id="reset">Сброс</button>
</div>
<script>
let startedAt = 0, elapsed = 0, timer = null;
const show = ms => {
  const m = String(Math.floor(ms / 60000)).padStart(2, "0");
  const s = String(Math.floor(ms / 1000) % 60).padStart(2, "0");
  const cs = String(Math.floor(ms / 10) % 100).padStart(2, "0");
  document.getElementById("time").textContent = `${m}:${s}.${cs}`;
};
document.getElementById("start").onclick = function () {
  if (timer) {
    clearInterval(timer); timer = null; elapsed += Date.now() - startedAt; this.textContent = "Старт";
  } else {
    startedAt = Date.now(); timer = setInterval(() => show(elapsed + Date.now() - startedAt), 31); this.textContent = "Пауза";
  }
};
document.getElementById("reset").onclick = () => {
  clearInterval(timer); timer = null; elapsed = 0; show(0); document.getElementById("start").textContent = "Старт";
};
setInterval(() => { document.getElementById("clock").textContent = new Date().toLocaleTimeString("ru-RU"); }, 250);
</script>
</body>
</html>
''',
     python='''import time

seconds = int(input("Сколько секунд отсчитать? "))
for left in range(seconds, 0, -1):
    print(f"Осталось: {left} с")
    time.sleep(1)
print("Время вышло!")
''')

task("password", r"парол", "Генератор паролей",
     "Надёжные пароли с помощью модуля secrets: буквы, цифры и символы.",
     python='''import secrets
import string


def make_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)):
            return password


for _ in range(5):
    print(make_password())
''',
     javascript='''function makePassword(length = 16) {
  const alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*-_";
  const values = crypto.getRandomValues(new Uint32Array(length));
  return Array.from(values, v => alphabet[v % alphabet.length]).join("");
}

for (let i = 0; i < 5; i++) console.log(makePassword());
''')

task("rps", r"камень|ножниц|rock.?paper", "Камень, ножницы, бумага",
     "Игра против компьютера до трёх побед.",
     python='''import random

options = ["камень", "ножницы", "бумага"]
beats = {"камень": "ножницы", "ножницы": "бумага", "бумага": "камень"}
me = pc = 0

while me < 3 and pc < 3:
    choice = input("камень, ножницы или бумага? ").strip().lower()
    if choice not in options:
        print("Не понял, попробуйте ещё раз.")
        continue
    computer = random.choice(options)
    print("Компьютер:", computer)
    if choice == computer:
        print("Ничья")
    elif beats[choice] == computer:
        me += 1
        print("Вы выиграли раунд!")
    else:
        pc += 1
        print("Раунд за компьютером")
    print(f"Счёт {me}:{pc}")

print("Вы победили!" if me == 3 else "Победил компьютер")
''')

task("quiz", r"викторин|quiz|тест с вопрос", "Викторина",
     "Викторина с вопросами и подсчётом очков.",
     python='''questions = [
    ("Сколько будет 2 + 2 * 2?", "6"),
    ("Столица Франции?", "париж"),
    ("Какой язык программирования назван в честь комик-группы?", "python"),
]

score = 0
for question, answer in questions:
    reply = input(question + " ").strip().lower()
    if reply == answer:
        print("Верно!")
        score += 1
    else:
        print(f"Неверно, правильный ответ: {answer}")

print(f"Результат: {score} из {len(questions)}")
''')

task("temperature", r"температур|цельси|фаренгейт", "Перевод температуры",
     "Перевод между градусами Цельсия и Фаренгейта.",
     python='''def c_to_f(c):
    return c * 9 / 5 + 32


def f_to_c(f):
    return (f - 32) * 5 / 9


print(f"100 °C = {c_to_f(100):.1f} °F")
print(f"98.6 °F = {f_to_c(98.6):.1f} °C")
''',
     javascript='''const cToF = c => c * 9 / 5 + 32;
const fToC = f => (f - 32) * 5 / 9;

console.log(`100 °C = ${cToF(100).toFixed(1)} °F`);
console.log(`98.6 °F = ${fToC(98.6).toFixed(1)} °C`);
''')

task("palindrome", r"палиндром|переверн\w* строк|reverse", "Палиндромы и переворот строки",
     "Переворот строки и проверка на палиндром (без учёта пробелов и регистра).",
     python='''def is_palindrome(text):
    letters = [c.lower() for c in text if c.isalnum()]
    return letters == letters[::-1]


print("привет"[::-1])
print(is_palindrome("А роза упала на лапу Азора"))  # True
print(is_palindrome("Python"))                      # False
''',
     javascript='''const reverse = s => [...s].reverse().join("");
const isPalindrome = s => {
  const clean = s.toLowerCase().replace(/[^\\p{L}\\p{N}]/gu, "");
  return clean === reverse(clean);
};

console.log(reverse("привет"));
console.log(isPalindrome("А роза упала на лапу Азора")); // true
''')

task("wordcount", r"подсч\w* слов|частот|сколько раз", "Частота слов",
     "Подсчёт, какие слова встречаются в тексте чаще всего.",
     python='''from collections import Counter
import re

text = """Python — простой язык. Python любят за простоту,
а простой код легко читать."""

words = re.findall(r"\\w+", text.lower())
for word, count in Counter(words).most_common(5):
    print(f"{word}: {count}")
''')

task("class", r"класс|ооп|объект", "Классы и ООП",
     "Пример класса с конструктором, методами и наследованием.",
     python='''class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "..."

    def __str__(self):
        return f"{self.__class__.__name__} {self.name}: {self.speak()}"


class Dog(Animal):
    def speak(self):
        return "Гав!"


class Cat(Animal):
    def speak(self):
        return "Мяу!"


for pet in (Dog("Шарик"), Cat("Мурка")):
    print(pet)
''',
     java='''class Animal {
    protected String name;
    Animal(String name) { this.name = name; }
    String speak() { return "..."; }
}

class Dog extends Animal {
    Dog(String name) { super(name); }
    @Override String speak() { return "Гав!"; }
}

public class Main {
    public static void main(String[] args) {
        Animal pet = new Dog("Шарик");
        System.out.println(pet.name + ": " + pet.speak());
    }
}
''',
     javascript='''class Animal {
  constructor(name) { this.name = name; }
  speak() { return "..."; }
  toString() { return `${this.constructor.name} ${this.name}: ${this.speak()}`; }
}

class Dog extends Animal { speak() { return "Гав!"; } }
class Cat extends Animal { speak() { return "Мяу!"; } }

[new Dog("Шарик"), new Cat("Мурка")].forEach(p => console.log(String(p)));
''')

task("json", r"json", "Работа с JSON",
     "Преобразование данных в JSON и обратно.",
     python='''import json

user = {"name": "Артём", "age": 16, "skills": ["Python", "HTML"]}
text = json.dumps(user, ensure_ascii=False, indent=2)
print(text)

data = json.loads(text)
print(data["name"], "знает", ", ".join(data["skills"]))
''',
     javascript='''const user = {name: "Артём", age: 16, skills: ["Python", "HTML"]};
const text = JSON.stringify(user, null, 2);
console.log(text);

const data = JSON.parse(text);
console.log(`${data.name} знает ${data.skills.join(", ")}`);
''')

task("page", r"лендинг|страниц|сайт|визитк|веб-?страниц", "Веб-страница",
     "Современная адаптивная страница: шапка, главный блок, карточки и подвал. Сайт целиком удобнее делать в AI Studio.",
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Моя страница</title>
<style>
  :root { --bg: #0b0b0c; --fg: #f3f1f1; --muted: #9b9599; --accent: #e10600; --card: #151517; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg); font: 17px/1.6 system-ui, sans-serif; }
  header, section, footer { padding: 20px max(20px, calc(50% - 540px)); }
  header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2a2a2e; }
  nav a { color: var(--fg); margin-left: 16px; text-decoration: none; }
  .hero { padding-top: 90px; padding-bottom: 90px; }
  .hero h1 { font-size: clamp(36px, 7vw, 64px); margin: 0 0 12px; line-height: 1.05; }
  .hero p { color: var(--muted); max-width: 42ch; }
  .btn { display: inline-block; background: var(--accent); color: #fff; padding: 12px 22px; border-radius: 12px; text-decoration: none; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
  .card { background: var(--card); border: 1px solid #2a2a2e; border-radius: 16px; padding: 20px; }
  footer { color: var(--muted); border-top: 1px solid #2a2a2e; }
</style>
</head>
<body>
<header><b>Моя страница</b><nav><a href="#about">О нас</a><a href="#contacts">Контакты</a></nav></header>
<section class="hero">
  <h1>Добро пожаловать</h1>
  <p>Короткий рассказ о том, чем вы занимаетесь и почему это интересно.</p>
  <a class="btn" href="#about">Подробнее</a>
</section>
<section id="about">
  <h2>Что мы делаем</h2>
  <div class="cards">
    <div class="card"><h3>Быстро</h3><p>Результат без долгого ожидания.</p></div>
    <div class="card"><h3>Надёжно</h3><p>Проверенные решения.</p></div>
    <div class="card"><h3>Удобно</h3><p>Всё понятно с первого взгляда.</p></div>
  </div>
</section>
<footer id="contacts">© 2026 · hello@example.com</footer>
</body>
</html>
''')

task("form", r"форм[ау]|регистрац|валидац", "Форма с проверкой",
     "Форма регистрации с проверкой полей прямо в браузере.",
     html='''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Регистрация</title>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0b0b0c; color: #f3f1f1; font: 17px system-ui, sans-serif; }
  form { background: #151517; padding: 24px; border-radius: 16px; width: min(360px, 92vw); display: grid; gap: 12px; }
  label { display: grid; gap: 4px; font-size: 14px; color: #bbb; }
  input { padding: 11px; border-radius: 10px; border: 1px solid #2a2a2e; background: #0b0b0c; color: #fff; font: inherit; }
  input:invalid:not(:placeholder-shown) { border-color: #ff2a2a; }
  button { padding: 12px; border: 0; border-radius: 10px; background: #e10600; color: #fff; font: inherit; cursor: pointer; }
  #msg { min-height: 1.4em; margin: 0; }
</style>
</head>
<body>
<form id="form" novalidate>
  <h2>Регистрация</h2>
  <label>Имя<input name="name" required minlength="2" placeholder=" "></label>
  <label>Почта<input name="email" type="email" required placeholder=" "></label>
  <label>Пароль (от 8 символов)<input name="password" type="password" required minlength="8" placeholder=" "></label>
  <button>Зарегистрироваться</button>
  <p id="msg"></p>
</form>
<script>
document.getElementById("form").onsubmit = e => {
  e.preventDefault();
  const form = e.target, msg = document.getElementById("msg");
  const bad = [...form.elements].find(el => el.willValidate && !el.checkValidity());
  if (bad) {
    msg.style.color = "#ff6b6b";
    msg.textContent = bad.name === "email" ? "Проверьте почту" : bad.name === "password" ? "Пароль короче 8 символов" : "Введите имя";
    bad.focus();
    return;
  }
  msg.style.color = "#3ccf7a";
  msg.textContent = "Готово, " + form.name.value + "!";
};
</script>
</body>
</html>
''')

task("dice", r"кубик|dice", "Бросок кубика",
     "Бросок двух кубиков и статистика выпадений.",
     python='''import random
from collections import Counter

rolls = [random.randint(1, 6) + random.randint(1, 6) for _ in range(1000)]
stats = Counter(rolls)
for total in range(2, 13):
    print(f"{total:2}: {'#' * (stats[total] // 5)}")
''')

task("csv", r"csv|таблиц\w* excel|эксел", "Работа с CSV",
     "Запись и чтение CSV-таблицы, подсчёт суммы по столбцу.",
     python='''import csv

rows = [
    {"товар": "Хлеб", "цена": 60, "количество": 2},
    {"товар": "Молоко", "цена": 90, "количество": 1},
    {"товар": "Сыр", "цена": 350, "количество": 1},
]

with open("покупки.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["товар", "цена", "количество"])
    writer.writeheader()
    writer.writerows(rows)

total = 0
with open("покупки.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        cost = int(row["цена"]) * int(row["количество"])
        total += cost
        print(f"{row['товар']}: {cost} ₽")
print("Итого:", total, "₽")
''')

task("hello", r"hello|привет,? мир|перв\w* программ", "Hello, World",
     "Первая программа — вывод приветствия.",
     python='print("Привет, мир!")\n', javascript='console.log("Привет, мир!");\n',
     html='<!DOCTYPE html>\n<html lang="ru">\n<head><meta charset="UTF-8"><title>Привет</title></head>\n<body><h1>Привет, мир!</h1></body>\n</html>\n',
     php='<?php\necho "Привет, мир!";\n',
     cpp='#include <iostream>\n\nint main() {\n    std::cout << "Привет, мир!" << std::endl;\n}\n',
     java='public class Main {\n    public static void main(String[] args) {\n        System.out.println("Привет, мир!");\n    }\n}\n')

import codeapps  # noqa: E402  игры и приложения: тетрис, 2048, пианино, погода, конвертер валют…
import funcgen  # noqa: E402  небольшие функции по описанию: «функция, которая считает среднее»

codeapps.register(task)

ORDER = codeapps.ORDER_FIRST + ["snake", "tictactoe", "guess", "rps", "quiz", "calculator", "fizzbuzz", "fibonacci", "factorial", "prime",
         "binary_search", "sort", "telegram", "todo", "timer", "password", "temperature", "palindrome", "wordcount",
         "csv", "json", "http", "server", "files", "form", "dice", "class", "hello", "page"]


def find_task(text):
    low = (text or "").lower().replace("ё", "е")
    for key in ORDER:
        if re.search(T[key]["words"], low):
            return key
    return None


# Простые задачи, где своя сборка программы (codemind) лучше готового примера, если в просьбе есть условия
ALGO_KEYS = {"fizzbuzz", "fibonacci", "factorial", "prime", "sort", "palindrome", "wordcount", "temperature", "binary_search"}


def generate(prompt, lang=None):
    """Код по описанию: {"code", "lang", "filename", "title", "about"} или None.

    Порядок: готовые программы и игры → Rai сам собирает программу по условиям задачи и проверяет её запуском
    (codemind) → небольшие функции по образцу (funcgen)."""
    import codemind
    key = find_task(prompt)
    explicit = lang_from_text(prompt)
    smart = None
    if (not key or key in ALGO_KEYS) and explicit in (None, "python", "javascript", "typescript"):
        smart = codemind.generate(prompt, explicit or lang)
        own = smart and smart["ok"] and (not key or smart["score"] >= 4 or any(c["user"] for c in smart["checks"]))
        if own:
            return smart
    if not key:
        found = funcgen.generate(prompt, explicit or lang)
        if found and not (smart and smart["score"] >= 3):
            return found
        return smart or found
    t = T[key]
    explicit = lang_from_text(prompt)
    # Игры и страницы по умолчанию делаем для браузера — их сразу видно в предпросмотре
    browser_first = key in ("snake", "tictactoe", "todo", "timer", "form", "page") + codeapps.HTML_FIRST
    wanted = explicit or ("html" if browser_first else lang) or "python"
    if wanted == "typescript":
        wanted = "javascript"
    codes = t["codes"]
    note = ""
    if wanted not in codes:
        # Игры и страницы лучше всего работают в браузере, остальное — на Python
        fallback = "html" if "html" in codes else "python" if "python" in codes else next(iter(codes))
        names = {"python": "Python", "javascript": "JavaScript", "html": "HTML", "php": "PHP", "cpp": "C++",
                 "java": "Java", "csharp": "C#"}
        note = f"\n\nНа {names.get(wanted, wanted)} этой программы у меня пока нет — сделал на {names[fallback]}."
        wanted = fallback
    # main.py, а не json.py/csv.py — иначе файл перекроет стандартный модуль Python
    filename = {"html": "index.html", "java": "Main.java", "php": "index.php"}.get(wanted, f"main.{EXT.get(wanted, 'txt')}")
    return {"code": codes[wanted], "lang": wanted, "filename": filename, "title": t["title"],
            "about": f"**{t['title']}** — {t['about']}{note}"}


def help_text():
    games = "змейка, тетрис, 2048, пинг-понг, арканоид, крестики-нолики, «найди пару», угадай число"
    apps = "погода, конвертер валют, калькулятор, ИМТ, пианино, рисовалка, галерея, список дел, часы и секундомер"
    return ("Такую программу я пока не знаю. Вот что напишу сразу:\n\n"
            f"- **сайты** по описанию: «сайт кофейни «Зерно» в тёмных тонах с меню и отзывами», «сайт про космос»;\n"
            f"- **игры**: {games};\n- **приложения**: {apps};\n"
            "- **боты и сервер**: Telegram-бот, Discord-бот, веб-сервер, HTTP-запросы;\n"
            "- **функции**: «функция, которая считает среднее списка», «проверка високосного года», «шифр Цезаря»;\n"
            "- **задачи**: сортировка, Фибоначчи, простые числа, факториал, таблица умножения, работа с файлами, JSON, CSV.\n\n"
            "Язык можно выбрать: «… на JavaScript», «… на C++», «… на Java».")
