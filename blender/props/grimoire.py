"""Asta's five-leaf-clover grimoire (Black Clover) — thick black tome, gold corners/spine bands, raised gold clover."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402


def slab(outline, thick, mats, y=0.0, inset=0.0, raise_=0.0, name='slab', smooth=False):
    """Extrude a 2D outline [(x, z), ...] along Y (centred on `y`). Optional inset/raise of both faces:
    rim faces get material 1, faces get material 0."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y - thick / 2, z)) for x, z in outline]
    back = [bm.verts.new((x, y + thick / 2, z)) for x, z in outline]
    f_front = bm.faces.new(front)
    f_back = bm.faces.new(list(reversed(back)))
    n = len(outline)
    sides = [bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n])) for i in range(n)]
    bm.normal_update()
    if f_front.normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    for f in sides:
        f.material_index = 1 if len(mats) > 1 else 0
    if inset:
        res = bmesh.ops.inset_individual(bm, faces=[f_front, f_back], thickness=inset, depth=raise_)
        for f in res['faces']:
            f.material_index = 1 if len(mats) > 1 else 0
    bmesh.ops.triangulate(bm, faces=[f_front, f_back], quad_method='BEAUTY', ngon_method='BEAUTY')
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    return obj


kit.reset()
random.seed(3)
LEATHER = kit.mat('#121116', 0.8)
LEATHER_W = kit.mat('#34323b', 0.75)
for _m in (LEATHER, LEATHER_W):
    _m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.15
GOLD = kit.mat('#d6a93a', 0.28, metal=1.0)
GOLD_D = kit.mat('#a87a22', 0.35, metal=1.0)
PAGE = kit.mat('#efe3c2', 0.9)
PAGE_D = kit.mat('#d4c39a', 0.9)
RIBBON = kit.mat('#b3202a', 0.7)

W, H, T = 0.6, 0.8, 0.24          # cover width, height, total thickness
CT = 0.028                         # cover board thickness
X0 = -W / 2                        # spine side
FY = -T / 2 + CT / 2               # front board centre y

# ── covers + spine ──
for y in (FY, -FY):
    kit.box((0.012, y, 0), (W, CT, H), LEATHER, bevel=0.012)
spine = kit.cylinder((X0 + 0.01, 0, 0), T / 2, H, LEATHER, verts=32, scale=(0.42, 1, 1))
# spine bands (gold ridges) and end caps
for z in (-0.3, -0.12, 0.12, 0.3):
    kit.cylinder((X0 + 0.01, 0, z), T / 2 + 0.006, 0.028, GOLD, verts=32, scale=(0.44, 1, 1))
    kit.torus((X0 + 0.01, 0, z + 0.014), T / 2 + 0.002, 0.005, GOLD_D, major_segs=32, minor_segs=6,
              scale=(0.44, 1, 1))

# ── page block with fore-edge layering ──
PX0, PX1 = X0 + 0.03, X0 + W - 0.01
kit.box(((PX0 + PX1) / 2, 0, 0), (PX1 - PX0, T - 2 * CT + 0.004, H - 0.04), PAGE, bevel=0.004)
for i, y in enumerate([-0.07, -0.042, -0.014, 0.014, 0.042, 0.07]):
    jitter = random.uniform(-0.004, 0.003)
    kit.box((PX1 + 0.001 + jitter, y, 0), (0.006, 0.006, H - 0.05 + jitter), PAGE_D)
    kit.box(((PX0 + PX1) / 2, y, H / 2 - 0.02 + 0.001 + jitter), (PX1 - PX0 - 0.02, 0.006, 0.006), PAGE_D)

# ── gold corner caps on the fore-edge corners of both boards ──
C = 0.12
for y in (FY, -FY):
    for sz in (1, -1):
        cx, cz = X0 + W + 0.012 + 0.004, sz * (H / 2 + 0.004)
        tri = [(cx, cz), (cx - C, cz), (cx, cz - sz * C)]
        if sz < 0:
            tri = list(reversed(tri))
        slab(tri, CT + 0.012, [GOLD, GOLD_D], y=y, inset=0.012, raise_=0.003, name='corner')
        kit.sphere((cx - 0.03, y - (CT / 2 + 0.008) * (1 if y < 0 else -1), cz - sz * 0.03), 0.009, GOLD_D,
                   segs=12, rings=6)
    # spine-side corners (smaller)
    for sz in (1, -1):
        kit.box((X0 + 0.06, y, sz * (H / 2 - 0.01)), (0.08, CT + 0.01, 0.03), GOLD, bevel=0.006)

