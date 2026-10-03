"use strict";
/*
 * Discord-бот RTeam (rteam.info) — весь бот в одном файле.
 *
 *  • Автомодерация: мат и оскорбления, реклама серверов, скам-ссылки, флуд, повторы, капс, массовые упоминания.
 *    Сообщение удаляется, участник получает предупреждение; 3 / 5 / 7 предупреждений — мут (тайм-аут).
 *  • Заявки в модераторы: кнопка в канале заявок → вопросы в окне, которое видит только кандидат →
 *    заявка с ответами в канале рассмотрения с кнопками «Отклонить» и «На обзвон» (выдаёт роль) → «Принять».
 *    Решение приходит кандидату в ЛС.
 *  • Идеи: сообщение в канале идей бот переносит в канал голосования и ставит 👍 и 👎 (один голос на человека).
 *  • Правила: /правила и сообщение с правилами в канале.
 *  • ЛС: бот отвечает на вопросы нейросетью Rai (та же, что в поддержке сайта, грузится с GitHub),
 *    присылает коды входа на rteam.info и уведомления сайта.
 *  • HTTP для сайта: POST /dm — написать участнику в ЛС (код входа, уведомление), GET /status — проверка.
 *
 * Файлы рядом: config.json — настройки и ID каналов, secret.json — токен и ключ для сайта (не выкладывать!),
 * data.json — заявки, предупреждения, идеи (создаётся сам). Запуск: npm install, затем node index.js.
 * В Plesk бот работает как Node.js-приложение (Passenger): он слушает HTTP-порт, а вторая копия, если Passenger
 * её запустит, не подключается к Discord (bot.lock), чтобы не было двойных ответов.
 */

const fs = require("fs");
const path = require("path");
const http = require("http");
const crypto = require("crypto");
const vm = require("vm");
const {
  Client, GatewayIntentBits, Partials, Events, PermissionFlagsBits: P, MessageFlags, REST, Routes,
} = require("discord.js");

const BOT_VERSION = "2026.10.03"; // сайт сравнивает: старая версия на сервере — «Проверить всё» подскажет обновить index.js
const DIR = process.env.RAI_BOT_DIR || __dirname;
const API_BASE = process.env.DISCORD_API_BASE || ""; // только для тестов: подменный Discord
const EPH = MessageFlags.Ephemeral;

/* ============================== файлы и настройки */

function readJson(file, def) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch (e) {
    if (e.code !== "ENOENT") log(`⚠️ Не удалось прочитать ${path.basename(file)}: ${e.message}`);
    return def;
  }
}
function writeJsonAtomic(file, obj) {
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 1));
  fs.renameSync(tmp, file);
}
function log(...a) { console.log(new Date().toISOString().replace("T", " ").slice(0, 19), ...a); }

const DEFAULTS = {
  guild_id: "", client_id: "", site_url: "https://rteam.info", public_url: "", port: 3000,
  rai_base: "https://raw.githubusercontent.com/rteaminfo1-source/rai/claude/awesome-mendel-tzoqsf/support/",
  log_channel_id: "", staff_role_ids: [],
  applications: {
    enabled: true, panel_channel_id: "", review_channel_id: "", call_role_id: "", accept_role_id: "",
    remove_call_role_on_accept: true, reviewer_role_ids: [], ping_role_ids: [], cooldown_hours: 24,
    title: "Заявка на модератора", panel_title: "🛡️ Набор в модераторы", panel_text: "", questions: [],
  },
  ideas: {
    enabled: true, input_channel_id: "", vote_channel_id: "", min_length: 10, max_length: 1800,
    cooldown_minutes: 3, like: "👍", dislike: "👎", one_vote: true, info_message: true,
  },
  rules: { channel_id: "", title: "📜 Правила сервера", items: [], footer: "" },
  automod: {
    enabled: true, exempt_role_ids: [], exempt_channel_ids: [],
    rules: { scam: true, badwords: true, invites: true, links: false, mentions: true, flood: true, duplicates: true, caps: true, emoji: true },
    bad_words: [], allowed_domains: [], allowed_invites: [],
    max_mentions: 5, caps_percent: 70, caps_min_letters: 12, max_emojis: 15,
    flood_messages: 6, flood_seconds: 8, duplicate_count: 3, duplicate_seconds: 60,
    flood_timeout_minutes: 5, scam_timeout_minutes: 60,
    warn_timeouts: [{ warns: 3, minutes: 10 }, { warns: 5, minutes: 60 }, { warns: 7, minutes: 1440 }],
    warn_expire_days: 30,
  },
  dm: { enabled: true, rai: true },
  panel: { role_ids: [], channel_id: "", announce_channels: [], call_voice_channel_ids: [] },
  levels: {
    enabled: true, xp_min: 15, xp_max: 25, cooldown_seconds: 60, voice_xp_per_minute: 10, voice_min_members: 2,
    announce: true, announce_channel_id: "", voice_announce_channel_id: "", ignore_channel_ids: [], roles: {},
  },
};

function loadConfig() {
  const file = path.join(DIR, "config.json");
  const c = readJson(file, null);
  if (!c) throw new Error(`Нет файла ${file} (или в нём ошибка JSON)`);
  const out = Object.assign({}, DEFAULTS, c);
  for (const k of ["applications", "ideas", "rules", "automod", "dm", "panel", "levels"]) out[k] = Object.assign({}, DEFAULTS[k], c[k] || {});
  out.automod.rules = Object.assign({}, DEFAULTS.automod.rules, (c.automod || {}).rules || {});
  const s = readJson(path.join(DIR, "secret.json"), {}) || {};
  out.token = String(process.env.DISCORD_TOKEN || s.token || "").trim();
  out.api_key = String(process.env.BOT_API_KEY || s.api_key || "").trim();
  if (!out.client_id && out.token) out.client_id = idFromToken(out.token);
  out.site_url = String(out.site_url || "").replace(/\/+$/, "");
  out.public_url = String(out.public_url || "").replace(/\/+$/, "");
  return out;
}
function idFromToken(t) {
  try { return Buffer.from(String(t).split(".")[0], "base64").toString("utf8").replace(/\D/g, ""); } catch (e) { return ""; }
}

let cfg = loadConfig();
const A = () => cfg.applications, I = () => cfg.ideas, AM = () => cfg.automod, PN = () => cfg.panel, LV = () => cfg.levels;

const DATA_FILE = path.join(DIR, "data.json");
const EMPTY_DATA = () => ({ apps: {}, app_seq: 0, drafts: {}, warnings: {}, ideas: {}, idea_seq: 0, messages: {}, levels: {}, days: {} });
let data = loadData();
function loadData() { return Object.assign(EMPTY_DATA(), readJson(DATA_FILE, {}) || {}); }
let saveTimer = null;
function save() { clearTimeout(saveTimer); saveTimer = setTimeout(saveNow, 250); }
function saveNow() {
  clearTimeout(saveTimer); saveTimer = null;
  try { writeJsonAtomic(DATA_FILE, data); } catch (e) { log("❌ Не удалось сохранить data.json:", e.message); }
}

/* ============================== мелочи */

const now = () => Date.now();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const cut = (s, n) => { s = String(s == null ? "" : s); return s.length > n ? s.slice(0, Math.max(0, n - 1)) + "…" : s; };
const isId = (s) => /^\d{15,22}$/.test(String(s || ""));
const ts = (ms, f = "R") => `<t:${Math.floor(ms / 1000)}:${f}>`;
const sha1 = (s) => crypto.createHash("sha1").update(s).digest("hex");
const ids = (arr) => (Array.isArray(arr) ? arr : []).map(String).filter(isId);
function plural(n, one, few, many) {
  const a = Math.abs(n) % 100, b = a % 10;
  return a > 10 && a < 20 ? many : b === 1 ? one : b >= 2 && b <= 4 ? few : many;
}
function fmtMin(m) {
  if (m % 1440 === 0) return `${m / 1440} ${plural(m / 1440, "день", "дня", "дней")}`;
  if (m % 60 === 0) return `${m / 60} ${plural(m / 60, "час", "часа", "часов")}`;
  return `${m} мин`;
}
function withTimeout(p, ms) {
  return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), ms))]);
}
const COLORS = { blurple: 0x5865f2, yellow: 0xf5a524, green: 0x22c55e, red: 0xef4444, gray: 0x6b7280, gold: 0xf5c518 };
const button = (style, label, custom_id, emoji) => ({ type: 2, style, label, custom_id, ...(emoji ? { emoji: { name: emoji } } : {}) });
const linkButton = (label, url) => ({ type: 2, style: 5, label, url });
const row = (...components) => ({ type: 1, components });

const PERM_NAMES = {
  ViewChannel: "Просматривать каналы", SendMessages: "Отправлять сообщения", EmbedLinks: "Встраивать ссылки",
  AttachFiles: "Прикреплять файлы", ReadMessageHistory: "Читать историю сообщений", ManageMessages: "Управлять сообщениями",
  AddReactions: "Добавлять реакции", ManageRoles: "Управлять ролями",
  ModerateMembers: "Отправлять участников подумать о своём поведении (тайм-аут)",
  MoveMembers: "Перемещать участников", MentionEveryone: "Упоминание @everyone, @here и всех ролей",
};
const permName = (flag) => PERM_NAMES[Object.keys(P).find((k) => P[k] === flag)] || String(flag);
const INVITE_PERMS = [P.ViewChannel, P.SendMessages, P.SendMessagesInThreads, P.EmbedLinks, P.AttachFiles, P.ReadMessageHistory,
  P.AddReactions, P.UseExternalEmojis, P.ManageMessages, P.ManageRoles, P.ModerateMembers, P.MoveMembers, P.MentionEveryone].reduce((a, b) => a | b, 0n);
const inviteUrl = () => `https://discord.com/oauth2/authorize?client_id=${cfg.client_id}&scope=bot+applications.commands` +
  `&permissions=${INVITE_PERMS}${isId(cfg.guild_id) ? `&guild_id=${cfg.guild_id}&disable_guild_select=true` : ""}`;

/* ============================== Discord: клиент и REST */

let client = null;
let mode = "starting"; // active — подключён к Discord, standby — работает другая копия, offline — нет токена
let lastError = "";
const rest = new REST({ version: "10", ...(API_BASE ? { api: API_BASE } : {}) });
if (cfg.token) rest.setToken(cfg.token);

const guild = () => (client && client.guilds.cache.get(cfg.guild_id)) || null;
async function chan(id) {
  if (!client || !isId(id)) return null;
  return client.channels.cache.get(id) || client.channels.fetch(id).catch(() => null);
}

/* Написать участнику в ЛС (работает и без подключения к шлюзу — через REST) */
const dmChannels = new Map();
async function dmUser(userId, body) {
  if (!isId(userId) || !cfg.token) return { ok: false, error: "bad_user" };
  try {
    let chId = dmChannels.get(userId);
    if (!chId) {
      chId = (await rest.post(Routes.userChannels(), { body: { recipient_id: String(userId) } })).id;
      dmChannels.set(userId, chId);
    }
    const msg = await rest.post(Routes.channelMessages(chId), { body: { allowed_mentions: { parse: [] }, ...body } });
    return { ok: true, id: msg.id };
  } catch (e) {
    const code = e.code || e.status;
    const error = code === 50007 ? "dm_closed" : code === 10013 ? "unknown_user" : e.status === 401 ? "bad_token" : "discord_error";
    if (error === "discord_error") log(`⚠️ ЛС ${userId}: ${e.message}`);
    return { ok: false, error, message: e.message };
  }
}

async function modLog(embed) {
  const ch = await chan(cfg.log_channel_id);
  if (!ch) return;
  await ch.send({ embeds: [Object.assign({ timestamp: new Date().toISOString() }, embed)], allowedMentions: { parse: [] } })
    .catch((e) => log("⚠️ Лог:", e.message));
}

/* ============================== права в командах и кнопках */

const hasPerm = (i, flag) => !!(i.memberPermissions && i.memberPermissions.has(flag));
function memberRoleIds(m) {
  if (!m) return [];
  if (m.roles && m.roles.cache) return [...m.roles.cache.keys()];
  return Array.isArray(m.roles) ? m.roles : [];
}
const isStaff = (i) => hasPerm(i, P.Administrator) || hasPerm(i, P.ManageGuild) ||
  ids(cfg.staff_role_ids).some((r) => memberRoleIds(i.member).includes(r));
const isReviewer = (i) => isStaff(i) || hasPerm(i, P.ManageRoles) ||
  ids([...A().reviewer_role_ids, ...PN().role_ids]).some((r) => memberRoleIds(i.member).includes(r));
// Админ-панель бота (/админ): администраторы сервера и роли из panel.role_ids
const isPanel = (i) => hasPerm(i, P.Administrator) || ids(PN().role_ids).some((r) => memberRoleIds(i.member).includes(r));
function canModerate(mod, target) {
  const g = target.guild;
  if (target.id === g.ownerId || target.user.bot) return false;
  if (mod.id === g.ownerId) return true;
  return mod.roles.highest.position > target.roles.highest.position;
}

/* ============================== автомодерация */

