import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v34', DIRECTORY / 'fitted_v35'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == 'e85708cd09bfa2f85654b64ede3024711dfd5d40001ea95635297727032c81e6'
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
report = json.loads((SOURCE / 'fitting.json').read_text())
attrs = doc['meshes'][0]['primitives'][0]['attributes']
values = {name: accessor(doc, binary, index) for name, index in attrs.items()}
vertices = np.array(report['vertices'])
points = values['POSITION'][vertices].astype(float)
low, high = .424, .566
offset = np.array([0, .071, -.0145])
t = np.clip((points[:, 1] - low) / (high - low), 0, 1)
influence = 1 - t * t * (3 - 2 * t)
slope = -6 * t * (1 - t) / (high - low)
values['POSITION'][vertices] = points + influence[:, None] * offset
jacobian = np.broadcast_to(np.eye(3), (len(vertices), 3, 3)).copy()
jacobian[:, :, 1] += slope[:, None] * offset
assert np.linalg.det(jacobian).min() > .24
normal = np.linalg.solve(jacobian.transpose(0, 2, 1), values['NORMAL'][vertices, :, None])[:, :, 0]
normal /= np.linalg.norm(normal, axis=1, keepdims=True)
tangent = np.einsum('nij,nj->ni', jacobian, values['TANGENT'][vertices, :3])
tangent -= normal * (tangent * normal).sum(1, keepdims=True)
tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
values['NORMAL'][vertices] = normal
values['TANGENT'][vertices, :3] = tangent
names = [doc['nodes'][node]['name'] for node in doc['skins'][0]['joints']]
for side in [-1, 1]:
    selected = vertices[points[:, 0] * side > 0]
    heights = accessor(doc, original_binary, attrs['POSITION'])[selected, 1]
    leg = np.clip((high - heights) / (high - low), 0, 1)
    leg = leg * leg * (3 - 2 * leg)
    values['JOINTS_0'][selected] = [names.index('Hips'), names.index('LeftUpLeg' if side > 0 else 'RightUpLeg'), 0, 0]
    values['WEIGHTS_0'][selected] = np.column_stack([1 - leg, leg, np.zeros((len(leg), 2))])
    dominant = selected[leg > .5]
    values['JOINTS_0'][dominant] = values['JOINTS_0'][dominant][:, [1, 0, 2, 3]]
    values['WEIGHTS_0'][dominant] = values['WEIGHTS_0'][dominant][:, [1, 0, 2, 3]]
    values['JOINTS_0'][selected] = np.where(values['WEIGHTS_0'][selected] > 0, values['JOINTS_0'][selected], 0)

for name in ['POSITION', 'NORMAL', 'TANGENT', 'JOINTS_0', 'WEIGHTS_0']:
    array = values[name]
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.strides[0]) == array.strides[0]
    start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[start:start + array.nbytes] = array.tobytes()
    if name == 'POSITION' or 'min' in metadata or 'max' in metadata:
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
for primitive in doc['meshes'][0]['primitives']:
    for index in primitive['attributes'].values():
        metadata = doc['accessors'][index]
        if 'min' in metadata or 'max' in metadata:
            array = accessor(doc, binary, index)
            metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 35
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.pop('front_plate_changes', None)
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Shorten both front leather straps, translating the unchanged-size lower clips to the boot thigh-plate rims. Retain waist anchors and blend pelvis/thigh weights across the shorter straps.',
              front_strap_shortening={'vertices': vertices.tolist(), 'clip_maximum_source_y': low, 'fixed_anchor_y': high, 'clip_translation': offset.tolist()},
              preserved=['clip dimensions and detail', 'waist anchors', 'all other geometry and weights', 'topology', 'UVs', 'textures', 'materials', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
validation = {'sha256': report['sha256'], 'selected_vertices': len(vertices), 'clip_translation': offset.tolist()}
after, after_binary = read_glb(target)
for index, primitive in enumerate(doc['meshes'][0]['primitives']):
    np.testing.assert_array_equal(accessor(doc, original_binary, primitive['indices']), accessor(after, after_binary, primitive['indices']))
    for name, attribute in primitive['attributes'].items():
        old, new = accessor(doc, original_binary, attribute), accessor(after, after_binary, attribute)
        keep = np.ones(len(old), dtype=bool)
        if index == 0 and name != 'TEXCOORD_0':
            keep[vertices] = False
        np.testing.assert_array_equal(old[keep], new[keep])
clips = vertices[points[:, 1] <= low]
np.testing.assert_allclose(values['POSITION'][clips], accessor(doc, original_binary, attrs['POSITION'])[clips] + offset, atol=3e-8)
np.testing.assert_allclose(values['WEIGHTS_0'][clips, 0], 1)
validation.update(unchanged_other_attributes=True, unchanged_clip_dimensions=True, rigid_thigh_bound_clips=True,
                  minimum_deformation_determinant=float(np.linalg.det(jacobian).min()))
(OUTPUT / 'shortening-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation))
