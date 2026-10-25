import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor
from outfits.mesh_components import welded_islands
from outfits.skinning import deform

DIRECTORY = ROOT / 'assets/items/female_rogue_skirt/tripo_v1'
OUTPUT = DIRECTORY / 'fitted_v5'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'


def load(path):
    doc, raw = read_glb(path)
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    return (doc, raw, accessor(doc, raw, attrs['POSITION']),
            accessor(doc, raw, primitive['indices']).reshape(-1, 3),
            accessor(doc, raw, attrs['JOINTS_0']).astype(int),
            accessor(doc, raw, attrs['WEIGHTS_0']))


doc, raw, points, faces, joints, weights = load(OUTPUT / 'bottom_female_rogue.glb')
source, original, old_points, old_faces, old_joints, old_weights = load(DIRECTORY / 'fitted_v4/bottom_female_rogue.glb')
assert raw[:len(original)] == original
for key in ['nodes', 'skins', 'materials', 'textures', 'images']:
    assert doc[key] == source[key], key
assert doc['meshes'][0]['weights'] == [0]
assert doc['meshes'][0]['extras']['targetNames'] == ['pose_sit_idle']
for current, previous in zip([points, faces, joints, weights], [old_points, old_faces, old_joints, old_weights]):
    assert np.array_equal(current, previous)