// Латиница и цифры, похожие на русские буквы: «cyka», «x y й», «6ля»
const LOOKALIKE = { a: "а", b: "в", c: "с", e: "е", h: "н", k: "к", m: "м", o: "о", p: "р", t: "т", x: "х", y: "у", u: "и", "3": "з", "0": "о", "6": "б", "@": "а" };
function filterVariants(text) {
  let base = String(text || "").toLowerCase().replace(/ё/g, "е");
  base = base.replace(/<a?:\w+:\d+>|<[@#][!&]?\d+>|https?:\/\/\S+/g, " ");
  // «х у й», «х.у.й» → «хуй»
  base = base.replace(/(?<![\p{L}\d@])(?:[\p{L}\d@][\s.*_\-]+){2,}[\p{L}\d@](?![\p{L}\d@])/gu, (m) => m.replace(/[\s.*_\-]+/g, ""));
  const plain = base.replace(/(?<=\p{L})[*_.\-]+(?=\p{L})/gu, "");          // «пи-дец» → «пидец»
  const starred = base.replace(/(?<=[\p{L}*])[_.\-]+(?=[\p{L}*])/gu, "");    // «п*здец»: звёздочка — любая буква
  const out = [];
  for (const b of [plain, starred]) {
    const mapped = b.replace(/[a-z0-9@]/g, (ch) => LOOKALIKE[ch] || ch);
    const collapse = (x) => x.replace(/(\p{L})\1+/gu, "$1");
    out.push(b, mapped, collapse(b), collapse(mapped));
  }
  return [...new Set(out)];
}
// tok похоже на s начиная с позиции at; «*» в tok — любая буква, но звёздочек не больше половины
function starMatch(tok, s, at) {
  if (at + s.length > tok.length) return false;
  let stars = 0;
  for (let k = 0; k < s.length; k++) {
    const c = tok[at + k];
    if (c === "*") stars++; else if (c !== s[k]) return false;
  }
  return stars * 2 <= s.length;
}
// «стем» — слово начинается с него, «*стем» — где угодно в слове, «=слово» — только целое слово
function findBadWord(text, list) {
  const stems = (list || []).map((w) => String(w).toLowerCase().replace(/ё/g, "е").trim()).filter(Boolean);
  if (!stems.length) return null;
  for (const v of filterVariants(text)) {
    for (let tok of v.split(/[^\p{L}\d*]+/u)) {
      tok = tok.replace(/^\*+|\*+$/g, "");
      if (!tok) continue;
      for (const s of stems) {
        const w = s.replace(/^[*=]/, "");
        if (!w) continue;
        let hit = false;
        if (s[0] === "*") { for (let at = 0; at + w.length <= tok.length && !hit; at++) hit = starMatch(tok, w, at); }
        else if (s[0] === "=") hit = tok.length === w.length && starMatch(tok, w, 0);
        else hit = starMatch(tok, w, 0);
        if (hit) return w;
      }
    }
  }
  return null;
}

const OFFICIAL = ["discord.com", "discord.gg", "discordapp.com", "discordapp.net", "discord.media", "discord.gift", "discord.new",
  "discordstatus.com", "discord.dev", "dis.gd", "steampowered.com", "steamcommunity.com", "steamstatic.com"];
const hostIs = (host, list) => list.some((d) => { d = String(d).toLowerCase().replace(/^www\./, ""); return host === d || host.endsWith("." + d); });
function linksOf(text) {
  const out = [];
  for (const m of String(text || "").matchAll(/https?:\/\/[^\s<>()\]]+/gi)) {
    try { out.push({ url: m[0], host: new URL(m[0]).hostname.toLowerCase().replace(/^www\./, "") }); } catch (e) { /* не ссылка */ }
  }
  return out;
}
const INVITE_RE = /(?:discord(?:app)?\.com\/invite|discord\.gg|discord\.me|dsc\.gg|invite\.gg)\/([\w-]+)/gi;
const SCAM_WORDS = /nitro|нитро|free|бесплатн|gift|подар|раздач|giveaway|скин|skins?\b|trade|airdrop/i;

function isScam(text, links, allowed) {
  const bad = links.filter((l) => !hostIs(l.host, OFFICIAL) && !hostIs(l.host, allowed));
  if (!bad.length) return false;
  for (const l of bad) {
    const skeleton = l.host.replace(/[1l|!]/g, "i").replace(/0/g, "o").replace(/[^a-z]/g, "");
    const lookalike = /d.?scord|disc.?rd|dicsord|discrod|disocrd/.test(skeleton);
    if (lookalike && !l.host.includes("discord")) return true;          // dlscord.com, d1scord.gift…
    if ((l.host.includes("discord") || /st[e3][a4]m|stearn/.test(l.host)) && SCAM_WORDS.test(text)) return true;
  }
  if (/@(everyone|here)/.test(text)) return true;                        // «@everyone бесплатный нитро: ссылка»
  return /nitro|нитро/i.test(text) && /free|бесплатн|раздач|gift|подар/i.test(text);
}

const recent = new Map(); // кто что писал недавно: для флуда и повторов
/* Проверка сообщения. msg = {id, authorId, channelId, content, t}. Возвращает нарушение или null. */
function automodCheck(msg, opts = {}) {
  const am = AM(), on = am.rules, text = String(msg.content || "");
  const t = msg.t || now();
  const links = linksOf(text);
  const allowed = am.allowed_domains || [];

  if (on.scam && isScam(text, links, allowed)) {
    return { rule: "scam", reason: "подозрительная ссылка (похоже на скам)", warn: true, timeout: am.scam_timeout_minutes };
  }
  if (on.badwords) {
    const w = findBadWord(text, am.bad_words);
    if (w) return { rule: "badwords", reason: "мат и оскорбления запрещены", warn: true, word: w };
  }
  if (on.invites) {
    const okInv = (am.allowed_invites || []).map((s) => String(s).toLowerCase());
    for (const m of text.matchAll(INVITE_RE)) {
      if (!okInv.includes(m[1].toLowerCase())) return { rule: "invites", reason: "реклама других серверов запрещена", warn: true };
    }
  }
  if (on.links && links.some((l) => !hostIs(l.host, allowed) && !hostIs(l.host, OFFICIAL))) {
    return { rule: "links", reason: "ссылки в этом чате запрещены", warn: false };
  }
  const mentions = (text.match(/<@[!&]?\d+>/g) || []).length;
  if (on.mentions && am.max_mentions > 0 && mentions >= am.max_mentions) {
    return { rule: "mentions", reason: "массовые упоминания запрещены", warn: true };
  }

  // флуд и повторы — по истории участника
  if (!opts.noHistory) {
    const key = msg.authorId;
    const norm = text.toLowerCase().replace(/\s+/g, " ").trim();
    const list = (recent.get(key) || []).filter((r) => t - r.t < 120000);
    list.push({ id: msg.id, ch: msg.channelId, t, norm });
    recent.set(key, list.slice(-30));
    if (on.flood && am.flood_messages > 0) {
      const win = list.filter((r) => t - r.t < am.flood_seconds * 1000);
      if (win.length >= am.flood_messages) {
        recent.set(key, []);
        return { rule: "flood", reason: "флуд запрещён", warn: true, timeout: am.flood_timeout_minutes, purge: win.map((r) => ({ id: r.id, ch: r.ch })) };
      }
    }
    if (on.duplicates && norm && am.duplicate_count > 1) {
      const same = list.filter((r) => r.norm === norm && t - r.t < am.duplicate_seconds * 1000);
      if (same.length >= am.duplicate_count) {
        recent.set(key, list.filter((r) => r.norm !== norm));
        return { rule: "duplicates", reason: "не повторяйте одно и то же сообщение", warn: true, purge: same.map((r) => ({ id: r.id, ch: r.ch })) };
      }
    }
  }

  const plain = text.replace(/<a?:\w+:\d+>|<[@#][!&]?\d+>|https?:\/\/\S+/g, "");
  const letters = plain.match(/\p{L}/gu) || [];
  if (on.caps && letters.length >= am.caps_min_letters) {
    const upper = letters.filter((ch) => ch !== ch.toLowerCase()).length;
    if (upper / letters.length >= am.caps_percent / 100) return { rule: "caps", reason: "не пишите капсом", warn: false };
  }
  const emojis = (text.match(/<a?:\w+:\d+>/g) || []).length + (plain.match(/\p{Extended_Pictographic}/gu) || []).length;
  if (on.emoji && am.max_emojis > 0 && emojis >= am.max_emojis) return { rule: "emoji", reason: "слишком много эмодзи", warn: false };
  return null;
}

function activeWarnings(uid) {
  const days = Number(AM().warn_expire_days) || 0;
  const list = data.warnings[uid] || [];
  return days > 0 ? list.filter((w) => now() - w.t < days * 864e5) : list;
}
function addWarning(uid, reason, by) {
  const list = (data.warnings[uid] = data.warnings[uid] || []);
  list.push({ id: crypto.randomBytes(3).toString("hex"), reason: cut(reason, 300), by, t: now() });
  if (list.length > 50) list.splice(0, list.length - 50);
  save();
  return activeWarnings(uid).length;
}
function warnSteps() {
  return (AM().warn_timeouts || []).filter((s) => s.warns > 0 && s.minutes > 0).sort((a, b) => a.warns - b.warns);
}
function timeoutFor(count) {
  const steps = warnSteps();
  if (!steps.length) return 0;
  const hit = steps.find((s) => s.warns === count);
  if (hit) return hit.minutes;
  const last = steps[steps.length - 1];
  return count > last.warns ? last.minutes : 0;
}
function nextStepText(count) {
  const s = warnSteps().find((x) => x.warns > count);
  return s ? `на ${s.warns}-м — мут на ${fmtMin(s.minutes)}` : "";
}
async function timeoutMember(member, minutes, reason) {
  if (!member || !minutes) return false;
  try {
    if (!member.moderatable) return false;
    await member.timeout(Math.min(minutes, 40320) * 60000, cut(reason, 400));
    return true;
  } catch (e) { log("⚠️ Мут не выдан:", e.message); return false; }
}

const noticeAt = new Map(), dmAt = new Map();
function isExempt(m) {
  const am = AM();
  if (ids(am.exempt_channel_ids).includes(m.channelId) || ids(am.exempt_channel_ids).includes(m.channel?.parentId)) return true;
  const mem = m.member;
  if (!mem) return false;
  if (mem.permissions && (mem.permissions.has(P.Administrator) || mem.permissions.has(P.ManageMessages))) return true;
  return ids([...am.exempt_role_ids, ...cfg.staff_role_ids]).some((r) => mem.roles.cache.has(r));
}

async function applyVerdict(m, v) {
  const uid = m.author.id;
  await m.delete().catch(() => {});
  if (v.purge && v.purge.length) {
    const byCh = new Map();
    for (const p of v.purge) if (p.id !== m.id) byCh.set(p.ch, [...(byCh.get(p.ch) || []), p.id]);
    for (const [chId, list] of byCh) {
      const ch = await chan(chId);
      if (!ch) continue;
      if (list.length === 1) await ch.messages.delete(list[0]).catch(() => {});
      else await ch.bulkDelete(list, true).catch(() => {});
    }
  }
  let count = 0, minutes = v.timeout || 0;
  if (v.warn) { count = addWarning(uid, `Автомодерация: ${v.reason}`, "auto"); minutes = Math.max(minutes, timeoutFor(count)); }
  const muted = minutes ? await timeoutMember(m.member, minutes, `Автомодерация: ${v.reason}`) : false;

  const tail = v.warn ? ` Предупреждение ${count}${nextStepText(count) ? ` (${nextStepText(count)})` : ""}.` : "";
  if (now() - (noticeAt.get(uid) || 0) > 8000) {
    noticeAt.set(uid, now());
    const n = await m.channel.send({ content: `⚠️ <@${uid}>, ${v.reason}.${tail}${muted ? ` 🔇 Мут на ${fmtMin(minutes)}.` : ""}`, allowedMentions: { users: [uid] } }).catch(() => null);
    if (n) setTimeout(() => n.delete().catch(() => {}), 8000);
  }
  if (v.warn && now() - (dmAt.get(uid) || 0) > 60000) {
    dmAt.set(uid, now());
    const g = guild();
    dmUser(uid, { embeds: [{
      color: COLORS.yellow, title: "⚠️ Сообщение удалено",
      description: `На сервере **${g ? g.name : "RTeam"}**: ${v.reason}.\nПредупреждений: **${count}**` +
        (nextStepText(count) ? ` — ${nextStepText(count)}.` : ".") + (muted ? `\n🔇 Мут на ${fmtMin(minutes)}.` : "") +
        "\n\nПравила сервера — команда **/правила**.",
    }] });
  }
  modLog({
    color: v.warn ? COLORS.yellow : COLORS.gray, title: `🛡️ Автомодерация: ${v.rule}`,
    description: `<@${uid}> в <#${m.channelId}> — ${v.reason}${v.word ? ` («${v.word}»)` : ""}` +
      (v.warn ? `\nПредупреждений: ${count}` : "") + (muted ? `\n🔇 Мут ${fmtMin(minutes)}` : "") +
      (m.content ? `\n\`\`\`${cut(m.content.replace(/`/g, "ˋ"), 900)}\`\`\`` : ""),
  });
}

/* ============================== заявки в модераторы */

const busy = new Set();
const questions = () => (A().questions || []).filter((q) => q && q.label).slice(0, 25);
const pagesCount = () => Math.max(1, Math.ceil(questions().length / 5));

function panelPayload() {
  const a = A();
  const text = a.panel_text || [
    "Хотите помогать серверу? Подайте заявку — это займёт пару минут.",
    "", "**Как это работает**",
    "1️⃣ Нажмите **«Подать заявку»** и ответьте на вопросы. Ответы видите только вы и администрация.",
    "2️⃣ Администрация рассмотрит заявку и пригласит вас на обзвон.",
    "3️⃣ Решение придёт в личные сообщения от бота — не закрывайте ЛС от участников сервера.",
    "", `Если заявку отклонят, подать новую можно через ${a.cooldown_hours} ${plural(a.cooldown_hours, "час", "часа", "часов")}.`,
  ].join("\n");
  return {
    embeds: [{ color: COLORS.blurple, title: cut(a.panel_title, 256), description: cut(text, 4000) }],
    components: [row(button(3, "Подать заявку", "app:start", "📝"))],
  };
}

