"""Light Up (real-time chat + video-call app) diorama: a glossy smartphone on a little stand with a glowing
chat UI (grey / violet speech bubbles, a video-call tile), 3D speech bubbles, a heart and a notification bell
floating out of the screen, and a warm glowing lightbulb beside it — on a rounded collectible base plate."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()

# ── palette ──────────────────────────────────────────────────────────────
BASE_TOP = kit.mat('#f4efe4', 0.6)
BASE_MAT = kit.mat('#34305e', 0.75)
BASE_TRIM = kit.mat('#2c2550', 0.45)
GOLD = kit.mat('#e2b64a', 0.3, metal=0.9)
FRAME = kit.mat('#6a4cf2', 0.28, metal=0.55)
GLASS = kit.mat('#0c0c14', 0.06)
SCREEN = kit.mat('#1a1d36', 0.4, emit=0.8)
ACCENT_E = kit.mat('#8a6cff', 0.3, emit=1.4)
GREY_E = kit.mat('#d9dce6', 0.3, emit=0.9)
WHITE_E = kit.mat('#ffffff', 0.3, emit=1.2)
TEXT_DK = kit.mat('#545a70', 0.5, emit=0.4)
TEXT_LT = kit.mat('#ece6ff', 0.5, emit=1.0)
TEAL_E = kit.mat('#3cc8b4', 0.4, emit=0.9)
SKIN_E = kit.mat('#f2c39a', 0.5, emit=0.6)
SHIRT_E = kit.mat('#ff7a59', 0.5, emit=0.8)
RED_E = kit.mat('#ff4d5e', 0.4, emit=1.0)
YELLOW_E = kit.mat('#ffd447', 0.4, emit=1.4)
STAND = kit.mat('#46406e', 0.35)
STAND_DK = kit.mat('#2c2850', 0.4)
LENS = kit.mat('#101018', 0.05, metal=0.3)
LENS_RING = kit.mat('#9a9aa6', 0.25, metal=1.0)
ACCENT = kit.mat('#7b5cff', 0.25)
BUBBLE_GREY = kit.mat('#e6e8ef', 0.3)
WHITE = kit.mat('#ffffff', 0.3)
HEART = kit.mat('#ff3d6e', 0.25)
BELL = kit.mat('#f5c242', 0.25, metal=0.8)
BADGE = kit.mat('#ff3b3b', 0.3)
BULB = kit.mat('#ffc21a', 0.18, emit=0.9)
BULB_CORE = kit.mat('#fff6d0', 0.2, emit=2.0)
SCREW = kit.mat('#c4c6cc', 0.25, metal=1.0)
SOCKET = kit.mat('#33304a', 0.5)
RAY = kit.mat('#ffcf3a', 0.3, emit=1.8)
LEAF = kit.mat('#4fbf6a', 0.55)
POT = kit.mat('#f08a5d', 0.6)
SOIL = kit.mat('#4a3424', 0.9)


# ── helpers ──────────────────────────────────────────────────────────────

def objs():
    return set(o for o in bpy.context.scene.objects if o.type == 'MESH')


def transform(objects, M):
    bpy.context.view_layer.update()
    for o in objects:
        o.matrix_world = M @ o.matrix_world


def _mesh_obj(bm, m, name):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
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


def slab(w, h, t, r, m, M, bevel=0.0, segs=6, name='slab'):
    """Rounded-rectangle prism in local XY (thickness along local Z), placed by matrix M."""
    bm = bmesh.new()
    pts = rrect_outline(w, h, r, segs)
    bot = [bm.verts.new((x, y, -t / 2)) for x, y in pts]
    top = [bm.verts.new((x, y, t / 2)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    for f in bm.faces:
        f.smooth = True
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


FACE = Matrix.Rotation(math.pi / 2, 4, 'X')   # local +Z -> -Y (faces the viewer), local +Y -> +Z


def panel(x, y, z, w, h, r, t, m, bevel=0.0, segs=6):
    """Upright rounded panel facing -Y, centred at (x, y, z)."""
    return slab(w, h, t, r, m, Matrix.Translation((x, y, z)) @ FACE, bevel=bevel, segs=segs, name='panel')


def flat(x, y, z, w, d, r, t, m, bevel=0.0, segs=6):
    """Rounded plate lying flat, centred at (x, y, z)."""
    return slab(w, d, t, r, m, Matrix.Translation((x, y, z)), bevel=bevel, segs=segs, name='flat')


def disc(x, y, z, r, t, m, verts=24):
    return kit.cylinder((x, y, z), r, t, m, rot=(math.pi / 2, 0, 0), verts=verts)


def lathe(profile, m, segs=40, name='lathe'):
    """Surface of revolution around Z. profile = [(r, z), ...] from bottom to top."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z))
                          for k in range(segs)])
    for A, B in zip(rings, rings[1:]):
        for k in range(segs):
            k2 = (k + 1) % segs
            if len(A) == 1:
                bm.faces.new((A[0], B[k], B[k2]))
            elif len(B) == 1:
                bm.faces.new((A[k], A[k2], B[0]))
            else:
                bm.faces.new((A[k], A[k2], B[k2], B[k]))
    for f in bm.faces:
        f.smooth = True
    return _mesh_obj(bm, m, name)


