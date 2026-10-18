import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile

import bpy
from mathutils import Matrix
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/items/rune_blade/tripo_v1/model_url.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
item = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
item.parent = None
item.matrix_world = Matrix.Identity(4)
item.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z'))
material = item.data.materials[0]
shader = material.node_tree.nodes.get('Principled BSDF')
color = shader.inputs['Base Color'].links[0].from_node.image
pixels = np.empty(color.size[0] * color.size[1] * 4, dtype=np.float32)
color.pixels.foreach_get(pixels)
pixels = pixels.reshape(-1, 4)
red, green, blue = pixels[:, 0], pixels[:, 1], pixels[:, 2]
mask = np.clip((red - 0.35) * 3, 0, 1)
mask *= np.clip((red - green * 1.8) * 4, 0, 1)
mask *= np.clip((green - blue * 1.3) * 8, 0, 1)
pixels[:, :3] *= mask[:, None]
pixels[:, 3] = 1
emission = bpy.data.images.new('RuneBladeEmission', width=color.size[0], height=color.size[1])
emission.colorspace_settings.name = color.colorspace_settings.name
emission.pixels.foreach_set(pixels.ravel())
emission.pack()
node = material.node_tree.nodes.new('ShaderNodeTexImage')
node.image = emission
material.node_tree.links.new(node.outputs['Color'], shader.inputs['Emission Color'])
shader.inputs['Emission Strength'].default_value = 1.6
material.use_backface_culling = True

with tempfile.TemporaryDirectory(prefix='rune-blade-') as directory:
    prepared = Path(directory) / 'rune_blade.glb'
    bpy.ops.export_scene.gltf(filepath=str(prepared), export_format='GLB', export_animations=False)
    sys.argv = [str(__file__), '--', '--source', str(prepared), '--name', 'rune_blade',
                '--category', 'weapons', '--size', '2.1', '--grip-fraction', '0.23',
                '--keep-emission', '--texture-size', '1024', '--icon-rotation', '90', '0', '40']
    runpy.run_path(str(ROOT / 'tools/blender-scripts/export_item_asset.py'), run_name='__main__')
    (ROOT / 'assets/items/rune_blade/rune_blade-render.png').unlink(missing_ok=True)

item = bpy.data.objects['rune_blade']
generation = json.loads((SOURCE.parent / 'generation.json').read_text())
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.unit_settings.length_unit = 'METERS'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets/items/rune_blade/rune_blade.blend'))
record = {
    'date': '2026-10-18',
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'generation_record': 'assets/items/rune_blade/tripo_v1/generation.json',
    'tool': generation['config']['tool'],
    'tier': generation['config']['tier'],
    'license': generation['config']['license'],
    'license_url': generation['config']['license_url'],
    'task_id': generation['task_id'],
    'credits_consumed': generation['task']['credits_consumed'],
    'parameters': generation['config']['parameters'],
    'method': 'Preserve generated topology and UVs; align blade to +X; bake metric size and grip origin; derive orange rune emission from the base color; resize PBR maps to 1024px.',
    'length_m': 2.1,
    'grip_fraction_from_pommel': 0.23,
    'blade_tip_x_m': 2.1 * 0.77,
    'triangles': sum(len(poly.vertices) - 2 for poly in item.data.polygons),
    'dimensions_blender_xyz_m': list(item.dimensions),
    'scale': list(item.scale),
    'model': 'client/public/models/weapons/rune_blade.glb',
    'icon': 'client/public/items/weapons/rune_blade.png',
    'blender': 'assets/items/rune_blade/rune_blade.blend',
}
(ROOT / 'doc/assets/rune-blade-model.json').write_text(json.dumps(record, indent=2) + '\n')
print('RUNE_BLADE', json.dumps(record))
