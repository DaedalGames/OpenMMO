import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
REPAIR = DIRECTORY / 'belt_rim_repair_v1'
SOURCE = REPAIR / 'before.glb'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
BLEND_HEIGHT = .607
TOP_HEIGHT = .615

doc, original = read_glb(SOURCE)
binary = bytearray(original)
mesh = next(mesh for mesh in doc['meshes'] if mesh['name'] == 'bottom_female_barbarian_belt')
primitive, = mesh['primitives']
attributes = primitive['attributes']
points = accessor(doc, original, attributes['POSITION'])
triangles = accessor(doc, original, primitive['indices']).reshape(-1, 3)
_, first, welded = np.unique(points.round(6), axis=0, return_index=True, return_inverse=True)
edges = welded[triangles[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
_, components = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                                              shape=(len(first),) * 2), directed=False)
shell = components[welded] == np.bincount(components[welded]).argmax()
selected = shell & (points[:, 1] > BLEND_HEIGHT)
height = TOP_HEIGHT - BLEND_HEIGHT
ramp = np.tanh(np.maximum(points[:, 1] - BLEND_HEIGHT, 0) / height)
result = points.copy()
result[selected, 1] = BLEND_HEIGHT + height * ramp[selected]
anchor_ids = [1425, 1577]
assert np.allclose(points[anchor_ids, 0], [.050819, .077304], atol=1e-6)
start, end = result[anchor_ids]
span = end[[0, 2]] - start[[0, 2]]
bridge = np.zeros(len(points), dtype=bool)
bridge_corners = []
for outer, inner in [(1549, 1438), (1557, 1552), (1569, 1565)]:
    t = np.clip((result[outer, [0, 2]] - start[[0, 2]]) @ span / (span @ span), 0, 1)
    target = float(start[1] + t * (end[1] - start[1]))
    lift = max(0, target - float(result[outer, 1]))
    group = np.isin(welded, welded[[outer, inner]])
    result[group, 1] += lift
    bridge |= group
    bridge_corners.append({'outer': outer, 'inner': inner, 'target_height': target, 'lift': lift})
selected |= bridge
assert np.array_equal(result[~selected], points[~selected])

body_doc, body_binary = read_glb(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
body_primitive = body_doc['meshes'][0]['primitives'][0]
body_points = accessor(body_doc, body_binary, body_primitive['attributes']['POSITION'])
body_faces = accessor(body_doc, body_binary, body_primitive['indices']).reshape(-1, 3)
body_triangles = body_points[body_faces]
body_triangles = body_triangles[(body_triangles[:, :, 1].max(1) > points[selected, 1].min()) &
                                (body_triangles[:, :, 1].min(1) < points[:, 1].max()) &
                                (np.abs(body_triangles[:, :, 0]).max(1) < .13)]
a = body_triangles[:, 0]
ab, ac = body_triangles[:, 1] - a, body_triangles[:, 2] - a
axis = np.array([0, 0, -.005607772618532181])


def body_radius(height, direction):
    origin = axis.copy()
    origin[1] = height
    h = np.cross(direction, ac)
    determinant = np.einsum('ij,ij->i', ab, h)
    inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=abs(determinant) > 1e-12)
    offset = origin - a
    u = np.einsum('ij,ij->i', offset, h) * inverse
    q = np.cross(offset, ab)
    v = q @ direction * inverse
    distance = np.einsum('ij,ij->i', ac, q) * inverse
    hits = distance[(abs(determinant) > 1e-12) & (u >= -1e-6) & (v >= -1e-6) &
                    (u + v <= 1 + 1e-6) & (distance > 0)]
    assert len(hits), 'Missing waist cross-section.'
    return float(hits.max())


