"""The Destined One (Black Myth: Wukong) — heroic-proportion fan-art statue built from kit primitives."""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Matrix, Quaternion
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import Vector as V  # noqa: E402

random.seed(7)


# ── local helpers ────────────────────────────────────────────────────────
def boolean(target, cutter, op='DIFFERENCE'):
    mod = target.modifiers.new('bool', 'BOOLEAN')
    mod.operation = op
    mod.object = cutter
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def bvh(obj):
    return BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())


def catmull(pts, n=8):
    """Smooth path through guide points (Catmull-Rom), n samples per segment."""
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


def mesh_obj(name, verts, faces, m, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return kit._finish(obj, m, smooth)


def ribbon(tree, guide, width, m, lift=0.003, thick=0.004, n=8, name='ribbon'):
    """Flat strip hugging a surface (straps, trims, tattoos)."""
    path = catmull(guide, n)
    verts, faces = [], []
    for i, p in enumerate(path):
        loc, nrm, _, _ = tree.find_nearest(p)
        tan = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        side = nrm.cross(tan).normalized() * (width / 2)
        base = loc + nrm * (lift + thick / 2)
        verts += [base + side, base - side]
        if i:
            j = 2 * i
            faces.append((j - 2, j - 1, j + 1, j))
    obj = mesh_obj(name, verts, faces, m)
    mod = obj.modifiers.new('solid', 'SOLIDIFY')
    mod.thickness = thick
    mod.offset = 0
    return obj


def banded_tube(guide, r0, r1, mats, bands=12, n=6):
    """Tapered tube split into alternating colour bands (barred feathers)."""
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


def lock(points, r, m, ref, sides=5, flat=0.5, n=3):
    """Cheap tapered fur lock: flattened cross-section lying against `ref` (surface normal)."""
    path = catmull(points, n)
    ref = V(ref).normalized()
    verts, faces, L = [], [], len(path)
    for i, p in enumerate(path[:-1]):
        tan = (path[i + 1] - path[max(i - 1, 0)]).normalized()
        sd = tan.cross(ref)
        if sd.length < 1e-5:
            sd = tan.cross(V((1, 0, 0)))
        sd.normalize()
        up = sd.cross(tan)
        rad = r * (1 - i / (L - 1)) ** 0.6
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            verts.append(p + sd * math.cos(ang) * rad + up * math.sin(ang) * rad * flat)
    verts.append(path[-1])
    rings = L - 1
    for i in range(rings - 1):
        for k in range(sides):
            a0, a1 = i * sides + k, i * sides + (k + 1) % sides
            faces.append((a0, a1, a1 + sides, a0 + sides))
    tip = len(verts) - 1
    for k in range(sides):
        faces.append(((rings - 1) * sides + k, (rings - 1) * sides + (k + 1) % sides, tip))
    faces.append(tuple(reversed(range(sides))))
    return mesh_obj('lock', verts, faces, m)


def panel(top, width, length, outward, flare, m, hem=None, thick=0.012):
    """Hanging cloth/armour panel: hangs from `top`, its bottom flaring towards `outward`."""
    from mathutils import Matrix
    out = V(outward).normalized()
    yaw = math.atan2(out.x, -out.y)
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-flare, 3, 'X')
    rot = R.to_euler()
    if length:
        kit.box(V(top) + R @ V((0, 0, -length / 2)), (width, thick, length), m, rot=rot, bevel=0.004)
    if hem:
        kit.box(V(top) + R @ V((0, 0, -length)), (width + 0.006, thick + 0.008, 0.02), hem, rot=rot, bevel=0.004)


def dome(center, normal, size, m, rim=None):
    """Armour plate: flattened ellipsoid whose thin axis points along `normal`, optional gold rim."""
    rot = kit.rot_between((0, 0, 0), normal)
    kit.sphere(center, size, m, rot=rot, segs=28, rings=14)
    if rim:
        kit.torus(V(center) - V(normal).normalized() * size[2] * 0.15, 1.0, 0.07, rim, rot=rot,
                  major_segs=32, minor_segs=6, scale=(size[0], size[1], size[0]))


