# AXIN backend

The backend will provide authenticated device connectivity, a health endpoint, AI-provider integration, and user-controlled shared memory.

## Initial API plan
- `GET /health` — process health; must not expose secrets.
- `POST /v1/messages` — accept a versioned AXIN command and return a structured response.
- Later: authenticated audio session endpoints and memory APIs.

## Requirements before implementation
- Choose a framework and deployment target.
- Define authentication and per-user/device authorization.
- Set request size limits, timeouts, rate limits, and AI spending limits.
- Keep provider credentials in server-side environment variables.
- Add tests before connecting the physical ESP32.

No running service is included in this scaffold.
