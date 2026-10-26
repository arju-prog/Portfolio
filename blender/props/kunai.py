"""Ninja kunai (Naruto) — dark steel diamond blade with honed edges, cloth-wrapped grip, ring pommel."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bpy  # noqa: E402


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


kit.reset()
STEEL = kit.mat('#363b44', 0.32, metal=0.9)
EDGE = kit.mat('#c3cad4', 0.18, metal=1.0)
IRON = kit.mat('#2a2d33', 0.4, metal=0.8)
CLOTH = kit.mat('#e9dfc6', 0.95)
CLOTH_D = kit.mat('#bfb193', 0.95)

# ── blade: lofted diamond cross-section (central ridge + honed bevel along both edges) ──
BLADE_H = 0.56
N = 22
sections = []
for i in range(N):
    t = i / (N - 1)
    z = t * BLADE_H
    if t < 0.3:
        w = 0.036 + (0.118 - 0.036) * math.sin(t / 0.3 * math.pi / 2)
    else:
        u = (t - 0.3) / 0.7
        w = 0.118 * (1 - u) ** 0.85
    th = 0.007 + 0.2 * w
    sections.append((z, w, th))

verts, faces, fm = [], [], []
ring_idx = []
for z, w, th in sections[:-1]:
    base = len(verts)
    pts = [(w, 0), (0.6 * w, -0.4 * th), (0, -th), (-0.6 * w, -0.4 * th),
           (-w, 0), (-0.6 * w, 0.4 * th), (0, th), (0.6 * w, 0.4 * th)]
    verts += [(x, y, z) for x, y in pts]
    ring_idx.append(list(range(base, base + 8)))
tip = len(verts)
verts.append((0, 0, BLADE_H))
edge_faces = {0, 3, 4, 7}  # outer bevel strips
for i in range(len(ring_idx) - 1):
    A, B = ring_idx[i], ring_idx[i + 1]
    for k in range(8):
        k2 = (k + 1) % 8
        faces.append((A[k], A[k2], B[k2], B[k]))
        fm.append(1 if k in edge_faces else 0)
for k in range(8):
    faces.append((ring_idx[-1][k], ring_idx[-1][(k + 1) % 8], tip))
    fm.append(1 if k in edge_faces else 0)
faces.append(tuple(reversed(ring_idx[0])))
fm.append(0)
mesh_obj(verts, faces, [STEEL, EDGE], fm, smooth=False, name='blade')

# ── guard collar ──
kit.cylinder((0, 0, -0.012), 0.032, 0.026, IRON, verts=24)
kit.torus((0, 0, -0.002), 0.031, 0.006, EDGE, major_segs=32, minor_segs=8)

# ── grip: dark core + crossing cloth wraps ──
G_TOP, G_BOT = -0.025, -0.33
kit.cylinder((0, 0, (G_TOP + G_BOT) / 2), 0.024, G_TOP - G_BOT, IRON, verts=20)
n_wraps = 12
step = (G_TOP - G_BOT) / n_wraps
for i in range(n_wraps):
    z = G_TOP - step * (i + 0.5)
    tilt = 0.22 if i % 2 == 0 else -0.22
    kit.torus((0, 0, z), 0.027, 0.0145, CLOTH if i % 2 == 0 else CLOTH_D, rot=(tilt, 0, 0),
              major_segs=28, minor_segs=8, scale=(1, 1, 0.9))
# loose wrap tail
kit.tube([(0.02, -0.018, G_BOT + 0.03), (0.05, -0.03, G_BOT + 0.0), (0.06, -0.035, G_BOT - 0.05)],
         0.006, CLOTH, taper_to=0.6, resolution=6, name='wrap_tail')

# ── pommel collar + ring ──
kit.cylinder((0, 0, G_BOT - 0.008), 0.03, 0.018, IRON, verts=24)
kit.torus((0, 0, G_BOT - 0.008), 0.03, 0.005, EDGE, major_segs=32, minor_segs=8)
RING_R = 0.062
kit.cylinder((0, 0, G_BOT - 0.026), 0.014, 0.022, IRON, verts=16)
kit.torus((0, 0, G_BOT - 0.03 - RING_R), RING_R, 0.013, IRON, rot=(math.pi / 2, 0, 0),
          major_segs=48, minor_segs=12)

kit.finalize_prop('kunai')