# ── palette ──────────────────────────────────────────────────────────────
kit.reset()
FUR_HEX, FACE_HEX = '#6e4426', '#d9ad7c'
FUR = kit.mat(FUR_HEX, 0.85)
FUR_DK = kit.mat('#4a2c17', 0.9)
FUR_LT = kit.mat('#8c5a32', 0.85)
FACE = kit.mat(FACE_HEX, 0.6)
IRON = kit.mat('#454a52', 0.32, metal=0.85)
IRON_DK = kit.mat('#2e3238', 0.38, metal=0.8)
GOLD = kit.mat('#e3a92b', 0.22, metal=1.0)
RED = kit.mat('#b8231a', 0.75)
ORANGE = kit.mat('#d9581c', 0.75)
WRAP = kit.mat('#cdbf9f', 0.85)
STAFF = kit.mat('#1f1c1b', 0.3, metal=0.7)
PLUME_A = kit.mat('#a8341c', 0.55)
PLUME_B = kit.mat('#3b1d12', 0.6)
PLUME_C = kit.mat('#d9a35a', 0.55)
INK = kit.mat('#1e120a', 0.5)

W = 1.1
a = kit.hero(skin=FACE_HEX, top=FUR_HEX, bottom='#3a312a', shoes='#262220', hands='#9b7552',
             iris='#e8a817', eyes='#120a05', brows=None, sleeves='long', mouth='line',
             right_arm='guard', left_arm='hip', stance='wide', build=W)
H, r = a['head'], a['head_r']

# drop the kit's generic eyes/mouth: the Destined One gets golden monkey eyes drawn below
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.endswith('_mesh')]:
    c = sum((o.matrix_world @ V(cc) for cc in o.bound_box), V()) / 8
    if abs(c.x) < 0.07 and 1.58 < c.z < 1.73 and c.y < -0.06:
        bpy.data.objects.remove(o, do_unlink=True)

# ── monkey head: fur shell with a heart-shaped face opening ──────────────
FM = kit._meta('wk_fur', resolution=0.009)
kit.blob_ellipsoid(FM, H + V((0, 0.014, 0.014)), (0.118, 0.126, 0.13))
kit.blob_ellipsoid(FM, H + V((0, 0.06, -0.07)), (0.085, 0.07, 0.08))               # nape
kit.blob_ellipsoid(FM, H + V((0, -0.07, 0.068)), (0.095, 0.06, 0.05))               # brow / forehead fur
kit.blob_limb(FM, (0, 0.0, 1.45), (0, -0.008, 1.6), 0.086, 0.08)                       # furry neck
for sx in (1, -1):
    kit.blob_ellipsoid(FM, H + V((0.082 * sx, -0.025, -0.055)), (0.05, 0.06, 0.06))  # cheek fluff
kit.solidify_blobs({'wk_fur': FUR})
fur = bpy.data.objects['wk_fur_mesh']
for loc, sc in (((0.041, -0.15, 1.71), (0.05, 0.06, 0.04)),
                ((-0.041, -0.15, 1.71), (0.05, 0.06, 0.04)),
                ((0, -0.145, 1.63), (0.062, 0.07, 0.066))):
    boolean(fur, kit.sphere(loc, sc, None, segs=32, rings=16))
FT = bvh(fur)
FURS = (FUR, FUR, FUR_DK, FUR_LT)

# fur locks over the whole shell, swept back over the scalp and down the nape
golden = math.pi * (3 - math.sqrt(5))
N = 340
for i in range(N):
    zc = 1 - 2 * (i + 0.5) / N
    rr = math.sqrt(1 - zc * zc)
    d = V((math.cos(golden * i) * rr, math.sin(golden * i) * rr, zc))
    if d.y < -0.3 and -0.75 < d.z < 0.5 and abs(d.x) < 0.72:
        continue  # keep the face clear
    if d.z < -0.7:
        continue
    loc, nrm, _, _ = FT.find_nearest(H + d * 0.25)
    if d.z > 0.35:
        sweep = V((d.x * 0.4, 0.8, 0.3 if d.y < 0 else -0.1))
    elif abs(d.x) > 0.55 and d.y < 0.25:
        sweep = V((d.x * 0.6, 0.7, -0.45))          # cheek / sideburn fur sweeps back
    else:
        sweep = V((d.x * 0.3, 0.45, -0.85))
    g = (nrm * 0.35 + sweep.normalized()).normalized()
    ln = random.uniform(0.055, 0.09) * (1.25 if abs(d.x) > 0.55 and d.z < 0.2 else 1)
    lock([loc - nrm * 0.006, loc + nrm * 0.008 + g * ln * 0.45, loc + nrm * 0.004 + g * ln],
         random.uniform(0.011, 0.016), random.choice(FURS), nrm)

