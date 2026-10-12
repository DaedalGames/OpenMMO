import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_knight_top/tripo_v1'
OUTPUT = DIRECTORY / 'fitted_v3'
previous = DIRECTORY / 'fitted_v2/top_female_knight.glb'
doc, binary = read_glb(previous)
binary = bytearray(binary)
data = np.load(OUTPUT / 'sleeve-adjustment.npz')
primitive = doc['meshes'][0]['primitives'][0]
attributes = primitive['attributes']
position = accessor(doc, binary, attributes['POSITION'])
blender_position = position[:, [0, 2, 1]] * np.array([1, -1, 1])
distance, mapping = cKDTree(data['previous']).query(blender_position)
assert distance.max() < 1e-7
updated = data['points'][mapping][:, [0, 2, 1]] * np.array([1, 1, -1])
names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
lookup = [names.index(name) for name in data['bone_names']]
dense = np.zeros((len(position), len(names)))
dense[:, lookup] = data['weights'][mapping]
order = np.argsort(dense, axis=1)[:, ::-1][:, :4]
weights = np.take_along_axis(dense, order, axis=1)
weights /= weights.sum(1, keepdims=True)
order[weights == 0] = 0
normal = accessor(doc, binary, attributes['NORMAL']).copy()
tangent = accessor(doc, binary, attributes['TANGENT']).copy()
unique, first, welded = np.unique(position, axis=0, return_index=True, return_inverse=True)
neighbors = cKDTree(unique).query(unique, k=12)[1]
jacobians = np.repeat(np.eye(3)[None], len(unique), axis=0)
for i in np.flatnonzero(data['amount'][mapping[first]] > 0):
    indices = neighbors[i]
    old = unique[indices] - unique[i]
    new = updated[first[indices]] - updated[first[i]]
    jacobians[i] = np.linalg.lstsq(np.vstack([old, np.eye(3) * .0003]),
                                   np.vstack([new, np.eye(3) * .0003]), rcond=None)[0].T
for i in np.flatnonzero(data['amount'][mapping] > 0):
    matrix = jacobians[welded[i]]
    u, _, vt = np.linalg.svd(matrix)
    if np.linalg.det(u @ vt) < 0:
        u[:, -1] *= -1
    rotation = u @ vt
    normal[i] = rotation @ normal[i]
    normal[i] /= np.linalg.norm(normal[i])
    direction = rotation @ tangent[i, :3]
    direction -= normal[i] * np.dot(direction, normal[i])
    tangent[i, :3] = direction / np.linalg.norm(direction)
for name, value, kind, component in [
    ('POSITION', updated.astype(np.float32), 'VEC3', 5126),
    ('NORMAL', normal, 'VEC3', 5126),
    ('TANGENT', tangent, 'VEC4', 5126),
    ('JOINTS_0', order.astype(np.uint16), 'VEC4', 5123),
    ('WEIGHTS_0', weights.astype(np.float32), 'VEC4', 5126),
]:
    attributes[name] = add_accessor(doc, binary, value, kind, component)
    doc['bufferViews'][doc['accessors'][attributes[name]]['bufferView']]['target'] = 34962
for node in doc['nodes']:
    if 'mesh' in node:
        node.setdefault('extras', {})['fitting_version'] = 3
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'top_female_knight.glb'
write_glb(target, doc, binary)
shutil.copyfile(DIRECTORY / 'fitted_v2/body-occlusion.json', OUTPUT / 'body-occlusion.json')
record = json.loads((OUTPUT / 'sleeve-adjustment.json').read_text())
record.update(date='2026-10-12', input=str(previous.relative_to(ROOT)),
              input_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              triangles=doc['accessors'][primitive['indices']]['count'] // 3,
              scope='Elbow sleeves only. Original v2 torso geometry, canonical bind matrices, UVs, textures and triangles retained. Body mask unchanged.',
              additional_api_credits=0)
(ROOT / 'doc/assets/modular-female-knight-top-fitting-v3.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
