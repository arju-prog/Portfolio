"""Sun Wukong's golden fillet (Black Myth: Wukong) — ornate gold circlet with cloud-scroll reliefs,
a central crest holding a red gem, and two long striped pheasant-tail plumes rising from the sides.
The ring is tilted ~28° toward the camera so it reads as a ring in the sprite."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kit  # noqa: E402
from kit import cone, cylinder, mat, sphere, torus, tube  # noqa: E402

kit.reset()

GOLD = mat('#f0b93a', 0.28, metal=0.88)
GOLD_D = mat('#b8801f', 0.38, metal=0.85)
GEM = mat('#d0141c', 0.08, metal=0.1, emit=0.35)
GEM_HI = mat('#ffd0c0', 0.1, emit=1.5)
TAN = mat('#b8813f', 0.65)
DARK = mat('#2a1810', 0.75)
RED = mat('#a8201a', 0.55)

R = 0.3        # ring radius
BH = 0.074     # band height
TILT = math.radians(28)


def slab(outline, half_t, m, y, bevel=0.003, name='slab'):
    """Flat plate from a 2D outline in the XZ plane, centred on depth y."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, 0, z)) for x, z in outline]
    edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    new_verts = {e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)}
    for v in bm.verts:
        v.co.y = y + (half_t if v in new_verts else -half_t)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(m)
    if bevel:
        mod = obj.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    return obj


def band():
    bpy.ops.mesh.primitive_cylinder_add(vertices=72, radius=R, depth=BH, end_fill_type='NOTHING')
    obj = bpy.context.active_object
    obj.data.materials.append(GOLD)
    for p in obj.data.polygons:
        p.use_smooth = True
    sol = obj.modifiers.new('solid', 'SOLIDIFY')
    sol.thickness = 0.014
    sol.offset = 0
    bev = obj.modifiers.new('bevel', 'BEVEL')
    bev.width = 0.004
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    return obj


def ring_point(phi, v, out=0.0):
    r = R + 0.007 + out
    return (r * math.cos(phi), r * math.sin(phi), v)


def curl(phi0, cu, cv, mirror, r0=0.022, turns=1.2, start=0.0):
    """Spiral cloud-scroll in the band's surface around (cu, cv) (u along the ring, v up)."""
    pts = []
    n = 16
    for i in range(n + 1):
        t = i / n
        a = start + t * turns * math.tau
        r = r0 * (1 - 0.8 * t)
        u = cu + mirror * r * math.cos(a)
        v = cv + r * math.sin(a)
        pts.append(ring_point(phi0 + u / R, v, 0.002))
    tube(pts, 0.0042, GOLD, smooth_path=False, name='curl')


# ── the circlet (built level, then tilted) ──
before = set(bpy.data.objects)
band()
for z in (BH / 2, -BH / 2):
    torus((0, 0, z), R + 0.002, 0.0075, GOLD, major_segs=72, minor_segs=8)
torus((0, 0, 0), R + 0.0075, 0.003, GOLD_D, major_segs=72, minor_segs=6)  # fine engraved centre line

# cloud-scroll motifs (pairs of mirrored curls) around the band
FRONT = -math.pi / 2
for deg in (-150, -125, -55, -30, 30, 65, 115, 150):
    phi = math.radians(deg)
    for m in (1, -1):
        curl(phi, 0.022 * m, 0.0, m, r0=0.019, turns=1.15, start=math.pi)
    sphere(ring_point(phi, 0.0, 0.004), 0.007, GOLD_D, segs=10, rings=6)
# beaded studs between motifs
for deg in range(-180, 180, 15):
    phi = math.radians(deg + 7.5)
    if abs(phi - FRONT) < 0.5 or min(abs(phi), abs(abs(phi) - math.pi)) < 0.2:
        continue
    for v in (BH / 2 - 0.012, -BH / 2 + 0.012):
        sphere(ring_point(phi, v, 0.0), 0.0045, GOLD, segs=8, rings=4)

# central crest at the front: a flame/cloud plate with scroll edges and a red gem
yc = -(R + 0.012)
crest = [(-0.075, -0.03), (0.075, -0.03), (0.088, 0.02), (0.075, 0.06), (0.052, 0.078), (0.042, 0.1),
         (0.022, 0.12), (0.0, 0.165), (-0.022, 0.12), (-0.042, 0.1), (-0.052, 0.078), (-0.075, 0.06),
         (-0.088, 0.02)]
crest = [(x * 1.45, z * 1.4 - 0.008) for x, z in crest]
slab(crest, 0.006, GOLD, yc, bevel=0.003, name='crest')
inner = [(x * 0.78, z * 0.8 + 0.008) for x, z in crest]
slab(inner, 0.003, GOLD_D, yc - 0.007, bevel=0.0015, name='crest_inner')
for m in (1, -1):  # scroll curls flanking the gem
    pts = []
    for i in range(15):
        t = i / 14
        a = math.pi * 0.2 + t * 1.3 * math.tau
        r = 0.026 * (1 - 0.75 * t)
        pts.append((m * (0.082 + r * math.cos(a)), yc - 0.012, 0.035 + r * math.sin(a)))
    tube(pts, 0.0045, GOLD, smooth_path=False, name='crest_curl')
