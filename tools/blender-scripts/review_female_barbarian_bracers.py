import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/items/female_barbarian_bracers/tripo_v1/fitted_v1'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
body = bpy.data.objects['female_body']
for track in rig.animation_data.nla_tracks:
    track.mute = True
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()


def add_part(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), bone_heuristic='TEMPERANCE')
    added = set(bpy.data.objects) - before
    meshes = [obj for obj in added if obj.type == 'MESH']
    for obj in meshes:
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.matrix_world = world
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
    for obj in added:
        if obj.type != 'MESH':
            bpy.data.objects.remove(obj, do_unlink=True)
    return meshes


bracers = add_part(OUT / 'gloves_female_barbarian.glb')
hidden = set(json.loads((OUT / 'body-occlusion.json').read_text())['hide_triangle_indices'])
bm = bmesh.new()
bm.from_mesh(body.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in hidden], context='FACES')
bm.to_mesh(body.data)
bm.free()
for action in bpy.data.actions:
    action.use_fake_user = True
rig.show_in_front = True
bpy.context.view_layer.update()
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'female-barbarian-bracers-fitted.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.20, .20, .20, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
for position, power in [((2, -3, 3), 260), ((-2, -1, 2), 220), ((0, 3, 2), 300)]:
    bpy.ops.object.light_add(type='AREA', location=position)
    light = bpy.context.object
    light.data.energy, light.data.size = power, 3
    light.rotation_euler = (Vector((0, 0, .65)) - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 900
scene.view_settings.view_transform = 'AgX'
review = OUT / 'review'
review.mkdir(exist_ok=True)


def render(name, center, offset, span):
    camera.data.ortho_scale = span
    camera.location = Vector(center) + Vector(offset)
    camera.rotation_euler = (Vector(center) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(review / f'{name}.png')
    bpy.ops.render.render(write_still=True)


render('rest-front', (0, 0, .67), (0, -2, .05), .79)
render('right-outer', (-.22, 0, .65), (-1, -.4, .5), .26)
render('right-inner', (-.22, 0, .65), (1, -.6, -.2), .26)
render('left-outer', (.22, 0, .65), (1, -.4, .5), .26)
for name in ['combat_idle', 'idle_armed', 'run', 'slash1', 'sit_idle']:
    action = next(action for action in bpy.data.actions if action.name == name)
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(sum(action.frame_range) / 2))
    bpy.context.view_layer.update()
    center = (rig.matrix_world @ rig.pose.bones['RightForeArm'].head + rig.matrix_world @ rig.pose.bones['RightHandMiddle2'].head) / 2
    render(name, center, (-1, -1, .7), .34)
