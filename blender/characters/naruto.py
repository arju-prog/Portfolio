"""Naruto Uzumaki (Naruto Shippuden) — orange/black jumpsuit, Leaf headband, spiky blond hair, Rasengan."""
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
random.seed(5)
kit.reset()

SKIN = '#f5c9a0'
ORANGE = '#ff7a12'
BLACK = '#1d1e24'
HAIR = '#ffcf26'
HAIR_DK = '#f0a81a'
BLUE = '#2a56b8'
CLOTH = '#1f2f63'
STEEL = '#cfd6de'
MK = 1 / 0.68  # a lone metaball's visible size is ~0.68x the requested size

# extra arm poses (offsets from the shoulder, figure's LEFT side; mirrored for the right)
kit.HERO_ARM_POSES['offer'] = ((0.15, -0.1, -0.2), (0.24, -0.31, -0.19))    # hand forward, palm up (Rasengan)
kit.HERO_ARM_POSES['chamber'] = ((0.11, 0.17, -0.17), (0.12, 0.02, -0.33))  # fist pulled back to the hip

a = kit.hero(skin=SKIN, top=ORANGE, bottom=ORANGE, shoes=BLUE, iris='#2f86e8', sleeves='long', pants='long',
             mouth='line', brows=None, right_arm='chamber', left_arm='offer', stance='wide', build=1.1)
H = a['head']
BODY = ['top_mesh', 'bottom_mesh', 'skin_mesh', 'nr_suit_mesh']


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
    """Outermost surface seen from inside: cast outward from `center` (ignores limbs further out)."""
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
    if loc is None:
        d = V(((x - HEADC.x) / HR[0], 0, (z - HEADC.z) / HR[2]))
        t = max(1e-4, 1 - d.x ** 2 - d.z ** 2)
        loc = V((x, HEADC.y - HR[1] * math.sqrt(t), z))
        nor = V(((x - HEADC.x) / HR[0] ** 2, (loc.y - HEADC.y) / HR[1] ** 2, (z - HEADC.z) / HR[2] ** 2)).normalized()
    return loc + nor * lift, nor


def oriented(n):
    return V((0, -1, 0)).rotation_difference(n).to_euler()


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


def ring_pts(names, c, n=48, tilt=0.0, lift=0.004, max_d=0.3):
    pts = []
    for i in range(n):
        ang = math.tau * i / n
        d = V((math.sin(ang), -math.cos(ang), 0))
        d.z = tilt * d.y
        loc, nor = shell(names, c, d, max_d)
        pts.append(loc + nor * lift if loc is not None else V(c) + d * 0.12)
    return pts


def band(names, z, lift, radius, m, n=48, tilt=0.0, center=(0, 0)):
    pts = ring_pts(names, V((center[0], center[1], z)), n, tilt, lift)
    return kit.tube([tuple(p) for p in pts + pts[:1]], radius, m, smooth_path=False, name='band')