# ── front cover decoration ──
FRONT = FY - CT / 2                # front surface y
CX, CZ = 0.03, 0.02                # clover centre on the cover
# border frame
for (x, z, w, h) in ((CX, 0.34, 0.46, 0.014), (CX, -0.34, 0.46, 0.014), (CX - 0.23, 0, 0.014, 0.69),
                     (CX + 0.23, 0, 0.014, 0.69)):
    kit.box((x, FRONT - 0.003, z), (w, 0.008, h), GOLD_D, bevel=0.003)
# medallion ring
kit.torus((CX, FRONT - 0.004, CZ), 0.2, 0.011, GOLD, rot=(math.pi / 2, 0, 0), major_segs=64, minor_segs=8)
kit.torus((CX, FRONT - 0.002, CZ), 0.215, 0.005, GOLD_D, rot=(math.pi / 2, 0, 0), major_segs=64, minor_segs=6)


def heart(scale, n=28):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * scale, y * scale))
    return pts  # lobes at +y, point at -y (≈ -17*scale)


# five heart-shaped leaves, points meeting at the centre
LS = 0.0046
for k in range(5):
    a = math.radians(90 + 72 * k)
    outline = []
    for x, y in heart(LS):
        yy = y + 17 * LS + 0.014                 # point near the origin, lobes outward
        u, v = -x * 0.82, yy
        rx = u * math.cos(a - math.pi / 2) - v * math.sin(a - math.pi / 2)
        rz = u * math.sin(a - math.pi / 2) + v * math.cos(a - math.pi / 2)
        outline.append((CX + rx, CZ + rz))
    slab(outline, 0.016, [GOLD, GOLD_D], y=FRONT - 0.004, inset=0.008, raise_=0.004, name='leaf')
    # vein down each leaf
    tip = Vector((CX + math.cos(a) * 0.13, FRONT - 0.016, CZ + math.sin(a) * 0.15))
    kit.rod((CX + math.cos(a) * 0.02, FRONT - 0.015, CZ + math.sin(a) * 0.02), tip, 0.0035, GOLD_D, verts=8)
kit.sphere((CX, FRONT - 0.014, CZ), (0.024, 0.01, 0.024), GOLD_D, segs=16, rings=8)
# stem
kit.tube([(CX + 0.0, FRONT - 0.012, CZ - 0.02), (CX + 0.03, FRONT - 0.012, CZ - 0.12),
          (CX + 0.07, FRONT - 0.012, CZ - 0.17)], 0.007, GOLD, taper_to=0.5, resolution=6, name='stem')

# worn scuffs along the cover edges
for _ in range(14):
    side = random.choice(['top', 'bottom', 'right'])
    if side == 'right':
        x, z = X0 + W + 0.01, random.uniform(-0.3, 0.3)
    else:
        x, z = random.uniform(X0 + 0.1, X0 + W - 0.1), (H / 2 + 0.002) * (1 if side == 'top' else -1)
    y = random.choice([FY, -FY])
    kit.sphere((x, y, z), (random.uniform(0.012, 0.03), CT * 0.52, random.uniform(0.006, 0.012))
               if side != 'right' else (0.006, CT * 0.52, random.uniform(0.012, 0.03)), LEATHER_W, segs=10, rings=5)

# ribbon bookmark hanging from the bottom
slab([(0.13, -H / 2 + 0.03), (0.165, -H / 2 + 0.03), (0.17, -H / 2 - 0.11), (0.155, -H / 2 - 0.09),
      (0.138, -H / 2 - 0.115)], 0.004, [RIBBON], y=-0.02, name='bookmark')

bpy.context.view_layer.update()
R = Euler((math.radians(-4), 0, math.radians(12))).to_matrix().to_4x4()
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = R @ o.matrix_world
kit.finalize_prop('grimoire')
