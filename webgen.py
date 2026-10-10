"""Конструктор сайтов Rai: из описания словами — готовый сайт (один index.html), и правки словами.

    spec = new_spec("сайт кофейни «Зерно» в тёмных тонах, меню: капучино 190, латте 220")
    html = render(spec)                       # готовая страница, спецификация спрятана внутри
    spec, done = edit_spec(spec, "добавь раздел отзывы")
    spec = spec_from_html(html)               # продолжить правку уже готовой страницы

Без внешних сервисов: тексты, картинки (SVG) и вёрстка собираются здесь же.
"""

import datetime
import html as _html
import json
import random
import re
import zlib

import creative

# ------------------------------------------------------------------ словари

TYPES = {
    # тип: (слова, название по умолчанию, слоган, разделы)
    "cafe": (("кафе", "ресторан", "кофейн", "пиццер", "бар ", "пекарн", "кондитер", "бургер", "суши", "столов", "шаурм", "еда"),
             "Уютное кафе", "Вкусно, тепло и по-домашнему", ["about", "menu", "gallery", "reviews", "form", "contacts"]),
    "shop": (("магазин", "shop", "товар", "продаж", "каталог", "одежд", "цветочн", "букет", "маркет"),
             "Интернет-магазин", "Лучшие товары с быстрой доставкой", ["about", "products", "features", "reviews", "contacts"]),
    "portfolio": (("портфолио", "резюме", "обо мне", "программист", "разработчик", "дизайнер", "фотограф", "художник", "визитк"),
                  "Моё портфолио", "Проекты, навыки и контакты", ["about", "skills", "projects", "contacts"]),
    "blog": (("блог", "статьи", "новост", "дневник", "журнал"),
             "Мой блог", "Заметки, идеи и истории", ["about", "posts", "contacts"]),
    "school": (("школ", "курс", "обучени", "урок", "репетитор", "академи", "учеб"),
               "Онлайн-школа", "Учитесь в своём темпе с поддержкой преподавателей", ["about", "courses", "prices", "faq", "form", "contacts"]),
    "fitness": (("фитнес", "спортзал", "тренаж", "йог", "тренер", "спорт", "бокс", "танц"),
                "Фитнес-клуб", "Сильнее с каждой тренировкой", ["about", "services", "prices", "team", "form", "contacts"]),
    "beauty": (("салон красоты", "маникюр", "барбер", "парикмахер", "косметолог", "красот", "ресниц", "бров"),
               "Салон красоты", "Красота, которой хочется делиться", ["about", "services", "prices", "gallery", "form", "contacts"]),
    "medical": (("клиник", "стоматолог", "врач", "медицин", "здоровь", "аптек", "ветеринар"),
                "Клиника", "Заботимся о вашем здоровье", ["about", "services", "team", "prices", "form", "contacts"]),
    "travel": (("туризм", "путешеств", "турагент", "отель", "гостиниц", "хостел", "база отдыха", "экскурси"),
               "Путешествия", "Откройте для себя новые места", ["about", "services", "gallery", "reviews", "form", "contacts"]),
    "auto": (("автосервис", "шиномонтаж", "автомойк", "автосалон", "авто", "машин", "такси"),
             "Автосервис", "Надёжно, быстро и с гарантией", ["about", "services", "prices", "reviews", "form", "contacts"]),
    "realty": (("недвижим", "квартир", "аренд", "риелтор", "новострой"),
               "Недвижимость", "Поможем найти дом мечты", ["about", "products", "features", "form", "contacts"]),
    "event": (("свадьб", "мероприяти", "праздник", "день рождения", "конференц", "фестивал", "вечеринк"),
              "Наше событие", "Ждём вас — будет здорово!", ["about", "schedule", "gallery", "form", "contacts"]),
    "music": (("музык", "групп", "исполнител", "диджей", "dj", "рэп", "песн"),
              "Музыкальная группа", "Новые треки и концерты", ["about", "tracks", "schedule", "gallery", "contacts"]),
    "gaming": (("игр", "гейм", "клан", "minecraft", "майнкрафт", "киберспорт", "сервер"),
               "Игровой проект", "Играем вместе — присоединяйся", ["about", "features", "team", "contacts"]),
    "landing": (("лендинг", "стартап", "продукт", "приложени", "сервис", "платформ", "бот"),
                "Новый сервис", "Решаем задачу быстро и просто", ["features", "how", "prices", "faq", "form", "contacts"]),
    "personal": (("личный сайт", "про себя", "про мою", "про моего", "про мой", "про моё", "про мое", "хобби", "семь"),
                 "Мой сайт", "Всё самое интересное — здесь", ["about", "gallery", "contacts"]),
    "business": (("компани", "бизнес", "услуг", "фирм", "агентств", "студи", "ремонт", "салон", "строител", "клининг"),
                 "Наша компания", "Делаем работу качественно и в срок", ["about", "services", "reviews", "form", "contacts"]),
}

SECTIONS = {
    "about": ("о нас", "обо мне", "о компании", "о проекте", "about"),
    "services": ("услуг",),
    "prices": ("цен", "тариф", "прайс", "стоимост"),
    "reviews": ("отзыв",),
    "form": ("заявк", "форм", "запис", "бронир", "обратн"),
    "contacts": ("контакт", "связ", "адрес"),
    "gallery": ("галере", "фото", "картин"),
    "menu": ("меню",),
    "products": ("товар", "каталог", "продукц", "объект"),
    "projects": ("проект", "работ", "кейс"),
    "skills": ("навык", "умени", "технолог"),
    "posts": ("стать", "пост", "запис", "новост"),
    "faq": ("вопрос", "faq", "чаво"),
    "team": ("команд", "сотрудник", "участник", "тренер", "врач", "мастер"),
    "schedule": ("расписани", "программ", "афиш", "концерт"),
    "courses": ("курс", "урок", "программы обучения"),
    "features": ("преимуществ", "возможност", "почему мы", "особенност"),
    "how": ("как это работает", "как работает", "этап", "шаг"),
    "tracks": ("трек", "песн", "альбом"),
    "facts": ("факт", "интересн"),
}

TITLES = {
    "about": "О нас", "services": "Услуги", "prices": "Цены", "reviews": "Отзывы", "contacts": "Контакты",
    "gallery": "Галерея", "menu": "Меню", "products": "Каталог", "projects": "Проекты", "skills": "Навыки",
    "posts": "Статьи", "faq": "Вопросы и ответы", "team": "Команда", "schedule": "Расписание", "courses": "Курсы",
    "features": "Преимущества", "how": "Как это работает", "tracks": "Треки", "form": "Оставьте заявку",
    "facts": "Интересные факты", "text": "Раздел",
}

COLORS = {
    "красн": "#e10600", "алый": "#ff2a2a", "бордов": "#8b0f1a", "темно-син": "#1e3a8a", "син": "#1e5bff",
    "голуб": "#2aa7e8", "зелен": "#1f9d55", "салатов": "#65a30d", "мятн": "#10b981", "желт": "#f5b800",
    "оранж": "#ff7a00", "фиолет": "#7c3aed", "сирен": "#a855f7", "розов": "#ff4f93", "бирюз": "#14b8a6",
    "золот": "#c9a227", "коричн": "#8b5a2b", "бежев": "#c8a97e", "сер": "#6b7280",
}

