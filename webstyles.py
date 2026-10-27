"""Стили оформления сайтов Rai: «сделай произведение искусства», «в стиле неон», «как у Apple», «добавь анимации».

Восемь стилей поверх обычного (классического) дизайна: «Арт», «Неон», «Люкс», «Минимализм», «Ретро», «Пастель»,
«Стекло», «Брутализм». Каждый — свои шрифты, цвета, фон, карточки, кнопки и анимации.

Работает в двух местах:
  • сайты, собранные конструктором Rai (webgen.render берёт отсюда стиль, шрифт, анимации, размер текста);
  • любые другие страницы (restyle): в страницу вставляется один блок <style id="rai-style">, повторные правки
    («а теперь цвет синий») складываются с прошлыми — их состояние хранится в атрибуте data-rai этого блока.
"""

import colorsys
import html as _html
import json
import re

# ------------------------------------------------------------------ какие бывают стили
# words — как о стиле просят; strict — слова, по которым стиль ставится и при СОЗДАНИИ сайта («сайт в стиле неон»);
# theme — тема, которую стиль задаёт; accent — цвет по умолчанию; fonts — шрифты Google Fonts (кириллица есть у всех)
STYLES = {
    "classic": {"label": "Классика", "theme": None, "accent": None, "fonts": [],
                "words": r"обычн|классическ|как было|верни (стиль|дизайн|как было)|стандартн|исходн|по умолчани"},
    "neon": {"label": "Неон", "theme": "dark", "accent": "#00e5ff", "fonts": ["Russo+One", "JetBrains+Mono:wght@400;700"],
             "words": r"неон|киберпанк|cyber ?punk|футурист|будущ|sci-?fi|хакер|матриц|светящ|кислотн|синтвейв|synthwave"},
    "luxury": {"label": "Люкс", "theme": "dark", "accent": "#c9a227", "fonts": ["Cormorant+Garamond:wght@500;600;700"],
               "words": r"люкс|премиум|premium|luxury|дорог(о|ой|ая|ое|им|ого|ую)\b|дорогост|элегантн|роскош|богат|\bvip\b|солидн|изыскан"},
    "minimal": {"label": "Минимализм", "theme": "light", "accent": None, "fonts": ["Manrope:wght@400;600;800"],
                "words": r"минимал|лаконичн|строг|\bapple\b|эппл|\bэпл|скандинав|\bпрощ|чист(ый|ого|ым|ом) (дизайн|стил)"},
    "retro": {"label": "Ретро", "theme": "light", "accent": "#ff5a1f", "fonts": ["Rubik+Mono+One", "Rubik:wght@400;600"],
              "words": r"ретро|винтаж|старин|олдскул|old ?school|\b80-?х|\b90-?х|пиксел|8-?бит|ностальг|комикс"},
    "pastel": {"label": "Пастель", "theme": "light", "accent": "#ff6fa3", "fonts": ["Comfortaa:wght@500;700"],
               "words": r"пастел|нежн|\bмил(ый|ая|ое|ые|ен)|милот|кавай|kawaii|воздушн|девичь|детск|мягк"},
    "brutal": {"label": "Брутализм", "theme": "light", "accent": "#ffe600", "fonts": ["JetBrains+Mono:wght@400;700"],
               "words": r"брутал|brutal|дерзк|смел(ый|ее|ое)|панк|грубее"},
    "glass": {"label": "Стекло", "theme": "dark", "accent": None, "fonts": [],
              "words": r"стекл|стекля|\bglass|матов|современн|трендов|модн|стильн"},
    "art": {"label": "Арт", "theme": "dark", "accent": None, "fonts": ["Playfair+Display:ital,wght@0,600;0,800;1,500"],
            "words": r"ис{1,2}к{1,2}у?с{0,2}т?в|шедевр|\bарт\b|\bart\b|художеств|креатив|\bвау\b|\bwow\b|восхит|потрясающ|"
                     r"невероятн|эпичн|необычн|красив|прекрасн|великолепн|круче|\bкрут(о|ой|ым)\b|произведени|галерейн|"
                     r"шикарн|офигенн|бомбическ|топов|эффектн|\bлучше\b|получше|ярче|поярче|покруче"},
}
# Сначала узкие стили, в конце — общие слова «красиво», «современно»
ORDER = ["classic", "neon", "luxury", "minimal", "retro", "pastel", "brutal", "glass", "art"]
_STRICT = {"art": r"ис{1,2}к{1,2}у?с{0,2}т?в|шедевр|\bарт\b|художеств|произведени", "glass": r"стекл|стекля|\bglass|матов"}

# Просьба о внешнем виде, а не о содержании: «сделай…», «стиль…», «дизайн…», «переделай…»
_DESIGN_RE = re.compile(r"сделай|переделай|преврати|оформи|оформлени|стил|дизайн|выгляд|внешн|\bвид\b|красивее|покрасивее|верни|"
                        r"получше|\bлучше\b|улучши|ярче|покруче|вау|шедевр|ис{1,2}к{1,2}у?с{0,2}т?в|как у\b|в духе|под\s")
# Команда про содержимое: «добавь раздел красивые фото» — это раздел, а не стиль
_CONTENT_RE = re.compile(r"(добавь|убери|удали|скрой|переименуй|назови|измени|поменяй|замени|напиши)\s.{0,30}"
                         r"(раздел|блок|секци|текст|назван|слоган|заголов|отзыв|цен|фото|картин|галере|меню|контакт|почт|телефон)")

FONTS = {
    # шрифт: (слова, семейство Google Fonts, CSS для заголовков, CSS для текста или None)
    "serif": (r"засечк|классическ|книжн|serif|благородн", "Playfair+Display:wght@600;800", '"Playfair Display",Georgia,serif', None),
    "elegant": (r"элегантн|изящн|тонк", "Cormorant+Garamond:wght@500;700", '"Cormorant Garamond",Georgia,serif', None),
    "script": (r"рукописн|каллиграф|от руки|прописн", "Caveat:wght@600;700", '"Caveat",cursive', None),
    "rounded": (r"округл|кругл|мягк|детск", "Comfortaa:wght@500;700", '"Comfortaa",sans-serif', '"Comfortaa",sans-serif'),
    "mono": (r"моноширин|\bмоно|кодов|программист|как в коде|терминал", "JetBrains+Mono:wght@400;700",
             '"JetBrains Mono",monospace', '"JetBrains Mono",monospace'),
    "sans": (r"прост|обычн|строг|без засечек|современн|ровн", "Manrope:wght@400;800", '"Manrope",sans-serif', '"Manrope",sans-serif'),
    "bold": (r"жирн|массивн|мощн", "Unbounded:wght@800", '"Unbounded","Arial Black",sans-serif', None),
}