# ears, muzzle, nose, mouth, fierce fur brows
for sx in (1, -1):
    kit.sphere(H + V((0.122 * sx, 0.015, -0.005)), (0.016, 0.03, 0.036), FUR, segs=16, rings=8)
    kit.sphere(H + V((0.13 * sx, 0.006, -0.005)), (0.01, 0.021, 0.026), FACE, segs=16, rings=8)
# remove the human nose so a flat monkey muzzle can replace it
skin = bpy.data.objects['skin_mesh']
bm = bmesh.new()
bm.from_mesh(skin.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.127 and 1.638 < v.co.z < 1.71 and abs(v.co.x) < 0.024],
                 context='VERTS')
bm.to_mesh(skin.data)
bm.free()
kit.subdivide(kit.sphere((0, -0.106, 1.628), (0.042, 0.034, 0.05), FACE, segs=20, rings=10), 1)
for sx in (1, -1):
    kit.sphere((0.009 * sx, -0.136, 1.652), (0.006, 0.004, 0.004), INK, segs=8, rings=4)
kit.tube([(-0.028, -0.125, 1.597), (0, -0.137, 1.602), (0.028, -0.125, 1.597)], 0.0028, INK, name='mouth')
ST = bvh(skin)


def face(x, z, lift=0.0):
    loc, nrm, _, _ = ST.ray_cast(V((x, -1.0, z)), V((0, 1, 0)))
    if loc is None:
        loc, nrm, _, _ = ST.find_nearest(V((x, H.y - 0.13, z)))
    return loc + nrm * lift, nrm


def decal(x, z, scale, m, lift=0.0, roll=0.0, segs=16, rings=8):
    p, n = face(x, z, lift)
    rot = (V((0, -1, 0)).rotation_difference(n).to_matrix() @ Matrix.Rotation(roll, 3, 'Y')).to_euler()
    return kit.sphere(p, scale, m, rot=rot, segs=segs, rings=rings)


GOLD_EYE = kit.mat('#f2b51c', 0.2, emit=0.6)
for sx in (1, -1):
    ex, ez = 0.041 * sx, 1.7
    decal(ex, ez, (0.019, 0.007, 0.0115), INK, lift=-0.001, roll=-0.15 * sx)                      # dark almond
    decal(ex - 0.001 * sx, ez - 0.001, (0.0135, 0.006, 0.0098), GOLD_EYE, lift=0.0015, roll=-0.15 * sx)
    decal(ex - 0.001 * sx, ez - 0.001, (0.0045, 0.005, 0.0068), INK, lift=0.0035, segs=10, rings=5)  # slit pupil
    decal(ex - 0.006 * sx, ez + 0.003, (0.0022, 0.002, 0.0022), kit.mat('#ffffff', 0.1), lift=0.005, segs=8, rings=4)
    kit.tube([tuple(face(ex + dx * sx, ez + dz, 0.0035)[0]) for dx, dz in
              ((-0.022, -0.002), (-0.006, 0.008), (0.012, 0.0105), (0.022, 0.007))],
             0.0022, INK, resolution=6, name='lid')                                                 # scowling lid line
    # fierce dark brow: thick stroke over the brow ridge (inner end low) + tufts flicking up-out
    kit.tube([tuple(face(x * sx, z, 0.004)[0]) for x, z in ((0.012, 1.713), (0.036, 1.724), (0.064, 1.73), (0.075, 1.727))],
             0.0075, FUR_DK, resolution=6, taper_to=0.5, name='brow')
    for k in range(4):
        x = (0.018 + k * 0.014) * sx
        base, n = face(x, 1.718 + k * 0.004, 0.007)
        lock([base, base + V((0.01 * sx, -0.004, 0.008)), base + V((0.022 * sx, 0.0, 0.016 + k * 0.003))],
             0.007, FUR_DK, n)

