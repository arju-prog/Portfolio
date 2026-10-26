"""Deku's One For All fist (My Hero Academia) — clenched white glove, red/dark-green support gauntlet,
glowing green lightning cracks. Points up, knuckles tilted toward the camera (cursor for "Detroit Smash")."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402


def mesh_obj(verts, faces, mats, smooth=True, name='mesh'):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    return obj


def shell(r, a0, a1, z0, z1, thick, m, segs=16, taper=0.0, name='shell'):
    """Curved plate: a slice of a (slightly tapered) tube around Z, angles measured from -Y."""
    verts, faces = [], []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        for z, rr in ((z0, r), (z1, r + taper)):
            for off in (0, thick):
                R = rr + off
                verts.append((R * math.sin(a), -R * math.cos(a), z))
    for i in range(segs):
        b, c = 4 * i, 4 * (i + 1)
        # verts per column: 0 (z0,in) 1 (z0,out) 2 (z1,in) 3 (z1,out)
        faces += [(b + 1, c + 1, c + 3, b + 3), (b, b + 2, c + 2, c), (b, c, c + 1, b + 1), (b + 2, b + 3, c + 3, c + 2)]
    faces += [(0, 1, 3, 2), (4 * segs, 4 * segs + 2, 4 * segs + 3, 4 * segs + 1)]
    obj = mesh_obj(verts, faces, [m], name=name)
    mod = obj.modifiers.new('bevel', 'BEVEL')
    mod.width = min(thick * 0.4, 0.004)
    mod.segments = 2
    return obj


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


kit.reset()
random.seed(1)
GLOVE = kit.mat('#f3f2ee', 0.6)
GLOVE_S = kit.mat('#d9d7d0', 0.7)
GREEN = kit.mat('#1d4a33', 0.45, metal=0.3)
GREEN_D = kit.mat('#123323', 0.5, metal=0.3)
RED = kit.mat('#c81f2a', 0.35, metal=0.2)
STUD = kit.mat('#cfd3d9', 0.2, metal=1.0)
BOLT = kit.mat('#4dff3a', 0.3, emit=2.2)

# ── fist (metaball families so each finger stays readable) ──
# Back of the hand / knuckles face -Y (camera); fingers curl away towards +Y; thumb wraps on the far side.
palm = kit._meta('palm', 0.008)
kit.blob_ellipsoid(palm, (0, 0.012, 0.135), (0.1, 0.058, 0.1))
for sx in (-1, 1):
    kit.blob_ellipsoid(palm, (0.055 * sx, 0.012, 0.15), (0.05, 0.05, 0.08))
kit.blob_ellipsoid(palm, (0, 0.012, 0.06), (0.075, 0.052, 0.06))
kit.blob_limb(palm, (0, 0.01, 0.06), (0, 0.01, -0.03), 0.06, 0.058)
fingers = [(-0.068, -0.004, 0.028), (-0.023, 0.006, 0.029), (0.023, 0.0, 0.028), (0.066, -0.018, 0.025)]
for i, (x, drop, r) in enumerate(fingers):
    z = 0.232 + drop
    kit.blob_ball(palm, (x, -0.012, z - 0.012), r * 1.08)   # knuckle bump
    f = kit._meta(f'finger{i}', 0.007)
    kit.blob_limb(f, (x, -0.008, z + 0.006), (x, 0.07, z + 0.01), r * 1.05, r)
    kit.blob_limb(f, (x, 0.078, z - 0.004), (x, 0.084, z - 0.085), r * 0.98, r * 0.92)
    kit.blob_limb(f, (x, 0.078, z - 0.098), (x, 0.04, z - 0.108), r * 0.9, r * 0.85)
thumb = kit._meta('thumb', 0.007)
kit.blob_limb(thumb, (-0.088, 0.012, 0.06), (-0.108, 0.07, 0.095), 0.034, 0.03)
kit.blob_limb(thumb, (-0.108, 0.075, 0.095), (-0.055, 0.122, 0.125), 0.029, 0.026)
kit.blob_limb(thumb, (-0.055, 0.122, 0.125), (-0.005, 0.124, 0.135), 0.026, 0.023)
kit.solidify_blobs({'palm': GLOVE, 'finger0': GLOVE, 'finger1': GLOVE, 'finger2': GLOVE, 'finger3': GLOVE,
                    'thumb': GLOVE})

# glove cuff + seam on the back of the hand
kit.torus((0, 0.005, 0.0), 0.062, 0.016, GLOVE_S, major_segs=32, minor_segs=8)
kit.torus((0, 0.005, -0.016), 0.064, 0.008, RED, major_segs=32, minor_segs=6)

# ── support gauntlet ──
Z0, Z1 = -0.3, -0.025
kit.cone((0, 0.005, (Z0 + Z1) / 2), 0.07, 0.066, Z1 - Z0, GREEN, verts=32)
for z in (Z1 - 0.012, Z0 + 0.014):
    kit.cylinder((0, 0.005, z), 0.078, 0.026, RED, verts=32)
    kit.torus((0, 0.005, z + 0.013), 0.077, 0.004, STUD, major_segs=32, minor_segs=4)
# armoured front plate + side plates
shell(0.074, -0.85, 0.85, Z0 + 0.04, Z1 - 0.04, 0.012, RED, segs=16, name='front_plate')
for sgn in (1, -1):
    shell(0.074, sgn * 1.05, sgn * 2.3, Z0 + 0.06, Z1 - 0.06, 0.009, GREEN_D, segs=10, name='side_plate')
# dark green chevron strips on the red plate
for k in range(2):
    z = Z0 + 0.09 + k * 0.08
    shell(0.0865, -0.32, 0.32, z, z + 0.022, 0.005, GREEN_D, segs=8, name='strip')
# studs on the plate corners
for a in (-0.7, 0.7):
    for z in (Z0 + 0.065, Z1 - 0.065):
        kit.sphere((0.087 * math.sin(a), -0.087 * math.cos(a), z), 0.009, STUD, segs=12, rings=6)

# ── One For All lightning: zig-zag cracks hugging the surface ──
bpy.ops.object.select_all(action='DESELECT')
for o in mesh_objects():
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects()[0]
bpy.ops.object.convert(target='MESH')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
dg = bpy.context.evaluated_depsgraph_get()
trees = [BVHTree.FromObject(o, dg) for o in mesh_objects()]


def surf(phi, z, lift=0.004):
    """Surface point seen from angle phi (0 = front / -Y) at height z."""
    d = Vector((math.sin(phi), -math.cos(phi), 0))
    origin = Vector((0, 0.005, z)) + d * 1.0
    best = None
    for t in trees:
        hit, nrm, _, dist = t.ray_cast(origin, -d)
        if hit is not None and (best is None or dist < best[1]):
            best = (hit + nrm * lift, dist)
    return best[0] if best else None


def surf_front(x, z, lift=0.004):
    """Surface point hit by a ray travelling +Y at (x, z) — for the back of the hand."""
    best = None
    for t in trees:
        hit, nrm, _, dist = t.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        if hit is not None and (best is None or dist < best[1]):
            best = (hit + nrm * lift, dist)
    return best[0] if best else None


def bolt_front(start, end, n, amp, radius=0.0042):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = start[0] + (end[0] - start[0]) * t
        z = start[1] + (end[1] - start[1]) * t
        if 0 < i < n:
            x += amp * (1 if i % 2 else -1) * random.uniform(0.5, 1.0)
            z += random.uniform(-0.006, 0.006)
        p = surf_front(x, z)
        if p is not None and (not pts or (p - pts[-1]).length < 0.06):
            pts.append(p)
    if len(pts) >= 2:
        kit.tube(pts, radius, BOLT, smooth_path=False, resolution=1, name='bolt')


def bolt(start, end, n, amp, radius=0.0042):
    pts = []
    for i in range(n + 1):
        t = i / n
        phi = start[0] + (end[0] - start[0]) * t
        z = start[1] + (end[1] - start[1]) * t
        if 0 < i < n:
            phi += amp * (1 if i % 2 else -1) * random.uniform(0.5, 1.0)
            z += random.uniform(-0.012, 0.012)
        p = surf(phi, z)
        if p is not None:
            pts.append(p)
    if len(pts) >= 2:
        kit.tube(pts, radius, BOLT, smooth_path=False, resolution=1, name='bolt')
    return pts


bolt((0.1, Z0 + 0.01), (0.0, 0.0), 12, 0.16, 0.0048)
bolt_front((0.0, -0.005), (-0.01, 0.07), 4, 0.012, 0.0048)
bolt_front((-0.01, 0.07), (-0.06, 0.2), 7, 0.014, 0.0042)
bolt_front((-0.01, 0.07), (0.05, 0.19), 7, 0.014, 0.0042)
bolt_front((-0.03, 0.12), (-0.08, 0.1), 2, 0.008, 0.0036)
bolt_front((0.02, 0.13), (0.075, 0.115), 2, 0.008, 0.0036)
bolt((0.02, -0.12), (0.45, -0.02), 4, 0.1, 0.004)
bolt((-0.6, Z0 + 0.02), (-0.25, -0.1), 6, 0.12, 0.0042)
bolt((0.7, -0.26), (0.55, 0.12), 7, 0.12, 0.0042)
bolt((1.3, -0.22), (1.05, 0.08), 6, 0.12, 0.0042)
bolt((-1.3, -0.2), (-1.0, 0.06), 6, 0.12, 0.0042)

# pose: point up, tilt the knuckles toward the camera
bpy.context.view_layer.update()
R = Matrix(Euler((math.radians(32), 0, math.radians(8))).to_matrix().to_4x4())
for o in mesh_objects():
    o.matrix_world = R @ o.matrix_world
kit.finalize_prop('ofa_glove')
