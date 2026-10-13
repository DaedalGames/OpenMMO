import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v32', DIRECTORY / 'fitted_v33'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '794e8dd91ff593190d8a916dcb8ac555d61c4bba20909075ada8eed54d0be763'
report = json.loads((SOURCE / 'fitting.json').read_text())
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
attrs = doc['meshes'][0]['primitives'][0]['attributes']
original = {name: accessor(doc, binary, attrs[name]) for name in ['POSITION', 'NORMAL', 'TANGENT']}
values = {name: array.copy() for name, array in original.items()}
replacement = json.loads((DIRECTORY / 'fitted_v24/fitting.json').read_text())['rear_guard_replacement']
regions = []
for name, key, inward, amplitude in [('front', 'source_vertices', -1, .018), ('rear', 'destination_vertices', 1, .022)]:
    vertices = np.array(replacement[key])
    points = original['POSITION'][vertices].astype(float)
    height = np.ptp(points[:, 1])
    start = points[:, 1].max() - .15 * height
    length = .85 * height
    t = np.clip((start - points[:, 1]) / length, 0, 1)
    power = 3 if name == 'rear' else 2
    offset = inward * amplitude * t ** power
    values['POSITION'][vertices, 2] = points[:, 2] + offset
    jacobian = np.broadcast_to(np.eye(3), (len(vertices), 3, 3)).copy()
    jacobian[:, 2, 1] = -inward * power * amplitude * t ** (power - 1) / length
    normals = np.linalg.solve(jacobian.transpose(0, 2, 1), original['NORMAL'][vertices, :, None]).squeeze(-1)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    tangents = np.einsum('nij,nj->ni', jacobian, original['TANGENT'][vertices, :3])
    tangents -= normals * np.sum(normals * tangents, axis=1)[:, None]
    tangents /= np.linalg.norm(tangents, axis=1)[:, None]
    values['NORMAL'][vertices] = normals
    values['TANGENT'][vertices, :3] = tangents
    top = t == 0
    np.testing.assert_array_equal(values['POSITION'][vertices[top]], original['POSITION'][vertices[top]])
    regions.append({'name': name, 'vertices': vertices.tolist(), 'bend_start_y': float(start),
                    'maximum_inward_offset': amplitude, 'profile_power': power, 'fixed_top_vertices': int(top.sum())})
changed = np.concatenate([region['vertices'] for region in regions])
for name, array in values.items():
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.shape[1] * 4) == array.shape[1] * 4
    start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[start:start + array.nbytes] = array.tobytes()
    if name == 'POSITION':
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 33
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.pop('rear_tab_vertices', None)
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Curve both central guards gently inward with progressive depth profiles below their fixed top attachments, correcting normals and tangents with the deformation Jacobian.',
              guard_bend_vertices=changed.tolist(), guard_bends=regions,
              preserved=['guard attachment positions', 'straps and buckles', 'plates', 'UVs', 'textures', 'weights', 'topology', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
before, old_binary = read_glb(source)
after, new_binary = read_glb(target)
for index, old in enumerate(before['meshes'][0]['primitives']):
    new = after['meshes'][0]['primitives'][index]
    np.testing.assert_array_equal(accessor(before, old_binary, old['indices']), accessor(after, new_binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a, b = accessor(before, old_binary, attribute), accessor(after, new_binary, new['attributes'][name])
        if index == 0 and name in values:
            keep = np.ones(len(a), dtype=bool)
            keep[changed] = False
            np.testing.assert_array_equal(a[keep], b[keep])
        else:
            np.testing.assert_array_equal(a, b)
np.testing.assert_array_equal(original['POSITION'][:, :2], values['POSITION'][:, :2])
for name in ['NORMAL', 'TANGENT']:
    np.testing.assert_allclose(np.linalg.norm(values[name][changed, :3], axis=1), 1, atol=1e-6)
faces = accessor(doc, binary, doc['meshes'][0]['primitives'][0]['indices']).reshape(-1, 3)
faces = faces[np.isin(faces, changed).any(1)]
triangles = values['POSITION'][faces].astype(float)
assert np.all(np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) > 1e-10)
validation = {'sha256': report['sha256'], 'changed_vertices': len(changed), 'regions': regions,
              'preserved': report['preserved'], 'unchanged_width_and_height': True,
              'normalized_shading_frames': True, 'nondegenerate_triangles': True}
(OUTPUT / 'guard-bend-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps({key: value for key, value in validation.items() if key != 'regions'}))
