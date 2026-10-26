"""Izuku Midoriya "Deku" (My Hero Academia) — hero costume, Full Cowl: One For All lightning, Smash punch."""
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import Vector  # noqa: E402

V = Vector
random.seed(11)
kit.reset()

SKIN = '#f3cfb0'
SUIT = '#1d6f5b'
SUIT_DK = '#124838'
BLACK = '#17191b'
HAIR = '#1e5034'
WHITE = '#f3f4f1'
RED = '#d6232a'
MK = 1 / 0.68  # a lone metaball's visible size is ~0.68x the requested size

# extra arm poses (offsets from the shoulder, figure's LEFT side; mirrored for the right)
kit.HERO_ARM_POSES['smash'] = ((0.11, -0.23, -0.05), (0.17, -0.47, 0.02))      # straight punch, shoulder height
kit.HERO_ARM_POSES['chamber'] = ((0.11, 0.17, -0.17), (0.12, 0.02, -0.33))    # fist pulled back to the hip

a = kit.hero(skin=SKIN, top=SUIT, bottom=SUIT, shoes=RED, hands=WHITE, iris='#2fae55', sleeves='long',
             pants='long', mouth='line', brows=None, right_arm='smash', left_arm='chamber', stance='wide',
             build=1.12)
H = a['head']
BODY = ['top_mesh', 'bottom_mesh', 'skin_mesh', 'dk_suit_mesh']


# ── local helpers ────────────────────────────────────────────────────────

def remove_where(pred):
    for o in [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and not o.name.endswith('_mesh') and pred(o.location)]:
        bpy.data.objects.remove(o, do_unlink=True)


def strip_verts(name, pred):
    o = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if pred(v.co)], context='VERTS')
    bm.to_mesh(o.data)
    bm.free()


def hit(names, origin, direction, dist=10.0):
    """Nearest ray hit against the named meshes -> (location, normal) or (None, None)."""
    best = (None, None, 1e9)
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        ok, loc, nor, _ = o.ray_cast(V(origin), V(direction).normalized(), distance=dist)
        if ok and (loc - V(origin)).length < best[2]:
            best = (loc, nor, (loc - V(origin)).length)
    return best[0], best[1]


def shell(names, center, direction, max_d=0.3):
    """Outermost body surface seen from inside: cast outward from `center` (ignores limbs further out)."""
    best = (None, None, -1)
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        ok, loc, nor, _ = o.ray_cast(V(center), V(direction).normalized(), distance=max_d)
        if ok and (loc - V(center)).length > best[2]:
            best = (loc, nor, (loc - V(center)).length)
    if best[0] is None:
        return None, None
    nor = best[1] if best[1].dot(V(direction)) > 0 else -best[1]
    return best[0], nor


def face(x, z, lift=0.0):
    loc, nor = hit([HEAD_MESH], (x, -1.0, z), (0, 1, 0))
    if loc is None:  # fall back to the analytic cranium ellipsoid
        d = V(((x - HEADC.x) / HR[0], 0, (z - HEADC.z) / HR[2]))
        t = max(1e-4, 1 - d.x ** 2 - d.z ** 2)
        loc = V((x, HEADC.y - HR[1] * math.sqrt(t), z))
        nor = V(((x - HEADC.x) / HR[0] ** 2, (loc.y - HEADC.y) / HR[1] ** 2, (z - HEADC.z) / HR[2] ** 2)).normalized()
    return loc + nor * lift, nor


def decal(x, z, scale, m, lift=0.0, segs=20, rings=10, roll=0.0):
    p, n = face(x, z, lift)
    q = V((0, -1, 0)).rotation_difference(n)
    rot = (q.to_matrix() @ kit.Euler((0, roll, 0)).to_matrix()).to_euler()
    return kit.sphere(p, scale, m, rot=rot, segs=segs, rings=rings)


