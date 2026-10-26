"""BuildVerse hackathon diorama: an open, sticker-covered laptop with glowing code on screen, a lanyard badge draped
over the lid, sticky notes, an energy-drink can, a steaming coffee mug and a little rocket toy — on a cutting-mat
desk base plate."""
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
random.seed(42)

# ── palette ──────────────────────────────────────────────────────────────
BASE_TOP = kit.mat('#f2efe8', 0.6)
BASE_MAT = kit.mat('#24406e', 0.8)
GRID = kit.mat('#7d9ccc', 0.8)
BASE_TRIM = kit.mat('#1b1b26', 0.45)
GOLD = kit.mat('#e2b64a', 0.3, metal=0.9)
ALU = kit.mat('#a3a9b4', 0.3, metal=0.85)
ALU_DK = kit.mat('#70767f', 0.35, metal=0.85)
KEY = kit.mat('#24262d', 0.5)
KEY_WELL = kit.mat('#3a3d45', 0.6)
BEZEL = kit.mat('#121318', 0.2)
SCREEN = kit.mat('#23263a', 0.4, emit=0.9)
SYNTAX = [kit.mat(c, 0.4, emit=1.8) for c in ('#ff79c6', '#8be9fd', '#f1fa8c', '#50fa7b', '#bd93f9', '#ffb86c')]
GUTTER = kit.mat('#5b6078', 0.5, emit=0.6)
TABBAR = kit.mat('#2a2d40', 0.4, emit=0.6)
TAB = kit.mat('#3d4260', 0.4, emit=0.8)
CURSOR = kit.mat('#ffffff', 0.4, emit=1.5)
STICKERS = [kit.mat(c, 0.45) for c in ('#ff5d8f', '#ffbe0b', '#3a86ff', '#06d6a0', '#ff7b00', '#8338ec', '#f8f9fa',
                                       '#ef233c')]
WHITE = kit.mat('#fbfbfb', 0.4)
INK = kit.mat('#1a1a22', 0.5)
RIBBON = kit.mat('#ff3d7f', 0.55)
RIBBON2 = kit.mat('#ffd23f', 0.55)
CLIP = kit.mat('#c7cbd3', 0.25, metal=1.0)
BADGE_HEAD = kit.mat('#7b2ff7', 0.45)
BADGE_FOOT = kit.mat('#ff7b00', 0.45)
PHOTO = kit.mat('#9cc3e6', 0.5)
SKIN = kit.mat('#e7b48a', 0.5)
NOTE_Y = kit.mat('#ffe45c', 0.75)
NOTE_P = kit.mat('#ff8fb8', 0.75)
NOTE_C = kit.mat('#7fe0f5', 0.75)
NOTE_INK = kit.mat('#4a4a5a', 0.7)
CAN = kit.mat('#1f6fff', 0.25, metal=0.6)
CAN_TOP = kit.mat('#d5d9e0', 0.25, metal=1.0)
BOLT = kit.mat('#d4ff3a', 0.35, emit=0.3)
MUG = kit.mat('#ff6b4a', 0.3)
COFFEE = kit.mat('#4a2a18', 0.15)
STEAM = kit.mat('#ffffff', 0.6)
ROCKET = kit.mat('#f6f6f2', 0.35)
ROCKET_RED = kit.mat('#ef233c', 0.35)
WINDOW = kit.mat('#4cc9f0', 0.1, emit=0.4)
NOZZLE = kit.mat('#5c6270', 0.3, metal=0.8)
SMOKE = kit.mat('#eef0f4', 0.8)
RUBBER = kit.mat('#1a1a1e', 0.8)


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
    """Extrude a 2D outline (local XY) by thickness t along local Z, placed by matrix M."""
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


def ngon(r, n, rot=0.0):
    return [(r * math.cos(rot + 2 * math.pi * i / n), r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def star_pts(ro, ri, n=5):
    return [((ro if i % 2 == 0 else ri) * math.cos(math.pi / 2 + i * math.pi / n),
             (ro if i % 2 == 0 else ri) * math.sin(math.pi / 2 + i * math.pi / n)) for i in range(2 * n)]


def heart_pts(s, n=28):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * s / 17, y * s / 17))
    return pts