# ── golden fillet + pheasant plumes ──────────────────────────────────────
band_c = H + V((0, 0.012, 0.062))
kit.torus(band_c, 0.121, 0.007, GOLD, rot=(-0.18, 0, 0), scale=(1, 1.07, 1), major_segs=48, minor_segs=8)
kit.torus(band_c + V((0, 0, -0.012)), 0.122, 0.004, GOLD, rot=(-0.18, 0, 0), scale=(1, 1.07, 1),
          major_segs=48, minor_segs=6)
crest = H + V((0, -0.128, 0.05))
kit.sphere(crest, (0.022, 0.008, 0.026), GOLD, segs=20, rings=10)
kit.sphere(crest + V((0, -0.007, 0)), (0.009, 0.004, 0.011), RED, segs=12, rings=6)
for sx in (1, -1):
    sock = H + V((0.04 * sx, -0.115, 0.07))
    kit.rod(sock + V((0, 0, -0.012)), sock + V((0.004 * sx, -0.004, 0.035)), 0.009, GOLD, verts=12)
    guide = [sock, sock + V((0.012 * sx, -0.012, 0.12)), sock + V((0.05 * sx, 0.02, 0.27)),
             sock + V((0.13 * sx, 0.11, 0.37)), sock + V((0.25 * sx, 0.22, 0.41)),
             sock + V((0.37 * sx, 0.32, 0.37)), sock + V((0.46 * sx, 0.39, 0.28))]
    banded_tube(guide, 0.011, 0.003, (PLUME_A, PLUME_B, PLUME_A, PLUME_C), bands=18)

# ── body armour ──────────────────────────────────────────────────────────
AM = kit._meta('wk_armor', resolution=0.012)
kit.blob_ellipsoid(AM, (0, 0, 1.335), (0.245 * W, 0.15 * W, 0.155))
kit.blob_ellipsoid(AM, (0, -0.04, 1.37), (0.19 * W, 0.11 * W, 0.08))
kit.blob_ellipsoid(AM, (0, 0, 1.21), (0.2 * W, 0.135 * W, 0.12))
kit.blob_ellipsoid(AM, (0, 0.005, 1.1), (0.17 * W, 0.118 * W, 0.08))
kit.blob_ellipsoid(AM, (0, -0.06, 1.39), (0.2 * W, 0.1, 0.07))                     # broad chest plate
kit.solidify_blobs({'wk_armor': IRON})
AT = bvh(bpy.data.objects['wk_armor_mesh'])
# gold trims: neckline, chest ridge, lower edge, chest medallion
ribbon(AT, [(-0.13, -0.08, 1.5), (-0.07, -0.13, 1.46), (0, -0.15, 1.44), (0.07, -0.13, 1.46), (0.13, -0.08, 1.5)],
       0.018, GOLD, thick=0.006)
ribbon(AT, [(0.13, 0.08, 1.5), (0, 0.12, 1.48), (-0.13, 0.08, 1.5)], 0.018, GOLD, thick=0.006)
ribbon(AT, [(0, -0.2, 1.43), (0, -0.2, 1.33), (0, -0.2, 1.08)], 0.012, GOLD, thick=0.005)
for z, wd in ((1.29, 0.014), (1.2, 0.012), (1.12, 0.012)):
    ring = [(math.cos(t) * 0.3, math.sin(t) * 0.2, z) for t in [k * math.pi / 10 for k in range(21)]]
    ribbon(AT, ring, wd, GOLD, thick=0.005)
kit.sphere(a['chest'] + V((0, -0.06, 0.02)), (0.03, 0.01, 0.03), GOLD, segs=20, rings=10)
kit.sphere(a['chest'] + V((0, -0.068, 0.02)), (0.014, 0.006, 0.014), RED, segs=12, rings=6)

# layered pauldrons following each upper arm
for side in ('l', 'r'):
    sh, el = a[f'shoulder_{side}'], a[f'elbow_{side}']
    sx = 1 if side == 'l' else -1
    arm = (el - sh).normalized()
    up = (V((0.55 * sx, 0, 1)) - arm * V((0.55 * sx, 0, 1)).dot(arm)).normalized()
    for k, s in enumerate((1.0, 0.85, 0.72)):
        c = sh + arm * (0.02 + k * 0.055) + up * (0.055 - k * 0.012)
        dome(c, up, (0.1 * s, 0.1 * s, 0.045 * s), IRON if k != 1 else IRON_DK, rim=GOLD)
    # gold-trimmed bracers on forearms
    wr = a[f'hand_{side}']
    fore = (wr - el)
    kit.rod(el + fore * 0.3, el + fore * 0.78, 0.05, IRON_DK, verts=20)
    for t in (0.3, 0.78):
        kit.torus(el + fore * t, 0.051, 0.006, GOLD, rot=kit.rot_between((0, 0, 0), fore), major_segs=24,
                  minor_segs=6)