def half_decal(x, z, scale, m, lift=0.0):
    """Lower half of a face decal (flat top edge) — D-shaped open mouth."""
    obj = decal(x, z, scale, m, lift=lift, segs=24, rings=12)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0),
                                 plane_no=(0, 0, 1), clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=[e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)])
    bm.to_mesh(obj.data)
    bm.free()
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def face_curve(pts_xz, radius, m, lift=0.002, taper=None):
    return kit.tube([tuple(face(x, z, lift)[0]) for x, z in pts_xz], radius, m, resolution=6, taper_to=taper)


def body_curve(pts, radius, m, lift=0.003, axis_x=0.0, axis_y=0.0):
    """Tube running over the torso surface; points are projected out from the body's vertical axis."""
    out = []
    for p in pts:
        p = V(p)
        c = V((axis_x, axis_y, p.z))
        loc, nor = shell(BODY, c, p - c)
        out.append(tuple(loc + nor * lift) if loc is not None else tuple(p))
    return kit.tube(out, radius, m, resolution=6, name='trim')


def band(z, lift, radius, m, n=48, tilt=0.0, center=(0, 0)):
    """Closed ring hugging the body at height z (belt, collar)."""
    pts = []
    c = V((center[0], center[1], z))
    for i in range(n + 1):
        ang = math.tau * i / n
        d = V((math.sin(ang), -math.cos(ang), tilt * -math.cos(ang)))
        loc, nor = shell(BODY, c, d)
        pts.append(tuple(loc + nor * lift) if loc is not None else tuple(c + d * 0.15))
    return kit.tube(pts, radius, m, smooth_path=False, name='band')


def no_ink(obj):
    """Freestyle face-mark: glowing energy is excluded from the ink outline in the thumbnail."""
    attr = obj.data.attributes.get('freestyle_face') or obj.data.attributes.new('freestyle_face', 'BOOLEAN', 'FACE')
    attr.data.foreach_set('value', [True] * len(obj.data.polygons))
    return obj


def bolt(points, r, m, jitter=0.01):
    pts = [tuple(V(p) + V([random.uniform(-jitter, jitter) for _ in range(3)])) for p in points]
    return no_ink(kit.tube(pts, r, m, smooth_path=False, name='bolt'))


def helix_bolt(a0, a1, rad, turns, m, n=12, r=0.0045, start=None, jitter=0.01):
    """Jagged lightning arc spiralling around the segment a0 -> a1."""
    a0, a1 = V(a0), V(a1)
    axis = (a1 - a0).normalized()
    u = axis.cross(V((0, 0, 1)) if abs(axis.z) < 0.9 else V((1, 0, 0))).normalized()
    v = axis.cross(u)
    start = random.uniform(0, math.tau) if start is None else start
    pts = []
    for i in range(n):
        t = i / (n - 1)
        ang = start + turns * math.tau * t
        rr = rad * (1 + (0.25 if i % 2 else -0.15))  # zig-zag in and out
        pts.append(a0.lerp(a1, t) + (u * math.cos(ang) + v * math.sin(ang)) * rr)
    return bolt(pts, r, m, jitter)


def oriented(n):
    return V((0, -1, 0)).rotation_difference(n).to_euler()


# ── body tweaks ──────────────────────────────────────────────────────────
# kit's small realistic face features + its head -> replaced by a sculpted anime head
remove_where(lambda p: p.y < H.y - 0.07 and abs(p.z - H.z) < 0.12 and abs(p.x) < 0.09)
strip_verts('skin_mesh', lambda c: c.z > 1.585 and abs(c.x) < 0.14 and -0.17 < c.y < 0.13)

