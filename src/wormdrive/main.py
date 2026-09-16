"""wormdrive CLI: run the camera-to-robot bridge.

Precedence for settings: CLI flag (if explicitly given) > config file > defaults.
"""
from __future__ import annotations

import argparse
import signal
import sys
import time

from .brain import MockWormBackend, ConnectomeBackend
from .config import Config, load_config
from .decoder import MotorDecoder
from .protocol import UdpLink
from .vision import SyntheticFrameSource, VisionEncoder, open_capture

_UNSET = object()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wormdrive", description=__doc__)
    p.add_argument("--config", type=str, default=None, help="path to a YAML config file")
    p.add_argument("--backend", choices=["mock", "connectome"], default=_UNSET)
    p.add_argument("--synthetic", action="store_true", help="use the built-in synthetic frame source")
    p.add_argument("--camera", type=int, default=None, help="webcam index")
    p.add_argument("--video", type=str, default=None, help="path to a video file")
    p.add_argument("--steps", type=int, default=300, help="number of frames to run (synthetic/video runs)")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    p.add_argument("--send", dest="dry_run", action="store_false", help="actually transmit UDP motor commands")
    p.add_argument("--robot-ip", default=_UNSET)
    p.add_argument("--robot-port", type=int, default=_UNSET)
    p.add_argument("--pc-port", type=int, default=_UNSET)
    p.add_argument("--invert", action="store_true", default=_UNSET, help="invert motor output polarity")
    p.add_argument("--fps", type=float, default=_UNSET)
    return p


def _resolve(cli_value, config_value):
    """CLI flag wins when explicitly provided; otherwise use config value."""
    return config_value if cli_value is _UNSET else cli_value


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        cfg = load_config(args.config) if args.config else Config()
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    backend_name = _resolve(args.backend, cfg.backend)
    robot_ip = _resolve(args.robot_ip, cfg.robot_ip)
    robot_port = _resolve(args.robot_port, cfg.robot_port)
    pc_port = _resolve(args.pc_port, cfg.pc_port)
    invert = _resolve(args.invert, cfg.motor.invert)
    fps = _resolve(args.fps, cfg.vision.fps)

    if not args.synthetic and args.camera is None and args.video is None:
        print("error: choose one of --synthetic, --camera N, or --video PATH", file=sys.stderr)
        return 2

    brain = ConnectomeBackend() if backend_name == "connectome" else MockWormBackend()
    encoder = VisionEncoder()
    decoder = MotorDecoder(smoothing=cfg.motor.smoothing, limit=cfg.motor.limit, invert=invert)

    try:
        link = UdpLink(robot_ip, robot_port, pc_port, send=not args.dry_run)
    except OSError as exc:
        print(f"error: could not open UDP socket on port {pc_port}: {exc}", file=sys.stderr)
        return 2

    stop_requested = {"flag": False}

    def _handle_sigint(_sig, _frame):
        stop_requested["flag"] = True

    signal.signal(signal.SIGINT, _handle_sigint)

    dt = 1.0 / fps
    cap = None

    if args.synthetic:
        source = SyntheticFrameSource()
        frame_iter = (next(source) for _ in range(args.steps))
        paced = True
    else:
        target = args.camera if args.camera is not None else args.video
        try:
            cap = open_capture(target)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            link.close()
            return 2
        import cv2  # type: ignore

        def _gen():
            n = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    return
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype("float32") / 255.0
                yield gray
                n += 1
                if args.camera is None and args.steps and n >= args.steps:
                    return

        frame_iter = _gen()
        paced = False

    print(
        f"wormdrive backend={backend_name} mode={'synthetic' if args.synthetic else 'live'} "
        f"dry_run={args.dry_run} fps={fps} target={robot_ip}:{robot_port}"
    )
    if not args.dry_run:
        print("LIVE MODE: transmitting motor commands. Ctrl-C sends a stop packet.")

    try:
        for i, frame in enumerate(frame_iter):
            if stop_requested["flag"]:
                break
            link.poll_telemetry()
            features = encoder.encode(frame)
            yaw = link.current_yaw_rate()
            try:
                state = brain.step(features, yaw, dt)
            except NotImplementedError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            cmd = decoder.decode(state, frame_index=i)
            payload = link.send_command(cmd)
            print(
                f"[{i:04d}] motion(L={features.left_motion:.2f} R={features.right_motion:.2f}) "
                f"looming={features.looming:.2f} yaw={yaw:.2f} "
                f"ASH={state.ASH:.2f} AVA={state.AVA:.2f} AVB={state.AVB:.2f} "
                f"cmd(L={cmd.left:+.2f} R={cmd.right:+.2f}) sent={len(payload)}B"
            )
            if paced:
                time.sleep(dt)
    finally:
        link.send_stop()
        link.close()
        if cap is not None:
            cap.release()

    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
