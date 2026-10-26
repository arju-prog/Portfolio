"""IMDb movie-review sentiment analysis diorama: a silver film reel standing on its edge with film unspooling across
a red-velvet base, a clapperboard, a striped popcorn bucket, a red-to-green "sentiment meter" gauge with its needle
in the green, and a floating thumbs-up plus gold stars."""
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
random.seed(89)

# ── palette ──────────────────────────────────────────────────────────────
BASE_TOP = kit.mat('#f3ece0', 0.6)
VELVET = kit.mat('#9b1c2c', 0.85)
BASE_TRIM = kit.mat('#2a1416', 0.45)
GOLD = kit.mat('#e2b64a', 0.3, metal=0.9)
REEL = kit.mat('#c3ccd8', 0.28, metal=0.9)
REEL_DK = kit.mat('#7d8796', 0.35, metal=0.9)
FILM_ROLL = kit.mat('#3a2a20', 0.3)
FILM = kit.mat('#231d1a', 0.35)
SPROCKET = kit.mat('#efe6d4', 0.5)
FRAME_LIT = kit.mat('#f4b24a', 0.4, emit=0.6)
FRAME_LIT2 = kit.mat('#7fc8f0', 0.4, emit=0.6)
SLATE = kit.mat('#1d1d24', 0.5)
CHALK = kit.mat('#f2f2ea', 0.7)
STRIPE_W = kit.mat('#f7f7f2', 0.4)
STRIPE_B = kit.mat('#16161b', 0.4)
HINGE = kit.mat('#a7adb8', 0.3, metal=1.0)
BUCKET_R = kit.mat('#e0262f', 0.45)
BUCKET_W = kit.mat('#fbf6ec', 0.45)
POP = kit.mat('#fff2d2', 0.75)
POP_B = kit.mat('#ffd166', 0.6)
POP_K = kit.mat('#e5a64a', 0.6)
HOUSING = kit.mat('#2b2a35', 0.4)
HOUSING_RIM = kit.mat('#d7dbe3', 0.3, metal=0.9)
GAUGE = [kit.mat(c, 0.4, emit=0.35) for c in ('#e63946', '#f4743b', '#ffd23f', '#9bdc4a', '#2ecc71')]
NEEDLE = kit.mat('#ffffff', 0.3)
THUMB = kit.mat('#3ccf6e', 0.35)
CUFF = kit.mat('#f5f5f0', 0.5)
STAR = kit.mat('#ffc83d', 0.25, metal=0.6)


# ── helpers ──────────────────────────────────────────────────────────────

def objs():
    return set(o for o in bpy.context.scene.objects if o.type == 'MESH')


def transform(objects, M):
    bpy.context.view_layer.update()
    for o in objects:
        o.matrix_world = M @ o.matrix_world


def _mesh_obj(bm, mats, name):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        me.materials.append(m)
    return obj