def ribbon(points, width, m, up=(0, 0, 1), thick=0.004, closed=False, widths=None):
    """Flat cloth strip through `points`, `width` measured along `up` (headband, tails)."""
    up = V(up).normalized()
    me = bpy.data.meshes.new('ribbon')
    bm = bmesh.new()
    rows = []
    for i, p in enumerate(points):
        w = (widths[i] if widths else width) / 2
        rows.append((bm.verts.new(V(p) - up * w), bm.verts.new(V(p) + up * w)))
    for i in range(len(rows) - (0 if closed else 1)):
        r0, r1 = rows[i], rows[(i + 1) % len(rows)]
        bm.faces.new((r0[0], r1[0], r1[1], r0[1]))
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new('ribbon', me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('solid', 'SOLIDIFY')
    mod.thickness = thick
    mod.offset = 0
    kit.subdivide(obj, 1)
    return kit._finish(obj, m, True)


def no_ink(obj):
    """Freestyle face-mark: glowing energy is excluded from the ink outline in the thumbnail."""
    attr = obj.data.attributes.get('freestyle_face') or obj.data.attributes.new('freestyle_face', 'BOOLEAN', 'FACE')
    attr.data.foreach_set('value', [True] * len(obj.data.polygons))
    return obj


def glass(hex_color, alpha, emit):
    """Translucent emissive material (own instance so kit's cache isn't affected)."""
    m = bpy.data.materials.new(f'glass_{hex_color.strip("#")}')
    if hasattr(m, 'use_nodes') and not m.use_nodes:
        m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    col = kit.rgba(hex_color)
    b.inputs['Base Color'].default_value = col
    b.inputs['Roughness'].default_value = 0.1
    b.inputs['Emission Color'].default_value = col
    b.inputs['Emission Strength'].default_value = emit
    b.inputs['Alpha'].default_value = alpha
    if hasattr(m, 'surface_render_method'):
        m.surface_render_method = 'BLENDED'
    if hasattr(m, 'blend_method'):
        try:
            m.blend_method = 'BLEND'
        except (TypeError, AttributeError):
            pass
    m.diffuse_color = col
    return m


def fib(n):
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        rr = math.sqrt(1 - z * z)
        yield V((rr * math.cos(g * i), rr * math.sin(g * i), z))


# ── body tweaks ──────────────────────────────────────────────────────────
remove_where(lambda p: p.y < H.y - 0.07 and abs(p.z - H.z) < 0.12 and abs(p.x) < 0.09)
strip_verts('skin_mesh', lambda c: c.z > 1.585 and abs(c.x) < 0.14 and -0.17 < c.y < 0.13)

HEADC, HR = V((0, -0.005, 1.70)), (0.1, 0.108, 0.112)
HEAD_MESH = 'nr_head_mesh'
HD = kit._meta('nr_head')
kit.blob_ellipsoid(HD, HEADC, tuple(r * MK for r in HR))
kit.blob_ellipsoid(HD, (0, -0.035, 1.635), (0.076 * MK, 0.074 * MK, 0.062 * MK))       # jaw
kit.blob_ellipsoid(HD, (0, -0.074, 1.588), (0.028 * MK, 0.024 * MK, 0.02 * MK))        # chin
kit.blob_ellipsoid(HD, (0, -0.11, 1.664), (0.008 * MK, 0.011 * MK, 0.015 * MK), rot=(-0.3, 0, 0))  # nose
for sx in (1, -1):
    kit.blob_ellipsoid(HD, (0.05 * sx, -0.072, 1.648), (0.035 * MK, 0.026 * MK, 0.03 * MK))   # cheeks
    kit.blob_ellipsoid(HD, (0.098 * sx, 0.0, 1.685), (0.012 * MK, 0.022 * MK, 0.03 * MK))     # ears
kit.blob_limb(HD, (0, 0.0, 1.5), (0, 0.0, 1.6), 0.042 * MK, 0.045 * MK)                     # neck

SU = kit._meta('nr_suit')  # athletic torso over the kit's
kit.blob_ellipsoid(SU, (0, 0.005, 1.2), (0.14 * MK, 0.088 * MK, 0.17 * MK))
kit.blob_ellipsoid(SU, (0, -0.025, 1.36), (0.15 * MK, 0.075 * MK, 0.075 * MK))
for sx in (1, -1):
    kit.blob_ellipsoid(SU, (0.12 * sx, 0.03, 1.3), (0.06 * MK, 0.07 * MK, 0.09 * MK))

kit.solidify_blobs({'nr_head': kit.mat(SKIN, 0.5), 'nr_suit': kit.mat(ORANGE, 0.75)})
for _n in ('top_mesh', 'bottom_mesh', 'nr_suit_mesh'):  # matte cloth
    for _m in bpy.data.objects[_n].data.materials:
        _m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.92

# black upper section of the jacket (shoulders, upper chest/back, upper sleeves): cut the orange
# jacket meshes cleanly at YOKE_Z and give everything above it the black material
YOKE_Z = 1.355


def two_tone(name, z_cut, m_above):
    o = bpy.data.objects[name]
    o.data.materials.append(m_above)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z_cut),
                           plane_no=(0, 0, 1))
    for f in bm.faces:
        if f.calc_center_median().z > z_cut:
            f.material_index = len(o.data.materials) - 1
    bm.to_mesh(o.data)
    bm.free()