def _low(s):
    return (s or "").lower().replace("ё", "е")


# Слова о том, КАК сделать, а не О ЧЁМ сайт: «сделай сайт красиво» — просьба об оформлении, а не сайт с названием «Красиво»
LOOK_RE = re.compile(
    r"(?<![\w-])(?:ещ[её]\s+|более\s+|очень\s+|по-?)?(?:красив\w*|покрасивее|прекрасн\w*|великолепн\w*|стильн\w*|"
    r"современн\w*|модн\w*|крут(?:о|ой|ая|ое|ые|ым|ую)|покруче|круче|классн\w*|шикарн\w*|эффектн\w*|"
    r"ярк(?:о|ий|ая|ое|ие|им|ую)|ярче|поярче|лучше|получше|необычн\w*|оригинальн\w*|креативн\w*|дизайнерск\w*|"
    r"премиальн\w*|роскошн\w*|аккуратн\w*|минималистичн\w*|лаконичн\w*|атмосферн\w*|сочн\w*|прикольн\w*|"
    r"симпатичн\w*|wow|вау|супер|топов\w*|идеальн\w*|уникальн\w*|профессиональн\w*|качественн\w*|потрясающ\w*|"
    r"невероятн\w*|эпичн\w*|восхитительн\w*|офигенн\w*|бомбическ\w*)(?![\w-])", re.I)
STYLE_PHRASE_RE = re.compile(r"(?<![\w-])(?:в\s+стиле\s+[\w-]+|в\s+[\w-]+\s+стиле|в\s+духе\s+[\w-]+|как\s+у\s+[\w-]+|"
                             r"с\s+анимаци\w*|анимированн\w*|с\s+эффектами|с\s+(?:красивым\s+)?дизайном)(?![\w-])", re.I)
FILL_RE = re.compile(r"(?<![\w-])(?:пожалуйста|пожалуйсто|плиз|please|срочно|быстро|побыстрее|быстренько|просто|"
                     r"какой-?\s?нибудь|какую-?\s?нибудь|любой|любую)(?![\w-])", re.I)
# Что ещё бывает в просьбе только про вид: «сделай мне этот сайт красиво», «хочу чтобы страница была стильной»
_ONLY_RE = re.compile(r"(?<![\w-])(?:а|теперь|сделай|сделать|сделайте|переделай|переделать|оформи|оформить|можешь|можно|хочу|"
                      r"нужен|нужна|нужно|сайт\w*|страниц\w*|лендинг\w*|дизайн\w*|оформлени\w*|вид|стиль|этот|эту|это|мой|мою|"
                      r"наш|нашу|весь|всю|его|её|ее|мне|нам|чтобы|чтоб|был|была|было|стал|стала|стало|выглядел\w*|"
                      r"и|да|в|с|на|по|же|бы|ну|давай|ещ[её]|чуть|немного|побольше|еще)(?![\w-])", re.I)


_TOPIC_MARK = re.compile(r"(?<![\w-])(?:про|о|об|обо|для|на\s+тему|по\s+теме|посвящ\w*)(?![\w-])", re.I)
_ADVERB = {"лучше", "получше", "ярче", "поярче", "круче", "покруче", "покрасивее", "красивее", "wow", "вау", "супер"}


def _is_adverb(word):
    """«красиво», «стильно», «лучше» — как сделать; «красивые», «современное» — может быть частью темы."""
    w = _low(word.split()[-1])
    return w in _ADVERB or w.endswith(("ски", "ее")) or (w.endswith("о") and not w.endswith(("ое", "го", "ео")))


def strip_look(text):
    """(текст без слов об оформлении, эти слова): «сделай сайт кофейни красиво» → («сделай сайт кофейни», «красиво»).

    Наречия («красиво», «стильно», «лучше») и «в стиле неон» убираем всегда, прилагательные — только до темы:
    «красивый сайт для кофейни» → «сайт для кофейни», но «сайт про современное искусство» не трогаем.
    Названия в «кавычках» не трогаем: «Красивые цветы» — это имя магазина."""
    found = []
    text = text or ""
    mark = None
    plain = re.sub(r"[«\"“][^»\"”]*[»\"”]", lambda m: " " * len(m.group(0)), text)
    m = _TOPIC_MARK.search(plain)
    if m:
        mark = m.start()

    def cutter(offset, keep_after_mark):
        def cut(m):
            if keep_after_mark and mark is not None and offset + m.start() > mark and not _is_adverb(m.group(0)):
                return m.group(0)
            found.append(m.group(0).strip())
            return "\x00" * len(m.group(0))   # длину сохраняем: позиция темы не сдвигается
        return cut
    parts = re.split(r"([«\"“][^»\"”]*[»\"”])", text)
    offset = 0
    for i, part in enumerate(parts):
        if i % 2 == 0:
            part = STYLE_PHRASE_RE.sub(cutter(offset, False), part)
            part = LOOK_RE.sub(cutter(offset, True), part)
            parts[i] = part
        offset += len(part)
    out = "".join(parts)
    out = re.sub(r"\x00+(?:\s*(?:,|и|да)\s*\x00+)+", "\x00", out)     # «стильно и современно» — убираем и союз между ними
    out = FILL_RE.sub(" ", out.replace("\x00", " "))
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.!?])", r"\1", out).strip(" ,.!?")
    out = re.sub(r"(?:[\s,]+(?:и|да|а|но))+\s*$", "", out).strip(" ,.!?")     # «стильно и современно» → хвостовое «и»
    out = re.sub(r"^(?:(?:и|да|а|но)[\s,]+)+", "", out)
    return out, " ".join(found)


def style_only(text):
    """Просьба только про внешний вид, без темы: «сделай сайт красиво», «сделай красивый сайт», «сайт в стиле неон»."""
    rest, look = strip_look(text)
    if not look and not detect(text):
        return False
    words = [w for w in re.split(r"[\s,.!?:;]+", _ONLY_RE.sub(" ", _low(rest))) if w]
    return all(detect(w) for w in words)          # остались только названия стилей: «неон», «ретро»


def detect(text, strict=False):
    """Стиль из просьбы или None. strict — только явные названия стиля (для описания нового сайта)."""
    low = _low(text)
    for key in ORDER:
        words = _STRICT.get(key, STYLES[key]["words"]) if strict else STYLES[key]["words"]
        if strict and key in ("classic",):
            continue
        if re.search(words, low):
            return key
    return None