# ── waist: red sash, gold buckle, cloth + armoured tassets ───────────────
kit.torus((0, 0, 1.05), 1.0, 0.032, RED, scale=(0.185, 0.135, 1.0), major_segs=40, minor_segs=10)
kit.torus((0, 0, 1.0), 1.0, 0.01, GOLD, scale=(0.19, 0.14, 1.0), major_segs=40, minor_segs=6)
kit.sphere((0, -0.165, 1.04), (0.035, 0.012, 0.03), GOLD, segs=20, rings=10)
kit.tube([(0.07, -0.15, 1.03), (0.09, -0.17, 0.92), (0.08, -0.16, 0.8)], 0.014, RED, taper_to=0.6, resolution=6)
kit.tube([(0.1, -0.13, 1.03), (0.125, -0.15, 0.95), (0.13, -0.15, 0.86)], 0.012, RED, taper_to=0.6, resolution=6)
panel((0, -0.16, 1.02), 0.15, 0.48, (0, -1, 0), 0.12, RED, hem=GOLD)
panel((0, -0.172, 0.86), 0.1, 0.0, (0, -1, 0), 0.12, RED, hem=GOLD)          # embroidered band
panel((0, 0.15, 1.02), 0.22, 0.52, (0, 1, 0), 0.14, RED, hem=GOLD)
for sx in (1, -1):
    for dy, mm in ((-0.06, IRON), (0.06, IRON_DK)):
        panel((0.2 * sx, dy, 1.0), 0.14, 0.3, (sx, 0, 0), 0.38, mm, hem=GOLD)
    panel((0.115 * sx, -0.135, 1.0), 0.085, 0.36, (0.55 * sx, -0.85, 0), 0.2, ORANGE)

# baggy trousers bound with leg wraps
PM = kit._meta('wk_pants', resolution=0.016)
for side in ('l', 'r'):
    hip, knee = a[f'hip_{side}'], a[f'knee_{side}']
    ank = V((knee.x * 1.06, 0.01, 0.1))
    kit.blob_limb(PM, hip + V((0, 0, -0.06)), knee, 0.12 * W, 0.085 * W)
    kit.blob_limb(PM, knee, knee.lerp(ank, 0.38), 0.085 * W, 0.08 * W)
    dome(knee + V((0, -0.075, 0.01)), (0, -1, 0.15), (0.05, 0.06, 0.025), IRON, rim=GOLD)
    kit.rod(ank + V((0, 0.005, 0.03)), ank.lerp(knee, 0.62) + V((0, 0.01, 0)), 0.05, WRAP, verts=20,
            r2=0.066)
    for k in range(5):
        p = ank.lerp(knee, 0.1 + k * 0.11)
        kit.torus(p + V((0, 0.006, 0)), 0.05 + k * 0.0035, 0.0045, kit.mat('#5a4630', 0.8),
                  rot=(0.3 * (-1) ** k, 0, 0), major_segs=24, minor_segs=5)
    kit.torus(ank.lerp(knee, 0.62), 0.07, 0.007, GOLD, major_segs=24, minor_segs=6)
kit.solidify_blobs({'wk_pants': kit.mat('#3a312a', 0.85)})

# ── tail ─────────────────────────────────────────────────────────────────
tail = [(0, 0.1, 0.96), (0.02, 0.24, 0.86), (0.12, 0.36, 0.72), (0.3, 0.42, 0.7), (0.44, 0.38, 0.85),
        (0.48, 0.32, 1.06), (0.42, 0.3, 1.18)]
kit.tube(tail, 0.024, FUR, taper_to=0.55, resolution=10, name='tail')
for k in range(7):
    tip = V(tail[-1])
    d = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.2, 1))).normalized()
    kit.spike(tip - d * 0.01, tip + d * 0.05, 0.012, FUR_DK, verts=8)

