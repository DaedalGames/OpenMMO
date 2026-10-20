"""Scale the Tripo Terraclash altar, cut the amulet-shaped recess, and export it for the client.

blender -b --python tools/blender-scripts/prepare_terraclash_altar.py -- SRC.glb AMULET.glb OUT.glb BLEND
"""
import math
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

src, amulet, out, blend = sys.argv[sys.argv.index('--') + 1:][:4]
WIDTH = 1.6
HEIGHT = 1.0
HEART_LENGTH = 0.5
DEPTH = 0.1
TEX_PX = 1024


def import_joined(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in meshes:
        world = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        o.data.transform(world)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    for o in list(bpy.data.objects):
        if o in before or o is obj:
            continue
        bpy.data.objects.remove(o)
    return obj


def heart_outline(obj, samples=180, grid=512):
    """Pendant silhouette seen from above, chain and bail cut off, as (x, y) in metres."""
    verts = np.array([v.co[:2] for v in obj.data.vertices])
    tris = [p.vertices for p in obj.data.polygons]
    mn, mx = verts.min(0), verts.max(0)
    # The floor model lays the pendant at -Y; the bail starts about 35% of the way up.
    cut = mn[1] + (mx[1] - mn[1]) * 0.35
    lo = np.array([mn[0], mn[1]])
    size = max(mx[0] - mn[0], cut - mn[1])
    px = (verts - lo) / size * (grid - 1)
    mask = np.zeros((grid, grid), bool)
    ys, xs = np.mgrid[0:grid, 0:grid]
    for t in tris:
        for i in range(1, len(t) - 1):
            a, b, c = px[t[0]], px[t[i]], px[t[i + 1]]
            if min(a[1], b[1], c[1]) > grid:
                continue
            x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
            x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, grid - 1), min(y1, grid - 1)
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = xs[y0:y1 + 1, x0:x1 + 1] + 0.5, ys[y0:y1 + 1, x0:x1 + 1] + 0.5
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-9:
                continue
            w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / d
            w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / d
            mask[y0:y1 + 1, x0:x1 + 1] |= (w0 >= 0) & (w1 >= 0) & (1 - w0 - w1 >= 0)
    cut_px = int((cut - mn[1]) / size * (grid - 1))
    mask[cut_px:] = False
    cy, cx = np.argwhere(mask).mean(0)
    points = []
    for k in range(samples):
        ang = 2 * math.pi * k / samples
        dx, dy = math.cos(ang), math.sin(ang)
        r, last = 0.0, 0.0
        while r < grid:
            x, y = int(cx + dx * r), int(cy + dy * r)
            if not (0 <= x < grid and 0 <= y < grid):
                break
            if mask[y, x]:
                last = r
            elif r - last > 6:
                break
            r += 0.5
        points.append((cx + dx * last, cy + dy * last))
    pts = np.array(points)
    for _ in range(3):
        pts = (pts + np.roll(pts, 1, 0) + np.roll(pts, -1, 0)) / 3
    pts = pts / (grid - 1) * size + lo
    return pts - pts.mean(0)


bpy.ops.wm.read_factory_settings(use_empty=True)
pendant = heart_outline(import_joined(amulet, 'amulet'))
bpy.data.objects.remove(bpy.data.objects['amulet'])

obj = import_joined(src, 'terraclash_altar')
# Tripo faces +X; glTF/game forward is +Z, which is Blender -Y.
obj.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z'))
co = np.array([v.co for v in obj.data.vertices])
mn, mx = co.min(0), co.max(0)
s = WIDTH / max(mx[0] - mn[0], mx[1] - mn[1])
sz = HEIGHT / (mx[2] - mn[2])
obj.data.transform(Matrix.Diagonal((s, s, sz, 1))
                   @ Matrix.Translation(-Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]))))
obj.data.update()

# Pendant point (-Y in the floor model) toward the altar front (-Y), matching the concept.
heart = pendant / (pendant[:, 1].max() - pendant[:, 1].min()) * HEART_LENGTH
depsgraph = bpy.context.evaluated_depsgraph_get()
tops = []
for x, y in list(heart) + [(0.0, 0.0)]:
    hit, loc, *_ = obj.ray_cast(Vector((x, y, HEIGHT + 1)), Vector((0, 0, -1)))
    if hit:
        tops.append(loc.z)
floor_z = min(tops) - DEPTH

bm = bmesh.new()
bottom = [bm.verts.new((x, y, floor_z)) for x, y in heart]
top = [bm.verts.new((x, y, HEIGHT + 0.5)) for x, y in heart]
floor_face = bm.faces.new(bottom[::-1])
bm.faces.new(top)
n = len(heart)
walls = [bm.faces.new((bottom[i], bottom[(i + 1) % n], top[(i + 1) % n], top[i])) for i in range(n)]
floor_face.material_index = 0
for f in walls:
    f.material_index = 1
bm.normal_update()
cutter_mesh = bpy.data.meshes.new('heart_cutter')
bm.to_mesh(cutter_mesh)
bm.free()
cutter_mesh.uv_layers.new(name=obj.data.uv_layers[0].name)
cutter = bpy.data.objects.new('heart_cutter', cutter_mesh)
bpy.context.scene.collection.objects.link(cutter)


def molten(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = 0.6
    bsdf.inputs['Emission Color'].default_value = (*color, 1)
    bsdf.inputs['Emission Strength'].default_value = strength
    return mat


cutter_mesh.materials.append(molten('altar_heart_core', (1.0, 0.32, 0.04), 1.2))
cutter_mesh.materials.append(molten('altar_heart_wall', (0.45, 0.05, 0.01), 0.5))

mod = obj.modifiers.new('heart', 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.solver = 'EXACT'
mod.use_hole_tolerant = True
mod.material_mode = 'TRANSFER'
mod.object = cutter
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cutter)

for img in bpy.data.images:
    if img.size[0] > TEX_PX:
        img.scale(TEX_PX, TEX_PX)
for mat in obj.data.materials:
    if mat.name.startswith('tripo_material'):
        mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0

bpy.context.view_layer.update()
print('ALTAR', 'scale', round(s, 4), 'z_stretch', round(sz / s, 3),
      'dims_m', tuple(round(v, 2) for v in obj.dimensions),
      'recess_floor', round(floor_z, 3), 'tris', sum(len(p.vertices) - 2 for p in obj.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=blend)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=False,
                          export_image_format='WEBP', export_image_quality=90)
