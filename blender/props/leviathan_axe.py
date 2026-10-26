"""Kratos' Leviathan Axe — steel bearded head facing left with a frost-blue glowing edge and runes,
leather-wrapped haft, steel collars and a knotted pommel."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, cone, mat, sphere, torus, tube  # noqa: E402

kit.reset()

STEEL = mat('#c3cad2', 0.3, metal=0.9)
BLADE = mat('#8d9cad', 0.3, metal=0.92)
STEEL_D = mat('#646c76', 0.38, metal=0.9)
DARK = mat('#2d3238', 0.5, metal=0.8)
FROST = mat('#36b6ff', 0.2, emit=3.0)
FROST_SOFT = mat('#7fd4ff', 0.25, emit=1.5)
LEATHER = mat('#5b3820', 0.8)
LEATHER_D = mat('#3a2213', 0.85)
WOOD = mat('#3b2618', 0.7)


def bez(p0, c, p1, n):
    """Quadratic Bezier samples (excluding the end point)."""
    out = []
    for i in range(n):
        t = i / n
        out.append(tuple((1 - t) ** 2 * p0[k] + 2 * (1 - t) * t * c[k] + t * t * p1[k] for k in range(2)))
    return out


def slab(outline, half_t, m, y=0.0, thick_fn=None, bevel=0.003, name='slab', cuts=0):
    """Extrude a 2D outline in the XZ plane (front = -Y) into a solid. `thick_fn(x, z)` -> half-thickness."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0, z)) for x, z in outline]
    edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    if cuts:  # interior vertices so a varying thickness can follow thick_fn
        inner = [e for e in bm.edges if not e.is_boundary]
        bmesh.ops.subdivide_edges(bm, edges=inner, cuts=cuts, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
    front = bm.faces[:]
    ext = bmesh.ops.extrude_face_region(bm, geom=front)
    new_verts = [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]
    for v in bm.verts:
        h = thick_fn(v.co.x, v.co.z) if thick_fn else half_t
        v.co.y = y + (h if v in new_verts else -h)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(m)
    for p in obj.data.polygons:
        p.use_smooth = False
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(35)
    return obj


def seg_dist(p, a, b):
    p, a, b = Vector(p), Vector(a), Vector(b)
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


# ── head outline (XZ), haft on x = 0, cutting edge to the left (-X) ──
TOP_HORN = (-0.31, 0.73)
BEARD = (-0.25, 0.07)
edge = bez(TOP_HORN, (-0.5, 0.38), BEARD, 24) + [BEARD]
top = bez((0.07, 0.58), (-0.1, 0.56), TOP_HORN, 10)
beard_inner = bez(BEARD, (-0.2, 0.3), (-0.06, 0.37), 10)
back = [(-0.06, 0.36), (0.06, 0.36), (0.1, 0.4), (0.2, 0.445), (0.23, 0.47), (0.2, 0.5), (0.1, 0.54)]
outline = top + edge + beard_inner + back


def head_thickness(x, z):
    d = min(seg_dist((x, z), edge[i], edge[i + 1]) for i in range(len(edge) - 1))
    d = min(d, 0.25)
    return 0.004 + 0.034 * min(d / 0.13, 1.0) ** 0.8


slab(outline, 0, BLADE, thick_fn=head_thickness, bevel=0.002, name='axe_head', cuts=3)

# frost glow: an emissive bead on the cutting edge + a glowing band along both edge bevels
edge3 = [(x + 0.003, 0, z) for x, z in edge]
tube(edge3, 0.007, FROST, smooth_path=False, name='edge_glow')


def offset_edge(dist):
    out = []
    for i, (x, z) in enumerate(edge):
        px, pz = edge[max(i - 1, 0)]
        nx, nz = edge[min(i + 1, len(edge) - 1)]
        tx, tz = nx - px, nz - pz
        ln = math.hypot(tx, tz)
        ox, oz = tz / ln, -tx / ln        # normal pointing into the blade
        if ox < 0:
            ox, oz = -ox, -oz
        out.append((x + ox * dist, z + oz * dist))
    return out


band = offset_edge(0.004)[2:-2] + offset_edge(0.032)[2:-2][::-1]
slab(band, 0, FROST_SOFT, thick_fn=lambda x, z: head_thickness(x, z) + 0.0022, bevel=0, name='edge_band')

# ── socket (eye) around the haft, with knot plates ──
box((0.0, 0, 0.46), (0.13, 0.095, 0.26), STEEL_D, bevel=0.012)
for z in (0.345, 0.575):
    box((0.0, 0, z), (0.15, 0.105, 0.03), DARK, bevel=0.008)
# raised dark knot-plate around the emblem (both faces)
plate = [(-0.04, 0.555), (-0.14, 0.575), (-0.235, 0.53), (-0.25, 0.42), (-0.22, 0.31), (-0.15, 0.3), (-0.05, 0.37)]
slab(plate, 0, STEEL_D, thick_fn=lambda x, z: head_thickness(x, z) + 0.004, bevel=0.003, name='plate')
# raised emblem ring on the blade face with a glowing rune inside
EMB = (-0.155, 0.43)
for s in (-1, 1):
    yf = s * (head_thickness(*EMB) + 0.006)
    torus((EMB[0], yf, EMB[1]), 0.065, 0.009, STEEL_D, rot=(math.pi / 2, 0, 0), major_segs=40, minor_segs=8)
    torus((EMB[0], yf, EMB[1]), 0.045, 0.004, STEEL_D, rot=(math.pi / 2, 0, 0), major_segs=32, minor_segs=6)
    # rune: vertical stave with two branches (ᛉ-like) + crossing knot strokes
    for (u0, v0, u1, v1) in ((0, -0.035, 0, 0.035), (0, 0.0, -0.025, 0.03), (0, 0.0, 0.025, 0.03),
                             (-0.02, -0.03, 0.02, -0.01)):
        a = (EMB[0] + u0, yf + s * 0.003, EMB[1] + v0)
        b = (EMB[0] + u1, yf + s * 0.003, EMB[1] + v1)
        tube([a, b], 0.0045, FROST, smooth_path=False, name='rune')
# small frost runes running up the blade toward the horn (front face)
for i, (u, v) in enumerate(((-0.27, 0.64), (-0.31, 0.56), (-0.32, 0.3), (-0.29, 0.22))):
    yf = -head_thickness(u, v) - 0.002
    h = 0.022
    tube([(u, yf, v - h), (u, yf, v + h)], 0.0035, FROST, smooth_path=False, name='rune')
    tube([(u, yf, v + (h if i % 2 else 0)), (u + 0.016, yf, v + (0 if i % 2 else h))], 0.0035, FROST,
         smooth_path=False, name='rune')
# back spike rivets
for s in (-1, 1):
    sphere((0.0, s * 0.05, 0.46), 0.016, STEEL, segs=12, rings=6)
    sphere((0.13, s * head_thickness(0.13, 0.46), 0.46), 0.012, STEEL_D, segs=10, rings=6)

# ── haft ──
Z_BOT, Z_TOP = -0.46, 0.62
cylinder((0, 0, (Z_BOT + Z_TOP) / 2), 0.03, Z_TOP - Z_BOT, WOOD, verts=24)
sphere((0, 0, Z_TOP), (0.03, 0.03, 0.012), WOOD, segs=24, rings=8)
# leather wrap: a spiral strap over a leather sleeve
W0, W1 = -0.35, 0.22
cylinder((0, 0, (W0 + W1) / 2), 0.032, W1 - W0, LEATHER_D, verts=24)
turns = 14
pts = []
for i in range(turns * 14 + 1):
    t = i / (turns * 14)
    a = t * turns * math.tau
    pts.append((math.cos(a) * 0.033, math.sin(a) * 0.033, W0 + (W1 - W0) * t))
tube(pts, 0.009, LEATHER, smooth_path=False, name='wrap')
# steel collars
for z, r in ((W0 - 0.01, 0.042), (W1 + 0.01, 0.04), (-0.06, 0.041)):
    cylinder((0, 0, z), r, 0.03, STEEL_D, verts=24)
    torus((0, 0, z + 0.015), r, 0.005, STEEL, major_segs=24, minor_segs=6)
    torus((0, 0, z - 0.015), r, 0.005, STEEL, major_segs=24, minor_segs=6)
# pommel: knot cap with a flared steel end
cylinder((0, 0, -0.4), 0.036, 0.06, STEEL_D, verts=24)
cone((0, 0, -0.445), 0.05, 0.034, 0.03, STEEL, verts=24)
sphere((0, 0, -0.48), (0.05, 0.05, 0.03), STEEL, segs=24, rings=10)
torus((0, 0, -0.46), 0.05, 0.007, DARK, major_segs=24, minor_segs=6)
sphere((0, 0, -0.51), 0.016, FROST, segs=12, rings=6)

kit.finalize_prop('leviathan_axe')
