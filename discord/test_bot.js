"use strict";
/*
 * Тесты Discord-бота без интернета: node test_bot.js (нужен npm install).
 * Поднимается поддельный Discord на 127.0.0.1 — REST API и шлюз (WebSocket) — и настоящий discord.js
 * бота подключается к нему: регистрирует команды, получает нажатия кнопок, окна, сообщения, реакции.
 * Проверяются заявки, идеи, автомодерация, команды, ЛС с нейросетью Rai и HTTP для сайта.
 */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");
const { WebSocketServer } = require("ws");
const { PermissionFlagsBits: P } = require("discord.js");

const CONFIG = JSON.parse(fs.readFileSync(path.join(__dirname, "config.json"), "utf8"));
const APP = "1506622482856017970", G = CONFIG.guild_id;
const A = CONFIG.applications, I = CONFIG.ideas;
const OWNER = "1400000000000000001", ALICE = "1400000000000000002", BOB = "1400000000000000003", CAROL = "1400000000000000004";
const GENERAL = "1500000000000000010", LOG = "1500000000000000011";
const BOTROLE = "1500000000000000020", MODROLE = "1500000000000000021", CALLROLE = A.call_role_id;
const KEY = "test-key-123";
let seqId = 1600000000000000000n;
const snow = () => String(++seqId);

/* ---------- поддельный Discord */
const users = {};
for (const [id, name, bot] of [[APP, "RTeam Bot", true], [OWNER, "owner"], [ALICE, "alice"], [BOB, "bob"], [CAROL, "carol"]]) {
  users[id] = { id, username: name, discriminator: "0", global_name: null, avatar: null, bot: !!bot };
}
const everyone = P.ViewChannel | P.SendMessages | P.ReadMessageHistory | P.AddReactions | P.EmbedLinks | P.AttachFiles | P.UseApplicationCommands;
const botPerms = P.ViewChannel | P.SendMessages | P.SendMessagesInThreads | P.EmbedLinks | P.AttachFiles | P.ReadMessageHistory |
  P.AddReactions | P.UseExternalEmojis | P.ManageMessages | P.ManageRoles | P.ModerateMembers;
const roles = [
  { id: G, name: "@everyone", position: 0, permissions: String(everyone) },
  { id: BOTROLE, name: "RTeam Bot", position: 5, permissions: String(botPerms), managed: true },
  { id: MODROLE, name: "Модератор", position: 3, permissions: String(everyone | P.ManageRoles | P.ModerateMembers | P.ManageMessages) },
  { id: CALLROLE, name: "Обзвон", position: 2, permissions: "0" },
].map((r) => ({ color: 0, hoist: false, managed: false, mentionable: false, flags: 0, ...r }));
const members = { [APP]: [BOTROLE], [OWNER]: [], [ALICE]: [], [BOB]: [MODROLE], [CAROL]: [] };
const timeouts = {};
const channels = {};
for (const [id, name] of [[A.panel_channel_id, "заявки"], [A.review_channel_id, "рассмотрение"], [I.input_channel_id, "идеи"],
  [I.vote_channel_id, "голосование"], [GENERAL, "общий"], [LOG, "логи"]]) {
  channels[id] = { id, type: 0, name, guild_id: G, position: 0, permission_overwrites: [], parent_id: null, nsfw: false, topic: null };
}
const messages = new Map(); // id → message
const reqs = [];            // все запросы бота к REST
const callbacks = [];       // ответы на взаимодействия
const tokens = new Map();   // токен взаимодействия → {channelId, componentMessageId, original}
let identifies = 0;

const memberPayload = (id) => ({ user: users[id], roles: members[id], joined_at: "2025-01-01T00:00:00.000Z", deaf: false, mute: false, flags: 0,
  nick: null, avatar: null, pending: false, communication_disabled_until: timeouts[id] || null });
