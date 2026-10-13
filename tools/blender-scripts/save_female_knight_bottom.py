import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
source, version = sys.argv[sys.argv.index('--') + 1:]
assert source.startswith('v') and source[1:].isdigit()
assert version.startswith('v') and version[1:].isdigit()
bpy.ops.wm.open_mainfile(filepath=str(DIRECTORY / f'fitted_{source}/female-knight-bottom-fitted.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and obj.name.startswith('bottom_female_knight'):
        bpy.data.objects.remove(obj, do_unlink=True)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(DIRECTORY / f'fitted_{version}/bottom_female_knight.glb'), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects) - before
for obj in imported:
    if obj.type == 'MESH':
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
        obj.parent = None
for obj in imported:
    if obj.type == 'ARMATURE':
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(DIRECTORY / f'fitted_{version}/female-knight-bottom-fitted.blend'))
