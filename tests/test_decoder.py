import pytest

from wormdrive.brain.base import BrainState
from wormdrive.decoder import MotorDecoder


def test_decoder_limits_output():
    decoder = MotorDecoder(smoothing=0.0, limit=0.5)
    state = BrainState(left_motor=1.0, right_motor=-1.0)
    cmd = decoder.decode(state)
    assert cmd.left == pytest.approx(0.5)
    assert cmd.right == pytest.approx(-0.5)


def test_decoder_invert():
    decoder = MotorDecoder(smoothing=0.0, invert=True)
    state = BrainState(left_motor=0.4, right_motor=-0.3)
    cmd = decoder.decode(state)
    assert cmd.left == pytest.approx(-0.4)
    assert cmd.right == pytest.approx(0.3)


def test_decoder_smooths_over_steps():
    decoder = MotorDecoder(smoothing=0.9)
    state = BrainState(left_motor=1.0, right_motor=1.0)
    first = decoder.decode(state)
    second = decoder.decode(state)
    assert first.left < second.left  # ramps up gradually toward target


def test_invalid_smoothing_raises():
    with pytest.raises(ValueError):
        MotorDecoder(smoothing=1.5)
