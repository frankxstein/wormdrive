from __future__ import annotations

from dataclasses import dataclass

from .brain.base import BrainState


@dataclass
class MotorCommand:
    left: float   # -1.0 (full reverse) .. 1.0 (full forward)
    right: float
    frame_index: int = 0


class MotorDecoder:
    """Converts BrainState motor activity into smoothed, limited commands.

    Applies an output-side exponential smoothing pass (independent of the
    brain's own leaky dynamics) and hard limits, so a downstream firmware
    change to motor limits doesn't require touching the brain model.
    """

    def __init__(self, smoothing: float = 0.4, limit: float = 1.0, invert: bool = False):
        if not (0.0 <= smoothing <= 1.0):
            raise ValueError("smoothing must be in [0, 1]")
        self.smoothing = smoothing
        self.limit = limit
        self.invert = invert
        self._last_left = 0.0
        self._last_right = 0.0

    def reset(self) -> None:
        self._last_left = 0.0
        self._last_right = 0.0

    def decode(self, state: BrainState, frame_index: int = 0) -> MotorCommand:
        left = state.left_motor
        right = state.right_motor
        if self.invert:
            left, right = -left, -right

        left = self._last_left + (left - self._last_left) * (1.0 - self.smoothing)
        right = self._last_right + (right - self._last_right) * (1.0 - self.smoothing)

        left = max(-self.limit, min(self.limit, left))
        right = max(-self.limit, min(self.limit, right))

        self._last_left, self._last_right = left, right
        return MotorCommand(left=left, right=right, frame_index=frame_index)