for n in ('top_mesh', 'nr_suit_mesh'):
    two_tone(n, YOKE_Z, kit.mat(BLACK, 0.7))

M_OR = kit.mat(ORANGE, 0.75)
M_BLACK = kit.mat(BLACK, 0.7)
M_WHITE = kit.mat('#f1efe8', 0.6)
M_HAIR = kit.mat(HAIR, 0.45)
M_HAIR_DK = kit.mat(HAIR_DK, 0.45)
M_CLOTH = kit.mat(CLOTH, 0.8)
M_STEEL = kit.mat(STEEL, 0.25, metal=0.9)
M_STEEL_DK = kit.mat('#8a949e', 0.3, metal=0.9)
M_BLUE = kit.mat(BLUE, 0.45)
M_RED = kit.mat('#d3262c', 0.6)

# ── face: blue eyes, whisker marks, cocky grin ───────────────────────────
M_EYE_W = kit.mat('#fbfbf7', 0.3)
M_DARK = kit.mat('#141414', 0.3)
for sx in (1, -1):
    ex, ez = 0.043 * sx, 1.697
    decal(ex, ez, (0.025, 0.008, 0.0135), M_EYE_W, lift=-0.001, roll=0.14 * sx)
    decal(ex - 0.002 * sx, ez - 0.001, (0.0125, 0.007, 0.0135), kit.mat('#1f6fd6', 0.2), lift=0.003)
    decal(ex - 0.002 * sx, ez - 0.006, (0.008, 0.006, 0.006), kit.mat('#8fd0ff', 0.2), lift=0.0055, segs=12, rings=6)
    decal(ex - 0.002 * sx, ez, (0.005, 0.006, 0.0068), M_DARK, lift=0.0065, segs=12, rings=6)
    decal(ex - 0.008 * sx, ez + 0.005, (0.0038, 0.004, 0.0038), M_EYE_W, lift=0.009, segs=10, rings=5)
    face_curve([(ex - 0.026 * sx, ez + 0.001), (ex - 0.008 * sx, ez + 0.0128), (ex + 0.016 * sx, ez + 0.0125),
                (ex + 0.032 * sx, ez + 0.006)], 0.0032, M_DARK, lift=0.003)
    face_curve([(ex - 0.012 * sx, ez - 0.0135), (ex + 0.014 * sx, ez - 0.012)], 0.0012, M_DARK, lift=0.002)
    # brows: confident, slightly arched
    face_curve([(0.018 * sx, 1.722), (0.042 * sx, 1.731), (0.068 * sx, 1.729)], 0.0035, kit.mat('#b8861c', 0.6),
               lift=0.003, taper=0.5)
    # three whisker marks per cheek
    for dz, tilt in ((0.012, 0.006), (0.0, 0.0), (-0.012, -0.006)):
        face_curve([(0.05 * sx, 1.664 + dz), (0.064 * sx, 1.664 + dz + tilt * 0.5), (0.08 * sx, 1.664 + dz + tilt)],
                   0.0018, kit.mat('#4a2a1e', 0.6), lift=0.0015, taper=0.4)
# wide grin
half_decal(0, 1.614, (0.036, 0.008, 0.02), kit.mat('#5e1717', 0.5), lift=0.0)
half_decal(0, 1.6138, (0.033, 0.006, 0.0075), M_WHITE, lift=0.0025)
decal(0, 1.599, (0.016, 0.006, 0.006), kit.mat('#e0706a', 0.6), lift=0.002, segs=12, rings=6)
for sx in (1, -1):
    face_curve([(0.042 * sx, 1.621), (0.036 * sx, 1.613)], 0.0015, kit.mat('#7a3a30', 0.5), lift=0.001)

# ── hair: blond mass + layered sharp spikes ──────────────────────────────
HC = HEADC + V((0, 0.018, 0.028))
HB = kit._meta('nr_hair')
kit.blob_ellipsoid(HB, HC, (0.1 * MK, 0.108 * MK, 0.094 * MK))
kit.blob_ellipsoid(HB, (0, -0.055, 1.775), (0.085 * MK, 0.06 * MK, 0.045 * MK))   # front, down to the band
kit.blob_ellipsoid(HB, (0, 0.045, 1.665), (0.088 * MK, 0.065 * MK, 0.075 * MK))   # back of the head / nape
kit.solidify_blobs({'nr_hair': M_HAIR})


