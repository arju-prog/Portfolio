"""
Shared Blender toolkit for the character collection.

Every character script builds a stylised chibi figurine out of primitives,
then calls `finalize(id)` which normalises it (feet at origin, 2 units tall),
exports `public/models/<id>.glb` and renders `public/models/<id>.png`.

Run one:   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/characters/<id>.py
Run all:   pnpm models
"""
import math
import os

import bpy
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT, 'public', 'models')
PROPS_DIR = os.path.join(ROOT, 'public', 'props')
TARGET_HEIGHT = 2.0

_MATS = {}


# ── Scene ────────────────────────────────────────────────────────────────

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(hex_color):
    h = hex_color.lstrip('#')
    return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


def mat(hex_color, rough=0.55, metal=0.0, emit=0.0):
    """Cached Principled material. Colours are sRGB hex, e.g. '#ff8800'."""
    key = (hex_color.lower(), rough, metal, emit)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(f"m_{hex_color.strip('#')}_{len(_MATS)}")
    if hasattr(m, 'use_nodes') and not m.use_nodes:
        m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    color = rgba(hex_color)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        bsdf.inputs['Emission Color'].default_value = color
        bsdf.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = color
    _MATS[key] = m
    return m


# ── Primitives ───────────────────────────────────────────────────────────
# All take a material from `mat()`. Rotations are Euler radians (x, y, z).

def _finish(obj, material, smooth=True, name=None):
    if name:
        obj.name = name
    if material is not None:
        obj.data.materials.append(material)
    if smooth:
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def sphere(loc, scale, m, rot=(0, 0, 0), segs=32, rings=16, name=None):
    """Ellipsoid. `scale` is radii (x, y, z) or a single radius."""
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.scale = scale
    return _finish(obj, m, True, name)


