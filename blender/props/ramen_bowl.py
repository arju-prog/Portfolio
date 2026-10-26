"""Ichiraku ramen (Naruto): red/black raimon-patterned bowl with noodles, narutomaki, egg halves,
chashu, nori, green onion and chopsticks resting on top."""
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
random.seed(5)

RED = kit.mat('#c8221a', 0.25)
BLACK = kit.mat('#1b1414', 0.3)
INSIDE = kit.mat('#2a1210', 0.35)
BROTH = kit.mat('#d98a3a', 0.15)
OIL = kit.mat('#f0b866', 0.1)
NOODLE = kit.mat('#f5dc8c', 0.5)
WHITE = kit.mat('#fbf7f0', 0.45)
PINK = kit.mat('#ef5f93', 0.45)
YOLK = kit.mat('#f59a1c', 0.3)
CHASHU = kit.mat('#a85a32', 0.55)
CHASHU_DK = kit.mat('#5e2c14', 0.6)
CHASHU_FAT = kit.mat('#f0c8a8', 0.5)
NORI = kit.mat('#1f2e1e', 0.6)
ONION = kit.mat('#5cbf3a', 0.45)
WOOD = kit.mat('#dcae74', 0.55)
WOOD_TIP = kit.mat('#8f5a2c', 0.55)


def lathe_z(profile, mats, mat_idx, segs=64, name='lathe'):
    """Revolve a closed (radius, z) profile around the Z axis."""
    bm = bmesh.new()
    n = len(profile)
    rows = []
    for i in range(segs):
        a = i * 2 * math.pi / segs
        rows.append([bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)) for r, z in profile])
    for i in range(segs):
        r0, r1 = rows[i], rows[(i + 1) % segs]
        for j in range(n):
            f = bm.faces.new((r0[j], r1[j], r1[(j + 1) % n], r0[(j + 1) % n]))
            f.material_index = mat_idx[j]
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    return obj


# ── bowl ─────────────────────────────────────────────────────────────────
outer = [(0.21, 0.0), (0.25, 0.0), (0.255, 0.05), (0.245, 0.062),                      # foot
         (0.29, 0.075), (0.36, 0.11), (0.42, 0.16), (0.462, 0.22), (0.484, 0.27),       # red body
         (0.497, 0.33), (0.5, 0.37), (0.502, 0.385), (0.495, 0.398), (0.48, 0.398)]     # band + rim
inner = [(0.468, 0.375), (0.455, 0.31), (0.42, 0.23), (0.36, 0.16), (0.27, 0.115), (0.15, 0.095), (0.002, 0.09)]
under = [(0.002, 0.05), (0.21, 0.042)]
profile = outer + inner + under
mi = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1] + [2] * 7 + [1, 1]
lathe_z(profile, [RED, BLACK, INSIDE], mi, segs=72, name='bowl')
kit.torus((0, 0, 0.27), 0.485, 0.006, kit.mat('#e8c25a', 0.3, metal=0.8), major_segs=72, minor_segs=6)   # gold pinstripe


def r_outer(z):
    pts = [(0.484, 0.27), (0.497, 0.33), (0.5, 0.37)]
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return 0.5


# raimon (square-spiral) band in red on the black upper band
UNIT = [(0, 0), (1, 0), (1, 1), (0.2, 1), (0.2, 0.32), (0.66, 0.32), (0.66, 0.66)]
n_units = 18
for k in range(n_units):
    phi0 = k * 2 * math.pi / n_units
    pts = []
    for u, v in UNIT:
        z = 0.292 + v * 0.07
        r = r_outer(z) + 0.004
        phi = phi0 + u * 0.24
        pts.append((math.cos(phi) * r, math.sin(phi) * r, z))
    kit.tube(pts, 0.0065, BLACK, smooth_path=False, resolution=1, name='raimon')

# ── broth + toppings ─────────────────────────────────────────────────────
BZ = 0.33
kit.cylinder((0, 0, BZ - 0.01), 0.462, 0.02, BROTH, verts=64)
for (x, y, r) in ((0.05, -0.05, 0.03), (-0.12, -0.1, 0.02), (0.16, -0.22, 0.018), (0.0, 0.2, 0.022)):
    kit.cylinder((x, y, BZ + 0.002), r, 0.004, OIL, verts=16)

# noodles: wavy strands draped across the front / middle
for k in range(13):
    y0 = -0.36 + k * 0.045
    half = math.sqrt(max(0.0, 0.43 ** 2 - y0 ** 2))
    if half < 0.12:
        continue
    pts = []
    ph = random.uniform(0, 6)
    for i in range(9):
        t = i / 8
        x = -half + 2 * half * t
        y = y0 + 0.022 * math.sin(t * 9 + ph)
        z = BZ + 0.012 + 0.008 * math.sin(t * 13 + ph)
        pts.append((x, y, z))
    kit.tube(pts, 0.013, NOODLE, resolution=2, name='noodle')
