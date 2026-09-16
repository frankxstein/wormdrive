from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass

from .decoder import MotorCommand

TELEMETRY_STALE_S = 0.5  # PC sends zero commands once telemetry is this old


@dataclass
class ImuSample:
    yaw_rate: float
    received_at: float


def encode_command(cmd: MotorCommand) -> bytes:
    payload = {"type": "motor", "left": round(cmd.left, 4), "right": round(cmd.right, 4),
               "frame": cmd.frame_index}
    return json.dumps(payload).encode("utf-8")


def decode_telemetry(raw: bytes) -> float | None:
    """Parse an inbound IMU telemetry packet. Returns yaw_rate or None if
    the packet is malformed / not a telemetry message — never raises on
    bad input, since UDP delivery is untrusted by construction."""
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict) or obj.get("type") != "imu":
        return None
    yaw = obj.get("yaw_rate")
    if not isinstance(yaw, (int, float)):
        return None
    return float(yaw)


class UdpLink:
    """Sends motor commands and (optionally) receives IMU telemetry.

    Defaults to dry-run: pass send=True to actually transmit. The
    receiver-side watchdog (stopping motors after stale telemetry) must
    also be implemented independently on the robot's firmware — this
    class only tracks staleness on the PC side to decide whether to keep
    commanding motion at all.
    """

    def __init__(self, robot_ip: str, robot_port: int, pc_port: int, send: bool = False):
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.pc_port = pc_port
        self.send_enabled = send
        self._sock: socket.socket | None = None
        self._last_imu: ImuSample | None = None

        if send:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.bind(("0.0.0.0", pc_port))
            self._sock.setblocking(False)

    def poll_telemetry(self) -> None:
        if self._sock is None:
            return
        try:
            while True:
                raw, _addr = self._sock.recvfrom(1024)
                yaw = decode_telemetry(raw)
                if yaw is not None:
                    self._last_imu = ImuSample(yaw_rate=yaw, received_at=time.monotonic())
        except BlockingIOError:
            pass

    def current_yaw_rate(self) -> float:
        if self._last_imu is None:
            return 0.0
        if time.monotonic() - self._last_imu.received_at > TELEMETRY_STALE_S:
            return 0.0
        return self._last_imu.yaw_rate

    def send_command(self, cmd: MotorCommand) -> bytes:
        """Returns the encoded payload regardless of send mode, so callers
        can log/print what *would* be sent even in dry-run."""
        payload = encode_command(cmd)
        if self.send_enabled and self._sock is not None:
            self._sock.sendto(payload, (self.robot_ip, self.robot_port))
        return payload

    def send_stop(self) -> None:
        if self.send_enabled and self._sock is not None:
            stop = MotorCommand(left=0.0, right=0.0)
            self._sock.sendto(encode_command(stop), (self.robot_ip, self.robot_port))

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
