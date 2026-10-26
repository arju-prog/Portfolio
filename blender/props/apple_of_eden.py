"""Apple of Eden — golden metallic orb with engraved concentric channels and panel lines that glow."""
import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import mat, rot_between, sphere, torus, tube  # noqa: E402

kit.reset()

GOLD = mat('#e0a838', 0.28, metal=0.9)
GOLD_D = mat('#6b4712', 0.45, metal=0.8)      # engraved channel walls
GLOW = mat('#fff1c2', 0.3, emit=5.0)
GLOW_W = mat('#ffd36b', 0.3, emit=3.0)

R = 0.5
# engraving axis: points roughly at the sprite camera so the rings read as concentric
AX = Vector((0.5, -0.68, 0.6)).normalized()
U = AX.cross(Vector((0, 0, 1))).normalized()
V = AX.cross(U).normalized()

sphere((0, 0, 0), R, GOLD, segs=56, rings=28)


def on_sphere(theta, phi, r=R):
    """Point at polar angle theta from the engraving axis, azimuth phi."""
    d = AX * math.cos(theta) + (U * math.cos(phi) + V * math.sin(phi)) * math.sin(theta)
    return tuple(d * r)


def channel_ring(theta, width=0.016):
    c = AX * ((R - 0.008) * math.cos(theta))
    major = (R - 0.008) * math.sin(theta)
    rot = rot_between((0, 0, 0), tuple(AX))
    torus(tuple(c), major, width, GOLD_D, rot=rot, major_segs=64, minor_segs=8)
    torus(tuple(AX * ((R + 0.003) * math.cos(theta))), (R + 0.003) * math.sin(theta), width * 0.6, GLOW,
          rot=rot, major_segs=64, minor_segs=6)


def channel_arc(t0, t1, phi, n=14):
    pts_d = [on_sphere(t0 + (t1 - t0) * i / n, phi, R - 0.006) for i in range(n + 1)]
    pts_g = [on_sphere(t0 + (t1 - t0) * i / n, phi, R + 0.003) for i in range(n + 1)]
    tube(pts_d, 0.013, GOLD_D, smooth_path=False, name='arc_d')
    tube(pts_g, 0.007, GLOW_W, smooth_path=False, name='arc_g')


# central glowing eye
sphere(on_sphere(0, 0, R - 0.02), 0.065, GOLD_D, segs=24, rings=12)
sphere(on_sphere(0, 0, R + 0.012), 0.042, GLOW, segs=24, rings=12)

# concentric engraved rings
RINGS = (math.radians(17), math.radians(36), math.radians(58), math.radians(84))
for th in RINGS:
    channel_ring(th)

# panel lines linking the rings (circuit-like), offset per band
links = [
    (RINGS[0], RINGS[1], (0.3, 2.4, 4.4)),
    (RINGS[1], RINGS[2], (1.1, 3.0, 5.2)),
    (RINGS[2], RINGS[3], (0.2, 1.7, 2.9, 4.1, 5.6)),
    (RINGS[3], math.radians(150), (0.8, 2.3, 3.6, 5.0)),
]
for t0, t1, phis in links:
    for phi in phis:
        channel_arc(t0, t1, phi, n=10 if t1 - t0 < 0.5 else 16)
        # glowing node where each line meets a ring
        sphere(on_sphere(t1, phi, R + 0.01), 0.014, GLOW, segs=10, rings=6)

# back cap ring (far side) so the orb has engraving all round
channel_ring(math.radians(150), width=0.014)

kit.finalize_prop('apple_of_eden')
