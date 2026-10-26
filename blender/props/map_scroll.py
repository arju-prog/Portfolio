"""Old treasure map: partly unrolled parchment between two rolled ends, inked island,
red dashed path and a raised red X, compass rose and a wax seal."""
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
random.seed(11)

PARCH = kit.mat('#dfbd7e', 0.9)
PARCH_DK = kit.mat('#9c6a32', 0.9)
PARCH_ROLL = kit.mat('#cfa86a', 0.9)
INK = kit.mat('#4a2f1a', 0.7)
LAND = kit.mat('#b99550', 0.9)
RED = kit.mat('#c0261c', 0.45)
WAX = kit.mat('#9e1a14', 0.35)
WAX_LT = kit.mat('#c4372b', 0.3)

HW, HH = 0.5, 0.3          # half width / half height of the open sheet
R_L, R_R = 0.095, 0.08    # roll radii


def sheet_y(x):
    """Gentle wave of the parchment surface (front face is -Y)."""
    return 0.025 * math.sin((x + HW) / (2 * HW) * math.pi * 2.0) - 0.012 * math.cos(x * 3.0)


def on_sheet(x, z, lift=0.007):
    return Vector((x, sheet_y(x) - lift, z))


def edge_noise(x, k):
    return 0.012 * math.sin(x * 23 + k) + 0.008 * math.sin(x * 57 + 2 * k)


# ── sheet (grid with ragged top/bottom edges, burnt rim, solidified) ─────
nx, nz = 40, 16
bm = bmesh.new()
grid = []
for i in range(nx + 1):
    x = -HW + 2 * HW * i / nx
    top = HH + edge_noise(x, 1.0)
    bot = -HH + edge_noise(x, 4.0)
    grid.append([bm.verts.new((x, sheet_y(x), bot + (top - bot) * j / nz)) for j in range(nz + 1)])
for i in range(nx):
    for j in range(nz):
        f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        edge = j in (0, nz - 1)
        f.material_index = 1 if edge else 0
        f.smooth = True
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('sheet')
bm.to_mesh(me)
bm.free()
sheet = bpy.data.objects.new('sheet', me)
bpy.context.scene.collection.objects.link(sheet)
me.materials.append(PARCH)
me.materials.append(PARCH_DK)
sol = sheet.modifiers.new('solid', 'SOLIDIFY')
sol.thickness = 0.006
sol.offset = 0.0


# ── rolled ends ──────────────────────────────────────────────────────────
def roll(cx, r, sign):
    """Rolled parchment along Z at x=cx; sheet joins its front tangent. sign=-1 left, +1 right."""
    cy = sheet_y(cx) + r
    kit.cylinder((cx + sign * 0.0, cy, 0), r, 2 * HH + 0.02, PARCH_ROLL, verts=32)
    for zs in (-1, 1):
        z = zs * (HH + 0.011)
        kit.cylinder((cx, cy, z), r * 0.98, 0.004, PARCH, verts=32)
        # spiral of rolled layers on the end cap
        pts = []
        turns = 3.2
        for k in range(32):
            t = k / 31
            a = t * turns * 2 * math.pi
            rr = r * (0.12 + 0.82 * t)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, z + zs * 0.003))
        kit.tube(pts, 0.0035, INK, resolution=1, name='spiral')
    # slight darker band where the roll wraps (age)
    for zz in (-HH + 0.02, HH - 0.02):
        kit.cylinder((cx, cy, zz), r + 0.002, 0.03, PARCH_DK, verts=32)
    return cy


roll(-HW, R_L, -1)
roll(HW, R_R, 1)

# ── map art ──────────────────────────────────────────────────────────────
# island: filled land + inked coastline
IC = (0.06, -0.01)


def island_pt(t):
    a = t * 2 * math.pi
    k = 1 + 0.16 * math.sin(3 * a + 0.4) + 0.09 * math.cos(5 * a + 1.0) + 0.05 * math.sin(9 * a)
    return IC[0] + math.cos(a) * 0.3 * k, IC[1] + math.sin(a) * 0.17 * k


ring = [island_pt(k / 64) for k in range(64)]
bm = bmesh.new()
c = bm.verts.new(on_sheet(IC[0], IC[1], 0.0045))
rings_v = []
for q in (0.2, 0.4, 0.6, 0.8, 1.0):   # concentric rings so the patch follows the sheet's wave
    rings_v.append([bm.verts.new(on_sheet(IC[0] + (x - IC[0]) * q, IC[1] + (z - IC[1]) * q, 0.0045)) for x, z in ring])
for k in range(64):
    bm.faces.new((c, rings_v[0][k], rings_v[0][(k + 1) % 64]))
