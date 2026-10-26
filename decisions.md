# Architecture decision log

## 0001 — Keep AI reasoning on a hosted backend initially
**Status:** Proposed  
**Reason:** The ESP32 has constrained memory and compute, and the Windows desktop has no dedicated usable GPU. The device should handle audio I/O and connectivity while a backend handles model requests.

## 0002 — Bring up hardware before wake-word features
**Status:** Proposed  
**Reason:** Verify microphone capture, speaker playback, power, and pin assignments independently before debugging voice activation.

## 0003 — Preserve the default branch during foundation work
**Status:** Accepted  
**Reason:** Work on a dedicated branch and review the diff before merging; avoid destructive history changes.