torus((0, yc - 0.012, 0.05), 0.044, 0.008, GOLD, rot=(math.pi / 2, 0, 0), major_segs=36, minor_segs=8)
sphere((0, yc - 0.016, 0.05), (0.04, 0.02, 0.04), GEM, segs=24, rings=12)
sphere((-0.013, yc - 0.034, 0.064), 0.008, GEM_HI, segs=8, rings=4)
sphere((0, yc - 0.012, 0.17), 0.013, GOLD, segs=12, rings=6)       # tip pearl
for m in (1, -1):
    sphere((m * 0.075, yc - 0.01, 0.105), 0.009, GOLD, segs=10, rings=6)

# plume sockets on the sides
for s in (1, -1):
    cylinder((s * (R + 0.012), 0, 0.0), 0.02, BH + 0.02, GOLD_D, verts=20)
    sphere((s * (R + 0.012), 0, BH / 2 + 0.012), 0.022, GOLD, segs=16, rings=8)
    torus((s * (R + 0.012), 0, -BH / 2 - 0.006), 0.021, 0.006, GOLD, major_segs=20, minor_segs=6)

ring_objs = [o for o in bpy.data.objects if o not in before]
rx = Matrix.Rotation(TILT, 4, 'X')
for o in ring_objs:
    o.matrix_world = rx @ o.matrix_world


# ── pheasant-tail plumes (striped tan / dark / red), rising from the side sockets ──
def catmull(ctrl, n):
    P = [Vector(p) for p in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    segs = len(P) - 3
    for i in range(n + 1):
        t = i / n * segs
        k = min(int(t), segs - 1)
        u = t - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return out


STRIPES = [TAN, TAN, DARK, TAN, TAN, DARK, RED, RED, DARK]


def plume(s):
    base = rx @ Vector((s * (R + 0.012), 0, BH / 2 + 0.02))
    ctrl = [tuple(base), (s * 0.34, 0.04, 0.2), (s * 0.35, 0.1, 0.42), (s * 0.38, 0.14, 0.64),
            (s * 0.46, 0.14, 0.84), (s * 0.58, 0.08, 0.95), (s * 0.7, 0.0, 0.94)]
    path = catmull(ctrl, 70)
    obj = tube([tuple(p) for p in path], 0.027, TAN, taper_to=None, smooth_path=False, name='plume')
    for m in STRIPES[1:]:
        if m.name not in obj.data.materials:
            obj.data.materials.append(m)
    slots = {m.name: i for i, m in enumerate(obj.data.materials)}
    me = obj.data
    acc = [0.0]
    for i in range(1, len(path)):
        acc.append(acc[-1] + (path[i] - path[i - 1]).length)
    total = acc[-1]

    def project(co):
        """Closest point on the path polyline -> (centre, tangent, arc length)."""
        best = None
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            ab = b - a
            t = max(0.0, min(1.0, (co - a).dot(ab) / ab.length_squared))
            q = a + ab * t
            d2 = (co - q).length_squared
            if best is None or d2 < best[0]:
                best = (d2, q, ab.normalized(), acc[i] + ab.length * t)
        return best[1:]

    # flatten into a broad feather facing the camera: thin along Y, wider across the curve
    Y = Vector((0, 1, 0))
    for v in me.vertices:
        c, tan, L = project(v.co)
        side = tan.cross(Y).normalized()
        d = v.co - c
        a, b = d.dot(side), d.dot(Y)
        t = L / total   # feather profile: thin quill, broad vane, pointed tip
        w = 0.35 + 0.65 * t / 0.15 if t < 0.15 else (1.0 if t < 0.7 else 1 - 0.95 * ((t - 0.7) / 0.3) ** 1.4)
        v.co = c + side * (a * 1.3 * w) + Y * (b * 0.4 * w) + (d - side * a - Y * b)
    nbands = 40
    for poly in me.polygons:
        t = project(poly.center)[2] / total
        poly.material_index = slots[STRIPES[int(t * nbands) % len(STRIPES)].name]
    return obj


for s in (1, -1):
    plume(s)
    # little red tassel bead at the base of each plume
    sphere(tuple(rx @ Vector((s * (R + 0.04), -0.01, -0.035))), 0.016, RED, segs=12, rings=6)
    cone(tuple(rx @ Vector((s * (R + 0.04), -0.01, -0.07))), 0.018, 0.004, 0.06, RED, verts=12,
         rot=(math.pi + TILT, 0, 0))

kit.finalize_prop('golden_headband')