BOLT_PTS = [(0.2, 1.0), (-0.45, -0.05), (-0.02, -0.05), (-0.25, -1.0), (0.45, 0.15), (0.03, 0.15)]

FACE = Matrix.Rotation(math.pi / 2, 4, 'X')   # local +Z -> -Y (faces the viewer), local +Y -> +Z
BACK = Matrix.Rotation(-math.pi / 2, 4, 'X') @ Matrix.Rotation(math.pi, 4, 'Z')  # local +Z -> +Y, reads from behind


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def RZ(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def RX(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def RY(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


def flat(x, y, z, w, d, r, t, m, bevel=0.0):
    return slab(w, d, t, r, m, T(x, y, z), bevel)


def lathe(profile, mats, face_mat=None, segs=40, name='lathe'):
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
            f.smooth = True
            f.material_index = face_mat(i, k) if face_mat else 0
    return _mesh_obj(bm, mats, name)


def sticker(shape, size, m, M, t=0.0022):
    """Flat vinyl sticker with a white die-cut border. M places it; local +Z is the sticker's outward normal."""
    if shape == 'hex':
        pts = ngon(size, 6, math.pi / 6)
    elif shape == 'circle':
        pts = ngon(size, 24)
    elif shape == 'star':
        pts = star_pts(size, size * 0.45)
    elif shape == 'heart':
        pts = heart_pts(size)
    elif shape == 'bolt':
        pts = [(x * size * 0.6, y * size) for x, y in BOLT_PTS]
    else:
        pts = rrect_outline(size * 1.8, size * 1.1, size * 0.3)
    border = [(x * 1.0 + (0.004 if x > 0 else -0.004), y + (0.004 if y > 0 else -0.004)) for x, y in pts] \
        if shape in ('rect', 'hex') else [(x * (1 + 0.006 / size), y * (1 + 0.006 / size)) for x, y in pts]
    prism(border, t, STICKERS[6], M, smooth_sides=False)
    prism(pts, t, m, M @ T(0, 0, t * 0.5), smooth_sides=False)


# ── base plate (navy cutting mat) ───────────────────────────────────────
BW, BD = 0.9, 0.78
flat(0, 0, 0.0125, BW + 0.03, BD + 0.03, 0.15, 0.025, BASE_TRIM, bevel=0.008)
flat(0, 0, 0.05, BW, BD, 0.13, 0.05, BASE_TOP, bevel=0.012)
flat(0, 0, 0.078, BW - 0.06, BD - 0.06, 0.11, 0.006, BASE_MAT, bevel=0.002)
TOP = 0.081


def grid_breaks(half, n, step):
    xs = [-half]
    for k in range(-n, n + 1):
        c = k * step
        lw = 0.0045 if k % 5 == 0 else 0.0025
        xs += [c - lw / 2, c + lw / 2]
    xs.append(half)
    return xs


# printed cutting-mat grid: one plane whose stripes are material faces (no extra outlines)
xs, ys = grid_breaks(0.38, 6, 0.06), grid_breaks(0.32, 5, 0.06)
bm = bmesh.new()
vg = [[bm.verts.new((x, y, TOP + 0.0006)) for x in xs] for y in ys]
for j in range(len(ys) - 1):
    for i in range(len(xs) - 1):
        f = bm.faces.new((vg[j][i], vg[j][i + 1], vg[j + 1][i + 1], vg[j + 1][i]))
        f.material_index = 1 if (i % 2 == 1 or j % 2 == 1) else 0
me = bpy.data.meshes.new('grid')
bm.to_mesh(me)
bm.free()
grid = bpy.data.objects.new('grid', me)
bpy.context.scene.collection.objects.link(grid)
me.materials.append(BASE_MAT)
me.materials.append(GRID)
slab(0.22, 0.032, 0.008, 0.008, GOLD, T(0, -BD / 2 - 0.003, 0.05) @ FACE, bevel=0.002)
for sx in (-1, 1):
    kit.sphere((sx * 0.095, -BD / 2 - 0.008, 0.05), 0.006, GOLD, segs=8, rings=4)

# ── laptop (built in its own frame, deck centred at origin, screen facing -Y) ──
before_laptop = objs()
LW, LD, LT = 0.46, 0.32, 0.02
slab(LW, LD, LT, 0.02, ALU, T(0, 0, LT / 2 + 0.006), bevel=0.005)
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cylinder((sx * 0.19, sy * 0.13, 0.004), 0.012, 0.008, RUBBER, verts=12)
DZ = LT + 0.006
# keyboard
slab(0.41, 0.15, 0.002, 0.008, KEY_WELL, T(0, 0.055, DZ + 0.0005))
kw = 0.0265
for r in range(5):
    y = 0.115 - r * 0.029
    n = 13
    for c in range(n):
        x = -0.18 + c * 0.03
        kit.box((x, y, DZ + 0.003), (kw, 0.024, 0.005), KEY)
kit.box((0, -0.006, DZ + 0.003), (0.16, 0.022, 0.005), KEY)                           # space bar
for x in (-0.15, -0.11, 0.11, 0.15):
    kit.box((x, -0.006, DZ + 0.003), (0.034, 0.022, 0.005), KEY)
slab(0.15, 0.085, 0.0015, 0.008, ALU_DK, T(0, -0.09, DZ + 0.0002))                    # trackpad
kit.box((0, -LD / 2 + 0.002, DZ - 0.004), (0.06, 0.004, 0.006), ALU_DK)               # lid notch
# palm-rest stickers
for (shape, size, mi, x, y, rz) in (('hex', 0.026, 4, -0.165, -0.095, 10), ('circle', 0.02, 2, -0.115, -0.12, 0),
                                    ('star', 0.026, 1, 0.12, -0.1, -12), ('heart', 0.02, 0, 0.17, -0.12, 15),
                                    ('rect', 0.017, 5, 0.165, -0.065, -8)):
    sticker(shape, size, STICKERS[mi], T(x, y, DZ + 0.0012) @ RZ(rz))

# lid (built upright at the hinge, then opened back)
before_lid = objs()
LH = 0.31
HY, HZ = LD / 2 - 0.006, DZ
slab(LW, LH, 0.012, 0.02, ALU, T(0, 0, LH / 2) @ FACE, bevel=0.004)
slab(LW - 0.01, LH - 0.01, 0.002, 0.016, BEZEL, T(0, -0.0065, LH / 2) @ FACE)
SY = -0.008
slab(0.42, 0.262, 0.002, 0.006, SCREEN, T(0, SY, LH / 2 + 0.006) @ FACE)
kit.sphere((0, -0.0075, LH - 0.008), 0.003, KEY, segs=8, rings=4)                     # webcam
UY = SY - 0.0015
# editor chrome: tab bar + tabs + gutter + code lines + cursor
TZ = LH / 2 + 0.006 + 0.131 - 0.011
kit.box((0, UY, TZ), (0.42, 0.002, 0.02), TABBAR)
for k, w in enumerate((0.08, 0.07, 0.09)):
    kit.box((-0.16 + k * 0.09 + (w - 0.08) / 2, UY - 0.001, TZ - 0.001), (w, 0.002, 0.016), TAB if k == 0 else TABBAR)
    kit.box((-0.17 + k * 0.09, UY - 0.002, TZ - 0.001), (0.035, 0.002, 0.005), SYNTAX[k + 1])
code = [(0, [(0, 0.04), (4, 0.06)]), (0, [(0, 0.05), (1, 0.09), (3, 0.03)]), (1, [(4, 0.04), (5, 0.08), (2, 0.06)]),
        (2, [(0, 0.03), (1, 0.12)]), (2, [(3, 0.05), (2, 0.1), (5, 0.03)]), (3, [(4, 0.07), (1, 0.05)]),
        (2, [(0, 0.04)]), (1, [(0, 0.03), (3, 0.06), (2, 0.08)]), (0, [(4, 0.02)]), (0, []),
        (0, [(0, 0.06), (1, 0.07), (5, 0.04)]), (1, [(3, 0.11), (2, 0.05)]), (1, [(4, 0.05), (1, 0.06)])]
z0 = TZ - 0.024
for li, (indent, toks) in enumerate(code):
    z = z0 - li * 0.0172
    kit.box((-0.193, UY, z), (0.012 if li >= 9 else 0.007, 0.002, 0.006), GUTTER)
    x = -0.17 + indent * 0.022
    for (ci, w) in toks:
        kit.box((x + w / 2, UY, z), (w, 0.002, 0.0095), SYNTAX[ci])
        x += w + 0.008
    if li == 12:
        kit.box((x + 0.004, UY - 0.001, z), (0.004, 0.002, 0.013), CURSOR)
kit.box((0, UY, LH / 2 + 0.006 - 0.131 + 0.007), (0.42, 0.002, 0.012), kit.mat('#7b2ff7', 0.4, emit=1.0))   # status bar
# sticky notes on the left bezel
for (x, z, m, rz) in ((-0.205, 0.255, NOTE_Y, 8), (-0.215, 0.18, NOTE_P, -6)):
    M = T(x, -0.0095, z) @ RY(rz) @ FACE
    prism(rrect_outline(0.06, 0.06, 0.002), 0.0015, m, M, smooth_sides=False)
    for k in range(3):
        kit.box(M @ Vector((0.0 - (0.006 if k == 2 else 0), 0.014 - k * 0.012, 0.001)),
                (0.04 if k < 2 else 0.028, 0.0012, 0.0025), NOTE_INK, rot=(0, math.radians(rz), 0))
# lid-back stickers
for (shape, size, mi, x, z, rz) in (('hex', 0.04, 1, -0.14, 0.22, 10), ('circle', 0.035, 3, -0.04, 0.24, 0),
                                    ('star', 0.04, 0, 0.08, 0.23, -12), ('rect', 0.03, 2, 0.16, 0.24, 6),
                                    ('heart', 0.03, 7, -0.16, 0.1, 0), ('bolt', 0.05, 4, -0.07, 0.1, -15),
                                    ('hex', 0.034, 5, 0.03, 0.12, 0), ('circle', 0.028, 1, 0.12, 0.09, 0),
                                    ('rect', 0.026, 0, 0.1, 0.16, -20), ('star', 0.026, 3, -0.11, 0.16, 20),
                                    ('circle', 0.02, 6, 0.18, 0.15, 0), ('hex', 0.025, 7, 0.17, 0.06, 0)):
    sticker(shape, size, STICKERS[mi], T(x, 0.0062, z) @ RY(rz) @ BACK)
# "</>" decal on the big circle sticker
for pts in (((-0.012, 0.008), (-0.022, 0.0), (-0.012, -0.008)), ((0.012, 0.008), (0.022, 0.0), (0.012, -0.008)),
            ((0.005, 0.012), (-0.005, -0.012))):
    kit.tube([(-0.04 - px, 0.0105, 0.24 + pz) for px, pz in pts], 0.0022, WHITE, smooth_path=False, resolution=1,
             name='code_icon')

# lanyard loop draped over the lid's top-right corner + badge resting against the screen
lan = [Vector(p) for p in ((0.185, -0.03, 0.12), (0.15, -0.02, 0.24), (0.125, -0.012, LH - 0.006), (0.125, 0.0, LH + 0.008),
                            (0.13, 0.012, LH - 0.01), (0.15, 0.016, 0.24), (0.175, 0.017, 0.215), (0.2, 0.016, 0.24),
                            (0.212, 0.012, LH - 0.01), (0.212, 0.0, LH + 0.008), (0.212, -0.012, LH - 0.006),
                            (0.205, -0.02, 0.24), (0.19, -0.03, 0.12))]


def catmull(points, n_per=10):
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


path = catmull(lan)
RWd, RT = 0.016, 0.0025
bm = bmesh.new()
rows = []
for i, p in enumerate(path):
    tng = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
    nrm = Vector((0, p.y, max(0.0, p.z - (LH - 0.012)) * 4))
    nrm = nrm.normalized() if nrm.length > 1e-6 else Vector((0, -1, 0))
    wv = nrm.cross(tng).normalized()
    nrm = tng.cross(wv).normalized() if tng.cross(wv).dot(nrm) > 0 else -tng.cross(wv).normalized()
    rows.append([bm.verts.new(p + wv * a * RWd / 2 + nrm * b * RT / 2) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
for i in range(len(rows) - 1):
    for j in range(4):
        f = bm.faces.new((rows[i][j], rows[i][(j + 1) % 4], rows[i + 1][(j + 1) % 4], rows[i + 1][j]))
        f.material_index = 1 if (i // 3) % 4 == 3 else 0
bm.faces.new(rows[0])
bm.faces.new(list(reversed(rows[-1])))
_mesh_obj(bm, [RIBBON, RIBBON2], 'lanyard')
# clip + badge
kit.torus((0.188, -0.032, 0.115), 0.008, 0.002, CLIP, rot=(math.pi / 2, 0, 0), major_segs=16, minor_segs=4)
kit.box((0.188, -0.033, 0.1), (0.012, 0.004, 0.016), CLIP, bevel=0.002)
BM = T(0.188, -0.034, 0.05)
slab(0.085, 0.1, 0.004, 0.008, WHITE, BM @ FACE, bevel=0.0015)
slab(0.085, 0.024, 0.0015, 0.008, BADGE_HEAD, BM @ T(0, -0.0025, 0.038) @ FACE)
kit.box(BM @ Vector((0, -0.0035, 0.038)), (0.05, 0.0015, 0.007), WHITE)
slab(0.03, 0.034, 0.0015, 0.003, PHOTO, BM @ T(-0.02, -0.0025, 0.002) @ FACE)
kit.cylinder(BM @ Vector((-0.02, -0.0035, 0.006)), 0.008, 0.0015, SKIN, rot=(math.pi / 2, 0, 0), verts=16)
kit.box(BM @ Vector((-0.02, -0.0035, -0.01)), (0.022, 0.0015, 0.01), BADGE_HEAD)
for k, w in enumerate((0.03, 0.022, 0.026)):
    kit.box(BM @ Vector((0.022, -0.003, 0.012 - k * 0.011)), (w, 0.0015, 0.005), INK if k == 0 else NOTE_INK)
slab(0.085, 0.012, 0.0015, 0.004, BADGE_FOOT, BM @ T(0, -0.0025, -0.042) @ FACE)

transform(objs() - before_lid, T(0, HY, HZ) @ RX(-16))
kit.cylinder((0, HY + 0.004, HZ + 0.002), 0.008, 0.36, ALU_DK, rot=(0, math.pi / 2, 0), verts=12)   # hinge
transform(objs() - before_laptop, T(0.0, 0.0, TOP) @ RZ(14) @ Matrix.Scale(1.12, 4))

# ── energy drink can (back right) ───────────────────────────────────────
CX, CYy = 0.33, 0.2
can = lathe([(0.0, 0.0), (0.03, 0.0), (0.038, 0.008), (0.042, 0.02), (0.042, 0.135), (0.036, 0.15), (0.032, 0.155),
             (0.033, 0.158), (0.0, 0.156)], [CAN, CAN_TOP], face_mat=lambda i, k: 0 if 2 <= i <= 3 else 1, segs=32,
            name='can')
can.location = (CX, CYy, TOP)
kit.torus((CX, CYy, TOP + 0.04), 0.0425, 0.004, BOLT, major_segs=32, minor_segs=4)
kit.torus((CX, CYy, TOP + 0.115), 0.0425, 0.003, BOLT, major_segs=32, minor_segs=4)
prism([(x * 0.024, y * 0.032) for x, y in BOLT_PTS], 0.004, BOLT,
      T(CX, CYy, TOP + 0.078) @ RZ(28) @ T(0, -0.042, 0) @ FACE, smooth_sides=False)
kit.torus((CX + 0.008, CYy - 0.01, TOP + 0.158), 0.009, 0.0025, CAN_TOP, major_segs=12, minor_segs=4, scale=(1, 0.7, 1))

# ── coffee mug (front right) with steam ─────────────────────────────────
MX, MY = 0.33, -0.2
lathe([(0.0, 0.0), (0.045, 0.0), (0.05, 0.006), (0.052, 0.09), (0.05, 0.096), (0.044, 0.096), (0.044, 0.01),
       (0.0, 0.01)], [MUG], segs=36, name='mug').location = (MX, MY, TOP)
kit.cylinder((MX, MY, TOP + 0.08), 0.0445, 0.004, COFFEE, verts=32)
kit.torus((MX + 0.058, MY + 0.02, TOP + 0.05), 0.026, 0.008, MUG, rot=(math.pi / 2, 0, math.radians(20)),
          major_segs=24, minor_segs=8, scale=(0.9, 1.1, 1))
# "{ }" print on the mug, facing the camera
ang = math.radians(-70)
for sx in (-1, 1):
    pts = []
    for k in range(5):
        z = TOP + 0.026 + k * 0.0095
        a = ang + sx * (0.16, 0.2, 0.27, 0.2, 0.16)[k]
        pts.append((MX + math.cos(a) * 0.0535, MY + math.sin(a) * 0.0535, z))
    kit.tube(pts, 0.003, WHITE, resolution=3, name='brace')
for k, phase in enumerate((0.0, 2.0)):
    pts = [(MX - 0.012 + k * 0.024 + 0.01 * math.sin(phase + i * 1.4), MY + 0.004 * math.cos(i), TOP + 0.1 + i * 0.022)
           for i in range(5)]
    kit.tube(pts, 0.0065, STEAM, taper_to=0.25, resolution=6, name='steam')

# ── sticky note pad (front left) ───────────────────────────────────────
for k, m in enumerate((NOTE_C, NOTE_C, NOTE_Y, NOTE_Y, NOTE_Y)):
    slab(0.09, 0.09, 0.003, 0.003, m, T(-0.34, 0.24, TOP + 0.002 + k * 0.003) @ RZ(12 if k >= 3 else 3 * k))
for k in range(3):
    kit.box((-0.34 + 0.005 * k, 0.245 - k * 0.018 + 0.015, TOP + 0.0165), (0.06 - 0.012 * k, 0.003, 0.0015), NOTE_INK,
            rot=(0, 0, math.radians(12)))
# a pencil on the pad
pa, pb = Vector((-0.41, 0.18, TOP + 0.024)), Vector((-0.27, 0.3, TOP + 0.024))
kit.rod(pa, pb, 0.008, kit.mat('#ffbe0b', 0.5), verts=6, caps=False)
kit.cone(pb + (pb - pa).normalized() * 0.012, 0.008, 0.0, 0.024, kit.mat('#e8c99a', 0.6), rot=kit.rot_between(pa, pb),
         verts=12)
kit.rod(pa - (pb - pa).normalized() * 0.014, pa, 0.0082, kit.mat('#ff8fb8', 0.7), verts=12, caps=False)

# ── rocket toy (back left) blasting off a puff of smoke ─────────────────
RXp, RYp = -0.33, -0.21
for (dx, dy, r) in ((0.0, 0.0, 0.045), (0.04, 0.02, 0.032), (-0.04, 0.015, 0.034), (0.02, -0.04, 0.03),
                    (-0.025, -0.035, 0.028), (0.045, -0.015, 0.024), (-0.05, -0.01, 0.022)):
    kit.sphere((RXp + dx, RYp + dy, TOP + r * 0.6), r, SMOKE, segs=16, rings=8)
before = objs()
body = lathe([(0.0, 0.0), (0.026, 0.0), (0.032, 0.03), (0.034, 0.08), (0.03, 0.12), (0.0, 0.122)],
             [ROCKET], segs=32, name='rocket')
lathe([(0.0, 0.118), (0.031, 0.118), (0.026, 0.145), (0.016, 0.17), (0.0, 0.185)], [ROCKET_RED], segs=32, name='nose')
kit.cylinder((0, -0.03, 0.085), 0.015, 0.012, WINDOW, rot=(math.pi / 2, 0, 0), verts=20)
kit.torus((0, -0.033, 0.085), 0.016, 0.004, NOZZLE, rot=(math.pi / 2, 0, 0), major_segs=20, minor_segs=6)
kit.torus((0, 0, 0.04), 0.0335, 0.004, ROCKET_RED, major_segs=32, minor_segs=4)
for k in range(3):
    a = math.radians(90 + k * 120)
    fin = [(0.0, 0.0), (0.035, -0.02), (0.035, 0.005), (0.0, 0.06)]
    prism(fin, 0.006, ROCKET_RED, RZ(math.degrees(a)) @ T(0.026, 0, 0.0) @ Matrix.Rotation(math.pi / 2, 4, 'X'),
          smooth_sides=False)
kit.cone((0, 0, -0.012), 0.016, 0.024, 0.02, NOZZLE, verts=20)
kit.cone((0, 0, -0.04), 0.0, 0.018, 0.04, kit.mat('#ff9f1c', 0.4, emit=1.5), verts=16)
transform(objs() - before, T(RXp, RYp, TOP + 0.07) @ RZ(20) @ RY(-8))

kit.finalize_prop('hackathon_laptop')
