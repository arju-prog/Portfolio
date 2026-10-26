"""Evaratus (AI startup) desk diorama: a tiny futuristic multi-agent RL lab. Three cute hover-robot agents
with glowing visors work at desks with dashboard monitors, a server rack blinks in the corner, a holo
projector in the middle floats task cards with arrows passing between the agents, cables snake across the
floor. White/grey + teal and violet accents, on a rounded collectible base plate."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, mat, rod, sphere, torus, tube  # noqa: E402

kit.reset()
random.seed(11)

WHITE = mat('#f3f5f8', 0.35)
LIGHT = mat('#d6dce5', 0.45)
GREY = mat('#9aa3b0', 0.4, metal=0.3)
DARK = mat('#2a2f3a', 0.35, metal=0.5)
SLATE = mat('#3a4150', 0.5)
FLOOR = mat('#e6eaf0', 0.6)
FLOOR_LINE = mat('#c9d0da', 0.6)
VISOR = mat('#141a26', 0.12)
SCREEN = mat('#0f1a2c', 0.25, emit=0.6)
TEAL = mat('#13bfae', 0.35)
TEAL_EM = mat('#20e3cf', 0.3, emit=3.0)
VIOLET = mat('#7c5cf0', 0.35)
VIOLET_EM = mat('#9b7bff', 0.3, emit=3.0)
AMBER_EM = mat('#ffb547', 0.3, emit=3.0)
GREEN_EM = mat('#4dff8a', 0.3, emit=3.0)
PINK_EM = mat('#ff5c9a', 0.3, emit=2.5)
WHITE_EM = mat('#e9fbff', 0.3, emit=2.0)
CABLE = mat('#3b4352', 0.6)
LEAF = mat('#3fae5a', 0.55)
POT = mat('#f3f5f8', 0.36)


def holo_mat(hex_color, emit=1.6, alpha=0.6, rough=0.21):
    m = mat(hex_color, rough, emit=emit)
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Alpha'].default_value = alpha
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'BLENDED'
    elif hasattr(m, 'blend_method'):
        m.blend_method = 'BLEND'
    return m


HOLO = holo_mat('#3ff0dc')
HOLO_V = holo_mat('#a58bff', rough=0.22)


# ── helpers ──────────────────────────────────────────────────────────────

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


def rounded_slab(w, d, r, z0, z1, m, bevel=0.0, segs=8, cx=0.0, cy=0.0, name='slab'):
    """Prism with a rounded-rectangle outline (corner radius r), optional bevel on its rims."""
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = sx * (w / 2 - r), sy * (d / 2 - r)
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + ccx + math.cos(a) * r, cy + ccy + math.sin(a) * r))
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    obj = _mesh_obj(bm, m, name)
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(50)
        mod.harden_normals = True
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def mark():
    return set(bpy.context.scene.objects)


def place(before, loc=(0, 0, 0), yaw=0.0, scale=1.0):
    """Move everything created since `before` (built around the origin) to loc, rotated by yaw about Z."""
    bpy.context.view_layer.update()
    M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Scale(scale, 4)
    for o in set(bpy.context.scene.objects) - before:
        o.matrix_world = M @ o.matrix_world


def yaw_to(dx, dy):
    """Yaw that turns a -Y-facing group to face direction (dx, dy)."""
    return math.atan2(dx, -dy)


# ── base plate ───────────────────────────────────────────────────────────
W = 2.0
rounded_slab(W, W, 0.24, 0.0, 0.16, SLATE, bevel=0.03, name='plinth')
rounded_slab(W + 0.03, W + 0.03, 0.255, 0.05, 0.075, TEAL, bevel=0.008, name='trim')
rounded_slab(W - 0.07, W - 0.07, 0.2, 0.16, 0.2, FLOOR, bevel=0.012, name='floor')
FZ = 0.2
# round floor mat under the holo projector + a darker work zone under the back desk
cylinder((0.12, -0.02, FZ + 0.004), 0.36, 0.008, mat('#cfe9e6', 0.6), verts=48)
rounded_slab(1.0, 0.62, 0.08, FZ, FZ + 0.006, FLOOR_LINE, cx=-0.42, cy=0.46, name='zone')


# ── back wall with big dashboard ─────────────────────────────────────────
WY = 0.82
box((-0.28, WY, FZ + 0.42), (1.3, 0.07, 0.84), WHITE, bevel=0.025)
box((-0.28, WY - 0.038, FZ + 0.08), (1.28, 0.012, 0.03), TEAL, bevel=0.004)      # front stripe
box((-0.28, WY + 0.038, FZ + 0.08), (1.28, 0.012, 0.03), TEAL, bevel=0.004)      # back stripe
for i in range(4):                                                                    # back vent slits
    box((-0.28, WY + 0.04, FZ + 0.5 + i * 0.07), (0.7, 0.01, 0.025), LIGHT, bevel=0.004)
box((-0.28, WY + 0.04, FZ + 0.3), (1.0, 0.012, 0.04), TEAL, bevel=0.005)
# wall dashboard (front)
DX, DZ = -0.33, FZ + 0.5
box((DX, WY - 0.045, DZ), (0.9, 0.03, 0.46), DARK, bevel=0.012)
box((DX, WY - 0.062, DZ), (0.84, 0.006, 0.4), SCREEN)
SY = WY - 0.067
box((DX, SY, DZ + 0.165), (0.8, 0.004, 0.035), VIOLET_EM)                            # header bar
for k, h in enumerate((0.08, 0.14, 0.11, 0.2, 0.17, 0.24)):                          # bar chart
    box((DX - 0.35 + k * 0.05, SY, DZ - 0.17 + h / 2), (0.032, 0.004, h), TEAL_EM if k % 2 == 0 else VIOLET_EM)
curve = [(DX + 0.0 + i * 0.05, SY - 0.002, DZ - 0.1 + 0.07 * math.sin(i * 0.9) + i * 0.02) for i in range(8)]
tube(curve, 0.008, AMBER_EM, resolution=3, name='graph')                            # line graph
for i in range(4):                                                                    # KPI tiles
    box((DX + 0.04 + i * 0.09, SY, DZ + 0.09), (0.075, 0.004, 0.07), [TEAL_EM, GREEN_EM, PINK_EM, VIOLET_EM][i])
# little wall clock-ish status light
sphere((0.25, WY - 0.05, FZ + 0.72), (0.03, 0.012, 0.03), GREEN_EM, segs=12, rings=6)


# ── furniture builders (built around the origin, facing -Y) ──────────────

def monitor(w=0.34, h=0.22, kind=0, stand_h=0.1):
    zc = stand_h + h / 2
    box((0, 0, zc), (w, 0.022, h), DARK, bevel=0.01)
    box((0, -0.012, zc), (w - 0.03, 0.004, h - 0.03), SCREEN)
    y = -0.0155
    iw, ih = w - 0.05, h - 0.05
    box((0, y, zc + ih / 2 - 0.01), (iw, 0.003, 0.016), TEAL_EM if kind != 1 else VIOLET_EM)
    if kind == 0:   # bars + line
        n = 6
        for k in range(n):
            bh = (0.25 + 0.6 * random.random()) * ih * 0.7
            box((-iw / 2 + 0.015 + k * (iw * 0.55 / n), y, zc - ih / 2 + bh / 2), (iw * 0.06, 0.003, bh),
                TEAL_EM if k % 2 else VIOLET_EM)
        pts = [(iw * 0.08 + i * iw * 0.07, y - 0.001, zc - ih * 0.25 + 0.03 * math.sin(i * 1.4) + i * 0.008)
               for i in range(6)]
        tube(pts, 0.005, AMBER_EM, resolution=2, name='graph')
    elif kind == 1:   # reward curve
        pts = [(-iw / 2 + 0.01 + i * iw / 9, y - 0.001, zc - ih * 0.38 + ih * 0.65 * (1 - math.exp(-i / 2.6))
                + 0.012 * math.sin(i * 2.1)) for i in range(10)]
        tube(pts, 0.006, GREEN_EM, resolution=2, name='graph')
        box((0, y, zc - ih * 0.42), (iw, 0.003, 0.006), WHITE_EM)
    else:   # grid of agent tiles
        for i in range(3):
            for j in range(2):
                box((-iw / 3 + i * iw / 3, y, zc - 0.035 + j * 0.06), (iw / 3 - 0.02, 0.003, 0.045),
                    [TEAL_EM, VIOLET_EM, AMBER_EM, GREEN_EM, PINK_EM, TEAL_EM][i + 3 * j])
    # stand
    box((0, 0.025, stand_h / 2 + 0.01), (0.03, 0.02, stand_h), GREY, bevel=0.006)
    box((0, 0.01, 0.006), (0.14, 0.09, 0.012), GREY, bevel=0.005)


def desk(w=0.8, d=0.36, h=0.3):
    box((0, 0, h - 0.015), (w, d, 0.03), WHITE, bevel=0.012)
    box((0, -d / 2 + 0.003, h - 0.032), (w - 0.04, 0.008, 0.008), TEAL_EM)            # glowing edge strip
    for sx in (-1, 1):
        box((sx * (w / 2 - 0.04), 0, (h - 0.03) / 2), (0.035, d - 0.06, h - 0.03), LIGHT, bevel=0.008)
    box((0, d / 2 - 0.05, h * 0.55), (w - 0.1, 0.02, h * 0.5), LIGHT, bevel=0.006)    # modesty panel


def keyboard(loc, yaw=0.0):
    b = mark()
    box((0, 0, 0.007), (0.17, 0.06, 0.014), DARK, bevel=0.004)
    box((0, -0.002, 0.0145), (0.15, 0.045, 0.003), GREY)
    place(b, loc, yaw)


def mug(loc):
    cylinder((loc[0], loc[1], loc[2] + 0.03), 0.022, 0.06, TEAL, verts=14)
    torus((loc[0] + 0.024, loc[1], loc[2] + 0.032), 0.013, 0.004, TEAL, rot=(math.pi / 2, 0, 0), major_segs=10,
          minor_segs=4)


def robot(accent=TEAL, accent_em=TEAL_EM, arm_l='down', arm_r='down', head_yaw=0.0, prop=None):
    """Cute hover-bot, ~0.5 tall, facing -Y, origin on the floor."""
    torus((0, 0, 0.03), 0.06, 0.012, accent_em, major_segs=20, minor_segs=6)          # hover ring
    cylinder((0, 0, 0.055), 0.05, 0.03, GREY, verts=16)
    sphere((0, 0, 0.16), (0.1, 0.09, 0.105), WHITE, segs=20, rings=10)               # body
    box((0, -0.088, 0.17), (0.07, 0.012, 0.05), VISOR, bevel=0.01)                    # chest plate
    sphere((-0.017, -0.095, 0.175), 0.008, accent_em, segs=8, rings=4)
    sphere((0.012, -0.095, 0.175), 0.008, AMBER_EM, segs=8, rings=4)
    torus((0, 0, 0.245), 0.055, 0.012, GREY, major_segs=16, minor_segs=6)             # neck ring
    # head (optionally turned)
    hb = mark()
    hz = 0.34
    box((0, 0, hz), (0.25, 0.2, 0.17), WHITE, bevel=0.055)
    box((0, -0.088, hz - 0.005), (0.2, 0.04, 0.1), VISOR, bevel=0.03)
    for sx in (-1, 1):
        sphere((sx * 0.045, -0.109, hz), (0.024, 0.008, 0.03), accent_em, segs=12, rings=6)   # eyes
        cylinder((sx * 0.13, 0, hz), 0.04, 0.025, accent, rot=(0, math.pi / 2, 0), verts=16)  # ear pods
        cylinder((sx * 0.143, 0, hz), 0.022, 0.006, accent_em, rot=(0, math.pi / 2, 0), verts=12)
    rod((0.04, 0.02, hz + 0.08), (0.06, 0.03, hz + 0.16), 0.007, GREY, verts=8, caps=False)
    sphere((0.06, 0.03, hz + 0.17), 0.018, VIOLET_EM if accent is TEAL else TEAL_EM, segs=12, rings=6)
    place(hb, (0, 0, 0), head_yaw)
    # arms
    poses = {
        'down': ((0.13, 0.0, 0.15), (0.15, -0.02, 0.07)),
        'type': ((0.13, -0.07, 0.15), (0.1, -0.16, 0.13)),
        'up': ((0.15, -0.02, 0.24), (0.17, -0.06, 0.33)),
        'hold': ((0.13, -0.08, 0.13), (0.06, -0.15, 0.15)),
    }
    for sx, pose in ((1, arm_l), (-1, arm_r)):
        e, h = poses[pose]
        sh = Vector((0.09 * sx, 0, 0.19))
        el = Vector((e[0] * sx, e[1], e[2]))
        wr = Vector((h[0] * sx, h[1], h[2]))
        sphere(sh, 0.028, GREY, segs=12, rings=6)
        rod(sh, el, 0.017, LIGHT, verts=10, caps=False)
        rod(el, wr, 0.016, LIGHT, verts=10, caps=False)
        sphere(el, 0.02, GREY, segs=10, rings=5)
        sphere(wr, 0.026, accent, segs=12, rings=6)
    if prop == 'tablet':
        box((0, -0.18, 0.17), (0.14, 0.012, 0.1), DARK, rot=(-0.6, 0, 0), bevel=0.006)
        box((0, -0.187, 0.174), (0.12, 0.004, 0.08), TEAL_EM, rot=(-0.6, 0, 0))


def holo_card(loc, yaw, tilt=0.0, m=None, lines_m=WHITE_EM, check=True, w=0.22, h=0.15):
    b = mark()
    box((0, 0, 0), (w, 0.006, h), m or HOLO, bevel=0.003)
    box((0, 0, h / 2 - 0.004), (w, 0.009, 0.008), lines_m)                    # top edge glow
    box((0, 0, -h / 2 + 0.004), (w, 0.009, 0.006), lines_m)
    for i, lw in enumerate((0.11, 0.14, 0.09)):
        box((-w / 2 + 0.03 + lw / 2 + (0.03 if check else 0), -0.006, h / 2 - 0.035 - i * 0.04), (lw, 0.004, 0.016),
            lines_m)
        if check:
            box((-w / 2 + 0.04, -0.006, h / 2 - 0.035 - i * 0.04), (0.024, 0.004, 0.024),
                GREEN_EM if i < 2 else AMBER_EM)
    bpy.context.view_layer.update()
    for o in set(bpy.context.scene.objects) - b:
        o.matrix_world = Matrix.Rotation(tilt, 4, 'X') @ o.matrix_world
    place(b, loc, yaw)


def arrow(points, m=VIOLET_EM, r=0.009):
    tube(points, r, m, resolution=6, name='arrow')
    a, b = Vector(points[-2]), Vector(points[-1])
    d = (b - a).normalized()
    kit.cone(b + d * 0.025, r * 3, 0.0, 0.05, m, rot=kit.rot_between(b, b + d), verts=12)


# ── desk A: back-left, two monitors ──────────────────────────────────────
b = mark()
desk(0.9, 0.38, 0.3)
place(b, (-0.42, 0.5, FZ))
b = mark()
monitor(0.36, 0.22, kind=0)
place(b, (-0.58, 0.56, FZ + 0.3), yaw=0.18)
b = mark()
monitor(0.3, 0.2, kind=1)
place(b, (-0.22, 0.58, FZ + 0.3), yaw=-0.2)
keyboard((-0.42, 0.42, FZ + 0.3), 0.05)
mug((-0.8, 0.44, FZ + 0.3))

# robot A: in front of desk A, half-turned to the viewer, typing
b = mark()
robot(TEAL, TEAL_EM, arm_l='down', arm_r='up', head_yaw=0.15)
place(b, (-0.2, 0.14, FZ), yaw=yaw_to(0.25, -1), scale=1.15)

# ── desk B: front-left corner, angled toward the viewer ──────────────────
b = mark()
desk(0.62, 0.34, 0.3)
place(b, (-0.54, -0.4, FZ), yaw=yaw_to(0.75, -0.66) + math.pi)
b = mark()
monitor(0.34, 0.22, kind=2)
place(b, (-0.58, -0.36, FZ + 0.3), yaw=yaw_to(0.75, -0.66))
keyboard((-0.48, -0.47, FZ + 0.3), yaw_to(0.75, -0.66))
# small desk plant
cylinder((-0.76, -0.53, FZ + 0.33), 0.035, 0.06, POT, verts=14)
for i in range(5):
    a = i * 2 * math.pi / 5
    sphere((-0.76 + math.cos(a) * 0.02, -0.53 + math.sin(a) * 0.02, FZ + 0.39), (0.022, 0.022, 0.04), LEAF,
           rot=(math.cos(a) * 0.5, math.sin(a) * -0.5, 0), segs=10, rings=6)

# robot B: beside desk B, violet accent, looking at the holo cards
b = mark()
robot(VIOLET, VIOLET_EM, arm_l='down', arm_r='type', head_yaw=-0.35)
place(b, (-0.2, -0.6, FZ), yaw=yaw_to(0.2, -1), scale=1.15)

# ── server rack: back-right corner ───────────────────────────────────────
RX, RY = 0.66, 0.6
RW, RD, RH = 0.36, 0.34, 0.92
box((RX, RY, FZ + RH / 2 + 0.03), (RW, RD, RH), DARK, bevel=0.018)
box((RX, RY - RD / 2 - 0.002, FZ + RH / 2 + 0.03), (RW - 0.05, 0.01, RH - 0.05), SLATE)
for sx in (-1, 1):
    for sy in (-1, 1):
        cylinder((RX + sx * (RW / 2 - 0.04), RY + sy * (RD / 2 - 0.04), FZ + 0.015), 0.02, 0.03, GREY, verts=10)
LED_MATS = [GREEN_EM, TEAL_EM, VIOLET_EM, AMBER_EM, GREEN_EM, TEAL_EM]
n_units = 8
for k in range(n_units):
    z = FZ + 0.1 + k * (RH - 0.12) / n_units + 0.04
    y = RY - RD / 2 - 0.012
    box((RX, y, z), (RW - 0.08, 0.012, 0.075), mat('#454d5c', 0.35, metal=0.5), bevel=0.004)
    for v in range(4):                                                               # vent slits
        box((RX + 0.02 + v * 0.025, y - 0.007, z), (0.012, 0.004, 0.05), DARK)
    for j in range(3):                                                               # blinking LEDs
        sphere((RX - 0.12 + j * 0.03, y - 0.008, z + 0.012), 0.009, random.choice(LED_MATS), segs=8, rings=4)
    box((RX - 0.09, y - 0.007, z - 0.018), (0.08, 0.004, 0.008), TEAL_EM if k % 2 else VIOLET_EM)
box((RX, RY, FZ + RH + 0.05), (RW - 0.06, RD - 0.06, 0.012), SLATE)               # top vent plate
# side panel stripe (visible from the right / back)
box((RX + RW / 2 + 0.002, RY, FZ + RH / 2 + 0.03), (0.008, 0.04, RH - 0.1), TEAL, bevel=0.003)
box((RX, RY + RD / 2 + 0.002, FZ + RH / 2 + 0.03), (0.04, 0.008, RH - 0.1), TEAL, bevel=0.003)
for k in range(5):
    box((RX, RY + RD / 2 + 0.003, FZ + 0.2 + k * 0.15), (RW - 0.1, 0.006, 0.03), SLATE)

# robot C: front-right, holding a tablet, facing the centre/viewer
b = mark()
robot(TEAL, TEAL_EM, arm_l='hold', arm_r='hold', head_yaw=-0.2, prop='tablet')
place(b, (0.56, -0.36, FZ), yaw=yaw_to(-0.15, -1), scale=1.15)

# ── holo projector + floating task cards ─────────────────────────────────
PX, PY = 0.12, 0.0
cylinder((PX, PY, FZ + 0.03), 0.14, 0.06, LIGHT, verts=32)
cylinder((PX, PY, FZ + 0.065), 0.12, 0.012, GREY, verts=32)
torus((PX, PY, FZ + 0.072), 0.12, 0.008, TEAL_EM, major_segs=32, minor_segs=6)
cylinder((PX, PY, FZ + 0.074), 0.085, 0.006, HOLO, verts=24)
cylinder((PX, PY, FZ + 0.078), 0.04, 0.006, WHITE_EM, verts=20)
torus((PX, PY, FZ + 0.16), 0.07, 0.005, HOLO, major_segs=24, minor_segs=4)
torus((PX, PY, FZ + 0.24), 0.05, 0.004, HOLO, major_segs=24, minor_segs=4)
cards = [((PX - 0.16, PY + 0.02, FZ + 0.56), yaw_to(-0.1, -1), 0.1, HOLO),
         ((PX + 0.16, PY + 0.08, FZ + 0.68), yaw_to(0.45, -1), -0.08, HOLO_V),
         ((PX + 0.04, PY - 0.06, FZ + 0.4), yaw_to(0.2, -1), 0.2, HOLO)]
for loc, yw, tilt, m in cards:
    holo_card(loc, yw, tilt, m)
# arrows: task handoffs between agents
arrow([(-0.26, 0.14, FZ + 0.68), (-0.18, 0.08, FZ + 0.78), (-0.06, 0.04, FZ + 0.72)], r=0.012)
arrow([(0.3, 0.1, FZ + 0.8), (0.46, -0.04, FZ + 0.82), (0.56, -0.22, FZ + 0.72)], TEAL_EM, r=0.012)
arrow([(-0.02, -0.12, FZ + 0.32), (-0.12, -0.3, FZ + 0.4), (-0.2, -0.46, FZ + 0.6)], VIOLET_EM, r=0.012)

# ── mini grid-world RL environment on the floor (front) ─────────────────
GX, GY, GN, GS = 0.2, -0.7, 4, 0.08
box((GX, GY, FZ + 0.015), (GN * GS + 0.04, GN * GS + 0.04, 0.03), DARK, bevel=0.01)
for i in range(GN):
    for j in range(GN):
        box((GX + (i - 1.5) * GS, GY + (j - 1.5) * GS, FZ + 0.033), (GS - 0.008, GS - 0.008, 0.008),
            WHITE if (i + j) % 2 == 0 else LIGHT)
for (i, j, m) in ((0, 0, TEAL), (2, 1, VIOLET)):                                          # agent pawns
    box((GX + (i - 1.5) * GS, GY + (j - 1.5) * GS, FZ + 0.06), (0.045, 0.045, 0.045), m, bevel=0.01)
    sphere((GX + (i - 1.5) * GS, GY + (j - 1.5) * GS - 0.024, FZ + 0.066), (0.012, 0.004, 0.008), WHITE_EM,
           segs=8, rings=4)
box((GX + 1.5 * GS, GY + 1.5 * GS, FZ + 0.05), (0.05, 0.05, 0.02), AMBER_EM, bevel=0.006)     # goal tile
rod((GX + 1.5 * GS, GY + 1.5 * GS, FZ + 0.06), (GX + 1.5 * GS, GY + 1.5 * GS, FZ + 0.17), 0.005, GREY, verts=8)
box((GX + 1.5 * GS + 0.03, GY + 1.5 * GS, FZ + 0.15), (0.06, 0.006, 0.04), AMBER_EM)          # goal flag
box((GX - 0.5 * GS, GY - 0.5 * GS, FZ + 0.05), (0.06, 0.06, 0.025), SLATE, bevel=0.006)       # wall block
box((GX + 0.5 * GS, GY + 1.5 * GS, FZ + 0.05), (0.06, 0.06, 0.025), SLATE, bevel=0.006)

# ── cables on the floor ──────────────────────────────────────────────────
tube([(RX - 0.12, RY - 0.18, FZ + 0.012), (0.3, 0.42, FZ + 0.012), (0.05, 0.3, FZ + 0.012),
      (-0.15, 0.36, FZ + 0.012), (-0.25, 0.42, FZ + 0.03)], 0.013, CABLE, resolution=6, name='cable')
tube([(RX - 0.08, RY - 0.2, FZ + 0.012), (0.42, 0.2, FZ + 0.012), (0.26, 0.05, FZ + 0.012),
      (PX + 0.13, PY + 0.02, FZ + 0.02)], 0.012, TEAL, resolution=6, name='cable')
tube([(PX - 0.1, PY - 0.1, FZ + 0.012), (-0.1, -0.2, FZ + 0.012), (-0.25, -0.18, FZ + 0.012),
      (-0.42, -0.28, FZ + 0.03)], 0.012, VIOLET, resolution=6, name='cable')

kit.finalize_prop('evaratus_lab', thumb_angle=-24, elevation=0.55)
