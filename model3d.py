"""Rai делает 3D-модели сам, без внешних сервисов.

По описанию («сделай 3д модель снеговика», «3d красная машина», «модель дома») Rai собирает сцену
из простых фигур (куб, шар, цилиндр, конус, тор) и отдаёт:
  • scene — список фигур {geo, args, pos, rot, scale, color} для просмотра прямо в чате
    (свой маленький 3D-движок на canvas, модель можно крутить мышкой/пальцем);
  • blender — готовый скрипт на Python (bpy), который собирает ту же модель в Blender;
  • title, about — название и короткое описание.

Система координат: Y — вверх. Для Blender (там вверх — Z) координаты переставляются при выводе скрипта.
Всё своё и офлайн: никаких库 и сетевых вызовов.
"""

import math
import random
import re

# ------------------------------------------------------------------ цвета
COLORS = {
    "красн": "#e23b2e", "алый": "#e8281a", "бордов": "#7d1f1f", "оранжев": "#f08a24", "рыж": "#d86a2a",
    "жёлт": "#f2c53d", "желт": "#f2c53d", "золот": "#e3b23c", "зелён": "#3fa34d", "зелен": "#3fa34d",
    "салатов": "#86c548", "голуб": "#5ec5e8", "синий": "#2f6fe0", "син": "#2f6fe0", "фиолетов": "#8b5cf6",
    "сиренев": "#a98bf0", "розов": "#ef7fb0", "корич": "#8a5a2b", "беж": "#d8c4a0", "сер": "#9aa0aa",
    "чёрн": "#2a2a30", "черн": "#2a2a30", "бел": "#f3f1ee", "бирюз": "#2fc5b0", "пурпур": "#b0338c",
}
_DEFAULT = "#8b5cf6"


def color_of(text, fallback=_DEFAULT):
    low = (text or "").lower().replace("ё", "е")
    for key, hexv in COLORS.items():
        if key.replace("ё", "е") in low:
            return hexv
    return fallback


def _o(geo, args, pos=(0, 0, 0), rot=(0, 0, 0), scale=None, color=_DEFAULT):
    """Один объект сцены."""
    obj = {"geo": geo, "args": args, "pos": [round(v, 3) for v in pos], "rot": [round(v, 2) for v in rot], "color": color}
    if scale:
        obj["scale"] = [round(v, 3) for v in scale]
    return obj


# ------------------------------------------------------------------ готовые модели (каждая — функция от основного цвета)

def _snowman(c):
    white = "#f3f4f6"
    return [
        _o("sphere", {"r": 1.0}, (0, 1.0, 0), color=white),
        _o("sphere", {"r": 0.72}, (0, 2.25, 0), color=white),
        _o("sphere", {"r": 0.5}, (0, 3.2, 0), color=white),
        _o("cone", {"r": 0.12, "h": 0.5}, (0, 3.2, 0.5), rot=(90, 0, 0), color="#f08a24"),       # нос-морковка
        _o("sphere", {"r": 0.07}, (-0.18, 3.33, 0.44), color="#2a2a30"),                          # глаза
        _o("sphere", {"r": 0.07}, (0.18, 3.33, 0.44), color="#2a2a30"),
        _o("cylinder", {"r": 0.42, "h": 0.42}, (0, 3.75, 0), color=c if c != _DEFAULT else "#2a2a30"),   # шляпа
        _o("cylinder", {"r": 0.6, "h": 0.06}, (0, 3.55, 0), color=c if c != _DEFAULT else "#2a2a30"),    # поля
    ]


def _house(c):
    wall = c if c != _DEFAULT else "#e3d5b8"
    return [
        _o("box", {"w": 2.4, "h": 1.8, "d": 2.4}, (0, 0.9, 0), color=wall),
        _o("cone", {"r": 1.9, "h": 1.3}, (0, 2.55, 0), rot=(0, 45, 0), color="#c0392b"),   # крыша-пирамида (4 грани)
        _o("box", {"w": 0.6, "h": 1.0, "d": 0.1}, (0, 0.5, 1.21), color="#7a4a1e"),         # дверь
        _o("box", {"w": 0.5, "h": 0.5, "d": 0.1}, (-0.7, 1.1, 1.21), color="#8fd0e8"),      # окна
        _o("box", {"w": 0.5, "h": 0.5, "d": 0.1}, (0.7, 1.1, 1.21), color="#8fd0e8"),
    ]


def _tree(c):
    crown = c if c != _DEFAULT else "#3fa34d"
    return [
        _o("cylinder", {"r": 0.28, "h": 1.4}, (0, 0.7, 0), color="#8a5a2b"),
        _o("sphere", {"r": 1.1}, (0, 2.1, 0), color=crown),
        _o("sphere", {"r": 0.8}, (0.7, 1.8, 0.3), color=crown),
        _o("sphere", {"r": 0.8}, (-0.6, 1.9, -0.3), color=crown),
    ]


