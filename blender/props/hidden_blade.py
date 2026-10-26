"""Ezio's Hidden Blade — leather bracer with steel bands, buckled straps, an insignia plate,
and the steel blade extended upward out of its housing."""
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cone, cylinder, mat, sphere, torus, tube  # noqa: E402

kit.reset()

LEATHER = mat('#6e4326', 0.78)
LEATHER_D = mat('#3e2414', 0.82)
STITCH = mat('#d8c39a', 0.7)
STEEL = mat('#cfd5dc', 0.22, metal=0.95)
STEEL_D = mat('#6b737d', 0.38, metal=0.9)
BLADE = mat('#dfe5ec', 0.15, metal=1.0)
BRASS = mat('#c89b46', 0.3, metal=0.9)
RED = mat('#9e1b1b', 0.35, metal=0.1)
VOID = mat('#140c08', 0.9)

Z0, Z1 = -0.5, 0.0          # bracer bottom (elbow) / top (wrist)
R0, R1 = 0.135, 0.095       # radii at the elbow / wrist
SY = 0.85                   # oval cross-section


def rad(z):
    return R0 + (R1 - R0) * (z - Z0) / (Z1 - Z0)


def surf(z, phi, out=0.0):
    """Point on the bracer surface at height z, angle phi (0 = front -Y, + towards +X)."""
    r = rad(z) + out
    return (r * math.sin(phi), -SY * r * math.cos(phi), z)


def slab(outline, m, thick_fn, y=0.0, bevel=0.002, cuts=0, name='slab'):
    """Extrude a 2D outline in the XZ plane (front = -Y) with per-vertex half-thickness thick_fn(x, z)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0, z)) for x, z in outline]
    edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    if cuts:
        inner = [e for e in bm.edges if not e.is_boundary]
        bmesh.ops.subdivide_edges(bm, edges=inner, cuts=cuts, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    new_verts = {e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)}
    for v in bm.verts:
        h = thick_fn(v.co.x, v.co.z)
        v.co.y = y + (h if v in new_verts else -h)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(m)
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    return obj


# ── bracer body ──
cone(((0, 0, (Z0 + Z1) / 2)), R0, R1, Z1 - Z0, LEATHER, verts=48)
bpy.context.active_object.scale = (1, SY, 1)
cylinder((0, 0, Z1 + 0.002), R1 - 0.012, 0.004, VOID, verts=40, scale=(1, SY, 1))   # hollow opening
# rolled steel rims at both ends
for z in (Z0 + 0.012, Z1 - 0.012):
    torus((0, 0, z), rad(z) + 0.004, 0.012, STEEL, major_segs=48, minor_segs=8, scale=(1, SY, 1))
# stitched seams next to the rims
for z in (Z0 + 0.045, Z1 - 0.045):
    for i in range(30):
        phi = i / 30 * math.tau
        p = surf(z, phi, 0.001)
        box(p, (0.012, 0.004, 0.004), STITCH, rot=(0, 0, phi))

# ── buckled straps ──
for z in (-0.44, -0.07):
    torus((0, 0, z), rad(z) + 0.004, 0.008, LEATHER_D, major_segs=48, minor_segs=6, scale=(1, SY, 2.6))
    phi = math.radians(62)
    p = surf(z, phi, 0.014)
    box(p, (0.006, 0.05, 0.05), STEEL, rot=(0, 0, phi), bevel=0.003)          # buckle frame
    box(surf(z, phi, 0.01), (0.03, 0.006, 0.04), VOID, rot=(0, 0, phi))      # buckle opening
    box(surf(z, phi + 0.22, 0.012), (0.03, 0.006, 0.024), LEATHER_D, rot=(0, 0, phi + 0.22), bevel=0.004)
    sphere(surf(z, phi - 0.12, 0.016), 0.006, STEEL, segs=8, rings=4)        # prong

# ── insignia plate on the front ──
PZ = -0.26
plate_y = surf(PZ, 0)[1]
sphere((0, plate_y + 0.016, PZ), (0.1, 0.034, 0.165), STEEL_D, segs=32, rings=16)   # curved steel plate
torus((0, plate_y - 0.012, PZ), 0.088, 0.008, STEEL, rot=(math.pi / 2, 0, 0), major_segs=48, minor_segs=6,
      scale=(1, 1.7, 1))
for zz in (PZ - 0.13, PZ + 0.13):
    sphere((0, plate_y - 0.012, zz), 0.01, BRASS, segs=10, rings=6)
# red enamel field
sphere((0, plate_y - 0.012, PZ), (0.076, 0.012, 0.135), RED, segs=32, rings=12)
# Assassin insignia: two curved blades meeting at the apex, flaring and hooking in at the base,
# plus the central drop
IY = plate_y - 0.024
for s in (1, -1):
    pts = [(0, IY, PZ + 0.1), (0.03 * s, IY, PZ + 0.045), (0.053 * s, IY, PZ - 0.025),
           (0.055 * s, IY, PZ - 0.075), (0.03 * s, IY, PZ - 0.1)]
    tube(pts, 0.014, STEEL, taper_to=0.35, resolution=8, name='insignia')
tube([(0, IY, PZ + 0.0), (0, IY, PZ - 0.04), (0, IY, PZ - 0.08)], 0.02, STEEL, taper_to=0.1,
     resolution=6, name='insignia_c')

# ── side lacing (criss-cross cord through brass eyelets) ──
for side in (1, -1):
    pc = math.radians(100) * side
    cord = []
    zs = [-0.38 + i * 0.045 for i in range(7)]
    for i, z in enumerate(zs):
        for j, dphi in enumerate((-0.16, 0.16) if i % 2 == 0 else (0.16, -0.16)):
            p = surf(z + j * 0.02, pc + dphi * side, 0.006)
            cord.append(p)
            sphere(surf(z + j * 0.02, pc + dphi * side, 0.002), 0.008, BRASS, segs=8, rings=4)
    tube(cord, 0.0045, LEATHER_D, smooth_path=False, name='lace')

# ── blade housing (mechanism) on top of the wrist ──
HY = surf(-0.04, 0)[1] - 0.02
box((0, HY, -0.04), (0.065, 0.045, 0.1), STEEL_D, bevel=0.008)
for sx in (1, -1):
    box((0.034 * sx, HY - 0.004, -0.04), (0.008, 0.04, 0.095), STEEL, bevel=0.003)     # rails
    sphere((0.034 * sx, HY - 0.026, -0.07), 0.007, BRASS, segs=8, rings=4)
box((0, HY, 0.012), (0.07, 0.05, 0.016), STEEL, bevel=0.004)                         # mouth collar

# ── the blade ──
BZ0, BZ1, W = 0.0, 0.56, 0.026


def blade_t(x, z):
    # diamond section: central ridge, sharp edges, thinning into the point
    tip = min(1.0, max(0.0, (BZ1 - z) / 0.14))
    return 0.0015 + (0.0005 + 0.007 * tip) * max(0.0, 1 - abs(x) / W)


for s in (1, -1):   # two halves so the central ridge is a real crease
    half = [(0.0, BZ0), (W * s, BZ0), (W * s, BZ1 - 0.13), (W * 0.6 * s, BZ1 - 0.06), (0.0, BZ1)]
    slab(half, BLADE, blade_t, y=HY, bevel=0.0, cuts=0, name='blade')
# fuller groove line + glint
box((0, HY - 0.0095, 0.22), (0.005, 0.002, 0.28), STEEL_D)

kit.finalize_prop('hidden_blade')