def heart(center, size, m, rot_z=0.0, name='heart'):
    mb = kit._meta(name, resolution=size * 0.06)
    s = size
    for sx in (1, -1):
        kit.blob_ball(mb, (0.26 * s * sx, 0, 0.18 * s), 0.3 * s)
        kit.blob_limb(mb, (0.26 * s * sx, 0, 0.12 * s), (0, 0, -0.42 * s), 0.27 * s, 0.05 * s, steps=7)
    kit.solidify_blobs({name: m})
    obj = bpy.data.objects[f'{name}_mesh']
    obj.scale = (1, 0.5, 1)
    obj.rotation_euler = (0, 0, rot_z)
    obj.location = center
    return obj


# ── base plate ───────────────────────────────────────────────────────────
BW, BD = 0.9, 0.78
flat(0, 0, 0.0125, BW + 0.03, BD + 0.03, 0.15, 0.025, BASE_TRIM, bevel=0.008)
flat(0, 0, 0.05, BW, BD, 0.13, 0.05, BASE_TOP, bevel=0.012)
flat(0, 0, 0.078, BW - 0.06, BD - 0.06, 0.11, 0.006, BASE_MAT, bevel=0.002)
TOP = 0.081
panel(0, -BD / 2 - 0.003, 0.05, 0.22, 0.032, 0.008, 0.008, GOLD, bevel=0.002)      # front name plaque
for sx in (-1, 1):
    kit.sphere((sx * 0.095, -BD / 2 - 0.008, 0.05), 0.006, GOLD, segs=8, rings=4)

# ── phone (built upright in its own frame: bottom-centre at origin, screen facing -Y) ──
before = objs()
W, H, T = 0.36, 0.74, 0.045
panel(0, 0, H / 2, W, H, 0.06, T, FRAME, bevel=0.012, segs=8)
panel(0, -T / 2 - 0.001, H / 2, W - 0.016, H - 0.016, 0.053, 0.004, GLASS, segs=8)
SY = -T / 2 - 0.0035
panel(0, SY, H / 2, W - 0.045, H - 0.05, 0.04, 0.002, SCREEN, segs=8)
UY = SY - 0.0015          # UI layer
U2 = UY - 0.0015          # layer above UI

# side buttons + back camera bump
kit.box((W / 2 + 0.003, 0, 0.56), (0.008, 0.016, 0.09), FRAME, bevel=0.003)
kit.box((-W / 2 - 0.003, 0, 0.6), (0.008, 0.016, 0.05), FRAME, bevel=0.003)
kit.box((-W / 2 - 0.003, 0, 0.52), (0.008, 0.016, 0.05), FRAME, bevel=0.003)
panel(-0.09, T / 2 + 0.006, 0.63, 0.14, 0.14, 0.04, 0.012, kit.mat('#5a3fe0', 0.2, metal=0.5), bevel=0.004)
for (x, z) in ((-0.12, 0.66), (-0.12, 0.6), (-0.06, 0.66)):
    kit.cylinder((x, T / 2 + 0.016, z), 0.022, 0.012, LENS_RING, rot=(math.pi / 2, 0, 0), verts=24)
    kit.cylinder((x, T / 2 + 0.02, z), 0.015, 0.006, LENS, rot=(math.pi / 2, 0, 0), verts=20)
