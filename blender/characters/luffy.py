"""Monkey D. Luffy (One Piece) — premium-statue take: low lunge into a stretched Gum-Gum Pistol, big coiled-straw
hat with red band, open red vest over a lean, scarred, muscled torso, blue rolled-cuff shorts, yellow sash, sandals."""
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


def lathe(profile, mats, n=96, checker=None):
    """Revolve [(r, z, slot), ...] around Z. Segment k (between points k and k+1) uses material slot
    profile[k][2]; slot 0/1 bands get a braided checker when `checker` = blocks around the circle."""
    bm = bmesh.new()
    rings = []
    for r_, z_, _ in profile:
        if r_ < 1e-6:
            rings.append([bm.verts.new((0, 0, z_))])
        else:
            rings.append([bm.verts.new((r_ * math.cos(2 * math.pi * i / n), r_ * math.sin(2 * math.pi * i / n), z_))
                          for i in range(n)])
    for k in range(len(profile) - 1):
        A, B = rings[k], rings[k + 1]
        slot = profile[k][2]
        for i in range(n):
            j = (i + 1) % n
            if len(A) == 1:
                f = bm.faces.new((A[0], B[i], B[j]))
            elif len(B) == 1:
                f = bm.faces.new((A[i], A[j], B[0]))
            else:
                f = bm.faces.new((A[i], A[j], B[j], B[i]))
            ms = slot
            if checker and slot in (0, 1) and ((i * checker // n) + k) % 2:
                ms = 1 - slot
            f.material_index = ms
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('lathe')
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new('lathe', me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
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


def decal(tree, outline, m, offset=0.0012, centre=None, rings=4, name='decal'):
    """Thin patch conforming to a surface seen from the front (-Y): mouths, markings. `outline` = [(x, z)]."""
    if centre is None:
        centre = (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
    cx, cz = centre
    bm = bmesh.new()
    vc = bm.verts.new(snap_dir(tree, (cx, 0, cz), (0, 1, 0), offset))
    grid = []
    for k in range(1, rings + 1):
        t = k / rings
        grid.append([bm.verts.new(snap_dir(tree, (cx + (x - cx) * t, 0, cz + (z - cz) * t), (0, 1, 0), offset))
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


# ── palette ─────────────────────────────────────────────────────────────
SKIN = '#e9b384'
VEST = '#d01f26'
SHORTS = '#2d5da8'
CUFF = '#e6edf6'
SASH = '#f2bd1d'
HAIR_C = '#121214'
STRAW = '#ecc55a'
STRAW2 = '#d9a83c'
BAND = '#c3141d'
SANDAL = '#b8893f'

kit.reset()
W_ = 1.15
K = 1.13                       # head scale
DROP = 0.17                    # lunge: upper body lowered by this much
a = kit.hero(skin=SKIN, top=SKIN, bottom=SHORTS, shoes=SKIN, sleeves='none', pants='short', mouth='line',
             right_arm='out', left_arm='hip', stance='wide', build=W_)
S = kit.mat(SKIN, 0.5)
strip_hero_legs()
bpy.data.objects.remove(bpy.data.objects['top_mesh'])
remove_arm(-1)
H = V((0, -0.01, 1.575 + 0.12 * K))
rebuild_head(H, k=K, name='lhead')

# ── lean, athletic torso (replaces hero torso): pecs, abs, lats ────────
w = W_
mb = kit._meta('ltorso', resolution=0.0095)
kit.blob_ellipsoid(mb, (0, 0.005, 1.08), (0.15 * w, 0.1 * w, 0.12))
kit.blob_ellipsoid(mb, (0, 0.0, 1.2), (0.165 * w, 0.11 * w, 0.14))
kit.blob_ellipsoid(mb, (0, 0, 1.33), (0.21 * w, 0.128 * w, 0.15))
kit.blob_ellipsoid(mb, (0, -0.03 * w, 1.37), (0.17 * w, 0.1 * w, 0.08))
for sx in (1, -1):
    E(mb, (0.066 * sx, -0.088, 1.37), (0.07, 0.03, 0.046), rot=(0, 0.25 * sx, 0))    # pecs
    E(mb, (0.115 * sx, 0.035, 1.3), (0.06, 0.05, 0.11))                              # lats
    E(mb, (0.105 * sx, -0.02, 1.13), (0.035, 0.05, 0.06))                            # obliques
    for j, z in enumerate((1.275, 1.215, 1.155)):
        E(mb, (0.024 * sx, -0.07 + j * 0.002, z), (0.021, 0.014, 0.024))             # abs
kit.solidify_blobs({'lhead': S, 'ltorso': S})
head_o, torso_o, skin_o = (bpy.data.objects[n] for n in ('lhead_mesh', 'ltorso_mesh', 'skin_mesh'))
T_TORSO = bvh(torso_o)

# ── Gum-Gum Pistol: stretched, muscular rubber arm + huge fist ─────────
mb = kit._meta('larm', resolution=0.0105)
Sh = a['shoulder_r']
El = Sh + V((-0.01, -0.24, -0.05))
Wr = Sh + V((-0.03, -0.7, 0.0))
adir = (Wr - El).normalized()
kit.blob_ball(mb, Sh, 0.095 * W_)                                    # deltoid
kit.blob_limb(mb, Sh, El, 0.085 * W_, 0.068 * W_)
E(mb, Sh.lerp(El, 0.5) + V((0, 0, 0.01)), (0.06, 0.06, 0.085), rot=along(Sh, El))   # bicep
kit.blob_limb(mb, El, Wr, 0.07 * W_, 0.05 * W_)
E(mb, El.lerp(Wr, 0.2), (0.055, 0.05, 0.1), rot=along(El, Wr))                     # forearm mass
F = Wr + adir * 0.065
E(mb, F, (0.072, 0.078, 0.066))                                      # fist
for i in range(4):
    kit.blob_ball(mb, F + adir * 0.05 + V((-0.034 + i * 0.023, 0, 0.014 - abs(i - 1.5) * 0.005)), 0.038)
E(mb, F + adir * 0.02 + V((0.045, 0, -0.03)), (0.022, 0.04, 0.02), rot=along(F, F + adir))   # thumb
# left arm (hand on hip): muscle masses over the hero arm
Sl, Ell, Hl = a['shoulder_l'], a['elbow_l'], a['hand_l']
kit.blob_ball(mb, Sl, 0.09 * W_)
E(mb, Sl.lerp(Ell, 0.48), (0.055, 0.055, 0.085), rot=along(Sl, Ell))
E(mb, Ell.lerp(Hl, 0.28), (0.046, 0.045, 0.08), rot=along(Ell, Hl))
kit.solidify_blobs({'larm': S})
# ── the X-scar across his chest ────────────────────────────────────────
SCAR = kit.mat('#b25a45', 0.6)
for p0, p1 in (((-0.065, 0, 1.43), (0.06, 0, 1.28)), ((0.065, 0, 1.43), (-0.06, 0, 1.28))):
    pts = [snap_dir(T_TORSO, V(p0).lerp(V(p1), t), (0, 1, 0), 0.002) for t in (0, 0.25, 0.5, 0.75, 1)]
    kit.tube(pts, 0.0065, SCAR, taper_to=0.5, resolution=4)

# ── open red vest (metaball cloth, cut open at the front, loose hem) + collar ──
mb = kit._meta('vest', resolution=0.0135)
kit.blob_ellipsoid(mb, (0, 0.008, 1.08), (0.17 * w + 0.03, 0.1 * w + 0.035, 0.1))
kit.blob_ellipsoid(mb, (0, 0.0, 1.2), (0.175 * w + 0.022, 0.115 * w + 0.03, 0.14))
kit.blob_ellipsoid(mb, (0, 0, 1.33), (0.21 * w + 0.022, 0.128 * w + 0.03, 0.15))
kit.blob_ellipsoid(mb, (0, -0.03 * w, 1.37), (0.17 * w + 0.022, 0.1 * w + 0.03, 0.08))
for sx in (1, -1):
    E(mb, (0.118 * sx, 0.045, 1.3), (0.075, 0.068, 0.125))
    E(mb, (0.11 * sx, -0.012, 1.13), (0.05, 0.065, 0.075))
    kit.blob_limb(mb, (0.05 * sx, 0.016, 1.5), (0.22 * w * sx, 0, 1.465), 0.086, 0.092, steps=4)
E(mb, (0, 0.075, 1.43), (0.13, 0.055, 0.08))
kit.solidify_blobs({'vest': kit.mat(VEST, 0.75)})
vest = bpy.data.objects['vest_mesh']
loops = garment(vest, z_hem=1.0, x_top=0.035, z_top=1.5, x_bot=0.135, neck_r=0.07, neck_z=1.45, neck_y=-0.012)
solidify(vest, 0.007)
RED = kit.mat(VEST, 0.75)
for lp in loops:
    kit.tube(smooth_pts(lp), 0.0065, RED, resolution=1, name='vtrim')
wrap_band(bvh(vest, skin_o, head_o), (0, 0.004, 1.49), (0, -0.3, 1), 0.0, 0.05, RED, off0=0.004, bulge=0.008,
          n=36, rows=4, name='collar', reach=0.2, arc=(-35, 215))

# ── face: big round eyes, huge grin, stitched scar under his left eye ──
T_FACE = bvh(head_o)
BRW = kit.mat('#101010', 0.5)
for sx in (1, -1):
    anime_eye(T_FACE, sx, 0.04 * K, H.z - 0.004 * K, 0.021 * K, 0.023 * K, '#111111', pupil=None, lash=0.0036)
    kit.tube([snap_dir(T_FACE, (x * sx * K, 0, H.z + (0.03 + dz) * K), (0, 1, 0), 0.0015)
              for x, dz in ((0.022, -0.002), (0.04, 0.004), (0.058, 0.0))], 0.003, BRW, taper_to=0.5, resolution=3)
MW, MT, MB = 0.042 * K, -0.066 * K, -0.1 * K
top_edge = [(x, H.z + MT + 0.009 * K * (x / MW) ** 2) for x in [MW * (i / 6 - 1) for i in range(13)]]
bottom = [(MW * math.cos(t), H.z + MT + 0.009 * K - (MT + 0.009 * K - MB) * math.sin(t) ** 0.8)
          for t in [math.pi * k / 12 for k in range(1, 12)]]
decal(T_FACE, top_edge + bottom, kit.mat('#5a0f12', 0.5), offset=0.0008, centre=(0, H.z - 0.08 * K), name='mouth')
teeth_low = [(x, z - 0.013 * K * (1 - (x / MW) ** 2) - 0.001) for x, z in reversed(top_edge[1:-1])]
decal(T_FACE, top_edge + teeth_low, kit.mat('#ffffff', 0.3), offset=0.0016, centre=(0, H.z + MT - 0.006 * K),
      name='teeth')
decal(T_FACE, [(0.02 * K * math.cos(t), H.z - 0.091 * K + 0.007 * K * math.sin(t)) for t in
               [2 * math.pi * k / 16 for k in range(16)]], kit.mat('#d8545e', 0.5), offset=0.0016, name='tongue')
LIP = kit.mat('#8a3a30', 0.5)
for sx in (1, -1):
    kit.tube([snap_dir(T_FACE, (0.041 * sx * K, 0, H.z - 0.058 * K), (0, 1, 0), 0.001),
              snap_dir(T_FACE, (0.048 * sx * K, 0, H.z - 0.05 * K), (0, 1, 0), 0.001)], 0.002, LIP, resolution=3)
SC = kit.mat('#7a2a20', 0.6)
sc_pts = [snap_dir(T_FACE, (x * K, 0, H.z + (-0.034 - 0.003 * math.sin((x - 0.03) / 0.026 * math.pi)) * K),
                   (0, 1, 0), 0.001) for x in (0.03, 0.039, 0.048, 0.056)]
kit.tube(sc_pts, 0.0018, SC, resolution=4)
for x in (0.037, 0.049):
    kit.tube([snap_dir(T_FACE, (x * K, 0, H.z - 0.027 * K), (0, 1, 0), 0.001),
              snap_dir(T_FACE, ((x + 0.0015) * K, 0, H.z - 0.043 * K), (0, 1, 0), 0.001)], 0.0015, SC, resolution=2)

# ── messy black hair, poking out under the brim all round ──────────────
HAIR = kit.mat(HAIR_C, 0.45)
cap = kit.sphere(H + V((0, 0.018, 0.03)) * 1.0 + V((0, 0, 0.03 * (K - 1))), (0.09 * K, 0.1 * K, 0.095 * K), HAIR,
                 segs=32, rings=16)
kit.subdivide(cap, 1)
T_HEAD = bvh(head_o, cap)
hc = H + V((0, 0.008, 0.02 * K))


def sph(az, el, rad=0.15 * K):
    az, el = math.radians(az), math.radians(el)
    return hc + V((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el))) * rad


def strand(az0, el0, az1, el1, flare=0.03, radius=0.018, n=4):
    pts = [snap(T_HEAD, sph(az0 + (az1 - az0) * i / (n - 1), el0 + (el1 - el0) * i / (n - 1)), hc,
                0.004 + flare * (i / (n - 1)) ** 1.6) for i in range(n)]
    kit.tube(pts, radius * K, HAIR, taper_to=0.08, resolution=4)


for az, el1, az1 in ((-46, 16, -56), (-33, 12, -38), (-20, 18, -24), (-7, 10, -8), (6, 16, 9), (19, 10, 24),
                     (32, 15, 38), (45, 12, 55)):
    strand(az, 60, az1, el1, flare=0.026)
for sx in (1, -1):
    for az, el1 in ((58, 2), (70, 8), (82, -2), (94, 10), (106, -4), (118, 4)):
        strand(az * sx, 50, (az + 10) * sx, el1, flare=0.055, radius=0.02)
for az in range(126, 240, 11):
    strand(az, 45, az + (6 if az % 2 else -6), -32 - (az % 3) * 6, flare=0.06, radius=0.021)

# ── THE straw hat: lathed coiled-straw profile, two-tone braid, red band, wide drooping brim ──
SW, SW2, RB = kit.mat(STRAW, 0.85), kit.mat(STRAW2, 0.85), kit.mat(BAND, 0.6)
R_OUT, RC, CH = 0.25, 0.098, 0.075        # brim radius, crown radius, crown wall height
prof = []
for i in range(8):                          # dome, centre outwards
    rr = (RC - 0.004) * i / 7
    prof.append((rr, CH + 0.03 * math.sqrt(max(0.0, 1 - (rr / RC) ** 2)), i % 2))
for i in range(1, 5):                       # crown wall
    t = i / 4
    prof.append((RC - 0.004 + 0.009 * t, CH - (CH - 0.036) * t, (i + 1) % 2))
prof[-1] = (prof[-1][0], prof[-1][1], 2)    # red band, slightly proud
prof.append((RC + 0.008, 0.036, 2))
prof.append((RC + 0.009, 0.006, 2))
prof.append((RC + 0.004, 0.003, 0))
nb = 11
for i in range(nb + 1):                     # brim top, drooping, coiled bands
    t = i / nb
    prof.append((RC + 0.004 + (R_OUT - RC - 0.004) * t, -0.042 * t ** 2, i % 2))
for k in range(1, 6):                       # rolled rim
    ang = math.pi * k / 5
    prof.append((R_OUT + 0.008 * math.sin(ang), -0.05 + 0.008 * math.cos(ang), 1))
for i in range(1, 6):                       # underside back in towards the crown
    rr = R_OUT - (R_OUT - RC + 0.01) * i / 5
    tt = max(0.0, (rr - RC) / (R_OUT - RC))
    prof.append((rr, -0.042 * tt ** 2 - 0.01, 1))
prof.append((0.0, -0.01, 1))
before = _objs()
lathe(prof, [SW, SW2, RB], n=96, checker=48)
hat = _objs() - before
HS = 1.27                       # hat scale: it's his silhouette
base = H.z + 0.062 * K
transform_group(hat, Matrix.Translation(V((0, 0.01, base))) @ Euler((-0.1, 0.14, 0.0)).to_matrix().to_4x4()
                @ Matrix.Scale(HS, 4))

# ── twist + lower the whole upper body into the lunge ──────────────────
pivot = V((0, 0, 1.0))
M_UP = (Matrix.Translation(V((0, 0, -DROP))) @ Matrix.Translation(pivot) @ Euler((0.12, 0, 0.18), 'ZYX')
        .to_matrix().to_4x4() @ Matrix.Translation(-pivot))
transform_group(_objs(), M_UP)
bpy.context.view_layer.update()

# ── lower body: deep lunge, left leg forward, right leg driving back ───
LEGS = {
    'l': (V((0.105, -0.01, 0.8)), V((0.2, -0.3, 0.5)), V((0.245, -0.33, 0.09)), V((0.25, -1, 0))),
    'r': (V((-0.105, 0.02, 0.8)), V((-0.22, 0.2, 0.44)), V((-0.3, 0.46, 0.12)), V((-0.1, -1, -0.5))),
}
mb = kit._meta('llegs', resolution=0.012)
for side, (hp, kn, an, fd) in LEGS.items():
    leg(mb, hp, kn, an, fd, W_)
    fdn = fd.normalized()
    fc = an + fdn * 0.06 + V((0, 0, -0.045))
    sx = 1 if side == 'l' else -1
    side_v = fdn.cross(V((0, 0, 1))).normalized()
    for i in range(5):
        kit.blob_ball(mb, fc + fdn * (0.105 - abs(i - 1.2) * 0.008) + side_v * (-0.03 + i * 0.015) * sx
                      + V((0, 0, -0.008)), 0.016 if i else 0.02)
mb2 = kit._meta('lshorts', resolution=0.0125)
E(mb2, (0, 0.005, 0.84), (0.155, 0.11, 0.095))
for side, (hp, kn, an, fd) in LEGS.items():
    kit.blob_limb(mb2, hp + V((0, 0, 0.02)), hp.lerp(kn, 0.84), 0.15 * W_, 0.125 * W_)
kit.solidify_blobs({'llegs': S, 'lshorts': kit.mat(SHORTS, 0.8)})
shorts_o = bpy.data.objects['lshorts_mesh']

# rolled light cuffs
C = kit.mat(CUFF, 0.85)
T_SH = bvh(shorts_o)
for side, (hp, kn, an, fd) in LEGS.items():
    wrap_band(T_SH, hp.lerp(kn, 0.8), (kn - hp).normalized(), -0.024, 0.026, C, off0=0.002, bulge=0.016, n=40,
              rows=4, name='cuff', reach=0.16)

# straw sandals
SD = kit.mat(SANDAL, 0.8)
for side, (hp, kn, an, fd) in LEGS.items():
    fdn = fd.normalized()
    q = V((0, 1, 0)).rotation_difference(fdn)
    up = q @ V((0, 0, 1))
    fc = an + fdn * 0.06 + V((0, 0, -0.045))
    kit.box(fc - up * 0.04 + fdn * 0.01, (0.115, 0.27, 0.016), SD, rot=q.to_euler(), bevel=0.005)
    kit.torus(fc + fdn * 0.02 + up * 0.0, 0.052, 0.007, SD, rot=(q @ Euler((math.pi / 2, 0, 0)).to_quaternion())
              .to_euler(), major_segs=20, minor_segs=6)

# yellow sash with a knot and hanging tails at his left hip
Y = kit.mat(SASH, 0.7)
T_BODY = bvh(torso_o, shorts_o)
wrap_band(T_BODY, (0, 0, 0.855), (0, 0, 1), -0.03, 0.035, Y, off0=0.004, bulge=0.015, name='sash')
knot = snap_dir(T_BODY, (0.11, 0, 0.86), (0.35, 1, 0), -0.014)
kit.sphere(knot, (0.03, 0.024, 0.028), Y, segs=16, rings=10)
kit.tube([knot + V((0.0, -0.005, -0.01)), knot + V((0.03, -0.01, -0.07)), knot + V((0.05, 0.0, -0.15)),
          knot + V((0.075, 0.02, -0.21))], 0.016, Y, taper_to=0.55, resolution=6)
kit.tube([knot + V((-0.01, -0.008, -0.01)), knot + V((0.0, -0.02, -0.06)), knot + V((0.02, -0.01, -0.13))],
         0.014, Y, taper_to=0.55, resolution=6)

kit.finalize('luffy')
