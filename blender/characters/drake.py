"""Nathan Drake (Uncharted) — fan-art collectible statue built from kit primitives."""
import math
import os
import sys

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import Vector  # noqa: E402


# ── local helpers ────────────────────────────────────────────────────────

def _link(me, m, name, smooth=True):
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for mm in (m if isinstance(m, (list, tuple)) else [m]):
        obj.data.materials.append(mm)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return obj


def grid(rows, m, wrap=False, name='grid', thickness=0.0, inner=None, offset=0.0, sub=0, flip=False):
    """Quad surface from rows[i][j] points; optional wrap in j, solidify and subdivision."""
    nr, nc = len(rows), len(rows[0])
    verts = [tuple(p) for row in rows for p in row]
    faces = []
    for i in range(nr - 1):
        for j in range(nc if wrap else nc - 1):
            j2 = (j + 1) % nc
            f = [i * nc + j, i * nc + j2, (i + 1) * nc + j2, (i + 1) * nc + j]
            faces.append(f[::-1] if flip else f)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = _link(me, [m, inner] if inner else m, name)
    if sub:
        kit.subdivide(obj, sub)
    if thickness:
        mod = obj.modifiers.new('solid', 'SOLIDIFY')
        mod.thickness = thickness
        mod.offset = offset
        mod.use_even_offset = True
        if inner:
            mod.material_offset = 1
    return obj


def prism(origin, U, V, N, pts, depth, m, name='prism'):
    """Extrude a 2D polygon (pts in the U/V plane) by `depth` along N, centred on origin."""
    origin, U, V, N = Vector(origin), Vector(U), Vector(V), Vector(N)
    verts = []
    for side in (-0.5, 0.5):
        for (u, v) in pts:
            verts.append(tuple(origin + U * u + V * v + N * (depth * side)))
    n = len(pts)
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return _link(me, m, name, smooth=False)


def basis(d, up=(0, 0, 1)):
    d = Vector(d).normalized()
    side = d.cross(Vector(up)).normalized()
    v = side.cross(d).normalized()
    return d, v, side


def interp(table, x):
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 >= x >= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[0][1] if x > table[0][0] else table[-1][1]


TREES = {}


def build_trees():
    dg = bpy.context.evaluated_depsgraph_get()
    TREES.clear()
    names = ['skin_mesh', 'top_mesh', 'bottom_mesh', 'hands_mesh']
    names += [o.name for o in bpy.data.objects if o.name.endswith('_head_mesh')]
    for n in names:
        if n in bpy.data.objects:
            TREES[n] = BVHTree.FromObject(bpy.data.objects[n], dg)


def nearest(p, only=None):
    best = None
    for n, t in TREES.items():
        if only and n not in only:
            continue
        r = t.find_nearest(Vector(p))
        if r[0] is not None and (best is None or r[3] < best[3]):
            best = r
    return best


def drape(p, off, only=None, maxd=0.06):
    """Push a point out of the body so it sits at least `off` above the nearest surface."""
    p0 = p = Vector(p)
    for _ in range(3):
        loc, n, _i, _d = nearest(p, only)
        if (p - loc).dot(n) >= off:
            break
        p = loc + n * off
    return p if (p - p0).length <= maxd else p0


def radial(z, th, cx=0.0, cy=0.0, only=('top_mesh', 'bottom_mesh'), cap=0.3):
    """Torso radius at height z along horizontal angle th (0 = back/+Y, pi/2 = +X), cast from inside."""
    d = Vector((math.sin(th), math.cos(th), 0))
    o = Vector((cx, cy, z))
    best = 0.0
    for n in only:
        t = TREES.get(n)
        if not t:
            continue
        hit = t.ray_cast(o, d, cap)
        if hit[0] is not None and hit[1].dot(d) > 0:  # only count surfaces we exit (the torso itself)
            best = max(best, hit[3])
    return best


