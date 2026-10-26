import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / (sys.argv[sys.argv.index('--directory') + 1] if '--directory' in sys.argv else 'assets/items/female_rogue_gloves/tripo_v1/fitted_v1')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
body = bpy.data.objects['female_body']
if rig.animation_data:
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


gloves = add_part(OUT / 'gloves_female_rogue.glb')
hidden = set(json.loads((OUT / 'body-occlusion.json').read_text())['hide_triangle_indices'])
for directory, name in [
    ('female_rogue_top/tripo_v1/fitted_v6', 'top_female_rogue'),
    ('female_rogue_skirt/tripo_v1/fitted_v6', 'bottom_female_rogue'),
    ('female_rogue_boots/tripo_v1/fitted_v3', 'boots_female_rogue'),
]:
    folder = ROOT / 'assets/items' / directory
    add_part(folder / (name + '.glb'))
    hidden.update(json.loads((folder / 'body-occlusion.json').read_text())['hide_triangle_indices'])
reference = body.copy()
reference.data = body.data.copy()
bpy.context.collection.objects.link(reference)
reference.name = 'female_body_unmasked_reference'
reference.hide_render = True
reference.hide_set(True)
bm = bmesh.new()
bm.from_mesh(body.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in hidden], context='FACES')
bm.to_mesh(body.data)
bm.free()
for action in bpy.data.actions:
    action.use_fake_user = True
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.16, .16, .16, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
for position, power, size in [((2, -3, 4), 700, 2), ((-3, -1, 3), 900, 2), ((0, 3, 3), 1000, 2)]:
    bpy.ops.object.light_add(type='AREA', location=position)
    light = bpy.context.object
    light.data.energy, light.data.size = power, size
    light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 768
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = -1
review = OUT / 'review'
review.mkdir(exist_ok=True)
hand_skin = reference.copy()
hand_skin.data = reference.data.copy()
bpy.context.collection.objects.link(hand_skin)
hand_skin.name = 'hand_skin_review'
hand_skin.hide_set(False)
hand_skin.hide_render = False
bm = bmesh.new()
bm.from_mesh(hand_skin.data)
bmesh.ops.delete(bm, geom=[face for face in bm.faces if not all(abs(v.co.x) > .405 and .87 < v.co.z < 1.19 for v in face.verts)], context='FACES')
bm.to_mesh(hand_skin.data)
bm.free()
outfit_meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj not in [*gloves, reference, hand_skin]]
for obj in outfit_meshes:
    obj.hide_render = True


def render(name, center, offset, span):
    camera.data.ortho_scale = span
    camera.location = Vector(center) + Vector(offset)
    camera.rotation_euler = (Vector(center) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(review / (name + '.png'))
    bpy.ops.render.render(write_still=True)


def hand_camera(side):
    wrist = rig.matrix_world @ rig.pose.bones[side + 'Hand'].head
    middle = rig.matrix_world @ rig.pose.bones[side + 'HandMiddle1'].head
    index = rig.matrix_world @ rig.pose.bones[side + 'HandIndex1'].head
    pinky = rig.matrix_world @ rig.pose.bones[side + 'HandPinky1'].head
    normal = (middle - wrist).cross(index - pinky).normalized()
    if side == 'Left':
        normal = -normal
    return (wrist + middle) / 2, normal


bpy.context.view_layer.update()
for side in ['Right', 'Left']:
    center, normal = hand_camera(side)
    for view, sign in [('dorsal', 1), ('palmar', -1)]:
        render(f'rest-{side.lower()}-{view}', center, normal * sign * 2, .245)
for obj in outfit_meshes:
    obj.hide_render = False
hand_skin.hide_render = True
render('outfit-front', (0, 0, .94), (0, -4, .08), 1.95)
for obj in outfit_meshes:
    obj.hide_render = True
hand_skin.hide_render = False
for name in ['combat_idle', 'slash1', 'run', 'sit_idle']:
    action = next(action for action in bpy.data.actions if action.name == name)
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(sum(action.frame_range) / 2))
    bpy.context.view_layer.update()
    for side in ['Right', 'Left']:
        center, normal = hand_camera(side)
        render(f'{name}-{side.lower()}', center, normal * 2, .27)
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
center, normal = hand_camera('Right')
camera.location = center + normal * 2
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.ortho_scale = .245
rig.show_in_front = True
for obj in outfit_meshes:
    obj.hide_render = False
bpy.data.objects.remove(hand_skin, do_unlink=True)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'female-rogue-gloves-fitted.blend'))
