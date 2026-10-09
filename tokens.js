/* Счётчик токенов Rai в браузере — зеркало tokens.py (считать надо ОДИНАКОВО и там, и тут).
   Нужен, чтобы показать пользователю, сколько стоит ответ, вести дневной лимит по тарифу и
   считать токены, когда отвечает нейросеть (у неё нет серверного usage). Работает везде: чат, слайды, код. */
(function () {
  "use strict";

  const PIECE = /[A-Za-z]+|[А-Яа-яЁё]+|[0-9]+|\S/gu;
  function count(text) {
    text = text == null ? "" : String(text);
    let n = 0, m;
    PIECE.lastIndex = 0;
    while ((m = PIECE.exec(text))) {
      const w = m[0], c = w[0];
      if ((c >= "а" && c <= "я") || (c >= "А" && c <= "Я") || c === "ё" || c === "Ё") n += Math.max(1, Math.ceil(w.length / 3));
      else if ((c >= "a" && c <= "z") || (c >= "A" && c <= "Z")) n += Math.max(1, Math.ceil(w.length / 4));
      else if (c >= "0" && c <= "9") n += Math.max(1, Math.ceil(w.length / 3));
      else n += 1;
    }
    return n;
  }

  const LEVEL_COST = {low: 1.0, medium: 2.0, high: 3.5, code: 4.0, extra: 6.0, ultra: 10.0};
  // 0 = без ограничений (бесконечно). Плюс больше, Премиум (Sun) ещё больше, Ультра (Quasar) — безлимит.
  const PLAN_LIMIT = {"pro-fast": 100000, "pro": 300000, "pro-plus": 1000000, "pro-sun": 3000000, "pro-quasar": 0};
  const DEFAULT_LIMIT = 300000;

  function limitFor(id) { return PLAN_LIMIT[id] || DEFAULT_LIMIT; }

  function reasoningCost(p, a, level) {
    const cost = LEVEL_COST[(level || "").toLowerCase()] || 2.0;
    return Math.round((p + a) * (cost - 1) * 0.5);
  }

  // Стоимость ответа в токенах: {prompt, answer, reasoning, total, level, limit}
  function usage(opts) {
    opts = opts || {};
    const p = count(opts.prompt || "");
    const a = count(opts.answer || "") + count(opts.extra || "");
    const r = opts.reasoning != null ? opts.reasoning : reasoningCost(p, a, opts.level);
    return {prompt: p, answer: a, reasoning: Math.max(0, r | 0), total: p + a + Math.max(0, r | 0),
            level: opts.level || "", limit: limitFor(opts.version)};
  }

  function human(n) {
    n = Math.round(Number(n) || 0);
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  window.RaiTokens = {count: count, usage: usage, limitFor: limitFor, reasoningCost: reasoningCost, human: human,
                      LEVEL_COST: LEVEL_COST, PLAN_LIMIT: PLAN_LIMIT};
})();
