"""Ezio Auditore (Assassin's Creed II) — fan-art collectible statue built from kit primitives."""
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
            hit = tr.ray_cast(c + dirv * 0.15, -dirv, 0.15)
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
WHITE = kit.mat('#f0ece3', 0.8)
WHITE2 = kit.mat('#d9d2c4', 0.85)
SHADOW = kit.mat('#5f5850', 0.9)
RED = kit.mat('#b3141c', 0.7)
MAROON = kit.mat('#5c0f1b', 0.75)
LEATHER = kit.mat('#5a3a22', 0.65)
DARK_LEATHER = kit.mat('#2e211a', 0.6)
SILVER = kit.mat('#d6d9de', 0.22, metal=0.95)
GOLD = kit.mat('#d4a73a', 0.28, metal=0.9)
STEEL = kit.mat('#eef2f7', 0.08, metal=1.0)
GLOVE = kit.mat('#4a2f1c', 0.6)

a = kit.hero(skin='#d6a27a', top='#f0ece3', bottom='#cbc2b2', shoes='#2e211a', hands='#4a2f1c',
             iris='#5a3a1e', brows='#2a1a12', sleeves='long', mouth='line',
             right_arm='guard', left_arm='relaxed', stance='wide', build=1.15)
replace_kit_head()
SKIN_SHADE = '#a87150'
BROW_RIGHT_DZ = 0.0
HEAD_MESH = sculpt_head('ez', '#d6a27a')
TREES_HEAD = BVHTree.FromObject(bpy.data.objects[HEAD_MESH], bpy.context.evaluated_depsgraph_get())
build_trees()

# face: determined brows, firm mouth with the lip scar, short dark beard
eyes('#5a3a1e', '#2a1a12', [(0.011, 1.715), (0.033, 1.726), (0.058, 1.729)])
face_curve([(-0.018, 1.6157), (0, 1.615), (0.018, 1.616)], 0.0015, kit.mat('#5e3228', 0.5), lift=0.001)
decal(0, 1.6085, (0.012, 0.004, 0.0033), kit.mat('#b97a62', 0.5), lift=-0.0006, segs=16, rings=8)
face_curve([(0.0075, 1.628), (0.0105, 1.6115)], 0.0011, kit.mat('#efc8ae', 0.6), lift=0.0017)
BD = kit._meta('ez_beard', resolution=0.003)


def beard_blob(p, r, push=0.0004):
    loc, nor, _i, _d = TREES_HEAD.find_nearest(Vector(p))
    kit.blob_ellipsoid(BD, loc + nor * push, (r * MK, r * MK, r * MK))


for sx in (1, -1):
    path = [Vector(p) for p in ((0.086 * sx, 0.0, 1.655), (0.079 * sx, -0.014, 1.626), (0.066 * sx, -0.042, 1.6),
                                (0.044 * sx, -0.068, 1.584), (0.018 * sx, -0.084, 1.576), (0.0, -0.088, 1.575))]
    for k in range(len(path) - 1):
        for t in (0.0, 0.25, 0.5, 0.75):
            beard_blob(path[k].lerp(path[k + 1], t), 0.0058)
    for x, z in ((0.004, 1.6305), (0.01, 1.6302), (0.016, 1.6285), (0.021, 1.625), (0.024, 1.6205)):
        beard_blob((x * sx, -0.1, z), 0.0034)                       # thin moustache
kit.solidify_blobs({'ez_beard': kit.mat('#3a2619', 0.9)})
H = a['head']

# ── hood: shell with an eagle-beak point, draping onto the shoulders ─────
HC = H + Vector((0, -0.015, 0.003))
RX, RY, RZ = 0.138, 0.126, 0.112
OPEN = [(90, 5), (50, 20), (41, 35), (24, 45), (-8, 54), (-40, 78), (-70, 96), (-90, 102)]
NB, NA = 80, 28
rows = []
for i in range(NA):
    row = []
    t = i / (NA - 1)
    for j in range(NB):
        beta = 2 * math.pi * j / NB
        bd = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(beta)))))
        a0 = math.radians(interp(OPEN, bd))
        al = a0 + (math.pi - 0.02 - a0) * t ** 1.1
        n = Vector((math.sin(al) * math.cos(beta), -math.cos(al), math.sin(al) * math.sin(beta)))
        p = HC + Vector((RX * n.x, RY * n.y, RZ * n.z))
        if n.z < 0:  # lower half falls onto the neck, shoulders and down the back to a point
            k = -n.z
            wb = max(0.0, n.y + 0.1)
            p.z -= (0.05 + 0.24 * wb) * k ** 1.1 + 0.1 * max(0.0, 1 - abs(n.x) * 2.5) * wb * k
            p.x *= 1 + 0.3 * k ** 2 * min(1.0, max(0.0, n.y + 0.3))
            p.y += 0.025 * k ** 2 * wb
        w = max(0.0, 1 - abs(bd - 90) / 28)
        p += Vector((0, -0.01, -0.018)) * w * max(0.0, 1 - t * 5)       # beak point
        p.z += 0.012 * max(0.0, n.z) * max(0.0, 1 - abs(n.x) * 3)        # crest
        p += Vector((n.x, 0, n.z)) * 0.0025 * math.sin(7 * beta + 9 * t)  # soft wrinkles
        if n.z < -0.25:
            p = drape(p, 0.01, maxd=0.025)
        row.append(p)
    rows.append(row)
