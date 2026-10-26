"""BITS Pilani desk diorama: a stylised, symmetric cream/sand clock-tower main building — arched colonnade
wings, a projecting portico with a grand arched entrance, a square clock tower (clock faces on all four sides)
with an arched belfry and a dome, corner chhatris and a balustrade, steps, lawn, hedges and trees."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, mat, rod, sphere, torus  # noqa: E402

kit.reset()
random.seed(4)

CREAM = mat('#f1dfb8', 0.7)
SAND = mat('#dcb97f', 0.7)
TRIM = mat('#c79b5c', 0.65)
RECESS = mat('#6a4a2c', 0.85)
DOME = mat('#f4e4c2', 0.55)
GOLD = mat('#e0aa3e', 0.25, metal=0.9)
FACE = mat('#fdf8ec', 0.4)
HAND = mat('#2a2018', 0.5)
PLINTH = mat('#4a3a2c', 0.55)
TRIM_BASE = mat('#c99a4e', 0.35, metal=0.6)
GRASS = mat('#86c46a', 0.75)
HEDGE = mat('#4f9a46', 0.65)
PATH = mat('#e2c993', 0.8)
TRUNK = mat('#7a5233', 0.8)
LEAF1 = mat('#4fae4f', 0.6)
LEAF2 = mat('#3c9447', 0.6)
LEAF3 = mat('#6cc35a', 0.6)
FLOWER1 = mat('#ff6f7d', 0.5)
FLOWER2 = mat('#ffd54a', 0.5)
WARM = mat('#ffd98a', 0.4, emit=0.6)


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


def on_face(face, u, z, du, dz, dn, off, m, bevel=0.0):
    """Box on a facade. face = (axis 'x'|'y', plane coordinate, outward sign)."""
    axis, c, s = face
    if axis == 'y':
        return box((u, c + s * off, z), (du, dn, dz), m, bevel=bevel)
    return box((c + s * off, u, z), (dn, du, dz), m, bevel=bevel)


def arch(face, u, zb, w, h, depth=0.02, frame=True, m=RECESS):
    """Dark arched opening (rectangle + semicircle) set into a facade, with a light arch moulding."""
    axis, c, s = face
    r = w / 2
    rect_h = h - r
    on_face(face, u, zb + rect_h / 2, w, rect_h, depth, 0.0, m)
    rot = (math.pi / 2, 0, 0) if axis == 'y' else (0, math.pi / 2, 0)
    pos = (u, c, zb + rect_h) if axis == 'y' else (c, u, zb + rect_h)
    cylinder(pos, r, depth, m, rot=rot, verts=12, smooth=False)
    if frame:
        # half-ring moulding around the arch head
        fpos = (u, c + s * 0.006, zb + rect_h) if axis == 'y' else (c + s * 0.006, u, zb + rect_h)
        t = torus(fpos, r + 0.006, 0.006, CREAM if m is RECESS else TRIM, rot=rot, major_segs=14, minor_segs=4)
        # remove the lower half of the ring
        bm = bmesh.new()
        bm.from_mesh(t.data)
        kill = [v for v in bm.verts if v.co.y < -1e-4] if axis == 'y' else [v for v in bm.verts if v.co.x > 1e-4]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(t.data)
        bm.free()
        on_face(face, u, zb + rect_h + r + 0.008, 0.016, 0.022, 0.012, 0.006, TRIM)   # keystone


def chhatri(x, y, z, r=0.05, h=0.08):
    """Small domed pavilion on four slender posts."""
    box((x, y, z + 0.01), (r * 2.3, r * 2.3, 0.02), TRIM, bevel=0.004)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rod((x + sx * r * 0.8, y + sy * r * 0.8, z + 0.02), (x + sx * r * 0.8, y + sy * r * 0.8, z + 0.02 + h),
                0.007, CREAM, verts=8, caps=False)
    box((x, y, z + 0.03 + h), (r * 2.3, r * 2.3, 0.022), TRIM, bevel=0.004)
    sphere((x, y, z + 0.04 + h), (r * 1.05, r * 1.05, r * 1.2), DOME, segs=18, rings=10)
    sphere((x, y, z + 0.04 + h + r * 1.2), 0.012, GOLD, segs=8, rings=4)
    kit.spike((x, y, z + 0.05 + h + r * 1.2), (x, y, z + 0.09 + h + r * 1.2), 0.006, GOLD, verts=8)


def balustrade(x0, x1, y, z, axis='x', n=None):
    L = abs(x1 - x0)
    n = n or max(2, int(L / 0.035))
    for k in range(n + 1):
        t = x0 + (x1 - x0) * k / n
        if axis == 'x':
            cylinder((t, y, z + 0.02), 0.007, 0.04, CREAM, verts=6)
        else:
            cylinder((y, t, z + 0.02), 0.007, 0.04, CREAM, verts=6)
    if axis == 'x':
        box(((x0 + x1) / 2, y, z + 0.045), (L + 0.02, 0.025, 0.012), TRIM)
    else:
        box((y, (x0 + x1) / 2, z + 0.045), (0.025, L + 0.02, 0.012), TRIM)


def clock(face, u, z, r=0.085):
    axis, c, s = face
    rot = (math.pi / 2, 0, 0) if axis == 'y' else (0, math.pi / 2, 0)

    def at(du, dz, off):
        return (u + du, c + s * off, z + dz) if axis == 'y' else (c + s * off, u + du, z + dz)
    cylinder(at(0, 0, 0.006), r + 0.016, 0.014, TRIM, rot=rot, verts=32)
    cylinder(at(0, 0, 0.012), r, 0.012, FACE, rot=rot, verts=32)
    torus(at(0, 0, 0.018), r, 0.008, GOLD, rot=rot, major_segs=32, minor_segs=6)
    for k in range(12):
        a = k * math.pi / 6
        size = 0.016 if k % 3 == 0 else 0.008
        p = at(math.sin(a) * r * 0.78, math.cos(a) * r * 0.78, 0.02)
        box(p, (size, size, size) if axis == 'y' else (size, size, size), HAND)
    # hands (10:10)
    for ang, ln, wd in ((math.radians(-60), r * 0.5, 0.012), (math.radians(60), r * 0.72, 0.008)):
        p = at(math.sin(ang) * ln / 2, math.cos(ang) * ln / 2, 0.022)
        if axis == 'y':
            box(p, (wd, 0.006, ln), HAND, rot=(0, ang, 0))
        else:
            box(p, (0.006, wd, ln), HAND, rot=(-ang, 0, 0))
    sphere(at(0, 0, 0.026), 0.009, GOLD, segs=8, rings=4)


def tree(x, y, z, s=1.0):
    h = 0.24 * s
    kit.cone((x, y, z + h / 2), 0.03 * s, 0.018 * s, h, TRUNK, verts=10)
    blobs = [(0, 0, h + 0.1 * s, 0.13), (0.07, 0.03, h + 0.05 * s, 0.1), (-0.07, -0.02, h + 0.06 * s, 0.1),
             (0.01, -0.06, h + 0.04 * s, 0.09), (-0.02, 0.06, h + 0.16 * s, 0.09)]
    for i, (dx, dy, dz, r) in enumerate(blobs):
        sphere((x + dx * s, y + dy * s, z + dz), r * s, [LEAF1, LEAF2, LEAF3][i % 3], segs=14, rings=8)


# ── base plate + grounds ─────────────────────────────────────────────────
W = 2.0
rounded_slab(W, W, 0.24, 0.0, 0.16, PLINTH, bevel=0.03, name='plinth')
rounded_slab(W + 0.03, W + 0.03, 0.255, 0.05, 0.075, TRIM_BASE, bevel=0.008, name='trim')
rounded_slab(W - 0.07, W - 0.07, 0.2, 0.16, 0.2, GRASS, bevel=0.012, name='lawn')
FZ = 0.2
rounded_slab(0.36, 0.86, 0.05, FZ, FZ + 0.012, PATH, cx=0.0, cy=-0.52, name='path')           # main avenue
rounded_slab(1.86, 0.14, 0.05, FZ, FZ + 0.012, PATH, cx=0.0, cy=-0.08, name='forecourt')     # walk along facade
# hedges lining the avenue + flower beds
for sx in (-1, 1):
    for k in range(3):
        box((sx * 0.25, -0.38 - k * 0.2, FZ + 0.03), (0.06, 0.15, 0.06), HEDGE, bevel=0.02)
    rounded_slab(0.36, 0.24, 0.1, FZ, FZ + 0.025, mat('#6b4a2e', 0.9), cx=sx * 0.6, cy=-0.55, name='bed')
    for k in range(10):
        a = random.uniform(0, 2 * math.pi)
        rr = random.uniform(0, 0.08)
        sphere((sx * 0.6 + math.cos(a) * rr * 1.5, -0.55 + math.sin(a) * rr, FZ + 0.04), 0.022,
               FLOWER1 if k % 2 else FLOWER2, segs=8, rings=4)
    tree(sx * 0.78, -0.18, FZ, s=1.0)
    tree(sx * 0.8, 0.82, FZ, s=0.85)

# ── main building ────────────────────────────────────────────────────────
Y0, Y1 = 0.02, 0.5          # wing front / back faces
X1 = 0.82                    # half width
box((0, (Y0 + Y1) / 2, FZ + 0.025), (2 * X1 + 0.08, Y1 - Y0 + 0.08, 0.05), SAND, bevel=0.008)     # podium
WZ0, WZ1 = FZ + 0.05, FZ + 0.5
box((0, (Y0 + Y1) / 2, (WZ0 + WZ1) / 2), (2 * X1, Y1 - Y0, WZ1 - WZ0), CREAM, bevel=0.006)
box((0, (Y0 + Y1) / 2, FZ + 0.28), (2 * X1 + 0.02, Y1 - Y0 + 0.02, 0.02), TRIM, bevel=0.004)     # floor band
box((0, (Y0 + Y1) / 2, WZ1 + 0.012), (2 * X1 + 0.04, Y1 - Y0 + 0.04, 0.024), TRIM, bevel=0.005)  # cornice
balustrade(-X1, -0.32, Y0, WZ1 + 0.024)
balustrade(0.32, X1, Y0, WZ1 + 0.024)
balustrade(-X1, X1, Y1, WZ1 + 0.024)
balustrade(Y0, Y1, -X1, WZ1 + 0.024, axis='y', n=12)
balustrade(Y0, Y1, X1, WZ1 + 0.024, axis='y', n=12)
# wing end pavilions (slightly projecting, with chhatris)
for sx in (-1, 1):
    box((sx * (X1 - 0.08), (Y0 + Y1) / 2, (WZ0 + WZ1) / 2 + 0.02), (0.18, Y1 - Y0 + 0.06, WZ1 - WZ0 + 0.04),
        CREAM, bevel=0.006)
    box((sx * (X1 - 0.08), (Y0 + Y1) / 2, WZ1 + 0.05), (0.2, Y1 - Y0 + 0.08, 0.02), TRIM, bevel=0.004)
    chhatri(sx * (X1 - 0.08), Y0 + 0.06, WZ1 + 0.06, r=0.045, h=0.07)
    chhatri(sx * (X1 - 0.08), Y1 - 0.06, WZ1 + 0.06, r=0.045, h=0.07)
    arch(('y', Y0 - 0.03, -1), sx * (X1 - 0.08), FZ + 0.07, 0.08, 0.16)
    arch(('y', Y0 - 0.03, -1), sx * (X1 - 0.08), FZ + 0.31, 0.06, 0.13)
    arch(('y', Y1 + 0.03, 1), sx * (X1 - 0.08), FZ + 0.07, 0.08, 0.16)
    arch(('y', Y1 + 0.03, 1), sx * (X1 - 0.08), FZ + 0.31, 0.06, 0.13)
    for k in range(3):   # side faces
        u = Y0 + 0.08 + k * (Y1 - Y0 - 0.16) / 2
        arch(('x', sx * X1, sx), u, FZ + 0.07, 0.07, 0.16)
        arch(('x', sx * X1, sx), u, FZ + 0.31, 0.05, 0.12)
# colonnade arches along the wings, front and back
for sx in (-1, 1):
    for k in range(4):
        x = sx * (0.39 + k * 0.085)
        arch(('y', Y0, -1), x, FZ + 0.07, 0.06, 0.17)
        arch(('y', Y0, -1), x, FZ + 0.31, 0.045, 0.13)
        arch(('y', Y1, 1), x, FZ + 0.07, 0.06, 0.17)
        arch(('y', Y1, 1), x, FZ + 0.31, 0.045, 0.13)

# ── central portico ──────────────────────────────────────────────────────
PX, PY0, PY1 = 0.3, -0.16, 0.56
PZ1 = FZ + 0.68
box((0, (PY0 + PY1) / 2, (FZ + PZ1) / 2), (2 * PX, PY1 - PY0, PZ1 - FZ), CREAM, bevel=0.006)
box((0, (PY0 + PY1) / 2, FZ + 0.025), (2 * PX + 0.04, PY1 - PY0 + 0.04, 0.05), SAND, bevel=0.008)
box((0, (PY0 + PY1) / 2, FZ + 0.28), (2 * PX + 0.02, PY1 - PY0 + 0.02, 0.02), TRIM, bevel=0.004)
box((0, (PY0 + PY1) / 2, PZ1 + 0.012), (2 * PX + 0.05, PY1 - PY0 + 0.05, 0.026), TRIM, bevel=0.005)
for sy, yy in ((-1, PY0), (1, PY1)):
    face = ('y', yy, sy)
    arch(face, 0, FZ + 0.07, 0.17, 0.34, depth=0.03)                  # grand entrance arch
    for sx in (-1, 1):
        arch(face, sx * 0.19, FZ + 0.07, 0.07, 0.17)
        arch(face, sx * 0.19, FZ + 0.33, 0.06, 0.15)
        on_face(face, sx * (PX - 0.025), (FZ + 0.05 + PZ1) / 2, 0.04, PZ1 - FZ - 0.07, 0.02, 0.01, SAND)  # pilasters
        on_face(face, sx * 0.105, (FZ + 0.05 + PZ1) / 2, 0.025, PZ1 - FZ - 0.07, 0.016, 0.008, SAND)
    arch(face, 0, FZ + 0.45, 0.1, 0.17)                               # window over the entrance
for sx in (-1, 1):
    for k in range(3):
        arch(('x', sx * PX, sx), PY0 + 0.1 + k * 0.08, FZ + 0.33, 0.045, 0.13)
# glow inside the entrance
on_face(('y', PY0, -1), 0, FZ + 0.15, 0.1, 0.12, 0.01, 0.004, WARM)
# portico corner turrets
for sx in (-1, 1):
    for yy in (PY0 + 0.04, PY1 - 0.04):
        cylinder((sx * (PX - 0.04), yy, PZ1 + 0.06), 0.036, 0.1, CREAM, verts=12)
        cylinder((sx * (PX - 0.04), yy, PZ1 + 0.115), 0.044, 0.014, TRIM, verts=12)
        sphere((sx * (PX - 0.04), yy, PZ1 + 0.122), (0.04, 0.04, 0.05), DOME, segs=14, rings=8)
        sphere((sx * (PX - 0.04), yy, PZ1 + 0.18), 0.01, GOLD, segs=8, rings=4)
balustrade(-PX + 0.09, PX - 0.09, PY0 + 0.02, PZ1 + 0.026, n=10)
balustrade(-PX + 0.09, PX - 0.09, PY1 - 0.02, PZ1 + 0.026, n=10)
# front steps
for i in range(3):
    d = 0.06 * (3 - i)
    box((0, PY0 - 0.02 - d / 2, FZ + 0.0175 * (i + 1) / 2), (0.46 - 0.03 * i, d, 0.0175 * (i + 1)),
        CREAM if i % 2 else SAND, bevel=0.003)

# ── clock tower ──────────────────────────────────────────────────────────
TY = (PY0 + PY1) / 2
TZ0 = PZ1 + 0.026
box((0, TY, TZ0 + 0.06), (0.34, 0.34, 0.12), SAND, bevel=0.008)                    # tower base stage
box((0, TY, TZ0 + 0.13), (0.37, 0.37, 0.02), TRIM, bevel=0.004)
SH0, SH1 = TZ0 + 0.14, TZ0 + 0.52
box((0, TY, (SH0 + SH1) / 2), (0.27, 0.27, SH1 - SH0), CREAM, bevel=0.006)         # shaft
for sx in (-1, 1):                                                                   # corner pilasters
    for sy in (-1, 1):
        box((sx * 0.13, TY + sy * 0.13, (SH0 + SH1) / 2), (0.035, 0.035, SH1 - SH0), SAND, bevel=0.004)
box((0, TY, SH1 + 0.015), (0.32, 0.32, 0.03), TRIM, bevel=0.005)                   # cornice
CZ = SH0 + 0.25
for face in (('y', TY - 0.135, -1), ('y', TY + 0.135, 1)):
    clock(face, 0, CZ)
    arch(face, 0, SH0 + 0.03, 0.05, 0.1)
for face in (('x', -0.135, -1), ('x', 0.135, 1)):
    clock(face, TY, CZ)
    arch(face, TY, SH0 + 0.03, 0.05, 0.1)
# belfry stage with arched openings
B0, B1 = SH1 + 0.03, SH1 + 0.17
box((0, TY, (B0 + B1) / 2), (0.21, 0.21, B1 - B0), CREAM, bevel=0.006)
for face in (('y', TY - 0.105, -1), ('y', TY + 0.105, 1)):
    for u in (-0.045, 0.045):
        arch(face, u, B0 + 0.02, 0.05, 0.1, frame=False)
for face in (('x', -0.105, -1), ('x', 0.105, 1)):
    for u in (TY - 0.045, TY + 0.045):
        arch(face, u, B0 + 0.02, 0.05, 0.1, frame=False)
box((0, TY, B1 + 0.012), (0.25, 0.25, 0.024), TRIM, bevel=0.005)
for sx in (-1, 1):                                                                   # mini corner finials
    for sy in (-1, 1):
        sphere((sx * 0.11, TY + sy * 0.11, B1 + 0.04), 0.018, DOME, segs=10, rings=6)
# drum + dome + finial
cylinder((0, TY, B1 + 0.05), 0.095, 0.05, CREAM, verts=16)
torus((0, TY, B1 + 0.075), 0.095, 0.008, TRIM, major_segs=24, minor_segs=4)
sphere((0, TY, B1 + 0.075), (0.1, 0.1, 0.13), DOME, segs=24, rings=12)
for k in range(8):                                                                   # dome ribs
    a = k * math.pi / 4
    pts = []
    for i in range(7):
        t = i / 6 * math.pi / 2
        pts.append((math.cos(a) * math.cos(t) * 0.102, TY + math.sin(a) * math.cos(t) * 0.102,
                    B1 + 0.075 + math.sin(t) * 0.132))
    kit.tube(pts, 0.005, TRIM, resolution=2, name='rib')
cylinder((0, TY, B1 + 0.215), 0.02, 0.02, GOLD, verts=12)
sphere((0, TY, B1 + 0.24), 0.02, GOLD, segs=12, rings=6)
kit.spike((0, TY, B1 + 0.25), (0, TY, B1 + 0.33), 0.01, GOLD, verts=10)

# lamp posts along the avenue
for sx in (-1, 1):
    for y in (-0.42, -0.78):
        x = sx * 0.32
        cylinder((x, y, FZ + 0.01), 0.018, 0.02, HAND, verts=10)
        rod((x, y, FZ), (x, y, FZ + 0.2), 0.006, HAND, verts=8, caps=False)
        sphere((x, y, FZ + 0.215), 0.02, mat('#fff3c4', 0.3, emit=2.0), segs=10, rings=6)

kit.finalize_prop('bits_campus', thumb_angle=-22, elevation=0.42)
