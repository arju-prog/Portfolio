"""Competitive-programming desk diorama: a shiny gold trophy cup on a stepped marble plinth with a little
chef's hat perched on one handle, three gold stars floating above (3-star rating), a star plaque, an open
laptop showing code, and a stack of algorithm books with a rubber duck on top — on a round wooden base."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, mat, rod, sphere, torus, tube  # noqa: E402

kit.reset()
random.seed(9)

GOLD = mat('#f2b632', 0.18, metal=1.0)
GOLD_D = mat('#c98e1c', 0.28, metal=1.0)
MARBLE = mat('#24252e', 0.25)
MARBLE_L = mat('#3a3c4a', 0.3)
PLINTH = mat('#2b2f45', 0.5)
WOOD = mat('#6e4426', 0.5)
WOOD_D = mat('#8a5a32', 0.65)
FELT = mat('#2e5a4a', 0.85)
WHITE = mat('#fbfbf8', 0.6)
SILVER = mat('#c9ced6', 0.3, metal=0.8)
KEYS = mat('#2a2d36', 0.5)
SCREEN = mat('#1b1e2a', 0.3, emit=0.5)
CODE = [mat('#ff7a90', 0.3, emit=2.0), mat('#7ad7ff', 0.3, emit=2.0), mat('#ffd36a', 0.3, emit=2.0),
        mat('#9cff8a', 0.3, emit=2.0), mat('#c9a2ff', 0.3, emit=2.0)]
GREEN_EM = mat('#3ddc84', 0.3, emit=2.5)
DUCK = mat('#ffd21f', 0.4)
BEAK = mat('#ff8a1c', 0.4)
INK = mat('#141414', 0.3)
PAGES = mat('#f6eedb', 0.7)
BOOKS = [mat('#d6453d', 0.55), mat('#3d6fd6', 0.55), mat('#3aa66a', 0.55), mat('#7b4fd1', 0.55)]
MUG = mat('#e9edf2', 0.35)
COFFEE = mat('#4a2c18', 0.2)


# ── helpers ──────────────────────────────────────────────────────────────

def _mesh_obj(bm, m, name, smooth=False):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    return obj


def rounded_slab(w, d, r, z0, z1, m, bevel=0.0, segs=8, cx=0.0, cy=0.0, name='slab'):
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = sx * (w / 2 - r), sy * (d / 2 - r)
        for i in range(segs + 1):
            if r >= min(w, d) / 2 - 1e-6 and i == segs:
                continue      # full circle: skip duplicate quadrant joints
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + ccx + math.cos(a) * r, cy + ccy + math.sin(a) * r))
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    obj = _mesh_obj(bm, m, name)
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(50)
        mod.harden_normals = True
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def lathe_z(profile, m, segs=48, name='lathe', loc=(0, 0, 0)):
    bm = bmesh.new()
    n = len(profile)
    rows = []
    for i in range(segs):
        a = i * 2 * math.pi / segs
        rows.append([bm.verts.new((loc[0] + math.cos(a) * r, loc[1] + math.sin(a) * r, loc[2] + z))
                     for r, z in profile])
    for i in range(segs):
        r0, r1 = rows[i], rows[(i + 1) % segs]
        for j in range(n - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    return _mesh_obj(bm, m, name, smooth=True)


def mark():
    return set(bpy.context.scene.objects)


def place(before, loc=(0, 0, 0), yaw=0.0, tilt=(0.0, 0.0), scale=1.0):
    bpy.context.view_layer.update()
    M = (Matrix.Translation(Vector(loc)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(tilt[1], 4, 'Y')
         @ Matrix.Rotation(tilt[0], 4, 'X') @ Matrix.Scale(scale, 4))
    for o in set(bpy.context.scene.objects) - before:
        o.matrix_world = M @ o.matrix_world


def star(r_out=0.1, r_in=0.045, t=0.04, m=GOLD, bevel=0.01):
    """Five-pointed star prism in the XZ plane (facing -Y), centred at the origin."""
    bm = bmesh.new()
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((math.cos(a) * r, math.sin(a) * r))
    front = [bm.verts.new((x, -t / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, t / 2, z)) for x, z in pts]
    cf = bm.verts.new((0, -t / 2 - t * 0.35, 0))     # slight pyramid bulge on both faces
    cb = bm.verts.new((0, t / 2 + t * 0.35, 0))
    for i in range(10):
        j = (i + 1) % 10
        bm.faces.new((front[i], front[j], cf))
        bm.faces.new((back[j], back[i], cb))
        bm.faces.new((front[j], front[i], back[i], back[j]))
    obj = _mesh_obj(bm, m, 'star')
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(35)
        mod.harden_normals = True
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


# ── round base plate ─────────────────────────────────────────────────────
W = 2.0
rounded_slab(W, W, W / 2, 0.0, 0.16, PLINTH, bevel=0.03, segs=16, name='plinth')
rounded_slab(W + 0.03, W + 0.03, (W + 0.03) / 2, 0.05, 0.075, GOLD_D, bevel=0.008, segs=16, name='trim')
rounded_slab(W - 0.07, W - 0.07, (W - 0.07) / 2, 0.16, 0.2, WOOD, bevel=0.012, segs=16, name='desk')
FZ = 0.2

# ── stepped plinth ───────────────────────────────────────────────────────
TX, TY = -0.08, 0.22
z = FZ
for (w, h, m) in ((0.78, 0.12, MARBLE), (0.62, 0.11, MARBLE_L), (0.46, 0.1, MARBLE)):
    box((TX, TY, z + h / 2), (w, w, h), m, bevel=0.018)
    box((TX, TY, z + h - 0.006), (w + 0.012, w + 0.012, 0.012), GOLD_D, bevel=0.004)   # gold edge trim
    z += h
TZ = z
# front plaque with three stars + a little rating bar
box((TX, TY - 0.39 - 0.006, FZ + 0.06), (0.4, 0.012, 0.08), GOLD, bevel=0.004)
for k in range(3):
    b = mark()
    star(0.024, 0.011, 0.008, INK, bevel=0)
    place(b, (TX - 0.07 + k * 0.07, TY - 0.404, FZ + 0.06))
box((TX, TY - 0.31 - 0.006, FZ + 0.175), (0.26, 0.01, 0.05), GOLD_D, bevel=0.004)
box((TX, TY - 0.317, FZ + 0.175), (0.2, 0.004, 0.012), INK)

# ── trophy cup ───────────────────────────────────────────────────────────
cup = [(0.001, 0.0), (0.17, 0.0), (0.175, 0.02), (0.165, 0.035), (0.13, 0.05), (0.09, 0.09), (0.05, 0.15),
       (0.04, 0.19), (0.075, 0.215), (0.08, 0.235), (0.045, 0.265), (0.035, 0.3), (0.05, 0.33),
       (0.11, 0.37), (0.2, 0.43), (0.255, 0.5), (0.28, 0.6), (0.29, 0.69), (0.31, 0.715), (0.312, 0.735),
       (0.29, 0.745), (0.27, 0.72), (0.255, 0.62), (0.225, 0.52), (0.15, 0.45), (0.001, 0.43)]
lathe_z(cup, GOLD, segs=56, name='cup', loc=(TX, TY, TZ))
torus((TX, TY, TZ + 0.235), 0.082, 0.012, GOLD_D, major_segs=32, minor_segs=8)     # knob ring
torus((TX, TY, TZ + 0.6), 0.282, 0.01, GOLD_D, major_segs=56, minor_segs=8)        # decorative band
torus((TX, TY, TZ + 0.025), 0.172, 0.012, GOLD_D, major_segs=48, minor_segs=8)     # foot ring
# handles
for sx in (-1, 1):
    pts = [(TX + sx * 0.27, TY, TZ + 0.66), (TX + sx * 0.38, TY, TZ + 0.7), (TX + sx * 0.45, TY, TZ + 0.62),
           (TX + sx * 0.42, TY, TZ + 0.5), (TX + sx * 0.32, TY, TZ + 0.44), (TX + sx * 0.22, TY, TZ + 0.43)]
    tube(pts, 0.026, GOLD, resolution=10, name='handle')
    sphere((TX + sx * 0.22, TY, TZ + 0.43), 0.03, GOLD, segs=14, rings=8)
# front emblem: a raised star medallion on the bowl
b = mark()
cylinder((0, 0, 0), 0.085, 0.02, GOLD, rot=(math.pi / 2, 0, 0), verts=32)
torus((0, -0.01, 0), 0.085, 0.008, GOLD, rot=(math.pi / 2, 0, 0), major_segs=32, minor_segs=6)
b2 = mark()
star(0.06, 0.026, 0.02, GOLD, bevel=0.004)
place(b2, (0, -0.015, 0))
place(b, (TX, TY - 0.275, TZ + 0.56), tilt=(-0.15, 0))

# ── chef's hat perched on the right handle ───────────────────────────────
b = mark()
cylinder((0, 0, 0.045), 0.075, 0.09, WHITE, verts=24)
for k in range(12):   # pleats
    a = k * math.pi / 6
    cylinder((math.cos(a) * 0.075, math.sin(a) * 0.075, 0.05), 0.009, 0.08, WHITE, verts=6)
torus((0, 0, 0.005), 0.075, 0.01, mat('#e6e2d8', 0.6), major_segs=24, minor_segs=6)
for (dx, dy, dz, r) in ((0, 0, 0.16, 0.09), (0.06, 0.0, 0.13, 0.06), (-0.06, 0.0, 0.13, 0.06),
                        (0.0, 0.06, 0.13, 0.06), (0.0, -0.06, 0.13, 0.06), (0.04, 0.04, 0.17, 0.06),
                        (-0.04, -0.04, 0.17, 0.06), (0.04, -0.04, 0.17, 0.06), (-0.04, 0.04, 0.17, 0.06)):
    sphere((dx, dy, dz), r, WHITE, segs=16, rings=8)
place(b, (TX + 0.41, TY - 0.01, TZ + 0.695), yaw=0.3, tilt=(0.0, 0.3))

# ── three floating gold stars (3-star rating) ────────────────────────────
for k, (dx, dz, s, roll) in enumerate(((-0.3, 0.96, 0.85, 0.25), (0.0, 1.08, 1.0, 0.0), (0.3, 0.96, 0.85, -0.25))):
    b = mark()
    star(0.12 * s, 0.054 * s, 0.045 * s)
    place(b, (TX + dx, TY - 0.04, TZ + dz), yaw=-0.25, tilt=(0.12, roll))

# ── open laptop with code (front right) ──────────────────────────────────
b = mark()
LW, LD = 0.44, 0.3
box((0, 0, 0.012), (LW, LD, 0.024), SILVER, bevel=0.008)
box((0, 0.03, 0.0245), (LW - 0.06, LD * 0.48, 0.003), KEYS)
for i in range(11):                                                                   # key caps grid
    for j in range(4):
        box((-LW / 2 + 0.055 + i * 0.0315, 0.03 + (j - 1.5) * 0.031, 0.027), (0.024, 0.024, 0.004), SILVER)
box((0, -0.095, 0.0245), (0.13, 0.07, 0.002), mat('#b5bac3', 0.3, metal=0.7))      # trackpad
hb = mark()
SH = 0.28
box((0, 0, SH / 2), (LW, 0.016, SH), SILVER, bevel=0.007)
box((0, -0.009, SH / 2 + 0.008), (LW - 0.04, 0.003, SH - 0.05), SCREEN)
# code lines: indentation + colourful tokens
lines = [(0, [2, 3, 1]), (1, [3, 2]), (1, [2, 4, 1]), (2, [3, 2]), (2, [5]), (1, [1]), (1, [2, 3]), (0, [1])]
for li, (indent, toks) in enumerate(lines):
    x = -LW / 2 + 0.04 + indent * 0.03
    zz = SH - 0.045 - li * 0.028
    for ti, tl in enumerate(toks):
        wl = tl * 0.022
        box((x + wl / 2, -0.0115, zz), (wl, 0.003, 0.012), CODE[(li + ti) % len(CODE)])
        x += wl + 0.01
box((LW / 2 - 0.07, -0.0115, 0.045), (0.09, 0.003, 0.03), GREEN_EM)              # "Accepted" banner
bpy.context.view_layer.update()
for o in set(bpy.context.scene.objects) - hb:
    o.matrix_world = (Matrix.Translation((0, LD / 2 - 0.01, 0.024)) @ Matrix.Rotation(math.radians(-14), 4, 'X')
                      @ o.matrix_world)
place(b, (0.5, -0.38, FZ), yaw=0.42)

# ── book stack + rubber duck (front left) ────────────────────────────────
b = mark()
zb = 0.0
for i, (w, d, h, rz) in enumerate(((0.36, 0.27, 0.06, 0.0), (0.33, 0.25, 0.055, 0.12), (0.34, 0.24, 0.05, -0.08))):
    bb = mark()
    box((0, 0, h / 2), (w, d, h), BOOKS[i], bevel=0.008)
    box((0.006, 0, h / 2), (w - 0.012, d - 0.02, h - 0.016), PAGES)
    box((-w / 2 - 0.001, 0, h / 2), (0.006, d * 0.7, h * 0.3), GOLD_D)               # spine band
    box((0, -d / 2 - 0.001, h / 2), (w - 0.04, 0.004, h * 0.25), BOOKS[(i + 1) % 4])
    place(bb, (0, 0, zb), yaw=rz)
    zb += h
# duck
cz = zb
sphere((0, 0.01, cz + 0.07), (0.1, 0.085, 0.07), DUCK, segs=20, rings=10)
sphere((0, 0.08, cz + 0.11), (0.03, 0.03, 0.04), DUCK, rot=(-0.5, 0, 0), segs=12, rings=6)   # tail
sphere((0, -0.045, cz + 0.16), 0.06, DUCK, segs=20, rings=10)
sphere((0, -0.105, cz + 0.15), (0.035, 0.03, 0.014), BEAK, segs=14, rings=7)
for sx in (-1, 1):
    sphere((sx * 0.027, -0.093, cz + 0.178), 0.011, INK, segs=10, rings=5)
    sphere((sx * 0.027 - 0.003, -0.102, cz + 0.182), 0.003, WHITE, segs=6, rings=3)
    sphere((sx * 0.075, 0.01, cz + 0.075), (0.02, 0.06, 0.035), DUCK, rot=(0.2, 0, 0), segs=12, rings=6)  # wings
place(b, (-0.56, -0.36, FZ), yaw=-0.35)

# ── coffee mug + sticky note ─────────────────────────────────────────────
cylinder((0.6, 0.38, FZ + 0.06), 0.06, 0.12, MUG, verts=24)
cylinder((0.6, 0.38, FZ + 0.115), 0.052, 0.008, COFFEE, verts=20)
torus((0.665, 0.38, FZ + 0.065), 0.03, 0.01, MUG, rot=(math.pi / 2, 0, 0), major_segs=14, minor_segs=6)
box((0.42, 0.62, FZ + 0.002), (0.14, 0.14, 0.004), mat('#ffe066', 0.7), rot=(0, 0, 0.3))
box((0.42, 0.62, FZ + 0.005), (0.08, 0.012, 0.002), INK, rot=(0, 0, 0.3))
# a pencil
rod((-0.5, 0.48, FZ + 0.012), (-0.28, 0.6, FZ + 0.012), 0.012, mat('#ffbf2e', 0.5), verts=6, caps=False)
kit.spike((-0.28, 0.6, FZ + 0.012), (-0.25, 0.617, FZ + 0.012), 0.012, mat('#f0d2a8', 0.6), verts=6)
cylinder((-0.51, 0.475, FZ + 0.012), 0.012, 0.025, mat('#ff8fa0', 0.6), rot=(0, math.pi / 2, math.atan2(0.12, 0.22)),
         verts=8)

kit.finalize_prop('codechef_trophy', thumb_angle=-22, elevation=0.4)