function appModal(page) {
  const qs = questions(), pages = pagesCount();
  return {
    custom_id: `app:p:${page}`,
    title: cut(`${A().title}${pages > 1 ? ` · ${page + 1}/${pages}` : ""}`, 45),
    components: qs.slice(page * 5, page * 5 + 5).map((q, k) => {
      const idx = page * 5 + k, short = q.style === "short";
      const max = Math.min(4000, Math.max(1, Number(q.max) || (short ? 100 : 1000)));
      const input = { type: 4, custom_id: `q${idx}`, label: cut(q.label, 45), style: short ? 1 : 2, required: q.required !== false, max_length: max };
      if (q.placeholder) input.placeholder = cut(q.placeholder, 100);
      if (q.min && q.required !== false) input.min_length = Math.min(max, Number(q.min));
      return row(input);
    }),
  };
}

function statusLine(app) {
  const d = app.decided || {};
  switch (app.status) {
    case "pending": return "🕓 Ждёт решения";
    case "call": {
      const last = (app.summons || [])[(app.summons || []).length - 1];
      return `📞 На обзвоне — вызвал(а) <@${app.call.by}> ${ts(app.call.t)}` + (last ? `\n🔊 Позван(а) в <#${last.vc}> ${ts(last.t)}` : "");
    }
    case "accepted": return `✅ Принят(а) — <@${d.by}> ${ts(d.t)}`;
    case "rejected": return `❌ Отклонена — <@${d.by}> ${ts(d.t)}${d.reason ? `\nПричина: ${cut(d.reason, 500)}` : ""}`;
    case "left": return "🚪 Кандидат вышел с сервера";
    default: return app.status;
  }
}
const appColor = (s) => ({ pending: COLORS.blurple, call: COLORS.yellow, accepted: COLORS.green, rejected: COLORS.red })[s] || COLORS.gray;

/* Заявка с ответами. Discord ограничивает сообщение 6000 символами — длинные ответы
   сокращаются, а полный текст прикладывается файлом (needFile). */
function appEmbed(app) {
  const title = `📝 ${A().title} #${app.id}`;
  const desc = [
    `Кандидат: <@${app.user_id}> · \`${app.user_tag}\``,
    app.account_created ? `Аккаунт Discord создан ${ts(app.account_created)}` : "",
    app.joined ? `На сервере с ${ts(app.joined, "D")}` : "",
    app.dm_closed ? "⚠️ У кандидата закрыты ЛС — ответ бота до него не дойдёт, сообщите ему сами." : "",
  ].filter(Boolean).join("\n");
  const status = statusLine(app);
  const footer = `ID кандидата: ${app.user_id}`;
  const fixed = title.length + desc.length + status.length + footer.length + 10;
  const n = Math.max(1, app.answers.length);
  const names = app.answers.map((x, k) => cut(`${k + 1}. ${x.q}`, 256));
  const room = 5800 - fixed - names.reduce((s, x) => s + x.length, 0);
  const each = Math.max(60, Math.min(1024, Math.floor(room / n)));
  let needFile = false;
  const fields = app.answers.map((x, k) => {
    const a = String(x.a || "").trim() || "—";
    if (a.length > each) needFile = true;
    return { name: names[k], value: cut(a, each) };
  });
  fields.push({ name: "Статус", value: cut(status, 1024) });
  return { embed: { color: appColor(app.status), title, description: desc, fields: fields.slice(0, 25), footer: { text: footer } }, needFile };
}
function appComponents(app) {
  if (app.status === "pending") return [row(button(4, "Отклонить", `app:rej:${app.id}`, "✖️"), button(3, "На обзвон", `app:call:${app.id}`, "📞"))];
  if (app.status === "call") return [row(button(3, "Принять", `app:acc:${app.id}`, "✅"), button(4, "Отклонить", `app:rej:${app.id}`, "✖️"))];
  return [];
}
const reviewPayload = (app) => ({ embeds: [appEmbed(app).embed], components: appComponents(app) });
function appText(app) {
  return `${A().title} #${app.id}\nКандидат: ${app.user_tag} (${app.user_id})\nДата: ${new Date(app.created).toLocaleString("ru-RU")}\n\n` +
    app.answers.map((x, k) => `${k + 1}. ${x.q}\n${x.a || "—"}`).join("\n\n") + "\n";
}

function openApp(uid) {
  return Object.values(data.apps).find((a) => a.user_id === uid && (a.status === "pending" || a.status === "call")) || null;
}
function cooldownLeft(uid) {
  const h = Number(A().cooldown_hours) || 0;
  if (!h) return 0;
  const last = Object.values(data.apps).filter((a) => a.user_id === uid && a.status === "rejected")
    .reduce((m, a) => Math.max(m, (a.decided && a.decided.t) || 0), 0);
  return Math.max(0, last + h * 3600e3 - now());
}

async function startApplication(i) {
  const a = A();
  if (!a.enabled || !questions().length) return i.reply({ content: "Приём заявок сейчас закрыт.", flags: EPH });
  const open = openApp(i.user.id);
  if (open) return i.reply({ content: `Ваша заявка #${open.id} уже на рассмотрении (${open.status === "call" ? "вы на этапе обзвона" : "ждёт решения"}). Ответ придёт в ЛС.`, flags: EPH });
  const left = cooldownLeft(i.user.id);
  if (left) return i.reply({ content: `Вашу прошлую заявку отклонили. Новую можно подать ${ts(now() + left)}.`, flags: EPH });
  data.drafts[i.user.id] = { page: 0, answers: {}, t: now() };
  save();
  return i.showModal(appModal(0));
}

async function onAppPage(i, page) {
  const uid = i.user.id, pages = pagesCount();
  let d = data.drafts[uid];
  if (page === 0) d = data.drafts[uid] = { page: 0, answers: {}, t: now() };
  if (!d || d.page !== page || now() - d.t > 3600e3) {
    return i.reply({ content: "Форма устарела. Нажмите «Подать заявку» ещё раз.", flags: EPH });
  }
  // ответ — в течение 3 секунд: дальше отправка может занять время
  if (page === 0) await i.deferReply({ flags: EPH }); else await i.deferUpdate();
  questions().forEach((q, idx) => {
    if (Math.floor(idx / 5) !== page) return;
    try { d.answers[idx] = String(i.fields.getTextInputValue(`q${idx}`) || ""); } catch (e) { d.answers[idx] = ""; }
  });
  d.page = page + 1; d.t = now();
  save();
  if (d.page < pages) {
    return i.editReply({
      content: `✅ Шаг ${page + 1} из ${pages} сохранён. Нажмите «Продолжить», чтобы ответить на остальные вопросы.`,
      components: [row(button(1, `Продолжить (шаг ${page + 2} из ${pages})`, "app:next", "➡️"), button(2, "Отменить", "app:cancel"))],
    });
  }
  if (openApp(uid)) {
    delete data.drafts[uid]; save();
    return i.editReply({ content: "Ваша заявка уже на рассмотрении.", components: [] });
  }
  const res = await submitApplication(i, d);
  return i.editReply({ content: res, components: [] });
}

async function submitApplication(i, d) {
  const uid = i.user.id;
  const review = await chan(A().review_channel_id);
  if (!review) {
    log(`❌ Канал рассмотрения заявок ${A().review_channel_id} не найден`);
    return "❌ Не удалось отправить заявку: канал для заявок не настроен. Сообщите администрации — ваши ответы сохранены, попробуйте позже.";
  }
  const app = {
    id: String(++data.app_seq), user_id: uid, user_tag: i.user.tag || i.user.username,
    answers: questions().map((q, k) => ({ q: q.label, a: String(d.answers[k] || "").trim() })),
    status: "pending", created: now(), account_created: i.user.createdTimestamp || null,
    joined: (i.member && i.member.joinedTimestamp) || null,
  };
  const { embed, needFile } = appEmbed(app);
  const pings = ids(A().ping_role_ids);
  let msg;
  try {
    msg = await review.send({
      content: pings.map((r) => `<@&${r}>`).join(" ") || undefined,
      embeds: [embed], components: appComponents(app),
      files: needFile ? [{ attachment: Buffer.from(appText(app), "utf8"), name: `zayavka-${app.id}.txt` }] : [],
      allowedMentions: { roles: pings, users: [] },
    });
  } catch (e) {
    data.app_seq--;
    log("❌ Заявка не отправлена:", e.message);
    return "❌ Не удалось отправить заявку (у бота нет доступа к каналу заявок). Сообщите администрации и попробуйте позже.";
  }
  app.review = { channel: review.id, message: msg.id };
  data.apps[app.id] = app;
  delete data.drafts[uid];
  save();
  const dm = await dmUser(uid, { embeds: [{
    color: COLORS.blurple, title: `📝 Заявка #${app.id} отправлена`,
    description: `Спасибо! Ваша заявка «${A().title}» на сервере RTeam принята на рассмотрение. Решение придёт сюда, в личные сообщения.`,
  }] });
  if (!dm.ok) { app.dm_closed = true; save(); await msg.edit(reviewPayload(app)).catch(() => {}); }
  modLog({ color: COLORS.blurple, title: `📝 Новая заявка #${app.id}`, description: `<@${uid}> — ${msg.url}` });
  return `✅ Заявка #${app.id} отправлена! Её видите только вы и администрация. Решение придёт в личные сообщения от бота` +
    (dm.ok ? "." : " — но у вас закрыты ЛС: откройте их в настройках конфиденциальности сервера, иначе ответ не дойдёт.");
}

const roleError = (e, roleId) => {
  const role = guild() && guild().roles.cache.get(roleId);
  return e && (e.code === 50013 || e.status === 403)
    ? `у бота нет права «Управлять ролями» или его роль ниже роли «${role ? role.name : roleId}». Настройки сервера → Роли → перетащите роль бота выше.`
    : (e && e.message) || "ошибка";
};
const already = (i, app) => i.reply({ content: `Заявка #${app.id} уже обработана: ${statusLine(app)}`, flags: EPH, allowedMentions: { parse: [] } });

/* Решения по заявке — общие для кнопок в канале рассмотрения и для админ-панели (/админ).
   Каждое возвращает {ok, error?} и само обновляет сообщение с заявкой. */
async function refreshReview(app) {
  if (!app.review) return;
  const ch = await chan(app.review.channel);
  const msg = ch ? await ch.messages.fetch(app.review.message).catch(() => null) : null;
  if (msg) await msg.edit(reviewPayload(app)).catch((e) => log("⚠️ Заявка не обновлена:", e.message));
}
async function fetchCandidate(app, by) {
  const g = guild();
  const member = g ? await g.members.fetch(app.user_id).catch(() => null) : null;
  if (!member) {
    app.status = "left"; app.decided = { by, t: now() }; save();
    await refreshReview(app);
  }
  return member;
}
async function appCall(app, by, byTag) {
  const member = await fetchCandidate(app, by);
  if (!member) return { ok: false, error: "Кандидат уже вышел с сервера — заявка закрыта." };
  const roleId = A().call_role_id;
  if (isId(roleId)) {
    try { await member.roles.add(roleId, `Заявка #${app.id}: на обзвон (${byTag})`); } catch (e) {
      return { ok: false, error: `❌ Не удалось выдать роль: ${roleError(e, roleId)}` };
    }
  }
  app.status = "call"; app.call = { by, t: now() }; save();
  await refreshReview(app);
  const role = isId(roleId) && guild().roles.cache.get(roleId);
  await dmUser(app.user_id, { embeds: [{
    color: COLORS.yellow, title: "📞 Вы прошли на обзвон!",
    description: `Ваша заявка #${app.id} («${A().title}») одобрена для обзвона.` + (role ? ` Вам выдана роль **${role.name}**.` : "") +
      "\nОжидайте — администратор позовёт вас в голосовой канал.",
  }] });
  modLog({ color: COLORS.yellow, title: `📞 Заявка #${app.id}: на обзвон`, description: `<@${app.user_id}> — решение <@${by}>` });
  return { ok: true };
}
async function appAccept(app, by, byTag) {
  const member = await fetchCandidate(app, by);
  if (!member) return { ok: false, error: "Кандидат уже вышел с сервера — заявка закрыта." };
  const acc = A().accept_role_id, call = A().call_role_id;
  if (isId(acc)) {
    try { await member.roles.add(acc, `Заявка #${app.id}: принят (${byTag})`); } catch (e) {
      return { ok: false, error: `❌ Не удалось выдать роль: ${roleError(e, acc)}` };
    }
    if (isId(call) && A().remove_call_role_on_accept && call !== acc) await member.roles.remove(call, `Заявка #${app.id}: принят`).catch(() => {});
  }
  app.status = "accepted"; app.decided = { by, t: now() }; save();
  await refreshReview(app);
  const role = isId(acc) && guild().roles.cache.get(acc);
  await dmUser(app.user_id, { embeds: [{
    color: COLORS.green, title: "🎉 Поздравляем, вы приняты!",
    description: `Ваша заявка #${app.id} («${A().title}») одобрена.` + (role ? ` Вам выдана роль **${role.name}**.` : "") +
      " Добро пожаловать в команду модераторов RTeam!",
  }] });
  modLog({ color: COLORS.green, title: `✅ Заявка #${app.id}: принят`, description: `<@${app.user_id}> — решение <@${by}>` });
  return { ok: true };
}
async function appReject(app, by, reason) {
  const hadCall = app.status === "call";
  app.status = "rejected"; app.decided = { by, t: now(), reason }; save();
  if (hadCall && isId(A().call_role_id)) {
    const member = guild() ? await guild().members.fetch(app.user_id).catch(() => null) : null;
    if (member) await member.roles.remove(A().call_role_id, `Заявка #${app.id}: отклонена`).catch(() => {});
  }
  await refreshReview(app);
  const h = Number(A().cooldown_hours) || 0;
  await dmUser(app.user_id, { embeds: [{
    color: COLORS.red, title: "Заявка отклонена",
    description: `К сожалению, ваша заявка #${app.id} («${A().title}») отклонена.` + (reason ? `\n\n**Причина:** ${cut(reason, 1000)}` : "") +
      (h ? `\n\nПодать новую заявку можно через ${h} ${plural(h, "час", "часа", "часов")}.` : ""),
  }] });
  modLog({ color: COLORS.red, title: `❌ Заявка #${app.id}: отклонена`, description: `<@${app.user_id}> — решение <@${by}>${reason ? `\nПричина: ${cut(reason, 500)}` : ""}` });
  return { ok: true };
}
const rejectModal = (customId, id) => ({
  custom_id: customId, title: cut(`Отклонить заявку #${id}`, 45),
  components: [row({ type: 4, custom_id: "reason", label: "Причина (кандидат увидит её в ЛС)", style: 2, required: false, max_length: 500 })],
});
const modalText = (i, id) => { try { return String(i.fields.getTextInputValue(id) || "").trim(); } catch (e) { return ""; } };

