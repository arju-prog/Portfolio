"""Ruyi Jingu Bang — Sun Wukong's staff: lacquered red-black shaft, engraved gold banded caps."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, mat, sphere, torus  # noqa: E402

kit.reset()

GOLD = mat('#f0b93a', 0.3, metal=0.85)
GOLD_D = mat('#b8801f', 0.4, metal=0.85)
LAC = mat('#6e1010', 0.22, metal=0.05)
LAC_D = mat('#220707', 0.3, metal=0.05)

H = 1.0            # half length
R = 0.046          # shaft radius
CAP = 0.4         # cap length
RC = R + 0.014     # cap radius

# lacquered shaft (dark core with a red lacquer sleeve in the middle)
cylinder((0, 0, 0), R, 2 * H - 0.1, LAC_D, verts=32)
cylinder((0, 0, 0), R + 0.002, 2 * (H - CAP - 0.12), LAC, verts=32)
for s in (1, -1):
    # thin gold inlay rings where the red lacquer meets the black collar
    z = s * (H - CAP - 0.12)
    torus((0, 0, z), R + 0.003, 0.005, GOLD, major_segs=32, minor_segs=6)
    torus((0, 0, z - s * 0.035), R + 0.002, 0.004, GOLD, major_segs=32, minor_segs=6)


def cap(s):
    z0 = s * (H - CAP)          # inner edge of the cap
    zm = s * (H - CAP / 2)
    cylinder((0, 0, zm), RC, CAP, GOLD, verts=40)
    # flared collar at the inner edge + end lip
    for zz, rr, mm in ((z0, RC + 0.01, 0.009), (z0 + s * 0.028, RC + 0.004, 0.006),
                       (s * (H - 0.03), RC + 0.008, 0.009), (s * (H - 0.06), RC + 0.003, 0.005)):
        torus((0, 0, zz), rr, mm, GOLD if mm > 0.007 else GOLD_D, major_segs=40, minor_segs=8)
    # engraved band of rings across the middle of the cap
    for k in (-1, 0, 1):
        torus((0, 0, zm + s * k * 0.04), RC + 0.002, 0.005, GOLD_D, major_segs=40, minor_segs=6)
    # recessed dark-gold engraving band between the rings, with gold cloud studs over it
    cylinder((0, 0, zm + s * 0.02), RC + 0.0005, 0.03, GOLD_D, verts=40)
    # raised studs (engraved "cloud" beads) in a ring between the bands
    for i in range(10):
        a = i / 10 * math.tau + (0.3 if s > 0 else 0)
        zz = s * (H - CAP + 0.07)
        sphere((math.cos(a) * RC, math.sin(a) * RC, zz), 0.008, GOLD, segs=10, rings=6)
        zz = s * (H - 0.1)
        box((math.cos(a + 0.31) * RC, math.sin(a + 0.31) * RC, zz), (0.012, 0.012, 0.012), GOLD_D,
            rot=(0, 0, a + 0.31 + math.pi / 4))
    # domed end
    sphere((0, 0, s * H), (RC + 0.004, RC + 0.004, 0.022), GOLD, segs=32, rings=12)


cap(1)
cap(-1)

kit.finalize_prop('jingu_bang')
