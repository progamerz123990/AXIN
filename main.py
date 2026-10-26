"""AXIN Core API v0.2 — Gemini model cycling with quota-aware fallback.

Dependency-free development server. Configure AXIN_API_KEY locally.
Never commit API keys or the SQLite database to GitHub.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

HOST = os.getenv("AXIN_HOST", "127.0.0.1")
PORT = int(os.getenv("AXIN_PORT", "8000"))
DB_PATH = Path(os.getenv("AXIN_DB_PATH", "axin_memory.sqlite3"))
API_KEY = os.getenv("AXIN_API_KEY", "").strip()
# Ordered strongest/preferred first. Override this list if model availability changes.
MODEL_NAMES = [m.strip() for m in os.getenv(
    "AXIN_MODELS", "gemini-2.5-flash,gemini-2.5-flash-lite"
).split(",") if m.strip()]
MAX_HISTORY = int(os.getenv("AXIN_MAX_HISTORY", "12"))
DEFAULT_COOLDOWN = max(15, int(os.getenv("AXIN_DEFAULT_COOLDOWN_SECONDS", "60")))
REQUEST_TIMEOUT = max(5, int(os.getenv("AXIN_REQUEST_TIMEOUT_SECONDS", "45")))

# In-memory cooldowns prevent repeatedly calling models known to be rate-limited.
# The preferred model is reconsidered after its cooldown expires.
_cooldowns: dict[str, float] = {}
_cooldown_lock = Lock()


class ProviderError(Exception):
    def __init__(self, message: str, status: int | None = None,
                 retry_after: int | None = None, quota: bool = False):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.quota = quota


def db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")
    return conn


def get_history(conversation_id: str):
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
            (conversation_id, MAX_HISTORY),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def save_message(conversation_id: str, role: str, content: str):
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, int(time.time())),
        )


def cooldown_remaining(model: str, now: float | None = None) -> float:
    now = time.time() if now is None else now
    with _cooldown_lock:
        until = _cooldowns.get(model, 0.0)
        if until <= now:
            _cooldowns.pop(model, None)
            return 0.0
        return until - now


def mark_cooldown(model: str, seconds: int | None = None):
    duration = max(1, seconds if seconds is not None else DEFAULT_COOLDOWN)
    with _cooldown_lock:
        _cooldowns[model] = time.time() + duration


def clear_cooldowns_for_tests():
    with _cooldown_lock:
        _cooldowns.clear()


def _extract_error(raw: str) -> str:
    try:
        data = json.loads(raw)
        return str(data.get("error", {}).get("message", raw))[:700]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return raw[:700]


def _retry_delay(raw: str, header_value: str | None) -> int | None:
    if header_value:
        try:
            return max(1, int(float(header_value)))
        except ValueError:
            pass
    # Gemini sometimes includes a structured retryDelay such as "37s".
    try:
        data = json.loads(raw)
        details = data.get("error", {}).get("details", [])
        for detail in details:
            delay = detail.get("retryDelay", "") if isinstance(detail, dict) else ""
            match = re.fullmatch(r"\s*(\d+)s\s*", str(delay))
            if match:
                return max(1, int(match.group(1)))
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    return None


def ask_gemini(model: str, contents: list[dict]) -> str:
    if not API_KEY:
        raise ProviderError("AXIN_API_KEY is not configured. Set it locally; never commit it to GitHub.")

    # Gemini REST API: API key is sent in a header, not embedded in the URL.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = json.dumps({
        "contents": contents,
        "generationConfig": {"temperature": 0.7},
    }).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload,
        headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read(3000).decode("utf-8", errors="replace")
        message = _extract_error(raw)
        retry_after = _retry_delay(raw, exc.headers.get("Retry-After"))
        # HTTP 429 is a rate/quota limit; HTTP 503 may be temporary provider overload.
        raise ProviderError(message, status=exc.code, retry_after=retry_after,
                            quota=(exc.code == 429)) from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Could not reach Google AI: {exc.reason}") from exc
    try:
        parts = data["candidates"][0]["content"]["parts"]
        reply = "".join(part.get("text", "") for part in parts).strip()
        if not reply:
            raise ValueError("empty response")
        return reply
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("Gemini returned no usable text response.") from exc


def to_gemini_contents(messages: list[dict]) -> list[dict]:
    """Translate chat history to Gemini's contents format."""
    contents = []
    for item in messages:
        role = item.get("role")
        content = item.get("content", "")
        if role == "system":
            # The small project currently folds system guidance into the first user turn.
            continue
        if role not in ("user", "assistant"):
            continue
        gemini_role = "model" if role == "assistant" else "user"
        # Gemini expects alternating user/model turns; normal stored history alternates.
        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"][0]["text"] += "\n\n" + content
        else:
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    if not contents or contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "You are AXIN, a helpful cross-device AI companion. Be accurate and concise. Do not claim to remember anything unless it is in the supplied conversation history."}]})
    else:
        contents[0]["parts"][0]["text"] = (
            "You are AXIN, a helpful cross-device AI companion. Be accurate and concise. "
            "Use the supplied conversation history where relevant.\n\n" + contents[0]["parts"][0]["text"]
        )
    return contents


