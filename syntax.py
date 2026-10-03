"""Синтаксис языков программирования: циклы, функции, условия, массивы, ввод, классы, словари.

«как сделать цикл в javascript», «функция на c++», «словарь в go», «класс в kotlin» — готовый проверенный пример.
"""

import re

import proglangs

# (заголовок, регулярное выражение темы, подсказка под примером)
TOPICS = {
    "loop": ("Циклы", r"цикл|\bloop\b|\bfor\b|\bwhile\b|\bforeach\b|перебрать|перебор|повтор",
             "`break` — выйти из цикла, `continue` — сразу к следующему шагу."),
    "function": ("Функции", r"функци|\bметод|\bdef\b|\bfunction\b|\bfunc\b|\bfn\b|процедур",
                 "Функция получает параметры и возвращает результат через `return` — её можно вызывать сколько угодно раз."),
    "condition": ("Условия", r"услови|\bif\b|\belse\b|\bесли\b|ветвлени|switch|\bwhen\b",
                  "Условия проверяются сверху вниз: выполняется первая подходящая ветка."),
    "array": ("Массивы и списки", r"массив|списк|список|\barray\b|\bvector\b|вектор|\blist\b|\bсрез|\bslice\b",
              "Счёт элементов почти везде начинается с 0 (в Lua и Pascal — с 1)."),
    "input": ("Ввод с клавиатуры", r"ввод|ввести|считать с клав|прочитать с клав|\binput\b|scanf|\bcin\b|readline|"
                                  r"от пользовател|с клавиатур",
              "Ввод — это всегда текст: число нужно преобразовать (int, parseInt, toInt…)."),
    "class": ("Классы и объекты", r"класс|объект|\bооп\b|\bclass\b|\bstruct\b|структур",
              "Класс — чертёж, объект — сделанная по нему вещь со своими данными."),
    "dict": ("Словари (ключ → значение)", r"словар|ассоциативн|\bmap\b|хеш.?таблиц|hashmap|dictionary|\bdict\b",
             "Поиск по ключу работает мгновенно, даже если записей миллионы."),
}

_HL = {"Python": "python", "JavaScript": "js", "TypeScript": "ts", "Java": "java", "C#": "csharp", "C++": "cpp",
       "C": "c", "Go": "go", "PHP": "php", "Rust": "rust", "Kotlin": "kotlin", "Swift": "swift", "Ruby": "ruby",
       "Pascal": "pascal", "Bash": "bash", "Lua": "lua", "Dart": "dart"}

S = {topic: {} for topic in TOPICS}

# ---------------------------------------------------------------- циклы
S["loop"]["Python"] = '''for i in range(5):
    print(i)              # 0 1 2 3 4

n = 3
while n > 0:
    print(n)
    n -= 1

for x in ["а", "б", "в"]:
    print(x)'''