def wants_design(text):
    """Похоже на просьбу изменить внешний вид (а не добавить раздел или текст)."""
    low = _low(text)
    if _CONTENT_RE.search(low) and not re.search(r"стил|дизайн|оформ", low):
        return False
    if len(low.split()) <= 3 and detect(low) not in (None, "art", "glass"):
        return True                     # просто «брутализм», «неон», «ретро стиль»
    return bool(_DESIGN_RE.search(low) or re.search(r"\bв стиле\b|\bстиль\b", low))


def detect_font(text):
    low = _low(text)
    if "шрифт" not in low:
        return None
    for key, (words, *_rest) in FONTS.items():
        if re.search(words, low):
            return key
    return "serif" if re.search(r"красив|другой|поменяй|смени", low) else None


def motion(text):
    """True — добавить анимации, False — убрать, None — о них не просили."""
    low = _low(text)
    if re.search(r"(убери|без|отключи|выключи|не надо|поменьше)\s+(\w+\s+)?(анимац|эффект|движени)", low):
        return False
    if re.search(r"анимац|оживи|живее|живым|динамичн|движени|эффект|плавн|параллакс|интерактив", low):
        return True
    return None


def scale(text):
    low = _low(text)
    if re.search(r"(шрифт|текст|буквы)\w*\s+(крупнее|побольше|больше)|крупнее|увеличь (шрифт|текст|буквы)|покрупнее", low):
        return 1.12
    if re.search(r"(шрифт|текст|буквы)\w*\s+(мельче|поменьше|меньше)|мельче|уменьши (шрифт|текст|буквы)|помельче", low):
        return 0.92
    return None


def hue(hex_, deg, light=0.0):
    """Цвет, повёрнутый по кругу на deg градусов (и чуть светлее/темнее): вторые цвета для градиентов."""
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, lum, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb((h + deg / 360) % 1, max(0.0, min(1.0, lum + light)), max(s, 0.55))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def palette(accent):
    """Цвета градиентов стиля из главного цвета."""
    return {"a2": hue(accent, 48, 0.08), "a3": hue(accent, -70, 0.02), "glow": accent + "33"}


def font_params(style, font):
    fams = list(STYLES.get(style, STYLES["classic"])["fonts"])
    if font in FONTS:
        fams.append(FONTS[font][1])
    return fams


