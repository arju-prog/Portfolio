"""Scaler School of Technology (Bangalore) desk diorama: a contemporary glass-and-concrete tech-school
block — concrete frame with ribbon windows and vertical fins, a fully glazed side wing, entrance canopy
with steps, rooftop solar panels + HVAC units, trees, lamp posts and a waving flag, on a rounded base."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, mat, rod, sphere, torus  # noqa: E402

kit.reset()
random.seed(3)

CONC = mat('#cfcac0', 0.7)
CONC_D = mat('#b9b4aa', 0.72)
CONC_W = mat('#f4f2ee', 0.6)
GLASS = mat('#8cc8f2', 0.06, metal=0.35)
GLASS_D = mat('#5d9fd6', 0.08, metal=0.35)
FRAME = mat('#2d3440', 0.35, metal=0.6)
STEEL = mat('#aab3be', 0.3, metal=0.8)
BLUE = mat('#2f6bff', 0.45)
ORANGE = mat('#ff8a3d', 0.45)
GRASS = mat('#7ec46b', 0.75)
GRASS_D = mat('#5aa556', 0.75)
PAVE = mat('#c9c4ba', 0.75)
PAVE_D = mat('#b3ada2', 0.75)
PLINTH = mat('#3a3f48', 0.5)
TRUNK = mat('#7a5233', 0.8)
LEAF1 = mat('#4fae4f', 0.6)
LEAF2 = mat('#3c9447', 0.6)
LEAF3 = mat('#6cc35a', 0.6)
SOLAR = mat('#1f3c78', 0.15, metal=0.5)
LAMP = mat('#fff3c4', 0.3, emit=2.0)
WARM = mat('#ffe2a0', 0.3, emit=0.8)
WHITE = mat('#ffffff', 0.5)


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


def face_box(face, u, z, du, dz, dn, off, m, bevel=0.0):
    """Box on a building face. face = (axis 'x'|'y', plane coord, outward sign). u = position along the face,
    du/dz = width/height, dn = thickness, off = how far its centre sits outside the plane."""
    axis, c, s = face
    if axis == 'y':
        return box((u, c + s * off, z), (du, dn, dz), m, bevel=bevel)
    return box((c + s * off, u, z), (dn, du, dz), m, bevel=bevel)


def ribbon_facade(face, u0, u1, floors, glass_h, bay, fins=False):
    """Horizontal ribbon windows per floor with mullions; optional vertical concrete fins."""
    w = u1 - u0
    for z in floors:
        face_box(face, (u0 + u1) / 2, z, w - 0.06, glass_h, 0.02, 0.0, GLASS)
        face_box(face, (u0 + u1) / 2, z - glass_h / 2 - 0.006, w - 0.05, 0.014, 0.03, 0.006, CONC_W)  # sill
        n = max(1, round((w - 0.06) / bay))
        for k in range(1, n):
            u = u0 + 0.03 + k * (w - 0.06) / n
            face_box(face, u, z, 0.012, glass_h, 0.02, 0.006, FRAME)
    if fins:
        n = max(2, round(w / (bay * 1.0)))
        z_lo, z_hi = min(floors) - glass_h / 2 - 0.02, max(floors) + glass_h / 2 + 0.02
        for k in range(n + 1):
            u = u0 + 0.02 + k * (w - 0.04) / n
            face_box(face, u, (z_lo + z_hi) / 2, 0.022, z_hi - z_lo, 0.05, 0.025, CONC_W, bevel=0.004)


def tree(x, y, z, s=1.0, tall=False):
    h = (0.32 if tall else 0.22) * s
    kit.cone((x, y, z + h / 2), 0.03 * s, 0.018 * s, h, TRUNK, verts=10)
    blobs = [(0, 0, h + 0.1 * s, 0.13), (0.07, 0.03, h + 0.05 * s, 0.1), (-0.07, -0.02, h + 0.06 * s, 0.1),
             (0.01, -0.06, h + 0.04 * s, 0.09), (-0.02, 0.06, h + 0.16 * s, 0.09)]
    for i, (dx, dy, dz, r) in enumerate(blobs):
        sphere((x + dx * s, y + dy * s, z + dz), r * s, [LEAF1, LEAF2, LEAF3][i % 3], segs=14, rings=8)


def bush(x, y, z, r=0.05):
    sphere((x, y, z + r * 0.6), (r * 1.2, r, r * 0.85), random.choice([LEAF1, LEAF2]), segs=12, rings=6)


def lamp(x, y, z, h=0.26):
    cylinder((x, y, z + 0.008), 0.02, 0.016, FRAME, verts=10)
    rod((x, y, z), (x, y, z + h), 0.007, FRAME, verts=8, caps=False)
    sphere((x, y, z + h + 0.012), 0.022, LAMP, segs=12, rings=6)
    cylinder((x, y, z + h + 0.036), 0.026, 0.008, FRAME, verts=12)


def flag(x, y, z, h=0.78, fw=0.28, fh=0.17):
    cylinder((x, y, z + 0.015), 0.035, 0.03, CONC_D, verts=14)
    rod((x, y, z), (x, y, z + h), 0.008, STEEL, verts=10, caps=False)
    sphere((x, y, z + h + 0.01), 0.014, mat('#e8c25a', 0.3, metal=0.9), segs=10, rings=5)
    # wavy cloth: two colour bands
    for (z0, z1, m) in ((0.0, 0.62, BLUE), (0.62, 1.0, ORANGE)):
        bm = bmesh.new()
        nu = 10
        rows = []
        for i in range(nu + 1):
            t = i / nu
            px = x + 0.01 + t * fw
            py = y + 0.018 * math.sin(t * math.pi * 1.6) * t
            rows.append([bm.verts.new((px, py + dy, z + h - fh + fh * (zz if zz < 1 else 1)))
                         for zz, dy in ((z0, -0.004), (z1, -0.004), (z1, 0.004), (z0, 0.004))])
        for i in range(nu):
            a, b = rows[i], rows[i + 1]
            for j in range(4):
                bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
        bm.faces.new(rows[0])
        bm.faces.new(list(reversed(rows[-1])))
        o = _mesh_obj(bm, m, 'flag', smooth=True)
        o.location = (0, 0, 0)


# ── base plate + landscape ───────────────────────────────────────────────
W = 2.0
rounded_slab(W, W, 0.24, 0.0, 0.16, PLINTH, bevel=0.03, name='plinth')
rounded_slab(W + 0.03, W + 0.03, 0.255, 0.05, 0.075, BLUE, bevel=0.008, name='trim')
rounded_slab(W - 0.07, W - 0.07, 0.2, 0.16, 0.2, GRASS, bevel=0.012, name='lawn')
FZ = 0.2
# plaza paving in front of the entrance + path to the front edge
rounded_slab(1.1, 0.42, 0.06, FZ, FZ + 0.014, PAVE, cx=-0.15, cy=-0.42, name='plaza')
rounded_slab(0.3, 0.5, 0.04, FZ, FZ + 0.012, PAVE, cx=-0.25, cy=-0.72, name='path')
# paving around the building
rounded_slab(1.86, 1.06, 0.06, FZ, FZ + 0.01, PAVE_D, cx=-0.02, cy=0.32, name='apron')

# ── main concrete block ──────────────────────────────────────────────────
MX0, MX1, MY0, MY1 = -0.82, 0.32, -0.06, 0.74
MH = 0.98
box(((MX0 + MX1) / 2, (MY0 + MY1) / 2, FZ + MH / 2), (MX1 - MX0, MY1 - MY0, MH), CONC, bevel=0.012)
floors = [FZ + 0.4, FZ + 0.6, FZ + 0.8]
GH = 0.12
ribbon_facade(('y', MY0, -1), MX0, MX1, floors, GH, 0.12, fins=True)            # front
ribbon_facade(('y', MY1, 1), MX0, MX1, floors, GH, 0.14)                         # back
ribbon_facade(('x', MX0, -1), MY0, MY1, floors, GH, 0.14, fins=True)            # left side
# ground floor: recessed glass lobby along the front with concrete columns
box(((MX0 + MX1) / 2, MY0 - 0.004, FZ + 0.14), (MX1 - MX0 - 0.08, 0.02, 0.22), GLASS_D)
for k in range(7):
    x = MX0 + 0.06 + k * (MX1 - MX0 - 0.12) / 6
    box((x, MY0 - 0.02, FZ + 0.14), (0.04, 0.04, 0.26), CONC_W, bevel=0.006)
box(((MX0 + MX1) / 2, MY0 - 0.02, FZ + 0.285), (MX1 - MX0 + 0.02, 0.06, 0.04), CONC_W, bevel=0.008)  # floor band
# warm lights inside the lobby
for k in range(3):
    box((MX0 + 0.2 + k * 0.36, MY0 + 0.01, FZ + 0.23), (0.12, 0.01, 0.015), WARM)
# rooftop: parapet, HVAC, solar panels
RZ = FZ + MH
for (cx, cy, sx, sy) in (((MX0 + MX1) / 2, MY0 + 0.02, MX1 - MX0, 0.04), ((MX0 + MX1) / 2, MY1 - 0.02, MX1 - MX0, 0.04),
                         (MX0 + 0.02, (MY0 + MY1) / 2, 0.04, MY1 - MY0), (MX1 - 0.02, (MY0 + MY1) / 2, 0.04, MY1 - MY0)):
    box((cx, cy, RZ + 0.03), (sx, sy, 0.06), CONC_W, bevel=0.008)
    box((cx, cy, RZ + 0.064), (sx + 0.004, sy + 0.004, 0.012), BLUE, bevel=0.004)
box((0.0, 0.5, RZ + 0.06), (0.2, 0.16, 0.12), CONC_D, bevel=0.012)            # HVAC unit
for dx in (-0.045, 0.045):
    cylinder((dx, 0.5, RZ + 0.122), 0.035, 0.008, FRAME, verts=16)
    rod((dx - 0.03, 0.5, RZ + 0.128), (dx + 0.03, 0.5, RZ + 0.128), 0.004, STEEL, verts=6, caps=False)
box((0.18, 0.2, RZ + 0.05), (0.1, 0.1, 0.1), CONC_D, bevel=0.01)
for i in range(3):
    for j in range(2):
        x, y = -0.66 + i * 0.2, 0.1 + j * 0.24
        box((x, y, RZ + 0.07), (0.17, 0.18, 0.012), SOLAR, rot=(math.radians(25), 0, 0), bevel=0.003)
        rod((x, y + 0.05, RZ), (x, y + 0.05, RZ + 0.08), 0.006, STEEL, verts=6, caps=False)
# rooftop roof-access + antenna
box((-0.05, 0.22, RZ + 0.08), (0.14, 0.14, 0.16), CONC_W, bevel=0.01)
rod((-0.05, 0.22, RZ + 0.16), (-0.05, 0.22, RZ + 0.3), 0.006, STEEL, verts=6)
sphere((-0.05, 0.22, RZ + 0.305), 0.012, mat('#ff4d4d', 0.3, emit=2.0), segs=8, rings=4)

# vertical banner on the left front corner of the block
box((MX0 + 0.08, MY0 - 0.06, FZ + 0.66), (0.09, 0.012, 0.42), BLUE, bevel=0.004)
box((MX0 + 0.08, MY0 - 0.067, FZ + 0.8), (0.06, 0.004, 0.06), WHITE)
box((MX0 + 0.08, MY0 - 0.067, FZ + 0.5), (0.09, 0.004, 0.025), ORANGE)
for z in (FZ + 0.87, FZ + 0.45):
    rod((MX0 + 0.08, MY0 - 0.004, z), (MX0 + 0.08, MY0 - 0.06, z), 0.005, STEEL, verts=6, caps=False)

# ── glazed wing (right) ──────────────────────────────────────────────────
GX0, GX1, GY0, GY1 = 0.32, 0.86, -0.28, 0.6
GHT = 0.7
box(((GX0 + GX1) / 2, (GY0 + GY1) / 2, FZ + GHT / 2), (GX1 - GX0 - 0.03, GY1 - GY0 - 0.03, GHT - 0.02), GLASS)
# floor slabs (white bands) and roof slab
for z in (FZ + 0.012, FZ + 0.25, FZ + 0.48):
    box(((GX0 + GX1) / 2, (GY0 + GY1) / 2, z), (GX1 - GX0, GY1 - GY0, 0.024), CONC_W, bevel=0.006)
box(((GX0 + GX1) / 2 + 0.01, (GY0 + GY1) / 2 - 0.01, FZ + GHT), (GX1 - GX0 + 0.06, GY1 - GY0 + 0.06, 0.04),
    CONC_W, bevel=0.01)
# mullions on the three exposed faces
for k in range(6):
    x = GX0 + 0.04 + k * (GX1 - GX0 - 0.08) / 5
    box((x, GY0 + 0.003, FZ + GHT / 2), (0.012, 0.012, GHT - 0.04), FRAME)
    box((x, GY1 - 0.003, FZ + GHT / 2), (0.012, 0.012, GHT - 0.04), FRAME)
for k in range(8):
    y = GY0 + 0.04 + k * (GY1 - GY0 - 0.08) / 7
    box((GX1 - 0.003, y, FZ + GHT / 2), (0.012, 0.012, GHT - 0.04), FRAME)
# interior hints: warm ceiling strips + a few chairs/desks silhouettes
for z in (FZ + 0.23, FZ + 0.46):
    for k in range(3):
        box((GX0 + 0.14 + k * 0.14, (GY0 + GY1) / 2, z), (0.06, GY1 - GY0 - 0.12, 0.008), WARM)
for k in range(3):
    box((GX0 + 0.14 + k * 0.14, GY0 + 0.12, FZ + 0.08), (0.08, 0.05, 0.012), CONC_D)
    box((GX0 + 0.14 + k * 0.14, GY0 + 0.12, FZ + 0.31), (0.08, 0.05, 0.012), CONC_D)
# rooftop terrace rail + planter on the wing
for k in range(7):
    x = GX0 + 0.03 + k * (GX1 - GX0 - 0.06) / 6
    rod((x, GY0 - 0.01, FZ + GHT + 0.02), (x, GY0 - 0.01, FZ + GHT + 0.1), 0.004, STEEL, verts=6, caps=False)
rod((GX0 + 0.03, GY0 - 0.01, FZ + GHT + 0.1), (GX1 - 0.03, GY0 - 0.01, FZ + GHT + 0.1), 0.006, STEEL, verts=8)
box((GX1 - 0.12, (GY0 + GY1) / 2 + 0.1, FZ + GHT + 0.05), (0.12, 0.5, 0.06), CONC_D, bevel=0.008)
for k in range(4):
    bush(GX1 - 0.12, (GY0 + GY1) / 2 - 0.08 + k * 0.12, FZ + GHT + 0.07, 0.045)
tree(GX0 + 0.16, GY1 - 0.18, FZ + GHT + 0.02, s=0.6)

# ── entrance: canopy + steps + doors ─────────────────────────────────────
EX = -0.25
box((EX, MY0 - 0.16, FZ + 0.3), (0.5, 0.34, 0.03), CONC_W, bevel=0.01)          # cantilever canopy
box((EX, MY0 - 0.33, FZ + 0.3), (0.5, 0.008, 0.035), BLUE)                       # canopy fascia stripe
for sx in (-1, 1):
    rod((EX + sx * 0.22, MY0 - 0.3, FZ + 0.042), (EX + sx * 0.22, MY0 - 0.3, FZ + 0.285), 0.01, STEEL, verts=8,
        caps=False)
for i in range(3):                                                                # steps
    box((EX, MY0 - 0.22 - i * 0.05 + 0.05, FZ + 0.014 + 0.014 * (2 - i)), (0.42, 0.26 - i * 0.0, 0.028),
        CONC_W, bevel=0.004)
box((EX, MY0 - 0.012, FZ + 0.15), (0.24, 0.02, 0.2), FRAME, bevel=0.004)         # door frame
for sx in (-1, 1):
    box((EX + sx * 0.055, MY0 - 0.024, FZ + 0.148), (0.1, 0.008, 0.18), GLASS_D)
    rod((EX + sx * 0.012, MY0 - 0.034, FZ + 0.12), (EX + sx * 0.012, MY0 - 0.034, FZ + 0.18), 0.004, STEEL,
        verts=6)

# ── landscape: trees, bushes, lamps, flag, bench ─────────────────────────
tree(-0.76, -0.5, FZ, s=1.15, tall=True)
tree(0.72, -0.68, FZ, s=1.0)
tree(0.78, 0.82, FZ, s=0.95)
tree(-0.78, 0.84, FZ, s=0.85)
for k in range(6):
    bush(MX0 - 0.06, MY0 + 0.06 + k * 0.13, FZ, 0.045)
# round planter with a young tree on the plaza
cylinder((0.24, -0.5, FZ + 0.04), 0.1, 0.08, CONC_W, verts=24)
cylinder((0.24, -0.5, FZ + 0.081), 0.088, 0.004, mat('#6b4a2e', 0.9), verts=24)
tree(0.24, -0.5, FZ + 0.08, s=0.55)
for a in range(4):
    bush(0.24 + 0.06 * math.cos(a * 1.57 + 0.6), -0.5 + 0.06 * math.sin(a * 1.57 + 0.6), FZ + 0.075, 0.03)
lamp(-0.48, -0.86, FZ)
lamp(0.04, -0.86, FZ)
lamp(0.5, -0.4, FZ)
flag(-0.62, -0.8, FZ)
# bench
box((0.4, -0.84, FZ + 0.06), (0.24, 0.07, 0.016), mat('#c58b4f', 0.6), bevel=0.004)
box((0.4, -0.81, FZ + 0.1), (0.24, 0.012, 0.05), mat('#c58b4f', 0.6), bevel=0.004)
for sx in (-1, 1):
    box((0.4 + sx * 0.1, -0.84, FZ + 0.03), (0.014, 0.06, 0.06), FRAME)

kit.finalize_prop('scaler_campus', thumb_angle=-26, elevation=0.5)