def _fir(c):
    green = c if c != _DEFAULT else "#2f8f4e"
    return [
        _o("cylinder", {"r": 0.22, "h": 0.8}, (0, 0.4, 0), color="#7a4a1e"),
        _o("cone", {"r": 1.3, "h": 1.3}, (0, 1.45, 0), color=green),
        _o("cone", {"r": 1.0, "h": 1.2}, (0, 2.2, 0), color=green),
        _o("cone", {"r": 0.7, "h": 1.1}, (0, 2.95, 0), color=green),
        _o("sphere", {"r": 0.16}, (0, 3.6, 0), color="#f2c53d"),   # звезда-макушка (шарик)
    ]


def _mushroom(c):
    cap = c if c != _DEFAULT else "#e23b2e"
    return [
        _o("cylinder", {"r": 0.35, "h": 1.1}, (0, 0.55, 0), color="#efe6d6"),
        _o("sphere", {"r": 0.95}, (0, 1.2, 0), scale=(1, 0.6, 1), color=cap),
        _o("sphere", {"r": 0.12}, (0.4, 1.35, 0.3), color="#f3f1ee"),
        _o("sphere", {"r": 0.1}, (-0.35, 1.3, -0.2), color="#f3f1ee"),
    ]


def _rocket(c):
    body = c if c != _DEFAULT else "#f3f1ee"
    fin = "#e23b2e"
    objs = [
        _o("cylinder", {"r": 0.5, "h": 2.4}, (0, 1.6, 0), color=body),
        _o("cone", {"r": 0.5, "h": 1.0}, (0, 3.3, 0), color=fin),
        _o("sphere", {"r": 0.26}, (0, 1.9, 0.5), color="#8fd0e8"),          # иллюминатор
        _o("cone", {"r": 0.35, "h": 0.6}, (0, 0.3, 0), rot=(180, 0, 0), color="#f08a24"),  # сопло-пламя снизу
    ]
    for a in (0, 90, 180, 270):                                             # крылья-стабилизаторы
        import math
        x, z = 0.55 * math.sin(math.radians(a)), 0.55 * math.cos(math.radians(a))
        objs.append(_o("box", {"w": 0.12, "h": 0.9, "d": 0.6}, (x, 0.6, z), rot=(0, a, 0), color=fin))
    return objs


def _car(c):
    body = c if c != _DEFAULT else "#2f6fe0"
    wheel = "#2a2a30"
    objs = [
        _o("box", {"w": 2.6, "h": 0.6, "d": 1.3}, (0, 0.6, 0), color=body),
        _o("box", {"w": 1.4, "h": 0.6, "d": 1.15}, (-0.1, 1.15, 0), color=body),
        _o("box", {"w": 1.2, "h": 0.42, "d": 1.0}, (-0.1, 1.16, 0), color="#9fd3ea"),   # окна
    ]
    for x in (-0.85, 0.85):
        for z in (-0.72, 0.72):
            objs.append(_o("cylinder", {"r": 0.38, "h": 0.25}, (x, 0.38, z), rot=(90, 0, 0), color=wheel))
    return objs


def _robot(c):
    body = c if c != _DEFAULT else "#9aa0aa"
    return [
        _o("box", {"w": 1.2, "h": 1.3, "d": 0.7}, (0, 1.4, 0), color=body),
        _o("box", {"w": 0.9, "h": 0.8, "d": 0.7}, (0, 2.5, 0), color=body),
        _o("sphere", {"r": 0.12}, (-0.2, 2.6, 0.36), color="#5ec5e8"),
        _o("sphere", {"r": 0.12}, (0.2, 2.6, 0.36), color="#5ec5e8"),
        _o("cylinder", {"r": 0.07, "h": 0.3}, (0, 3.05, 0), color="#e23b2e"),   # антенна
        _o("sphere", {"r": 0.1}, (0, 3.25, 0), color="#e23b2e"),
        _o("cylinder", {"r": 0.16, "h": 1.0}, (-0.8, 1.4, 0), color="#6b7079"),  # руки
        _o("cylinder", {"r": 0.16, "h": 1.0}, (0.8, 1.4, 0), color="#6b7079"),
        _o("cylinder", {"r": 0.2, "h": 0.9}, (-0.35, 0.45, 0), color="#6b7079"),  # ноги
        _o("cylinder", {"r": 0.2, "h": 0.9}, (0.35, 0.45, 0), color="#6b7079"),
    ]


def _table(c):
    wood = c if c != _DEFAULT else "#a9743f"
    objs = [_o("box", {"w": 2.4, "h": 0.18, "d": 1.4}, (0, 1.4, 0), color=wood)]
    for x in (-1.0, 1.0):
        for z in (-0.5, 0.5):
            objs.append(_o("cylinder", {"r": 0.12, "h": 1.3}, (x, 0.65, z), color=wood))
    return objs


def _chair(c):
    wood = c if c != _DEFAULT else "#c0894b"
    objs = [
        _o("box", {"w": 1.0, "h": 0.14, "d": 1.0}, (0, 1.0, 0), color=wood),
        _o("box", {"w": 1.0, "h": 1.0, "d": 0.14}, (0, 1.55, -0.43), color=wood),
    ]
    for x in (-0.4, 0.4):
        for z in (-0.4, 0.4):
            objs.append(_o("cylinder", {"r": 0.08, "h": 1.0}, (x, 0.5, z), color=wood))
    return objs


