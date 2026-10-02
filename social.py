"""Анализ по ссылке: TikTok, YouTube, Telegram, Instagram, VK, X и любые сайты.

Данные страницы достаёт посредник на хостинге (net.php?social=ссылка → social.php): соцсети не пускают браузер
к своим страницам напрямую. Здесь — разбор цифр: вовлечённость (ER), охват, частота постов, SEO сайта и советы.
Ориентиры по ER — средние по рынку, а не правило: у каждой ниши свои.
"""

import re
from datetime import datetime, timedelta, timezone

import net

SOCIAL_HOSTS = re.compile(r"(?:^|\.)(tiktok\.com|youtube\.com|youtu\.be|t\.me|telegram\.me|instagram\.com|vk\.com|vk\.ru|"
                          r"vkvideo\.ru|x\.com|twitter\.com)$", re.I)
URL_RE = re.compile(r"(?:https?://[^\s<>\"«»]+|(?<![\w@./])(?:(?:www|vm|vt|m)\.)?(?:tiktok\.com|youtube\.com|youtu\.be|t\.me|"
                    r"instagram\.com|vk\.com|x\.com|twitter\.com)/[^\s<>\"«»]+)", re.I)
ANALYZE_RE = re.compile(r"(анализ|проанализ|разбер|разбор|оцени|статистик|аудит|посмотри|что скажешь|проверь|изучи|"
                        r"сколько\s+(просмотр|подписчик|лайк)|охват|вовлеч|\ber\b|продвиж|раскрут|почему.*(не|мало)|как.*(набрать|увелич))",
                        re.I)
PLATFORM = {"tiktok": "TikTok", "youtube": "YouTube", "telegram": "Telegram", "instagram": "Instagram", "vk": "VK", "x": "X (Twitter)",
            "web": "Сайт"}
KIND = {"video": "видео", "short": "Shorts", "profile": "аккаунт", "channel": "канал", "post": "пост", "page": "страница"}
MSK = timezone(timedelta(hours=3))
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def find_link(text: str):
    m = URL_RE.search(text or "")
    if not m:
        return None
    url = m.group(0).rstrip(").,;!?»")
    return url if url.lower().startswith("http") else "https://" + url


def _host(url):
    m = re.match(r"https?://([^/?#]+)", url or "", re.I)
    return (m.group(1) if m else "").lower()


def is_link_request(text: str) -> bool:
    """Ссылка на соцсеть — всегда анализ; ссылка на сайт — если просят разобрать или прислали только ссылку."""
    url = find_link(text)
    if not url:
        return False
    if SOCIAL_HOSTS.search(_host(url)):
        return True
    rest = (text or "").replace(url, "").replace(url.replace("https://", ""), "").strip(" \n\t.,:;!?")
    return not rest or bool(ANALYZE_RE.search(text))


def fetch(url: str) -> dict:
    """Данные по ссылке от посредника на хостинге (net.php?social=…)."""
    return net.social(url)


# ------------------------------------------------------------------ числа и даты

def num(n):
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", " ")


def short(n):
    if n is None:
        return "—"
    n = float(n)
    for size, word in ((1e9, "млрд"), (1e6, "млн"), (1e3, "тыс.")):
        if n >= size:
            return f"{n / size:.1f}".replace(".", ",").replace(",0", "") + " " + word
    return num(n)


def pct(a, b, digits=1):
    if not a or not b:
        return None
    return round(a / b * 100, digits)


def fmt_pct(p):
    return "—" if p is None else f"{p:.{1 if p < 10 else 0}f} %".replace(".", ",")


def parse_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    s = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            d = datetime.strptime(s.replace("Z", "+00:00"), fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def human_date(d, now=None):
    if not d:
        return "—"
    local = d.astimezone(MSK)
    now = now or datetime.now(timezone.utc)
    days = (now - d).days
    ago = "сегодня" if days <= 0 else "вчера" if days == 1 else f"{days} дн. назад"
    time = f", {local:%H:%M} МСК" if (d.hour or d.minute) else ""
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}{time} · {ago}"


def duration(sec):
    if not sec:
        return "—"
    sec = int(sec)
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def grade(value, levels):
    """levels: [(порог, оценка)] по убыванию."""
    if value is None:
        return ""
    for threshold, word in levels:
        if value >= threshold:
            return word
    return levels[-1][1] if levels else ""


