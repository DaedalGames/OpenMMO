"""Check the fitted hat against every current face and selectable hair mesh."""

import hashlib
import json
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / 'assets/modular_human_male_01'


def tree(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = BVHTree.FromPolygons(
        [evaluated.matrix_world @ v.co for v in mesh.vertices],
        [list(p.vertices) for p in mesh.polygons])
    evaluated.to_mesh_clear()
    return result


def record(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = PARTS / 'bard/tripo_hat_v1/helmet_bard.glb'
    bpy.ops.import_scene.gltf(filepath=str(path))
    hat = tree(next(obj for obj in bpy.data.objects if obj.get('part_id') == 'helmet_bard'))
    report = dict(hat=record(path), method='Blender BVHTree triangle overlap in canonical rest pose', variants={})
    hair_path = PARTS / 'bard/tripo_hat_v1/equipped-hair.json'
    hair = json.loads(hair_path.read_text())
    assert all(record(ROOT / item['path'])['sha256'] == item['sha256']
               for item in hair['sources']), 'Regenerate equipped hair for the current assets'
    report['equipped_hair'] = record(hair_path)
    for name, relative in [
        ('default', 'fitted/base.glb'),
        ('rugged', 'faces/tripo_rugged_v1/base_rugged.glb'),
        ('ranger', 'faces/tripo_ranger_v1/base_ranger.glb'),
        ('hair_crop', 'fitted/hair_crop.glb'),
        ('hair_wavy_bone', 'hair/tripo_wavy_v1/hair_wavy_bone.glb'),
        ('hair_ranger', 'hair/tripo_ranger_v1/hair_ranger.glb'),
    ]:
        path = PARTS / relative
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        objects = set(bpy.data.objects) - before
        meshes = [obj for obj in objects if obj.type == 'MESH' and
                  (obj.get('part_id', '').startswith('hair_') if name.startswith('hair_')
                   else obj.get('region') == 'head')]
        assert meshes, name
        raw_overlaps = sum(len(hat.overlap(tree(obj))) for obj in meshes)
        overlaps = raw_overlaps
        if name.startswith('hair_'):
            overlaps = 0
            for mesh in hair['variants'][name]:
                p, f = mesh['positions'], mesh['indices']
                surface = BVHTree.FromPolygons(
                    [(p[i], -p[i + 2], p[i + 1]) for i in range(0, len(p), 3)],
                    [f[i:i + 3] for i in range(0, len(f), 3)])
                overlaps += len(hat.overlap(surface))
        report['variants'][name] = dict(source=record(path),
            untrimmed_intersecting_triangle_pairs=raw_overlaps,
            intersecting_triangle_pairs=overlaps)
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    target = ROOT / 'doc/assets/modular-bard-tripo-hat-clearance-v1.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    assert all(value['intersecting_triangle_pairs'] == 0 for value in report['variants'].values()), report
    print(json.dumps(report))


if __name__ == '__main__':
    main()
