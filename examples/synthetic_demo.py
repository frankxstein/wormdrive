"""Minimal library-usage example: run the pipeline without the CLI.

Shows how to wire VisionEncoder -> MockWormBackend -> MotorDecoder in your
own code (e.g. to embed wormdrive in a larger robot stack or a notebook).
"""
from wormdrive.brain import MockWormBackend
from wormdrive.decoder import MotorDecoder
from wormdrive.vision import SyntheticFrameSource, VisionEncoder

def main() -> None:
    source = SyntheticFrameSource()
    encoder = VisionEncoder()
    brain = MockWormBackend()
    decoder = MotorDecoder()

    dt = 1.0 / 30.0
    for i in range(60):
        frame = next(source)
        features = encoder.encode(frame)
        state = brain.step(features, imu_yaw_rate=0.0, dt=dt)
        cmd = decoder.decode(state, frame_index=i)
        print(f"[{i:03d}] AVB={state.AVB:.2f} AVA={state.AVA:.2f} "
              f"-> L={cmd.left:+.2f} R={cmd.right:+.2f}")

if __name__ == "__main__":
    main()