S["loop"]["JavaScript"] = '''for (let i = 0; i < 5; i++) {
  console.log(i);         // 0 1 2 3 4
}

let n = 3;
while (n > 0) {
  console.log(n);
  n--;
}

for (const x of ["а", "б", "в"]) {
  console.log(x);
}'''
S["loop"]["TypeScript"] = '''for (let i = 0; i < 5; i++) {
  console.log(i);
}

const items: string[] = ["а", "б", "в"];
for (const x of items) {
  console.log(x);
}

items.forEach((x, i) => console.log(i, x));'''
S["loop"]["Java"] = '''public class Main {
    public static void main(String[] args) {
        for (int i = 0; i < 5; i++) {
            System.out.println(i);
        }

        int n = 3;
        while (n > 0) {
            System.out.println(n);
            n--;
        }

        String[] items = {"а", "б", "в"};
        for (String x : items) {
            System.out.println(x);
        }
    }
}'''
S["loop"]["C#"] = '''for (int i = 0; i < 5; i++)
{
    Console.WriteLine(i);
}

int n = 3;
while (n > 0)
{
    Console.WriteLine(n);
    n--;
}

string[] items = { "а", "б", "в" };
foreach (string x in items)
{
    Console.WriteLine(x);
}'''
S["loop"]["C++"] = '''#include <iostream>
#include <string>
#include <vector>

int main() {
    for (int i = 0; i < 5; i++) {
        std::cout << i << "\\n";
    }

    int n = 3;
    while (n > 0) {
        std::cout << n << "\\n";
        n--;
    }

    std::vector<std::string> items = {"а", "б", "в"};
    for (const auto& x : items) {
        std::cout << x << "\\n";
    }
}'''
S["loop"]["C"] = '''#include <stdio.h>

int main(void) {
    for (int i = 0; i < 5; i++) {
        printf("%d\\n", i);
    }

    int n = 3;
    while (n > 0) {
        printf("%d\\n", n);
        n--;
    }
    return 0;
}'''
S["loop"]["Go"] = '''package main

import "fmt"

func main() {
	for i := 0; i < 5; i++ {
		fmt.Println(i)
	}

	n := 3
	for n > 0 { // в Go нет while — это тоже for
		fmt.Println(n)
		n--
	}

	for i, x := range []string{"а", "б", "в"} {
		fmt.Println(i, x)
	}
}'''
S["loop"]["PHP"] = '''<?php
for ($i = 0; $i < 5; $i++) {
    echo $i, "\\n";
}

$n = 3;
while ($n > 0) {
    echo $n, "\\n";
    $n--;
}

foreach (["а", "б", "в"] as $i => $x) {
    echo "$i: $x\\n";
}'''
S["loop"]["Rust"] = '''fn main() {
    for i in 0..5 {
        println!("{}", i);
    }

    let mut n = 3;
    while n > 0 {
        println!("{}", n);
        n -= 1;
    }

    for (i, x) in ["а", "б", "в"].iter().enumerate() {
        println!("{} {}", i, x);
    }
}'''
S["loop"]["Kotlin"] = '''fun main() {
    for (i in 0 until 5) {
        println(i)
    }

    var n = 3
    while (n > 0) {
        println(n)
        n--
    }

    for ((i, x) in listOf("а", "б", "в").withIndex()) {
        println("$i $x")
    }
}'''
S["loop"]["Swift"] = '''for i in 0..<5 {
    print(i)
}

var n = 3
while n > 0 {
    print(n)
    n -= 1
}

for (i, x) in ["а", "б", "в"].enumerated() {
    print(i, x)
}'''
S["loop"]["Ruby"] = '''5.times do |i|
  puts i
end

n = 3
while n > 0
  puts n
  n -= 1
end

["а", "б", "в"].each_with_index { |x, i| puts "#{i} #{x}" }'''
S["loop"]["Pascal"] = '''program Loops;
var
  i, n: integer;
begin
  for i := 0 to 4 do
    writeln(i);

  n := 3;
  while n > 0 do
  begin
    writeln(n);
    n := n - 1;
  end;

  repeat
    n := n + 1;
  until n = 3;
  writeln(n);
end.'''
S["loop"]["Bash"] = '''for i in {0..4}; do
  echo "$i"
done

n=3
while [ "$n" -gt 0 ]; do
  echo "$n"
  n=$((n - 1))
done

for x in а б в; do
  echo "$x"
done'''
S["loop"]["Lua"] = '''for i = 0, 4 do
  print(i)
end

local n = 3
while n > 0 do
  print(n)
  n = n - 1
end

for i, x in ipairs({"а", "б", "в"}) do
  print(i, x)
end'''
S["loop"]["Dart"] = '''void main() {
  for (var i = 0; i < 5; i++) {
    print(i);
  }

  var n = 3;
  while (n > 0) {
    print(n);
    n--;
  }

  for (final x in ['а', 'б', 'в']) {
    print(x);
  }
}'''

# ---------------------------------------------------------------- функции
S["function"]["Python"] = '''def add(a, b):
    return a + b


def greet(name, greeting="Привет"):   # значение по умолчанию
    return f"{greeting}, {name}!"


print(add(2, 3))          # 5
print(greet("Аня"))       # Привет, Аня!'''
S["function"]["JavaScript"] = '''function add(a, b) {
  return a + b;
}

const mul = (a, b) => a * b;            // стрелочная функция

function greet(name, greeting = "Привет") {
  return `${greeting}, ${name}!`;
}

console.log(add(2, 3), mul(2, 3));      // 5 6
console.log(greet("Аня"));              // Привет, Аня!'''
S["function"]["TypeScript"] = '''function add(a: number, b: number): number {
  return a + b;
}

const mul = (a: number, b: number): number => a * b;

console.log(add(2, 3), mul(2, 3));  // 5 6'''
S["function"]["Java"] = '''public class Main {
    static int add(int a, int b) {
        return a + b;
    }

    public static void main(String[] args) {
        System.out.println(add(2, 3));  // 5
    }
}'''
S["function"]["C#"] = '''static int Add(int a, int b)
{
    return a + b;
}

static int Mul(int a, int b) => a * b;   // короткая запись

Console.WriteLine(Add(2, 3));  // 5
Console.WriteLine(Mul(2, 3));  // 6'''
S["function"]["C++"] = '''#include <iostream>

int add(int a, int b) {
    return a + b;
}

int main() {
    auto mul = [](int a, int b) { return a * b; };  // лямбда
    std::cout << add(2, 3) << " " << mul(2, 3) << "\\n";  // 5 6
}'''
S["function"]["C"] = '''#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main(void) {
    printf("%d\\n", add(2, 3));  /* 5 */
    return 0;
}'''
S["function"]["Go"] = '''package main

import "fmt"

func add(a, b int) int {
	return a + b
}

func divmod(a, b int) (int, int) { // функция может вернуть несколько значений
	return a / b, a % b
}

func main() {
	fmt.Println(add(2, 3)) // 5
	q, r := divmod(7, 2)
	fmt.Println(q, r) // 3 1
}'''
S["function"]["PHP"] = '''<?php
function add(int $a, int $b): int {
    return $a + $b;
}

$mul = fn($a, $b) => $a * $b;   // стрелочная функция

echo add(2, 3), " ", $mul(2, 3);  // 5 6'''
S["function"]["Rust"] = '''fn add(a: i32, b: i32) -> i32 {
    a + b // последнее выражение без «;» — это результат
}

fn main() {
    let mul = |a: i32, b: i32| a * b; // замыкание
    println!("{} {}", add(2, 3), mul(2, 3)); // 5 6
}'''
S["function"]["Kotlin"] = '''fun add(a: Int, b: Int): Int {
    return a + b
}

fun mul(a: Int, b: Int) = a * b  // короткая запись

fun main() {
    println(add(2, 3))  // 5
    println(mul(2, 3))  // 6
}'''
S["function"]["Swift"] = '''func add(_ a: Int, _ b: Int) -> Int {
    return a + b
}

func greet(name: String) -> String {
    return "Привет, \\(name)!"
}

print(add(2, 3))            // 5
print(greet(name: "Аня"))   // Привет, Аня!'''
S["function"]["Ruby"] = '''def add(a, b)
  a + b # последнее выражение — результат
end

mul = ->(a, b) { a * b } # лямбда

puts add(2, 3)      # 5
puts mul.call(2, 3) # 6'''
S["function"]["Pascal"] = '''program Functions;

function Add(a, b: integer): integer;
begin
  Add := a + b;
end;

procedure Greet(name: string);
begin
  writeln('Привет, ', name, '!');
end;

begin
  writeln(Add(2, 3));  { 5 }
  Greet('Аня');
end.'''
S["function"]["Bash"] = '''add() {
  echo $(( $1 + $2 ))
}

result=$(add 2 3)
echo "$result"  # 5'''
S["function"]["Lua"] = '''local function add(a, b)
  return a + b
end

local mul = function(a, b) return a * b end

print(add(2, 3), mul(2, 3))  -- 5 6'''
S["function"]["Dart"] = '''int add(int a, int b) {
  return a + b;
}

int mul(int a, int b) => a * b;

void main() {
  print(add(2, 3)); // 5
  print(mul(2, 3)); // 6
}'''