HEADC, HR = V((0, -0.005, 1.70)), (0.1, 0.108, 0.112)
HEAD_MESH = 'dk_head_mesh'
HD = kit._meta('dk_head')
kit.blob_ellipsoid(HD, HEADC, tuple(r * MK for r in HR))
kit.blob_ellipsoid(HD, (0, -0.035, 1.635), (0.074 * MK, 0.074 * MK, 0.062 * MK))       # jaw
kit.blob_ellipsoid(HD, (0, -0.074, 1.588), (0.028 * MK, 0.024 * MK, 0.02 * MK))        # chin
kit.blob_ellipsoid(HD, (0, -0.11, 1.664), (0.008 * MK, 0.011 * MK, 0.015 * MK), rot=(-0.3, 0, 0))  # nose
for sx in (1, -1):
    kit.blob_ellipsoid(HD, (0.05 * sx, -0.072, 1.648), (0.034 * MK, 0.026 * MK, 0.03 * MK))   # cheeks
    kit.blob_ellipsoid(HD, (0.098 * sx, 0.0, 1.685), (0.012 * MK, 0.022 * MK, 0.03 * MK))     # ears
kit.blob_limb(HD, (0, 0.0, 1.5), (0, 0.0, 1.6), 0.042 * MK, 0.045 * MK)                     # neck

# heroic upper-body bulk over the suit (pecs, lats, obliques) — kills the kit's narrow waist
SU = kit._meta('dk_suit')
kit.blob_ellipsoid(SU, (0, 0.005, 1.2), (0.14 * MK, 0.088 * MK, 0.17 * MK))  # straight, athletic waist
for sx in (1, -1):
    kit.blob_ellipsoid(SU, (0.12 * sx, 0.03, 1.3), (0.06 * MK, 0.07 * MK, 0.09 * MK))  # lats -> V taper
kit.solidify_blobs({'dk_head': kit.mat(SKIN, 0.5), 'dk_suit': kit.mat(SUIT, 0.75)})
# matte cloth: kill the glossy highlight on the suit
for _n in ('top_mesh', 'bottom_mesh', 'dk_suit_mesh'):
    for _m in bpy.data.objects[_n].data.materials:
        _m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.92

M_SUIT, M_SUIT_DK = kit.mat(SUIT, 0.75), kit.mat(SUIT_DK, 0.75)
M_BLACK = kit.mat(BLACK, 0.6)
M_WHITE = kit.mat(WHITE, 0.45)
M_GREY = kit.mat('#a9b0b4', 0.3, metal=0.6)
M_DGREY = kit.mat('#3c4246', 0.55)
M_RED = kit.mat(RED, 0.3)
M_HAIR = kit.mat(HAIR, 0.6)
M_BOLT = kit.mat('#29e81a', 0.4, emit=3.0)
M_BOLT_HOT = kit.mat('#7CFF6B', 0.3, emit=2.0)

# ── face: big anime eyes, freckles, thick brows, determined grin ─────────
M_EYE_W = kit.mat('#fbfbf7', 0.3)
M_DARK = kit.mat('#101614', 0.3)
M_IRIS = kit.mat('#23a34b', 0.2)
M_IRIS_LT = kit.mat('#8be89a', 0.2)
for sx in (1, -1):
    ex, ez = 0.043 * sx, 1.698
    decal(ex, ez, (0.025, 0.008, 0.015), M_EYE_W, lift=-0.001, roll=0.1 * sx)
    decal(ex - 0.002 * sx, ez - 0.001, (0.0135, 0.007, 0.0155), M_IRIS, lift=0.003)
    decal(ex - 0.002 * sx, ez - 0.006, (0.009, 0.006, 0.007), M_IRIS_LT, lift=0.0055, segs=12, rings=6)
    decal(ex - 0.002 * sx, ez, (0.0058, 0.006, 0.0072), M_DARK, lift=0.0065, segs=12, rings=6)
    decal(ex - 0.008 * sx, ez + 0.006, (0.004, 0.004, 0.004), M_EYE_W, lift=0.009, segs=10, rings=5)
    # heavy upper lash line, flicked at the outer corner
    face_curve([(ex - 0.026 * sx, ez + 0.003), (ex - 0.008 * sx, ez + 0.0145), (ex + 0.016 * sx, ez + 0.0135),
                (ex + 0.031 * sx, ez + 0.004)], 0.0032, M_DARK, lift=0.003)
    face_curve([(ex - 0.012 * sx, ez - 0.0148), (ex + 0.012 * sx, ez - 0.014)], 0.0012, M_DARK, lift=0.002)
    # determined brows: low and angled toward the nose
    face_curve([(0.016 * sx, 1.72), (0.04 * sx, 1.73), (0.068 * sx, 1.735)], 0.0045, kit.mat('#123826', 0.6),
               lift=0.003, taper=0.45)
    # freckles
    for fx, fz in ((0.052, 1.667), (0.062, 1.672), (0.072, 1.665), (0.06, 1.66)):
        decal(fx * sx, fz, (0.0028, 0.002, 0.0028), kit.mat('#9a5a34', 0.6), lift=0.0, segs=8, rings=4)