def _donut(c):
    return [
        _o("torus", {"r": 1.0, "tube": 0.45}, (0, 1.0, 0), rot=(90, 0, 0), color=c if c != _DEFAULT else "#f0a6c0"),
        _o("torus", {"r": 1.0, "tube": 0.47}, (0, 1.12, 0), rot=(90, 0, 0), scale=(1, 1, 0.5), color="#f3e0a0"),  # глазурь
    ]


def _star(c):
    # «звёздочка» из двух повёрнутых тонких коробок + центр (простая узнаваемая форма)
    col = c if c != _DEFAULT else "#f2c53d"
    objs = [_o("sphere", {"r": 0.45}, (0, 1.2, 0), color=col)]
    for a in (0, 72, 144, 216, 288):
        import math
        objs.append(_o("cone", {"r": 0.28, "h": 0.9}, (0.7 * math.sin(math.radians(a)), 1.2, 0.7 * math.cos(math.radians(a))),
                       rot=(90, a, 0), color=col))
    return objs


def _heart(c):
    col = c if c != _DEFAULT else "#e23b2e"
    return [
        _o("sphere", {"r": 0.6}, (-0.5, 1.7, 0), color=col),
        _o("sphere", {"r": 0.6}, (0.5, 1.7, 0), color=col),
        _o("cone", {"r": 0.95, "h": 1.5}, (0, 0.75, 0), rot=(180, 0, 0), color=col),
    ]


def _animal(c):
    """Обобщённое четвероногое: туловище, голова, уши, лапы, хвост — узнаётся как зверёк."""
    body = c if c != _DEFAULT else "#b07a46"
    objs = [
        _o("sphere", {"r": 0.9}, (0, 1.1, 0), scale=(1.5, 0.95, 1.0), color=body),      # туловище
        _o("sphere", {"r": 0.6}, (1.25, 1.5, 0), color=body),                            # голова
        _o("cone", {"r": 0.18, "h": 0.35}, (1.1, 2.05, 0.22), color=body),               # ушки
        _o("cone", {"r": 0.18, "h": 0.35}, (1.1, 2.05, -0.22), color=body),
        _o("sphere", {"r": 0.09}, (1.7, 1.55, 0.2), color="#2a2a30"),                     # глаза
        _o("sphere", {"r": 0.09}, (1.7, 1.55, -0.2), color="#2a2a30"),
        _o("sphere", {"r": 0.12}, (1.82, 1.4, 0), color="#2a2a30"),                        # нос
    ]
    for x in (-0.7, 0.7):
        for z in (-0.45, 0.45):
            objs.append(_o("cylinder", {"r": 0.16, "h": 0.8}, (x, 0.4, z), color=body))    # лапы
    objs.append(_o("cylinder", {"r": 0.09, "h": 0.8}, (-1.35, 1.35, 0), rot=(0, 0, 55), color=body))  # хвост
    return objs


def _bird(c):
    body = c if c != _DEFAULT else "#f2c53d"
    return [
        _o("sphere", {"r": 0.75}, (0, 1.1, 0), scale=(1.0, 1.15, 1.0), color=body),
        _o("sphere", {"r": 0.45}, (0, 2.0, 0.15), color=body),
        _o("cone", {"r": 0.14, "h": 0.4}, (0, 2.0, 0.6), rot=(90, 0, 0), color="#f08a24"),   # клюв
        _o("sphere", {"r": 0.07}, (0.18, 2.15, 0.4), color="#2a2a30"),
        _o("sphere", {"r": 0.07}, (-0.18, 2.15, 0.4), color="#2a2a30"),
        _o("cone", {"r": 0.4, "h": 0.8}, (0, 1.0, -0.8), rot=(70, 0, 0), color=body),         # хвост
        _o("cylinder", {"r": 0.05, "h": 0.4}, (0.2, 0.3, 0), color="#f08a24"),
        _o("cylinder", {"r": 0.05, "h": 0.4}, (-0.2, 0.3, 0), color="#f08a24"),
    ]


def _fish(c):
    body = c if c != _DEFAULT else "#2fb2e0"
    return [
        _o("sphere", {"r": 0.9}, (0, 1.2, 0), scale=(1.6, 1.0, 0.7), color=body),
        _o("cone", {"r": 0.6, "h": 0.8}, (-1.5, 1.2, 0), rot=(0, 0, 90), color=body),          # хвост
        _o("cone", {"r": 0.4, "h": 0.6}, (0, 2.0, 0), color=body),                              # плавник сверху
        _o("sphere", {"r": 0.1}, (1.1, 1.35, 0.3), color="#2a2a30"),                            # глаз
    ]