# ---------------------------------------------------------------- условия
S["condition"]["Python"] = '''age = 17
if age >= 18:
    print("Взрослый")
elif age >= 14:
    print("Подросток")
else:
    print("Ребёнок")

status = "можно" if age >= 18 else "нельзя"   # условие в одну строку'''
S["condition"]["JavaScript"] = '''const age = 17;
if (age >= 18) {
  console.log("Взрослый");
} else if (age >= 14) {
  console.log("Подросток");
} else {
  console.log("Ребёнок");
}

const access = age >= 18 ? "можно" : "нельзя";  // тернарный оператор
console.log(access);'''
S["condition"]["TypeScript"] = '''const age: number = 17;
if (age >= 18) {
  console.log("Взрослый");
} else if (age >= 14) {
  console.log("Подросток");
} else {
  console.log("Ребёнок");
}

const access: string = age >= 18 ? "можно" : "нельзя";
console.log(access);'''
S["condition"]["Java"] = '''public class Main {
    public static void main(String[] args) {
        int age = 17;
        if (age >= 18) {
            System.out.println("Взрослый");
        } else if (age >= 14) {
            System.out.println("Подросток");
        } else {
            System.out.println("Ребёнок");
        }

        String status = age >= 18 ? "можно" : "нельзя";
        System.out.println(status);
    }
}'''
S["condition"]["C#"] = '''int age = 17;
if (age >= 18)
{
    Console.WriteLine("Взрослый");
}
else if (age >= 14)
{
    Console.WriteLine("Подросток");
}
else
{
    Console.WriteLine("Ребёнок");
}

string status = age >= 18 ? "можно" : "нельзя";
Console.WriteLine(status);'''
S["condition"]["C++"] = '''#include <iostream>

int main() {
    int age = 17;
    if (age >= 18) {
        std::cout << "Взрослый\\n";
    } else if (age >= 14) {
        std::cout << "Подросток\\n";
    } else {
        std::cout << "Ребёнок\\n";
    }
}'''
S["condition"]["C"] = '''#include <stdio.h>

int main(void) {
    int age = 17;
    if (age >= 18) {
        printf("Взрослый\\n");
    } else if (age >= 14) {
        printf("Подросток\\n");
    } else {
        printf("Ребёнок\\n");
    }
    return 0;
}'''
S["condition"]["Go"] = '''package main

import "fmt"

func main() {
	age := 17
	if age >= 18 {
		fmt.Println("Взрослый")
	} else if age >= 14 {
		fmt.Println("Подросток")
	} else {
		fmt.Println("Ребёнок")
	}
}'''
S["condition"]["PHP"] = '''<?php
$age = 17;
if ($age >= 18) {
    echo "Взрослый";
} elseif ($age >= 14) {
    echo "Подросток";
} else {
    echo "Ребёнок";
}

$status = $age >= 18 ? "можно" : "нельзя";
echo "\\n", $status;'''
S["condition"]["Rust"] = '''fn main() {
    let age = 17;
    if age >= 18 {
        println!("Взрослый");
    } else if age >= 14 {
        println!("Подросток");
    } else {
        println!("Ребёнок");
    }

    let status = if age >= 18 { "можно" } else { "нельзя" };
    println!("{}", status);
}'''
S["condition"]["Kotlin"] = '''fun main() {
    val age = 17
    if (age >= 18) {
        println("Взрослый")
    } else if (age >= 14) {
        println("Подросток")
    } else {
        println("Ребёнок")
    }

    val who = when {        // when — удобная замена цепочке if
        age >= 18 -> "взрослый"
        age >= 14 -> "подросток"
        else -> "ребёнок"
    }
    println(who)
}'''
S["condition"]["Swift"] = '''let age = 17
if age >= 18 {
    print("Взрослый")
} else if age >= 14 {
    print("Подросток")
} else {
    print("Ребёнок")
}

let status = age >= 18 ? "можно" : "нельзя"
print(status)'''
S["condition"]["Ruby"] = '''age = 17
if age >= 18
  puts "Взрослый"
elsif age >= 14
  puts "Подросток"
else
  puts "Ребёнок"
end

status = age >= 18 ? "можно" : "нельзя"
puts status'''
S["condition"]["Pascal"] = '''program Conditions;
var
  age: integer;
begin
  age := 17;
  if age >= 18 then
    writeln('Взрослый')
  else if age >= 14 then
    writeln('Подросток')
  else
    writeln('Ребёнок');
end.'''
S["condition"]["Bash"] = '''age=17
if [ "$age" -ge 18 ]; then
  echo "Взрослый"
elif [ "$age" -ge 14 ]; then
  echo "Подросток"
else
  echo "Ребёнок"
fi'''
S["condition"]["Lua"] = '''local age = 17
if age >= 18 then
  print("Взрослый")
elseif age >= 14 then
  print("Подросток")
else
  print("Ребёнок")
end'''
S["condition"]["Dart"] = '''void main() {
  var age = 17;
  if (age >= 18) {
    print('Взрослый');
  } else if (age >= 14) {
    print('Подросток');
  } else {
    print('Ребёнок');
  }

  var status = age >= 18 ? 'можно' : 'нельзя';
  print(status);
}'''

