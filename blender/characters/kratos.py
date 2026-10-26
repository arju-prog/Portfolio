"""Kratos (God of War, Norse era) — heroic-proportion fan-art statue built from kit primitives."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import Vector as V  # noqa: E402

random.seed(11)


# ── local helpers ────────────────────────────────────────────────────────
def bvh(obj):
    return BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())


def nearest(trees, p):
    best = None
    for t in trees:
        hit = t.find_nearest(p)
        if hit[0] is not None and (best is None or hit[3] < best[3]):
            best = hit
    return best


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


def mesh_obj(name, verts, faces, m, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return kit._finish(obj, m, smooth)


def ribbon(trees, guide, width, m, lift=0.002, thick=0.003, n=8, name='ribbon'):
    """Flat strip hugging the body (tattoo, straps)."""
    path = catmull(guide, n)
    hits = [nearest(trees, p) for p in path]
    locs, nrms = [h[0] for h in hits], [h[1] for h in hits]
    for _ in range(3):  # relax away surface facets
        locs = [locs[0]] + [(locs[i - 1] + locs[i] * 2 + locs[i + 1]) / 4 for i in range(1, len(locs) - 1)] + [locs[-1]]
        nrms = [nrms[0]] + [(nrms[i - 1] + nrms[i] * 2 + nrms[i + 1]).normalized() for i in range(1, len(nrms) - 1)] + [nrms[-1]]
    verts, faces = [], []
    for i, p in enumerate(path):
        loc, nrm = locs[i], nrms[i]
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
    return path


def lock(points, r, m, ref, sides=5, flat=0.5, n=3):
    """Tapered hair/beard lock with a flattened cross-section."""
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


def extrude(profile, origin, U, D, thick, m, smooth=False):
    """Extrude a 2D outline (u, v) lying in the plane spanned by U, D; thickness along U x D."""
    U, D = V(U).normalized(), V(D).normalized()
    N = U.cross(D).normalized()
    o = V(origin)
    n = len(profile)
    verts = [o + U * u + D * v + N * thick / 2 for u, v in profile] + \
            [o + U * u + D * v - N * thick / 2 for u, v in profile]
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    faces += [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    obj = mesh_obj('plate', verts, faces, m, smooth)
    obj.modifiers.new('tri', 'TRIANGULATE')
    return obj


def panel(top, width, length, outward, flare, m, hem=None, thick=0.012):
    """Hanging leather/cloth panel from `top`, its bottom flaring towards `outward`."""
    out = V(outward).normalized()
    yaw = math.atan2(out.x, -out.y)
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-flare, 3, 'X')
    rot = R.to_euler()
    kit.box(V(top) + R @ V((0, 0, -length / 2)), (width, thick, length), m, rot=rot, bevel=0.004)
    if hem:
        kit.box(V(top) + R @ V((0, 0, -length)), (width + 0.006, thick + 0.006, 0.016), hem, rot=rot, bevel=0.003)
    return R


def dome(center, normal, size, m, rim=None, segs=28):
    rot = kit.rot_between((0, 0, 0), normal)
    kit.sphere(center, size, m, rot=rot, segs=segs, rings=segs // 2)
    if rim:
        kit.torus(V(center) - V(normal).normalized() * size[2] * 0.15, 1.0, 0.07, rim, rot=rot,
                  major_segs=32, minor_segs=6, scale=(size[0], size[1], size[0]))


# ── palette ──────────────────────────────────────────────────────────────
kit.reset()
SKIN_HEX = '#8f8b84'
SKIN = kit.mat(SKIN_HEX, 0.6)
TATTOO = kit.mat('#a3191a', 0.75)
BEARD = kit.mat('#3a2a1e', 0.85)
BEARD_DK = kit.mat('#261a12', 0.9)
BEARD_LT = kit.mat('#4d3826', 0.85)
LEATHER = kit.mat('#5b3b24', 0.7)
LEATHER_DK = kit.mat('#34231a', 0.75)
STEEL = kit.mat('#9aa2aa', 0.28, metal=0.95)
BRONZE = kit.mat('#9a7140', 0.32, metal=0.9)
CLOTH = kit.mat('#6e1f17', 0.8)
AXE_STEEL = kit.mat('#62798a', 0.32, metal=0.85)
FROST = kit.mat('#8fe3ff', 0.2, emit=3.0)
RUNE = kit.mat('#5fd2ff', 0.3, emit=2.5)
WOOD = kit.mat('#6b4528', 0.6)

W = 1.25
a = kit.hero(skin=SKIN_HEX, top=SKIN_HEX, bottom='#3a2e25', shoes='#2a2019', iris='#b07d2a', eyes='#140c06',
             brows='#2a1d14', sleeves='none', mouth='line', right_arm='guard', left_arm='relaxed',
             stance='wide', build=W)
H, r = a['head'], a['head_r']
skin_obj, top_obj = bpy.data.objects['skin_mesh'], bpy.data.objects['top_mesh']


def _centre(o):
    cs = [o.matrix_world @ V(c) for c in o.bound_box]
    return sum(cs, V()) / 8


# drop the kit's generic face parts; Kratos gets his own sculpted head below
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.endswith('_mesh')]:
    c = _centre(o)
    if abs(c.x) < 0.11 and 1.55 < c.z < 1.8 and c.y < -0.04:
        bpy.data.objects.remove(o, do_unlink=True)
bm = bmesh.new()
bm.from_mesh(skin_obj.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 1.59 and abs(v.co.x) < 0.15 and -0.18 < v.co.y < 0.15],
                 context='VERTS')
bm.to_mesh(skin_obj.data)
bm.free()

# ── heroic upper body: one metaball family (torso + arms + muscles) enclosing the base body ──
MM = kit._meta('kr_body', resolution=0.009)
w = W
kit.blob_ellipsoid(MM, (0, 0.005, 1.08), (0.155 * w, 0.104 * w, 0.125))                 # waist
kit.blob_ellipsoid(MM, (0, 0, 1.2), (0.17 * w, 0.114 * w, 0.145))                      # abdomen
kit.blob_ellipsoid(MM, (0, 0, 1.33), (0.215 * w, 0.132 * w, 0.155))                    # ribcage
kit.blob_ellipsoid(MM, (0, 0.0, 1.0), (0.165 * w, 0.112 * w, 0.06))                     # hips under belt
kit.blob_limb(MM, (0, 0.01, 1.44), (0, 0.0, 1.6), 0.056 * w, 0.05 * w, steps=4)       # neck
for sx in (1, -1):
    kit.blob_limb(MM, (0.05 * sx, 0.015, 1.5), (0.21 * w * sx, 0, 1.46), 0.06 * w, 0.064 * w, steps=4)  # traps
    kit.blob_ellipsoid(MM, (0.085 * sx, -0.112, 1.375), (0.1, 0.045, 0.065), rot=(0, 0.2 * sx, 0))        # pecs
    kit.blob_ellipsoid(MM, (0.17 * sx, -0.02, 1.26), (0.06, 0.11, 0.13))                             # lats
    kit.blob_ellipsoid(MM, (0.09 * sx, 0.1, 1.38), (0.1, 0.05, 0.11))                                # back
for side in ('l', 'r'):
    shd, elb, palm_ = a[f'shoulder_{side}'], a[f'elbow_{side}'], a[f'hand_{side}']
    fdir = (palm_ - elb).normalized()
    wrist = palm_ - fdir * 0.055
    kit.blob_ball(MM, shd, 0.082 * w)                                                     # deltoid
    kit.blob_limb(MM, shd, elb, 0.07 * w, 0.054 * w)
    kit.blob_ellipsoid(MM, shd.lerp(elb, 0.5) + V((0, -0.02, 0)), (0.058 * w, 0.058 * w, 0.07 * w))  # bicep
    kit.blob_limb(MM, elb, wrist, 0.058 * w, 0.04 * w)
    kit.blob_ellipsoid(MM, elb.lerp(wrist, 0.3), (0.06 * w, 0.06 * w, 0.06 * w))         # forearm mass
kit.solidify_blobs({'kr_body': SKIN})
MT = bvh(bpy.data.objects['kr_body_mesh'])
TT = MT
bpy.data.objects.remove(top_obj, do_unlink=True)   # fully enclosed by kr_body; avoids poke-through

# ── sculpted head: heavy brow ridge, cheek planes, square jaw, broad nose ──
MK = 1 / 0.68   # lone metaball elements render ~0.68x their requested size
HEADC, HR = V((0, -0.008, 1.70)), (0.1, 0.112, 0.116)
HD = kit._meta('kr_head', resolution=0.0065)
kit.blob_ellipsoid(HD, HEADC, tuple(x * MK for x in HR))                                      # cranium
kit.blob_ellipsoid(HD, (0, -0.035, 1.628), (0.08 * MK, 0.076 * MK, 0.064 * MK))               # jaw
kit.blob_ellipsoid(HD, (0, -0.078, 1.584), (0.03 * MK, 0.025 * MK, 0.022 * MK))               # chin
kit.blob_ellipsoid(HD, (0, -0.103, 1.717), (0.015 * MK, 0.011 * MK, 0.011 * MK))              # glabella
kit.blob_ellipsoid(HD, (0, -0.108, 1.688), (0.0095 * MK, 0.012 * MK, 0.021 * MK), rot=(-0.3, 0, 0))  # nose bridge
kit.blob_ellipsoid(HD, (0, -0.122, 1.664), (0.013 * MK, 0.012 * MK, 0.011 * MK))              # nose tip
for sx in (1, -1):
    kit.blob_ellipsoid(HD, (0.034 * sx, -0.096, 1.727), (0.03 * MK, 0.014 * MK, 0.011 * MK),
                       rot=(0, -0.22 * sx, 0))                                                 # brow ridge
    kit.blob_ellipsoid(HD, (0.056 * sx, -0.074, 1.674), (0.026 * MK, 0.02 * MK, 0.016 * MK))  # cheekbone
    kit.blob_ellipsoid(HD, (0.05 * sx, -0.062, 1.638), (0.028 * MK, 0.022 * MK, 0.026 * MK))  # cheek plane
    kit.blob_ellipsoid(HD, (0.06 * sx, -0.018, 1.6), (0.026 * MK, 0.036 * MK, 0.03 * MK))     # jaw corner
    kit.blob_ellipsoid(HD, (0.013 * sx, -0.11, 1.659), (0.0085 * MK, 0.008 * MK, 0.008 * MK))   # nostril wing
    kit.blob_ellipsoid(HD, (0.1 * sx, 0.0, 1.685), (0.011 * MK, 0.021 * MK, 0.029 * MK))      # ear
kit.blob_limb(HD, (0, 0.0, 1.5), (0, -0.005, 1.6), 0.056 * MK, 0.054 * MK)                    # neck
kit.solidify_blobs({'kr_head': SKIN})
HEAD = bpy.data.objects['kr_head_mesh']
HT = bvh(HEAD)
ST = HT


def face(x, z, lift=0.0):
    loc, nrm, _, _ = HT.ray_cast(V((x, -1.0, z)), V((0, 1, 0)))
    return loc + nrm * lift, nrm


def decal(x, z, scale, m, lift=0.0, roll=0.0, segs=16, rings=8):
    p, n = face(x, z, lift)
    rot = (V((0, -1, 0)).rotation_difference(n).to_matrix() @ Matrix.Rotation(roll, 3, 'Y')).to_euler()
    return kit.sphere(p, scale, m, rot=rot, segs=segs, rings=rings)


def face_curve(pts_xz, radius, m, lift=0.002, taper=None):
    return kit.tube([tuple(face(x, z, lift)[0]) for x, z in pts_xz], radius, m, resolution=6, taper_to=taper)


# ── fierce eyes: deep-set under the ridge, heavy lids slanting to the nose ──
EYE_W = kit.mat('#e9e4da', 0.35)
INK = kit.mat('#140c06', 0.3)
for sx in (1, -1):
    ex, ez = 0.04 * sx, 1.701
    decal(ex, ez, (0.019, 0.007, 0.0095), EYE_W, lift=-0.002, roll=-0.12 * sx)
    decal(ex - 0.002 * sx, ez - 0.001, (0.0085, 0.006, 0.0085), kit.mat('#c48a22', 0.2), lift=0.001)
    decal(ex - 0.002 * sx, ez - 0.001, (0.0042, 0.005, 0.0045), INK, lift=0.0028, segs=10, rings=5)
    decal(ex - 0.005 * sx, ez + 0.002, (0.0018, 0.002, 0.0018), EYE_W, lift=0.0045, segs=8, rings=4)
    decal(ex, ez + 0.0085, (0.023, 0.009, 0.0085), SKIN, lift=0.0005, roll=-0.3 * sx)          # heavy upper lid
    face_curve([(ex - 0.021 * sx, ez - 0.0015), (ex - 0.004 * sx, ez + 0.0035), (ex + 0.019 * sx, ez + 0.006)],
               0.0018, INK, lift=0.0028)                                                            # lid line
    face_curve([(ex - 0.014 * sx, ez - 0.009), (ex + 0.012 * sx, ez - 0.0085)], 0.001, kit.mat('#6d6862', 0.6),
               lift=0.0012)                                                                         # lower lid
    face_curve([(0.011 * sx, 1.713), (0.036 * sx, 1.727), (0.07 * sx, 1.733)], 0.0062, BEARD_DK,
               lift=0.003, taper=0.5)                                                               # heavy brow
    face_curve([(0.016 * sx, 1.718), (0.045 * sx, 1.731), (0.066 * sx, 1.737)], 0.004, BEARD,
               lift=0.0045, taper=0.4)
# set, downturned mouth
face_curve([(-0.02, 1.6), (0, 1.603), (0.02, 1.6)], 0.0026, kit.mat('#5a3530', 0.5), lift=0.0005)

# ── red tattoo: back of the skull, over the crown, down over the left eye; down the left torso ──
ribbon([HT], [(0.042, 0.13, 1.64), (0.044, 0.1, 1.77), (0.044, 0.0, 1.83), (0.044, -0.08, 1.8),
              (0.042, -0.112, 1.745)], 0.028, TATTOO, lift=0.0008, thick=0.0015)
ribbon([HT], [(0.04, -0.11, 1.689), (0.043, -0.11, 1.668), (0.047, -0.1, 1.645), (0.052, -0.09, 1.618)], 0.017,
       TATTOO, lift=0.0008, thick=0.0015)
ribbon([MT], [(0.14, 0.17, 1.28), (0.145, 0.14, 1.45), (0.15, 0.03, 1.53), (0.145, -0.12, 1.46),
               (0.14, -0.2, 1.3), (0.14, -0.2, 1.07)], 0.042, TATTOO,
       lift=0.0008, thick=0.0015)

# ── beard: sculpted mass + many locks ────────────────────────────────────
BM = kit._meta('kr_beard', resolution=0.008)
kit.blob_ellipsoid(BM, (0, -0.1, 1.56), (0.05, 0.045, 0.045))                    # chin mass
kit.blob_ellipsoid(BM, (0, -0.088, 1.52), (0.04, 0.04, 0.04))                    # beard point
kit.blob_ellipsoid(BM, (0, -0.114, 1.582), (0.02, 0.02, 0.016))                  # under the lip
for sx in (1, -1):
    kit.blob_ellipsoid(BM, (0.065 * sx, -0.045, 1.6), (0.036, 0.058, 0.05))       # jaw
    kit.blob_ellipsoid(BM, (0.045 * sx, -0.085, 1.565), (0.038, 0.04, 0.04))      # jaw-chin bridge
    kit.blob_ellipsoid(BM, (0.07 * sx, -0.062, 1.638), (0.025, 0.04, 0.035))      # cheek
    kit.blob_ellipsoid(BM, (0.09 * sx, -0.012, 1.655), (0.02, 0.04, 0.04))        # sideburn
    kit.blob_ellipsoid(BM, (0.03 * sx, -0.106, 1.586), (0.03, 0.028, 0.026))      # beside the lip
kit.solidify_blobs({'kr_beard': BEARD})
BT = bvh(bpy.data.objects['kr_beard_mesh'])
golden = math.pi * (3 - math.sqrt(5))
for i in range(260):
    zc = 1 - 2 * (i + 0.5) / 260
    rr = math.sqrt(1 - zc * zc)
    d = V((math.cos(golden * i) * rr, math.sin(golden * i) * rr, zc))
    if d.y > 0.35:
        continue
    loc, nrm, _, _ = BT.find_nearest(V((0, -0.07, 1.58)) + d * 0.15)
    if loc.z > 1.66 or (loc.z > 1.6 and abs(loc.x) < 0.03 and loc.y < -0.1):
        continue
    g = (V((0, -0.25, -1)) + nrm * 0.35).normalized()
    ln = random.uniform(0.03, 0.055)
    lock([loc - nrm * 0.004, loc + nrm * 0.006 + g * ln * 0.5, loc + nrm * 0.002 + g * ln],
         random.uniform(0.008, 0.011), random.choice((BEARD, BEARD, BEARD_DK, BEARD_LT)), nrm)
# moustache framing the mouth
for sx in (1, -1):
    lock([face(0.004 * sx, 1.618, 0.003)[0], face(0.02 * sx, 1.612, 0.004)[0], face(0.03 * sx, 1.594, 0.005)[0],
          face(0.034 * sx, 1.572, 0.006)[0]], 0.009, BEARD, (0, -1, 0))

# ── right-shoulder pauldron, held by a leather baldric ───────────────────
sh, el = a['shoulder_r'], a['elbow_r']
arm = (el - sh).normalized()
up = (V((-0.6, 0, 1)) - arm * V((-0.6, 0, 1)).dot(arm)).normalized()
PAUL = kit.mat('#4f565e', 0.35, metal=0.85)
dome(sh + arm * 0.05 + up * 0.0, up, (0.12, 0.125, 0.06), LEATHER_DK)
dome(sh + up * 0.025 + arm * 0.01, up, (0.115, 0.12, 0.062), PAUL, rim=BRONZE, segs=36)
dome(sh + up * 0.075 + arm * 0.01, up, (0.055, 0.06, 0.02), BRONZE)
for k in range(6):
    ang = k / 6 * 2 * math.pi
    q = Matrix.Rotation(ang, 3, up)
    side = (q @ arm.cross(up)).normalized()
    kit.sphere(sh + up * 0.07 + side * 0.075, 0.009, BRONZE, segs=10, rings=5)
strap_front = ribbon([MT], [(-0.2, -0.04, 1.52), (-0.15, -0.15, 1.44), (-0.05, -0.18, 1.3),
                                (0.07, -0.17, 1.17), (0.18, -0.13, 1.06)], 0.042, LEATHER_DK,
                     lift=0.004, thick=0.008)
ribbon([MT], [(-0.2, 0.04, 1.52), (-0.15, 0.14, 1.42), (-0.03, 0.16, 1.28), (0.1, 0.15, 1.15),
                  (0.18, 0.11, 1.06)], 0.042, LEATHER_DK, lift=0.004, thick=0.008)
for t in (0.25, 0.55):
    p = strap_front[int(t * (len(strap_front) - 1))]
    loc, nrm, _, _ = nearest([MT], p)
    kit.box(loc + nrm * 0.014, (0.03, 0.006, 0.022), STEEL, rot=kit.rot_between((0, 0, 0), nrm), bevel=0.002)

# ── belt, buckle, skirt of leather tassets with a cloth flap ─────────────
kit.torus((0, 0.0, 1.02), 1.0, 0.04, LEATHER_DK, scale=(0.205, 0.15, 1.0), major_segs=40, minor_segs=10)
kit.torus((0, 0.0, 0.985), 1.0, 0.012, BRONZE, scale=(0.215, 0.158, 1.0), major_segs=40, minor_segs=6)
kit.cylinder((0, -0.19, 1.02), 0.05, 0.02, STEEL, rot=(math.pi / 2, 0, 0), verts=24)
kit.torus((0, -0.2, 1.02), 0.042, 0.008, BRONZE, rot=(math.pi / 2, 0, 0), major_segs=24, minor_segs=6)
kit.sphere((0, -0.205, 1.02), (0.018, 0.008, 0.018), STEEL, segs=12, rings=6)
panel((0, -0.17, 0.99), 0.13, 0.42, (0, -1, 0), 0.12, CLOTH)
for k, ang in enumerate((-80, -45, 45, 80, 120, 160, 200, 240)):
    t = math.radians(ang)
    out = V((math.sin(t), -math.cos(t), 0))
    top = V((0, 0, 0.99)) + V((out.x * 0.2, out.y * 0.15, 0))
    panel(top, 0.1, 0.3 if abs(ang) < 100 else 0.26, out, 0.22, LEATHER if k % 2 else LEATHER_DK, hem=BRONZE)

# ── vambraces + Guardian Shield folded on the left forearm ───────────────
for side in ('l', 'r'):
    el_, wr_ = a[f'elbow_{side}'], a[f'hand_{side}']
    fore = wr_ - el_
    kit.rod(el_ + fore * 0.28, el_ + fore * 0.82, 0.05, LEATHER_DK, verts=20, r2=0.044)
    for t in (0.32, 0.55, 0.78):
        kit.torus(el_ + fore * t, 0.051 - t * 0.008, 0.005, STEEL, rot=kit.rot_between((0, 0, 0), fore),
                  major_segs=24, minor_segs=6)
el_, wr_ = a['elbow_l'], a['hand_l']
mid = el_.lerp(wr_, 0.52)
sc = mid + V((0.055, 0, 0))
kit.cylinder(sc, 0.085, 0.022, STEEL, rot=(0, math.pi / 2, 0), verts=40)
kit.torus(sc + V((0.012, 0, 0)), 0.085, 0.009, BRONZE, rot=(0, math.pi / 2, 0), major_segs=40, minor_segs=8)
kit.sphere(sc + V((0.014, 0, 0)), (0.012, 0.035, 0.035), BRONZE, segs=20, rings=10)
for k in range(8):
    t = k / 8 * 2 * math.pi
    kit.box(sc + V((0.013, math.cos(t) * 0.058, math.sin(t) * 0.058)), (0.006, 0.012, 0.03), BRONZE,
            rot=(t, 0, 0))

# ── legs: leather wraps, boots ───────────────────────────────────────────
for side in ('l', 'r'):
    knee = a[f'knee_{side}']
    ank = V((knee.x * 1.06, 0.01, 0.1))
    kit.rod(ank + V((0, 0.004, 0.0)), ank.lerp(knee, 0.6), 0.058, LEATHER_DK, verts=20, r2=0.07)
    for k in range(5):
        p = ank.lerp(knee, 0.08 + k * 0.12)
        kit.torus(p, 0.06 + k * 0.0025, 0.006, LEATHER, rot=(0.3 * (-1) ** k, 0, 0), major_segs=24, minor_segs=5)

# clenched fists
for side in ('l', 'r'):
    kit.subdivide(kit.sphere(a[f'hand_{side}'], (0.04, 0.042, 0.05), SKIN, segs=16, rings=8), 1)

# ── Leviathan Axe ────────────────────────────────────────────────────────
palm = a['hand_r']
d = V((-0.22, 0.12, 0.97)).normalized()
bottom, top = palm - d * 0.2, palm + d * 0.5
kit.rod(bottom, top, 0.016, WOOD, verts=16)
for k in range(9):
    kit.torus(bottom + d * (0.03 + k * 0.03), 0.017, 0.004, LEATHER_DK, rot=kit.rot_between((0, 0, 0), d),
              major_segs=16, minor_segs=5)
kit.sphere(bottom - d * 0.012, (0.022, 0.022, 0.026), STEEL, rot=kit.rot_between((0, 0, 0), d), segs=16, rings=8)
kit.torus(palm, 0.024, 0.016, SKIN, rot=kit.rot_between((0, 0, 0), d), major_segs=20, minor_segs=8)  # grip
U = V((-1, -0.25, 0))
U = (U - d * U.dot(d)).normalized()
hc = top - d * 0.08
blade = [(-0.03, 0.05), (0.03, 0.045), (0.08, 0.07), (0.125, 0.1), (0.165, 0.125), (0.178, 0.08),
         (0.188, 0.03), (0.19, -0.02), (0.184, -0.07), (0.17, -0.12), (0.15, -0.165), (0.12, -0.135),
         (0.085, -0.085), (0.05, -0.05), (0.02, -0.045), (-0.03, -0.045)]
SCALE = 1.35
blade = [(u * SCALE, v * SCALE) for u, v in blade]
extrude(blade, hc, U, d, 0.018, AXE_STEEL)
cx = 0.09
rim = [(cx + (u - cx) * 1.07, v * 1.08) for u, v in blade]
extrude(rim, hc, U, d, 0.007, FROST)
kit.rod(hc - d * 0.075, hc + d * 0.08, 0.026, STEEL, verts=20)
inlay = [(u * SCALE, v * SCALE) for u, v in
         ((0.125, 0.082), (0.152, 0.06), (0.164, 0.02), (0.166, -0.03), (0.157, -0.08), (0.14, -0.118),
          (0.128, -0.1), (0.142, -0.07), (0.15, -0.03), (0.148, 0.015), (0.138, 0.05), (0.115, 0.07))]
extrude(inlay, hc, U, d, 0.0205, RUNE)
kit.box(hc - U * 0.04, (0.03, 0.03, 0.06), STEEL, rot=Matrix((U, U.cross(d), d)).transposed().to_euler(),
        bevel=0.004)

kit.finalize('kratos', thumb_angle=float(os.environ.get('KR_ANGLE', -28)))


def closeup(path, target, dist=1.2, angle=-28, lens=85):
    """Debug render of a detail (only when KR_CLOSEUP is set; writes outside public/)."""
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


if os.environ.get('KR_CLOSEUP'):
    closeup(os.environ['KR_CLOSEUP'] + '_face.png', (0, 0, float(os.environ.get('KR_Z', '1.55'))),
            dist=float(os.environ.get('KR_D', '1.2')), angle=float(os.environ.get('KR_A', '-28')))