def limb_r(a, b, t=0.5, only=None):
    """Average radius of a limb around the segment a->b at parameter t."""
    a, b = Vector(a), Vector(b)
    c = a.lerp(b, t)
    d, u, s = basis(b - a, up=(0, 0, 1) if abs((b - a).normalized().z) < 0.9 else (0, 1, 0))
    rs = []
    for k in range(8):
        ang = k * math.pi / 4
        dirv = u * math.cos(ang) + s * math.sin(ang)
        hits = []
        for n, tr in TREES.items():
            if only and n not in only:
                continue
            hit = tr.ray_cast(c + dirv * 0.09, -dirv, 0.09)
            if hit[0] is not None:
                hits.append((hit[0] - c).dot(dirv))
        if hits:
            rs.append(max(hits))
    return sum(rs) / len(rs) if rs else 0.04


def band(z0, z1, m, lift, nseg=64, rows=3, name='band', thickness=0.006, wobble=0.0, cy=0.0):
    """Cloth band hugging the torso between heights z0 and z1."""
    grid_rows = []
    for i in range(rows):
        z = z0 + (z1 - z0) * i / (rows - 1)
        row = []
        for j in range(nseg):
            th = 2 * math.pi * j / nseg
            rr = radial(z, th, cy=cy) + lift + wobble * math.sin(5 * th + i)
            row.append((rr * math.sin(th), cy + rr * math.cos(th), z))
        grid_rows.append(row)
    return grid(grid_rows, m, wrap=True, name=name, thickness=thickness, offset=1)


def smooth_path(pts, n=8, closed=False):
    """Catmull-Rom resample through the control points."""
    P = [Vector(p) for p in pts]
    if closed:
        P = P + P[:3]
    out = []
    rng = range(1, len(P) - 2) if closed else range(len(P) - 1)
    for i in rng:
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(P[-1])
    return out


def snap(p, lift, only=None):
    loc, n, _i, _d = nearest(p, only)
    return loc + n * lift


def strap(pts, width, m, lift, only=None, thickness=0.004, n=8, closed=False, name='strap'):
    """Flat leather strap lying on the body surface through control points."""
    path = [snap(p, lift, only) for p in smooth_path(pts, n, closed)]
    N = len(path)
    for _ in range(4):  # relax the stair-steps of the metaball surface, then push back out
        path = [path[i] if (not closed and i in (0, N - 1)) else
                (path[i - 1] + path[i] * 2 + path[(i + 1) % N]) / 4 for i in range(N)]
        path = [drape(p, lift, only, maxd=0.03) for p in path]
    ra, rb = [], []
    for i, p in enumerate(path):
        t = (path[(i + 1) % len(path)] - path[i - 1]) if closed else \
            (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)])
        nrm = (p - nearest(p, only)[0]).normalized()
        w = t.normalized().cross(nrm).normalized() * width / 2
        ra.append(p - w)
        rb.append(p + w)
    if closed:
        ra.append(ra[0])
        rb.append(rb[0])
    return grid([ra, rb], m, name=name, thickness=thickness, offset=0)


# ── sculpted head (replaces the kit's generic face) ──────────────────────
import bmesh  # noqa: E402

MK = 1 / 0.68  # a lone metaball's visible size is ~0.68x the requested size
HEADC, HR = Vector((0, -0.006, 1.70)), (0.096, 0.104, 0.11)


def replace_kit_head():
    """Drop the kit's face meshes and the top of its sculpted skin (we sculpt our own head)."""
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH' or o.name.endswith('_mesh') or not len(o.data.vertices):
            continue
        c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
        if c.z > 1.56 and abs(c.x) < 0.14 and -0.2 < c.y < 0.14:
            bpy.data.objects.remove(o, do_unlink=True)
    o = bpy.data.objects['skin_mesh']
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 1.585 and abs(v.co.x) < 0.14
                               and -0.17 < v.co.y < 0.13], context='VERTS')
    bm.to_mesh(o.data)
    bm.free()


