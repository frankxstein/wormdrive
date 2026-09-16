# Changelog

## 0.1.0 — initial release

- Vision encoder: left/right frame-difference motion + looming heuristic;
  synthetic frame source; optional OpenCV camera/video input.
- MockWormBackend: leaky ASH/AVA/AVB forward-backward circuit with
  motion-asymmetry steering and IMU yaw damping.
- MotorDecoder: output smoothing, hard limits, polarity inversion.
- UdpLink: JSON-over-UDP motor commands and IMU telemetry with malformed
  packet rejection and PC-side staleness handling; dry-run by default.
- YAML config file support with CLI-over-config precedence.
- ConnectomeBackend: honest not-implemented stub for future real
  connectome integration.
- ESP32 firmware scaffold (untested) implementing the receiver watchdog.
- Test suite covering brain dynamics, decoder, protocol, and config.