def _human(c):
    body = c if c != _DEFAULT else "#3b7dd8"
    skin = "#f0c27b"
    return [
        _o("sphere", {"r": 0.42}, (0, 2.5, 0), color=skin),                       # голова
        _o("cylinder", {"r": 0.45, "h": 1.3}, (0, 1.5, 0), color=body),           # туловище
        _o("cylinder", {"r": 0.13, "h": 1.1}, (-0.62, 1.55, 0), rot=(0, 0, 12), color=body),  # руки
        _o("cylinder", {"r": 0.13, "h": 1.1}, (0.62, 1.55, 0), rot=(0, 0, -12), color=body),
        _o("cylinder", {"r": 0.17, "h": 1.1}, (-0.22, 0.55, 0), color="#2a3550"),  # ноги
        _o("cylinder", {"r": 0.17, "h": 1.1}, (0.22, 0.55, 0), color="#2a3550"),
    ]


def _plane(c):
    body = c if c != _DEFAULT else "#dfe6ee"
    return [
        _o("cylinder", {"r": 0.4, "h": 3.2}, (0, 1.4, 0), rot=(90, 0, 0), color=body),   # фюзеляж
        _o("cone", {"r": 0.4, "h": 0.7}, (0, 1.4, 1.9), rot=(90, 0, 0), color=body),      # нос
        _o("box", {"w": 3.6, "h": 0.12, "d": 0.8}, (0, 1.4, 0), color=body),              # крылья
        _o("box", {"w": 1.4, "h": 0.1, "d": 0.5}, (0, 1.5, -1.4), color=body),            # хвост-крыло
        _o("box", {"w": 0.1, "h": 0.7, "d": 0.5}, (0, 1.85, -1.4), color="#c0392b"),      # киль
    ]


def _boat(c):
    body = c if c != _DEFAULT else "#c0392b"
    return [
        _o("sphere", {"r": 1.3}, (0, 0.9, 0), scale=(1.6, 0.5, 0.8), color=body),         # корпус
        _o("box", {"w": 1.0, "h": 0.6, "d": 0.8}, (-0.2, 1.4, 0), color="#f3f1ee"),        # рубка
        _o("cylinder", {"r": 0.06, "h": 1.6}, (0.6, 1.9, 0), color="#8a5a2b"),             # мачта
        _o("cone", {"r": 0.5, "h": 0.9}, (0.6, 1.95, 0), rot=(0, 0, -90), color="#f3f1ee"),  # парус
    ]


def _flower(c):
    petal = c if c != _DEFAULT else "#ef7fb0"
    objs = [
        _o("cylinder", {"r": 0.08, "h": 2.0}, (0, 1.0, 0), color="#3fa34d"),
        _o("sphere", {"r": 0.3}, (0, 2.1, 0), color="#f2c53d"),                             # серединка
        _o("cone", {"r": 0.25, "h": 0.6}, (0.45, 1.0, 0.25), rot=(0, 30, 60), color="#3fa34d"),  # лист
    ]
    for a in range(0, 360, 60):
        objs.append(_o("sphere", {"r": 0.28}, (0.55 * math.sin(math.radians(a)), 2.1, 0.55 * math.cos(math.radians(a))), color=petal))
    return objs


def _apple(c):
    col = c if c != _DEFAULT else "#e23b2e"
    return [
        _o("sphere", {"r": 0.9}, (0, 1.0, 0), scale=(1.0, 0.92, 1.0), color=col),
        _o("cylinder", {"r": 0.06, "h": 0.4}, (0, 1.85, 0), color="#7a4a1e"),
        _o("sphere", {"r": 0.18}, (0.25, 1.95, 0), scale=(1.4, 0.4, 1.0), color="#3fa34d"),
    ]


def _cake(c):
    base = c if c != _DEFAULT else "#f0c9a0"
    return [
        _o("cylinder", {"r": 1.1, "h": 0.6}, (0, 0.6, 0), color=base),
        _o("cylinder", {"r": 0.85, "h": 0.55}, (0, 1.15, 0), color="#f3e0a0"),
        _o("cylinder", {"r": 0.6, "h": 0.5}, (0, 1.65, 0), color="#ef7fb0"),
        _o("cylinder", {"r": 0.05, "h": 0.4}, (0, 2.05, 0), color="#e23b2e"),                # свеча
        _o("cone", {"r": 0.08, "h": 0.18}, (0, 2.32, 0), color="#f2c53d"),                    # огонёк
    ]


def _cup(c):
    col = c if c != _DEFAULT else "#f3f1ee"
    return [
        _o("cylinder", {"r": 0.6, "h": 1.0}, (0, 0.6, 0), color=col),
        _o("cylinder", {"r": 0.5, "h": 0.1}, (0, 1.06, 0), color="#6b4a2b"),                  # «кофе»
        _o("torus", {"r": 0.33, "tube": 0.08}, (0.72, 0.6, 0), color=col),                    # ручка
    ]


def _bottle(c):
    col = c if c != _DEFAULT else "#2fa36a"
    return [
        _o("cylinder", {"r": 0.45, "h": 1.5}, (0, 0.75, 0), color=col),
        _o("cone", {"r": 0.45, "h": 0.4}, (0, 1.6, 0), color=col),
        _o("cylinder", {"r": 0.15, "h": 0.5}, (0, 1.95, 0), color=col),
        _o("cylinder", {"r": 0.17, "h": 0.2}, (0, 2.25, 0), color="#e8e8e8"),                 # крышка
    ]