# a lifted noodle loop near the front for volume
kit.tube([(-0.25, -0.2, BZ + 0.01), (-0.18, -0.24, BZ + 0.06), (-0.08, -0.22, BZ + 0.035), (0.02, -0.26, BZ + 0.012)],
         0.013, NOODLE, resolution=4, name='noodle')

# nori sheet standing at the back
kit.box((-0.04, 0.3, BZ + 0.15), (0.3, 0.012, 0.34), NORI, rot=(math.radians(-18), 0, math.radians(4)), bevel=0.004)
for dz in (-0.08, 0.0, 0.08):   # faint texture ridges
    kit.box((-0.04, 0.29 - 0.004 + dz * 0.0, BZ + 0.15 + dz), (0.28, 0.006, 0.006),
            kit.mat('#2c3f2a', 0.6), rot=(math.radians(-18), 0, math.radians(4)))

# chashu (two overlapping slices, back-left)
for (x, y, tilt, rz) in ((-0.24, 0.1, 0.22, 0.4), (-0.17, 0.2, 0.3, -0.2)):
    rot = (tilt, -0.15, rz)
    kit.cylinder((x, y, BZ + 0.03), 0.13, 0.03, CHASHU_DK, rot=rot, verts=32)
    R = Matrix.Translation((x, y, BZ + 0.03)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(-0.15, 4, 'Y') \
        @ Matrix.Rotation(tilt, 4, 'X')
    top = R @ Vector((0, 0, 0.016))
    kit.cylinder(top, 0.115, 0.004, CHASHU, rot=rot, verts=32)
    kit.torus(R @ Vector((0, 0, 0.019)), 0.07, 0.006, CHASHU_FAT, rot=rot, major_segs=28, minor_segs=4)

# soft-boiled egg halves (right)
for (x, y, rz) in ((0.24, 0.1, 0.5), (0.27, -0.09, -0.3)):
    kit.sphere((x, y, BZ + 0.015), (0.085, 0.115, 0.055), WHITE, rot=(0, 0, rz), segs=24, rings=12)
    kit.sphere((x, y, BZ + 0.06), (0.05, 0.06, 0.012), YOLK, rot=(0, 0, rz), segs=20, rings=8)

# narutomaki slices (front), scalloped edge + pink swirl
for (x, y, tilt) in ((-0.06, -0.28, 0.35), (0.11, -0.3, 0.3)):
    R = Matrix.Translation((x, y, BZ + 0.04)) @ Matrix.Rotation(tilt, 4, 'X')
    rot = (tilt, 0, 0)
    kit.cylinder(R @ Vector((0, 0, 0)), 0.078, 0.022, WHITE, rot=rot, verts=32)
    for i in range(12):
        a = i * 2 * math.pi / 12
        kit.sphere(R @ Vector((math.cos(a) * 0.078, math.sin(a) * 0.078, 0)), (0.016, 0.016, 0.011), WHITE,
                   rot=rot, segs=10, rings=5)
    sw = []
    for i in range(28):
        t = i / 27
        a = t * 2.3 * 2 * math.pi
        rr = 0.008 + 0.052 * t
        sw.append(R @ Vector((math.cos(a) * rr, math.sin(a) * rr, 0.012)))
    kit.tube(sw, 0.007, PINK, resolution=2, name='swirl')

# green onion rings
for _ in range(9):
    a = random.uniform(0, 2 * math.pi)
    r = random.uniform(0.05, 0.3)
    x, y = math.cos(a) * r, math.sin(a) * r * 0.8 - 0.02
    kit.torus((x, y, BZ + 0.035), 0.026, 0.009, ONION, rot=(random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4), 0),
              major_segs=12, minor_segs=5)

# ── chopsticks resting across the rim ────────────────────────────────────
for dx, dy in ((0.0, 0.0), (0.05, 0.035)):
    a = Vector((-0.58 + dx, -0.12 + dy, 0.42))
    b = Vector((0.6 + dx, 0.2 + dy, 0.42))
    kit.rod(a, a.lerp(b, 0.82), 0.02, WOOD, verts=12, r2=0.012, caps=False)
    kit.rod(a.lerp(b, 0.82), b, 0.012, WOOD_TIP, verts=12, r2=0.009, caps=False)
    kit.sphere(a, 0.02, WOOD, segs=12, rings=6)
    kit.sphere(b, 0.009, WOOD_TIP, segs=8, rings=4)
    kit.box(a.lerp(b, 0.08), (0.05, 0.05, 0.045), kit.mat('#b8201a', 0.4), rot=(0, 0, math.atan2(b.y - a.y, b.x - a.x)),
            bevel=0.004)   # red lacquer end band

# tilt the bowl toward the camera so the toppings read in the sprite
bpy.context.view_layer.update()
R = Matrix.Rotation(math.radians(18), 4, 'X')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = R @ o.matrix_world

kit.finalize_prop('ramen_bowl')
