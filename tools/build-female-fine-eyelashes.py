"""Replace textured lash cards with fine tapered curves, preserving corner strands."""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/modular_human_female_01'
OUT = BASE / 'eyelashes_v3'


def main():
    OUT.mkdir(exist_ok=True)
    source = (BASE / 'eyelashes_v2/base-eyelashes-v2.glb').read_bytes()
    assert hashlib.sha256(source).hexdigest() == 'ffcddcd0546a763a7ab0f655cdcbb29ebf9eed047ecce966877edd1a27c0ffcf'
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
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': array.nbytes, 'target': target})
        binary.extend(array.tobytes())
        a = {'bufferView': len(doc['bufferViews']) - 1, 'componentType': component, 'count': len(array), 'type': kind}
        if bounds:
            a.update(min=array.min(axis=0).tolist(), max=array.max(axis=0).tolist())
        doc['accessors'].append(a)
        return len(doc['accessors']) - 1

    body, cards, corners = doc['meshes'][0]['primitives']
    prior = json.loads((BASE / 'eyelashes_v2/validation.json').read_text())
    corner_indices = read(corners['indices']).reshape(-1, 3)
    retained = [corner_indices[i * 16:(i + 1) * 16] for i, strand in enumerate(prior['new_strands'])
                if strand['region'] == 'outer']
    corner_indices = np.concatenate(retained).astype('<u2')
    assert corner_indices.shape == (96, 3)
    corners['indices'] = append(corner_indices.reshape(-1, 1), 'SCALAR', 5123, 34963)
    mapping = json.loads((BASE / 'eyelashes_v1/validation.json').read_text())['mapping']
    positions, normals, indices, strands = [], [], [], []
    for name in ['right_upper', 'left_upper', 'right_lower', 'left_lower']:
        sign = 1 if name.startswith('right') else -1
        upper = name.endswith('upper')
        root = np.array(mapping[name]['root_curve'])
        x0, x1 = root[0, 0] * sign, root[-1, 0] * sign
        samples = np.linspace(.085, .765, 28) if upper else np.linspace(.12, .86, 12)
        for i, s in enumerate(samples):
            s += .002 * np.sin(i * 2.13)
            x = x0 + s * (x1 - x0)
            start = np.array([sign * x, np.interp(x, root[:, 0] * sign, root[:, 1]) - .00008,
                              np.interp(x, root[:, 0] * sign, root[:, 2])])
            variation = 1 + .055 * np.sin(i * 2.4)
            if upper:
                rise = np.interp(s, [.085, .22, .45, .60, .765], [.0010, .0015, .0022, .0026, .00225]) * variation
                sweep = np.interp(s, [.085, .35, .55, .765], [-.00055, -.00020, .0009, .0032])
                end = start + np.array([sign * sweep, -.0014, rise])
                control = start + np.array([sign * sweep * .17, -.0016, rise * .30])
                width = .000058 * (1 + .05 * np.sin(i * 1.7))
            else:
                rise = -(.00055 + .00045 * np.sin(np.pi * s)) * variation
                sweep = (s - .4) * .0017
                end = start + np.array([sign * sweep, -.00085, rise])
                control = start + np.array([sign * sweep * .3, -.0008, rise * .4])
                width = .000034 * (1 + .06 * np.sin(i * 1.7))
            strip = []
            for segment in range(9):
                t = segment / 8
                center = (1 - t) ** 2 * start + 2 * (1 - t) * t * control + t ** 2 * end
                tangent = 2 * (1 - t) * (control - start) + 2 * t * (end - control)
                across = np.array([-tangent[2], 0, tangent[0]])
                across /= np.linalg.norm(across)
                normal = np.cross(tangent, across)
                normal /= np.linalg.norm(normal)
                if normal[1] > 0:
                    normal *= -1
                half_width = width * (1 - t) ** .8 + .0000015
                pair = []
                for side in [-1, 1]:
                    point = center + side * half_width * across
                    pair.append(len(positions))
                    positions.append([point[0], point[2], -point[1]])
                    normals.append([normal[0], normal[2], -normal[1]])
                strip.append(pair)
            for a, b in zip(strip, strip[1:]):
                indices.extend([[a[0], a[1], b[0]], [a[1], b[1], b[0]]])
            strands.append({'group': name, 'root': start.tolist(), 'tip': end.tolist(), 'root_half_width': width})
    new_primitive = {
        'attributes': {
            'POSITION': append(np.array(positions, dtype='<f4'), 'VEC3', 5126, 34962, True),
            'NORMAL': append(np.array(normals, dtype='<f4'), 'VEC3', 5126, 34962),
        },
        'indices': append(np.array(indices, dtype='<u2').reshape(-1, 1), 'SCALAR', 5123, 34963),
        'material': corners['material'],
    }
    doc['meshes'][0]['primitives'] = [body, corners, new_primitive]
    assert binary[:original_length] == source[28 + size:]
    doc['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    output = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    output += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    output += struct.pack('<II', len(binary), 0x004e4942) + binary
    (OUT / 'base-eyelashes-v3.glb').write_bytes(output)
    report = {'source_sha256': hashlib.sha256(source).hexdigest(), 'output_sha256': hashlib.sha256(output).hexdigest(),
              'triangles_before': 21183, 'triangles_after': 20799 + len(corner_indices) + len(indices),
              'removed_card_triangles': 128, 'replaced_inner_extension_triangles': 160,
              'retained_corner_triangles': len(corner_indices), 'new_strand_triangles': len(indices),
              'upper_strands_per_eye': 28, 'lower_strands_per_eye': 12, 'retained_corner_strands_per_eye': 3,
              'original_binary_preserved': True, 'body_primitive_preserved': True,
              'rendered_eyelashes_use_texture': False, 'strands': strands}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'strands'}))


if __name__ == '__main__':
    main()
