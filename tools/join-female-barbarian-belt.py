import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
REPAIR = DIRECTORY / 'belt_fur_join_v1'
SOURCE = REPAIR / 'before.glb'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
doc, original = read_glb(SOURCE)
binary = bytearray(original)
nodes = {node['extras']['panel']: node for node in doc['nodes'] if 'panel' in node.get('extras', {})}
belt_primitive, = doc['meshes'][nodes['belt']['mesh']]['primitives']
belt = {key: accessor(doc, original, index) for key, index in belt_primitive['attributes'].items()}
outer = np.flatnonzero((belt['NORMAL'][:, [0, 2]] * belt['POSITION'][:, [0, 2]]).sum(1) > .008)
tree = cKDTree(belt['POSITION'][outer])
records = {}
for panel in ['front', 'left', 'right']:
    node = nodes[panel]
    primitive, = doc['meshes'][node['mesh']]['primitives']
    arrays = {key: accessor(doc, original, index) for key, index in primitive['attributes'].items()}
    points = arrays['POSITION']
    faces = accessor(doc, original, primitive['indices']).reshape(-1, 3)
    count = len(points)
    _, welded = np.unique(points.round(6), axis=0, return_inverse=True)
    welded = welded.ravel()
    edges = {}
    for face in faces:
        for i in range(3):
            a, b = int(face[i]), int(face[(i + 1) % 3])
            edges.setdefault(tuple(sorted([welded[a], welded[b]])), []).append((a, b))
    distance, nearest = tree.query(points)
    selected = []
    for rows in edges.values():
        if len(rows) != 1:
            continue
        a, b = rows[0]
        if max(points[[a, b], 1]) < .55 or min(points[[a, b], 2]) < -.035:
            continue
        if max(distance[[a, b]]) > .045 or max(distance[[a, b]]) < 1e-5:
            continue
        selected.append((a, b))
    clipped, additions = [], []
    for a, b in selected:
        if min(points[[a, b], 1]) < .548:
            low, high = (a, b) if points[a, 1] < points[b, 1] else (b, a)
            t = float((.548 - points[low, 1]) / (points[high, 1] - points[low, 1]))
            index = len(arrays['POSITION'])
            additions.append({'index': index, 'panel': panel, 'vertices': [low, high], 'weights': [1 - t, t]})
            for key, values in list(arrays.items()):
                if key in ['JOINTS_0', 'WEIGHTS_0']:
                    continue
                value = values[low] * (1 - t) + values[high] * t
                if key in ['NORMAL', 'TANGENT']:
                    value[:3] /= np.linalg.norm(value[:3])
                arrays[key] = np.concatenate([values, value[None]])
            weights = {}
            for vertex, share in [(low, 1 - t), (high, t)]:
                for bone, weight in zip(arrays['JOINTS_0'][vertex], arrays['WEIGHTS_0'][vertex]):
                    weights[int(bone)] = weights.get(int(bone), 0) + float(weight) * share
            top = sorted(weights.items(), key=lambda row: -row[1])[:4]
            total = sum(weight for _, weight in top)
            arrays['JOINTS_0'] = np.concatenate([arrays['JOINTS_0'], [[bone for bone, _ in top] + [0] * (4 - len(top))]])
            arrays['WEIGHTS_0'] = np.concatenate([arrays['WEIGHTS_0'], [[weight / total for _, weight in top] + [0] * (4 - len(top))]])
            if low == a:
                a = index
            else:
                b = index
        clipped.append((a, b))
    vertices = sorted({vertex for edge in clipped for vertex in edge})
    _, nearest = tree.query(arrays['POSITION'])
    nearest = outer[nearest]
    anchors = {vertex: len(arrays['POSITION']) + i for i, vertex in enumerate(vertices)}
    additions.extend({'index': anchors[vertex], 'panel': 'belt', 'vertices': [int(nearest[vertex])], 'weights': [1]} for vertex in vertices)
    lower = {vertex: len(arrays['POSITION']) + len(vertices) + i for i, vertex in enumerate(vertices)}
    additions.extend({'index': lower[vertex], 'panel': panel, 'vertices': [vertex], 'weights': [1]} for vertex in vertices)
    for key, values in arrays.items():
        extra = values[vertices].copy()
        if key in ['POSITION', 'JOINTS_0', 'WEIGHTS_0']:
            extra = belt[key][nearest[vertices]].copy()
        if key == 'POSITION' and panel == 'front':
            radial = extra[:, [0, 2]]
            extra[:, [0, 2]] += radial / np.linalg.norm(radial, axis=1)[:, None] * .006
        metadata = doc['accessors'][primitive['attributes'][key]]
        lower_values = values[vertices].copy()
        if key == 'TEXCOORD_0':
            extra[:] = [.207, .616]
            lower_values[:] = [.207, .616]
        combined = np.concatenate([values, extra, lower_values])
        primitive['attributes'][key] = add_accessor(doc, binary, combined, metadata['type'], metadata['componentType'])
        doc['bufferViews'][doc['accessors'][primitive['attributes'][key]]['bufferView']]['target'] = 34962
    output_faces = faces.tolist()
    for a, b in clipped:
        output_faces.extend([[lower[b], lower[a], anchors[a]], [lower[b], anchors[a], anchors[b]]])
    primitive['indices'] = add_accessor(doc, binary, np.asarray(output_faces).reshape(-1, 1), 'SCALAR', 5123)
    doc['bufferViews'][doc['accessors'][primitive['indices']]['bufferView']]['target'] = 34963
    config = node['extras']['pelt_physics']
    config['bend']['constraint_triangles'] = len(faces)
    pinned = set(config['attachment_vertices']) | {row['index'] for row in additions if row['index'] not in lower.values()}
    pinned.update(lower[vertex] for vertex in vertices if vertex in pinned)
    config['attachment_vertices'] = sorted(pinned)
    records[panel] = {'original_vertices': count, 'original_triangles': len(faces), 'bridge_edges': len(clipped), 'vertices': additions}
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT, doc, binary)
groups = {}
for panel, node in nodes.items():
    primitive, = doc['meshes'][node['mesh']]['primitives']
    for point in accessor(doc, binary, primitive['attributes']['POSITION']):
        groups.setdefault(tuple(point.round(6)), set()).add(panel)
report = {
    'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output': str(OUTPUT.relative_to(ROOT)), 'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Bridge upper pelt boundaries to the outer belt with skin-weighted anchors; clip long edges at 0.548 m and keep added lining outside the original cloth length constraints. Front anchors gain 6 mm radial clearance. Added faces sample the existing brown lining texel at UV 0.207, 0.616.',
    'panels': records,
    'stitched_belt_seams': sum('belt' in labels and len(labels) > 1 for labels in groups.values()),
    'triangles_added': sum(row['bridge_edges'] * 2 for row in records.values()),
    'vertices_added': sum(len(row['vertices']) for row in records.values()),
    'original_vertices_indices_materials_and_rig_unchanged': True,
}
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
fitting_path = ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json'
fitting = json.loads(fitting_path.read_text())
fitting['rigging']['sha256'] = report['output_sha256']
fitting['rigging']['vertices'] = sum(doc['accessors'][mesh['primitives'][0]['attributes']['POSITION']]['count'] for mesh in doc['meshes'])
fitting['triangles'] = sum(doc['accessors'][mesh['primitives'][0]['indices']]['count'] // 3 for mesh in doc['meshes'])
fitting['belt_fur_join'] = str((REPAIR / 'repair.json').relative_to(ROOT))
fitting_path.write_text(json.dumps(fitting, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'panels'}, indent=2))
