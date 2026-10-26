"""Open pirate treasure chest: wood planks, iron straps, brass corner brackets and lock plate,
barrel lid open, overflowing with gold coins, gems and a pearl strand."""
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
random.seed(7)

WOOD = kit.mat('#8a5a2e', 0.8)
WOOD2 = kit.mat('#7a4c24', 0.82)
WOOD_DK = kit.mat('#3f2512', 0.85)
IRON = kit.mat('#3b3836', 0.4, metal=0.85)
BRASS = kit.mat('#b98a34', 0.3, metal=0.9)
GOLD = kit.mat('#f0b52c', 0.22, metal=1.0)
GOLD2 = kit.mat('#d99a1e', 0.3, metal=1.0)
INK = kit.mat('#140c06', 0.6)
RUBY = kit.mat('#d0162e', 0.08, emit=0.35)
EMERALD = kit.mat('#17b45a', 0.08, emit=0.35)
SAPPHIRE = kit.mat('#2a5bff', 0.08, emit=0.35)
PEARL = kit.mat('#f6f0e4', 0.25)


# ── local helpers ────────────────────────────────────────────────────────

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


def arc_band(x0, x1, cy, cz, r_in, r_out, a0, a1, m, segs=8, name='arc', smooth=False):
    """Curved slab around the X axis (centre cy, cz). Angle 0 = front (-Y), pi = back (+Y), pi/2 = top."""
    bm = bmesh.new()
    rings = []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        dy, dz = -math.cos(a), math.sin(a)
        rings.append([bm.verts.new((x, cy + dy * r, cz + dz * r))
                      for x, r in ((x0, r_in), (x1, r_in), (x1, r_out), (x0, r_out))])
    for i in range(segs):
        a, b = rings[i], rings[i + 1]
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    return _mesh_obj(bm, m, name, smooth)


def half_disc(x0, x1, cy, cz, r, m, segs=16, name='cap'):
    bm = bmesh.new()
    sides = []
    for x in (x0, x1):
        vs = [bm.verts.new((x, cy - math.cos(math.pi * i / segs) * r, cz + math.sin(math.pi * i / segs) * r))
              for i in range(segs + 1)]
        sides.append(vs)
    bm.faces.new(sides[0])
    bm.faces.new(list(reversed(sides[1])))
    for i in range(segs):
        bm.faces.new((sides[0][i], sides[0][i + 1], sides[1][i + 1], sides[1][i]))
    bm.faces.new((sides[0][segs], sides[0][0], sides[1][0], sides[1][segs]))
    return _mesh_obj(bm, m, name)


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def coin(loc, normal, jitter=0.35, r=0.045):
    n = Vector(normal).normalized()
    n = (n + Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * jitter).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(n).to_euler()
    kit.cylinder(loc, r, 0.012, GOLD if random.random() < 0.65 else GOLD2, rot=rot, verts=18)


def gem(loc, m, size=0.05, tilt=(0, 0, 0)):
    """Brilliant-cut gem: crown + pavilion cones, faceted."""
    R = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(tilt[0], 4, 'X') @ Matrix.Rotation(tilt[1], 4, 'Y')
    crown = kit.cone((0, 0, size * 0.25), size, size * 0.6, size * 0.5, m, verts=8, smooth=False)
    pav = kit.cone((0, 0, -size * 0.5), 0.0, size, size, m, verts=8, smooth=False)
    bpy.context.view_layer.update()
    for o in (crown, pav):
        o.matrix_world = R @ o.matrix_world


def rivet(loc, r=0.012):
    kit.sphere(loc, r, BRASS, segs=8, rings=4)


# ── body ─────────────────────────────────────────────────────────────────
W, D, Hh = 1.0, 0.6, 0.45
kit.box((0, 0, Hh / 2), (W - 0.04, D - 0.04, Hh), WOOD_DK)                                 # core
kit.box((0, 0, 0.03), (W + 0.05, D + 0.05, 0.06), WOOD_DK, bevel=0.012)                    # base trim
ph = Hh / 3
for i in range(3):
    z = ph * (i + 0.5)
    m = WOOD if i % 2 == 0 else WOOD2
    for sy in (-1, 1):
        kit.box((0, sy * (D / 2 - 0.01), z), (W - 0.02, 0.04, ph - 0.012), m, bevel=0.01)
    for sx in (-1, 1):
        kit.box((sx * (W / 2 - 0.01), 0, z), (0.04, D - 0.02, ph - 0.012), WOOD2 if m is WOOD else WOOD, bevel=0.01)