def sculpt_head(prefix, skin):
    """Mature, game-character head: defined jaw + chin, cheek planes, brow ridge, sculpted nose, lips."""
    HD = kit._meta(prefix + '_head', resolution=0.0065)

    def E(c, s, rot=(0, 0, 0)):
        kit.blob_ellipsoid(HD, c, tuple(v * MK for v in s), rot=rot)

    E(HEADC, HR)                                                         # cranium
    E((0, -0.02, 1.64), (0.068, 0.068, 0.056))                          # jaw mass
    for sx in (1, -1):
        E((0.058 * sx, -0.014, 1.612), (0.02, 0.03, 0.022))              # jaw angle
        E((0.045 * sx, -0.071, 1.668), (0.024, 0.018, 0.019))             # cheekbone plane
        E((0.034 * sx, -0.087, 1.727), (0.03, 0.016, 0.011), rot=(0, 0, -0.12 * sx))  # brow ridge
        E((0.095 * sx, 0.004, 1.686), (0.011, 0.022, 0.03))              # ears
        E((0.011 * sx, -0.08, 1.588), (0.017, 0.02, 0.018))              # squared chin
    E((0, -0.1, 1.692), (0.0075, 0.011, 0.022), rot=(-0.45, 0, 0))        # nose bridge
    E((0, -0.116, 1.664), (0.0105, 0.013, 0.011))                        # nose tip
    for sx in (1, -1):
        E((0.0105 * sx, -0.106, 1.66), (0.0085, 0.008, 0.007))          # nostril wings
    E((0, -0.088, 1.623), (0.019, 0.0075, 0.006))                         # upper lip
    E((0, -0.085, 1.608), (0.016, 0.008, 0.006))                        # lower lip
    kit.blob_limb(HD, (0, 0.01, 1.47), (0, 0.002, 1.62), 0.05 * MK, 0.046 * MK)  # neck
    kit.solidify_blobs({prefix + '_head': kit.mat(skin, 0.5)})
    return prefix + '_head_mesh'


def face(x, z, lift=0.0):
    o = bpy.data.objects[HEAD_MESH]
    ok, loc, nor, _ = o.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), distance=2.0)
    if not ok:
        loc, nor, _i, _d = TREES_HEAD.find_nearest(Vector((x, -0.1, z)))
    return loc + nor * lift, nor


def decal(x, z, scale, m, lift=0.0, segs=20, rings=10, roll=0.0):
    p, n = face(x, z, lift)
    q = Vector((0, -1, 0)).rotation_difference(n)
    rot = (q.to_matrix() @ kit.Euler((0, roll, 0)).to_matrix()).to_euler()
    return kit.sphere(p, scale, m, rot=rot, segs=segs, rings=rings)


def face_curve(pts_xz, radius, m, lift=0.002, taper=None):
    return kit.tube([tuple(face(x, z, lift)[0]) for x, z in pts_xz], radius, m, resolution=6, taper_to=taper,
                    name='face_line')