def _tower(c):
    col = c if c != _DEFAULT else "#9aa0aa"
    objs, y, r = [], 0.0, 1.0
    for i in range(4):
        h = 1.0
        objs.append(_o("box", {"w": r * 2, "h": h, "d": r * 2}, (0, y + h / 2, 0), color=col))
        y += h
        r *= 0.8
    objs.append(_o("cone", {"r": r * 1.6, "h": 1.0}, (0, y + 0.5, 0), color="#c0392b"))        # крыша
    objs.append(_o("cylinder", {"r": 0.03, "h": 0.6}, (0, y + 1.3, 0), color="#7a4a1e"))
    return objs


def _planet(c):
    col = c if c != _DEFAULT else "#d9a05b"
    return [
        _o("sphere", {"r": 1.1}, (0, 1.3, 0), color=col),
        _o("torus", {"r": 1.8, "tube": 0.12}, (0, 1.3, 0), rot=(78, 0, 0), color="#e8d7a0"),   # кольцо
    ]


def _sword(c):
    blade = "#cfd6de"
    grip = c if c != _DEFAULT else "#7a4a1e"
    return [
        _o("box", {"w": 0.14, "h": 2.2, "d": 0.03}, (0, 2.1, 0), color=blade),                 # клинок
        _o("cone", {"r": 0.1, "h": 0.25}, (0, 3.25, 0), color=blade),                           # остриё
        _o("box", {"w": 0.7, "h": 0.12, "d": 0.12}, (0, 0.95, 0), color="#d4af37"),             # гарда
        _o("cylinder", {"r": 0.07, "h": 0.6}, (0, 0.6, 0), color=grip),                         # рукоять
        _o("sphere", {"r": 0.1}, (0, 0.28, 0), color="#d4af37"),                                 # навершие
    ]


def _pencil(c):
    col = c if c != _DEFAULT else "#f2c53d"
    return [
        _o("cylinder", {"r": 0.16, "h": 2.4}, (0, 1.3, 0), color=col),
        _o("cone", {"r": 0.16, "h": 0.4}, (0, 2.7, 0), color="#e8d2b0"),
        _o("cone", {"r": 0.05, "h": 0.12}, (0, 2.95, 0), color="#2a2a30"),                      # грифель
        _o("cylinder", {"r": 0.16, "h": 0.2}, (0, 0.1, 0), color="#ef7fb0"),                    # ластик
    ]


# Обобщённые строители по категориям слова: regex → (название-подпись, функция)
CATEGORY = [
    (r"кот|кошк|собак|\bпёс\b|\bпес\b|щен|лев\b|львиц|тигр|леопард|гепард|пантер|рыс[иь]|конь|лошад|пони|осёл|осл[иоа]|"
     r"коров|\bбык\b|тел[её]н|свин|поросён|овц|бараш|козл|\bкоз[аыу]|медвед|мишк|волк|лис[аиоу]|заяц|зайч|крол|слон|жираф|"
     r"зебр|бегемот|носорог|олен|лос[ья]|кабан|панд|коал|кенгуру|белк|\bёж|\bеж[аиоуы]|крыс|мыш|хомяк|бобр|выдр|обезьян|"
     r"горилл|верблюд|\bлам[аыу]|\bяк\b|бизон|буйвол|антилоп|динозавр|дракон|зверь|животн", "Зверёк", _animal),
    (r"птиц|попуг|\bорёл|\bорл|сов[аыиу]|пингвин|утк|\bгус|куриц|петух|цыпл|воробь|голуб|ворон|сорок|синиц|ласточк|"
     r"фламинго|павлин|тукан|аист|журавл|лебед|\bчайк", "Птица", _bird),
    (r"рыб|акул|\bкит\b|дельфин|\bсом\b|карп|щук|окун|форел|лосос|пиран|\bскат|осьминог|кальмар|\bкраб|креветк|медуз", "Рыбка", _fish),
    (r"человек|мальчик|девочк|мужчин|женщин|парен|девушк|\bдруг\b|ребён|реб[её]нок|малыш|принц|рыцар|солдат|космонавт|супергер|лыцар", "Человечек", _human),
    (r"самол[её]т|авиа|истребител|боинг|аэроплан|вертол", "Самолётик", _plane),
    (r"кораб|лодк|катер|яхт|парусник|\bсудно", "Кораблик", _boat),
    (r"цвет(?:ок|ы|очек)?|роз[аыу]|тюльпан|ромашк|подсолнух|букет|одуванчик|нарцисс", "Цветок", _flower),
    (r"кактус", "Кактус", lambda c: [_o("cylinder", {"r": 0.45, "h": 2.0}, (0, 1.0, 0), color=c if c != _DEFAULT else "#3fa34d"),
                                      _o("sphere", {"r": 0.45}, (0, 2.0, 0), color=c if c != _DEFAULT else "#3fa34d"),
                                      _o("cylinder", {"r": 0.18, "h": 0.8}, (-0.5, 1.4, 0), rot=(0, 0, 55), color=c if c != _DEFAULT else "#3fa34d"),
                                      _o("cylinder", {"r": 0.18, "h": 0.8}, (0.5, 1.5, 0), rot=(0, 0, -55), color=c if c != _DEFAULT else "#3fa34d")]),
    (r"яблок|груш|апельсин|мандарин|персик|абрикос|\bслив[аыу]|помидор|томат|\bмяч.*фрукт", "Яблоко", _apple),
    (r"торт|\bкекс|пирожн|капкейк", "Тортик", _cake),
    (r"чашк|кружк|стакан\b|бокал", "Чашка", _cup),
    (r"бутылк|\bваз[аыу]|кувшин|фляг", "Бутылка", _bottle),
    (r"башн|небоскр[её]б|замок|замк[аиуе]|крепост|маяк|\bхрам|церков|мечет|дворец", "Башня", _tower),
    (r"планет|сатурн|юпитер|\bмарс|\bземл|\bнло|тарелк.*лет", "Планета", _planet),
    (r"\bмеч\b|\bмеча|шпаг|сабл|клинок|катан", "Меч", _sword),
    (r"карандаш|\bручк[аиуе]|фломастер", "Карандаш", _pencil),
]