# ---------------------------------------------------------------- массивы и списки
S["array"]["Python"] = '''nums = [3, 1, 2]
nums.append(5)            # добавить в конец
print(nums[0])            # 3 — первый элемент
print(nums[-1])           # 5 — последний
print(len(nums))          # 4 — длина
nums.sort()               # [1, 2, 3, 5]
doubled = [x * 2 for x in nums]   # [2, 4, 6, 10]
print(nums, doubled)'''
S["array"]["JavaScript"] = '''const nums = [3, 1, 2];
nums.push(5);                       // добавить в конец
console.log(nums[0]);               // 3 — первый элемент
console.log(nums.length);           // 4 — длина
nums.sort((a, b) => a - b);         // [1, 2, 3, 5] (без функции сортирует как строки!)
const doubled = nums.map((x) => x * 2);   // [2, 4, 6, 10]
const big = nums.filter((x) => x > 2);    // [3, 5]
console.log(nums, doubled, big);'''
S["array"]["TypeScript"] = '''const nums: number[] = [3, 1, 2];
nums.push(5);
console.log(nums[0], nums.length);      // 3 4
nums.sort((a, b) => a - b);             // [1, 2, 3, 5]
const doubled: number[] = nums.map((x) => x * 2);
console.log(doubled);'''
S["array"]["Java"] = '''import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        int[] fixed = {3, 1, 2};                 // массив фиксированной длины
        System.out.println(fixed.length);        // 3

        List<Integer> nums = new ArrayList<>(List.of(3, 1, 2));  // список, который растёт
        nums.add(5);
        Collections.sort(nums);                  // [1, 2, 3, 5]
        System.out.println(nums.get(0) + " " + nums.size());  // 1 4
    }
}'''
S["array"]["C#"] = '''int[] fixedArr = { 3, 1, 2 };                 // массив фиксированной длины
Console.WriteLine(fixedArr.Length);             // 3

var nums = new List<int> { 3, 1, 2 };           // список, который растёт
nums.Add(5);
nums.Sort();                                    // 1, 2, 3, 5
Console.WriteLine($"{nums[0]} {nums.Count}");   // 1 4'''
S["array"]["C++"] = '''#include <algorithm>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> nums = {3, 1, 2};
    nums.push_back(5);                        // добавить в конец
    std::sort(nums.begin(), nums.end());      // 1 2 3 5
    std::cout << nums[0] << " " << nums.size() << "\\n";  // 1 4
}'''
S["array"]["C"] = '''#include <stdio.h>

int main(void) {
    int nums[] = {3, 1, 2, 5};
    int n = sizeof(nums) / sizeof(nums[0]);   /* длина: 4 */
    for (int i = 0; i < n; i++) {
        printf("%d ", nums[i]);
    }
    printf("\\n");
    return 0;
}'''
S["array"]["Go"] = '''package main

import (
	"fmt"
	"sort"
)

func main() {
	nums := []int{3, 1, 2} // срез — массив, который растёт
	nums = append(nums, 5)
	sort.Ints(nums)                 // [1 2 3 5]
	fmt.Println(nums[0], len(nums)) // 1 4
}'''
S["array"]["PHP"] = '''<?php
$nums = [3, 1, 2];
$nums[] = 5;                        // добавить в конец
sort($nums);                        // [1, 2, 3, 5]
echo $nums[0], " ", count($nums);   // 1 4
$doubled = array_map(fn($x) => $x * 2, $nums);
print_r($doubled);'''
S["array"]["Rust"] = '''fn main() {
    let mut nums = vec![3, 1, 2]; // Vec — массив, который растёт
    nums.push(5);
    nums.sort(); // [1, 2, 3, 5]
    let doubled: Vec<i32> = nums.iter().map(|x| x * 2).collect();
    println!("{} {} {:?}", nums[0], nums.len(), doubled);
}'''
S["array"]["Kotlin"] = '''fun main() {
    val nums = mutableListOf(3, 1, 2)
    nums.add(5)
    nums.sort()                          // [1, 2, 3, 5]
    println("${nums[0]} ${nums.size}")   // 1 4
    println(nums.map { it * 2 })         // [2, 4, 6, 10]
}'''
S["array"]["Swift"] = '''var nums = [3, 1, 2]
nums.append(5)
nums.sort()                     // [1, 2, 3, 5]
print(nums[0], nums.count)      // 1 4
print(nums.map { $0 * 2 })      // [2, 4, 6, 10]'''
S["array"]["Ruby"] = '''nums = [3, 1, 2]
nums << 5                   # добавить в конец
nums.sort!                  # [1, 2, 3, 5]
puts nums[0], nums.length   # 1, 4
p nums.map { |x| x * 2 }    # [2, 4, 6, 10]'''
S["array"]["Pascal"] = '''program Arrays;
var
  nums: array[1..4] of integer = (3, 1, 2, 5);
  i: integer;
begin
  for i := 1 to 4 do
    write(nums[i], ' ');
  writeln;
end.'''
S["array"]["Bash"] = '''nums=(3 1 2)
nums+=(5)                 # добавить в конец
echo "${nums[0]}"         # 3 — первый элемент
echo "${#nums[@]}"        # 4 — длина
for x in "${nums[@]}"; do
  echo "$x"
done'''
S["array"]["Lua"] = '''local nums = {3, 1, 2}
table.insert(nums, 5)     -- добавить в конец
table.sort(nums)          -- {1, 2, 3, 5}
print(nums[1], #nums)     -- 1 4 (в Lua счёт с 1)'''
S["array"]["Dart"] = '''void main() {
  final nums = [3, 1, 2];
  nums.add(5);
  nums.sort();                          // [1, 2, 3, 5]
  print('${nums[0]} ${nums.length}');   // 1 4
  print(nums.map((x) => x * 2).toList());
}'''