clearances = []
for i in np.flatnonzero(selected):
    direction = points[i] - axis
    direction[1] = 0
    direction /= np.linalg.norm(direction)
    before_radius = body_radius(points[i, 1], direction)
    after_radius = body_radius(result[i, 1], direction)
    widening = max(0, after_radius - before_radius)
    result[i] += direction * widening
    clearances.append([np.linalg.norm((points[i] - axis)[[0, 2]]) - before_radius,
                       np.linalg.norm((result[i] - axis)[[0, 2]]) - after_radius])
clearances = np.array(clearances)
assert clearances[:, 1].min() >= .001 - 1e-6


def surface_normals(vertices):
    normals = np.zeros_like(vertices)
    faces = np.cross(vertices[triangles[:, 1]] - vertices[triangles[:, 0]],
                     vertices[triangles[:, 2]] - vertices[triangles[:, 0]])
    for corner in range(3):
        np.add.at(normals, triangles[:, corner], faces)
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


before_normals, after_normals = surface_normals(points), surface_normals(result)
rotation = np.cross(before_normals, after_normals)
cosine = (before_normals * after_normals).sum(1)
assert np.all(cosine > -.999)
for name in ['POSITION', 'NORMAL', 'TANGENT']:
    if name not in attributes:
        continue
    metadata = doc['accessors'][attributes[name]]
    values = result if name == 'POSITION' else accessor(doc, original, attributes[name])
    if name != 'POSITION':
        rotated = values[:, :3] + np.cross(rotation, values[:, :3])
        rotated += np.cross(rotation, np.cross(rotation, values[:, :3])) / (1 + cosine[:, None])
        changed = np.any(before_normals != after_normals, axis=1)
        values[changed, :3] = rotated[changed] / np.linalg.norm(rotated[changed], axis=1, keepdims=True)
    attributes[name] = add_accessor(doc, binary, values, metadata['type'], metadata['componentType'])
    doc['bufferViews'][doc['accessors'][attributes[name]]['bufferView']]['target'] = 34962

before_area = np.linalg.norm(np.cross(points[triangles[:, 1]] - points[triangles[:, 0]],
                                      points[triangles[:, 2]] - points[triangles[:, 0]]), axis=1)
after_area = np.linalg.norm(np.cross(result[triangles[:, 1]] - result[triangles[:, 0]],
                                     result[triangles[:, 2]] - result[triangles[:, 0]]), axis=1)
assert np.all(after_area[before_area > 1e-12] > 1e-12)
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT, doc, binary)
report = {
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output': str(OUTPUT.relative_to(ROOT)),
    'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Compress the continuous belt upper rim smoothly toward a level 0.615 m line with a tanh height blend above 0.607 m; preserve waist clearance using body cross-sections and rotate shading normals with the surface; lift only the paired corners of the front-right notch onto the line joining its existing rim endpoints.',
    'blend_height': BLEND_HEIGHT,
    'top_height': TOP_HEIGHT,
    'moved_vertices': int(selected.sum()),
    'local_rim_bridge': {'anchors': anchor_ids, 'corners': bridge_corners,
                         'vertices': np.flatnonzero(bridge).tolist()},
    'minimum_radial_body_clearance_before_after': clearances.min(0).tolist(),
    'maximum_radial_adjustment': float(np.linalg.norm((result - points)[:, [0, 2]], axis=1).max()),
    'maximum_lowering': float((points[:, 1] - result[:, 1]).max()),
    'upper_shell_height_before': float(points[:, 1].max()),
    'upper_shell_height_after': float(result[:, 1].max()),
    'textures_uvs_indices_weights_buckle_fittings_and_fur_unchanged': True,
    'no_new_degenerate_triangles': True,
}
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
fitting_path = ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json'
fitting = json.loads(fitting_path.read_text())
fitting['rigging']['sha256'] = report['output_sha256']
fitting['belt_rim_repair'] = str((REPAIR / 'repair.json').relative_to(ROOT))
fitting_path.write_text(json.dumps(fitting, indent=2) + '\n')
print(json.dumps(report, indent=2))
