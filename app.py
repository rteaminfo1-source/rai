"""HTTP-сервер Rai (Flask). Собственный движок, без внешних API.

Сайт на другом хостинге отправляет POST с JSON
{"message": "...", "version": "pro", "session_id": "..."}
и получает {"answer": "..."} — тот же формат, что ждёт chat.js.
"""

import hmac
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

import codeai
from brain import Brain, RaiError
from versions import DEFAULT_VERSION, VERSIONS, resolve

app = Flask(__name__)
app.json.ensure_ascii = False
# Хостинг (Render и т.п.) стоит за прокси: так Flask видит настоящий адрес и https.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
# Аккаунты (регистрация, вход, Google) живут на основном сайте rteam.info, а не в Rai.
app.config.update(MAX_CONTENT_LENGTH=5 * 1024 * 1024)

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
CORS(app, origins=_origins or "*")

brain = Brain()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _payload():
    data = request.get_json(silent=True)
    if data is None:
        # На случай отправки обычной формой (application/x-www-form-urlencoded).
        data = request.form.to_dict()
    return data if isinstance(data, dict) else None


@app.get("/")
def index():
    """Страница чата (та же, что работает и без сервера)."""
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/api/versions")
def versions():
    return jsonify(
        {
            "service": "Rai",
            "default": DEFAULT_VERSION,
            "versions": [v.public() for v in VERSIONS.values()],
        }
    )


@app.get("/health")
def health():
    return jsonify({"ok": True, "intents": len(brain.intents)})


@app.post("/api/chat")
@app.post("/api/chat/<version_id>")
@app.post("/rai")
@app.post("/rai.php")
def chat(version_id=None):
    data = _payload()
    if data is None:
        return jsonify({"answer": "Неверный формат запроса.", "error": "bad_request"}), 400

    version = resolve(version_id or data.get("version"))
    if version is None:
        names = ", ".join(VERSIONS)
        return jsonify({"answer": f"Неизвестная версия. Доступны: {names}.", "error": "unknown_version"}), 400

    try:
        return jsonify(
            brain.answer(version, data.get("message", ""), data.get("session_id"), data.get("history"))
        )
    except RaiError as e:
        return jsonify({"answer": str(e), "error": "rai_error", "version": version.id}), e.status


@app.post("/api/code")
def code():
    """Вкладка Code: check | fix | explain | comment | generate | edit (правка сайта). Код не выполняется на сервере."""
    data = _payload() or {}
    action = data.get("action")
    source = data.get("code") or ""
    if action not in ("check", "fix", "explain", "comment", "generate", "edit"):
        return jsonify({"error": "action: check, fix, explain, comment, generate или edit"}), 400
    if len(source) > 200_000 or len(data.get("prompt") or "") > 4000:
        return jsonify({"error": "Слишком большой код"}), 413
    return jsonify(codeai.run_action(action, source, data.get("lang"), data.get("prompt") or ""))


@app.post("/api/slides")
def slides_tools():
    """Вкладка «Слайды»: цвета темы по словам (theme) и картинка в цветах темы (image)."""
    import creative
    data = _payload() or {}
    action = data.get("action")
    if action == "theme":
        return jsonify(creative.deck_theme(str(data.get("text") or "")[:300]))
    if action == "image":
        theme = data.get("theme") if isinstance(data.get("theme"), dict) else None
        seed = data.get("seed") if isinstance(data.get("seed"), int) else None
        return jsonify(creative.make_image(str(data.get("prompt") or "")[:300], seed=seed, theme=theme))
    return jsonify({"error": "action: theme или image"}), 400


@app.post("/api/teach")
def teach():
    """Добавить знание. Работает, только если задан RAI_ADMIN_TOKEN."""
    token = os.environ.get("RAI_ADMIN_TOKEN", "")
    data = _payload() or {}
    given = request.headers.get("X-Rai-Token") or data.get("token") or ""
    if not token or not hmac.compare_digest(str(given), token):
        return jsonify({"error": "forbidden"}), 403
    patterns = data.get("patterns")
    if isinstance(patterns, str):
        patterns = [patterns]
    try:
        intent_id = brain.teach(patterns or [], data.get("answer"), data.get("title"))
    except RaiError as e:
        return jsonify({"error": str(e)}), e.status
    return jsonify({"ok": True, "id": intent_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