# ------------------------------------------------------------------ CSS стилей для сайтов конструктора Rai
SITE_CSS = {
    "art": """
:root{--bg:#07060b;--fg:#f6f3ff;--muted:#b7b0cc;--line:rgba(255,255,255,.12);--surface:rgba(255,255,255,.06);--ink:#fff}
body{background:#07060b}
.aurora{position:fixed;inset:-25vmax;z-index:-3;pointer-events:none;filter:blur(70px) saturate(150%);opacity:.8}
.aurora i{position:absolute;width:60vmax;height:60vmax;border-radius:50%;mix-blend-mode:screen;animation:aur 26s ease-in-out infinite alternate}
.aurora i:nth-child(1){left:5%;top:5%;background:radial-gradient(circle,var(--accent),transparent 62%)}
.aurora i:nth-child(2){right:0;top:20%;background:radial-gradient(circle,var(--a2),transparent 62%);animation-duration:32s;animation-delay:-8s}
.aurora i:nth-child(3){left:25%;bottom:0;background:radial-gradient(circle,var(--a3),transparent 62%);animation-duration:38s;animation-delay:-16s}
@keyframes aur{0%{transform:translate(0,0) scale(1)}50%{transform:translate(9vmax,-7vmax) scale(1.18)}100%{transform:translate(-7vmax,8vmax) scale(.92)}}
.grain{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.08;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.spot{position:fixed;inset:0;z-index:-2;pointer-events:none;background:radial-gradient(520px circle at var(--mx,70%) var(--my,20%),var(--glow),transparent 65%)}
header{background:rgba(7,6,11,.5);border-bottom-color:rgba(255,255,255,.07)}
.logo,.hero h1,.sec h2{font-family:"Playfair Display",Georgia,serif;letter-spacing:-.01em}
.hero{border:0;min-height:86vh;display:flex;align-items:center}
.hero>img{opacity:.28;mix-blend-mode:screen;filter:saturate(1.4)}
.hero::after{background:radial-gradient(ellipse at 25% 50%,transparent,var(--bg) 78%)}
.hero h1{font-size:clamp(46px,9vw,118px);line-height:.95;font-weight:800;max-width:13ch;background:linear-gradient(105deg,#fff 15%,var(--a2) 38%,var(--accent) 55%,var(--a3) 72%,#fff 90%);background-size:260% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:sheen 10s linear infinite}
@keyframes sheen{to{background-position:-260% 0}}
.hero p{font-family:"Playfair Display",Georgia,serif;font-style:italic;font-size:clamp(20px,2.8vw,30px);color:var(--muted)}
.sec{border-bottom:0;padding:110px 0}
.sec h2{font-size:clamp(34px,5.4vw,64px);font-weight:800}
.sec h2::before{content:attr(data-n) " —";display:block;font:600 13px/1 "Onest",sans-serif;letter-spacing:.32em;color:var(--accent);margin-bottom:16px}
.card{background:linear-gradient(155deg,rgba(255,255,255,.1),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.12);border-radius:24px;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 24px 70px -36px rgba(0,0,0,.9);transition:transform .25s,border-color .25s,box-shadow .25s}
.card:hover{border-color:var(--accent);box-shadow:0 30px 90px -34px var(--accent)}
.btn{background:linear-gradient(120deg,var(--accent),var(--a2),var(--a3),var(--accent));background-size:300% 100%;color:#fff;border-radius:999px;padding:15px 30px;box-shadow:0 14px 44px -14px var(--accent);transition:background-position .8s,transform .2s}
.btn:hover{background-position:100% 0;transform:translateY(-2px);filter:none}
.btn.ghost{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.2);color:var(--fg);box-shadow:none}
.ico,.ava{background:linear-gradient(135deg,var(--accent),var(--a3));color:#fff;box-shadow:0 10px 30px -10px var(--accent)}
.price,.steps li::before{background:linear-gradient(90deg,var(--accent),var(--a2));-webkit-background-clip:text;background-clip:text;color:transparent}
.steps li{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.1);border-radius:18px}
.lead-form input,.lead-form textarea,.tags span{background:rgba(255,255,255,.05)}
.shot{border-radius:18px}.shot img{transition:transform .6s;filter:saturate(1.2)}
.band{overflow:hidden;white-space:nowrap;border-block:1px solid rgba(255,255,255,.1);padding:18px 0;font:italic 600 clamp(22px,3vw,34px)/1.2 "Playfair Display",serif;color:var(--muted)}
.band div{display:inline-block;animation:band 40s linear infinite}.band span{margin:0 28px}.band b{color:var(--accent);font-style:normal}
@keyframes band{to{transform:translateX(-50%)}}
.rv{filter:blur(10px);transform:translateY(34px) scale(.98);transition:opacity .9s,transform .9s,filter .9s}
.rv.in{filter:none;transform:none}
footer{border-top:1px solid rgba(255,255,255,.08)}
@media (prefers-reduced-motion:reduce){.aurora i,.hero h1,.band div{animation:none}}
""",
    "neon": """
:root{--bg:#04050a;--fg:#e6fbff;--muted:#89a6b8;--line:rgba(0,229,255,.2);--surface:rgba(4,12,20,.78);--ink:#04050a}
body{background:#04050a;font-family:"JetBrains Mono","Onest",monospace}
.gridbg{position:fixed;inset:0;z-index:-2;pointer-events:none;background:linear-gradient(transparent 0 calc(100% - 1px),var(--glow) 0) 0 0/100% 46px,linear-gradient(90deg,transparent 0 calc(100% - 1px),rgba(255,43,214,.1) 0) 0 0/46px 100%;-webkit-mask-image:radial-gradient(ellipse at 50% 40%,#000 30%,transparent 80%);mask-image:radial-gradient(ellipse at 50% 40%,#000 30%,transparent 80%)}
.scan{position:fixed;inset:0;z-index:70;pointer-events:none;background:repeating-linear-gradient(to bottom,rgba(255,255,255,.035) 0 1px,transparent 1px 3px)}
header{background:rgba(4,5,10,.82);border-bottom:1px solid var(--line)}
.logo,.hero h1,.sec h2,nav a{font-family:"Russo One","Unbounded",sans-serif;text-transform:uppercase;letter-spacing:.06em}
.logo{color:var(--accent);text-shadow:0 0 12px var(--accent);font-size:18px}
nav a{font-size:12.5px;letter-spacing:.05em}
.hero{border-bottom:1px solid var(--line)}
.hero>img{opacity:.22;filter:hue-rotate(160deg) saturate(2)}
.hero::after{background:linear-gradient(90deg,var(--bg) 25%,transparent)}
.hero h1{color:#fff;text-shadow:0 0 4px #fff,0 0 14px var(--accent),0 0 38px var(--accent),0 0 80px var(--a2);animation:flick 5s infinite}
@keyframes flick{0%,18%,22%,62%,64%,100%{opacity:1}20%,63%{opacity:.45}}
.hero p{color:var(--accent)}
.sec{border-bottom:1px solid var(--line)}
.sec h2{color:var(--accent);text-shadow:0 0 14px var(--accent)}
.card{background:var(--surface);border:1px solid var(--accent);border-radius:6px;box-shadow:inset 0 0 22px -8px var(--accent)}
.card:hover{box-shadow:inset 0 0 26px -6px var(--accent),0 0 34px -6px var(--accent)}
.btn{background:transparent;color:var(--accent);border:2px solid var(--accent);border-radius:4px;text-transform:uppercase;letter-spacing:.1em;box-shadow:0 0 18px -4px var(--accent),inset 0 0 14px -6px var(--accent)}
.btn:hover{background:var(--accent);color:var(--ink);filter:none}
.btn.ghost{border-color:var(--a2);color:var(--a2);box-shadow:0 0 18px -6px var(--a2)}
.ico,.ava{background:transparent;color:var(--accent);border:1px solid var(--accent);box-shadow:0 0 14px -4px var(--accent)}
.price{color:var(--a2);text-shadow:0 0 10px var(--a2)}
.tags span{border-color:var(--a2);box-shadow:0 0 12px -6px var(--a2)}
.steps li{background:var(--surface);border-color:var(--line)}
.steps li::before{color:var(--a2);text-shadow:0 0 10px var(--a2)}
@media (prefers-reduced-motion:reduce){.hero h1{animation:none}}
""",
    "luxury": """
:root{--bg:#0c0b09;--fg:#f2eadb;--muted:#b3a68e;--line:rgba(201,162,39,.22);--surface:#14120e;--ink:#0c0b09}
body{background:#0c0b09}
header{background:rgba(12,11,9,.88);border-bottom:1px solid var(--line)}
.logo,.hero h1,.sec h2,.price,.card h3{font-family:"Cormorant Garamond",Georgia,serif;letter-spacing:.01em}
.logo{font-weight:700;font-size:24px}
nav a{text-transform:uppercase;letter-spacing:.2em;font-size:12px}
.hero>img{opacity:.25;filter:sepia(.6) saturate(.8)}
.hero h1{font-weight:500;font-size:clamp(46px,8.5vw,108px);line-height:1}
.hero p{font-family:"Cormorant Garamond",serif;font-style:italic;font-size:clamp(20px,2.6vw,28px);color:var(--muted)}
.sec{padding:120px 0}
.sec h2{font-weight:500;font-size:clamp(34px,5vw,58px)}
.sec h2::after{content:"";display:block;width:70px;height:1px;background:var(--accent);margin-top:18px}
.card{border-radius:0;background:linear-gradient(180deg,#17140f,#100e0b);border:1px solid var(--line)}
.card:hover{transform:none;border-color:var(--accent)}
.card h3{font-size:24px;font-weight:600}
.btn{background:transparent;color:var(--accent);border:1px solid var(--accent);border-radius:0;text-transform:uppercase;letter-spacing:.22em;font-size:13px;padding:16px 32px}
.btn:hover{background:var(--accent);color:var(--ink);filter:none}
.btn.ghost{border-color:var(--line);color:var(--fg)}
.ico,.ava{background:transparent;border:1px solid var(--accent);color:var(--accent);border-radius:50%}
.price{font-weight:600}
.steps li,.tags span{border-radius:0}
""",
    "minimal": """
:root{--bg:#ffffff;--fg:#0f0f0f;--muted:#6b6b6b;--line:#ececec;--surface:#ffffff;--ink:#fff}
body{background:#fff;font-family:"Manrope","Onest",system-ui,sans-serif}
header{background:rgba(255,255,255,.92)}
.logo,.hero h1,.sec h2{font-family:"Manrope","Onest",sans-serif;font-weight:800;letter-spacing:-.045em}
.hero>img{opacity:.06;filter:grayscale(1)}
.hero::after{background:linear-gradient(90deg,#fff 35%,transparent)}
.hero h1{font-size:clamp(46px,8.5vw,104px);line-height:.98}
.sec{padding:120px 0}
.card{border-radius:14px;box-shadow:none}
.card:hover{transform:none;border-color:#0f0f0f}
.btn{background:#0f0f0f;color:#fff;border-radius:999px}
.btn.ghost{background:transparent;color:#0f0f0f;border:1px solid #d9d9d9}
.ico,.ava{background:#0f0f0f;color:#fff;border-radius:50%}
.price{color:#0f0f0f}
""",
    "retro": """
:root{--bg:#f3e9d2;--fg:#1c1a16;--muted:#5e564a;--line:#1c1a16;--surface:#fff8ea;--ink:#fff}
body{background:#f3e9d2 radial-gradient(rgba(28,26,22,.12) 1px,transparent 1px) 0 0/18px 18px;font-family:"Rubik","Onest",sans-serif}
header{background:#f3e9d2;border-bottom:3px solid var(--line)}
.logo,.hero h1,.sec h2{font-family:"Rubik Mono One","Unbounded",sans-serif;text-transform:uppercase}
.hero{border-bottom:3px solid var(--line)}
.hero>img{opacity:.35;filter:sepia(.5) contrast(1.1)}
.hero::after{background:linear-gradient(90deg,#f3e9d2 30%,transparent)}
.hero h1{color:var(--fg);text-shadow:4px 4px 0 var(--accent),8px 8px 0 var(--a3)}
.sec{border-bottom:3px solid var(--line)}
.card{border:3px solid var(--line);border-radius:6px;box-shadow:6px 6px 0 var(--line);background:var(--surface)}
.card:hover{transform:translate(-3px,-3px);box-shadow:9px 9px 0 var(--line);border-color:var(--line)}
.btn{border:3px solid var(--line);border-radius:6px;box-shadow:5px 5px 0 var(--line);background:var(--accent);color:#fff}
.btn:hover{transform:translate(-2px,-2px);box-shadow:7px 7px 0 var(--line);filter:none}
.btn.ghost{background:#fff8ea;color:var(--fg)}
.ico,.ava{border:3px solid var(--line);box-shadow:3px 3px 0 var(--line)}
.steps li{border:3px solid var(--line);box-shadow:5px 5px 0 var(--line);border-radius:6px}
.tags span{border:3px solid var(--line);box-shadow:3px 3px 0 var(--line);background:#fff8ea}
.band{background:var(--accent);color:#fff;border-block:3px solid var(--line);font:400 22px/1.2 "Rubik Mono One",sans-serif;padding:14px 0;overflow:hidden;white-space:nowrap}
.band div{display:inline-block;animation:band 30s linear infinite}.band span{margin:0 24px}
@keyframes band{to{transform:translateX(-50%)}}
""",
    "pastel": """
:root{--bg:#fff6fb;--fg:#3a2e48;--muted:#8b7f9b;--line:#f0dbe9;--surface:rgba(255,255,255,.8);--ink:#fff}
body{background:linear-gradient(140deg,#ffe3f0,#ebe5ff 45%,#dcf6ee) fixed;font-family:"Comfortaa","Onest",sans-serif}
header{background:rgba(255,246,251,.72)}
.logo,.hero h1,.sec h2{font-family:"Comfortaa","Onest",sans-serif;font-weight:700}
.hero{border:0}
.hero>img{opacity:.3;filter:saturate(.7) brightness(1.15)}
.hero::after{background:linear-gradient(90deg,rgba(255,246,251,.95) 20%,transparent)}
.sec{border-bottom:0}
.card{border:0;border-radius:28px;box-shadow:0 20px 44px -24px rgba(170,120,200,.6)}
.card:hover{transform:translateY(-5px)}
.btn{border-radius:999px;background:linear-gradient(120deg,var(--accent),#b39dff);color:#fff;box-shadow:0 12px 30px -12px var(--accent)}
.btn.ghost{background:rgba(255,255,255,.7);color:var(--fg);border:0}
.ico,.ava{border-radius:50%;background:linear-gradient(135deg,var(--accent),#c4b5ff);color:#fff}
.steps li{border:0;border-radius:22px;box-shadow:0 14px 30px -22px rgba(170,120,200,.6)}
.tags span{border:0;background:#fff;box-shadow:0 8px 20px -14px rgba(170,120,200,.8)}
""",
    "glass": """
:root{--fg:#ffffff;--muted:rgba(255,255,255,.8);--line:rgba(255,255,255,.22);--surface:rgba(255,255,255,.13);--ink:#141414}
body{background:linear-gradient(135deg,var(--accent),var(--a3) 50%,var(--a2)) fixed;color:#fff}
.aurora{position:fixed;inset:-20vmax;z-index:-2;pointer-events:none;filter:blur(60px);opacity:.6}
.aurora i{position:absolute;width:50vmax;height:50vmax;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.55),transparent 60%);animation:aur 30s ease-in-out infinite alternate}
.aurora i:nth-child(2){right:0;top:30%;animation-duration:36s}.aurora i:nth-child(3){left:30%;bottom:0;animation-duration:42s}
@keyframes aur{0%{transform:translate(0,0)}100%{transform:translate(10vmax,8vmax)}}
header{background:rgba(255,255,255,.12);border-bottom:1px solid var(--line)}
.logo span{color:#fff}
.hero{border-bottom:0}
.hero>img{opacity:.22;mix-blend-mode:overlay}
.hero::after{background:none}
.sec{border-bottom:0}
.card,.steps li,.lead-form{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);backdrop-filter:blur(18px) saturate(160%);-webkit-backdrop-filter:blur(18px) saturate(160%);border-radius:24px;box-shadow:0 22px 50px -28px rgba(0,0,0,.5)}
.card:hover{border-color:#fff}
.card p,.card small,.lead{color:rgba(255,255,255,.88)}
.btn{background:#fff;color:#141414;border-radius:999px}
.btn.ghost{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.4)}
.ico,.ava{background:rgba(255,255,255,.9);color:#141414}
.price,.stars,.steps li::before,a{color:#fff}
.tags span{border-color:rgba(255,255,255,.6);background:rgba(255,255,255,.1)}
.lead-form input,.lead-form textarea{background:rgba(255,255,255,.12);border-color:rgba(255,255,255,.35);color:#fff}
@media (prefers-reduced-motion:reduce){.aurora i{animation:none}}
""",
    "brutal": """
:root{--bg:#ffffff;--fg:#000;--muted:#222;--line:#000;--surface:#fff;--ink:#000}
body{background:#fff;font-family:"JetBrains Mono",monospace}
header{background:#fff;border-bottom:3px solid #000}
.logo,.hero h1,.sec h2{font-family:"Unbounded",sans-serif;text-transform:uppercase;letter-spacing:-.03em}
.hero{border-bottom:3px solid #000}
.hero>img{opacity:.12;filter:grayscale(1) contrast(2)}
.hero::after{background:none}
.hero h1{font-size:clamp(50px,11vw,150px);line-height:.86}
.sec{border-bottom:3px solid #000}
.card{border:3px solid #000;border-radius:0;box-shadow:none}
.card:hover{background:var(--accent);transform:none;border-color:#000}
.card p,.card small{color:#000}
.btn{border-radius:0;border:3px solid #000;background:var(--accent);color:#000;text-transform:uppercase}
.btn.ghost{background:#fff}
.ico,.ava{border-radius:0;background:#000;color:var(--accent)}
.price{color:#000;background:var(--accent);padding:4px 8px}
.steps li,.tags span{border:3px solid #000;border-radius:0}
.band{background:#000;color:var(--accent);font:800 26px/1.2 "Unbounded",sans-serif;text-transform:uppercase;padding:16px 0;overflow:hidden;white-space:nowrap}
.band div{display:inline-block;animation:band 25s linear infinite}.band span{margin:0 26px}
@keyframes band{to{transform:translateX(-50%)}}
""",
}

