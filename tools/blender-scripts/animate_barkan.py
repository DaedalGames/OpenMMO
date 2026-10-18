import argparse
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('wing_io', ROOT / 'tools/blender-scripts/cut_barkan_wing_holes.py')
wing_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wing_io)
FPS = 24
FOLLOW_THROUGH = {
    'start': .66, 'slow_start': .7, 'slow_full': .82, 'slow_end': 1.1, 'resume': 1.35, 'slow_rate': .4,
    'twist_peak': 1.02, 'twist_hold': 1.12, 'twists': {'Spine': 17, 'Spine1': 15, 'Spine2': 13, 'Neck': -18},
}


def clear_pose(rig):
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def set_action(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]


def world_bounds(mesh):
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = np.empty(len(evaluated.data.vertices) * 3, dtype=np.float32)
    evaluated.data.vertices.foreach_get('co', points)
    points = points.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    points = points @ matrix[:3, :3].T + matrix[:3, 3]
    return points.min(0), points.max(0)


def load_motion(path, names, retime=None):
    before = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=str(path))
    imported = set(bpy.data.objects) - before
    source = next(obj for obj in imported if obj.type == 'ARMATURE')
    mapping = {name: next((bone.name for bone in source.data.bones if bone.name.split(':')[-1] == name), None) for name in names}
    mapping = {name: actual for name, actual in mapping.items() if actual}
    rest = {name: source.matrix_world @ source.data.bones[actual].matrix_local for name, actual in mapping.items()}
    start, end = source.animation_data.action.frame_range
    source_fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    duration = (end - start) / source_fps
    count = round(duration * FPS)
    times = retime(duration) if retime else [duration * index / count for index in range(count + 1)]
    frames = []
    for time in times:
        frame = start + (end - start) * time / duration
        bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
        frames.append({name: source.matrix_world @ source.pose.bones[actual].matrix for name, actual in mapping.items()})
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    for action in set(bpy.data.actions) - before_actions:
        bpy.data.actions.remove(action)
    return rest, frames, duration


def smoothstep(value, low, high, smoother=False):
    t = min(max((value - low) / (high - low), 0), 1)
    return t * t * t * (t * (t * 6 - 15) + 10) if smoother else t * t * (3 - 2 * t)


def follow_through_source_time(time):
    f = FOLLOW_THROUGH
    steps = math.ceil(time * 1000)
    source = 0
    for step in range(steps):
        at = (step + .5) * time / steps
        slow = smoothstep(at, f['slow_start'], f['slow_full']) * (1 - smoothstep(at, f['slow_end'], f['resume']))
        source += time / steps * (1 - (1 - f['slow_rate']) * slow)
    return source


def follow_through_times(duration):
    frames = math.ceil(duration * FPS)
    while follow_through_source_time(frames / FPS) < duration:
        frames += 1
    return [min(follow_through_source_time(index / FPS), duration) for index in range(frames + 1)]


# The source chop bottoms out near the floor, so the extra swing turns the torso
# about world up: the blade travels further without dropping.
def twist_follow_through(rig, time, duration):
    f = FOLLOW_THROUGH
    amount = smoothstep(time, f['start'], f['twist_peak'], True) * (1 - smoothstep(time, f['twist_hold'], duration - .1, True))
    up = (rig.matrix_world.to_3x3().inverted() @ Vector((0, 0, 1))).normalized()
    for name, degrees in f['twists'].items():
        bone = rig.pose.bones[name]
        pivot = bone.head.copy()
        turn = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees) * amount, 4, up) @ Matrix.Translation(-pivot)
        bone.matrix = turn @ bone.matrix
        bpy.context.view_layer.update()


def rotate_world_axis(bone, axis, angle):
    local_axis = bone.bone.matrix_local.to_quaternion().inverted() @ Vector(axis)
    bone.rotation_quaternion = Quaternion(local_axis, angle)


