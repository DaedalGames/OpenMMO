import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
REPAIR = DIRECTORY / 'panel_weights_v1'
SOURCE = REPAIR / 'before.glb'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
if len(sys.argv) > 1:
    incoming = (ROOT / sys.argv[1]).resolve()
    incoming_doc, _ = read_glb(incoming)
    assert len(incoming_doc['meshes']) == 1, 'Panel authoring needs the fitted single-mesh input.'
    if incoming != SOURCE.resolve():
        REPAIR.mkdir(exist_ok=True)
        shutil.copyfile(incoming, SOURCE)

doc, original = read_glb(SOURCE)
binary = bytearray(original)
primitive, = doc['meshes'][0]['primitives']
attributes = primitive['attributes']
points = accessor(doc, original, attributes['POSITION'])
triangles = accessor(doc, original, primitive['indices']).reshape(-1, 3)
joints = accessor(doc, original, attributes['JOINTS_0'])
weights = accessor(doc, original, attributes['WEIGHTS_0'])
names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
fit = np.load(DIRECTORY / 'fit-data.npz')
fitted = fit['fitted']
_, nearest = cKDTree(np.c_[fitted[:, 0], fitted[:, 2], -fitted[:, 1]]).query(points)
fur, cord = fit['fur'][nearest], fit['cord'][nearest]
edges = triangles[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)
_, charts = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                                          shape=(len(points),) * 2), directed=False)
seeds, roles = [], []
for chart in np.unique(charts):
    group = np.flatnonzero(charts == chart)
    low, high = points[group].min(0), points[group].max(0)
    if len(group) < 30 or low[1] > .48 or high[1] < .54 or fur[group].mean() < .8:
        continue
    role = 'center' if low[0] < 0 < high[0] else 'left' if low[0] > 0 else 'right'
    seeds.extend(group)
    roles.extend([role] * len(group))
assert set(roles) == {'center', 'left', 'right'}
_, first, welded = np.unique(points.round(6), axis=0, return_index=True, return_inverse=True)
unique_edges = np.unique(np.sort(welded[edges], axis=1), axis=0)
lengths = np.linalg.norm(points[first][unique_edges[:, 0]] - points[first][unique_edges[:, 1]], axis=1)
graph = coo_matrix((lengths, (unique_edges[:, 0], unique_edges[:, 1])), shape=(len(first),) * 2).tocsr()
graph = graph.maximum(graph.T)
_, components = connected_components(graph, directed=False)
components = components[welded]
front_shell = components == np.bincount(components).argmax()
fur |= front_shell & (points[:, 1] < .575)
distances = []
labels = ['center', 'left', 'right']
for label in labels:
    starts = np.unique(welded[np.array(seeds)[np.array(roles) == label]])
    distances.append(dijkstra(graph, indices=starts, min_only=True))
distance = np.array(distances)
role = np.array(labels)[distance.argmin(0)][welded]
unreachable = ~np.isfinite(distance.min(0))[welded]
_, closest = cKDTree(points[seeds]).query(points[unreachable])
role[unreachable] = np.array(roles)[closest]
blend = np.clip((.58 - points[:, 1]) / .025, 0, 1)
blend = blend * blend * (3 - 2 * blend)
full = np.zeros((len(points), len(names)))
for k in range(4):
    full[np.arange(len(points)), joints[:, k]] += weights[:, k]
updated = full.copy()
for label in ['center', 'left', 'right']:
    group = fur & (role == label)
    updated[group] *= (1 - blend[group, None])
    target = {'Hips': 1} if label == 'center' else {f'{label.title()}UpLeg': 1}
    for bone, share in target.items():
        updated[group, names.index(bone)] += blend[group] * share
updated[fur & (points[:, 1] > .555)] = full[fur & (points[:, 1] > .555)]
fur_ids = np.flatnonzero(fur)
_, closest = cKDTree(points[fur_ids]).query(points[cord])
updated[cord] = updated[fur_ids[closest]]
order = np.argsort(updated, axis=1)[:, ::-1][:, :4]
values = np.take_along_axis(updated, order, axis=1)
values /= values.sum(1, keepdims=True)
order[values == 0] = 0
unchanged = ~(fur | cord)
order[unchanged] = joints[unchanged]
values[unchanged] = weights[unchanged]
for name, array in [('JOINTS_0', order), ('WEIGHTS_0', values)]:
    metadata = doc['accessors'][attributes[name]]
    attributes[name] = add_accessor(doc, binary, array, metadata['type'], metadata['componentType'])
    doc['bufferViews'][doc['accessors'][attributes[name]]['bufferView']]['target'] = 34962