# ---------------------------------------------------------------- ввод
S["input"]["Python"] = '''name = input("Как вас зовут? ")
age = int(input("Сколько вам лет? "))
print(f"Привет, {name}! Через год вам будет {age + 1}.")'''
S["input"]["JavaScript"] = '''// В браузере:
// const name = prompt("Как вас зовут?");

// В Node.js:
const readline = require("readline");
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
rl.question("Как вас зовут? ", (name) => {
  console.log(`Привет, ${name}!`);
  rl.close();
});'''
S["input"]["Java"] = '''import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("Как вас зовут? ");
        String name = in.nextLine();
        System.out.print("Сколько вам лет? ");
        int age = in.nextInt();
        System.out.println("Привет, " + name + "! Через год вам будет " + (age + 1) + ".");
    }
}'''
S["input"]["C#"] = '''Console.Write("Как вас зовут? ");
string name = Console.ReadLine() ?? "";
Console.Write("Сколько вам лет? ");
int age = int.Parse(Console.ReadLine() ?? "0");
Console.WriteLine($"Привет, {name}! Через год вам будет {age + 1}.");'''
S["input"]["C++"] = '''#include <iostream>
#include <string>

int main() {
    std::string name;
    int age;
    std::cout << "Как вас зовут? ";
    std::getline(std::cin, name);
    std::cout << "Сколько вам лет? ";
    std::cin >> age;
    std::cout << "Привет, " << name << "! Через год вам будет " << age + 1 << ".\\n";
}'''
S["input"]["C"] = '''#include <stdio.h>

int main(void) {
    char name[100];
    int age;
    printf("Как вас зовут? ");
    scanf("%99s", name);
    printf("Сколько вам лет? ");
    scanf("%d", &age);
    printf("Привет, %s! Через год вам будет %d.\\n", name, age + 1);
    return 0;
}'''
S["input"]["Go"] = '''package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

func main() {
	reader := bufio.NewReader(os.Stdin)
	fmt.Print("Как вас зовут? ")
	name, _ := reader.ReadString('\\n')
	name = strings.TrimSpace(name)

	fmt.Print("Сколько вам лет? ")
	line, _ := reader.ReadString('\\n')
	age, _ := strconv.Atoi(strings.TrimSpace(line))
	fmt.Printf("Привет, %s! Через год вам будет %d.\\n", name, age+1)
}'''
S["input"]["PHP"] = '''<?php
// В консоли:
$name = readline("Как вас зовут? ");
echo "Привет, $name!\\n";

// На сайте — из формы <form method="post"><input name="name"></form>:
// $name = $_POST["name"] ?? "гость";
// echo "Привет, " . htmlspecialchars($name);'''
S["input"]["Rust"] = '''use std::io;

fn main() {
    let mut name = String::new();
    println!("Как вас зовут?");
    io::stdin().read_line(&mut name).expect("не удалось прочитать");
    let name = name.trim();

    let mut age = String::new();
    println!("Сколько вам лет?");
    io::stdin().read_line(&mut age).expect("не удалось прочитать");
    let age: u32 = age.trim().parse().unwrap_or(0);

    println!("Привет, {}! Через год вам будет {}.", name, age + 1);
}'''
S["input"]["Kotlin"] = '''fun main() {
    print("Как вас зовут? ")
    val name = readln()
    print("Сколько вам лет? ")
    val age = readln().toInt()
    println("Привет, $name! Через год вам будет ${age + 1}.")
}'''
S["input"]["Swift"] = '''print("Как вас зовут?")
let name = readLine() ?? ""
print("Сколько вам лет?")
let age = Int(readLine() ?? "") ?? 0
print("Привет, \\(name)! Через год вам будет \\(age + 1).")'''
S["input"]["Ruby"] = '''print "Как вас зовут? "
name = gets.chomp
print "Сколько вам лет? "
age = gets.to_i
puts "Привет, #{name}! Через год вам будет #{age + 1}."'''
S["input"]["Pascal"] = '''program Input;
var
  name: string;
  age: integer;
begin
  write('Как вас зовут? ');
  readln(name);
  write('Сколько вам лет? ');
  readln(age);
  writeln('Привет, ', name, '! Через год вам будет ', age + 1, '.');
end.'''
S["input"]["Bash"] = '''read -p "Как вас зовут? " name
read -p "Сколько вам лет? " age
echo "Привет, $name! Через год вам будет $((age + 1))."'''
S["input"]["Lua"] = '''io.write("Как вас зовут? ")
local name = io.read("*l")
io.write("Сколько вам лет? ")
local age = io.read("*n")
print("Привет, " .. name .. "! Через год вам будет " .. (age + 1) .. ".")'''
S["input"]["Dart"] = '''import 'dart:io';

void main() {
  stdout.write('Как вас зовут? ');
  final name = stdin.readLineSync() ?? '';
  stdout.write('Сколько вам лет? ');
  final age = int.tryParse(stdin.readLineSync() ?? '') ?? 0;
  print('Привет, $name! Через год вам будет ${age + 1}.');
}'''