async function reviewButton(i, action, id) {
  if (!isReviewer(i)) return i.reply({ content: "Решать заявки может только администрация.", flags: EPH });
  const app = data.apps[id];
  if (!app) return i.reply({ content: "Заявка не найдена.", flags: EPH });
  if (busy.has(id)) return i.reply({ content: "Эту заявку сейчас обрабатывает другой администратор.", flags: EPH });
  if (action === "rej") {
    if (app.status !== "pending" && app.status !== "call") return already(i, app);
    return i.showModal(rejectModal(`app:rejm:${id}`, id));
  }
  if (action === "call" && app.status !== "pending") return already(i, app);
  if (action === "acc" && app.status !== "call") return already(i, app);
  busy.add(id);
  try {
    await i.deferUpdate();
    const r = action === "call" ? await appCall(app, i.user.id, i.user.tag) : await appAccept(app, i.user.id, i.user.tag);
    if (!r.ok) return i.followUp({ content: r.error, flags: EPH });
  } finally { busy.delete(id); }
}

async function onRejectModal(i, id) {
  if (!isReviewer(i)) return i.reply({ content: "Решать заявки может только администрация.", flags: EPH });
  const app = data.apps[id];
  if (!app) return i.reply({ content: "Заявка не найдена.", flags: EPH });
  if (app.status !== "pending" && app.status !== "call") return already(i, app);
  if (busy.has(id)) return i.reply({ content: "Эту заявку сейчас обрабатывает другой администратор.", flags: EPH });
  busy.add(id);
  try {
    await i.deferUpdate();
    await appReject(app, i.user.id, modalText(i, "reason"));
  } finally { busy.delete(id); }
}

/* ============================== идеи */

const ideaAt = new Map();
function ideaCooldown(uid) {
  const left = (ideaAt.get(uid) || 0) + (Number(I().cooldown_minutes) || 0) * 60000 - now();
  return left > 0 ? left : 0;
}
/* Публикует идею в канал голосования. image — вложение из сообщения (перезаливается: оригинал удаляется). */
async function postIdea(user, member, text, image) {
  const vote = await chan(I().vote_channel_id);
  if (!vote) return { ok: false, error: "Канал голосования не найден — сообщите администрации." };
  const n = ++data.idea_seq;
  const name = (member && member.displayName) || user.globalName || user.username;
  const embed = {
    color: COLORS.gold, author: { name: cut(name, 256), icon_url: user.displayAvatarURL ? user.displayAvatarURL({ size: 64 }) : undefined },
    title: `💡 Идея #${n}`, description: cut(text || "", 4000) || "—",
    footer: { text: `Голосуйте: ${I().like} — за, ${I().dislike} — против` }, timestamp: new Date().toISOString(),
  };
  let msg = null;
  if (image) {
    const fname = `idea-${n}.${(image.name || "png").split(".").pop().toLowerCase().replace(/[^a-z0-9]/g, "") || "png"}`;
    msg = await vote.send({ embeds: [{ ...embed, image: { url: `attachment://${fname}` } }], files: [{ attachment: image.url, name: fname }] }).catch(() => null);
  }
  if (!msg) msg = await vote.send({ embeds: [embed] }).catch((e) => { log("❌ Идея не отправлена:", e.message); return null; });
  if (!msg) { data.idea_seq--; return { ok: false, error: "Не удалось отправить идею — у бота нет доступа к каналу голосования." }; }
  data.ideas[msg.id] = { n, user_id: user.id, t: now() };
  save();
  ideaAt.set(user.id, now());
  for (const e of [I().like, I().dislike]) await msg.react(e).catch((err) => log("⚠️ Реакция:", err.message));
  return { ok: true, n, url: msg.url, channel: vote.id };
}

