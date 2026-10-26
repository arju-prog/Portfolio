"""Chibi Naruto making the Shadow Clone seal: both hands together in front of the chest, the
index+middle fingers of each hand crossed in a '+'. Spiky blond hair, Leaf headband (navy band,
steel plate, engraved leaf), orange jumpsuit with black shoulders, whisker marks, big grin."""
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
import _mini as M  # noqa: E402
from mathutils import Vector as V  # noqa: E402

kit.reset()

SKIN = kit.mat('#f5c9a0', 0.55)
ORANGE = kit.mat('#ff7a12', 0.7)
ORANGE_DK = kit.mat('#e0600c', 0.75)
BLACK = kit.mat('#23242b', 0.65)
HAIR = kit.mat('#ffd02a', 0.45)
HAIR_DK = kit.mat('#f2a81a', 0.45)
NAVY = kit.mat('#1f2f63', 0.8)
STEEL = kit.mat('#cfd6de', 0.25, metal=0.9)
STEEL_DK = kit.mat('#7d8791', 0.35, metal=0.8)
ENGRAVE = kit.mat('#3a4048', 0.4, metal=0.6)
WHITE = kit.mat('#fbfbf7', 0.3)
IRIS = kit.mat('#1f6fd6', 0.2)
IRIS_LT = kit.mat('#7cc4ff', 0.2)
INK = kit.mat('#141414', 0.3)
MOUTH = kit.mat('#6a1a1a', 0.5)
TONGUE = kit.mat('#e0706a', 0.6)
SANDAL = kit.mat('#2546a8', 0.5)
BANDAGE = kit.mat('#eeeae0', 0.8)

HC = V((0, 0, 1.6))   # head centre
R = 0.43


def face_y(x, z, lift=0.0):
    """Front surface of the head ellipsoid at (x, z)."""
    dz = (z - HC.z) / 0.98
    return -0.95 * math.sqrt(max(0.0, R * R - x * x - dz * dz)) - lift


def on_face(x, z, lift=0.0):
    return V((x, face_y(x, z, lift), z))


