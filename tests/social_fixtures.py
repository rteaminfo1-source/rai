"""Образцы страниц соцсетей для проверки разбора ссылок (структура как у настоящих страниц, данные выдуманы)."""
import json

TIKTOK_VIDEO = {"__DEFAULT_SCOPE__": {"webapp.video-detail": {"statusCode": 0, "itemInfo": {"itemStruct": {
    "id": "7400000000000000001", "desc": "Как сделать сайт за 5 минут 🔥 А вы бы попробовали? #сайт #нейросеть #rai",
    "createTime": 1790609400,
    "video": {"duration": 34, "cover": "https://p16-sign.tiktokcdn.com/cover.jpeg"},
    "author": {"uniqueId": "rai.team", "nickname": "Rai Team", "verified": False, "signature": "Делаем ИИ · rai.rteam.info"},
    "music": {"title": "оригинальный звук", "authorName": "Rai Team"},
    "stats": {"diggCount": 61000, "shareCount": 3200, "commentCount": 1450, "playCount": 1250000, "collectCount": 8800},
    "statsV2": {"playCount": "1250000", "diggCount": "61000"},
    "authorStats": {"followerCount": 120000, "followingCount": 40, "heartCount": 2400000, "videoCount": 85},
    "textExtra": [{"hashtagName": "сайт"}, {"hashtagName": "нейросеть"}, {"hashtagName": "rai"}],
}}}}}
TIKTOK_PROFILE = {"__DEFAULT_SCOPE__": {"webapp.user-detail": {"statusCode": 0, "userInfo": {
    "user": {"uniqueId": "rai.studio", "nickname": "Rai Studio", "signature": "", "verified": True,
             "avatarLarger": "https://p16-sign.tiktokcdn.com/avatar.jpeg"},
    "stats": {"followerCount": 50000, "followingCount": 120, "heartCount": 400000, "videoCount": 200}}}}}


def tiktok_page(data):
    return ("<!DOCTYPE html><html><head><title>TikTok</title></head><body><div id=app></div>"
            '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">' + json.dumps(data, ensure_ascii=False) +
            "</script></body></html>")