# grin with clenched top teeth
half_decal(0, 1.61, (0.03, 0.008, 0.017), kit.mat('#5e1717', 0.5), lift=0.0)
half_decal(0, 1.6098, (0.027, 0.006, 0.0068), M_WHITE, lift=0.0025)
for sx in (1, -1):
    face_curve([(0.036 * sx, 1.615), (0.031 * sx, 1.61)], 0.0015, kit.mat('#7a3a30', 0.5), lift=0.001)

# ── hair: bushy curly mass + layered rounded tufts ───────────────────────
HC = HEADC + V((0, 0.018, 0.02))


def fib(n):
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        rr = math.sqrt(1 - z * z)
        yield V((rr * math.cos(g * i), rr * math.sin(g * i), z))


def on_scalp(d):
    """Keep hair off the face and jaw."""
    if d.z < -0.5:
        return False
    if d.y < -0.15 and d.z < 0.5:
        return False
    if d.y < 0.3 and d.z < -0.05:
        return False
    return True


HB = kit._meta('dk_hair')
kit.blob_ellipsoid(HB, HC, (0.104 * MK, 0.11 * MK, 0.1 * MK))
for d in fib(80):
    if not on_scalp(d):
        continue
    p = HC + V((d.x * 0.1, d.y * 0.106, d.z * 0.1))
    kit.blob_ball(HB, p, random.uniform(0.032, 0.042) * MK)
kit.solidify_blobs({'dk_hair': M_HAIR})


def tuft(root, out, length, rad, curl_dir, curl=0.8, taper=0.08):
    """A rounded hair clump: grows along `out`, then curls toward `curl_dir`."""
    out, curl_dir = V(out).normalized(), V(curl_dir).normalized()
    p0 = V(root)
    p1 = p0 + out * length * 0.5
    p2 = p1 + (out * 0.7 + curl_dir * 0.5 * curl).normalized() * length * 0.35
    p3 = p2 + (out * 0.1 + curl_dir * curl).normalized() * length * 0.25
    kit.tube([tuple(p0), tuple(p1), tuple(p2), tuple(p3)], rad, M_HAIR, taper_to=taper, resolution=4, name='hair')


for count, rmul, lmin, lmax in ((80, 0.95, 0.07, 0.1), (44, 1.05, 0.09, 0.12)):
    for d in fib(count):
        d = (d + V([random.uniform(-0.15, 0.15) for _ in range(3)])).normalized()
        if not on_scalp(d) or (d.y < 0.0 and d.z < 0.62):
            continue
        root = HC + V((d.x * 0.11, d.y * 0.115, d.z * 0.11)) * rmul
        out = d + V((0, 0.2, 0.12 if d.z > -0.2 else -0.15))
        side = d.cross(V((0, 0, 1)) if abs(d.z) < 0.95 else V((1, 0, 0))).normalized() * random.choice((1, -1))
        tuft(root, out, random.uniform(lmin, lmax), random.uniform(0.026, 0.034), side - d * 0.4,
             curl=random.uniform(0.7, 1.1))