def box(loc, size, m, rot=(0, 0, 0), bevel=0.0, name=None):
    """Box with full dimensions `size` (x, y, z); optional rounded edges."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.scale = size
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
    return _finish(obj, m, bool(bevel), name)


def cylinder(loc, radius, depth, m, rot=(0, 0, 0), verts=32, scale=None, smooth=True, name=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    if scale:
        obj.scale = scale
    return _finish(obj, m, smooth, name)


def cone(loc, r1, r2, depth, m, rot=(0, 0, 0), verts=32, smooth=True, name=None):
    """r1 = bottom radius, r2 = top radius (0 for a point)."""
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    return _finish(bpy.context.active_object, m, smooth, name)


def torus(loc, major, minor, m, rot=(0, 0, 0), major_segs=48, minor_segs=12, scale=None, name=None):
    bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot, major_radius=major, minor_radius=minor,
                                     major_segments=major_segs, minor_segments=minor_segs)
    obj = bpy.context.active_object
    if scale:
        obj.scale = scale
    return _finish(obj, m, True, name)


def rot_between(a, b):
    """Euler rotation that points local +Z from a towards b."""
    return Vector((0, 0, 1)).rotation_difference(Vector(b) - Vector(a)).to_euler()


def rod(a, b, radius, m, verts=24, caps=True, r2=None, name=None):
    """Cylinder (or tapered cone if r2 given) from point a to point b; rounded caps by default."""
    a, b = Vector(a), Vector(b)
    mid = (a + b) / 2
    length = (b - a).length
    rot = rot_between(a, b)
    if r2 is None:
        obj = cylinder(mid, radius, length, m, rot=rot, verts=verts, name=name)
    else:
        obj = cone(mid, radius, r2, length, m, rot=rot, verts=verts, name=name)
    if caps:
        sphere(a, radius, m, segs=verts, rings=max(8, verts // 2))
        sphere(b, r2 if r2 is not None else radius, m, segs=verts, rings=max(8, verts // 2))
    return obj


def tube(points, radius, m, taper_to=None, resolution=12, smooth_path=True, name='tube'):
    """Smooth tube along a list of points (hair strands, cloth folds, ropes, tails...).
    `taper_to` linearly scales the radius towards the end (e.g. 0.1 for a pointy spike)."""
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    curve.resolution_u = resolution
    curve.use_fill_caps = True
    if smooth_path:
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(len(points) - 1)
        for i, p in enumerate(points):
            bp = spline.bezier_points[i]
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = 'AUTO'
            if taper_to is not None:
                bp.radius = 1 + (taper_to - 1) * (i / max(1, len(points) - 1))
    else:
        spline = curve.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for i, p in enumerate(points):
            spline.points[i].co = (*p, 1)
            if taper_to is not None:
                spline.points[i].radius = 1 + (taper_to - 1) * (i / max(1, len(points) - 1))
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.active_object
    return _finish(obj, m, True, None)


def spike(base, tip, radius, m, verts=16):
    """Cone from base point to tip point — hair spikes, horns, blades, claws."""
    return rod(base, tip, radius, m, verts=verts, caps=False, r2=0.0)


def mirror_x(fn):
    """Call fn(sign) for sign in (+1, -1) — build symmetric parts once."""
    return [fn(s) for s in (1, -1)]


# ── Chibi figure base ────────────────────────────────────────────────────

def chibi(skin='#f2c9a0', top='#ffffff', bottom='#333333', shoes='#222222', hands=None,
          eyes='#1a1a1a', iris=None, sleeves='short', pants='long', mouth='smile', brows=None,
          right_arm='down', left_arm='down'):
    """
    Builds a ~2.1-unit-tall chibi body (big head, small body) facing -Y (front).
    Returns anchors so accessories line up across every character:

      head (centre), head_r, crown (top of head), face (front of face),
      neck, chest, waist, back, hand_l, hand_r, foot_l, foot_r, shoulder_l, shoulder_r

    sleeves: 'none' | 'short' | 'long'   pants: 'short' | 'long'
    right_arm / left_arm: 'down' | 'out' | 'up' (raised, e.g. holding a weapon overhead) | 'fist' (forward)
    The figure's own right side is -X.
    """
    hands = hands or skin
    S, T, B = mat(skin, 0.6), mat(top, 0.6), mat(bottom, 0.65)
    SH = mat(shoes, 0.5)
    a = {}

    # legs + feet
    for side, sx in (('l', 1), ('r', -1)):
        hip = (0.16 * sx, 0, 0.62)
        knee = (0.17 * sx, 0, 0.32)
        ankle = (0.17 * sx, 0, 0.12)
        leg_mat = B if pants == 'long' else S
        rod(hip, knee, 0.095, B if pants else leg_mat)
        rod(knee, ankle, 0.085, leg_mat)
        if pants == 'short':
            cylinder((0.165 * sx, 0, 0.47), 0.12, 0.2, B)
        sphere((0.17 * sx, -0.06, 0.07), (0.11, 0.17, 0.08), SH)
        a[f'foot_{side}'] = Vector((0.17 * sx, -0.06, 0.0))

    # torso + pelvis
    sphere((0, 0, 0.66), (0.25, 0.18, 0.13), B)
    cylinder((0, 0, 0.9), 0.24, 0.42, T, scale=(1, 0.78, 1))
    sphere((0, 0, 1.1), (0.26, 0.2, 0.1), T)
    a['waist'] = Vector((0, 0, 0.7))
    a['chest'] = Vector((0, -0.19, 0.98))
    a['back'] = Vector((0, 0.19, 0.95))
    a['neck'] = Vector((0, 0, 1.17))
    cylinder((0, 0, 1.17), 0.08, 0.1, S)

    # arms
    poses = {
        'down': lambda sx: [(0.27 * sx, 0, 1.08), (0.36 * sx, 0, 0.86), (0.4 * sx, -0.02, 0.66)],
        'out': lambda sx: [(0.27 * sx, 0, 1.08), (0.48 * sx, 0, 0.98), (0.66 * sx, -0.02, 0.9)],
        'up': lambda sx: [(0.27 * sx, 0, 1.08), (0.44 * sx, -0.02, 1.28), (0.5 * sx, -0.06, 1.5)],
        'fist': lambda sx: [(0.27 * sx, 0, 1.08), (0.34 * sx, -0.18, 0.95), (0.3 * sx, -0.4, 0.98)],
    }
    for side, sx, pose in (('l', 1, left_arm), ('r', -1, right_arm)):
        shoulder, elbow, wrist = poses[pose](sx)
        a[f'shoulder_{side}'] = Vector(shoulder)
        upper = T if sleeves in ('short', 'long') else S
        lower = T if sleeves == 'long' else S
        rod(shoulder, elbow, 0.075, upper)
        rod(elbow, wrist, 0.065, lower)
        sphere(wrist, 0.085, mat(hands, 0.6))
        a[f'hand_{side}'] = Vector(wrist)

    # head
    head = Vector((0, 0, 1.58))
    r = 0.42
    sphere(head, (r, r * 0.95, r * 0.98), S)
    a['head'] = head
    a['head_r'] = r
    a['crown'] = head + Vector((0, 0, r * 0.98))
    a['face'] = head + Vector((0, -r * 0.95, 0))
    # ears
    for sx in (1, -1):
        sphere((r * 0.98 * sx, 0.02, 1.56), (0.05, 0.035, 0.08), S)
    # eyes: dark ellipsoid + optional iris + white highlight
    E = mat(eyes, 0.2)
    for sx in (1, -1):
        ex = 0.15 * sx
        eye_c = (ex, -r * 0.86, 1.55)
        sphere(eye_c, (0.065, 0.03, 0.085), E, rot=(0.25, 0, 0))
        if iris:
            sphere((ex, -r * 0.875, 1.54), (0.045, 0.02, 0.058), mat(iris, 0.2), rot=(0.25, 0, 0))
        sphere((ex - 0.02 * sx, -r * 0.89, 1.585), 0.018, mat('#ffffff', 0.1))
    if brows:
        for sx in (1, -1):
            box((0.15 * sx, -r * 0.86, 1.67), (0.11, 0.02, 0.022), mat(brows, 0.6), rot=(0.3, 0, -0.18 * sx))
    if mouth == 'smile':
        y = -r * 0.93
        tube([(-0.07, y + 0.01, 1.445), (0, y, 1.41), (0.07, y + 0.01, 1.445)], 0.012, mat('#5a2a2a', 0.5),
             name='mouth')
    elif mouth == 'grin':
        sphere((0, -r * 0.9, 1.42), (0.08, 0.02, 0.035), mat('#ffffff', 0.3))
    elif mouth == 'line':
        box((0, -r * 0.92, 1.43), (0.08, 0.015, 0.012), mat('#5a2a2a', 0.5))
    return a


# ── Heroic figure base (realistic proportions) ───────────────────────────

def subdivide(obj, levels=2):
    """Smooth an organic part (applied on finalize)."""
    mod = obj.modifiers.new('subsurf', 'SUBSURF')
    mod.levels = levels
    mod.render_levels = levels
    return obj


def _meta(name, resolution=0.011):
    """A metaball 'family'. Elements in one family melt together into a single smooth surface."""
    mb = bpy.data.metaballs.new(name)
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = 0.6
    obj = bpy.data.objects.new(name, mb)
    bpy.context.scene.collection.objects.link(obj)
    return mb


# Visible surface radius of a lone metaball ≈ radius * META_K (stiffness 2, threshold 0.6).
META_K = 0.84


def blob_ball(mb, co, radius, stiffness=2.0):
    e = mb.elements.new(type='BALL')
    e.co = co
    e.radius = radius / META_K
    e.stiffness = stiffness
    return e


def blob_ellipsoid(mb, co, size, rot=(0, 0, 0), stiffness=2.0):
    """`size` = half-extents (x, y, z) of the visible shape."""
    e = mb.elements.new(type='ELLIPSOID')
    e.co = co
    e.radius = 1.0
    e.size_x, e.size_y, e.size_z = (s / META_K for s in size)
    e.rotation = Euler(rot).to_quaternion()
    e.stiffness = stiffness
    return e


def blob_limb(mb, a, b, r1, r2, steps=None):
    """Tapered limb from a (radius r1) to b (radius r2) — melts into neighbouring blobs."""
    a, b = Vector(a), Vector(b)
    if steps is None:
        steps = max(3, math.ceil((b - a).length / (min(r1, r2) * 0.45)))
    for i in range(steps + 1):
        t = i / steps
        blob_ball(mb, a.lerp(b, t), r1 + (r2 - r1) * t)


def solidify_blobs(families):
    """Convert metaball families to meshes. `families` maps name -> material."""
    for name, material in families.items():
        obj = bpy.data.objects.get(name)
        if obj is None or len(obj.data.elements) == 0:
            if obj is not None:
                bpy.data.objects.remove(obj)
            continue
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        mesh_obj = bpy.context.active_object
        mesh_obj.name = f'{name}_mesh'
        _finish(mesh_obj, material, True)


HERO_ARM_POSES = {
    # (elbow, wrist) offsets from the shoulder, for the figure's LEFT side (+X); mirrored for the right.
    'down': ((0.05, 0.0, -0.27), (0.07, -0.03, -0.52)),
    'relaxed': ((0.06, 0.02, -0.26), (0.06, -0.07, -0.5)),
    'out': ((0.27, 0.0, -0.06), (0.52, -0.02, -0.1)),
    'up': ((0.14, -0.04, 0.2), (0.16, -0.08, 0.46)),
    'fist': ((0.07, -0.24, -0.1), (0.04, -0.5, -0.06)),   # punch straight forward
    'hip': ((0.17, 0.05, -0.2), (0.07, -0.02, -0.4)),     # hand on hip
    'guard': ((0.1, -0.15, -0.22), (0.02, -0.3, 0.02)),   # forearm raised in front (holding a weapon)
    'back': ((0.06, 0.18, -0.2), (0.02, 0.32, -0.02)),    # reaching behind (weapon on back)
}


def hero(skin='#d9a77c', top='#ffffff', bottom='#333333', shoes='#222222', hands=None,
         eyes='#1a1a1a', iris='#4a3020', sleeves='short', pants='long', mouth='line', brows='#2a1a10',
         right_arm='down', left_arm='down', stance='stand', build=1.0):
    """
    Realistic-proportion action figure (~7.5 heads, ~1.85 units tall before finalize), facing -Y.
    The body is sculpted from metaballs, so joints, muscles and face blend into smooth surfaces.
    Clothing regions are separate metaball families: skin, top (torso + sleeves), bottom (pelvis + legs).

    Returns the same anchors as chibi(): head, head_r, crown, face, neck, chest, waist, back,
    hand_l, hand_r, foot_l, foot_r, shoulder_l, shoulder_r — plus elbow_l/r, hip_l/r, knee_l/r.

    sleeves: 'none' | 'short' | 'long'      pants: 'short' | 'long'
    arms: 'down' | 'relaxed' | 'out' | 'up' | 'fist' | 'hip' | 'guard' | 'back'
    stance: 'stand' | 'wide' (heroic, feet apart)      build: 1.0 normal, 1.25 muscular
    The figure's own right side is -X.
    """
    w = build
    SK, TP, BT = _meta('skin'), _meta('top'), _meta('bottom')
    a = {}

    # ── legs ──
    spread = 0.16 if stance == 'wide' else 0.11
    for side, sx in (('l', 1), ('r', -1)):
        hip = Vector((0.095 * w * sx, 0, 0.95))
        knee = Vector((spread * sx, -0.015, 0.52))
        ankle = Vector(((spread + 0.01) * sx, 0.01, 0.1))
        blob_limb(BT, hip, knee, 0.098 * w, 0.064 * w)
        blob_limb(BT if pants == 'long' else SK, knee, ankle, 0.064 * w, 0.044 * w)
        blob_ellipsoid(BT if pants == 'long' else SK, knee.lerp(ankle, 0.3) + Vector((0, 0.025, 0)),
                       (0.056 * w, 0.056 * w, 0.1))  # calf
        sphere(ankle + Vector((0, -0.045, -0.055)), (0.052, 0.125, 0.05), mat(shoes, 0.45), segs=20, rings=10)
        a[f'hip_{side}'], a[f'knee_{side}'] = hip, knee
        a[f'foot_{side}'] = ankle + Vector((0, -0.05, -0.1))

    # ── torso ──
    blob_ellipsoid(BT, (0, 0, 0.97), (0.165 * w, 0.11 * w, 0.1))                       # pelvis
    blob_ellipsoid(TP, (0, 0.005, 1.08), (0.15 * w, 0.1 * w, 0.12))                    # waist
    blob_ellipsoid(TP, (0, 0.0, 1.2), (0.165 * w, 0.11 * w, 0.14))                     # abdomen
    blob_ellipsoid(TP, (0, 0, 1.33), (0.21 * w, 0.128 * w, 0.15))                     # ribcage
    blob_ellipsoid(TP, (0, -0.03 * w, 1.37), (0.17 * w, 0.1 * w, 0.08))                # chest plane
    for sx in (1, -1):
        blob_limb(TP if sleeves != 'none' else SK, (0.05 * sx, 0.01, 1.49), (0.205 * w * sx, 0, 1.45),
                  0.055 * w, 0.06 * w, steps=4)                                             # trapezius
    a['waist'] = Vector((0, 0, 1.0))
    a['chest'] = Vector((0, -0.13 * w, 1.34))
    a['back'] = Vector((0, 0.13 * w, 1.3))
    a['neck'] = Vector((0, 0, 1.52))
    blob_limb(SK, (0, 0.01, 1.44), (0, 0.0, 1.58), 0.06 * w, 0.055 * w, steps=5)

    # ── arms ──
    for side, sx, pose in (('l', 1, left_arm), ('r', -1, right_arm)):
        shoulder = Vector((0.23 * w * sx, 0, 1.43))
        e_off, w_off = HERO_ARM_POSES[pose]
        elbow = shoulder + Vector((e_off[0] * sx, e_off[1], e_off[2]))
        wrist = shoulder + Vector((w_off[0] * sx, w_off[1], w_off[2]))
        upper = TP if sleeves in ('short', 'long') else SK
        lower = TP if sleeves == 'long' else SK
        blob_ball(upper, shoulder, 0.07 * w)                                     # deltoid
        blob_limb(upper, shoulder, elbow, 0.064 * w, 0.05 * w)
        blob_ellipsoid(upper, shoulder.lerp(elbow, 0.45), (0.05 * w, 0.05 * w, 0.06 * w))  # bicep mass
        blob_limb(lower, elbow, wrist, 0.052 * w, 0.037 * w)
        if lower is TP:
            blob_limb(SK, wrist.lerp(elbow, 0.15), wrist, 0.032, 0.03, steps=2)
        # hand: palm + thumb along the forearm direction
        direction = (wrist - elbow).normalized()
        palm = wrist + direction * 0.055
        blob_ellipsoid(SK if not hands else _meta('hands'), palm, (0.033, 0.026, 0.05),
                       rot=rot_between(wrist, palm))
        thumb_base = palm + Vector((0.022 * sx, -0.022, 0.0))
        blob_limb(SK if not hands else _meta('hands'), thumb_base, thumb_base + direction * 0.03 + Vector((0.008 * sx, -0.012, 0)),
                  0.013, 0.011, steps=3)
        a[f'shoulder_{side}'], a[f'elbow_{side}'] = shoulder, elbow
        a[f'hand_{side}'] = palm

    # ── head ──
    head = Vector((0, -0.01, 1.69))
    r = 0.13
    blob_ellipsoid(SK, head, (r * 0.84, r * 0.93, r * 0.98))                                   # cranium
    blob_ellipsoid(SK, head + Vector((0, -0.03, -0.065)), (r * 0.66, r * 0.68, r * 0.6))       # jaw
    blob_ellipsoid(SK, head + Vector((0, -0.075, -0.112)), (0.03, 0.026, 0.024))               # chin
    blob_ellipsoid(SK, head + Vector((0, -r * 0.9, -0.022)), (0.011, 0.016, 0.022),
                   rot=(math.radians(-15), 0, 0))                                               # nose
    for sx in (1, -1):
        blob_ellipsoid(SK, head + Vector((r * 0.82 * sx, 0.0, -0.012)), (0.012, 0.022, 0.03))  # ears
        blob_ellipsoid(SK, head + Vector((0.042 * sx, -0.098, 0.032)), (0.03, 0.014, 0.01))    # brow ridge

    solidify_blobs({'skin': mat(skin, 0.5), 'top': mat(top, 0.7), 'bottom': mat(bottom, 0.75),
                    'hands': mat(hands, 0.55) if hands else None})

    # ── face details (meshes), placed on the real surface of the sculpted head ──
    skin_obj = bpy.data.objects.get('skin_mesh')
    tree = BVHTree.FromObject(skin_obj, bpy.context.evaluated_depsgraph_get()) if skin_obj else None

    def surf(x, z, inset=0.0):
        """Front surface of the face at (x, z), pushed `inset` into the head."""
        if tree:
            hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))[0]
            if hit is not None:
                return hit.y + inset
        return head.y - r * 0.72 + inset

    for sx in (1, -1):
        ex, ez = 0.041 * sx, head.z + 0.012
        ec = Vector((ex, surf(ex, ez, 0.004), ez))
        sphere(ec, (0.02, 0.008, 0.011), mat('#f4f1ea', 0.3), segs=14, rings=7)
        sphere(ec + Vector((0, -0.005, 0)), (0.0095, 0.005, 0.0095), mat(iris, 0.2), segs=10, rings=6)
        sphere(ec + Vector((0, -0.009, 0)), 0.0045, mat(eyes, 0.1), segs=8, rings=4)
        if brows:  # tapered strokes lying on the brow ridge
            pts = [(0.018 * sx, head.z + 0.036), (0.044 * sx, head.z + 0.045), (0.07 * sx, head.z + 0.04)]
            tube([Vector((x, surf(x, z, -0.001), z)) for x, z in pts], 0.0055, mat(brows, 0.7),
                 taper_to=0.45, name='brow')
    lips = mat('#8a4b40', 0.5)
    mz = head.z - 0.088

    def lip_line(points, radius, name):
        tube([Vector((x, surf(x, z, -0.0005), z)) for x, z in points], radius, lips, name=name)

    if mouth == 'smile':
        lip_line([(-0.026, mz + 0.004), (0, mz - 0.005), (0.026, mz + 0.004)], 0.004, 'mouth')
    elif mouth == 'grin':
        sphere((0, surf(0, mz - 0.002, 0.003), mz - 0.002), (0.028, 0.008, 0.011), mat('#f4f1ea', 0.3), segs=12, rings=6)
        lip_line([(-0.03, mz + 0.004), (0, mz - 0.012), (0.03, mz + 0.004)], 0.0035, 'grin')
    else:
        lip_line([(-0.02, mz), (0, mz - 0.001), (0.02, mz)], 0.0028, 'mouth')
    a['head'] = head
    a['head_r'] = r
    a['crown'] = head + Vector((0, 0, r))
    a['face'] = head + Vector((0, -r * 0.9, 0))
    return a


# ── Output ───────────────────────────────────────────────────────────────

def _mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def _join_all(name):
    objs = _mesh_objects()
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')  # applies modifiers
    bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return body


def _bounds(body):
    pts = [body.matrix_world @ v.co for v in body.data.vertices]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def _export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=False, export_apply=True,
                              export_yup=True, export_animations=False, export_materials='EXPORT',
                              export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6)


def finalize(model_id, thumb_angle=-28):
    """Join, normalise (feet on origin, TARGET_HEIGHT tall), export GLB, render PNG."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    body = _join_all(model_id)
    lo, hi = _bounds(body)
    k = TARGET_HEIGHT / (hi.z - lo.z)
    body.location = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) * k
    body.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    glb = os.path.join(MODELS_DIR, f'{model_id}.glb')
    _export(glb)
    png = os.path.join(MODELS_DIR, f'{model_id}.png')
    debug_view = os.environ.get('KIT_VIEW')  # "angle,dist,target_z,out.png" — debug close-ups, skips the thumbnail
    if debug_view:
        angle, dist, target_z, out = debug_view.split(',', 3)
        render_thumbnail(out, float(angle), dist=float(dist), target_z=float(target_z))
    else:
        render_thumbnail(png, thumb_angle)
    size_kb = os.path.getsize(glb) / 1024
    print(f'[kit] {model_id}: {tris} tris, {size_kb:.0f} KB -> {glb}')
    print(f'[kit] thumbnail -> {png}')


