import json

from wormdrive.decoder import MotorCommand
from wormdrive.protocol import decode_telemetry, encode_command


def test_encode_command_roundtrip():
    cmd = MotorCommand(left=0.5, right=-0.25, frame_index=7)
    raw = encode_command(cmd)
    obj = json.loads(raw.decode("utf-8"))
    assert obj["type"] == "motor"
    assert obj["left"] == 0.5
    assert obj["right"] == -0.25
    assert obj["frame"] == 7


def test_decode_valid_telemetry():
    raw = json.dumps({"type": "imu", "yaw_rate": 1.23}).encode("utf-8")
    assert decode_telemetry(raw) == 1.23


def test_decode_rejects_malformed_json():
    assert decode_telemetry(b"not json{{{") is None


def test_decode_rejects_wrong_type():
    raw = json.dumps({"type": "motor", "yaw_rate": 1.0}).encode("utf-8")
    assert decode_telemetry(raw) is None


def test_decode_rejects_missing_yaw():
    raw = json.dumps({"type": "imu"}).encode("utf-8")
    assert decode_telemetry(raw) is None


def test_decode_rejects_non_numeric_yaw():
    raw = json.dumps({"type": "imu", "yaw_rate": "fast"}).encode("utf-8")
    assert decode_telemetry(raw) is None