async function ideaFromMessage(m) {
  const text = String(m.content || "").trim();
  const image = [...m.attachments.values()].find((a) => /^image\//.test(a.contentType || "") && a.size <= 8 * 1024 * 1024) || null;
  const say = async (content) => {
    const n = await m.channel.send({ content, allowedMentions: { users: [m.author.id] } }).catch(() => null);
    if (n) setTimeout(() => n.delete().catch(() => {}), 10000);
  };
  const left = ideaCooldown(m.author.id);
  if (left) { await m.delete().catch(() => {}); return say(`⏳ <@${m.author.id}>, следующую идею можно отправить ${ts(now() + left)}.`); }
  if (text.length < I().min_length && !image) {
    await m.delete().catch(() => {});
    return say(`✏️ <@${m.author.id}>, опишите идею подробнее (минимум ${I().min_length} символов).`);
  }
  const r = await postIdea(m.author, m.member, cut(text, I().max_length), image);
  await m.delete().catch(() => {});
  return say(r.ok ? `✅ <@${m.author.id}>, идея #${r.n} отправлена на голосование в <#${r.channel}>!` : `❌ ${r.error}`);
}

async function onReaction(reaction, user) {
  if (user.bot || !I().enabled || !I().one_vote) return;
  const msg = reaction.message;
  if (msg.channelId !== I().vote_channel_id || !data.ideas[msg.id]) return;
  const name = reaction.emoji.name, like = I().like, dislike = I().dislike;
  if (name !== like && name !== dislike) return;
  const other = name === like ? dislike : like;
  await rest.delete(Routes.channelMessageUserReaction(msg.channelId, msg.id, encodeURIComponent(other), user.id)).catch(() => {});
}

/* ============================== уровни и активность
   XP за сообщения (раз в минуту, 15–25 XP) и за время в голосовых каналах (10 XP в минуту, если в канале
   не меньше двух человек и вы не выключили звук). Уровень L → L+1 стоит 5·L² + 50·L + 100 XP. */

const xpNeed = (l) => 5 * l * l + 50 * l + 100;
function levelOf(xp) {
  let level = 0, rest = Math.max(0, Math.floor(xp || 0));
  while (rest >= xpNeed(level)) { rest -= xpNeed(level); level++; }
  return { level, into: rest, need: xpNeed(level) };
}
const dayKey = (t = now()) => new Date(t + 3 * 3600e3).toISOString().slice(0, 10); // сутки по Москве
function bumpDay(uid, msgs, voice) {
  const k = dayKey();
  const d = (data.days[k] = data.days[k] || { m: 0, v: 0, u: {} });
  d.m += msgs; d.v += voice; d.u[uid] = (d.u[uid] || 0) + msgs + voice;
  const keys = Object.keys(data.days).sort();
  while (keys.length > 31) delete data.days[keys.shift()];
}
/* Добавить активность. Возвращает новый уровень, если он вырос, иначе 0 */
function addActivity(uid, xp, msgs, voice) {
  const st = (data.levels[uid] = data.levels[uid] || { xp: 0, msgs: 0, voice: 0 });
  const before = levelOf(st.xp).level;
  st.xp += xp; st.msgs += msgs; st.voice += voice; st.t = now();
  bumpDay(uid, msgs, voice);
  save();
  const after = levelOf(st.xp).level;
  return after > before ? after : 0;
}
const xpAt = new Map();
async function messageXp(m) {
  const L = LV();
  if (!L.enabled || ids(L.ignore_channel_ids).includes(m.channelId)) return;
  let xp = 0;
  if (now() - (xpAt.get(m.author.id) || 0) >= (Number(L.cooldown_seconds) || 0) * 1000) {
    xpAt.set(m.author.id, now());
    const lo = Number(L.xp_min) || 0, hi = Math.max(lo, Number(L.xp_max) || 0);
    xp = lo + Math.floor(Math.random() * (hi - lo + 1));
  }
  const up = addActivity(m.author.id, xp, 1, 0);
  if (up) await levelUp(m.author.id, up, m.channel);
}
async function levelUp(uid, level, channel) {
  const L = LV(), g = guild();
  const rewards = Object.entries(L.roles || {}).filter(([lv, rid]) => Number(lv) <= level && isId(rid)).map(([, rid]) => rid);
  const got = [];
  if (rewards.length && g) {
    const mem = await g.members.fetch(uid).catch(() => null);
    for (const rid of rewards) {
      if (!mem || mem.roles.cache.has(rid)) continue;
      try { await mem.roles.add(rid, `Уровень ${level}`); got.push(rid); } catch (e) { log("⚠️ Роль за уровень:", roleError(e, rid)); }
    }
  }
  if (!L.announce) return;
  const ch = (isId(L.announce_channel_id) && await chan(L.announce_channel_id)) || channel;
  if (!ch) return;
  await ch.send({ content: `🎉 <@${uid}> достигает **${level} уровня**!` + (got.length ? ` Новая роль: ${got.map((r) => `<@&${r}>`).join(", ")}` : ""),
    allowedMentions: { users: [uid] } }).catch(() => {});
}
/* Раз в минуту: XP всем, кто сидит в голосовых каналах (не в AFK, не один, со звуком) */
function voiceTick() {
  const L = LV(), g = guild();
  if (!L.enabled || !g || !client || !client.isReady()) return;
  const byCh = new Map();
  for (const vs of g.voiceStates.cache.values()) {
    if (!vs.channelId || vs.channelId === g.afkChannelId) continue;
    const u = client.users.cache.get(vs.id);
    if (u && u.bot) continue;
    if (!byCh.has(vs.channelId)) byCh.set(vs.channelId, []);
    byCh.get(vs.channelId).push(vs);
  }
  for (const list of byCh.values()) {
    if (list.length < Math.max(1, Number(L.voice_min_members) || 1)) continue;
    for (const vs of list) {
      if (vs.selfDeaf || vs.serverDeaf) continue;
      const up = addActivity(vs.id, Number(L.voice_xp_per_minute) || 0, 0, 1);
      if (up) chan(L.voice_announce_channel_id).then((ch) => ch && levelUp(vs.id, up, ch)).catch(() => {});
    }
  }
}
const ranked = () => Object.entries(data.levels).sort((a, b) => b[1].xp - a[1].xp || b[1].msgs - a[1].msgs);
const num = (x) => String(Math.round(Number(x) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
const fmtVoice = (min) => (min >= 60 ? `${Math.floor(min / 60)} ч ${min % 60} мин` : `${min} мин`);
const bar = (a, b, n = 12) => { const f = Math.max(0, Math.min(n, Math.round((b ? a / b : 0) * n))); return "▰".repeat(f) + "▱".repeat(n - f); };
function levelEmbed(user, member) {
  const st = data.levels[user.id] || { xp: 0, msgs: 0, voice: 0 };
  const lv = levelOf(st.xp);
  const place = ranked().findIndex(([id]) => id === user.id);
  return {
    color: COLORS.blurple, author: { name: cut((member && member.displayName) || user.globalName || user.username, 256), icon_url: user.displayAvatarURL ? user.displayAvatarURL({ size: 64 }) : undefined },
    title: `⭐ Уровень ${lv.level}`, description: `${bar(lv.into, lv.need)}  **${num(lv.into)}** / ${num(lv.need)} XP до ${lv.level + 1} уровня`,
    fields: [
      { name: "Место", value: place >= 0 ? `#${place + 1}` : "—", inline: true },
      { name: "Всего XP", value: num(st.xp), inline: true },
      { name: "Сообщений", value: num(st.msgs), inline: true },
      { name: "В голосе", value: fmtVoice(st.voice || 0), inline: true },
    ],
  };
}
function topEmbed(n = 10) {
  const list = ranked().slice(0, n);
  const medal = ["🥇", "🥈", "🥉"];
  const lines = list.map(([id, st], k) => `${medal[k] || `**${k + 1}.**`} <@${id}> — ${levelOf(st.xp).level} ур. · ${num(st.xp)} XP · 💬 ${num(st.msgs)} · 🎙 ${fmtVoice(st.voice || 0)}`);
  return { color: COLORS.gold, title: "🏆 Топ активности", description: lines.join("\n") || "Пока никого — пишите в чат и заходите в голосовые каналы!" };
}
function activityStats(days) {
  const keys = Object.keys(data.days).sort().slice(-days);
  const users = new Set();
  let m = 0, v = 0;
  for (const k of keys) { const d = data.days[k]; m += d.m; v += d.v; Object.keys(d.u).forEach((u) => users.add(u)); }
  return { m, v, u: users.size };
}

/* ============================== админ-панель (/админ)
   Открывают администраторы сервера и роли из panel.role_ids. Объявления в каналы из panel.announce_channels,
   список кандидатов на обзвоне: позвать в голосовой канал (panel.call_voice_channel_ids), «Прошёл» / «Не прошёл». */

const annDrafts = new Map();
const back = (id = "adm:home", label = "Назад") => button(2, label, id, "⬅️");
function panelHome(note) {
  const apps = Object.values(data.apps);
  const pending = apps.filter((a) => a.status === "pending").length, calls = apps.filter((a) => a.status === "call").length;
  const today = activityStats(1), week = activityStats(7);
  const anns = (PN().announce_channels || []).filter((c) => isId(c.id)).slice(0, 5);
  const rows = [];
  if (anns.length) rows.push(row(...anns.map((c, k) => button(1, cut(`Объявление: ${c.name || "канал"}`, 80), `adm:ann:${k}`, c.emoji || "📢"))));
  rows.push(row(button(3, `Обзвон (${calls})`, "adm:calls", "📞"), button(2, "Активность", "adm:act", "📊"), button(2, "Обновить", "adm:home", "🔄")));
  return {
    content: note || "",
    embeds: [{
      color: COLORS.blurple, title: "🛠️ Админ-панель RTeam",
      description: [
        `📝 Заявок ждут решения: **${pending}**`,
        `📞 На обзвоне: **${calls}**`,
        `📊 Сегодня: ${num(today.m)} сообщ. · ${fmtVoice(today.v)} в голосе · активных ${today.u}`,
        `📈 За 7 дней: ${num(week.m)} сообщ. · ${fmtVoice(week.v)} в голосе · активных ${week.u}`,
        "", "Объявление — бот опубликует его от своего имени. Обзвон — все, кого отправили на обзвон: позвать в голосовой канал и принять решение.",
      ].join("\n"),
    }],
    components: rows,
    allowedMentions: { parse: [] },
  };
}
const annChannel = (k) => (PN().announce_channels || []).filter((c) => isId(c.id))[Number(k)] || null;
function annEmbed(d, user) {
  const e = { color: COLORS.blurple, description: cut(d.text, 4000), footer: { text: `Объявление RTeam · ${user.globalName || user.username}` }, timestamp: new Date().toISOString() };
  if (d.title) e.title = cut(d.title, 256);
  if (d.image) e.image = { url: d.image };
  return e;
}
function annModal(k, d) {
  const c = annChannel(k);
  const field = (custom_id, label, style, max, required, value, placeholder) => {
    const f = { type: 4, custom_id, label, style, max_length: max, required };
    if (value) f.value = cut(value, max);
    if (placeholder) f.placeholder = placeholder;
    return row(f);
  };
  return {
    custom_id: `adm:annm:${k}`, title: cut(`Объявление: ${c ? c.name : "канал"}`, 45),
    components: [
      field("title", "Заголовок (необязательно)", 1, 256, false, d && d.title),
      field("text", "Текст объявления", 2, 4000, true, d && d.text),
      field("image", "Картинка — ссылка https://… (необязательно)", 1, 500, false, d && d.image, "https://…"),
    ],
  };
}
function callsList() {
  return Object.values(data.apps).filter((a) => a.status === "call").sort((a, b) => (a.call ? a.call.t : 0) - (b.call ? b.call.t : 0));
}
function callsView(note) {
  const list = callsList();
  const lines = list.slice(0, 25).map((a) => {
    const last = (a.summons || [])[(a.summons || []).length - 1];
    return `**#${a.id}** <@${a.user_id}> · \`${a.user_tag}\` — на обзвоне с ${ts(a.call.t)}` + (last ? ` · звали в <#${last.vc}> ${ts(last.t)}` : "");
  });
  const rows = [];
  if (list.length) {
    rows.push(row({ type: 3, custom_id: "adm:cand", placeholder: "Выберите кандидата", min_values: 1, max_values: 1,
      options: list.slice(0, 25).map((a) => ({ label: cut(`#${a.id} ${a.user_tag}`, 100), value: a.id, description: cut(`На обзвоне с ${new Date(a.call.t).toLocaleDateString("ru-RU")}`, 100) })) }));
  }
  rows.push(row(back()));
  return {
    content: note || "",
    embeds: [{ color: COLORS.yellow, title: `📞 Обзвон — ${list.length}`, description: lines.join("\n") || "Сейчас никого на обзвоне. Кандидат появляется здесь, когда в канале заявок нажимают «На обзвон»." }],
    components: rows, allowedMentions: { parse: [] },
  };
}
function candView(id, note) {
  const app = data.apps[id];
  if (!app || app.status !== "call") return callsView(note || "Этот кандидат уже не на обзвоне.");
  const link = app.review ? `https://discord.com/channels/${cfg.guild_id}/${app.review.channel}/${app.review.message}` : "";
  const summons = (app.summons || []).slice(-3).map((x) => `🔊 <#${x.vc}> — позвал(а) <@${x.by}> ${ts(x.t)}`);
  const vcs = ids(PN().call_voice_channel_ids).slice(0, 5);
  const rows = [];
  if (vcs.length) {
    rows.push(row(...vcs.map((vc, k) => {
      const c = client && client.channels.cache.get(vc);
      return button(1, cut(`Позвать в ${c ? c.name : `канал ${k + 1}`}`, 80), `adm:sum:${id}:${k}`, "🔊");
    })));
  }
  rows.push(row(button(3, "Прошёл", `adm:pass:${id}`, "✅"), button(4, "Не прошёл", `adm:fail:${id}`, "✖️"), back("adm:calls", "К списку")));
  return {
    content: note || "",
    embeds: [{
      color: COLORS.yellow, title: `📞 Кандидат #${app.id}`,
      description: [`<@${app.user_id}> · \`${app.user_tag}\``, `На обзвоне с ${ts(app.call.t)} — отправил(а) <@${app.call.by}>`,
        link ? `[Заявка с ответами](${link})` : "", ...summons].filter(Boolean).join("\n"),
      fields: app.answers.slice(0, 4).map((x) => ({ name: cut(x.q, 256), value: cut(x.a || "—", 300) })),
    }],
    components: rows, allowedMentions: { parse: [] },
  };
}
/* Позвать кандидата: пинг в чате голосового канала, ЛС со ссылкой и, если он уже в другом голосовом, перенос */
async function summon(app, vcId, by) {
  const g = guild();
  const vc = await chan(vcId);
  if (!g || !vc || vc.guildId !== g.id) return "❌ Голосовой канал не найден — проверьте panel.call_voice_channel_ids в config.json.";
  const member = await fetchCandidate(app, by);
  if (!member) return "Кандидат уже вышел с сервера — заявка закрыта.";
  const done = [];
  const ping = vc.isTextBased() ? await vc.send({ content: `📞 <@${app.user_id}>, вас вызывают на обзвон! Заходите в этот голосовой канал — <#${vc.id}>.`, allowedMentions: { users: [app.user_id] } }).catch(() => null) : null;
  if (ping) done.push("пинг в чате канала");
  const dm = await dmUser(app.user_id, {
    embeds: [{ color: COLORS.yellow, title: "📞 Вас вызывают на обзвон", description: `Заходите в голосовой канал **${vc.name}** на сервере RTeam — вас ждёт администратор.` }],
    components: [row(linkButton("Зайти в канал", `https://discord.com/channels/${g.id}/${vc.id}`))],
  });
  if (dm.ok) done.push("сообщение в ЛС");
  const now_ = member.voice && member.voice.channelId;
  if (now_ === vc.id) done.push("он(а) уже в канале");
  else if (now_) {
    try { await member.voice.setChannel(vc, `Обзвон, заявка #${app.id}`); done.push("перенёс из другого голосового"); } catch (e) { done.push("перенести не вышло — нет права «Перемещать участников»"); }
  }
  app.summons = [...(app.summons || []), { vc: vc.id, by, t: now() }].slice(-10);
  save();
  await refreshReview(app);
  modLog({ color: COLORS.yellow, title: `🔊 Заявка #${app.id}: позван(а) на обзвон`, description: `<@${app.user_id}> в <#${vc.id}> — <@${by}>` });
  return ping || dm.ok ? `✅ Позвал(а) <@${app.user_id}> в <#${vc.id}>: ${done.join(", ")}.` : `❌ Не получилось позвать: нет доступа к чату <#${vc.id}> и закрыты ЛС.`;
}
const openPanelPayload = () => ({
  embeds: [{ color: COLORS.blurple, title: "🛠️ Админ-панель RTeam", description: "Объявления, обзвон кандидатов и активность сервера. Открыть может только администрация." }],
  components: [row(button(1, "Открыть админ-панель", "adm:open", "🛠️"))],
});
const ensureAdminPanel = (channelId, fresh) => ensureMessage("admin_panel", channelId, openPanelPayload(), (x) => hasButton(x, "adm:open"), fresh);

async function onPanel(i, action, a, b) {
  if (!isPanel(i)) return i.reply({ content: "Админ-панель доступна только администрации.", flags: EPH });
  if (action === "open") return i.reply({ ...panelHome(), flags: EPH });
  if (action === "home") return i.update(panelHome());
  if (action === "act") return i.update({ content: "", embeds: [topEmbed(15)], components: [row(back())], allowedMentions: { parse: [] } });
  if (action === "calls") return i.update(callsView());
  if (action === "cand") return i.update(candView(i.values[0]));
  if (action === "ann") {
    if (!annChannel(a)) return i.update(panelHome("❌ Канал для объявлений не найден в config.json."));
    const d = annDrafts.get(i.user.id);
    return i.showModal(annModal(a, d && d.k === String(a) ? d : null));
  }
  if (action === "annpub") {
    const d = annDrafts.get(i.user.id);
    if (!d) return i.update(panelHome("Черновик устарел — напишите объявление ещё раз."));
    const c = annChannel(d.k);
    const ch = c && await chan(c.id);
    if (!ch) return i.update(panelHome("❌ Канал для объявлений не найден или бот его не видит."));
    await i.deferUpdate();
    const everyone = a === "1";
    let msg;
    try {
      msg = await ch.send({ content: everyone ? "@everyone" : undefined, embeds: [annEmbed(d, i.user)], allowedMentions: { parse: everyone ? ["everyone"] : [] } });
    } catch (e) { return i.editReply(panelHome(`❌ Не опубликовано: ${e.code === 50013 ? "у бота нет прав писать в этот канал" : e.message}`)); }
    if (ch.type === 5) await msg.crosspost().catch(() => {}); // канал объявлений — сразу «Опубликовать» для подписчиков
    annDrafts.delete(i.user.id);
    const g = guild(), me = g && g.members.me;
    const noPing = everyone && me && !ch.permissionsFor(me).has(P.MentionEveryone);
    modLog({ color: COLORS.blurple, title: "📢 Объявление", description: `<@${i.user.id}> в <#${ch.id}>: ${msg.url}` });
    return i.editReply(panelHome(`✅ Объявление опубликовано в <#${ch.id}>: ${msg.url}` + (noPing ? "\n⚠️ У бота нет права «Упоминание @everyone» — пинга не было." : "")));
  }
  if (action === "sum" || action === "pass" || action === "fail") {
    const app = data.apps[a];
    if (!app || app.status !== "call") return i.update(callsView("Этот кандидат уже не на обзвоне."));
    if (busy.has(a)) return i.reply({ content: "Эту заявку сейчас обрабатывает другой администратор.", flags: EPH });
    if (action === "fail") return i.showModal(rejectModal(`adm:failm:${a}`, a));
    busy.add(a);
    try {
      await i.deferUpdate();
      if (action === "sum") {
        const vc = ids(PN().call_voice_channel_ids)[Number(b)];
        return i.editReply(candView(a, await summon(app, vc, i.user.id)));
      }
      const r = await appAccept(app, i.user.id, i.user.tag);
      const role = isId(A().accept_role_id) && guild().roles.cache.get(A().accept_role_id);
      return i.editReply(r.ok ? callsView(`✅ <@${app.user_id}> прошёл обзвон` + (role ? ` — выдана роль «${role.name}».` : ".")) : candView(a, r.error));
    } finally { busy.delete(a); }
  }
}
async function onPanelModal(i, action, a) {
  if (!isPanel(i)) return i.reply({ content: "Админ-панель доступна только администрации.", flags: EPH });
  if (action === "annm") {
    const d = { k: String(a), title: modalText(i, "title"), text: modalText(i, "text"), image: modalText(i, "image") };
    if (d.image && !/^https:\/\/\S+$/i.test(d.image)) return i.reply({ content: "Ссылка на картинку должна начинаться с https://", flags: EPH });
    annDrafts.set(i.user.id, d);
    const c = annChannel(a);
    const payload = {
      content: `👀 Так будет выглядеть объявление в <#${c ? c.id : "?"}>. Опубликовать?`,
      embeds: [annEmbed(d, i.user)],
      components: [row(button(3, "Опубликовать", "adm:annpub:0", "✅"), button(1, "С пингом @everyone", "adm:annpub:1", "📣"),
        button(2, "Изменить", `adm:ann:${a}`, "✏️"), button(2, "Отмена", "adm:home"))],
      allowedMentions: { parse: [] },
    };
    return i.isFromMessage() ? i.update(payload) : i.reply({ ...payload, flags: EPH });
  }
  if (action === "failm") {
    const app = data.apps[a];
    if (!app || app.status !== "call") return i.isFromMessage() ? i.update(callsView("Этот кандидат уже не на обзвоне.")) : i.reply({ content: "Кандидат уже не на обзвоне.", flags: EPH });
    if (busy.has(a)) return i.reply({ content: "Эту заявку сейчас обрабатывает другой администратор.", flags: EPH });
    busy.add(a);
    try {
      await i.deferUpdate();
      await appReject(app, i.user.id, modalText(i, "reason"));
      return i.editReply(callsView(`❌ <@${app.user_id}> не прошёл обзвон — заявка отклонена, роль обзвона снята.`));
    } finally { busy.delete(a); }
  }
}

/* ============================== правила */

function rulesPayload() {
  const r = cfg.rules;
  const body = (r.items || []).map((x, k) => `**${k + 1}.** ${x}`).join("\n\n");
  return { embeds: [{ color: COLORS.blurple, title: cut(r.title, 256), description: cut(body || "Правила пока не заполнены.", 4000), ...(r.footer ? { footer: { text: cut(r.footer, 2048) } } : {}) }] };
}
function ideasInfoPayload() {
  return { embeds: [{
    color: COLORS.gold, title: "💡 Предложите идею",
    description: `Напишите идею сюда (можно с картинкой) — бот отправит её на голосование в <#${I().vote_channel_id}>.\n` +
      `Там участники голосуют ${I().like} и ${I().dislike}. Ещё можно командой **/идея**.\n\nМинимум ${I().min_length} символов, ` +
      `не чаще одной идеи в ${I().cooldown_minutes} мин.`,
  }] };
}

/* Сообщение бота в канале (кнопка заявок, правила): находит своё прошлое и обновляет, а не шлёт новое */
async function ensureMessage(key, channelId, payload, isMine, fresh = false) {
  const ch = await chan(channelId);
  if (!ch || !ch.isTextBased()) throw new Error(`канал ${channelId} не найден или бот его не видит`);
  const hash = sha1(JSON.stringify(payload));
  const st = data.messages[key];
  let msg = null;
  if (st && st.id && st.channel === ch.id) msg = await ch.messages.fetch(st.id).catch(() => null);
  if (!msg) {
    const list = await ch.messages.fetch({ limit: 50 }).catch(() => null);
    msg = list ? list.find((x) => x.author && x.author.id === client.user.id && isMine(x)) || null : null;
  }
  if (msg && fresh) { await msg.delete().catch(() => {}); msg = null; } // перезапуск из админки: сообщение заново, внизу канала
  if (msg && (!st || st.hash !== hash || st.id !== msg.id)) await msg.edit(payload);
  if (!msg) msg = await ch.send(payload);
  data.messages[key] = { channel: ch.id, id: msg.id, hash };
  save();
  return msg;
}
const hasButton = (x, id) => (x.components || []).some((r) => (r.components || []).some((c) => c.customId === id));
const ensurePanel = (fresh) => ensureMessage("panel", A().panel_channel_id, panelPayload(), (x) => hasButton(x, "app:start"), fresh);
const ensureRules = (channelId, fresh) => ensureMessage("rules", channelId || cfg.rules.channel_id, rulesPayload(),
  (x) => x.embeds && x.embeds[0] && x.embeds[0].title === cut(cfg.rules.title, 256), fresh);
const ensureIdeasInfo = (fresh) => ensureMessage("ideas_info", I().input_channel_id, ideasInfoPayload(),
  (x) => x.embeds && x.embeds[0] && x.embeds[0].title === "💡 Предложите идею", fresh);

/* ============================== нейросеть Rai в ЛС */

const rai = { lib: null, at: 0, loading: null };
function evalRai(code) {
  const m = { exports: {} };
  const sandbox = { module: m, exports: m.exports, console, setTimeout, clearTimeout, URL, URLSearchParams, AbortController,
    TextEncoder, TextDecoder, atob, btoa, fetch: (...a) => fetch(...a) };
  vm.runInNewContext(code, sandbox, { filename: "rai-support.js", timeout: 5000 });
  if (!m.exports || typeof m.exports.reply !== "function") throw new Error("в rai-support.js нет RaiSupport");
  return m.exports;
}
async function loadRai() {
  const dir = path.join(DIR, "rai-cache");
  const get = async (f) => {
    const r = await withTimeout(fetch(cfg.rai_base + f), 20000);
    if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`);
    return r.text();
  };
  try {
    const [js, model] = await Promise.all([get("rai-support.js"), get("model.json")]);
    const lib = evalRai(js); lib.use(JSON.parse(model));
    rai.lib = lib; rai.at = now();
    try { fs.mkdirSync(dir, { recursive: true }); fs.writeFileSync(path.join(dir, "rai-support.js"), js); fs.writeFileSync(path.join(dir, "model.json"), model); } catch (e) { /* кэш необязателен */ }
    log(`🧠 Нейросеть Rai загружена с GitHub (${lib.model && lib.model.intents ? lib.model.intents.length : "?"} тем)`);
  } catch (e) {
    if (!rai.lib) {
      try {
        const lib = evalRai(fs.readFileSync(path.join(dir, "rai-support.js"), "utf8"));
        lib.use(JSON.parse(fs.readFileSync(path.join(dir, "model.json"), "utf8")));
        rai.lib = lib; rai.at = now();
        log(`🧠 GitHub недоступен (${e.message}) — нейросеть Rai загружена из кэша`);
      } catch (e2) { log(`⚠️ Нейросеть Rai не загружена: ${e.message}`); }
    }
  }
}
function ensureRai() {
  if (rai.lib && now() - rai.at < 6 * 3600e3) return Promise.resolve();
  if (!rai.loading) rai.loading = loadRai().finally(() => { rai.loading = null; });
  return rai.lib ? Promise.resolve() : rai.loading;
}

function supportUrl(text) {
  const base = `${cfg.site_url}/support.php?new_ticket=1&text=`;
  let t = String(text || "").slice(0, 300);
  while (t && (base + encodeURIComponent(t)).length > 500) t = t.slice(0, -10);
  return base + encodeURIComponent(t);
}
const DM_TEXT = {
  greeting: "Привет! Я Rai — бот RTeam 🤖\nСпросите что угодно про RTeam и сайт rteam.info — отвечу сразу.\n\n" +
    "Ещё сюда приходят коды входа на сайт и уведомления — если привязать Discord в кабинете (rteam.info → кабинет → «Привязки»).",
  thanks: "Рад помочь! Если появятся вопросы — пишите сюда 🙂",
  close_ticket: "Рад, что всё решилось! Если появятся вопросы — пишите сюда 🙂",
  page_help: "Я бот в Discord. На сайте rteam.info есть помощник ✨ — он покажет нужные кнопки прямо на странице. А здесь просто напишите вопрос — отвечу.",
  support_time: "Я — Rai, ИИ-помощник RTeam, отвечаю сразу. Если нужен живой сотрудник — нажмите «Написать в поддержку» ниже: обычно отвечают в течение дня.",
  human: "Хорошо! Живой сотрудник отвечает в поддержке на сайте — нажмите кнопку ниже, ваш вопрос уже будет в обращении.",
};
const HANDOFF_TEXT = "Этот вопрос решает администрация RTeam. Нажмите «Написать в поддержку» ниже — откроется обращение на сайте с вашим вопросом, и вам ответит сотрудник.";
const dmHistory = new Map();

/* Ответ Rai в ЛС. Возвращает {text, components}. */
async function raiAnswer(uid, text) {
  const h = dmHistory.get(uid);
  const history = h && now() - h.t < 30 * 60000 ? h.items : [];
  let r = null;
  if (cfg.dm.rai) {
    try {
      await withTimeout(ensureRai(), 25000);
      if (rai.lib) r = await withTimeout(rai.lib.reply(text, { history, mode: "client", sitePages: [`${cfg.site_url}/`, `${cfg.site_url}/team.php`, `${cfg.site_url}/projects.php`] }), 20000);
    } catch (e) { log("⚠️ Rai:", e.message); r = null; }
  }
  let out, support = false;
  if (!r) { out = "Сейчас я не могу ответить сам. Напишите в поддержку на сайте — вам ответит сотрудник RTeam."; support = true; }
  else if (DM_TEXT[r.intent] && r.source !== "secret") { out = DM_TEXT[r.intent]; support = r.intent === "human" || r.intent === "support_time"; }
  else if (r.handoff && ["ban", "payment", "appeal", "human"].includes(r.intent)) { out = HANDOFF_TEXT; support = true; }
  else {
    out = String(r.reply || "");
    const fixed = out.replace(/([Нн])ажмите (?:кнопку )?«Позвать администратора»/g, (m0, n) => (n === "Н" ? "Н" : "н") + "апишите в поддержку на сайте (кнопка ниже)");
    if (fixed !== out || r.handoff) support = true;
    out = fixed;
  }
  history.push({ from: "client", text: cut(text, 600) }, { from: "ai", text: (r && r.reply) || out });
  dmHistory.set(uid, { items: history.slice(-12), t: now() });
  return { text: cut(out, 1990), components: support ? [row(linkButton("Написать в поддержку", supportUrl(text)))] : [] };
}

const dmLast = new Map();
async function onDM(m) {
  if (!cfg.dm.enabled) return;
  const text = String(m.content || "").trim();
  if (!text) return;
  if (now() - (dmLast.get(m.author.id) || 0) < 1500) return;
  dmLast.set(m.author.id, now());
  let reply;
  if (/^\/?(code|код|2fa)$/i.test(text)) {
    reply = { text: "Код входа приходит сюда сам, когда вы входите на rteam.info (если Discord привязан в кабинете). Не пришёл — нажмите «Прислать ещё раз» на странице входа.", components: [] };
  } else if (/^\/?(help|помощь|start|старт|команды)$/i.test(text)) {
    reply = { text: "Я бот RTeam. Здесь можно:\n• спросить что угодно про RTeam и сайт — отвечает нейросеть Rai;\n• получать коды входа на rteam.info и уведомления (привяжите Discord в кабинете).\n\nНа сервере: /правила, /идея, /спросить, кнопка заявки в модераторы.", components: [] };
  } else {
    m.channel.sendTyping().catch(() => {});
    reply = await raiAnswer(m.author.id, text);
  }
  await m.reply({ content: reply.text, components: reply.components, allowedMentions: { repliedUser: false, parse: [] } })
    .catch((e) => log("⚠️ Ответ в ЛС:", e.message));
}

/* ============================== команды */

const S = 3, INT = 4, BOOL = 5, USER = 6, SUB = 1;
const opt = (type, name, ru, description, extra = {}) => ({ type, name, name_localizations: { ru }, description, ...extra });
function commandList() {
  const mod = String(P.ModerateMembers);
  return [
    { name: "rules", name_localizations: { ru: "правила" }, description: "Правила сервера (видите только вы)" },
    { name: "idea", name_localizations: { ru: "идея" }, description: "Предложить идею — она уйдёт на голосование",
      options: [opt(S, "text", "текст", "Опишите идею", { required: true, min_length: Math.max(1, I().min_length), max_length: Math.min(4000, I().max_length) })] },
    { name: "ask", name_localizations: { ru: "спросить" }, description: "Спросить ИИ Rai — ответ увидите только вы",
      options: [opt(S, "question", "вопрос", "Ваш вопрос", { required: true, max_length: 500 })] },
    { name: "link", name_localizations: { ru: "привязать" }, description: "Привязать Discord к аккаунту rteam.info" },
    { name: "warn", name_localizations: { ru: "пред" }, description: "Выдать предупреждение", default_member_permissions: mod,
      options: [opt(USER, "user", "участник", "Кому", { required: true }), opt(S, "reason", "причина", "За что", { required: true, max_length: 300 })] },
    { name: "warnings", name_localizations: { ru: "преды" }, description: "Предупреждения участника", default_member_permissions: mod,
      options: [opt(USER, "user", "участник", "Чьи предупреждения", { required: true })] },
    { name: "unwarn", name_localizations: { ru: "снять-пред" }, description: "Снять последнее предупреждение (или все)", default_member_permissions: mod,
      options: [opt(USER, "user", "участник", "С кого снять", { required: true }), opt(BOOL, "all", "все", "Снять все предупреждения")] },
    { name: "mute", name_localizations: { ru: "мут" }, description: "Мут (тайм-аут) участника", default_member_permissions: mod,
      options: [opt(USER, "user", "участник", "Кого", { required: true }), opt(INT, "minutes", "минуты", "На сколько минут (до 40320 = 28 дней)", { required: true, min_value: 1, max_value: 40320 }),
        opt(S, "reason", "причина", "За что", { max_length: 300 })] },
    { name: "unmute", name_localizations: { ru: "размут" }, description: "Снять мут", default_member_permissions: mod,
      options: [opt(USER, "user", "участник", "С кого снять мут", { required: true })] },
    { name: "clear", name_localizations: { ru: "очистить" }, description: "Удалить последние сообщения в канале", default_member_permissions: String(P.ManageMessages),
      options: [opt(INT, "count", "сколько", "Сколько сообщений (1–100)", { required: true, min_value: 1, max_value: 100 }),
        opt(USER, "user", "участник", "Только сообщения этого участника")] },
    { name: "setup", name_localizations: { ru: "настройка" }, description: "Настройка бота (для администрации)", default_member_permissions: String(P.Administrator),
      options: [opt(SUB, "panel", "заявки", "Отправить или обновить кнопку заявок в канале заявок"),
        opt(SUB, "rules", "правила", "Опубликовать или обновить правила в этом канале"),
        opt(SUB, "check", "проверка", "Проверить права бота, каналы и роли"),
        opt(SUB, "adminpanel", "админка", "Кнопка «Открыть админ-панель» в этом канале")] },
    { name: "admin", name_localizations: { ru: "админ" }, description: "Админ-панель: объявления, обзвон, активность (для администрации)" },
    { name: "level", name_localizations: { ru: "уровень" }, description: "Уровень и активность",
      options: [opt(USER, "user", "участник", "Чей уровень (по умолчанию ваш)")] },
    { name: "top", name_localizations: { ru: "топ" }, description: "Топ активности сервера" },
  ];
}

async function onCommand(i) {
  const name = i.commandName;
  if (name === "rules") return i.reply({ ...rulesPayload(), flags: EPH });
  if (name === "admin") return onPanel(i, "open");
  if (name === "level") {
    const u = i.options.getUser("user") || i.user;
    return i.reply({ embeds: [levelEmbed(u, i.options.getMember("user") || (u.id === i.user.id ? i.member : null))], allowedMentions: { parse: [] } });
  }
  if (name === "top") return i.reply({ embeds: [topEmbed(10)], allowedMentions: { parse: [] } });
  if (name === "link") {
    return i.reply({
      content: "Привяжите Discord к аккаунту rteam.info — тогда коды входа и уведомления сайта будут приходить сюда, в ЛС. " +
        "А ещё можно входить на сайт через Discord.",
      components: [row(linkButton("Привязать Discord", `${cfg.site_url}/discord_auth.php?mode=link`))], flags: EPH,
    });
  }
  if (name === "ask") {
    await i.deferReply({ flags: EPH });
    const r = await raiAnswer(i.user.id, i.options.getString("question", true));
    return i.editReply({ content: r.text, components: r.components });
  }
  if (name === "idea") {
    if (!I().enabled) return i.reply({ content: "Приём идей сейчас выключен.", flags: EPH });
    const left = ideaCooldown(i.user.id);
    if (left) return i.reply({ content: `⏳ Следующую идею можно отправить ${ts(now() + left)}.`, flags: EPH });
    const text = i.options.getString("text", true).trim();
    const v = AM().enabled ? automodCheck({ content: text, authorId: i.user.id }, { noHistory: true }) : null;
    if (v && (v.rule === "scam" || v.rule === "badwords" || v.rule === "invites")) return i.reply({ content: `❌ Идея не отправлена: ${v.reason}.`, flags: EPH });
    await i.deferReply({ flags: EPH });
    const r = await postIdea(i.user, i.member, text, null);
    return i.editReply(r.ok ? `✅ Идея #${r.n} отправлена на голосование: ${r.url}` : `❌ ${r.error}`);
  }
  if (name === "setup") {
    if (!isStaff(i)) return i.reply({ content: "Эта команда — для администрации.", flags: EPH });
    const sub = i.options.getSubcommand();
    await i.deferReply({ flags: EPH });
    try {
      if (sub === "panel") { const msg = await ensurePanel(); return i.editReply(`✅ Кнопка заявок на месте: ${msg.url}`); }
      if (sub === "adminpanel") { const msg = await ensureAdminPanel(i.channelId); return i.editReply(`✅ Кнопка «Открыть админ-панель»: ${msg.url}. Открыть её смогут только администраторы и роли из panel.role_ids.`); }
      if (sub === "rules") { const msg = await ensureRules(i.channelId); return i.editReply(`✅ Правила опубликованы: ${msg.url}`); }
      const report = await diagnose();
      return i.editReply(cut(report.map((x) => `${x.ok ? "✅" : "❌"} ${x.text}`).join("\n"), 1990));
    } catch (e) { return i.editReply(`❌ ${e.message}`); }
  }

  // модерация (права проверяет и Discord, и бот — на случай, если их поменяли в настройках сервера)
  const modPerm = name === "clear" ? P.ManageMessages : P.ModerateMembers;
  if (!hasPerm(i, modPerm) && !isStaff(i)) return i.reply({ content: "Эта команда — для модераторов.", flags: EPH });
  const target = i.options.getMember("user");
  const targetUser = i.options.getUser("user");
  if (name === "warnings") {
    const list = activeWarnings(targetUser.id);
    const txt = list.length ? list.map((w, k) => `**${k + 1}.** ${ts(w.t, "d")} — ${w.reason} (${w.by === "auto" ? "автомодерация" : `<@${w.by}>`})`).join("\n") : "Предупреждений нет.";
    return i.reply({ content: cut(`Предупреждения <@${targetUser.id}> (${list.length}):\n${txt}`, 1990), flags: EPH, allowedMentions: { parse: [] } });
  }
  if (name === "unwarn") {
    const list = data.warnings[targetUser.id] || [];
    const active = activeWarnings(targetUser.id);
    if (!active.length) return i.reply({ content: "У участника нет действующих предупреждений.", flags: EPH });
    if (i.options.getBoolean("all")) data.warnings[targetUser.id] = list.filter((w) => !active.includes(w));
    else data.warnings[targetUser.id] = list.filter((w) => w !== active[active.length - 1]);
    save();
    return i.reply({ content: `✅ Готово. Действующих предупреждений у <@${targetUser.id}>: ${activeWarnings(targetUser.id).length}.`, flags: EPH, allowedMentions: { parse: [] } });
  }
  if (name === "clear") {
    const count = i.options.getInteger("count", true);
    await i.deferReply({ flags: EPH });
    let deleted = 0;
    try {
      if (targetUser) {
        const list = await i.channel.messages.fetch({ limit: 100 });
        const mine = [...list.values()].filter((x) => x.author.id === targetUser.id).slice(0, count);
        deleted = mine.length ? (await i.channel.bulkDelete(mine, true)).size : 0;
      } else deleted = (await i.channel.bulkDelete(count, true)).size;
    } catch (e) { return i.editReply(`❌ Не удалось удалить: ${e.message}`); }
    return i.editReply(`🧹 Удалено сообщений: ${deleted}.` + (deleted < count ? " (Сообщения старше 14 дней Discord удалять пачкой не даёт.)" : ""));
  }
  if (!target) return i.reply({ content: "Этого участника нет на сервере.", flags: EPH });
  if (target.id === i.user.id) return i.reply({ content: "Нельзя применить к себе.", flags: EPH });
  if (!canModerate(i.member, target)) return i.reply({ content: "Нельзя: у участника роль не ниже вашей (или это бот/владелец).", flags: EPH });
  if (name === "warn") {
    const reason = i.options.getString("reason", true);
    const count = addWarning(target.id, reason, i.user.id);
    const minutes = timeoutFor(count);
    const muted = minutes ? await timeoutMember(target, minutes, `Предупреждений: ${count}`) : false;
    await i.reply({ content: `⚠️ <@${target.id}> получает предупреждение (${count}): ${reason}` + (muted ? `\n🔇 Мут на ${fmtMin(minutes)}.` : ""), allowedMentions: { users: [target.id] } });
    dmUser(target.id, { embeds: [{ color: COLORS.yellow, title: "⚠️ Предупреждение", description: `На сервере **${i.guild.name}**: ${reason}\nПредупреждений: **${count}**` + (nextStepText(count) ? ` — ${nextStepText(count)}.` : ".") + (muted ? `\n🔇 Мут на ${fmtMin(minutes)}.` : "") }] });
    return modLog({ color: COLORS.yellow, title: "⚠️ Предупреждение", description: `<@${target.id}> от <@${i.user.id}>: ${reason}\nВсего: ${count}${muted ? `, мут ${fmtMin(minutes)}` : ""}` });
  }
  if (name === "mute") {
    const minutes = i.options.getInteger("minutes", true), reason = i.options.getString("reason") || "без причины";
    if (!(await timeoutMember(target, minutes, `${reason} (${i.user.tag})`))) return i.reply({ content: "❌ Не удалось: у бота нет права на тайм-аут или роль участника выше роли бота.", flags: EPH });
    await i.reply({ content: `🔇 <@${target.id}> в муте на ${fmtMin(minutes)}: ${reason}`, allowedMentions: { users: [target.id] } });
    return modLog({ color: COLORS.yellow, title: "🔇 Мут", description: `<@${target.id}> на ${fmtMin(minutes)} от <@${i.user.id}>: ${reason}` });
  }
  if (name === "unmute") {
    try { await target.timeout(null, `Снят мут (${i.user.tag})`); } catch (e) { return i.reply({ content: `❌ ${e.message}`, flags: EPH }); }
    await i.reply({ content: `🔊 С <@${target.id}> снят мут.`, allowedMentions: { parse: [] } });
    return modLog({ color: COLORS.green, title: "🔊 Мут снят", description: `<@${target.id}> — <@${i.user.id}>` });
  }
}

async function onButton(i) {
  const [scope, action, id, extra] = i.customId.split(":");
  if (scope === "adm") return onPanel(i, action, id, extra);
  if (scope !== "app") return;
  if (action === "start") return startApplication(i);
  if (action === "next") {
    const d = data.drafts[i.user.id];
    if (!d || d.page >= pagesCount() || now() - d.t > 3600e3) return i.update({ content: "Форма устарела. Нажмите «Подать заявку» ещё раз.", components: [] });
    return i.showModal(appModal(d.page));
  }
  if (action === "cancel") { delete data.drafts[i.user.id]; save(); return i.update({ content: "Заявка отменена.", components: [] }); }
  if (["call", "rej", "acc"].includes(action)) return reviewButton(i, action, id);
}

async function onModal(i) {
  const [scope, action, arg] = i.customId.split(":");
  if (scope === "adm") return onPanelModal(i, action, arg);
  if (scope !== "app") return;
  if (action === "p") return onAppPage(i, Number(arg) || 0);
  if (action === "rejm") return onRejectModal(i, arg);
}

/* ============================== проверка настроек */

async function diagnose() {
  const out = [], ok = (text) => out.push({ ok: true, text }), bad = (text) => out.push({ ok: false, text });
  const g = guild();
  if (!g) { bad(`Бот не добавлен на сервер ${cfg.guild_id}. Пригласите его: ${inviteUrl()}`); return out; }
  ok(`Сервер: ${g.name}`);
  const me = g.members.me || await g.members.fetchMe().catch(() => null);
  if (!me) { bad("Не удалось получить данные бота на сервере"); return out; }
  const need = async (id, what, perms) => {
    if (!isId(id)) { bad(`${what}: не указан ID канала в config.json`); return; }
    const ch = await chan(id);
    if (!ch || ch.guildId !== g.id) { bad(`${what}: канал ${id} не найден или бот его не видит`); return; }
    const p = ch.permissionsFor(me);
    const miss = perms.filter((f) => !p || !p.has(f));
    if (miss.length) bad(`${what} #${ch.name}: у бота нет прав — ${miss.map(permName).join(", ")}`);
    else ok(`${what}: #${ch.name}`);
  };
  const base = [P.ViewChannel, P.SendMessages, P.EmbedLinks, P.ReadMessageHistory];
  if (A().enabled) {
    await need(A().panel_channel_id, "Канал заявок (кнопка)", base);
    await need(A().review_channel_id, "Канал рассмотрения заявок", [...base, P.AttachFiles]);
    for (const [rid, what] of [[A().call_role_id, "Роль для обзвона"], [A().accept_role_id, "Роль для принятых"]]) {
      if (!isId(rid)) { if (what === "Роль для обзвона") bad(`${what}: не указана в config.json`); continue; }
      const role = g.roles.cache.get(rid);
      if (!role) bad(`${what}: роль ${rid} не найдена на сервере`);
      else if (!me.permissions.has(P.ManageRoles)) bad(`${what} «${role.name}»: у бота нет права «Управлять ролями»`);
      else if (role.position >= me.roles.highest.position) bad(`${what} «${role.name}» выше роли бота — Настройки сервера → Роли: перетащите роль бота выше неё`);
      else ok(`${what}: «${role.name}»`);
    }
    if (!questions().length) bad("Заявки: в config.json нет вопросов");
  }
  if (I().enabled) {
    await need(I().input_channel_id, "Канал идей", [...base, P.ManageMessages]);
    await need(I().vote_channel_id, "Канал голосования за идеи", [...base, P.AddReactions, P.AttachFiles, ...(I().one_vote ? [P.ManageMessages] : [])]);
  }
  for (const c of (PN().announce_channels || []).filter((x) => isId(x.id))) {
    await need(c.id, `Объявления «${c.name}»`, base);
    const ch = await chan(c.id);
    if (ch && ch.permissionsFor && !ch.permissionsFor(me).has(P.MentionEveryone)) bad(`Объявления «${c.name}»: нет права «Упоминание @everyone» — кнопка «С пингом @everyone» не будет пинговать`);
  }
  for (const vc of ids(PN().call_voice_channel_ids)) await need(vc, "Голосовой канал обзвона", [P.ViewChannel, P.SendMessages]);
  if (ids(PN().call_voice_channel_ids).length && !me.permissions.has(P.MoveMembers)) bad("Обзвон: нет права «Перемещать участников» — бот будет звать сообщением, но не сможет перенести кандидата из другого голосового канала");
  for (const rid of ids(PN().role_ids)) { const r = g.roles.cache.get(rid); if (r) ok(`Роль админ-панели: «${r.name}»`); else bad(`Роль админ-панели ${rid} не найдена на сервере`); }
    if (isId(cfg.rules.channel_id)) await need(cfg.rules.channel_id, "Канал правил", base);
  if (isId(cfg.log_channel_id)) await need(cfg.log_channel_id, "Канал логов модерации", [P.ViewChannel, P.SendMessages, P.EmbedLinks]);
  else bad("Канал логов модерации не указан (log_channel_id) — нарушения не будут записываться");
  if (AM().enabled) {
    if (!me.permissions.has(P.ManageMessages)) bad("Автомодерация: нет права «Управлять сообщениями» — бот не сможет удалять нарушения");
    else if (!me.permissions.has(P.ModerateMembers)) bad("Автомодерация: нет права на тайм-аут — бот будет только удалять сообщения, без мутов");
    else ok("Автомодерация: права есть");
  }
  ok(rai.lib ? "Нейросеть Rai для ЛС загружена" : "Нейросеть Rai ещё не загружена (загрузится при первом вопросе)");
  return out;
}

/* ============================== подключение к Discord */

function createClient() {
  const c = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent,
      GatewayIntentBits.GuildMessageReactions, GatewayIntentBits.DirectMessages, GatewayIntentBits.GuildVoiceStates],
    partials: [Partials.Channel, Partials.Message, Partials.Reaction, Partials.User],
    allowedMentions: { parse: ["users"], repliedUser: false },
    ...(API_BASE ? { rest: { api: API_BASE } } : {}),
  });
  c.once(Events.ClientReady, () => onReady().catch((e) => log("❌ Запуск:", e.message)));
  c.on(Events.GuildCreate, (g) => { if (g.id === cfg.guild_id) setupGuild().catch((e) => log("❌", e.message)); });
  c.on(Events.InteractionCreate, (i) => {
    if (i.guildId && i.guildId !== cfg.guild_id) return;
    const run = i.isChatInputCommand() ? onCommand(i) : i.isButton() ? onButton(i) : i.isModalSubmit() ? onModal(i)
      : i.isStringSelectMenu() && i.customId === "adm:cand" ? onPanel(i, "cand") : null;
    if (run) run.catch(async (e) => {
      log(`❌ ${i.customId || i.commandName}:`, e.stack || e.message);
      const msg = { content: "⚠️ Что-то пошло не так. Попробуйте ещё раз или сообщите администрации.", flags: EPH };
      try { if (i.deferred || i.replied) await i.followUp(msg); else await i.reply(msg); } catch (e2) { /* ответ уже невозможен */ }
    });
  });
  c.on(Events.MessageCreate, (m) => onMessage(m).catch((e) => log("❌ Сообщение:", e.stack || e.message)));
  c.on(Events.MessageUpdate, (o, m) => onEdit(o, m).catch((e) => log("❌ Правка:", e.message)));
  c.on(Events.MessageReactionAdd, (r, u) => onReaction(r, u).catch((e) => log("❌ Реакция:", e.message)));
  c.on(Events.Error, (e) => log("❌ Discord:", e.message));
  return c;
}

