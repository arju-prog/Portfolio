"""Diving eagle (Assassin's Creed Leap of Faith): head-down stoop, wings swept back in a V, brown
body, white head and tail, white-tipped feathers, yellow hooked beak and tucked talons.
Feathers are layered tapered blades (cambered lens cross-section, two-tone tip)."""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
import _mini as M  # noqa: E402
from mathutils import Vector as V  # noqa: E402

kit.reset()

BROWN = kit.mat('#6b4423', 0.75)
BROWN_DK = kit.mat('#4a2e18', 0.8)
BROWN_LT = kit.mat('#93633a', 0.75)
WHITE = kit.mat('#f7f5ef', 0.7)
TIP = kit.mat('#f3efe4', 0.7)
YELLOW = kit.mat('#f4b51f', 0.4)
YELLOW_DK = kit.mat('#c9861a', 0.45)
CLAW = kit.mat('#2a2420', 0.35)
EYE = kit.mat('#1a1208', 0.15)
IRIS = kit.mat('#e8a21c', 0.2, emit=0.3)


def blade(base, tip, width, normal, m, m_tip=None, tip_frac=0.25, camber=0.0, thick=0.014, n=10, name='feather'):
    """Tapered feather: lens cross-section (raised shaft ridge), rounded-pointed tip, optional tip colour.
    `normal` = the side the feather's top surface faces."""
    base, tip, normal = V(base), V(tip), V(normal).normalized()
    d = tip - base
    side = d.cross(normal).normalized()
    nrm = side.cross(d).normalized()
    verts, faces, fmat = [], [], []
    for i in range(n + 1):
        t = i / n
        p = base + d * t + nrm * camber * math.sin(math.pi * t)
        w = width * (0.55 + 0.45 * math.sin(math.pi * min(1.0, t * 1.15))) * math.sqrt(max(0.0, 1 - t ** 3)) / 2
        h = thick * (1 - 0.7 * t)
        verts += [p - side * w, p + nrm * h, p + side * w, p - nrm * h * 0.5]
    for i in range(n):
        a, b = 4 * i, 4 * (i + 1)
        tmat = 1 if (m_tip is not None and (i + 0.5) / n > 1 - tip_frac) else 0
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((a + k, a + k2, b + k2, b + k))
            fmat.append(tmat)
    faces.append((3, 2, 1, 0))
    fmat.append(0)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m)
    if m_tip is not None:
        me.materials.append(m_tip)
    for poly, mi in zip(me.polygons, fmat):
        poly.material_index = mi
        poly.use_smooth = True
    return obj


# ── body (head down, tail up, BACK facing the viewer at -Y) ──────────────
kit.sphere((0, 0.0, 0.04), (0.155, 0.13, 0.33), BROWN, segs=32, rings=16)
kit.sphere((0, -0.03, -0.1), (0.145, 0.11, 0.2), BROWN_DK, segs=24, rings=12)          # mantle
# layered back / scapular feathers pointing towards the tail
for row, z in enumerate((-0.1, 0.05)):
    cnt = 3 if row == 0 else 2
    for k in range(cnt):
        x = (k - (cnt - 1) / 2) * 0.075
        y = -0.12 + abs(x) * 0.5 - row * 0.005
        blade((x, y, z), (x * 1.15, y + 0.02, z + 0.2), 0.11, (0, -1, 0.15),
              (BROWN, BROWN_LT)[(row + k) % 2], thick=0.014, n=6, name='back')

# ── white head (beak down, face tipped towards the viewer), hooked beak, stern eyes ──
kit.sphere((0, -0.02, -0.3), (0.135, 0.125, 0.13), WHITE, segs=24, rings=12)          # neck
HD = V((0, -0.05, -0.42))
kit.sphere(HD, (0.12, 0.118, 0.13), WHITE, segs=32, rings=16)
for k in range(7):
    a = (k - 3) * 0.32
    x, y = math.sin(a) * 0.13, -math.cos(a) * 0.11 - 0.01
    blade((x, y, -0.27), (x * 1.15, y * 1.1, -0.12), 0.08, (x, y, 0.2), WHITE, thick=0.012, n=6, name='ruff')
kit.sphere((0, -0.1, -0.5), (0.05, 0.05, 0.045), YELLOW, segs=16, rings=8)              # cere
kit.tube([(0, -0.1, -0.5), (0, -0.135, -0.575), (0, -0.13, -0.645), (0, -0.095, -0.68)], 0.048, YELLOW,
         taper_to=0.15, resolution=8, name='beak')
