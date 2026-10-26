"""Asta (Black Clover) — premium-statue take: compact, buff, planted power stance; spiky ash-blond hair, black
headband, determined grin; long flowing Black Bulls cloak with gold trim, bunched hood and bull emblem; the huge chipped,
rusted Demon-Slayer Sword resting on his shoulder; floating five-leaf-clover grimoire."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

V = Vector


# ── local helpers ───────────────────────────────────────────────────────
def _objs():
    return set(o.name for o in bpy.context.scene.objects)


def transform_group(names, M):
    bpy.context.view_layer.update()   # make sure freshly scaled primitives have current matrices
    for n in names:
        o = bpy.data.objects[n]
        o.matrix_world = M @ o.matrix_world


def bvh(*objs):
    """BVH of the evaluated, world-space geometry of the given objects (for surface snapping)."""
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        off = len(verts)
        verts += [o.matrix_world @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def snap(tree, p, centre, offset=0.0):
    """Project p onto the surface along the ray from outside towards `centre`; push out by offset."""
    p, centre = V(p), V(centre)
    d = (p - centre).normalized()
    hit, n, _, _ = tree.ray_cast(centre + d * 1.0, -d)
    if hit is None:
        return p
    return hit + d * offset


def snap_dir(tree, p, direction, offset=0.0):
    """Project p onto the surface along a fixed direction (ray comes from -direction*far)."""
    d = V(direction).normalized()
    hit, n, _, _ = tree.ray_cast(V(p) - d * 1.0, d)
    if hit is None:
        return V(p)
    return hit - d * offset


def wrap_band(tree, centre, axis, h0, h1, m, off0=0.003, bulge=0.012, n=48, rows=5, name='band', reach=0.6,
              arc=None):
    """Cloth band hugging a surface around `axis` through `centre` (sashes, cuffs, headbands, collars).
    arc=(deg0, deg1) makes an open strip; angle 0 = +X, 90 = +Y (back), measured around the axis."""
    axis = V(axis).normalized()
    u = V((1, 0, 0)) - axis * axis.x
    u = u.normalized() if u.length > 1e-4 else axis.orthogonal().normalized()
    v = axis.cross(u)
    bm = bmesh.new()
    grid = []
    cols = n + 1 if arc else n
    for j in range(rows + 1):
        t = j / rows
        c = V(centre) + axis * (h0 + (h1 - h0) * t)
        off = off0 + bulge * math.sin(math.pi * t)
        row = []
        for i in range(cols):
            if arc:
                ang = math.radians(arc[0] + (arc[1] - arc[0]) * i / n)
            else:
                ang = 2 * math.pi * i / n
            d = u * math.cos(ang) + v * math.sin(ang)
            hit, _, _, _ = tree.ray_cast(c + d * reach, -d)
            p = (hit if hit is not None else c + d * 0.1) + d * off
            row.append(bm.verts.new(p))
        grid.append(row)
    for j in range(rows):
        for i in range(n):
            i2 = i + 1 if arc else (i + 1) % n
            bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    if arc:
        solidify(obj, 0.004)
    return obj


def cut_half(obj, keep='below'):
    """Bisect a primitive at its local z=0 plane and cap the hole."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    no = V((0, 0, 1)) if keep == 'below' else V((0, 0, -1))
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V((0, 0, 0)),
                           plane_no=no, clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)
    bm.to_mesh(obj.data)
    bm.free()
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def garment(obj, z_hem, x_top, z_top, x_bot, neck_r=None, neck_z=None, neck_y=0.0, hem_tilt=0.0):
    """Turn a closed metaball blob into an open garment: cut the hem, a V/straight front opening and a
    neckline. Returns the boundary loops (for trims)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V((0, 0, z_hem)),
                           plane_no=V((0, hem_tilt, 1)).normalized(), clear_inner=True)
    for sx in (1, -1):
        p0, p1 = V((x_top * sx, 0, z_top)), V((x_bot * sx, 0, z_hem))
        n = (p1 - p0).normalized().cross(V((0, 1, 0)))
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=p0, plane_no=n)

    def edge_x(z):
        t = (z - z_top) / (z_hem - z_top)
        return x_top + (x_bot - x_top) * t

    kill = set()
    for f in bm.faces:
        c = f.calc_center_median()
        if c.y < 0 and abs(c.x) < edge_x(c.z):
            kill.add(f)
        if neck_r and c.z > neck_z and math.hypot(c.x, c.y - neck_y) < neck_r:
            kill.add(f)
    bmesh.ops.delete(bm, geom=list(kill), context='FACES')
    # drop small islands left over by the cuts
    bm.faces.ensure_lookup_table()
    seen, islands = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, isl = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    junk = [f for isl in islands[1:] if len(isl) < 200 for f in isl]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context='FACES')
    loops = _boundary_loops(bm)
    bm.to_mesh(obj.data)
    bm.free()
    for p in obj.data.polygons:
        p.use_smooth = True
    return loops


def _boundary_loops(bm):
    edges = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in edges:
        for v in e.verts:
            adj.setdefault(v.index, []).append(e)
    used, loops = set(), []
    for e0 in edges:
        if e0.index in used:
            continue
        used.add(e0.index)
        start, cur = e0.verts[0], e0.verts[1]
        pts = [start.co.copy(), cur.co.copy()]
        while True:
            nxt = [e for e in adj.get(cur.index, []) if e.index not in used]
            if not nxt:
                break
            e = nxt[0]
            used.add(e.index)
            cur = e.other_vert(cur)
            pts.append(cur.co.copy())
            if cur == start:
                break
        if len(pts) > 12:
            loops.append(pts)
    return loops


def smooth_pts(pts, step=2, iters=3):
    pts = [V(p) for p in pts[::step]]
    for _ in range(iters):
        pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
    return pts


def solidify(obj, thick, offset=-1.0):
    mod = obj.modifiers.new('solid', 'SOLIDIFY')
    mod.thickness = thick
    mod.offset = offset
    return obj


def snap_n(tree, p, direction=(0, 1, 0)):
    d = V(direction).normalized()
    hit, n, _, _ = tree.ray_cast(V(p) - d * 1.0, d)
    return hit, n


def face_frame(tree, p):
    """Surface point + rotation matrix whose local -Y faces out of the surface (for decals on the face)."""
    hit, n = snap_n(tree, p)
    q = (-n).to_track_quat('Y', 'Z')
    return hit, n, q.to_matrix(), q.to_euler()


def rebuild_head(H, k=1.0, res=0.0062, name='head'):
    """Swap hero()'s generic head for a sculpted anime-statue head (smaller nose, pointed chin), scaled by k."""
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and not o.name.endswith('_mesh'):
            c = o.matrix_world @ (sum((V(b) for b in o.bound_box), V()) / 8)
            if c.z > 1.5:
                bpy.data.objects.remove(o)
    skin = bpy.data.objects['skin_mesh']
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 1.56 and abs(v.co.x) < 0.17], context='VERTS')
    bm.to_mesh(skin.data)
    bm.free()
    mb = kit._meta(name, resolution=res)

    def Eh(off, size, rot=(0, 0, 0)):
        kit.blob_ellipsoid(mb, H + V(off) * k, tuple(x * 1.38 * k for x in size), rot=rot)

    kit.blob_limb(mb, (0, 0.006, 1.5), (0, 0.0, H.z - 0.06 * k), 0.078, 0.074, steps=6)   # neck
    Eh((0, 0.01, 0.02), (0.088, 0.1, 0.104))                                  # cranium
    Eh((0, -0.024, -0.04), (0.07, 0.074, 0.068))                              # face mass
    Eh((0, -0.044, -0.084), (0.042, 0.044, 0.04))                             # jaw
    Eh((0, -0.064, -0.11), (0.018, 0.016, 0.012))                             # chin
    Eh((0, -0.094, -0.03), (0.0075, 0.011, 0.015), rot=(-0.3, 0, 0))          # nose
    for sx in (1, -1):
        Eh((0.042 * sx, -0.058, -0.036), (0.028, 0.026, 0.026))               # cheeks
        Eh((0.084 * sx, 0.008, -0.012), (0.011, 0.02, 0.026))                 # ears
    return mb


