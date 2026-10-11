"""Seat the upper lashes on the corrected eye texture's eyelid line."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/modular_human_female_01'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v6', 'v7', 'v8', 'v9', 'v10'], default='v6')
    version = parser.parse_args().version
    out = BASE / f'eyelashes_{version}'
    source_paths = {'v6': 'eyes_v2/base-eyes-v2.glb', 'v7': 'eyes_v4/base-eyes-v4.glb',
                    'v8': 'eyes_v6/base-eyes-v6.glb', 'v9': 'eyelashes_v8/base-eyelashes-v8.glb',
                    'v10': 'eyelashes_v9/base-eyelashes-v9.glb'}
    source = (BASE / source_paths[version]).read_bytes()
    if version == 'v6':
        assert hashlib.sha256(source).hexdigest() == 'df16f3f8775f1a91e87dd2d90980415572ca6913f57b5b4b1cf324a9b0cf4e6e'
    size = struct.unpack_from('<I', source, 12)[0]
    doc = json.loads(source[20:20 + size])
    binary = bytearray(source[28 + size:])

    def read(index):
        accessor = doc['accessors'][index]
        view = doc['bufferViews'][accessor['bufferView']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        width = {'VEC3': 3, 'SCALAR': 1}[accessor['type']]
        values = np.frombuffer(binary, dtype={5126: '<f4', 5123: '<u2', 5125: '<u4'}[
            accessor['componentType']], offset=offset, count=accessor['count'] * width)
        return values.reshape(accessor['count'], width).copy(), offset

    body, corners, lashes = doc['meshes'][0]['primitives']
    positions, _ = read(body['attributes']['POSITION'])
    indices, _ = read(body['indices'])
    faces = positions[indices.reshape(-1, 3)].astype(np.float64)
    faces = faces[(faces[:, :, 1].max(axis=1) > .932) & (faces[:, :, 1].min(axis=1) < .945)]

    def surface_depth(x, y):
        origin = faces[:, 0, :2]
        a, b = faces[:, 1, :2] - origin, faces[:, 2, :2] - origin
        delta = np.array([x, y]) - origin
        determinant = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        valid = abs(determinant) > 1e-14
        u = np.zeros(len(faces))
        v = np.zeros(len(faces))
        u[valid] = (delta[valid, 0] * b[valid, 1] - delta[valid, 1] * b[valid, 0]) / determinant[valid]
        v[valid] = (a[valid, 0] * delta[valid, 1] - a[valid, 1] * delta[valid, 0]) / determinant[valid]
        hit = valid & (u >= -1e-8) & (v >= -1e-8) & (u + v <= 1 + 1e-8)
        assert hit.any()
        depth = faces[:, 0, 2] + u * (faces[:, 1, 2] - faces[:, 0, 2]) + v * (faces[:, 2, 2] - faces[:, 0, 2])
        return float(depth[hit].max())

    line_roots = {}
    if version == 'v9':
        previous = json.loads((BASE / 'eyelashes_v8/validation.json').read_text())
        line_roots = {(s['group'], s['strand']): s['root_before'][1] for s in previous['strands']}
    records = []
    for primitive, is_corner in [(corners, True), (lashes, False)]:
        points, offset = read(primitive['attributes']['POSITION'])
        normals, normal_offset = read(primitive['attributes']['NORMAL'])
        before = points.copy()
        indices, _ = read(primitive['indices'])
        strands = sorted(set(indices.ravel() // 18)) if is_corner else range(56)
        for strand in strands:
            selection = slice(strand * 18, (strand + 1) * 18)
            root = before[strand * 18:strand * 18 + 2].astype(float).mean(axis=0)
            progress = (strand % 28) / 27
            rise = .00025 if is_corner else .0003 + .0003 * np.sin(np.pi * progress)
            if version == 'v7':
                rise = -.00025 if is_corner else -.00035 - .0003 * np.sin(np.pi * progress)
            crest_depth = None
            if version == 'v8':
                rim_height = .0006 if is_corner else .0012
                heights = np.linspace(root[1], root[1] + rim_height, 121)
                depths = np.array([surface_depth(root[0], height) for height in heights])
                peaks = np.flatnonzero((depths[1:-1] > depths[:-2]) & (depths[1:-1] >= depths[2:])) + 1
                peak = int(peaks[0]) if len(peaks) else int(depths.argmax())
                crest_depth = float(depths[peak])
                ridge = int(np.flatnonzero(depths[:peak + 1] >= crest_depth - .000025)[0])
                rise = float(heights[ridge] - root[1])
            if version == 'v10':
                rise = 0
                depth = root[2]
            elif version == 'v9':
                line_height = line_roots[('corner' if is_corner else 'upper', int(strand))]
                rise = min(0, line_height + .00006 - root[1])
                depth = root[2]
            else:
                depth = surface_depth(root[0], root[1] + rise) + .000025
            shift = np.array([0, rise, depth - root[2]])
            points[selection] = before[selection].astype(float) + shift
            assert np.allclose(points[selection] - before[selection], shift, atol=6e-8, rtol=0)
            angle = 0
            if version in ('v7', 'v8'):
                local = before[selection].astype(float) - root
                anchor = root + shift
                for degrees in range(0, 76, 3):
                    angle = np.deg2rad(degrees)
                    rotation = np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)],
                                         [0, np.sin(angle), np.cos(angle)]])
                    candidate = local @ rotation.T + anchor
                    centers = candidate.reshape(9, 2, 3).mean(axis=1)
                    if all(p[2] >= surface_depth(p[0], p[1]) + .00001 for p in centers[1:]):
                        break
                else:
                    raise ValueError(f'Cannot clear eyelid for strand {strand}')
                points[selection] = candidate
                normals[selection] = normals[selection].astype(float) @ rotation.T
            if version == 'v10':
                strip = before[selection].astype(float).copy()
                root_offsets = np.array([surface_depth(p[0], p[1]) - .000012 - p[2] for p in strip[:2]])
                for segment in range(3):
                    t = segment / 3
                    weight = 1 - t * t * (3 - 2 * t)
                    pair = slice(segment * 2, segment * 2 + 2)
                    strip[pair, 2] += root_offsets * weight
                    if segment:
                        for point in strip[pair]:
                            point[2] = max(point[2], surface_depth(point[0], point[1]) + .00001)
                points[selection] = strip
                local_faces = indices.reshape(-1, 3)
                local_faces = local_faces[(local_faces[:, 0] // 18) == strand] - strand * 18
                accumulated = np.zeros((18, 3))
                for face in local_faces:
                    cross = np.cross(strip[face[1]] - strip[face[0]], strip[face[2]] - strip[face[0]])
                    accumulated[face] += cross
                accumulated /= np.linalg.norm(accumulated, axis=1)[:, None]
                original_normals = normals[selection].astype(float)
                accumulated[np.sum(accumulated * original_normals, axis=1) < 0] *= -1
                normals[strand * 18:strand * 18 + 8] = accumulated[:8]
                shift = strip[:2].mean(axis=0) - root
            records.append({'group': 'corner' if is_corner else 'upper', 'strand': int(strand),
                            'root_before': root.tolist(), 'translation': shift.tolist(),
                            'outward_rotation_degrees': float(np.rad2deg(angle)),
                            'eyelid_crest_depth': crest_depth,
                            'root_after': (root + shift).tolist()})
        if not is_corner:
            assert np.array_equal(points[56 * 18:], before[56 * 18:])
        assert np.isfinite(points).all()
        binary[offset:offset + points.nbytes] = points.tobytes()
        if version in ('v7', 'v8', 'v10'):
            binary[normal_offset:normal_offset + normals.nbytes] = normals.tobytes()
        accessor = doc['accessors'][primitive['attributes']['POSITION']]
        accessor.update(min=points.min(axis=0).tolist(), max=points.max(axis=0).tolist())
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    result = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    result += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    result += struct.pack('<II', len(binary), 0x004e4942) + binary
    out.mkdir(exist_ok=True)
    (out / f'base-eyelashes-{version}.glb').write_bytes(result)
    report = {'source_sha256': hashlib.sha256(source).hexdigest(), 'output_sha256': hashlib.sha256(result).hexdigest(),
              'triangles': 22175,
              'moved_upper_strands': sum(s['group'] == 'upper' and any(s['translation']) for s in records),
              'moved_corner_strands': sum(s['group'] == 'corner' and any(s['translation']) for s in records),
              'lower_lashes_unchanged': True, 'rigid_strand_transforms': version != 'v10',
              'surface_clearance': -.000012 if version == 'v10' else None if version == 'v9' else .000025,
              'front_depth_preserved': version == 'v9', 'strands': records}
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'strands'}))


if __name__ == '__main__':
    main()
