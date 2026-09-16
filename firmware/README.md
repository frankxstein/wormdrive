# Firmware

`esp32/wormdrive_receiver/` is an **untested scaffold** for an ESP32 running
the Arduino framework. It documents the receiver side of the UDP contract:

- Parses `{"type":"motor","left":..,"right":..}` packets and drives two
  placeholder PWM/direction channels.
- Rejects malformed or mistyped packets (same policy as the PC side).
- **Implements the receiver-side watchdog**: motors are zeroed after 500ms
  without a valid packet. This is the safety-critical piece — do not remove
  it, and do not rely on the PC side alone.
- Sends `{"type":"imu","yaw_rate":..}` telemetry every 50ms (yaw is stubbed
  to 0.0 until an IMU is wired up).

## Status

This sketch has not been compiled or run on a physical board. Pin numbers,
PWM setup (`analogWrite` on ESP32 depends on core version), motor driver
wiring, and the IMU read are placeholders. Requires the `ArduinoJson`
library.

Before driving real motors: bench-test with wheels off the ground, verify
the watchdog by killing the PC process mid-run, and keep an independent
power cutoff within reach.
