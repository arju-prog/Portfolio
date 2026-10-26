"""A single thick, slightly worn gold doubloon facing the camera: raised rim, beaded border,
embossed cross-potent with quartered crest marks (both faces)."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()
random.seed(3)

GOLD_HI = kit.mat('#f5c542', 0.18, metal=1.0)     # polished high points
GOLD = kit.mat('#dba22c', 0.3, metal=1.0)
GOLD_LO = kit.mat('#9c6a16', 0.5, metal=0.9)      # grimy recessed field


def lathe(profile, m_list, mat_idx=None, segs=72, name='lathe', wobble=0.0):
    """Revolve a closed (radius, y) profile around the Y axis. `wobble` adds a little irregularity (worn cob)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    n = len(profile)
    rows = []
    for i in range(segs):
        a = i * 2 * math.pi / segs
        k = 1 + wobble * (math.sin(3 * a + 0.7) * 0.6 + math.sin(5 * a + 2.1) * 0.4)
        rows.append([bm.verts.new((math.cos(a) * r * k, y, math.sin(a) * r * k)) for r, y in profile])
    for i in range(segs):
        r0, r1 = rows[i], rows[(i + 1) % segs]
        for j in range(n):
            f = bm.faces.new((r0[j], r1[j], r1[(j + 1) % n], r0[(j + 1) % n]))
            f.material_index = mat_idx[j] if mat_idx else 0
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in m_list:
        me.materials.append(m)
    return obj


WOB = 0.012
T = 0.06    # half thickness at the rim
profile = [
    (0.5, 0.035), (0.5, -0.035),                                   # edge
    (0.494, -0.052), (0.478, -T), (0.452, -T + 0.003), (0.432, -0.05), (0.425, -0.042),   # front rim
    (0.425, 0.042), (0.432, 0.05), (0.452, T - 0.003), (0.478, T), (0.494, 0.052),       # back rim
]
mat_idx = [1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0]
lathe(profile, [GOLD_HI, GOLD, GOLD_LO], mat_idx, wobble=WOB, name='rim')
# recessed field
kit.cylinder((0, 0, 0), 0.428, 0.084, GOLD_LO, rot=(math.pi / 2, 0, 0), verts=72)
# reeded edge marks
for i in range(90):
    a = i * 2 * math.pi / 90
    k = 1 + WOB * (math.sin(3 * a + 0.7) * 0.6 + math.sin(5 * a + 2.1) * 0.4)
    kit.box((math.cos(a) * 0.5 * k, 0, math.sin(a) * 0.5 * k), (0.008, 0.06, 0.012), GOLD, rot=(0, -a, 0))


def face_design(side):
    """Embossed design on the face at y = side * 0.042 (side=-1 front)."""
    y = side * 0.042
    up = side * 0.012   # emboss height direction
    # beaded border
    for i in range(44):
        a = i * 2 * math.pi / 44
        kit.sphere((math.cos(a) * 0.385, y + up * 0.3, math.sin(a) * 0.385), (0.016, 0.012, 0.016), GOLD_HI,
                   segs=8, rings=5)
    kit.torus((0, y, 0), 0.355, 0.006, GOLD, rot=(math.pi / 2, 0, 0), major_segs=64, minor_segs=6)
    # cross potent
    for rz in (0, math.pi / 2):
        kit.box((0, y + up * 0.6, 0), (0.085, 0.022, 0.5), GOLD_HI, rot=(0, rz, 0), bevel=0.012)
    for a in range(4):
        ang = a * math.pi / 2
        c = Vector((math.cos(ang) * 0.255, y + up * 0.6, math.sin(ang) * 0.255))
        kit.box(c, (0.19, 0.022, 0.06), GOLD_HI, rot=(0, -ang + math.pi / 2, 0), bevel=0.012)
    kit.cylinder((0, y + up * 1.2, 0), 0.06, 0.02, GOLD, rot=(math.pi / 2, 0, 0), verts=24)
    kit.sphere((0, y + up * 1.8, 0), (0.035, 0.012, 0.035), GOLD_HI, segs=16, rings=8)
    # quartered crest marks: castles (top-left / bottom-right) and lions-as-roundels (others)
    for a in range(4):
        ang = math.pi / 4 + a * math.pi / 2
        c = Vector((math.cos(ang) * 0.19, y + up * 0.5, math.sin(ang) * 0.19))
        if a % 2 == 0:
            kit.box(c, (0.07, 0.02, 0.06), GOLD_HI, bevel=0.008)
            for dx in (-0.025, 0, 0.025):
                kit.box(c + Vector((dx, 0, 0.04)), (0.016, 0.02, 0.022), GOLD_HI)
        else:
            kit.sphere(c, (0.045, 0.014, 0.045), GOLD_HI, segs=16, rings=8)
            kit.sphere(c + Vector((0, up * 0.8, 0)), (0.018, 0.008, 0.018), GOLD, segs=10, rings=5)


face_design(-1)
face_design(+1)

# slight yaw so the thick reeded edge reads in the sprite
bpy.context.view_layer.update()
R = Matrix.Rotation(math.radians(14), 4, 'Z')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = R @ o.matrix_world

kit.finalize_prop('gold_coin', thumb_angle=0, elevation=0.05)