# Анимации поверх любого стиля: «добавь анимации», «оживи сайт»
MOTION_CSS = """
.hero .wrap{animation:rise 1s cubic-bezier(.2,.8,.2,1) both}
@keyframes rise{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:none}}
.card{transition:transform .25s,box-shadow .25s,border-color .25s}
.card:hover{box-shadow:0 22px 50px -26px var(--accent)}
.sec h2{background-image:linear-gradient(var(--accent),var(--accent));background-repeat:no-repeat;background-position:0 100%;background-size:0 3px;padding-bottom:6px;transition:background-size 1s .2s}
.sec h2.in{background-size:90px 3px}
.btn{position:relative;overflow:hidden}
.btn::after{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.35) 50%,transparent 70%);transform:translateX(-120%);transition:transform .7s}
.btn:hover::after{transform:translateX(120%)}
@media (prefers-reduced-motion:reduce){.hero .wrap{animation:none}}
"""

# Наклон карточек и свет за курсором (стиль «Арт» и «анимации»); безопасно для телефонов и «меньше движения»
MOTION_JS = """
(function(){var b=document.body,mv=b.dataset.motion==="1"||b.dataset.style==="art";
if(!mv||!matchMedia("(pointer:fine)").matches||matchMedia("(prefers-reduced-motion: reduce)").matches)return;
var r=document.documentElement.style;addEventListener("pointermove",function(e){r.setProperty("--mx",e.clientX+"px");r.setProperty("--my",e.clientY+"px")},{passive:true});
document.querySelectorAll(".card").forEach(function(c){c.addEventListener("pointermove",function(e){var q=c.getBoundingClientRect(),x=(e.clientX-q.left)/q.width-.5,y=(e.clientY-q.top)/q.height-.5;
c.style.transform="perspective(800px) rotateX("+(-y*7).toFixed(2)+"deg) rotateY("+(x*7).toFixed(2)+"deg) translateY(-4px)"});c.addEventListener("pointerleave",function(){c.style.transform=""})})})();
"""


