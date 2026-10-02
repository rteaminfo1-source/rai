// Тесты помощника по сайту (rai-guide.js) без браузера: node support/test_guide.js
"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const G = require("./rai-guide.js").RaiGuide._internal;
const site = JSON.parse(fs.readFileSync(path.join(__dirname, "site.json"), "utf8"));
const model = JSON.parse(fs.readFileSync(path.join(__dirname, "model.json"), "utf8"));

let failed = 0;
const test = (name, fn) => { try { fn(); console.log("ok   " + name); } catch (e) { failed++; console.log("FAIL " + name + ": " + e.message); } };

test("команды", () => {
  const cases = {
    "нажми на войти": ["click", "войти"], "Кликни по кнопке регистрации": ["click", "кнопке регистрации"],
    "открой кабинет": ["open", "кабинет"], "перейди в проекты": ["open", "проекты"], "зайди на форум": ["open", "форум"],
    "покажи где сменить пароль": ["show", "сменить пароль"], "где кнопка заявки?": ["show", "заявки"],
    "найди на странице рейтинг": ["show", "рейтинг"], "прокрути вниз": ["scroll", "вниз"], "листай наверх": ["scroll", "наверх"],
  };
  for (const [text, [kind, target]] of Object.entries(cases)) {
    const c = G.parseCommand(text);
    assert.ok(c, text);
    assert.deepStrictEqual([c.kind, c.target], [kind, target], text);
  }
  for (const text of ["как подать заявку", "привет", "что такое золотой билет", "не приходит код"]) assert.strictEqual(G.parseCommand(text), null, text);
});

test("похожесть текста", () => {
  assert.ok(G.scoreText("войти", "Войти") > 1);
  assert.ok(G.scoreText("кабинет", "Личный кабинет") >= 0.6);
  assert.ok(G.scoreText("сменить пароль", "Сменить пароль") > G.scoreText("сменить пароль", "Пароль"));
  assert.ok(G.scoreText("блог", "Форум") < 0.6);
});

test("карта сайта и нейросеть согласованы", () => {
  const ids = new Set(model.intents.map((i) => i.id));
  const pages = new Set(site.pages.map((p) => p.path));
  for (const [intent, steps] of Object.entries(site.guides)) {
    assert.ok(ids.has(intent), "в нейросети нет темы " + intent);
    assert.ok(steps.length, intent);
    for (const st of steps) {
      assert.ok(pages.has(st.page.split(/[?#]/)[0]), `${intent}: нет страницы ${st.page} в pages`);
      assert.ok(st.say, intent + ": нет say");
      if (st.when) assert.ok(["guest", "user"].includes(st.when), intent);
    }
  }
  for (const t of Object.keys(site.support_topics)) assert.ok(ids.has(t), t);
});

console.log(failed ? `${failed} тестов не прошли` : "Все тесты помощника прошли");
process.exit(failed ? 1 : 0);