kit.sphere((-0.06, T / 2 + 0.014, 0.6), 0.008, kit.mat('#fff2c0', 0.3, emit=1.0), segs=10, rings=5)   # flash

# notch / camera pill
panel(0, UY, 0.705, 0.07, 0.016, 0.008, 0.002, GLASS)

# header bar with avatar + app-bulb icon
panel(0, UY, 0.655, W - 0.07, 0.06, 0.02, 0.002, ACCENT_E)
disc(-0.115, U2, 0.655, 0.019, 0.002, WHITE_E)
disc(-0.115, U2 - 0.001, 0.66, 0.008, 0.002, SHIRT_E, verts=16)
panel(-0.045, U2, 0.664, 0.08, 0.011, 0.005, 0.002, TEXT_LT)
panel(-0.055, U2, 0.645, 0.06, 0.008, 0.004, 0.002, TEXT_LT)
disc(0.115, U2, 0.655, 0.016, 0.002, YELLOW_E)                                   # tiny bulb icon
panel(0.115, U2, 0.636, 0.012, 0.01, 0.003, 0.002, WHITE_E)

# video-call tile (top right) with a caller + self-view inset + hang-up button
VX, VZ, VW, VH = 0.075, 0.52, 0.15, 0.18
panel(VX, UY, VZ, VW, VH, 0.022, 0.002, TEAL_E)
panel(VX, U2, VZ - 0.055, 0.085, 0.07, 0.035, 0.002, SHIRT_E)                    # shoulders
disc(VX, U2 - 0.0005, VZ + 0.015, 0.03, 0.002, SKIN_E)                            # head
panel(VX, U2 - 0.001, VZ + 0.04, 0.062, 0.02, 0.01, 0.002, kit.mat('#3a2418', 0.6, emit=0.4))   # hair
panel(VX + 0.045, U2 - 0.0015, VZ + 0.058, 0.038, 0.05, 0.008, 0.002, kit.mat('#2a2f52', 0.4, emit=0.6))
disc(VX + 0.045, U2 - 0.002, VZ + 0.062, 0.009, 0.002, SKIN_E, verts=12)
disc(VX - 0.035, U2 - 0.0015, VZ - 0.07, 0.013, 0.002, RED_E, verts=16)
disc(VX + 0.0, U2 - 0.0015, VZ - 0.07, 0.013, 0.002, WHITE_E, verts=16)

# chat bubbles: left = grey, right = violet accent
for (x, z, w, h, side) in ((-0.085, 0.575, 0.13, 0.045, 'L'), (-0.095, 0.51, 0.1, 0.045, 'L'),
                           (0.05, 0.385, 0.21, 0.065, 'R'), (-0.045, 0.285, 0.21, 0.065, 'L'),
                           (0.07, 0.195, 0.15, 0.05, 'R')):
    m = ACCENT_E if side == 'R' else GREY_E
    tm = TEXT_LT if side == 'R' else TEXT_DK
    panel(x, UY, z, w, h, 0.02, 0.002, m)
    lines = 2 if h > 0.055 else 1
    for k in range(lines):
        lw = (w - 0.04) * (1.0 if k == 0 else 0.6)
        lz = z + (0.011 - 0.022 * k if lines == 2 else 0)
        panel(x - (w - 0.04 - lw) / 2, U2, lz, lw, 0.009, 0.004, 0.002, tm)
# typing indicator
panel(-0.1, UY, 0.12, 0.08, 0.04, 0.02, 0.002, GREY_E)
for k in range(3):
    disc(-0.12 + k * 0.02, U2, 0.12, 0.006, 0.002, TEXT_DK, verts=12)