async function onMessage(m) {
  if (!m.author || m.author.bot || m.webhookId || m.system) return;
  if (!m.guildId) return onDM(m);
  if (m.guildId !== cfg.guild_id) return;
  if (AM().enabled && !isExempt(m)) {
    const v = automodCheck({ id: m.id, authorId: m.author.id, channelId: m.channelId, content: m.content, t: m.createdTimestamp });
    if (v) return applyVerdict(m, v);
  }
  if (I().enabled && m.channelId === I().input_channel_id) return ideaFromMessage(m);
  await messageXp(m);
}
async function onEdit(old, m) {
  if (m.partial || !m.guildId || m.guildId !== cfg.guild_id || !m.author || m.author.bot) return;
  if (old && !old.partial && old.content === m.content) return;
  if (!AM().enabled || isExempt(m) || m.channelId === I().input_channel_id) return;
  const v = automodCheck({ id: m.id, authorId: m.author.id, channelId: m.channelId, content: m.content }, { noHistory: true });
  if (v) return applyVerdict(m, v);
}

/* Команды и начальные сообщения бота (кнопка заявок, правила, подсказка в канале идей).
   fresh — удалить старые и написать заново (кнопка «Перезапустить бота» в админ-панели). Возвращает отчёт. */
async function setupGuild(fresh = false) {
  const out = [], ok = (text) => out.push({ ok: true, text }), bad = (text) => { out.push({ ok: false, text }); log("❌", text); };
  const g = guild();
  if (!g) { bad(`Бот не добавлен на сервер ${cfg.guild_id}. Пригласите его: ${inviteUrl()}`); return out; }
  await g.commands.set(commandList()).then(() => { ok("Команды зарегистрированы"); log("✅ Команды зарегистрированы"); }).catch((e) => bad("Команды: " + e.message));
  const step = async (what, fn) => { try { const m = await fn(); ok(`${what}: ${m.url}`); } catch (e) { bad(`${what}: ${e.message}`); } };
  if (A().enabled) await step("Кнопка заявок", () => ensurePanel(fresh));
  if (isId(cfg.rules.channel_id)) await step("Правила", () => ensureRules(null, fresh));
  else if (fresh && data.messages.rules && data.messages.rules.channel) await step("Правила", () => ensureRules(data.messages.rules.channel, true));
  if (I().enabled && I().info_message) await step("Подсказка в канале идей", () => ensureIdeasInfo(fresh));
  const adminCh = isId(PN().channel_id) ? PN().channel_id : data.messages.admin_panel && data.messages.admin_panel.channel;
  if (adminCh && (fresh || isId(PN().channel_id))) await step("Кнопка админ-панели", () => ensureAdminPanel(adminCh, fresh));
  for (const x of await diagnose()) if (!x.ok) { out.push(x); log("⚠️", x.text); }
  return out;
}
/* Перезапуск из админ-панели: перечитать config.json, заново зарегистрировать команды и написать начальные сообщения */
async function restartBot() {
  cfg = loadConfig();
  if (cfg.token) rest.setToken(cfg.token);
  if (!client || !client.isReady()) {
    if (mode === "offline" && cfg.token) { await goActive(); return [{ ok: !!(client && client.isReady()), text: client && client.isReady() ? "Бот подключился к Discord" : "Бот не подключился: " + lastError }]; }
    return [{ ok: false, text: mode === "standby" ? "Эта копия в резерве — повторите через минуту" : "Бот не подключён к Discord: " + (lastError || mode) }];
  }
  log("🔄 Перезапуск из админ-панели");
  return [{ ok: true, text: "config.json перечитан" }, ...await setupGuild(true)];
}
async function onReady() {
  lastError = "";
  log(`✅ ${client.user.tag} в сети`);
  await setupGuild();
  ensureRai().catch(() => {});
}

