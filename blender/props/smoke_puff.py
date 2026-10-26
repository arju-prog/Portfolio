"""Cartoon smoke 'poof' (Shadow Clone appear/vanish): a cluster of overlapping puffy balls, bright
white on top shading to a cool grey underneath, a few stray puffs and swirl curls. Front-on."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
import _mini as M  # noqa: E402
from mathutils import Vector as V  # noqa: E402

random.seed(11)
kit.reset()

TONES = [kit.mat('#ffffff', 0.9), kit.mat('#eef1f5', 0.9), kit.mat('#d3d9e2', 0.9), kit.mat('#b4bdca', 0.9)]
CURL = kit.mat('#9aa5b4', 0.9)


def tone(z):
    """Brighter towards the top, cool grey on the underside."""
    t = max(0.0, min(1.0, (0.3 - z) / 0.7))
    return TONES[min(3, int(t * 4))]


def puff(c, r, squash=0.92):
    c = V(c)
    return kit.sphere(c, (r, r * 0.85, r * squash), tone(c.z), segs=32, rings=16)


# core mass
puff((0, 0.05, 0.02), 0.46)
puff((-0.22, -0.02, 0.18), 0.34)
puff((0.24, -0.02, 0.16), 0.33)
puff((0.0, -0.06, 0.3), 0.32)
# lobes around the rim (bigger on top, flatter along the base)
lobes = [(90, 0.62, 0.3), (130, 0.62, 0.27), (50, 0.6, 0.27), (165, 0.62, 0.25), (15, 0.64, 0.26),
         (200, 0.58, 0.23), (-20, 0.6, 0.24), (235, 0.52, 0.22), (-55, 0.52, 0.22), (270, 0.42, 0.22),
         (-90 + 18, 0.48, 0.2)]
for ang, dist, r in lobes:
    a = math.radians(ang)
    y = random.uniform(-0.06, 0.08)
    puff((math.cos(a) * dist * 1.08, y, math.sin(a) * dist * 0.98 + 0.06), r)
for x, z, r in ((-0.3, 0.62, 0.24), (0.3, 0.6, 0.23), (0.0, 0.72, 0.22)):
    puff((x, 0.04, z), r)
# front bulges so the cloud has depth and inner outlines
for x, z, r in ((-0.18, -0.12, 0.24), (0.2, -0.1, 0.25), (0.02, 0.12, 0.22), (-0.34, 0.06, 0.2), (0.38, 0.02, 0.19)):
    puff((x, -0.24, z), r)
# stray little puffs flying off
for x, z, r in ((-0.98, -0.28, 0.12), (-1.08, -0.08, 0.075), (0.98, -0.3, 0.11), (1.08, 0.12, 0.08),
                (-0.66, 0.8, 0.09), (0.7, 0.78, 0.1)):
    puff((x, 0.0, z), r, squash=1.0)

# swirl curls on the front puffs (no ink: they are the drawn detail)
for cx, cz, rr, turn in ((-0.19, -0.12, 0.16, 1), (0.21, -0.1, 0.16, -1)):
    pts = []
    for k in range(16):
        t = k / 15
        a = turn * (t * math.pi * 1.6) + math.pi * 0.3
        r = rr * (0.25 + 0.75 * t)
        x, z = cx + math.cos(a) * r, cz + math.sin(a) * r * 0.9
        # sit on the front puff: spherical cap of radius ~0.24 around (cx, -0.24, cz)
        d2 = (x - cx) ** 2 + (z - cz) ** 2
        y = -0.24 - 0.85 * math.sqrt(max(0.0, 0.245 ** 2 - d2)) - 0.012
        pts.append((x, y, z))
    M.no_ink(kit.tube(pts, 0.02, CURL, taper_to=0.3, resolution=4, name='curl'))

M.skip_marked_ink()
M.tri_report()
kit.finalize_prop('smoke_puff', thumb_angle=0, elevation=0.15)