ER_TIKTOK = [(8, "отлично"), (4, "хорошо"), (2, "средне"), (0, "низко")]
ER_INSTA = [(3, "отлично"), (1.5, "хорошо"), (0.7, "средне"), (0, "низко")]
LIKES_YT = [(5, "отлично"), (3, "хорошо"), (1.5, "средне"), (0, "низко")]
ERR_TG = [(40, "отлично"), (20, "хорошо"), (10, "средне"), (0, "низко")]


def _table(rows):
    rows = [(k, v) for k, v in rows if v not in (None, "", "—")]
    if not rows:
        return ""
    return "| Показатель | Значение |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)


def _clip(text, n=280):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def _md(text):
    """Текст со страницы без символов разметки (не ломает таблицы, ссылки и жирный шрифт)."""
    return re.sub(r"[*`=~]", "", str(text or "")).replace("|", "/").replace("[", "(").replace("]", ")")


# ------------------------------------------------------------------ отчёт

def report(data: dict, now=None):
    """Данные по ссылке → (отчёт в Markdown, вложения)."""
    now = now or datetime.now(timezone.utc)
    platform, kind = data.get("platform", "web"), data.get("kind", "page")
    a, st = data.get("author") or {}, data.get("stats") or {}
    who = ("@" + a["handle"]) if a.get("handle") and platform in ("tiktok", "instagram", "telegram") else (a.get("name") or "")
    out = [f"## {PLATFORM.get(platform, platform)}: {KIND.get(kind, kind)}" + (" " + _md(who) if who else "")]
    good, todo = [], []
    if data.get("title") and (platform in ("youtube", "web") or kind not in ("video", "post")):
        out.append(f"**{_md(_clip(data['title'], 160))}**")
    if data.get("text") and kind in ("video", "short", "post"):
        out.append("> " + _md(_clip(data["text"], 400)).replace("\n", " "))
    if platform == "web":
        out += _web(data, good, todo)
    elif platform == "telegram" and kind in ("channel", "post"):
        out += _telegram(data, now, good, todo)
    elif kind in ("video", "short", "post"):
        out += _content(data, now, good, todo)
    else:
        out += _profile(data, good, todo)
    tags = data.get("hashtags") or []
    if tags:
        out.append("**Хэштеги:** " + " ".join("#" + _md(t) for t in tags[:20]))
    if data.get("music"):
        out.append("**Музыка:** " + _md(data["music"]))
    if good:
        out.append("### Что хорошо\n" + "\n".join("- " + g for g in good))
    if todo:
        out.append("### Что улучшить\n" + "\n".join("- " + t for t in todo))
    for w in data.get("warnings") or []:
        out.append(f"*⚠ {w}.*")
    out.append(f"Источник: [{PLATFORM.get(platform, 'страница')}]({data.get('url')}) · данные на момент запроса." +
               ("" if platform == "web" else " Ориентиры вовлечённости — средние по рынку; у каждой ниши свои."))
    attachments = []
    thumb = data.get("thumbnail")
    if isinstance(thumb, str) and thumb.startswith("https://"):
        attachments.append({"type": "photo", "url": thumb, "title": _clip(data.get("title") or who or "Превью", 80), "source": data.get("url", "")})
    return "\n\n".join(x for x in out if x), attachments


