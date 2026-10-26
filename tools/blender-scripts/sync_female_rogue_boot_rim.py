from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_rogue_boots/tripo_v1'
OUTPUT = DIRECTORY / 'fitted_v2'
if '--' in sys.argv:
    OUTPUT = ROOT / sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(DIRECTORY / 'fitted_v1/female-rogue-boots-fitted.blend'))
boots = [bpy.data.objects[f'boots_female_rogue_{side}'] for side in ['right', 'left']]
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(OUTPUT / 'boots_female_rogue.glb'), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects)-before
for old in boots:
    new = next(o for o in imported if o.type == 'MESH' and o.name.startswith(old.name))
    action = old.data.shape_keys.animation_data.action
    old.data = new.data
    old.data.shape_keys.animation_data_create()
    old.data.shape_keys.animation_data.action = action
for obj in imported:
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-rogue-boots-fitted.blend'))