def site_css(style, accent, motion_on=False, font=None, zoom=None):
    """CSS поверх базовой вёрстки конструктора: цвета градиентов, стиль, анимации, шрифт, размер текста."""
    pal = palette(accent)
    out = [f":root{{--a2:{pal['a2']};--a3:{pal['a3']};--glow:{pal['glow']}}}", SITE_CSS.get(style, "")]
    if motion_on and style != "art":
        out.append(MOTION_CSS)
    if font in FONTS:
        _w, _f, head, body = FONTS[font]
        out.append(f".logo,.hero h1,.sec h2,.card h3{{font-family:{head}}}")
        if body:
            out.append(f"body{{font-family:{body}}}")
    if zoom:
        out.append(f"body{{zoom:{zoom}}}")
    return "\n".join(x for x in out if x)


def decor(style, title, tagline, sections):
    """Украшения страницы: (фон в начале body, бегущая строка после первого экрана)."""
    top = ""
    if style == "art":
        top = ('<div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div><div class="spot" aria-hidden="true"></div>'
               '<div class="grain" aria-hidden="true"></div>')
    elif style == "glass":
        top = '<div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div>'
    elif style == "neon":
        top = '<div class="gridbg" aria-hidden="true"></div><div class="scan" aria-hidden="true"></div>'
    band = ""
    if style in ("art", "retro", "brutal"):
        words = [title, tagline] + [s for s in sections[:4]]
        line = "".join(f"<span>{_html.escape(w)}</span><b>✦</b>" for w in words if w)
        band = f'<div class="band" aria-hidden="true"><div>{line * 3}{line * 3}</div></div>'
    return top, band