MODELS = [
    (r"снеговик", "Снеговик", _snowman),
    (r"\bдом\b|домик|изб[аы]|коттедж", "Домик", _house),
    (r"[её]лк|\bель\b|новогодн", "Ёлка", _fir),
    (r"дерев|\bдуб\b|сосн", "Дерево", _tree),
    (r"гриб", "Гриб", _mushroom),
    (r"ракет", "Ракета", _rocket),
    (r"машин|автомоб|\bтачк", "Машина", _car),
    (r"робот", "Робот", _robot),
    (r"\bстол\b|столик", "Стол", _table),
    (r"\bстул\b|кресл", "Стул", _chair),
    (r"пончик|\bбублик\b|\bдонат", "Пончик", _donut),
    (r"звезд|звёзд", "Звезда", _star),
    (r"сердц|сердеч", "Сердце", _heart),
]

# базовые фигуры по слову
SHAPES = [
    (r"\bкуб\b|кубик|ящик|коробк", "Куб", lambda c: [_o("box", {"w": 1.6, "h": 1.6, "d": 1.6}, (0, 0.8, 0), color=c)]),
    (r"\bшар\b|сфер|мяч|глобус", "Шар", lambda c: [_o("sphere", {"r": 1.0}, (0, 1.0, 0), color=c)]),
    (r"цилиндр|труб|бочк|банк", "Цилиндр", lambda c: [_o("cylinder", {"r": 0.8, "h": 1.8}, (0, 0.9, 0), color=c)]),
    (r"конус|\bрожок", "Конус", lambda c: [_o("cone", {"r": 0.9, "h": 1.8}, (0, 0.9, 0), color=c)]),
    (r"пирамид", "Пирамида", lambda c: [_o("cone", {"r": 1.1, "h": 1.7}, (0, 0.85, 0), rot=(0, 45, 0), color=c)]),
    (r"\bтор\b|кольц|\bпончик", "Тор", lambda c: [_o("torus", {"r": 1.0, "tube": 0.4}, (0, 1.0, 0), rot=(90, 0, 0), color=c)]),
]

_TRIGGER = re.compile(r"\b3\s?-?д\b|\b3\s?-?d\b|тр[её]хмерн|трехмерн|3d-?модел|объ[её]мн\w*\s+модел|blender|блендер", re.I)
_MAKE = re.compile(r"сдела|созда|нарису|постро|смодел|слепи|хочу|нужн|покажи|дай|собери", re.I)
_MODEL_VERB = re.compile(r"смодел|слепи|замодел", re.I)
# Это ВОПРОС про 3D (а не просьба сделать модель) — не перехватываем: «что такое 3d», «3d принтер», «3d фильм».
_NOT = re.compile(r"что\s+так|что\s+это|как\s+(?:работает|устро|сдела(?:ть|н))|зачем|почему|для\s+чего|"
                  r"принтер|печат|\bфильм|\bкино|очк[иа]\b|телевизор|"
                  r"\bигр[ауео]|\bсайт|программ|приложени|лендинг|\bбот\b", re.I)   # игры/сайты/программы — к коду, не к 3D


def wants(text):
    """Похоже ли это на просьбу сделать 3D-модель (а не вопрос про 3D)."""
    low = (text or "").lower().replace("ё", "е")
    if _NOT.search(low):
        return False
    obj = _find_model(low) or _find_shape(low) or _find_category(low)
    three = bool(_TRIGGER.search(low))
    if _MODEL_VERB.search(low):                 # «смоделируй дом», «слепи снеговика» — явная просьба лепить
        return True
    if three and (bool(_MAKE.search(low)) or obj or "модел" in low or "blender" in low or "блендер" in low):
        return True
    if "модел" in low and obj and _MAKE.search(low):   # «сделай модель робота»
        return True
    return False


def _find_model(low):
    for rx, name, fn in MODELS:
        if re.search(rx, low):
            return name, fn
    return None