PALETTES = {"light": ("#faf8f5", "#1d1a17", "#ffffff"), "dark": ("#0c0c0e", "#f2f0f0", "#17171a")}

_SITE_WORDS = re.compile(r"сайт|лендинг|landing|веб-?страниц|страничк|страниц[уаы]\b|визитк|портфолио|website|web ?page|homepage")
_EDIT_RE = re.compile(r"^\s*(?:а\s+)?(?:теперь\s+)?(?:добавь|добавить|убери|удали|скрой|переименуй|назови|измени|поменяй|замени|"
                      r"сделай\s+(?:его\s+|сайт\s+|фон\s+)?(?:тёмн|темн|светл|черн|чёрн|бел|красн|син|зелен|зелён|желт|жёлт|оранж|фиолет|розов|бирюз|золот|голуб|сер|коричн)|"
                      r"цвет|другие картинки|новые картинки|слоган|почт|телефон)", re.I)


def is_site_request(text):
    """Просьба сделать сайт или страницу (а не программу)."""
    low = (text or "").lower().replace("ё", "е")
    return bool(_SITE_WORDS.search(low))


def is_edit(text):
    """Похоже на правку уже сделанного сайта: «добавь раздел цены», «сделай синим»."""
    return bool(_EDIT_RE.search((text or "").lower().replace("ё", "е")))


# ------------------------------------------------------------------ разбор описания

def _low(s):
    return (s or "").lower().replace("ё", "е")


def _has(text, words):
    """Есть ли слово (или начало слова) в тексте: «бот» не находится внутри «работы»."""
    return any(re.search(r"(?<![a-zа-я0-9])" + re.escape(w.replace("ё", "е")), text) for w in words)


def detect_type(low):
    for key, (words, *_rest) in TYPES.items():
        if _has(low, words):
            return key
    return None


def section_kind(name):
    low = _low(name).strip()
    for kind, words in SECTIONS.items():
        if _has(low, words):
            return kind
    return "text"


def _cap(s):
    s = (s or "").strip()
    return s[:1].upper() + s[1:]


_NAME_NOUNS = (r"кафе|кофейни|кофейня|ресторана?|пекарни|пиццерии|бара|магазина?|компании|фирмы|агентства|студии|салона|клиники|"
               r"школы|академии|группы|клана?|клуба|отеля|автосервиса|бренда?|проекта|сервиса|приложения|бота|канала|команды")
_STOP = {"в", "во", "с", "со", "для", "и", "на", "про", "о", "об", "по", "из", "у", "где", "который", "которая", "с", "тёмных",
         "темных", "светлых", "синих", "красных", "тонах", "цвете", "стиле", "меню", "разделами", "контактами", "отзывами"}


