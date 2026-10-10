"""Sync the corrected glove into its editable character file."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / 'assets/modular_human_male_01'
parser = argparse.ArgumentParser()
parser.add_argument('--part', choices=['leather', 'plate'], default='leather')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
blend = 'plate_parts' if args.part == 'plate' else 'character_parts'
path = PARTS / f'fitted/{blend}.blend'


def import_mesh(glb):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    imported = set(bpy.data.objects) - before
    return next(o for o in imported if o.type == 'MESH'), imported


def world_tree(obj):
    tree = KDTree(len(obj.data.vertices))
    for vertex in obj.data.vertices:
        tree.insert(obj.matrix_world @ vertex.co, vertex.index)
    tree.balance()
    return tree


bpy.ops.wm.open_mainfile(filepath=str(path))
target = next(o for o in bpy.data.objects if o.type == 'MESH' and o.get('part_id') == f'gloves_{args.part}')
original, original_objects = import_mesh(PARTS / f'gloves/shape_sources/{args.part}-before-thumb-v1.glb')
corrected, corrected_objects = import_mesh(PARTS / f'fitted/gloves_{args.part}.glb')
assert len(original.data.vertices) == len(corrected.data.vertices)
assert [tuple(p.vertices) for p in original.data.polygons] == [tuple(p.vertices) for p in corrected.data.polygons]
mapping = list(target.get(f'{args.part}_thumb_source_vertices', []))
if not mapping:
    tree = world_tree(original)
    corrected_tree = world_tree(corrected)
    for vertex in target.data.vertices:
        point = target.matrix_world @ vertex.co
        _, index, distance = tree.find(point)
        if distance >= 1e-5:
            _, index, distance = corrected_tree.find(point)
        assert distance < 1e-5, 'Editable glove differs from the preserved source and current output'
        mapping.append(index)
assert len(mapping) == len(target.data.vertices)
inverse = target.matrix_world.inverted()
for vertex, index in zip(target.data.vertices, mapping):
    vertex.co = inverse @ corrected.matrix_world @ corrected.data.vertices[index].co
target.data.update()
target[f'{args.part}_thumb_source_vertices'] = mapping
target.data.normals_split_custom_set([(0, 0, 0)] * len(target.data.loops))
for obj in original_objects | corrected_objects:
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(path))
