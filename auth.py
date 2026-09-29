"""Вход и регистрация в Rai: логин/пароль и через Google. Чаты пользователя хранятся на сервере.

Настройки (переменные окружения на хостинге):
    GOOGLE_CLIENT_ID      — ID клиента Google OAuth
    GOOGLE_CLIENT_SECRET  — секрет клиента (НИКОГДА не кладите его в GitHub)
    GOOGLE_REDIRECT_URI   — адрес возврата, по умолчанию https://<ваш-сервер>/auth/google/callback
    RAI_SECRET_KEY        — ключ подписи сессий (любая длинная случайная строка)
    RAI_DATA_DIR          — папка для users.json и чатов (по умолчанию ./data)
"""

import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from flask import Blueprint, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("RAI_DATA_DIR", os.path.join(BASE_DIR, "data"))

GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID", "40211315152-jq7a91jcqrpu8hkmlqmg1poh6bthgs5j.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")

MAX_CHATS_BYTES = 4 * 1024 * 1024

bp = Blueprint("auth", __name__)


def secret_key():
    """Ключ подписи сессий: из RAI_SECRET_KEY или сохранённый в data/secret_key."""
    key = os.environ.get("RAI_SECRET_KEY")
    if key:
        return key
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


class UserStore:
    """Пользователи в data/users.json. Пароли — только в виде хеша."""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        self.path = os.path.join(self.data_dir, "users.json")
        self.lock = threading.Lock()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, users):
        os.makedirs(self.data_dir, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def get(self, uid):
        return self._load().get(uid) if uid else None

    def find(self, **by):
        field, value = next(iter(by.items()))
        value = (value or "").lower()
        if not value:
            return None
        return next((u for u in self._load().values() if (u.get(field) or "").lower() == value), None)

    def create(self, **fields):
        with self.lock:
            users = self._load()
            user = {"id": uuid.uuid4().hex, "created": int(time.time()), "login": None, "email": None,
                    "name": None, "password_hash": None, "google_id": None, "avatar": None}
            user.update(fields)
            users[user["id"]] = user
            self._save(users)
            return user

    def update(self, uid, **fields):
        with self.lock:
            users = self._load()
            users[uid].update(fields)
            self._save(users)
            return users[uid]

    def unique_login(self, base):
        base = re.sub(r"[^a-z0-9_.-]", "", (base or "user").lower())[:24] or "user"
        login, n = base, 1
        while self.find(login=login):
            n += 1
            login = f"{base}{n}"
        return login

    # чаты
    def chats_path(self, uid):
        return os.path.join(self.data_dir, "chats", f"{uid}.json")

    def load_chats(self, uid):
        path = self.chats_path(uid)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def save_chats(self, uid, chats):
        path = self.chats_path(uid)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(chats, f, ensure_ascii=False)
        os.replace(path + ".tmp", path)


store = UserStore()

# ---------------------------------------------------------------- защита от перебора паролей
_attempts = {}


def _too_many(limit=10, window=300):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    now = time.time()
    hits = [t for t in _attempts.get(ip, []) if now - t < window]
    hits.append(now)
    _attempts[ip] = hits
    return len(hits) > limit


def public(user):
    if not user:
        return None
    return {"id": user["id"], "login": user.get("login"), "name": user.get("name") or user.get("login"),
            "email": user.get("email"), "avatar": user.get("avatar"), "google": bool(user.get("google_id"))}


def current_user():
    return store.get(session.get("uid"))


def _sign_in(user):
    session.clear()
    session["uid"] = user["id"]
    session.permanent = True


def _err(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------- логин и пароль
LOGIN_RE = re.compile(r"[A-Za-z0-9_.-]{3,32}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@bp.get("/auth/me")
def me():
    return jsonify({"user": public(current_user()), "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)})


@bp.post("/auth/register")
def register():
    if _too_many():
        return _err("Слишком много попыток. Подождите пару минут.", 429)
    data = request.get_json(silent=True) or {}
    login = (data.get("login") or "").strip()
    email = (data.get("email") or "").strip().lower() or None
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()[:60] or login
    if not LOGIN_RE.fullmatch(login):
        return _err("Логин: 3–32 символа, латинские буквы, цифры, точка, дефис или подчёркивание.")
    if email and not EMAIL_RE.fullmatch(email):
        return _err("Похоже, почта написана с ошибкой.")
    if len(password) < 8:
        return _err("Пароль должен быть не короче 8 символов.")
    if store.find(login=login):
        return _err("Такой логин уже занят.")
    if email and store.find(email=email):
        return _err("Эта почта уже зарегистрирована. Войдите или используйте вход через Google.")
    user = store.create(login=login.lower(), email=email, name=name,
                        password_hash=generate_password_hash(password))
    _sign_in(user)
    return jsonify({"user": public(user)})


@bp.post("/auth/login")
def login():
    if _too_many():
        return _err("Слишком много попыток. Подождите пару минут.", 429)
    data = request.get_json(silent=True) or {}
    who = (data.get("login") or "").strip()
    password = data.get("password") or ""
    user = store.find(email=who) if "@" in who else store.find(login=who)
    if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
        if user and not user.get("password_hash"):
            return _err("Этот аккаунт создан через Google — войдите кнопкой «Войти через Google».", 401)
        return _err("Неверный логин или пароль.", 401)
    _sign_in(user)
    return jsonify({"user": public(user)})


@bp.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- Google
def _redirect_uri():
    return GOOGLE_REDIRECT_URI or url_for("auth.google_callback", _external=True)


@bp.get("/auth/google/start")
@bp.get("/google_start.php")
def google_start():
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return redirect("/?auth_error=google_not_configured")
    state = secrets.token_urlsafe(24)
    session["google_state"] = state
    session["google_mode"] = "link" if request.args.get("mode") == "link" and current_user() else "login"
    params = {"client_id": GOOGLE_CLIENT_ID, "redirect_uri": _redirect_uri(), "response_type": "code",
              "scope": "openid email profile", "state": state, "prompt": "select_account"}
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params))


def _http_json(url, data=None, headers=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError):
        return None


def google_profile(code):
    """Обменять код на токен и получить профиль Google (вынесено отдельно для тестов)."""
    token = _http_json("https://oauth2.googleapis.com/token", {
        "code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": _redirect_uri(), "grant_type": "authorization_code"})
    if not token or not token.get("access_token"):
        return None
    return _http_json("https://openidconnect.googleapis.com/v1/userinfo",
                      headers={"Authorization": "Bearer " + token["access_token"]})


@bp.get("/auth/google/callback")
@bp.get("/google_callback.php")
def google_callback():
    state = session.pop("google_state", None)
    mode = session.pop("google_mode", "login")
    if not state or request.args.get("state") != state:
        return redirect("/?auth_error=state")
    if request.args.get("error") or not request.args.get("code"):
        return redirect("/?auth_error=cancelled")
    profile = google_profile(request.args["code"])
    if not profile or not profile.get("sub"):
        return redirect("/?auth_error=google")

    gid = profile["sub"]
    email = (profile.get("email") or "").lower() if profile.get("email_verified", True) else ""
    fields = {"google_id": gid, "avatar": profile.get("picture")}

    me_user = current_user()
    if mode == "link" and me_user:
        other = store.find(google_id=gid)
        if other and other["id"] != me_user["id"]:
            return redirect("/?auth_error=already_linked")
        store.update(me_user["id"], **fields)
        return redirect("/?auth=linked")

    user = store.find(google_id=gid) or (store.find(email=email) if email else None)
    if user:
        user = store.update(user["id"], **fields)
    else:
        base = email.split("@")[0] if email else profile.get("name", "user")
        user = store.create(login=store.unique_login(base), email=email or None,
                            name=profile.get("name") or base, **fields)
    _sign_in(user)
    return redirect("/?auth=google")


# ---------------------------------------------------------------- чаты аккаунта
@bp.get("/api/chats")
def get_chats():
    user = current_user()
    if not user:
        return _err("Нужно войти.", 401)
    return jsonify({"chats": store.load_chats(user["id"])})


@bp.put("/api/chats")
def put_chats():
    user = current_user()
    if not user:
        return _err("Нужно войти.", 401)
    if (request.content_length or 0) > MAX_CHATS_BYTES:
        return _err("Чаты слишком большие для сохранения — удалите старые чаты с картинками.", 413)
    data = request.get_json(silent=True) or {}
    chats = data.get("chats")
    if not isinstance(chats, list):
        return _err("Нужен список чатов.")
    store.save_chats(user["id"], chats[:500])
    return jsonify({"ok": True})
