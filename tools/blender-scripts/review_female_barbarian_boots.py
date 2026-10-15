import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'assets/items/female_barbarian_boots/tripo_v1/fitted_v3'
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import add_accessor

body_doc, body_raw = read_glb(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
body_raw = bytearray(body_raw)
offsets = {entry['name']: entry['lifts'] for entry in json.loads((OUTPUT / 'heel-animation-offsets.json').read_text())}
node_ids = {node.get('name'): i for i, node in enumerate(body_doc['nodes'])}
for animation in body_doc['animations']:
    frames = offsets[animation['name']]
    rotations = frames[0]['rotations']
    replaced = {(node_ids[name], 'rotation') for name in rotations} | {(node_ids['Hips'], 'translation')}
    animation['channels'] = [channel for channel in animation['channels'] if (channel['target']['node'], channel['target']['path']) not in replaced]
    times = add_accessor(body_doc, body_raw, np.array([f['time'] for f in frames])[:, None], 'SCALAR')
    body_doc['accessors'][times].update(min=[frames[0]['time']], max=[frames[-1]['time']])
    for name, path in [(name, 'rotation') for name in rotations] + [('Hips', 'translation')]:
        values = np.array([f['rotations'][name] if path == 'rotation' else np.array(f['hips']) + [0, f['lift'], 0] for f in frames])
        output = add_accessor(body_doc, body_raw, values, 'VEC4' if path == 'rotation' else 'VEC3')
        sampler = len(animation['samplers'])
        animation['samplers'].append({'input': times, 'output': output, 'interpolation': 'LINEAR'})
        animation['channels'].append({'sampler': sampler, 'target': {'node': node_ids[name], 'path': path}})
body_doc['buffers'][0]['byteLength'] = len(body_raw)
write_glb(OUTPUT / 'body-high-heels-review.glb', body_doc, body_raw)
REVIEW = OUTPUT / 'review'
REVIEW.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUTPUT / 'body-high-heels-review.glb'), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
body = bpy.data.objects['female_body']
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(OUTPUT / 'boots_female_barbarian.glb'), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects) - before
for obj in imported:
    if obj.type == 'MESH':
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.matrix_world = world
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
for obj in imported:
    if obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
for track in rig.animation_data.nla_tracks:
    track.mute = True
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
for side in ['Left', 'Right']:
    foot, toe = [rig.data.bones[side + suffix] for suffix in ['Foot', 'ToeBase']]
    forward = toe.head_local - foot.head_local
    forward.z = 0
    axis = Vector((0, 0, 1)).cross(forward.normalized())
    for bone, degrees in [(foot, 30), (toe, -30)]:
        local_axis = bone.matrix_local.to_quaternion().inverted() @ axis
        rig.pose.bones[bone.name].rotation_quaternion = Quaternion(local_axis, math.radians(degrees))
lift = json.loads((OUTPUT / 'runtime-validation.json').read_text())['heel_posture']['root_lift']
hips = rig.pose.bones['Hips']
hips.location = rig.data.bones['Hips'].matrix_local.to_quaternion().inverted() @ Vector((0, 0, lift))
bpy.context.view_layer.update()
reference = body.copy()
reference.data = body.data.copy()
bpy.context.collection.objects.link(reference)
reference.name = 'unmasked_body_reference'
reference.hide_render = True
reference.hide_set(True)
mask = json.loads((OUTPUT / 'body-occlusion.json').read_text())
bm = bmesh.new()
bm.from_mesh(body.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in mask['hide_triangle_indices']], context='FACES')
bm.to_mesh(body.data)
bm.free()
for action in bpy.data.actions:
    action.use_fake_user = True
rig.show_in_front = True
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-barbarian-boots-fitted.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Review')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.3, .3, .3, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
for location, power in [((2, -3, 3), 300), ((-2, -1, 2), 200), ((0, 3, 2), 250)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.data.energy, light.data.size = power, 3
    light.rotation_euler = (Vector((0, 0, .4)) - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
scene.camera = camera
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.view_settings.view_transform = 'AgX'


def render(name, offset, center=(0, 0, .085), scale=.44):
    scene.render.resolution_x, scene.render.resolution_y = (1200, 600) if name.startswith('rest-') else (900, 900)
    center = Vector(center)
    camera.data.ortho_scale = scale
    camera.location = center + Vector(offset)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'{name}.png')
    bpy.ops.render.render(write_still=True)


for name, offset in [('front', (0, -3, .1)), ('side', (3, 0, .1)), ('back', (0, 3, .1)), ('angle', (1.8, -3, .3))]:
    render('rest-' + name, offset)
render('full', (1.4, -3, .2), (0, 0, .51), 1.14)
for name in ['idle1', 'walk', 'run', 'jump', 'slash1', 'sit_idle']:
    action = next((a for a in bpy.data.actions if a.name == name), None)
    if not action:
        continue
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frame = action.frame_range[0] + .35 * (action.frame_range[1] - action.frame_range[0])
    scene.frame_set(int(frame), subframe=frame % 1)
    render('pose-' + name, (1.8, -3, .25), (0, 0, .35), .85)

command = ['ffmpeg', '-y', '-loglevel', 'error']
for view in ['front', 'side', 'back', 'angle']:
    command.extend(['-i', str(REVIEW / f'rest-{view}.png')])
command.extend(['-filter_complex', '[0:v]scale=600:300[a];[1:v]scale=600:300[b];[2:v]scale=600:300[c];[3:v]scale=600:300[d];[a][b][c][d]hstack=inputs=4[out]',
                '-map', '[out]', '-frames:v', '1', str(REVIEW / 'strip.png')])
subprocess.run(command, check=True)