def bake_motion(rig, mesh, name, path):
    rig.animation_data_create()
    rig.animation_data.action = None
    clear_pose(rig)
    follow_through = name == 'Attack'
    source_rest, source_frames, source_duration = load_motion(
        path, [bone.name for bone in rig.data.bones], follow_through_times if follow_through else None)
    duration = (len(source_frames) - 1) / FPS if follow_through else source_duration
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1
    target_rest = {bone.name: rig.matrix_world @ bone.matrix_local for bone in rig.data.bones}
    def leg_length(rest):
        return sum((rest[side + child].translation - rest[side + parent].translation).length
                   for side in ['Left', 'Right'] for parent, child in [('UpLeg', 'Leg'), ('Leg', 'Foot')])

    factor = leg_length(target_rest) / leg_length(source_rest)
    first = source_frames[0]['Hips'].translation
    travel = source_frames[-1]['Hips'].translation - first
    root_motion = []
    for index, source in enumerate(source_frames):
        motion = (source['Hips'].translation - source_rest['Hips'].translation) * factor
        for axis in [0, 1]:
            motion[axis] -= (first[axis] - source_rest['Hips'].translation[axis]) * factor
            if name == 'Walk':
                motion[axis] -= travel[axis] * factor * index / (len(source_frames) - 1)
        root_motion.append(motion)
    if name == 'Walk':
        center = sum(root_motion[:-1], Vector()) / (len(root_motion) - 1)
        for motion in root_motion:
            motion.x -= center.x
            motion.y -= center.y
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    set_action(rig, action)
    previous = {}
    minimum, maximum = [], []
    for index, source in enumerate(source_frames):
        scene.frame_set(index)
        clear_pose(rig)
        for bone in rig.pose.bones:
            if bone.name not in source:
                continue
            rotation = source[bone.name].to_quaternion() @ source_rest[bone.name].to_quaternion().inverted() @ target_rest[bone.name].to_quaternion()
            rotation = rig.matrix_world.to_quaternion().inverted() @ rotation
            location = bone.head.copy()
            if bone.name == 'Hips':
                location = bone.bone.head_local + rig.matrix_world.to_3x3().inverted() @ root_motion[index]
            bone.matrix = Matrix.Translation(location) @ rotation.to_matrix().to_4x4()
            bpy.context.view_layer.update()
        if follow_through:
            twist_follow_through(rig, index / FPS, duration)
        phase = index / max(1, len(source_frames) - 1)
        for side, sign in [('Left', 1), ('Right', -1)]:
            angle = math.radians(2 * math.sin(phase * math.tau))
            rotate_world_axis(rig.pose.bones[side + 'WingRoot'], (0, 0, 1), sign * angle)
            chain = rig.pose.bones[side + 'WristChain']
            chain.matrix = Matrix.Translation(chain.head) @ (rig.matrix_world.inverted() @ target_rest[chain.name]).to_quaternion().to_matrix().to_4x4()
        bpy.context.view_layer.update()
        low, _ = world_bounds(mesh)
        hip = rig.pose.bones['Hips']
        adjusted = hip.matrix.copy()
        adjusted.translation += rig.matrix_world.to_3x3().inverted() @ Vector((0, 0, -low[2]))
        hip.matrix = adjusted
        bpy.context.view_layer.update()
        low, high = world_bounds(mesh)
        minimum.append(float(low[2])); maximum.append(float(high[2]))
        for bone in rig.pose.bones:
            quaternion = bone.rotation_quaternion
            if bone.name in previous and quaternion.dot(previous[bone.name]) < 0:
                quaternion.negate()
            previous[bone.name] = quaternion.copy()
            bone.keyframe_insert(data_path='rotation_quaternion', frame=index, group=bone.name)
            if bone.name == 'Hips':
                bone.keyframe_insert(data_path='location', frame=index, group=bone.name)
    extra = {'source_duration': source_duration, 'follow_through': FOLLOW_THROUGH} if follow_through else {}
    return action, {'name': name, 'frames': len(source_frames), 'duration': duration, **extra,
                    'min_ground_m': min(minimum), 'max_ground_m': max(minimum),
                    'max_height_m': max(maximum), 'root_translation_ratio': factor,
                    'root_translation_scale_basis': 'summed upper/lower leg lengths; independent of source origin',
                    'lateral_root_span_m': max(motion.x for motion in root_motion) - min(motion.x for motion in root_motion),
                    'source': str(path.relative_to(ROOT)), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def bake_wing_test(rig):
    action = bpy.data.actions.new('WingFold')
    action.use_fake_user = True
    set_action(rig, action)
    clear_pose(rig)
    for frame in range(49):
        bpy.context.scene.frame_set(frame)
        clear_pose(rig)
        amount = .5 - .5 * math.cos(frame / 48 * math.tau)
        for side, sign in [('Left', 1), ('Right', -1)]:
            rotate_world_axis(rig.pose.bones[side + 'WingRoot'], (0, 0, 1), sign * math.radians(40) * amount)
            rotate_world_axis(rig.pose.bones[side + 'WingArm'], (0, 0, 1), sign * math.radians(12) * amount)
        for bone in rig.pose.bones:
            bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone.name)
    return action