def spike(root, direction, length, rad, bend=(0, 0, 0), m=None):
    d = V(direction).normalized()
    p0 = V(root)
    p1 = p0 + d * length * 0.5 + V(bend) * 0.3
    p2 = p0 + d * length + V(bend)
    kit.tube([tuple(p0), tuple(p1), tuple(p2)], rad, m or M_HAIR, taper_to=0.03, resolution=4, name='spike')


for d in fib(150):
    d = (d + V([random.uniform(-0.1, 0.1) for _ in range(3)])).normalized()
    if d.z < -0.75:
        continue
    if d.y < -0.25 and d.z < 0.55:   # face
        continue
    if d.y < 0.35 and d.z < -0.1:    # jaw / ears
        continue
    root = HC + V((d.x * 0.085, d.y * 0.095, d.z * 0.1))
    if d.z > 0.35:          # crown: up and swept back
        out = d + V((0, 0.35, 0.25))
        length = random.uniform(0.14, 0.2)
    elif d.y > 0.3:         # back: down and back
        out = d + V((0, 0.25, -0.35))
        length = random.uniform(0.11, 0.14)
    else:                   # sides: out, slightly down
        out = d + V((0, 0.2, -0.1))
        length = random.uniform(0.12, 0.17)
    spike(root, out, length, random.uniform(0.03, 0.04), m=M_HAIR if random.random() > 0.25 else M_HAIR_DK)

# nape: a fan of spikes hanging down the back of the neck
for k in range(9):
    ang = math.radians(-80 + 160 * k / 8)
    d = V((math.sin(ang), math.cos(ang), 0))
    root = V((0, 0.02, 1.665)) + V((d.x * 0.075, d.y * 0.085, 0))
    spike(root, d * 0.6 + V((0, 0.15, -1)), random.uniform(0.08, 0.11), 0.026,
          m=M_HAIR if k % 3 else M_HAIR_DK)

# front spikes over the headband + long strands framing the face
for x, tip in ((-0.06, (-0.09, -0.11, 1.84)), (-0.02, (-0.03, -0.13, 1.86)), (0.025, (0.04, -0.13, 1.86)),
               (0.065, (0.1, -0.11, 1.84))):
    spike((x, -0.05, 1.79), V(tip) - V((x, -0.05, 1.79)), (V(tip) - V((x, -0.05, 1.79))).length, 0.026)
for sx in (1, -1):
    for k, (dz, ln) in enumerate(((0.0, 0.1), (0.02, 0.085))):
        r0 = V((0.088 * sx, -0.045 + 0.02 * k, 1.75 + dz))
        spike(r0, V((0.02 * sx, -0.25, -1)), ln, 0.02, bend=(0.012 * sx, -0.01, 0))

# ── Hidden Leaf forehead protector ───────────────────────────────────────
HEADBAND_NAMES = ['nr_head_mesh', 'nr_hair_mesh']
bc = V((0, 0.0, 1.762))
pts = ring_pts(HEADBAND_NAMES, bc, n=56, tilt=0.15, lift=0.004, max_d=0.25)
ribbon(pts, 0.036, M_CLOTH, closed=True, thick=0.006)
# metal plate on the forehead
pl, pn = shell(HEADBAND_NAMES, bc, (0, -1, -0.15), 0.25)
pq = V((0, -1, 0)).rotation_difference(pn)
right, up = pq @ V((1, 0, 0)), pq @ V((0, 0, 1))
pc = pl + pn * 0.012
kit.box(pc, (0.1, 0.012, 0.042), M_STEEL, rot=pq.to_euler(), bevel=0.004)
for sx in (1, -1):
    for sz in (1, -1):
        kit.sphere(pc + right * 0.043 * sx + up * 0.015 * sz + pn * 0.006, 0.0028, M_STEEL_DK, segs=8, rings=4)
# engraved leaf-swirl: spiral + leaf point + tail, raised just off the plate
sym = []
for i in range(26):
    t = i / 25
    ang = 0.6 + t * 2.4 * math.pi
    r = 0.002 + 0.0105 * t
    sym.append((math.cos(ang) * r, math.sin(ang) * r))
