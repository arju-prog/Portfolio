"""Gomu Gomu no Mi (One Piece): lobed purple fruit covered in raised swirls, curly stem and a leaf."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()

SKIN = kit.mat('#5a1f86', 0.4)
SWIRL = kit.mat('#b884ec', 0.3)
STEM = kit.mat('#5c6b26', 0.6)
STEM_DK = kit.mat('#3f4a18', 0.6)
LEAF = kit.mat('#3c9a2c', 0.5)
LEAF_DK = kit.mat('#2f7a24', 0.5)

BASE = 0.45
ZS = 0.9   # vertical squash


def radius(theta, phi):
    r = BASE * (1 + 0.045 * math.cos(5 * phi) * math.sin(theta) ** 2)      # gentle lobes
    r *= 1 - 0.2 * math.exp(-(theta / 0.38) ** 2)                            # stem dimple
    r *= 1 - 0.07 * math.exp(-((math.pi - theta) / 0.45) ** 2)               # flattened bottom
    return r


def surf(d, lift=0.0):
    d = Vector(d).normalized()
    theta = math.acos(max(-1, min(1, d.z)))
    phi = math.atan2(d.y, d.x)
    p = d * (radius(theta, phi) + lift)
    p.z *= ZS
    return p


# ── body: custom UV sphere driven by radius() ────────────────────────────
NR, NS = 32, 56
bm = bmesh.new()
top = bm.verts.new(surf((0, 0, 1)))
bot = bm.verts.new(surf((0, 0, -1)))
rows = []
for i in range(1, NR):
    th = math.pi * i / NR
    rows.append([bm.verts.new(surf((math.sin(th) * math.cos(2 * math.pi * j / NS),
                                    math.sin(th) * math.sin(2 * math.pi * j / NS), math.cos(th))))
                 for j in range(NS)])
for j in range(NS):
    bm.faces.new((top, rows[0][j], rows[0][(j + 1) % NS]))
    bm.faces.new((bot, rows[-1][(j + 1) % NS], rows[-1][j]))
for a, b in zip(rows, rows[1:]):
    for j in range(NS):
        bm.faces.new((a[j], b[j], b[(j + 1) % NS], a[(j + 1) % NS]))
for f in bm.faces:
    f.smooth = True
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('fruit')
bm.to_mesh(me)
bm.free()
body = bpy.data.objects.new('fruit', me)
bpy.context.scene.collection.objects.link(body)
me.materials.append(SKIN)


def lowpoly_tube(points, radius_, m, res=2, bevel_res=2, taper_to=None, name='swirl'):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius_
    curve.bevel_resolution = bevel_res
    curve.resolution_u = res
    curve.use_fill_caps = True
    sp = curve.splines.new('BEZIER')
    sp.bezier_points.add(len(points) - 1)
    for i, p in enumerate(points):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
        if taper_to is not None:
            bp.radius = 1 + (taper_to - 1) * i / (len(points) - 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.active_object
    obj.data.materials.append(m)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


# ── raised swirls (Fibonacci-distributed, skipping the stem cap) ─────────
N = 30
golden = math.pi * (3 - math.sqrt(5))
centres = []
for k in range(N):
    z = 1 - 2 * (k + 0.5) / N
    rr = math.sqrt(1 - z * z)
    a = k * golden
    d = Vector((math.cos(a) * rr, math.sin(a) * rr, z))
    if d.z > 0.8:
        continue
    centres.append(d)

for idx, c in enumerate(centres):
    u = c.cross(Vector((0, 0, 1)))
    if u.length < 1e-3:
        u = Vector((1, 0, 0))
    u.normalize()
    v = c.cross(u).normalized()
    spin = 1 if idx % 2 == 0 else -1
    pts = []
    turns = 1.75
    n = 20
    rho_max = 0.33
    a0 = idx * 1.3
    for i in range(n):
        t = i / (n - 1)
        a = a0 + spin * t * turns * 2 * math.pi
        rho = 0.03 + rho_max * t
        d = c + (u * math.cos(a) + v * math.sin(a)) * rho
        pts.append(surf(d, 0.004))
    lowpoly_tube(pts, 0.014, SWIRL, res=2, bevel_res=1, taper_to=0.55)

# ── curly stem ───────────────────────────────────────────────────────────
top_z = surf((0, 0, 1)).z
stem = [Vector((0, 0, top_z - 0.02)), Vector((0.0, 0.0, top_z + 0.06)), Vector((0.03, -0.01, top_z + 0.13))]
# pig-tail curl at the end
cc = Vector((0.03, -0.01, top_z + 0.13)) + Vector((0.055, 0, 0.02))
for i in range(1, 15):
    t = i / 14
    a = math.pi - t * 1.7 * 2 * math.pi
    rr = 0.055 * (1 - 0.5 * t)
    stem.append(cc + Vector((math.cos(a) * rr, -0.012 * t * 3, math.sin(a) * rr)))
kit.tube(stem, 0.022, STEM, taper_to=0.45, resolution=4, name='stem')
kit.sphere((0, 0, top_z - 0.005), (0.045, 0.045, 0.02), STEM_DK, segs=16, rings=8)   # stem socket

# ── leaf ─────────────────────────────────────────────────────────────────
def leaf(base, direction, length, width, m, rib_m, lift=0.35, curl=0.12):
    """Lens-shaped leaf with an upward curl, slightly folded along the midrib."""
    dirv = Vector(direction).normalized()
    side = dirv.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(dirv).normalized()
    bm = bmesh.new()
    nl, nw = 14, 4
    grid = []
    for i in range(nl + 1):
        t = i / nl
        w = width * math.sin(math.pi * t) ** 0.8 * (1 - 0.25 * t)
        row = []
        for j in range(-nw, nw + 1):
            s = j / nw
            p = Vector(base) + dirv * (t * length) + side * (s * w)
            p += up * (lift * length * t * t * 0.5 + curl * length * t ** 3 + abs(s) * w * 0.25)
            row.append(bm.verts.new(p))
        grid.append(row)
    for i in range(nl):
        for j in range(2 * nw):
            q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
            if len(set(q)) == 4:
                bm.faces.new(q).smooth = True
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('leaf')
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new('leaf', me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m)
    mod = obj.modifiers.new('solid', 'SOLIDIFY')
    mod.thickness = 0.008
    mod.offset = 0
    # midrib + veins
    rib = [Vector(base) + dirv * (t * length) + up * (lift * length * t * t * 0.5 + curl * length * t ** 3 + 0.006)
           for t in (0.0, 0.25, 0.5, 0.75, 0.95)]
    kit.tube(rib, 0.006, rib_m, taper_to=0.3, resolution=4, name='rib')
    for t in (0.3, 0.5, 0.7):
        w = width * math.sin(math.pi * t) ** 0.8 * (1 - 0.25 * t) * 0.7
        for s in (-1, 1):
            p0 = Vector(base) + dirv * (t * length) + up * (lift * length * t * t * 0.5 + curl * length * t ** 3 + 0.006)
            p1 = Vector(base) + dirv * ((t + 0.12) * length) + side * (s * w) + \
                up * (lift * length * (t + 0.12) ** 2 * 0.5 + curl * length * (t + 0.12) ** 3 + abs(s) * w * 0.25 + 0.006)
            kit.tube([p0, p1], 0.0035, rib_m, resolution=2, name='vein')
    return obj


leaf((0.0, 0.0, top_z + 0.04), (-0.8, -0.35, 0.15), 0.42, 0.16, LEAF, LEAF_DK, lift=0.25, curl=0.05)

kit.finalize_prop('devil_fruit')
