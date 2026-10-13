import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v27'
OUTPUT = DIRECTORY / 'fitted_v28'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '26fbfda2e56a7d492b8a3b57e9924e3d6a93ee16f621926efb95a8ac2eac6719'
replacement = json.loads((DIRECTORY / 'fitted_v24/fitting.json').read_text())['rear_guard_replacement']
vertices = np.array(replacement['destination_vertices'])
doc, binary = read_glb(source)
binary = bytearray(binary)
attribute = doc['meshes'][0]['primitives'][0]['attributes']['POSITION']
points = accessor(doc, binary, attribute)
before = points.copy()
translation = np.array([0, -.017, -.0065])
points[vertices] = points[vertices] + translation
metadata = doc['accessors'][attribute]
view = doc['bufferViews'][metadata['bufferView']]
assert view.get('byteStride', 12) == 12
offset = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
binary[offset:offset + points.nbytes] = points.tobytes()
metadata.update(min=points.min(0).tolist(), max=points.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 28
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.pop('rear_plate_changes', None)
report.pop('rear_edge_vertices', None)
report.update(
    date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
    output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    method='Lower the rear central guard by 0.017 in body-height-normalized coordinates, preserving its shape; offset rearward by 0.0065 to clear the body at the lower height.',
    rear_guard_translation={'primitive': 0, 'vertices': vertices.tolist(), 'offset': translation.tolist()},
    preserved=['front guard', 'plates', 'leather', 'topology', 'normals', 'tangents', 'UVs', 'weights', 'materials', 'textures', 'rig', 'occlusion mask'],
    additional_api_credits=0,
)
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
original_doc, original_binary = read_glb(source)
actual_doc, actual_binary = read_glb(target)
for original, actual in zip(original_doc['meshes'][0]['primitives'], actual_doc['meshes'][0]['primitives']):
    np.testing.assert_array_equal(accessor(original_doc, original_binary, original['indices']), accessor(actual_doc, actual_binary, actual['indices']))
    for name, index in original['attributes'].items():
        expected = accessor(original_doc, original_binary, index)
        if index == attribute:
            expected[vertices] = expected[vertices] + translation
        np.testing.assert_array_equal(accessor(actual_doc, actual_binary, actual['attributes'][name]), expected)
assert original_doc['materials'] == actual_doc['materials']
assert original_binary[:offset] == actual_binary[:offset]
assert original_binary[offset + points.nbytes:] == actual_binary[offset + points.nbytes:]
validation = {'sha256': report['sha256'], 'vertices': len(vertices), 'offset': translation.tolist(),
              'before_bounds': [before[vertices].min(0).tolist(), before[vertices].max(0).tolist()],
              'after_bounds': [points[vertices].min(0).tolist(), points[vertices].max(0).tolist()],
              'other_attributes_and_binary_preserved': True}
(OUTPUT / 'guard-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation))
