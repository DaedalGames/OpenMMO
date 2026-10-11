"""Adjust inner/outer lash lengths and add a small lateral corner fan."""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/modular_human_female_01/eyelashes_v1'
OUT = ROOT / 'assets/modular_human_female_01/eyelashes_v2'


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    OUT.mkdir(exist_ok=True)
    source = (BASE / 'base-eyelashes-v1.glb').read_bytes()
    assert hashlib.sha256(source).hexdigest() == '6f79dd71a30033ec42a23bcdcc251830887ca0e414cfe5a251c4fdcb3ff37bac'
    size = struct.unpack_from('<I', source, 12)[0]
    doc = json.loads(source[20:20 + size])
    binary = bytearray(source[28 + size:])
    original_length = len(binary)

    def read(index):
        a = doc['accessors'][index]
        v = doc['bufferViews'][a['bufferView']]
        width = {'VEC3': 3, 'VEC2': 2, 'SCALAR': 1}[a['type']]
        return np.frombuffer(binary, dtype={5126: '<f4', 5123: '<u2', 5125: '<u4'}[
            a['componentType']], count=a['count'] * width,
            offset=v.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(a['count'], width).copy()

    def append(array, kind, component, target, bounds=False):
        binary.extend(b'\0' * (-len(binary) % 4))
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary),
                                  'byteLength': array.nbytes, 'target': target})
        binary.extend(array.tobytes())
        a = {'bufferView': len(doc['bufferViews']) - 1, 'componentType': component,
             'count': len(array), 'type': kind}
        if bounds:
            a.update(min=array.min(axis=0).tolist(), max=array.max(axis=0).tolist())
        doc['accessors'].append(a)
        return len(doc['accessors']) - 1

    primitive = doc['meshes'][0]['primitives'][1]
    uv = read(primitive['attributes']['TEXCOORD_1'])
    original_uv = uv.copy()
    positions = read(primitive['attributes']['POSITION'])
    world = positions[:, [0, 2, 1]].copy()
    world[:, 1] *= -1
    source_indices = read(3).reshape(-1, 3)
    selection = json.loads((BASE / 'selected-faces.json').read_text())
    mapping = json.loads((BASE / 'validation.json').read_text())['mapping']
    with Image.open(BASE / 'eyelash-fringe.png') as image:
        alpha = np.asarray(image.getchannel('A'))
    height, width = alpha.shape
    affected = []
    new_positions, new_normals, new_indices = [], [], []
    strand_records = []
    for name in ['right_upper', 'left_upper']:
        sign = 1 if name.startswith('right') else -1
        root = np.array(mapping[name]['root_curve'])
        x0, x1 = min(root[:, 0] * sign), max(root[:, 0] * sign)
        vertices = np.unique(source_indices[selection[name]])
        affected.extend(vertices.tolist())
        for vertex in vertices:
            s = np.clip((world[vertex, 0] * sign - x0) / (x1 - x0), 0, 1)
            u = float(uv[vertex, 0])
            visible = np.where(alpha[:, int(u * (width - 1))] > 80)[0]
            root_v = (visible.max() - 2) / height if len(visible) else .75
            scale = 1 + .5 * (1 - smoothstep(.20, .50, s)) - .14 * smoothstep(.55, .9, s)
            uv[vertex, 1] = root_v + (uv[vertex, 1] - root_v) / scale
        strand_specs = [('inner', s) for s in [.13, .20, .27, .34, .41]]
        strand_specs += [('outer', s) for s in [.73, .765, .80]]
        for strand, (region, s) in enumerate(strand_specs):
            x = x0 + s * (x1 - x0)
            start = np.array([x * sign, np.interp(x, root[:, 0] * sign, root[:, 1]) - .00008,
                              np.interp(x, root[:, 0] * sign, root[:, 2])])
            if region == 'outer':
                length = [.0060, .0064, .0062][strand - 5]
                rise = [.0011, .0003, -.00055][strand - 5]
                end = start + np.array([sign * length, -.0010, rise])
                control = start + np.array([sign * length * .60, -.0014, rise - .0005])
            else:
                length = [.0010, .0012, .0013, .0014, .0015][strand]
                end = start + np.array([-sign * .00055, -.0011, length])
                control = start + np.array([-sign * .0002, -.0009, length * .40])
            curve = []
            for i in range(9):
                t = i / 8
                center = (1 - t) ** 2 * start + 2 * (1 - t) * t * control + t * t * end
                tangent = 2 * (1 - t) * (control - start) + 2 * t * (end - control)
                across = np.array([-tangent[2], 0, tangent[0]])
                across /= np.linalg.norm(across)
                half_width = (.000065 if region == 'outer' else .000052) * (1 - t) ** .8 + .000002
                pair = []
                for side in [-1, 1]:
                    point = center + side * half_width * across
                    pair.append(len(new_positions))
                    new_positions.append([point[0], point[2], -point[1]])
                    new_normals.append([0, 0, 1])
                curve.append(pair)
            for a, b in zip(curve, curve[1:]):
                new_indices.extend([[a[0], a[1], b[0]], [a[1], b[1], b[0]]])
            strand_records.append({'side': name, 'region': region, 'strand': strand, 'root': start.tolist(),
                                   'tip': end.tolist(), 'length': length})
    primitive['attributes']['TEXCOORD_1'] = append(uv, 'VEC2', 5126, 34962)
    position_accessor = append(np.array(new_positions, dtype='<f4'), 'VEC3', 5126, 34962, True)
    normal_accessor = append(np.array(new_normals, dtype='<f4'), 'VEC3', 5126, 34962)
    index_accessor = append(np.array(new_indices, dtype='<u2').reshape(-1, 1), 'SCALAR', 5123, 34963)
    doc['materials'].append({'name': 'Fine corner lashes', 'doubleSided': True,
                             'pbrMetallicRoughness': {'baseColorFactor': [.015, .010, .007, 1],
                                                     'metallicFactor': 0, 'roughnessFactor': .85}})
    doc['meshes'][0]['primitives'].append({'attributes': {'POSITION': position_accessor, 'NORMAL': normal_accessor},
                                          'indices': index_accessor, 'material': len(doc['materials']) - 1})
    assert binary[:original_length] == source[28 + size:]
    untouched = np.ones(len(uv), dtype=bool)
    untouched[affected] = False
    assert np.array_equal(uv[untouched], original_uv[untouched])
    doc['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    output = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    output += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    output += struct.pack('<II', len(binary), 0x004e4942) + binary
    (OUT / 'base-eyelashes-v2.glb').write_bytes(output)
    report = {'source_sha256': hashlib.sha256(source).hexdigest(), 'output_sha256': hashlib.sha256(output).hexdigest(),
              'triangles_before': 20927, 'triangles_after': 20927 + len(new_indices),
              'inner_length_scale': 1.5, 'outer_length_scale': .86,
              'inner_extension_strands_per_eye': 5, 'outer_extension_strands_per_eye': 3,
              'new_triangles': len(new_indices), 'original_binary_preserved': True,
              'original_geometry_and_textures_preserved': True, 'lower_lash_uv_preserved': True,
              'upper_uv_vertices': len(set(affected)), 'new_strands': strand_records}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'new_strands'}))


if __name__ == '__main__':
    main()