sym += [(0.012, 0.014), (0.017, 0.018)]
to3 = lambda u, v: tuple(pc + right * u + up * (v - 0.001) + pn * 0.0068)  # noqa: E731
kit.tube([to3(u, v) for u, v in sym], 0.0016, M_STEEL_DK, resolution=3, taper_to=0.3, name='leaf')
kit.tube([to3(-0.011, -0.006), to3(-0.017, -0.012), to3(-0.022, -0.016)], 0.0016, M_STEEL_DK, resolution=3,
         name='leaf_tail')
# knot and flowing tails at the back
kn, knn = shell(HEADBAND_NAMES, bc, (0, 1, 0.15), 0.25)
kit.subdivide(kit.sphere(kn + knn * 0.012, (0.022, 0.014, 0.016), M_CLOTH, segs=12, rings=8), 1)
for sx, sway in ((1, 1.0), (-1, -0.6)):
    k0 = kn + knn * 0.012
    tail = [k0 + V((0.008 * sx, 0.006, 0)), k0 + V((0.024 * sx, 0.035, -0.04)), k0 + V((0.034 * sx, 0.06, -0.1)),
            k0 + V((0.04 * sx + 0.02 * sway, 0.085, -0.16)), k0 + V((0.045 * sx + 0.04 * sway, 0.11, -0.23))]
    ribbon(tail, 0.03, M_CLOTH, up=(1, 0, 0.3 * sx), thick=0.005, widths=[0.032, 0.036, 0.034, 0.032, 0.028])

# ── costume ─────────────────────────────────────────────────────────────
# high collar (orange outside, black rim) + zipper and pull ring
kit.cone((0, 0.0, 1.49), 0.085, 0.056, 0.11, M_BLACK, verts=32)
kit.torus((0, 0.0, 1.545), 0.056, 0.007, M_OR, major_segs=24, minor_segs=6)
zp = []
for z in (1.5, 1.42, 1.32, 1.2, 1.08, 1.0):
    loc, nor = shell(BODY, (0, 0, z), (0, -1, 0))
    zp.append(tuple(loc + nor * 0.002) if loc is not None else (0, -0.1, z))
kit.tube(zp, 0.0035, M_BLACK, name='zip')
zl, zn = shell(BODY, (0, 0, 1.44), (0, -1, 0))
kit.torus(zl + zn * 0.01 + V((0, 0, -0.01)), 0.011, 0.0028, M_STEEL, rot=(math.pi / 2 - 0.3, 0, 0),
          major_segs=16, minor_segs=6)
# hem of the black yoke (piping)
band(BODY, YOKE_Z, 0.001, 0.0045, M_BLACK, tilt=0.0)
# waistband
band(BODY, 1.0, 0.002, 0.01, kit.mat('#e0600c', 0.75), tilt=0.08)
# red Uzumaki swirl on the back
bl, bn = shell(BODY, (0, 0, 1.3), (0, 1, 0))
bq = V((0, 1, 0)).rotation_difference(bn)
br_, bu = bq @ V((-1, 0, 0)), bq @ V((0, 0, 1))
sw = []
for i in range(30):
    t = i / 29
    ang = t * 2.6 * math.pi
    r = 0.004 + 0.034 * t
    sw.append(tuple(bl + br_ * math.cos(ang) * r + bu * math.sin(ang) * r + bn * 0.003))
kit.tube(sw, 0.0045, M_RED, resolution=4, name='swirl')

# right-thigh bandage + kunai holster
hr, kr = a['hip_r'], a['knee_r']
for t in (0.5, 0.6):
    c = hr.lerp(kr, t)
    band(['bottom_mesh'], c.z, 0.002, 0.008, M_WHITE, n=32, center=(c.x, c.y))
hc = hr.lerp(kr, 0.55)
hl, hn = shell(['bottom_mesh'], hc, (-0.7, -0.7, 0), 0.2)
if hl is not None:
    kit.box(hl + hn * 0.016, (0.045, 0.03, 0.07), M_BLACK, rot=(0, 0, math.atan2(hn.x, -hn.y)), bevel=0.008)

