"""Sir Francis Drake's gold ring ("SIC PARVIS MAGNA") hanging on a leather cord loop."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()

GOLD = kit.mat('#d6a536', 0.22, metal=1.0)
GOLD_LT = kit.mat('#f0c95a', 0.18, metal=1.0)
GOLD_DK = kit.mat('#7d5418', 0.45, metal=0.9)
LEATHER = kit.mat('#6e4122', 0.8)
LEATHER_DK = kit.mat('#4a2814', 0.75)


# ── local helpers ────────────────────────────────────────────────────────

def lathe(profile, m_list, mat_idx=None, segs=64, name='lathe'):
    """Revolve a closed (radius, y) profile around the Y axis. mat_idx[j] picks the material of
    the band between profile points j and j+1."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    n = len(profile)
    rows = []
    for i in range(segs):
        a = i * 2 * math.pi / segs
        rows.append([bm.verts.new((math.cos(a) * r, y, math.sin(a) * r)) for r, y in profile])
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


def text_mesh(s, size, m, matrix, extrude=0.006):
    cu = bpy.data.curves.new('txt', 'FONT')
    cu.body = s
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 2
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    obj = bpy.data.objects.new('txt', cu)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = matrix
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.active_object
    obj.data.materials.append(m)
    return obj


def loop_tube(points, radius, m, name='cord'):
    """Closed smooth tube (cyclic Bezier)."""
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.resolution_u = 8
    sp = curve.splines.new('BEZIER')
    sp.bezier_points.add(len(points) - 1)
    for i, p in enumerate(points):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    sp.use_cyclic_u = True
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.active_object
    obj.data.materials.append(m)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


# ── ring (axis = Y, i.e. facing the camera; rotated at the end) ──────────
RIN, ROUT, CH = 0.16, 0.25, 0.236
profile = [
    (0.172, 0.068), (0.163, 0.035), (0.16, 0.0), (0.163, -0.035), (0.172, -0.068),     # comfort-fit inside
    (0.2, -0.075), (0.235, -0.074), (0.249, -0.066), (ROUT, -0.054), (0.247, -0.044),  # lower rim
    (CH, -0.039), (CH, 0.039),                                                         # inscription channel
    (0.247, 0.044), (ROUT, 0.054), (0.249, 0.066), (0.235, 0.074), (0.2, 0.075),       # upper rim
]
mat_idx = [0] * len(profile)
mat_idx[10] = 1   # channel band -> dark patina so raised letters pop
lathe(profile, [GOLD, GOLD_DK], mat_idx, segs=72, name='band')

# raised inscription letters around the channel, leaving a gap for the crest (crest at angle CREST_A)
CREST_A = math.radians(332)   # on the band's right side (faces the camera after the final rotation)
motto = 'SIC PARVIS MAGNA'
step = math.radians(11.2)
start = math.radians(170)
for k, ch in enumerate(motto):
    if ch == ' ':
        continue
    phi = start - k * step
    r = Vector((math.cos(phi), 0, math.sin(phi)))
    t = Vector((-math.sin(phi), 0, math.cos(phi)))
    t = -t
    u = Vector((0, 1, 0))
    m4 = Matrix((
        (t.x, u.x, r.x, r.x * (CH + 0.003)),
        (t.y, u.y, r.y, r.y * (CH + 0.003)),
        (t.z, u.z, r.z, r.z * (CH + 0.003)),
        (0, 0, 0, 1)))
    text_mesh(ch, 0.062, GOLD_LT, m4, extrude=0.005)

# crest: raised oval cartouche with a tiny compass-star, on the band side
cr = Vector((math.cos(CREST_A), 0, math.sin(CREST_A)))
crest_rot = Vector((0, 0, 1)).rotation_difference(cr).to_euler()
kit.sphere(cr * 0.248, (0.06, 0.075, 0.022), GOLD_LT, rot=crest_rot, segs=24, rings=12)
kit.torus(cr * 0.258, 0.05, 0.008, GOLD, rot=crest_rot, major_segs=32, minor_segs=6, scale=(1, 1.25, 1))
for a in range(4):  # 4-point star
    ang = a * math.pi / 2
    tip = Vector((math.cos(ang) * 0.034, math.sin(ang) * 0.042, 0))
    m_rot = Matrix.Translation(cr * 0.266) @ crest_rot.to_matrix().to_4x4()
    kit.spike(m_rot @ Vector((0, 0, 0)), m_rot @ tip, 0.011, GOLD_DK, verts=8)

# ── leather cord ─────────────────────────────────────────────────────────
TOPIN = RIN - 0.025
knot_z = 0.4
pts = [
    (0, 0.0, TOPIN), (0, -0.1, TOPIN + 0.04), (0, -0.07, 0.27), (0, -0.025, knot_z),      # front strand to knot
    (-0.11, -0.02, 0.5), (-0.23, 0.0, 0.64), (-0.22, 0.02, 0.78), (-0.09, 0.03, 0.85),
    (0.0, 0.03, 0.86), (0.09, 0.03, 0.85), (0.22, 0.02, 0.78), (0.23, 0.0, 0.64), (0.11, 0.0, 0.5),
    (0, 0.025, knot_z), (0, 0.07, 0.27), (0, 0.1, TOPIN + 0.04),
]
loop_tube(pts, 0.019, LEATHER)
# sliding knot: wrapped barrel around both strands
kit.cylinder((0, 0, knot_z + 0.005), 0.05, 0.07, LEATHER_DK, verts=20, scale=(0.85, 1, 1))
for dz in (-0.022, 0.0, 0.022):
    kit.torus((0, 0, knot_z + 0.005 + dz), 0.05, 0.012, LEATHER, major_segs=24, minor_segs=8, scale=(0.85, 1, 1))
# small gold bead under the knot
kit.sphere((0, 0, knot_z - 0.06), 0.028, GOLD, segs=20, rings=10)

# turn the whole thing so the ring face and crest catch the 3/4 sprite camera
bpy.context.view_layer.update()
R = Matrix.Rotation(math.radians(-14), 4, 'Z') @ Matrix.Rotation(math.radians(8), 4, 'X')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = R @ o.matrix_world

kit.finalize_prop('drake_ring')