grid(rows, WHITE, wrap=True, name='hood', thickness=0.006, inner=SHADOW, offset=0, flip=True)
kit.tube([rows[0][j] for j in list(range(NB)) + [0]], 0.004, WHITE, name='hood_rim', resolution=2)

# high collar around the neck, open in a V at the throat
rows = []
for i in range(5):
    t = i / 4
    z = 1.45 + 0.145 * t
    row = []
    for j in range(40):
        th = math.radians(-160 + 320 * j / 39)
        rr = 0.088 - 0.036 * t
        p = Vector((rr * math.sin(th), 0.005 + rr * math.cos(th), z - 0.03 * (1 - math.cos(th)) * t))
        row.append(drape(p, 0.008))
    rows.append(row)
grid(rows, WHITE, name='collar', thickness=0.006, inner=WHITE2, offset=0)

# ── tunic chest: overlapping front flap + the throwing-knife strap ───────
flap = []
for i in range(9):
    z = 1.47 - i * 0.055
    row = []
    for j in range(7):
        x = -0.02 + 0.115 * j / 6 - (0.03 if i < 2 else 0.0) * (1 - j / 6)
        p = drape((x, -0.3, z), 0.006, only=('top_mesh',))
        row.append(drape(Vector((x, p.y - 0.004, z)), 0.006, only=('top_mesh',)))
    flap.append(row)
# re-project each point onto the chest from the front
flap = [[drape(Vector((p.x, -0.02, p.z)), 0.006, only=('top_mesh',)) for p in row] for row in flap]
grid(flap, WHITE, name='flap', thickness=0.005, offset=1)
kit.tube([flap[i][0] for i in range(len(flap))], 0.004, WHITE2, name='flap_edge')

def _snap(p, off, only=('top_mesh',)):
    loc, n, _i, _d = nearest(p, only)
    return loc + n * off


strap_pts = [_snap(Vector(p), 0.008) for p in
             [(0.13, 0.07, 1.04), (0.06, 0.1, 1.17), (-0.04, 0.1, 1.3), (-0.13, 0.08, 1.42), (-0.18, 0.02, 1.49),
              (-0.15, -0.05, 1.42), (-0.09, -0.08, 1.33), (-0.02, -0.08, 1.24), (0.05, -0.08, 1.15),
              (0.11, -0.07, 1.08), (0.14, -0.05, 1.03)]]
kit.tube(strap_pts, 0.012, LEATHER, name='strap')
for k in (6, 7, 8):
    p = strap_pts[k]
    n = nearest(p)[1]
    kit.box(p + n * 0.012, (0.016, 0.006, 0.05), SILVER, rot=(0, 0.75, 0), bevel=0.002)

# ── waist: red sash, leather belt, silver insignia buckle ────────────────
band(0.96, 1.09, RED, 0.012, rows=4, name='sash', thickness=0.008, wobble=0.003)
band(1.005, 1.035, LEATHER, 0.024, rows=2, name='belt', thickness=0.006)
fy = -radial(1.02, math.pi) - 0.034
kit.box((0, fy + 0.006, 1.02), (0.07, 0.008, 0.06), DARK_LEATHER, bevel=0.004)
ins = [(0.0, 0.044), (0.036, -0.026), (0.023, -0.04), (0.011, -0.018), (0.0, 0.0), (-0.011, -0.018),
       (-0.023, -0.04), (-0.036, -0.026)]
