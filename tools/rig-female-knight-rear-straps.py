import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v21'
OUTPUT = DIRECTORY / 'fitted_v22'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '0266fb47f8af186de9a64a5035b57fa77539f2d3d73c1767e5394815974853f2'
doc, binary = read_glb(source)
binary = bytearray(binary)
attrs = doc['meshes'][0]['primitives'][0]['attributes']
points = accessor(doc, binary, attrs['POSITION'])
joints = accessor(doc, binary, attrs['JOINTS_0'])
weights = accessor(doc, binary, attrs['WEIGHTS_0'])
names = [doc['nodes'][index]['name'] for index in doc['skins'][0]['joints']]
sections = []
for side in [-1, 1]:
    for height in [.541, .486]:
        vertices = np.flatnonzero(
            (points[:, 0] * side > .055) & (points[:, 0] * side < .085)
            & (points[:, 2] < -.075) & (abs(points[:, 1] - height) < .003)
        )
        assert len(vertices) == 8
        center_height = float(points[vertices, 1].mean())
        t = (.5715 - center_height) / (.5715 - .4195)
        leg_weight = t * t * (3 - 2 * t)
        joints[vertices] = [names.index('Hips'), names.index('LeftUpLeg' if side > 0 else 'RightUpLeg'), 0, 0]
        weights[vertices] = [1 - leg_weight, leg_weight, 0, 0]
        if leg_weight > .5:
            joints[vertices] = joints[vertices][:, [1, 0, 2, 3]]
            weights[vertices] = weights[vertices][:, [1, 0, 2, 3]]
        sections.append({'side': side, 'height': center_height, 'leg_weight': leg_weight, 'vertices': vertices.tolist()})

for name, values, component in [('JOINTS_0', joints, 5123), ('WEIGHTS_0', weights, 5126)]:
    attrs[name] = add_accessor(doc, binary, values, 'VEC4', component)
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
doc['nodes'][0]['extras']['fitting_version'] = 22
doc['buffers'][0]['byteLength'] = len(binary)
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update({
    'date': '2026-10-13', 'source': str(source.relative_to(ROOT)), 'source_sha256': source_hash,
    'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'method': 'Use one pelvis/thigh blend across each rear strap cross-section, transitioning smoothly from the unchanged hip-bound buckle to the unchanged thigh-bound tip.',
    'rear_strap_sections': sections,
    'rear_strap_vertices': sorted(vertex for section in sections for vertex in section['vertices']),
    'preserved': ['all geometry', 'normals', 'tangents', 'UVs', 'indices', 'materials', 'textures', 'bones', 'inverse binds', 'occlusion mask', 'buckle and tip weights', 'all other weights'],
    'additional_api_credits': 0,
})
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'changed_vertices': len(report['rear_strap_vertices'])}))