def extract_name(prompt):
    """Название: из «кавычек», «под названием X», «кофейни Зерно», «группы Ночные Волки»."""
    m = re.search(r"[«\"“]([^»\"”]{2,60})[»\"”]", prompt)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:под названием|называется|с названием|название)\s*:?\s*([\w\-.&' ]{2,40}?)(?=[,.;!]|\s+(?:в|с|для|и)\s|$)", prompt, re.I)
    if m:
        return _cap(m.group(1).strip())
    m = re.search(rf"(?:{_NAME_NOUNS})\s+([A-ZА-ЯЁ][\w\-.&']*(?:\s+[A-ZА-ЯЁ][\w\-.&']*){{0,3}})", prompt)
    if m:
        return m.group(1).strip()
    m = re.search(rf"(?:{_NAME_NOUNS})\s+([a-zа-яё][\w\-]{{2,20}})\b", prompt, re.I)
    if m and _low(m.group(1)) not in _STOP and not any(_low(m.group(1)).startswith(c) for c in COLORS) \
            and section_kind(m.group(1)) == "text" and not detect_type(_low(m.group(1)) + " "):
        return _cap(m.group(1))
    return None


# Частые профессии и заведения: родительный → именительный, чтобы заголовок «сайт ДЛЯ тренера» стал «Тренер».
_SUBJ_FIX = {
    "тренера": "тренер", "магазина": "магазин", "магазинчика": "магазинчик", "салона": "салон",
    "студии": "студия", "школы": "школа", "курсов": "курсы", "фотографа": "фотограф", "дизайнера": "дизайнер",
    "мастера": "мастер", "врача": "врач", "юриста": "юрист", "адвоката": "адвокат", "репетитора": "репетитор",
    "парикмахера": "парикмахер", "косметолога": "косметолог", "психолога": "психолог", "стоматолога": "стоматолог",
    "ресторана": "ресторан", "кофейни": "кофейня", "пекарни": "пекарня", "кондитерской": "кондитерская",
    "компании": "компания", "фирмы": "фирма", "агентства": "агентство", "клуба": "клуб", "центра": "центр",
    "барбершопа": "барбершоп", "автосервиса": "автосервис", "клиники": "клиника", "отеля": "отель",
    "кафе": "кафе", "бара": "бар", "пиццерии": "пиццерия", "блогера": "блогер", "блогерши": "блогер",
    "музыканта": "музыкант", "группы": "группа", "бренда": "бренд", "стартапа": "стартап", "сервиса": "сервис",
    "приложения": "приложение", "питомника": "питомник", "мастерской": "мастерская", "турагентства": "турагентство",
}


def extract_subject(prompt):
    """«сайт для тренера по теннису» -> «Тренер по теннису»: тема сайта из запроса, если явного названия нет."""
    m = re.search(r"(?:сайт\w*|лендинг\w*|веб-?сайт\w*|страниц\w+|визитк\w+)\s+(?:для|про|о|об|под)\s+"
                  r"([\w\- ]{3,50}?)(?:[.,!?;]|\s+(?:в|с|со|на|из|без|и)\s|$)", prompt, re.I)
    if not m:
        m = re.search(r"(?:сайт|лендинг)\s+([\w\- ]{3,40}?)(?:[.,!?;]|\s+(?:в|с|со|на|из)\s|$)", prompt, re.I)
    if not m:
        return None
    sub = " ".join(m.group(1).split())
    low = _low(sub)
    if _has(low, ("себ", "мою", "мой", "мое", "моё", "моего", "моих", "нас", "меня", "наш")) or len(sub) < 3:
        return None
    if detect_type(low + " ") is None and section_kind(sub) != "text":
        return None    # это слова раздела («цены», «контакты»), а не тема
    words = sub.split()
    words[0] = _SUBJ_FIX.get(_low(words[0]), words[0])
    return _cap(" ".join(words))


def extract_topic(prompt):
    """«сайт про космос» -> «космос»; None, если это не сайт-рассказ о теме."""
    m = re.search(r"\b(?:про|о|об|посвящ[её]нн\w*)\s+([\w\- ]{3,50}?)(?:[.,!?;]|\s+(?:в|с|со|и|на)\s|$)", prompt, re.I)
    if not m:
        return None
    topic = m.group(1).strip()
    if _has(_low(topic), ("себ", "мою", "мой", "мое", "моё", "моего", "моих", "нас", "меня", "компани", "наш")):
        return None
    return topic


def extract_sections(prompt):
    m = re.search(r"(?:раздел\w*|блок\w*|секци\w*)\s*:?\s*(.+?)(?:\.|;|$)", prompt, re.I)
    if not m:
        return []
    parts = re.split(r"\s*(?:,|\sи\s|\+)\s*", m.group(1))
    return [p.strip(" \t«»\"'") for p in parts if p.strip(" \t«»\"'") and len(p) <= 40]


_GRAY = re.compile(r"^сер(?:ый|ая|ое|ые|ого|ой|ую|ым|ых|ыми|о)?$")


def extract_color(low):
    tokens = re.findall(r"[a-zа-я]+(?:-[a-zа-я]+)?", low)
    for word, hex_ in COLORS.items():
        for t in tokens:
            if word == "сер" and _GRAY.match(t) or word != "сер" and t.startswith(word):
                return hex_
    m = re.search(r"#[0-9a-f]{6}\b", low)
    return m.group(0) if m else None


def extract_contacts(prompt, contacts):
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+\w", prompt)
    if m:
        contacts["email"] = m.group(0)
    m = re.search(r"(?:\+7|8|\+\d{1,3})[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}", prompt)
    if m:
        contacts["phone"] = m.group(0).strip()
    m = re.search(r"(?:адрес|находимся)\s*:?\s*([^.;\n]{5,80})", prompt, re.I)
    if m:
        contacts["address"] = m.group(1).strip()
    m = re.search(r"(?:telegram|телеграм\w*|тг)\s*:?\s*@?([A-Za-z0-9_]{4,32})\b", prompt, re.I)
    if m and _low(m.group(1)) not in ("бота", "бот", "канал"):
        contacts["telegram"] = m.group(1)
    return contacts


_PRICE = r"(\d[\d\s]{0,8}(?:[.,]\d+)?)\s*(?:₽|р\.?|руб\w*|\$|€)?"


def extract_items(prompt, kind):
    """«меню: капучино 190, латте 220 и чизкейк 290» -> [{"title": "Капучино", "price": "190 ₽"}, …]."""
    words = {"menu": r"меню", "prices": r"цены|прайс|тарифы", "products": r"товары|каталог", "services": r"услуги",
             "courses": r"курсы", "team": r"команда|тренеры|врачи|мастера", "skills": r"навыки|технологии|умею",
             "projects": r"проекты"}.get(kind)
    if not words:
        return None
    m = re.search(rf"(?:{words})\s*:\s*(.+?)(?:\.\s|;|\n|$)", prompt, re.I)
    if not m:
        return None
    items = []
    for part in re.split(r"\s*(?:,|\sи\s)\s*", m.group(1)):
        part = part.strip(" .«»\"'")
        if not part:
            continue
        pm = re.match(rf"(.+?)\s*[-—–:]?\s*{_PRICE}$", part)
        if pm and kind in ("menu", "prices", "products", "services", "courses"):
            price = re.sub(r"\s+", " ", pm.group(2)).strip()
            items.append({"title": _cap(pm.group(1).strip(" -—–:")), "price": f"{price} ₽", "text": ""})
        else:
            items.append({"title": _cap(part), "text": ""})
    return items[:12] or None


# ------------------------------------------------------------------ содержимое разделов

_SERVICES = {
    "fitness": [("Тренажёрный зал", "Современное оборудование и зона свободных весов."), ("Групповые занятия", "Йога, функциональный тренинг, растяжка."),
                ("Персональные тренировки", "Программа под вашу цель и уровень.")],
    "beauty": [("Стрижки и укладки", "Подберём форму, которая подчеркнёт вашу красоту."), ("Маникюр и педикюр", "Стерильные инструменты и стойкие покрытия."),
               ("Уход за лицом", "Процедуры для сияющей и здоровой кожи.")],
    "medical": [("Консультация врача", "Внимательный осмотр и понятный план лечения."), ("Диагностика", "Анализы и обследования в одном месте."),
                ("Лечение", "Современные методы и комфорт на каждом этапе.")],
    "auto": [("Диагностика", "Компьютерная проверка всех систем за 30 минут."), ("Ремонт двигателя", "Оригинальные запчасти и гарантия на работы."),
             ("Шиномонтаж", "Сезонная замена и хранение шин.")],
    "travel": [("Туры", "Готовые путешествия с перелётом и проживанием."), ("Экскурсии", "Лучшие маршруты с опытными гидами."),
               ("Визы и страховки", "Поможем с документами.")],
    "cafe": [("Завтраки", "Каждый день с 8:00."), ("Банкеты", "Отметим ваш праздник."), ("Доставка", "Привезём горячим.")],
}
_DEFAULT_SERVICES = [("Консультация", "Разберёмся в задаче и предложим решение."), ("Работа под ключ", "Сделаем всё сами — от плана до результата."),
                     ("Поддержка", "Остаёмся на связи и помогаем после сдачи.")]

_ABOUT = {
    "cafe": "«{n}» — место, куда хочется возвращаться. Готовим из свежих продуктов, варим ароматный кофе и всегда рады гостям.",
    "shop": "«{n}» — магазин, где легко найти нужное. Проверяем каждый товар, быстро доставляем и помогаем с выбором.",
    "portfolio": "Привет! Я {n}. Создаю проекты, которые решают реальные задачи, и постоянно учусь новому.",
    "blog": "Здесь я пишу о том, что меня вдохновляет: идеи, опыт, полезные находки.",
    "school": "«{n}» — обучение с практикой и поддержкой. Короткие уроки, домашние задания и обратная связь от преподавателей.",
    "fitness": "«{n}» — зал, где каждый найдёт свой спорт. Опытные тренеры, удобное расписание и дружная атмосфера.",
    "beauty": "«{n}» — мастера, которые любят своё дело. Качественные материалы, уют и внимание к каждому гостю.",
    "medical": "«{n}» — современная клиника с опытными врачами. Принимаем без очередей и объясняем всё понятным языком.",
    "travel": "«{n}» — путешествия без хлопот. Подберём маршрут, забронируем отели и будем на связи всю поездку.",
    "auto": "«{n}» — сервис для тех, кто ценит своё время. Честная диагностика, понятные цены и гарантия на работы.",
    "realty": "«{n}» — поможем купить, продать или снять жильё. Проверяем документы и сопровождаем сделку до ключей.",
    "event": "Приглашаем вас разделить с нами этот день. Здесь вся информация о событии.",
    "music": "{n} — музыка, в которую вкладываем душу. Пишем песни, играем концерты и ждём вас в зале.",
    "gaming": "{n} — сообщество игроков. Турниры, совместные игры и дружная атмосфера.",
    "landing": "«{n}» экономит ваше время: всё нужное — в одном месте, без лишних шагов.",
    "personal": "Здесь фотографии, истории и всё самое интересное — {n}.",
    "business": "«{n}» — команда профессионалов. Работаем честно, по договору и с гарантией результата.",
}


def default_section(kind, type_, name):
    title = TITLES.get(kind, "Раздел")
    it = lambda *pairs: [{"title": a, "text": b} for a, b in pairs]  # noqa: E731
    if kind == "about":
        return {"kind": "about", "title": "Обо мне" if type_ == "portfolio" else "О нас",
                "text": _ABOUT.get(type_, _ABOUT["business"]).format(n=name)}
    if kind == "services":
        return {"kind": kind, "title": title, "items": it(*_SERVICES.get(type_, _DEFAULT_SERVICES))}
    if kind == "features":
        return {"kind": kind, "title": title, "items": it(("Быстро", "Результат без долгого ожидания."),
                                                          ("Надёжно", "Проверенные решения и честные условия."),
                                                          ("Удобно", "Всё понятно с первого взгляда."))}
    if kind == "prices":
        return {"kind": kind, "title": title, "items": [
            {"title": "Старт", "price": "990 ₽", "text": "Всё необходимое, чтобы начать."},
            {"title": "Стандарт", "price": "2 490 ₽", "text": "Оптимально для большинства.", "hot": True},
            {"title": "Премиум", "price": "4 990 ₽", "text": "Максимум возможностей и поддержка."}]}
    if kind == "reviews":
        return {"kind": kind, "title": title, "items": it(("Анна", "Всё понравилось, обязательно вернусь ещё!"),
                                                          ("Дмитрий", "Быстро, качественно и с вниманием к деталям."),
                                                          ("Мария", "Рекомендую друзьям — лучший выбор."))}
    if kind == "menu":
        return {"kind": kind, "title": title, "items": [
            {"title": "Капучино", "price": "190 ₽", "text": "Эспрессо с нежной молочной пеной"},
            {"title": "Сырники", "price": "320 ₽", "text": "Со сметаной и ягодным соусом"},
            {"title": "Паста карбонара", "price": "450 ₽", "text": "Сливочный соус, бекон, пармезан"},
            {"title": "Чизкейк", "price": "290 ₽", "text": "Классический нью-йоркский"}]}
    if kind == "products":
        if type_ == "realty":
            return {"kind": kind, "title": "Объекты", "items": [
                {"title": "Студия у парка", "price": "5 900 000 ₽", "text": "28 м², 5 минут до метро"},
                {"title": "Двушка с видом", "price": "9 800 000 ₽", "text": "54 м², 12 этаж, ремонт"},
                {"title": "Дом за городом", "price": "14 500 000 ₽", "text": "120 м², участок 8 соток"}]}
        return {"kind": kind, "title": title, "items": [
            {"title": "Хит продаж", "price": "1 200 ₽", "text": "Выбор большинства покупателей."},
            {"title": "Новинка", "price": "2 400 ₽", "text": "Только что в продаже."},
            {"title": "Подарочный набор", "price": "3 600 ₽", "text": "Красиво упакуем и доставим."}]}
    if kind == "projects":
        return {"kind": kind, "title": title, "items": it(("Сайт для кофейни", "Дизайн, вёрстка и запуск за неделю."),
                                                          ("Телеграм-бот", "Экономит команде 5 часов в неделю."),
                                                          ("Игра на Python", "Сделана за выходные на геймджеме."))}
    if kind == "skills":
        return {"kind": kind, "title": title, "tags": ["HTML", "CSS", "JavaScript", "Python", "PHP", "Git", "Figma"]}
    if kind == "posts":
        today = datetime.date.today()
        return {"kind": kind, "title": title, "items": [
            {"title": "С чего всё началось", "date": today.strftime("%d.%m.%Y"), "text": "Первая запись блога: рассказываю, зачем он нужен."},
            {"title": "5 полезных привычек", "date": (today - datetime.timedelta(days=7)).strftime("%d.%m.%Y"), "text": "Маленькие шаги, которые меняют многое."},
            {"title": "Мои любимые инструменты", "date": (today - datetime.timedelta(days=14)).strftime("%d.%m.%Y"), "text": "Подборка того, чем пользуюсь каждый день."}]}
    if kind == "faq":
        return {"kind": kind, "title": title, "items": it(("Как начать?", "Напишите нам — ответим в течение дня и всё расскажем."),
                                                          ("Сколько это стоит?", "Цены указаны выше, точную сумму назовём после короткого разговора."),
                                                          ("Можно ли вернуть деньги?", "Да, если что-то пошло не так, вернём деньги в течение 14 дней."))}
    if kind == "team":
        roles = {"fitness": ("Тренер", "Инструктор йоги", "Нутрициолог"), "medical": ("Главный врач", "Терапевт", "Стоматолог"),
                 "beauty": ("Стилист", "Мастер маникюра", "Косметолог")}.get(type_, ("Основатель", "Дизайн", "Разработка"))
        return {"kind": kind, "title": title, "items": it(("Алексей", roles[0]), ("Ирина", roles[1]), ("Максим", roles[2]))}
    if kind == "schedule":
        return {"kind": kind, "title": title, "items": it(("18:00", "Сбор гостей"), ("19:00", "Начало программы"), ("22:00", "Финал и фото на память"))}
    if kind == "courses":
        return {"kind": kind, "title": title, "items": it(("Основы", "8 уроков для старта с нуля."), ("Практика", "Реальные задачи и проверка домашних заданий."),
                                                          ("Проект", "Свой проект в портфолио к концу курса."))}
    if kind == "how":
        return {"kind": kind, "title": title, "items": it(("Оставьте заявку", "Это займёт минуту."), ("Обсудим детали", "Уточним задачу и сроки."),
                                                          ("Получите результат", "Точно в срок."))}
    if kind == "tracks":
        return {"kind": kind, "title": title, "items": it(("Первый трек", "3:24"), ("Ночной город", "4:02"), ("Домой", "3:47"))}
    if kind == "gallery":
        return {"kind": kind, "title": title, "count": 6}
    if kind == "form":
        return {"kind": kind, "title": title, "text": "Оставьте имя и телефон — перезвоним и ответим на все вопросы."}
    if kind == "contacts":
        return {"kind": kind, "title": title, "text": "Напишите или позвоните — ответим быстро."}
    if kind == "facts":
        return {"kind": kind, "title": title, "items": []}
    return {"kind": "text", "title": _cap(name), "text": f"Расскажите, что написать в разделе «{_cap(name)}», — например: «измени раздел {_low(name)} на: …»."}


# ------------------------------------------------------------------ новая спецификация

KNOWLEDGE = None  # функция topic -> [предложения]; её подключает Brain, чтобы сайты «про X» были с фактами


def _sentences(text):
    text = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    text = re.sub(r"^\s*\|.*$", " ", text, flags=re.M)
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    out = []
    for s in re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ0-9«\"(])", text):
        s = s.strip()
        if 25 <= len(s) <= 260 and not re.match(r"^(Я|Меня|Мне|Могу)\s", s):
            out.append(s)
    return out


def new_spec(prompt, facts=None, owner=""):
    prompt = (prompt or "").strip()[:2000]
    low = _low(prompt)
    type_ = detect_type(low)
    topic = extract_topic(prompt) if type_ in (None, "blog") else None
    if topic and facts is None and KNOWLEDGE:
        try:
            facts = KNOWLEDGE(topic)
        except Exception:  # знания — не обязательны
            facts = None
    sentences = []
    for f in facts or []:
        sentences += _sentences(f)
    info = bool(topic and sentences)
    if not type_:
        type_ = "info" if info else ("personal" if topic else "business")
    words, default_title, tagline, kinds = TYPES.get(type_, (None, "", "", []))
    name = extract_name(prompt)
    if not name and topic:
        name = _cap(topic)
    if not name:
        name = extract_subject(prompt)   # «сайт для тренера по теннису» -> «Тренер по теннису», а не «Фитнес-клуб»
    if not name and type_ == "personal":
        m = re.search(r"\bпро\s+((?:мо|наш)\w+\s+[\w\- ]{2,40}?)(?:[.,!?;]|\s+(?:в|с|со|и)\s|$)", prompt, re.I)
        if m:
            name = "Про " + m.group(1).strip()
    name = name or default_title or "Мой сайт"

    dark = _has(low, ("темн", "черн", "ночн", "dark"))
    if _has(low, ("светл", "бел", "light")) and not _has(low, ("черно-бел",)):
        dark = False
    accent = extract_color(low)
    if _has(low, ("черно-красн", "rteam")):
        dark, accent = True, "#e10600"
    spec = {
        "version": 2, "type": type_, "owner": owner, "title": name, "tagline": tagline,
        "theme": "dark" if dark else "light", "accent": accent or ("#ff2a2a" if dark else "#e10600"),
        "seed": zlib.crc32((name + prompt).encode("utf-8")), "sections": [], "contacts": {}, "prompt": prompt,
    }
    m = re.search(r"(?:слоган|девиз)\s*:?\s*[«\"]?([^»\".\n]{3,80})", prompt, re.I)
    if m:
        spec["tagline"] = m.group(1).strip()

    if info:
        spec["tagline"] = sentences[0] if len(sentences[0]) <= 140 else "Всё самое интересное — на одной странице"
        spec["sections"] = [{"kind": "about", "title": f"Что такое {_low(name)}" if len(name.split()) <= 3 else "Главное",
                             "text": " ".join(sentences[:2])}]
        if len(sentences) > 2:
            spec["sections"].append({"kind": "facts", "title": "Интересные факты",
                                     "items": [{"title": "", "text": s} for s in sentences[2:8]]})
        spec["sections"].append(default_section("gallery", type_, name))
        spec["sections"].append({"kind": "faq", "title": "Коротко о главном", "items": [
            {"title": f"Что такое {_low(name)}?", "text": sentences[0]}] + (
            [{"title": "А ещё?", "text": sentences[1]}] if len(sentences) > 1 else [])})
        extract_contacts(prompt, spec["contacts"])
        return spec

    wanted = [(section_kind(w), w) for w in extract_sections(prompt)]
    if not wanted:
        wanted = [(k, TITLES[k]) for k in kinds]
        # «с меню и отзывами», «добавь цены» прямо в описании — тоже разделы
        for kind, ws in SECTIONS.items():
            if kind not in dict(wanted) and _has(low, ws) and kind not in ("about", "text", "projects", "posts") \
                    and re.search(r"\b(?:с|со|и|раздел\w*|плюс)\s+" + ws[0], low):
                wanted.insert(len(wanted) - 1, (kind, TITLES[kind]))
    seen = set()
    for kind, label in wanted:
        if kind != "text" and kind in seen:
            continue
        seen.add(kind)
        section = default_section(kind, type_, label if kind == "text" else name)
        custom = extract_items(prompt, kind)
        if custom:
            if kind == "skills":
                section["tags"] = [i["title"] for i in custom]
            else:
                section["items"] = custom
        spec["sections"].append(section)
    if "contacts" not in seen:
        spec["sections"].append(default_section("contacts", type_, name))
    extract_contacts(prompt, spec["contacts"])
    return spec


# ------------------------------------------------------------------ правки

def _find(spec, name):
    kind = section_kind(name)
    low = _low(name).strip(" «»\"'")
    for i, s in enumerate(spec["sections"]):
        if _low(s["title"]) == low or (kind != "text" and s["kind"] == kind):
            return i
    return None


def edit_spec(spec, instruction):
    """Правка словами. Возвращает (spec, «что сделано») или (spec, None), если не понял."""
    spec = json.loads(json.dumps(spec))
    text = (instruction or "").strip()[:1000]
    low = _low(text)
    done = []

    m = re.search(r"(?:переименуй|назови|название|заголовок)(?:\s+сайта?)?\s*(?:на|в|:)?\s*[«\"]?([^»\"\n]{2,60}?)[»\"]?\s*$", text, re.I)
    if m:
        spec["title"] = m.group(1).strip()
        done.append(f"новое название: «{spec['title']}»")
    else:
        m = re.search(r"(?:слоган|подзаголовок|девиз)\s*(?:на|:)?\s*[«\"]?([^»\"\n]{2,120}?)[»\"]?\s*$", text, re.I)
        if m:
            spec["tagline"] = m.group(1).strip()
            done.append("новый слоган")

    m = re.search(r"(?:измени|поменяй|замени|напиши)\s+(?:текст\s+)?(?:в\s+)?(?:раздел[еа]?|блок[еа]?)\s*[«\"]?(.+?)[»\"]?(?:\s+на(?=[\s:])\s*:?|\s*:)\s*(.{3,})$", text, re.I | re.S)
    if m:
        i = _find(spec, m.group(1))
        if i is not None:
            sec = spec["sections"][i]
            sec["text"] = m.group(2).strip()
            sec.pop("items", None)
            sec.pop("tags", None)
            if sec["kind"] not in ("about", "contacts", "text", "form"):
                sec["kind"] = "text"
            done.append(f"обновил раздел «{sec['title']}»")
        else:
            done.append(f"не нашёл раздел «{m.group(1).strip()}»")
    else:
        m = re.search(r"(?:добавь|добавить|создай|нужен|нужна|нужны|сделай)\s+(?:ещё\s+)?(?:раздел\w*|блок\w*|секци\w*)?\s*:?\s*(.+)$", text, re.I)
        if m and re.search(r"раздел|блок|секци|отзыв|цен|галере|меню|команд|вопрос|контакт|заявк|форм|услуг|навык|проект|курс|расписан|преимуществ|товар|каталог", _low(m.group(1)) + " " + low):
            for part in re.split(r"\s*(?:,|\sи\s)\s*", m.group(1)):
                part = part.strip(" .«»\"'")
                if not part or part.startswith(("почт", "телефон", "адрес")):
                    continue
                kind = section_kind(part)
                if kind != "text" and _find(spec, part) is not None:
                    done.append(f"раздел «{part}» уже есть")
                    continue
                section = default_section(kind, spec.get("type", "business"), part if kind == "text" else spec["title"])
                custom = extract_items(text, kind)
                if custom:
                    section["items"] = custom
                # новый раздел — перед формой заявки и контактами
                at = next((j for j, s in enumerate(spec["sections"]) if s["kind"] in ("form", "contacts")), len(spec["sections"]))
                spec["sections"].insert(at, section)
                done.append(f"добавил раздел «{section['title']}»")
        else:
            m = re.search(r"(?:убери|удали|скрой)\s+(?:раздел\w*|блок\w*|секци\w*)?\s*[«\"]?(.+?)[»\"]?\s*$", text, re.I)
            if m:
                i = _find(spec, m.group(1))
                if i is not None:
                    done.append(f"убрал раздел «{spec['sections'][i]['title']}»")
                    del spec["sections"][i]
                else:
                    done.append(f"не нашёл раздел «{m.group(1).strip()}»")

    if not re.search(r"раздел|название|слоган|переименуй", low):
        if _has(low, ("темн", "черн", "ночн")):
            spec["theme"] = "dark"
            done.append("тёмная тема")
        elif _has(low, ("светл", "бел")):
            spec["theme"] = "light"
            done.append("светлая тема")
        color = extract_color(re.sub(r"(темн|черн|светл|бел)\w*", "", low))
        if color:
            spec["accent"] = color
            done.append("новый цвет")
    if _has(low, ("другой дизайн", "по-другому", "перемешай", "новые картинки", "другие картинки")):
        spec["seed"] = random.randint(1, 2 ** 31)
        done.append("новые картинки")
    before = dict(spec.get("contacts") or {})
    spec["contacts"] = extract_contacts(text, dict(before))
    if spec["contacts"] != before:
        done.append("обновил контакты")
    if not done:
        return spec, None
    return spec, ", ".join(dict.fromkeys(done))


# ------------------------------------------------------------------ картинки и сборка

def _mix(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def _lum(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


_SCENE = {"cafe": "абстракция", "travel": "горы море закат", "music": "ночь город", "gaming": "космос", "event": "закат",
          "personal": "рассвет", "fitness": "абстракция", "info": "абстракция"}


def _art(seed, w, h, accent, bg):
    rnd = random.Random(seed)
    colors = [accent, _mix(accent, "#ffffff", 0.35), _mix(accent, "#000000", 0.45), _mix(bg, accent, 0.2)]
    parts = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    for _ in range(14):
        c, op = rnd.choice(colors), rnd.randint(20, 85) / 100
        kind = rnd.randint(0, 2)
        if kind == 0:
            parts.append(f'<circle cx="{rnd.randint(0, w)}" cy="{rnd.randint(0, h)}" r="{rnd.randint(20, h // 2)}" fill="{c}" opacity="{op}"/>')
        elif kind == 1:
            x, y, s = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(40, int(h * 0.8))
            parts.append(f'<rect x="{x}" y="{y}" width="{s}" height="{int(s * .6)}" rx="8" fill="{c}" opacity="{op}" transform="rotate({rnd.randint(0, 90)} {x} {y})"/>')
        else:
            parts.append(f'<line x1="{rnd.randint(0, w)}" y1="{rnd.randint(0, h)}" x2="{rnd.randint(0, w)}" y2="{rnd.randint(0, h)}" stroke="{c}" stroke-width="{rnd.randint(2, 10)}" opacity="{op}"/>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">{"".join(parts)}</svg>'
    return _data_uri(svg)


def _data_uri(svg):
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _e(s):
    return _html.escape(str(s or ""), quote=True)


def render(spec, made_by="Rai"):
    """Готовая страница. Спецификация лежит внутри (<script id="rai-site">), чтобы сайт можно было править дальше."""
    dark = spec.get("theme") == "dark"
    bg, fg, surface = PALETTES["dark" if dark else "light"]
    accent = spec.get("accent") if re.fullmatch(r"#[0-9a-fA-F]{6}", spec.get("accent") or "") else "#e10600"
    if abs(_lum(accent) - _lum(bg)) < 0.2:  # акцент должен читаться на фоне
        accent = _mix(accent, "#ffffff" if dark else "#000000", 0.4)
    muted, line = _mix(fg, bg, 0.42), _mix(fg, bg, 0.85)
    ink = "#111111" if _lum(accent) > 0.6 else "#ffffff"
    seed = int(spec.get("seed") or 1)
    title = _e(spec.get("title"))
    theme = {"bg": "#111114" if dark else _mix(bg, accent, 0.1), "accent": accent, "accent2": _mix(accent, "#ffffff", 0.3), "fg": fg}
    scene = _SCENE.get(spec.get("type"), "абстракция")
    hero = _data_uri(creative.make_image(scene, seed=seed, theme=theme)["svg"])
    tile_bg = "#16161a" if dark else _mix(bg, accent, 0.12)

    nav, body = [], []
    for i, s in enumerate(spec.get("sections") or []):
        sid, kind, items = f"s{i + 1}", s.get("kind"), s.get("items") or []
        nav.append(f'<a href="#{sid}">{_e(s.get("title"))}</a>')
        out = [f'<section id="{sid}" class="sec sec-{_e(kind)}"><div class="wrap"><h2 class="rv">{_e(s.get("title"))}</h2>']
        if kind in ("about", "text"):
            out.append(f'<p class="lead rv">{_e(s.get("text")).replace(chr(10), "<br>")}</p>')
        elif kind == "skills":
            out.append('<div class="tags rv">' + "".join(f"<span>{_e(t)}</span>" for t in s.get("tags") or []) + "</div>")
        elif kind == "gallery":
            out.append('<div class="gallery">' + "".join(
                f'<button class="shot rv" type="button" aria-label="Открыть фото {k + 1}"><img alt="Фото {k + 1}" loading="lazy" src="{_art(seed + k + 7, 600, 420, accent, tile_bg)}"></button>'
                for k in range(int(s.get("count") or 6))) + "</div>")
        elif kind == "reviews":
            out.append('<div class="grid">' + "".join(
                f'<blockquote class="card rv"><div class="stars" aria-label="5 из 5">★★★★★</div><p>«{_e(it.get("text"))}»</p><cite>— {_e(it.get("title"))}</cite></blockquote>'
                for it in items) + "</div>")
        elif kind == "faq":
            out.append("".join(f'<details class="card rv"><summary>{_e(it.get("title"))}</summary><p>{_e(it.get("text"))}</p></details>' for it in items))
        elif kind in ("how", "schedule", "facts"):
            out.append('<ol class="steps">' + "".join(
                f'<li class="rv">' + (f'<b>{_e(it.get("title"))}</b>' if it.get("title") else "") + f'<span>{_e(it.get("text"))}</span></li>'
                for it in items) + "</ol>")
        elif kind in ("menu", "tracks"):
            out.append('<ul class="list">' + "".join(
                f'<li class="rv"><div><b>{_e(it.get("title"))}</b>' + (f'<small>{_e(it.get("text"))}</small>' if it.get("text") else "") + "</div>"
                + (f'<span class="price">{_e(it.get("price"))}</span>' if it.get("price") else "") + "</li>" for it in items) + "</ul>")
        elif kind == "team":
            out.append('<div class="grid">' + "".join(
                f'<div class="card person rv"><div class="ava">{_e((it.get("title") or "?")[:1])}</div><b>{_e(it.get("title"))}</b><small>{_e(it.get("text"))}</small></div>'
                for it in items) + "</div>")
        elif kind == "form":
            email = (spec.get("contacts") or {}).get("email") or ""
            out.append(f'<form class="lead-form card rv" data-mail="{_e(email)}" novalidate><p>{_e(s.get("text"))}</p>'
                       '<label>Имя<input name="name" autocomplete="name" required></label>'
                       '<label>Телефон или почта<input name="contact" autocomplete="tel" required></label>'
                       '<label>Сообщение<textarea name="msg" rows="3"></textarea></label>'
                       '<button class="btn" type="submit">Отправить заявку</button><p class="form-note" role="status"></p></form>')
        elif kind == "contacts":
            c = spec.get("contacts") or {}
            links = []
            if c.get("email"):
                links.append(f'<a class="btn" href="mailto:{_e(c["email"])}">{_e(c["email"])}</a>')
            if c.get("phone"):
                links.append(f'<a class="btn ghost" href="tel:{_e(re.sub(r"[^0-9+]", "", c["phone"]))}">{_e(c["phone"])}</a>')
            if c.get("telegram"):
                links.append(f'<a class="btn ghost" href="https://t.me/{_e(c["telegram"])}" rel="noopener">Telegram: @{_e(c["telegram"])}</a>')
            if c.get("address"):
                links.append(f'<p class="addr">{_e(c["address"])}</p>')
            if not c:
                links.append('<p class="addr">Добавьте контакты: напишите «добавь почту name@mail.ru и телефон +7 900 000-00-00».</p>')
            out.append(f'<p class="lead rv">{_e(s.get("text"))}</p><div class="contacts rv">{"".join(links)}</div>')
        else:  # services, features, prices, products, projects, posts, courses
            out.append('<div class="grid">')
            for k, it in enumerate(items):
                pic = (f'<img alt="" loading="lazy" src="{_art(seed + 31 * (k + 1) + i, 600, 360, accent, tile_bg)}">'
                       if kind in ("products", "projects", "posts") else "")
                icon = f'<div class="ico">{k + 1:02d}</div>' if kind in ("services", "features", "courses") else ""
                out.append(f'<article class="card rv{" hot" if it.get("hot") else ""}">{pic}{icon}'
                           + (f'<small>{_e(it.get("date"))}</small>' if it.get("date") else "")
                           + f'<h3>{_e(it.get("title"))}</h3>' + (f'<p>{_e(it.get("text"))}</p>' if it.get("text") else "")
                           + (f'<div class="price">{_e(it.get("price"))}</div>' if it.get("price") else "") + "</article>")
            out.append("</div>")
        out.append("</div></section>")
        body.append("".join(out))

    first = "#s1" if spec.get("sections") else "#top"
    cta = next((f"#s{i + 1}" for i, s in enumerate(spec.get("sections") or []) if s.get("kind") in ("form", "contacts")), first)
    cta_label = "Оставить заявку" if any(s.get("kind") == "form" for s in spec.get("sections") or []) else "Связаться"
    hdr = "rgba(12,12,14,.86)" if dark else "rgba(250,248,245,.9)"
    data = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    year = datetime.date.today().year
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{_e(spec.get("tagline"))}">
<meta name="generator" content="{_e(made_by)} Rteam">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@700;800&family=Onest:wght@400;500;700&display=swap">
<style>
:root{{--bg:{bg};--fg:{fg};--muted:{muted};--line:{line};--surface:{surface};--accent:{accent};--ink:{ink}}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 "Onest","Segoe UI",system-ui,sans-serif}}
a{{color:var(--accent)}}img{{max-width:100%;display:block}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 20px}}
header{{position:sticky;top:0;z-index:10;background:{hdr};backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}}
header .wrap{{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:64px}}
.logo{{font:800 20px/1 "Unbounded","Arial Black",sans-serif;color:var(--fg);text-decoration:none}}.logo span{{color:var(--accent)}}
nav{{display:flex;gap:18px;flex-wrap:wrap}}nav a{{color:var(--fg);text-decoration:none;font-weight:500;font-size:15px}}nav a:hover{{color:var(--accent)}}
#menu{{display:none;background:none;border:1px solid var(--line);color:var(--fg);border-radius:10px;padding:8px 12px;font:inherit}}
.hero{{position:relative;overflow:hidden;border-bottom:1px solid var(--line)}}
.hero>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.6;animation:drift 18s ease-out both}}
.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,var(--bg) 20%,transparent 80%)}}
.hero .wrap{{position:relative;z-index:1;padding:110px 20px 100px}}
.hero h1{{font:800 clamp(36px,7vw,76px)/1.02 "Unbounded","Arial Black",sans-serif;margin:0 0 18px;letter-spacing:-.02em;max-width:14ch;text-wrap:balance}}
.hero p{{font-size:clamp(18px,2.4vw,22px);margin:0 0 30px;max-width:44ch}}
.btn{{display:inline-block;background:var(--accent);color:var(--ink);padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:700;border:0;font:inherit;font-weight:700;cursor:pointer}}
.btn:hover{{filter:brightness(1.08)}}.btn.ghost{{background:transparent;color:var(--fg);border:1px solid var(--line)}}
.sec{{padding:84px 0;border-bottom:1px solid var(--line)}}
.sec h2{{font:800 clamp(28px,4vw,40px)/1.1 "Unbounded","Arial Black",sans-serif;margin:0 0 30px;letter-spacing:-.01em}}
.lead{{font-size:20px;max-width:62ch;margin:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:22px;margin:0;display:flex;flex-direction:column;gap:8px;transition:transform .2s,border-color .2s}}
.card:hover{{transform:translateY(-3px);border-color:var(--accent)}}.card.hot{{border:2px solid var(--accent)}}
.card img{{border-radius:10px;margin:-6px -6px 6px;width:calc(100% + 12px);max-width:none;aspect-ratio:5/3;object-fit:cover}}
.card h3{{margin:0;font-size:20px}}.card p{{margin:0;color:var(--muted)}}.card small{{color:var(--muted)}}
.ico{{font:800 15px/1 "Unbounded",sans-serif;color:var(--ink);background:var(--accent);width:44px;height:44px;border-radius:12px;display:grid;place-items:center}}
.price{{font:800 22px/1 "Unbounded","Arial Black",sans-serif;color:var(--accent);margin-top:auto;white-space:nowrap}}
.stars{{color:var(--accent);letter-spacing:2px}}blockquote.card p{{color:var(--fg);font-size:18px}}cite{{color:var(--muted);font-style:normal}}
details.card{{margin-bottom:12px}}summary{{cursor:pointer;font-weight:700;font-size:18px}}
.tags{{display:flex;flex-wrap:wrap;gap:10px}}.tags span{{border:1px solid var(--accent);border-radius:999px;padding:8px 16px;font-weight:500}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}}
.shot{{padding:0;border:0;background:none;cursor:zoom-in;border-radius:12px;overflow:hidden}}.shot img{{aspect-ratio:10/7;object-fit:cover;width:100%;transition:transform .3s}}.shot:hover img{{transform:scale(1.05)}}
.steps{{list-style:none;counter-reset:s;padding:0;margin:0;display:grid;gap:14px}}
.steps li{{counter-increment:s;display:flex;gap:18px;align-items:baseline;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 22px}}
.steps li::before{{content:counter(s,decimal-leading-zero);font:800 22px/1 "Unbounded",sans-serif;color:var(--accent)}}.steps b{{min-width:120px}}
.list{{list-style:none;padding:0;margin:0;max-width:720px}}.list li{{display:flex;justify-content:space-between;gap:20px;padding:16px 0;border-bottom:1px dashed var(--line)}}.list small{{display:block;color:var(--muted)}}
.person{{align-items:center;text-align:center}}.ava{{width:72px;height:72px;border-radius:50%;background:var(--accent);color:var(--ink);display:grid;place-items:center;font:800 28px/1 "Unbounded",sans-serif}}
.lead-form{{max-width:560px}}.lead-form label{{display:flex;flex-direction:column;gap:4px;font-size:14px;color:var(--muted)}}
.lead-form input,.lead-form textarea{{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:11px 12px}}
.lead-form input:focus,.lead-form textarea:focus{{outline:none;border-color:var(--accent)}}.lead-form .bad{{border-color:#e5484d}}.form-note{{min-height:1.2em;color:var(--accent)}}
.contacts{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-top:24px}}.addr{{width:100%;color:var(--muted);margin:6px 0 0}}
footer{{padding:36px 0;color:var(--muted);font-size:14px}}footer .wrap{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.lightbox{{position:fixed;inset:0;background:rgba(0,0,0,.85);display:grid;place-items:center;z-index:50;padding:20px;cursor:zoom-out}}.lightbox img{{max-height:90vh;border-radius:12px}}
.up{{position:fixed;right:18px;bottom:18px;width:46px;height:46px;border-radius:50%;border:0;background:var(--accent);color:var(--ink);font-size:20px;cursor:pointer;opacity:0;pointer-events:none;transition:opacity .2s}}.up.on{{opacity:1;pointer-events:auto}}
.rv{{opacity:0;transform:translateY(18px);transition:opacity .6s,transform .6s}}.rv.in{{opacity:1;transform:none}}
@keyframes drift{{from{{transform:scale(1.12)}}to{{transform:scale(1)}}}}
@media (max-width:760px){{#menu{{display:block}}nav{{display:none;position:absolute;left:0;right:0;top:64px;background:var(--bg);flex-direction:column;padding:16px 20px;border-bottom:1px solid var(--line)}}
nav.open{{display:flex}}.steps li{{flex-direction:column;gap:6px}}.sec{{padding:60px 0}}.hero .wrap{{padding:80px 20px 70px}}}}
@media (prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}.rv{{opacity:1;transform:none;transition:none}}.hero>img{{animation:none}}}}
</style>
</head>
<body>
<header><div class="wrap"><a class="logo" href="#top">{title}<span>.</span></a>
<button id="menu" type="button" aria-label="Меню" aria-expanded="false">Меню</button><nav id="nav">{"".join(nav)}</nav></div></header>
<main id="top">
<section class="hero"><img alt="" src="{hero}"><div class="wrap"><h1>{title}</h1><p>{_e(spec.get("tagline"))}</p>
<a class="btn" href="{cta}">{cta_label}</a> <a class="btn ghost" href="{first}">Подробнее</a></div></section>
{"".join(body)}
</main>
<footer><div class="wrap"><span>© {year} {title}</span><span>Сайт создан ИИ {_e(made_by)} · Rteam</span></div></footer>
<button class="up" type="button" aria-label="Наверх">↑</button>
<script type="application/json" id="rai-site">{data}</script>
<script>
(function(){{
var nav=document.getElementById("nav"),menu=document.getElementById("menu");
menu.onclick=function(){{var o=nav.classList.toggle("open");menu.setAttribute("aria-expanded",o)}};
nav.querySelectorAll("a").forEach(function(a){{a.onclick=function(){{nav.classList.remove("open")}}}});
var items=document.querySelectorAll(".rv");
if("IntersectionObserver" in window){{var io=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add("in");io.unobserve(e.target)}}}})}},{{threshold:.12}});items.forEach(function(el){{io.observe(el)}})}}
else items.forEach(function(el){{el.classList.add("in")}});
var up=document.querySelector(".up");addEventListener("scroll",function(){{up.classList.toggle("on",scrollY>600)}});up.onclick=function(){{scrollTo({{top:0}})}};
document.querySelectorAll(".shot").forEach(function(b){{b.onclick=function(){{var d=document.createElement("div");d.className="lightbox";d.innerHTML='<img alt="">';d.firstChild.src=b.querySelector("img").src;d.onclick=function(){{d.remove()}};document.body.append(d)}}}});
document.querySelectorAll(".lead-form").forEach(function(f){{f.onsubmit=function(e){{e.preventDefault();var ok=true;
f.querySelectorAll("[required]").forEach(function(i){{var bad=!i.value.trim();i.classList.toggle("bad",bad);if(bad)ok=false}});
var note=f.querySelector(".form-note");if(!ok){{note.textContent="Заполните имя и контакт.";return}}
var mail=f.dataset.mail,body="Имя: "+f.name.value+"\\nКонтакт: "+f.contact.value+"\\n\\n"+f.msg.value;
if(mail){{location.href="mailto:"+mail+"?subject="+encodeURIComponent("Заявка с сайта")+"&body="+encodeURIComponent(body);note.textContent="Открываем почту — отправьте письмо."}}
else note.textContent="Заявка заполнена. Чтобы заявки приходили, добавьте на сайт почту.";}}}});
}})();
</script>
</body>
</html>
"""


def spec_from_html(html):
    """Достать спецификацию из страницы, собранной этим конструктором (или AI Studio v2)."""
    m = re.search(r'<script type="application/json" id="rai-site">(.*?)</script>', html or "", re.S)
    if not m:
        return None
    try:
        spec = json.loads(m.group(1))
    except ValueError:
        return None
    return spec if isinstance(spec, dict) and isinstance(spec.get("sections"), list) else None


def summary(spec):
    names = ", ".join(s["title"] for s in spec["sections"])
    theme = "тёмная" if spec.get("theme") == "dark" else "светлая"
    return f"**Сайт «{spec['title']}»** — разделы: {names}. Тема {theme}, цвет {spec.get('accent')}."


EDIT_HELP = ("Правьте словами: «добавь раздел цены», «убери отзывы», «сделай тёмным», «цвет синий», "
             "«переименуй в «Кофе & Ко»», «измени раздел о нас на: …», «добавь почту name@mail.ru».")
