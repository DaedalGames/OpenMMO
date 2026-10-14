import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
# Optional args reuse this for other female tops: <fitted dir> <part id> <fitting report> <version>.
OUT, PART, REPORT, VERSION = (sys.argv[1:] + ['assets/items/female_knight_top/tripo_v1/fitted_v2', 'top_female_knight',
                                              'doc/assets/modular-female-knight-top-fitting-v2.json', '2'][len(sys.argv) - 1:])
OUT, REPORT, VERSION = ROOT / OUT, ROOT / REPORT, int(VERSION)
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
doc, binary = read_glb(OUT / 'top-fitted-unskinned.glb')
binary = bytearray(binary)
base, base_binary = read_glb(BODY)
skin = base['skins'][0]
ids = skin['joints']
names = [base['nodes'][index]['name'] for index in ids]
mapping = {index: len(doc['nodes']) + i for i, index in enumerate(ids)}
part_nodes = list(doc['scenes'][0]['nodes'])
for index in ids:
    bone = copy.deepcopy(base['nodes'][index])
    if 'children' in bone:
        bone['children'] = [mapping[i] for i in bone['children'] if i in mapping]
    doc['nodes'].append(bone)
children = {child for index in ids for child in base['nodes'][index].get('children', [])}
rig_id = 'human_female_01_local_v1'
doc['scenes'][0]['nodes'].append(len(doc['nodes']))
doc['nodes'].append({'name': 'Armature', 'children': [mapping[i] for i in ids if i not in children], 'extras': {'rig_id': rig_id}})
doc['scenes'][0]['extras'] = {'rig_id': rig_id}
doc['skins'] = [{'joints': [mapping[i] for i in ids], 'skeleton': mapping[skin['skeleton']],
                 'inverseBindMatrices': add_accessor(doc, binary, accessor(base, base_binary, skin['inverseBindMatrices']), 'MAT4')}]
node, = [doc['nodes'][i] for i in part_nodes]
assert not any(key in node for key in ['matrix', 'translation', 'rotation', 'scale'])
node.update(skin=0, extras={'rig_id': rig_id, 'part_id': PART, 'fitting_version': VERSION})
primitive, = doc['meshes'][node['mesh']]['primitives']
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION'])
data = np.load(OUT / 'fit-data.npz')
lookup = np.array([names.index(name) for name in data['bone_names']])
joints = lookup[np.rint(accessor(doc, binary, attrs.pop('_RIG_JOINTS'))).astype(int)].astype(np.uint16)
weights = accessor(doc, binary, attrs.pop('_RIG_WEIGHTS')).astype(np.float32)
assert np.allclose(weights.sum(1), 1)
for key in list(attrs):
    if key.startswith('COLOR_'):
        del attrs[key]
attrs['JOINTS_0'] = add_accessor(doc, binary, joints, 'VEC4', 5123)
attrs['WEIGHTS_0'] = add_accessor(doc, binary, weights, 'VEC4')
for key in ['JOINTS_0', 'WEIGHTS_0']:
    doc['bufferViews'][doc['accessors'][attrs[key]]['bufferView']]['target'] = 34962
if 'TANGENT' in attrs:
    tangent = accessor(doc, binary, attrs['TANGENT'])
    invalid = np.linalg.norm(tangent[:, :3], axis=1) < 1e-6
    if invalid.any():
        normals = accessor(doc, binary, attrs['NORMAL'])[invalid]
        axes = np.eye(3)[np.argmin(np.abs(normals), axis=1)]
        fallback = np.cross(normals, axes)
        tangent[invalid, :3] = fallback / np.linalg.norm(fallback, axis=1, keepdims=True)
        attrs['TANGENT'] = add_accessor(doc, binary, tangent, 'VEC4')
        doc['bufferViews'][doc['accessors'][attrs['TANGENT']]['bufferView']]['target'] = 34962
path = OUT / f'{PART}.glb'
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(path, doc, binary)
report_path = REPORT
report = json.loads(report_path.read_text())
report['rigging'] = {'rig_id': rig_id, 'bones': len(names), 'output': str(path.relative_to(ROOT)),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'vertices': len(points),
                     'exact_female_hierarchy_and_inverse_bind': True,
                     'method': report.get('weights', {}).get('method', 'Regional garment weights authored from original surface. Thorax excludes shoulders and arms; elbow weights limited to cloth; plate and rivet weights follow their own region.')}
report_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report['rigging']))
