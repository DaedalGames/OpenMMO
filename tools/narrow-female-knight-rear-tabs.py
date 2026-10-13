import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v28', DIRECTORY / 'fitted_v29'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '523c822e2c0dc6ea1b5adb033956fc263d901f8eac3cd30efde0cb7f824c0507'
report = json.loads((SOURCE / 'fitting.json').read_text())
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
attrs = doc['meshes'][0]['primitives'][0]['attributes']
original = {name: accessor(doc, binary, attrs[name]) for name in ['POSITION', 'NORMAL', 'TANGENT']}
values = {name: array.copy() for name, array in original.items()}
regions = []
centers = {}
groups = []
for region in report['rear_leather_regions']:
    if len(region) not in [126, 269]:
        continue
    vertices = np.array(region)
    vertices = vertices[original['POSITION'][vertices, 1] > .584]
    points = original['POSITION'][vertices].astype(float)
    upper = points[points[:, 1] >= .600]
    center = float((upper[:, 0].min() + upper[:, 0].max()) / 2)
    centers[int(np.sign(center))] = center
    groups.append((vertices, center, False))
waist = np.array(next(region for region in report['rear_leather_regions'] if len(region) == 1136))
for side, center in centers.items():
    points = original['POSITION'][waist]
    selected = (points[:, 0] * side > .025) & (abs(points[:, 0]) < .074) & (points[:, 2] < -.032) & (points[:, 1] < .623)
    groups.append((waist[selected], center, True))
for vertices, center, folded in groups:
    points = original['POSITION'][vertices].astype(float)
    t = np.clip(((.623 - points[:, 1]) / .007 if folded else (points[:, 1] - .584) / .016), 0, 1)
    scale = 1 - .30 * t * t * (3 - 2 * t)
    derivative = .30 * 6 * t * (1 - t) / .007 if folded else -.30 * 6 * t * (1 - t) / .016
    values['POSITION'][vertices, 0] = center + (points[:, 0] - center) * scale
    jacobian = np.broadcast_to(np.eye(3), (len(vertices), 3, 3)).copy()
    jacobian[:, 0, 0] = scale
    jacobian[:, 0, 1] = (points[:, 0] - center) * derivative
    normals = np.linalg.solve(jacobian.transpose(0, 2, 1), original['NORMAL'][vertices, :, None]).squeeze(-1)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    tangents = np.einsum('nij,nj->ni', jacobian, original['TANGENT'][vertices, :3])
    tangents -= normals * np.sum(normals * tangents, axis=1)[:, None]
    tangents /= np.linalg.norm(tangents, axis=1)[:, None]
    values['NORMAL'][vertices] = normals
    values['TANGENT'][vertices, :3] = tangents
    full = t == 1
    regions.append({'vertices': vertices.tolist(), 'center_x': center, 'folded_tab': folded,
                    'full_reduction_width_before': float(np.ptp(points[full, 0])),
                    'full_reduction_width_after': float(np.ptp(values['POSITION'][vertices[full], 0]))})
assert len(regions) == 4
changed = np.concatenate([region['vertices'] for region in regions])
for name, array in values.items():
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.shape[1] * 4) == array.shape[1] * 4
    start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[start:start + array.nbytes] = array.tobytes()
    if name == 'POSITION':
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 29
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.pop('rear_guard_translation', None)
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Narrow the two upper rear leather tabs by 30 percent in X, fading to the original width at the waist belt and lower buckles. Transform shading frames with the deformation Jacobian.',
              rear_tab_vertices=changed.tolist(), rear_tab_regions=regions,
              preserved=['lowered rear guard', 'front leather', 'waist belt', 'lower straps and buckles', 'plates', 'UVs', 'textures', 'weights', 'topology', 'rig', 'occlusion mask'])
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
np.testing.assert_array_equal(original['POSITION'][:, 1:], values['POSITION'][:, 1:])
for name in ['NORMAL', 'TANGENT']:
    np.testing.assert_allclose(np.linalg.norm(values[name][changed, :3], axis=1), 1, atol=1e-6)
for region in regions:
    assert abs(region['full_reduction_width_after'] / region['full_reduction_width_before'] - .7) < 1e-6
validation = {'sha256': report['sha256'], 'changed_vertices': len(changed), 'upper_width_ratio': .7,
              'preserved': report['preserved'], 'unchanged_height_and_depth': True,
              'normalized_shading_frames': True, 'regions': regions}
(OUTPUT / 'tab-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps({key: value for key, value in validation.items() if key != 'regions'}))