def flat_top(obj):
    """Squash the upper half of a sphere flat -> a 'D' shape (open grin)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.z *= 0.12
    bm.to_mesh(obj.data)
    bm.free()
    return obj


# ── legs + sandals ──────────────────────────────────────────────────────
for sx in (1, -1):
    hip, knee, ankle = V((0.15 * sx, 0, 0.62)), V((0.2 * sx, -0.05, 0.36)), V((0.21 * sx, 0, 0.13))
    kit.rod(hip, knee, 0.1, ORANGE, verts=16)
    kit.rod(knee, ankle + V((0, 0, 0.06)), 0.092, ORANGE, verts=16, r2=0.1)
    kit.torus(ankle + V((0, 0, 0.07)), 0.095, 0.025, ORANGE_DK, major_segs=24, minor_segs=8)   # rolled cuff
    kit.cylinder(ankle + V((0, 0, 0.0)), 0.065, 0.08, SKIN)
    kit.sphere(ankle + V((0, -0.06, -0.06)), (0.1, 0.16, 0.045), SANDAL)
    kit.sphere(ankle + V((0, -0.14, -0.035)), (0.075, 0.05, 0.035), SKIN, segs=16, rings=8)        # toes
    kit.sphere(ankle + V((0, 0.0, -0.01)), (0.085, 0.09, 0.06), SANDAL)                              # heel strap
# bandage + holster on his right thigh
kit.cylinder((-0.17, -0.02, 0.5), 0.112, 0.07, BANDAGE, rot=(0, 0.15, 0))
kit.box((-0.25, -0.06, 0.48), (0.07, 0.1, 0.12), NAVY, bevel=0.02)

# ── torso: orange jumpsuit, black shoulders/yoke, collar, zip ─────────────
kit.sphere((0, 0, 0.66), (0.25, 0.185, 0.14), ORANGE)
kit.sphere((0, 0, 0.88), (0.25, 0.19, 0.27), ORANGE)
kit.sphere((0, 0, 1.03), (0.265, 0.205, 0.13), BLACK)
kit.torus((0, 0, 1.16), 0.13, 0.055, BLACK, major_segs=28, minor_segs=10)                         # high collar
kit.torus((0, 0, 1.2), 0.125, 0.02, ORANGE, major_segs=28, minor_segs=6)                          # collar rim
kit.cylinder((0, 0, 1.22), 0.085, 0.1, SKIN)
zip_pts = [(0, -0.205, 1.12), (0, -0.215, 1.02), (0, -0.24, 0.9), (0, -0.235, 0.76), (0, -0.2, 0.66)]
kit.tube(zip_pts, 0.011, WHITE, name='zip')
kit.sphere((0, -0.235, 1.06), (0.025, 0.012, 0.035), WHITE, segs=12, rings=6)                     # zip pull

# ── arms: elbows out, hands meeting in the clone seal ─────────────────────
SEAL = V((0, -0.42, 1.02))
for sx, side in ((1, 'l'), (-1, 'r')):
    sh = V((0.26 * sx, 0, 1.07))
    hand = SEAL + V((0.05 * sx, 0.03, -0.02))
    el = M.joint(sh, hand, 0.26, 0.26, (sx, 0.3, -0.6))
    kit.rod(sh, el, 0.078, BLACK, verts=16)
    kit.sphere(sh, 0.1, BLACK, segs=20, rings=10)
    kit.rod(el, hand, 0.07, ORANGE, verts=16, r2=0.064)
    kit.torus(el.lerp(hand, 0.82), 0.068, 0.018, ORANGE_DK, rot=kit.rot_between(el, hand), major_segs=20, minor_segs=6)
    kit.sphere(hand, (0.07, 0.07, 0.075), SKIN, segs=16, rings=8)
# right hand: index + middle fingers straight up; left hand: two fingers crossing horizontally in front
for dx in (-0.024, 0.022):
    kit.rod(SEAL + V((-0.03 + dx, -0.01, 0.03)), SEAL + V((-0.03 + dx, -0.02, 0.3)), 0.025, SKIN, verts=12)
for dz in (0.115, 0.165):
    kit.rod(SEAL + V((0.08, -0.06, dz)), SEAL + V((-0.12, -0.075, dz)), 0.025, SKIN, verts=12)
kit.rod(SEAL + V((0.08, -0.04, 0.03)), SEAL + V((0.08, -0.06, 0.14)), 0.034, SKIN, verts=12)     # left knuckles up to the fingers

# ── head ────────────────────────────────────────────────────────────────
kit.sphere(HC, (R, R * 0.95, R * 0.98), SKIN, segs=32, rings=16)
for sx in (1, -1):
    kit.sphere((R * 0.98 * sx, 0.02, 1.57), (0.05, 0.04, 0.085), SKIN, segs=16, rings=8)
# eyes: white almond, blue iris, pupil, highlights (determined, slightly narrowed)
for sx in (1, -1):
    ex, ez = 0.155 * sx, 1.585
    tilt = (0.2, -0.3 * sx, 0.0)
    kit.sphere(on_face(ex, ez, -0.005), (0.075, 0.03, 0.068), WHITE, rot=tilt, segs=20, rings=10)
    kit.sphere(on_face(ex - 0.012 * sx, ez - 0.004, 0.0), (0.05, 0.03, 0.058), IRIS, rot=tilt, segs=16, rings=8)
    M.no_ink(kit.sphere(on_face(ex - 0.012 * sx, ez - 0.004, 0.012), (0.024, 0.02, 0.03), INK, rot=tilt, segs=12, rings=6))
    M.no_ink(kit.sphere(on_face(ex - 0.03 * sx, ez + 0.022, 0.02), 0.014, WHITE, segs=10, rings=5))
    M.no_ink(kit.sphere(on_face(ex + 0.0, ez - 0.035, 0.014), (0.022, 0.01, 0.012), IRIS_LT, segs=10, rings=5))
    # upper lid line + brow
    kit.tube([on_face(ex + d * sx * 0.08 - 0.0 * sx, ez + 0.06 - abs(d) * 0.02, 0.012) for d in (-1, -0.3, 0.4, 1.1)],
             0.013, INK, resolution=6, name='lid')
    kit.tube([on_face(x * sx, z, 0.012) for x, z in ((0.07, 1.675), (0.15, 1.7), (0.24, 1.705))], 0.016, HAIR_DK,
             taper_to=0.5, resolution=6, name='brow')
    # three whisker marks per cheek
    for k, z in enumerate((1.505, 1.475, 1.445)):
        M.no_ink(kit.tube([on_face(x * sx, z + (x - 0.2) * 0.15 * (k - 1), 0.004) for x in (0.21, 0.25, 0.29)],
                          0.0095, INK, taper_to=0.45, resolution=4, name="whisker"))
# big open grin: D-shaped mouth, teeth, tongue, cheeky corners
mz = 1.43
flat_top(kit.sphere(on_face(0, mz, -0.012), (0.12, 0.03, 0.085), MOUTH, rot=(0.25, 0, 0), segs=24, rings=12))
kit.sphere(on_face(0, mz - 0.006, 0.002), (0.1, 0.02, 0.018), WHITE, rot=(0.25, 0, 0), segs=20, rings=10)
kit.sphere(on_face(0, mz - 0.055, 0.0), (0.06, 0.02, 0.022), TONGUE, rot=(0.3, 0, 0), segs=16, rings=8)

# ── hair: blond cap + big spikes radiating from the crown, bangs over the band ──
kit.sphere((0, 0.05, 1.7), (0.445, 0.43, 0.37), HAIR, segs=32, rings=16)
SP = [((0, 0.05, 1), 0.3), ((0.55, 0.0, 0.84), 0.28), ((-0.55, 0.0, 0.84), 0.28), ((0, 0.6, 0.8), 0.28),
      ((0.5, 0.5, 0.7), 0.26), ((-0.5, 0.5, 0.7), 0.26), ((0.88, 0.15, 0.42), 0.24), ((-0.88, 0.15, 0.42), 0.24),
      ((0, 0.95, 0.3), 0.24), ((0.55, 0.8, 0.2), 0.22), ((-0.55, 0.8, 0.2), 0.22), ((0.3, 0.92, -0.15), 0.2),
      ((-0.3, 0.92, -0.15), 0.2), ((0.32, -0.5, 0.8), 0.24), ((-0.32, -0.5, 0.8), 0.24), ((0, -0.42, 0.9), 0.22),
      ((0.85, 0.45, 0.05), 0.2), ((-0.85, 0.45, 0.05), 0.2)]
for i, (d, L) in enumerate(SP):
    d = V(d).normalized()
    c = V((0, 0.03, 1.66))
    kit.spike(c + d * 0.28, c + d * (0.36 + L) + V((0, 0.04, 0.02)), 0.155, (HAIR, HAIR_DK)[i % 2 if i > 2 else 0],
              verts=16)
for sx, x, L in ((1, 0.27, 0.2), (-1, 0.27, 0.2), (1, 0.12, 0.16), (-1, 0.12, 0.16)):
    base = V((x * sx, -0.3, 1.86))
    kit.spike(base, base + V((0.05 * sx, -0.13, -L)), 0.07, HAIR, verts=14)          # bangs falling over the band
for sx in (1, -1):
    base = V((0.37 * sx, -0.18, 1.72))
    kit.spike(base, base + V((0.06 * sx, -0.06, -0.26)), 0.07, HAIR, verts=14)       # side locks by the ears

# ── Leaf headband ───────────────────────────────────────────────────────
kit.torus((0, 0.0, 1.735), 0.4, 0.045, NAVY, rot=(0.08, 0, 0), scale=(1, 0.97, 1), major_segs=40, minor_segs=10)
PL = V((0, -0.408, 1.74))
kit.box(PL, (0.32, 0.035, 0.125), STEEL, rot=(0.08, 0, 0), bevel=0.016)
for sx in (1, -1):
    for dz in (0.042, -0.042):
        kit.sphere(PL + V((0.135 * sx, -0.02, dz)), 0.011, STEEL_DK, segs=10, rings=5)
# engraved leaf: spiral that sweeps out into a pointed tip, plus a little stem
sp = []
for k in range(14):
    t = k / 13
    a = math.pi * 0.5 + t * math.pi * 1.7
    rr = 0.01 + 0.026 * t
    sp.append(PL + V((math.cos(a) * rr * 1.1, -0.022, math.sin(a) * rr)))
sp += [PL + V((0.04, -0.022, 0.035)), PL + V((0.012, -0.022, 0.05))]
M.no_ink(kit.tube([tuple(p) for p in sp], 0.0065, ENGRAVE, resolution=3, name='leaf'))
M.no_ink(kit.tube([tuple(PL + V((-0.025, -0.022, -0.012))), tuple(PL + V((-0.05, -0.022, -0.04)))], 0.0065,
                  ENGRAVE, name='stem'))
# knot + fluttering tails at the back
kit.sphere((0, 0.4, 1.76), (0.06, 0.04, 0.05), NAVY, segs=16, rings=8)
for sx in (1, -1):
    kit.tube([(0.02 * sx, 0.42, 1.75), (0.12 * sx, 0.55, 1.62), (0.2 * sx, 0.6, 1.48), (0.32 * sx, 0.62, 1.4)],
             0.03, NAVY, taper_to=0.8, resolution=8, name='tail')

M.tri_report()
M.skip_marked_ink()
kit.finalize_prop('naruto_clone', thumb_angle=-15)
