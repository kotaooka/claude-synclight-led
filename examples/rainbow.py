"""区間ごとに色を変えて虹を流すデモ（約8秒）。"""
import colorsys
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import synclight_led as L  # noqa: E402

N = L.LAMPS_DEFAULT
SEGMENTS = 6
SEG = max(1, N // SEGMENTS)


def frame(offset, seq):
    secs = []
    for k in range(SEGMENTS):
        h = (k / SEGMENTS + offset) % 1.0
        r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(h, 1, 1))
        end = N if k == SEGMENTS - 1 else (k + 1) * SEG
        secs.append((k * SEG + 1, r, g, b, end))
    secs.append((N + 1, 0, 0, 0, 254))
    L.send(L.build_section_packet(secs, seq))


t0 = time.time()
seq = 1
while time.time() - t0 < 8:
    frame((time.time() - t0) / 3, seq)
    seq = seq % 254 + 1
    time.sleep(0.05)
L.set_color((0, 0, 0))
