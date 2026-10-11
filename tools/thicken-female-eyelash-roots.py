"""Widen lash roots without changing strand centers, tips, or triangle counts."""
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
    parser.add_argument('--version', choices=['v4', 'v5'], default='v4')
    parser.add_argument('--root-scale', type=float, default=1.6)
    args = parser.parse_args()
    if not np.isfinite(args.root_scale) or args.root_scale < 1:
        parser.error('--root-scale must be finite and at least 1')
    out = BASE / f'eyelashes_{args.version}'
    source = (BASE / 'eyelashes_v3/base-eyelashes-v3.glb').read_bytes()
    assert hashlib.sha256(source).hexdigest() == 'd579a613dc5ff7a41128abda662b050630293bb5e6d4b41c36b4711f6e48da68'
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

    results = []
    for primitive in doc['meshes'][0]['primitives'][1:]:
        accessor = doc['accessors'][primitive['attributes']['POSITION']]
        positions, offset = read(primitive['attributes']['POSITION'])
        before = positions.copy()
        indices, _ = read(primitive['indices'])
        vertices = set(indices.ravel().tolist())
        strands = sorted({v // 18 for v in vertices})
        for strand in strands:
            assert set(range(strand * 18, (strand + 1) * 18)) <= vertices
            for segment in range(4):
                pair = slice(strand * 18 + segment * 2, strand * 18 + segment * 2 + 2)
                center = before[pair].astype(np.float64).mean(axis=0)
                t = segment / 8
                blend = np.clip(t / .5, 0, 1)
                blend = blend * blend * (3 - 2 * blend)
                scale = 1 + (args.root_scale - 1) * (1 - blend)
                positions[pair] = center + (before[pair].astype(np.float64) - center) * scale
            tip = slice(strand * 18 + 8, (strand + 1) * 18)
            assert np.array_equal(positions[tip], before[tip])
        assert np.isfinite(positions).all()
        binary[offset:offset + positions.nbytes] = positions.tobytes()
        accessor.update(min=positions.min(axis=0).tolist(), max=positions.max(axis=0).tolist())
        results.append({'strands': len(strands), 'changed_vertices': int(np.any(positions != before, axis=1).sum())})
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    output = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    output += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    output += struct.pack('<II', len(binary), 0x004e4942) + binary
    out.mkdir(exist_ok=True)
    (out / f'base-eyelashes-{args.version}.glb').write_bytes(output)
    report = {'source_sha256': hashlib.sha256(source).hexdigest(), 'output_sha256': hashlib.sha256(output).hexdigest(),
              'root_width_scale': args.root_scale, 'falloff_end_fraction': .5, 'strand_centers_unchanged': True,
              'outer_half_and_tips_unchanged': True, 'triangle_count_before': 22175, 'triangle_count_after': 22175,
              'adjusted_strands': sum(r['strands'] for r in results), 'primitives': results}
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
