"""Навыки Rai, которым нужен интернет: погода, валюты, перевод, поиск.

Используются бесплатные открытые сервисы без ключей:
- погода — Open-Meteo (open-meteo.com);
- курсы валют — open.er-api.com (запасной — cbr-xml-daily.ru, курсы ЦБ РФ);
- перевод — MyMemory (mymemory.translated.net);
- поиск — Википедия.
"""

import re
from datetime import date

import urllib.parse

import creative
import net
import nlp

# ================================================================== погода

WEATHER_CODES = {
    0: ("ясно", "clear"), 1: ("преимущественно ясно", "clear"), 2: ("переменная облачность", "partly"),
    3: ("пасмурно", "cloudy"), 45: ("туман", "fog"), 48: ("туман с изморозью", "fog"),
    51: ("слабая морось", "rain"), 53: ("морось", "rain"), 55: ("сильная морось", "rain"),
    56: ("ледяная морось", "rain"), 57: ("ледяная морось", "rain"),
    61: ("небольшой дождь", "rain"), 63: ("дождь", "rain"), 65: ("сильный дождь", "rain"),
    66: ("ледяной дождь", "rain"), 67: ("сильный ледяной дождь", "rain"),
    71: ("небольшой снег", "snow"), 73: ("снег", "snow"), 75: ("сильный снег", "snow"), 77: ("снежная крупа", "snow"),
    80: ("небольшой ливень", "rain"), 81: ("ливень", "rain"), 82: ("сильный ливень", "rain"),
    85: ("снегопад", "snow"), 86: ("сильный снегопад", "snow"),
    95: ("гроза", "storm"), 96: ("гроза с градом", "storm"), 99: ("сильная гроза с градом", "storm"),
}
_WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

_WEATHER_RE = re.compile(
    r"(погод\w*|температур\w*|прогноз\w*|дожд\w*|снег\w*|холодно|жарко|тепло)", re.I
)
_CITY_RE = re.compile(
    r"(?:\bв|\bво|\bна|\bдля|\bпо)\s+(?:городе\s+|город\s+)?([а-яёa-z][а-яёa-z\- ]{1,40}?)"
    r"(?:\s+(?:сегодня|сейчас|завтра|на завтра|на неделю|на выходные|будет|есть))?[\s?!.]*$",
    re.I,
)


def is_weather_request(text: str) -> bool:
    low = text.lower()
    if not _WEATHER_RE.search(low):
        return False
    # «прогноз» без погоды и «снег»/«дождь» как тема «что такое дождь» — не про погоду
    if re.search(r"что такое|кто такой|нарису|презентац", low):
        return False
    return bool(re.search(r"погод|температур|будет ли|идет ли|идёт ли|холодно|жарко|тепло|прогноз погод", low))


def _city_candidates(phrase: str):
    """«Москве» -> «Москве», «Москва», «Москв»… Open-Meteo ищет по началу названия."""
    phrase = phrase.strip(" -")
    words = phrase.split()
    cands = [phrase]
    if len(words) == 1:
        w = words[0]
        for old, new in (("е", "а"), ("и", "ь"), ("и", "а"), ("е", ""), ("у", "а"), ("и", "я")):
            if w.lower().endswith(old) and len(w) > 3:
                cands.append(w[: -len(old)] + new)
        cands.append(nlp.stem(w.lower()))
    else:
        fixed = []
        for w in words:
            lw = w.lower()
            if lw.endswith(("ем", "ом")) and len(lw) > 4:
                fixed.append(w[:-2] + ("ий" if lw.endswith("ем") else "ый"))
            elif lw.endswith("ой") and len(lw) > 4:
                fixed.append(w[:-2] + "ая")
            elif lw.endswith("е") and len(lw) > 3:
                fixed.append(w[:-1])
            else:
                fixed.append(w)
        cands.append(" ".join(fixed))
    out = []
    for c in cands:
        if c and c.lower() not in [o.lower() for o in out]:
            out.append(c)
    return out[:5]


def geocode(phrase: str):
    for cand in _city_candidates(phrase):
        data = net.fetch_json(net.url("https://geocoding-api.open-meteo.com/v1/search",
                                      name=cand, count=1, language="ru", format="json"), ttl=86400)
        results = data.get("results") or []
        if results:
            return results[0]
    return None


