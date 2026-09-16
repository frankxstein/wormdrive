from __future__ import annotations

from ..vision import VisionFeatures
from .base import BrainState


def _leak_toward(current: float, target: float, rate: float, dt: float) -> float:
    """First-order leaky integration toward a target, clamped to [0, 1]."""
    alpha = 1.0 - pow(2.718281828, -rate * dt)
    value = current + (target - current) * alpha
    return max(0.0, min(1.0, value))


class MockWormBackend:
    """A small, hand-designed stand-in for the C. elegans locomotion circuit.

    Real C. elegans forward/backward locomotion is switched by a well
    studied pair of command interneurons: AVB (forward) and AVA (backward),
    with ASH acting as a nociceptive sensor that triggers reversal on
    aversive stimuli (Chalfie et al. 1985; Gray, Hill & Bargmann 2005).
    This backend borrows that forward/backward switch structure and wires
    it to optical-flow-style vision features instead of chemosensation.

    It is a demonstrator, not a simulation of real neurons: no membrane
    dynamics, no synaptic weights from the actual connectome, no gap
    junctions. Treat the neuron names as labels for engineering roles.
    """

    def __init__(
        self,
        escape_gain: float = 3.0,
        forward_bias: float = 0.6,
        reversal_leak_rate: float = 4.0,
        motor_leak_rate: float = 6.0,
        steer_gain: float = 1.0,
    ):
        self.escape_gain = escape_gain
        self.forward_bias = forward_bias
        self.reversal_leak_rate = reversal_leak_rate
        self.motor_leak_rate = motor_leak_rate
        self.steer_gain = steer_gain
        self._state = BrainState()

    def reset(self) -> None:
        self._state = BrainState()

    def step(self, features: VisionFeatures, imu_yaw_rate: float, dt: float) -> BrainState:
        s = self._state

        # ASH: aversive sensory integration, driven by looming (a proxy for
        # an approaching object) plus a small contribution from raw motion.
        ash_target = min(1.0, features.looming * self.escape_gain)
        ash = _leak_toward(s.ASH, ash_target, self.reversal_leak_rate, dt)

        # AVA / AVB: mutually suppressive forward/backward command drive.
        # High ASH pushes AVA up (reverse) and suppresses AVB (forward).
        ava_target = ash
        avb_target = max(0.0, self.forward_bias - ash)
        ava = _leak_toward(s.AVA, ava_target, self.reversal_leak_rate, dt)
        avb = _leak_toward(s.AVB, avb_target, self.reversal_leak_rate, dt)

        # Steering bias: asymmetric left/right motion nudges the two motor
        # neurons apart, loosely evoking klinotaxis-style gradient steering.
        steer = (features.right_motion - features.left_motion) * self.steer_gain
        steer -= imu_yaw_rate * 0.2  # damp against measured yaw drift

        if ava > avb:
            # Reversing: both motors driven backward together, steering
            # suppressed (the worm backs away first, turns second).
            left_target = -ava
            right_target = -ava
        else:
            left_target = avb - steer
            right_target = avb + steer

        left_target = max(-1.0, min(1.0, left_target))
        right_target = max(-1.0, min(1.0, right_target))

        left_motor = _clamped_leak(s.left_motor, left_target, self.motor_leak_rate, dt)
        right_motor = _clamped_leak(s.right_motor, right_target, self.motor_leak_rate, dt)

        self._state = BrainState(
            ASH=ash, AVA=ava, AVB=avb, left_motor=left_motor, right_motor=right_motor
        )
        return self._state


def _clamped_leak(current: float, target: float, rate: float, dt: float) -> float:
    alpha = 1.0 - pow(2.718281828, -rate * dt)
    value = current + (target - current) * alpha
    return max(-1.0, min(1.0, value))