function permsOf(id) {
  if (id === OWNER) return P.Administrator | everyone;
  return [G, ...members[id]].reduce((a, r) => a | BigInt(roles.find((x) => x.id === r).permissions), 0n);
}
const topPos = (id) => Math.max(0, ...members[id].map((r) => roles.find((x) => x.id === r).position));
function makeMessage(channelId, body, extra = {}) {
  const m = {
    id: snow(), channel_id: channelId, author: users[APP], content: body.content || "", embeds: body.embeds || [], components: body.components || [],
    attachments: (body._files || []).map((f) => ({ id: snow(), filename: f, size: 10, url: `http://x/${f}`, proxy_url: `http://x/${f}` })),
    timestamp: new Date().toISOString(), edited_timestamp: null, type: 0, flags: body.flags || 0, mentions: [], mention_roles: [],
    mention_everyone: false, pinned: false, tts: false, ...extra,
  };
  if (channels[channelId]) m.guild_id = G;
  messages.set(m.id, m);
  return m;
}
function parseBody(req, buf) {
  const ct = req.headers["content-type"] || "";
  if (ct.startsWith("multipart/form-data")) {
    const boundary = ct.split("boundary=")[1];
    const parts = buf.toString("latin1").split("--" + boundary);
    let json = {}; const files = [];
    for (const p of parts) {
      const name = (p.match(/name="([^"]+)"/) || [])[1];
      if (name === "payload_json") json = JSON.parse(Buffer.from(p.split("\r\n\r\n").slice(1).join("\r\n\r\n").replace(/\r\n$/, ""), "latin1").toString("utf8"));
      const fn = (p.match(/filename="([^"]+)"/) || [])[1];
      if (fn) files.push(fn);
    }
    json._files = files;
    return json;
  }
  if (!buf.length) return {};
  try { return JSON.parse(buf.toString("utf8")); } catch (e) { return {}; }
}
let PORT = 0, WSPORT = 0;
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==", "base64");
const rest = http.createServer((req, res) => {
  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    const url = new URL(req.url, "http://x");
    const send = (status, obj) => {
      if (obj === undefined) { res.writeHead(status); return res.end(); }
      res.writeHead(status, { "Content-Type": "application/json" }); res.end(JSON.stringify(obj));
    };
    if (url.pathname.startsWith("/rai/")) {
      const f = path.join(__dirname, "..", "support", path.basename(url.pathname));
      if (!fs.existsSync(f)) return send(404, {});
      res.writeHead(200, { "Content-Type": "text/plain" }); return res.end(fs.readFileSync(f));
    }
    if (url.pathname === "/cdn/pic.png") { res.writeHead(200, { "Content-Type": "image/png" }); return res.end(PNG); }
    if (url.pathname.startsWith("/site")) { res.writeHead(200, { "Content-Type": "text/html" }); return res.end("<html><body><h1>RTeam</h1></body></html>"); }
    const p = decodeURIComponent(url.pathname).replace(/^\/api\/v10/, "");
    const body = parseBody(req, Buffer.concat(chunks));
    reqs.push({ method: req.method, path: p, body, query: url.search });
    let m;
    if (req.method === "GET" && p === "/gateway/bot") {
      return send(200, { url: `ws://127.0.0.1:${WSPORT}`, shards: 1, session_start_limit: { total: 1000, remaining: 999, reset_after: 0, max_concurrency: 1 } });
    }
    if ((m = p.match(/^\/applications\/\d+\/guilds\/\d+\/commands$/)) && req.method === "PUT") {
      return send(200, body.map((c) => ({ ...c, id: snow(), application_id: APP, guild_id: G, version: snow(), type: 1 })));
    }
    if ((m = p.match(/^\/channels\/(\d+)$/)) && req.method === "GET") return channels[m[1]] ? send(200, channels[m[1]]) : send(404, { code: 10003, message: "Unknown Channel" });
    if ((m = p.match(/^\/channels\/(\d+)\/messages$/))) {
      if (req.method === "GET") {
        const list = [...messages.values()].filter((x) => x.channel_id === m[1] && !x.deleted).reverse().slice(0, Number(url.searchParams.get("limit") || 50));
        return send(200, list);
      }
      if (m[1] === "1900000000000000004") return send(403, { code: 50007, message: "Cannot send messages to this user" }); // ЛС Carol закрыты
      return send(200, makeMessage(m[1], body));
    }
    if ((m = p.match(/^\/channels\/(\d+)\/messages\/bulk-delete$/))) { body.messages.forEach((id) => { if (messages.get(id)) messages.get(id).deleted = true; }); return send(204); }
    if ((m = p.match(/^\/channels\/(\d+)\/messages\/(\d+)$/))) {
      const msg = messages.get(m[2]);
      if (!msg || msg.deleted) return send(404, { code: 10008, message: "Unknown Message" });
      if (req.method === "GET") return send(200, msg);
      if (req.method === "DELETE") { msg.deleted = true; return send(204); }
      if (req.method === "PATCH") { Object.assign(msg, { content: body.content ?? msg.content, embeds: body.embeds ?? msg.embeds, components: body.components ?? msg.components, edited_timestamp: new Date().toISOString() }); return send(200, msg); }
    }
    if (p.match(/^\/channels\/\d+\/messages\/\d+\/reactions\//)) return send(204);
    if (p.match(/^\/channels\/\d+\/typing$/)) return send(204);
    if (p === "/users/@me/channels" && req.method === "POST") {
      const rid = body.recipient_id;
      return send(200, { id: "19" + rid.slice(2), type: 1, recipients: [users[rid]], last_message_id: null });
    }
    if ((m = p.match(/^\/guilds\/\d+\/members\/(\d+)$/))) {
      if (!members[m[1]]) return send(404, { code: 10007, message: "Unknown Member" });
      if (req.method === "PATCH" && "communication_disabled_until" in body) timeouts[m[1]] = body.communication_disabled_until;
      return send(200, memberPayload(m[1]));
    }
    if ((m = p.match(/^\/guilds\/\d+\/members\/(\d+)\/roles\/(\d+)$/))) {
      const role = roles.find((r) => r.id === m[2]);
      if (!role || role.position >= topPos(APP)) return send(403, { code: 50013, message: "Missing Permissions" });
      if (req.method === "PUT" && !members[m[1]].includes(m[2])) members[m[1]].push(m[2]);
      if (req.method === "DELETE") members[m[1]] = members[m[1]].filter((r) => r !== m[2]);
      return send(204);
    }
    if ((m = p.match(/^\/interactions\/(\d+)\/([^/]+)\/callback$/))) {
      const t = tokens.get(m[2]);
      callbacks.push({ token: m[2], type: body.type, data: body.data || {} });
      if (body.type === 4 || body.type === 5) t.original = makeMessage(t.channelId, body.data || {}, { flags: (body.data || {}).flags || 0, interaction_token: m[2] }).id;
      if (body.type === 6 || body.type === 7) t.original = t.componentMessageId;
      if (body.type === 7) Object.assign(messages.get(t.original), body.data);
      return send(204);
    }
    if ((m = p.match(/^\/webhooks\/\d+\/([^/]+)\/messages\/@original$/))) {
      const t = tokens.get(m[1]);
      const msg = messages.get(t.original);
      if (req.method === "PATCH") Object.assign(msg, { content: body.content ?? msg.content, embeds: body.embeds ?? msg.embeds, components: body.components ?? msg.components });
      return send(200, msg);
    }
    if ((m = p.match(/^\/webhooks\/\d+\/([^/]+)$/)) && req.method === "POST") {
      const t = tokens.get(m[1]);
      return send(200, makeMessage(t.channelId, body, { followup_of: m[1] }));
    }
    console.log("!!! неизвестный запрос", req.method, p);
    return send(404, { code: 0, message: "404: Not Found" });
  });
});