def E(mb, co, size, rot=(0, 0, 0)):
    """Ellipsoid blob whose visible half-extents ~= size."""
    kit.blob_ellipsoid(mb, co, tuple(x * 1.38 for x in size), rot=rot)


def along(a, b):
    """Euler that points local +Z from a to b (for ellipsoids aligned with a limb)."""
    return kit.rot_between(a, b)


def strip_hero_legs():
    """Remove hero()'s pelvis/legs/shoes so a custom posed lower body can be built."""
    bpy.data.objects.remove(bpy.data.objects['bottom_mesh'])
    for o in list(bpy.context.scene.objects):
        if o.type == 'MESH' and not o.name.endswith('_mesh'):
            c = o.matrix_world @ (sum((V(b) for b in o.bound_box), V()) / 8)
            if c.z < 0.25:
                bpy.data.objects.remove(o)
    skin = bpy.data.objects['skin_mesh']
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 0.9], context='VERTS')
    bm.to_mesh(skin.data)
    bm.free()


def remove_arm(sx, x_cut=0.262):
    """Delete hero()'s arm on side sx (+1 left / -1 right) — use with an 'out' pose."""
    skin = bpy.data.objects['skin_mesh']
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x * sx > x_cut and 1.2 < v.co.z < 1.6],
                     context='VERTS')
    bm.to_mesh(skin.data)
    bm.free()