# soft fur collar ruff, covered in lying locks
CM = kit._meta('wk_collar', resolution=0.012)
for k in range(14):
    t = k / 14 * 2 * math.pi
    kit.blob_ellipsoid(CM, (math.sin(t) * 0.12, -math.cos(t) * 0.1, 1.48), (0.06, 0.06, 0.04))
kit.solidify_blobs({'wk_collar': FUR})
CT = bvh(bpy.data.objects['wk_collar_mesh'])
for k in range(90):
    t = random.uniform(0, 2 * math.pi)
    out = V((math.sin(t), -math.cos(t) * 0.85, 0))
    loc, nrm, _, _ = CT.find_nearest(V((0, 0, 1.5)) + out * 0.2 + V((0, 0, random.uniform(0.0, 0.06))))
    g = (out + V((0, 0, -0.35)) + nrm * 0.3).normalized()
    ln = random.uniform(0.045, 0.075)
    lock([loc - nrm * 0.005, loc + nrm * 0.008 + g * ln * 0.45, loc + nrm * 0.004 + g * ln],
         random.uniform(0.012, 0.017), random.choice(FURS), nrm)

# fur along the arms (lying flat, pointing towards the wrist)
TT = bvh(bpy.data.objects['top_mesh'])
for side in ('l', 'r'):
    sh, el, wr = a[f'shoulder_{side}'], a[f'elbow_{side}'], a[f'hand_{side}']
    for seg_a, seg_b, ts in ((sh, el, (0.45, 0.6, 0.75, 0.9)), (el, wr, (0.05, 0.2))):
        ax = (seg_b - seg_a).normalized()
        perp = ax.cross(V((0, 0, 1)) if abs(ax.z) < 0.9 else V((1, 0, 0))).normalized()
        for t in ts:
            for k in range(9):
                ang = 2 * math.pi * (k + 0.5 * (t * 10 % 2)) / 9
                dirn = perp.copy()
                dirn.rotate(Quaternion(ax, ang))
                loc, nrm, _, _ = TT.find_nearest(seg_a.lerp(seg_b, t) + dirn * 0.1)
                g = (ax + nrm * 0.25).normalized()
                lock([loc - nrm * 0.004, loc + g * 0.025 + nrm * 0.006, loc + g * 0.055 + nrm * 0.004],
                     0.014, random.choice(FURS), nrm)

# ── Jingu Bang: planted, the Destined One leaning on it ──────────────────
palm = a['hand_r']
bottom = V((palm.x + 0.03, palm.y - 0.02, 0.0))
d = (palm - bottom).normalized()
top = palm + d * 0.62
kit.rod(bottom, top, 0.017, STAFF, verts=16)
for end, s in ((bottom, 1), (top, -1)):
    kit.rod(end, end + d * 0.13 * s, 0.021, GOLD, verts=20)
    for k in (0.145, 0.165, 0.185):
        kit.torus(end + d * k * s, 0.02, 0.0045, GOLD, rot=kit.rot_between((0, 0, 0), d), major_segs=20,
                  minor_segs=6)
kit.torus(palm + d * 0.005, 0.024, 0.015, kit.mat('#9b7552', 0.55), rot=kit.rot_between((0, 0, 0), d),
          major_segs=20, minor_segs=8)   # curled fingers

kit.finalize('wukong', thumb_angle=float(os.environ.get('WK_ANGLE', -28)))


def closeup(path, target, dist=1.4, angle=-28, lens=85):
    """Debug render of a detail (only when WK_CLOSEUP is set; writes outside public/)."""
    scene = bpy.context.scene
    cam = bpy.data.objects.new('closecam', bpy.data.cameras.new('closecam'))
    cam.data.lens = lens
    t = math.radians(angle)
    cam.location = V(target) + V((-math.sin(t) * dist, -math.cos(t) * dist, 0.05))
    cam.rotation_euler = (V(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 800
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


if os.environ.get('WK_CLOSEUP'):
    out = os.environ['WK_CLOSEUP']
    closeup(out + '_face.png', (0, 0, float(os.environ.get('WK_Z', '1.55'))), dist=float(os.environ.get('WK_D', '1.2')),
            angle=float(os.environ.get('WK_A', '-28')))