def eyes(iris_hex, brow_hex, brow_pts, lash='#1d1410'):
    """Almond eyes with lids + crease, tapered brows (brow_pts per side: [(x, z), ...] for sx=+1)."""
    WHITE_E = kit.mat('#f3eee6', 0.3)
    LASH = kit.mat(lash, 0.4)
    CREASE = kit.mat(SKIN_SHADE, 0.6)
    for sx in (1, -1):
        ex, ez = 0.036 * sx, 1.702
        decal(ex, ez, (0.0165, 0.006, 0.0078), WHITE_E, lift=-0.0012, roll=-0.1 * sx)
        decal(ex, ez - 0.0005, (0.0071, 0.005, 0.0071), kit.mat(iris_hex, 0.25), lift=0.0018, segs=16, rings=8)
        decal(ex, ez - 0.0005, (0.0033, 0.004, 0.0033), kit.mat('#0c0c0c', 0.2), lift=0.003, segs=10, rings=5)
        decal(ex - 0.0022 * sx, ez + 0.0026, (0.0016, 0.002, 0.0016), WHITE_E, lift=0.0042, segs=8, rings=4)
        # upper lid / lash line (heavier at the outer corner), lower lid, crease
        face_curve([(ex - 0.0175 * sx, ez - 0.0008), (ex - 0.007 * sx, ez + 0.0068), (ex + 0.006 * sx, ez + 0.0074),
                    (ex + 0.0175 * sx, ez + 0.0018)], 0.0019, LASH, lift=0.0016)
        face_curve([(ex - 0.015 * sx, ez - 0.0035), (ex - 0.002 * sx, ez - 0.0072), (ex + 0.013 * sx, ez - 0.0052)],
                   0.0009, CREASE, lift=0.0008)
        pts = [(x * sx, z + (0.0 if sx > 0 else BROW_RIGHT_DZ * (i / (len(brow_pts) - 1))))
               for i, (x, z) in enumerate(brow_pts)]
        face_curve(pts, 0.0042, kit.mat(brow_hex, 0.7), lift=0.0022, taper=0.35)


kit.reset()

# ── palette ──────────────────────────────────────────────────────────────
HENLEY = kit.mat('#e6dac0', 0.85)
HENLEY_D = kit.mat('#cdbf9f', 0.85)
DENIM = kit.mat('#35557f', 0.9)
DENIM_D = kit.mat('#263f60', 0.9)
LEATHER = kit.mat('#6b4226', 0.6)
DARK_LEATHER = kit.mat('#3b2416', 0.6)
HAIR = kit.mat('#4a2e1a', 0.75)
GUNMETAL = kit.mat('#2b2d31', 0.32, metal=0.85)
GRIP = kit.mat('#1a1a1c', 0.6)
STEEL = kit.mat('#c9ced6', 0.2, metal=1.0)
GOLD = kit.mat('#e0b040', 0.22, metal=1.0)
CORD = kit.mat('#2a1d14', 0.8)
BRASS = kit.mat('#b8862f', 0.3, metal=0.9)
PAPER = kit.mat('#efe3c2', 0.7)
LIPS = kit.mat('#8a4b40', 0.5)

# custom poses (left-side offsets from the shoulder, mirrored for the right)
kit.HERO_ARM_POSES['drake_gun'] = ((0.09, -0.1, -0.21), (0.03, -0.17, 0.07))
kit.HERO_ARM_POSES['drake_compass'] = ((0.08, -0.02, -0.25), (0.05, -0.24, -0.31))

a = kit.hero(skin='#d29a72', top='#e6dac0', bottom='#35557f', shoes='#6b4226', iris='#6a7a3a',
             brows='#3b2414', sleeves='short', mouth='line', right_arm='drake_gun', left_arm='drake_compass',
             stance='wide', build=1.2)
H = a['head']

replace_kit_head()
SKIN_SHADE = '#a8704f'
BROW_RIGHT_DZ = -0.004   # one brow cocked higher than the other
HEAD_MESH = sculpt_head('dr', '#d29a72')
TREES_HEAD = BVHTree.FromObject(bpy.data.objects[HEAD_MESH], bpy.context.evaluated_depsgraph_get())
build_trees()
eyes('#6a7a3a', '#3b2414', [(0.011, 1.718), (0.033, 1.729), (0.058, 1.728)])
# confident half-smile: the figure's left corner lifts into a crease
LIP_LINE = kit.mat('#6e3a30', 0.5)
face_curve([(-0.019, 1.6158), (-0.006, 1.6146), (0.008, 1.615), (0.019, 1.6185), (0.026, 1.6238)], 0.0015,
           LIP_LINE, lift=0.001)
face_curve([(0.029, 1.627), (0.031, 1.6185)], 0.0009, kit.mat(SKIN_SHADE, 0.6), lift=0.0008)
decal(0, 1.6085, (0.013, 0.004, 0.0035), kit.mat('#bd7c66', 0.5), lift=-0.0006, segs=16, rings=8)

