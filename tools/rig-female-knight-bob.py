import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
doc, binary = read_glb(OUT / 'hair-fitted-unskinned.glb')
binary = bytearray(binary)
base, base_binary = read_glb(BODY)
skin = base['skins'][0]
joint_ids = skin['joints']
names = [base['nodes'][index]['name'] for index in joint_ids]
mapping = {index: len(doc['nodes']) + i for i, index in enumerate(joint_ids)}
part_nodes = list(doc['scenes'][0]['nodes'])
for index in joint_ids:
    bone = copy.deepcopy(base['nodes'][index])
    if 'children' in bone:
        bone['children'] = [mapping[i] for i in bone['children'] if i in mapping]
    doc['nodes'].append(bone)
children = {child for index in joint_ids for child in base['nodes'][index].get('children', [])}
rig_id = 'human_female_01_local_v1'
doc['scenes'][0]['nodes'].append(len(doc['nodes']))
doc['nodes'].append({'name': 'Armature', 'children': [mapping[i] for i in joint_ids if i not in children],
                     'extras': {'rig_id': rig_id}})
doc['scenes'][0]['extras'] = {'rig_id': rig_id}
inverse = accessor(base, base_binary, skin['inverseBindMatrices'])
doc['skins'] = [{'joints': [mapping[i] for i in joint_ids], 'skeleton': mapping[skin['skeleton']],
                 'inverseBindMatrices': add_accessor(doc, binary, inverse, 'MAT4')}]
vertices = 0
tangent_fallbacks = 0
for index in part_nodes:
    node = doc['nodes'][index]
    assert not any(key in node for key in ['matrix', 'translation', 'rotation', 'scale'])
    node.update(skin=0, extras={'rig_id': rig_id, 'part_id': 'hair_female_knight_bob'})
    for primitive in doc['meshes'][node['mesh']]['primitives']:
        attrs = primitive['attributes']
        count = doc['accessors'][attrs['POSITION']]['count']
        vertices += count
        tangents = accessor(doc, binary, attrs['TANGENT']).copy()
        invalid = np.linalg.norm(tangents[:, :3], axis=1) < 1e-6
        if invalid.any():
            normals = accessor(doc, binary, attrs['NORMAL'])[invalid]
            axes = np.eye(3)[np.argmin(np.abs(normals), axis=1)]
            fallback = np.cross(normals, axes)
            fallback /= np.linalg.norm(fallback, axis=1, keepdims=True)
            tangents[invalid, :3] = fallback
            attrs['TANGENT'] = add_accessor(doc, binary, tangents, 'VEC4')
            doc['bufferViews'][doc['accessors'][attrs['TANGENT']]['bufferView']]['target'] = 34962
            tangent_fallbacks += int(invalid.sum())
        joints = np.zeros((count, 4), dtype=np.uint16)
        weights = np.zeros((count, 4), dtype=np.float32)
        joints[:, 0] = names.index('Head')
        weights[:, 0] = 1
        attrs['JOINTS_0'] = add_accessor(doc, binary, joints, 'VEC4', 5123)
        attrs['WEIGHTS_0'] = add_accessor(doc, binary, weights, 'VEC4')
        for key in ['JOINTS_0', 'WEIGHTS_0']:
            doc['bufferViews'][doc['accessors'][attrs[key]]['bufferView']]['target'] = 34962
target = OUT / 'hair_female_knight_bob.glb'
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(target, doc, binary)
report_path = ROOT / 'doc/assets/modular-female-knight-bob-fitting-v1.json'
report = json.loads(report_path.read_text())
report['rigging'] = {'rig_id': rig_id, 'bones': len(names), 'vertices': vertices,
                     'zero_tangent_orthogonal_fallbacks': tangent_fallbacks,
                     'method': 'Rigid Head weight 1 for the short bob; exact female bone hierarchy, order and inverse bind matrices.',
                     'physics': False, 'output': str(target.relative_to(ROOT)),
                     'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
report_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report['rigging']))
