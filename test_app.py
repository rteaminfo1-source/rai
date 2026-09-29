"""Тесты Rai: python -m unittest -v"""

import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import app as rai_app
import nlp
import skills
from brain import Brain, RaiError
from versions import VERSIONS, resolve

PRO, FAST, PLUS, SUN = (VERSIONS[k] for k in ("pro", "pro-fast", "pro-plus", "pro-sun"))

import fake_net
import net

_real_fetch = net.fetch_text


def setUpModule():
    # Тесты не ходят в интернет: сервисы отвечают из fake_net.
    net.fetch_text = fake_net.fetch_text
    net._cache.clear()


def tearDownModule():
    net.fetch_text = _real_fetch


class VersionsTest(unittest.TestCase):
    def test_four_versions(self):
        self.assertEqual(list(VERSIONS), ["pro", "pro-fast", "pro-plus", "pro-sun"])

    def test_aliases(self):
        for raw, expected in [
            (None, "pro"), ("Pro", "pro"), ("Pro Fast", "pro-fast"),
            ("pro_plus", "pro-plus"), ("Rai Pro Sun", "pro-sun"), ("prosun", "pro-sun"),
        ]:
            self.assertEqual(resolve(raw).id, expected, raw)
        self.assertIsNone(resolve("ultra"))


class NlpTest(unittest.TestCase):
    def test_stem_merges_word_forms(self):
        self.assertEqual(nlp.stem("питоне"), nlp.stem("питон"))
        self.assertEqual(nlp.stem("циклы"), nlp.stem("цикл"))

    def test_spellchecker(self):
        sp = nlp.SpellChecker(["привет", "что такое python", "цикл"])
        self.assertEqual(sp.correct("ghbdtn"), "привет")
        self.assertEqual(sp.correct("что такое pyton"), "что такое python")
        self.assertEqual(sp.correct("цыкл"), "цикл")


class SkillsTest(unittest.TestCase):
    def test_calculator(self):
        self.assertEqual(skills.calculator("сколько будет 15*4+2"), "15*4+2 = 62")
        self.assertEqual(skills.calculator("2 плюс 2 умножить на 3"), "2 + 2 * 3 = 8")
        self.assertEqual(skills.calculator("корень из 144"), "√144 = 12")
        self.assertEqual(skills.calculator("20% от 350"), "20% от 350 = 70")
        self.assertEqual(skills.calculator("10/0"), "На ноль делить нельзя.")
        self.assertIsNone(skills.calculator("привет"))
        self.assertIsNone(skills.calculator("__import__('os')"))
        self.assertIsNone(skills.calculator("9**9**9"))

    def test_converter(self):
        self.assertEqual(skills.converter("1 км в м"), "1 км = 1000 м")
        self.assertEqual(skills.converter("100 c в f"), "100 °C = 212 °F")
        self.assertEqual(skills.converter("1 кг в км"), "Эти единицы нельзя перевести друг в друга.")

    def test_password(self):
        answer = skills.password("сгенерируй пароль 20")
        self.assertEqual(len(answer.rsplit(" ", 1)[1]), 20)

    def test_text_tools(self):
        self.assertEqual(skills.text_tools("переверни: абв"), "вба")
        self.assertTrue(skills.text_tools("сколько слов в: раз два три").startswith("Слов: 3"))

    def test_skill_sets_differ_by_version(self):
        self.assertIsNone(skills.run("сгенерируй пароль", FAST.skills))
        self.assertIsNotNone(skills.run("сгенерируй пароль", PLUS.skills))


class BrainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, version, text, sid="t"):
        return self.brain.answer(version, text, session_id=sid)

    def test_knowledge_in_all_versions(self):
        for v in VERSIONS.values():
            self.assertEqual(self.ask(v, "привет")["intent"], "greeting", v.id)
            self.assertEqual(self.ask(v, "что такое питон?")["intent"], "python", v.id)
            self.assertEqual(self.ask(v, "что такое джаваскрипт")["intent"], "javascript", v.id)

    def test_generic_words_do_not_match(self):
        for v in VERSIONS.values():
            self.assertIsNone(self.ask(v, "что такое рхп")["intent"], v.id)

    def test_typos_only_in_plus_and_sun(self):
        self.assertIsNone(self.ask(PRO, "ghbdtn")["intent"])
        self.assertEqual(self.ask(PLUS, "ghbdtn")["intent"], "greeting")
        self.assertEqual(self.ask(SUN, "что такое pyton")["intent"], "python")

    def test_name_memory(self):
        self.ask(PLUS, "меня зовут артём", "a")
        self.assertEqual(self.ask(PLUS, "как меня зовут", "a")["answer"], "Вас зовут Артём.")
        self.assertIn("Артём", self.ask(PLUS, "спасибо", "a")["answer"])
        # Другая сессия имя не знает.
        self.assertNotIn("Артём", self.ask(PLUS, "как меня зовут", "b")["answer"])
        # Pro имя не запоминает.
        self.assertIn("Pro Plus", self.ask(PRO, "как меня зовут", "a")["answer"])

    def test_name_from_history_without_session(self):
        history = [{"role": "user", "content": "Меня зовут Ира"}, {"role": "assistant", "content": "Ок"}]
        r = self.brain.answer(PLUS, "как меня зовут", history=history)
        self.assertEqual(r["answer"], "Вас зовут Ира.")

    def test_more(self):
        self.ask(PLUS, "кто ты", "m")
        self.assertEqual(self.ask(PLUS, "подробнее", "m")["answer"], self.brain.intents["who_are_you"]["more"])
        first = self.ask(PLUS, "расскажи шутку", "m")["answer"]
        self.assertNotEqual(self.ask(PLUS, "ещё", "m")["answer"], first)

    def test_sun_memory_and_multi(self):
        self.assertIn("только Rai Pro Sun", self.ask(PLUS, "запомни, что я люблю чай")["answer"])
        self.ask(SUN, "запомни, что мой любимый цвет красный", "s")
        self.assertIn("красный", self.ask(SUN, "какой мой любимый цвет", "s")["answer"])
        self.assertIn("красный", self.ask(SUN, "что ты помнишь", "s")["answer"])
        self.ask(SUN, "забудь всё", "s")
        self.assertIn("ничего", self.ask(SUN, "что ты помнишь", "s")["answer"])
        self.assertEqual(self.ask(SUN, "что такое html? а css?")["intent"], ["html", "css"])

    def test_sun_is_detailed(self):
        more = self.brain.intents["python"]["more"]
        self.assertIn(more, self.ask(SUN, "что такое python")["answer"])
        self.assertNotIn(more, self.ask(PRO, "что такое python")["answer"])

    def test_suggestions(self):
        r = self.ask(PLUS, "расскажи про php сервер")
        self.assertTrue(r["intent"] or "Возможно" in r["answer"])

    def test_teach(self):
        self.brain.teach(["когда созвон команды"], "Созвон по пятницам в 19:00.")
        self.assertEqual(self.ask(PRO, "когда созвон?")["answer"], "Созвон по пятницам в 19:00.")
        with open(self.brain.learned_path, encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)["intents"]), 1)
        with self.assertRaises(RaiError):
            self.brain.teach([], "x")

    def test_validation(self):
        with self.assertRaises(RaiError):
            self.ask(PRO, "   ")
        with self.assertRaises(RaiError):
            self.ask(PRO, "а" * 10000)


class CreativeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_image(self):
        r = self.brain.answer(PRO, "нарисуй закат над морем")
        image = r["attachments"][0]
        self.assertEqual(image["type"], "image")
        self.assertTrue(image["svg"].startswith("<svg"))
        self.assertIn("Закат", image["title"])
        self.assertIn("не умею", self.brain.answer(PRO, "нарисуй кота")["answer"])
        self.assertEqual(self.brain.answer(FAST, "нарисуй закат")["attachments"], [])

    def test_logo_text_is_escaped(self):
        import creative
        svg = creative.make_image('логотип <script>alert(1)</script>')["svg"]
        self.assertNotIn("<script", svg)

    def test_slides(self):
        self.assertEqual(self.brain.answer(PRO, "сделай презентацию про python")["attachments"], [])
        deck = self.brain.answer(SUN, "сделай презентацию про python")["attachments"][0]
        kinds = [s["kind"] for s in deck["slides"]]
        self.assertEqual((kinds[0], kinds[-1]), ("title", "end"))
        self.assertIn("code", kinds)
        self.assertTrue(deck["slides"][0].get("image"))
        self.assertTrue(all(s.get("transition") for s in deck["slides"]))
        glossary_deck = self.brain.answer(PLUS, "презентация про космос")["attachments"][0]
        self.assertFalse(glossary_deck["template"])
        # «Как сделать презентацию?» — вопрос, а не просьба.
        self.assertEqual(self.brain.answer(PLUS, "как сделать презентацию")["attachments"], [])

    def test_glossary_capitals_tables(self):
        self.assertEqual(self.brain.answer(PRO, "что такое фотосинтез")["intent"], "glossary")
        self.assertEqual(self.brain.answer(PLUS, "что такое фатосинтез")["intent"], "glossary")
        self.assertEqual(self.brain.answer(PRO, "что такое сервер")["intent"], "glossary")
        self.assertIn("Париж", self.brain.answer(PRO, "столица франции")["answer"])
        self.assertIn("Сеул", self.brain.answer(PRO, "какая столица южной кореи?")["answer"])
        self.assertIn("| 7 × 3 | **21** |", self.brain.answer(PRO, "таблица умножения на 7")["answer"])
        unknown = self.brain.answer(SUN, "что такое квазар")["answer"]
        self.assertIn("запомни, что квазар", unknown)


class OnlineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))
        net._cache.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, text, version=None, sid="o"):
        return self.brain.answer(version or PLUS, text, session_id=sid)

    def test_weather_with_picture_and_city_memory(self):
        r = self.ask("какая погода в Казани?")
        self.assertEqual(r["intent"], "weather")
        self.assertIn("Казань", r["answer"])
        self.assertIn("| завтра |", r["answer"])
        self.assertEqual(r["attachments"][0]["type"], "image")
        self.assertIn("+12°", r["attachments"][0]["svg"])
        self.assertIn("Казань", self.ask("а погода?")["answer"])      # город запомнился
        self.assertIn("Москва", self.ask("погода в москве")["answer"])  # «москве» -> Москва

    def test_currency(self):
        self.assertIn("**100 USD = 9 250 RUB**", self.ask("100 долларов в рублях")["answer"])
        self.assertIn("1 USD = 92,5 RUB", self.ask("курс доллара")["answer"])
        self.assertIn("50 BYN", self.ask("50 белорусских рублей в рублях")["answer"])
        self.assertIn("| евро | EUR |", self.ask("курсы валют")["answer"])
        # «сумма», «Лариса», «1 фунт в кг» — не валюты
        self.assertNotEqual(self.ask("какая сумма у Ларисы")["intent"], "currency")
        self.assertEqual(self.ask("1 фунт в кг")["intent"], "skill")

    def test_translate(self):
        import online
        self.assertEqual(online.detect_language("Guten Morgen, wie geht es dir?"), "de")
        self.assertEqual(online.detect_language("¿Cómo estás?"), "es")
        self.assertEqual(online.detect_language("Привіт, як справи?"), "uk")
        self.assertEqual(online.detect_language("こんにちは"), "ja")
        self.assertEqual(online.parse_translate("переведи на английский: доброе утро"), ("доброе утро", None, "en"))
        self.assertEqual(online.parse_translate("как по-немецки кошка"), ("кошка", None, "de"))
        r = self.ask("переведи с английского на французский: good morning")
        self.assertIn("[en|fr] good morning", r["answer"])
        self.assertIn("[de|ru]", self.ask("переведи Guten Morgen")["answer"])

    def test_web_search(self):
        r = self.ask("найди в интернете эйфелева башня")
        self.assertEqual(r["intent"], "web")
        self.assertIn("Парижа", r["answer"])
        self.assertEqual(r["attachments"][0]["type"], "photo")
        # неизвестное — Rai сам идёт искать
        self.assertEqual(self.ask("что такое эйфелева башня")["intent"], "web")
        self.assertIn("умеют Rai Pro", self.ask("найди в интернете эйфелева башня", FAST)["answer"])

    def test_no_internet(self):
        def down(*a, **k):
            raise net.NetError("offline")
        with mock.patch.object(net, "fetch_text", down):
            self.assertIn("нет связи", self.ask("погода в Казани")["answer"])
            self.assertIn("нет связи", self.ask("курс доллара")["answer"])
            answer = self.ask("что такое квазар", SUN)["answer"]
            self.assertIn("запомни, что квазар", answer)
            self.assertIn("не получилось", answer)

    def test_programming_languages(self):
        self.assertIn("```go", self.ask("hello world на go")["answer"])
        self.assertIn("**Rust**", self.ask("что такое rust")["answer"])
        self.assertIn("**C#**", self.ask("что такое c#")["answer"])
        self.assertIn("Языки программирования", self.ask("какие языки программирования ты знаешь")["answer"])
        import proglangs
        self.assertGreaterEqual(len(proglangs.LANGUAGES), 45)
        # короткие названия («c», «r») только в явном контексте
        self.assertIsNone(proglangs.find_language("у меня есть r и c"))


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rai_app.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))
        self.client = rai_app.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"<title>Rai", resp.data)
        resp.close()

    def test_versions_endpoint(self):
        data = self.client.get("/api/versions").get_json()
        self.assertEqual([v["id"] for v in data["versions"]], list(VERSIONS))

    def test_chat_js_compatible(self):
        resp = self.client.post("/rai.php", json={"message": "Привет"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["answer"])
        self.assertEqual(data["version"], "pro")

    def test_version_in_path_body_and_form(self):
        self.assertEqual(self.client.post("/api/chat/pro-sun", json={"message": "x"}).get_json()["version"], "pro-sun")
        body = {"message": "x", "version": "Pro Fast"}
        self.assertEqual(self.client.post("/api/chat", json=body).get_json()["version"], "pro-fast")
        self.assertEqual(self.client.post("/rai", data=body).get_json()["version"], "pro-fast")

    def test_errors(self):
        r = self.client.post("/api/chat", json={"message": "x", "version": "ultra"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("answer", r.get_json())
        self.assertEqual(self.client.post("/api/chat", json={"message": " "}).status_code, 400)

    def test_teach_requires_token(self):
        body = {"patterns": ["пароль от wifi"], "answer": "Спросите у админа."}
        with mock.patch.dict(os.environ, {"RAI_ADMIN_TOKEN": ""}):
            self.assertEqual(self.client.post("/api/teach", json=body).status_code, 403)
        with mock.patch.dict(os.environ, {"RAI_ADMIN_TOKEN": "secret"}):
            self.assertEqual(self.client.post("/api/teach", json=body).status_code, 403)
            ok = self.client.post("/api/teach", json=body, headers={"X-Rai-Token": "secret"})
            self.assertEqual(ok.status_code, 200)
        answer = self.client.post("/api/chat", json={"message": "пароль от wifi"}).get_json()["answer"]
        self.assertEqual(answer, "Спросите у админа.")


if __name__ == "__main__":
    unittest.main()


class AuthTest(unittest.TestCase):
    def setUp(self):
        import auth
        self.auth = auth
        self.tmp = tempfile.TemporaryDirectory()
        auth.store = auth.UserStore(self.tmp.name)
        auth._attempts.clear()
        self.client = rai_app.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, **body):
        return self.client.post(path, json=body)

    def test_register_login_logout(self):
        self.assertIsNone(self.client.get("/auth/me").get_json()["user"])
        r = self.post("/auth/register", login="artem", password="1234567", email="a@b.ru")
        self.assertEqual(r.status_code, 400)  # пароль короче 8 символов
        r = self.post("/auth/register", login="artem", password="12345678", email="a@b.ru", name="Артём")
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(self.client.get("/auth/me").get_json()["user"]["name"], "Артём")
        self.assertEqual(self.post("/auth/register", login="Artem", password="12345678").status_code, 400)
        self.post("/auth/logout")
        self.assertIsNone(self.client.get("/auth/me").get_json()["user"])
        self.assertEqual(self.post("/auth/login", login="artem", password="неверный").status_code, 401)
        self.assertEqual(self.post("/auth/login", login="a@b.ru", password="12345678").status_code, 200)
        # пароль хранится только хешем
        with open(os.path.join(self.tmp.name, "users.json"), encoding="utf-8") as f:
            self.assertNotIn("12345678", f.read())

    def test_rate_limit(self):
        for _ in range(10):
            self.post("/auth/login", login="x", password="y")
        self.assertEqual(self.post("/auth/login", login="x", password="y").status_code, 429)

    def test_chats_sync(self):
        self.assertEqual(self.client.get("/api/chats").status_code, 401)
        self.post("/auth/register", login="user1", password="12345678")
        chats = [{"id": "c1", "title": "Тест", "messages": []}]
        self.assertEqual(self.client.put("/api/chats", json={"chats": chats}).status_code, 200)
        self.assertEqual(self.client.get("/api/chats").get_json()["chats"], chats)

    def test_google_login_creates_and_links_by_email(self):
        profile = {"sub": "g-1", "email": "a@b.ru", "email_verified": True, "name": "Артём", "picture": "https://p/1"}
        with mock.patch.object(self.auth, "GOOGLE_CLIENT_SECRET", "test-secret"):
            start = self.client.get("/auth/google/start")
            self.assertEqual(start.status_code, 302)
            self.assertIn("accounts.google.com", start.headers["Location"])
            self.assertIn("40211315152-", start.headers["Location"])
            self.assertNotIn("test-secret", start.headers["Location"])
            state = urllib.parse.parse_qs(urllib.parse.urlparse(start.headers["Location"]).query)["state"][0]
            # чужой state — отказ
            bad = self.client.get("/auth/google/callback?state=wrong&code=x")
            self.assertIn("auth_error=state", bad.headers["Location"])
            self.client.get("/auth/google/start")
            with self.client.session_transaction() as sess:
                state = sess["google_state"]
            with mock.patch.object(self.auth, "google_profile", return_value=profile):
                done = self.client.get(f"/google_callback.php?state={state}&code=abc")
            self.assertIn("auth=google", done.headers["Location"])
            me = self.client.get("/auth/me").get_json()["user"]
            self.assertEqual((me["login"], me["google"]), ("a", True))

    def test_google_not_configured(self):
        with mock.patch.object(self.auth, "GOOGLE_CLIENT_SECRET", ""):
            r = self.client.get("/auth/google/start")
            self.assertIn("google_not_configured", r.headers["Location"])
            self.assertFalse(self.client.get("/auth/me").get_json()["google"])
