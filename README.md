# AXIN

An open-source, cross-device AI companion with voice, reasoning, and shared memory.

> **Current stage:** repository foundation. Hardware and runtime behaviour are not yet verified.

## Project goals
- ESP32-WROOM-32 device with INMP441 I²S microphone and MAX98357A I²S amplifier/speaker.
- Wake phrase: `Axin`, with a sleep mode.
- Voice interaction in English and supported Indian languages.
- Hosted AI reasoning backend; do not attempt to run a large language model on the ESP32.
- Desktop and Android clients, with a user-controlled active device and shared conversation memory.
- Clear separation between device firmware, backend, clients, and protocol.

## Repository map
- `firmware/esp32/` — ESP32 firmware and hardware notes.
- `backend/` — hosted AI/API service.
- `desktop/` — Windows desktop client.
- `android/` — Android client.
- `protocol/` — messages shared between devices and backend.
- `tests/` — protocol and backend tests.
- `docs/` — architecture, decisions, and build notes.

## First milestone
1. Confirm the exact ESP32 board and kit contents.
2. Verify microphone capture and speaker playback independently.
3. Connect the ESP32 to a small authenticated backend health endpoint.
4. Send a short audio/command event and receive a response.
5. Add wake-word detection only after basic audio I/O works.

## Development rules
- Never commit API keys, Wi-Fi passwords, tokens, or personal data.
- Keep secrets in local environment files that are ignored by Git.
- Prefer small, testable steps. Record which checks actually ran.
- Do not describe untested firmware or cloud integration as working.
- ESP32 is part of the first milestone, not a later phase.

## Status
This is a clean starting scaffold, not a finished assistant. See `docs/architecture.md` and `firmware/esp32/README.md`.