def _content(data, now, good, todo):
    platform = data["platform"]
    st, a = data.get("stats") or {}, data.get("author") or {}
    views, likes, comments = st.get("views"), st.get("likes"), st.get("comments")
    shares, saves = st.get("shares"), st.get("saves")
    published = parse_date(data.get("published"))
    days = max(1, (now - published).days) if published else None
    actions = sum(x or 0 for x in (likes, comments, shares, saves))
    if platform == "instagram":
        er = pct(actions, a.get("followers")) if a.get("followers") else None
        scale = ER_INSTA
    else:
        er = pct(actions, views)
        scale = ER_TIKTOK
    like_rate = pct(likes, views)
    rows = [("Просмотры", num(views)),
            ("Лайки", num(likes) + (f" ({fmt_pct(like_rate)} от просмотров)" if like_rate else "") if likes is not None else None),
            ("Комментарии", num(comments) if comments is not None else None),
            ("Репосты", num(shares) if shares is not None else None),
            ("Сохранения", num(saves) if saves is not None else None)]
    if platform == "youtube":
        rows.append(("Лайки от просмотров", f"**{fmt_pct(like_rate)}** — {grade(like_rate, LIKES_YT)}" if like_rate else None))
    elif er:
        rows.append(("Вовлечённость (ER)", f"**{fmt_pct(er)}** — {grade(er, scale)}"))
    rows += [("Длительность", duration(data.get("duration")) if data.get("duration") else None),
             ("Опубликовано", human_date(published, now) if published else (data.get("published") or None)),
             ("Просмотров в день", num(views // days) if views and days else None)]
    if platform == "youtube" and data.get("category"):
        rows.append(("Категория", _md(data["category"])))
    out = [_table(rows)]
    author_rows = [("Автор", _md(a.get("name") or a.get("handle") or "")),
                   ("Подписчики", num(a.get("followers")) if a.get("followers") is not None else None),
                   ("Видео в аккаунте", num(a.get("videos")) if a.get("videos") is not None else None),
                   ("Лайков на аккаунте", num(a.get("likes")) if a.get("likes") is not None else None)]
    if views and a.get("followers"):
        reach = views / a["followers"]
        author_rows.append(("Просмотры / подписчики", f"{reach:.1f}×".replace(".", ",")))
        if reach >= 3:
            good.append(f"Видео вышло далеко за подписчиков ({reach:.1f}× от их числа) — попало в рекомендации".replace(".", ",", 1))
        elif reach < 0.1:
            todo.append("Видео увидели меньше 10 % подписчиков — первые 1–2 секунды и обложка не цепляют, начните с самого интересного")
    if any(v for k, v in author_rows[1:]):
        out.append("### Автор\n" + _table(author_rows))
    # оценки и советы
    if er is not None and platform != "youtube":
        if er >= scale[1][0]:
            good.append(f"Высокая вовлечённость: {fmt_pct(er)} — зрители активно реагируют")
        elif er < scale[2][0]:
            todo.append(f"Вовлечённость низкая ({fmt_pct(er)}): дайте зрителю повод отреагировать — вопрос, спор, «сохрани, пригодится»")
    if like_rate is not None and platform == "youtube":
        (good if like_rate >= 3 else todo).append(
            f"Лайков {fmt_pct(like_rate)} от просмотров" + (" — выше среднего" if like_rate >= 3 else " — попросите лайк в начале и в конце ролика"))
    if comments is not None and likes:
        c_rate = comments / likes * 100
        if c_rate < 1:
            todo.append("Комментариев мало относительно лайков — закончите видео вопросом к зрителям и отвечайте на первые комментарии")
        elif c_rate > 5:
            good.append("Много комментариев — тема вызывает обсуждение")
    if shares and views and shares / views > 0.005:
        good.append("Видео часто пересылают — им хочется поделиться")
    if saves and views and saves / views > 0.005:
        good.append("Видео часто сохраняют — оно полезное, такой формат стоит повторять")
    text = data.get("text") or ""
    tags = data.get("hashtags") or []
    if platform in ("tiktok", "instagram"):
        if not tags:
            todo.append("Нет хэштегов — добавьте 3–5 точных по теме (не только #fyp / #рекомендации)")
        elif len(tags) > 10:
            todo.append(f"Хэштегов слишком много ({len(tags)}) — оставьте 3–5 самых точных")
        else:
            good.append(f"Хэштегов в норме ({len(tags)})")
        if not text.strip():
            todo.append("Нет подписи — короткая подпись с вопросом помогает алгоритму и комментариям")
        elif "?" not in text:
            todo.append("В подписи нет вопроса к зрителю — вопрос поднимает комментарии")
    dur = data.get("duration")
    if dur and platform == "tiktok":
        if dur > 180:
            todo.append("Длинное видео (больше 3 минут) — досматривают реже; держите крючок в первые 2 секунды")
        elif dur < 7:
            todo.append("Очень короткое видео — хорошо для досмотров, но мало времени на смысл")
    if platform == "youtube":
        title = data.get("title") or ""
        if len(title) > 70:
            todo.append(f"Название длинное ({len(title)} знаков) — в поиске видно ~60–70, главное слово ставьте в начало")
        if len(text) < 200:
            todo.append("Короткое описание — добавьте 2–3 предложения с ключевыми словами и тайм-коды")
        if not data.get("keywords"):
            todo.append("Не указаны теги видео")
    if published:
        local = published.astimezone(MSK)
        out.append(f"**Время публикации:** {WEEKDAYS[local.weekday()]}, {local:%H:%M} по Москве.")
    return out


def _profile(data, good, todo):
    platform = data["platform"]
    a = data.get("author") or {}
    followers, videos, likes = a.get("followers"), a.get("videos"), a.get("likes")
    rows = [("Имя", _md(a.get("name") or "")), ("Ник", ("@" + a["handle"]) if a.get("handle") else None),
            ("Подписчики", num(followers) if followers is not None else None),
            ("Подписки", num(a.get("following")) if a.get("following") is not None else None),
            ("Публикаций" if platform == "instagram" else "Видео", num(videos) if videos is not None else None),
            ("Лайков всего", num(likes) if likes is not None else None),
            ("Подтверждённый", "да ✔" if a.get("verified") else None)]
    if likes and videos:
        per_video = likes / videos
        rows.append(("Лайков на видео в среднем", num(int(per_video))))
        if followers:
            ratio = per_video / followers * 100
            rows.append(("Средние лайки / подписчики", fmt_pct(ratio)))
            if ratio >= 10:
                good.append(f"Видео в среднем набирают лайков на {fmt_pct(ratio)} от числа подписчиков — аудитория живая")
            elif ratio < 2:
                todo.append("Лайков на видео мало относительно подписчиков — часть аудитории «спит»: обновите формат, "
                            "посмотрите, какие ролики зашли лучше всего, и делайте похожие")
    out = [_table(rows)]
    bio = (a.get("bio") or data.get("text") or "").strip()
    if bio:
        out.append("**Описание профиля:** " + _md(_clip(bio, 300)))
        if not re.search(r"https?://|www\.|\.ru|\.com|@|t\.me", bio):
            good.append("Есть описание профиля")
            todo.append("В описании нет контакта или ссылки — добавьте, куда писать или переходить")
        else:
            good.append("В описании есть контакт или ссылка")
    else:
        todo.append("Пустое описание профиля — в 1–2 строках скажите, о чём аккаунт и зачем подписываться")
    if videos is not None and videos < 10:
        todo.append("Мало публикаций — алгоритму нужно больше роликов, чтобы понять аудиторию (ориентир: 3–5 в неделю)")
    if followers is not None and a.get("following") and a["following"] > followers:
        todo.append("Подписок больше, чем подписчиков — так аккаунт выглядит менее авторитетно")
    return out


def _telegram(data, now, good, todo):
    a = data.get("author") or {}
    subs = a.get("followers")
    posts = [p for p in data.get("posts") or [] if p.get("views") is not None]
    rows = [("Канал", _md(data.get("title") or a.get("handle") or "")), ("Подписчики", num(subs) if subs is not None else None)]
    out = []
    if data.get("kind") == "post" and (data.get("stats") or {}).get("views") is not None:
        v = data["stats"]["views"]
        rows.append(("Просмотры поста", num(v)))
        if subs:
            rows.append(("Охват поста", f"{fmt_pct(pct(v, subs))} подписчиков"))
    if posts:
        views = [p["views"] for p in posts]
        avg = sum(views) // len(views)
        rows.append(("Средние просмотры поста", num(avg) + f" (по последним {len(posts)})"))
        err = pct(avg, subs) if subs else None
        if err is not None:
            rows.append(("Охват (ERR)", f"**{fmt_pct(err)}** — {grade(err, ERR_TG)}"))
            if err >= 20:
                good.append(f"Хороший охват: пост в среднем видят {fmt_pct(err)} подписчиков")
            elif err < 10:
                todo.append(f"Охват низкий ({fmt_pct(err)}): много неактивных подписчиков — меньше рекламы подряд, "
                            "больше полезных постов, проверьте источники подписчиков")
        dates = sorted(d for d in (parse_date(p.get("date")) for p in posts) if d)
        if len(dates) >= 2:
            span = max(1, (dates[-1] - dates[0]).days)
            per_day = len(dates) / span
            rows.append(("Частота постов", f"{per_day:.1f} в день".replace(".", ",") if per_day >= 1 else f"{per_day * 7:.1f} в неделю".replace(".", ",")))
            silent = (now - dates[-1]).days
            if silent >= 7:
                todo.append(f"Последний пост — {silent} дн. назад: регулярность важна, ориентир — от 3–4 постов в неделю")
            if per_day > 6:
                todo.append("Очень много постов в день — подписчики устают и отписываются; 1–3 сильных поста лучше")
        media = sum(1 for p in posts if p.get("media"))
        rows.append(("Посты с фото и видео", f"{media} из {len(posts)}"))
        if media < len(posts) / 3:
            todo.append("Мало постов с фото и видео — визуал заметно повышает просмотры")
        reactions = [p.get("reactions") or 0 for p in posts]
        if any(reactions) and avg:
            rows.append(("Реакции на пост", f"{sum(reactions) // len(reactions)} в среднем"))
        best = max(posts, key=lambda p: p["views"])
        out.append(_table(rows))
        out.append(f"**Самый просматриваемый из последних:** [{num(best['views'])} просмотров]({best['url']}) — "
                   + _md(_clip(best.get("text") or best.get("media") or "без текста", 160)))
        top = sorted(posts, key=lambda p: -p["views"])[:5]
        out.append("### Последние посты по просмотрам\n| Пост | Просмотры | Дата |\n|---|---|---|\n" + "\n".join(
            f"| [{_md(_clip(p.get('text') or p.get('media') or 'пост', 60))}]({p['url']}) | {num(p['views'])} | "
            f"{human_date(parse_date(p.get('date')), now).split(' · ')[0] if p.get('date') else '—'} |" for p in top))
        lengths = [len(p.get("text") or "") for p in posts if p.get("text")]
        if lengths and sum(lengths) / len(lengths) > 1500:
            todo.append("Посты очень длинные — разбивайте на абзацы и выносите главное в первую строку")
    else:
        out.append(_table(rows))
    if data.get("text"):
        out.append("**Описание:** " + _md(_clip(data["text"], 300)))
    else:
        todo.append("Нет описания канала — напишите, о чём канал и как часто выходят посты")
    return out


def _web(data, good, todo):
    seo = data.get("seo") or {}
    rows = [("Заголовок (title)", f"{_md(_clip(data.get('title') or '—', 90))} ({seo.get('title_len', 0)} зн.)"),
            ("Описание (description)", f"{seo.get('description_len', 0)} зн." if seo.get("description_len") else "нет"),
            ("Заголовки H1", "; ".join(_md(_clip(h, 60)) for h in seo.get("h1") or []) or "нет"),
            ("Подзаголовков H2", seo.get("h2")), ("Слов на странице", num(seo.get("words"))),
            ("Картинок", f"{seo.get('images', 0)} (без alt: {seo.get('images_no_alt', 0)})"),
            ("Ссылок", f"{seo.get('links', 0)} (внешних: {seo.get('external_links', 0)})"), ("Язык", seo.get("lang") or "не указан")]
    checks = [(seo.get("https"), "Сайт работает по HTTPS", "Нет HTTPS — браузеры помечают сайт как небезопасный"),
              (30 <= seo.get("title_len", 0) <= 65, "Длина заголовка в норме (30–65 знаков)",
               f"Заголовок {seo.get('title_len', 0)} знаков — лучше 30–65, с главным словом в начале"),
              (70 <= seo.get("description_len", 0) <= 170, "Описание для поисковиков в норме",
               "Описание (meta description) отсутствует или неудачной длины — нужно 70–160 знаков"),
              (len(seo.get("h1") or []) == 1, "Один заголовок H1", "На странице должен быть ровно один H1"),
              (seo.get("viewport"), "Есть настройка для телефонов (viewport)", "Нет meta viewport — на телефоне страница будет мелкой"),
              (seo.get("og"), "Есть превью для соцсетей (Open Graph)", "Нет Open Graph — ссылка в соцсетях будет без картинки и описания"),
              (seo.get("canonical"), "Указан canonical", "Нет canonical — возможны дубли страниц в поиске"),
              (not seo.get("images_no_alt"), "У картинок есть alt", f"Картинок без alt: {seo.get('images_no_alt', 0)} — их не видят поисковики и экранные чтецы"),
              ((seo.get("words") or 0) >= 300, "Достаточно текста", "Мало текста (меньше 300 слов) — поисковикам нечего ранжировать"),
              (seo.get("lang"), "Указан язык страницы", "Не указан язык страницы (<html lang>)")]
    for ok, yes, no in checks:
        (good if ok else todo).append(yes if ok else no)
    out = [_table(rows)]
    if data.get("text"):
        out.append("**Описание:** " + _md(_clip(data["text"], 300)))
    if data.get("summary"):
        out.append("**О чём страница:** " + _md(_clip(data["summary"], 500)))
    return out