def weather(text: str, session: dict, default_city: str = "Москва"):
    """Вернуть (ответ, вложения) или None, если это не вопрос о погоде."""
    if not is_weather_request(text):
        return None
    m = _CITY_RE.search(text)
    city_phrase = m.group(1).strip() if m else None
    if city_phrase and re.fullmatch(r"(сегодня|завтра|неделю|выходные|улице|дворе)", city_phrase, re.I):
        city_phrase = None
    city_phrase = city_phrase or session.get("city") or default_city
    try:
        place = geocode(city_phrase)
        if not place:
            return f"Не нашёл город «{city_phrase}». Напишите, например: «погода в Казани».", []
        data = net.fetch_json(net.url(
            "https://api.open-meteo.com/v1/forecast",
            latitude=place["latitude"], longitude=place["longitude"], timezone="auto", forecast_days=4,
            wind_speed_unit="ms",
            current="temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
            daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        ), ttl=600)
    except net.NetError as e:
        return f"Не удалось узнать погоду: нет связи с сервисом погоды ({e}).", []

    session["city"] = place.get("name", city_phrase)
    cur = data.get("current", {})
    code = int(cur.get("weather_code", 0))
    desc, kind = WEATHER_CODES.get(code, ("без осадков", "cloudy"))
    temp = cur.get("temperature_2m")
    feels = cur.get("apparent_temperature")
    name = place.get("name", city_phrase)
    where = ", ".join(x for x in (name, place.get("country")) if x)

    def t(v):
        return f"{'+' if v is not None and round(v) > 0 else ''}{round(v)}°" if v is not None else "—"

    lines = [
        f"## Погода: {where}",
        f"Сейчас **{t(temp)}**, {desc}. Ощущается как {t(feels)}.",
        f"Ветер {cur.get('wind_speed_10m', '—')} м/с, влажность {cur.get('relative_humidity_2m', '—')}%.",
    ]
    daily = data.get("daily", {})
    days = daily.get("time", [])
    if days:
        lines.append("\n| День | Погода | Мин | Макс | Осадки |\n|---|---|---|---|---|")
        for i, day in enumerate(days[:4]):
            d = date.fromisoformat(day)
            label = "сегодня" if i == 0 else "завтра" if i == 1 else f"{_WEEKDAYS[d.weekday()]}, {d.day:02d}.{d.month:02d}"
            dcode = int(daily.get("weather_code", [0] * 4)[i])
            prob = (daily.get("precipitation_probability_max") or [None] * 4)[i]
            lines.append(
                f"| {label} | {WEATHER_CODES.get(dcode, ('—',))[0]} | {t(daily['temperature_2m_min'][i])} | "
                f"**{t(daily['temperature_2m_max'][i])}** | {'' if prob is None else str(prob) + '%'} |"
            )
    card = creative.weather_card(name, t(temp), desc, kind, bool(cur.get("is_day", 1)), f"ощущается как {t(feels)}")
    return "\n".join(lines), [card]


# ================================================================== валюты

# (код, слова-формы (регулярное выражение для целого слова), название)
CURRENCIES = [
    ("BYN", r"белорусск\w*|byn", "белорусский рубль"),
    ("CAD", r"канадск\w*|cad", "канадский доллар"),
    ("AUD", r"австралийск\w*|aud", "австралийский доллар"),
    ("SEK", r"шведск\w*|sek", "шведская крона"),
    ("CZK", r"чешск\w*|czk", "чешская крона"),
    ("RUB", r"рубл\w*|руб|rub|₽", "рубль"),
    ("USD", r"доллар\w*|бакс\w*|usd|\$", "доллар США"),
    ("EUR", r"евро|eur|€", "евро"),
    ("CNY", r"юан\w*|cny|¥", "юань"),
    ("GBP", r"фунт\w*|стерлинг\w*|gbp|£", "фунт стерлингов"),
    ("JPY", r"[иий]ен\w*|jpy", "иена"),
    ("KZT", r"тенге|kzt|₸", "тенге"),
    ("UAH", r"гривн\w*|uah|₴", "гривна"),
    ("TRY", r"лир[аыу]?|лирах", "турецкая лира"),
    ("CHF", r"франк\w*|chf", "швейцарский франк"),
    ("KRW", r"вон[аыу]|krw", "вона"),
    ("INR", r"рупи\w*|inr", "индийская рупия"),
    ("PLN", r"злот\w*|pln", "злотый"),
    ("KGS", r"сом(?:а|ов|ы)?|kgs", "сом"),
    ("UZS", r"сум(?:ов)?|uzs", "сум"),
    ("GEL", r"лари|gel", "лари"),
    ("AMD", r"драм(?:ов)?|amd", "драм"),
    ("AZN", r"манат\w*|azn", "манат"),
    ("AED", r"дирхам\w*|aed", "дирхам ОАЭ"),
    ("ILS", r"шекел\w*|ils", "шекель"),
    ("THB", r"бат(?:а|ов)?|thb", "бат"),
    ("BRL", r"реал(?:а|ов)|brl", "бразильский реал"),
]
# «белорусских рублей», «канадских долларов» — второе слово не отдельная валюта
_COMPOUND = {"BYN": "RUB", "CAD": "USD", "AUD": "USD", "SEK": "", "CZK": ""}


