# AXIN protocol

Protocol messages are versioned. The initial scaffold defines the shape only; transport and authentication are not implemented yet.

## Message envelope
See `message.schema.json`. Keep payloads small and avoid putting secrets or raw personal data in logs.

## Initial message types
- `hello` — device identifies its software/protocol version.
- `health` — connectivity and basic device status.
- `command` — text command or user-approved action request.
- `response` — result, status, or a user-facing error.

Audio streaming will be specified separately after microphone and speaker tests.