# ------------------------------------------------------------------ любая страница: стиль одним блоком <style>
_GENERIC = {
    # стиль: (фон, текст, приглушённый, тема, CSS по элементам)
    "art": ("#07060b", "#f6f3ff", "#b7b0cc", "dark", """
html body::before{content:"";position:fixed;inset:-25vmax;z-index:-1;pointer-events:none;background:radial-gradient(circle at 20% 25%,var(--rai-accent),transparent 35%),radial-gradient(circle at 80% 30%,var(--rai-a2),transparent 35%),radial-gradient(circle at 45% 80%,var(--rai-a3),transparent 35%);filter:blur(70px) saturate(140%);opacity:.5;animation:raiAur 30s ease-in-out infinite alternate}
@keyframes raiAur{to{transform:translate(6vmax,-5vmax) rotate(12deg) scale(1.1)}}
html body h1,html body h2,html body h3{font-family:"Playfair Display",Georgia,serif;letter-spacing:-.01em}
html body h1{background:linear-gradient(105deg,#fff 15%,var(--rai-a2) 40%,var(--rai-accent) 60%,#fff 88%);background-size:260% 100%;-webkit-background-clip:text;background-clip:text;color:transparent!important;animation:raiSheen 10s linear infinite}
@keyframes raiSheen{to{background-position:-260% 0}}
html body .card,html body article,html body form{background:linear-gradient(155deg,rgba(255,255,255,.09),rgba(255,255,255,.02))!important;border:1px solid rgba(255,255,255,.14);border-radius:22px;backdrop-filter:blur(14px)}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:linear-gradient(120deg,var(--rai-accent),var(--rai-a2),var(--rai-a3))!important;color:#fff!important;border:0!important;border-radius:999px!important;box-shadow:0 12px 36px -14px var(--rai-accent);cursor:pointer}
@media (prefers-reduced-motion:reduce){html body::before,html body h1{animation:none}}
"""),
    "neon": ("#04050a", "#e6fbff", "#89a6b8", "dark", """
html body{font-family:"JetBrains Mono",monospace!important}
html body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:linear-gradient(transparent 0 calc(100% - 1px),var(--rai-glow) 0) 0 0/100% 46px,linear-gradient(90deg,transparent 0 calc(100% - 1px),rgba(255,43,214,.1) 0) 0 0/46px 100%}
html body h1,html body h2,html body h3{font-family:"Russo One",sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--rai-accent)!important;text-shadow:0 0 14px var(--rai-accent)}
html body h1{color:#fff!important;text-shadow:0 0 4px #fff,0 0 16px var(--rai-accent),0 0 44px var(--rai-accent)}
html body .card,html body article,html body form{background:rgba(4,12,20,.78)!important;border:1px solid var(--rai-accent);border-radius:6px;box-shadow:inset 0 0 22px -8px var(--rai-accent)}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:transparent!important;color:var(--rai-accent)!important;border:2px solid var(--rai-accent)!important;border-radius:4px!important;text-transform:uppercase;box-shadow:0 0 18px -4px var(--rai-accent);cursor:pointer}
html body canvas{box-shadow:0 0 30px -6px var(--rai-accent)}
"""),
    "luxury": ("#0c0b09", "#f2eadb", "#b3a68e", "dark", """
html body h1,html body h2,html body h3{font-family:"Cormorant Garamond",Georgia,serif;font-weight:500;letter-spacing:.01em}
html body h2::after{content:"";display:block;width:60px;height:1px;background:var(--rai-accent);margin-top:14px}
html body .card,html body article,html body form{background:linear-gradient(180deg,#17140f,#100e0b)!important;border:1px solid rgba(201,162,39,.25);border-radius:0}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:transparent!important;color:var(--rai-accent)!important;border:1px solid var(--rai-accent)!important;border-radius:0!important;text-transform:uppercase;letter-spacing:.2em;cursor:pointer}
"""),
    "minimal": ("#ffffff", "#0f0f0f", "#6b6b6b", "light", """
html body{font-family:"Manrope",system-ui,sans-serif!important}
html body h1,html body h2,html body h3{font-family:"Manrope",sans-serif;font-weight:800;letter-spacing:-.04em}
html body .card,html body article,html body form{background:#fff!important;border:1px solid #ececec;border-radius:14px;box-shadow:none}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:#0f0f0f!important;color:#fff!important;border:0!important;border-radius:999px!important;cursor:pointer}
"""),
    "retro": ("#f3e9d2", "#1c1a16", "#5e564a", "light", """
html body{font-family:"Rubik",sans-serif!important}
html body h1,html body h2,html body h3{font-family:"Rubik Mono One",sans-serif;text-transform:uppercase}
html body h1{text-shadow:4px 4px 0 var(--rai-accent),8px 8px 0 var(--rai-a3)}
html body .card,html body article,html body form,html body canvas{background-color:#fff8ea!important;border:3px solid #1c1a16;border-radius:6px;box-shadow:6px 6px 0 #1c1a16}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:var(--rai-accent)!important;color:#fff!important;border:3px solid #1c1a16!important;border-radius:6px!important;box-shadow:4px 4px 0 #1c1a16;cursor:pointer}
"""),
    "pastel": ("#fff6fb", "#3a2e48", "#8b7f9b", "light", """
html body{font-family:"Comfortaa",sans-serif!important;background:linear-gradient(140deg,#ffe3f0,#ebe5ff 45%,#dcf6ee) fixed!important}
html body .card,html body article,html body form{background:rgba(255,255,255,.82)!important;border:0;border-radius:26px;box-shadow:0 20px 44px -24px rgba(170,120,200,.6)}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:linear-gradient(120deg,var(--rai-accent),#b39dff)!important;color:#fff!important;border:0!important;border-radius:999px!important;cursor:pointer}
html body img,html body canvas{border-radius:22px}
"""),
    "glass": ("#3b1d6e", "#ffffff", "rgba(255,255,255,.8)", "dark", """
html body{background:linear-gradient(135deg,var(--rai-accent),var(--rai-a3) 50%,var(--rai-a2)) fixed!important}
html body .card,html body article,html body form{background:rgba(255,255,255,.14)!important;border:1px solid rgba(255,255,255,.3);border-radius:24px;backdrop-filter:blur(18px) saturate(160%);-webkit-backdrop-filter:blur(18px) saturate(160%)}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:#fff!important;color:#141414!important;border:0!important;border-radius:999px!important;cursor:pointer}
"""),
    "brutal": ("#ffffff", "#000000", "#222222", "light", """
html body{font-family:"JetBrains Mono",monospace!important}
html body h1,html body h2,html body h3{font-family:"Unbounded",sans-serif;text-transform:uppercase;letter-spacing:-.03em}
html body .card,html body article,html body form,html body canvas{border:3px solid #000;border-radius:0;box-shadow:none}
html body button,html body input[type=submit],html body input[type=button],html body .btn{background:var(--rai-accent)!important;color:#000!important;border:3px solid #000!important;border-radius:0!important;text-transform:uppercase;cursor:pointer}
"""),
}
_THEMES = {"dark": ("#0e0e13", "#f2f1f5", "#a6a3b3"), "light": ("#ffffff", "#17161b", "#5f5d68")}
_GEN_MOTION = """
@keyframes raiRise{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
html body h1,html body h2,html body p,html body img,html body .card,html body article,html body section{animation:raiRise .9s cubic-bezier(.2,.8,.2,1) both}
html body button,html body a,html body .card{transition:transform .2s,box-shadow .2s,filter .2s}
html body button:hover,html body .btn:hover{transform:translateY(-2px);filter:brightness(1.08)}
html body .card:hover,html body article:hover{transform:translateY(-4px)}
@media (prefers-reduced-motion:reduce){html body *{animation:none!important;transition:none!important}}
"""


def _page_is_dark(html):
    """Тёмная ли страница: цвет фона из правил для body/html (если найдётся)."""
    m = re.search(r"(?:^|[}\s,])(?:html|body)\s*\{[^}]*?background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]*\))", html or "")
    if not m:
        return False
    c = m.group(1)
    if c.startswith("#"):
        c = c[1:]
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    else:
        nums = [int(float(x)) for x in re.findall(r"[\d.]+", c)[:3]] + [0, 0, 0]
        r, g, b = nums[:3]
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.45