def _find_currencies(text):
    """Найти валюты в тексте по порядку упоминания: [(позиция, код)]."""
    low = text.lower().replace("ё", "е")
    found = []
    prev_word_code = None  # валюта, найденная в предыдущем слове
    for m in re.finditer(r"[a-zа-я]+|[$€£¥₽₸₴]", low):
        word = m.group(0)
        code = next((c for c, pattern, _ in CURRENCIES if re.fullmatch(pattern, word)), None)
        skip = prev_word_code and code is not None and (
            _COMPOUND.get(prev_word_code) == code or (prev_word_code in ("SEK", "CZK") and word.startswith("крон")))
        if code and not skip:
            found.append((m.start(), code))
        if prev_word_code in ("SEK", "CZK") and word.startswith("крон"):
            code = None
        prev_word_code = None if skip else code
    return found


def is_currency_request(text: str) -> bool:
    low = text.lower()
    if re.search(r"курс\w*\s+валют|валют\w*\s+курс", low):
        return True
    cur = _find_currencies(text)
    if not cur:
        return False
    if re.search(r"\bкурс", low):
        return True
    has_number = bool(re.search(r"\d", low))
    if len(cur) >= 2 and (has_number or re.search(r"\bв\b|\bto\b|сколько", low)):
        return True
    return has_number and bool(re.search(r"сколько|стоит|это|будет", low))


def rates():
    """Курсы к доллару: {"USD": 1, "RUB": 92.1, ...}, дата."""
    try:
        data = net.fetch_json("https://open.er-api.com/v6/latest/USD", ttl=3600)
        if data.get("result") == "success":
            return data["rates"], data.get("time_last_update_utc", "")[:16]
    except net.NetError:
        pass
    data = net.fetch_json("https://www.cbr-xml-daily.ru/daily_json.js", ttl=3600)
    rub = {"RUB": 1.0}
    for code, v in data.get("Valute", {}).items():
        rub[code] = v["Value"] / v["Nominal"]  # рублей за 1 единицу
    usd = rub["USD"]
    return {code: usd / value for code, value in rub.items()}, "ЦБ РФ, " + data.get("Date", "")[:10]


def _money(v):
    if float(v).is_integer() and abs(v) < 1e15:
        return f"{int(v):,}".replace(",", " ")
    if v >= 100:
        s = f"{v:,.2f}"
    elif v >= 1:
        s = f"{v:,.4f}".rstrip("0").rstrip(".")
    else:
        s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s.replace(",", " ").replace(".", ",")


def _name(code):
    return next((n for c, _, n in CURRENCIES if c == code), code)


