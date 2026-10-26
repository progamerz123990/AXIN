# ESP32 firmware

## Target hardware (expected; confirm against the actual kit)
- ESP32-WROOM-32 development board
- INMP441 I²S microphone
- MAX98357A I²S amplifier with speaker
- Display: **not assumed** until kit contents are confirmed

## Bring-up order
1. Identify the exact ESP32 board and available GPIO pins.
2. Wire and test the microphone using its documented I²S pinout.
3. Test the amplifier/speaker with a low-volume test tone.
4. Run both devices together and check for I²S pin conflicts.
5. Connect to Wi-Fi and test a backend health request.
6. Add authenticated commands and then evaluate wake-word options.

## Pin mapping
Do not copy random GPIO values from an online example. Record the selected pins here only after checking the board, wiring, and library constraints.

| Signal | ESP32 GPIO | Confirmed? |
|---|---:|---|
| INMP441 SCK/BCLK | TBD | No |
| INMP441 WS/LRCLK | TBD | No |
| INMP441 SD/DOUT | TBD | No |
| MAX98357A BCLK | TBD | No |
| MAX98357A LRC/WS | TBD | No |
| MAX98357A DIN | TBD | No |

## Safety and debugging
- Power down before changing wiring.
- Check the module's supply-voltage requirements and common ground.
- Start at low speaker volume.
- Never place Wi-Fi passwords or provider API keys in firmware source.
- This directory is documentation only so far; no firmware has been flashed or hardware-tested.
