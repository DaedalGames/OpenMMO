"""Save bard trousers on the canonical rig and render outside the asset tree."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / 'assets/modular_human_male_01'
OUTPUT = PARTS / 'bard/tripo_pants_v1'
SOURCE = ROOT / 'assets/items/bard_starter/tripo_pants_v1/source.glb'


def helper(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review = helper('review', 'tools/blender-scripts/review_rogue_fitting.py')
trousers = helper('trousers', 'tools/blender-scripts/review_tripo_pants.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', required=True, type=Path)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--rest-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    directory = args.images.resolve()
    assert not directory.is_relative_to(ROOT / 'assets')
    directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(PARTS / 'fitted/base.glb'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    body = [o for o in bpy.data.objects if o.type == 'MESH']
    pants = review.import_part(OUTPUT / 'pants_bard.glb', rig)
    top = review.import_part(PARTS / 'bard/tripo_top_v1/top_bard.glb', rig)
    hair = review.import_part(PARTS / 'fitted/hair_crop.glb', rig)

    def triangles(objects):
        total = 0
        for obj in objects:
            if any(c.name.startswith('glTF_not_exported') for c in obj.users_collection):
                continue
            obj.data.calc_loop_triangles()
            total += len(obj.data.loop_triangles)
        return total

    assembled = dict(body=triangles(body), pants=triangles(pants), top=triangles(top), hair=triangles(hair))
    for obj in body:
        obj.hide_render = obj.get('region') == 'boot_ankles'
    for obj in top:
        obj.hide_render = True
    scene, camera = trousers.setup(args.quick)

    def render(name, offset, target=(0, 0, .66), scale=1.48):
        target = Vector(target)
        camera.location = target + Vector(offset)
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(directory / f'{name}.png')
        bpy.ops.render.render(write_still=True)

    for name, offset in [('front', (0, -5, 0)), ('side', (-5, 0, 0)), ('back', (0, 5, 0))]:
        render(name, offset)
    review.contact_sheet(directory, ['front', 'side', 'back'], ['SKIN FRONT', 'SKIN SIDE', 'SKIN BACK'],
                         3, directory / 'rest.png')
    for obj in top:
        obj.hide_render = False
    for obj in body:
        review.clip_top_skin(obj, True, waist_height=1.08)
        obj.hide_render = obj.get('region') in ['upper_arms', 'torso', 'legs', 'ankles', 'boot_ankles']
        obj.hide_set(obj.hide_render)
    for name, offset in [('set-front', (0, -5, 0)), ('set-back', (0, 5, 0)), ('set-side', (-5, 0, 0))]:
        render(name, offset, (0, 0, 1), 2.13)
    review.contact_sheet(directory, ['set-front', 'set-side', 'set-back'], ['SET FRONT', 'SET SIDE', 'SET BACK'],
                         3, directory / 'set.png')
    render('waist-front', (0, -5, 0), (0, 0, 1.05), .67)
    render('waist-back', (0, 5, 0), (0, 0, 1.05), .67)
    render('belt-buckle', (-3, -5, 0), (-.13, 0, 1), .40)
    render('ankles', (1.5, -5, .3), (0, 0, .21), .58)
    review.contact_sheet(directory, ['waist-front', 'waist-back', 'ankles'], ['WAIST FRONT', 'WAIST BACK', 'ANKLES'],
                         3, directory / 'connections.png')
    if not args.rest_only:
        report = json.loads((ROOT / 'doc/assets/modular-bard-tripo-pants-animation-v1.json').read_text())
        for source in report['sources']:
            assert review.file_record(ROOT / source['path'])['sha256'] == source['sha256']
        conversion = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        ordered = sorted(rig.pose.bones, key=lambda bone: len(bone.parent_recursive))
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'

        def key(frame):
            for bone in rig.pose.bones:
                for channel in ['location', 'rotation_quaternion', 'scale']:
                    bone.keyframe_insert(data_path=channel, frame=frame)

        key(1)
        scene.timeline_markers.new('REST', frame=1)
        snapshots = json.loads((OUTPUT / 'animation-snapshots.json').read_text())
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
            center = rig.matrix_world @ rig.pose.bones['Hips'].head + Vector((0, 0, -.12))
            render(snapshot['clip'], (-2.3, -5, .6), center, 1.75)
            if snapshot['clip'] in ['run', 'combat_idle', 'sit_idle']:
                render(snapshot['clip'] + '-back', (0, 5, .4), center, 1.75)
        names = [s['clip'] for s in snapshots if s['clip'] != 'combat_idle']
        review.contact_sheet(directory, names, ['IDLE', 'WALK', 'RUN', 'JUMP', 'SLASH', 'SIT'],
                             3, directory / 'motion.png')
        review.contact_sheet(directory, ['run-back', 'combat_idle-back', 'sit_idle-back'], ['RUN BACK', 'COMBAT BACK', 'SIT BACK'],
                             3, directory / 'motion-back.png')
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
    if args.quick:
        return
    references = bpy.data.collections.new('Unmodified source and interface references - hidden')
    scene.collection.children.link(references)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    for obj in set(bpy.data.objects) - before:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        references.objects.link(obj)
    with bpy.data.libraries.load(str(PARTS / 'interfaces/v1/outfit-reference.blend'), link=False) as (source, target):
        target.objects = [n for n in source.objects if n.endswith(('_center', '_band_minus', '_band_plus'))]
    for obj in target.objects:
        if obj:
            references.objects.link(obj)
    references.hide_render = references.hide_viewport = True
    bpy.ops.object.select_all(action='DESELECT')
    pants[0].select_set(True)
    bpy.context.view_layer.objects.active = pants[0]
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    editable = SOURCE.with_name('bard-pants-fitting.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(editable))
    record = dict(date='2026-10-11', blender_version=bpy.app.version_string,
        model=review.file_record(OUTPUT / 'pants_bard.glb'), editable=review.file_record(editable),
        source=review.file_record(SOURCE), context=['canonical body and rig', 'bard top', 'crop hair', 'bare feet'],
        images_retained_in_asset_tree=False, unmasked_rest_views=True,
        review_scene_hidden_regions=['upper_arms', 'torso', 'legs', 'ankles', 'boot_ankles'],
        timeline='Rest and sampled game poses, constant interpolation',
        triangles=dict(source_parts=assembled, including_hidden=sum(assembled.values()),
            visible_review_scene=triangles([o for o in body + pants + top + hair if not o.hide_render]),
            scope='Base, crop hair, bard top and pants; no boots, gloves or weapon. Review-scene masking only.'),
        status='Fitting review scene; runtime clothing masks and mixed-equipment support are separate')
    (ROOT / 'doc/assets/modular-bard-tripo-pants-fitted-review-v1.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
