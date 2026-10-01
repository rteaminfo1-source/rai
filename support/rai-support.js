/*
 * Rai Support — своя нейросеть поддержки rteam.info. Работает прямо в браузере.
 *
 * Страницы сайта (support.php, admin.php) ничего не знают о нейросети: они загружают этот файл
 * и model.json с GitHub и спрашивают RaiSupport.reply(...). Вся нейросеть — здесь и в model.json.
 *
 *   await RaiSupport.load("https://raw.githubusercontent.com/<владелец>/rai/<ветка>/support/");
 *   const r = await RaiSupport.reply("не приходит код из бота", { history, topic, mode: "client" });
 *   // r = { reply, handoff, source, confidence, intent }
 *
 * Сеть: признаки текста (слова, начала слов, буквенные тройки, пары слов → хеш FNV-1a)
 * → скрытый слой ReLU → softmax по темам. Обучение — support/train.py, признаки — support/nn.py
 * (здесь ровно то же самое; тест проверяет, что Python и браузер отвечают одинаково).
 *
 * Чего сеть не делает: не знает паролей, токенов и других секретов — их ей не передают,
 * а на такие просьбы она отвечает отказом. Оплату, баны и апелляции сразу передаёт администратору.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.RaiSupport = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const VERSION = "1.0";
  const CONFIDENT = 0.5;      // ниже — сеть не уверена: уточняем или ищем на сайте и в интернете
  const SITE_TTL = 30 * 60 * 1000;

  /* ============================== признаки (как в nn.py) */

  const normalize = (t) => String(t == null ? "" : t).toLowerCase().replace(/ё/g, "е");
  const words = (t) => normalize(t).match(/[a-zа-я0-9]+/g) || [];

  function features(text) {
    const ws = words(text), feats = new Set();
    ws.forEach((w, i) => {
      feats.add("w:" + w);
      if (w.length > 5) feats.add("s:" + w.slice(0, 5));
      if (w.length >= 2) {
        const g = "<" + w + ">";
        for (let j = 0; j < g.length - 2; j++) feats.add("c:" + g.slice(j, j + 3));
      }
      if (i + 1 < ws.length) feats.add("b:" + w.slice(0, 5) + "_" + ws[i + 1].slice(0, 5));
    });
    return feats;
  }

  function fnv1a(s) {
    let h = 2166136261;
    for (const ch of s) {
      h ^= ch.codePointAt(0);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h >>> 0;
  }

  function indices(text, dims) {
    const set = new Set();
    for (const f of features(text)) set.add(fnv1a(f) % dims);
    return [...set].sort((a, b) => a - b);
  }

  /* ============================== сеть */

  function b64bytes(b64) {
    if (typeof atob === "function") {
      const s = atob(b64), out = new Uint8Array(s.length);
      for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
      return out;
    }
    return new Uint8Array(Buffer.from(b64, "base64"));
  }

  class Model {
    constructor(m) {
      if (m.format !== "rai-support-mlp-1") throw new Error("Неизвестный формат модели: " + m.format);
      this.meta = m;
      this.dims = m.dims; this.hidden = m.hidden;
      this.intents = m.intents;
      this.ids = m.intents.map((it) => it.id);
      const q = new Int8Array(b64bytes(m.w1.data).buffer), H = this.hidden;
      this.w1 = new Float32Array(q.length);
      for (let i = 0; i < q.length; i++) this.w1[i] = q[i] * m.w1.scale[i % H];
      this.b1 = m.b1; this.w2 = m.w2; this.b2 = m.b2;
    }

    probs(text) {
      const idx = indices(text, this.dims), H = this.hidden, K = this.ids.length;
      if (!idx.length) return this.ids.map((id) => (id === "other" ? 1 : 0));
      const s = 1 / Math.sqrt(idx.length), hid = new Float64Array(this.b1);
      for (const i of idx) {
        const off = i * H;
        for (let j = 0; j < H; j++) hid[j] += s * this.w1[off + j];
      }
      const logits = new Float64Array(this.b2);
      for (let j = 0; j < H; j++) {
        const v = hid[j];
        if (v > 0) { const row = this.w2[j]; for (let k = 0; k < K; k++) logits[k] += v * row[k]; }
      }
      const top = Math.max(...logits);
      const ex = Array.from(logits, (v) => Math.exp(v - top));
      const sum = ex.reduce((a, b) => a + b, 0);
      return ex.map((v) => v / sum);
    }

    predict(text, top = 3) {
      const p = this.probs(text);
      return p.map((v, k) => ({ id: this.ids[k], p: v })).sort((a, b) => b.p - a.p).slice(0, top);
    }

    intent(id) { return this.intents.find((it) => it.id === id) || null; }
  }

  /* ============================== безопасность */

  const SW = "(парол[а-я]*|password[a-z]*|passwd|токен[а-я]*|token[a-z]*|секрет[а-я]*|secret[a-z]*|api[\\s-]?ключ[а-я]*|ключ[а-я]*\\s+api|cookie[a-z]*|куки|сесси[а-я]+|cvv|данные\\s+карты)";
  const ASK = "(скажи|скажите|дай|дайте|покажи|покажите|назови|скинь|пришли|напиши|узна[а-я]*|выдай|слей|раскрой|подскажи|какой|какие|tell|give|show|send)";
  const WHOSE = "(админ[а-я]*|руководител[а-я]*|друг[а-я]*|чуж[а-я]*|друго[а-я]*|бот[а-я]*|сайт[а-я]*|баз[а-я]*|users|пользовател[а-я]*|сотрудник[а-я]*|директор[а-я]*|сервер[а-я]*|ftp)";
  const SECRET_RE = new RegExp(`${ASK}[^]{0,40}${SW}|${SW}[^]{0,40}${WHOSE}|${WHOSE}[^]{0,20}${SW}`, "i");
  const OWN_PASSWORD_RE = /(забыл|не помню|сменить|поменять|изменить|восстанов|сброс|смена|не подходит|неверн)/;

  // Что вырезаем из любого найденного текста: вдруг на странице оказался секрет
  const REDACT = [
    [/\b\d{6,12}:[A-Za-z0-9_-]{30,}\b/g, "[скрыто]"],                         // токен Telegram-бота
    [/\b[A-Fa-f0-9]{32,}\b/g, "[скрыто]"],                                     // длинные ключи
    [/(pass(?:word)?|пароль|token|secret|key)(\s*[:=]\s*)\S+/gi, "$1: [скрыто]"],
    [/\b(?:\d[ -]?){13,19}\b/g, "[скрыто]"],                                   // номера карт
  ];
  const redact = (t) => REDACT.reduce((s, [re, rep]) => s.replace(re, rep), String(t));

  /* ============================== страницы сайта */

  const STOP = new Set("как что где когда кто это для или так все уже еще есть нет мне меня вас вам нас наш ваш при про над под без его она они оно мой моя мои твой если чтобы можно нужно надо очень тоже только там тут где какой какая какие почему зачем сколько".split(" "));
  const stems = (t) => new Set(words(t).filter((w) => w.length > 2 && !STOP.has(w)).map((w) => w.slice(0, 5)));

  function htmlToText(html) {
    let s = String(html)
      .replace(/<(script|style|svg|noscript|template)\b[\s\S]*?<\/\1>/gi, " ")
      .replace(/<!--[\s\S]*?-->/g, " ")
      .replace(/<br\s*\/?>|<\/(p|div|li|h[1-6]|section|article|tr|summary|details)>/gi, "\n")
      .replace(/<[^>]+>/g, " ");
    s = s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&laquo;/g, "«").replace(/&raquo;/g, "»").replace(/&mdash;/g, "—");
    return s.split("\n").map((l) => l.replace(/\s+/g, " ").trim()).filter((l) => l.length > 2).join("\n");
  }

  function chunks(text, size = 420) {
    const out = []; let cur = "";
    for (const line of text.split("\n")) {
      if (cur.length + line.length > size && cur) { out.push(cur.trim()); cur = ""; }
      cur += " " + line;
    }
    if (cur.trim()) out.push(cur.trim());
    return out.filter((c) => c.length > 40);
  }

  const site = { chunks: [], loadedAt: 0, loading: null };

  async function loadSite(pages) {
    if (site.loadedAt && Date.now() - site.loadedAt < SITE_TTL) return site.chunks;
    if (site.loading) return site.loading;
    site.loading = (async () => {
      const all = [];
      for (const url of pages) {
        try {
          const r = await fetch(url, { credentials: "omit" });
          if (!r.ok) continue;
          for (const c of chunks(redact(htmlToText(await r.text())))) all.push({ url, text: c, stems: stems(c) });
        } catch (e) { /* страница недоступна — берём остальные */ }
      }
      site.chunks = all; site.loadedAt = Date.now(); site.loading = null;
      return all;
    })();
    return site.loading;
  }

  async function searchSite(query, pages) {
    const want = stems(query);
    if (want.size < 1 || !pages || !pages.length) return null;
    let best = null, bestScore = 0;
    for (const ch of await loadSite(pages)) {
      let hit = 0;
      for (const w of want) if (ch.stems.has(w)) hit++;
      const score = hit / want.size;
      if (hit >= 2 && score > bestScore) { best = ch; bestScore = score; }
    }
    return best && bestScore >= 0.5 ? { chunk: best, score: bestScore } : null;
  }

  /* ============================== интернет */

  const QUESTION_WORDS = /^(найди|поищи|загугли|погугли|расскажи( мне)? (про|о)|что такое|что за|кто такой|кто такая|кто такие|что значит)\s+|\s+в интернете|[?!.]+$/gi;
  const relevant = (query, text) => {
    const want = stems(query), have = stems(text);
    if (!want.size) return true;
    let hit = 0; for (const w of want) if (have.has(w)) hit++;
    return hit * 2 >= want.size;
  };
  const firstSentences = (t, n = 3) => (String(t).match(/[^.!?]+[.!?]+/g) || [String(t)]).slice(0, n).join("").trim();

  async function searchWeb(query, searchUrl) {
    const q = query.replace(QUESTION_WORDS, "").trim() || query;
    // Википедия (разрешает запросы с любых сайтов)
    try {
      const api = "https://ru.wikipedia.org/w/api.php?action=query&list=search&srlimit=3&format=json&origin=*&srsearch=" + encodeURIComponent(q);
      const found = (await (await fetch(api)).json()).query.search || [];
      for (const item of found.slice(0, 2)) {
        const sum = await (await fetch("https://ru.wikipedia.org/api/rest_v1/page/summary/" + encodeURIComponent(item.title))).json();
        if (sum.extract && relevant(q, sum.title + " " + sum.extract.slice(0, 600))) {
          const link = (sum.content_urls && sum.content_urls.desktop && sum.content_urls.desktop.page) || "";
          return { text: `${sum.title}\n\n${firstSentences(sum.extract)}` + (link ? `\n\nИсточник: ${link}` : ""), links: link ? [link] : [] };
        }
      }
    } catch (e) { /* Википедия недоступна */ }
    // Поиск Google / DuckDuckGo через net.php на хостинге (если указан)
    if (searchUrl) {
      try {
        const res = await (await fetch(searchUrl + (searchUrl.includes("?") ? "&" : "?") + "n=4&search=" + encodeURIComponent(q))).json();
        const items = (res.results || []).filter((r) => relevant(q, r.title + " " + (r.snippet || ""))).slice(0, 3);
        if (items.length) {
          return { text: "Вот что нашёл в интернете:\n\n" + items.map((r) => `• ${r.title}${r.snippet ? " — " + firstSentences(r.snippet, 2) : ""}\n${r.url}`).join("\n\n"), links: items.map((r) => r.url) };
        }
      } catch (e) { /* поиск недоступен */ }
    }
    return null;
  }

  /* ============================== разговор */

  const clientMessages = (history) => (Array.isArray(history) ? history : [])
    .filter((h) => h && h.from === "client").map((h) => String(h.text || "").slice(0, 600)).slice(-6);
  const alreadySaid = (history, answer) => {
    const key = normalize(answer).slice(0, 200);
    return (Array.isArray(history) ? history : []).some((h) => h && h.from === "ai" && normalize(h.text).slice(0, 200) === key);
  };

  const api = {
    VERSION, Model, model: null, base: "",
    features, indices, fnv1a, words, normalize, redact, htmlToText,

    /** Загрузить модель: base — папка на GitHub (или где угодно), где лежит model.json */
    async load(base, options = {}) {
      const url = String(base || "").replace(/\/?$/, "/") + "model.json";
      const r = await fetch(url, { cache: options.cache || "default" });
      if (!r.ok) throw new Error("model.json: HTTP " + r.status);
      api.model = new Model(await r.json());
      api.base = base;
      return api.model;
    },

    /** Модель уже в памяти (для тестов и своих сборок) */
    use(modelJson) { api.model = new Model(modelJson); return api.model; },

    predict(text, top = 3) {
      if (!api.model) throw new Error("Сначала RaiSupport.load(...)");
      return api.model.predict(text, top);
    },

    /**
     * Ответ на сообщение клиента.
     * opts.history — [{from: "client"|"admin"|"ai", text}], opts.topic — тема тикета,
     * opts.mode — "client" (ответ от имени Rai) или "draft" (черновик для сотрудника),
     * opts.sitePages — адреса страниц сайта для поиска, opts.searchUrl — net.php для поиска в интернете.
     * Возвращает {reply, handoff, source, confidence, intent}; handoff — передать тикет администратору.
     */
    async reply(message, opts = {}) {
      if (!api.model) throw new Error("Сначала RaiSupport.load(...)");
      const m = api.model;
      const history = opts.history || [], draft = opts.mode === "draft";
      const text = String(message || "").trim().slice(0, 2000);
      const pages = opts.sitePages === undefined ? ["/", "/team.php", "/projects.php"] : opts.sitePages;

      const out = (reply, source, confidence, handoff = false, intent = null) => {
        reply = redact(reply);
        if (draft && !/^здравствуйте/i.test(reply)) reply = "Здравствуйте! " + reply;
        return { reply, handoff: !!handoff && !draft, source, confidence: Math.round(confidence * 100) / 100, intent };
      };
      const answerOf = (it) => (draft && it.draft ? it.draft : it.answer);
      const siteAnswer = (found) => {
        const snippet = found.chunk.text.slice(0, 500).replace(/\s+\S*$/, "");
        const tail = draft ? "" : "\n\nЕсли это не то, что нужно, уточните вопрос или нажмите «Позвать администратора».";
        return out(`Вот что сказано об этом на сайте:\n\n«${snippet}…»\n\nПодробнее: ${found.chunk.url}${tail}`, "site", found.score * 0.8);
      };

      if (!text) return out("Напишите, пожалуйста, ваш вопрос — я постараюсь помочь.", "empty", 0.2);

      // 1. Пароли и прочие секреты — никогда (правило срабатывает раньше нейросети)
      const norm = normalize(text);
      if (SECRET_RE.test(norm) && !OWN_PASSWORD_RE.test(norm)) return out(m.intent("secret").answer, "secret", 1, false, "secret");

      // 2. Нейросеть: тема вопроса. Короткое уточнение («а как это сделать?», «а если не пришёл?»)
      //    сеть понимает вместе с прошлыми сообщениями клиента
      let pred = m.predict(text, 3), used = text;
      const followUp = stems(text).size <= 2 || /^(а|и|но|еще|так|тогда|ну)\s/.test(norm);
      if (followUp && (pred[0].p < CONFIDENT || (pred[0].id === "other" && pred[0].p < 0.9))) {
        for (const prev of clientMessages(history).reverse()) {
          if (!prev.trim() || normalize(prev) === norm) continue;
          const p2 = m.predict(prev + " " + text, 3);
          if (p2[0].id !== "other" && p2[0].p >= CONFIDENT && (pred[0].id === "other" || p2[0].p > pred[0].p)) {
            pred = p2; used = prev + " " + text; break;
          }
        }
      }
      const best = pred[0], it = m.intent(best.id);
      const sure = best.p >= CONFIDENT;

      // Сеть не очень уверена, а на странице сайта есть абзац почти обо всём вопросе — он точнее
      if (best.p < 0.65 && !(it && it.handoff) && !["secret", "human", "greeting", "thanks"].includes(best.id)) {
        const exact = await searchSite(text, pages);
        if (exact && exact.score >= 0.66) return siteAnswer(exact);
      }

      if (sure && best.id === "secret") return out(it.answer, "secret", best.p, false, "secret");
      if (sure && best.id === "human" && !draft) return out(it.answer, "human", best.p, true, "human");
      if (sure && (best.id === "greeting" || best.id === "thanks")) {
        if (!draft) return out(it.answer, best.id, best.p, false, best.id);
        return out("Здравствуйте! Чем можем помочь? Опишите, пожалуйста, вопрос подробнее.", best.id, best.p, false, best.id);
      }

      // 3. Тема сайта, в которой сеть уверена
      if (sure && best.id !== "other" && it && it.answer) {
        const normUsed = normalize(used);
        const handoff = !!it.handoff || (it.handoff_if || []).some((w) => normUsed.includes(w));
        const answer = answerOf(it);
        if (!draft && !handoff && alreadySaid(history, answer)) {
          return out("Я уже ответил на это выше, и, похоже, этого мало. Нажмите «Позвать администратора» — сотрудник RTeam " +
                     "разберётся лично. Или опишите подробнее, что именно не получается.", "repeat", 0.3, false, best.id);
        }
        return out(answer, "nn:" + best.id, best.p, handoff, best.id);
      }

      // 4. Сеть сомневается между двумя темами сайта — уточняем
      const second = pred[1];
      const isSite = (x) => x && !["other", "greeting", "thanks", "human", "secret"].includes(x.id);
      if (!draft && isSite(best) && isSite(second) && best.p + second.p >= 0.6 && best.p >= 0.25) {
        return out(`Уточните, пожалуйста: вы спрашиваете про ${m.intent(best.id).title} или про ${m.intent(second.id).title}? ` +
                   "Опишите вопрос чуть подробнее — так я отвечу точнее.", "clarify", best.p, false, best.id);
      }
      if (draft && isSite(best) && best.p >= 0.3) return out(answerOf(it), "nn:" + best.id, best.p, false, best.id);

      // 5. Страницы сайта
      const found = await searchSite(text, pages) || (used !== text ? await searchSite(used, pages) : null);
      if (found) return siteAnswer(found);

      // 6. Интернет — для общих вопросов
      if (words(text).length >= 2) {
        const web = await searchWeb(text, opts.searchUrl);
        if (web) {
          const tail = draft ? "" : "\n\nЭто ответ из интернета. Если вопрос про сайт RTeam и ответ не подошёл — нажмите «Позвать администратора».";
          return out(web.text.slice(0, 1400) + tail, "web", 0.5);
        }
      }

      // 7. Не нашёл — честно говорим и предлагаем человека
      if (draft) return out("Спасибо за обращение! Уточните, пожалуйста, подробности: что именно происходит, на какой странице и с какого аккаунта — так мы быстрее поможем.", "fallback", 0.1);
      return out("Я не нашёл точного ответа на этот вопрос. Попробуйте описать подробнее — или нажмите «Позвать администратора», и вам ответит сотрудник RTeam.", "fallback", 0.1);
    },
  };
  return api;
});
