from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1'
bpy.ops.wm.open_mainfile(filepath=str(DIRECTORY / 'female-barbarian-helmet-fitted.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
for name in ['bob', 'knight']:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(DIRECTORY / f'hair_{name}_barbarian_helmet.glb'), bone_heuristic='TEMPERANCE')
    for obj in set(bpy.data.objects) - before:
        if obj.type != 'MESH':
            continue
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.matrix_world = world
        obj['helmet_hair_variant'] = name
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
        obj.hide_set(name == 'knight')
        obj.hide_render = name == 'knight'
    for obj in set(bpy.data.objects) - before:
        if obj.type != 'MESH':
            bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(DIRECTORY / 'female-barbarian-helmet-hair-fitted.blend'))