def currency(text: str):
    if not is_currency_request(text):
        return None
    try:
        table, updated = rates()
    except net.NetError as e:
        return f"Не удалось получить курсы валют: нет связи ({e})."
    found = [code for _, code in _find_currencies(text)]
    low = text.lower()
    if not found or re.search(r"курс\w*\s+валют", low) and len(found) < 2:
        rows = "\n".join(
            f"| {_name(c)} | {c} | **{_money(table['RUB'] / table[c])} ₽** |"
            for c in ("USD", "EUR", "CNY", "GBP", "JPY", "KZT", "BYN", "TRY") if c in table
        )
        return f"## Курсы валют к рублю\n\n| Валюта | Код | Курс |\n|---|---|---|\n{rows}\n\nОбновлено: {updated}."
    num = re.search(r"(\d[\d\s]*(?:[.,]\d+)?)\s*(тыс\w*|к\b|млн|миллион\w*)?", low)
    amount = 1.0
    if num:
        amount = float(num.group(1).replace(" ", "").replace(",", "."))
        mult = num.group(2) or ""
        amount *= 1000 if mult.startswith(("тыс", "к")) else 1_000_000 if mult.startswith(("млн", "миллион")) else 1
    src = found[0]
    dst = found[1] if len(found) > 1 and found[1] != src else ("RUB" if src != "RUB" else "USD")
    if src not in table or dst not in table:
        return "Для этой валюты у меня нет курса."
    value = amount * table[dst] / table[src]
    one = table[dst] / table[src]
    return (f"**{_money(amount)} {src} = {_money(value)} {dst}**\n\n"
            f"Курс: 1 {_name(src)} = {_money(one)} {dst}. Обновлено: {updated}.")


# ================================================================== перевод

LANGS = {
    "en": ("английск", "английский"), "ru": ("русск", "русский"), "de": ("немецк", "немецкий"),
    "fr": ("французск", "французский"), "es": ("испанск", "испанский"), "it": ("итальянск", "итальянский"),
    "pt": ("португальск", "португальский"), "pl": ("польск", "польский"), "uk": ("украинск", "украинский"),
    "be": ("белорусск", "белорусский"), "kk": ("казахск", "казахский"), "zh": ("китайск", "китайский"),
    "ja": ("японск", "японский"), "ko": ("корейск", "корейский"), "ar": ("арабск", "арабский"),
    "tr": ("турецк", "турецкий"), "el": ("греческ", "греческий"), "he": ("иврит", "иврит"),
    "hi": ("хинди", "хинди"), "cs": ("чешск", "чешский"), "nl": ("нидерландск", "нидерландский"),
    "sv": ("шведск", "шведский"), "no": ("норвежск", "норвежский"), "da": ("датск", "датский"),
    "fi": ("финск", "финский"), "hu": ("венгерск", "венгерский"), "ro": ("румынск", "румынский"),
    "bg": ("болгарск", "болгарский"), "sr": ("сербск", "сербский"), "hr": ("хорватск", "хорватский"),
    "lv": ("латышск", "латышский"), "lt": ("литовск", "литовский"), "et": ("эстонск", "эстонский"),
    "ka": ("грузинск", "грузинский"), "hy": ("армянск", "армянский"), "az": ("азербайджанск", "азербайджанский"),
    "uz": ("узбекск", "узбекский"), "tt": ("татарск", "татарский"), "fa": ("персидск", "персидский"),
    "vi": ("вьетнамск", "вьетнамский"), "th": ("тайск", "тайский"), "id": ("индонезийск", "индонезийский"),
    "la": ("латын", "латынь"), "eo": ("эсперанто", "эсперанто"), "ky": ("киргизск", "киргизский"),
    "tg": ("таджикск", "таджикский"), "mn": ("монгольск", "монгольский"), "sk": ("словацк", "словацкий"),
    "sl": ("словенск", "словенский"), "ga": ("ирландск", "ирландский"), "is": ("исландск", "исландский"),
}
_LANG_ALIAS = {"голландск": "nl", "фарси": "fa", "по-русск": "ru", "англ": "en"}

_STOP = {
    "en": "the and is are you to of in it what hello how this that with for my your i we they be not have".split(),
    "de": "und der die das ist nicht ich du ein eine wie guten danke mit für ist sie wir haben".split(),
    "fr": "le la les et est je vous un une bonjour pas que merci avec pour nous il elle".split(),
    "es": "el la los las y es que de hola como estás por una gracias con para muy yo".split(),
    "it": "il lo la e è che di ciao come sono non una grazie con per io tu".split(),
    "pt": "o a os e é que de olá você não um uma obrigado com para eu muito".split(),
    "pl": "i w nie jest to się na cześć jak dzień dobry dziękuję ja ty".split(),
    "tr": "ve bir bu ne merhaba nasılsın için değil ben sen teşekkür".split(),
    "nl": "de het een en is niet ik hallo hoe dank je wij".split(),
    "sv": "och är jag du det inte hej tack en ett".split(),
    "cs": "a je to se na ne ahoj jak děkuji já ty".split(),
    "id": "dan yang di ini itu apa saya kamu terima kasih".split(),
}
_HINTS = [("es", "ñ¿¡"), ("de", "ßäöü"), ("tr", "ğşı"), ("pl", "łąęśźżćń"), ("pt", "ãõ"),
          ("fr", "àâçèêëîïôœùû"), ("cs", "ěřůčšž"), ("ro", "ăîșț"), ("hu", "őű")]