kit.tube([(0, -0.07, -0.52), (0, -0.075, -0.585)], 0.034, YELLOW_DK, taper_to=0.4, resolution=6, name='jaw')
BROWG = kit.mat('#cfc6b4', 0.7)
for sx in (1, -1):
    ec = V((0.078 * sx, -0.115, -0.455))
    kit.sphere(ec, (0.03, 0.02, 0.034), IRIS, rot=(0, 0, -0.5 * sx), segs=14, rings=7)
    M.no_ink(kit.sphere(ec + V((-0.004 * sx, -0.012, -0.004)), (0.016, 0.012, 0.018), EYE, segs=10, rings=5))
    # stern brow ridge over the eye, inner end dipping towards the beak
    kit.tube([ec + V((-0.045 * sx, -0.03, -0.015)), ec + V((0.0, -0.022, 0.026)), ec + V((0.04 * sx, 0.0, 0.03))],
             0.017, BROWG, taper_to=0.6, resolution=6, name='brow')

# ── wings: swept back into a tight V, top surface + layered coverts facing the viewer ──
for sx in (1, -1):
    sh = V((0.12 * sx, 0.02, -0.12))
    wr = V((0.37 * sx, 0.08, -0.07))
    hand = V((0.42 * sx, 0.16, 0.12))
    up = V((0.12 * sx, -1, -0.05))
    M.aligned(sh.lerp(wr, 0.5), (0.06, 0.05, 0.16), wr - sh, BROWN_DK)
    M.aligned(wr.lerp(hand, 0.5), (0.05, 0.045, 0.11), hand - wr, BROWN_DK)
    kit.sphere(wr, 0.058, BROWN_DK, segs=16, rings=8)
    # primaries: long, fanning back from the hand
    for k in range(6):
        t = k / 5
        b = wr.lerp(hand, 0.25 + 0.75 * t) + V((0, 0.02, 0))
        ang = 0.04 + 0.3 * t
        dirn = V((math.sin(ang) * sx, 0.16, math.cos(ang))).normalized()
        L = 0.46 + 0.12 * math.sin(math.pi * (0.3 + 0.55 * t))
        blade(b, b + dirn * L, 0.1, up, BROWN, TIP, tip_frac=0.22, camber=-0.02, thick=0.018, name='primary')
    # secondaries: along the forearm, pointing back to the tail
    for k in range(5):
        t = k / 4
        b = sh.lerp(wr, 0.15 + 0.85 * t) + V((0, 0.0, 0.0))
        dirn = V((0.1 * sx * t, 0.12, 1)).normalized()
        blade(b, b + dirn * (0.38 + 0.04 * t), 0.12, up, BROWN, TIP, tip_frac=0.18, camber=-0.015, thick=0.016,
              name='secondary')
    # coverts: two bold rows over the bases
    for row, (L, w, mm, dy, cnt) in enumerate(((0.26, 0.11, BROWN_LT, -0.035, 6), (0.15, 0.1, BROWN_DK, -0.06, 5))):
        for k in range(cnt):
            t = k / (cnt - 1)
            b = sh.lerp(hand, 0.06 + 0.86 * t) + V((0, dy, -0.02))
            dirn = V((0.22 * sx * t, 0.1, 1)).normalized()
            blade(b, b + dirn * L, w, up, mm, thick=0.016, n=6, name='covert')

# ── tail: white fan ──────────────────────────────────────────────────────
for k in range(5):
    a = (k - 2) * 0.17
    b = V((math.sin(a) * 0.04, 0.02 + abs(k - 2) * 0.012, 0.3))
    blade(b, b + V((math.sin(a) * 0.3, 0.02, math.cos(a) * 0.34)), 0.15, (0, -1, 0), WHITE, thick=0.016,
          name='tail')
for k in range(3):
    x = (k - 1) * 0.07
    blade((x, -0.08, 0.2), (x * 1.3, -0.04, 0.4), 0.09, (0, -1, 0), (BROWN, BROWN_LT, BROWN)[k], thick=0.014, n=6,
          name='uppertail')

# ── talons tucked under the tail, gripping toes peeking out at its sides ──
for sx in (1, -1):
    foot = V((0.105 * sx, 0.06, 0.33))
    kit.rod(V((0.07 * sx, 0.06, 0.18)), foot, 0.026, YELLOW, verts=12)
    kit.sphere(foot, (0.04, 0.035, 0.035), YELLOW, segs=12, rings=6)
    for k in range(3):
        a = (k - 1) * 0.55 + 0.5
        toe = foot + V((math.sin(a) * 0.06 * sx, -0.015, math.cos(a) * 0.05))
        kit.rod(foot, toe, 0.016, YELLOW, verts=10)
        kit.spike(toe, toe + V((math.sin(a) * 0.012 * sx, -0.03, -0.022)), 0.014, CLAW, verts=8)

M.skip_marked_ink()
M.tri_report()
kit.finalize_prop('eagle', thumb_angle=-28, elevation=0.3)