# ---------------------------------------------------------------- классы
S["class"]["Python"] = '''class Cat:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def speak(self):
        return f"{self.name}: мяу!"


class Kitten(Cat):                 # наследование
    def speak(self):
        return f"{self.name}: мяу-мяу!"


print(Cat("Том", 3).speak())       # Том: мяу!
print(Kitten("Пушок", 1).speak())  # Пушок: мяу-мяу!'''
S["class"]["JavaScript"] = '''class Cat {
  constructor(name, age) {
    this.name = name;
    this.age = age;
  }

  speak() {
    return `${this.name}: мяу!`;
  }
}

class Kitten extends Cat {          // наследование
  speak() {
    return `${this.name}: мяу-мяу!`;
  }
}

console.log(new Cat("Том", 3).speak());       // Том: мяу!
console.log(new Kitten("Пушок", 1).speak());  // Пушок: мяу-мяу!'''
S["class"]["TypeScript"] = '''class Cat {
  constructor(public name: string, private age: number) {}

  speak(): string {
    return `${this.name}: мяу!`;
  }
}

const tom = new Cat("Том", 3);
console.log(tom.speak());  // Том: мяу!'''
S["class"]["Java"] = '''class Cat {
    private final String name;
    private final int age;

    Cat(String name, int age) {
        this.name = name;
        this.age = age;
    }

    String speak() {
        return name + ": мяу!";
    }
}

public class Main {
    public static void main(String[] args) {
        Cat tom = new Cat("Том", 3);
        System.out.println(tom.speak());  // Том: мяу!
    }
}'''
S["class"]["C#"] = '''var tom = new Cat("Том", 3);
Console.WriteLine(tom.Speak());  // Том: мяу!

class Cat
{
    public string Name { get; }
    public int Age { get; }

    public Cat(string name, int age)
    {
        Name = name;
        Age = age;
    }

    public string Speak() => $"{Name}: мяу!";
}'''
S["class"]["C++"] = '''#include <iostream>
#include <string>
#include <utility>

class Cat {
public:
    Cat(std::string name, int age) : name_(std::move(name)), age_(age) {}

    std::string speak() const {
        return name_ + ": мяу!";
    }

    int age() const { return age_; }

private:
    std::string name_;
    int age_;
};

int main() {
    Cat tom("Том", 3);
    std::cout << tom.speak() << "\\n";  // Том: мяу!
}'''
S["class"]["Go"] = '''package main

import "fmt"

// В Go нет классов: структура + методы
type Cat struct {
	Name string
	Age  int
}

func (c Cat) Speak() string {
	return c.Name + ": мяу!"
}

func main() {
	tom := Cat{Name: "Том", Age: 3}
	fmt.Println(tom.Speak()) // Том: мяу!
}'''
S["class"]["PHP"] = '''<?php
class Cat {
    public function __construct(
        public string $name,
        private int $age,
    ) {}

    public function speak(): string {
        return "{$this->name}: мяу!";
    }
}

$tom = new Cat("Том", 3);
echo $tom->speak();  // Том: мяу!'''
S["class"]["Rust"] = '''// В Rust нет классов: структура + impl
struct Cat {
    name: String,
    age: u32,
}

impl Cat {
    fn new(name: &str, age: u32) -> Self {
        Cat { name: name.to_string(), age }
    }

    fn speak(&self) -> String {
        format!("{} ({} г.): мяу!", self.name, self.age)
    }
}

fn main() {
    let tom = Cat::new("Том", 3);
    println!("{}", tom.speak()); // Том (3 г.): мяу!
}'''
S["class"]["Kotlin"] = '''class Cat(val name: String, private val age: Int) {
    fun speak() = "$name: мяу!"
}

data class Point(val x: Int, val y: Int)  // класс для данных: equals, toString — сами

fun main() {
    val tom = Cat("Том", 3)
    println(tom.speak())     // Том: мяу!
    println(Point(1, 2))     // Point(x=1, y=2)
}'''
S["class"]["Swift"] = '''class Cat {
    let name: String
    let age: Int

    init(name: String, age: Int) {
        self.name = name
        self.age = age
    }

    func speak() -> String {
        return "\\(name): мяу!"
    }
}

let tom = Cat(name: "Том", age: 3)
print(tom.speak())  // Том: мяу!'''
S["class"]["Ruby"] = '''class Cat
  attr_reader :name

  def initialize(name, age)
    @name = name
    @age = age
  end

  def speak
    "#{@name}: мяу!"
  end
end

tom = Cat.new("Том", 3)
puts tom.speak  # Том: мяу!'''
S["class"]["Lua"] = '''-- В Lua классы делают из таблиц и метатаблиц
local Cat = {}
Cat.__index = Cat

function Cat.new(name, age)
  return setmetatable({name = name, age = age}, Cat)
end

function Cat:speak()
  return self.name .. ": мяу!"
end

local tom = Cat.new("Том", 3)
print(tom:speak())  -- Том: мяу!'''
S["class"]["Dart"] = '''class Cat {
  final String name;
  final int age;

  Cat(this.name, this.age);

  String speak() => '$name: мяу!';
}

void main() {
  final tom = Cat('Том', 3);
  print(tom.speak()); // Том: мяу!
}'''
S["class"]["Pascal"] = '''program Classes;
{$mode objfpc}

type
  TCat = class
  private
    FName: string;
  public
    constructor Create(const AName: string);
    function Speak: string;
  end;

constructor TCat.Create(const AName: string);
begin
  FName := AName;
end;

function TCat.Speak: string;
begin
  Result := FName + ': мяу!';
end;

var
  Tom: TCat;
begin
  Tom := TCat.Create('Том');
  writeln(Tom.Speak);
  Tom.Free;
end.'''