# fringe: clumps falling over the forehead, curling in different directions
for x, end_z, flick in ((-0.075, 1.75, -1), (-0.04, 1.743, 1), (-0.005, 1.748, -1), (0.03, 1.742, 1),
                        (0.065, 1.75, 1), (-0.095, 1.77, -1), (0.095, 1.77, 1)):
    top, n = face(x * 0.8, 1.77, 0.012)
    root = V((x * 0.7, top.y + 0.04, 1.82))
    p1 = V((x, top.y - 0.008, 1.79))
    p2 = V((x + 0.01 * flick, top.y - 0.012, end_z + 0.012))
    p3 = V((x + 0.022 * flick, top.y - 0.008, end_z))
    kit.tube([tuple(root), tuple(p1), tuple(p2), tuple(p3)], 0.022, M_HAIR, taper_to=0.12, resolution=5,
             name='fringe')
# sideburns in front of the ears
for sx in (1, -1):
    s0, _ = face(0.09 * sx, 1.71, 0.004)
    kit.tube([tuple(s0 + V((0, 0.01, 0.03))), tuple(s0), tuple(s0 + V((0.004 * sx, -0.004, -0.035)))], 0.015,
             M_HAIR, taper_to=0.3, resolution=5, name='sideburn')

# ── costume ─────────────────────────────────────────────────────────────
# black trim lines down the chest and black side panels
for sx in (1, -1):
    for dy in (-0.02, 0.0, 0.02):
        body_curve([(0.3 * sx, dy, z) for z in (1.3, 1.22, 1.14, 1.06)], 0.012, M_BLACK, lift=0.0)
# zip line
body_curve([(0, -0.2, z) for z in (1.47, 1.35, 1.2, 1.05)], 0.004, M_SUIT_DK)
# high collar
kit.cone((0, 0.0, 1.49), 0.085, 0.054, 0.11, M_SUIT, verts=32)
kit.torus((0, 0.0, 1.54), 0.054, 0.007, M_SUIT_DK, major_segs=24, minor_segs=6)
band(1.475, 0.004, 0.012, M_SUIT_DK, tilt=0.15)

# utility belt: black strap, metal buckle, pouches
band(1.0, 0.006, 0.018, M_BLACK, tilt=0.1)
bl, bn = shell(BODY, (0, 0, 0.985), (0, -1, 0))
kit.box(bl + bn * 0.022, (0.05, 0.012, 0.032), M_GREY, bevel=0.006)
for sx in (1, -1):
    for ang in (0.8, 1.4, 2.2):
        d = V((math.sin(ang) * sx, -math.cos(ang), 0))
        loc, nor = shell(BODY, V((0, 0, 0.965)), d)
        kit.box(loc + nor * 0.026, (0.045, 0.03, 0.05), M_DGREY, rot=(0, 0, math.atan2(nor.x, -nor.y)),
                bevel=0.008)

# hood bunched behind the neck
kit.subdivide(kit.torus((0, 0.045, 1.49), 0.07, 0.026, M_SUIT_DK, rot=(0.6, 0, 0), major_segs=24, minor_segs=8), 1)

# mouth-guard mask hanging around the neck
kit.torus((0, -0.01, 1.485), 0.068, 0.008, M_DGREY, rot=(0.55, 0, 0), major_segs=24, minor_segs=6)
mloc, mnor = shell(BODY, (0, 0, 1.44), (0, -1, 0.15))
mc = mloc + mnor * 0.016
mrot = oriented(mnor)
kit.subdivide(kit.sphere(mc, (0.058, 0.02, 0.03), kit.mat('#d5d9d9', 0.35), rot=mrot, segs=20, rings=10), 1)
kit.sphere(mc + mnor * 0.012, (0.024, 0.012, 0.022), M_DGREY, rot=mrot, segs=16, rings=8)
for dz in (-0.009, 0.0, 0.009):
    kit.box(mc + mnor * 0.023 + V((0, 0, dz)), (0.022, 0.004, 0.0032), M_BLACK, rot=mrot)

