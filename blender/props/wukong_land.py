"""Chibi Destined One landing: crouched superhero landing on one knee, right fist planted on the
ground, left arm flung out, plumes bouncing in springy arcs, tail up. Ground is z = 0 (the site
adds the dust)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
import _mini as M  # noqa: E402
from mathutils import Matrix, Vector as V  # noqa: E402

kit.reset()
M.palette()

ARM = (0.34, 0.32)
LEAN = 0.55
PELVIS = V((0.02, 0.06, 0.3))
body = (Matrix.Translation(PELVIS) @ Matrix.Rotation(0.12, 4, 'Z') @ Matrix.Rotation(LEAN, 4, 'X') @
        Matrix.Translation((0, 0, -0.64)))
# head stays fairly level, chin tucked: glaring up from under the brows
head = (Matrix.Translation(M.tf(body, (0, 0.02, 1.58))) @ Matrix.Rotation(0.2, 4, 'Z') @
        Matrix.Rotation(-LEAN + 0.2, 4, 'X') @ Matrix.Rotation(-0.1, 4, 'Y'))

with M.Group(body):
    M.wk_torso()
    M.wk_skirt(front_len=0.24, flare=0.25, side_flare=0.6)
with M.Group(head):
    socks = M.wk_head('grin')
socks = [M.tf(head, s) for s in socks]

# right fist punched into the ground out to the side, left arm flung out and back for balance
M.wk_arm(M.tf(body, (-0.25, 0, 1.06)), (-0.5, -0.36, 0.09), hint=(-0.4, 0.6, 0.3), fist_dir=(0, -0.1, -1),
         pauldron_up=(-0.7, 0, 1), lengths=ARM)
M.wk_arm(M.tf(body, (0.25, 0, 1.06)), (0.78, 0.32, 0.58), hint=(0.2, -0.2, 1), fist_dir=(1, 0.4, -0.3),
         pauldron_up=(0.6, 0, 1), lengths=ARM)

# left foot planted forward and out (knee up), right knee down on the ground with the shin trailing back
M.wk_leg(M.tf(body, (0.13, 0, 0.6)), (0.34, -0.34, 0.09), hint=(0.6, -0.4, 1), foot_dir=(0.25, -1, 0))
M.wk_leg(M.tf(body, (-0.13, 0, 0.6)), (-0.3, 0.36, 0.1), hint=(-0.3, -0.4, -1), foot_dir=(0, 1, -0.6))

# plumes bounce: springy arcs out to the sides, drooping at the tips
for s, sx in zip(socks, (1, -1)):
    g = [s, s + V((0.03 * sx, 0.0, 0.22)), s + V((0.12 * sx, 0.1, 0.42)), s + V((0.26 * sx, 0.22, 0.5)),
         s + V((0.4 * sx, 0.32, 0.42)), s + V((0.48 * sx, 0.36, 0.26))]
    M.banded_tube(g, 0.042, 0.014, M.PLUMES, bands=10)

# tail whips up on the open side in a question-mark curl
root = M.tf(body, (0, 0.17, 0.62))
M.wk_tail([root, root + V((-0.08, 0.16, -0.02)), V((-0.36, 0.5, 0.3)), V((-0.7, 0.5, 0.56)),
           V((-0.86, 0.4, 0.92)), V((-0.8, 0.3, 1.2)), V((-0.62, 0.26, 1.26)), V((-0.56, 0.26, 1.12))])

M.tri_report()
kit.finalize_prop('wukong_land', thumb_angle=-15)
