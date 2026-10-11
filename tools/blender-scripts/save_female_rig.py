"""Keep an editable, packed Blender source with all female motion actions."""
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/modular_human_female_01/rig_v1'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT / 'female-base.glb'), bone_heuristic='TEMPERANCE')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for action in bpy.data.actions:
    action.use_fake_user = True
if rig.animation_data:
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
rig.show_in_front = True
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'female-base.blend'))
print('Saved', len(rig.data.bones), 'bones;', len(bpy.data.actions), 'actions;',
      sum(bool(image.packed_file) for image in bpy.data.images), 'packed images')
