"""Shared helpers for the posed chibi sprites (wukong_slide, wukong_land, naruto_clone).

Underscore-prefixed so build scripts skip it. Everything is built from kit primitives:
  Group(M)      — context manager: every object created inside is transformed by matrix M
  joint(...)    — 2-bone IK: elbow/knee position from root, end and a bend hint
  banded_tube   — striped tapered tube (pheasant plumes)
  wukong(...)   — the chibi Destined One in any pose (body matrix + world hand/foot targets)
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

V = Vector

# sprite-budget defaults (runtime only, kit.py untouched): 24x12 spheres, 16-sided rods/caps
kit.sphere.__defaults__ = ((0, 0, 0), 24, 12, None)
kit.rod.__defaults__ = (16, True, None, None)


# ── generic helpers ──────────────────────────────────────────────────────

class Group:
    """Objects created inside the `with` block get `M @ matrix_world`."""

    def __init__(self, M):
        self.M = M

    def __enter__(self):
        self.before = set(bpy.context.scene.objects)
        return self

    def __exit__(self, *exc):
        bpy.context.view_layer.update()
        for o in set(bpy.context.scene.objects) - self.before:
            o.matrix_world = self.M @ o.matrix_world
        bpy.context.view_layer.update()


def no_ink(obj):
    """Freestyle face-mark: tiny decals (whiskers, pupils, engravings) skip the ink outline."""
    attr = obj.data.attributes.get('freestyle_face') or obj.data.attributes.new('freestyle_face', 'BOOLEAN', 'FACE')
    attr.data.foreach_set('value', [True] * len(obj.data.polygons))
    return obj


def skip_marked_ink():
    """Call before finalize_prop: the ink lineset ignores face-marked geometry."""
    fs = bpy.context.view_layer.freestyle_settings
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('ink')
    ls.select_by_face_marks = True
    ls.face_mark_negation = 'EXCLUSIVE'
    ls.face_mark_condition = 'ONE'


def tf(M, p):
    return M @ V(p)


def joint(a, c, L1, L2, hint):
    """Middle joint of a two-bone chain a→?→c with bone lengths L1, L2, bending towards `hint`."""
    a, c = V(a), V(c)
    d = c - a
    D = d.length
    n = d.normalized()
    if D >= L1 + L2 - 1e-4:
        return a + d * (L1 / (L1 + L2))
    x = (L1 * L1 - L2 * L2 + D * D) / (2 * D)
    h = math.sqrt(max(0.0, L1 * L1 - x * x))
    hint = V(hint)
    perp = hint - n * hint.dot(n)
    if perp.length < 1e-6:
        perp = n.orthogonal()
    return a + n * x + perp.normalized() * h


def catmull(pts, n=8):
    pts = [V(p) for p in pts]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def banded_tube(guide, r0, r1, mats, bands=10, n=8):
    """Tapered tube split into alternating colour bands."""
    path = catmull(guide, n)
    per = max(2, len(path) // bands)
    for b in range(0, len(path) - 1, per):
        seg = path[b:b + per + 1]
        if len(seg) < 2:
            break
        t0, t1 = b / (len(path) - 1), min(1, (b + per) / (len(path) - 1))
        ra, rb = r0 + (r1 - r0) * t0, r0 + (r1 - r0) * t1
        kit.tube([tuple(p) for p in seg], ra, mats[(b // per) % len(mats)], taper_to=rb / ra,
                 resolution=2, smooth_path=False, name='band')


def dome(center, normal, size, m, rim=None, segs=24):
    """Flattened ellipsoid whose thin axis points along `normal`; optional rim torus."""
    rot = kit.rot_between((0, 0, 0), normal)
    kit.sphere(center, size, m, rot=rot, segs=segs, rings=segs // 2)
    if rim:
        kit.torus(V(center) - V(normal).normalized() * size[2] * 0.1, 1.0, 0.09, rim, rot=rot,
                  major_segs=28, minor_segs=6, scale=(size[0], size[1], size[0]))


def aligned(loc, size, axis, m, segs=20):
    """Ellipsoid with its local Z (size[2]) along `axis`."""
    return kit.sphere(loc, size, m, rot=kit.rot_between((0, 0, 0), axis), segs=segs, rings=segs // 2)


def tri_report(top=12):
    """Debug (env MINI_TRIS=1): print the heaviest object kinds by triangle count."""
    if not os.environ.get('MINI_TRIS'):
        return
    deps = bpy.context.evaluated_depsgraph_get()
    tally = {}
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        me = o.evaluated_get(deps).to_mesh()
        key = o.name.split('.')[0]
        n, t = tally.get(key, (0, 0))
        tally[key] = (n + 1, t + sum(len(p.vertices) - 2 for p in me.polygons))
    for key, (n, t) in sorted(tally.items(), key=lambda kv: -kv[1][1])[:top]:
        print(f'[kit]   {key}: {n} objs, {t} tris')


def bounds():
    """World bbox (lo, hi) of every mesh, modifiers applied — what finalize_prop will measure."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = V((1e9, 1e9, 1e9)), V((-1e9, -1e9, -1e9))
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        for v in me.vertices:
            p = o.matrix_world @ v.co
            lo = V((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = V((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
        ev.to_mesh_clear()
    return lo, hi


def bounds_x():
    lo, hi = bounds()
    return lo.x, hi.x


def sprite_px(points, lo, hi, res=512):
    """After finalize_prop: pixel (x, y from top) of pre-finalize world points in the rendered sprite."""
    from bpy_extras.object_utils import world_to_camera_view
    k = 1.0 / max(hi - lo)
    c = (lo + hi) / 2
    scene = bpy.context.scene
    out = []
    for p in points:
        q = world_to_camera_view(scene, scene.camera, (V(p) - c) * k)
        out.append((q.x * res, (1 - q.y) * res))
    return out


# ── chibi Destined One ───────────────────────────────────────────────────

FUR = FUR_DK = FUR_LT = FACE = HAND = IRON = IRON_DK = GOLD = RED = ORANGE = WRAP = None
PANTS = SHOE = INK = GOLD_EYE = WHITE = MOUTH = PLUMES = None


def palette():
    global FUR, FUR_DK, FUR_LT, FACE, HAND, IRON, IRON_DK, GOLD, RED, ORANGE, WRAP, PANTS, SHOE, INK
    global GOLD_EYE, WHITE, MOUTH, PLUMES
    FUR = kit.mat('#6e4426', 0.85)
    FUR_DK = kit.mat('#4a2c17', 0.9)
    FUR_LT = kit.mat('#8c5a32', 0.85)
    FACE = kit.mat('#e0b585', 0.6)
    HAND = kit.mat('#a87d55', 0.6)
    IRON = kit.mat('#4f5660', 0.35, metal=0.75)
    IRON_DK = kit.mat('#353a42', 0.4, metal=0.7)
    GOLD = kit.mat('#eab030', 0.25, metal=0.9)
    RED = kit.mat('#c42a1e', 0.7)
    ORANGE = kit.mat('#e0621f', 0.7)
    WRAP = kit.mat('#d8cba9', 0.85)
    PANTS = kit.mat('#3d342c', 0.85)
    SHOE = kit.mat('#2a2522', 0.5)
    INK = kit.mat('#1a0f08', 0.4)
    GOLD_EYE = kit.mat('#ffc21f', 0.2, emit=0.5)
    WHITE = kit.mat('#fbf7ee', 0.3)
    MOUTH = kit.mat('#5a1410', 0.5)
    PLUMES = (kit.mat('#b8361c', 0.55), kit.mat('#3b1d12', 0.6), kit.mat('#b8361c', 0.55), kit.mat('#e3aa5c', 0.55))


HEAD_R = 0.42
UPPER, FORE = 0.29, 0.27
THIGH, SHIN = 0.3, 0.28


def wk_head(mouth='grin'):
    """Monkey head around the origin (front -Y). Returns plume socket points (head-local)."""
    r = HEAD_R
    kit.sphere((0, 0, 0), (r, r * 0.96, r * 0.98), FUR, segs=32, rings=16)
    # heart-shaped tan face: two eye lobes + muzzle, fur widow's peak between the lobes
    for sx in (1, -1):
        kit.sphere((0.125 * sx, -0.215, 0.02), (0.17, 0.2, 0.165), FACE, segs=24, rings=12)
    kit.sphere((0, -0.25, -0.16), (0.21, 0.19, 0.15), FACE, segs=24, rings=12)
    kit.spike((0, -0.33, 0.25), (0, -0.4, 0.07), 0.075, FUR, verts=14)
    # cheek fur / sideburns + crown tufts (chunky, readable spikes)
    for sx in (1, -1):
        for (bx, by, bz), (tx, ty, tz), rr in ((((0.36, -0.12, -0.12), (0.53, -0.08, -0.26), 0.085)),
                                                (((0.37, -0.02, 0.06), (0.55, 0.04, -0.03), 0.08)),
                                                (((0.31, -0.18, -0.24), (0.42, -0.2, -0.38), 0.07))):
            kit.spike((bx * sx, by, bz), (tx * sx, ty, tz), rr, FUR if rr > 0.075 else FUR_DK, verts=14)
    tufts = [((0.0, 0.05, 0.38), (0.0, 0.22, 0.6)), ((0.2, 0.06, 0.34), (0.33, 0.24, 0.5)),
             ((-0.2, 0.06, 0.34), (-0.33, 0.24, 0.5)), ((0.1, 0.25, 0.3), (0.14, 0.48, 0.38)),
             ((-0.1, 0.25, 0.3), (-0.14, 0.48, 0.38)), ((0.25, 0.25, 0.12), (0.38, 0.45, 0.1)),
             ((-0.25, 0.25, 0.12), (-0.38, 0.45, 0.1)), ((0.0, 0.33, 0.08), (0.0, 0.56, 0.0)),
             ((0.15, 0.3, -0.15), (0.24, 0.48, -0.28)), ((-0.15, 0.3, -0.15), (-0.24, 0.48, -0.28))]
    for i, (b, t) in enumerate(tufts):
        kit.spike(b, t, 0.1, (FUR, FUR_DK, FUR_LT)[i % 3], verts=14)
    # ears
    for sx in (1, -1):
        kit.sphere((0.41 * sx, 0.03, -0.02), (0.06, 0.07, 0.1), FUR, segs=16, rings=8)
        kit.sphere((0.44 * sx, 0.0, -0.02), (0.035, 0.05, 0.07), FACE, segs=16, rings=8)
    # fierce golden eyes, slanted
    for sx in (1, -1):
        ex, ey, ez = 0.13 * sx, -0.395, 0.03
        rot = (0.15, 0, 0.32 * sx)
        kit.sphere((ex, ey, ez), (0.09, 0.035, 0.072), INK, rot=(0.15, -0.28 * sx, 0.32 * sx), segs=20, rings=10)
        kit.sphere((ex - 0.004 * sx, ey - 0.012, ez - 0.004), (0.068, 0.03, 0.056), GOLD_EYE,
                   rot=(0.15, -0.28 * sx, 0.32 * sx), segs=20, rings=10)
        kit.sphere((ex - 0.012 * sx, ey - 0.03, ez - 0.004), (0.026, 0.02, 0.046), INK, rot=rot, segs=12, rings=6)
        kit.sphere((ex - 0.035 * sx, ey - 0.035, ez + 0.025), 0.014, WHITE, segs=10, rings=5)
        # thick angry brow (inner end low)
        kit.tube([(0.03 * sx, -0.415, 0.115), (0.13 * sx, -0.41, 0.16), (0.25 * sx, -0.345, 0.2)], 0.034, FUR_DK,
                 taper_to=0.45, resolution=8, name='brow')
    # nose + fierce open grin with fangs
    for sx in (1, -1):
        kit.sphere((0.03 * sx, -0.43, -0.08), (0.018, 0.012, 0.012), INK, segs=10, rings=5)
    if mouth == 'grin':
        kit.sphere((0, -0.405, -0.19), (0.13, 0.04, 0.06), MOUTH, rot=(0.25, 0, 0), segs=24, rings=12)
        kit.sphere((0, -0.43, -0.165), (0.115, 0.03, 0.026), WHITE, rot=(0.25, 0, 0), segs=20, rings=10)
        for sx in (1, -1):
            kit.spike((0.065 * sx, -0.435, -0.165), (0.07 * sx, -0.44, -0.215), 0.017, WHITE, verts=10)
            kit.tube([(0.1 * sx, -0.42, -0.17), (0.145 * sx, -0.39, -0.135)], 0.01, INK, name='grin_corner')
    else:  # gritted: teeth band
        kit.sphere((0, -0.41, -0.18), (0.12, 0.04, 0.045), MOUTH, segs=24, rings=12)
        kit.sphere((0, -0.432, -0.18), (0.105, 0.03, 0.03), WHITE, segs=20, rings=10)
    # golden fillet + crest + plume sockets
    kit.torus((0, 0.0, 0.27), 0.335, 0.032, GOLD, rot=(0.12, 0, 0), scale=(1, 0.98, 1), major_segs=36, minor_segs=10)
    kit.sphere((0, -0.335, 0.245), (0.065, 0.03, 0.07), GOLD, segs=20, rings=10)
    kit.sphere((0, -0.36, 0.245), (0.028, 0.015, 0.032), RED, segs=12, rings=6)
    socks = []
    for sx in (1, -1):
        s = V((0.12 * sx, -0.3, 0.29))
        kit.rod(s + V((0, 0.01, -0.03)), s + V((0.01 * sx, -0.01, 0.06)), 0.028, GOLD, verts=12)
        socks.append(s + V((0.01 * sx, -0.01, 0.06)))
    return socks


def wk_torso():
    """Body-local (chibi coords: pelvis 0.66, shoulders 1.07, neck 1.17)."""
    kit.sphere((0, 0, 0.64), (0.24, 0.18, 0.15), PANTS, segs=24, rings=12)
    kit.sphere((0, 0, 0.92), (0.26, 0.2, 0.25), IRON, segs=24, rings=12)
    kit.sphere((0, -0.05, 0.97), (0.22, 0.17, 0.17), IRON, segs=24, rings=12)       # chest plate swell
    # gold trims
    kit.torus((0, 0, 0.8), 1.0, 0.018, GOLD, scale=(0.245, 0.19, 1), major_segs=32, minor_segs=6)
    kit.torus((0, 0, 1.09), 1.0, 0.016, GOLD, scale=(0.17, 0.13, 1), major_segs=32, minor_segs=6)
    pts = []
    for z in (1.08, 1.0, 0.92, 0.84):
        y = -0.17 * math.sqrt(max(0, 1 - ((z - 0.97) / 0.17) ** 2)) - 0.05 if abs(z - 0.97) < 0.17 else -0.18
        pts.append((0, min(y, -0.2 * math.sqrt(max(0, 1 - ((z - 0.92) / 0.25) ** 2))) - 0.004, z))
    kit.tube(pts, 0.013, GOLD, name='ridge')
    kit.sphere((0, -0.225, 0.95), (0.05, 0.018, 0.05), GOLD, segs=20, rings=10)
    kit.sphere((0, -0.24, 0.95), (0.024, 0.012, 0.024), RED, segs=12, rings=6)
    # fur collar ruff
    kit.torus((0, 0, 1.13), 0.15, 0.07, FUR, major_segs=32, minor_segs=12)
    for k in range(10):
        t = k / 10 * math.tau + 0.3
        d = V((math.sin(t), -math.cos(t), 0))
        kit.spike(V((0, 0, 1.13)) + d * 0.17, V((0, 0, 1.07)) + d * 0.28, 0.055, (FUR, FUR_DK)[k % 2], verts=10)
    kit.cylinder((0, 0, 1.2), 0.1, 0.1, FUR)
    # red sash + gold buckle
    kit.torus((0, 0, 0.73), 1.0, 0.05, RED, scale=(0.245, 0.19, 1), major_segs=32, minor_segs=10)
    kit.sphere((0, -0.235, 0.73), (0.055, 0.02, 0.045), GOLD, segs=20, rings=10)


def wk_skirt(front_len=0.26, flare=0.25, side_flare=0.5):
    """Red loin cloth + orange side flaps + iron tassets (body-local)."""
    def panel(top, width, length, yaw, tilt, m, hem=None, thick=0.03):
        R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-tilt, 3, 'X')
        kit.box(V(top) + R @ V((0, 0, -length / 2)), (width, thick, length), m, rot=R.to_euler(), bevel=0.01)
        if hem:
            kit.box(V(top) + R @ V((0, 0, -length)), (width + 0.01, thick + 0.012, 0.035), hem, rot=R.to_euler(),
                    bevel=0.01)
    panel((0, -0.2, 0.71), 0.17, front_len, 0, flare, RED, hem=GOLD)
    for sx in (1, -1):
        panel((0.22 * sx, -0.06, 0.72), 0.16, 0.2, math.pi / 2 * sx * -1 + 0 * sx, side_flare, IRON, hem=GOLD)
        panel((0.13 * sx, -0.18, 0.71), 0.09, front_len * 0.85, 0.5 * sx, flare + 0.1, ORANGE)


def wk_arm(shoulder, hand, hint, grip_axis=None, fist_dir=None, pauldron_up=None, lengths=(UPPER, FORE)):
    """World-space arm. grip_axis: fist closed round an axis through `hand` (e.g. a pole)."""
    shoulder, hand = V(shoulder), V(hand)
    elbow = joint(shoulder, hand, lengths[0], lengths[1], hint)
    kit.rod(shoulder, elbow, 0.085, FUR, verts=14)
    fore = hand - elbow
    kit.rod(elbow, hand - fore.normalized() * 0.06, 0.072, FUR, verts=14)
    b0, b1 = elbow + fore * 0.28, elbow + fore * 0.78
    kit.rod(b0, b1, 0.082, IRON_DK, verts=14)
    for p in (b0, b1):
        kit.torus(p, 0.083, 0.012, GOLD, rot=kit.rot_between((0, 0, 0), fore), major_segs=24, minor_segs=6)
    # pauldron: stacked domes following the upper arm
    arm = (elbow - shoulder).normalized()
    up = V(pauldron_up) if pauldron_up else V((0, 0, 1))
    up = (up - arm * up.dot(arm)).normalized()
    for k, s in enumerate((1.0, 0.8)):
        c = shoulder + arm * (0.02 + k * 0.08) + up * (0.07 - k * 0.015)
        dome(c, up, (0.14 * s, 0.13 * s, 0.06 * s), IRON if k == 0 else IRON_DK, rim=GOLD)
    if grip_axis is not None:
        # fist wrapped round the pole: a chunky mitt centred on the pole line + a row of knuckles
        ax = V(grip_axis).normalized()
        kit.sphere(hand, (0.1, 0.085, 0.095), HAND, segs=24, rings=12)
        for k in range(4):
            z = (k - 1.5) * 0.042
            kit.sphere(hand + ax * z + V((0.0, -0.075, 0)), (0.03, 0.026, 0.024), HAND, segs=12, rings=6)
        kit.sphere(hand + ax * 0.075 + V((0.03, -0.03, 0)), (0.035, 0.03, 0.03), HAND, segs=12, rings=6)  # thumb
    else:
        d = V(fist_dir) if fist_dir else fore.normalized()
        aligned(hand, (0.085, 0.08, 0.095), d, HAND)
        kit.sphere(hand + d * 0.06, (0.07, 0.07, 0.07), HAND, segs=16, rings=8)
    return elbow


def wk_leg(hip, ankle, hint, foot_dir, knee_plate=True, lengths=(THIGH, SHIN)):
    hip, ankle = V(hip), V(ankle)
    knee = joint(hip, ankle, lengths[0], lengths[1], hint)
    kit.rod(hip, knee, 0.11, PANTS, verts=14, r2=0.095)
    kit.sphere(knee, 0.095, PANTS, segs=16, rings=8)
    shin = ankle - knee
    kit.rod(knee + shin * 0.15, ankle, 0.085, WRAP, verts=14, r2=0.07)
    ax = kit.rot_between((0, 0, 0), shin)
    for k, t in enumerate((0.35, 0.58, 0.8)):
        kit.torus(knee + shin * t, 0.08 - 0.01 * t, 0.012, kit.mat('#5a4630', 0.8), rot=ax, major_segs=20, minor_segs=5)
    kit.torus(knee + shin * 0.17, 0.09, 0.014, GOLD, rot=ax, major_segs=20, minor_segs=6)
    if knee_plate:
        thigh = (knee - hip).normalized()
        out = (-thigh + shin.normalized()) * -0.5
        n = out.normalized() if out.length > 1e-3 else V((0, -1, 0))
        dome(knee + n * 0.07, n, (0.08, 0.08, 0.035), IRON, rim=GOLD)
    fd = V(foot_dir).normalized()
    aligned(ankle + fd * 0.07 + V((0, 0, -0.01)), (0.085, 0.075, 0.15), fd, SHOE)
    return knee


def wk_tail(points, r=0.045):
    kit.tube(points, r, FUR, taper_to=0.55, resolution=8, name="tail")
    tip = V(points[-1])
    d0 = (V(points[-1]) - V(points[-2])).normalized()
    for k in range(6):
        a = k / 6 * math.tau
        side = d0.orthogonal().normalized()
        side.rotate(Matrix.Rotation(a, 3, d0))
        d = (d0 * 0.8 + side * 0.6).normalized()
        kit.spike(tip - d0 * 0.02, tip + d * 0.09, 0.03, FUR_DK if k % 2 else FUR, verts=10)
