import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v24', DIRECTORY / 'fitted_v25'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '255e155340af4de1165357e91b3af6dd80baf45b5e9f785e2a2cc1480a863821'
doc, binary = read_glb(source)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attribute = primitive['attributes']['POSITION']
points = accessor(doc, binary, attribute)
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
regions = []
for label in np.unique(labels[faces]):
    vertices = np.unique(faces[labels[faces[:, 0]] == label])
    bounds = points[vertices]
    rear_strap = bounds[:, 2].max() < -.04 and bounds[:, 1].max() > .57 and np.min(abs(bounds[:, 0])) > .025
    waist = len(vertices) == 1136
    if rear_strap or waist:
        regions.append(vertices)
assert sorted(map(len, regions)) == [126, 150, 269, 1136]
triangles = points[faces].astype(float)
area_normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
selected = np.concatenate(regions)
selected = selected[points[selected, 2] < -.015]
offsets = np.zeros(len(points))
for group in np.unique(welded[selected]):
    vertices = np.flatnonzero(welded == group)
    normal = area_normals[np.isin(faces, vertices).any(1)].sum(0)
    blend = np.clip((-float(points[vertices[0], 2]) - .015) / .02, 0, 1)
    blend = blend * blend * (3 - 2 * blend)
    offsets[vertices] = .0015 * blend * np.sign(normal[2])
points[:, 2] += offsets
changed = np.flatnonzero(offsets)
assert len(changed) > 500
metadata = doc['accessors'][attribute]
view = doc['bufferViews'][metadata['bufferView']]
assert view.get('byteStride', 12) == 12
start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
binary[start:start + points.nbytes] = points.tobytes()
metadata.update(min=points.min(0).tolist(), max=points.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 25
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.pop('rear_guard_replacement', None)
report.update({
    'date': '2026-10-13', 'source': str(source.relative_to(ROOT)), 'source_sha256': source_hash,
    'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'method': 'Separate rear leather front/back layers along Z using welded geometric winding, with a smooth fade into the unchanged side belt. Preserve shading, UVs and weights.',
    'rear_leather_vertices': changed.tolist(), 'rear_leather_regions': [vertices.tolist() for vertices in regions],
    'maximum_surface_offset': .0015,
    'preserved': ['front leather', 'both guards', 'plates', 'topology', 'XY positions', 'normals', 'tangents', 'UVs', 'weights', 'materials', 'textures', 'rig', 'occlusion mask'],
    'additional_api_credits': 0,
})
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'changed_vertices': len(changed)}))
