import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v38', DIRECTORY / 'fitted_v39'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == 'ab70b4b99ace7135a9138098e5302a58a712d4f2724176c34236093fad779a7a'
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
report = json.loads((SOURCE / 'fitting.json').read_text())
primitives = doc['meshes'][0]['primitives']
attrs = primitives[0]['attributes']
original = {name: accessor(doc, binary, index) for name, index in attrs.items()}
faces = accessor(doc, binary, primitives[0]['indices']).reshape(-1, 3)
plate = {name: accessor(doc, binary, index) for name, index in primitives[1]['attributes'].items()}
plate_faces = accessor(doc, binary, primitives[1]['indices']).reshape(-1, 3)
names = [doc['nodes'][node]['name'] for node in doc['skins'][0]['joints']]
pose_file = DIRECTORY / 'fitted_v37/strap-poses.json'
pose = json.loads(pose_file.read_text())[1]
assert pose['name'] == 'idle1' and pose['time'] == 0
matrices = np.repeat(np.eye(4)[None], len(names), axis=0)
for name, matrix in zip(['Hips', 'LeftUpLeg', 'RightUpLeg'], pose['matrices']):
    matrices[names.index(name)] = np.array(matrix).reshape(4, 4).T


def transform(joints, weights):
    return (matrices[np.asarray(joints, dtype=int)] * np.asarray(weights)[:, None, None]).sum(0)


def posed(attributes):
    return np.array([(transform(j, w) @ np.append(p, 1))[:3]
                     for p, j, w in zip(attributes['POSITION'], attributes['JOINTS_0'], attributes['WEIGHTS_0'])])


plate_posed = posed(plate)
triangles = plate_posed[plate_faces]
a, u, v = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
determinant = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
valid = abs(determinant) > 1e-12
inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
face_normal = np.cross(u, v)
face_normal /= np.maximum(np.linalg.norm(face_normal, axis=1, keepdims=True), 1e-12)
face_normal *= np.where(face_normal[:, 2:3] > 0, -1, 1)


def hit(point):
    delta = point - a
    bu = (delta[:, 0] * v[:, 1] - delta[:, 1] * v[:, 0]) * inverse
    bv = (u[:, 0] * delta[:, 1] - u[:, 1] * delta[:, 0]) * inverse
    z = a[:, 2] + bu * u[:, 2] + bv * v[:, 2]
    selected = np.flatnonzero(valid & (bu >= -1e-6) & (bv >= -1e-6) & (bu + bv <= 1.000001) & (z < -.015))
    if len(selected):
        index = selected[np.argmin(z[selected])]
        return index, np.array([1 - bu[index] - bv[index], bu[index], bv[index]]), z[index], 0.
    best = None
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        start, end = triangles[:, i, :2], triangles[:, j, :2]
        edge = end - start
        t = np.clip(np.sum((point[:2] - start) * edge, axis=1) / np.maximum(np.sum(edge * edge, axis=1), 1e-15), 0, 1)
        distance = np.linalg.norm(start + t[:, None] * edge - point[:2], axis=1)
        distance[~valid | (triangles[:, :, 2].mean(1) >= -.015) | (abs(face_normal[:, 2]) < .7)] = np.inf
        index = np.argmin(distance)
        if distance[index] < .018 and (best is None or distance[index] < best[3]):
            bary = np.zeros(3)
            bary[i], bary[j] = 1 - t[index], t[index]
            best = index, bary, z[index], float(distance[index])
    return best


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


middle = np.array([vertex for section in report['rear_strap_sections'] for vertex in section['vertices']])
removed = np.flatnonzero(np.isin(faces, middle).any(1))
assert len(removed) == 48
strap_posed = posed(original)
strap_triangles = strap_posed[faces[removed]]
sa = strap_triangles[:, 0]
su, sv = strap_triangles[:, 1] - sa, strap_triangles[:, 2] - sa
sd = su[:, 0] * sv[:, 1] - su[:, 1] * sv[:, 0]
svalid = abs(sd) > 1e-12
sinverse = np.divide(1, sd, out=np.zeros_like(sd), where=svalid)


def thickness(point):
    delta = point - sa
    bu = (delta[:, 0] * sv[:, 1] - delta[:, 1] * sv[:, 0]) * sinverse
    bv = (su[:, 0] * delta[:, 1] - su[:, 1] * delta[:, 0]) * sinverse
    z = sa[:, 2] + bu * su[:, 2] + bv * sv[:, 2]
    hits = z[svalid & (bu >= -1e-4) & (bv >= -1e-4) & (bu + bv <= 1.0001)]
    if len(hits) == 0 or np.ptp(hits) < 1e-8:
        return 0.
    return .001 * float(np.clip((hits.max() - point[2]) / np.ptp(hits), 0, 1))


new_values = {name: list(array) for name, array in original.items()}
new_faces, contacts, cache = [], [], {}
clearance = .001 / 1.8


def weights_for(attributes, ids, bary):
    weights = np.zeros(len(names))
    for vertex, fraction in zip(ids, bary):
        for joint, weight in zip(attributes['JOINTS_0'][vertex], attributes['WEIGHTS_0'][vertex]):
            weights[joint] += fraction * weight
    return weights


def pack_weights(weights):
    ids = np.argsort(-weights)[:4]
    values = np.maximum(weights[ids], 0)
    values /= values.sum()
    return np.where(values > 0, ids, 0), values