let socket = null, seq = 0;
const wss = new WebSocketServer({ port: 0 });
WSPORT = wss.address().port;
const dispatch = (t, d) => socket && socket.send(JSON.stringify({ op: 0, t, s: ++seq, d }));
wss.on("connection", (ws) => {
  ws.send(JSON.stringify({ op: 10, d: { heartbeat_interval: 30000 } }));
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw);
    if (msg.op === 1) ws.send(JSON.stringify({ op: 11 }));
    if (msg.op === 2) {
      identifies++;
      socket = ws;
      assert.ok(BigInt(msg.d.intents) & (1n << 15n), "нужен Message Content intent");
      dispatch("READY", { v: 10, user: users[APP], guilds: [{ id: G, unavailable: true }], session_id: "s" + identifies,
        resume_gateway_url: `ws://127.0.0.1:${WSPORT}`, application: { id: APP, flags: 0 } });
      dispatch("GUILD_CREATE", {
        id: G, name: "RTeam", owner_id: OWNER, roles, channels: Object.values(channels), members: Object.keys(members).map(memberPayload),
        emojis: [], stickers: [], features: [], member_count: 5, presences: [], voice_states: [], threads: [], stage_instances: [],
        guild_scheduled_events: [], large: false, unavailable: false, joined_at: "2025-01-01T00:00:00.000Z", afk_timeout: 300,
        verification_level: 0, default_message_notifications: 0, explicit_content_filter: 0, mfa_level: 0, system_channel_flags: 0,
        premium_tier: 0, preferred_locale: "ru", nsfw_level: 0, premium_progress_bar_enabled: false, icon: null, splash: null, banner: null,
      });
    }
  });
});

/* ---------- помощники */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, what, ms = 6000) {
  const end = Date.now() + ms;
  for (;;) {
    const v = fn();
    if (v) return v;
    if (Date.now() > end) throw new Error("не дождались: " + what);
    await sleep(20);
  }
}
const live = (ch) => [...messages.values()].filter((m) => m.channel_id === ch && !m.deleted);
const embedText = (m) => (m.embeds || []).map((e) => [e.title, e.description, ...(e.fields || []).map((f) => f.name + " " + f.value)].join(" ")).join(" ");
let itn = 0;
function interact(type, user, channelId, data, message) {
  const token = "tok" + (++itn);
  tokens.set(token, { channelId, componentMessageId: message ? message.id : null, original: null });
  const d = {
    id: snow(), application_id: APP, type, token, version: 1, guild_id: G, channel_id: channelId, channel: channels[channelId],
    member: { ...memberPayload(user), permissions: String(permsOf(user)) }, app_permissions: String(botPerms), locale: "ru", guild_locale: "ru",
    data, entitlements: [], authorizing_integration_owners: { 0: G }, context: 0, attachment_size_limit: 8388608,
  };
  if (message) d.message = message;
  dispatch("INTERACTION_CREATE", d);
  return token;
}
const cb = (token, what) => waitFor(() => callbacks.find((c) => c.token === token), what);
const original = (token) => messages.get(tokens.get(token).original);
const click = (user, msg, customId) => interact(3, user, msg.channel_id, { custom_id: customId, component_type: 2 }, msg);
function modal(user, channelId, customId, values, msg) {
  return interact(5, user, channelId, { custom_id: customId, components: Object.entries(values).map(([k, v]) => ({ type: 1, components: [{ type: 4, custom_id: k, value: v }] })) }, msg);
}
function command(user, channelId, name, options = []) {
  const resolved = { users: {}, members: {} };
  for (const o of options) if (o.type === 6) { resolved.users[o.value] = users[o.value]; if (members[o.value]) { const mp = memberPayload(o.value); delete mp.user; resolved.members[o.value] = { ...mp, permissions: String(permsOf(o.value)) }; } }
  return interact(2, user, channelId, { id: snow(), name, type: 1, options, resolved, guild_id: G });
}
function say(user, channelId, content, extra = {}) {
  const m = { id: snow(), channel_id: channelId, channel_type: 0, guild_id: G, author: users[user], member: { roles: members[user], joined_at: "2025-01-01T00:00:00.000Z", deaf: false, mute: false, flags: 0 },
    content, timestamp: new Date().toISOString(), edited_timestamp: null, tts: false, mention_everyone: false, mentions: [], mention_roles: [],
    attachments: [], embeds: [], pinned: false, type: 0, ...extra };
  messages.set(m.id, { ...m, author: users[user] });
  dispatch("MESSAGE_CREATE", m);
  return m;
}
function dm(user, content) {
  const m = { id: snow(), channel_id: "19" + user.slice(2), channel_type: 1, author: users[user], content, timestamp: new Date().toISOString(), edited_timestamp: null,
    tts: false, mention_everyone: false, mentions: [], mention_roles: [], attachments: [], embeds: [], pinned: false, type: 0 };
  dispatch("MESSAGE_CREATE", m);
  return m;
}
const dmsTo = (user) => [...messages.values()].filter((m) => m.channel_id === "19" + user.slice(2));
const deleted = (m) => waitFor(() => messages.get(m.id) && messages.get(m.id).deleted, "удаление сообщения");