YT_PLAYER = {"videoDetails": {"videoId": "dQw4w9WgXcQ", "title": "Как работает нейросеть в браузере — полный разбор {без серверов}",
                              "lengthSeconds": "754", "keywords": ["нейросеть", "webgpu"], "channelId": "UC123",
                              "shortDescription": "Разбираем, как запустить нейросеть прямо в браузере.", "viewCount": "48210",
                              "author": "Rai Team", "thumbnail": {"thumbnails": [{"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}]}},
             "microformat": {"playerMicroformatRenderer": {"publishDate": "2026-09-01T10:00:00-07:00", "category": "Education",
                                                           "ownerProfileUrl": "http://www.youtube.com/@raiteam"}}}
YT_WATCH = ("<html><head><title>Видео</title><meta property=\"og:title\" content=\"Нейросеть\"></head><body><script>"
            "var ytInitialPlayerResponse = " + json.dumps(YT_PLAYER, ensure_ascii=False) + ";var meta = 1;</script>"
            '<script>var ytInitialData = {"x":{"likeCount":"2950"}};</script></body></html>')
YT_CHANNEL = ("<html><head><meta property=\"og:title\" content=\"Rai Team\"></head><body><script>var ytInitialData = " + json.dumps({
    "metadata": {"channelMetadataRenderer": {"title": "Rai Team", "description": "Канал про ИИ и сайты. Пишите: hi@rteam.info",
                                             "vanityChannelUrl": "http://www.youtube.com/@raiteam", "externalId": "UC123",
                                             "keywords": "ИИ нейросети сайты", "avatar": {"thumbnails": [{"url": "https://yt3.ggpht.com/a.jpg"}]}}},
    "header": {"content": "1,23 млн подписчиков"}}, ensure_ascii=False).replace('"content": "1,23', '"content":"1,23') + ";</script></body></html>")


def _post(n, views, text, date, media=""):
    extra = '<a class="tgme_widget_message_photo_wrap" href="#"></a>' if media == "photo" else ""
    return (f'<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message js-widget_message" data-post="raichannel/{n}">'
            f'{extra}<div class="tgme_widget_message_text js-message_text" dir="auto">{text}</div>'
            f'<div class="tgme_widget_message_footer"><span class="tgme_widget_message_views">{views}</span>'
            f'<time datetime="{date}" class="time">12:00</time></div></div></div>')


TELEGRAM = ('<html><head><meta property="og:title" content="Rai Channel"><meta property="og:image" content="https://cdn4.telesco.pe/file/x.jpg"></head><body>'
            '<div class="tgme_channel_info"><div class="tgme_channel_info_header_title"><span dir="auto">Rai Channel</span></div>'
            '<div class="tgme_channel_info_counters"><div class="tgme_channel_info_counter"><span class="counter_value">12.5K</span> '
            '<span class="counter_type">subscribers</span></div><div class="tgme_channel_info_counter"><span class="counter_value">340</span> '
            '<span class="counter_type">photos</span></div></div>'
            '<div class="tgme_channel_info_description">Новости Rai и нейросетей.<br>Каждый день.</div></div>'
            + _post(101, "3.1K", "Вышла новая версия Rai Нейро #новости", "2026-09-28T09:00:00+00:00", "photo")
            + _post(102, "2.4K", "Как читать страницы <b>нейросетью</b>", "2026-09-29T09:00:00+00:00")
            + _post(103, "5.6K", "Своя нейросеть на своём сайте — инструкция", "2026-09-30T09:00:00+00:00", "photo")
            + _post(104, "2.9K", "Опрос: что добавить дальше?", "2026-10-01T09:00:00+00:00")
            + "</body></html>")
INSTA_PROFILE = ('<html><head><meta property="og:title" content="Rai Team (@rai.team) • Instagram photos and videos">'
                 '<meta property="og:description" content="15.2K Followers, 180 Following, 96 Posts - See Instagram photos and videos from Rai Team (@rai.team)">'
                 '<meta property="og:image" content="https://scontent.cdninstagram.com/a.jpg"></head><body></body></html>')
INSTA_POST = ('<html><head><meta property="og:title" content="Rai Team on Instagram">'
              '<meta property="og:description" content="1,204 likes, 87 comments - rai.team on September 30, 2026: &quot;Новая нейросеть уже на сайте! #ai #rai&quot;">'
              '</head><body></body></html>')
WEB = ('<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Rai — своя нейросеть</title>'
       '<meta name="description" content="Rai — нейросеть в браузере: отвечает на вопросы, пишет код и сайты, ищет в интернете, без серверов и ключей.">'
       '<meta name="viewport" content="width=device-width"><meta property="og:title" content="Rai"></head><body>'
       '<h1>Rai</h1><h2>Возможности</h2><p>' + "Нейросеть работает прямо в браузере и отвечает на вопросы. " * 20 + '</p>'
       '<img src="a.png" alt="Логотип"><img src="b.png"><a href="https://github.com/x">GitHub</a><a href="/about">О нас</a></body></html>')

# путь (как на сайте соцсети) -> (содержимое, тип)
PAGES = {
    "www.tiktok.com/@rai.team/video/7400000000000000001": (tiktok_page(TIKTOK_VIDEO), "text/html; charset=utf-8"),
    "www.tiktok.com/@rai.studio": (tiktok_page(TIKTOK_PROFILE), "text/html; charset=utf-8"),
    "www.youtube.com/watch": (YT_WATCH, "text/html; charset=utf-8"),
    "www.youtube.com/@raiteam": (YT_CHANNEL, "text/html; charset=utf-8"),
    "t.me/s/raichannel": (TELEGRAM, "text/html; charset=utf-8"),
    "www.instagram.com/rai.team/": (INSTA_PROFILE, "text/html; charset=utf-8"),
    "www.instagram.com/p/ABC123/": (INSTA_POST, "text/html; charset=utf-8"),
    "example.com/": (WEB, "text/html; charset=utf-8"),
}
