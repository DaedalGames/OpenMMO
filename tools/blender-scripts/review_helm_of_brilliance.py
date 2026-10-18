import argparse
import json
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor
parser = argparse.ArgumentParser()
parser.add_argument('sex', choices=['male', 'female'])
parser.add_argument('--directory', type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = ROOT / (args.directory or Path('assets/items/helm_of_brilliance/tripo_v2/fitted_v3') / args.sex)
fitting = json.loads((OUT / 'fitting.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
body_path = ROOT / fitting['body']['path']
mask_path = OUT / 'body-occlusion.json'
with tempfile.TemporaryDirectory() as temporary:
    if mask_path.exists():
        mask = json.loads(mask_path.read_text())
        if mask['hide_triangle_indices'] or mask.get('vertex_adjustments'):
            body, binary = read_glb(body_path)
            primitive = body['meshes'][mask['mesh_index']]['primitives'][mask['primitive_index']]
            faces = accessor(body, binary, primitive['indices']).reshape(-1, 3)
            hidden = set(mask['hide_triangle_indices'])
            faces = faces[[i not in hidden for i in range(len(faces))]]
            binary = bytearray(binary)
            primitive['indices'] = add_accessor(body, binary, faces.reshape(-1, 1), 'SCALAR', 5125)
            if mask.get('vertex_adjustments'):
                attrs = primitive['attributes']
                positions = accessor(body, binary, attrs['POSITION']).copy()
                normals = accessor(body, binary, attrs['NORMAL']).copy()
                for item in mask['vertex_adjustments']:
                    positions[item['vertex']] = item['position']
                    normals[item['vertex']] = item['normal']
                attrs['POSITION'] = add_accessor(body, binary, positions, 'VEC3')
                attrs['NORMAL'] = add_accessor(body, binary, normals, 'VEC3')
            body_path = Path(temporary) / 'masked-body.glb'
            write_glb(body_path, body, binary)
    bpy.ops.import_scene.gltf(filepath=str(body_path), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
if rig.animation_data:
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rig.animation_data.action = None
else:
    rig.animation_data_create()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.get('region') in ['ankles', 'boot_ankles']:
        obj.hide_render = True
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(OUT / 'helmet_brilliance.glb'), bone_heuristic='TEMPERANCE')
added = set(bpy.data.objects) - before
for obj in added:
    if obj.type != 'MESH':
        continue
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_world = world
    for modifier in obj.modifiers:
        if modifier.type == 'ARMATURE':
            modifier.object = rig
for obj in added:
    if obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.20, .20, .20, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
for position, power in [((3, -5, 5), 900), ((-3, -2, 3), 650), ((0, 5, 4), 1000)]:
    bpy.ops.object.light_add(type='AREA', location=position)
    light = bpy.context.object
    light.data.energy, light.data.size = power, 5
    light.rotation_euler = (Vector((0, 0, 1.5)) - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 800
scene.view_settings.view_transform = 'AgX'
review = OUT / 'review'
review.mkdir(exist_ok=True)
center = Vector((0, 0, fitting['offset_xyz'][1]))


def render(name, target, offset, span):
    camera.data.ortho_scale = span
    camera.location = target + Vector(offset)
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(review / f'{name}.png')
    bpy.ops.render.render(write_still=True)


for name, offset in [('front', (0, -3, 0)), ('side', (-3, 0, 0)),
                     ('back', (0, 3, 0)), ('angle', (-2, -3, .5))]:
    render('head-' + name, center, offset, .64)
render('rest-upper', Vector((0, 0, fitting['offset_xyz'][1] - .38)), (0, -4, .1), 1.35)
conversion = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
to_blender = rig.matrix_world.inverted() @ conversion
from_blender = conversion.inverted() @ rig.matrix_world
ordered = sorted(rig.pose.bones, key=lambda bone: len(bone.parent_recursive))
for bone in ordered:
    bone.rotation_mode = 'QUATERNION'
    for channel in ['location', 'rotation_quaternion', 'scale']:
        bone.keyframe_insert(data_path=channel, frame=1)
snapshots = json.loads((OUT / 'animation-snapshots.json').read_text())
for index, snapshot in enumerate(snapshots, 1):
    frame = index * 10
    scene.frame_set(frame)
    for bone in ordered:
        values = snapshot['bone_deformation_matrices'].get(bone.name)
        if values:
            deformation = Matrix([values[i:i + 4] for i in range(0, 16, 4)]).transposed()
            bone.matrix = to_blender @ deformation @ from_blender @ bone.bone.matrix_local
            bpy.context.view_layer.update()
        for channel in ['location', 'rotation_quaternion', 'scale']:
            bone.keyframe_insert(data_path=channel, frame=frame)
    scene.timeline_markers.new(snapshot['clip'], frame=frame)
    target = rig.matrix_world @ rig.pose.bones['Head'].head
    render(snapshot['clip'], target + Vector((0, 0, .06)), (-2, -3, .5), .90)
scene.frame_start, scene.frame_end = 1, len(snapshots) * 10
scene.frame_set(1)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/items/helm_of_brilliance/tripo_v2/source/model_url.glb'))
references = bpy.data.collections.new('Unmodified Tripo source')
scene.collection.children.link(references)
for obj in set(bpy.data.objects) - before:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    references.objects.link(obj)
references.hide_render = references.hide_viewport = True
rig.show_in_front = True
camera.data.ortho_scale = .64
camera.location = center + Vector((-2, -3, .5))
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'helm-brilliance-{args.sex}-fitted.blend'))
