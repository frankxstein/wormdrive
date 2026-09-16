# Architecture

## Signal flow

```
Camera / video / synthetic frames
        │
        ▼
  VisionEncoder            frame-difference motion (left/right halves)
        │                  + center-energy-growth "looming" heuristic
        ▼
   BrainBackend            leaky ASH/AVA/AVB units → left/right motor targets
        │           ▲
        │           │ IMU yaw rate (damps steering)
        ▼           │
  MotorDecoder ──────┘      output-side smoothing + hard limits
        │
        ▼
     UdpLink ──────────►  robot (motor commands)
        ▲
        │
    robot IMU  ─────────►  telemetry (yaw rate), staleness-checked
```

## Brain backend

`MockWormBackend` (src/wormdrive/brain/mock.py) implements five leaky
scalar units:

- **ASH** — aversive/nociceptive integration, driven by the looming signal.
- **AVA** — backward command drive, driven by ASH.
- **AVB** — forward command drive, suppressed by ASH (mutual exclusion with
  AVA).
- **left_motor / right_motor** — driven by AVB (forward) or AVA (reverse),
  with a steering term derived from left/right motion asymmetry when not
  reversing.

All five use the same first-order leaky-integration update:
`x += (target - x) * (1 - exp(-rate * dt))`, clamped to their valid range.

This is a labeled engineering model, not a simulation of the real
*C. elegans* nervous system. Real AVA/AVB/ASH have specific synaptic
partners, gap junctions, and graded (non-spiking) membrane dynamics that
aren't reproduced here.

## UDP packet format

Motor command (PC → robot), JSON over UDP:

```json
{"type": "motor", "left": 0.42, "right": -0.10, "frame": 118}
```

IMU telemetry (robot → PC), JSON over UDP:

```json
{"type": "imu", "yaw_rate": 0.87}
```

`decode_telemetry` rejects anything that isn't valid JSON, isn't a dict,
doesn't have `"type": "imu"`, or has a non-numeric `yaw_rate` — it returns
`None` rather than raising, since UDP senders are untrusted.

## Watchdog

The PC-side `UdpLink.current_yaw_rate()` treats telemetry older than 500ms
as stale and returns `0.0`, which removes the yaw-damping term from
steering. This is **not** a substitute for a robot-side watchdog: firmware
must independently zero motor output after ~500ms without a fresh command,
in case the PC process or network link dies outright.

## Extension points

- `ConnectomeBackend` (src/wormdrive/brain/connectome_stub.py) — intended
  home for a real connectivity-graph-driven backend. Currently raises
  `NotImplementedError` unconditionally.
- `VisionEncoder` — the motion/looming heuristics are deliberately simple;
  swapping in real optical flow (e.g. Farneback via OpenCV) is a drop-in
  replacement as long as `VisionFeatures` keeps its shape.
