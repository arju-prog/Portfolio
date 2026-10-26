"""Manga portfolio website diorama: an open black-and-white manga book whose spread pops up into a tiny colored
3D scene (a red-gold staff, a straw hat and a frost-steel axe in front of a paper pop-up backdrop), a dip pen and an
ink bottle beside it, and a browser window floating behind — on a rounded collectible base plate."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()
random.seed(3)

# ── palette ──────────────────────────────────────────────────────────────
BASE_TOP = kit.mat('#f5f2ea', 0.6)
BASE_MAT = kit.mat('#2a9d8f', 0.8)
BASE_TRIM = kit.mat('#17171b', 0.45)
GOLD = kit.mat('#e2b64a', 0.3, metal=0.9)
PAPER = kit.mat('#fbfaf5', 0.85)
PAPER_EDGE = kit.mat('#e9e6dc', 0.9)
INK = kit.mat('#141416', 0.6)
TONE = kit.mat('#c4c4c4', 0.85)
TONE_DK = kit.mat('#8e8e8e', 0.85)
COVER = kit.mat('#1c1c20', 0.5)
STAFF = kit.mat('#c8261e', 0.35)
STAFF_GOLD = kit.mat('#f2b632', 0.25, metal=0.9)
STRAW = kit.mat('#f0bf3c', 0.8)
STRAW_D = kit.mat('#d99a26', 0.8)
HAT_BAND = kit.mat('#c81c22', 0.6)
AXE_STEEL = kit.mat('#a9c3dc', 0.25, metal=0.85)
AXE_DK = kit.mat('#4c6a8a', 0.3, metal=0.8)
RUNE = kit.mat('#5fd0ff', 0.3, emit=1.2)
LEATHER = kit.mat('#6b3f22', 0.7)
LEATHER_DK = kit.mat('#3e2412', 0.7)
GLASS_INK = kit.mat('#121218', 0.06)
CAP = kit.mat('#2a2a30', 0.35, metal=0.4)
LABEL = kit.mat('#f4ecd8', 0.8)
HANKO = kit.mat('#d6302a', 0.6)
PEN = kit.mat('#2c2f3a', 0.3)
NIB = kit.mat('#c9ccd2', 0.2, metal=1.0)
WIN_FRAME = kit.mat('#23253a', 0.35)
WIN_BAR = kit.mat('#3a3e5c', 0.4)
WIN_SCREEN = kit.mat('#f7f5ef', 0.5, emit=0.6)
WIN_INK = kit.mat('#16161a', 0.5, emit=0.2)
WIN_TONE = kit.mat('#cfcfcf', 0.6, emit=0.4)
WIN_ORANGE = kit.mat('#ff7a3d', 0.3, emit=0.9)


# ── helpers ──────────────────────────────────────────────────────────────

def objs():
    return set(o for o in bpy.context.scene.objects if o.type == 'MESH')


def transform(objects, M):
    bpy.context.view_layer.update()
    for o in objects:
        o.matrix_world = M @ o.matrix_world


def _mesh_obj(bm, mats, name):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        me.materials.append(m)
    return obj


def rrect_outline(w, h, r, segs=6):
    r = max(1e-4, min(r, w / 2 - 1e-4, h / 2 - 1e-4))
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism(pts, t, m, M, bevel=0.0, smooth_sides=True, name='prism'):
    """Extrude a 2D outline (local XY) by thickness t along local Z, placed by matrix M."""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, -t / 2)) for x, y in pts]
    top = [bm.verts.new((x, y, t / 2)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    for f in bm.faces:
        f.smooth = smooth_sides
    for e in bm.edges:
        if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6:
            e.smooth = False
    obj = _mesh_obj(bm, m, name)
    obj.matrix_world = M
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    return obj


def slab(w, h, t, r, m, M, bevel=0.0, segs=6):
    return prism(rrect_outline(w, h, r, segs), t, m, M, bevel)


def ellipse_pts(rx, ry, n=24):
    return [(rx * math.cos(2 * math.pi * i / n), ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


FACE = Matrix.Rotation(math.pi / 2, 4, 'X')   # local +Z -> -Y (faces the viewer), local +Y -> +Z


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def RZ(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def RX(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def RY(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


def flat(x, y, z, w, d, r, t, m, bevel=0.0):
    return slab(w, d, t, r, m, T(x, y, z), bevel)


def lathe(profile, mats, face_mat=None, segs=40, name='lathe'):
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z))
                          for k in range(segs)])
    for i, (A, B) in enumerate(zip(rings, rings[1:])):
        for k in range(segs):
            k2 = (k + 1) % segs
            if len(A) == 1:
                f = bm.faces.new((A[0], B[k], B[k2]))
            elif len(B) == 1:
                f = bm.faces.new((A[k], A[k2], B[0]))
            else:
                f = bm.faces.new((A[k], A[k2], B[k2], B[k]))
            f.smooth = True
            f.material_index = face_mat(i, k) if face_mat else 0
    return _mesh_obj(bm, mats, name)


# ── base plate ───────────────────────────────────────────────────────────
BW, BD = 0.9, 0.78
flat(0, 0, 0.0125, BW + 0.03, BD + 0.03, 0.15, 0.025, BASE_TRIM, bevel=0.008)
flat(0, 0, 0.05, BW, BD, 0.13, 0.05, BASE_TOP, bevel=0.012)
flat(0, 0, 0.078, BW - 0.06, BD - 0.06, 0.11, 0.006, BASE_MAT, bevel=0.002)
TOP = 0.081
slab(0.22, 0.032, 0.008, 0.008, GOLD, T(0, -BD / 2 - 0.003, 0.05) @ FACE, bevel=0.002)
for sx in (-1, 1):
    kit.sphere((sx * 0.095, -BD / 2 - 0.008, 0.05), 0.006, GOLD, segs=8, rings=4)

# ── open manga book ─────────────────────────────────────────────────────
BY = -0.04                 # book centre (y)
PW, PD = 0.33, 0.46        # page width (x, per side) and depth (y)
CT = 0.012                 # cover thickness
Z0 = TOP + CT              # top of cover
RISE, HB = 0.06, 0.04      # gutter curve width, page block height


def z_page(u):
    """Height of the page surface at distance u from the gutter."""
    if u >= RISE:
        return Z0 + HB - 0.004 * max(0.0, (u - (PW - 0.03)) / 0.03)
    t = u / RISE
    return Z0 + 0.006 + (HB - 0.006) * (1 - (1 - t) ** 2.2)


for s in (-1, 1):
    slab(PW + 0.016, PD + 0.024, CT, 0.01, COVER, T(s * (PW + 0.016) / 2, BY, TOP + CT / 2), bevel=0.003)
    us = [0.004 + (PW - 0.004) * (i / 20) ** 1.3 for i in range(21)]
    prof = [(s * u, z_page(u)) for u in us] + [(s * PW, Z0), (s * 0.004, Z0)]
    if s < 0:
        prof.reverse()
    prism(prof, PD, PAPER, T(0, BY, 0) @ FACE, name='pages')
    for k in range(5):     # page lines on the fore-edge and the front edge
        z = Z0 + 0.006 + k * 0.007
        kit.box((s * (PW + 0.0005), BY, z), (0.002, PD - 0.01, 0.0018), PAPER_EDGE)
        kit.box((s * (PW * 0.5 + 0.03), BY - PD / 2 - 0.0005, z), (PW - 0.07, 0.002, 0.0018), PAPER_EDGE)
# spine headband
kit.cylinder((0, BY, Z0 + 0.004), 0.006, PD + 0.024, COVER, rot=(math.pi / 2, 0, 0), verts=12)

PZ = Z0 + HB + 0.0012      # decal height on the flat part of the pages


def frame_rect(x0, x1, y0, y1, w=0.0045):
    for (cx, cy, sx, sy) in (((x0 + x1) / 2, y0, x1 - x0 + w, w), ((x0 + x1) / 2, y1, x1 - x0 + w, w),
                             (x0, (y0 + y1) / 2, w, y1 - y0 + w), (x1, (y0 + y1) / 2, w, y1 - y0 + w)):
        kit.box((cx, cy, PZ), (sx, sy, 0.0016), INK)


def manga_panel(x0, x1, y0, y1, kind):
    frame_rect(x0, x1, y0, y1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, d = x1 - x0, y1 - y0
    if kind == 'tone':
        kit.box((cx, cy, PZ - 0.0003), (w - 0.006, d - 0.006, 0.0016), TONE)
        kit.sphere((cx + w * 0.15, cy, PZ + 0.0004), (min(w, d) * 0.28, min(w, d) * 0.28, 0.001), PAPER, segs=20, rings=4)
        kit.sphere((cx + w * 0.15, cy, PZ + 0.0008), (min(w, d) * 0.12, min(w, d) * 0.12, 0.001), INK, segs=16, rings=4)
    elif kind == 'speed':
        fx, fy = cx + w * 0.1, cy
        for k in range(14):
            a = k * 2 * math.pi / 14 + 0.1
            dvec = Vector((math.cos(a), math.sin(a), 0))
            r0 = min(w, d) * 0.22
            p0 = Vector((fx, fy, PZ)) + dvec * r0
            r1 = min(abs((x0 + 0.004 - fx) / dvec.x) if dvec.x < -1e-6 else abs((x1 - 0.004 - fx) / dvec.x) if dvec.x > 1e-6 else 9,
                     abs((y0 + 0.004 - fy) / dvec.y) if dvec.y < -1e-6 else abs((y1 - 0.004 - fy) / dvec.y) if dvec.y > 1e-6 else 9)
            p1 = Vector((fx, fy, PZ)) + dvec * r1
            L = (p1 - p0).length
            kit.box((p0 + p1) / 2, (L, 0.0022, 0.0016), INK, rot=(0, 0, a))
    elif kind == 'bubble':
        kit.box((cx, cy, PZ - 0.0003), (w - 0.006, d - 0.006, 0.0016), TONE_DK)
        prism(ellipse_pts(w * 0.32, d * 0.3), 0.0016, PAPER, T(cx, cy, PZ + 0.0004))
        kit.torus((cx, cy, PZ + 0.0006), 1.0, 0.0018, INK, scale=(w * 0.32, d * 0.3, 1), major_segs=32, minor_segs=4)
        for k in range(2):
            kit.box((cx, cy + 0.008 - k * 0.016, PZ + 0.001), (w * 0.3, 0.004, 0.0016), INK)
    elif kind == 'figure':
        kit.box((cx, cy, PZ - 0.0003), (w - 0.006, d - 0.006, 0.0016), TONE)
        kit.sphere((cx, cy + d * 0.12, PZ + 0.0005), (min(w, d) * 0.16, min(w, d) * 0.16, 0.001), INK, segs=16, rings=4)
        kit.box((cx, cy - d * 0.18, PZ + 0.0005), (min(w, d) * 0.36, d * 0.3, 0.0016), INK)


for s in (-1, 1):
    def X(u):
        return s * u
    us0, us1 = RISE + 0.012, PW - 0.02
    mid = (us0 + us1) / 2
    yb0, yb1 = BY - PD / 2 + 0.02, BY + PD / 2 - 0.02
    manga_panel(min(X(us0), X(us1)), max(X(us0), X(us1)), yb1 - 0.13, yb1, 'speed' if s > 0 else 'tone')
    manga_panel(min(X(us0), X(mid - 0.006)), max(X(us0), X(mid - 0.006)), yb0 + 0.15, yb1 - 0.145,
                'figure' if s > 0 else 'bubble')
    manga_panel(min(X(mid + 0.006), X(us1)), max(X(mid + 0.006), X(us1)), yb0 + 0.15, yb1 - 0.145,
                'bubble' if s > 0 else 'figure')
    manga_panel(min(X(us0), X(us1)), max(X(us0), X(us1)), yb0, yb0 + 0.135, 'tone' if s > 0 else 'speed')

# ── pop-up paper backdrop standing across the gutter ────────────────────
CY = BY + 0.09
CW, CH = 0.5, 0.27
before = objs()
card = [(-CW / 2, 0), (CW / 2, 0), (CW / 2, CH * 0.7), (CW * 0.36, CH * 0.86), (CW * 0.12, CH), (-CW * 0.1, CH * 0.92),
        (-CW * 0.32, CH), (-CW / 2, CH * 0.78)]
prism(card, 0.006, PAPER, FACE, smooth_sides=False, name='card')
# manga ink art on the card: sun burst, sun, mountain silhouettes, clouds
FZ = -0.0035
burst = []
for i in range(32):
    a = i * 2 * math.pi / 32
    r = 0.1 if i % 2 == 0 else 0.055
    burst.append((0.05 + r * 1.15 * math.cos(a), 0.17 + r * 1.15 * math.sin(a) * 0.8))
burst = [(min(max(x, -CW / 2 + 0.01), CW / 2 - 0.01), min(y, CH * 0.84)) for x, y in burst]
prism(burst, 0.0015, TONE, T(0, FZ + 0.0005, 0) @ FACE, smooth_sides=False)
prism(ellipse_pts(0.045, 0.045, 28), 0.0015, PAPER, T(0, FZ - 0.0002, 0) @ FACE @ T(0.05, 0.17, 0))
kit.torus((0.05, FZ - 0.0012, 0.17), 0.045, 0.0025, INK, rot=(math.pi / 2, 0, 0), major_segs=32, minor_segs=4)
mount = [(-CW / 2 + 0.005, 0.0), (CW / 2 - 0.005, 0.0), (CW / 2 - 0.005, 0.05), (0.15, 0.1), (0.09, 0.06),
         (0.0, 0.12), (-0.07, 0.07), (-0.13, 0.13), (-CW / 2 + 0.005, 0.06)]
prism(mount, 0.0015, INK, T(0, FZ - 0.0015, 0) @ FACE, smooth_sides=False)
for (x, z, w) in ((-0.15, 0.21, 0.065), (0.17, 0.22, 0.055)):
    kit.cylinder((x, FZ - 0.002, z), 1.0, 0.0015, PAPER, rot=(math.pi / 2, 0, 0), verts=20, scale=(w, 0.018, 1))
    kit.torus((x, FZ - 0.003, z), 1.0, 0.0018, INK, rot=(math.pi / 2, 0, 0), scale=(w, 0.018, 1), major_segs=24,
              minor_segs=4)
transform(objs() - before, T(0, CY, Z0 + 0.004))
# pop-up fold tabs (paper V-folds) holding the card
for s in (-1, 1):
    x = s * 0.12
    prism([(0, 0), (0.07, 0), (0, 0.07)], 0.004, PAPER_EDGE,
          T(x, CY - 0.004, PZ) @ RZ(90) @ Matrix.Rotation(math.pi / 2, 4, 'X'), smooth_sides=False)
    kit.box((x, CY - 0.035, PZ + 0.0005), (0.008, 0.07, 0.002), PAPER_EDGE)

# mid-ground pop-up layer: a manga wave strip (paper with ink outline + screentone)
before = objs()
wave = [(-0.17, 0.0), (0.17, 0.0)]
for i in range(41):
    x = 0.17 - 0.34 * i / 40
    wave.append((x, 0.05 + 0.018 * math.sin(i * 0.9) + 0.012 * math.cos(i * 0.37)))
prism(wave, 0.005, PAPER, FACE, smooth_sides=False, name='wave')
prism([(x * 0.97, y * 0.6) for x, y in wave], 0.0015, TONE, T(0, -0.003, 0.004) @ FACE, smooth_sides=False)
kit.tube([(x, -0.003, y) for x, y in wave[2:]], 0.0022, INK, resolution=1, smooth_path=False, name='wave_ink')
for k in range(5):
    x = -0.13 + k * 0.065
    kit.tube([(x, -0.004, 0.02), (x + 0.015, -0.004, 0.035), (x + 0.03, -0.004, 0.03)], 0.0018, INK, resolution=3,
             name='curl')
transform(objs() - before, T(0, CY - 0.075, Z0 + 0.004))
for s_ in (-1, 1):
    kit.box((s_ * 0.1, CY - 0.06, PZ + 0.0005), (0.008, 0.03, 0.002), PAPER_EDGE)

# ── colored mini scene popping out of the pages ─────────────────────────
# straw hat on the right page
before = objs()
brim = lathe([(0.042, 0.004), (0.06, 0.002), (0.075, -0.002), (0.079, -0.006), (0.074, -0.008), (0.06, -0.005),
              (0.042, -0.002)], [STRAW], segs=40, name='brim')
crown = lathe([(0.04, 0.0), (0.042, 0.012), (0.043, 0.03), (0.04, 0.043), (0.03, 0.05), (0.015, 0.053), (0.0, 0.054)],
              [STRAW, HAT_BAND, STRAW_D], face_mat=lambda i, k: 1 if i in (0, 1) else 0, segs=40, name='crown')
kit.torus((0, 0, 0.032), 0.0425, 0.0015, STRAW_D, major_segs=40, minor_segs=4)
kit.torus((0, 0, 0.046), 0.034, 0.0015, STRAW_D, major_segs=40, minor_segs=4)
transform(objs() - before, T(0.15, BY - 0.1, PZ + 0.012) @ RY(-10) @ RX(8) @ Matrix.Scale(1.5, 4))

# staff (red with gold caps) leaning against the backdrop on the left
sa, sb = Vector((-0.27, BY - 0.1, PZ + 0.004)), Vector((-0.1, CY - 0.014, Z0 + 0.3))
d = (sb - sa).normalized()
kit.rod(sa + d * 0.03, sb - d * 0.03, 0.014, STAFF, verts=16, caps=False)
for p, q in ((sa, sa + d * 0.035), (sb - d * 0.035, sb)):
    kit.rod(p, q, 0.017, STAFF_GOLD, verts=16, caps=False)
    kit.sphere(p if p is sa else q, 0.017, STAFF_GOLD, segs=16, rings=8)
for t in (0.04, 0.96):
    kit.torus(sa.lerp(sb, t), 0.017, 0.0035, STAFF_GOLD, rot=kit.rot_between(sa, sb), major_segs=16, minor_segs=4)

# axe stuck into the left page (blade buried, handle rising toward the viewer)
before = objs()
blade = [(-0.012, 0.0), (0.03, 0.0), (0.05, -0.02), (0.06, -0.05), (0.058, -0.075), (0.04, -0.083), (0.03, -0.065),
         (0.012, -0.05), (-0.01, -0.04), (-0.025, -0.06), (-0.04, -0.07), (-0.05, -0.05), (-0.04, -0.02)]
blade = [(x, z) for x, z in blade]
prism(blade, 0.014, AXE_STEEL, FACE @ T(0, 0, 0), bevel=0.003, smooth_sides=False, name='blade')
prism([(-0.035, -0.055), (-0.03, -0.065), (0.0, -0.045), (0.035, -0.06), (0.048, -0.072), (0.042, -0.077),
       (0.025, -0.064)], 0.016, AXE_DK, FACE, smooth_sides=False)
kit.box((0.0, 0, -0.012), (0.04, 0.026, 0.03), AXE_DK, bevel=0.005)                     # eye collar
for x in (-0.01, 0.01):
    kit.sphere((x, -0.0085, -0.03), 0.004, RUNE, segs=8, rings=4)
hz = -0.005
kit.rod((-0.002, 0, hz), (0.2, 0, hz), 0.0085, LEATHER, verts=12, caps=False)
for k in range(5):
    kit.torus((0.04 + k * 0.03, 0, hz), 0.0095, 0.0025, LEATHER_DK, rot=(0, math.pi / 2, 0), major_segs=12, minor_segs=4)
kit.sphere((0.205, 0, hz), 0.012, AXE_DK, segs=12, rings=6)
transform(objs() - before, T(-0.1, BY - 0.07, PZ + 0.07) @ RZ(-125) @ RY(-30) @ Matrix.Scale(1.6, 4))

# paper speech bubble "!!" cut-out standing on the right page
before = objs()
bub = ellipse_pts(0.055, 0.04, 28)
prism(bub, 0.004, PAPER, FACE, smooth_sides=False)
kit.torus((0, -0.0025, 0), 1.0, 0.0022, INK, rot=(math.pi / 2, 0, 0), scale=(0.055, 0.04, 1), major_segs=32, minor_segs=4)
prism([(-0.012, -0.03), (0.012, -0.034), (0.02, -0.06)], 0.004, PAPER, FACE, smooth_sides=False)
for x in (-0.012, 0.012):
    kit.box((x, -0.003, 0.006), (0.008, 0.002, 0.03), INK, bevel=0.002)
    kit.sphere((x, -0.003, -0.019), 0.0045, INK, segs=10, rings=5)
kit.box((0, 0.004, -0.07), (0.006, 0.004, 0.04), PAPER_EDGE)
transform(objs() - before, T(0.27, CY - 0.03, PZ + 0.1) @ RZ(-15) @ Matrix.Scale(1.2, 4))

# ── dip pen + ink bottle beside the book ────────────────────────────────
# ink bottle (front right)
IX, IY = 0.33, -0.3
kit.box((IX, IY, TOP + 0.042), (0.085, 0.085, 0.084), GLASS_INK, bevel=0.016)
kit.box((IX, IY, TOP + 0.04), (0.089, 0.089, 0.045), LABEL, bevel=0.01)
kit.cylinder((IX - 0.004, IY - 0.046, TOP + 0.04), 0.012, 0.003, HANKO, rot=(math.pi / 2, 0, 0), verts=20)
for k in range(2):
    kit.box((IX + 0.018, IY - 0.046, TOP + 0.048 - k * 0.014), (0.016, 0.002, 0.004), INK)
kit.cylinder((IX, IY, TOP + 0.092), 0.022, 0.02, GLASS_INK, verts=24)
kit.cylinder((IX, IY, TOP + 0.112), 0.028, 0.03, CAP, verts=24)
kit.torus((IX, IY, TOP + 0.127), 0.026, 0.004, CAP, major_segs=24, minor_segs=6)
for (x, y, r) in ((0.25, -0.33, 0.016), (0.22, -0.3, 0.008), (0.27, -0.36, 0.006), (0.38, -0.22, 0.01)):
    kit.sphere((x, y, TOP + 0.001), (r, r * 0.8, 0.0025), INK, segs=12, rings=4)

# dip pen lying in front of the book, nib towards the ink
pa, pb = Vector((-0.36, -0.33, TOP + 0.014)), Vector((0.14, -0.32, TOP + 0.014))
dv = (pb - pa).normalized()
kit.rod(pa, pa + dv * 0.34, 0.012, PEN, verts=16, r2=0.011, caps=False)
kit.sphere(pa, 0.012, PEN, segs=14, rings=7)
kit.rod(pa + dv * 0.34, pa + dv * 0.39, 0.011, GOLD, verts=16, r2=0.009, caps=False)
kit.torus(pa + dv * 0.345, 0.0115, 0.0025, GOLD, rot=kit.rot_between(pa, pb), major_segs=16, minor_segs=4)
nib0 = pa + dv * 0.39
kit.rod(nib0, pb, 0.008, NIB, verts=12, r2=0.0005, caps=False)
kit.sphere(nib0.lerp(pb, 0.4) + Vector((0, 0, 0.007)), 0.0018, INK, segs=8, rings=4)
kit.box(nib0.lerp(pb, 0.75) + Vector((0, 0, 0.004)), (0.03, 0.0012, 0.002), INK,
        rot=(0, 0, math.atan2(dv.y, dv.x)))
for k in range(5):            # grip ridges
    kit.torus(pa + dv * (0.26 + k * 0.014), 0.012, 0.0018, kit.mat('#454a5a', 0.4), rot=kit.rot_between(pa, pb),
              major_segs=16, minor_segs=4)

# ── browser window floating behind ──────────────────────────────────────
before = objs()
WW, WH = 0.46, 0.3
slab(WW, WH, 0.018, 0.022, WIN_FRAME, FACE, bevel=0.005, segs=6)
slab(WW - 0.02, 0.034, 0.004, 0.01, WIN_BAR, T(0, -0.01, WH / 2 - 0.025) @ FACE, segs=4)
for k, c in enumerate(('#ff5f57', '#febc2e', '#28c840')):
    kit.cylinder((-WW / 2 + 0.03 + k * 0.022, -0.0125, WH / 2 - 0.025), 0.0075, 0.003, kit.mat(c, 0.3, emit=0.6),
                 rot=(math.pi / 2, 0, 0), verts=16)
slab(0.22, 0.016, 0.003, 0.008, WIN_SCREEN, T(0.04, -0.0125, WH / 2 - 0.025) @ FACE, segs=4)
SZ = -0.02
slab(WW - 0.024, WH - 0.06, 0.003, 0.01, WIN_SCREEN, T(0, -0.0095, SZ) @ FACE, segs=4)
# page content: nav, big title bars, a manga panel grid, and a coloured 3D blob (the three.js stage)
fy = -0.0115
kit.box((0, fy, SZ + 0.1), (WW - 0.05, 0.002, 0.014), WIN_INK)
for k, w in enumerate((0.16, 0.12)):
    kit.box((-0.095 + (w - 0.16) / 2, fy, SZ + 0.06 - k * 0.026), (w, 0.002, 0.016), WIN_INK)
kit.box((-0.11, fy, SZ + 0.008), (0.1, 0.002, 0.007), WIN_TONE)
kit.box((-0.12, fy, SZ - 0.006), (0.08, 0.002, 0.007), WIN_TONE)
for k in range(3):
    x = -0.15 + k * 0.08
    kit.box((x, fy, SZ - 0.07), (0.07, 0.002, 0.06), WIN_INK if k == 1 else WIN_TONE)
    kit.box((x, fy - 0.0005, SZ - 0.07), (0.058, 0.002, 0.048), WIN_SCREEN if k != 1 else WIN_INK)
kit.sphere((0.11, -0.012, SZ + 0.0), (0.05, 0.016, 0.05), WIN_ORANGE, segs=24, rings=12)
kit.torus((0.11, -0.03, SZ + 0.0), 0.072, 0.004, WIN_INK, rot=(1.2, 0.3, 0), major_segs=32, minor_segs=4)
transform(objs() - before, T(-0.04, 0.3, 0.5) @ RZ(8) @ RX(-8))

kit.finalize_prop('manga_portfolio')
