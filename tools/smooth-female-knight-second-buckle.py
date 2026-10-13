import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v41', DIRECTORY / 'fitted_v42'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '98166e9d881c86bcc509124dcec599c4fa4e428eea59eddf0b7cff8f3c45bbb4'
doc, binary = read_glb(source)
binary = bytearray(binary)
report = json.loads((SOURCE / 'fitting.json').read_text())
primitive = doc['meshes'][0]['primitives'][0]
original = {name: accessor(doc, binary, index) for name, index in primitive['attributes'].items()}
values = {name: array.copy() for name, array in original.items()}
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
parameters = np.load(DIRECTORY / 'fitted_v40/surface-source-positions.npy')
reference_doc, reference_binary = read_glb(DIRECTORY / 'fitted_v40/bottom_female_knight.glb')
reference = {name: accessor(reference_doc, reference_binary, index) for name, index in reference_doc['meshes'][0]['primitives'][0]['attributes'].items()}
names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
matrices = np.repeat(np.eye(4)[None], len(names), axis=0)
pose = json.loads((DIRECTORY / 'fitted_v37/strap-poses.json').read_text())[1]
for name, matrix in zip(['Hips', 'LeftUpLeg', 'RightUpLeg'], pose['matrices']):
    matrices[names.index(name)] = np.array(matrix).reshape(4, 4).T


def posed(data):
    skin = (matrices[data['JOINTS_0']] * data['WEIGHTS_0'][:, :, None, None]).sum(1)
    return np.einsum('vij,vj->vi', skin, np.column_stack([data['POSITION'], np.ones(len(parameters))]))[:, :3]


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def hermite(a, b, da, db, t):
    return (2*t**3 - 3*t**2 + 1)*a + (t**3 - 2*t**2 + t)*da + (-2*t**3 + 3*t**2)*b + (t**3 - t**2)*db


world, reference_world = posed(original), posed(reference)
new_world = world.copy()
used = np.unique(faces)
changed, blends, records = [], {}, []
upper, lower = .575, .505
span = upper - lower
for region in report['straight_upper_rear_straps']['regions']:
    side = region['side']
    selected = used[(used >= report['rear_strap_surface']['original_vertex_count']) & (parameters[used, 0] * side > 0)]
    side_faces = faces[np.isin(faces, selected).all(1)]
    triangles = parameters[side_faces]
    a = triangles[:, 0]
    u, v = triangles[:, 1] - a, triangles[:, 2] - a
    det = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    inv = np.divide(1, det, out=np.zeros_like(det), where=abs(det) > 1e-12)

    def bounds(y):
        crossings = []
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            lo, hi = triangles[:, i], triangles[:, j]
            mask = ((lo[:, 1] <= y) & (hi[:, 1] >= y) | (hi[:, 1] <= y) & (lo[:, 1] >= y)) & (abs(hi[:, 1] - lo[:, 1]) > 1e-12)
            t = (y - lo[mask, 1]) / (hi[mask, 1] - lo[mask, 1])
            crossings.extend((lo[mask] + t[:, None] * (hi[mask] - lo[mask]))[:, 0])
        return min(crossings), max(crossings)

    def surface(x, y, data=reference, positions=reference_world):
        delta = np.array([x, y, 0]) - a
        bu = (delta[:, 0] * v[:, 1] - delta[:, 1] * v[:, 0]) * inv
        bv = (u[:, 0] * delta[:, 1] - u[:, 1] * delta[:, 0]) * inv
        z = a[:, 2] + bu * u[:, 2] + bv * v[:, 2]
        hits = np.flatnonzero((abs(det) > 1e-12) & (bu >= -1e-5) & (bv >= -1e-5) & (bu + bv <= 1.00001))
        if not len(hits):
            return None
        face = hits[np.argmax(z[hits])]
        bary = np.array([1 - bu[face] - bv[face], bu[face], bv[face]])
        weights = np.zeros(len(names))
        for vertex, fraction in zip(side_faces[face], bary):
            for joint, weight in zip(data['JOINTS_0'][vertex], data['WEIGHTS_0'][vertex]):
                weights[joint] += fraction * weight
        return z[face], bary @ positions[side_faces[face]], weights

    def section(y, data=reference, positions=reference_world):
        xmin, xmax = bounds(y)
        sample = surface((xmin + xmax) / 2, y, data, positions)
        left, right = surface(xmin + .0002, y, data, positions), surface(xmax - .0002, y, data, positions)
        across = right[1] - left[1]
        width = np.linalg.norm(across) + .0004
        return sample[1], across / np.linalg.norm(across), width, sample[2]

    start = np.array(region['bottom'])
    start_direction = np.array(region['across'])
    start_width = region['widths'][0]
    end, end_direction, end_width, end_weights = section(lower)
    tangent_start = -(np.array(region['top']) - start) * span / (.623 - upper)
    tangent_end = -(section(lower + .001)[0] - section(lower - .001)[0]) * span / .002
    width_tangent_start = -(region['widths'][1] - start_width) * span / (.623 - upper)
    width_tangent_end = -(section(lower + .001)[2] - section(lower - .001)[2]) * span / .002
    start_weights = section(upper, original, world)[3]
    weights_tangent_start = -(section(upper + .001, original, world)[3] - start_weights) * span / .001
    weights_tangent_end = -(section(lower + .001)[3] - section(lower - .001)[3]) * span / .002
    samples = []
    for vertex in selected:
        p = parameters[vertex]
        if not lower < p[1] < upper:
            continue
        t = (upper - p[1]) / span
        center = hermite(start, end, tangent_start, tangent_end, t)
        tangent = (hermite(start, end, tangent_start, tangent_end, t + 1e-5) - hermite(start, end, tangent_start, tangent_end, t - 1e-5)) / 2e-5
        across = start_direction * (1 - smooth(t)) + end_direction * smooth(t)
        across /= np.linalg.norm(across)
        outward = np.cross(across, -tangent)
        outward /= np.linalg.norm(outward)
        outward *= -1 if outward[2] > 0 else 1
        width = hermite(start_width, end_width, width_tangent_start, width_tangent_end, t)
        xmin, xmax = bounds(p[1])
        lateral = (p[0] - (xmin + xmax) / 2) / (xmax - xmin)
        inner = surface(p[0], p[1])
        layer = np.clip(inner[0] - p[2], 0, .005) if inner is not None else .001
        target = center + across * lateral * width + outward * layer
        blend = smooth((p[1] - lower) / .012)
        new_world[vertex] = world[vertex] * (1 - blend) + target * blend
        weights = np.zeros(len(names))
        for joint, weight in zip(original['JOINTS_0'][vertex], original['WEIGHTS_0'][vertex]):
            weights[joint] += weight * (1 - blend)
        weights += blend * hermite(start_weights, end_weights, weights_tangent_start, weights_tangent_end, t)
        weights = np.maximum(weights, 0)
        joints = np.argsort(-weights)[:4]
        weights = weights[joints] / weights[joints].sum()
        joints = np.where(weights > 0, joints, 0)
        matrix = (matrices[joints] * weights[:, None, None]).sum(0)
        values['POSITION'][vertex] = np.linalg.solve(matrix, np.append(new_world[vertex], 1))[:3]
        values['JOINTS_0'][vertex], values['WEIGHTS_0'][vertex] = joints, weights
        changed.append(int(vertex))
        blends[int(vertex)] = blend
        samples.append({'vertex': int(vertex), 'position': new_world[vertex].tolist()})
    records.append({'side': side, 'start': start.tolist(), 'end': end.tolist(), 'start_tangent': tangent_start.tolist(), 'end_tangent': tangent_end.tolist(), 'start_width': start_width, 'end_width': end_width, 'start_width_tangent': width_tangent_start, 'end_width_tangent': width_tangent_end, 'samples': samples})

