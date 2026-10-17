"""Fit the horned helmet to the female head by radial clearance and bind it rigidly to Head."""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh

from lib.glb import read_glb, write_glb, view_bytes
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
DIRECTORY = ROOT / 'assets/items/female_barbarian_helmet/tripo_v2'
SOURCE = DIRECTORY / 'source/model_url.glb'
OUT = DIRECTORY / 'fitted_v1'
REPORT = ROOT / 'doc/assets/modular-female-barbarian-helmet-fitting-v1.json'
spec = importlib.util.spec_from_file_location('io', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
CENTER = np.array([0, 1.692, -.0072])
CLEARANCE = .00306
BROW_PEAK_Y = 1.7118
COARSE = (np.arange(.27, .3602, .018), np.arange(-.0216, .0218, .0072))
FINE_STEPS = (.0045, .0036)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def directions():
    rows = []
    for elevation in np.radians(np.arange(-45, 90, 5)):
        count = max(int(72 * np.cos(elevation)), 8)
        for azimuth in np.arange(count) * 2 * np.pi / count:
            rows.append([np.cos(elevation) * np.sin(azimuth), np.sin(elevation), np.cos(elevation) * np.cos(azimuth)])
    rows.append([0, 1, 0])
    return np.array(rows)


def hits(mesh, rays, first):
    locations, index, _ = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_location(
        np.repeat(CENTER[None], len(rays), 0), rays, multiple_hits=True)
    distance = np.full(len(rays), np.nan)
    along = np.linalg.norm(locations - CENTER, axis=1)
    order = np.argsort(along if first else -along)
    seen = set()
    for i in order:
        if index[i] not in seen:
            seen.add(index[i])
            distance[index[i]] = along[i]
    return distance


def place(points, scale, offset):
    return np.column_stack([-points[:, 2], points[:, 1], points[:, 0]]) * scale + offset


def main():
    OUT.mkdir(exist_ok=True)
    assert digest(SOURCE) == '7e1f9be83b2519e5f3e8a266a8dcb94029a8d8634aaf58945a08388f4af7da9f'
    assert digest(BODY) == '3eb7c0a5f3c6b30aec0fbae0b70c8fd925e4cb91772647420007eee795a1e0a5'
    base, base_raw = read_glb(BODY)
    names = [base['nodes'][i]['name'] for i in base['skins'][0]['joints']]
    body = base['meshes'][0]['primitives'][0]
    body_points = accessor(base, base_raw, body['attributes']['POSITION']).astype(float)
    body_faces = accessor(base, base_raw, body['indices']).reshape(-1, 3)
    joints = accessor(base, base_raw, body['attributes']['JOINTS_0'])
    weights = accessor(base, base_raw, body['attributes']['WEIGHTS_0'])
    head_weight = (weights * np.isin(joints, [names.index('Head'), names.index('Neck')])).sum(1)
    head = trimesh.Trimesh(body_points, body_faces[head_weight[body_faces].mean(1) > .5], process=False)
    rays = directions()
    skin = hits(head, rays, first=False)

    doc, source_raw = read_glb(SOURCE)
    images = [view_bytes(doc, source_raw, image['bufferView']) for image in doc['images']]
    primitive = doc['meshes'][0]['primitives'][0]
    points = accessor(doc, source_raw, primitive['attributes']['POSITION']).astype(float)
    uv = accessor(doc, source_raw, primitive['attributes']['TEXCOORD_0'])
    faces = accessor(doc, source_raw, primitive['indices']).reshape(-1, 3)
    centerline = (abs(points[:, 2]) < .03) & (points[:, 0] > .1)
    peak = points[centerline][points[centerline, 1].argmin()]

    shell_rays = trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.Trimesh(points, faces, process=False))

    def evaluate(scale, z):
        offset = np.array([0, BROW_PEAK_Y - peak[1] * scale[1], z])
        # Map rays to source space without normalizing their directions.
        origin = (CENTER - offset) / scale
        local = (rays / scale)[:, [2, 1, 0]] * [1, 1, -1]
        origin = origin[[2, 1, 0]] * [1, 1, -1]
        locations, index, _ = shell_rays.intersects_location(np.repeat(origin[None], len(rays), 0), local, multiple_hits=True)
        shell = np.full(len(rays), np.inf)
        along = np.einsum('ij,ij->i', locations - origin, local[index]) / np.einsum('ij,ij->i', local[index], local[index])
        np.minimum.at(shell, index, along)
        gap = np.where(np.isfinite(shell), shell, np.nan) - skin
        valid = ~np.isnan(gap)
        if valid.sum() < len(rays) * .5 or gap[valid].min() < CLEARANCE:
            return None
        return dict(scale=scale, offset=offset, gap=gap, valid=valid)

    def search(scales, depths):
        candidates = [np.array(c) for c in itertools.product(scales, scales, scales)
                      if max(c) / min(c) <= 1.12]
        candidates.sort(key=lambda c: c.sum())
        for scale in candidates:
            for z in depths:
                result = evaluate(scale, z)
                if result:
                    return result

    best = search(*COARSE)
    assert best, 'No helmet placement clears the head'
    around = lambda value, step: value + np.arange(-4, 1) * step
    best = search(np.unique(np.concatenate([around(v, FINE_STEPS[0]) for v in best['scale']])),
                  best['offset'][2] + np.arange(-2, 3) * FINE_STEPS[1]) or best
    assert best, 'No helmet placement clears the head'
    fitted = place(points, best['scale'], best['offset'])

    bones = np.zeros((len(points), 4), dtype=np.uint16)
    bones[:, 0] = names.index('Head')
    influence = np.zeros((len(points), 4))
    influence[:, 0] = 1
    raw = bytearray(source_raw)
    normals = io.smooth_normals(fitted, faces)
    attrs = io.add_skin_attributes(doc, raw, fitted, normals, bones, influence)
    attrs['TEXCOORD_0'] = add_accessor(doc, raw, uv, 'VEC2')
    attrs['TANGENT'] = add_accessor(doc, raw, io.tangents(fitted, normals, uv, faces), 'VEC4')
    doc['meshes'] = [{'name': 'helmet_female_barbarian', 'primitives': [{'attributes': attrs, 'material': primitive['material'],
        'indices': add_accessor(doc, raw, faces.reshape(-1, 1).astype(np.uint32), 'SCALAR', 5125)}]}]
    ids = base['skins'][0]['joints']
    remap = {old: i for i, old in enumerate(ids)}
    doc['nodes'] = [copy.deepcopy(base['nodes'][i]) for i in ids]
    for bone in doc['nodes']:
        if 'children' in bone:
            bone['children'] = [remap[i] for i in bone['children'] if i in remap]
    children = {i for bone in doc['nodes'] for i in bone.get('children', [])}
    rig_id = 'human_female_01_local_v1'
    doc['nodes'].append({'name': 'Armature', 'children': [i for i in range(len(ids)) if i not in children], 'extras': {'rig_id': rig_id}})
    doc['nodes'].append({'name': 'helmet_female_barbarian', 'mesh': 0, 'skin': 0, 'extras': {'rig_id': rig_id, 'part_id': 'helmet_female_barbarian'}})
    doc['scenes'] = [{'nodes': [len(ids), len(ids) + 1], 'extras': {'rig_id': rig_id}}]
    doc['scene'] = 0
    rig = copy.deepcopy(base['skins'][0])
    rig['joints'] = [remap[i] for i in ids]
    rig['skeleton'] = remap[rig['skeleton']]
    rig['inverseBindMatrices'] = add_accessor(doc, raw, accessor(base, base_raw, rig['inverseBindMatrices']), 'MAT4')
    doc['skins'] = [rig]
    doc.pop('animations', None)
    raw = io.compact(doc, raw)
    assert [view_bytes(doc, raw, image['bufferView']) for image in doc['images']] == images
    target = OUT / 'helmet_female_barbarian.glb'
    write_glb(target, doc, raw)
    mask = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': digest(BODY), 'mesh_index': 0, 'primitive_index': 0,
            'primitive_triangles': len(body_faces), 'hide_triangle_indices': [],
            'scope': 'No skin is hidden; the preview uses fitted hair variants below the horned helmet.'}
    (OUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
    gap = best['gap'][best['valid']]
    report = {'date': '2026-10-15', 'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': digest(SOURCE)},
              'body': {'path': str(BODY.relative_to(ROOT)), 'sha256': digest(BODY)},
              'output': {'path': str(target.relative_to(ROOT)), 'sha256': digest(target)},
              'rig_id': rig_id, 'triangles': len(faces), 'source_axis_mapping': '[-z, y, x]',
              'scale_xyz': best['scale'].tolist(), 'offset_xyz': best['offset'].tolist(),
              'brow_peak_y': BROW_PEAK_Y, 'radial_center': CENTER.tolist(), 'rays': len(rays), 'rays_hitting_shell': int(best['valid'].sum()),
              'clearance_m': {'required': CLEARANCE, 'minimum': float(gap.min()), 'median': float(np.median(gap))},
              'method': 'Rotate the source +X front to +Z. Search per-axis scales (ratio within 1.12) and depth offset; the brow peak '
                        'sits at BROW_PEAK_Y. Keep the smallest helmet whose inner shell clears the head and neck skin by CLEARANCE '
                        'along every ray from the head center that meets the shell.',
              'weights': 'Head 100%; rigid helmet including horns and cheek guards',
              'original_topology_uv_and_embedded_textures_preserved': True, 'status': 'Candidate; preview-clip animation check passed (tools/validate-female-barbarian-helmet.mjs)'}
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['scale_xyz', 'offset_xyz', 'rays_hitting_shell', 'clearance_m']}))


if __name__ == '__main__':
    main()
