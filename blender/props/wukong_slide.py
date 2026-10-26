"""Chibi Destined One sliding down a vertical pole (the site draws the Jingu Bang behind him).

Both fists grip an imaginary pole on x = 0 and the ankles hook around it; the body hangs off to
the figure's left, the tail curls out the other side (its x-reach is solved so the bbox is
symmetric about x = 0, i.e. the pole line is the sprite's vertical centre line) and the plumes
stream upward.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
import _mini as M  # noqa: E402
from mathutils import Matrix, Vector as V  # noqa: E402

kit.reset()
M.palette()

Y_POLE = -0.2           # depth of the imaginary pole (just in front of the body's side)
ARM = (0.37, 0.35)      # long monkey arms for this pose

body = Matrix.Translation((0.17, 0.0, 0.1)) @ Matrix.Rotation(0.2, 4, 'Y') @ Matrix.Rotation(-0.35, 4, 'Z')
head = (Matrix.Translation(M.tf(body, (0, 0, 1.6))) @ Matrix.Rotation(-0.12, 4, 'Y') @
        Matrix.Rotation(0.3, 4, 'Z') @ Matrix.Rotation(-0.06, 4, 'X'))

with M.Group(body):
    M.wk_torso()
    M.wk_skirt(front_len=0.22, flare=0.55, side_flare=0.7)
with M.Group(head):
    socks = M.wk_head('grin')
socks = [M.tf(head, s) for s in socks]

# fists on the pole: upper = his right hand beside the head, lower = left hand reaching across
HAND_HI = V((0, Y_POLE - 0.05, 1.78))
HAND_LO = V((0, Y_POLE - 0.08, 1.3))
M.wk_arm(M.tf(body, (-0.25, 0, 1.06)), HAND_HI, hint=(0.2, 0.3, -1), grip_axis=(0, 0, 1),
         pauldron_up=(-0.8, 0, 1), lengths=ARM)
M.wk_arm(M.tf(body, (0.25, 0, 1.06)), HAND_LO, hint=(0.4, -0.6, -1), grip_axis=(0, 0, 1),
         pauldron_up=(0.6, 0, 1), lengths=ARM)

# legs wrapped round the pole (a diamond the staff shows through): right knee crosses in front to
# the far side, left knee juts out; ankles cross on x = 0
LEG = (0.35, 0.33)
M.wk_leg(M.tf(body, (-0.13, 0, 0.6)), (-0.03, Y_POLE + 0.0, 0.3), hint=(-1, -0.8, 0.5), foot_dir=(0.7, 0.2, -0.7),
         lengths=LEG)
M.wk_leg(M.tf(body, (0.13, 0, 0.6)), (0.06, Y_POLE + 0.14, 0.04), hint=(1, -0.5, 0.2), foot_dir=(-1, 0.2, -0.3),
         lengths=LEG)

# plumes stream upward (he's moving down) and drift away from the pole
for s, sx in zip(socks, (1, -1)):
    g = [s, s + V((0.02 * sx, 0.03, 0.2)), s + V((0.06 + 0.03 * sx, 0.08, 0.42)),
         s + V((0.15 + 0.04 * sx, 0.12, 0.6)), s + V((0.22 + 0.03 * sx, 0.15, 0.74))]
    M.banded_tube(g, 0.042, 0.014, M.PLUMES, bands=10)

# tail curls out on the pole side; its x-reach is solved so the bbox is symmetric about the pole line
lo, hi = M.bounds_x()
root = M.tf(body, (0, 0.17, 0.62))
tail_pts = [root, root + V((-0.08, 0.12, -0.16)), V((-0.15, 0.3, 0.3)), V((-0.45, 0.2, 0.32)),
            V((-0.66, 0.05, 0.5)), V((-0.66, -0.04, 0.76)), V((-0.5, -0.06, 0.84)), V((-0.42, -0.05, 0.74))]
before = set(bpy.context.scene.objects)
M.wk_tail(tail_pts)
tail_objs = [o for o in bpy.context.scene.objects if o not in before]
lo2, _ = M.bounds_x()
k = (root.x + hi) / (root.x - lo2)          # stretch about the root so the tail's far edge lands on -hi
bpy.context.view_layer.update()
S = Matrix.Translation((root.x, 0, 0)) @ Matrix.Diagonal((k, 1, 1, 1)) @ Matrix.Translation((-root.x, 0, 0))
for o in tail_objs:
    o.matrix_world = S @ o.matrix_world
lo3, hi3 = M.bounds_x()
print(f'[kit] slide bbox x: {lo3:.3f} .. {hi3:.3f} (tail x-scale {k:.2f}); fists z {HAND_LO.z} / {HAND_HI.z}')

M.tri_report()
LO, HI = M.bounds()
kit.finalize_prop('wukong_slide', thumb_angle=0)

if not os.environ.get('KIT_VIEW'):
    # where the grip line lands in the 512² sprite (the site aligns the staff to it)
    pts = [V((0, Y_POLE, LO.z)), V((0, Y_POLE, HI.z)), HAND_HI + V((0, 0, 0.095)), HAND_HI, HAND_LO,
           HAND_LO - V((0, 0, 0.095))]
    px = M.sprite_px(pts, LO, HI)
    print('[kit] pole line px: x %.1f..%.1f' % (px[0][0], px[1][0]))
    print('[kit] fists px: upper centre (%.1f, %.1f) top y %.1f; lower centre (%.1f, %.1f) bottom y %.1f'
          % (px[3][0], px[3][1], px[2][1], px[4][0], px[4][1], px[5][1]))
