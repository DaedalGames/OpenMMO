import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, view_bytes
from lib.glb_accessors import accessor

DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
OUT = DIRECTORY / 'fitted_v5'
doc, binary = read_glb(OUT / 'bottom_female_knight.glb')
source, source_binary = read_glb(DIRECTORY / 'fitted_v4/bottom_female_knight.glb')
report = json.loads((OUT / 'fitting.json').read_text())
data = np.load(OUT / 'shell-data.npz')
original = doc['meshes'][0]['primitives'][0]
previous = source['meshes'][0]['primitives'][0]
for name in ['TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0']:
    assert np.array_equal(accessor(doc, binary, original['attributes'][name]),
                          accessor(source, source_binary, previous['attributes'][name])), name
source_faces = accessor(source, source_binary, previous['indices']).reshape(-1, 3)
removed = data['removed_face_indices']
kept = np.ones(len(source_faces), dtype=bool)
kept[removed] = False
assert np.array_equal(accessor(doc, binary, original['indices']).reshape(-1, 3), source_faces[kept])
assert doc['materials'][0] == source['materials'][0]
assert doc['skins'] == source['skins']
assert doc['nodes'][1:] == source['nodes'][1:]
assert [view_bytes(doc, binary, image['bufferView']) for image in doc['images']] == [view_bytes(source, source_binary, image['bufferView']) for image in source['images']]
assert (OUT / 'body-occlusion.json').read_bytes() == (DIRECTORY / 'fitted_v4/body-occlusion.json').read_bytes()

plate = doc['meshes'][0]['primitives'][1]
points = accessor(doc, binary, plate['attributes']['POSITION']).astype(float)
normals = accessor(doc, binary, plate['attributes']['NORMAL']).astype(float)
faces = accessor(doc, binary, plate['indices']).reshape(-1, 3)
assert np.isfinite(points).all() and np.isfinite(normals).all()
assert np.max(abs(np.linalg.norm(normals, axis=1) - 1)) < 1e-6
center = np.array(report['shell']['center'])
radii = np.array(report['shell']['radii'])
tilt = report['shell']['depth_shear_per_height']
local = points - center
local[:, 2] -= tilt * local[:, 1]
gradient = local / radii ** 2
gradient[:, 1] -= tilt * gradient[:, 2]
gradient /= np.linalg.norm(gradient, axis=1, keepdims=True)
outer = (normals * gradient).sum(1) > .99999
used = np.zeros(len(points), dtype=bool)
used[np.unique(faces)] = True
outer &= used
outer_faces = faces[outer[faces].all(1)]
assert len(outer_faces) >= 500
assert np.max(np.linalg.norm(normals[outer] - gradient[outer], axis=1)) < .004
hem = outer & (abs(points[:, 1] - report['shell']['hem_height']) < 1e-7)
assert hem.sum() >= 30
for primitive in doc['meshes'][0]['primitives'][1:]:
    material = doc['materials'][primitive['material']]
    assert 'normalTexture' not in material
    assert 'baseColorTexture' not in material['pbrMetallicRoughness']

body, body_binary = read_glb(ROOT / report['body'])
bp = body['meshes'][0]['primitives'][0]
body_points = accessor(body, body_binary, bp['attributes']['POSITION'])
body_faces = accessor(body, body_binary, bp['indices']).reshape(-1, 3)
mask = (abs(body_points[body_faces, 0]) < .14).all(1) & (body_points[body_faces, 1] < .66).all(1)
mask[json.loads((OUT / 'body-occlusion.json').read_text())['hide_triangle_indices']] = False
tri = body_points[body_faces[mask]].astype(float)
a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
ab, ac = b - a, c - a
denominator = ab[:, 1] * ac[:, 2] - ab[:, 2] * ac[:, 1]
valid = abs(denominator) > 1e-12
a, ab, ac, denominator = a[valid], ab[valid], ac[valid], denominator[valid]
samples = np.concatenate((points[np.unique(outer_faces)], points[outer_faces].mean(1)))
intrusions = []
for point in samples:
    offset = point - a
    u = (offset[:, 1] * ac[:, 2] - offset[:, 2] * ac[:, 1]) / denominator
    v = (ab[:, 1] * offset[:, 2] - ab[:, 2] * offset[:, 1]) / denominator
    hit = (u >= 0) & (v >= 0) & (u + v <= 1)
    intersections = a[:, 0] + u * ab[:, 0] + v * ac[:, 0]
    count = np.count_nonzero(hit & (intersections > point[0]))
    if count % 2:
        intrusions.append(point.tolist())
assert not intrusions, intrusions[:10]
triangles = sum(doc['accessors'][p['indices']]['count'] // 3 for p in doc['meshes'][0]['primitives'])
result = {
    'date': '2026-10-13', 'sha256': hashlib.sha256((OUT / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
    'triangles': triangles, 'retained_source_triangles': int(kept.sum()), 'replaced_triangles': len(removed),
    'retained_uv_weights_bones_material_and_texture_bytes_unchanged': True,
    'canonical_skin_and_bone_hierarchy_unchanged': True, 'occlusion_mask_unchanged': True,
    'horizontal_outer_hem_vertices': int(hem.sum()), 'hem_height': report['shell']['hem_height'],
    'analytic_convex_surface_faces_checked': len(outer_faces), 'unit_normals': True,
    'clean_plate_material_has_no_baked_color_or_normal_map': True,
    'rest_skin_parity_samples': len(samples), 'rest_skin_intrusions': len(intrusions),
    'scope': 'Source preservation, convex surface normals, horizontal hem, and rest-pose skin parity at shell vertices and face centroids. No complete moving-triangle collision approval.'}
(OUT / 'preservation-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