def rrect_outline(w, h, r, segs=6):
    r = max(1e-4, min(r, w / 2 - 1e-4, h / 2 - 1e-4))
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def prism(pts, t, m, M, bevel=0.0, smooth_sides=True, name='prism'):
    """Extrude a 2D outline (local XY, CCW) by thickness t along local Z, placed by matrix M."""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, -t / 2)) for x, y in pts]
    top = [bm.verts.new((x, y, t / 2)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    for f in bm.faces:
        f.smooth = smooth_sides
    for e in bm.edges:
        if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6:
            e.smooth = False
    obj = _mesh_obj(bm, m, name)
    obj.matrix_world = M
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    return obj


def slab(w, h, t, r, m, M, bevel=0.0, segs=6):
    return prism(rrect_outline(w, h, r, segs), t, m, M, bevel)


FACE = Matrix.Rotation(math.pi / 2, 4, 'X')   # local +Z -> -Y (faces the viewer), local +Y -> +Z


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def flat(x, y, z, w, d, r, t, m, bevel=0.0):
    return slab(w, d, t, r, m, T(x, y, z), bevel)


def lathe(profile, mats, face_mat=None, segs=40, name='lathe', smooth=True):
    """Surface of revolution around Z. face_mat(ring_index, seg_index) -> material index."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z))
                          for k in range(segs)])
    for i, (A, B) in enumerate(zip(rings, rings[1:])):
        for k in range(segs):
            k2 = (k + 1) % segs
            if len(A) == 1:
                f = bm.faces.new((A[0], B[k], B[k2]))
            elif len(B) == 1:
                f = bm.faces.new((A[k], A[k2], B[0]))
            else:
                f = bm.faces.new((A[k], A[k2], B[k2], B[k]))
            f.smooth = smooth
            f.material_index = face_mat(i, k) if face_mat else 0
    return _mesh_obj(bm, mats, name)


def apply_boolean(target, cutters):
    for c in cutters:
        mod = target.modifiers.new('cut', 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = c
        mod.solver = 'EXACT'
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    for mod in list(target.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)


def star3d(r_out, r_in, depth, m, M, points=5):
    """Puffy faceted star: a ring of points with a raised apex on both faces."""
    bm = bmesh.new()
    ring = []
    for i in range(points * 2):
        a = math.pi / 2 + i * math.pi / points
        r = r_out if i % 2 == 0 else r_in
        ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0)))
    front, back = bm.verts.new((0, 0, depth)), bm.verts.new((0, 0, -depth))
    n = len(ring)
    for i in range(n):
        bm.faces.new((ring[i], ring[(i + 1) % n], front))
        bm.faces.new((ring[(i + 1) % n], ring[i], back))
    obj = _mesh_obj(bm, m, 'star')
    obj.matrix_world = M
    return obj


# ── base plate ───────────────────────────────────────────────────────────
BW, BD = 0.9, 0.78
flat(0, 0, 0.0125, BW + 0.03, BD + 0.03, 0.15, 0.025, BASE_TRIM, bevel=0.008)
flat(0, 0, 0.05, BW, BD, 0.13, 0.05, BASE_TOP, bevel=0.012)
flat(0, 0, 0.078, BW - 0.06, BD - 0.06, 0.11, 0.006, VELVET, bevel=0.002)
TOP = 0.081
slab(0.22, 0.032, 0.008, 0.008, GOLD, T(0, -BD / 2 - 0.003, 0.05) @ FACE, bevel=0.002)
for sx in (-1, 1):
    kit.sphere((sx * 0.095, -BD / 2 - 0.008, 0.05), 0.006, GOLD, segs=8, rings=4)

# ── film reel standing on its edge ──────────────────────────────────────
RR = 0.26                         # flange radius
RX, RY, RZ_ROT = -0.13, 0.13, math.radians(20)
RC = Vector((RX, RY, TOP + 0.022 + RR))
before = objs()
GAP = 0.034                       # half distance between flanges
for sy in (-1, 1):
    fl = kit.cylinder((0, sy * GAP, 0), RR, 0.012, REEL, rot=(math.pi / 2, 0, 0), verts=64, smooth=False)
    cutters = []
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        cutters.append(kit.cylinder((math.cos(a) * 0.15, sy * GAP, math.sin(a) * 0.15), 0.068, 0.05, None,
                                    rot=(math.pi / 2, 0, 0), verts=32))
    apply_boolean(fl, cutters)
    kit.torus((0, sy * GAP, 0), RR, 0.009, REEL_DK, rot=(math.pi / 2, 0, 0), major_segs=64, minor_segs=8)
    kit.torus((0, sy * (GAP + 0.006), 0), 0.075, 0.006, REEL, rot=(math.pi / 2, 0, 0), major_segs=32, minor_segs=6)
    for k in range(6):          # rivets on the spokes
        a = k * math.pi / 3
        kit.sphere((math.cos(a) * 0.1, sy * (GAP + 0.007), math.sin(a) * 0.1), 0.008, REEL_DK, segs=8, rings=4)
kit.cylinder((0, 0, 0), 0.205, 2 * GAP - 0.012, FILM_ROLL, rot=(math.pi / 2, 0, 0), verts=64, smooth=False)
for r in (0.12, 0.165):         # wound-layer rings visible through the holes
    for sy in (-1, 1):
        kit.torus((0, sy * (GAP - 0.006), 0), r, 0.0025, kit.mat('#5a4434', 0.3), rot=(math.pi / 2, 0, 0),
                  major_segs=48, minor_segs=4)
kit.cylinder((0, 0, 0), 0.05, 2 * GAP + 0.04, REEL_DK, rot=(math.pi / 2, 0, 0), verts=32)
for sy in (-1, 1):
    kit.cylinder((0, sy * (GAP + 0.021), 0), 0.03, 0.004, kit.mat('#2a2a30', 0.4), rot=(math.pi / 2, 0, 0), verts=4)
REEL_M = T(*RC) @ Matrix.Rotation(RZ_ROT, 4, 'Z')
transform(objs() - before, REEL_M)
# cradle chocks under the reel
for s in (-1, 1):
    p = REEL_M @ Vector((s * 0.13, 0, -RR + 0.02))
    kit.box((p.x, p.y, TOP + 0.03), (0.07, 0.13, 0.06), kit.mat('#3a2a26', 0.6), rot=(0, 0, RZ_ROT), bevel=0.012)

# ── film strip unspooling from the reel across the base ─────────────────
U = Vector((math.cos(RZ_ROT), math.sin(RZ_ROT), 0))
Zv = Vector((0, 0, 1))
FT = 0.004
GZ = TOP + FT / 2 + 0.001
ctrl = [RC - Zv * 0.205 - U * 0.03, RC - Zv * 0.215 + U * 0.08, RC - Zv * (RC.z - GZ - 0.01) + U * 0.2,
        Vector((0.12, -0.04, GZ)), Vector((0.06, -0.17, GZ)), Vector((-0.06, -0.25, GZ)), Vector((-0.15, -0.33, GZ)),
        Vector((-0.17, -0.375, GZ - 0.004)), Vector((-0.175, -0.405, GZ - 0.03)), Vector((-0.17, -0.418, 0.0))]


def catmull(points, n_per=24):
    pts = [points[0]] + points + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n_per):
            t = k / n_per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(points[-1])
    return out


def resample(poly, step):
    out = [poly[0]]
    acc = 0.0
    for a, b in zip(poly, poly[1:]):
        seg = (b - a).length
        while acc + seg >= step:
            t = (step - acc) / seg
            a = a.lerp(b, t)
            out.append(a)
            seg = (b - a).length
            acc = 0.0
        acc += seg
    return out


path = resample(catmull(ctrl), 0.012)
FW = 0.07
cols = [-0.5, -0.38, -0.27, 0.27, 0.38, 0.5]
bm = bmesh.new()
top_rows, bot_rows = [], []
for i, p in enumerate(path):
    tng = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
    wv = tng.cross(Zv).normalized()
    nv = wv.cross(tng).normalized()
    if nv.z < 0:
        nv = -nv
    top_rows.append([bm.verts.new(p + wv * c * FW + nv * FT / 2) for c in cols])
    bot_rows.append([bm.verts.new(p + wv * c * FW - nv * FT / 2) for c in cols])
nC = len(cols)
for i in range(len(path) - 1):
    for j in range(nC - 1):
        f = bm.faces.new((top_rows[i][j], top_rows[i][j + 1], top_rows[i + 1][j + 1], top_rows[i + 1][j]))
        if j in (1, 3):
            f.material_index = 1 if i % 2 == 0 else 0
        elif j == 2:
            f.material_index = 0 if i % 6 == 5 else (2 if (i // 6) % 3 else 3)
        bm.faces.new((bot_rows[i][j + 1], bot_rows[i][j], bot_rows[i + 1][j], bot_rows[i + 1][j + 1]))
    for j in (0, nC - 1):
        bm.faces.new((top_rows[i][j], bot_rows[i][j], bot_rows[i + 1][j], top_rows[i + 1][j]))
for i in (0, len(path) - 1):
    for j in range(nC - 1):
        bm.faces.new((top_rows[i][j], top_rows[i][j + 1], bot_rows[i][j + 1], bot_rows[i][j]))
_mesh_obj(bm, [FILM, SPROCKET, FRAME_LIT, FRAME_LIT2], 'film')

# ── popcorn bucket (back right) ─────────────────────────────────────────
PX, PY = 0.3, 0.17
H_B = 0.24
prof = [(0.0, 0.0), (0.07, 0.0), (0.072, 0.008), (0.112, H_B), (0.104, H_B), (0.07, 0.015), (0.0, 0.015)]
bucket = lathe(prof, [BUCKET_R, BUCKET_W], face_mat=lambda i, k: (k // 3) % 2 if i == 2 else 1, segs=48,
               name='bucket', smooth=False)
bucket.location = (PX, PY, TOP)
kit.torus((PX, PY, TOP + H_B), 0.11, 0.008, BUCKET_W, major_segs=48, minor_segs=8)
kit.torus((PX, PY, TOP + 0.01), 0.072, 0.007, BUCKET_W, major_segs=40, minor_segs=6)
slab(0.07, 0.07, 0.004, 0.035, kit.mat('#ffd23f', 0.4), T(PX - 0.035, PY - 0.098, TOP + 0.13)
     @ Matrix.Rotation(-math.radians(20), 4, 'Z') @ Matrix.Rotation(-0.17, 4, 'Y') @ FACE)   # round label
star3d(0.026, 0.011, 0.006, kit.mat('#e0262f', 0.4), T(PX - 0.037, PY - 0.104, TOP + 0.13)
       @ Matrix.Rotation(-math.radians(20), 4, 'Z') @ Matrix.Rotation(-0.17, 4, 'Y') @ FACE)


def kernel(c, s=1.0):
    c = Vector(c)
    m = POP_B if random.random() < 0.3 else POP
    for _ in range(3):
        off = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.5, 1))) * 0.012 * s
        kit.sphere(c + off, random.uniform(0.016, 0.022) * s, m, segs=8, rings=5)
    kit.sphere(c + Vector((0, 0, -0.008 * s)), 0.008 * s, POP_K, segs=8, rings=4)


kit.sphere((PX, PY, TOP + H_B + 0.005), (0.1, 0.1, 0.04), POP, segs=24, rings=8)
for _ in range(34):
    a = random.uniform(0, 2 * math.pi)
    rr = math.sqrt(random.random()) * 0.1
    dz = 0.07 * math.sqrt(max(0.0, 1 - (rr / 0.11) ** 2))
    kernel((PX + math.cos(a) * rr, PY + math.sin(a) * rr, TOP + H_B + 0.01 + dz))
for (x, y) in ((0.17, 0.1), (0.21, 0.02), (0.38, 0.03), (0.12, 0.22)):
    kernel((x, y, TOP + 0.016), 0.85)

# ── clapperboard (front right) ──────────────────────────────────────────
before = objs()
CWd, CH = 0.25, 0.17
slab(CWd, CH, 0.018, 0.012, SLATE, T(0, 0, CH / 2) @ FACE, bevel=0.003)
for z in (0.045, 0.085, 0.125):                     # chalk ruled lines + columns
    kit.box((0, -0.011, z), (CWd - 0.04, 0.003, 0.004), CHALK)
for x in (-0.04, 0.05):
    kit.box((x, -0.011, 0.065), (0.004, 0.003, 0.08), CHALK)
for (x, z, w) in ((-0.08, 0.145, 0.05), (0.03, 0.145, 0.07), (-0.075, 0.105, 0.04), (0.0, 0.065, 0.03),
                  (0.085, 0.065, 0.03), (-0.08, 0.025, 0.06)):
    kit.box((x, -0.011, z), (w, 0.003, 0.008), kit.mat('#c9c9c0', 0.7))


def striped_bar(L, h, t, n, M):
    """Clapper stick: alternating black/white slanted stripes; local x in [0, L], z in [0, h]."""
    step = L / n
    s = h * 0.9
    for i in range(-1, n + 1):
        a, b = i * step, (i + 1) * step
        cl = lambda v: min(max(v, 0.0), L)
        poly = [(cl(a), 0), (cl(b), 0), (cl(b + s), h), (cl(a + s), h)]
        ded = []
        for p in poly:
            if not ded or (abs(ded[-1][0] - p[0]) > 1e-6 or abs(ded[-1][1] - p[1]) > 1e-6):
                ded.append(p)
        if len(ded) > 1 and abs(ded[0][0] - ded[-1][0]) < 1e-6 and abs(ded[0][1] - ded[-1][1]) < 1e-6:
            ded.pop()
        if len(ded) < 3:
            continue
        prism(ded, t, STRIPE_W if i % 2 == 0 else STRIPE_B, M @ FACE, smooth_sides=False)


SH = 0.036
striped_bar(CWd, SH, 0.02, 6, T(-CWd / 2, 0, CH))
ang = math.radians(28)
striped_bar(CWd, SH, 0.02, 6, T(-CWd / 2, -0.002, CH + SH + 0.003) @ Matrix.Rotation(-ang, 4, 'Y'))
kit.cylinder((-CWd / 2 + 0.012, -0.016, CH + SH), 0.01, 0.012, HINGE, rot=(math.pi / 2, 0, 0), verts=16)
kit.cylinder((-CWd / 2 + 0.012, 0.016, CH + SH), 0.01, 0.012, HINGE, rot=(math.pi / 2, 0, 0), verts=16)
transform(objs() - before, T(0.24, -0.2, TOP) @ Matrix.Rotation(math.radians(-28), 4, 'Z')
          @ Matrix.Rotation(math.radians(-8), 4, 'X'))

# ── sentiment meter gauge (front left) ──────────────────────────────────
before = objs()
GR = 0.13
outline = [(GR * math.cos(math.pi * i / 32), GR * math.sin(math.pi * i / 32)) for i in range(33)]
outline += [(-GR, -0.03), (GR, -0.03)]
prism(outline, 0.04, HOUSING, T(0, 0, 0.03) @ FACE, bevel=0.008)
kit.tube([(GR * math.cos(math.pi * i / 32), -0.02, 0.03 + GR * math.sin(math.pi * i / 32)) for i in range(33)],
         0.007, HOUSING_RIM, resolution=2, name='rim')


def sector(r_in, r_out, a0, a1, m, y, segs=8):
    pts = [(r_out * math.cos(a0 + (a1 - a0) * i / segs), r_out * math.sin(a0 + (a1 - a0) * i / segs)) for i in range(segs + 1)]
    pts += [(r_in * math.cos(a1 + (a0 - a1) * i / segs), r_in * math.sin(a1 + (a0 - a1) * i / segs)) for i in range(segs + 1)]
    return prism(pts, 0.006, m, T(0, y, 0.03) @ FACE, smooth_sides=False)


for k in range(5):
    a0 = math.pi - k * math.pi / 5 - 0.02
    a1 = math.pi - (k + 1) * math.pi / 5 + 0.02
    sector(0.072, 0.108, a1, a0, GAUGE[k], -0.022)
for k in range(11):          # ticks
    a = math.pi * k / 10
    p = Vector((math.cos(a) * 0.064, -0.022, 0.03 + math.sin(a) * 0.064))
    kit.box(p, (0.004, 0.006, 0.014 if k % 5 == 0 else 0.009), CHALK, rot=(0, -(a - math.pi / 2), 0))
na = math.radians(32)        # needle pointing into the green
tip = Vector((math.cos(na) * 0.1, -0.03, 0.03 + math.sin(na) * 0.1))
kit.spike((0, -0.03, 0.03), tip, 0.008, NEEDLE, verts=12)
kit.cylinder((0, -0.03, 0.03), 0.018, 0.012, GOLD, rot=(math.pi / 2, 0, 0), verts=24)
kit.sphere((0, -0.037, 0.03), 0.008, kit.mat('#e63946', 0.3), segs=10, rings=5)
# tiny sad / happy face markers at the ends
kit.sphere((-0.1, -0.022, 0.008), 0.012, GAUGE[0], segs=12, rings=6)
kit.sphere((0.1, -0.022, 0.008), 0.012, GAUGE[4], segs=12, rings=6)
transform(objs() - before, T(-0.26, -0.21, TOP + 0.026) @ Matrix.Rotation(math.radians(15), 4, 'Z')
          @ Matrix.Rotation(math.radians(-10), 4, 'X'))
flat(-0.26, -0.2, TOP + 0.013, 0.3, 0.12, 0.03, 0.026, HOUSING, bevel=0.006)    # pedestal

# ── floating thumbs-up and stars ────────────────────────────────────────
before = objs()
kit.box((0.01, 0, -0.005), (0.11, 0.075, 0.11), THUMB, bevel=0.035)              # fist
for k in range(4):                                                               # curled fingers (knuckle rolls)
    kit.sphere((-0.045, -0.004, 0.032 - k * 0.026), (0.03, 0.036, 0.0145), THUMB, segs=16, rings=8)
kit.rod((-0.015, 0, 0.04), (-0.022, 0, 0.1), 0.026, THUMB, verts=20)               # thumb
kit.box((0.072, 0, -0.008), (0.03, 0.085, 0.125), CUFF, bevel=0.01)                 # sleeve cuff
kit.box((0.09, 0, -0.008), (0.012, 0.07, 0.1), kit.mat('#2a7fd4', 0.5), bevel=0.004)  # sleeve
transform(objs() - before, T(0.2, -0.06, 0.66) @ Matrix.Rotation(math.radians(20), 4, 'Z')
          @ Matrix.Rotation(math.radians(-10), 4, 'Y'))

star3d(0.065, 0.028, 0.02, STAR, T(0.41, 0.06, 0.57) @ Matrix.Rotation(math.radians(20), 4, 'Z')
       @ Matrix.Rotation(math.radians(-12), 4, 'Y') @ FACE)
star3d(0.05, 0.022, 0.017, STAR, T(-0.4, -0.06, 0.6) @ Matrix.Rotation(math.radians(25), 4, 'Z')
       @ Matrix.Rotation(math.radians(15), 4, 'Y') @ FACE)
star3d(0.035, 0.015, 0.012, STAR, T(0.05, -0.1, 0.76) @ Matrix.Rotation(math.radians(15), 4, 'Z') @ FACE)

kit.finalize_prop('imdb_reel')