/* ---------- запуск */
(async () => {
  await new Promise((r) => rest.listen(0, "127.0.0.1", r));
  PORT = rest.address().port;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "rteam-bot-"));
  const cfg = JSON.parse(JSON.stringify(CONFIG));
  Object.assign(cfg, { log_channel_id: LOG, public_url: "", rai_base: `http://127.0.0.1:${PORT}/rai/`, site_url: `http://127.0.0.1:${PORT}/site` });
  fs.writeFileSync(path.join(dir, "config.json"), JSON.stringify(cfg));
  fs.writeFileSync(path.join(dir, "secret.json"), JSON.stringify({ token: Buffer.from(APP).toString("base64") + ".fake.token", api_key: KEY }));
  const BOTPORT = 39000 + Math.floor(Math.random() * 2000);
  Object.assign(process.env, { RAI_BOT_TEST: "1", RAI_BOT_DIR: dir, DISCORD_API_BASE: `http://127.0.0.1:${PORT}/api`, PORT: String(BOTPORT), RAI_BOT_LOCK_TICK: "1000" });
  const realFetch = global.fetch; // интернет в тестах не нужен
  global.fetch = (u, o) => (/^http:\/\/127\.0\.0\.1/.test(String(u)) ? realFetch(u, o) : Promise.reject(new Error("offline")));
  const bot = require("./index.js");
  let passed = 0;
  const test = async (name, fn) => { await fn(); passed++; console.log("✓", name); };

  await bot.start();
  await test("подключение: команды, кнопка заявок, подсказка в канале идей", async () => {
    const put = await waitFor(() => reqs.find((r) => r.method === "PUT" && r.path.endsWith("/commands")), "команды");
    assert.deepStrictEqual(put.body.map((c) => c.name).sort(), ["ask", "clear", "idea", "link", "mute", "rules", "setup", "unmute", "unwarn", "warn", "warnings"]);
    assert.ok(put.body.every((c) => c.name_localizations && c.name_localizations.ru));
    await waitFor(() => live(A.panel_channel_id).find((m) => JSON.stringify(m.components).includes("app:start")), "кнопка заявок");
    await waitFor(() => live(I.input_channel_id).find((m) => embedText(m).includes("Предложите идею")), "подсказка идей");
    assert.strictEqual(identifies, 1);
  });
  const panel = live(A.panel_channel_id)[0];

  await test("заявка: два окна вопросов, ответы видит только кандидат, заявка в канале рассмотрения", async () => {
    let t = click(ALICE, panel, "app:start");
    let c = await cb(t, "окно 1");
    assert.strictEqual(c.type, 9);
    assert.strictEqual(c.data.custom_id, "app:p:0");
    assert.strictEqual(c.data.components.length, 5);
    assert.ok(c.data.components.every((r) => r.components[0].label.length <= 45));
    t = modal(ALICE, panel.channel_id, "app:p:0", { q0: "16", q1: "МСК, 3 часа", q2: "Был модератором на сервере 2 месяца", q3: "Хочу помогать серверу и людям", q4: "Удалю сообщение, выдам предупреждение" }, panel);
    c = await cb(t, "ответ на окно 1");
    assert.strictEqual(c.type, 5);
    assert.strictEqual(c.data.flags, 64, "ответ только для кандидата");
    const step = await waitFor(() => original(t).content.includes("Шаг 1 из 2") && original(t), "шаг 1");
    assert.ok(JSON.stringify(step.components).includes("app:next"));
    assert.strictEqual(panel.content, "", "кнопка заявок не изменилась");
    t = click(ALICE, step, "app:next");
    c = await cb(t, "окно 2");
    assert.strictEqual(c.data.custom_id, "app:p:1");
    assert.strictEqual(c.data.components.length, 3);
    t = modal(ALICE, panel.channel_id, "app:p:1", { q5: "Уважение", q6: "alice", q7: "Вечером" }, step);
    c = await cb(t, "ответ на окно 2");
    assert.strictEqual(c.type, 6);
    await waitFor(() => step.content.includes("Заявка #1 отправлена"), "подтверждение");
    const review = await waitFor(() => live(A.review_channel_id)[0], "заявка в канале");
    const txt = embedText(review);
    for (const a of ["16", "МСК, 3 часа", "Уважение", "alice", "Вечером", "Ждёт решения"]) assert.ok(txt.includes(a), a);
    assert.deepStrictEqual(review.components[0].components.map((b) => b.custom_id), ["app:rej:1", "app:call:1"]);
    await waitFor(() => dmsTo(ALICE).find((m) => embedText(m).includes("Заявка #1 отправлена")), "ЛС кандидату");
    assert.strictEqual(bot.data.apps["1"].status, "pending");
  });
  const review1 = live(A.review_channel_id)[0];

  await test("повторная заявка и чужие кнопки", async () => {
    let t = click(ALICE, panel, "app:start");
    let c = await cb(t, "повтор");
    assert.strictEqual(c.type, 4);
    assert.ok(c.data.content.includes("уже на рассмотрении"));
    t = click(ALICE, review1, "app:call:1");
    c = await cb(t, "не админ");
    assert.ok(c.data.content.includes("только администрация"));
  });

  await test("«На обзвон» выдаёт роль и пишет в ЛС, потом «Отклонить» с причиной снимает её", async () => {
    let t = click(BOB, review1, "app:call:1");
    await cb(t, "обзвон");
    await waitFor(() => members[ALICE].includes(CALLROLE), "роль выдана");
    await waitFor(() => embedText(review1).includes("На обзвоне"), "статус обзвона");
    assert.deepStrictEqual(review1.components[0].components.map((b) => b.custom_id), ["app:acc:1", "app:rej:1"]);
    await waitFor(() => dmsTo(ALICE).find((m) => embedText(m).includes("обзвон") && embedText(m).includes("Обзвон")), "ЛС про обзвон");
    t = click(BOB, review1, "app:call:1");
    assert.ok((await cb(t, "повторный обзвон")).data.content.includes("уже обработана"));
    t = click(BOB, review1, "app:rej:1");
    const c = await cb(t, "окно причины");
    assert.strictEqual(c.data.custom_id, "app:rejm:1");
    t = modal(BOB, review1.channel_id, "app:rejm:1", { reason: "Мало опыта" }, review1);
    await cb(t, "отклонение");
    await waitFor(() => !members[ALICE].includes(CALLROLE), "роль снята");
    await waitFor(() => embedText(review1).includes("Отклонена") && embedText(review1).includes("Мало опыта"), "статус отказа");
    assert.deepStrictEqual(review1.components, []);
    await waitFor(() => dmsTo(ALICE).find((m) => embedText(m).includes("Мало опыта")), "ЛС с причиной");
    t = click(ALICE, panel, "app:start");
    assert.ok((await cb(t, "кулдаун")).data.content.includes("Новую можно подать"));
  });

  await test("длинные ответы — файлом, закрытые ЛС, роль выше бота, «Принять»", async () => {
    let t = click(CAROL, panel, "app:start");
    await cb(t, "окно");
    const long = "очень длинный ответ ".repeat(60).slice(0, 1000);
    t = modal(CAROL, panel.channel_id, "app:p:0", { q0: "20", q1: long, q2: long, q3: long, q4: long }, panel);
    await cb(t, "шаг 1");
    const step = await waitFor(() => original(t) && original(t).content.includes("Шаг 1") && original(t), "шаг 1");
    t = click(CAROL, step, "app:next"); await cb(t, "окно 2");
    t = modal(CAROL, panel.channel_id, "app:p:1", { q5: long, q6: "", q7: long }, step);
    await cb(t, "отправка");
    await waitFor(() => step.content.includes("Заявка #2") && step.content.includes("закрыты ЛС"), "подсказка про ЛС");
    const rev = await waitFor(() => live(A.review_channel_id).find((m) => embedText(m).includes("#2")), "заявка 2");
    const e = rev.embeds[0];
    const total = [e.title, e.description, e.footer && e.footer.text, ...e.fields.map((f) => f.name + f.value)].join("").length;
    assert.ok(total <= 6000, "лимит Discord 6000 символов: " + total);
    assert.ok(e.fields.every((f) => f.value.length <= 1024));
    assert.deepStrictEqual(rev.attachments.map((a) => a.filename), ["zayavka-2.txt"]);
    await waitFor(() => embedText(rev).includes("закрыты ЛС"), "пометка о закрытых ЛС");
    roles.find((r) => r.id === CALLROLE).position = 6;
    t = click(BOB, rev, "app:call:2");
    await cb(t, "обзвон без прав");
    const fu = await waitFor(() => [...messages.values()].find((m) => m.followup_of === t), "ошибка роли");
    assert.ok(fu.content.includes("перетащите роль бота"), fu.content);
    assert.strictEqual(bot.data.apps["2"].status, "pending");
    roles.find((r) => r.id === CALLROLE).position = 2;
    t = click(BOB, rev, "app:call:2"); await cb(t, "обзвон");
    await waitFor(() => bot.data.apps["2"].status === "call", "обзвон 2");
    t = click(BOB, rev, "app:acc:2"); await cb(t, "принять");
    await waitFor(() => embedText(rev).includes("Принят"), "принят");
    assert.strictEqual(bot.data.apps["2"].status, "accepted");
  });

  await test("идеи: перенос в голосование, 👍/👎, один голос, кулдаун, картинка, /идея", async () => {
    const m = say(ALICE, I.input_channel_id, "Добавьте ночную тему на сайт, пожалуйста");
    await deleted(m);
    const idea = await waitFor(() => live(I.vote_channel_id).find((x) => embedText(x).includes("ночную тему")), "идея в голосовании");
    assert.ok(idea.embeds[0].title.includes("Идея #1"));
    await waitFor(() => reqs.filter((r) => r.method === "PUT" && r.path.includes(`/messages/${idea.id}/reactions/`)).length === 2, "реакции");
    const reacts = reqs.filter((r) => r.method === "PUT" && r.path.includes(`/messages/${idea.id}/reactions/`)).map((r) => decodeURIComponent(r.path.split("/reactions/")[1].split("/")[0]));
    assert.deepStrictEqual(reacts, ["👍", "👎"]);
    await waitFor(() => live(I.input_channel_id).find((x) => x.content.includes("отправлена на голосование")), "подтверждение");
    const again = say(ALICE, I.input_channel_id, "Ещё одна идея сразу же после первой");
    await deleted(again);
    await waitFor(() => live(I.input_channel_id).find((x) => x.content.includes("следующую идею можно")), "кулдаун");
    const short = say(CAROL, I.input_channel_id, "ок");
    await deleted(short);
    await waitFor(() => live(I.input_channel_id).find((x) => x.content.includes("опишите идею подробнее")), "короткая");
    dispatch("MESSAGE_REACTION_ADD", { user_id: CAROL, channel_id: I.vote_channel_id, message_id: idea.id, guild_id: G, member: memberPayload(CAROL),
      emoji: { id: null, name: "👍" }, type: 0, burst: false, message_author_id: APP });
    const del = await waitFor(() => reqs.find((r) => r.method === "DELETE" && r.path.includes(`/messages/${idea.id}/reactions/`)), "снятие второго голоса");
    assert.ok(decodeURIComponent(del.path).endsWith(`/👎/${CAROL}`), del.path);
    const pic = say(BOB, I.input_channel_id, "Идея с картинкой: новый логотип", { attachments: [{ id: snow(), filename: "pic.png", size: 70, content_type: "image/png", url: `http://127.0.0.1:${PORT}/cdn/pic.png`, proxy_url: `http://127.0.0.1:${PORT}/cdn/pic.png` }] });
    await deleted(pic);
    const withPic = await waitFor(() => live(I.vote_channel_id).find((x) => embedText(x).includes("логотип")), "идея с картинкой");
    assert.deepStrictEqual(withPic.attachments.map((a) => a.filename), ["idea-2.png"]);
    assert.strictEqual(withPic.embeds[0].image.url, "attachment://idea-2.png");
    const t = command(CAROL, GENERAL, "idea", [{ name: "text", type: 3, value: "Сделайте конкурс артов" }]);
    await cb(t, "/идея");
    await waitFor(() => original(t).content.includes("Идея #3"), "ответ /идея");
  });

  await test("фильтр мата: обходы ловятся, обычные слова — нет", async () => {
    const list = bot.cfg.automod.bad_words;
    for (const bad of ["ты сука", "С У К А", "cyka", "х.у.й", "ПИЗДЕЦ", "нахуй", "ебать", "заебал", "долбоёб", "бля", "блять", "пидор", "fuck you", "сууука", "мудак", "п*здец"]) {
      assert.ok(bot.findBadWord(bad, list), "должно ловиться: " + bad);
    }
    for (const ok of ["употребляется", "барсука", "колебание", "страхуйте", "сукно", "мудрый", "оскорблять", "рубля", "корабля", "бляшка", "педикюр", "хлебушек",
      "ребята", "команда", "подписка", "учебник", "небо", "скрипт", "психология", "потребление", "Привет, как дела?", "застрахую машину"]) {
      assert.strictEqual(bot.findBadWord(ok, list), null, "не должно ловиться: " + ok);
    }
  });

  await test("ссылки: скам и реклама ловятся, обычные — нет", async () => {
    const chk = (t) => bot.automodCheck({ content: t, authorId: "x" }, { noHistory: true });
    assert.strictEqual(chk("Free nitro https://dlscord-gift.com/xyz").rule, "scam");
    assert.strictEqual(chk("@everyone раздача https://steamcommunlty.ru/gift").rule, "scam");
    assert.strictEqual(chk("заходите https://discord.gg/abc123").rule, "invites");
    assert.strictEqual(chk("гайд https://discord.js.org/docs"), null);
    assert.strictEqual(chk("видео https://youtube.com/watch?v=1"), null);
    assert.strictEqual(chk("база https://steamdb.info/app/1"), null);
    assert.strictEqual(chk("<@1> <@2> <@3> <@4> <@5> привет").rule, "mentions");
    assert.strictEqual(chk("ПРИВЕТ ВСЕМ КАК У ВАС ДЕЛА").rule, "caps");
    assert.strictEqual(chk("НЛО"), null);
  });

  await test("автомодерация в чате: удаление, предупреждение, ЛС, лог, мут, флуд, правка, модераторов не трогает", async () => {
    const m = say(ALICE, GENERAL, "ну ты и сука");
    await deleted(m);
    await waitFor(() => live(GENERAL).find((x) => x.content.includes("мат и оскорбления") && x.content.includes("Предупреждение 1")), "уведомление");
    await waitFor(() => dmsTo(ALICE).find((x) => embedText(x).includes("Сообщение удалено")), "ЛС о нарушении");
    await waitFor(() => live(LOG).find((x) => embedText(x).includes("badwords")), "лог");
    const scam = say(CAROL, GENERAL, "Free nitro https://dlscord-gift.com/xyz");
    await deleted(scam);
    await waitFor(() => timeouts[CAROL], "мут за скам");
    assert.ok(new Date(timeouts[CAROL]) - Date.now() > 55 * 60000);
    timeouts[CAROL] = null;
    const caps = say(BOB, GENERAL, "ПРИВЕТ ВСЕМ МОДЕРАТОРАМ СЕРВЕРА");
    const modSwear = say(BOB, GENERAL, "блять, опять сервер упал");
    await sleep(300);
    assert.ok(!messages.get(caps.id).deleted && !messages.get(modSwear.id).deleted, "модератора не трогаем");
    const flood = [];
    for (let k = 0; k < 6; k++) flood.push(say(CAROL, GENERAL, "спам " + k));
    await waitFor(() => reqs.find((r) => r.path.endsWith("/bulk-delete")), "чистка флуда");
    await waitFor(() => timeouts[CAROL], "мут за флуд");
    const edited = say(ALICE, GENERAL, "нормальное сообщение");
    await sleep(100);
    dispatch("MESSAGE_UPDATE", { ...edited, author: users[ALICE], content: "уже не нормальное, пиздец", edited_timestamp: new Date().toISOString() });
    await deleted(edited);
    assert.strictEqual(bot.data.warnings[ALICE].length, 2);
  });

  await test("команды модерации: /пред с мутом на 3-м, /преды, /снять-пред, /мут, /размут, /очистить, права", async () => {
    timeouts[ALICE] = null;
    let t = command(BOB, GENERAL, "warn", [{ name: "user", type: 6, value: ALICE }, { name: "reason", type: 3, value: "флуд в общем чате" }]);
    let c = await cb(t, "/пред");
    assert.strictEqual(c.type, 4);
    assert.ok(c.data.content.includes("(3)") && c.data.content.includes("Мут на 10 мин"), c.data.content);
    await waitFor(() => timeouts[ALICE], "мут на 3-м");
    t = command(BOB, GENERAL, "warnings", [{ name: "user", type: 6, value: ALICE }]);
    c = await cb(t, "/преды");
    assert.ok(c.data.content.includes("(3)") && c.data.content.includes("флуд в общем чате"));
    assert.strictEqual(c.data.flags, 64);
    t = command(BOB, GENERAL, "unwarn", [{ name: "user", type: 6, value: ALICE }]);
    assert.ok((await cb(t, "/снять-пред")).data.content.includes(": 2."));
    t = command(BOB, GENERAL, "unmute", [{ name: "user", type: 6, value: ALICE }]);
    await cb(t, "/размут");
    await waitFor(() => timeouts[ALICE] === null, "мут снят");
    t = command(BOB, GENERAL, "mute", [{ name: "user", type: 6, value: ALICE }, { name: "minutes", type: 4, value: 15 }]);
    assert.ok((await cb(t, "/мут")).data.content.includes("15 мин"));
    t = command(BOB, GENERAL, "warn", [{ name: "user", type: 6, value: OWNER }, { name: "reason", type: 3, value: "x" }]);
    assert.ok((await cb(t, "владелец")).data.content.startsWith("Нельзя"));
    t = command(ALICE, GENERAL, "warn", [{ name: "user", type: 6, value: CAROL }, { name: "reason", type: 3, value: "x" }]);
    assert.ok((await cb(t, "без прав")).data.content.includes("для модераторов"));
    t = command(BOB, GENERAL, "clear", [{ name: "count", type: 4, value: 3 }]);
    await cb(t, "/очистить");
    await waitFor(() => original(t).content.includes("Удалено сообщений: 3"), "очистка");
  });

  await test("правила, проверка настроек, /спросить, /привязать", async () => {
    let t = command(ALICE, GENERAL, "rules");
    let c = await cb(t, "/правила");
    assert.strictEqual(c.data.flags, 64);
    assert.ok(c.data.embeds[0].description.includes("**10.**"));
    t = command(ALICE, GENERAL, "setup", [{ name: "check", type: 1, options: [] }]);
    assert.ok((await cb(t, "setup без прав")).data.content.includes("для администрации"));
    t = command(OWNER, GENERAL, "setup", [{ name: "rules", type: 1, options: [] }]);
    await cb(t, "setup rules");
    await waitFor(() => live(GENERAL).find((x) => embedText(x).includes("Правила сервера")), "правила в канале");
    t = command(OWNER, GENERAL, "setup", [{ name: "check", type: 1, options: [] }]);
    await cb(t, "setup check");
    const rep = await waitFor(() => original(t).content.includes("Сервер") && original(t).content, "отчёт");
    assert.ok(!rep.includes("❌"), rep);
    t = command(ALICE, GENERAL, "ask", [{ name: "question", type: 3, value: "как подать заявку в команду" }]);
    await cb(t, "/спросить");
    await waitFor(() => /заявк/i.test(original(t).content), "ответ Rai");
    t = command(ALICE, GENERAL, "link");
    c = await cb(t, "/привязать");
    assert.ok(c.data.components[0].components[0].url.endsWith("/discord_auth.php?mode=link"));
  });

  await test("ЛС: нейросеть Rai отвечает, зовёт поддержку, приветствие", async () => {
    dm(ALICE, "как привязать телеграм к аккаунту");
    await waitFor(() => dmsTo(ALICE).find((x) => /telegram|телеграм/i.test(x.content)), "ответ про Telegram", 15000);
    await sleep(1600);
    dm(ALICE, "позовите живого человека");
    const h = await waitFor(() => dmsTo(ALICE).find((x) => x.content.includes("Живой сотрудник")), "передача человеку");
    assert.ok(h.components[0].components[0].url.includes("/support.php?new_ticket=1&text="));
    await sleep(1600);
    dm(ALICE, "привет");
    await waitFor(() => dmsTo(ALICE).find((x) => x.content.startsWith("Привет! Я Rai")), "приветствие");
    assert.ok(!dmsTo(ALICE).some((x) => /тикет/i.test(x.content)), "в ЛС нет слов про тикеты");
  });

  await test("HTTP для сайта: /dm с ключом, без ключа, закрытые ЛС, /status", async () => {
    const base = `http://127.0.0.1:${process.env.PORT}`;
    const post = (p, body, key) => realFetch(base + p, { method: "POST", headers: { "Content-Type": "application/json", ...(key ? { "X-Api-Key": key } : {}) }, body: JSON.stringify(body) });
    assert.strictEqual((await (await realFetch(base + "/")).json()).online, true);
    assert.strictEqual((await post("/dm", { user_id: ALICE, text: "x" })).status, 403);
    assert.strictEqual((await post("/dm", { user_id: ALICE, text: "x" }, "wrong")).status, 403);
    let r = await post("/dm", { user_id: ALICE, title: "🔐 Код входа", text: "Ваш код: **123456**", button: { label: "Открыть сайт", url: "https://rteam.info/" } }, KEY);
    assert.deepStrictEqual(await r.json(), { ok: true });
    const got = dmsTo(ALICE).find((x) => embedText(x).includes("123456"));
    assert.ok(got && got.components[0].components[0].url === "https://rteam.info/");
    r = await post("/dm", { user_id: CAROL, text: "код" }, KEY);
    assert.deepStrictEqual(await r.json(), { ok: false, error: "dm_closed" });
    r = await realFetch(base + "/status", { headers: { Authorization: "Bearer " + KEY } });
    const st = await r.json();
    assert.strictEqual(st.online, true);
    assert.ok(st.checks.length > 5 && st.checks.every((x) => x.ok), JSON.stringify(st.checks));
  });

  await test("вторая копия (как в Plesk/Passenger) ждёт в резерве и подхватывает работу", async () => {
    const child = spawn(process.execPath, [path.join(__dirname, "index.js")], {
      env: { ...process.env, RAI_BOT_TEST: "", PORT: String(Number(process.env.PORT) + 1) }, stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    child.stdout.on("data", (d) => { out += d; });
    child.stderr.on("data", (d) => { out += d; });
    await waitFor(() => out.includes("в резерве"), "резерв", 8000);
    assert.strictEqual(identifies, 1, "вторая копия не подключается к Discord");
    const before = live(A.panel_channel_id).length;
    await bot.stop();
    await waitFor(() => identifies === 2, "подхватила работу", 12000);
    await waitFor(() => out.includes("в сети"), "в сети", 8000);
    await sleep(500);
    assert.strictEqual(live(A.panel_channel_id).length, before, "кнопка заявок не задвоилась");
    child.kill("SIGTERM");
    await new Promise((r) => child.on("exit", r));
  });

  console.log(`\nВсе тесты прошли: ${passed}`);
  rest.close(); wss.close();
  process.exit(0);
})().catch((e) => { console.error("✗", e.stack || e.message); process.exit(1); });
