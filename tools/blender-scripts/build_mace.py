import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/items/mace/tripo_v1/model_url.glb'
LENGTH = 0.8
GRIP = 0.136

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
item = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
item.parent = None
item.matrix_world = Matrix.Identity(4)
item.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z'))
item.data.materials[0].use_backface_culling = True

with tempfile.TemporaryDirectory(prefix='mace-') as directory:
    prepared = Path(directory) / 'mace.glb'
    bpy.ops.export_scene.gltf(filepath=str(prepared), export_format='GLB', export_animations=False)
    sys.argv = [str(__file__), '--', '--source', str(prepared), '--name', 'mace',
                '--category', 'weapons', '--size', str(LENGTH), '--grip-fraction', str(GRIP),
                '--icon-rotation', '90', '0', '40']
    runpy.run_path(str(ROOT / 'tools/blender-scripts/export_item_asset.py'), run_name='__main__')
    (ROOT / 'assets/items/mace/mace-render.png').unlink(missing_ok=True)

item = bpy.data.objects['mace']
generation = json.loads((SOURCE.parent / 'generation.json').read_text())
record = {
    'date': '2026-10-31',
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'generation_record': 'assets/items/mace/tripo_v1/generation.json',
    'concept_record': 'assets/items/mace/concepts/generation.json',
    'tool': generation['config']['tool'],
    'tier': generation['config']['tier'],
    'license': generation['config']['license'],
    'license_url': generation['config']['license_url'],
    'task_id': generation['task_id'],
    'credits_consumed': generation['task']['credits_consumed'],
    'parameters': generation['config']['parameters'],
    'method': 'Preserve generated topology and UVs; align head to +X; bake metric size and grip origin; drop emission; resize PBR maps to 512px.',
    'length_m': LENGTH,
    'grip_fraction_from_pommel': GRIP,
    'triangles': sum(len(poly.vertices) - 2 for poly in item.data.polygons),
    'dimensions_blender_xyz_m': list(item.dimensions),
    'scale': list(item.scale),
    'model': 'client/public/models/weapons/mace.glb',
    'icon': 'client/public/items/weapons/mace.png',
    'blender': 'assets/items/mace/mace.blend',
}
(ROOT / 'doc/assets/mace-model.json').write_text(json.dumps(record, indent=2) + '\n')
print('MACE', json.dumps(record))