/* Одна копия на связи с Discord. Passenger (Plesk) иногда запускает вторую — она ждёт в резерве
   и отвечает только на HTTP. Кто подключён, раз в 20 секунд отмечается в bot.lock. */
const LOCK_FILE = path.join(DIR, "bot.lock");
let lockNonce = "";
function readLock() { return readJson(LOCK_FILE, null); }
function pidAlive(pid) { try { process.kill(pid, 0); return true; } catch (e) { return e.code === "EPERM"; } }
const heldByOther = (l) => !!(l && l.nonce !== lockNonce && pidAlive(l.pid) && now() - l.time < 70000);
const writeLock = () => writeJsonAtomic(LOCK_FILE, { pid: process.pid, nonce: lockNonce, time: now() });
async function takeLock() {
  if (heldByOther(readLock())) return false;
  lockNonce = crypto.randomBytes(8).toString("hex");
  writeLock();
  await sleep(1500);
  const l = readLock();
  return !!(l && l.nonce === lockNonce);
}

let loginTimer = null;
async function goActive() {
  mode = "active";
  data = loadData();
  client = createClient();
  try {
    await client.login(cfg.token);
  } catch (e) {
    if (/disallowed intents/i.test(e.message)) lastError = "Discord не пускает бота: включите Message Content Intent — Developer Portal → Bot → Privileged Gateway Intents → Save, потом Restart App";
    else if (/token/i.test(e.message)) lastError = "неверный токен бота — Developer Portal → Bot → Reset Token и вставьте новый в secret.json";
    else lastError = "не удалось подключиться к Discord: " + e.message;
    log("❌", lastError);
    try { client.destroy(); } catch (e2) { /* уже закрыт */ }
    client = null;
    mode = "offline";
    clearTimeout(loginTimer);
    loginTimer = setTimeout(() => { if (mode === "offline") goActive(); }, 120000);
  }
}
async function goStandby() {
  mode = "standby";
  saveNow();
  if (client) { try { await client.destroy(); } catch (e) { /* ок */ } client = null; }
}
async function lockTick() {
  if (mode === "active" || mode === "offline") {
    const l = readLock();
    if (heldByOther(l)) { log("ℹ️ Работает другая копия бота — перехожу в резерв"); return goStandby(); }
    writeLock();
  } else if (mode === "standby" && await takeLock()) {
    log("ℹ️ Другая копия остановилась — подключаюсь к Discord");
    return goActive();
  }
}

