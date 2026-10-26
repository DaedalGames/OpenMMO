"""Audit the ankle pivot, lower-shin stability and animated cross sections."""
import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, view_bytes
from lib.glb_accessors import accessor
from scipy.spatial.transform import Rotation

from outfits.female_boot_pose import heel_pose, node_worlds
from outfits.skinning import deform

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_rogue_boots/tripo_v1'
OUTPUT = DIRECTORY / 'fitted_v5'
SOURCE = DIRECTORY / 'fitted_v3/boots_female_rogue.glb'


def area(points):
    centered = points - points.mean(0)
    return np.linalg.norm(np.cross(centered, np.roll(centered, -1, axis=0)).sum(0)) * .5


def mesh_data(doc, raw, mesh):
    primitive = doc['meshes'][mesh]['primitives'][0]
    attrs = primitive['attributes']
    return [accessor(doc, raw, attrs[name]) for name in ['POSITION', 'JOINTS_0', 'WEIGHTS_0']]


def rings(points, faces):
    result = []
    for height in [.135, .15, .165, .18]:
        edges = faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)
        edges = edges[(points[edges[:, 0], 1] < height) != (points[edges[:, 1], 1] < height)]
        t = (height - points[edges[:, 0], 1]) / (points[edges[:, 1], 1] - points[edges[:, 0], 1])
        contour = points[edges[:, 0]] * (1 - t[:, None]) + points[edges[:, 1]] * t[:, None]
        _, unique = np.unique(np.round(contour, 6), axis=0, return_index=True)
        contour, edges, t = contour[unique], edges[unique], t[unique]
        center = contour.mean(0)
        order = np.argsort(np.arctan2(contour[:, 2] - center[2], contour[:, 0] - center[0]))
        result.append((height, edges[order], t[order], area(contour[order])))
    return result


