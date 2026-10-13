import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v31', DIRECTORY / 'fitted_v32'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '2ffcd1a57334af801b470ff7807c4d99cecf681cbe24c1e448711d7dffd8dfbe'
report = json.loads((SOURCE / 'fitting.json').read_text())
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
attrs = doc['meshes'][0]['primitives'][0]['attributes']
original = {name: accessor(doc, binary, attrs[name]) for name in ['POSITION', 'NORMAL', 'TANGENT']}
values = {name: array.copy() for name, array in original.items()}
profile_y = np.array([.414, .445, .484, .541, .568, .582, .599])
profile_z = np.array([0, .0003, .001, .002, .0065, .0065, 0])
profile = PchipInterpolator(profile_y, profile_z)
vertices = np.array([vertex for region in report['rear_leather_regions'] if len(region) in [126, 150] for vertex in region])
points = original['POSITION'][vertices].astype(float)
active = (points[:, 1] > profile_y[0]) & (points[:, 1] < profile_y[-1])
changed = vertices[active]
points = points[active]
offset = profile(points[:, 1])
values['POSITION'][changed, 2] = points[:, 2] + offset
values['POSITION'][changed, 0] = points[:, 0] - offset * .65
jacobian = np.broadcast_to(np.eye(3), (len(changed), 3, 3)).copy()
jacobian[:, 2, 1] = profile.derivative()(points[:, 1])
jacobian[:, 0, 1] = -.65 * jacobian[:, 2, 1]
normals = np.linalg.solve(jacobian.transpose(0, 2, 1), original['NORMAL'][changed, :, None]).squeeze(-1)
normals /= np.linalg.norm(normals, axis=1)[:, None]
tangents = np.einsum('nij,nj->ni', jacobian, original['TANGENT'][changed, :3])
tangents -= normals * np.sum(normals * tangents, axis=1)[:, None]
tangents /= np.linalg.norm(tangents, axis=1)[:, None]
values['NORMAL'][changed] = normals
values['TANGENT'][changed, :3] = tangents
for name, array in values.items():
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.shape[1] * 4) == array.shape[1] * 4
    start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[start:start + array.nbytes] = array.tobytes()
    if name == 'POSITION':
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 32
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.pop('rear_tab_alignment', None)
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Bring the wearer-right rear short strap, middle buckle and hanging strap closer to the plate with height-dependent inward Z and slight outward X offsets following the curved plate, retaining the upper connection and fading toward the tip.',
              rear_tab_vertices=changed.tolist(), rear_strap_fit={'profile_y': profile_y.tolist(), 'profile_z': profile_z.tolist()},
              preserved=['upper tab alignment', 'opposite rear strap', 'lowered rear guard', 'front leather', 'waist belt', 'plates', 'UVs', 'textures', 'weights', 'topology', 'rig', 'occlusion mask'])
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
np.testing.assert_array_equal(original['POSITION'][:, 1], values['POSITION'][:, 1])
for name in ['NORMAL', 'TANGENT']:
    np.testing.assert_allclose(np.linalg.norm(values[name][changed, :3], axis=1), 1, atol=1e-6)
validation = {'sha256': report['sha256'], 'changed_vertices': len(changed), 'maximum_inward_shift': float(offset.max()),
              'preserved': report['preserved'], 'unchanged_height': True, 'outward_x_per_inward_z': .65,
              'normalized_shading_frames': True, 'profile': report['rear_strap_fit']}
plate = doc['meshes'][0]['primitives'][1]
plate_points = accessor(doc, binary, plate['attributes']['POSITION'])
plate_faces = accessor(doc, binary, plate['indices']).reshape(-1, 3)
triangles = plate_points[plate_faces].astype(float)
a = triangles[:, 0]
u, v = triangles[:, 1] - a, triangles[:, 2] - a
determinant = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
valid = abs(determinant) > 1e-12
inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
faces = accessor(doc, binary, doc['meshes'][0]['primitives'][0]['indices']).reshape(-1, 3)
faces = faces[np.isin(faces, changed).any(1)]
barycentric = np.array([[1/3, 1/3, 1/3], [.8, .1, .1], [.1, .8, .1], [.1, .1, .8]])
samples = [np.einsum('sc,fcd->fsd', barycentric, positions[faces]).reshape(-1, 3)
           for positions in [original['POSITION'], values['POSITION']]]
gaps = []
heights = []
for old, new in zip(*samples):
    pair = []
    for point in [old, new]:
        delta = point - a
        bu = (delta[:, 0] * v[:, 1] - delta[:, 1] * v[:, 0]) * inverse
        bv = (u[:, 0] * delta[:, 1] - u[:, 1] * delta[:, 0]) * inverse
        z = a[:, 2] + bu * u[:, 2] + bv * v[:, 2]
        hits = z[valid & (bu >= 0) & (bv >= 0) & (bu + bv <= 1) & (z < 0)]
        pair.append(float(hits.min() - point[2]) if len(hits) else float('inf'))
    if np.isfinite(pair).all():
        gaps.append(pair)
        heights.append(float(old[1]))
    assert not (pair[0] == float('inf') and pair[1] <= 0)
gaps = np.array(gaps)
assert len(gaps) > 100
assert not np.any((gaps[:, 0] >= 0) & (gaps[:, 1] <= 0)), [(heights[i], gaps[i].tolist()) for i in np.flatnonzero((gaps[:, 0] >= 0) & (gaps[:, 1] <= 0))]
validation['plate_clearance'] = {'samples': len(gaps), 'minimum_before_after': gaps.min(0).tolist(),
                               'median_before_after': np.median(gaps, axis=0).tolist(), 'new_intersections': 0,
                               'scope': 'Rest-pose interior triangle samples projected along Z onto the rear plate.'}
(OUTPUT / 'strap-fit-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation))
