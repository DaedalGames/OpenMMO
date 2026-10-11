"""Save the editable bard boot assembly and render its game pose samples."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / 'assets/modular_human_male_01'
ASSETS = ROOT / 'assets/items/bard_starter/tripo_boots_v1'


def helper(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review = helper('review', 'tools/blender-scripts/review_rogue_fitting.py')
studio = helper('studio', 'tools/blender-scripts/review_tripo_pants.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    directory = args.images.resolve()
    assert not directory.is_relative_to(ROOT / 'assets')
    directory.mkdir(parents=True, exist_ok=True)
    report = json.loads((ROOT / 'doc/assets/modular-bard-tripo-boots-animation-v1.json').read_text())
    for source in report['sources'] + [report['snapshot']]:
        assert review.file_record(ROOT / source['path'])['sha256'] == source['sha256']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(PARTS / 'fitted/base.glb'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    body = [o for o in bpy.data.objects if o.type == 'MESH']
    for path in [PARTS / 'bard/tripo_boots_v1/boots_bard.glb',
                 PARTS / 'bard/tripo_top_v1/top_bard.glb', PARTS / 'fitted/hair_crop.glb',
                 ASSETS / 'pants-bard-boots-review.glb']:
        review.import_part(path, rig)
    for obj in body:
        review.clip_top_skin(obj, True, waist_height=1.08)
        obj.hide_render = obj.get('region') in ['upper_arms', 'torso', 'legs', 'ankles', 'boot_ankles', 'feet']
        obj.hide_set(obj.hide_render)
    scene, camera = studio.setup(False)

    def render(name, offset, center=(0, 0, .98), scale=2.13):
        center = Vector(center)
        camera.location = center + Vector(offset)
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(directory / f'{name}.png')
        bpy.ops.render.render(write_still=True)

    for name, offset in [('front', (0, -5, 0)), ('side', (-5, 0, 0)), ('back', (0, 5, 0))]:
        render(name, offset)
        render('boots-' + name, offset, (0, 0, .30), .78)
    review.contact_sheet(directory, ['front', 'side', 'back'], ['FRONT', 'SIDE', 'BACK'], 3, directory / 'set.png')
    review.contact_sheet(directory, ['boots-front', 'boots-side', 'boots-back'], ['FRONT', 'SIDE', 'BACK'], 3, directory / 'boots.png')
    conversion = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    ordered = sorted(rig.pose.bones, key=lambda b: len(b.parent_recursive))
    for bone in ordered:
        bone.rotation_mode = 'QUATERNION'

    def key(frame):
        for bone in ordered:
            for channel in ['location', 'rotation_quaternion', 'scale']:
                bone.keyframe_insert(data_path=channel, frame=frame)

    key(1)
    scene.timeline_markers.new('REST', frame=1)
    snapshots = json.loads((ASSETS / 'animation-snapshots.json').read_text())
    for index, snapshot in enumerate(snapshots, 1):
        frame = index * 10
        scene.frame_set(frame)
        for bone in ordered:
            values = snapshot['bone_deformation_matrices'][bone.name]
            deformation = Matrix([values[i:i + 4] for i in range(0, 16, 4)]).transposed()
            bone.matrix = rig.matrix_world.inverted() @ conversion @ deformation @ conversion.inverted() @ rig.matrix_world @ bone.bone.matrix_local
            bpy.context.view_layer.update()
        key(frame)
        scene.timeline_markers.new(snapshot['clip'], frame=frame)
        center = rig.matrix_world @ rig.pose.bones['Hips'].head + Vector((0, 0, -.23))
        render(snapshot['clip'], (-2.3, -5, .3), center, 1.9)
    names = [s['clip'] for s in snapshots if s['clip'] != 'combat_idle']
    review.contact_sheet(directory, names, ['IDLE', 'WALK', 'RUN', 'JUMP', 'SLASH', 'SIT'], 3, directory / 'motion.png')
    for layer in rig.animation_data.action.layers:
        for strip in layer.strips:
            for slot in rig.animation_data.action.slots:
                channels = strip.channelbag(slot)
                if channels:
                    for curve in channels.fcurves:
                        for point in curve.keyframe_points:
                            point.interpolation = 'CONSTANT'
    rig.animation_data.action.name = 'Sampled game poses - not continuous animation'
    scene.frame_end = len(snapshots) * 10
    scene.frame_set(1)
    references = bpy.data.collections.new('Unmodified source and interface references - hidden')
    scene.collection.children.link(references)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSETS / 'source.glb'))
    for obj in set(bpy.data.objects) - before:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        references.objects.link(obj)
    with bpy.data.libraries.load(str(PARTS / 'interfaces/v1/outfit-reference.blend'), link=False) as (source, target):
        target.objects = [n for n in source.objects if n.startswith(('boot_calf_', 'shoe_ankle_'))]
    for obj in target.objects:
        if obj:
            references.objects.link(obj)
    references.hide_render = references.hide_viewport = True
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    target = ASSETS / 'bard-boots-fitting.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    record = dict(date='2026-10-11', blend=review.file_record(target), sources=report['sources'],
        images_directory=str(directory), note='Matching-set assembly and fixed game pose samples; no continuous Blender animation or mixed-outfit certification.')
    (ROOT / 'doc/assets/modular-bard-tripo-boots-fitted-review-v1.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
