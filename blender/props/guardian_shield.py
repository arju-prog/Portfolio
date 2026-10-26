"""Kratos' Guardian Shield — round wooden shield with a steel rim, central boss, rune band and rivets."""
import math
import os
import random
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import box, cylinder, mat, sphere, torus  # noqa: E402

kit.reset()
random.seed(7)

STEEL = mat('#b9c0c8', 0.28, metal=0.95)
STEEL_D = mat('#5d646d', 0.4, metal=0.9)
IRON = mat('#41464e', 0.55, metal=0.75)
RUNE = mat('#e8d9a8', 0.45, metal=0.55)
BRASS = mat('#c79a45', 0.3, metal=0.9)
WOODS = [mat('#7a4626', 0.75), mat('#6a3b1e', 0.78), mat('#84502e', 0.72), mat('#5e341a', 0.8)]

R = 0.5           # outer radius
T = 0.06          # wood thickness
FRONT = -T / 2    # y of the wooden face
FACE = (math.pi / 2, 0, 0)   # rotation that turns a Z-axis primitive to face -Y


def plank(x0, x1, m):
    """A vertical wooden plank: the slice x0..x1 of the wooden disc."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R - 0.03, depth=T, rotation=FACE)
    obj = bpy.context.active_object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for co, no in (((x0, 0, 0), (-1, 0, 0)), ((x1, 0, 0), (1, 0, 0))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.append(m)
    mod = obj.modifiers.new('bevel', 'BEVEL')
    mod.width = 0.004
    mod.segments = 2
    mod.limit_method = 'ANGLE'
    return obj


# ── wooden planks (slightly different tones, tiny gaps) ──
edges = [-R + 0.03 + i * (2 * (R - 0.03) / 6) for i in range(7)]
for i in range(6):
    plank(edges[i] + 0.003, edges[i + 1] - 0.003, WOODS[i % len(WOODS)])
cylinder((0, T * 0.1, 0), R - 0.035, T * 0.7, mat('#2a170b', 0.9), rot=FACE, verts=64)  # dark backing fills the gaps

# ── steel rim ──
torus((0, 0, 0), R - 0.025, 0.04, STEEL, rot=FACE, major_segs=72, minor_segs=12, scale=(1, 1, 1))
torus((0, FRONT, 0), R - 0.075, 0.012, STEEL_D, rot=FACE, major_segs=64, minor_segs=8)
for i in range(20):  # rivets around the rim
    a = i / 20 * math.tau
    sphere((math.cos(a) * (R - 0.025), -0.04, math.sin(a) * (R - 0.025)), 0.014, BRASS, segs=12, rings=6)

# ── four steel straps from the boss to the rim, with rivets ──
for k in range(4):
    a = math.pi / 4 + k * math.pi / 2
    mid = 0.29
    box((math.cos(a) * mid, FRONT - 0.006, math.sin(a) * mid), (0.05, 0.014, 0.33), STEEL_D,
        rot=(0, math.pi / 2 - a, 0), bevel=0.004)
    for rr in (0.2, 0.39):
        sphere((math.cos(a) * rr, FRONT - 0.014, math.sin(a) * rr), 0.012, BRASS, segs=12, rings=6)

# ── rune band: dark iron ring carved with raised steel runes ──
RB = 0.29
torus((0, FRONT - 0.004, 0), RB, 0.045, IRON, rot=FACE, major_segs=72, minor_segs=10, scale=(1, 1, 0.25))
torus((0, FRONT - 0.008, 0), RB + 0.048, 0.007, STEEL, rot=FACE, major_segs=72, minor_segs=6)
torus((0, FRONT - 0.008, 0), RB - 0.048, 0.007, STEEL, rot=FACE, major_segs=72, minor_segs=6)

RUNES = [  # strokes in a unit rune cell: (u0, v0, u1, v1), u across, v up (radial)
    [(0, -1, 0, 1), (0, 1, 0.6, 0.4), (0, 0.3, 0.6, -0.3)],     # ᚠ-ish
    [(0, -1, 0, 1), (0, 1, 0.6, 0.0), (0.6, 0.0, 0, -0.3)],     # ᚱ-ish
    [(0, -1, 0, 1), (-0.6, 0.6, 0.6, -0.6)],                    # ᚾ-ish
    [(-0.5, -1, 0.5, 1), (0.5, -1, -0.5, 1)],                   # X
    [(0, -1, 0, 1), (-0.6, 1, 0, 0.4), (0.6, 1, 0, 0.4)],       # ᛉ-ish
    [(-0.4, -1, -0.4, 1), (0.4, -1, 0.4, 1), (-0.4, 1, 0.4, 0.2), (0.4, 1, -0.4, 0.2)],  # ᛗ-ish
    [(0, -1, 0, 1), (0, 0.9, 0.55, 0.45), (0, 0.4, 0.55, -0.05)],
    [(0, -1, 0, 1), (0, 0, 0.6, -0.6), (0, 0, 0.6, 0.6)],
]
N_RUNES = 18
for i in range(N_RUNES):
    th = i / N_RUNES * math.tau + 0.09
    n = (math.cos(th), math.sin(th))        # radial (rune "up")
    t = (math.sin(th), -math.cos(th))       # tangent (rune "right", reads clockwise)
    cu = (n[0] * RB, n[1] * RB)
    for u0, v0, u1, v1 in random.choice(RUNES):
        hs, ws = 0.026, 0.026
        p0 = (cu[0] + t[0] * u0 * ws + n[0] * v0 * hs, cu[1] + t[1] * u0 * ws + n[1] * v0 * hs)
        p1 = (cu[0] + t[0] * u1 * ws + n[0] * v1 * hs, cu[1] + t[1] * u1 * ws + n[1] * v1 * hs)
        dx, dz = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(dx, dz)
        box(((p0[0] + p1[0]) / 2, FRONT - 0.016, (p0[1] + p1[1]) / 2), (0.008, 0.008, ln + 0.006), RUNE,
            rot=(0, math.atan2(dx, dz), 0))

# ── central boss ──
cylinder((0, FRONT - 0.01, 0), 0.16, 0.02, STEEL_D, rot=FACE, verts=48)
torus((0, FRONT - 0.02, 0), 0.155, 0.012, STEEL, rot=FACE, major_segs=48, minor_segs=8)
sphere((0, FRONT - 0.02, 0), (0.125, 0.085, 0.125), STEEL, segs=40, rings=20)
torus((0, FRONT - 0.03, 0), 0.118, 0.008, STEEL_D, rot=FACE, major_segs=48, minor_segs=6)
for i in range(8):
    a = i / 8 * math.tau + math.pi / 8
    sphere((math.cos(a) * 0.142, FRONT - 0.026, math.sin(a) * 0.142), 0.011, BRASS, segs=10, rings=6)
sphere((0, FRONT - 0.1, 0), 0.025, BRASS, segs=16, rings=8)  # boss cap

# ── back: grip bar ──
box((0, T / 2 + 0.03, 0), (0.3, 0.03, 0.04), STEEL_D, bevel=0.006)
cylinder((0, T / 2 + 0.06, 0), 0.02, 0.2, mat('#4a2c18', 0.85), rot=(0, math.pi / 2, 0), verts=16)

kit.finalize_prop('guardian_shield')