accumulated = np.zeros_like(world)
changed_set = set(changed)
for face in faces:
    if not any(int(vertex) in changed_set for vertex in face):
        continue
    triangle = new_world[face]
    normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
    for vertex in face:
        accumulated[vertex] += normal
for vertex in changed:
    n = accumulated[vertex]
    if np.linalg.norm(n) < 1e-12:
        continue
    matrix = (matrices[values['JOINTS_0'][vertex]] * values['WEIGHTS_0'][vertex, :, None, None]).sum(0)
    n = matrix[:3, :3].T @ n
    n /= np.linalg.norm(n)
    n = n * blends[vertex] + original['NORMAL'][vertex] * (1 - blends[vertex])
    n /= np.linalg.norm(n)
    values['NORMAL'][vertex] = n
    tangent = values['TANGENT'][vertex, :3]
    tangent -= n * (n @ tangent)
    values['TANGENT'][vertex, :3] = tangent / np.linalg.norm(tangent)
for name in ['POSITION', 'NORMAL', 'TANGENT', 'JOINTS_0', 'WEIGHTS_0']:
    array = values[name]
    metadata = doc['accessors'][primitive['attributes'][name]]
    view = doc['bufferViews'][metadata['bufferView']]
    offset = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    assert view.get('byteStride', array.strides[0]) == array.strides[0]
    binary[offset:offset + array.nbytes] = array.tobytes()
    if 'min' in metadata or 'max' in metadata:
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 42
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(source=str(source.relative_to(ROOT)), source_sha256=source_hash, output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Continue the straight upper rear straps below the second buckles with tangent-matched cubic curves, matching width and skin-weight slopes and blending back into the existing lower straps.',
              smooth_second_buckle={'vertices': changed, 'regions': records},
              preserved=['straight upper straps', 'front straps', 'boot clips', 'plates', 'topology', 'UVs', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'changed_vertices': len(changed)}))