# ── messy hair: a sculpted cap + many tapered tufts ───────────────────────
HH = H + Vector((0, 0.002, 0.022))  # sit the hair on the taller sculpted cranium
HB = kit._meta('dr_hair')
kit.blob_ellipsoid(HB, HH + Vector((0, 0.008, 0.055)), (0.128, 0.11, 0.065))
kit.blob_ellipsoid(HB, HH + Vector((0, 0.03, -0.005)), (0.124, 0.088, 0.098))
kit.blob_ellipsoid(HB, HH + Vector((0, 0.045, -0.06)), (0.09, 0.05, 0.05))
kit.blob_ellipsoid(HB, HH + Vector((-0.01, -0.07, 0.07)), (0.085, 0.032, 0.03))
for sx in (1, -1):
    kit.blob_ellipsoid(HB, HH + Vector((0.104 * sx, 0.006, 0.018)), (0.03, 0.075, 0.055))
kit.solidify_blobs({'dr_hair': HAIR})
dg = bpy.context.evaluated_depsgraph_get()
HAIR_TREE = BVHTree.FromObject(bpy.data.objects['dr_hair_mesh'], dg)

import random  # noqa: E402
rnd = random.Random(7)
HC = HH + Vector((0, 0.01, 0.03))
for el in range(-10, 90, 12):
    ring = max(1, int(round(16 * math.cos(math.radians(el)))))
    for k in range(ring):
        az = -170 + 340 * (k + 0.5 * (el // 12 % 2)) / ring + rnd.uniform(-6, 6)
        e, z_ = math.radians(el + rnd.uniform(-4, 4)), math.radians(az)
        n = Vector((math.sin(z_) * math.cos(e), -math.cos(z_) * math.cos(e), math.sin(e)))
        hit = HAIR_TREE.ray_cast(HC + n * 0.3, -n, 0.4)
        if hit[0] is None:
            continue
        root, nrm = hit[0], hit[1]
        if root.z < HH.z - 0.06 and abs(az) < 100:
            continue
        front = max(0.0, math.cos(z_)) ** 2 * max(0.0, 1 - abs(el - 35) / 45)
        F = Vector((-0.45, -0.55, 0.55)) * front + Vector((0.1 * math.sin(z_), 0.6, -1.0)) * (1 - front)
        if el > 55:
            F = Vector((-0.35, -0.8, 0.15))
        T = (F - nrm * F.dot(nrm)).normalized()
        L = rnd.uniform(0.032, 0.05) * (1.25 if front > 0.4 else 1.0)
        lift = 0.014 if front > 0.4 else 0.006
        jit = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.006
        kit.tube([root - nrm * 0.006, root + T * L * 0.5 + nrm * lift, root + T * L + nrm * lift * 0.6 + jit],
                 rnd.uniform(0.011, 0.015), HAIR, taper_to=0.12, resolution=4, name='tuft')

# ── straight-leg jeans shell over the sculpted legs ──────────────────────
JN = kit._meta('dr_jeans')
for s_ in ('l', 'r'):
    hp, kn = a[f'hip_{s_}'], a[f'knee_{s_}']
    ank = a[f'foot_{s_}'] + Vector((0, 0.05, 0.1))
    pts = [(hp.lerp(kn, t), limb_r(hp, kn, t, only=('bottom_mesh', 'jeans'))) for t in (0.2, 0.45, 0.7, 0.95)]
    pts += [(kn.lerp(ank, t), limb_r(kn, ank, t, only=('bottom_mesh', 'jeans'))) for t in (0.25, 0.5, 0.75, 0.92)]
    for (p0, r0), (p1, r1) in zip(pts, pts[1:]):
        kit.blob_limb(JN, p0, p1, max(r0 + 0.008, 0.06), max(r1 + 0.008, 0.06 if p1.z > 0.3 else 0.058))
kit.solidify_blobs({'dr_jeans': DENIM})
build_trees()
TREES['jeans'] = BVHTree.FromObject(bpy.data.objects['dr_jeans_mesh'], bpy.context.evaluated_depsgraph_get())

# ── henley: collar, placket with buttons, rolled sleeves ─────────────────
neck = a['neck']
collar = []
for k in range(16):
    th = 2 * math.pi * k / 16
    collar.append(Vector((0.085 * math.sin(th), 0.07 * math.cos(th) - 0.005, 1.49 - 0.025 * max(0.0, -math.cos(th)))))
strap(collar, 0.014, HENLEY_D, 0.005, only=('top_mesh',), closed=True, name='collar')
plk = [Vector((0.0, -0.3, z)) for z in (1.465, 1.425, 1.385)]
plk = [snap(p + Vector((0, 0.3, 0)) + Vector((0, -0.15, 0)), 0.004, only=('top_mesh',)) for p in plk]
strap(plk, 0.022, HENLEY_D, 0.004, only=('top_mesh',), name='placket')
for p in plk:
    kit.sphere(snap(p, 0.008, only=('top_mesh',)), 0.0048, kit.mat('#f4efe4', 0.4), segs=10, rings=6)
for s in ('l', 'r'):
    sh, el = a[f'shoulder_{s}'], a[f'elbow_{s}']
    for tt, extra, mr in ((0.86, 0.012, 0.015), (0.76, 0.01, 0.012)):
        c = sh.lerp(el, tt)
        kit.torus(c, limb_r(sh, el, tt, only=('top_mesh', 'skin_mesh')) + extra, mr, HENLEY_D if tt > 0.8 else HENLEY,
                  rot=kit.rot_between(sh, el), major_segs=28, minor_segs=8)

# ── jeans belt + buckle; shirt bloused over the belt ─────────────────────
band(1.035, 1.075, HENLEY, 0.008, rows=3, name='blouse', thickness=0.006, wobble=0.003)
band(0.985, 1.02, LEATHER, 0.008, rows=2, name='belt', thickness=0.006)
fy = -radial(1.0, math.pi) - 0.016
kit.box((0, fy, 1.0), (0.05, 0.008, 0.04), STEEL, bevel=0.004)
kit.box((0, fy - 0.003, 1.0), (0.034, 0.006, 0.024), LEATHER, bevel=0.002)
for sx in (1, -1):  # belt loops
    for xx in (0.07, 0.14):
        ang = math.pi - math.atan2(xx * sx, 1) * 1.6
        rr = radial(1.0, ang) + 0.014
        kit.box((rr * math.sin(ang), rr * math.cos(ang), 1.0), (0.012, 0.006, 0.05), DENIM_D, rot=(0, 0, -ang))

# ── shoulder holster harness ─────────────────────────────────────────────
HARN = ('top_mesh',)
for sx in (1, -1):
    loop = [(0.0, 0.1, 1.3), (0.08 * sx, 0.1, 1.4), (0.14 * sx, 0.02, 1.49), (0.15 * sx, -0.09, 1.42),
            (0.2 * sx, -0.07, 1.33), (0.22 * sx, 0.0, 1.28), (0.16 * sx, 0.09, 1.27)]
    strap(loop, 0.024, LEATHER, 0.007, only=HARN, closed=True, n=10, name='harness')
kit.torus(snap((0, 0.1, 1.3), 0.012, only=HARN), 0.02, 0.005, STEEL, rot=(math.pi / 2, 0, 0), major_segs=20,
          minor_segs=6)
# empty holster under the left arm, spare-mag pouches under the right
hp = snap((0.19, 0.0, 1.2), 0.03, only=HARN)
kit.box(hp, (0.036, 0.075, 0.12), DARK_LEATHER, rot=(0.3, 0, 0), bevel=0.012)
kit.box(hp + Vector((0.004, 0.0, 0.06)), (0.04, 0.08, 0.02), LEATHER, rot=(0.3, 0, 0), bevel=0.006)
mp = snap((-0.19, 0.0, 1.22), 0.03, only=HARN)
for dy in (-0.022, 0.022):
    kit.box(mp + Vector((0, dy, 0)), (0.034, 0.036, 0.07), DARK_LEATHER, bevel=0.008)
    kit.box(mp + Vector((-0.002, dy, 0.03)), (0.038, 0.04, 0.016), LEATHER, bevel=0.004)

# ── Sir Francis Drake's ring on a cord ───────────────────────────────────
cord_pts = [(-0.05, 0.03, 1.53), (-0.07, -0.04, 1.48), (-0.04, -0.1, 1.4), (0.0, -0.12, 1.355),
            (0.04, -0.1, 1.4), (0.07, -0.04, 1.48), (0.05, 0.03, 1.53), (0.0, 0.06, 1.55)]
cord = [snap(p, 0.004, only=('top_mesh', 'skin_mesh')) for p in smooth_path(cord_pts, 6, closed=True)]
kit.tube(cord + [cord[0]], 0.0022, CORD, name='cord', resolution=2)
low = min(cord, key=lambda p: p.z)
rn = nearest(low, ('top_mesh',))[1]
kit.torus(low + rn * 0.008 - Vector((0, 0, 0.016)), 0.015, 0.0045, GOLD, rot=kit.rot_between((0, 0, 0), rn),
          major_segs=28, minor_segs=10)
kit.sphere(low + rn * 0.012 - Vector((0, 0, 0.002)), (0.006, 0.004, 0.005), GOLD, segs=12, rings=6)

# ── pistol raised beside the face ────────────────────────────────────────
e, h = a['elbow_r'], a['hand_r']
d = (h - e).normalized()
B = (d + Vector((0, 0.25, 0))).normalized()          # barrel axis: up, tipped slightly back
side = B.cross(Vector((0, -1, 0))).normalized()
top = side.cross(B).normalized()                      # the gun's "top" (sights side)
q = basis(B)[0].to_track_quat('Z', 'Y')
gun_base = h + B * 0.03
# grip in the fist, slide + frame above it
kit.box(h + B * 0.0 - top * 0.005, (0.026, 0.05, 0.1), GRIP, rot=B.to_track_quat('Z', 'X').to_euler(), bevel=0.006)
slide_c = gun_base + B * 0.085 + top * 0.022


def gun_box(c, size, m, bevel):
    # size = (side, top, barrel)
    M = [side, top, B]
    import mathutils
    rot = mathutils.Matrix((
        (M[0].x, M[1].x, M[2].x), (M[0].y, M[1].y, M[2].y), (M[0].z, M[1].z, M[2].z))).to_euler()
    return kit.box(c, size, m, rot=rot, bevel=bevel)


gun_box(slide_c, (0.026, 0.034, 0.19), GUNMETAL, 0.005)
gun_box(slide_c - top * 0.02 - B * 0.01, (0.024, 0.02, 0.15), GRIP, 0.004)     # frame
gun_box(gun_base - top * 0.0 + B * 0.0 + top * 0.012, (0.03, 0.04, 0.05), GRIP, 0.008)  # grip top / hand
gun_box(slide_c + top * 0.019 + B * 0.085, (0.004, 0.008, 0.008), GUNMETAL, 0.001)  # front sight
gun_box(slide_c + top * 0.019 - B * 0.085, (0.012, 0.008, 0.008), GUNMETAL, 0.001)  # rear sight
kit.cylinder(slide_c + B * 0.096, 0.007, 0.006, kit.mat('#050505', 0.9), rot=kit.rot_between((0, 0, 0), B),
             verts=12)
kit.torus(gun_base + B * 0.035 - top * 0.012, 0.016, 0.0035, GRIP, rot=kit.rot_between((0, 0, 0), side),
          major_segs=16, minor_segs=6)  # trigger guard

# ── old brass compass in the left hand ────────────────────────────────────
hl = a['hand_l']
cn = Vector((0.15, -0.45, 0.88)).normalized()
cc = hl + Vector((0, -0.005, 0.034))
rot_c = kit.rot_between((0, 0, 0), cn)
kit.cylinder(cc, 0.03, 0.012, BRASS, rot=rot_c, verts=28)
kit.cylinder(cc + cn * 0.0062, 0.025, 0.002, PAPER, rot=rot_c, verts=24)
kit.torus(cc + cn * 0.006, 0.027, 0.003, BRASS, rot=rot_c, major_segs=28, minor_segs=6)
u_ax = cn.cross(Vector((0, 0, 1))).normalized()
v_ax = cn.cross(u_ax).normalized()
prism(cc + cn * 0.0085, v_ax, u_ax, cn, [(0.02, 0), (0, 0.004), (-0.02, 0), (0, -0.004)], 0.002,
      kit.mat('#b01818', 0.4), name='needle')
w_ax = Vector((0, 1, 0)) - cn * cn.y
w_ax.normalize()
hinge = cc + w_ax * 0.03
kit.cylinder(hinge + cn * 0.029 + w_ax * 0.004, 0.03, 0.005, BRASS, rot=kit.rot_between((0, 0, 0), w_ax),
             verts=28)  # open lid
kit.cylinder(hinge + cn * 0.029 - w_ax * 0.0, 0.025, 0.002, PAPER, rot=kit.rot_between((0, 0, 0), w_ax),
             verts=24)  # map scrap inside the lid
kit.torus(cc - w_ax * 0.034, 0.006, 0.002, BRASS, rot=kit.rot_between((0, 0, 0), u_ax), major_segs=12,
          minor_segs=4)  # bow ring

# ── boots, jean cuffs, back pockets ──────────────────────────────────────
BO = kit._meta('dr_boots')
for s in ('l', 'r'):
    kn, ft = a[f'knee_{s}'], a[f'foot_{s}']
    ank = ft + Vector((0, 0.05, 0.1))
    kit.blob_ellipsoid(BO, ank + Vector((0, -0.05, -0.052)), (0.06, 0.135, 0.058))
    kit.blob_limb(BO, ank - Vector((0, 0, 0.03)), ank + Vector((0, 0, 0.07)), 0.058, 0.055)
    kit.sphere(ank + Vector((0, -0.05, -0.094)), (0.052, 0.122, 0.014), DARK_LEATHER, segs=24, rings=8)  # sole
    cz = ank + Vector((0, 0, 0.09))
    kit.torus(cz, limb_r(kn, ank, 0.82) + 0.008, 0.011, DENIM, major_segs=28, minor_segs=8)
kit.solidify_blobs({'dr_boots': LEATHER})


def patch(center, U, V, w, h, m, lift, only, nu=6, nv=6, name='patch'):
    """Cloth patch conforming to the body surface."""
    rows = []
    for i in range(nv):
        row = []
        for j in range(nu):
            u = (j / (nu - 1) - 0.5) * w
            v = (i / (nv - 1) - 0.5) * h
            row.append(snap(Vector(center) + Vector(U) * u + Vector(V) * v, lift, only))
        rows.append(row)
    return grid(rows, m, name=name, thickness=0.003, offset=1)


for sx in (1, -1):
    # back pockets
    patch((0.075 * sx, 0.3, 0.9), (1, 0, 0), (0, 0, 1), 0.075, 0.085, DENIM_D, 0.004, ('bottom_mesh', 'jeans'),
          name='pocket')
    # front pocket openings
    kit.tube([snap((x * sx, -0.3, z), 0.004, ('bottom_mesh', 'jeans')) for x, z in ((0.065, 0.985), (0.1, 0.955), (0.125, 0.92))],
             0.0035, DENIM_D, name='pocket_edge', resolution=4)

kit.finalize('drake')