def choose_and_ask(messages: list[dict]) -> tuple[str, str]:
    """Try preferred available models in order; quota errors trigger fallback.

    On each new request, expired cooldowns are removed and the preferred model is
    tried again first, so AXIN automatically upgrades after a model recovers.
    """
    if not MODEL_NAMES:
        raise ProviderError("No models configured. Set AXIN_MODELS.")
    if not API_KEY:
        raise ProviderError("AXIN_API_KEY is not configured. Set it locally; never commit it to GitHub.")

    contents = to_gemini_contents(messages)
    skipped = []
    for model in MODEL_NAMES:
        remaining = cooldown_remaining(model)
        if remaining > 0:
            skipped.append(f"{model} cooling down ({int(remaining)}s)")
            continue
        try:
            return ask_gemini(model, contents), model
        except ProviderError as exc:
            # Only quota/rate-limit errors trigger automatic model fallback.
            if exc.quota:
                mark_cooldown(model, exc.retry_after)
                print(f"[AXIN] {model} rate-limited; cooling down and trying fallback.")
                continue
            # A temporary 503 can use the next configured model as a fallback too.
            if exc.status == 503:
                mark_cooldown(model, exc.retry_after or 30)
                print(f"[AXIN] {model} temporarily unavailable; trying fallback.")
                continue
            # Authentication/model-not-found/bad-request errors should be surfaced,
            # not silently treated as exhausted quota.
            raise
    raise ProviderError("No configured Gemini model is currently available. " + "; ".join(skipped), status=429, quota=True)


class AxinHandler(BaseHTTPRequestHandler):
    server_version = "AXIN-Core/0.2.0"

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        if status != 204:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        if self.path == "/health":
            return self.send_json(200, {
                "ok": True, "service": "axin-core", "version": "0.2.0",
                "ai_configured": bool(API_KEY), "provider": "google-gemini",
                "models_priority": MODEL_NAMES,
                "models_cooling_down": {m: round(cooldown_remaining(m)) for m in MODEL_NAMES if cooldown_remaining(m) > 0},
                "memory": "sqlite",
            })
        return self.send_json(404, {"error": "not_found", "message": "Try GET /health or POST /api/chat."})

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_json(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 64000:
                return self.send_json(413, {"error": "invalid_body_size"})
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            conversation_id = str(data.get("conversation_id", "default")).strip()
            message = data.get("message")
            if not conversation_id or len(conversation_id) > 128:
                return self.send_json(400, {"error": "invalid_conversation_id"})
            if not isinstance(message, str) or not message.strip() or len(message) > 8000:
                return self.send_json(400, {"error": "message_must_be_nonempty_text_under_8000_chars"})

            save_message(conversation_id, "user", message.strip())
            history = get_history(conversation_id)
            reply, model = choose_and_ask(history)
            save_message(conversation_id, "assistant", reply)
            return self.send_json(200, {
                "conversation_id": conversation_id, "reply": reply,
                "model": model, "provider": "google-gemini",
            })
        except json.JSONDecodeError:
            return self.send_json(400, {"error": "invalid_json"})
        except ProviderError as exc:
            status = 429 if exc.quota else 503
            return self.send_json(status, {
                "error": "model_unavailable", "message": str(exc),
                "cooldowns_seconds": {m: round(cooldown_remaining(m)) for m in MODEL_NAMES if cooldown_remaining(m) > 0},
            })
        except Exception as exc:
            print(f"[AXIN] Unexpected error: {type(exc).__name__}: {exc}")
            return self.send_json(500, {"error": "internal_error", "message": "Unexpected server error."})

    def log_message(self, fmt, *args):
        print("[AXIN]", fmt % args)


if __name__ == "__main__":
    db_connection().close()
    print(f"AXIN Core v0.2.0 listening at http://{HOST}:{PORT}")
    print(f"Health check: http://127.0.0.1:{PORT}/health")
    print("Preferred model order:", " -> ".join(MODEL_NAMES))
    print("AI configured:", bool(API_KEY))
    ThreadingHTTPServer((HOST, PORT), AxinHandler).serve_forever()