def detect_language(text: str) -> str:
    """Свой определитель языка: по алфавиту, особым буквам и частым словам."""
    s = text.lower()
    scripts = [
        (r"[぀-ヿ]", "ja"), (r"[가-힯]", "ko"), (r"[一-鿿]", "zh"),
        (r"[؀-ۿ]", "ar"), (r"[֐-׿]", "he"), (r"[Ͱ-Ͽ]", "el"),
        (r"[฀-๿]", "th"), (r"[ऀ-ॿ]", "hi"), (r"[Ⴀ-ჿ]", "ka"),
        (r"[԰-֏]", "hy"),
    ]
    for pattern, code in scripts:
        if re.search(pattern, s):
            if code == "ar" and re.search(r"[پچژگ]", s):
                return "fa"
            return code
    if re.search(r"[а-яёіїєґўәғқңөұүһђћџјљњ]", s):
        if re.search(r"[әғқңөұүһ]", s):
            return "kk"
        if re.search(r"[їєґ]", s) or (re.search(r"і", s) and not re.search(r"ў", s)):
            return "uk"
        if re.search(r"ў", s):
            return "be"
        if re.search(r"[ђћџјљњ]", s):
            return "sr"
        return "ru"
    words = re.findall(r"[a-zà-ÿąęłśźżćńěřůčšžőűăîșțğşı]+", s)
    scores = {lang: sum(2 for w in words if w in stop) for lang, stop in _STOP.items()}
    for lang, letters in _HINTS:
        scores[lang] = scores.get(lang, 0) + sum(3 for ch in s if ch in letters)
    best = max(scores, key=scores.get) if scores else "en"
    return best if scores.get(best) else "en"


_TRANSLATE_RE = re.compile(
    r"^\s*(?:пожалуйста\s+)?(?:переведи(?:те)?|перевод|translate|как (?:будет|сказать|пишется)|как)\b", re.I
)


def _lang_code(word: str):
    w = word.lower().replace("ё", "е")
    for alias, code in _LANG_ALIAS.items():
        if w.startswith(alias):
            return code
    for code, (prefix, _) in LANGS.items():
        if w.startswith(prefix):
            return code
    return None


def is_translate_request(text: str) -> bool:
    low = text.lower()
    if re.match(r"^\s*(?:пожалуйста\s+)?(?:переведи|перевод|translate)\b", low):
        return True
    return bool(re.search(r"\bпо-[а-я]+(?:ски|цки)\b", low) and re.match(r"^\s*как\b", low))


def parse_translate(text: str):
    """Разобрать запрос: (текст, язык-источник или None, язык перевода или None)."""
    src = dst = None
    body = text.strip()
    quoted = re.search(r"[«\"“'](.+?)[»\"”']", body)
    m = re.search(r"\bс\s+([а-я]+(?:ого|ого языка)?)\s+(?:на|в)\s+([а-я-]+)", body, re.I)
    if m:
        src, dst = _lang_code(m.group(1)), _lang_code(m.group(2))
        body = body.replace(m.group(0), " ")
    m = re.search(r"\b(?:на|в)\s+([а-я-]+?)(?:\s+язык)?\b(?=[\s:,.!?]|$)", body, re.I)
    if not dst and m and _lang_code(m.group(1)):
        dst = _lang_code(m.group(1))
        body = body.replace(m.group(0), " ", 1)
    m = re.search(r"\bпо-([а-я]+)", body, re.I)
    if not dst and m and _lang_code(m.group(1)):
        dst = _lang_code(m.group(1))
        body = body.replace(m.group(0), " ", 1)
    m = re.search(r"\b(?:to|into)\s+([a-z]+)\s*$", body, re.I)
    if not dst and m:
        names = {"english": "en", "russian": "ru", "german": "de", "french": "fr", "spanish": "es",
                 "italian": "it", "chinese": "zh", "japanese": "ja", "korean": "ko", "ukrainian": "uk"}
        if m.group(1).lower() in names:
            dst = names[m.group(1).lower()]
            body = body[: m.start()]
    if quoted:
        body = quoted.group(1)
    else:
        body = _TRANSLATE_RE.sub("", body, count=1)
        body = re.sub(r"^\s*(?:текст|слово|фразу|предложение)?\s*[:\-—]?\s*", "", body, flags=re.I)
        body = re.sub(r"^\s*(?:будет|сказать)\s+", "", body, flags=re.I)
    return body.strip(" \t\n:—-?"), src, dst


