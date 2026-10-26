"""Deku's "Hero Analysis for the Future No.13" notebook (My Hero Academia) — worn, singed spiral notebook,
big raised "13", fanning pages and a pencil resting on the cover."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402

import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402


def objs():
    return set(o for o in bpy.context.scene.objects if o.type == 'MESH')


def transform(objects, M):
    bpy.context.view_layer.update()
    for o in objects:
        o.matrix_world = M @ o.matrix_world


kit.reset()
random.seed(13)
COVER = kit.mat('#b5864a', 0.9)
COVER_E = kit.mat('#8f6634', 0.9)
for _m in (COVER, COVER_E):
    _m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.2
INK = kit.mat('#4a2c17', 0.7)
LABEL = kit.mat('#f1e8d2', 0.85)
TEXT = kit.mat('#3a3a40', 0.8)
PAGE = kit.mat('#f7f3e8', 0.9)
PAGE_L = kit.mat('#9fb7d6', 0.9)
SPIRAL = kit.mat('#b9bec6', 0.25, metal=1.0)
CHAR = kit.mat('#2a1a10', 0.95)
SINGE = kit.mat('#6b4423', 0.95)
YELLOW = kit.mat('#f2bf1f', 0.5)
WOOD = kit.mat('#e6c08e', 0.8)
LEAD = kit.mat('#2b2b30', 0.4, metal=0.3)
FERRULE = kit.mat('#c9ccd2', 0.25, metal=1.0)
ERASER = kit.mat('#ec8a9c', 0.8)

W, D = 0.6, 0.8                 # notebook width (x) and height (y), lying flat, cover facing +Z
X0 = -W / 2
BACK_T, BLOCK_T, COVER_T = 0.012, 0.055, 0.012
ZB = BACK_T + BLOCK_T           # top of page block

# ── back cover + page block (with ruled fore-edge hints) ──
kit.box((0, 0, BACK_T / 2), (W, D, BACK_T), COVER_E, bevel=0.003)
kit.box((0.008, 0, BACK_T + BLOCK_T / 2), (W - 0.03, D - 0.02, BLOCK_T), PAGE, bevel=0.003)
for i in range(4):
    z = BACK_T + 0.01 + i * 0.012
    kit.box((W / 2 - 0.006, 0, z), (0.004, D - 0.03, 0.003), PAGE_L)

# ── fanning loose pages between block and cover (hinged at the spine) ──
hinge = Vector((X0 + 0.02, 0, ZB))
for i, ang in enumerate((2.0, 4.0, 6.5)):
    before = objs()
    kit.box((0.008, -0.004 * i, ZB + 0.002), (W - 0.035, D - 0.03 - 0.01 * i, 0.003), PAGE)
    for k in range(5):
        kit.box((0.02, -0.25 + k * 0.1, ZB + 0.0037), (W - 0.12, 0.0035, 0.0006), PAGE_L)
    M = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-ang), 4, 'Y') @ Matrix.Translation(-hinge)
    transform(objs() - before, M)

# ── front cover group (cover, label, "13", singe marks, pencil) ──
before = objs()
CZ = ZB + COVER_T / 2 + 0.006
TOP = CZ + COVER_T / 2
kit.box((0, 0, CZ), (W, D, COVER_T), COVER, bevel=0.004)
# label with title lines
kit.box((0.04, 0.25, TOP + 0.002), (0.42, 0.15, 0.004), LABEL, bevel=0.002)
for k, (w, x) in enumerate(((0.3, 0.02), (0.34, 0.04), (0.22, -0.02))):
    kit.box((x, 0.29 - k * 0.04, TOP + 0.0045), (w, 0.014, 0.002), TEXT)
# big raised "13"
S = 0.008                       # stroke half-thickness
NZ = TOP + 0.006


def stroke(a, b):
    kit.rod((a[0], a[1], NZ), (b[0], b[1], NZ), S * 1.6, INK, verts=10)


one_x = -0.1
stroke((one_x, 0.09), (one_x, -0.14))
stroke((one_x, 0.09), (one_x - 0.05, 0.05))
stroke((one_x - 0.04, -0.14), (one_x + 0.04, -0.14))
t3x = 0.03
stroke((t3x, 0.09), (t3x + 0.1, 0.09))
stroke((t3x + 0.1, 0.09), (t3x + 0.13, 0.06))
stroke((t3x + 0.13, 0.06), (t3x + 0.13, -0.0))
stroke((t3x + 0.13, -0.0), (t3x + 0.1, -0.025))
stroke((t3x + 0.04, -0.025), (t3x + 0.1, -0.025))
stroke((t3x + 0.1, -0.025), (t3x + 0.13, -0.05))
stroke((t3x + 0.13, -0.05), (t3x + 0.13, -0.11))
stroke((t3x + 0.13, -0.11), (t3x + 0.1, -0.14))
stroke((t3x + 0.1, -0.14), (t3x, -0.14))
# singe marks: charred clusters on two corners and along the bottom edge
for cx, cy, k in ((W / 2 - 0.03, -D / 2 + 0.04, 9), (W / 2 - 0.05, D / 2 - 0.03, 6), (-0.05, -D / 2 + 0.02, 5)):
    for _ in range(k):
        x = cx + random.uniform(-0.06, 0.03)
        y = cy + random.uniform(-0.03, 0.05) * (1 if cy < 0 else -1)
        r = random.uniform(0.015, 0.035)
        kit.sphere((x, y, TOP - 0.0012), (r * 1.3, r, 0.0018), SINGE, rot=(0, 0, random.uniform(0, 3)), segs=12, rings=4)
        kit.sphere((x, y, TOP - 0.0004), (r * 0.7, r * 0.55, 0.0018), CHAR, rot=(0, 0, random.uniform(0, 3)), segs=10, rings=4)
# pencil resting diagonally across the lower cover
PR = 0.02
a = Vector((-0.24, -0.34, TOP + PR))
b = Vector((0.4, -0.2, TOP + PR))
d = (b - a).normalized()
L = (b - a).length
rot = kit.rot_between(a, b)
body_a, body_b = a + d * 0.07, b - d * 0.07
kit.cylinder((body_a + body_b) / 2, PR, (body_b - body_a).length, YELLOW, rot=rot, verts=6, smooth=False)
kit.cylinder(a + d * 0.05, PR * 1.02, 0.04, FERRULE, rot=rot, verts=16)
for k in (0.037, 0.063):
    kit.torus(a + d * k, PR * 1.03, 0.003, FERRULE, rot=rot, major_segs=16, minor_segs=4)
kit.cylinder(a + d * 0.015, PR * 0.95, 0.03, ERASER, rot=rot, verts=16)
kit.sphere(a, PR * 0.95, ERASER, segs=16, rings=8)
kit.cone(b - d * 0.035, PR, PR * 0.3, 0.07, WOOD, rot=rot, verts=16)
kit.cone(b - d * 0.0, PR * 0.3, 0.0, 0.014, LEAD, rot=rot, verts=12)
# tilt the cover open a little around the spine
M = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(-8.5), 4, 'Y') @ Matrix.Translation(-hinge)
transform(objs() - before, M)

# ── spiral coils along the spine ──
n = 15
for i in range(n):
    y = -D / 2 + 0.04 + i * (D - 0.08) / (n - 1)
    kit.torus((X0 + 0.012, y, ZB / 2 + 0.008), 0.05, 0.0065, SPIRAL, rot=(math.pi / 2, 0.25, 0),
              major_segs=24, minor_segs=6, scale=(0.75, 1, 1))

# pose: stand it up facing the camera, tilted back a little
transform(objs(), Matrix(Euler((math.radians(64), 0, math.radians(-8))).to_matrix().to_4x4()))
kit.finalize_prop('hero_notebook')
