"use strict";
/*
 * Дополнительные функции Discord-бота RTeam. Лежит рядом с index.js, тот подключает его сам.
 *
 * Админ-панель (/админ):
 *   🎉 розыгрыши (кнопка «Участвовать», итоги по времени, «Завершить сейчас», «Перевыбрать»),
 *   📊 опросы (встроенные опросы Discord), 👤 участник (уровень, преды, заявки; пред, мут, XP, сообщение в ЛС),
 *   🎭 роли по кнопкам (участники сами берут и снимают роли), 📝 заявки, ⚙️ модули (включить и выключить на лету).
 * Для всех: /бонус (каждый день, серия растёт), /профиль с достижениями, /спасибо (репутация), /викторина,
 *   /дуэль (камень-ножницы-бумага с участником или ботом), /монетка, /кубик, /шар, /помощь, /топ по категориям.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const FEATURES_VERSION = "2026.10.04";

module.exports = function install(api) {
  const { P, EPH, COLORS, button, row, cut, ts, isId, num } = api;
  const now = () => Date.now();
  const key = () => crypto.randomBytes(4).toString("hex");
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const shuffle = (arr) => { const a = arr.slice(); for (let k = a.length - 1; k > 0; k--) { const j = Math.floor(Math.random() * (k + 1)); [a[k], a[j]] = [a[j], a[k]]; } return a; };
  const back = (id = "adm:home", label = "Назад") => button(2, label, id, "⬅️");
  const say = (i, content) => i.reply({ content, flags: EPH, allowedMentions: { parse: [] } });
  const respond = (i, payload) => (i.isFromMessage && i.isFromMessage() ? i.update(payload) : i.reply({ ...payload, flags: EPH }));

  const FUN = () => Object.assign({
    enabled: true, daily_base: 50, daily_step: 10, daily_max: 150, quiz_xp: 25, quiz_seconds: 30,
    duel_xp: 15, duel_bot_xp: 5, thanks_xp: 10, thanks_cooldown_hours: 6,
  }, api.cfg.fun || {});
  function D() {
    const d = api.data;
    for (const k of ["gw", "rep", "daily", "quizw", "duelw", "rolepanels", "toggles"]) if (!d[k] || typeof d[k] !== "object") d[k] = {};
    if (typeof d.gw_seq !== "number") d.gw_seq = 0;
    return d;
  }
  const gamesOn = () => FUN().enabled !== false && D().toggles.games !== false;

  let QUIZ = [];
  try {
    QUIZ = (JSON.parse(fs.readFileSync(path.join(__dirname, "quiz.json"), "utf8")).questions || [])
      .filter((q) => q && q.q && Array.isArray(q.a) && q.a.length >= 2 && q.a.length <= 5 && q.a[q.c] !== undefined);
  } catch (e) { api.log("⚠️ quiz.json не загружен:", e.message); }

  const nextMidnight = () => { const d = new Date(now() + 3 * 3600e3); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + 1) - 3 * 3600e3; };

  /* ============================== команды для всех */

  const S = 3, INT = 4, USER = 6;
  const opt = (type, name, ru, description, extra = {}) => ({ type, name, name_localizations: { ru }, description, ...extra });
  const COMMANDS = [
    { name: "help", name_localizations: { ru: "помощь" }, description: "Что умеет бот RTeam" },
    { name: "daily", name_localizations: { ru: "бонус" }, description: "Ежедневный бонус XP — заходите каждый день, серия растёт" },
    { name: "profile", name_localizations: { ru: "профиль" }, description: "Профиль: уровень, репутация, достижения", options: [opt(USER, "user", "участник", "Чей профиль (по умолчанию ваш)")] },
    { name: "thanks", name_localizations: { ru: "спасибо" }, description: "Сказать спасибо — +1 к репутации участника", options: [opt(USER, "user", "участник", "Кого поблагодарить", { required: true })] },
    { name: "quiz", name_localizations: { ru: "викторина" }, description: "Вопрос викторины — кто первый ответит правильно, получит XP" },
    { name: "duel", name_localizations: { ru: "дуэль" }, description: "Камень, ножницы, бумага — с участником или с ботом", options: [opt(USER, "user", "соперник", "С кем играть (пусто — с ботом)")] },
    { name: "coin", name_localizations: { ru: "монетка" }, description: "Подбросить монетку" },
    { name: "dice", name_localizations: { ru: "кубик" }, description: "Бросить кубик", options: [opt(INT, "sides", "грани", "Сколько граней (по умолчанию 6)", { min_value: 2, max_value: 1000 })] },
    { name: "ball", name_localizations: { ru: "шар" }, description: "Магический шар ответит на вопрос", options: [opt(S, "question", "вопрос", "Ваш вопрос", { required: true, max_length: 200 })] },
  ];
  function extendCommands(list) {
    const top = list.find((c) => c.name === "top");
    if (top) {
      top.options = [opt(S, "by", "по", "Какой топ (по умолчанию — уровень)", { choices: [
        { name: "Уровень и XP", value: "xp" }, { name: "Репутация", value: "rep" }, { name: "Викторина", value: "quiz" },
        { name: "Дуэли", value: "duel" }, { name: "Серия бонусов", value: "streak" },
      ] })];
    }
    return list.concat(COMMANDS);
  }

  const ACH = [
    { icon: "💬", name: "Первое слово", test: (s) => s.msgs >= 1 },
    { icon: "🗣️", name: "Болтун (1000 сообщений)", test: (s) => s.msgs >= 1000 },
    { icon: "🎙️", name: "Голос сервера (10 ч в голосе)", test: (s) => s.voice >= 600 },
    { icon: "⭐", name: "10 уровень", test: (s) => s.level >= 10 },
    { icon: "🔥", name: "Неделя бонусов подряд", test: (s) => s.best >= 7 },
    { icon: "🧠", name: "Знаток (10 побед в викторине)", test: (s) => s.quiz >= 10 },
    { icon: "⚔️", name: "Дуэлянт (10 побед)", test: (s) => s.duel >= 10 },
    { icon: "💖", name: "Уважаемый (10 репутации)", test: (s) => s.rep >= 10 },
  ];
  function statsOf(uid) {
    const d = D(), st = (api.data.levels || {})[uid] || { xp: 0, msgs: 0, voice: 0 };
    const dl = d.daily[uid] || {};
    const alive = dl.last === api.dayKey() || dl.last === api.dayKey(now() - 864e5);
    return { ...st, level: api.levelOf(st.xp).level, rep: (d.rep[uid] || {}).n || 0, streak: alive ? dl.streak || 0 : 0, best: dl.best || 0,
      quiz: d.quizw[uid] || 0, duel: d.duelw[uid] || 0 };
  }
  function profileEmbed(user, member) {
    const s = statsOf(user.id), lv = api.levelOf(s.xp);
    const place = api.ranked().findIndex(([id]) => id === user.id);
    const earned = ACH.filter((a) => a.test(s));
    return {
      color: COLORS.blurple,
      author: { name: cut((member && member.displayName) || user.globalName || user.username, 256), icon_url: user.displayAvatarURL ? user.displayAvatarURL({ size: 64 }) : undefined },
      title: `⭐ Уровень ${lv.level}`,
      description: `${api.bar(lv.into, lv.need)}  **${num(lv.into)}** / ${num(lv.need)} XP`,
      fields: [
        { name: "Место", value: place >= 0 ? `#${place + 1}` : "—", inline: true },
        { name: "Репутация", value: `💖 ${s.rep}`, inline: true },
        { name: "Серия бонусов", value: `🔥 ${s.streak} (рекорд ${s.best})`, inline: true },
        { name: "Сообщений", value: num(s.msgs), inline: true },
        { name: "В голосе", value: api.fmtVoice(s.voice || 0), inline: true },
        { name: "Викторина · дуэли", value: `🧠 ${s.quiz} · ⚔️ ${s.duel}`, inline: true },
        { name: `Достижения ${earned.length}/${ACH.length}`, value: earned.length ? earned.map((a) => `${a.icon} ${a.name}`).join("\n") : "Пока нет — пишите в чат, заходите в голосовые, играйте в /викторина и /дуэль." },
      ],
    };
  }
  function topBy(by) {
    const d = D();
    const medal = ["🥇", "🥈", "🥉"];
    const src = {
      rep: ["💖 Топ репутации", Object.entries(d.rep).map(([id, r]) => [id, r.n || 0]), "💖"],
      quiz: ["🧠 Топ викторины", Object.entries(d.quizw), "побед"],
      duel: ["⚔️ Топ дуэлянтов", Object.entries(d.duelw), "побед"],
      streak: ["🔥 Самые длинные серии бонусов", Object.entries(d.daily).map(([id, s]) => [id, s.best || 0]), "дн."],
    }[by];
    const list = src[1].filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 10);
    return { color: COLORS.gold, title: src[0], description: list.map(([id, v], k) => `${medal[k] || `**${k + 1}.**`} <@${id}> — ${num(v)} ${src[2]}`).join("\n") || "Пока пусто — будьте первым!" };
  }
  function helpEmbed(i) {
    const staff = api.isPanel(i);
    const fields = [
      { name: "⭐ Уровни и профиль", value: "`/уровень` · `/профиль` · `/топ` (по уровню, репутации, викторине, дуэлям, бонусам) · `/бонус` — каждый день, серия растёт · `/спасибо @участник`" },
      { name: "🎮 Игры", value: "`/викторина` — первый правильный ответ получает XP · `/дуэль` — камень, ножницы, бумага · `/монетка` · `/кубик` · `/шар`" },
      { name: "💡 Сервер", value: "`/правила` · `/идея` · `/спросить` — ИИ Rai ответит только вам · `/привязать` — Discord к аккаунту rteam.info · заявка в модераторы — кнопкой в канале заявок" },
      { name: "✉️ ЛС", value: "Напишите боту в личные сообщения — ответит нейросеть Rai. Туда же приходят коды входа на rteam.info." },
    ];
    if (staff) fields.push({ name: "🛠️ Администрации", value: "`/админ` — объявления, обзвон, розыгрыши, опросы, участник, роли по кнопкам, модули · `/пред` `/мут` `/очистить` · `/настройка`" });
    return { color: COLORS.blurple, title: "🤖 Бот RTeam — что я умею", fields };
  }
  const BALL = ["Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да", "Можешь быть уверен в этом", "Мне кажется — да", "Вероятнее всего",
    "Хорошие перспективы", "Знаки говорят — да", "Да", "Пока не ясно, попробуй снова", "Спроси позже", "Лучше не рассказывать",
    "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять", "Даже не думай", "Мой ответ — нет", "По моим данным — нет",
    "Перспективы не очень хорошие", "Весьма сомнительно"];

  async function onCommand(i) {
    const n = i.commandName;
    if (n === "top") {
      const by = i.options.getString("by");
      if (!by || by === "xp") return false;
      await i.reply({ embeds: [topBy(by)], allowedMentions: { parse: [] } });
      return true;
    }
    if (!COMMANDS.some((c) => c.name === n)) return false;
    if (n === "help") { await i.reply({ embeds: [helpEmbed(i)], flags: EPH }); return true; }
    if (n === "profile") {
      const u = i.options.getUser("user") || i.user;
      await i.reply({ embeds: [profileEmbed(u, i.options.getMember("user") || (u.id === i.user.id ? i.member : null))], allowedMentions: { parse: [] } });
      return true;
    }
    if (!gamesOn()) { await say(i, "Игры и бонусы сейчас выключены администрацией."); return true; }
    if (n === "daily") await daily(i);
    else if (n === "thanks") await thanks(i);
    else if (n === "quiz") await quiz(i);
    else if (n === "duel") await duel(i);
    else if (n === "coin") await i.reply({ content: `🪙 <@${i.user.id}> подбрасывает монетку… **${Math.random() < 0.5 ? "Орёл" : "Решка"}**!`, allowedMentions: { parse: [] } });
    else if (n === "dice") {
      const sides = i.options.getInteger("sides") || 6;
      await i.reply({ content: `🎲 <@${i.user.id}> бросает кубик (${sides}): **${1 + Math.floor(Math.random() * sides)}**`, allowedMentions: { parse: [] } });
    } else if (n === "ball") {
      await i.reply({ embeds: [{ color: COLORS.blurple, title: "🎱 Магический шар", description: `**Вопрос:** ${cut(i.options.getString("question", true), 200)}\n**Ответ:** ${pick(BALL)}` }], allowedMentions: { parse: [] } });
    }
    return true;
  }

  async function daily(i) {
    const d = D(), f = FUN(), uid = i.user.id;
    const today = api.dayKey();
    const st = d.daily[uid] || { last: "", streak: 0, best: 0 };
    if (st.last === today) return say(i, `🎁 Сегодня бонус уже получен. Следующий — ${ts(nextMidnight())}. Серия: 🔥 ${st.streak}`);
    st.streak = st.last === api.dayKey(now() - 864e5) ? st.streak + 1 : 1;
    st.best = Math.max(st.best || 0, st.streak);
    st.last = today;
    d.daily[uid] = st;
    const xp = Math.min(f.daily_max, f.daily_base + f.daily_step * (st.streak - 1));
    const tomorrow = Math.min(f.daily_max, f.daily_base + f.daily_step * st.streak);
    const up = api.addActivity(uid, xp, 0, 0);
    api.save();
    await i.reply({ embeds: [{ color: COLORS.gold, title: "🎁 Ежедневный бонус",
      description: `<@${uid}> получает **+${xp} XP**!\n🔥 Серия: **${st.streak}** ${api.plural(st.streak, "день", "дня", "дней")} подряд\nЗавтра: +${tomorrow} XP — не пропускайте, иначе серия начнётся заново.` }],
      allowedMentions: { parse: [] } });
    if (up) await api.levelUp(uid, up, i.channel);
  }

  async function thanks(i) {
    const target = i.options.getUser("user", true), d = D(), f = FUN();
    if (target.id === i.user.id) return say(i, "Себя благодарить нельзя 🙂");
    if (target.bot) return say(i, "Ботам спасибо не нужно — но приятно! 🤖");
    const last = (d.rep[i.user.id] || {}).gave || 0;
    const left = last + f.thanks_cooldown_hours * 3600e3 - now();
    if (left > 0) return say(i, `Благодарить можно раз в ${f.thanks_cooldown_hours} ч. Следующий раз — ${ts(now() + left)}.`);
    (d.rep[i.user.id] = d.rep[i.user.id] || { n: 0 }).gave = now();
    const t = (d.rep[target.id] = d.rep[target.id] || { n: 0 });
    t.n++;
    const up = api.addActivity(target.id, f.thanks_xp, 0, 0);
    api.save();
    await i.reply({ content: `💖 <@${i.user.id}> благодарит <@${target.id}>! Репутация: **${t.n}** (+${f.thanks_xp} XP)`, allowedMentions: { users: [target.id] } });
    if (up) await api.levelUp(target.id, up, i.channel);
  }

  /* ---------- викторина */
  const quizzes = new Map(), quizByChannel = new Map(), recentQ = [];
  const L = "ABCDE";
  function quizPayload(st, result) {
    const q = st.q, f = FUN();
    const lines = st.order.map((oi, k) => `**${L[k]})** ${q.a[oi]}`).join("\n");
    const tail = result
      ? `\n\n✅ Правильный ответ: **${L[st.correct]}) ${q.a[q.c]}**\n` + (result.winner ? `🏆 Первым ответил(а) <@${result.winner}> — +${f.quiz_xp} XP` : "⏰ Время вышло — правильно никто не ответил.")
      : `\n\nУ каждого одна попытка. Ответы до ${ts(st.end)}. Первый правильный ответ — **+${f.quiz_xp} XP**.`;
    return {
      embeds: [{ color: result ? (result.winner ? COLORS.green : COLORS.gray) : COLORS.blurple, title: "🧠 Викторина", description: `**${q.q}**\n\n${lines}${tail}` }],
      components: [row(...st.order.map((oi, k) => ({ type: 2, style: result ? (k === st.correct ? 3 : 2) : 1, label: cut(`${L[k]}) ${q.a[oi]}`, 80), custom_id: `quiz:${st.key}:${k}`, disabled: !!result })))],
      allowedMentions: { parse: [] },
    };
  }
  async function quiz(i) {
    if (!QUIZ.length) return say(i, "Вопросов для викторины нет — администрация может добавить их в quiz.json.");
    const active = quizzes.get(quizByChannel.get(i.channelId));
    if (active && !active.done) return say(i, "В этом канале уже идёт викторина — ответьте на неё!");
    let qi = 0;
    for (let t = 0; t < 20; t++) { qi = Math.floor(Math.random() * QUIZ.length); if (!recentQ.includes(qi)) break; }
    recentQ.push(qi);
    while (recentQ.length > Math.min(20, QUIZ.length - 1)) recentQ.shift();
    const q = QUIZ[qi], order = shuffle(q.a.map((_, k) => k));
    const st = { key: key(), q, order, correct: order.indexOf(q.c), tried: new Set(), done: false, i, end: now() + FUN().quiz_seconds * 1000, ch: i.channelId };
    quizzes.set(st.key, st);
    quizByChannel.set(i.channelId, st.key);
    await i.reply(quizPayload(st));
    st.timer = setTimeout(() => finishQuiz(st).catch(() => {}), FUN().quiz_seconds * 1000);
  }
  async function finishQuiz(st) {
    if (st.done) return;
    st.done = true;
    await st.i.editReply(quizPayload(st, { winner: null })).catch(() => {});
    cleanupQuiz(st);
  }
  function cleanupQuiz(st) {
    if (quizByChannel.get(st.ch) === st.key) quizByChannel.delete(st.ch);
    setTimeout(() => quizzes.delete(st.key), 60000).unref();
  }
  async function onQuiz(i, k, answer) {
    const st = quizzes.get(k);
    if (!st || st.done) return say(i, "Этот вопрос уже закрыт. Новый — /викторина");
    if (st.tried.has(i.user.id)) return say(i, "У вас уже была попытка в этом вопросе.");
    st.tried.add(i.user.id);
    if (Number(answer) !== st.correct) return say(i, "❌ Неверно! Попробуйте в следующем вопросе.");
    st.done = true;
    clearTimeout(st.timer);
    const d = D();
    d.quizw[i.user.id] = (d.quizw[i.user.id] || 0) + 1;
    const up = api.addActivity(i.user.id, FUN().quiz_xp, 0, 0);
    api.save();
    await i.update(quizPayload(st, { winner: i.user.id }));
    cleanupQuiz(st);
    if (up) await api.levelUp(i.user.id, up, i.channel);
  }

  /* ---------- дуэль: камень, ножницы, бумага */
  const duels = new Map(), botDuelAt = new Map();
  const RPS = { r: "🪨 Камень", p: "📄 Бумага", s: "✂️ Ножницы" };
  const BEATS = { r: "s", s: "p", p: "r" };
  const who = (st, id) => (id === "bot" ? "🤖 Бот" : `<@${id}>`);
  function duelPayload(st) {
    const title = `⚔️ Дуэль: ${who(st, st.a)} против ${who(st, st.b)}`;
    if (st.stage === "invite") {
      return { content: `<@${st.b}>`, embeds: [{ color: COLORS.yellow, title: "⚔️ Вызов на дуэль!", description: `${who(st, st.a)} вызывает ${who(st, st.b)} на дуэль: камень, ножницы, бумага.\nПринять можно до ${ts(st.until)}.` }],
        components: [row(button(3, "Принять", `duel:${st.key}:acc`, "⚔️"), button(4, "Отказаться", `duel:${st.key}:dec`))], allowedMentions: { users: [st.b] } };
    }
    if (st.stage === "pick") {
      const done = [st.a, st.b].filter((id) => id !== "bot" && st.picks[id]).map((id) => `✅ <@${id}> выбрал(а)`);
      return { content: "", embeds: [{ color: COLORS.blurple, title, description: `Выберите — выбор соперника не виден до конца.\nВремя: до ${ts(st.until)}` + (done.length ? `\n\n${done.join("\n")}` : "") }],
        components: [row(...Object.entries(RPS).map(([c, label]) => button(1, label, `duel:${st.key}:pick:${c}`)))], allowedMentions: { parse: [] } };
    }
    if (st.stage === "declined") return { content: "", embeds: [{ color: COLORS.gray, title: "⚔️ Дуэль отменена", description: `${who(st, st.b)} отказался(ась) от дуэли.` }], components: [], allowedMentions: { parse: [] } };
    if (st.stage === "expired") return { content: "", embeds: [{ color: COLORS.gray, title: "⚔️ Дуэль не состоялась", description: "Время вышло." }], components: [], allowedMentions: { parse: [] } };
    const pa = st.picks[st.a], pb = st.picks[st.b];
    const res = pa === pb ? "🤝 **Ничья!**" : `🏆 Победил(а) ${who(st, BEATS[pa] === pb ? st.a : st.b)}` + (st.xp ? ` (+${st.xp} XP)` : "");
    return { content: "", embeds: [{ color: pa === pb ? COLORS.gray : COLORS.green, title, description: `${who(st, st.a)}: ${RPS[pa]}\n${who(st, st.b)}: ${RPS[pb]}\n\n${res}` }], components: [], allowedMentions: { parse: [] } };
  }
  async function duel(i) {
    const opp = i.options.getUser("user");
    if (opp && opp.id === i.user.id) return say(i, "Нельзя вызвать на дуэль самого себя 🙂");
    if (!opp || opp.bot) {
      const left = (botDuelAt.get(i.user.id) || 0) + 20000 - now();
      if (left > 0) return say(i, `С ботом можно играть раз в 20 секунд. Ещё ${Math.ceil(left / 1000)} с.`);
      botDuelAt.set(i.user.id, now());
    }
    const st = { key: key(), a: i.user.id, b: !opp || opp.bot ? "bot" : opp.id, picks: {}, i, stage: !opp || opp.bot ? "pick" : "invite", until: now() + 60000 };
    duels.set(st.key, st);
    await i.reply(duelPayload(st));
    st.timer = setTimeout(() => expireDuel(st).catch(() => {}), 60000);
  }
  async function expireDuel(st) {
    if (st.stage !== "invite" && st.stage !== "pick") return;
    st.stage = "expired";
    await st.i.editReply(duelPayload(st)).catch(() => {});
    setTimeout(() => duels.delete(st.key), 60000).unref();
  }
  async function onDuel(i, k, action, choice) {
    const st = duels.get(k);
    if (!st || !["invite", "pick"].includes(st.stage)) return say(i, "Эта дуэль уже закончилась. Новая — /дуэль");
    if (action === "acc" || action === "dec") {
      if (i.user.id !== st.b) return say(i, "Это приглашение не вам.");
      if (st.stage !== "invite") return say(i, "Дуэль уже началась.");
      st.stage = action === "acc" ? "pick" : "declined";
      if (st.stage === "pick") { clearTimeout(st.timer); st.until = now() + 60000; st.timer = setTimeout(() => expireDuel(st).catch(() => {}), 60000); }
      return i.update(duelPayload(st));
    }
    if (action !== "pick" || !RPS[choice] || st.stage !== "pick") return say(i, "Сначала соперник должен принять вызов.");
    if (i.user.id !== st.a && i.user.id !== st.b) return say(i, "Это не ваша дуэль 🙂 Вызовите кого-нибудь — /дуэль");
    if (st.picks[i.user.id]) return say(i, `Вы уже выбрали: ${RPS[st.picks[i.user.id]]}`);
    st.picks[i.user.id] = choice;
    if (st.b === "bot") st.picks.bot = pick(Object.keys(RPS));
    if (!st.picks[st.a] || !st.picks[st.b]) {
      await i.update(duelPayload(st));
      return i.followUp({ content: `Ваш выбор: ${RPS[choice]}. Ждём соперника…`, flags: EPH });
    }
    clearTimeout(st.timer);
    st.stage = "done";
    const pa = st.picks[st.a], pb = st.picks[st.b];
    let up = 0, winner = null;
    if (pa !== pb) {
      winner = BEATS[pa] === pb ? st.a : st.b;
      if (winner !== "bot") {
        st.xp = st.b === "bot" ? FUN().duel_bot_xp : FUN().duel_xp;
        if (st.b !== "bot") { const d = D(); d.duelw[winner] = (d.duelw[winner] || 0) + 1; }
        up = api.addActivity(winner, st.xp, 0, 0);
        api.save();
      }
    }
    await i.update(duelPayload(st));
    setTimeout(() => duels.delete(st.key), 60000).unref();
    if (up) await api.levelUp(winner, up, i.channel);
  }

  /* ============================== админ-панель: доп. разделы */

  function panelRows() {
    const d = D();
    const pending = Object.values(d.apps || {}).filter((a) => a.status === "pending").length;
    const gwActive = Object.values(d.gw).filter((g) => !g.done).length;
    return [
      row(button(1, `Розыгрыши${gwActive ? ` (${gwActive})` : ""}`, "adx:gw", "🎉"), button(1, "Опрос", "adx:poll", "📊"),
        button(2, "Участник", "adx:member", "👤"), button(2, "Роли по кнопкам", "adx:roles", "🎭")),
      row(button(2, `Заявки (${pending})`, "adx:apps", "📝"), button(2, "Модули", "adx:mods", "⚙️"), button(2, "Помощь", "adx:help", "❓")),
    ];
  }
  const annChannels = () => ((api.cfg.panel || {}).announce_channels || []).filter((c) => isId(c.id)).slice(0, 4);
  const channelButtons = (prefix) => [...annChannels().map((c, k) => button(1, cut(`В «${c.name || "канал"}»`, 80), `${prefix}:${k}`, c.emoji || "📢")),
    button(2, "Сюда (в этот канал)", `${prefix}:here`, "📍")];
  async function targetChannel(i, which) {
    if (which === "here") return i.channel;
    const c = annChannels()[Number(which)];
    return c ? api.chan(c.id) : null;
  }
  const field = (custom_id, label, style, max, required, placeholder, value) => {
    const f = { type: 4, custom_id, label, style, max_length: max, required };
    if (placeholder) f.placeholder = placeholder;
    if (value) f.value = cut(value, max);
    return row(f);
  };
  const modalText = (i, id) => { try { return String(i.fields.getTextInputValue(id) || "").trim(); } catch (e) { return ""; } };

  /* ---------- розыгрыши */
  const gwDrafts = new Map(), gwEditTimers = new Map();
  function parseDuration(text) {
    const m = String(text || "").trim().toLowerCase().replace(",", ".").match(/^(\d+(?:\.\d+)?)\s*(с|сек|s|м|мин|m|min|ч|час|часа|часов|h|д|дн|день|дня|дней|d)?$/);
    if (!m) return 0;
    const n = Number(m[1]), u = m[2] || "м";
    const mult = /^(с|сек|s)$/.test(u) ? 1000 : /^(ч|час|часа|часов|h)$/.test(u) ? 3600e3 : /^(д|дн|день|дня|дней|d)$/.test(u) ? 864e5 : 60000;
    const ms = Math.round(n * mult);
    return ms >= 10000 && ms <= 30 * 864e5 ? ms : 0;
  }
  function gwMessage(g) {
    const desc = (g.desc ? `${cut(g.desc, 1500)}\n\n` : "") + (g.done
      ? (g.won.length ? `🏆 Победители: ${g.won.map((u) => `<@${u}>`).join(", ")}` : "Никто не участвовал 😔")
      : `Нажмите **«Участвовать»**!\nИтоги: ${ts(g.ends)} (${ts(g.ends, "f")})`) + `\nПобедителей: **${g.winners}**`;
    return {
      embeds: [{ color: g.done ? COLORS.gray : COLORS.gold, title: `🎉 Розыгрыш: ${cut(g.prize, 200)}`, description: desc,
        footer: { text: `Участников: ${g.users.length}${g.done ? " · розыгрыш завершён" : ""}` }, timestamp: new Date(g.ends).toISOString() }],
      components: g.done ? [] : [row(button(3, "Участвовать", `gw:${g.id}:join`, "🎉"))],
      allowedMentions: { parse: [] },
    };
  }
  const gwLink = (g) => (g.msg ? `https://discord.com/channels/${api.cfg.guild_id}/${g.ch}/${g.msg}` : "");
  function gwView(note) {
    const all = Object.values(D().gw);
    const active = all.filter((g) => !g.done).sort((a, b) => a.ends - b.ends);
    const ended = all.filter((g) => g.done).sort((a, b) => b.ends - a.ends).slice(0, 5);
    const lines = [
      ...active.map((g) => `🎉 **${cut(g.prize, 80)}** — итоги ${ts(g.ends)} · участников ${g.users.length} · [сообщение](${gwLink(g)})`),
      ...ended.map((g) => `✅ ${cut(g.prize, 80)} — ${g.won.length ? g.won.map((u) => `<@${u}>`).join(", ") : "без победителей"}`),
    ];
    const rows = [];
    const sel = [...active, ...ended].slice(0, 25);
    if (sel.length) rows.push(row({ type: 3, custom_id: "adx:gwsel", placeholder: "Выберите розыгрыш", options: sel.map((g) => ({ label: cut(`${g.done ? "✅" : "🎉"} ${g.prize}`, 100), value: g.id })) }));
    rows.push(row(button(3, "Новый розыгрыш", "adx:gwnew", "➕"), back()));
    return { content: note || "", embeds: [{ color: COLORS.gold, title: "🎉 Розыгрыши", description: lines.join("\n") || "Розыгрышей пока нет. Нажмите «Новый розыгрыш»." }], components: rows, allowedMentions: { parse: [] } };
  }
  function gwCard(id, note) {
    const g = D().gw[id];
    if (!g) return gwView(note || "Розыгрыш не найден.");
    const b = g.done ? [button(1, "Перевыбрать победителей", `adx:gwre:${g.id}`, "🔁")]
      : [button(3, "Завершить сейчас", `adx:gwend:${g.id}`, "⏹️"), button(4, "Отменить", `adx:gwdel:${g.id}`, "🗑️")];
    return {
      content: note || "",
      embeds: [{ color: COLORS.gold, title: `🎉 ${cut(g.prize, 200)}`, description: [
        g.done ? "Статус: завершён" : `Итоги: ${ts(g.ends)} (${ts(g.ends, "f")})`, `Победителей: ${g.winners} · участников: ${g.users.length}`,
        g.won.length ? `Победители: ${g.won.map((u) => `<@${u}>`).join(", ")}` : "", gwLink(g) ? `[Сообщение розыгрыша](${gwLink(g)})` : "", g.by ? `Создал(а): <@${g.by}>` : "",
      ].filter(Boolean).join("\n") }],
      components: [row(...b, back("adx:gw", "К розыгрышам"))], allowedMentions: { parse: [] },
    };
  }
  async function gwFinish(g, reroll) {
    const prev = new Set(reroll ? g.won : []);
    const pool = shuffle(g.users.filter((u) => !prev.has(u)));
    g.won = pool.slice(0, g.winners);
    g.done = true;
    api.save();
    const ch = await api.chan(g.ch);
    const msg = ch ? await ch.messages.fetch(g.msg).catch(() => null) : null;
    if (msg) await msg.edit(gwMessage(g)).catch(() => {});
    if (ch) {
      await ch.send({ content: g.won.length ? `🎉 Поздравляем ${g.won.map((u) => `<@${u}>`).join(", ")}! ${reroll ? "Новые победители розыгрыша" : "Вы выиграли"} **${cut(g.prize, 200)}**!`
        : `Розыгрыш **${cut(g.prize, 200)}** завершён — участников не было.`, allowedMentions: { users: g.won }, reply: msg ? { messageReference: msg.id, failIfNotExists: false } : undefined }).catch(() => {});
    }
    for (const u of g.won) {
      await api.dmUser(u, { embeds: [{ color: COLORS.gold, title: "🎉 Вы выиграли в розыгрыше!", description: `Приз: **${cut(g.prize, 200)}**. Администрация свяжется с вами — или напишите ей сами.` }] });
    }
    api.modLog({ color: COLORS.gold, title: `🎉 Розыгрыш ${reroll ? "перевыбран" : "завершён"}`, description: `${cut(g.prize, 200)} — ${g.won.map((u) => `<@${u}>`).join(", ") || "без победителей"}` });
  }
  async function onGwJoin(i, id) {
    const g = D().gw[id];
    if (!g || g.done) return say(i, "Этот розыгрыш уже завершён.");
    const k = g.users.indexOf(i.user.id);
    if (k >= 0) g.users.splice(k, 1); else g.users.push(i.user.id);
    api.save();
    if (!gwEditTimers.has(id)) {
      gwEditTimers.set(id, setTimeout(async () => {
        gwEditTimers.delete(id);
        const gg = D().gw[id];
        if (gg && !gg.done) await i.message.edit(gwMessage(gg)).catch(() => {});
      }, 2000));
    }
    return say(i, k >= 0 ? "Вы вышли из розыгрыша." : `🎉 Вы участвуете в розыгрыше **${cut(g.prize, 100)}**! Итоги ${ts(g.ends)}. Нажмите ещё раз, чтобы выйти.`);
  }

  /* ---------- опросы */
  const pollDrafts = new Map();
  function pollPreview(d, note) {
    return {
      content: note || "👀 Так будет выглядеть опрос. Где опубликовать?",
      embeds: [{ color: COLORS.blurple, title: `📊 ${cut(d.question, 256)}`, description: d.answers.map((a, k) => `${k + 1}. ${a}`).join("\n") +
        `\n\nДлится: **${d.hours} ч** · Несколько ответов: **${d.multi ? "да" : "нет"}**` }],
      components: [row(...channelButtons("adx:pollpub")), row(button(2, d.multi ? "Несколько ответов: да" : "Несколько ответов: нет", "adx:pollmulti", "🔀"), button(2, "Изменить", "adx:poll", "✏️"), back())],
      allowedMentions: { parse: [] },
    };
  }

  /* ---------- участник */
  async function memberCard(i, uid, note) {
    const g = api.guild(), d = D();
    const m = g ? await g.members.fetch(uid).catch(() => null) : null;
    const user = m ? m.user : await api.client.users.fetch(uid).catch(() => null);
    if (!user) return memberPick("Участник не найден.");
    const s = statsOf(uid);
    const warns = api.activeWarnings(uid);
    const apps = Object.values(d.apps || {}).filter((a) => a.user_id === uid);
    const until = m && m.communicationDisabledUntilTimestamp > now() ? m.communicationDisabledUntilTimestamp : 0;
    return {
      content: note || "",
      embeds: [{
        color: COLORS.blurple, author: { name: cut(`${(m && m.displayName) || user.globalName || user.username} · ${user.tag || user.username}`, 256), icon_url: user.displayAvatarURL ? user.displayAvatarURL({ size: 64 }) : undefined },
        description: [`<@${uid}> · ID \`${uid}\``, m ? `На сервере с ${ts(m.joinedTimestamp || now(), "D")}` : "❗ Не на сервере", `Аккаунт создан ${ts(user.createdTimestamp || now(), "D")}`,
          until ? `🔇 В муте до ${ts(until)}` : ""].filter(Boolean).join("\n"),
        fields: [
          { name: "Уровень", value: `${s.level} · ${num(s.xp)} XP`, inline: true },
          { name: "Активность", value: `💬 ${num(s.msgs)} · 🎙 ${api.fmtVoice(s.voice || 0)}`, inline: true },
          { name: "Репутация", value: `💖 ${s.rep}`, inline: true },
          { name: `Предупреждения: ${warns.length}`, value: warns.slice(-3).map((w) => `• ${ts(w.t, "d")} ${cut(w.reason, 80)}`).join("\n") || "нет" },
          { name: "Заявки", value: apps.slice(-5).map((a) => `#${a.id} — ${cut(api.statusLine(a).split("\n")[0], 70)}`).join("\n") || "нет" },
        ],
      }],
      components: [
        row(button(4, "Пред", `adx:mwarn:${uid}`, "⚠️"), button(2, "Снять преды", `adx:munwarn:${uid}`, "🧹"), button(2, "Мут 10 мин", `adx:mmute:${uid}:10`, "🔇"),
          button(2, "Мут 1 час", `adx:mmute:${uid}:60`, "🔇"), button(2, "Снять мут", `adx:munmute:${uid}`, "🔊")),
        row(button(1, "XP ±", `adx:mxp:${uid}`, "✨"), button(1, "Написать в ЛС", `adx:mdm:${uid}`, "✉️"), button(2, "Другой участник", "adx:member", "👤"), back()),
      ],
      allowedMentions: { parse: [] },
    };
  }
  function memberPick(note) {
    return { content: note || "", embeds: [{ color: COLORS.blurple, title: "👤 Участник", description: "Выберите участника — покажу уровень, предупреждения и заявки, а ещё можно выдать пред, мут, XP или написать ему в ЛС." }],
      components: [row({ type: 5, custom_id: "adx:msel", placeholder: "Выберите участника", min_values: 1, max_values: 1 }), row(back())], allowedMentions: { parse: [] } };
  }
  async function targetMember(i, uid) {
    const g = api.guild();
    const m = g ? await g.members.fetch(uid).catch(() => null) : null;
    if (!m) return { error: "Участника нет на сервере." };
    if (!api.canModerate(i.member, m)) return { error: "Нельзя: у участника роль не ниже вашей (или это бот/владелец)." };
    return { m };
  }

  /* ---------- роли по кнопкам */
  const roleDrafts = new Map();
  const DANGER = [P.Administrator, P.ManageGuild, P.ManageRoles, P.ManageChannels, P.BanMembers, P.KickMembers, P.ManageMessages, P.ModerateMembers,
    P.MentionEveryone, P.ManageWebhooks, P.ManageNicknames, P.MoveMembers, P.MuteMembers, P.DeafenMembers];
  function checkRoles(roleIds) {
    const g = api.guild(), me = g && g.members.me;
    const ok = [], bad = [];
    for (const id of roleIds) {
      const r = g && g.roles.cache.get(id);
      if (!r || id === g.id) bad.push(`«${r ? r.name : id}» — нельзя (@everyone)`);
      else if (r.managed) bad.push(`«${r.name}» — роль бота или интеграции`);
      else if (!me || r.position >= me.roles.highest.position) bad.push(`«${r.name}» — выше роли бота`);
      else if (DANGER.some((f) => r.permissions.has(f))) bad.push(`«${r.name}» — даёт права модерации, такие роли сами брать нельзя`);
      else ok.push(id);
    }
    return { ok, bad };
  }
  function rolePanelMessage(roleIds) {
    const g = api.guild();
    const roles = roleIds.map((id) => g.roles.cache.get(id)).filter(Boolean);
    const rows = [];
    for (let k = 0; k < roles.length; k += 5) rows.push(row(...roles.slice(k, k + 5).map((r) => button(2, cut(r.name, 80), `role:${r.id}`))));
    return { embeds: [{ color: COLORS.blurple, title: "🎭 Выберите роли", description: "Нажмите на кнопку, чтобы взять роль. Нажмите ещё раз — роль снимется.\n\n" + roles.map((r) => `• <@&${r.id}>`).join("\n") }],
      components: rows, allowedMentions: { parse: [] } };
  }
  async function onRole(i, rid) {
    const p = D().rolepanels[i.message.id];
    if (!p || !p.roles.includes(rid)) return say(i, "Эта кнопка устарела — попросите администрацию обновить сообщение с ролями.");
    const m = i.member, r = i.guild.roles.cache.get(rid);
    if (!m || !r) return say(i, "Роль не найдена.");
    const has = m.roles.cache.has(rid);
    try {
      if (has) await m.roles.remove(rid, "Роли по кнопкам"); else await m.roles.add(rid, "Роли по кнопкам");
    } catch (e) { return say(i, `Не получилось: ${api.roleError(e, rid)}`); }
    return say(i, has ? `Роль «${r.name}» снята.` : `✅ Роль «${r.name}» выдана!`);
  }

  /* ---------- заявки и модули */
  function appsView() {
    const list = Object.values(D().apps || {}).filter((a) => a.status === "pending").sort((a, b) => a.created - b.created);
    const link = (a) => (a.review ? `https://discord.com/channels/${api.cfg.guild_id}/${a.review.channel}/${a.review.message}` : "");
    return { content: "", embeds: [{ color: COLORS.blurple, title: `📝 Заявки ждут решения — ${list.length}`,
      description: list.slice(0, 20).map((a) => `**#${a.id}** <@${a.user_id}> · ${ts(a.created)}${link(a) ? ` · [открыть](${link(a)})` : ""}`).join("\n") || "Все заявки рассмотрены 👍" }],
      components: [row(button(3, "Обзвон", "adm:calls", "📞"), back())], allowedMentions: { parse: [] } };
  }
  const MODS = [["applications", "Приём заявок"], ["ideas", "Идеи"], ["automod", "Автомодерация"], ["levels", "Уровни и XP"], ["games", "Игры и бонусы"]];
  const isOn = (k) => (k === "games" ? gamesOn() : !!(api.cfg[k] && api.cfg[k].enabled));
  function applyToggles() {
    const t = D().toggles;
    for (const [k] of MODS) if (k !== "games" && typeof t[k] === "boolean" && api.cfg[k]) api.cfg[k].enabled = t[k];
  }
  function modsView(note) {
    return { content: note || "", embeds: [{ color: COLORS.blurple, title: "⚙️ Модули бота", description: MODS.map(([k, name]) => `${isOn(k) ? "✅" : "⛔"} ${name}`).join("\n") +
      "\n\nНажмите, чтобы включить или выключить. Выключенный «Приём заявок» показывает в канале заявок «Набор закрыт»." }],
      components: [row(...MODS.map(([k, name]) => button(isOn(k) ? 3 : 2, `${isOn(k) ? "✅" : "⛔"} ${name}`, `adx:tog:${k}`))), row(back())], allowedMentions: { parse: [] } };
  }

  /* ============================== обработчики */

  async function onButton(i) {
    const [scope, a, b, c] = i.customId.split(":");
    if (scope === "quiz") { await onQuiz(i, a, b); return true; }
    if (scope === "duel") { await onDuel(i, a, b, c); return true; }
    if (scope === "gw") { await onGwJoin(i, a); return true; }
    if (scope === "role") { await onRole(i, a); return true; }
    if (scope !== "adx") return false;
    if (!api.isPanel(i)) { await say(i, "Админ-панель доступна только администрации."); return true; }
    const d = D();
    switch (a) {
      case "help": await i.update({ content: "", embeds: [helpEmbed(i)], components: [row(back())] }); break;
      case "gw": await i.update(gwView()); break;
      case "gwnew": await i.showModal({ custom_id: "adx:gwm", title: "Новый розыгрыш", components: [
        field("prize", "Приз", 1, 100, true, "Например: Nitro на месяц"),
        field("dur", "Сколько длится", 1, 20, true, "30м, 2ч, 1д"),
        field("win", "Сколько победителей", 1, 2, false, "1"),
        field("desc", "Условия (необязательно)", 2, 1000, false, "Например: быть на сервере до итогов")] }); break;
      case "gwpub": {
        const dr = gwDrafts.get(i.user.id);
        if (!dr) { await i.update(gwView("Черновик устарел — создайте розыгрыш ещё раз.")); break; }
        const ch = await targetChannel(i, b);
        if (!ch) { await i.update(gwView("❌ Канал не найден.")); break; }
        await i.deferUpdate();
        const g = { id: String(++d.gw_seq), prize: dr.prize, desc: dr.desc, winners: dr.winners, ends: now() + dr.ms, ch: ch.id, msg: null, users: [], won: [], done: false, by: i.user.id };
        let msg;
        try { msg = await ch.send(gwMessage(g)); } catch (e) { d.gw_seq--; await i.editReply(gwView(`❌ Не удалось опубликовать: ${e.code === 50013 ? "у бота нет прав в этом канале" : e.message}`)); break; }
        g.msg = msg.id;
        d.gw[g.id] = g;
        gwDrafts.delete(i.user.id);
        api.save();
        api.modLog({ color: COLORS.gold, title: "🎉 Новый розыгрыш", description: `${cut(g.prize, 200)} — <@${i.user.id}>, итоги ${ts(g.ends)}: ${msg.url}` });
        await i.editReply(gwCard(g.id, `✅ Розыгрыш запущен: ${msg.url}`));
        break;
      }
      case "gwend": case "gwre": {
        const g = d.gw[b];
        if (!g || (a === "gwend" && g.done) || (a === "gwre" && !g.done)) { await i.update(gwView("Розыгрыш уже изменился — обновите список.")); break; }
        await i.deferUpdate();
        await gwFinish(g, a === "gwre");
        await i.editReply(gwCard(g.id, g.won.length ? `✅ Победители: ${g.won.map((u) => `<@${u}>`).join(", ")}` : "Победителей нет — участников не было."));
        break;
      }
      case "gwdel": {
        const g = d.gw[b];
        if (!g || g.done) { await i.update(gwView()); break; }
        g.done = true; g.won = []; g.cancelled = true;
        api.save();
        const ch = await api.chan(g.ch);
        const msg = ch ? await ch.messages.fetch(g.msg).catch(() => null) : null;
        if (msg) await msg.edit({ embeds: [{ color: COLORS.gray, title: `🎉 Розыгрыш: ${cut(g.prize, 200)}`, description: "Розыгрыш отменён администрацией." }], components: [] }).catch(() => {});
        await i.update(gwView("🗑️ Розыгрыш отменён."));
        break;
      }
      case "poll": {
        const dr = pollDrafts.get(i.user.id);
        await i.showModal({ custom_id: "adx:pollm", title: "Новый опрос", components: [
          field("q", "Вопрос", 1, 300, true, "Например: Во что играем в пятницу?", dr && dr.question),
          field("ans", "Варианты — каждый с новой строки (2–10)", 2, 1000, true, "Minecraft\nCS2\nRoblox", dr && dr.answers.join("\n")),
          field("hours", "Сколько часов длится (1–768)", 1, 3, false, "24", dr && String(dr.hours))] });
        break;
      }
      case "pollmulti": {
        const dr = pollDrafts.get(i.user.id);
        if (!dr) { await i.update(api.panelHome("Черновик опроса устарел.")); break; }
        dr.multi = !dr.multi;
        await i.update(pollPreview(dr));
        break;
      }
      case "pollpub": {
        const dr = pollDrafts.get(i.user.id);
        if (!dr) { await i.update(api.panelHome("Черновик опроса устарел.")); break; }
        const ch = await targetChannel(i, b);
        if (!ch) { await i.update(pollPreview(dr, "❌ Канал не найден.")); break; }
        await i.deferUpdate();
        try {
          const msg = await ch.send({ poll: { question: { text: dr.question }, answers: dr.answers.map((t) => ({ text: t })), duration: dr.hours, allowMultiselect: dr.multi } });
          pollDrafts.delete(i.user.id);
          api.modLog({ color: COLORS.blurple, title: "📊 Опрос", description: `<@${i.user.id}>: ${cut(dr.question, 200)} — ${msg.url}` });
          await i.editReply(api.panelHome(`✅ Опрос опубликован: ${msg.url}`));
        } catch (e) {
          await i.editReply(pollPreview(dr, `❌ Не опубликовано: ${e.code === 50013 ? "у бота нет права «Создавать опросы» или писать в этот канал" : e.message}`));
        }
        break;
      }
      case "member": await i.update(memberPick()); break;
      case "mwarn": await i.showModal({ custom_id: `adx:mwarnm:${b}`, title: "Предупреждение", components: [field("reason", "Причина (участник увидит её в ЛС)", 2, 300, true)] }); break;
      case "mxp": await i.showModal({ custom_id: `adx:mxpm:${b}`, title: "Изменить XP", components: [field("amount", "Сколько XP: +100 добавить, -50 убрать", 1, 8, true, "+100")] }); break;
      case "mdm": await i.showModal({ custom_id: `adx:mdmm:${b}`, title: "Сообщение в ЛС", components: [field("text", "Текст (придёт от бота от имени администрации)", 2, 2000, true)] }); break;
      case "munwarn": {
        const before = api.activeWarnings(b).length;
        d.warnings[b] = (d.warnings[b] || []).filter((w) => !api.activeWarnings(b).includes(w));
        api.save();
        api.modLog({ color: COLORS.green, title: "🧹 Предупреждения сняты", description: `<@${b}> — <@${i.user.id}> (было ${before})` });
        await i.update(await memberCard(i, b, `🧹 Сняты предупреждения: ${before}.`));
        break;
      }
      case "mmute": case "munmute": {
        const t = await targetMember(i, b);
        if (t.error) { await i.update(await memberCard(i, b, `❌ ${t.error}`)); break; }
        await i.deferUpdate();
        let note;
        if (a === "mmute") {
          const ok = await api.timeoutMember(t.m, Number(c) || 10, `Админ-панель (${i.user.tag})`);
          note = ok ? `🔇 Мут на ${api.fmtMin(Number(c) || 10)}.` : "❌ Не удалось: у бота нет права на тайм-аут или роль участника выше роли бота.";
          if (ok) api.modLog({ color: COLORS.yellow, title: "🔇 Мут", description: `<@${b}> на ${api.fmtMin(Number(c) || 10)} — <@${i.user.id}> (админ-панель)` });
        } else {
          note = await t.m.timeout(null, `Админ-панель (${i.user.tag})`).then(() => "🔊 Мут снят.", (e) => `❌ ${e.message}`);
        }
        await i.editReply(await memberCard(i, b, note));
        break;
      }
      case "roles": await i.update({ content: "", embeds: [{ color: COLORS.blurple, title: "🎭 Роли по кнопкам",
        description: "Выберите роли (до 10), которые участники смогут брать сами — например, роли уведомлений или игр. Бот опубликует сообщение с кнопками в канале, где вы открыли панель.\n\nНельзя: роли выше роли бота и роли с правами модерации." }],
        components: [row({ type: 6, custom_id: "adx:rsel", placeholder: "Выберите роли", min_values: 1, max_values: 10 }), row(back())] }); break;
      case "rpub": {
        const ok = roleDrafts.get(i.user.id);
        if (!ok || !ok.length) { await i.update(api.panelHome("Выберите роли ещё раз.")); break; }
        await i.deferUpdate();
        try {
          const msg = await i.channel.send(rolePanelMessage(ok));
          d.rolepanels[msg.id] = { ch: msg.channelId, roles: ok, by: i.user.id, t: now() };
          roleDrafts.delete(i.user.id);
          api.save();
          await i.editReply(api.panelHome(`✅ Сообщение с ролями опубликовано: ${msg.url}`));
        } catch (e) { await i.editReply(api.panelHome(`❌ Не опубликовано: ${e.code === 50013 ? "у бота нет прав в этом канале" : e.message}`)); }
        break;
      }
      case "apps": await i.update(appsView()); break;
      case "mods": await i.update(modsView()); break;
      case "tog": {
        if (!MODS.some(([k]) => k === b)) { await i.update(modsView()); break; }
        d.toggles[b] = !isOn(b);
        applyToggles();
        api.save();
        if (b === "applications") await api.ensurePanel().catch(() => {});
        const name = MODS.find(([k]) => k === b)[1];
        api.modLog({ color: COLORS.blurple, title: "⚙️ Модули", description: `${name}: ${d.toggles[b] ? "включено" : "выключено"} — <@${i.user.id}>` });
        await i.update(modsView(`${d.toggles[b] ? "✅ Включено" : "⛔ Выключено"}: ${name}.`));
        break;
      }
      default: await i.update(api.panelHome());
    }
    return true;
  }

  async function onSelect(i) {
    if (!i.customId.startsWith("adx:")) return false;
    if (!api.isPanel(i)) { await say(i, "Админ-панель доступна только администрации."); return true; }
    if (i.customId === "adx:gwsel") await i.update(gwCard(i.values[0]));
    else if (i.customId === "adx:msel") await i.update(await memberCard(i, i.values[0]));
    else if (i.customId === "adx:rsel") {
      const { ok, bad } = checkRoles(i.values);
      roleDrafts.set(i.user.id, ok);
      await i.update({ content: bad.length ? `⚠️ Пропущены: ${bad.join("; ")}` : "",
        embeds: [{ color: COLORS.blurple, title: "🎭 Роли по кнопкам — проверьте", description: ok.length ? ok.map((r) => `• <@&${r}>`).join("\n") + `\n\nОпубликовать в <#${i.channelId}>?` : "Ни одну из выбранных ролей нельзя раздавать по кнопкам." }],
        components: [row(...(ok.length ? [button(3, "Опубликовать здесь", "adx:rpub", "📌")] : []), button(2, "Выбрать заново", "adx:roles", "🔁"), back())], allowedMentions: { parse: [] } });
    }
    return true;
  }

  async function onModal(i) {
    const [scope, a, b] = i.customId.split(":");
    if (scope !== "adx") return false;
    if (!api.isPanel(i)) { await say(i, "Админ-панель доступна только администрации."); return true; }
    if (a === "gwm") {
      const ms = parseDuration(modalText(i, "dur"));
      const winners = Math.min(20, Math.max(1, parseInt(modalText(i, "win") || "1", 10) || 1));
      if (!ms) { await respond(i, gwView("❌ Не понял длительность. Пишите так: 30м, 2ч, 1д (от 10 секунд до 30 дней).")); return true; }
      const dr = { prize: modalText(i, "prize"), desc: modalText(i, "desc"), winners, ms };
      gwDrafts.set(i.user.id, dr);
      const preview = gwMessage({ id: "0", prize: dr.prize, desc: dr.desc, winners, ends: now() + ms, users: [], won: [], done: false });
      await respond(i, { content: "👀 Так будет выглядеть розыгрыш. Где опубликовать?", embeds: preview.embeds,
        components: [row(...channelButtons("adx:gwpub")), row(button(2, "Изменить", "adx:gwnew", "✏️"), back("adx:gw", "К розыгрышам"))], allowedMentions: { parse: [] } });
      return true;
    }
    if (a === "pollm") {
      const answers = modalText(i, "ans").split(/\r?\n/).map((s) => s.trim()).filter(Boolean).map((s) => cut(s, 55));
      const hours = Math.min(768, Math.max(1, parseInt(modalText(i, "hours") || "24", 10) || 24));
      const dr = { question: cut(modalText(i, "q"), 300), answers: [...new Set(answers)].slice(0, 10), hours, multi: (pollDrafts.get(i.user.id) || {}).multi || false };
      pollDrafts.set(i.user.id, dr);
      if (dr.answers.length < 2) { await respond(i, { ...pollPreview(dr, "❌ Нужно минимум 2 разных варианта — каждый с новой строки."), components: [row(button(2, "Изменить", "adx:poll", "✏️"), back())] }); return true; }
      await respond(i, pollPreview(dr));
      return true;
    }
    if (a === "mwarnm") {
      const t = await targetMember(i, b);
      if (t.error) { await respond(i, await memberCard(i, b, `❌ ${t.error}`)); return true; }
      if (i.isFromMessage()) await i.deferUpdate(); else await i.deferReply({ flags: EPH });
      const reason = modalText(i, "reason");
      const count = api.addWarning(b, reason, i.user.id);
      const minutes = api.timeoutFor(count);
      const muted = minutes ? await api.timeoutMember(t.m, minutes, `Предупреждений: ${count}`) : false;
      await api.dmUser(b, { embeds: [{ color: COLORS.yellow, title: "⚠️ Предупреждение", description: `На сервере **${i.guild.name}**: ${reason}\nПредупреждений: **${count}**` +
        (api.nextStepText(count) ? ` — ${api.nextStepText(count)}.` : ".") + (muted ? `\n🔇 Мут на ${api.fmtMin(minutes)}.` : "") }] });
      api.modLog({ color: COLORS.yellow, title: "⚠️ Предупреждение", description: `<@${b}> от <@${i.user.id}> (админ-панель): ${reason}\nВсего: ${count}${muted ? `, мут ${api.fmtMin(minutes)}` : ""}` });
      await i.editReply(await memberCard(i, b, `⚠️ Предупреждение выдано (всего ${count})${muted ? `, мут на ${api.fmtMin(minutes)}` : ""}.`));
      return true;
    }
    if (a === "mxpm") {
      const m = modalText(i, "amount").replace(/\s/g, "").match(/^([+-]?)(\d{1,7})$/);
      if (!m) { await respond(i, await memberCard(i, b, "❌ Напишите число, например +100 или -50.")); return true; }
      const delta = (m[1] === "-" ? -1 : 1) * Number(m[2]);
      const st = (api.data.levels[b] = api.data.levels[b] || { xp: 0, msgs: 0, voice: 0 });
      const before = st.xp;
      st.xp = Math.max(0, st.xp + delta);
      api.save();
      api.modLog({ color: COLORS.blurple, title: "✨ XP изменён", description: `<@${b}>: ${num(before)} → ${num(st.xp)} — <@${i.user.id}>` });
      await respond(i, await memberCard(i, b, `✨ XP: ${num(before)} → ${num(st.xp)} (уровень ${api.levelOf(st.xp).level}).`));
      return true;
    }
    if (a === "mdmm") {
      const text = modalText(i, "text");
      const r = await api.dmUser(b, { embeds: [{ color: COLORS.blurple, title: "✉️ Сообщение от администрации RTeam", description: cut(text, 4000) }] });
      if (r.ok) api.modLog({ color: COLORS.blurple, title: "✉️ Сообщение в ЛС", description: `<@${i.user.id}> → <@${b}>: ${cut(text, 500)}` });
      await respond(i, await memberCard(i, b, r.ok ? "✉️ Сообщение отправлено." : "❌ Не дошло: у участника закрыты ЛС или его нет на сервере."));
      return true;
    }
    return true;
  }

  /* ============================== фоновые задачи и проверка */

  let ticking = false;
  async function tick() {
    if (ticking || !api.client || !api.client.isReady()) return;
    ticking = true;
    try {
      for (const g of Object.values(D().gw)) if (!g.done && g.ends <= now()) await gwFinish(g, false).catch((e) => api.log("⚠️ Розыгрыш:", e.message));
    } finally { ticking = false; }
  }
  function diagnose() {
    const out = [{ ok: true, text: `Доп. функции (features.js ${FEATURES_VERSION}): розыгрыши, опросы, игры; вопросов викторины: ${QUIZ.length}` }];
    const g = api.guild(), me = g && g.members.me;
    if (me && !me.permissions.has(P.SendPolls)) out.push({ ok: false, text: "Опросы: у роли бота нет права «Создавать опросы»" });
    if (!QUIZ.length) out.push({ ok: false, text: "Викторина: нет вопросов — положите quiz.json рядом с index.js" });
    return out;
  }

  return { version: FEATURES_VERSION, extendCommands, onCommand, onButton, onSelect, onModal, panelRows, diagnose, tick, applyToggles,
    _quizzes: quizzes, _duels: duels, _parseDuration: parseDuration, _checkRoles: checkRoles };
};