def emit(ids, bary):
    data = {name: bary @ array[ids] for name, array in original.items() if name not in ['JOINTS_0', 'WEIGHTS_0']}
    joint, weight = pack_weights(weights_for(original, ids, bary))
    rest = data['POSITION'].copy()
    key = tuple(np.round(np.concatenate([rest, data['NORMAL'], data['TEXCOORD_0']]), 7))
    if key in cache:
        return cache[key]
    matrix = transform(joint, weight)
    world = (matrix @ np.append(rest, 1))[:3]
    contact = hit(world)
    blend = smooth((.572 - rest[1]) / .012) * smooth((rest[1] - .46) / .025)
    if contact is not None and blend > 0:
        face, barycentric, z, edge_distance = contact
        blend *= 1 - smooth((edge_distance - .002) / .016)
        n = face_normal[face]
        layer = thickness(world)
        target = world.copy()
        target[2] = z - (clearance + layer) / max(abs(n[2]), .2)
        plate_weights = weights_for(plate, plate_faces[face], barycentric)
        mixed = (1 - blend) * weights_for(original, ids, bary) + blend * plate_weights
        joint, weight = pack_weights(mixed)
        new_matrix = transform(joint, weight)
        world = world * (1 - blend) + target * blend
        data['POSITION'] = (np.linalg.inv(new_matrix) @ np.append(world, 1))[:3]
        old_normal = np.linalg.solve(matrix[:3, :3].T, data['NORMAL'])
        old_normal /= np.linalg.norm(old_normal)
        outward = np.array([0., 0., -1.])
        axis = np.cross(outward, n)
        skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        rotation = np.eye(3) + skew + skew @ skew / (1 + outward @ n)
        normal = ((1 - blend) * old_normal + blend * (rotation @ old_normal)) @ new_matrix[:3, :3]
        normal /= np.linalg.norm(normal)
        data['NORMAL'] = normal
        tangent = matrix[:3, :3] @ data['TANGENT'][:3]
        tangent = np.linalg.solve(new_matrix[:3, :3], ((1 - blend) * tangent + blend * (rotation @ tangent)))
        tangent -= normal * (normal @ tangent)
        data['TANGENT'][:3] = tangent / np.linalg.norm(tangent)
        if blend > .999 and layer < 1e-7 and edge_distance == 0:
            contacts.append({'vertex': len(new_values['POSITION']), 'plate_vertices': plate_faces[face].tolist(), 'barycentric': barycentric.tolist(), 'normal': n.tolist(), 'gap': clearance})
    for name in ['NORMAL', 'TANGENT']:
        data[name][:3] /= np.linalg.norm(data[name][:3])
    data['TANGENT'][3] = -1 if data['TANGENT'][3] < 0 else 1
    data['JOINTS_0'], data['WEIGHTS_0'] = joint, weight
    index = len(new_values['POSITION'])
    for name, value in data.items():
        new_values[name].append(value)
    cache[key] = index
    return index


def clip(polygon, height, ids, above):
    result = []
    for left, right in zip(polygon, polygon[1:] + polygon[:1]):
        y0, y1 = left @ original['POSITION'][ids, 1], right @ original['POSITION'][ids, 1]
        in0, in1 = (y0 >= height, y1 >= height) if above else (y0 <= height, y1 <= height)
        if in0:
            result.append(left)
        if in0 != in1:
            result.append(left + (right - left) * ((height - y0) / (y1 - y0)))
    return result


for face in removed:
    ids = faces[face]
    polygons = [list(np.eye(3))]
    low, high = original['POSITION'][ids, 1].min(), original['POSITION'][ids, 1].max()
    for height in np.arange(.44, .575, .0025):
        if not low < height < high:
            continue
        divided = []
        for polygon in polygons:
            ys = [bary @ original['POSITION'][ids, 1] for bary in polygon]
            if min(ys) < height < max(ys):
                divided.extend([clip(polygon, height, ids, True), clip(polygon, height, ids, False)])
            else:
                divided.append(polygon)
        polygons = divided
    for polygon in polygons:
        indices = [emit(ids, bary) for bary in polygon]
        for i in range(1, len(indices) - 1):
            if len({indices[0], indices[i], indices[i + 1]}) == 3:
                new_faces.append([indices[0], indices[i], indices[i + 1]])
for name, values in new_values.items():
    meta = doc['accessors'][attrs[name]]
    attrs[name] = add_accessor(doc, binary, np.array(values), meta['type'], meta['componentType'])
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
indices = np.concatenate([np.delete(faces, removed, axis=0), new_faces]).astype('<u4')
primitives[0]['indices'] = add_accessor(doc, binary, indices.reshape(-1, 1), 'SCALAR', 5125)
doc['bufferViews'][doc['accessors'][primitives[0]['indices']]['bufferView']]['target'] = 34963
doc['buffers'][0]['byteLength'] = len(binary)
doc['nodes'][0]['extras']['fitting_version'] = 39
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Subdivide the two rear strap ribbons and fit their inner surface to the posed hip plates with a 1 mm clearance at 1.8 m character height; transfer plate weights at contact and retain waist/clip transitions.',
              rear_strap_surface={'removed_faces': removed.tolist(), 'original_vertex_count': len(original['POSITION']), 'new_vertex_count': len(new_values['POSITION']), 'new_faces': new_faces, 'contacts': contacts, 'clearance_m': .001, 'character_height_m': 1.8},
              triangles=sum(doc['accessors'][p['indices']]['count'] // 3 for p in primitives),
              preserved=['front straps', 'clips', 'waist anchors', 'plates', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'new_vertices': len(new_values['POSITION']) - len(original['POSITION']), 'new_triangles': len(new_faces), 'contacts': len(contacts)}))
