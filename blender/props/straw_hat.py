"""Luffy's straw hat (One Piece) — woven straw rings, red band, tilted toward the camera."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bpy  # noqa: E402
from mathutils import Euler  # noqa: E402


# ── local helpers ────────────────────────────────────────────────────────

def mesh_obj(verts, faces, mats, face_mats=None, smooth=True, name='mesh'):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    for i, p in enumerate(me.polygons):
        p.use_smooth = smooth
        if face_mats:
            p.material_index = face_mats[i]
    return obj


def lathe(profile, mats, seg_mat=None, segs=72, name='lathe'):
    """Surface of revolution around Z. profile = [(r, z), ...]; seg_mat(i) -> material index of segment i."""
    verts, faces, fm, rings = [], [], [], []
    for r, z in profile:
        if r < 1e-6:
            rings.append([len(verts)])
            verts.append((0, 0, z))
        else:
            ring = []
            for k in range(segs):
                a = 2 * math.pi * k / segs
                ring.append(len(verts))
                verts.append((r * math.cos(a), r * math.sin(a), z))
            rings.append(ring)
    for i in range(len(profile) - 1):
        A, B = rings[i], rings[i + 1]
        mi = seg_mat(i) if seg_mat else 0
        for k in range(segs):
            k2 = (k + 1) % segs
            if len(A) == 1:
                faces.append((A[0], B[k2], B[k]))
            elif len(B) == 1:
                faces.append((A[k], A[k2], B[0]))
            else:
                faces.append((A[k], A[k2], B[k2], B[k]))
            fm.append(mi)
    return mesh_obj(verts, faces, mats, fm, name=name)


def rotate_all(euler):
    bpy.context.view_layer.update()
    R = Euler(euler).to_matrix().to_4x4()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.matrix_world = R @ o.matrix_world


# ── build ────────────────────────────────────────────────────────────────

kit.reset()
STRAW = kit.mat('#f0bf3c', 0.8)
STRAW_D = kit.mat('#d99a26', 0.8)
GROOVE = kit.mat('#9c6416', 0.9)
STRAW_U = kit.mat('#c48a2c', 0.9)
RIM = kit.mat('#b07a1e', 0.8)
RED = kit.mat('#c81c22', 0.6)
MATS = [STRAW, STRAW_D, RIM, STRAW_U, GROOVE]

# Brim: woven concentric ridges (alternating straw tones, dark grooves between), rounded rim, plain underside.
R_IN, R_OUT, BW = 0.2, 0.47, 0.04


def droop(r):
    return -0.05 * ((r - R_IN) / (R_OUT - R_IN)) ** 2


prof, segmat = [], []
r = R_IN
band = 0
while r < R_OUT - 0.02:
    w = min(BW, R_OUT - 0.02 - r)
    prof += [(r, droop(r)), (r + 0.006, droop(r + 0.006) + 0.0005),
             (r + w * 0.55, droop(r + w * 0.55) + 0.0015)]
    segmat += [4, band % 2, band % 2]
    r += w
    band += 1
rim_z = droop(R_OUT)
prof += [(R_OUT - 0.02, droop(R_OUT - 0.02) - 0.002), (R_OUT - 0.004, rim_z + 0.004), (R_OUT + 0.006, rim_z - 0.008),
         (R_OUT - 0.004, rim_z - 0.022), (R_OUT - 0.03, droop(R_OUT - 0.03) - 0.02), (R_IN, -0.018)]
segmat += [4, 2, 2, 2, 2, 3]
lathe(prof, MATS, lambda i: segmat[i] if i < len(segmat) else 3, segs=80, name='brim')

# Crown: short cylinder under the band, then a woven dome.
CR, CYL_H, DOME_H = 0.205, 0.1, 0.21
prof = [(CR - 0.002, -0.01), (CR, CYL_H)]
segmat = [0]
n = 8
for i in range(n):
    for j, bump, mi in ((0, 0.0, 4), (0.1, 0.0005, i % 2), (0.55, 0.0015, i % 2)):
        phi = (i + j) / n * (math.pi / 2) * 0.93
        rr = (CR + bump) * math.cos(phi)
        zz = CYL_H + (DOME_H + bump) * math.sin(phi)
        prof.append((rr, zz))
        segmat.append(mi)
prof.append((0.0, CYL_H + DOME_H + 0.004))
lathe(prof, MATS, lambda i: segmat[i] if i < len(segmat) else (n - 1) % 2, segs=72, name='crown')

# Red band (slightly proud of the crown) with a crisp top/bottom lip.
lathe([(CR - 0.004, 0.0), (CR + 0.012, 0.004), (CR + 0.016, 0.02), (CR + 0.016, 0.082),
       (CR + 0.012, 0.098), (CR - 0.004, 0.104)], [RED], segs=72, name='band')

rotate_all((math.radians(20), 0, 0))
kit.finalize_prop('straw_hat')