# shin wraps + blue open-toe ninja sandals
for side, sx in (('l', 1), ('r', -1)):
    ankle = V((0.176 * sx, 0.01, 0.1))
    for dz in (0.1, 0.13, 0.16):
        band(['bottom_mesh'], ankle.z + dz, 0.002, 0.0075, M_WHITE, n=28, center=(ankle.x, ankle.y))
    kit.cylinder(ankle + V((0, 0, -0.01)), 0.044, 0.09, M_BLUE, verts=24)
    kit.subdivide(kit.sphere(ankle + V((0, -0.045, -0.088)), (0.058, 0.135, 0.016), kit.mat('#1d3f8c', 0.5),
                             segs=24, rings=10), 1)
    kit.sphere(ankle + V((0, -0.135, -0.072)), (0.04, 0.035, 0.018), kit.mat(SKIN, 0.5), segs=16, rings=8)  # toes
    for dy in (-0.07, -0.02):
        kit.box(ankle + V((0, dy, -0.06)), (0.11, 0.02, 0.03), M_BLUE, rot=(-0.4, 0, 0), bevel=0.008)

# clenched right fist
_el, _hd = a['elbow_r'], a['hand_r']
kit.subdivide(kit.sphere(_hd + (_hd - _el).normalized() * 0.005, (0.034, 0.03, 0.04), kit.mat(SKIN, 0.5),
                         rot=kit.rot_between(_el, _hd), segs=16, rings=8), 1)

# ── Rasengan in the left palm ────────────────────────────────────────────
hl_, el_ = a['hand_l'], a['elbow_l']
fdir = (hl_ - el_).normalized()
rc = hl_ + fdir * 0.01 + V((0, 0, 0.1))
no_ink(kit.sphere(rc, 0.05, kit.mat('#8fd0ff', 0.2, emit=2.0), segs=24, rings=12))
no_ink(kit.sphere(rc, 0.072, glass('#1f78ff', 0.5, 1.4), segs=32, rings=16))
no_ink(kit.sphere(rc, 0.086, glass('#6cc0ff', 0.2, 1.2), segs=32, rings=16))
M_SWIRL = kit.mat('#3f9dff', 0.2, emit=2.5)
M_SWIRL2 = kit.mat('#7cc4ff', 0.2, emit=2.5)
for i, (rx, ry) in enumerate(((0.3, 0.0), (1.1, 0.6), (-0.6, 1.2), (1.6, -0.9), (0.2, 2.2))):
    no_ink(kit.torus(rc, 0.08 + 0.005 * (i % 2), 0.0032, M_SWIRL if i % 2 else M_SWIRL2, rot=(rx, ry, 0),
                     major_segs=40, minor_segs=6))
# swirling streaks wrapping the sphere
for i in range(6):
    ax = V([random.uniform(-1, 1) for _ in range(3)]).normalized()
    u = ax.cross(V((0, 0, 1)) if abs(ax.z) < 0.9 else V((1, 0, 0))).normalized()
    v = ax.cross(u)
    start = random.uniform(0, math.tau)
    pts = []
    for k in range(10):
        t = k / 9
        ang = start + t * 2.4
        r = 0.084 + 0.014 * math.sin(t * math.pi)
        pts.append(tuple(rc + (u * math.cos(ang) + v * math.sin(ang)) * r + ax * 0.01 * math.sin(t * 3)))
    no_ink(kit.tube(pts, 0.0035, M_SWIRL2, taper_to=0.1, resolution=4, name='swirl'))


# ── dynamic pose ─────────────────────────────────────────────────────────
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


pose_deform(twist=-0.1, lean=0.06, fwd_l=-0.08, fwd_r=0.12, knee_fwd=0.06, knee_out=0.03, crouch=0.92)

# thumbnail ink: skip face-marked (glowing) geometry; kit.render_thumbnail configures the rest of this lineset
_fs = bpy.context.view_layer.freestyle_settings
_ls = _fs.linesets[0] if len(_fs.linesets) else _fs.linesets.new('ink')
_ls.select_by_face_marks = True
_ls.face_mark_negation = 'EXCLUSIVE'
_ls.face_mark_condition = 'ONE'

kit.finalize('naruto')