prism((0, fy - 0.002, 1.022), (1, 0, 0), (0, 0, 1), (0, 1, 0), ins, 0.008, SILVER, name='insignia')
# hanging sash tails at the right hip
for dx, ln in ((0.0, 0.2), (0.025, 0.15)):
    st = Vector((-0.11 + dx, -radial(1.0, math.pi + 0.6) - 0.015, 1.0))
    kit.tube([st, st + Vector((-0.01, -0.012, -ln * 0.5)), st + Vector((-0.015, -0.006, -ln))], 0.014, RED,
             taper_to=0.75, name='sash_tail')

# ── coat: two layers of flared tails, split at the back, open in front ───
def coat(z_top, z_back, z_side, flare, opening, m, inner, name, lift, nphi=72, nz=14):
    rows = []
    for i in range(nz):
        t = i / (nz - 1)
        row = []
        for j in range(nphi):
            ph = -opening + 2 * opening * j / (nphi - 1)
            c = max(0.0, math.cos(ph))
            zb = z_side + (z_back - z_side) * c ** 1.4
            zb += 0.2 * max(0.0, 1 - abs(ph) / 0.16) * (z_side - z_back) / 0.3  # centre-back split
            fr = max(0.0, (abs(ph) - 1.25) / (opening - 1.25)) ** 1.6          # tailcoat cutaway front
            zb += (z_top - 0.07 - zb) * fr
            z = z_top + (zb - z_top) * t
            r0 = radial(min(z_top, 1.04), ph) + lift
            rr = r0 + flare * t ** 1.4 * (0.8 + 0.2 * math.sin(abs(ph)))
            rr += 0.02 * t ** 1.5 * math.sin(11 * ph)          # vertical folds
            p = Vector((rr * math.sin(ph), rr * math.cos(ph), z))
            row.append(drape(p, lift, only=('bottom_mesh',), maxd=0.03))
        rows.append(row)
    return grid(rows, m, name=name, thickness=0.006, inner=inner, offset=1)


coat(1.0, 0.5, 0.64, 0.17, 2.45, WHITE2, WHITE2, 'coat_under', 0.006)
coat(1.01, 0.56, 0.7, 0.15, 2.3, WHITE, SHADOW, 'coat', 0.011)

# leather pouch on the right hip
PP = Vector((-(radial(1.0, -1.75) + 0.035) * math.sin(1.75), (radial(1.0, -1.75) + 0.035) * math.cos(1.75), 0.975))
kit.box(PP, (0.03, 0.07, 0.065), LEATHER, rot=(0, 0, -0.18), bevel=0.01)
kit.box(PP + Vector((-0.012, 0, 0.02)), (0.012, 0.074, 0.035), DARK_LEATHER, rot=(0, 0, -0.18), bevel=0.006)
kit.sphere(PP + Vector((-0.02, -0.0, 0.012)), 0.006, SILVER, segs=10, rings=6)

# ── maroon cape over the left shoulder with gold trim ────────────────────
CC = a['shoulder_l'] + Vector((-0.03, 0.005, 0.03))
PROFILE = [(0.01, 0.06), (0.04, 0.055), (0.07, 0.035), (0.09, 0.0), (0.1, -0.05), (0.108, -0.1),
           (0.118, -0.15), (0.13, -0.2), (0.145, -0.25)]
NPS, PS0 = 56, 2.25
rows = []
for i, (pr, dz) in enumerate(PROFILE):
    t = i / (len(PROFILE) - 1)
    row = []
    for j in range(NPS):
        ps = -PS0 + 2 * PS0 * j / (NPS - 1)
        rr = pr * (1 + 0.11 * t ** 1.5 * math.sin(6 * ps + 0.5))
        p = CC + Vector((rr * math.cos(ps), rr * 1.3 * math.sin(ps), dz - 0.05 * t * max(0.0, math.sin(ps))))
        row.append(drape(p, 0.012, only=('top_mesh',)))
    rows.append(row)
grid(rows, MAROON, name='cape', thickness=0.007, offset=1)
kit.tube([p + Vector((0, 0, -0.002)) for p in rows[-1]], 0.0055, GOLD, name='cape_trim')
for j in (0, NPS - 1):
    kit.tube([rows[i][j] for i in range(2, len(rows))], 0.0045, GOLD, name='cape_edge')
clasp = rows[3][int(NPS * 0.12)]
kit.sphere(clasp + Vector((0, -0.006, 0)), (0.011, 0.006, 0.011), GOLD, segs=16, rings=8)
kit.tube([clasp, drape((-0.06, -0.12, 1.36), 0.01), drape((-0.17, -0.06, 1.3), 0.01)], 0.004, GOLD,
         name='cape_cord')