base, body_raw = read_glb(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
heel, _ = heel_pose(base, body_raw)
worlds = node_worlds(base)
nodes = {node.get('name'): i for i, node in enumerate(base['nodes'])}
names = [base['nodes'][i]['name'] for i in base['skins'][0]['joints']]
old, old_raw = read_glb(SOURCE)
target = OUTPUT / 'boots_female_rogue.glb'
new, new_raw = read_glb(target)
assert len(new['skins'][0]['joints']) == 65
assert np.array_equal(accessor(new, new_raw, new['skins'][0]['inverseBindMatrices']), accessor(old, old_raw, old['skins'][0]['inverseBindMatrices']))
for key in ['nodes', 'scenes', 'materials', 'textures']:
    assert new[key] == old[key], key
assert [view_bytes(new, new_raw, i['bufferView']) for i in new['images']] == [view_bytes(old, old_raw, i['bufferView']) for i in old['images']]
poses = json.loads((OUTPUT / 'animation-samples.json').read_text())
records, pivot_records = [], []
for mesh in range(2):
    before = mesh_data(old, old_raw, mesh)
    after = mesh_data(new, new_raw, mesh)
    old_p = old['meshes'][mesh]['primitives'][0]
    new_p = new['meshes'][mesh]['primitives'][0]
    faces = accessor(old, old_raw, old_p['indices']).reshape(-1, 3)
    assert np.array_equal(faces.reshape(-1), accessor(new, new_raw, new_p['indices']).reshape(-1))
    for name in ['TEXCOORD_0', 'TEXCOORD_1']:
        assert np.array_equal(accessor(old, old_raw, old_p['attributes'][name]), accessor(new, new_raw, new_p['attributes'][name]))
    for old_target, new_target in zip(old_p['targets'], new_p['targets']):
        for name in old_target:
            assert np.array_equal(accessor(old, old_raw, old_target[name]), accessor(new, new_raw, new_target[name]))
    old_heel = deform(*before, heel)
    new_heel = deform(*after, heel)
    def equipped_normals(doc, raw, primitive, values):
        normals = accessor(doc, raw, primitive['attributes']['NORMAL'])
        matrix = np.einsum('nk,nkij->nij', values[2], heel[values[1]])
        result = np.einsum('nij,nj->ni', matrix[:, :3, :3], normals)
        return result / np.linalg.norm(result, axis=1, keepdims=True)
    assert np.max(np.linalg.norm(equipped_normals(old, old_raw, old_p, before) - equipped_normals(new, new_raw, new_p, after), axis=1)) < 2e-6
    fixed = (old_heel[:, 1] <= .075) | (old_heel[:, 1] >= .27)
    for a, b in zip(before, after):
        assert np.array_equal(a[fixed], b[fixed]), 'Sole, heel or upper shaft changed'
    assert np.max(np.linalg.norm(new_heel - old_heel, axis=1)) < 2e-6, 'Equipped shape changed'
    side = 'Right' if mesh == 0 else 'Left'
    foot_index = names.index(side + 'Foot')
    leg_index = names.index(side + 'Leg')
    high_shin = (new_heel[:, 1] >= .17) & (new_heel[:, 1] < .27)
    foot_share = (after[2] * (after[1] == foot_index)).sum(1)
    assert foot_share[high_shin].max() < .001, 'Foot influence reached the lower shin'
    ankle = worlds[nodes[side + 'Foot'], :3, 3]
    direction = worlds[nodes[side + 'ToeBase'], :3, 3] - ankle
    direction[1] = 0
    direction /= np.linalg.norm(direction)
    lateral = np.cross([0, 1, 0], direction)
    for degrees in [-60, -30, 30, 60]:
        delta = np.eye(4)
        delta[:3, :3] = Rotation.from_rotvec(lateral * np.deg2rad(degrees)).as_matrix()
        delta[:3, 3] = ankle - delta[:3, :3] @ ankle
        matrices = heel.copy()
        matrices[foot_index] = delta @ heel[foot_index]
        old_motion = deform(*before, matrices)
        new_motion = deform(*after, matrices)
        pivot_records.append({'side': side, 'isolated_foot_rotation_degrees': degrees, 'old_maximum_shin_motion_m': float(np.linalg.norm(old_motion[high_shin] - old_heel[high_shin], axis=1).max()), 'new_maximum_shin_motion_m': float(np.linalg.norm(new_motion[high_shin] - new_heel[high_shin], axis=1).max())})
    contours = rings(old_heel, faces)
    for pose in poses:
        matrices = np.array(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        old_pose = deform(*before, matrices)
        new_pose = deform(*after, matrices)
        for height, edges, t, reference in contours:
            cut = lambda p: p[edges[:, 0]] * (1 - t[:, None]) + p[edges[:, 1]] * t[:, None]
            old_area, new_area = area(cut(old_pose)), area(cut(new_pose))
            records.append({'side': 'Right' if mesh == 0 else 'Left', 'clip': pose['clip'], 'phase': pose['phase'], 'height_m': height, 'old_area_relative_to_old_heel': float(old_area / reference), 'new_area_relative_to_old_heel': float(new_area / reference), 'new_area_relative_to_new_heel': float(new_area / area(cut(new_heel))), 'area_gain': float(new_area / old_area)})
summary = {}
for clip in dict.fromkeys(pose['clip'] for pose in poses):
    rows = [row for row in records if row['clip'] == clip]
    summary[clip] = {'samples': len(rows) // 8, 'old_minimum_relative_area': min(row['old_area_relative_to_old_heel'] for row in rows), 'new_minimum_relative_area': min(row['new_area_relative_to_old_heel'] for row in rows), 'minimum_area_gain': min(row['area_gain'] for row in rows), 'new_minimum_relative_to_own_heel': min(row['new_area_relative_to_new_heel'] for row in rows)}
report = {'boot_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'scope': 'Isolated Foot rotation at the anatomical joint, lower-shin stability and four material cross sections at 135–180mm. Actual runtime heel and ground corrections are included in all clip samples; this is not a continuous collision proof.', 'equipped_shape_preserved_within_m': 2e-6, 'unchanged_sole_heel_and_upper_shaft': True, 'original_uvs_pbr_and_seated_morph_preserved': True, 'isolated_ankle_rotation': pivot_records, 'clips': summary}
(OUTPUT / 'ankle-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
assert all(row['new_maximum_shin_motion_m'] < .0005 for row in pivot_records)
assert all(summary[clip]['new_minimum_relative_to_own_heel'] > .97 for clip in ['walk', 'run'])
