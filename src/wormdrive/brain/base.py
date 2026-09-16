from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..vision import VisionFeatures


@dataclass
class BrainState:
    """Snapshot of neuron-group activity, for logging/visualization.

    Named after real C. elegans neuron classes with well-documented roles
    in locomotion, but these are single scalar leaky units standing in for
    each class — not per-cell simulations, and not a model of the neurons'
    actual biophysics.
    """

    ASH: float = 0.0   # nociceptive / aversive sensory integration
    AVA: float = 0.0   # backward command interneuron
    AVB: float = 0.0   # forward command interneuron
    left_motor: float = 0.0
    right_motor: float = 0.0

    def as_dict(self) -> dict:
        return {
            "ASH": self.ASH,
            "AVA": self.AVA,
            "AVB": self.AVB,
            "left_motor": self.left_motor,
            "right_motor": self.right_motor,
        }


class BrainBackend(Protocol):
    """Interface every brain backend implements."""

    def step(self, features: VisionFeatures, imu_yaw_rate: float, dt: float) -> BrainState:
        ...

    def reset(self) -> None:
        ...
