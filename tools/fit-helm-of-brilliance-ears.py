import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'female': {'body': 'assets/modular_human_female_01/rig_v1/female-base.glb',
               'sha256': '3eb7c0a5f3c6b30aec0fbae0b70c8fd925e4cb91772647420007eee795a1e0a5',
               'mesh_index': 0, 'anchor_x': .066, 'height_offset': 0},
    'male': {'body': 'assets/modular_human_male_01/fitted/base.glb',
             'sha256': '0e629865af6c3feac3a4444e0cb2d5f2d3861bf2350d643cbff0f9858b83535a',
             'mesh_index': 3, 'anchor_x': .068, 'height_offset': .100, 'upper_start': 1.615},
}
spec = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


def deform(points, profile):
    result = points.copy()
    distance = np.maximum(abs(points[:, 0]) - profile['anchor_x'], 0)
    inward = .92 * (distance - .003 * (1 - np.exp(-distance / .003)))
    height = points[:, 1] - profile['height_offset']
    upper = io.smoothstep((height - profile.get('upper_start', 1.655)) / .032)
    crown = 1 - io.smoothstep((height - 1.700) / .016)
    rear = io.smoothstep((-.005 - points[:, 2]) / .020)
    nape = io.smoothstep((points[:, 2] + .060) / .016)
    result[:, 0] -= np.sign(points[:, 0]) * inward * upper * crown * rear * nape
    return result


def main(sex):
    profile = PROFILES[sex]
    body = ROOT / profile['body']
    out = ROOT / 'assets/items/helm_of_brilliance/tripo_v2/fitted_v3' / sex
    digest = hashlib.sha256(body.read_bytes()).hexdigest()
    assert digest == profile['sha256']
    doc, binary = read_glb(body)
    primitive = doc['meshes'][profile['mesh_index']]['primitives'][0]
    points = accessor(doc, binary, primitive['attributes']['POSITION']).astype(float)
    normals = accessor(doc, binary, primitive['attributes']['NORMAL'])
    fitted = deform(points, profile)
    selected = np.flatnonzero(np.linalg.norm(fitted - points, axis=1) > 1e-8)
    assert 0 < len(selected) < 1500
    names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
    joints = accessor(doc, binary, primitive['attributes']['JOINTS_0'])[selected]
    weights = accessor(doc, binary, primitive['attributes']['WEIGHTS_0'])[selected]
    head_weights = (weights * (joints == names.index('Head'))).sum(1)
    assert np.all(head_weights > .9)
    transformed = io.transformed_normals(points, normals, lambda values: deform(values, profile))
    adjustments = [{'vertex': int(i), 'position': fitted[i].tolist(),
                    'normal': transformed[i].tolist()} for i in selected]
    mask = {'mesh_index': profile['mesh_index'], 'primitive_index': 0,
            'primitive_triangles': doc['accessors'][primitive['indices']]['count'] // 3,
            'hide_triangle_indices': [], 'vertex_adjustments': adjustments}
    (out / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
    report = {'date': '2026-10-17', 'body_sha256': digest,
              'helmet_sha256': hashlib.sha256((out / 'helmet_brilliance.glb').read_bytes()).hexdigest(),
              'method': 'Restore every ear triangle; smoothly press the upper rear ears toward the head while equipped. Restore the original body geometry on removal.',
              'compression': {'anchor_x_m': profile['anchor_x'], 'height_offset_m': profile['height_offset'],
                              'upper_start_m': profile.get('upper_start', 1.655) + profile['height_offset'],
                              'transition_m': .003, 'strength': .92,
                              'minimum_x_derivative': .08},
              'maximum_vertex_displacement_m': float(np.linalg.norm(fitted - points, axis=1).max()),
              'adjusted_vertices': len(selected), 'hidden_triangles': 0,
              'minimum_original_head_weight': float(head_weights.min()),
              'left_vertices': int((points[selected, 0] > 0).sum()),
              'right_vertices': int((points[selected, 0] < 0).sum()),
              'preserved': ['all body triangles', 'helmet geometry and proportions', 'base GLB', 'UVs', 'skin weights', 'animations'],
              'rejected': 'Triangle hiding exposed a hole beside the upper ear; discarded at user review.',
              'source': f'Local fitting derived from the canonical {sex} body; inherits its source and license. No paid generation.'}
    (out / 'ear-fitting.json').write_text(json.dumps(report, indent=2) + '\n')
    previous = out / 'ear-occlusion.json'
    if previous.exists():
        previous.unlink()
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sex', nargs='?', choices=PROFILES, default='female')
    main(parser.parse_args().sex)
