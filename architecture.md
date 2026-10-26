# AXIN architecture (initial proposal)

## Components
1. **ESP32 device** — audio capture/playback, Wi-Fi connectivity, device identity, sleep/wake states, and a small command client.
2. **Backend** — authenticates clients, receives commands/audio, calls a hosted AI service, and stores user-authorized conversation memory.
3. **Desktop client** — Windows UI, voice/text interaction, device selection, and diagnostics.
4. **Android client** — mobile UI, voice/text interaction, device selection, and diagnostics.
5. **Shared protocol** — versioned JSON messages and explicit error responses.

## Important constraints
- ESP32-WROOM-32 has limited RAM and should not host a general-purpose LLM.
- Start with text/command round-trips before streaming audio. Audio adds bandwidth, latency, and format complexity.
- Wake-word detection must be evaluated on the target hardware; it is not implemented by this scaffold.
- Cross-device memory requires backend persistence and authentication. It must not mean every device can access every user's data.
- Use TLS for internet traffic. Local HTTP is only for controlled development on a trusted network.
- Never embed a long-lived AI provider key in firmware or a client app.

## First milestone acceptance criteria
- [ ] Exact board and pin mapping documented from the kit/manual.
- [ ] INMP441 microphone captures a known test signal.
- [ ] MAX98357A produces a test tone at a safe volume.
- [ ] ESP32 joins Wi-Fi and reports connection failures clearly.
- [ ] Backend health endpoint can be reached with device authentication.
- [ ] One versioned request/response passes end-to-end.
- [ ] No secrets appear in Git history or logs.

## Decisions still open
- Hosted AI provider and cost limits.
- Backend framework and deployment target.
- Audio codec, sample rate, chunk size, and streaming transport.
- Wake-word implementation and false-trigger handling.
- Account model and memory retention controls.
- Whether display hardware is included; do not assume it is.