# input bar + send button
panel(-0.025, UY, 0.06, 0.24, 0.045, 0.022, 0.002, kit.mat('#2d3150', 0.4, emit=0.6))
panel(-0.05, U2, 0.06, 0.15, 0.008, 0.004, 0.002, kit.mat('#6b7090', 0.5, emit=0.5))
disc(0.125, UY, 0.06, 0.024, 0.002, ACCENT_E)
kit.cone((0.127, U2, 0.06), 0.011, 0.0, 0.003, WHITE_E, rot=(math.pi / 2, 0, 0), verts=3)

# stand pieces that move with the phone (back support + front lip)
panel(0, T / 2 + 0.014, 0.17, 0.12, 0.34, 0.04, 0.022, STAND, bevel=0.006)
kit.box((0, -T / 2 - 0.016, 0.018), (0.3, 0.03, 0.05), STAND, bevel=0.01)

PX, PY, PZ = -0.07, 0.02, TOP + 0.022
transform(objs() - before, Matrix.Translation((PX, PY, PZ)) @ Matrix.Rotation(math.radians(-12), 4, 'X'))

# stand foot + rear brace
flat(PX, PY + 0.02, TOP + 0.011, 0.34, 0.24, 0.05, 0.022, STAND, bevel=0.006)
kit.box((PX, PY + 0.105, TOP + 0.06), (0.05, 0.03, 0.09), STAND_DK, rot=(math.radians(-12), 0, 0), bevel=0.008)

# ── lightbulb (Light Up motif) standing on the base, back-right ──
LX, LY = 0.3, 0.13
kit.cylinder((LX, LY, TOP + 0.015), 0.07, 0.03, SOCKET, verts=32)
kit.cylinder((LX, LY, TOP + 0.034), 0.058, 0.012, kit.mat('#4a456a', 0.4), verts=32)
z = TOP + 0.04
kit.cone((LX, LY, z + 0.01), 0.018, 0.035, 0.02, SOCKET, verts=24)
kit.cylinder((LX, LY, z + 0.05), 0.04, 0.06, SCREW, verts=28)
for k in range(4):
    kit.torus((LX, LY, z + 0.027 + k * 0.015), 0.04, 0.006, SCREW, major_segs=28, minor_segs=6)
gz = z + 0.08
glass = lathe([(0.0, 0.0), (0.042, 0.0), (0.045, 0.03), (0.062, 0.075), (0.085, 0.12), (0.099, 0.17),
               (0.103, 0.205), (0.098, 0.24), (0.084, 0.272), (0.06, 0.295), (0.032, 0.306), (0.0, 0.31)], BULB,
              segs=40, name='bulb')
glass.location = (LX, LY, gz)
BC = Vector((LX, LY, gz + 0.2))
kit.tube([BC + Vector((-0.075, -0.045, -0.02)), BC + Vector((-0.07, -0.06, 0.035)), BC + Vector((-0.04, -0.07, 0.07))],
         0.008, BULB_CORE, resolution=6, name='glint')
# rays: a halo of glowing dashes around the top of the bulb
for k in range(9):
    az = math.radians(-90 + k * 40)
    el = math.radians(35 if k % 2 == 0 else 15)
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    kit.rod(BC + d * 0.15, BC + d * 0.2, 0.009, RAY, verts=10)
kit.rod(BC + Vector((0, 0, 0.14)), BC + Vector((0, 0, 0.19)), 0.009, RAY, verts=10)

# ── floating 3D speech bubbles, heart and bell coming out of the screen ──
def bubble(center, w, h, m, tail_sign=1, rz=0.0, tilt=0.0):
    before_b = objs()
    slab(w, h, 0.04, min(w, h) * 0.45, m, FACE, bevel=0.012, segs=8, name='bubble')
    kit.spike((tail_sign * w * 0.25, 0, -h * 0.35), (tail_sign * w * 0.42, 0, -h * 0.5 - 0.05), 0.026, m, verts=16)
    new = objs() - before_b
    transform(new, Matrix.Translation(center) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'Y'))
    return Matrix.Translation(center) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'Y')