# ---------------------------------------------------------------- словари
S["dict"]["Python"] = '''ages = {"Аня": 17, "Макс": 20}
ages["Оля"] = 19                  # добавить
print(ages["Аня"])                # 17
print(ages.get("Петя", 0))        # 0 — если ключа нет
for name, age in ages.items():
    print(name, age)'''
S["dict"]["JavaScript"] = '''const ages = { "Аня": 17, "Макс": 20 };   // объект
ages["Оля"] = 19;
console.log(ages["Аня"]);                  // 17
console.log(ages["Петя"] ?? 0);            // 0 — если ключа нет

const map = new Map([["Аня", 17]]);        // Map — для любых ключей
map.set("Макс", 20);
for (const [name, age] of map) console.log(name, age);'''
S["dict"]["TypeScript"] = '''const ages: Record<string, number> = { "Аня": 17, "Макс": 20 };
ages["Оля"] = 19;

const map = new Map<string, number>([["Аня", 17]]);
map.set("Макс", 20);
console.log(map.get("Аня"), ages["Оля"]);  // 17 19'''
S["dict"]["Java"] = '''import java.util.HashMap;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        Map<String, Integer> ages = new HashMap<>();
        ages.put("Аня", 17);
        ages.put("Макс", 20);
        System.out.println(ages.get("Аня"));               // 17
        System.out.println(ages.getOrDefault("Петя", 0));  // 0
        for (Map.Entry<String, Integer> e : ages.entrySet()) {
            System.out.println(e.getKey() + " " + e.getValue());
        }
    }
}'''
S["dict"]["C#"] = '''var ages = new Dictionary<string, int> { ["Аня"] = 17, ["Макс"] = 20 };
ages["Оля"] = 19;
Console.WriteLine(ages["Аня"]);  // 17
Console.WriteLine(ages.TryGetValue("Петя", out int age) ? age : 0);  // 0
foreach (var (name, a) in ages) Console.WriteLine($"{name} {a}");'''
S["dict"]["C++"] = '''#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> ages = {{"Аня", 17}, {"Макс", 20}};
    ages["Оля"] = 19;
    std::cout << ages["Аня"] << "\\n";  // 17
    for (const auto& [name, age] : ages) {  // C++17
        std::cout << name << " " << age << "\\n";
    }
}'''
S["dict"]["Go"] = '''package main

import "fmt"

func main() {
	ages := map[string]int{"Аня": 17, "Макс": 20}
	ages["Оля"] = 19
	fmt.Println(ages["Аня"]) // 17
	if age, ok := ages["Петя"]; ok {
		fmt.Println(age)
	} else {
		fmt.Println("Пети нет")
	}
	for name, age := range ages {
		fmt.Println(name, age)
	}
}'''
S["dict"]["PHP"] = '''<?php
$ages = ["Аня" => 17, "Макс" => 20];
$ages["Оля"] = 19;
echo $ages["Аня"], "\\n";           // 17
echo $ages["Петя"] ?? 0, "\\n";     // 0 — если ключа нет
foreach ($ages as $name => $age) {
    echo "$name $age\\n";
}'''
S["dict"]["Rust"] = '''use std::collections::HashMap;

fn main() {
    let mut ages = HashMap::new();
    ages.insert("Аня", 17);
    ages.insert("Макс", 20);
    println!("{:?}", ages.get("Аня"));               // Some(17)
    println!("{}", ages.get("Петя").unwrap_or(&0));  // 0
    for (name, age) in &ages {
        println!("{} {}", name, age);
    }
}'''
S["dict"]["Kotlin"] = '''fun main() {
    val ages = mutableMapOf("Аня" to 17, "Макс" to 20)
    ages["Оля"] = 19
    println(ages["Аня"])                   // 17
    println(ages.getOrDefault("Петя", 0))  // 0
    for ((name, age) in ages) println("$name $age")
}'''
S["dict"]["Swift"] = '''var ages = ["Аня": 17, "Макс": 20]
ages["Оля"] = 19
print(ages["Аня"] ?? 0)    // 17
print(ages["Петя"] ?? 0)   // 0
for (name, age) in ages {
    print(name, age)
}'''
S["dict"]["Ruby"] = '''ages = { "Аня" => 17, "Макс" => 20 }
ages["Оля"] = 19
puts ages["Аня"]             # 17
puts ages.fetch("Петя", 0)   # 0
ages.each { |name, age| puts "#{name} #{age}" }'''
S["dict"]["Lua"] = '''local ages = {["Аня"] = 17, ["Макс"] = 20}
ages["Оля"] = 19
print(ages["Аня"])           -- 17
print(ages["Петя"] or 0)     -- 0
for name, age in pairs(ages) do
  print(name, age)
end'''
S["dict"]["Dart"] = '''void main() {
  final ages = {'Аня': 17, 'Макс': 20};
  ages['Оля'] = 19;
  print(ages['Аня']);         // 17
  print(ages['Петя'] ?? 0);   // 0
  ages.forEach((name, age) => print('$name $age'));
}'''
S["dict"]["Bash"] = '''declare -A ages=([Аня]=17 [Макс]=20)   # нужен bash 4+
ages[Оля]=19
echo "${ages[Аня]}"           # 17
for name in "${!ages[@]}"; do
  echo "$name ${ages[$name]}"
done'''

