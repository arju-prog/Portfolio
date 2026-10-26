"""Hidden Leaf forehead protector (Naruto) — navy cloth loop with knot + tails, riveted steel plate, engraved leaf swirl."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402


# ── local helpers ────────────────────────────────────────────────────────

def mesh_obj(verts, faces, mats, face_mats=None, smooth=True, name='mesh'):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    for i, p in enumerate(me.polygons):
        p.use_smooth = smooth
        if face_mats:
            p.material_index = face_mats[i]
    return obj


def catmull(points, n=8, closed=False):
    P = [Vector(p) for p in points]
    out = []
    count = len(P) if closed else len(P) - 1
    for i in range(count):
        p0 = P[(i - 1) % len(P)] if (closed or i > 0) else P[0]
        p1, p2 = P[i], P[(i + 1) % len(P)]
        p3 = P[(i + 2) % len(P)] if (closed or i + 2 < len(P)) else P[-1]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    if not closed:
        out.append(P[-1])
    return out


def ribbon(points, ups, width, thick, m, closed=False, name='ribbon', taper=None):
    """Flat band with a rectangular cross-section along `points`; `ups` gives the width direction per point."""
    verts, faces = [], []
    n = len(points)
    for i, p in enumerate(points):
        a = points[(i - 1) % n] if (closed or i > 0) else points[i]
        b = points[(i + 1) % n] if (closed or i < n - 1) else points[i]
        T = (b - a).normalized()
        up = Vector(ups[i])
        side = (up - T * up.dot(T)).normalized()
        N = T.cross(side).normalized()
        w = width * (taper(i / (n - 1)) if taper else 1.0) / 2
        h = thick / 2
        for sw, sn in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            verts.append(p + side * w * sw + N * h * sn)
    segs = n if closed else n - 1
    for i in range(segs):
        A, B = 4 * i, 4 * ((i + 1) % n)
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((A + k, A + k2, B + k2, B + k))
    if not closed:
        faces.append((3, 2, 1, 0))
        L = 4 * (n - 1)
        faces.append((L, L + 1, L + 2, L + 3))
    return mesh_obj(verts, faces, [m], name=name)


def bevel(obj, width, segs=2):
    mod = obj.modifiers.new('bevel', 'BEVEL')
    mod.width = width
    mod.segments = segs
    mod.limit_method = 'ANGLE'
    return obj


# ── build ────────────────────────────────────────────────────────────────

kit.reset()
CLOTH = kit.mat('#16204a', 0.9)
CLOTH_D = kit.mat('#0f1736', 0.9)
STEEL = kit.mat('#c7ced8', 0.22, metal=0.85)
RIVET = kit.mat('#e6ebf1', 0.15, metal=1.0)
ENGRAVE = kit.mat('#1a1d24', 0.5, metal=0.3)
STITCH = kit.mat('#2f3f78', 0.9)

RX, RY, BAND_H = 0.3, 0.33, 0.12


def loop_pt(th, off=0.0, z=0.0):
    return Vector(((RX + off) * math.sin(th), -(RY + off) * math.cos(th), z))


# cloth loop (opens at the back into the knot), with a gentle cloth wave
pts, ups = [], []
N = 120
for i in range(N + 1):
    th = -math.pi * 0.94 + (2 * math.pi * 0.94) * i / N
    pts.append(loop_pt(th, 0.0, 0.006 * math.sin(th * 5)))
    ups.append((0, 0, 1))
ribbon(pts, ups, BAND_H, 0.014, CLOTH, name='band')
# stitched hems (thin raised lines along the top and bottom edges)
for zz in (BAND_H / 2 - 0.012, -BAND_H / 2 + 0.012):
    hem = [loop_pt(-math.pi * 0.94 + (2 * math.pi * 0.94) * i / N, 0.008, zz + 0.006 * math.sin(
        (-math.pi * 0.94 + (2 * math.pi * 0.94) * i / N) * 5)) for i in range(N + 1)]
    ribbon(hem, [(0, 0, 1)] * len(hem), 0.004, 0.004, STITCH, name='hem')

# steel plate: curved, bevelled, sitting proud of the band
PH, PT, PA = 0.155, 0.022, 0.6
P_OFF = 0.007 + PT / 2
plate_pts = [loop_pt(-PA + 2 * PA * i / 24, P_OFF) for i in range(25)]
bevel(ribbon(plate_pts, [(0, 0, 1)] * 25, PH, PT, STEEL, name='plate'), 0.007, 3)


def on_plate(u, v, lift=0.0):
    """Point on the plate's front surface at horizontal offset u, height v."""
    r_y = RY + P_OFF + PT / 2 + lift
    r_x = RX + P_OFF + PT / 2 + lift
    th = math.asin(max(-1, min(1, u / r_x)))
    return Vector((r_x * math.sin(th), -r_y * math.cos(th), v))


# rivets in the corners
for su in (1, -1):
    for sv in (1, -1):
        p = on_plate(su * 0.142, sv * 0.054, 0.0)
        kit.sphere(p, (0.011, 0.007, 0.011), RIVET, segs=16, rings=8)

# engraved Konoha leaf: outer leaf contour ending in a sharp tip, plus the inner swirl
S = 0.074
contour_a = [(-1.05, -0.62), (-0.35, -0.6), (0.25, -0.5), (0.62, -0.15), (0.72, 0.3), (0.78, 0.82)]
contour_b = [(0.78, 0.82), (0.25, 0.72), (-0.3, 0.55), (-0.62, 0.18), (-0.55, -0.22), (-0.2, -0.38),
             (0.18, -0.25), (0.3, 0.08), (0.1, 0.3), (-0.17, 0.2), (-0.2, -0.02), (0.0, -0.06)]
for curve in (contour_a, contour_b):
    kit.tube([on_plate(u * S, v * S - 0.002, -0.002) for u, v in curve], 0.0068, ENGRAVE,
             resolution=8, name='leaf')

# knot at the back + two wind-blown tails trailing to the camera's side
back = loop_pt(math.pi, 0.01)
kit.sphere(back + Vector((0, 0.02, 0)), (0.055, 0.04, 0.05), CLOTH_D, segs=20, rings=12)
for sx in (1, -1):
    kit.sphere(back + Vector((0.045 * sx, 0.01, 0)), (0.035, 0.03, 0.055), CLOTH, rot=(0, 0.4 * sx, 0), segs=16, rings=10)

tail_a = catmull([back + Vector(d) for d in
                  [(0.02, 0.03, 0.0), (0.14, 0.09, -0.03), (0.3, 0.1, -0.08), (0.46, 0.04, -0.1), (0.6, -0.05, -0.07)]], 6)
ribbon(tail_a, [(0, 0.25, 1)] * len(tail_a), 0.085, 0.012, CLOTH, name='tail_a', taper=lambda t: 1 - 0.25 * t)
tail_b = catmull([back + Vector(d) for d in
                  [(0.02, 0.03, -0.01), (0.1, 0.1, -0.08), (0.22, 0.12, -0.18), (0.36, 0.06, -0.25), (0.47, -0.02, -0.26)]], 6)
ribbon(tail_b, [(0.3, 0.2, 1)] * len(tail_b), 0.08, 0.012, CLOTH_D, name='tail_b', taper=lambda t: 1 - 0.25 * t)

bpy.context.view_layer.update()
R = Euler((math.radians(8), 0, math.radians(18))).to_matrix().to_4x4()
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = R @ o.matrix_world
kit.finalize_prop('leaf_headband')
