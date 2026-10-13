import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v23'
OUTPUT = DIRECTORY / 'fitted_v24'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '54c92f01878c62bed4636d87192a4daec47ccbaa356e6afe15302c73e48df474'
doc, binary = read_glb(source)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION'])
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
labels = np.array([root(index) for index in welded[faces[:, 0]]])
guards = {}
for label in np.unique(labels):
    selected = np.flatnonzero(labels == label)
    vertices = np.unique(faces[selected])
    bounds = points[vertices]
    if np.ptp(bounds[:, 0]) > .07 and bounds[:, 1].min() < .50 and bounds[:, 1].max() > .59:
        if bounds[:, 2].min() > .04:
            guards['front'] = (selected, vertices)
        elif bounds[:, 2].max() < -.03:
            guards['rear'] = (selected, vertices)
assert set(guards) == {'front', 'rear'}
front_faces, front_vertices = guards['front']
rear_faces, rear_vertices = guards['rear']
assert len(front_faces) == 106 and len(rear_faces) == 72
assert len(front_vertices) == 138 and len(rear_vertices) == 89
angle = np.deg2rad(25)
rotation = np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)], [0, np.sin(angle), np.cos(angle)]]) @ np.diag([-1, 1, -1])
upper = front_vertices[points[front_vertices, 1] > .59]
anchor = points[upper].mean(0).astype(float)
target_anchor = np.array([0, .628, -.043])
translation = target_anchor - rotation @ anchor
destinations = np.concatenate([rear_vertices, np.arange(len(points), len(points) + len(front_vertices) - len(rear_vertices))])
mapping = np.full(len(points), -1, dtype=int)
mapping[front_vertices] = destinations
kept = np.delete(faces, rear_faces, axis=0)
new_faces = np.vstack([kept, mapping[faces[front_faces]]])
for name, attribute in list(attrs.items()):
    original = accessor(doc, binary, attribute)
    copy = original[front_vertices].copy()
    if name == 'POSITION':
        copy = copy @ rotation.T + translation
    elif name in ['NORMAL', 'TANGENT']:
        copy[:, :3] = copy[:, :3] @ rotation.T
    result = np.concatenate([original, np.zeros((len(destinations) - len(rear_vertices), original.shape[1]), dtype=original.dtype)])
    result[destinations] = copy
    metadata = doc['accessors'][attribute]
    attrs[name] = add_accessor(doc, binary, result, metadata['type'], metadata['componentType'])
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
primitive['indices'] = add_accessor(doc, binary, new_faces.reshape(-1, 1), 'SCALAR', 5125)
doc['bufferViews'][doc['accessors'][primitive['indices']]['bufferView']]['target'] = 34963
doc['nodes'][0]['extras']['fitting_version'] = 24
doc['buffers'][0]['byteLength'] = len(binary)
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update({
    'date': '2026-10-13', 'source': str(source.relative_to(ROOT)), 'source_sha256': source_hash,
    'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'method': 'Replace the old rear guard with a rigidly rotated and translated copy of the front guard, including its UVs, shading and hip weights.',
    'rear_guard_replacement': {
        'primitive': 0, 'source_vertices': front_vertices.tolist(), 'destination_vertices': destinations.tolist(),
        'removed_vertices': rear_vertices.tolist(), 'removed_face_indices': rear_faces.tolist(),
        'source_face_indices': front_faces.tolist(), 'rotation': rotation.tolist(), 'translation': translation.tolist(),
        'source_anchor': anchor.tolist(), 'target_anchor': target_anchor.tolist(),
        'rear_tilt_degrees': 25, 'removed_triangles': len(rear_faces), 'copied_triangles': len(front_faces),
    },
    'triangles': sum(doc['accessors'][part['indices']]['count'] // 3 for part in doc['meshes'][0]['primitives']),
    'preserved': ['front guard', 'straps and buckles', 'side plates and rivets', 'other weights', 'materials', 'textures', 'bones', 'inverse binds', 'occlusion mask'],
    'additional_api_credits': 0,
})
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'triangles': report['triangles']}))