# iron straps (vertical) + top rim band
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.box((sx * 0.27, sy * (D / 2 + 0.012), Hh / 2), (0.075, 0.014, Hh), IRON, bevel=0.004)
        for z in (0.08, 0.22, 0.36):
            rivet((sx * 0.27, sy * (D / 2 + 0.02), z))
for sy in (-1, 1):
    kit.box((0, sy * (D / 2 + 0.014), Hh - 0.02), (W + 0.02, 0.016, 0.05), IRON, bevel=0.005)
for sx in (-1, 1):
    kit.box((sx * (W / 2 + 0.014), 0, Hh - 0.02), (0.016, D + 0.02, 0.05), IRON, bevel=0.005)

# brass corner brackets (full height L-guards) with rivets
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.box((sx * (W / 2 - 0.035), sy * (D / 2 + 0.02), Hh / 2), (0.1, 0.012, Hh + 0.02), BRASS, bevel=0.004)
        kit.box((sx * (W / 2 + 0.02), sy * (D / 2 - 0.035), Hh / 2), (0.012, 0.1, Hh + 0.02), BRASS, bevel=0.004)
        for z in (0.06, 0.39):
            rivet((sx * (W / 2 - 0.04), sy * (D / 2 + 0.028), z))
            rivet((sx * (W / 2 + 0.028), sy * (D / 2 - 0.04), z))
    # side handles
    kit.torus((sx * (W / 2 + 0.05), 0, 0.3), 0.07, 0.013, IRON, rot=(0, math.pi / 2, 0), major_segs=24,
              minor_segs=8, scale=(1, 1, 1))
    kit.box((sx * (W / 2 + 0.03), 0, 0.35), (0.03, 0.08, 0.04), IRON, bevel=0.006)

# brass ball feet
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.sphere((sx * (W / 2 - 0.02), sy * (D / 2 - 0.02), 0.0), 0.04, BRASS, segs=12, rings=6)

# lock plate with keyhole
kit.box((0, -D / 2 - 0.03, Hh - 0.1), (0.17, 0.022, 0.2), BRASS, bevel=0.016)
kit.cylinder((0, -D / 2 - 0.042, Hh - 0.08), 0.018, 0.01, INK, rot=(math.pi / 2, 0, 0), verts=12)
kit.box((0, -D / 2 - 0.042, Hh - 0.115), (0.016, 0.01, 0.045), INK)
for x in (-0.06, 0.06):
    for z in (Hh - 0.03, Hh - 0.17):
        rivet((x, -D / 2 - 0.043, z), 0.01)

# ── treasure ─────────────────────────────────────────────────────────────
MC = Vector((0, -0.01, Hh - 0.02))
MR = Vector((0.46, 0.27, 0.15))
kit.sphere(MC, MR, GOLD2, segs=32, rings=12)


def mound_point(x, y):
    t = 1 - (x / MR.x) ** 2 - (y / MR.y) ** 2
    if t <= 0:
        return None
    z = MC.z + MR.z * math.sqrt(t)
    n = Vector((x / MR.x ** 2, y / MR.y ** 2, (z - MC.z) / MR.z ** 2)).normalized()
    return Vector((x, y + MC.y, z)), n


placed = 0
tries = 0
while placed < 85 and tries < 2000:
    tries += 1
    x, y = random.uniform(-0.46, 0.46), random.uniform(-0.27, 0.27)
    mp = mound_point(x, y)
    if mp is None:
        continue
    p, n = mp
    coin(p + n * 0.006, n)
    placed += 1
# a few stacked coin piles on top
for (x, y, k) in ((-0.18, -0.06, 4), (0.22, 0.02, 3)):
    p, n = mound_point(x, y)
    for i in range(k):
        kit.cylinder(p + Vector((random.uniform(-0.006, 0.006), random.uniform(-0.006, 0.006), 0.012 * i + 0.008)),
                     0.045, 0.012, GOLD, verts=18)
# coins spilling over the front rim and on the ground
for (x, z, tilt) in ((-0.36, Hh + 0.01, 0.9), (0.12, Hh + 0.0, 1.1), (0.38, Hh - 0.01, 1.2)):
    coin((x, -D / 2 - 0.03, z), (0, -math.sin(tilt), math.cos(tilt)), jitter=0.1)
for (x, y) in ((-0.3, -0.42), (-0.18, -0.46), (0.26, -0.44), (0.42, -0.4), (0.05, -0.47), (-0.42, -0.38)):
    coin((x, y, 0.006 + random.uniform(0, 0.01)), (0, 0, 1), jitter=0.12)