def render_review(rig, mesh, actions, directory):
    scene = bpy.context.scene
    materials = list(mesh.data.materials)
    for index, original in enumerate(materials):
        material = original.copy()
        mesh.data.materials[index] = material
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = next(node for node in nodes if node.type == 'BSDF_PRINCIPLED')
        output = next(node for node in nodes if node.type == 'OUTPUT_MATERIAL')
        emission = nodes.new('ShaderNodeEmission')
        links.new(shader.inputs['Base Color'].links[0].from_socket, emission.inputs['Color'])
        links.new(emission.outputs[0], output.inputs['Surface'])
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'Standard'
    camera_data = bpy.data.cameras.new('Review camera')
    camera_data.type = 'ORTHO'; camera_data.ortho_scale = 3.7
    camera = bpy.data.objects.new('Review camera', camera_data)
    scene.collection.objects.link(camera); scene.camera = camera
    center = Vector((0, .35, 1.25))
    views = [('front', (0, -5, 0)), ('angle', (4, -6, 1.5)), ('back', (0, 5, 0))]
    for name, frame in [('Bind', 0), ('Idle', 12), ('Walk', 8), ('WingFold', 24), ('Attack', 16), ('Death', 48)]:
        if name != 'Bind' and name not in actions:
            continue
        rig.animation_data.action = None
        clear_pose(rig)
        if name != 'Bind':
            set_action(rig, actions[name]); scene.frame_set(frame)
        for view, offset in views[:2] if name != 'Bind' else views:
            camera.location = center + Vector(offset)
            camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(directory / f'{name.lower()}-{view}.png')
            bpy.ops.render.render(write_still=True)
    for index, material in enumerate(materials):
        mesh.data.materials[index] = material
    bpy.data.objects.remove(camera, do_unlink=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--game-output', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = args.game_output or args.model
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()), bone_heuristic='TEMPERANCE')
    rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
    mesh = next(obj for obj in bpy.data.objects if obj.type == 'MESH')
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    clear_pose(rig)
    rig.name = 'BarkanRig'
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.unit_settings.length_unit = 'METERS'
    scene.render.fps, scene.render.fps_base = FPS, 1
    actions, reports = {}, []
    for name in ['Idle', 'Walk'] + (['Attack', 'Death'] if args.game_output else []):
        source = (ROOT / f'assets/monsters/barkan/fbx/Orc_{name}.fbx' if name in ['Idle', 'Walk']
                  else ROOT / f'assets/monsters/skeleton_knight/fbx/{name}.fbx')
        action, report = bake_motion(rig, mesh, name, source)
        actions[name] = action; reports.append(report)
    if not args.game_output:
        actions['WingFold'] = bake_wing_test(rig)
    rig.animation_data.action = None
    clear_pose(rig)
    low, high = world_bounds(mesh)
    assert abs(high[2] - low[2] - 2.5) < 1e-5
    assert abs(low[2]) < 1e-5
    assert all(abs(value - 1) < 1e-6 for obj in [rig, mesh] for value in obj.scale)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); mesh.select_set(True)
    bpy.context.view_layer.objects.active = rig
    rig.show_in_front = True
    for bone in rig.data.bones:
        bone.use_deform = True
    with tempfile.TemporaryDirectory(prefix='barkan-textures-') as temporary:
        original = Path(temporary) / 'original.glb'
        original.write_bytes(args.model.read_bytes())
        bpy.ops.export_scene.gltf(
            filepath=str(output.resolve()), export_format='GLB', use_selection=True,
            export_skins=True, export_animations=True, export_animation_mode='ACTIONS',
            export_rest_position_armature=True, export_force_sampling=True,
            export_image_format='WEBP', export_image_quality=90,
            export_extras=True, export_leaf_bone=False,
        )
        wing_io.restore_textures(original, output)
    document, binary = wing_io.read_glb(output)
    for node in document['nodes']:
        if 'scale' in node and max(abs(value - 1) for value in node['scale']) < .00003:
            node.pop('scale')
    for animation in document.get('animations', []):
        channels = []
        for channel in animation['channels']:
            if channel['target']['path'] == 'scale':
                sampler = animation['samplers'][channel['sampler']]
                index = sampler['output']
                accessor = document['accessors'][index]
                view = document['bufferViews'][accessor['bufferView']]
                values = np.frombuffer(binary, dtype='<f4', count=accessor['count'] * 3,
                                       offset=view.get('byteOffset', 0) + accessor.get('byteOffset', 0))
                if np.max(abs(values - 1)) < .00003:
                    continue
            channels.append(channel)
        animation['channels'] = channels
    wing_io.write_glb(output, document, binary)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.type = 'MATERIAL'
                region = area.spaces.active.region_3d
                region.view_location = Vector((0, 0, 1.2))
                region.view_distance = 4
                region.view_rotation = Vector((3, -6, 2)).to_track_quat('Z', 'Y')
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend').resolve()))
    report_path = ROOT / 'doc/assets/barkan-rig-v1.json'
    report = json.loads(report_path.read_text())
    report['output'] = str(output.resolve().relative_to(ROOT))
    report['animations'] = reports
    report['locomotion'] = {'movement_clip': 'Walk', 'running_enabled': False,
                            'unused_run_source': 'assets/monsters/skeleton_knight/fbx/Run.fbx'}
    report['idle_retargeting'] = {
        'animation': 'Orc Idle', 'provider': 'Adobe Mixamo', 'supplied_by': 'user',
        'download_date': '2026-10-18', 'original_path': '/mnt/y/web_downloads/Orc Idle.fbx',
        'source_conditions': 'User-provided Mixamo download; original Mixamo terms apply; local retargeting, no paid generation.',
        'method': 'Retarget the original Orc Idle body motion to the fitted Barkan rig; scale root motion by the leg-length ratio, keep the feet grounded, and add independent wing sway and hanging wrist chains.',
        'superseded': {'status': 'unused', 'source': 'assets/monsters/skeleton_knight/fbx/Idle.fbx'},
    }
    report['walk_retargeting'] = {
        'animation': 'Orc Walk', 'provider': 'Adobe Mixamo', 'supplied_by': 'user',
        'download_date': '2026-10-18', 'original_path': '/mnt/y/web_downloads/Orc Walk.fbx',
        'source_conditions': 'User-provided Mixamo download; original Mixamo terms apply; local retargeting, no paid generation.',
        'method': 'Retarget the original Orc Walk body motion to the fitted Barkan rig; scale root motion by the leg-length ratio, remove forward travel and center horizontal sway for in-place playback, keep the feet grounded, and add independent wing sway and hanging wrist chains.',
        'superseded': {'status': 'unused', 'source': 'assets/monsters/skeleton_knight/fbx/Walk.fbx'},
    }
    report['wing_fold_test'] = {'name': 'WingFold', 'frames': 49, 'duration': 2, 'root_fold_degrees': 40, 'arm_fold_degrees': 12}
    if args.game_output:
        runtime = ROOT / 'client/public/models/monsters/barkan.glb'
        runtime.write_bytes(output.read_bytes())
        report_path = ROOT / 'doc/assets/barkan-game-v1.json'
        report.pop('wing_fold_test', None)
        report['runtime'] = str(runtime.relative_to(ROOT))
        report['combat_motion_status'] = 'Temporary retargeted skeleton knight Attack and Death; unarmed movement review, final boss attacks and weapon fitting pending.'
    report['blender_units'] = {'system': 'METRIC', 'scale_length': 1, 'length_unit': 'METERS'}
    report['blender_object_scales'] = {obj.name: list(obj.scale) for obj in [rig, mesh]}
    report['output_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(reports), flush=True)
    if args.review:
        args.review.mkdir(parents=True, exist_ok=True)
        render_review(rig, mesh, actions, args.review)


if __name__ == '__main__':
    main()