def leg(mb, hip, knee, ank, fdir, W, foot=True):
    """Muscular leg (skin) from hip to ankle with knee, calf and a foot pointing along fdir."""
    hip, knee, ank, fdir = V(hip), V(knee), V(ank), V(fdir).normalized()
    shin = (ank - knee).normalized()
    back = (V((0, 1, 0)) - shin * shin.y).normalized()
    kit.blob_limb(mb, hip, knee, 0.105 * W, 0.078 * W)
    E(mb, hip.lerp(knee, 0.4), (0.07 * W, 0.075 * W, 0.13), rot=along(hip, knee))                                                         # quads
    kit.blob_ball(mb, knee, 0.08 * W)
    kit.blob_limb(mb, knee, ank, 0.075 * W, 0.05 * W)
    E(mb, knee.lerp(ank, 0.3) + back * 0.018, (0.052 * W, 0.055 * W, 0.1), rot=along(knee, ank))   # calf
    kit.blob_ball(mb, ank, 0.056 * W)
    if foot:
        fc = ank + fdir * 0.06 + V((0, 0, -0.045))
        q = V((0, 1, 0)).rotation_difference(fdir)
        E(mb, fc, (0.045, 0.1, 0.034), rot=q.to_euler())
    return fdir


def decal(tree, outline, m, offset=0.0012, centre=None, rings=4, name='decal', dirv=(0, 1, 0)):
    """Thin patch conforming to a surface seen from the front (-Y): mouths, markings. `outline` = [(x, z)]."""
    if centre is None:
        centre = (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
    cx, cz = centre
    bm = bmesh.new()
    vc = bm.verts.new(snap_dir(tree, (cx, 0, cz), dirv, offset))
    grid = []
    for k in range(1, rings + 1):
        t = k / rings
        grid.append([bm.verts.new(snap_dir(tree, (cx + (x - cx) * t, 0, cz + (z - cz) * t), dirv, offset))
                     for x, z in outline])
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vc, grid[0][i], grid[0][j]))
        for k in range(rings - 1):
            bm.faces.new((grid[k][i], grid[k + 1][i], grid[k + 1][j], grid[k][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    return obj


def anime_eye(tree, sx, cx, cz, w, hgt, iris, pupil='#050505', lash=0.0028, iris_k=0.72):
    c, n, R, eul = face_frame(tree, (cx * sx, 0, cz))
    kit.sphere(c + n * 0.0006, (w, 0.006, hgt), kit.mat('#fbf8f2', 0.25), rot=eul, segs=20, rings=10)
    kit.sphere(c + n * 0.0026, (w * iris_k, 0.0052, hgt * 0.86), kit.mat(iris, 0.2), rot=eul, segs=16, rings=8)
    if pupil:
        kit.sphere(c + n * 0.0042, (w * iris_k * 0.5, 0.004, hgt * 0.45), kit.mat(pupil, 0.15), rot=eul,
                   segs=12, rings=6)
    kit.sphere(c + n * 0.0072 + R @ V((w * 0.28 * -sx, 0, hgt * 0.38)), 0.0035, kit.mat('#ffffff', 0.1),
               segs=8, rings=6)
    pts = []
    for k in range(7):
        a_ = math.radians(178 - k * 30) if sx > 0 else math.radians(2 + k * 30)
        pts.append(c + R @ V((w * 1.04 * math.cos(a_), -0.0045, hgt * 1.0 * math.sin(a_) + 0.001)))
    # outer flick
    outer = pts[-1] if sx > 0 else pts[0]
    flick = outer + R @ V((0.008 * sx, -0.002, 0.004))
    if sx > 0:
        pts.append(flick)
    else:
        pts.insert(0, flick)
    kit.tube(pts, lash, kit.mat('#0b0b0b', 0.4), taper_to=None, resolution=3)
    return c, n, R


def prism(outline, depth, m, name='prism'):
    """Extrude a 2D outline in the XZ plane by `depth` along Y (centred)."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -depth / 2, z)) for x, z in outline]
    back = [bm.verts.new((x, depth / 2, z)) for x, z in outline]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    k = len(outline)
    for i in range(k):
        bm.faces.new((front[i], back[i], back[(i + 1) % k], front[(i + 1) % k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m)
    return obj


# ── palette ─────────────────────────────────────────────────────────────
SKIN = '#efc29a'
HAIR_C = '#cfc8ac'      # ash blond
TOP = '#383b44'
PANTS = '#3b3d48'
BOOTS = '#2e1c12'
ROBE = '#0f0f13'
GOLD = '#d6a43a'
BLADE = '#2a292d'
RUST = '#5e3220'
WRAP = '#3b2b22'
GREEN = '#34b35a'

kit.reset()
W_ = 1.2
a = kit.hero(skin=SKIN, top=TOP, bottom=PANTS, shoes=BOOTS, sleeves='none', pants='long', mouth='line',
             right_arm='down', left_arm='out', stance='wide', build=W_)
S = kit.mat(SKIN, 0.5)
K = 1.1                        # head scale
DROP = 0.08                    # bent-knee power stance: upper body lowered by this much
strip_hero_legs()
remove_arm(+1)
H = V((0, -0.01, 1.575 + 0.12 * K))
rebuild_head(H, k=K, res=0.007, name='ahead')
kit.solidify_blobs({'ahead': S})
head_o = bpy.data.objects['ahead_mesh']
skin_o, top_o = (bpy.data.objects[n] for n in ('skin_mesh', 'top_mesh'))
G_ = kit.mat(GOLD, 0.3, metal=0.9)
BLK = kit.mat(ROBE, 0.55)


# ── the Demon-Slayer Sword's frame: resting on his LEFT shoulder, blade sweeping up and back ──
D = V((0.55, 0.75, 0.37)).normalized()                  # hilt -> tip
Wd = (V((0, 0, 1)) - D * D.z).normalized()              # blade width direction (edge on the shoulder)
Nn = D.cross(Wd).normalized()                           # flat of the blade (faces the 3/4 camera)
HW = 0.088                                              # blade half-width
contact = V((0.245, 0.03, 1.515))
Q = contact + Wd * HW
GRIP = Q - D * 0.25
SWORD_M = Matrix((Wd, Nn, D)).transposed().to_4x4()
SWORD_M.translation = GRIP

# ── left arm rebuilt to grip the hilt in front of the shoulder ──────────
mb = kit._meta('aarm', resolution=0.0095)
Sh = a['shoulder_l']
El = V((0.3, -0.16, 1.24))
palm = GRIP + Nn * 0.012 + V((0, -0.01, -0.012))
Wr = palm - (palm - El).normalized() * 0.05
kit.blob_ball(mb, Sh + V((-0.004, 0, 0.006)), 0.1 * W_)                          # deltoid
kit.blob_limb(mb, Sh, El, 0.08 * W_, 0.064 * W_)
E(mb, Sh.lerp(El, 0.47) + V((0, -0.014, 0)), (0.064, 0.064, 0.09), rot=along(Sh, El))   # bicep
kit.blob_limb(mb, El, Wr, 0.066 * W_, 0.048 * W_)
E(mb, El.lerp(Wr, 0.28), (0.055, 0.052, 0.088), rot=along(El, Wr))           # forearm muscle
E(mb, palm, (0.05, 0.055, 0.05))                                                # fist around the grip
for i in range(4):
    kit.blob_ball(mb, palm + Nn * 0.02 + D * (-0.03 + i * 0.02), 0.026)          # fingers wrapped
kit.solidify_blobs({'aarm': S})

# ── muscle on the hero right arm ─────────────────────
mb = kit._meta('abulk', resolution=0.012)
sr, er, hr = a['shoulder_r'], a['elbow_r'], a['hand_r']
E(mb, sr.lerp(er, 0.47) + V((0, -0.012, 0)), (0.064, 0.064, 0.095), rot=along(sr, er))
E(mb, er.lerp(hr, 0.28), (0.054, 0.052, 0.09), rot=along(er, hr))
kit.blob_ball(mb, sr + V((-0.004, 0, 0.004)), 0.1 * W_)
kit.solidify_blobs({'abulk': S})
# broader chest for a V-shaped silhouette
mb = kit._meta('achest', resolution=0.012)
E(mb, (0, -0.02, 1.36), (0.17, 0.105, 0.1))
E(mb, (0, 0.01, 1.3), (0.165, 0.1, 0.1))
kit.solidify_blobs({'achest': kit.mat(TOP, 0.7)})

# ── right hand: clenched fist ───────────────────────────────────────────
mb = kit._meta('afist', resolution=0.006)
pr = a['hand_r']
E(mb, pr + V((0, -0.006, -0.008)), (0.042, 0.046, 0.05))
for i in range(4):
    kit.blob_ball(mb, pr + V((-0.012, -0.03 + i * 0.019, -0.04)), 0.024)
kit.solidify_blobs({'afist': S})

# ── black wristbands ───────────────────────────────────────────────────
T_RARM = bvh(skin_o)
el_r = a['elbow_r']
ax = (a['hand_r'] - el_r).normalized()
wrap_band(T_RARM, el_r.lerp(a['hand_r'], 0.7), ax, -0.03, 0.02, BLK, off0=0.002, bulge=0.006, n=32, rows=3,
          name='wb', reach=0.09)
T_LARM = bvh(bpy.data.objects['aarm_mesh'])
wrap_band(T_LARM, El.lerp(Wr, 0.72), (Wr - El).normalized(), -0.03, 0.02, BLK, off0=0.002, bulge=0.006, n=32,
          rows=3, name='wb', reach=0.09)

# ── Black Bulls robe: long cloak draped over the shoulders, flaring behind him, gold trim ──
w = W_
mb = kit._meta('acloak', resolution=0.0175)
kit.blob_ellipsoid(mb, (0, 0.01, 1.2), (0.175 * w + 0.03, 0.115 * w + 0.04, 0.14))
kit.blob_ellipsoid(mb, (0, 0, 1.33), (0.21 * w + 0.03, 0.128 * w + 0.032, 0.15))
kit.blob_ellipsoid(mb, (0, -0.03 * w, 1.37), (0.17 * w + 0.03, 0.1 * w + 0.03, 0.08))
for sx in (1, -1):
    kit.blob_limb(mb, (0.05 * sx, 0.014, 1.5), (0.235 * w * sx, 0, 1.46), 0.08, 0.09, steps=4)
    kit.blob_ball(mb, (0.27 * sx, 0.0, 1.44), 0.105)
E(mb, (0, 0.09, 1.49), (0.13, 0.075, 0.06))                                # bunched hood
E(mb, (0, 0.11, 1.43), (0.16, 0.06, 0.05))
NZ = 15
for k in range(NZ):                                                        # back drape, flaring out behind
    t = k / (NZ - 1)
    z = 1.36 - t * 0.78
    y = 0.1 + 0.2 * t ** 1.6
    sway = 0.04 * t ** 2
    E(mb, (sway, y, z), (0.2 + 0.13 * t, 0.03, 0.06))
    if k >= 4:                                                             # folds
        for j, fx in enumerate((-0.22, -0.08, 0.06, 0.2)):
            E(mb, (sway + fx * (1 + 0.5 * t), y + (0.03 if j % 2 else -0.01) * t, z), (0.04, 0.032, 0.06))
    for sx in (1, -1):                                                     # sides hanging behind the arms
        if z > 0.75:
            E(mb, (sx * (0.25 + 0.08 * t) + sway, 0.05 + 0.13 * t, z), (0.045, 0.06, 0.06))
kit.solidify_blobs({'acloak': BLK})
cloak = bpy.data.objects['acloak_mesh']
loops = garment(cloak, z_hem=0.84, x_top=0.06, z_top=1.52, x_bot=0.34, hem_tilt=0.85)
T_CLOAK = bvh(cloak)
solidify(cloak, 0.008)
for lp in loops:
    kit.tube(smooth_pts(lp, step=3), 0.0075, G_, resolution=1, name='ctrim')
# clasp chain across the chest
for sx in (1, -1):
    kit.sphere(snap_dir(T_CLOAK, (0.105 * sx, 0, 1.45), (0, 1, 0), 0.004), 0.012, G_, segs=12, rings=8)
kit.tube([snap_dir(T_CLOAK, (0.105, 0, 1.45), (0, 1, 0), 0.004), V((0, -0.15, 1.41)),
          snap_dir(T_CLOAK, (-0.105, 0, 1.45), (0, 1, 0), 0.004)], 0.0035, G_, resolution=6)
# bull emblem on the back
bz = 1.18
face = [(0.05 * math.sin(t) * (1.0 if math.cos(t) > 0 else 0.55), bz + 0.056 * math.cos(t))
        for t in [2 * math.pi * k / 20 for k in range(20)]]
decal(T_CLOAK, face, G_, offset=0.004, centre=(0, bz), name='emblem', dirv=(0, -1, 0))
for sx in (1, -1):
    pts = [snap_dir(T_CLOAK, (x * sx, 0, z), (0, -1, 0), 0.006) for x, z in
           ((0.036, bz + 0.035), (0.1, bz + 0.05), (0.15, bz + 0.095), (0.155, bz + 0.16))]
    kit.tube(pts, 0.015, G_, taper_to=0.25, resolution=6)
    kit.sphere(snap_dir(T_CLOAK, (0.02 * sx, 0, bz + 0.01), (0, -1, 0), 0.007), 0.01, BLK, segs=8, rings=6)

# ── face: green eyes, angry brows, gritted-teeth grin ──────────────────
T_FACE = bvh(head_o)
for sx in (1, -1):
    anime_eye(T_FACE, sx, 0.04 * K, H.z - 0.006 * K, 0.02 * K, 0.017 * K, GREEN, pupil='#0a0a0a', lash=0.0034, iris_k=0.68)
    kit.tube([snap_dir(T_FACE, (x * sx * K, 0, H.z + dz * K), (0, 1, 0), 0.002)
              for x, dz in ((0.014, 0.012), (0.035, 0.022), (0.06, 0.03))], 0.0042, kit.mat('#8d866f', 0.6),
             taper_to=0.45, resolution=3)
MW, MT, MB = 0.034 * K, -0.064 * K, -0.085 * K
top_edge = [(x, H.z + MT + 0.006 * K * (x / MW) ** 2) for x in [MW * (i / 6 - 1) for i in range(13)]]
bottom = [(MW * math.cos(t), H.z + MT + 0.006 * K - (MT + 0.006 * K - MB) * math.sin(t) ** 0.6)
          for t in [math.pi * k / 12 for k in range(1, 12)]]
decal(T_FACE, top_edge + bottom, kit.mat('#4a0e10', 0.5), offset=0.0008, centre=(0, H.z - 0.074 * K), name='mouth')
inner = [(x * 0.92, z - 0.0015) for x, z in top_edge] + [(x * 0.92, z + 0.0025) for x, z in bottom]
decal(T_FACE, inner, kit.mat('#ffffff', 0.3), offset=0.0015, centre=(0, H.z - 0.073 * K), name='teeth')
kit.tube([snap_dir(T_FACE, (x * K, 0, H.z - 0.072 * K + 0.004 * K * (x * K / MW) ** 2), (0, 1, 0), 0.002)
          for x in (-0.03, -0.015, 0, 0.015, 0.03)], 0.0012, kit.mat('#3a1010', 0.5), resolution=3)
for sx in (1, -1):
    kit.tube([snap_dir(T_FACE, (0.034 * sx * K, 0, H.z - 0.059 * K), (0, 1, 0), 0.001),
              snap_dir(T_FACE, (0.042 * sx * K, 0, H.z - 0.05 * K), (0, 1, 0), 0.001)], 0.0018, kit.mat('#8a3a30', 0.5),
             resolution=3)

# ── spiky ash-blond hair + black headband ──────────────────────────────
HAIR = kit.mat(HAIR_C, 0.5)
cap = kit.sphere(H + V((0, 0.018, 0.03)) * 1.0 + V((0, 0, 0.03 * (K - 1))), (0.09 * K, 0.1 * K, 0.095 * K), HAIR,
                 segs=32, rings=16)
kit.subdivide(cap, 1)
T_HEAD = bvh(head_o, cap)
hc = H + V((0, 0.008, 0.02 * K))


def sph(az, el, rad=0.15 * K):
    az, el = math.radians(az), math.radians(el)
    return hc + V((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el))) * rad


def hspike(az, el, length, radius=0.026, lift=0.6, curl=0.0):
    """Tapered spike rooted on the scalp, pointing outward and swept upward by `lift`."""
    root = snap(T_HEAD, sph(az, el), hc, -0.012)
    n = (root - hc).normalized()
    d = (n + V((0, 0.12, lift))).normalized()
    mid = root + d * length * K * 0.55 + V((0, 0, curl))
    tip = root + d * length * K + V((0, 0, curl * 1.4))
    kit.tube([root, mid, tip], radius * K, HAIR, taper_to=0.04, resolution=4)


# crown + back: big spikes sweeping up and back
for az, el, ln in ((0, 80, 0.15), (40, 72, 0.15), (-40, 72, 0.15), (80, 62, 0.14), (-80, 62, 0.14),
                   (120, 60, 0.14), (-120, 60, 0.14), (160, 58, 0.13), (-160, 58, 0.13), (180, 70, 0.14),
                   (20, 55, 0.13), (-20, 55, 0.13), (60, 45, 0.12), (-60, 45, 0.12), (100, 35, 0.12),
                   (-100, 35, 0.12), (140, 30, 0.12), (-140, 30, 0.12), (180, 35, 0.12), (165, 10, 0.1),
                   (-165, 10, 0.1), (125, 5, 0.1), (-125, 5, 0.1), (95, 12, 0.09), (-95, 12, 0.09),
                   (0, 62, 0.13), (30, 88, 0.13), (-150, 82, 0.13)):
    hspike(az, el, ln, radius=0.027, lift=0.75 if el > 40 else 0.35)
# front spikes jutting up over the headband
for az, ln in ((-34, 0.12), (-14, 0.13), (6, 0.13), (26, 0.12), (46, 0.11), (-52, 0.1)):
    hspike(az, 45, ln, radius=0.024, lift=1.1)
# a few bangs falling over the band onto the forehead
for x, tip in ((-0.03, -0.05), (0.04, 0.056)):
    root = snap_dir(T_HEAD, (x * K, 0, H.z + 0.08 * K), (0, 1, 0), -0.006)
    t1 = snap_dir(T_HEAD, (x * 1.1 * K, 0, H.z + 0.05 * K), (0, 1, 0), 0.012)
    t2 = snap_dir(T_HEAD, (tip * K, 0, H.z + 0.02 * K), (0, 1, 0), 0.006)
    kit.tube([root, t1, t2], 0.017, HAIR, taper_to=0.05, resolution=4)
HB = kit.mat('#141414', 0.7)
band_ax = V((0, 0.28, 1)).normalized()
wrap_band(T_HEAD, H + V((0, 0.0, 0.046 * K)), band_ax, -0.018, 0.018, HB, off0=0.003, bulge=0.006, n=56,
          name='headband', reach=0.25)
knot = snap_dir(T_HEAD, (0, 0, H.z + 0.075 * K), (0, -1, 0), 0.008)
kit.sphere(knot, (0.018, 0.012, 0.014), HB, segs=12, rings=8)
for sx in (1, -1):
    kit.tube([knot, knot + V((0.03 * sx, 0.04, -0.02)), knot + V((0.05 * sx, 0.07, -0.06))], 0.01, HB,
             taper_to=0.4, resolution=5)

# ── the Demon-Slayer Sword ─────────────────────────────────────────────
before = _objs()
BL = kit.mat(BLADE, 0.6, metal=0.85)
RU = kit.mat(RUST, 0.9)
L0, L1 = 0.13, 1.38        # blade start/end along the axis (grip centre = 0)
w_ = HW
left = [(-w_, L0), (-w_, 0.34), (-w_ + 0.022, 0.36), (-w_ + 0.006, 0.39), (-w_ - 0.004, 0.62),
        (-w_ + 0.03, 0.65), (-w_ + 0.014, 0.69), (-w_ - 0.004, 0.71), (-w_ - 0.008, 0.95),
        (-w_ + 0.018, 0.98), (-w_ - 0.004, 1.01), (-w_ - 0.008, 1.2), (-w_ + 0.02, 1.235), (-w_ - 0.004, 1.26),
        (-w_ - 0.004, L1 - 0.05), (-0.02, L1)]
right = [(w_ + 0.006, L1 - 0.09), (w_, 1.2), (w_ - 0.026, 1.17), (w_ - 0.006, 1.13), (w_ + 0.004, 0.88),
         (w_ - 0.03, 0.85), (w_ - 0.01, 0.8), (w_, 0.52), (w_ - 0.02, 0.495), (w_, 0.47), (w_, L0)]
blade = prism(left + right, 0.024, BL, name='blade')
blade.data.polygons.foreach_set('use_smooth', [False] * len(blade.data.polygons))
# darker raised spine + rust blotches on both flats
kit.box((0, 0, (L0 + L1 - 0.12) / 2), (0.026, 0.03, L1 - L0 - 0.16), kit.mat('#1c1b1e', 0.5, metal=0.85),
        bevel=0.004)
# rust: grid the blade flats with bisects, then paint cells by a cheap noise (no extra geometry/outlines)
blade.data.materials.append(RU)
bm = bmesh.new()
bm.from_mesh(blade.data)
for k in range(1, 84):
    z = L0 + (L1 - L0) * k / 84
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V((0, 0, z)),
                           plane_no=V((0, 0, 1)))
for k in range(1, 15):
    x = -w_ + 2 * w_ * k / 15
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=V((x, 0, 0)),
                           plane_no=V((1, 0, 0)))
import random  # noqa: E402
random.seed(11)
patches = []
for side in (-1, 1):
    for zc in (0.32, 0.6, 0.86, 1.08, 1.3):
        patches.append((side, random.uniform(-0.055, 0.055), zc + random.uniform(-0.06, 0.06),
                        random.uniform(0.02, 0.045), random.uniform(0, 6.3), random.uniform(1.2, 2.2)))


def rusty(x, z, side):
    for sd, cx, cz, rr, ph, st in patches:
        if sd != side:
            continue
        dx, dz = x - cx, (z - cz) / st
        ang = math.atan2(dz, dx)
        lim = rr * (1 + 0.35 * math.sin(3 * ang + ph) + 0.2 * math.sin(5 * ang + 2 * ph))
        if math.hypot(dx, dz) < lim:
            return True
    return False


for f in bm.faces:
    c = f.calc_center_median()
    if abs(f.normal.y) > 0.9 and rusty(c.x, c.z, 1 if c.y > 0 else -1):
        f.material_index = 1
bm.to_mesh(blade.data)
bm.free()
blade.data.polygons.foreach_set('use_smooth', [False] * len(blade.data.polygons))
# guard, cloth-wrapped grip, pommel
IRON = kit.mat('#1d1b1b', 0.45, metal=0.9)
kit.box((0, 0, 0.115), (0.2, 0.05, 0.035), IRON, bevel=0.006)
kit.cylinder((0, 0, 0.0), 0.022, 0.21, kit.mat(WRAP, 0.95), verts=16)
for i in range(7):
    kit.torus((0, 0, -0.09 + i * 0.03), 0.023, 0.006, kit.mat('#261b15', 0.95), rot=(0.4, 0, 0),
              major_segs=16, minor_segs=6)
kit.sphere((0, 0, -0.12), (0.03, 0.03, 0.025), IRON, segs=16, rings=8)
kit.tube([(0, -0.02, -0.1), (0.02, -0.05, -0.15), (0.03, -0.07, -0.22)], 0.007, kit.mat(WRAP, 0.95),
         taper_to=0.4, resolution=6)        # loose wrap end
sword = _objs() - before
transform_group(sword, SWORD_M)

# ── lower the whole upper body into a bent-knee power stance ───────────
transform_group(_objs(), Matrix.Translation(V((0, 0, -DROP))))
bpy.context.view_layer.update()

# ── legs: thick muscular legs in baggy trousers, glossy leather boots ──
LEGS = {
    'l': (V((0.1, 0.0, 0.87)), V((0.2, -0.1, 0.48)), V((0.26, -0.01, 0.09)), V((0.3, -1, 0))),
    'r': (V((-0.1, 0.0, 0.87)), V((-0.2, -0.1, 0.48)), V((-0.26, -0.01, 0.09)), V((-0.3, -1, 0))),
}
mb = kit._meta('apants', resolution=0.0155)
E(mb, (0, 0.005, 0.9), (0.14, 0.1, 0.095))
mb2 = kit._meta('aboot', resolution=0.0135)
for side, (hp, kn, an, fd) in LEGS.items():
    fdn = fd.normalized()
    kit.blob_limb(mb, hp + V((0, 0, 0.02)), kn, 0.125 * W_, 0.098 * W_)
    E(mb, hp.lerp(kn, 0.42), (0.088, 0.092, 0.16), rot=along(hp, kn))                  # quads
    kit.blob_ball(mb, kn, 0.098 * W_)
    kit.blob_limb(mb, kn, kn.lerp(an, 0.62), 0.095 * W_, 0.082 * W_)
    E(mb, kn.lerp(an, 0.28) + V((0, 0.02, 0)), (0.064, 0.064, 0.11), rot=along(kn, an))  # calf
    top = kn.lerp(an, 0.45)
    kit.blob_limb(mb2, an + V((0, 0, -0.02)), top, 0.098 * W_, 0.104 * W_)
    fc = an + fdn * 0.06 + V((0, 0, -0.04))
    E(mb2, fc, (0.06, 0.13, 0.052), rot=V((0, 1, 0)).rotation_difference(fdn).to_euler())
kit.solidify_blobs({'apants': kit.mat(PANTS, 0.8), 'aboot': kit.mat(BOOTS, 0.3)})
BT = kit.mat(BOOTS, 0.3)
for side, (hp, kn, an, fd) in LEGS.items():
    fdn = fd.normalized()
    q = V((0, 1, 0)).rotation_difference(fdn)
    kit.torus(kn.lerp(an, 0.45), 0.08 * W_ * 0.84, 0.013, BT, rot=along(an, kn), major_segs=28, minor_segs=8)
    fc = an + fdn * 0.06 + V((0, 0, -0.04))
    kit.box(fc + V((0, 0, -0.045)) + fdn * 0.005, (0.11, 0.255, 0.018), kit.mat('#1a120c', 0.5), rot=q.to_euler(),
            bevel=0.006)

# belt
pants_o = bpy.data.objects['apants_mesh']
T_BODY = bvh(top_o, pants_o)
wrap_band(T_BODY, (0, 0, 0.94), (0, 0, 1), -0.022, 0.022, kit.mat('#4a2e1c', 0.45), off0=0.003, bulge=0.007,
          name='belt')
buckle = snap_dir(T_BODY, (0, 0, 0.94), (0, 1, 0), 0.01)
kit.box(buckle, (0.055, 0.012, 0.045), G_, bevel=0.004)
kit.box(buckle + V((0, -0.005, 0)), (0.032, 0.01, 0.024), kit.mat('#4a2e1c', 0.45))

# ── grimoire with the five-leaf clover, floating by his left hip ───────
before = _objs()
kit.box((0, 0, 0), (0.08, 0.026, 0.1), kit.mat('#16110f', 0.7), bevel=0.004)
kit.box((0.002, 0, 0), (0.074, 0.028, 0.092), kit.mat('#d9cfb2', 0.8))
for i in range(5):
    ang = math.radians(90 + i * 72)
    c = V((0.017 * math.cos(ang), -0.0145, 0.017 * math.sin(ang)))
    kit.sphere(c, (0.01, 0.003, 0.008), G_, rot=(0, -ang + math.pi / 2, 0), segs=10, rings=6)
kit.sphere((0, -0.015, 0), 0.005, G_, segs=8, rings=6)
kit.box((0, -0.0145, -0.03), (0.004, 0.002, 0.018), G_)
for zz in (0.04, -0.04):
    kit.box((-0.036, -0.0145, zz), (0.008, 0.003, 0.012), G_)
book = _objs() - before
transform_group(book, Matrix.Translation(V((0.42, -0.16, 0.9))) @ Euler((0.15, 0.3, 0.45)).to_matrix().to_4x4()
                @ Matrix.Scale(1.25, 4))

kit.finalize('asta')
