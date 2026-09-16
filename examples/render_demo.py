"""Regenerate assets/demo.gif from the real pipeline.

Runs the synthetic camera through VisionEncoder -> MockWormBackend ->
MotorDecoder and renders each step: camera view on the left, live neuron
activity and motor bars on the right. Requires Pillow (pip install pillow).

Usage:  python examples/render_demo.py
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from wormdrive.brain import MockWormBackend
from wormdrive.decoder import MotorDecoder
from wormdrive.vision import SyntheticFrameSource, VisionEncoder

W, H = 900, 420
CAM_X, CAM_Y, CAM_W, CAM_H = 30, 70, 400, 300
TOTAL_STEPS = 210          # 7s of simulation at 30 fps
RENDER_EVERY = 3           # render every 3rd frame -> 10 fps GIF
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "demo.gif")


def _font(size: int, bold: bool = True):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)
    except OSError:
        return ImageFont.load_default()


F_T, F_S, F_V = _font(20), _font(15, bold=False), _font(14, bold=False)


def _bar(d, x, y, w, h, frac, col, signed=False, label="", value=""):
    d.rounded_rectangle([x, y, x + w, y + h], radius=6, fill=(22, 27, 34),
                        outline=(48, 54, 61), width=2)
    if signed:
        mid = x + w / 2
        d.line([mid, y + 2, mid, y + h - 2], fill=(48, 54, 61), width=2)
        bw = (w / 2 - 4) * min(1.0, abs(frac))
        if frac >= 0:
            d.rounded_rectangle([mid, y + 4, mid + bw, y + h - 4], radius=4, fill=col)
        else:
            d.rounded_rectangle([mid - bw, y + 4, mid, y + h - 4], radius=4, fill=col)
    else:
        bw = (w - 8) * min(1.0, max(0.0, frac))
        if bw > 1:
            d.rounded_rectangle([x + 4, y + 4, x + 4 + bw, y + h - 4], radius=4, fill=col)
    d.text((x, y - 22), label, font=F_S, fill=(230, 237, 243))
    tv = d.textlength(value, font=F_V)
    d.text((x + w - tv, y - 21), value, font=F_V, fill=(125, 133, 144))


def render() -> str:
    source = SyntheticFrameSource()
    encoder = VisionEncoder()
    brain = MockWormBackend()
    decoder = MotorDecoder()
    dt = 1.0 / 30.0

    frames: list[Image.Image] = []
    for i in range(TOTAL_STEPS):
        frame = next(source)
        feats = encoder.encode(frame)
        state = brain.step(feats, imu_yaw_rate=0.0, dt=dt)
        cmd = decoder.decode(state, frame_index=i)
        if i % RENDER_EVERY:
            continue

        img = Image.new("RGB", (W, H), (13, 17, 23))
        d = ImageDraw.Draw(img)
        d.text((30, 22), "wormdrive — live demo (synthetic camera)", font=F_T,
               fill=(230, 237, 243))

        g = (np.clip(frame, 0, 1) * 255).astype(np.uint8)
        cam = Image.fromarray(g, mode="L").resize((CAM_W, CAM_H), Image.NEAREST).convert("RGB")
        arr = np.array(cam).astype(np.float32)
        arr[..., 0] *= 0.25
        arr[..., 2] *= 0.35
        img.paste(Image.fromarray(arr.astype(np.uint8)), (CAM_X, CAM_Y))
        d.rectangle([CAM_X, CAM_Y, CAM_X + CAM_W, CAM_Y + CAM_H],
                    outline=(48, 54, 61), width=2)
        d.line([CAM_X + CAM_W / 2, CAM_Y, CAM_X + CAM_W / 2, CAM_Y + CAM_H],
               fill=(48, 54, 61), width=1)
        d.text((CAM_X, CAM_Y + CAM_H + 10),
               f"frame {i:03d}   motion L={feats.left_motion:.2f}  "
               f"R={feats.right_motion:.2f}   looming={feats.looming:.2f}",
               font=F_V, fill=(125, 133, 144))

        bx, bw = 480, 380
        d.text((bx, CAM_Y - 6), "neuron activity", font=F_T, fill=(230, 237, 243))
        _bar(d, bx, CAM_Y + 46, bw, 26, state.ASH, (219, 109, 40),
             label="ASH  (aversive)", value=f"{state.ASH:.2f}")
        _bar(d, bx, CAM_Y + 106, bw, 26, state.AVA, (248, 81, 73),
             label="AVA  (reverse)", value=f"{state.AVA:.2f}")
        _bar(d, bx, CAM_Y + 166, bw, 26, state.AVB, (63, 185, 80),
             label="AVB  (forward)", value=f"{state.AVB:.2f}")

        d.text((bx, CAM_Y + 212), "motor commands", font=F_T, fill=(230, 237, 243))
        _bar(d, bx, CAM_Y + 264, bw, 26, cmd.left, (88, 166, 255), signed=True,
             label="left", value=f"{cmd.left:+.2f}")
        _bar(d, bx, CAM_Y + 322, bw, 26, cmd.right, (88, 166, 255), signed=True,
             label="right", value=f"{cmd.right:+.2f}")

        if state.AVA > state.AVB:
            d.text((CAM_X + 8, CAM_Y + 8), "ESCAPE: reversing", font=F_T,
                   fill=(248, 81, 73))
        frames.append(img)

    out = os.path.abspath(OUT)
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=True)
    return out


if __name__ == "__main__":
    path = render()
    print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)")
