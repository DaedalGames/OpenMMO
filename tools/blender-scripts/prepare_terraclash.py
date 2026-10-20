"""Scale a Terraclash Tripo GLB to game size and export it for the client.

blender -b --python tools/blender-scripts/prepare_terraclash.py -- SRC.glb OUT.glb BLEND [HEIGHT_M] [TEX_PX]
"""
import math
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
src, out, blend = args[:3]
height = float(args[3]) if len(args) > 3 else 9.0
tex_px = int(args[4]) if len(args) > 4 else 2048

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = 'terraclash'
world = obj.matrix_world.copy()
obj.parent = None
obj.matrix_world = Matrix.Identity(4)
# Tripo faces +X; glTF/game forward is +Z, which is Blender -Y.
obj.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z') @ world)
pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
mn = Vector([min(p[i] for p in pts) for i in range(3)])
mx = Vector([max(p[i] for p in pts) for i in range(3)])
s = height / (mx.z - mn.z)
obj.data.transform(
    Matrix.Diagonal((s, s, s, 1))
    @ Matrix.Translation(-Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z)))
)
obj.data.update()
for o in list(bpy.context.scene.objects):
    if o is not obj:
        bpy.data.objects.remove(o)

for img in bpy.data.images:
    if img.size[0] > tex_px:
        img.scale(tex_px, tex_px)
for mat in obj.data.materials:
    for node in mat.node_tree.nodes if mat and mat.use_nodes else []:
        if node.type == 'BSDF_PRINCIPLED':
            node.inputs['Emission Strength'].default_value = 0.0

bpy.context.view_layer.update()
dims = obj.dimensions
print('TERRACLASH', 'scale', round(s, 4), 'dims_m', tuple(round(v, 2) for v in dims),
      'tris', sum(len(p.vertices) - 2 for p in obj.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=blend)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=False,
                          export_image_format='WEBP', export_image_quality=90)