for a, b in zip(rings_v, rings_v[1:]):
    for k in range(64):
        bm.faces.new((a[k], b[k], b[(k + 1) % 64], a[(k + 1) % 64]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('land')
bm.to_mesh(me)
bm.free()
land = bpy.data.objects.new('land', me)
bpy.context.scene.collection.objects.link(land)
me.materials.append(LAND)
coast = [on_sheet(x, z, 0.007) for x, z in ring] + [on_sheet(*ring[0], 0.007)]
kit.tube(coast, 0.006, INK, resolution=1, name='coast')
# mountains (ink chevrons) and a palm
for (x, z, s) in ((-0.06, 0.05, 0.05), (0.02, 0.07, 0.065), (0.1, 0.04, 0.045)):
    kit.tube([on_sheet(x - s, z - s * 0.5), on_sheet(x, z + s * 0.6), on_sheet(x + s, z - s * 0.5)], 0.005, INK,
             smooth_path=False, resolution=1, name='mtn')
px, pz = 0.28, -0.06
kit.tube([on_sheet(px, pz - 0.06), on_sheet(px + 0.01, pz), on_sheet(px + 0.005, pz + 0.05)], 0.005, INK,
         resolution=3, name='trunk')
for a in (-2.6, -1.9, -0.5, 0.3):
    kit.tube([on_sheet(px + 0.005, pz + 0.05), on_sheet(px + 0.005 + math.cos(a) * 0.035, pz + 0.07 + math.sin(a) * 0.01),
              on_sheet(px + 0.005 + math.cos(a) * 0.06, pz + 0.04 + math.sin(a) * 0.02)], 0.004, INK,
             resolution=3, name='frond')

# sea waves
for (x, z) in ((-0.36, 0.08), (-0.3, -0.05), (0.36, 0.16), (-0.18, -0.24), (0.42, 0.02)):
    kit.tube([on_sheet(x + dx * 0.02, z + 0.008 * math.sin(dx * 1.6)) for dx in range(4)], 0.0035, INK,
             resolution=3, name='wave')

# compass rose (ink star) in the top-left corner
CR = (-0.33, 0.19)
for k in range(8):
    a = k * math.pi / 4
    L = 0.06 if k % 2 == 0 else 0.035
    kit.tube([on_sheet(CR[0], CR[1]), on_sheet(CR[0] + math.cos(a) * L, CR[1] + math.sin(a) * L)], 0.004, INK,
             smooth_path=False, resolution=1, taper_to=0.2, name='rose')
kit.tube([on_sheet(CR[0] + math.cos(a / 16 * 2 * math.pi) * 0.025, CR[1] + math.sin(a / 16 * 2 * math.pi) * 0.025)
          for a in range(17)], 0.003, INK, resolution=2, name='rosering')

# red dashed path from the ship landing (left) to the X
path = [(-0.4, -0.2), (-0.28, -0.24), (-0.17, -0.17), (-0.13, -0.06), (-0.02, -0.07), (0.08, -0.12),
        (0.17, -0.05), (0.18, 0.04)]
pts = [Vector(p) for p in path]
dense = []
for i in range(len(pts) - 1):  # catmull-rom
    p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
    for s in range(10):
        t = s / 10
        dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                            + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
dense.append(pts[-1])
acc, draw, seg = 0.0, True, []
for i in range(1, len(dense)):
    d = (dense[i] - dense[i - 1]).length
    acc += d
    if draw:
        seg.append(dense[i - 1])
    if acc > (0.03 if draw else 0.018):
        if draw and seg:
            seg.append(dense[i])
            kit.tube([on_sheet(p.x, p.y, 0.009) for p in seg], 0.0075, RED, resolution=2, name='dash')
        seg, acc, draw = [], 0.0, not draw
# the X
XC = (0.2, 0.08)
for a in (math.pi / 4, -math.pi / 4):
    d = Vector((math.cos(a), math.sin(a))) * 0.068
    kit.tube([on_sheet(XC[0] - d.x, XC[1] - d.y, 0.02), on_sheet(XC[0] + d.x, XC[1] + d.y, 0.02)], 0.016, RED,
             smooth_path=False, resolution=1, name='x')

# wax seal on the bottom-right corner
SC = on_sheet(0.4, -0.22, 0.012)
kit.cylinder(SC, 0.05, 0.016, WAX, rot=(math.pi / 2, 0, 0), verts=20, scale=(1.05, 0.95, 1))
for k in range(7):
    a = k * 2 * math.pi / 7 + 0.3
    kit.sphere(SC + Vector((math.cos(a) * 0.05, 0, math.sin(a) * 0.05)), (0.016, 0.008, 0.014), WAX, segs=10, rings=5)
kit.cylinder(SC + Vector((0, -0.009, 0)), 0.03, 0.006, WAX_LT, rot=(math.pi / 2, 0, 0), verts=20)
kit.box(SC + Vector((0, -0.013, 0)), (0.008, 0.004, 0.03), WAX)
kit.box(SC + Vector((0, -0.013, 0)), (0.03, 0.004, 0.008), WAX)

# tilt back a little so the sheet faces the elevated sprite camera
bpy.context.view_layer.update()
R = Matrix.Rotation(math.radians(-14), 4, 'X') @ Matrix.Rotation(math.radians(6), 4, 'Z')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = R @ o.matrix_world

kit.finalize_prop('map_scroll')
