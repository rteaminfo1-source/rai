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
    obj = _find_model(low) or _find_shape(low)
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
    found = _find_model(low) or _find_shape(low)
    if found:
        name, fn = found
        objects = fn(color)
        title = name
    else:
        subj = _subject(text)
        # неизвестный объект — делаем аккуратную «заготовку»: цветная фигура на подставке, чтобы было что покрутить
        objects = [
            _o("box", {"w": 1.8, "h": 0.2, "d": 1.8}, (0, 0.1, 0), color="#6b7079"),
            _o("sphere", {"r": 0.9}, (0, 1.1, 0), color=color),
        ]
        title = ("Модель: " + subj) if subj else "3D-модель"
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