def finalize_prop(prop_id, thumb_angle=-20, elevation=0.35):
    """Props (weapons, relics…): join, centre on the origin, scale the LONGEST side to 1.0,
    export public/props/<id>.glb and a square ink-outlined sprite public/props/<id>.png (512²).
    Model the prop in the pose it should have as a sprite/icon (front = -Y, up = +Z)."""
    os.makedirs(PROPS_DIR, exist_ok=True)
    body = _join_all(prop_id)
    lo, hi = _bounds(body)
    k = 1.0 / max(hi - lo)
    body.location = -(lo + hi) / 2 * k
    body.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    glb = os.path.join(PROPS_DIR, f'{prop_id}.glb')
    _export(glb)
    png = os.path.join(PROPS_DIR, f'{prop_id}.png')
    debug_view = os.environ.get('KIT_VIEW')
    if debug_view:
        angle, dist, target_z, out = debug_view.split(',', 3)
        render_thumbnail(out, float(angle), res=(512, 512), dist=float(dist), target_z=float(target_z),
                         elevation=elevation)
    else:
        render_thumbnail(png, thumb_angle, res=(512, 512), elevation=elevation)
    print(f'[kit] prop {prop_id}: {tris} tris, {os.path.getsize(glb) / 1024:.0f} KB -> {glb}')
    print(f'[kit] sprite -> {png}')


