"""Inspect the raw bard hat without changing or fitting its geometry."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'assets/items/bard_starter/tripo_hat_v1'
spec = importlib.util.spec_from_file_location(
    'studio', ROOT / 'tools/blender-scripts/review_tripo_pants.py')
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


def intersections():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.hide_render or not obj.get('part_id'):
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        trees[obj.name] = BVHTree.FromPolygons(
            [evaluated.matrix_world @ v.co for v in mesh.vertices],
            [list(p.vertices) for p in mesh.polygons])
        evaluated.to_mesh_clear()
    hat = next(obj.name for obj in bpy.data.objects if obj.get('part_id') == 'helmet_bard')
    return {name: len(trees[hat].overlap(tree)) for name, tree in trees.items() if name != hat}


def equip_crop_hair(directory):
    snapshot = json.loads((directory / 'equipped-hair.json').read_text())['variants']['hair_crop'][0]
    obj = next(obj for obj in bpy.data.objects if obj.get('part_id') == 'hair_crop')
    points, indices = snapshot['positions'], snapshot['indices']
    inverse = obj.matrix_world.inverted()
    mesh = bpy.data.meshes.new('hair_crop_under_bard_hat')
    mesh.from_pydata(
        [inverse @ Vector((points[i], -points[i + 2], points[i + 1]))
         for i in range(0, len(points), 3)], [],
        [indices[i:i + 3] for i in range(0, len(indices), 3)])
    for material in obj.data.materials:
        mesh.materials.append(material)
    uv = mesh.uv_layers.new()
    for loop in mesh.loops:
        i = loop.vertex_index * 2
        uv.data[loop.index].uv = snapshot['uv'][i:i + 2]
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj.data = mesh
    obj.vertex_groups.clear()
    obj.vertex_groups.new(name='Head').add(list(range(len(mesh.vertices))), 1.0, 'REPLACE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', required=True, type=Path)
    parser.add_argument('--fitted', action='store_true')
    parser.add_argument('--animations', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    directory = args.images.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts = ROOT / 'assets/modular_human_male_01'
    fitted_dir = parts / 'bard/tripo_hat_v1'
    source = fitted_dir / 'helmet_bard.glb' if args.fitted else ASSETS / 'source.glb'
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH'
              and (not args.fitted or obj.get('part_id') == 'helmet_bard')]
    diagnostic, low, high = studio.source_review.diagnostics(meshes)
    center, scale = (low + high) / 2, (high - low).length * 1.12
    if args.fitted:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(parts / 'fitted/base.glb'))
        rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                obj.hide_render = obj.get('region') not in ['head', 'neck', 'hands']
        for path in [source, parts / 'fitted/hair_crop.glb',
                     parts / 'bard/tripo_top_v1/top_bard.glb',
                     parts / 'bard/tripo_pants_v1/pants_bard.glb',
                     parts / 'bard/tripo_boots_v1/boots_bard.glb']:
            studio.review.import_part(path, rig)
        equip_crop_hair(fitted_dir)
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and not obj.get('part_id'):
                obj.hide_render = True
        center, scale = Vector((0, 0, 1.84)), .68
    scene, camera = studio.setup(False)
    scene.render.resolution_x = scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    report = {
        'status': 'fitted review' if args.fitted else 'raw source; not fitted or rigged',
        'source': studio.review.file_record(source),
        **diagnostic,
        'bounds_blender': {'min': list(low), 'max': list(high)},
        'views': {},
    }
    if args.fitted:
        report['rest_intersections'] = intersections()
    for name, offset in [
        ('front', (0, -5, 0)), ('feather-side', (5, 0, 0)),
        ('back', (0, 5, 0)), ('three-quarter', (3, -5, 2)),
        ('underside', (0, -1, -5)),
    ]:
        camera.location = center + Vector(offset)
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(directory / f'{name}.png')
        bpy.ops.render.render(write_still=True)
        report['views'][name] = {'camera_offset_blender': offset}
    if args.fitted:
        center = Vector((0, 0, 1.03))
        camera.location = center + Vector((0, -5, .1))
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = 2.2
        scene.render.filepath = str(directory / 'full.png')
        bpy.ops.render.render(write_still=True)
        if args.animations:
            snapshots = json.loads((fitted_dir / 'animation-snapshots.json').read_text())
            conversion = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
            to_blender = rig.matrix_world.inverted() @ conversion
            from_blender = conversion.inverted() @ rig.matrix_world
            bones = sorted(rig.pose.bones, key=lambda bone: len(bone.parent_recursive))
            for bone in bones:
                bone.rotation_mode = 'QUATERNION'
                for channel in ['location', 'rotation_quaternion', 'scale']:
                    bone.keyframe_insert(data_path=channel, frame=1)
            scene.timeline_markers.new('REST', frame=1)
            report['motion_intersections'] = {}
            for index, snapshot in enumerate(snapshots, 1):
                scene.frame_set(index * 10)
                for bone in bones:
                    values = snapshot['bone_deformation_matrices'][bone.name]
                    deformation = Matrix([values[i:i + 4] for i in range(0, 16, 4)]).transposed()
                    bone.matrix = to_blender @ deformation @ from_blender @ bone.bone.matrix_local
                    bpy.context.view_layer.update()
                    for channel in ['location', 'rotation_quaternion', 'scale']:
                        bone.keyframe_insert(data_path=channel, frame=index * 10)
                name = snapshot['clip']
                scene.timeline_markers.new(name, frame=index * 10)
                report['motion_intersections'][name] = intersections()
                center = rig.matrix_world @ rig.pose.bones['Head'].head + Vector((0, 0, .13))
                camera.location = center + Vector((2, -5, 1))
                camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
                camera.data.ortho_scale = .80
                scene.render.filepath = str(directory / f'motion-{name}.png')
                bpy.ops.render.render(write_still=True)
            scene.frame_end = len(snapshots) * 10
            scene.frame_set(1)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(ASSETS / 'source.glb'))
        references = bpy.data.collections.new('Original Tripo hat')
        scene.collection.children.link(references)
        for obj in set(bpy.data.objects) - before:
            for collection in list(obj.users_collection):
                collection.objects.unlink(obj)
            references.objects.link(obj)
        references.hide_render = references.hide_viewport = True
    destination = fitted_dir if args.fitted else ASSETS
    (destination / 'fitted-review.json' if args.fitted else destination / 'source-review.json').write_text(
        json.dumps(report, indent=2) + '\n')
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(
        ASSETS / 'bard-hat-fitting.blend' if args.fitted else ASSETS / 'source-review.blend'))


if __name__ == '__main__':
    main()