# armoured forearm braces with grey bands + chunky gloved fists
for side in ('l', 'r'):
    el, hd = a[f'elbow_{side}'], a[f'hand_{side}']
    fore = hd - el
    kit.rod(el + fore * 0.3, el + fore * 0.78, 0.042, M_WHITE, verts=20)
    for t in (0.38, 0.72):
        kit.torus(el + fore * t, 0.043, 0.006, M_GREY, rot=kit.rot_between(el, hd), major_segs=20, minor_segs=6)
    kit.subdivide(kit.sphere(hd + fore.normalized() * 0.005, (0.04, 0.038, 0.046), M_WHITE,
                             rot=kit.rot_between(el, hd), segs=16, rings=8), 1)

# knee pads
for side in ('l', 'r'):
    k = a[f'knee_{side}']
    loc, nor = shell(BODY, k + V((0, 0.02, 0)), (0, -1, 0))
    if loc is not None:
        kit.subdivide(kit.sphere(loc + nor * 0.004, (0.048, 0.026, 0.055), M_BLACK, rot=oriented(nor),
                                 segs=16, rings=8), 1)

# chunky red boots with thick white soles (own metaball family so they melt into one shape)
BOOT = kit._meta('dk_boots')
for side, sx in (('l', 1), ('r', -1)):
    ankle = V((0.17 * sx, 0.01, 0.1))
    kit.blob_limb(BOOT, ankle + V((0, 0, 0.16)), ankle, 0.05 * MK, 0.047 * MK)
    kit.blob_ellipsoid(BOOT, ankle + V((0, -0.065, -0.05)), (0.055 * MK, 0.1 * MK, 0.045 * MK))
    kit.blob_ellipsoid(BOOT, ankle + V((0, 0.0, -0.045)), (0.052 * MK, 0.06 * MK, 0.05 * MK))
    kit.subdivide(kit.sphere(ankle + V((0, -0.05, -0.098)), (0.064, 0.14, 0.02), M_WHITE, segs=24, rings=10), 1)
    kit.torus(ankle + V((0, 0, 0.165)), 0.05, 0.01, M_RED, major_segs=24, minor_segs=6)
    for dz, dy in ((-0.005, -0.1), (0.03, -0.075)):
        kit.box(ankle + V((0, dy, dz)), (0.08, 0.012, 0.014), M_WHITE, rot=(-0.7, 0, 0), bevel=0.004)
kit.solidify_blobs({'dk_boots': M_RED})

# ── One For All: Full Cowl lightning ─────────────────────────────────────
sh_r, el_r, hd_r = a['shoulder_r'], a['elbow_r'], a['hand_r']
tipv = (hd_r - el_r).normalized()
fist_end = hd_r + tipv * 0.05
helix_bolt(sh_r, fist_end, 0.075, 1.6, M_BOLT, n=18, r=0.008, start=0.3)
helix_bolt(el_r - (el_r - sh_r) * 0.4, fist_end, 0.07, 1.0, M_BOLT_HOT, n=12, r=0.007, start=2.5)
helix_bolt(sh_r, el_r, 0.075, 0.6, M_BOLT_HOT, n=8, r=0.007, start=4.4)
# arcs leaping forward off the fist, each with a short side branch
u = tipv.cross(V((0, 0, 1))).normalized()
v = tipv.cross(u)
for i, ang in enumerate((0.5, 2.2, 3.6, 5.1)):
    d = (u * math.cos(ang) + v * math.sin(ang))
    pts = [hd_r + tipv * 0.02 + d * 0.045]
    for k in range(4):
        pts.append(pts[-1] + tipv * 0.035 + d * (0.025 if k % 2 == 0 else -0.004) + v * 0.01 * (-1) ** k)
    bolt(pts, 0.0075, M_BOLT_HOT if i % 2 else M_BOLT, jitter=0.006)
    br = pts[2]
    bolt([br, br + d * 0.03 + tipv * 0.01, br + d * 0.045 + tipv * 0.03], 0.005, M_BOLT, jitter=0.004)
