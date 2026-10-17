import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import trimesh

from lib.glb import read_glb, view_bytes, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/helm_of_brilliance/tripo_v2'
SOURCE = DIRECTORY / 'source/model_url.glb'
SPEC = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(io)
PROFILES = {
    'male': {
        'body': 'assets/modular_human_male_01/fitted/base.glb',
        'body_sha256': '0e629865af6c3feac3a4444e0cb2d5f2d3861bf2350d643cbff0f9858b83535a',
        'rig_id': 'human_male_01_mixamo_candidate_v2',
        'center': [0, 1.790, -.005], 'brow_y': 1.800,
    },
    'female': {
        'body': 'assets/modular_human_female_01/rig_v1/female-base.glb',
        'body_sha256': '3eb7c0a5f3c6b30aec0fbae0b70c8fd925e4cb91772647420007eee795a1e0a5',
        'rig_id': 'human_female_01_local_v1',
        'center': [0, 1.692, -.0072], 'brow_y': 1.7118,
    },
}
CLEARANCE = .003


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rays(step):
    result = []
    for elevation in np.radians(np.arange(-60, 90, step)):
        count = max(int(360 / step * np.cos(elevation)), 8)
        for azimuth in np.arange(count) * 2 * np.pi / count:
            result.append([np.cos(elevation) * np.sin(azimuth), np.sin(elevation),
                           np.cos(elevation) * np.cos(azimuth)])
    return np.array(result + [[0, 1, 0]])


def distances(intersector, origin, directions, nearest):
    origins = np.broadcast_to(origin, directions.shape)
    locations, indices, _ = intersector.intersects_location(origins, directions, multiple_hits=True)
    values = np.full(len(directions), np.inf if nearest else -np.inf)
    along = np.einsum('ij,ij->i', locations - origins[indices], directions[indices])
    along /= np.einsum('ij,ij->i', directions[indices], directions[indices])
    positive = along > 1e-7
    operation = np.minimum if nearest else np.maximum
    operation.at(values, indices[positive], along[positive])
    return values


def body_head(base, binary, names):
    points, faces = [], []
    for mesh in base['meshes']:
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            vertices = accessor(base, binary, attrs['POSITION']).astype(float)
            joints = accessor(base, binary, attrs['JOINTS_0'])
            weights = accessor(base, binary, attrs['WEIGHTS_0'])
            influence = (weights * np.isin(joints, [names.index('Head'), names.index('Neck')])).sum(1)
            triangles = accessor(base, binary, primitive['indices']).reshape(-1, 3)
            faces.extend(triangles[influence[triangles].mean(1) > .5] + len(points))
            points.extend(vertices)
    return trimesh.Trimesh(np.array(points), np.array(faces), process=False)


def fit(profile, source_points, source_faces, head):
    center = np.array(profile['center'])
    brow = source_points[(abs(source_points[:, 0]) < .025) & (source_points[:, 2] > .20), 1].min()
    intersector = trimesh.ray.ray_triangle.RayMeshIntersector(
        trimesh.Trimesh(source_points, source_faces, process=False))
    head_rays = trimesh.ray.ray_triangle.RayMeshIntersector(head)
    coarse = rays(12)
    skin = distances(head_rays, center, coarse, False)

    def evaluate(scale, depth, directions, skin_distances):
        offset = np.array([0, profile['brow_y'] - brow * scale[1], depth])
        shell = distances(intersector, (center - offset) / scale, directions / scale, True)
        valid = np.isfinite(shell) & np.isfinite(skin_distances)
        gap = shell[valid] - skin_distances[valid]
        if valid.sum() < len(directions) * .45 or not len(gap):
            return None
        return {'scale': scale, 'offset': offset, 'gap': gap, 'hits': int(valid.sum()),
                'minimum': float(gap.min())}

    candidates = []
    for shape in [[1, 1, 1], [1.06, 1, 1], [1, 1, 1.06], [1.06, 1, 1.06]]:
        for depth in np.arange(-.016, .0161, .008):
            low, high = .20, .48
            for _ in range(8):
                size = (low + high) / 2
                result = evaluate(np.array(shape) * size, depth, coarse, skin)
                if result and result['minimum'] >= CLEARANCE + .001:
                    high = size
                else:
                    low = size
            result = evaluate(np.array(shape) * high, depth, coarse, skin)
            if result and result['minimum'] >= CLEARANCE + .001:
                candidates.append(result)
    assert candidates, 'No placement clears the reference head'
    fine = rays(5)
    fine_skin = distances(head_rays, center, fine, False)
    candidates.sort(key=lambda item: np.prod(item['scale']))
    best = None
    for candidate in candidates:
        for increase in np.arange(0, .0251, .002):
            scale = candidate['scale'] + increase
            result = evaluate(scale, candidate['offset'][2], fine, fine_skin)
            if result and result['minimum'] >= CLEARANCE:
                if best is None or np.prod(scale) < np.prod(best['scale']):
                    best = result
                break
        if best is not None:
            break
    assert best, 'Dense clearance check failed'
    best['ray_count'] = len(fine)
    return best


