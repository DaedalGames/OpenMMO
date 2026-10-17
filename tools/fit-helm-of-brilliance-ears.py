import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUT = ROOT / 'assets/items/helm_of_brilliance/tripo_v2/fitted_v3/female'
spec = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


def deform(points):
    result = points.copy()
    distance = np.maximum(abs(points[:, 0]) - .066, 0)
    inward = .92 * (distance - .003 * (1 - np.exp(-distance / .003)))
    upper = io.smoothstep((points[:, 1] - 1.655) / .032)
    crown = 1 - io.smoothstep((points[:, 1] - 1.700) / .016)
    rear = io.smoothstep((-.005 - points[:, 2]) / .020)
    nape = io.smoothstep((points[:, 2] + .060) / .016)
    result[:, 0] -= np.sign(points[:, 0]) * inward * upper * crown * rear * nape
    return result


def main():
    digest = hashlib.sha256(BODY.read_bytes()).hexdigest()
    assert digest == '3eb7c0a5f3c6b30aec0fbae0b70c8fd925e4cb91772647420007eee795a1e0a5'
    doc, binary = read_glb(BODY)
    primitive = doc['meshes'][0]['primitives'][0]
    points = accessor(doc, binary, primitive['attributes']['POSITION']).astype(float)
    normals = accessor(doc, binary, primitive['attributes']['NORMAL'])
    fitted = deform(points)
    selected = np.flatnonzero(np.linalg.norm(fitted - points, axis=1) > 1e-8)
    assert 0 < len(selected) < 1500
    names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
    joints = accessor(doc, binary, primitive['attributes']['JOINTS_0'])[selected]
    weights = accessor(doc, binary, primitive['attributes']['WEIGHTS_0'])[selected]
    assert np.allclose((weights * (joints == names.index('Head'))).sum(1), 1)
    transformed = io.transformed_normals(points, normals, deform)
    adjustments = [{'vertex': int(i), 'position': fitted[i].tolist(),
                    'normal': transformed[i].tolist()} for i in selected]
    mask = {'mesh_index': 0, 'primitive_index': 0,
            'primitive_triangles': doc['accessors'][primitive['indices']]['count'] // 3,
            'hide_triangle_indices': [], 'vertex_adjustments': adjustments}
    (OUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
    report = {'date': '2026-10-17', 'body_sha256': digest,
              'helmet_sha256': hashlib.sha256((OUT / 'helmet_brilliance.glb').read_bytes()).hexdigest(),
              'method': 'Restore every ear triangle; smoothly press the upper rear ears toward the head while equipped. Restore the original body geometry on removal.',
              'compression': {'anchor_x_m': .066, 'transition_m': .003, 'strength': .92,
                              'minimum_x_derivative': .08},
              'maximum_vertex_displacement_m': float(np.linalg.norm(fitted - points, axis=1).max()),
              'adjusted_vertices': len(selected), 'hidden_triangles': 0,
              'left_vertices': int((points[selected, 0] > 0).sum()),
              'right_vertices': int((points[selected, 0] < 0).sum()),
              'preserved': ['all body triangles', 'helmet geometry and proportions', 'base GLB', 'UVs', 'skin weights', 'animations'],
              'rejected': 'Triangle hiding exposed a hole beside the upper ear; discarded at user review.',
              'source': 'Local fitting derived from the canonical female body; inherits its source and license. No paid generation.'}
    (OUT / 'ear-fitting.json').write_text(json.dumps(report, indent=2) + '\n')
    previous = OUT / 'ear-occlusion.json'
    if previous.exists():
        previous.unlink()
    print(json.dumps(report))


if __name__ == '__main__':
    main()
