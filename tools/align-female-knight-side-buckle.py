import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v19'
OUTPUT = DIRECTORY / 'fitted_v20'
OUTPUT.mkdir(exist_ok=True)
assert hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest() == '526bbe329b3ad8d0ee8ceb57ceb61a26852218b2ab2b2f2fd69b929a1503accc'
doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
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
selected = []
for label in np.unique(labels[faces]):
    vertices = np.unique(faces[labels[faces[:, 0]] == label])
    bounds = points[vertices]
    if bounds[:, 0].min() > .08 and bounds[:, 2].min() > .025 and bounds[:, 1].min() > .56 and bounds[:, 1].max() < .62:
        selected.extend(vertices.tolist())
selected = np.array(sorted(selected))
assert len(selected) == 290
opening_groups = [[3404, 3407, 3410, 3414], [3591, 3594, 3600, 3603]]
tab_vertices = [3398, 3581]
source_ends = np.array([points[group].mean(0) for group in opening_groups])
target_ends = points[tab_vertices].copy()
source_center = source_ends.mean(0)
target_center = target_ends.mean(0)
source_axis = source_ends[1] - source_ends[0]
target_axis = target_ends[1] - target_ends[0]
source_axis /= np.linalg.norm(source_axis)
target_axis /= np.linalg.norm(target_axis)
v = np.cross(source_axis, target_axis)
s = np.linalg.norm(v)
c = np.dot(source_axis, target_axis)
k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
rotation = np.eye(3) + k + k @ k * ((1 - c) / s ** 2)
pitch = np.radians(-30)
k = np.array([[0, -target_axis[2], target_axis[1]], [target_axis[2], 0, -target_axis[0]], [-target_axis[1], target_axis[0], 0]])
rotation = (np.eye(3) + np.sin(pitch) * k + (1 - np.cos(pitch)) * k @ k) @ rotation
outward = np.array([target_center[0], 0, target_center[2] + .004])
outward /= np.linalg.norm(outward)
target_center += outward * .0015
points[selected] = (points[selected] - source_center) @ rotation.T + target_center
normals = accessor(doc, binary, attrs['NORMAL'])
tangents = accessor(doc, binary, attrs['TANGENT'])
normals[selected] = normals[selected] @ rotation.T
tangents[selected, :3] = tangents[selected, :3] @ rotation.T
names = [doc['nodes'][index]['name'] for index in doc['skins'][0]['joints']]
joints = accessor(doc, binary, attrs['JOINTS_0'])
weights = accessor(doc, binary, attrs['WEIGHTS_0'])
leg = np.clip((.615 - points[selected, 1]) / .055, 0, 1)
leg = leg * leg * (3 - 2 * leg)
joints[selected] = 0
joints[selected, 0] = names.index('Hips')
joints[selected, 1] = names.index('LeftUpLeg')
weights[selected] = np.column_stack([1 - leg, leg, np.zeros((len(selected), 2))])
swap = selected[leg > .5]
joints[swap] = joints[swap][:, [1, 0, 2, 3]]
weights[swap] = weights[swap][:, [1, 0, 2, 3]]
joints[selected] = np.where(weights[selected] > 0, joints[selected], 0)
for name, values, kind, component in [('POSITION', points, 'VEC3', 5126), ('NORMAL', normals, 'VEC3', 5126), ('TANGENT', tangents, 'VEC4', 5126), ('JOINTS_0', joints, 'VEC4', 5123), ('WEIGHTS_0', weights, 'VEC4', 5126)]:
    attrs[name] = add_accessor(doc, binary, values, kind, component)
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
doc['nodes'][0]['extras']['fitting_version'] = 20
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)), source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Align the wearer-left front side buckle opening with the waist tab edge. Move its short strap and tip together.',
              buckle_vertices=selected.tolist(), source_opening_center=source_center.tolist(), target_opening_center=target_center.tolist(), rotation=rotation.tolist(),
              opening_vertex_groups=opening_groups, tab_vertices=tab_vertices, opening_axis_rotation_degrees=float(np.degrees(np.arccos(c))), outward_pitch_degrees=float(np.degrees(pitch)),
              weights='Use the same Hips/LeftUpLeg height blend as the waist tab and plate at the new position.',
              preserved=['opposite side', 'waist belt', 'plate geometry', 'front hanging straps', 'UVs', 'topology', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'translation': (target_center-source_center).tolist(), 'rotation_degrees': float(np.degrees(np.arccos(c)))}))
