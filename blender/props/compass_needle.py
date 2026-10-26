"""Compass needle (overlay for the `compass` prop): slim faceted diamond in the X–Z plane, red half up,
silver half down, brass pivot cap. Geometry is symmetric in X, Y and Z so the bounding-box centre
(= sprite centre) is exactly the pivot."""
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()

RED = kit.mat('#c4271d', 0.35, metal=0.35)
RED_DK = kit.mat('#7e1410', 0.4, metal=0.35)
SILVER = kit.mat('#e4e8ee', 0.22, metal=0.85)
SILVER_DK = kit.mat('#a9b0ba', 0.3, metal=0.9)
BRASS = kit.mat('#c99a40', 0.28, metal=0.9)
BRASS_DK = kit.mat('#7a5320', 0.4, metal=0.85)

L = 0.5      # half length
W = 0.08    # half width at the waist
T = 0.022    # ridge height (each side)


def needle_half(sign, m_light, m_dark):
    """Upper (sign=+1) or lower (sign=-1) half: 4 facets meeting at the tip, two-tone for a ridge highlight."""
    me = bpy.data.meshes.new('needle')
    bm = bmesh.new()
    tip = bm.verts.new((0, 0, sign * L))
    left = bm.verts.new((-W, 0, 0))
    right = bm.verts.new((W, 0, 0))
    front = bm.verts.new((0, -T, 0))
    back = bm.verts.new((0, T, 0))
    faces = [
        ((tip, left, front), 0), ((tip, front, right), 1),
        ((tip, right, back), 0), ((tip, back, left), 1),
    ]
    for vs, mi in faces:
        f = bm.faces.new(vs)
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new('needle', me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m_light)
    me.materials.append(m_dark)
    return obj


needle_half(+1, RED, RED_DK)
needle_half(-1, SILVER, SILVER_DK)

# pivot cap: symmetric through the needle (front + back)
Y90 = (math.pi / 2, 0, 0)
kit.cylinder((0, 0, 0), 0.05, 0.05, BRASS, rot=Y90, verts=32)
kit.torus((0, 0, 0), 0.05, 0.012, BRASS_DK, rot=Y90, major_segs=32, minor_segs=8)
for sy in (-1, 1):
    kit.sphere((0, sy * 0.025, 0), (0.042, 0.022, 0.042), BRASS, segs=24, rings=12)
    kit.sphere((0, sy * 0.045, 0), (0.012, 0.006, 0.012), BRASS_DK, segs=12, rings=6)

kit.finalize_prop('compass_needle', thumb_angle=0, elevation=0.0)
