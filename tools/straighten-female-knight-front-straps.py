import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v36', DIRECTORY / 'fitted_v37'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '587dd8ca70597e3340d0400b4aca108ee02cd447855f90ea6ac90527bc876ec8'
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
values = {name: accessor(doc, binary, index) for name, index in attrs.items()}
points = values['POSITION'].astype(float)
reference, reference_binary = read_glb(DIRECTORY / 'fitted_v34/bottom_female_knight.glb')
original_points = accessor(reference, reference_binary, reference['meshes'][0]['primitives'][0]['attributes']['POSITION'])
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
report = json.loads((SOURCE / 'fitting.json').read_text())
vertices = np.array(report['vertices'])
poses = json.loads((OUTPUT / 'strap-poses.json').read_text())
matrices = np.array([pose['matrices'] for pose in poses]).reshape(-1, 3, 4, 4).transpose(0, 1, 3, 2)
assert poses[1]['name'] == 'idle1' and poses[1]['time'] == 0
names = [doc['nodes'][node]['name'] for node in doc['skins'][0]['joints']]
records = []
for side in [-1, 1]:
    middle = vertices[(original_points[vertices, 0] * side > 0) & (original_points[vertices, 1] > .48) & (original_points[vertices, 1] < .55)]
    adjacent = np.unique(faces[np.isin(faces, middle).any(1)])
    rings = [adjacent[(original_points[adjacent, 1] > low) & (original_points[adjacent, 1] < high)]
             for low, high in [(.56, 1), (.52, .55), (.48, .51), (0, .45)]]
    corner_ids, corner_maps = [], []
    for ring in rings:
        unique, first, inverse = np.unique(original_points[ring], axis=0, return_index=True, return_inverse=True)
        assert len(unique) == 4
        order = np.argsort(unique[:, 0])
        order = np.concatenate([pair[np.argsort(unique[pair, 2])] for pair in [order[:2], order[2:]]])
        rank = np.empty(4, dtype=int)
        rank[order] = np.arange(4)
        corner_ids.append(ring[first[order]])
        corner_maps.append(rank[inverse])
    centers = np.array([points[ids].mean(0) for ids in corner_ids])
    hips, leg = matrices[:, 0], matrices[:, 1 if side > 0 else 2]
    top = np.einsum('nij,kj->nki', hips[:, :3, :3], points[corner_ids[0]]) + hips[:, None, :3, 3]
    bottom = np.einsum('nij,kj->nki', leg[:, :3, :3], points[corner_ids[-1]]) + leg[:, None, :3, 3]
    shifts = np.zeros_like(centers)
    sections = []
    for section, ring in enumerate(rings[1:-1], 1):
        fraction = (centers[0, 1] - centers[section, 1]) / (centers[0, 1] - centers[-1, 1])
        target = top * (1 - fraction) + bottom * fraction

        def fit(weight):
            transform = hips * (1 - weight) + leg * weight
            center = np.linalg.solve(transform[1, :3, :3], (target[1] - transform[1, :3, 3]).T).T
            error = np.einsum('nij,kj->nki', transform[:, :3, :3], center) + transform[:, None, :3, 3] - target
            error[np.array([pose['name'] == 'idle1' for pose in poses])] *= 5
            return np.mean(error ** 2), center

        result = minimize_scalar(lambda weight: fit(weight)[0], bounds=(0, 1), method='bounded')
        _, center = fit(result.x)
        shifts[section] = center.mean(0) - centers[section]
        values['POSITION'][ring] = center[corner_maps[section]]
        joints = [names.index('Hips'), names.index('LeftUpLeg' if side > 0 else 'RightUpLeg'), 0, 0]
        weights = [1 - result.x, result.x, 0, 0]
        if result.x > .5:
            joints[:2], weights[:2] = joints[1::-1], weights[1::-1]
        values['JOINTS_0'][ring] = joints
        values['WEIGHTS_0'][ring] = weights
        sections.append({'vertices': ring.tolist(), 'fraction': fraction, 'leg_weight': result.x, 'offset': shifts[section].tolist()})
    def frame(corners, length):
        return np.column_stack([corners[2:].mean(0) - corners[:2].mean(0), length, corners[[1, 3]].mean(0) - corners[[0, 2]].mean(0)])
    for section, ring in enumerate(rings[1:-1], 1):
        old_frame = frame(points[corner_ids[section]], centers[section - 1] - centers[section + 1])
        new_frame = frame(values['POSITION'][corner_ids[section]], centers[section - 1] + shifts[section - 1] - centers[section + 1] - shifts[section + 1])
        jacobian = new_frame @ np.linalg.inv(old_frame)
        assert np.linalg.det(jacobian) > 0
        normals = np.linalg.solve(jacobian.T, values['NORMAL'][ring].T).T
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        tangent = values['TANGENT'][ring, :3] @ jacobian.T
        tangent -= normals * (tangent * normals).sum(1, keepdims=True)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
        values['NORMAL'][ring] = normals
        values['TANGENT'][ring, :3] = tangent
    records.append({'side': side, 'rings': [ring.tolist() for ring in rings], 'sections': sections})

for name in ['POSITION', 'NORMAL', 'TANGENT', 'JOINTS_0', 'WEIGHTS_0']:
    array = values[name]
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.strides[0]) == array.strides[0]
    offset = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[offset:offset + array.nbytes] = array.tobytes()
    if 'min' in metadata or 'max' in metadata:
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 37
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Straighten the two intermediate sections of each shortened front strap between its fixed waist and clip anchors in idle. Fit shared cross-section pelvis/thigh weights over idle and walk samples.',
              straight_front_straps=records,
              preserved=['waist and clip attachment geometry', 'clip alignment and weights', 'all other geometry and weights', 'topology', 'UVs', 'textures', 'materials', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
after, new_binary = read_glb(target)
changed = np.array([vertex for record in records for section in record['sections'] for vertex in section['vertices']])
for index, primitive in enumerate(doc['meshes'][0]['primitives']):
    np.testing.assert_array_equal(accessor(doc, original_binary, primitive['indices']), accessor(after, new_binary, primitive['indices']))
    for name, attribute in primitive['attributes'].items():
        old, new = accessor(doc, original_binary, attribute), accessor(after, new_binary, attribute)
        keep = np.ones(len(old), dtype=bool)
        if index == 0 and name != 'TEXCOORD_0':
            keep[changed] = False
        np.testing.assert_array_equal(old[keep], new[keep])
validation = {'sha256': report['sha256'], 'changed_vertices': len(changed), 'unchanged_other_attributes': True, 'unchanged_waist_and_clip_anchors': True, 'sections': records}
(OUTPUT / 'straightening-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps({'sha256':report['sha256'], 'changed_vertices':len(changed)}))
