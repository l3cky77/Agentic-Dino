import os
import json
import sqlite3
import secrets
import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)
#os.getenv("FLASK_SECRET_KEY", "change-this-dev-secret")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

DB_PATH = os.getenv("DATABASE_PATH", "dino_ai.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pair_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")


def current_user():
    if "user_id" not in session:
        return None
    with db() as conn:
        return conn.execute("SELECT id, username FROM users WHERE id = ?", (session["user_id"],)).fetchone()


def require_user_json():
    user = current_user()
    if not user:
        return None, (jsonify({"error": "Please sign in first."}), 401)
    return user, None


def safe_http_url(value):
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc) and not any(
            bad in parsed.hostname.lower() for bad in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")
        )
    except Exception:
        return False


def gemini_reply(message, history=None):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return (
            "Dino AI is running in demo mode because GEMINI_API_KEY is not configured. "
            "Add your key to the .env file to enable AI responses.\n\n"
            "I can still help you plan a task. Try: “Find official Python learning resources” "
            "or “Make a 3-step plan to debug my Flask app.”"
        )
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        recent = (history or [])[-8:]
        transcript = "\n".join(
            f'{("User" if item.get("role") == "user" else "Dino AI")}: {str(item.get("content", ""))[:2000]}'
            for item in recent
        )
        prompt = (
            "You are Dino AI, a careful, helpful agentic assistant. Be clear and concise. "
            "You may suggest plans, but do not claim you performed browser actions unless the app confirms it. "
            "Never ask for passwords or secrets. If a task involves sending, buying, deleting, or changing account "
            "security, require the user to do it themselves.\\n\\n"
            f"Recent conversation:\\n{transcript}\\n\\nUser: {message}\\nDino AI:"
        )
        response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt)
        return response.text or "I couldn't generate a response. Please try again."
    except Exception as exc:
        app.logger.exception("Gemini request failed")
        return f"I couldn't reach the AI service right now. Check your API key, model, and internet connection. ({type(exc).__name__})"


@app.route("/")
def index():
    if current_user():
        return render_template("dashboard.html", username=current_user()["username"])
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 32:
            flash("Username must be between 3 and 32 characters.", "error")
            return render_template("auth.html", mode="register")
        if len(password) < 8:
            flash("Use a password with at least 8 characters.", "error")
            return render_template("auth.html", mode="register")
        try:
            with db() as conn:
                cur = conn.execute(
                    "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                    (username, generate_password_hash(password), datetime.utcnow().isoformat())
                )
                session["user_id"] = cur.lastrowid
                session.permanent = True
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("That username is already taken.", "error")
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")
    return render_template("auth.html", mode="login")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/chat", methods=["POST"])
def api_chat():
    user, error = require_user_json()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    if not message:
        return jsonify({"error": "Please enter a message."}), 400
    if len(message) > 5000:
        return jsonify({"error": "Message is too long (maximum 5,000 characters)."}), 400

    answer = gemini_reply(message, history if isinstance(history, list) else [])
    with db() as conn:
        conn.execute(
            "INSERT INTO tasks(user_id, prompt, status, result, created_at) VALUES(?,?,?,?,?)",
            (user["id"], message[:1000], "completed", answer[:8000],datetime.now(timezone.utc).isoformat())
            
             # datetime.utcnow().isoformat())
        )
    return jsonify({"reply": answer})


@app.route("/api/tasks")
def api_tasks():
    user, error = require_user_json()
    if error:
        return error
    with db() as conn:
        rows = conn.execute(
            "SELECT id, prompt, status, result, created_at FROM tasks WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user["id"],)
        ).fetchall()
    return jsonify({"tasks": [dict(row) for row in rows]})


@app.route("/api/pair-code", methods=["POST"])
def pair_code():
    user, error = require_user_json()
    if error:
        return error
    code = f"{secrets.randbelow(900000) + 100000}"
    expiry = (
    datetime.now(timezone.utc)
    + timedelta(minutes=5)
).isoformat()
    #expiry = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    with db() as conn:
        conn.execute("UPDATE pair_codes SET used=1 WHERE user_id=? AND used=0", (user["id"],))
        conn.execute("INSERT INTO pair_codes(user_id, code, expires_at) VALUES(?,?,?)",
                     (user["id"], code, expiry))
    return jsonify({"code": code, "expires_in_seconds": 300})


@app.route("/companion")
def companion():
    return render_template("companion.html")


@app.route("/api/pair", methods=["POST"])
def consume_pair_code():
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip()
    if not re.fullmatch(r"\d{6}", code):
        return jsonify({"error": "Enter a valid six-digit code."}), 400
    with db() as conn:
        row = conn.execute("SELECT * FROM pair_codes WHERE code=? AND used=0", (code,)).fetchone()
        if not row:
            return jsonify({"error": "Code is invalid or already used."}), 400
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            conn.execute("UPDATE pair_codes SET used=1 WHERE id=?", (row["id"],))
            return jsonify({"error": "Code expired. Generate a new code on your phone."}), 400
        conn.execute("UPDATE pair_codes SET used=1 WHERE id=?", (row["id"],))
    # Demo pairing confirms the code. Production pairing should issue a scoped device token.
    return jsonify({"success": True, "message": "Pairing code accepted. This demo confirms pairing only."})


@app.route("/api/open-url", methods=["POST"])
def open_url():
    user, error = require_user_json()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip()
    if not safe_http_url(url):
        return jsonify({"error": "Enter a valid public HTTP or HTTPS URL."}), 400
    # Browser automation intentionally is not performed by the server in this MVP.
    # The companion browser page can open a user-approved URL locally.
    return jsonify({"success": True, "url": url, "message": "URL validated. Confirm on the companion device to open it."})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "Dino AI"})


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