def _find_shape(low):
    for rx, name, fn in SHAPES:
        if re.search(rx, low):
            return name, fn
    return None


def _find_category(low):
    for rx, name, fn in CATEGORY:
        if re.search(rx, low):
            return name, fn
    return None


def _seed(subj):
    """Стабильное число из слова: одно и то же слово — всегда одна и та же модель."""
    s = 0
    for i, ch in enumerate(subj):
        s = (s * 131 + (i + 1) * ord(ch)) & 0x7FFFFFFF
    return s or 1


def _abstract(text, color):
    """Для ЛЮБОГО слова — собрать объёмную «скульптуру» из нескольких фигур.
    Детерминированно по слову (одно слово → всегда одна модель), но у разных слов — разный вид:
    башенка из 2–4 ярусов, что сужается кверху, симметричные «руки/крылья» и деталь-макушка."""
    subj = (_subject(text) or (text or "").strip() or "модель").lower()
    rnd = random.Random(_seed(subj))
    pal = list(COLORS.values())
    main = color if color != _DEFAULT else rnd.choice(pal)
    accent = rnd.choice(pal)
    while accent == main and len(pal) > 1:
        accent = rnd.choice(pal)

    objs = [_o("cylinder", {"r": 1.15, "h": 0.2}, (0, 0.1, 0), color="#6b7079")]   # подставка

    n = rnd.randint(2, 4)          # сколько ярусов в стопке
    y = 0.2
    r = rnd.uniform(0.82, 1.05)
    mids = []                      # запоминаем середины ярусов — пригодится для «рук»
    for i in range(n):
        g = rnd.choice(("box", "sphere", "cylinder", "cone"))
        col = main if i % 2 == 0 else accent
        turn = rnd.choice((0, 45)) if g == "box" else 0
        if g == "sphere":
            objs.append(_o("sphere", {"r": r}, (0, y + r, 0), color=col))
            step = r * 2 * rnd.uniform(0.72, 0.9)
        elif g == "box":
            h = r * rnd.uniform(1.2, 1.7)
            objs.append(_o("box", {"w": r * 1.7, "h": h, "d": r * 1.7}, (0, y + h / 2, 0), rot=(0, turn, 0), color=col))
            step = h
        elif g == "cylinder":
            h = r * rnd.uniform(1.3, 1.8)
            objs.append(_o("cylinder", {"r": r, "h": h}, (0, y + h / 2, 0), color=col))
            step = h
        else:  # cone
            h = r * rnd.uniform(1.5, 2.0)
            objs.append(_o("cone", {"r": r, "h": h}, (0, y + h / 2, 0), color=col))
            step = h
        mids.append(y + step / 2)
        y += step
        r *= rnd.uniform(0.62, 0.82)

    top = y
    # симметричные «руки/крылья/плавники» на одном из ярусов
    if rnd.random() < 0.75 and mids:
        arm_y = rnd.choice(mids[: max(1, n - 1)])
        ag = rnd.choice(("cylinder", "cone", "box"))
        reach = rnd.uniform(0.9, 1.4)
        for sx in (-1, 1):
            if ag == "cylinder":
                objs.append(_o("cylinder", {"r": 0.14, "h": reach}, (sx * reach * 0.7, arm_y, 0), rot=(0, 0, sx * 70), color=accent))
            elif ag == "cone":
                objs.append(_o("cone", {"r": 0.3, "h": reach}, (sx * reach * 0.85, arm_y, 0), rot=(0, 0, sx * 90), color=accent))
            else:
                objs.append(_o("box", {"w": reach, "h": 0.14, "d": 0.5}, (sx * reach * 0.6, arm_y, 0), color=accent))

    # деталь-макушка
    if rnd.random() < 0.7:
        tg = rnd.choice(("sphere", "cone"))
        if tg == "sphere":
            objs.append(_o("sphere", {"r": 0.22}, (0, top + 0.22, 0), color=accent))
        else:
            objs.append(_o("cone", {"r": 0.22, "h": 0.5}, (0, top + 0.25, 0), color=accent))

    # пара «глаз» — делает модель живее, если наверху был шар
    if rnd.random() < 0.5:
        eye_y = mids[-1]
        for sx in (-1, 1):
            objs.append(_o("sphere", {"r": 0.08}, (sx * 0.22, eye_y + 0.05, r * 1.2 + 0.4), color="#2a2a30"))
    return objs


def _subject(text):
    """Из запроса убираем служебные слова — остаётся тема для заголовка."""
    low = re.sub(r"\b3\s?-?[дd]\b|тр[её]хмерн\w*|трехмерн\w*|3d-?модел\w*|blender|блендер|модел\w*", " ", (text or "").lower())
    low = re.sub(r"сдела\w*|созда\w*|нарису\w*|постро\w*|смодел\w*|слепи\w*|хочу|нужн\w*|покажи|дай|мне|пожалуйста|красив\w*", " ", low)
    for key in COLORS:
        low = low.replace(key, " ")
    low = re.sub(r"\b(про|для|это|в|на|с|и)\b", " ", low)
    return re.sub(r"\s+", " ", low).strip(" .,!?")