_STATE_RE = re.compile(r"<style id=\"rai-style\" data-rai='([^']*)'>.*?</style>\s*", re.S)


def generic_state(html):
    m = _STATE_RE.search(html or "")
    if not m:
        return {}
    try:
        st = json.loads(_html.unescape(m.group(1)))
        return st if isinstance(st, dict) else {}
    except ValueError:
        return {}


def generic_css(st):
    """CSS для любой страницы по состоянию {style, theme, accent, motion, font, zoom}."""
    style = st.get("style") if st.get("style") in _GENERIC else None
    accent = st.get("accent") or (STYLES.get(style or "", {}).get("accent")) or "#ff3d81"
    pal = palette(accent)
    if style:
        bg, fg, muted, _theme, css = _GENERIC[style]
    else:
        bg, fg, muted = _THEMES.get(st.get("theme") or "", (None, None, None))
        css = ""
    lines = [f"/* Rai Code: оформление «{STYLES.get(style or 'classic', STYLES['classic'])['label']}» — правьте словами в Rai Code */",
             f":root{{--rai-accent:{accent};--rai-a2:{pal['a2']};--rai-a3:{pal['a3']};--rai-glow:{pal['glow']}}}"]
    if bg:
        # фон — у body (он переходит на всё окно), у html — нет: иначе украшения стиля за страницей не видны
        lines.append(f"html{{background:none!important}}html body{{background-color:{bg}!important;color:{fg}!important}}")
        lines.append("html body header,html body main,html body section,html body footer,html body nav,html body aside,"
                     "html body .container,html body .wrap,html body .wrapper{background-color:transparent!important;color:inherit!important}")
        lines.append(f"html body p,html body li,html body small,html body label{{color:inherit}}html body small{{color:{muted}}}")
        lines.append("html body input:not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]),html body textarea,"
                     "html body select{background:rgba(127,127,127,.12)!important;color:inherit!important;"
                     "border:1px solid rgba(127,127,127,.35)!important;border-radius:12px}")
    lines.append("html body a{color:var(--rai-accent)}html body h1,html body h2{color:inherit}")
    if not style and st.get("accent"):
        lines.append("html body button,html body input[type=submit],html body .btn{background:var(--rai-accent)!important;"
                     "color:#fff!important;border-color:var(--rai-accent)!important}html body h1{color:var(--rai-accent)}")
    lines.append(css)
    if st.get("motion"):
        lines.append(_GEN_MOTION)
    if st.get("font") in FONTS:
        _w, _f, head, body = FONTS[st["font"]]
        lines.append(f"html body h1,html body h2,html body h3{{font-family:{head}!important}}")
        if body:
            lines.append(f"html body{{font-family:{body}!important}}")
    if st.get("zoom"):
        lines.append(f"html body{{zoom:{st['zoom']}}}")
    fams = font_params(style or "classic", st.get("font"))
    imp = ("@import url('https://fonts.googleapis.com/css2?family=" + "&family=".join(fams) + "&display=swap');\n") if fams else ""
    return imp + "\n".join(x.strip("\n") for x in lines if x)


def restyle(html, instruction, defaults=None):
    """Правка оформления ЛЮБОЙ страницы словами. Возвращает (html, «что сделано») или (html, None), если не про вид.

    Понимает: стиль («сделай произведение искусства», «в стиле неон»), тему («тёмная»), цвет («цвет синий»),
    анимации, шрифт, размер текста и новое название («назови «Мой сайт»»)."""
    text = (instruction or "").strip()[:1000]
    low = _low(text)
    st = generic_state(html)
    done = []
    style = detect(text) if wants_design(text) else None
    if style:
        if style == "classic":
            st = {}                      # «верни как было» — всё оформление Rai убираем целиком
        else:
            st["style"] = style
            st["theme"] = STYLES[style]["theme"] or st.get("theme")
        done.append(f"стиль «{STYLES[style]['label']}»")
    color = (defaults or {}).get("color")
    if color:
        st["accent"] = color
        done.append("новый цвет")
    theme = (defaults or {}).get("theme")
    if theme and not style:
        st["theme"] = theme
        if st.get("style") and STYLES[st["style"]]["theme"] not in (None, theme):
            st.pop("style")          # «сделай светлым» после «неона» — неон тёмный, поэтому стиль снимаем
        done.append("тёмная тема" if theme == "dark" else "светлая тема")
    mv = motion(text)
    if mv is not None:
        st["motion"] = mv
        done.append("анимации" if mv else "без анимаций")
    font = detect_font(text)
    if font:
        st["font"] = font
        done.append("новый шрифт")
    z = scale(text)
    if z:
        st["zoom"] = round((st.get("zoom") or 1) * z, 2)
        done.append("крупнее текст" if z > 1 else "мельче текст")
    m = re.search(r"(?:переименуй|назови|название|заголовок)(?:\s+(?:сайта?|страницы))?\s*(?:на|в|:)?\s*[«\"]([^»\"\n]{2,60})[»\"]", text, re.I)
    if m:
        name = _html.escape(m.group(1).strip())
        if re.search(r"<title>.*?</title>", html, re.S | re.I):
            html = re.sub(r"<title>.*?</title>", f"<title>{name}</title>", html, count=1, flags=re.S | re.I)
        if re.search(r"<h1\b[^>]*>.*?</h1>", html, re.S | re.I):
            html = re.sub(r"(<h1\b[^>]*>).*?(</h1>)", lambda k: k.group(1) + name + k.group(2), html, count=1, flags=re.S | re.I)
        done.append(f"новое название: «{m.group(1).strip()}»")
    if not done:
        return html, None
    if "style" not in st and not st.get("theme") and not st.get("accent") and not st.get("motion") and not st.get("font") \
            and not st.get("zoom"):
        html = _STATE_RE.sub("", html)
        return html, ", ".join(done)
    if not st.get("style") and not st.get("theme") and _page_is_dark(html):
        st["theme"] = "dark"
    data = _html.escape(json.dumps(st, ensure_ascii=False), quote=True).replace("'", "&#x27;")
    block = f"<style id=\"rai-style\" data-rai='{data}'>\n{generic_css(st)}\n</style>\n"
    html = _STATE_RE.sub("", html)
    if re.search(r"</head>", html, re.I):
        html = re.sub(r"</head>", lambda _m: block + "</head>", html, count=1, flags=re.I)
    elif re.search(r"<body\b", html, re.I):
        html = re.sub(r"<body\b", lambda _m: block + "<body", html, count=1, flags=re.I)
    else:
        html = block + html
    return html, ", ".join(dict.fromkeys(done))
