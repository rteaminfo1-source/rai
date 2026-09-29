"""Тесты Rai: python -m unittest -v"""

import json
import os
import tempfile
import unittest
from unittest import mock

import app as rai_app
import nlp
import skills
from brain import Brain, RaiError
from versions import VERSIONS, resolve

PRO, FAST, PLUS, SUN = (VERSIONS[k] for k in ("pro", "pro-fast", "pro-plus", "pro-sun"))


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
