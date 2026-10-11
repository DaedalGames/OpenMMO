"""Apply a transparent lash material while preserving the source mesh buffers."""
import collections
import copy
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/modular_human_female_01/eyelashes_v1'
SOURCE = ROOT / 'assets/modular_human_female_01/tripo_api_v3/base-review.glb'


def main():
    source = SOURCE.read_bytes()
    assert hashlib.sha256(source).hexdigest() == '24fe1ccd3031f6cd9a87abb32d65785ecfcb84e316d58e88dd68720c7ec416b7'
    size = struct.unpack_from('<I', source, 12)[0]
    doc = json.loads(source[20:20 + size])
    binary = bytearray(source[28 + size:])
    original_length = len(binary)
    original_doc = copy.deepcopy(doc)

    def read(index):
        accessor = doc['accessors'][index]
        view = doc['bufferViews'][accessor['bufferView']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        width = {'VEC3': 3, 'VEC2': 2, 'SCALAR': 1}[accessor['type']]
        return np.frombuffer(binary, dtype={5126: '<f4', 5123: '<u2', 5125: '<u4'}[
            accessor['componentType']], count=accessor['count'] * width,
            offset=offset).reshape(accessor['count'], width).copy()

    def append_view(data, target=None):
        binary.extend(b'\0' * (-len(binary) % 4))
        view = {'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)}
        if target:
            view['target'] = target
        doc['bufferViews'].append(view)
        binary.extend(data)
        return len(doc['bufferViews']) - 1

    def append_accessor(array, kind, component, target):
        view = append_view(array.tobytes(), target)
        doc['accessors'].append({'bufferView': view, 'componentType': component,
                                 'count': len(array), 'type': kind})
        return len(doc['accessors']) - 1

    primitive = doc['meshes'][0]['primitives'][0]
    positions = read(primitive['attributes']['POSITION'])
    positions = positions[:, [0, 2, 1]]
    positions[:, 1] *= -1
    indices = read(primitive['indices']).reshape(-1, 3)
    selected = json.loads((OUT / 'selected-faces.json').read_text())
    all_lashes = sorted(f for group in selected.values() for f in group)
    assert len(all_lashes) == len(set(all_lashes)) == 128
    assert len(indices) == 20927
    texture_path = OUT / 'eyelash-fringe.png'
    with Image.open(texture_path) as image:
        alpha = np.asarray(image.getchannel('A'))
    image_height, image_width = alpha.shape
    assert alpha.min() == 0 and alpha.max() == 255
    uv = np.zeros((len(positions), 2), dtype='<f4')
    mapping = {}
    for name, faces in selected.items():
        sign = 1 if name.startswith('right') else -1
        edge_counts = collections.Counter()
        coordinates = {}
        for face in faces:
            points = [tuple(p.round(6)) for p in positions[indices[face]]]
            for point in points:
                coordinates[point] = np.asarray(point)
            for a, b in zip(points, points[1:] + points[:1]):
                edge_counts[tuple(sorted((a, b)))] += 1
        boundary = collections.defaultdict(list)
        for (a, b), count in edge_counts.items():
            if count == 1:
                boundary[a].append(b)
                boundary[b].append(a)
        assert all(len(neighbors) == 2 for neighbors in boundary.values())
        inner = min(boundary, key=lambda p: p[0] * sign)
        outer = max(boundary, key=lambda p: p[0] * sign)
        paths = []
        for neighbor in boundary[inner]:
            path = [inner, neighbor]
            while path[-1] != outer:
                path.append(next(p for p in boundary[path[-1]] if p != path[-2]))
                assert len(path) <= len(boundary)
            paths.append(np.array(path))
        root, tip = sorted(paths, key=lambda path: path[:, 1].mean(), reverse=True)
        root = root[np.argsort(root[:, 0] * sign)]
        tip = tip[np.argsort(tip[:, 0] * sign)]
        x0, x1 = inner[0] * sign, outer[0] * sign
        vertices = np.unique(indices[faces])
        for vertex in vertices:
            point = positions[vertex]
            x = point[0] * sign
            start = np.array([np.interp(x, root[:, 0] * sign, root[:, axis]) for axis in [1, 2]])
            end = np.array([np.interp(x, tip[:, 0] * sign, tip[:, axis]) for axis in [1, 2]])
            delta = end - start
            fraction = np.clip(np.dot(point[1:] - start, delta) / max(np.dot(delta, delta), 1e-12), 0, 1)
            u = .055 + .89 * np.clip((x - x0) / (x1 - x0), 0, 1)
            column = int(u * (image_width - 1))
            visible = np.where(alpha[:, column] > 80)[0]
            root_v = (visible.max() - 2) / image_height if len(visible) else .75
            length = 1.8 if name.endswith('lower') else 1.0
            uv[vertex] = (u, root_v * (1 - fraction * length))
        mapping[name] = {'triangles': len(faces), 'root_curve': root.tolist(), 'tip_curve': tip.tolist()}
    uv_accessor = append_accessor(uv, 'VEC2', 5126, 34962)
    texture_view = append_view(texture_path.read_bytes())
    doc['images'].append({'name': 'Natural eyelash fringe alpha', 'mimeType': 'image/png',
                          'bufferView': texture_view})
    doc.setdefault('samplers', []).append({'magFilter': 9729, 'minFilter': 9987,
                                          'wrapS': 33071, 'wrapT': 33071})
    doc['textures'].append({'source': len(doc['images']) - 1, 'sampler': len(doc['samplers']) - 1})
    doc['materials'].append({'name': 'Eyelashes alpha cutout', 'alphaMode': 'MASK',
                             'alphaCutoff': .18, 'doubleSided': True,
                             'pbrMetallicRoughness': {'baseColorFactor': [.25, .16, .10, 1],
                                 'baseColorTexture': {'index': len(doc['textures']) - 1, 'texCoord': 1},
                                 'metallicFactor': 0, 'roughnessFactor': .85}})
    body_mask = np.ones(len(indices), dtype=bool)
    body_mask[all_lashes] = False
    body = copy.deepcopy(primitive)
    body['indices'] = append_accessor(indices[body_mask].astype('<u2').reshape(-1, 1), 'SCALAR', 5123, 34963)
    lashes = copy.deepcopy(primitive)
    lashes['indices'] = append_accessor(indices[all_lashes].astype('<u2').reshape(-1, 1), 'SCALAR', 5123, 34963)
    lashes['attributes']['TEXCOORD_1'] = uv_accessor
    lashes['material'] = len(doc['materials']) - 1
    doc['meshes'][0]['primitives'] = [body, lashes]
    assert binary[:original_length] == source[28 + size:]
    assert doc['materials'][0] == original_doc['materials'][0]
    doc['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    packed = struct.pack('<III', 0x46546C67, 2, 28 + len(encoded) + len(binary))
    packed += struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
    packed += struct.pack('<II', len(binary), 0x004E4942) + binary
    (OUT / 'base-eyelashes-v1.glb').write_bytes(packed)
    report = {'source_sha256': hashlib.sha256(source).hexdigest(),
              'output_sha256': hashlib.sha256(packed).hexdigest(),
              'triangles_before': len(indices), 'triangles_after': len(indices),
              'body_triangles': int(body_mask.sum()), 'eyelash_triangles': len(all_lashes),
              'original_binary_preserved': True, 'body_material_preserved': True,
              'original_accessors_preserved': True, 'original_images_preserved': True,
              'alpha_cutoff': .18, 'mapping': mapping}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'mapping'}))


if __name__ == '__main__':
    main()
