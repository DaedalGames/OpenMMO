import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v20', DIRECTORY / 'fitted_v21'
OUTPUT.mkdir(exist_ok=True)
assert hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest() == 'c38053cc954bfd08b1a2352c41c471afa19220be5adef6b9ec9ca9359416e699'
doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
primitive, plate = doc['meshes'][0]['primitives'][:2]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
normals = accessor(doc, binary, attrs['NORMAL'])
tangents = accessor(doc, binary, attrs['TANGENT'])
joints = accessor(doc, binary, attrs['JOINTS_0'])
weights = accessor(doc, binary, attrs['WEIGHTS_0'])
names = [doc['nodes'][index]['name'] for index in doc['skins'][0]['joints']]
plate_points = accessor(doc, binary, plate['attributes']['POSITION']).astype(float)
plate_faces = accessor(doc, binary, plate['indices']).reshape(-1, 3)
triangles = plate_points[plate_faces]
a = triangles[:, 0]
ab, ac = triangles[:, 1] - a, triangles[:, 2] - a
_, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
parents = np.arange(welded.max() + 1)


def root(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


for face in welded[faces]:
    for corner in face[1:]:
        parents[root(corner)] = root(face[0])
labels = np.array([root(index) for index in welded])


def skew(axis):
    x, y, z = axis
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])


def clearance(samples):
    gaps = []
    for point in samples:
        origin = np.array([0, point[1], -.004])
        direction = point - origin
        radius = np.linalg.norm(direction)
        direction /= radius
        h = np.cross(direction, ac)
        det = (ab * h).sum(1)
        valid = abs(det) > 1e-12
        inverse = np.divide(1, det, out=np.zeros_like(det), where=valid)
        offset = origin - a
        u = (offset * h).sum(1) * inverse
        cross = np.cross(offset, ab)
        v = (cross * direction).sum(1) * inverse
        distance = (cross * ac).sum(1) * inverse
        hits = distance[valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (distance > 0)]
        if len(hits):
            gaps.append(float(radius - hits.max()))
    return min(gaps) if gaps else float('inf')


specs = [
    {'name': 'wearer-right-front', 'side': -1, 'seeds': [367, 317], 'count': 302,
     'opening': [[565, 535, 579, 569], [687, 695, 681, 684]], 'tab': [555, 669]},
    {'name': 'wearer-right-rear', 'side': -1, 'seeds': [704, 1464], 'count': 302,
     'opening': [[711, 716, 708, 1645], [1793, 1806, 1790, 1803]], 'tab': [1632, 1775]},
    {'name': 'wearer-left-rear', 'side': 1, 'seeds': [3633], 'count': 350,
     'opening': [[4971, 3639, 3633, 3636], [4885, 4888, 4848, 4822]], 'tab': [4963, 4827]},
]
changed, records = [], []
for spec in specs:
    selected = np.flatnonzero(np.isin(labels, labels[spec['seeds']]))
    assert len(selected) == spec['count']
    source_ends = np.array([points[group].mean(0) for group in spec['opening']])
    target_ends = points[spec['tab']].copy()
    source_center, target_center = source_ends.mean(0), target_ends.mean(0)
    source_axis, target_axis = source_ends[1] - source_ends[0], target_ends[1] - target_ends[0]
    source_axis /= np.linalg.norm(source_axis)
    target_axis /= np.linalg.norm(target_axis)
    v = np.cross(source_axis, target_axis)
    c = np.dot(source_axis, target_axis)
    k = skew(v)
    alignment = np.eye(3) + k + k @ k / (1 + c)
    outward = np.array([target_center[0], 0, target_center[2] + .004])
    outward /= np.linalg.norm(outward)
    target_center += outward * .0015
    part_faces = faces[np.isin(faces, selected).all(1)]
    source_triangles = points[part_faces]
    for degrees in range(0, 61, 5):
        pitch = np.radians(-spec['side'] * degrees)
        k = skew(target_axis)
        rotation = (np.eye(3) + np.sin(pitch) * k + (1 - np.cos(pitch)) * k @ k) @ alignment
        transformed = (source_triangles - source_center) @ rotation.T + target_center
        face_normals = np.cross(transformed[:, 1] - transformed[:, 0], transformed[:, 2] - transformed[:, 0])
        radial = transformed.mean(1) - [0, 0, -.004]
        radial[:, 1] = 0
        outer = transformed[(face_normals * radial).sum(1) > 0]
        samples = np.concatenate([outer[:, 0] * (1-u-v) + outer[:, 1] * u + outer[:, 2] * v for u, v in [(1/3, 1/3), (.1, .1), (.8, .1), (.1, .8), (.45, .1), (.1, .45), (.45, .45)]])
        gap = clearance(samples)
        if gap > .00075:
            break
    else:
        raise ValueError(f'No clear buckle orientation: {spec["name"]}')
    points[selected] = (points[selected] - source_center) @ rotation.T + target_center
    normals[selected] = normals[selected] @ rotation.T
    tangents[selected, :3] = tangents[selected, :3] @ rotation.T
    leg = np.clip((.615 - points[selected, 1]) / .055, 0, 1)
    leg = leg * leg * (3 - 2 * leg)
    joints[selected] = 0
    joints[selected, 0] = names.index('Hips')
    joints[selected, 1] = names.index('LeftUpLeg' if spec['side'] > 0 else 'RightUpLeg')
    weights[selected] = np.column_stack([1 - leg, leg, np.zeros((len(selected), 2))])
    swap = selected[leg > .5]
    joints[swap] = joints[swap][:, [1, 0, 2, 3]]
    weights[swap] = weights[swap][:, [1, 0, 2, 3]]
    joints[selected] = np.where(weights[selected] > 0, joints[selected], 0)
    changed.extend(selected.tolist())
    records.append({**spec, 'vertices': selected.tolist(), 'rotation': rotation.tolist(), 'source_opening_center': source_center.tolist(),
                    'target_opening_center': target_center.tolist(), 'outward_pitch_degrees': float(np.degrees(pitch)), 'minimum_sampled_clearance': gap})
for name, values, kind, component in [('POSITION', points, 'VEC3', 5126), ('NORMAL', normals, 'VEC3', 5126), ('TANGENT', tangents, 'VEC4', 5126), ('JOINTS_0', joints, 'VEC4', 5123), ('WEIGHTS_0', weights, 'VEC4', 5126)]:
    attrs[name] = add_accessor(doc, binary, values, kind, component)
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
doc['nodes'][0]['extras']['fitting_version'] = 21
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)), source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Align the remaining three side buckle openings to their waist tabs with rigid transforms and the smallest tested outward pitch that clears the plate.',
              buckle_vertices=changed, buckle_parts=records,
              opening_vertex_groups=report['opening_vertex_groups'] + [group for spec in specs for group in spec['opening']],
              tab_vertices=report['tab_vertices'] + [vertex for spec in specs for vertex in spec['tab']],
              weights='Use the same Hips/same-side UpLeg height blend as each waist tab and plate at the new position.',
              preserved=['previously aligned buckle', 'waist belt', 'plate geometry', 'front hanging straps', 'UVs', 'topology', 'materials', 'textures', 'rig', 'occlusion mask'])
for name in ['source_opening_center', 'target_opening_center', 'rotation', 'opening_axis_rotation_degrees', 'outward_pitch_degrees']:
    report.pop(name, None)
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'parts': [{k: record[k] for k in ['name', 'outward_pitch_degrees', 'minimum_sampled_clearance']} for record in records]}))