primitive = doc['meshes'][0]['primitives'][0]
delta = accessor(doc, raw, primitive['targets'][0]['POSITION'])
corrected = points+delta
_, welded, labels = welded_islands(points, faces)
main = max(np.unique(labels), key=lambda label: len(np.unique(welded[labels == label])))
cloth = labels == main
queries = np.concatenate([points[cloth], points[faces[cloth[faces].all(1)]].mean(1)])
front = (queries[:, 2] > .045) & (queries[:, 1] < 1.015) & (queries[:, 1] > .855)
body_doc, body_raw, bp, bf, bj, bw = load(BODY)
_, _, body_labels = welded_islands(bp, bf)
skin_label = np.bincount(body_labels).argmax()
skin_faces = bf[(body_labels[bf] == skin_label).all(1)]
torso_leg_faces = skin_faces[(np.abs(bp[:, 0]) < .26)[skin_faces].all(1)]
body_region = (bp[:, 1] > .45) & (bp[:, 1] < 1.015) & (np.abs(bp[:, 0]) < .26)
leg_faces = bf[body_region[bf].all(1)]
pelvis_region = (bp[:, 1] > .45) & (bp[:, 1] < 1.16) & (np.abs(bp[:, 0]) < .26)
pelvis_faces = bf[(pelvis_region & (body_labels == skin_label))[bf].all(1)]
front_waist = (queries[:, 2] > .035) & (queries[:, 1] > .91)
poses = json.loads((OUTPUT / 'sit-poses.json').read_text())
assert poses['base_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
gaps = {'before': [], 'after': []}
front_gaps = {'before': [], 'after': []}
hem = cloth & (points[:, 2] > .05) & (points[:, 1] < .868)
rear_center = cloth & (points[:, 2] < -.04) & (points[:, 1] > 1.09) & (np.abs(points[:, 0]) < .03)
rear_side = cloth & (points[:, 2] < -.035) & (points[:, 1] > 1.087) & (np.abs(points[:, 0]) > .10) & (np.abs(points[:, 0]) < .15)
hem_ranges, waist_heights, areas = [], [], []


def inside(surface, point):
    votes = 0
    for axis in [(1, .013, .007), (.007, 1, .013), (.013, .007, 1),
                 (-1, .013, .007), (.007, -1, .013), (.013, .007, -1)]:
        origin = Vector(point)
        direction = Vector(axis).normalized()
        crossings = 0
        for _ in range(32):
            hit, _, _, _ = surface.ray_cast(origin, direction, 3)
            if hit is None:
                break
            crossings += 1
            origin = hit+direction*.00001
        else:
            raise AssertionError('Unexpected repeated skin intersections')
        votes += crossings % 2
    return votes >= 4


for sample in poses['samples']:
    matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    body = deform(bp, bj, bw, matrices)
    surface = BVHTree.FromPolygons([Vector(p) for p in body], leg_faces.tolist())
    pelvis_surface = BVHTree.FromPolygons([Vector(p) for p in body], pelvis_faces.tolist())
    full_skin = BVHTree.FromPolygons([Vector(p) for p in body], torso_leg_faces.tolist())
    for name, rest in [('before', points), ('after', corrected)]:
        posed = deform(rest, joints, weights, matrices)
        samples = np.concatenate([posed[cloth], posed[faces[cloth[faces].all(1)]].mean(1)])
        for p in samples[front_waist]:
            _, _, _, distance = pelvis_surface.find_nearest(Vector(p))
            front_gaps[name].append(-distance if inside(full_skin, p) else distance)
        for p in samples[front]:
            hit, _, _, distance = surface.ray_cast(Vector(p+[0, .18, 0]), Vector((0, -1, 0)), .36)
            if hit is not None:
                gaps[name].append(distance-.18)
        if name == 'after':
            hem_ranges.append(np.ptp(posed[hem], axis=0))
            areas.append(float(np.linalg.norm(np.cross(posed[faces[:, 1]]-posed[faces[:, 0]],
                                                       posed[faces[:, 2]]-posed[faces[:, 0]]), axis=1).min()/2))
        waist_heights.append({'clip_phase': sample['phase'], 'version': name,
                             'center_y_m': float(posed[rear_center, 1].mean()),
                             'sides_y_m': float(posed[rear_side, 1].mean())})


def metrics(values):
    values = np.array(values)
    return {'samples': len(values), 'minimum_gap_m': float(values.min()),
            'deeper_than_1mm': int((values < -.001).sum()), 'mean_gap_m': float(values.mean())}


report = {'skirt_sha256': hashlib.sha256((OUTPUT / 'bottom_female_rogue.glb').read_bytes()).hexdigest(),
          'seated_frames': len(poses['samples']), 'front_thigh_clearance': {key: metrics(value) for key, value in gaps.items()},
          'front_panel_pelvis_clearance': {key: metrics(value) for key, value in front_gaps.items()},
          'front_hem_maximum_y_range_m': float(np.max(hem_ranges, axis=0)[1]),
          'front_hem_maximum_z_range_m': float(np.max(hem_ranges, axis=0)[2]),
          'rear_rim_center_minus_sides_m': {name: float(np.mean([item['center_y_m']-item['sides_y_m']
                                                    for item in waist_heights if item['version'] == name]))
                                           for name in ['before', 'after']},
          'minimum_posed_triangle_area_m2': min(areas),
          'source_binary_prefix_and_bind_materials_preserved': True,
          'scope': '61 actual sitting frames. Front cloth vertices and triangle centers: lower torso/pelvis skin distance with inside/outside classified by six-direction ray parity vote on torso/legs (rest abs(X)<0.26m excludes resting arms). Vertical rays to lower pelvis/thighs include underwear and exclude abdomen. Rays missing the gap between legs are excluded. Arm contact is outside the pelvis correction. Rear upper rim and front hem shape checked separately; other motions checked by the runtime validator.'}
(OUTPUT / 'seated-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)
assert report['front_thigh_clearance']['after']['deeper_than_1mm'] == 0
assert report['front_panel_pelvis_clearance']['after']['deeper_than_1mm'] == 0
assert report['front_hem_maximum_y_range_m'] < .015
assert report['front_hem_maximum_z_range_m'] < .02
assert report['rear_rim_center_minus_sides_m']['before'] > 0
assert report['rear_rim_center_minus_sides_m']['after'] < 0
assert report['minimum_posed_triangle_area_m2'] > 1e-10