def _chunks(text, size=450):
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > size:
            parts.append(sentence[:size]); sentence = sentence[size:]
        if len(cur) + len(sentence) + 1 > size:
            parts.append(cur); cur = ""
        cur = (cur + " " + sentence).strip()
    if cur:
        parts.append(cur)
    return parts


def translate(text: str):
    if not is_translate_request(text):
        return None
    body, src, dst = parse_translate(text)
    if not body:
        return "Что перевести? Напишите, например: «переведи на английский: доброе утро»."
    if len(body) > 3000:
        return "Текст слишком длинный для перевода — до 3000 символов за раз."
    src = src or detect_language(body)
    dst = dst or ("en" if src == "ru" else "ru")
    if src == dst:
        dst = "en" if src != "en" else "ru"
    out = []
    try:
        for part in _chunks(body):
            data = net.fetch_json(net.url("https://api.mymemory.translated.net/get", q=part, langpair=f"{src}|{dst}"),
                                  ttl=86400)
            if int(data.get("responseStatus", 200)) != 200:
                return f"Сервис перевода ответил: {data.get('responseDetails', 'ошибка')}."
            out.append(data.get("responseData", {}).get("translatedText", ""))
    except net.NetError as e:
        return f"Не удалось перевести: нет связи с сервисом перевода ({e})."
    result = " ".join(x for x in out if x).strip()
    return (f"**{LANGS.get(src, (None, src))[1].capitalize()} → {LANGS.get(dst, (None, dst))[1]}:**\n\n"
            f"> {body}\n\n{result}")


# ================================================================== поиск

_SEARCH_RE = re.compile(
    r"^\s*(?:найди|поищи|загугли|погугли|найти|ищи|поиск)(?:\s+(?:в\s+интернете|в\s+сети|в\s+гугле|информацию))*"
    r"(?:\s+(?:про|о|об|что такое))?\s+(.+?)[\s?!.]*$",
    re.I,
)


def explicit_search(text: str):
    m = _SEARCH_RE.match(text)
    return m.group(1) if m else None


def _first_sentences(text, limit=700):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > 200 else cut.rstrip() + "…"


def web_search(query: str):
    """Найти ответ в Википедии: (ответ, вложения) или None."""
    query = query.strip(" ?!.")
    if len(query) < 2:
        return None
    for lang in ("ru", "en"):
        found = net.fetch_json(net.url(
            f"https://{lang}.wikipedia.org/w/api.php", action="query", list="search", srsearch=query,
            srlimit=1, format="json", origin="*", utf8=1), ttl=3600)
        hits = found.get("query", {}).get("search", [])
        if not hits:
            continue
        title = hits[0]["title"]
        page = net.fetch_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
                              + urllib.parse.quote(title.replace(" ", "_")), ttl=3600)
        extract = (page.get("extract") or "").strip()
        if not extract:
            continue
        link = page.get("content_urls", {}).get("desktop", {}).get("page", "")
        answer = f"**{page.get('title', title)}**\n\n{_first_sentences(extract)}"
        if lang == "en":
            answer += "\n\n*(нашёл только в английской Википедии)*"
        answer += f"\n\nИсточник: [Википедия]({link})" if link else ""
        attachments = []
        thumb = page.get("thumbnail", {}).get("source") or page.get("originalimage", {}).get("source")
        if thumb:
            attachments.append({"type": "photo", "url": thumb, "title": page.get("title", title), "source": link})
        return answer, attachments
    return None