Mb = bubble((-0.34, -0.16, 0.6), 0.2, 0.12, ACCENT, tail_sign=1, rz=math.radians(18), tilt=math.radians(6))
for k in range(3):
    kit.sphere(Mb @ Vector((-0.05 + k * 0.05, -0.024, 0)), (0.016, 0.008, 0.016), WHITE, segs=12, rings=6)

Mg = bubble((-0.36, -0.1, 0.37), 0.15, 0.09, BUBBLE_GREY, tail_sign=1, rz=math.radians(14), tilt=math.radians(-5))
for k, lw in enumerate((0.09, 0.055)):
    b = slab(lw, 0.012, 0.004, 0.006, kit.mat('#8a90a8', 0.5), FACE)
    transform([b], Mg @ Matrix.Translation((-(0.09 - lw) / 2, -0.022, 0.012 - 0.024 * k)))

heart((0.27, -0.14, 0.66), 0.13, HEART, rot_z=math.radians(-15), name='heartA')
heart((0.4, -0.05, 0.78), 0.07, kit.mat('#ff7aa0', 0.3), rot_z=math.radians(-25), name='heartB')

# notification bell with a red badge
before = objs()
bell = lathe([(0.0, -0.002), (0.058, -0.002), (0.06, 0.008), (0.05, 0.016), (0.044, 0.04), (0.04, 0.07),
              (0.032, 0.095), (0.018, 0.105), (0.0, 0.108)], BELL, segs=32, name='bell')
kit.sphere((0, 0, -0.012), 0.016, BELL, segs=12, rings=6)
kit.torus((0, 0, 0.115), 0.012, 0.004, BELL, rot=(math.pi / 2, 0, 0), major_segs=16, minor_segs=6)
kit.sphere((0.04, -0.03, 0.09), 0.022, BADGE, segs=16, rings=8)
transform(objs() - before, Matrix.Translation((-0.22, -0.12, 0.82)) @ Matrix.Rotation(math.radians(18), 4, 'Y'))

# little succulent pot in the front-right corner for charm
kit.cylinder((0.3, -0.24, TOP + 0.035), 0.05, 0.07, POT, verts=24)
kit.torus((0.3, -0.24, TOP + 0.07), 0.05, 0.008, POT, major_segs=24, minor_segs=6)
kit.cylinder((0.3, -0.24, TOP + 0.066), 0.044, 0.004, SOIL, verts=24)
for k in range(6):
    a = k * math.pi / 3
    kit.sphere((0.3 + math.cos(a) * 0.02, -0.24 + math.sin(a) * 0.02, TOP + 0.085), (0.014, 0.014, 0.03), LEAF,
               rot=(math.sin(a) * 0.6, -math.cos(a) * 0.6, 0), segs=10, rings=6)
kit.sphere((0.3, -0.24, TOP + 0.095), (0.012, 0.012, 0.03), LEAF, segs=10, rings=6)

# wireless earbuds case (front-left) — calls need earbuds
EX, EY = -0.27, -0.25
flat(EX, EY, TOP + 0.022, 0.13, 0.09, 0.04, 0.044, WHITE, bevel=0.012)
kit.box((EX, EY - 0.045, TOP + 0.03), (0.1, 0.004, 0.003), kit.mat('#c8c8d4', 0.4))
kit.sphere((EX, EY - 0.046, TOP + 0.02), 0.006, kit.mat('#3cc8b4', 0.3, emit=1.0), segs=10, rings=5)
for sx in (-1, 1):
    bud = Vector((EX + sx * 0.03, EY + 0.005, TOP + 0.058))
    kit.sphere(bud, (0.022, 0.02, 0.018), WHITE, segs=16, rings=8)
    kit.sphere(bud + Vector((sx * -0.012, -0.01, 0.004)), 0.01, kit.mat('#9a9aa8', 0.4), segs=10, rings=5)

kit.finalize_prop('lightup_phone')
