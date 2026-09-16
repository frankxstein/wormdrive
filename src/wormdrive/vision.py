"""Vision encoding: turns frames into a small feature vector.

No hard OpenCV dependency for the synthetic path — synthetic mode runs on
numpy alone so `wormdrive --synthetic --dry-run` works with zero external
hardware or heavyweight vision deps. A real camera / video file path uses
OpenCV if it's installed, and fails with a clear error if it isn't.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class VisionFeatures:
    """Compact per-frame feature vector fed into the brain backend."""

    left_motion: float      # 0..1 motion magnitude, left half of frame
    right_motion: float     # 0..1 motion magnitude, right half of frame
    looming: float          # 0..1 center-relative expansion estimate
    frame_index: int


class SyntheticFrameSource:
    """Deterministic synthetic frame generator.

    Produces a moving blob whose trajectory is a fixed function of the
    frame index, so runs are reproducible without a camera. This mirrors
    flybrain-robot-bridge's synthetic mode but with its own simpler blob
    kinematics.
    """

    def __init__(self, width: int = 160, height: int = 120, seed: int = 7):
        self.width = width
        self.height = height
        self._rng = np.random.default_rng(seed)
        self._t = 0

    def __iter__(self):
        return self

    def __next__(self) -> np.ndarray:
        t = self._t
        self._t += 1
        frame = np.zeros((self.height, self.width), dtype=np.float32)
        # Blob drifts left-right and grows/shrinks to simulate looming.
        cx = self.width / 2 + math.sin(t * 0.05) * (self.width * 0.35)
        cy = self.height / 2
        radius = 8 + 6 * (0.5 + 0.5 * math.sin(t * 0.03))
        yy, xx = np.mgrid[0 : self.height, 0 : self.width]
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        frame += np.exp(-(dist**2) / (2 * radius**2))
        frame += self._rng.normal(0, 0.01, size=frame.shape).astype(np.float32)
        return np.clip(frame, 0.0, 1.0)


class VisionEncoder:
    """Turns consecutive frames into a VisionFeatures vector.

    Uses simple frame-differencing split across the left/right halves of
    the image, plus a crude center-relative expansion heuristic for
    looming. This is intentionally simple — a heuristic, not a trained
    optical-flow model.
    """

    def __init__(self):
        self._prev: np.ndarray | None = None
        self._prev_center_energy: float | None = None
        self._frame_index = 0

    def encode(self, frame: np.ndarray) -> VisionFeatures:
        idx = self._frame_index
        self._frame_index += 1

        if self._prev is None:
            self._prev = frame
            self._prev_center_energy = self._center_energy(frame)
            return VisionFeatures(0.0, 0.0, 0.0, idx)

        diff = np.abs(frame - self._prev)
        _h, w = diff.shape
        left = diff[:, : w // 2]
        right = diff[:, w // 2 :]

        left_motion = float(np.clip(left.mean() * 8.0, 0.0, 1.0))
        right_motion = float(np.clip(right.mean() * 8.0, 0.0, 1.0))

        center_energy = self._center_energy(frame)
        looming = 0.0
        if self._prev_center_energy is not None and self._prev_center_energy > 1e-6:
            growth = (center_energy - self._prev_center_energy) / self._prev_center_energy
            looming = float(np.clip(growth * 2.0, 0.0, 1.0))

        self._prev = frame
        self._prev_center_energy = center_energy
        return VisionFeatures(left_motion, right_motion, looming, idx)

    @staticmethod
    def _center_energy(frame: np.ndarray) -> float:
        h, w = frame.shape
        cy0, cy1 = int(h * 0.35), int(h * 0.65)
        cx0, cx1 = int(w * 0.35), int(w * 0.65)
        return float(frame[cy0:cy1, cx0:cx1].sum())


def open_capture(source: str | int):
    """Open a webcam index or video file path using OpenCV.

    Raises a clear RuntimeError if OpenCV is not installed, rather than a
    confusing ImportError deep in a call stack.
    """
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without cv2
        raise RuntimeError(
            "OpenCV (opencv-python) is required for camera/video input. "
            "Install it or use --synthetic mode instead."
        ) from exc

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source!r}")
    return cap
