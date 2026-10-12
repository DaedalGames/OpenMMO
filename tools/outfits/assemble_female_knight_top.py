import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

VERSION = sys.argv[1] if len(sys.argv) > 1 else 'v2'
assert VERSION in ['v2', 'v3']
OUT = ROOT / f'assets/items/female_knight_top/tripo_v1/fitted_{VERSION}'
base, base_binary = read_glb(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
top, top_binary = read_glb(OUT / 'top_female_knight.glb')
base_binary = bytearray(base_binary)
mask = json.loads((OUT / 'body-occlusion.json').read_text())
primitive = base['meshes'][0]['primitives'][0]
faces = accessor(base, base_binary, primitive['indices']).reshape(-1, 3)
keep = np.ones(len(faces), dtype=bool)
keep[mask['hide_triangle_indices']] = False
primitive['indices'] = add_accessor(base, base_binary, faces[keep].reshape(-1, 1), 'SCALAR', 5125)
base['bufferViews'][base['accessors'][primitive['indices']]['bufferView']]['target'] = 34963
base_binary.extend(b'\0' * (-len(base_binary) % 4))
binary_offset = len(base_binary)
base_binary.extend(top_binary)
view_offset, accessor_offset = len(base['bufferViews']), len(base['accessors'])
for view in copy.deepcopy(top['bufferViews']):
    view['byteOffset'] = view.get('byteOffset', 0) + binary_offset
    base['bufferViews'].append(view)
for value in copy.deepcopy(top['accessors']):
    value['bufferView'] += view_offset
    base['accessors'].append(value)
image_offset = len(base.get('images', []))
for value in copy.deepcopy(top.get('images', [])):
    value['bufferView'] += view_offset
    base.setdefault('images', []).append(value)
sampler_offset = len(base.get('samplers', []))
base.setdefault('samplers', []).extend(copy.deepcopy(top.get('samplers', [])))
texture_offset = len(base.get('textures', []))
for value in copy.deepcopy(top.get('textures', [])):
    value['source'] += image_offset
    if 'sampler' in value:
        value['sampler'] += sampler_offset
    base.setdefault('textures', []).append(value)


def remap_texture(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'index':
                value[key] += texture_offset
            else:
                remap_texture(item)
    elif isinstance(value, list):
        for item in value:
            remap_texture(item)


material_offset = len(base['materials'])
for value in copy.deepcopy(top['materials']):
    remap_texture(value)
    base['materials'].append(value)
mesh = copy.deepcopy(top['meshes'][0])
for primitive in mesh['primitives']:
    primitive['attributes'] = {name: value + accessor_offset for name, value in primitive['attributes'].items()}
    primitive['indices'] += accessor_offset
    primitive['material'] += material_offset
mesh_index = len(base['meshes'])
base['meshes'].append(mesh)
base['scenes'][0]['nodes'].append(len(base['nodes']))
base['nodes'].append({'name': 'top_female_knight', 'mesh': mesh_index, 'skin': 0,
                      'extras': {'part_id': 'top_female_knight', 'rig_id': 'human_female_01_local_v1'}})
base['scenes'][0]['extras'] = {'equipment': f'female_knight_top_{VERSION}', 'body_mask_applied': True}
base['buffers'][0]['byteLength'] = len(base_binary)
write_glb(OUT / 'female-knight-assembled.glb', base, base_binary)
print('Saved assembled GLB with existing 9 animations and reversible body mask.')