/* ============================== HTTP для сайта */

function sendJson(res, status, obj) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
  res.end(JSON.stringify(obj));
}
function authorized(req) {
  if (!cfg.api_key) return false;
  const given = String(req.headers["x-api-key"] || (req.headers.authorization || "").replace(/^Bearer\s+/i, ""));
  const a = crypto.createHash("sha256").update(given).digest(), b = crypto.createHash("sha256").update(cfg.api_key).digest();
  return crypto.timingSafeEqual(a, b);
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on("data", (c) => { size += c.length; if (size > 32768) { reject(new Error("too_large")); req.destroy(); } else chunks.push(c); });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}
async function handleHttp(req, res) {
  const url = new URL(req.url, "http://localhost");
  const p = url.pathname.replace(/\/+$/, "") || "/";
  if (req.method === "GET" && (p === "/" || p === "/health")) {
    const online = !!(client && client.isReady());
    const reason = online ? (guild() ? "" : `бот не добавлен на сервер — пригласите: ${inviteUrl()}`)
      : mode === "standby" ? "работает другая копия бота" : lastError || "подключается к Discord…";
    if (p === "/" && /text\/html/.test(req.headers.accept || "")) {
      const esc = (t) => String(t).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
      return res.end(`<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Discord-бот RTeam</title>
<style>body{font:16px/1.5 system-ui,sans-serif;background:#111827;color:#e5e7eb;margin:0;padding:32px 16px}main{max-width:640px;margin:auto}.ok{color:#4ade80}.bad{color:#f87171}code{background:#1f2937;padding:2px 6px;border-radius:6px}</style></head>
<body><main><h1>Discord-бот RTeam</h1><p class="ok">✅ Приложение запущено — Node.js в Plesk работает.</p>
<p class="${online && !reason ? "ok" : "bad"}">${online ? `✅ В Discord: в сети как <b>${esc(client.user.tag)}</b>${guild() ? `, сервер «${esc(guild().name)}»` : ""}` : "❌ В Discord: не в сети"}</p>
${reason ? `<p class="bad">Причина: ${esc(reason)}</p>` : ""}
<p>Ключ для сайта: ${cfg.api_key ? "✅ задан" : "❌ не задан — впишите api_key в secret.json"}</p><p>Версия бота: <code>${BOT_VERSION}</code></p></main></body></html>`);
    }
    return sendJson(res, 200, { ok: true, service: "rteam-discord-bot", version: BOT_VERSION, online, mode, reason });
  }
  if (p !== "/dm" && p !== "/status" && p !== "/restart") return sendJson(res, 404, { ok: false, error: "not_found" });
  if (!cfg.api_key) return sendJson(res, 503, { ok: false, error: "api_key_not_set" });
  if (!authorized(req)) return sendJson(res, 403, { ok: false, error: "forbidden" });
  if (p === "/restart") {
    if (req.method !== "POST") return sendJson(res, 405, { ok: false, error: "method" });
    const report = await restartBot().catch((e) => [{ ok: false, text: e.message }]);
    return sendJson(res, 200, { ok: report.every((x) => x.ok), report });
  }
  if (p === "/status") {
    const report = { ok: true, version: BOT_VERSION, mode, online: !!(client && client.isReady()), bot: client && client.user ? client.user.tag : null,
      guild: guild() ? guild().name : null, invite_url: inviteUrl(), last_error: lastError || null, rai: !!rai.lib, checks: [] };
    if (report.online) report.checks = await diagnose().catch((e) => [{ ok: false, text: e.message }]);
    else if (mode === "standby") report.checks = [{ ok: true, text: "Эта копия в резерве — с Discord работает другая" }];
    return sendJson(res, 200, report);
  }
  if (req.method !== "POST") return sendJson(res, 405, { ok: false, error: "method" });
  let body;
  try { body = JSON.parse(await readBody(req) || "{}"); } catch (e) { return sendJson(res, 400, { ok: false, error: "bad_json" }); }
  const uid = String(body.user_id || "");
  const text = String(body.text || "").trim();
  if (!isId(uid) || !text) return sendJson(res, 400, { ok: false, error: "user_id_and_text_required" });
  const embed = { color: Number(body.color) || COLORS.blurple, description: cut(text, 4000), footer: { text: "rteam.info" } };
  if (body.title) embed.title = cut(body.title, 256);
  const msg = { embeds: [embed] };
  if (body.button && /^https:\/\//.test(String(body.button.url || ""))) {
    msg.components = [row(linkButton(cut(body.button.label || "Открыть", 80), cut(body.button.url, 512)))];
  }
  const r = await dmUser(uid, msg);
  return sendJson(res, r.ok ? 200 : 502, r.ok ? { ok: true } : { ok: false, error: r.error });
}

/* ============================== запуск */

let server = null, timers = [];
async function start() {
  server = http.createServer((req, res) => handleHttp(req, res).catch((e) => { log("❌ HTTP:", e.message); sendJson(res, 500, { ok: false, error: "internal" }); }));
  const port = process.env.PORT || cfg.port || 3000;
  server.listen(port, () => log(`🌐 HTTP на порту ${port}, версия бота ${BOT_VERSION}`));
  if (!cfg.token) { mode = "offline"; lastError = "нет токена: положите secret.json (с токеном) рядом с index.js и нажмите Restart App"; log("❌", lastError); return; }
  if (await takeLock()) await goActive();
  else { mode = "standby"; log("ℹ️ Бот уже работает в другой копии — эта в резерве"); }
  timers.push(setInterval(() => lockTick().catch((e) => log("⚠️ lock:", e.message)), Number(process.env.RAI_BOT_LOCK_TICK) || 20000));
  // Plesk (Passenger) усыпляет приложение без HTTP-запросов — бот сам стучится к себе
  if (cfg.public_url) timers.push(setInterval(() => fetch(cfg.public_url + "/health").catch(() => {}), 120000));
  timers.push(setInterval(() => { try { voiceTick(); } catch (e) { log("⚠️ Голос:", e.message); } }, Number(process.env.RAI_BOT_VOICE_TICK) || 60000));
  timers.push(setInterval(() => { // старые черновики заявок
    let changed = false;
    for (const [k, d] of Object.entries(data.drafts)) if (now() - d.t > 3600e3) { delete data.drafts[k]; changed = true; }
    if (changed) save();
  }, 600000));
}
async function stop() {
  timers.forEach(clearInterval); timers = [];
  clearTimeout(loginTimer);
  saveNow();
  const l = readLock();
  if (l && l.nonce === lockNonce) { try { fs.unlinkSync(LOCK_FILE); } catch (e) { /* уже нет */ } }
  if (client) { try { await client.destroy(); } catch (e) { /* ок */ } client = null; }
  if (server) await new Promise((r) => server.close(() => r()));
}

if (process.env.RAI_BOT_TEST !== "1") {
  process.on("unhandledRejection", (e) => log("⚠️", e && (e.stack || e.message || e)));
  for (const sig of ["SIGTERM", "SIGINT"]) process.on(sig, () => { log("Остановка…"); stop().finally(() => process.exit(0)); setTimeout(() => process.exit(0), 3000).unref(); });
  start().catch((e) => { log("❌ Бот не запустился:", e.message); });
}

module.exports = {
  start, stop, automodCheck, findBadWord, filterVariants, isScam, linksOf, timeoutFor, nextStepText, appEmbed, appModal,
  commandList, panelPayload, rulesPayload, supportUrl, raiAnswer, evalRai, idFromToken, inviteUrl, plural, fmtMin,
  get data() { return data; }, get cfg() { return cfg; }, get mode() { return mode; }, get client() { return client; },
  _reset() { data = EMPTY_DATA(); recent.clear(); ideaAt.clear(); noticeAt.clear(); dmAt.clear(); dmHistory.clear(); cfg = loadConfig(); },
};