rest_matrices = np.linalg.inv(accessor(doc, original, doc['skins'][0]['inverseBindMatrices']).reshape(-1, 4, 4).swapaxes(-1, -2))
colliders = []
for side in ['Left', 'Right']:
    upper = rest_matrices[names.index(side + 'UpLeg'), :3, 3]
    lower = rest_matrices[names.index(side + 'Leg'), :3, 3]
    colliders.append({'bone': side + 'UpLeg', 'center': ((upper + lower) * .5).tolist(), 'radii': [.047, .125, .057]})
face_role = np.array(labels)[np.array([(role[triangles] == label).sum(1) for label in labels]).argmax(0)]
cloth_faces = fur[triangles].all(1)
front = cloth_faces & (face_role == 'center') & (points[triangles, 2].mean(1) >= 0)
back = cloth_faces & (face_role == 'center') & ~front
front |= cord[triangles].all(1)
groups = [('front', front, [0, 0, 1]), ('back', back, [0, 0, -1]),
          ('left', cloth_faces & (face_role == 'left'), [1, 0, 0]),
          ('right', cloth_faces & (face_role == 'right'), [-1, 0, 0])]
base_faces = ~np.any([group for _, group, _ in groups], axis=0)
mesh_node = next(node for node in doc['nodes'] if node.get('mesh') == 0)
doc['meshes'] = []
arrays = {name: accessor(doc, binary, index) for name, index in attributes.items()}
part_sources = {}
for label, face_mask, outward in [('belt', base_faces, None), *groups]:
    faces_used = triangles[face_mask]
    vertices, inverse = np.unique(faces_used, return_inverse=True)
    part_sources[label] = vertices.tolist()
    attrs = {}
    for name, array in arrays.items():
        metadata = doc['accessors'][attributes[name]]
        attrs[name] = add_accessor(doc, binary, array[vertices], metadata['type'], metadata['componentType'])
        doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
    indices = add_accessor(doc, binary, inverse.reshape(-1, 1), 'SCALAR', 5123)
    doc['bufferViews'][doc['accessors'][indices]['bufferView']]['target'] = 34963
    extras = {'rig_id': 'human_female_01_local_v1', 'part_id': 'bottom_female_barbarian', 'panel': label}
    if outward is not None:
        high = points[vertices, 1].max()
        top = points[vertices][points[vertices, 1] > high - .025]
        pivot = [float(np.median(top[:, 0])), float(high), float(np.median(top[:, 2]))]
        collider_list = colliders if label in ['front', 'back'] else [colliders[0 if label == 'left' else 1]]
        extras['pelt_physics'] = {
            'kind': 'fur', 'bone': 'Hips', 'pivot': pivot, 'outward': outward,
            'attachment_depth': .025,
            'length': float(high - points[vertices, 1].min()),
            'bend': {'droop': .9, 'contact': True},
            'motion': {'damping': 12, 'stiffness': 65, 'gravity': 6, 'inertia': .6,
                       'max_angle': 1.35, 'min_angle': .08 if label == 'front' else .10 if label in ['left', 'right'] else 0, 'flex_clearance': .15},
            'colliders': collider_list,
        }
    name = 'bottom_female_barbarian_' + label
    doc['meshes'].append({'name': name, 'primitives': [{'attributes': attrs, 'indices': indices, 'material': primitive['material']}]})
    if label == 'belt':
        mesh_node.update(mesh=0, name=name, extras=extras)
    else:
        doc['scenes'][0]['nodes'].append(len(doc['nodes']))
        doc['nodes'].append({'name': name, 'mesh': len(doc['meshes']) - 1, 'skin': 0, 'extras': extras})
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT, doc, binary)
report = {
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output': str(OUTPUT.relative_to(ROOT)),
    'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Separate the belt, front with braid, rear, and side fur panels; preserve their rest surfaces and attachments; use existing pelt bending and thigh colliders with Hips anchors.',
    'parts': part_sources,
    'meshes': len(doc['meshes']),
    'vertices': sum(doc['accessors'][mesh['primitives'][0]['attributes']['POSITION']]['count'] for mesh in doc['meshes']),
    'panel_vertices': {label: int((fur & (role == label)).sum()) for label in ['center', 'left', 'right']},
    'geometry_uvs_textures_belt_and_fittings_unchanged': True,
}
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'parts'}, indent=2))