coin((0.17, -0.37, 0.05), (0, -0.6, 0.8), jitter=0.05)   # one leaning against the chest

# gems
for (x, y, m, size, tilt) in ((-0.24, -0.12, RUBY, 0.075, (0.5, -0.3, 0)), (0.08, -0.16, EMERALD, 0.068, (0.6, 0.35, 0)),
                               (0.32, -0.06, SAPPHIRE, 0.062, (0.4, 0.6, 0)), (-0.04, 0.04, RUBY, 0.05, (-0.2, 0.2, 0))):
    p, n = mound_point(x, y)
    gem(p + n * size * 0.55, m, size, tilt=tilt)

# pearl strand draped over the front edge
strand = [Vector((-0.02, -0.12, Hh + 0.12)), Vector((-0.1, -0.24, Hh + 0.05)), Vector((-0.14, -D / 2 - 0.04, Hh + 0.01)),
          Vector((-0.16, -D / 2 - 0.05, Hh - 0.1)), Vector((-0.24, -D / 2 - 0.05, Hh - 0.14)),
          Vector((-0.3, -D / 2 - 0.045, Hh - 0.06)), Vector((-0.32, -D / 2 - 0.04, Hh + 0.0)),
          Vector((-0.3, -0.24, Hh + 0.06))]
for i in range(len(strand) - 1):
    a, b = strand[i], strand[i + 1]
    k = max(1, int((b - a).length / 0.03))
    for j in range(k):
        kit.sphere(a.lerp(b, j / k), 0.016, PEARL, segs=10, rings=6)

# ── lid (built closed, then swung open about the back hinge) ─────────────
before = set(bpy.context.scene.objects)
CY, CZ, LR = 0.0, Hh, D / 2 + 0.01
n_planks = 5
for i in range(n_planks):
    a0 = math.pi * i / n_planks + 0.012
    a1 = math.pi * (i + 1) / n_planks - 0.012
    arc_band(-W / 2 + 0.01, W / 2 - 0.01, CY, CZ, LR - 0.04, LR, a0, a1, WOOD if i % 2 == 0 else WOOD2, segs=4)
arc_band(-W / 2 + 0.02, W / 2 - 0.02, CY, CZ, LR - 0.05, LR - 0.03, 0, math.pi, WOOD_DK, segs=16)   # inner lining
for sx in (-1, 1):
    half_disc(sx * (W / 2 - 0.03), sx * (W / 2 + 0.01), CY, CZ, LR, WOOD_DK)
    arc_band(sx * (W / 2 + 0.005), sx * (W / 2 + 0.025), CY, CZ, LR - 0.06, LR + 0.012, 0, math.pi, BRASS,
             segs=20, smooth=True)                                                           # brass end trim
    arc_band(sx * 0.27 - 0.037, sx * 0.27 + 0.037, CY, CZ, LR, LR + 0.014, 0, math.pi, IRON, segs=20, smooth=True)
    for k in range(1, 6):
        a = math.pi * k / 6
        rivet((sx * 0.27, CY - math.cos(a) * (LR + 0.02), CZ + math.sin(a) * (LR + 0.02)))
# lid front rim band + hasp
kit.box((0, -LR - 0.006, CZ + 0.025), (W + 0.02, 0.016, 0.05), IRON, bevel=0.005)
kit.box((0, -LR - 0.02, CZ + 0.0), (0.07, 0.014, 0.12), BRASS, bevel=0.006)
kit.torus((0, -LR - 0.03, CZ - 0.05), 0.022, 0.008, BRASS, rot=(math.pi / 2, 0, 0), major_segs=16, minor_segs=6)
# hinges at the back
for sx in (-1, 1):
    kit.cylinder((sx * 0.27, D / 2 + 0.01, Hh), 0.022, 0.1, IRON, rot=(0, math.pi / 2, 0), verts=12)

OPEN = math.radians(-108)
hinge = Vector((0, D / 2 + 0.01, Hh))
bpy.context.view_layer.update()
T = Matrix.Translation(hinge) @ Matrix.Rotation(OPEN, 4, 'X') @ Matrix.Translation(-hinge)
for o in set(bpy.context.scene.objects) - before:
    if 'Cylinder' in o.name and abs(o.location.y - (D / 2 + 0.01)) < 1e-4:
        continue   # hinge barrels stay put
    o.matrix_world = T @ o.matrix_world

kit.finalize_prop('treasure_chest')
