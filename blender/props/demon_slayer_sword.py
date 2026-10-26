"""Asta's Demon-Slayer Sword (Black Clover) — huge chipped black greatsword with rust, cross-guard and wrapped grip."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402


def slab(outline, thick, mats, inset=0.0, raise_=0.0, name='slab'):
    """Extrude a 2D outline [(x, z), ...] (counter-clockwise seen from -Y) along Y.
    Optionally inset both faces (thinner honed rim, mat index 1, raised centre mat index 0)."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -thick / 2, z)) for x, z in outline]
    back = [bm.verts.new((x, thick / 2, z)) for x, z in outline]
    f_front = bm.faces.new(front)
    f_back = bm.faces.new(list(reversed(back)))
    n = len(outline)
    sides = [bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n])) for i in range(n)]
    bm.normal_update()
    if f_front.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for f in sides:
        f.material_index = 1
    if inset:
        res = bmesh.ops.inset_individual(bm, faces=[f_front, f_back], thickness=inset, depth=raise_)
        for f in res['faces']:
            f.material_index = 1
        f_front.material_index = f_back.material_index = 0
    bmesh.ops.triangulate(bm, faces=[f_front, f_back], quad_method='BEAUTY', ngon_method='BEAUTY')
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    return obj


kit.reset()
random.seed(7)
BLACK = kit.mat('#17171b', 0.38, metal=0.75)
EDGE = kit.mat('#62656e', 0.3, metal=0.9)
RUST = kit.mat('#6e3519', 0.95, metal=0.1)
RUST_L = kit.mat('#93502a', 0.95, metal=0.0)
IRON = kit.mat('#26262b', 0.35, metal=0.85)
WRAP = kit.mat('#d3c8ae', 0.95)
WRAP_D = kit.mat('#a89c82', 0.95)

# ── blade outline: broad, slanted broken tip, notched and chipped edges ──
right = [(0.088, 0.0), (0.094, 0.08), (0.096, 0.115), (0.074, 0.13), (0.07, 0.145), (0.097, 0.165),
         (0.1, 0.29), (0.082, 0.305), (0.068, 0.33), (0.08, 0.35), (0.101, 0.37), (0.104, 0.5),
         (0.09, 0.515), (0.088, 0.535), (0.105, 0.55), (0.106, 0.66), (0.092, 0.685)]
tip = [(0.06, 0.70), (0.048, 0.685), (0.03, 0.692), (0.005, 0.725), (-0.03, 0.735), (-0.04, 0.752),
       (-0.075, 0.765), (-0.1, 0.785)]
left = [(-0.108, 0.76), (-0.106, 0.62), (-0.088, 0.6), (-0.084, 0.58), (-0.104, 0.565), (-0.103, 0.46),
        (-0.08, 0.44), (-0.072, 0.41), (-0.088, 0.385), (-0.101, 0.375), (-0.098, 0.24),
        (-0.084, 0.225), (-0.096, 0.205), (-0.092, 0.08), (-0.088, 0.0)]
outline = [(x, z * 1.12) for x, z in right + tip + left]
slab(outline, 0.024, [BLACK, EDGE], inset=0.016, raise_=0.008, name='blade')

# fuller-like raised spine strip running up the centre
spine = [(-0.011, 0.03), (0.011, 0.03), (0.011, 0.66), (0.0, 0.71), (-0.011, 0.66)]
s = slab(spine, 0.05, [EDGE, EDGE], name='spine')

# rust patches: clusters of flattened discs on both faces
for cx, cz, k in ((0.05, 0.47, 9), (-0.055, 0.23, 7), (-0.045, 0.74, 7), (0.06, 0.09, 5), (0.04, 0.66, 4),
                  (-0.02, 0.5, 3)):
    for _ in range(k):
        x = cx + random.uniform(-0.025, 0.025)
        z = cz + random.uniform(-0.035, 0.035)
        r = random.uniform(0.006, 0.013)
        for sy in (-1, 1):
            kit.sphere((x, sy * 0.0205, z), (r, 0.0018, r * random.uniform(0.4, 1.0)),
                       RUST if random.random() < 0.55 else RUST_L, rot=(0, random.uniform(0, 3), 0), segs=10, rings=5)

# ── cross-guard ──
kit.box((0, 0, -0.02), (0.3, 0.06, 0.04), IRON, bevel=0.008)
kit.box((0, 0, -0.02), (0.31, 0.04, 0.025), EDGE, bevel=0.006)
for sx in (1, -1):
    kit.sphere((0.16 * sx, 0, -0.02), (0.022, 0.034, 0.026), IRON, segs=16, rings=8)
    kit.sphere((0.07 * sx, -0.031, -0.02), 0.008, EDGE, segs=12, rings=6)
kit.box((0, 0, 0.004), (0.12, 0.04, 0.02), IRON, bevel=0.005)

# ── grip with bandage wraps ──
G_TOP, G_BOT = -0.04, -0.29
kit.cylinder((0, 0, (G_TOP + G_BOT) / 2), 0.027, G_TOP - G_BOT, IRON, verts=20)
n = 11
step = (G_TOP - G_BOT) / n
for i in range(n):
    z = G_TOP - step * (i + 0.5)
    kit.torus((0, 0, z), 0.029, 0.013, WRAP if i % 2 == 0 else WRAP_D, rot=(0.25 if i % 2 else -0.25, 0, 0),
              major_segs=28, minor_segs=8)
kit.tube([(0.03, -0.01, G_TOP - 0.03), (0.06, -0.02, G_TOP - 0.07), (0.07, -0.03, G_TOP - 0.13)], 0.008,
         WRAP, taper_to=0.5, resolution=6, name='wrap_tail')

# ── pommel ──
kit.cylinder((0, 0, G_BOT - 0.012), 0.036, 0.024, IRON, verts=8)
kit.sphere((0, 0, G_BOT - 0.035), (0.03, 0.03, 0.026), EDGE, segs=16, rings=8)

kit.finalize_prop('demon_slayer_sword')