def render_thumbnail(path, angle_deg=-28, res=(768, 1024), dist=None, target_z=None, elevation=None):
    scene = bpy.context.scene
    for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'

    # ink outline (manga look) via Freestyle
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = 'ABSOLUTE'
    scene.render.line_thickness = 1.6
    fs = bpy.context.view_layer.freestyle_settings
    lineset = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('ink')
    lineset.select_by_visibility = True
    lineset.select_silhouette = lineset.select_border = True
    lineset.select_crease = False
    if lineset.linestyle is None:
        lineset.linestyle = bpy.data.linestyles.new('ink')
    lineset.linestyle.color = (0, 0, 0)
    lineset.linestyle.thickness = 1.6

    world = bpy.data.worlds.new('world')
    world.color = (1, 1, 1)
    if hasattr(world, 'use_nodes') and not world.use_nodes:
        world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (1, 1, 1, 1)
        bg.inputs['Strength'].default_value = 0.6
    scene.world = world

    def light(name, kind, loc, energy, size=3.0):
        data = bpy.data.lights.new(name, kind)
        data.energy = energy
        if kind == 'AREA':
            data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = loc
        obj.rotation_euler = rot_between(loc, (0, 0, 1.0))
        obj.rotation_euler.rotate_axis('X', math.pi)  # lights point down -Z
        scene.collection.objects.link(obj)
        direction = Vector((0, 0, 1.0)) - Vector(loc)
        obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    light('key', 'AREA', (-3, -4, 4.5), 900, 4)
    light('fill', 'AREA', (4, -3, 2), 300, 4)
    light('rim', 'AREA', (0, 4, 4), 600, 3)

    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 70
    cam = bpy.data.objects.new('cam', cam_data)
    a = math.radians(angle_deg)
    if dist is None:
        # Auto-frame: fit the figure's height and its width as seen from this angle (with a margin).
        pts = [o.matrix_world @ Vector(c) for o in _mesh_objects() for c in o.bound_box]
        side = Vector((math.cos(a), math.sin(a), 0))  # camera's horizontal axis
        across = [p.dot(side) for p in pts]
        half_w = max(abs(min(across)), abs(max(across)))
        z_lo, z_hi = min(p.z for p in pts), max(p.z for p in pts)
        extent = max(z_hi - z_lo, 2 * half_w)
        tan_v = math.tan(math.atan(18 / cam_data.lens))       # half the FOV of the longer image side (36mm sensor)
        tan_h = tan_v * min(res) / max(res)
        if res[0] > res[1]:
            tan_v, tan_h = tan_h, tan_v
        dist = max(((z_hi - z_lo) / 2 + 0.06 * extent) / tan_v, (half_w + 0.04 * extent) / tan_h) * 1.04
        target_z = (z_lo + z_hi) / 2
    rise = dist * elevation if elevation is not None else 0.55 * dist / 5.6
    cam.location = (math.sin(a) * dist * -1, -math.cos(a) * dist, target_z + rise)
    target = Vector((0, 0, target_z))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