# glowing veins on the punching upper arm
for t in (0.3, 0.65):
    p = sh_r.lerp(el_r, t)
    bolt([p + V((0, -0.05, 0.03)), p + V((0.01, -0.055, 0.0)), p + V((-0.01, -0.05, -0.03))], 0.0028, M_BOLT,
         jitter=0.003)
# arcs crawling up the legs and the other arm
for side in ('l', 'r'):
    helix_bolt(a[f'knee_{side}'] + V((0, 0, -0.33)), a[f'knee_{side}'], 0.075, 0.7, M_BOLT, n=9, r=0.006)
    helix_bolt(a[f'knee_{side}'], a[f'hip_{side}'] + V((0, 0, -0.08)), 0.09, 0.6, M_BOLT_HOT, n=9, r=0.006)
helix_bolt(a['elbow_l'], a['hand_l'], 0.065, 0.8, M_BOLT, n=8, r=0.006)

# ── dynamic pose: lunge (left leg forward, right back), torso twisted into the punch, slight lean ──
def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def pose_deform(twist=0.0, lean=0.0, fwd_l=0.0, fwd_r=0.0, knee_fwd=0.0, knee_out=0.0, crouch=1.0,
                pivot_z=1.0, hip_z=0.95, knee_z=0.52):
    """Re-pose the finished statue: lunge (legs sheared forward/back), bent knees + crouch,
    upper body twisted and leaning above the waist."""
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in meshes:
        n = len(o.data.vertices)
        co = np.empty(n * 3)
        o.data.vertices.foreach_get('co', co)
        co = co.reshape(n, 3)
        x, y, z = co[:, 0].copy(), co[:, 1].copy(), co[:, 2].copy()
        wl, wr = smooth(-0.02, 0.06, x), smooth(0.02, -0.06, x)
        below = np.clip(hip_z - z, 0, None)
        hat = np.clip(np.minimum((hip_z - z) / (hip_z - knee_z), z / knee_z), 0, 1)
        y += -(fwd_l * wl + fwd_r * wr) * below - knee_fwd * hat * (wl + wr)
        x += knee_out * hat * (wl - wr)
        w = smooth(pivot_z - 0.02, pivot_z + 0.2, z)
        ang = twist * w
        c, s = np.cos(ang), np.sin(ang)
        x2, y2 = x * c - y * s, x * s + y * c
        lz = z - pivot_z
        la = lean * w
        y3 = y2 * np.cos(la) - lz * np.sin(la)
        z3 = y2 * np.sin(la) + lz * np.cos(la) + pivot_z
        z3 = np.where(z3 < hip_z, z3 * crouch, z3 - hip_z * (1 - crouch))
        o.data.vertices.foreach_set('co', np.stack([x2, y3, z3], 1).ravel())
        o.data.update()


pose_deform(twist=0.15, lean=0.1, fwd_l=0.12, fwd_r=-0.12, knee_fwd=0.07, knee_out=0.035, crouch=0.9)

# thumbnail ink: skip face-marked (glowing) geometry; kit.render_thumbnail configures the rest of this lineset
_fs = bpy.context.view_layer.freestyle_settings
_ls = _fs.linesets[0] if len(_fs.linesets) else _fs.linesets.new('ink')
_ls.select_by_face_marks = True
_ls.face_mark_negation = 'EXCLUSIVE'
_ls.face_mark_condition = 'ONE'

kit.finalize('deku')
