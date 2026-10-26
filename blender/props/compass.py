"""Nathan Drake's antique brass compass — lid open behind, dial facing the camera, NO needle
(the needle is the separate `compass_needle` prop, rotated on top by the site)."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

kit.reset()

BRASS = kit.mat('#a97a30', 0.35, metal=0.9)
BRASS_LT = kit.mat('#d9b25e', 0.25, metal=0.9)
BRASS_DK = kit.mat('#6e4b1e', 0.45, metal=0.8)
DIAL = kit.mat('#e8d2a2', 0.7)
INK = kit.mat('#2b1e12', 0.5)
RED = kit.mat('#a8231b', 0.45)


# ── local helpers ────────────────────────────────────────────────────────

def text_mesh(s, loc, size, m, extrude=0.006, rot=(math.pi / 2, 0, 0)):
    """Flat embossed text facing -Y (default rot), centred on loc."""
    cu = bpy.data.curves.new('txt', 'FONT')
    cu.body = s
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 3
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    obj = bpy.data.objects.new('txt', cu)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.active_object
    obj.data.materials.append(m)
    return obj


def rose(center_y, r_main, r_diag, r_valley, height, m_a, m_b, ink_y_off=0.0):
    """Faceted 8-point compass rose lying in the XZ plane, raised toward -Y. Two-tone facets."""
    me = bpy.data.meshes.new('rose')
    bm = bmesh.new()
    c = bm.verts.new((0, center_y - height, 0))
    n = 8
    tips, valleys = [], []
    for i in range(n):
        a = math.pi / 2 - i * 2 * math.pi / n
        r = r_main if i % 2 == 0 else r_diag
        tips.append(bm.verts.new((math.cos(a) * r, center_y, math.sin(a) * r)))
        av = a - math.pi / n
        valleys.append(bm.verts.new((math.cos(av) * r_valley, center_y, math.sin(av) * r_valley)))
    for i in range(n):
        vl = valleys[i - 1]
        vr = valleys[i]
        f1 = bm.faces.new((c, vl, tips[i]))
        f1.material_index = 0
        f2 = bm.faces.new((c, tips[i], vr))
        f2.material_index = 1
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new('rose', me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(m_a)
    me.materials.append(m_b)
    for p in me.polygons:
        p.use_smooth = False
    # make normals face -Y
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def ring_pts(r, y, a):
    return (math.cos(a) * r, y, math.sin(a) * r)


Y90 = (math.pi / 2, 0, 0)   # cylinder/torus axis -> Y

# ── case ─────────────────────────────────────────────────────────────────
R = 0.5
kit.cylinder((0, 0.07, 0), R, 0.16, BRASS, rot=Y90, verts=64)
kit.torus((0, -0.025, 0), 0.468, 0.048, BRASS_LT, rot=Y90, major_segs=64, minor_segs=12)     # front bezel
kit.torus((0, 0.155, 0), 0.47, 0.04, BRASS, rot=Y90, major_segs=64, minor_segs=10)          # back rim
kit.sphere((0, 0.16, 0), (0.47, 0.05, 0.47), BRASS, segs=48, rings=12)                     # domed back
kit.torus((0, 0.07, 0), 0.503, 0.012, BRASS_DK, rot=Y90, major_segs=64, minor_segs=6)        # mid-band groove
# reeded edge: small ribs around the case side
for i in range(48):
    a = i * 2 * math.pi / 48
    kit.box(ring_pts(0.505, 0.07, a), (0.012, 0.09, 0.012), BRASS_DK, rot=(0, -a, 0))

# ── dial ─────────────────────────────────────────────────────────────────
kit.cylinder((0, 0.0, 0), 0.44, 0.02, DIAL, rot=Y90, verts=64)
DY = -0.012   # dial surface for inlays
kit.torus((0, DY, 0), 0.432, 0.012, BRASS, rot=Y90, major_segs=64, minor_segs=8)            # chapter ring edge
for r, w in ((0.405, 0.0045), (0.33, 0.004), (0.315, 0.0025), (0.155, 0.003)):
    kit.torus((0, DY, 0), r, w, INK, rot=Y90, major_segs=64, minor_segs=6)

# degree ticks
for i in range(72):
    a = math.pi / 2 - i * 2 * math.pi / 72
    deg = i * 5
    if deg % 90 == 0:
        continue
    long = deg % 30 == 0
    r0, r1 = (0.34, 0.403) if long else (0.375, 0.403)
    w = 0.009 if long else 0.005
    mid = (r0 + r1) / 2
    kit.box(ring_pts(mid, DY, a), (r1 - r0, 0.006, w), INK, rot=(0, -a, 0))

# cardinal arrowheads on the outer ring (N red)
for i, letter in enumerate('NESW'):
    a = math.pi / 2 - i * math.pi / 2
    tip = ring_pts(0.405, DY - 0.002, a)
    base = 0.335
    me = bpy.data.meshes.new('tri')
    bm = bmesh.new()
    perp = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
    p0 = bm.verts.new(tip)
    p1 = bm.verts.new((math.cos(a) * base + perp[0] * 0.028, DY - 0.002, math.sin(a) * base + perp[1] * 0.028))
    p2 = bm.verts.new((math.cos(a) * base - perp[0] * 0.028, DY - 0.002, math.sin(a) * base - perp[1] * 0.028))
    f = bm.faces.new((p0, p1, p2))
    bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in bm.verts[3:]:
        v.co.y += 0.006
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new('tri', me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(RED if letter == 'N' else INK)

# letters
for i, letter in enumerate('NESW'):
    a = math.pi / 2 - i * math.pi / 2
    x, _, z = ring_pts(0.243, DY, a)
    text_mesh(letter, (x, DY - 0.002, z), 0.115, RED if letter == 'N' else INK, extrude=0.004)

# intercardinal small dots
for i in range(4):
    a = math.pi / 4 + i * math.pi / 2
    kit.sphere(ring_pts(0.243, DY, a), (0.014, 0.006, 0.014), BRASS_DK, segs=12, rings=6)

# compass rose (under where the needle will sit)
rose(DY - 0.001, 0.15, 0.1, 0.035, 0.022, BRASS_LT, BRASS_DK)
kit.cylinder((0, DY - 0.03, 0), 0.022, 0.03, BRASS_LT, rot=Y90, verts=16)                     # pivot post
kit.sphere((0, DY - 0.045, 0), 0.016, BRASS_LT, segs=16, rings=8)

# glass crystal ring glint (thin bright ring just inside the bezel)
kit.torus((0, -0.05, 0), 0.445, 0.006, kit.mat('#fff6dc', 0.1, metal=0.3), rot=Y90, major_segs=64, minor_segs=6)

# thumb catch at the bottom
kit.box((0, -0.01, -0.53), (0.1, 0.07, 0.05), BRASS_LT, bevel=0.012)

# ── hinge ────────────────────────────────────────────────────────────────
H = Vector((0, 0.1, 0.545))
for x, w in ((-0.09, 0.06), (0.0, 0.07), (0.09, 0.06)):
    kit.cylinder((x, H.y, H.z), 0.032, w - 0.004, BRASS_LT if x == 0 else BRASS, rot=(0, math.pi / 2, 0), verts=20)
kit.box((0, 0.09, 0.505), (0.2, 0.05, 0.06), BRASS, bevel=0.012)   # hinge leaf on case

# ── lid (built opened 180° above the hinge, then leaned back) ────────────
before = set(bpy.context.scene.objects)
C = Vector((0, H.y, H.z + 0.53))
kit.box((0, H.y + 0.005, H.z + 0.045), (0.2, 0.05, 0.07), BRASS, bevel=0.012)   # hinge leaf on lid
kit.cylinder(C + Vector((0, 0.01, 0)), 0.5, 0.05, BRASS, rot=Y90, verts=64)
kit.sphere(C + Vector((0, 0.035, 0)), (0.48, 0.05, 0.48), BRASS, segs=48, rings=12)         # outer dome
kit.torus(C + Vector((0, -0.015, 0)), 0.47, 0.04, BRASS_LT, rot=Y90, major_segs=64, minor_segs=10)
# inner face: dark engraved panel with ring + motto
kit.cylinder(C + Vector((0, -0.01, 0)), 0.43, 0.01, BRASS_DK, rot=Y90, verts=64)
kit.torus(C + Vector((0, -0.016, 0)), 0.395, 0.007, BRASS_LT, rot=Y90, major_segs=64, minor_segs=6)
kit.torus(C + Vector((0, -0.016, 0)), 0.37, 0.004, BRASS_LT, rot=Y90, major_segs=64, minor_segs=6)
text_mesh('SIC PARVIS', C + Vector((0, -0.018, 0.075)), 0.1, BRASS_LT, extrude=0.004)
text_mesh('MAGNA', C + Vector((0, -0.018, -0.06)), 0.1, BRASS_LT, extrude=0.004)
for zz in (0.17, -0.16):  # engraved divider rules with a small diamond
    kit.box(C + Vector((0, -0.016, zz)), (0.34, 0.006, 0.008), BRASS_LT)
    kit.box(C + Vector((0, -0.017, zz)), (0.035, 0.008, 0.035), BRASS_LT, rot=(0, math.pi / 4, 0))

LEAN = math.radians(48)
bpy.context.view_layer.update()
T = Matrix.Translation(H) @ Matrix.Rotation(-LEAN, 4, 'X') @ Matrix.Translation(-H)
for o in set(bpy.context.scene.objects) - before:
    o.matrix_world = T @ o.matrix_world

# report where the dial centre lands after normalisation (the site overlays the needle there)
_dg = bpy.context.evaluated_depsgraph_get()
_pts = [o.matrix_world @ v.co for o in bpy.context.scene.objects if o.type == 'MESH'
        for v in o.evaluated_get(_dg).to_mesh().vertices]
_lo = Vector([min(p[i] for p in _pts) for i in range(3)])
_hi = Vector([max(p[i] for p in _pts) for i in range(3)])
_k = 1.0 / max(_hi - _lo)
print('[kit] compass dial centre (normalised):', tuple(round(c, 4) for c in (-(_lo + _hi) / 2 * _k)),
      'dial radius:', round(0.44 * _k, 4))

kit.finalize_prop('compass', thumb_angle=0, elevation=0.15)
