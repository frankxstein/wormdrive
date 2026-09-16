from wormdrive.brain.mock import MockWormBackend
from wormdrive.vision import VisionFeatures


def _feat(left=0.0, right=0.0, looming=0.0, idx=0):
    return VisionFeatures(left_motion=left, right_motion=right, looming=looming, frame_index=idx)


def test_no_stimulus_settles_forward():
    brain = MockWormBackend()
    state = None
    for i in range(50):
        state = brain.step(_feat(idx=i), imu_yaw_rate=0.0, dt=0.05)
    assert state.AVB > state.AVA
    assert state.left_motor > 0
    assert state.right_motor > 0


def test_looming_triggers_reversal():
    brain = MockWormBackend()
    state = None
    for i in range(50):
        state = brain.step(_feat(looming=1.0, idx=i), imu_yaw_rate=0.0, dt=0.05)
    assert state.AVA > state.AVB
    assert state.left_motor < 0
    assert state.right_motor < 0


def test_asymmetric_motion_steers():
    brain = MockWormBackend()
    state = None
    for i in range(50):
        state = brain.step(_feat(left=0.0, right=1.0, idx=i), imu_yaw_rate=0.0, dt=0.05)
    # motion on the right side steers away from it: right motor speeds up
    # relative to left, turning the robot left (differential-drive convention)
    assert state.right_motor > state.left_motor


def test_values_stay_bounded():
    brain = MockWormBackend()
    for i in range(200):
        state = brain.step(_feat(left=1.0, right=1.0, looming=1.0, idx=i), imu_yaw_rate=5.0, dt=0.05)
        assert -1.0 <= state.left_motor <= 1.0
        assert -1.0 <= state.right_motor <= 1.0
        assert 0.0 <= state.ASH <= 1.0


def test_reset_clears_state():
    brain = MockWormBackend()
    for i in range(30):
        brain.step(_feat(looming=1.0, idx=i), imu_yaw_rate=0.0, dt=0.05)
    brain.reset()
    state = brain.step(_feat(idx=0), imu_yaw_rate=0.0, dt=0.05)
    assert state.ASH == 0.0 or state.ASH < 0.2
