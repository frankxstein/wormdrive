"""YAML config loading with safe defaults.

Every field is optional; anything missing falls back to the CLI defaults.
Unknown keys are ignored with a warning rather than crashing, so a config
written for a newer version still loads on an older one.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_KNOWN_TOP = {"robot_ip", "robot_port", "pc_port", "motor", "vision", "backend"}
_KNOWN_MOTOR = {"limit", "smoothing", "invert"}
_KNOWN_VISION = {"fps"}


@dataclass
class MotorConfig:
    limit: float = 1.0
    smoothing: float = 0.4
    invert: bool = False


@dataclass
class VisionConfig:
    fps: float = 30.0


@dataclass
class Config:
    robot_ip: str = "127.0.0.1"
    robot_port: int = 9000
    pc_port: int = 9001
    backend: str = "mock"
    motor: MotorConfig = field(default_factory=MotorConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping, got {type(raw).__name__}")

    for key in raw:
        if key not in _KNOWN_TOP:
            print(f"warning: unknown config key {key!r} ignored", file=sys.stderr)

    motor_raw = raw.get("motor") or {}
    vision_raw = raw.get("vision") or {}
    for key in motor_raw:
        if key not in _KNOWN_MOTOR:
            print(f"warning: unknown motor config key {key!r} ignored", file=sys.stderr)
    for key in vision_raw:
        if key not in _KNOWN_VISION:
            print(f"warning: unknown vision config key {key!r} ignored", file=sys.stderr)

    cfg = Config(
        robot_ip=str(raw.get("robot_ip", Config.robot_ip)),
        robot_port=int(raw.get("robot_port", Config.robot_port)),
        pc_port=int(raw.get("pc_port", Config.pc_port)),
        backend=str(raw.get("backend", Config.backend)),
        motor=MotorConfig(
            limit=float(motor_raw.get("limit", MotorConfig.limit)),
            smoothing=float(motor_raw.get("smoothing", MotorConfig.smoothing)),
            invert=bool(motor_raw.get("invert", MotorConfig.invert)),
        ),
        vision=VisionConfig(fps=float(vision_raw.get("fps", VisionConfig.fps))),
    )

    if cfg.backend not in ("mock", "connectome"):
        raise ValueError(f"Unknown backend in config: {cfg.backend!r}")
    if not (0.0 <= cfg.motor.smoothing <= 1.0):
        raise ValueError("motor.smoothing must be in [0, 1]")
    if not (0.0 < cfg.motor.limit <= 1.0):
        raise ValueError("motor.limit must be in (0, 1]")
    if cfg.vision.fps <= 0:
        raise ValueError("vision.fps must be positive")
    return cfg