# ── bracers + hidden blade ────────────────────────────────────────────────
for s in ('l', 'r'):
    e, h = a[f'elbow_{s}'], a[f'hand_{s}']
    d = (h - e).normalized()
    w = h - d * 0.055
    r0 = limb_r(e, w, 0.35) + 0.007
    r1 = max(limb_r(e, w, 0.9), limb_r(e, w, 1.0)) + 0.01
    p0, p1 = e.lerp(w, 0.25), w + d * 0.022
    kit.rod(p0, p1, r0, LEATHER, verts=24, caps=False, r2=r1)
    for tt, rr in ((0.04, r0), (0.5, (r0 + r1) / 2), (0.96, r1)):
        kit.torus(p0.lerp(p1, tt), rr + 0.002, 0.004, DARK_LEATHER, rot=kit.rot_between(p0, p1),
                  major_segs=24, minor_segs=6)
    # gloved fist
    kit.box(h - d * 0.01, (0.044, 0.052, 0.088), GLOVE, rot=d.to_track_quat('Z', 'Y').to_euler(), bevel=0.014)

e, h = a['elbow_r'], a['hand_r']
d, up, side = basis(h - e)
w = h - d * 0.055
# blade mechanism under the wrist, blade springing past the knuckles
mech = w - d * 0.02 + up * 0.042
kit.box(mech, (0.024, 0.02, 0.07), SILVER, rot=d.to_track_quat('Z', 'Y').to_euler(), bevel=0.005)
L = 0.25
blade = [(0, -0.011), (L - 0.05, -0.011), (L, 0.0), (L - 0.05, 0.011), (0, 0.011)]
prism(mech + up * 0.004, d, side, up, blade, 0.005, STEEL, name='hidden_blade')

# ── sword on the left hip ────────────────────────────────────────────────
s_top, s_bot = Vector((0.17, 0.0, 0.96)), Vector((0.27, 0.42, 0.52))
sw = (s_bot - s_top).normalized()
s_top = drape(s_top, 0.05)
s_bot = s_top + sw * 0.62
kit.rod(s_top, s_bot, 0.017, DARK_LEATHER, verts=12, r2=0.013)
kit.sphere(s_bot, 0.016, SILVER, segs=12, rings=8)
grip_end = s_top - sw * 0.13
kit.rod(s_top - sw * 0.01, grip_end, 0.011, LEATHER, verts=10)
kit.sphere(grip_end - sw * 0.008, 0.016, SILVER, segs=12, rings=8)
kit.box(s_top - sw * 0.01, (0.1, 0.012, 0.012), SILVER, rot=sw.to_track_quat('Z', 'Y').to_euler(), bevel=0.003)
kit.tube([drape((0.12, -0.05, 1.0), 0.03), s_top + Vector((0, 0, 0.01))], 0.006, LEATHER, name='frog')

# ── tall leather boots ───────────────────────────────────────────────────
BO = kit._meta('ez_boots')
for s in ('l', 'r'):
    kn, ft = a[f'knee_{s}'], a[f'foot_{s}']
    ank = ft + Vector((0, 0.05, 0.1))
    top = kn.lerp(ank, 0.12)
    kit.blob_limb(BO, top, ank, limb_r(kn, ank, 0.12) + 0.012, limb_r(kn, ank, 0.95) + 0.012)
    kit.blob_ellipsoid(BO, kn.lerp(ank, 0.3) + Vector((0, 0.025, 0)), (0.066, 0.066, 0.12))
    for tt in (0.55, 0.78):
        c = kn.lerp(ank, tt)
        kit.torus(c, limb_r(kn, ank, tt) + 0.016, 0.006, LEATHER, major_segs=24, minor_segs=6)
        kit.box(c + Vector((0.0, -limb_r(kn, ank, tt) - 0.022, 0)), (0.02, 0.006, 0.018), SILVER, bevel=0.002)
    kit.blob_ellipsoid(BO, ank + Vector((0, -0.05, -0.055)), (0.056, 0.13, 0.054))
    kit.torus(top + Vector((0, 0, 0.005)), limb_r(kn, ank, 0.12) + 0.016, 0.01, DARK_LEATHER,
              major_segs=28, minor_segs=8)

kit.solidify_blobs({'ez_boots': DARK_LEATHER})
kit.finalize('ezio')