def build(text):
    """Описание → {"title","about","scene","blender"} или None, если это не про 3D."""
    low = (text or "").lower().replace("ё", "е")
    if not wants(text):
        return None
    color = color_of(text)
    found = _find_model(low) or _find_shape(low) or _find_category(low)
    if found:
        name, fn = found
        objects = fn(color)
        title = name
    else:
        # ЛЮБОЕ слово — собираем уникальную объёмную модель-скульптуру (детерминированно по слову)
        subj = _subject(text)
        objects = _abstract(text, color)
        title = ("Модель: " + subj[:1].upper() + subj[1:]) if subj else "3D-модель"
    scene = {"bg": "#0e1016", "ground": "#1a1d27", "objects": objects}
    blender = blender_script(objects, title)
    n = len(objects)
    about = (f"**{title}** — собрал 3D-модель из {n} " + _fig_word(n) + ". "
             "Крутите её мышкой (на телефоне — пальцем), колесо — приблизить. "
             "Можно скачать для **Blender** (скрипт `.py`) или как `.obj`.")
    return {"title": title, "about": about, "scene": scene, "blender": blender}


def _fig_word(n):
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "фигур"
    d = n % 10
    return "фигуры" if 2 <= d <= 4 else "фигуры" if d == 1 else "фигур" if d == 0 else "фигур"


# ------------------------------------------------------------------ скрипт для Blender (bpy)

_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")


def _rgb(hexv):
    m = _HEX.match(hexv or "")
    if not m:
        return (0.55, 0.36, 1.0)
    h = m.group(1)
    # sRGB -> линейное (чтобы цвет в Blender совпадал с тем, что видно в чате)
    def lin(v):
        v = int(v, 16) / 255.0
        return round(v ** 2.2, 4)
    return (lin(h[0:2]), lin(h[2:4]), lin(h[4:6]))


def blender_script(objects, title="Модель Rai"):
    """Готовый скрипт на Python для Blender: открыть Blender → вкладка Scripting → Run."""
    lines = [
        '"""' + title + ' — 3D-модель, собрал Rai (rai.rteam.info). Blender → Scripting → вставить → Run Script."""',
        "import bpy, math",
        "",
        "# чистим сцену",
        "bpy.ops.object.select_all(action='SELECT')",
        "bpy.ops.object.delete(use_global=False)",
        "",
        "def mat(name, rgb):",
        "    m = bpy.data.materials.new(name)",
        "    m.use_nodes = True",
        "    b = m.node_tree.nodes.get('Principled BSDF')",
        "    if b: b.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)",
        "    return m",
        "",
        "def put(obj, rgb, rot, scale):",
        "    obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))",
        "    obj.scale = scale",
        "    obj.data.materials.append(mat('rai', rgb))",
        "",
    ]
    for i, o in enumerate(objects):
        geo, a = o["geo"], o["args"]
        x, y, z = o["pos"]
        bx, by, bz = x, z, y          # сцена Y-вверх → Blender Z-вверх
        rx, ry, rz = o.get("rot", [0, 0, 0])
        brot = (rx, rz, ry)
        sx, sy, sz = o.get("scale", [1, 1, 1])
        bscale = (sx, sz, sy)
        rgb = _rgb(o["color"])
        loc = f"location=({bx}, {by}, {bz})"
        if geo == "box":
            lines.append(f"bpy.ops.mesh.primitive_cube_add(size=1, {loc})")
            bscale = (sx * a["w"], sz * a["d"], sy * a["h"])
        elif geo == "sphere":
            lines.append(f"bpy.ops.mesh.primitive_uv_sphere_add(radius={a['r']}, segments=48, ring_count=24, {loc})")
            lines.append("bpy.ops.object.shade_smooth()")
        elif geo == "cylinder":
            lines.append(f"bpy.ops.mesh.primitive_cylinder_add(radius={a['r']}, depth={a['h']}, vertices=48, {loc})")
            lines.append("bpy.ops.object.shade_smooth()")
        elif geo == "cone":
            lines.append(f"bpy.ops.mesh.primitive_cone_add(radius1={a['r']}, radius2=0, depth={a['h']}, vertices=48, {loc})")
        elif geo == "torus":
            lines.append(f"bpy.ops.mesh.primitive_torus_add(major_radius={a['r']}, minor_radius={a['tube']}, {loc})")
            lines.append("bpy.ops.object.shade_smooth()")
        else:
            lines.append(f"bpy.ops.mesh.primitive_cube_add(size=1, {loc})")
        lines.append(f"put(bpy.context.active_object, {rgb}, {list(brot)}, {list(bscale)})")
        lines.append("")
    lines += [
        "# свет и камера",
        "bpy.ops.object.light_add(type='SUN', location=(4, -6, 8)); bpy.context.active_object.data.energy = 3.0",
        "bpy.ops.object.camera_add(location=(7, -7, 5), rotation=(math.radians(62), 0, math.radians(45)))",
        "bpy.context.scene.camera = bpy.context.active_object",
        "print('Готово: модель собрана Rai')",
    ]
    return "\n".join(lines) + "\n"
