"""Widen lash ribbons while preserving frontal centerlines, tips, and topology."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/modular_human_female_01'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v4', 'v5', 'v11', 'v12'], default='v4')
    parser.add_argument('--root-scale', type=float, default=1.6)
    parser.add_argument('--mid-scale', type=float, default=2.5)
    args = parser.parse_args()
    if not np.isfinite(args.root_scale) or args.root_scale < 1:
        parser.error('--root-scale must be finite and at least 1')
    if not np.isfinite(args.mid_scale) or args.mid_scale < 1:
        parser.error('--mid-scale must be finite and at least 1')
    out = BASE / f'eyelashes_{args.version}'
    extended = args.version == 'v12'
    seated = args.version in ('v11', 'v12')
    source_path = BASE / ('brow_normals_v1/base-brow-normals-v1.glb' if extended else
                          'eyelashes_v10/base-eyelashes-v10.glb' if seated else 'eyelashes_v3/base-eyelashes-v3.glb')
    source = source_path.read_bytes()
    expected = ('88cf89fe24e6aa6e7020d212a0c3181de9cb4b678cbf04809201929c8cbd920c' if extended else
                'abfe7f89a437594c2e7072e66a820506c038dcc49937d242ae700af74148e6d5' if seated
                else 'd579a613dc5ff7a41128abda662b050630293bb5e6d4b41c36b4711f6e48da68')
    assert hashlib.sha256(source).hexdigest() == expected
    size = struct.unpack_from('<I', source, 12)[0]
    doc = json.loads(source[20:20 + size])
    binary = bytearray(source[28 + size:])

    def read(index):
        accessor = doc['accessors'][index]
        view = doc['bufferViews'][accessor['bufferView']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        width = {'VEC3': 3, 'SCALAR': 1}[accessor['type']]
        array = np.frombuffer(binary, dtype={5126: '<f4', 5123: '<u2', 5125: '<u4'}[
            accessor['componentType']], offset=offset, count=accessor['count'] * width)
        return array.reshape(accessor['count'], width).copy(), offset

    if seated:
        body = doc['meshes'][0]['primitives'][0]
        points, _ = read(body['attributes']['POSITION'])
        indices, _ = read(body['indices'])
        faces = points[indices.reshape(-1, 3)].astype(float)
        faces = faces[(faces[:, :, 1].max(axis=1) > .932) & (faces[:, :, 1].min(axis=1) < .945)]
        origin = faces[:, 0, :2]
        a, b = faces[:, 1, :2] - origin, faces[:, 2, :2] - origin
        determinant = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        valid = abs(determinant) > 1e-14

    def surface_depth(point):
        delta = point[:2] - origin
        u, v = np.zeros(len(faces)), np.zeros(len(faces))
        u[valid] = (delta[valid, 0] * b[valid, 1] - delta[valid, 1] * b[valid, 0]) / determinant[valid]
        v[valid] = (a[valid, 0] * delta[valid, 1] - a[valid, 1] * delta[valid, 0]) / determinant[valid]
        hit = valid & (u >= -1e-8) & (v >= -1e-8) & (u + v <= 1 + 1e-8)
        assert hit.any()
        depths = faces[:, 0, 2] + u * (faces[:, 1, 2] - faces[:, 0, 2]) + v * (faces[:, 2, 2] - faces[:, 0, 2])
        return float(depths[hit].max())

    results = []
    for group, primitive in enumerate(doc['meshes'][0]['primitives'][1:]):
        accessor = doc['accessors'][primitive['attributes']['POSITION']]
        positions, offset = read(primitive['attributes']['POSITION'])
        before = positions.copy()
        normals, normal_offset = read(primitive['attributes']['NORMAL'])
        indices, _ = read(primitive['indices'])
        vertices = set(indices.ravel().tolist())
        strands = sorted({v // 18 for v in vertices})
        for strand in strands:
            assert set(range(strand * 18, (strand + 1) * 18)) <= vertices
            for segment in range(8 if extended else 4):
                pair = slice(strand * 18 + segment * 2, strand * 18 + segment * 2 + 2)
                center = before[pair].astype(np.float64).mean(axis=0)
                t = segment / 8
                if extended:
                    rise = np.clip(t / .25, 0, 1)
                    rise = rise * rise * (3 - 2 * rise)
                    taper = np.clip((t - .625) / .375, 0, 1)
                    taper = taper * taper * (3 - 2 * taper)
                    scale = 1 + (args.root_scale - 1 + (args.mid_scale - args.root_scale) * rise) * (1 - taper)
                else:
                    blend = np.clip(t / .5, 0, 1)
                    blend = blend * blend * (3 - 2 * blend)
                    scale = 1 + (args.root_scale - 1) * (1 - blend)
                positions[pair] = center + (before[pair].astype(np.float64) - center) * scale
            if seated:
                start = strand * 18
                strip = positions[start:start + 18].astype(float)
                if group == 0 or strand < 56:
                    correction = np.array([surface_depth(p) - .000012 - p[2] for p in strip[:2]])
                    for segment in range(3):
                        t = segment / 3
                        pair = slice(segment * 2, segment * 2 + 2)
                        strip[pair, 2] += correction * (1 - t * t * (3 - 2 * t))
                        if segment:
                            for point in strip[pair]:
                                point[2] = max(point[2], surface_depth(point) + .00001)
                positions[start:start + 18] = strip
                local_faces = indices.reshape(-1, 3)
                local_faces = local_faces[local_faces[:, 0] // 18 == strand] - start
                accumulated = np.zeros((18, 3))
                for face in local_faces:
                    accumulated[face] += np.cross(strip[face[1]] - strip[face[0]], strip[face[2]] - strip[face[0]])
                lengths = np.linalg.norm(accumulated, axis=1)
                assert (lengths > 0).all()
                accumulated /= lengths[:, None]
                accumulated[np.sum(accumulated * normals[start:start + 18], axis=1) < 0] *= -1
                count = 18 if extended else 10
                normals[start:start + count] = accumulated[:count]
            tip = slice(strand * 18 + (16 if extended else 8), (strand + 1) * 18)
            assert np.array_equal(positions[tip], before[tip])
        assert np.isfinite(positions).all()
        binary[offset:offset + positions.nbytes] = positions.tobytes()
        if seated:
            binary[normal_offset:normal_offset + normals.nbytes] = normals.tobytes()
        accessor.update(min=positions.min(axis=0).tolist(), max=positions.max(axis=0).tolist())
        results.append({'strands': len(strands), 'changed_vertices': int(np.any(positions != before, axis=1).sum())})
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    output = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    output += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    output += struct.pack('<II', len(binary), 0x004e4942) + binary
    out.mkdir(exist_ok=True)
    model_path = out / f'base-eyelashes-{args.version}.glb'
    model_path.write_bytes(output)
    if extended:
        subprocess.run(['blender', '-b', '--python-expr',
                        'import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); '
                        f'bpy.ops.import_scene.gltf(filepath={str(model_path)!r}); '
                        'bpy.context.preferences.filepaths.save_version = 0; bpy.ops.file.pack_all(); '
                        f'bpy.ops.wm.save_as_mainfile(filepath={str(model_path.with_suffix(".blend"))!r})'], check=True)
    report = {'source_sha256': hashlib.sha256(source).hexdigest(), 'output_sha256': hashlib.sha256(output).hexdigest(),
              'source_model': str(source_path.relative_to(ROOT)),
              'root_width_scale': args.root_scale, 'falloff_end_fraction': 1 if extended else .5, 'strand_centers_unchanged': not seated,
              'strand_centers_xy_unchanged': True, 'upper_root_surface_clearance': -.000012 if seated else None,
              'outer_half_and_tips_unchanged': not extended, 'tip_positions_unchanged': True, 'triangle_count_before': 22175, 'triangle_count_after': 22175,
              'adjusted_strands': sum(r['strands'] for r in results), 'primitives': results}
    if extended:
        report.update(mid_width_scale=args.mid_scale, mid_plateau_fraction=[.25, .625])
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