def main(sex, uniform_scale=None, offset=None, directory=None):
    profile = PROFILES[sex]
    body_path = ROOT / profile['body']
    assert digest(body_path) == profile['body_sha256'], 'Reference body changed; revalidate the fitting profile'
    base, base_raw = read_glb(body_path)
    ids = base['skins'][0]['joints']
    names = [base['nodes'][index]['name'] for index in ids]
    head = body_head(base, base_raw, names)
    doc, source_raw = read_glb(SOURCE)
    assert digest(SOURCE) == 'd8e87a665d9127145cb43e288c2b8d41a2a047f1056dd3fcffb347ea3057f039'
    primitive = doc['meshes'][0]['primitives'][0]
    attributes = primitive['attributes']
    original = accessor(doc, source_raw, attributes['POSITION']).astype(float)
    source_matrix = np.array(doc['nodes'][0]['matrix']).reshape(4, 4).T
    rotation = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]])
    source_transform = rotation @ source_matrix[:3, :3]
    points = original @ source_transform.T + rotation @ source_matrix[:3, 3]
    faces = accessor(doc, source_raw, primitive['indices']).reshape(-1, 3)
    if uniform_scale is None:
        result = fit(profile, points, faces, head)
    else:
        assert uniform_scale > 0 and offset is not None
        result = {'scale': np.full(3, uniform_scale), 'offset': np.array(offset)}
    fitted = points * result['scale'] + result['offset']
    transform = np.diag(result['scale']) @ source_transform
    normal = accessor(doc, source_raw, attributes['NORMAL']).astype(float) @ np.linalg.inv(transform)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    joints = np.zeros((len(points), 4), dtype=np.uint16)
    joints[:, 0] = names.index('Head')
    weights = np.zeros((len(points), 4))
    weights[:, 0] = 1
    images = [view_bytes(doc, source_raw, image['bufferView']) for image in doc['images']]
    uv = accessor(doc, source_raw, attributes['TEXCOORD_0'])
    raw = bytearray(source_raw)
    attrs = io.add_skin_attributes(doc, raw, fitted, normal, joints, weights)
    attrs['TEXCOORD_0'] = add_accessor(doc, raw, uv, 'VEC2')
    if 'TANGENT' in attributes:
        tangent = accessor(doc, source_raw, attributes['TANGENT']).astype(float)
        tangent[:, :3] = tangent[:, :3] @ transform.T
        tangent[:, :3] -= normal * (normal * tangent[:, :3]).sum(1, keepdims=True)
        tangent[:, :3] /= np.linalg.norm(tangent[:, :3], axis=1, keepdims=True)
    else:
        tangent = io.tangents(fitted, normal, uv, faces)
    attrs['TANGENT'] = add_accessor(doc, raw, tangent, 'VEC4')
    part_id = 'helmet_brilliance'
    doc['meshes'] = [{'name': part_id, 'primitives': [{'attributes': attrs,
        'indices': add_accessor(doc, raw, faces.reshape(-1, 1), 'SCALAR', 5125),
        'material': primitive['material']}]}]
    original_nodes = [i for i, node in enumerate(base['nodes']) if 'mesh' not in node]
    remap = {old: new for new, old in enumerate(original_nodes)}
    doc['nodes'] = [copy.deepcopy(base['nodes'][index]) for index in original_nodes]
    for node in doc['nodes']:
        if 'children' in node:
            node['children'] = [remap[index] for index in node['children'] if index in remap]
    doc['scenes'] = copy.deepcopy(base['scenes'])
    for scene in doc['scenes']:
        scene['nodes'] = [remap[index] for index in scene['nodes'] if index in remap]
    doc['scenes'][base.get('scene', 0)]['nodes'].append(len(doc['nodes']))
    doc['scene'] = base.get('scene', 0)
    doc['nodes'].append({'name': part_id, 'mesh': 0, 'skin': 0,
                         'extras': {'rig_id': profile['rig_id'], 'part_id': part_id}})
    skin = copy.deepcopy(base['skins'][0])
    skin['joints'] = [remap[index] for index in ids]
    if 'skeleton' in skin:
        skin['skeleton'] = remap[skin['skeleton']]
    skin['inverseBindMatrices'] = add_accessor(doc, raw,
        accessor(base, base_raw, skin['inverseBindMatrices']), 'MAT4')
    doc['skins'] = [skin]
    doc.pop('animations', None)
    raw = io.compact(doc, raw)
    assert images == [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    assert np.isfinite(fitted).all() and np.isfinite(normal).all() and np.isfinite(tangent).all()
    out = (ROOT / directory).resolve() if directory else DIRECTORY / 'fitted_v1' / sex
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'helmet_brilliance.glb'
    write_glb(target, doc, raw)
    report = {
        'date': '2026-10-17', 'sex': sex, 'rig_id': profile['rig_id'], 'bones': len(ids),
        'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': digest(SOURCE)},
        'body': {'path': profile['body'], 'sha256': digest(body_path)},
        'output': {'path': str(target.relative_to(ROOT)), 'sha256': digest(target)},
        'triangles': len(faces), 'scale_xyz': result['scale'].tolist(),
        'offset_xyz': result['offset'].tolist(), 'brow_y': profile['brow_y'],
        'radial_center': profile['center'],
        'method': 'Bake original node matrix; rotate +X front to +Z. Search scale and depth with a fixed brow landmark, then verify dense head/neck radial clearance.',
        'weights': 'Head 100%, including wings, crystal and neck guard',
        'preserved': ['triangle indices', 'UVs', 'embedded texture bytes', 'canonical bone hierarchy and inverse bind matrices'],
        'hair': 'Hide selected hair on equipment attachment and restore on removal; runtime wiring is a later stage.',
        'body_occlusion': 'No body triangles hidden or changed.',
        'status': 'Fitted candidate; awaits runtime animation and appearance review',
    }
    if uniform_scale is None:
        report.update({'rays': result['ray_count'], 'rays_hitting_skin_and_shell': result['hits'],
                       'clearance_m': {'required': CLEARANCE, 'minimum': result['minimum'],
                                       'median': float(np.median(result['gap']))}})
    else:
        stored = accessor(doc, raw, doc['meshes'][0]['primitives'][0]['attributes']['POSITION']).astype(float)
        error = np.max(np.linalg.norm(stored - fitted, axis=1))
        assert error < 2e-7
        report.update({
            'brow_y': float(points[(abs(points[:, 0]) < .025) & (points[:, 2] > .20), 1].min()
                            * uniform_scale + offset[1]),
            'method': 'Unmodified Tripo source, baked node matrix and rigid +X-to-+Z rotation; one uniform scale and translation only.',
            'uniform_scale': uniform_scale,
            'uniform_transform_maximum_error_m': float(error),
            'local_deformation': False,
            'bounds': [fitted.min(0).tolist(), fitted.max(0).tolist()],
            'operator_decision': '2026-10-17: restore the original proportions; reduce the whole helmet uniformly instead of deforming cheek guards or individual regions.',
        })
    (out / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sex', choices=PROFILES)
    parser.add_argument('--uniform-scale', type=float)
    parser.add_argument('--offset', type=float, nargs=3)
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    if args.uniform_scale is not None and args.offset is None:
        parser.error('--uniform-scale requires --offset')
    main(args.sex, args.uniform_scale, args.offset, args.directory)
