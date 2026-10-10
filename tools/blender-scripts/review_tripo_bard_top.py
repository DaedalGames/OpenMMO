"""Render bard fitting evidence and save an editable canonical-rig scene."""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / 'assets/modular_human_male_01'
OUTPUT = PARTS / 'bard/tripo_top_v1'
SOURCE = ROOT / 'assets/items/bard_starter/tripo_top_v1/source.glb'
IMAGES = OUTPUT / 'review'
spec = importlib.util.spec_from_file_location('review', ROOT / 'tools/blender-scripts/review_rogue_fitting.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def main(directory):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rest-only', action='store_true')
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(PARTS / 'fitted/base.glb'))
    rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
    body = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    for obj in body:
        obj.hide_render = obj.get('region') in ['boot_ankles', 'legs']
        obj.hide_set(obj.hide_render)
    top = review.import_part(OUTPUT / 'top_bard.glb', rig)
    review.import_part(PARTS / 'fitted/hair_crop.glb', rig)
    review.import_part(PARTS / 'fitted/pants_cloth.glb', rig)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12 if args.quick else 32
    scene.world = bpy.data.worlds.new('Bard review')
    scene.world.color = (.18, .18, .18)
    center = Vector((0, 0, 1.35))
    for location, energy in [((-3, -4, 5), 600), ((4, -2, 3), 450), ((0, 3, 4), 650)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object
        light.data.energy, light.data.shape, light.data.size = energy, 'DISK', 4
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = 700, 900
    scene.render.resolution_percentage = 70 if args.quick else 100
    scene.view_settings.view_transform = 'AgX'
    IMAGES.mkdir(parents=True, exist_ok=True)

    def render(name, offset, target=center, scale=1.32):
        camera.location = target + Vector(offset)
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(directory / f'{name}.png')
        bpy.ops.render.render(write_still=True)

    for name, offset in [('front', (0, -5, 0)), ('side', (-5, 0, 0)), ('back', (0, 5, 0))]:
        render(name, offset)
    review.contact_sheet(directory, ['front', 'side', 'back'], ['FRONT', 'SIDE', 'BACK'], 3, IMAGES / 'rest.png')
    for name, target, offset in [
        ('neck', (0, .02, 1.61), (0, -4, .3)),
        ('left_cuff', (.427, .047, 1.029), (.8, -4, .2)),
        ('right_cuff', (-.427, .047, 1.029), (-.8, -4, .2)),
    ]:
        render(name, offset, Vector(target), .34)
    review.contact_sheet(directory, ['neck', 'left_cuff', 'right_cuff'], ['COLLAR', 'LEFT CUFF', 'RIGHT CUFF'], 3, IMAGES / 'openings.png')
    if not args.rest_only:
        report = json.loads((ROOT / 'doc/assets/modular-bard-tripo-top-animation-v1.json').read_text())
        for source in report['sources']:
            assert review.file_record(ROOT / source['path'])['sha256'] == source['sha256']
        snapshots = json.loads((OUTPUT / 'animation-snapshots.json').read_text())
        for obj in body:
            review.clip_top_skin(obj, tripo_top=True, waist_height=1.08)
            if obj.get('region') == 'upper_arms':
                obj.hide_render = True
                obj.hide_set(True)
        conversion = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        ordered = sorted(rig.pose.bones, key=lambda bone: len(bone.parent_recursive))
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'

        def key_pose(frame):
            for bone in rig.pose.bones:
                for channel in ['location', 'rotation_quaternion', 'scale']:
                    bone.keyframe_insert(data_path=channel, frame=frame)

        key_pose(1)
        scene.timeline_markers.new('REST', frame=1)
        for index, snapshot in enumerate(snapshots, 1):
            frame = index * 10
            scene.frame_set(frame)
            for bone in ordered:
                values = snapshot['bone_deformation_matrices'].get(bone.name)
                if values is not None:
                    deformation = Matrix([values[i:i + 4] for i in range(0, 16, 4)]).transposed()
                    bone.matrix = rig.matrix_world.inverted() @ conversion @ deformation @ conversion.inverted() @ rig.matrix_world @ bone.bone.matrix_local
                    bpy.context.view_layer.update()
            key_pose(frame)
            scene.timeline_markers.new(snapshot['clip'], frame=frame)
            pose_center = rig.matrix_world @ rig.pose.bones['Hips'].head + Vector((0, 0, .32))
            render(snapshot['clip'], (-2.3, -5, .6), pose_center, 2.0 if snapshot['clip'] == 'jump' else 1.45)
            if snapshot['clip'] in ['run', 'slash1', 'sit_idle']:
                render(snapshot['clip'] + '_back', (1.5, 5, .6), pose_center, 1.45)
        for layer in rig.animation_data.action.layers:
            for strip in layer.strips:
                for slot in rig.animation_data.action.slots:
                    channels = strip.channelbag(slot)
                    if channels:
                        for curve in channels.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = 'CONSTANT'
        rig.animation_data.action.name = 'Sampled game poses'
        scene.frame_end = len(snapshots) * 10
        scene.frame_set(1)
        names = [p['clip'] for p in snapshots if p['clip'] != 'combat_idle']
        review.contact_sheet(directory, names, ['IDLE', 'WALK', 'RUN', 'JUMP', 'SLASH', 'SIT'], 3, IMAGES / 'motion.png')
        review.contact_sheet(directory, ['run_back', 'slash1_back', 'sit_idle_back'], ['RUN BACK', 'SLASH BACK', 'SIT BACK'], 3, IMAGES / 'motion-back.png')
    if not args.quick:
        references = bpy.data.collections.new('Unmodified source - hidden')
        scene.collection.children.link(references)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(SOURCE))
        for obj in set(bpy.data.objects) - before:
            for collection in list(obj.users_collection):
                collection.objects.unlink(obj)
            references.objects.link(obj)
        references.hide_render = references.hide_viewport = True
        bpy.ops.object.select_all(action='DESELECT')
        top[0].select_set(True)
        bpy.context.view_layer.objects.active = top[0]
        bpy.ops.file.pack_all()
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'bard-top-fitting.blend'))
        images = ['rest.png', 'openings.png']
        if not args.rest_only:
            images += ['motion.png', 'motion-back.png']
        record = dict(date='2026-10-10', blender_version=bpy.app.version_string,
                      status='Editable fitting and rigging result; runtime registration and mixed equipment approval separate',
                      model=review.file_record(OUTPUT / 'top_bard.glb'),
                      editable=review.file_record(OUTPUT / 'bard-top-fitting.blend'),
                      images=[review.file_record(IMAGES / name) for name in images],
                      source=review.file_record(SOURCE),
                      fitting=review.file_record(ROOT / 'doc/assets/modular-bard-tripo-top-fitting-v1.json'),
                      unmasked_views=['rest', 'openings'],
                      animation_mask=dict(torso_retained_below_m=1.08, hidden_regions=['upper_arms'],
                                          neck_lower_trim_m=1.54, hands_and_forearms_preserved=True,
                                          canonical_base_unchanged=True, runtime_mask_implemented=False),
                      context='Existing crop hair and cloth pants; source hidden in separate collection',
                      timeline='Rest and sampled game poses, constant interpolation')
        (ROOT / 'doc/assets/modular-bard-tripo-top-fitted-review-v1.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='bard-top-review-') as temporary:
        main(Path(temporary))