# «Как … в/на <языке>» — вопрос о синтаксисе; «напиши функцию, которая считает …» — уже задача для генератора кода
_HOWTO_RE = re.compile(r"^\s*(?:а\s+)?(?:как|пример\w*|покажи|синтаксис|объясни|что такое|как выглядит|как пишется|"
                       r"как объявить|как создать|как сделать|как написать)\b", re.I)
_TASK_RE = re.compile(r"котор\w+|чтобы|\bдля (?:подсч|вычисл|поиск|сорт)|посчита|вычисл|найд|сортир|факториал|"
                      r"фибоначчи|прост\w+ чис|палиндром|калькулятор|игр[уа]|бот", re.I)


def topic_of(text: str):
    low = (text or "").lower().replace("ё", "е")
    for key, (_, pattern, _) in TOPICS.items():
        if re.search(pattern, low):
            return key
    return None


def answer(text: str):
    """Пример конструкции на нужном языке или None."""
    if not text or _TASK_RE.search(text):
        return None
    entry = proglangs.find_language(re.sub(r"\b(?:в|для)\s+(?=\w)", "на ", text, flags=re.I))
    if not entry:
        return None
    topic = topic_of(text)
    if not topic:
        return None
    if not _HOWTO_RE.search(text) and len(text.split()) > 6:
        return None
    lang = entry[0]
    title, _, hint = TOPICS[topic]
    code = S[topic].get(lang)
    if not code:
        have = ", ".join(sorted(S[topic]))
        return (f"Готового примера «{title.lower()}» для {lang} у меня нет. Есть для: {have}. "
                f"Включите Rai Нейро — нейросеть напишет пример на {lang}.")
    others = [name for name in S[topic] if name != lang]
    return (f"## {title} на {lang}\n\n```{_HL.get(lang, 'text')}\n{code}\n```\n\n{hint}\n\n"
            f"*Этот же пример есть на других языках: {', '.join(others[:8])} — спросите, например, "
            f"«{title.split()[0].lower()} на {others[0]}».*")
