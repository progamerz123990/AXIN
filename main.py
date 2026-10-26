"""AXIN Core API — minimal, dependency-free development server."""
from __future__ import annotations
import json, os, sqlite3, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.getenv("AXIN_HOST", "127.0.0.1")
PORT = int(os.getenv("AXIN_PORT", "8000"))
DB_PATH = Path(os.getenv("AXIN_DB_PATH", "axin_memory.sqlite3"))
API_KEY = os.getenv("AXIN_API_KEY", "")
API_BASE_URL = os.getenv("AXIN_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
MODEL = os.getenv("AXIN_MODEL", "gpt-4o-mini")
MAX_HISTORY = int(os.getenv("AXIN_MAX_HISTORY", "12"))

def db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
        content TEXT NOT NULL, created_at INTEGER NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")
    return conn

def get_history(conversation_id: str):
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
            (conversation_id, MAX_HISTORY)).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

def save_message(conversation_id: str, role: str, content: str):
    with db_connection() as conn:
        conn.execute("INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                     (conversation_id, role, content, int(time.time())))

def ask_model(messages):
    if not API_KEY:
        raise RuntimeError("AXIN_API_KEY is not configured. Set it locally; never commit API keys to GitHub.")
    payload = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.7}).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE_URL}/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"AI provider returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach AI provider: {exc.reason}") from exc
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise RuntimeError("AI provider returned an unexpected response format.") from exc

class AxinHandler(BaseHTTPRequestHandler):
    server_version = "AXIN-Core/0.1.0"
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
            return self.send_json(200, {"ok": True, "service": "axin-core",
                "version": "0.1.0", "ai_configured": bool(API_KEY), "memory": "sqlite"})
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
            messages = [{"role": "system", "content":
                "You are AXIN, a helpful cross-device AI companion. Be accurate and concise. "
                "Do not claim to remember anything unless it is in the supplied conversation history."}]
            messages.extend(get_history(conversation_id))
            reply = ask_model(messages)
            save_message(conversation_id, "assistant", reply)
            return self.send_json(200, {"conversation_id": conversation_id, "reply": reply, "model": MODEL})
        except json.JSONDecodeError:
            return self.send_json(400, {"error": "invalid_json"})
        except RuntimeError as exc:
            return self.send_json(503, {"error": "ai_unavailable", "message": str(exc)})
        except Exception:
            return self.send_json(500, {"error": "internal_error", "message": "Unexpected server error."})
    def log_message(self, format, *args):
        print("[AXIN]", format % args)

if __name__ == "__main__":
    db_connection().close()
    print(f"AXIN Core listening at http://{HOST}:{PORT}")
    print(f"Health check: http://127.0.0.1:{PORT}/health")
    ThreadingHTTPServer((HOST, PORT), AxinHandler).serve_forever()
