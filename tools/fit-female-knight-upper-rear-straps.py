import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v39', DIRECTORY / 'fitted_v40'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == 'd9109ce31212e9297d46a68088ec85b4ecf1140628a767eb8eac0fccbdc11b23'
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
report = json.loads((SOURCE / 'fitting.json').read_text())
primitives = doc['meshes'][0]['primitives']
attributes = [{name: accessor(doc, binary, index) for name, index in p['attributes'].items()} for p in primitives]
original, plate = attributes[:2]
faces = accessor(doc, binary, primitives[0]['indices']).reshape(-1, 3)
plate_faces = accessor(doc, binary, primitives[1]['indices']).reshape(-1, 3)
names = [doc['nodes'][node]['name'] for node in doc['skins'][0]['joints']]
pose = json.loads((DIRECTORY / 'fitted_v37/strap-poses.json').read_text())[1]
assert pose['name'] == 'idle1' and pose['time'] == 0
matrices = np.repeat(np.eye(4)[None], len(names), axis=0)
for name, matrix in zip(['Hips', 'LeftUpLeg', 'RightUpLeg'], pose['matrices']):
    matrices[names.index(name)] = np.array(matrix).reshape(4, 4).T


def transform(joints, weights):
    return (matrices[np.asarray(joints, dtype=int)] * np.asarray(weights)[:, None, None]).sum(0)


def posed(data):
    return np.array([(transform(j, w) @ np.append(p, 1))[:3]
                     for p, j, w in zip(data['POSITION'], data['JOINTS_0'], data['WEIGHTS_0'])])


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def rays(triangles):
    a = triangles[:, 0]
    u, v = triangles[:, 1] - a, triangles[:, 2] - a
    determinant = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    valid = abs(determinant) > 1e-12
    inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)

    def intersect(point):
        delta = point - a
        bu = (delta[:, 0] * v[:, 1] - delta[:, 1] * v[:, 0]) * inverse
        bv = (u[:, 0] * delta[:, 1] - u[:, 1] * delta[:, 0]) * inverse
        z = a[:, 2] + bu * u[:, 2] + bv * v[:, 2]
        hits = valid & (bu >= -1e-5) & (bv >= -1e-5) & (bu + bv <= 1.00001)
        return z, np.column_stack([1 - bu - bv, bu, bv]), hits

    return intersect


selected = set(vertex for region in report['rear_leather_regions'][:3] for vertex in region)
selected.update(vertex for region in report['rear_tab_regions'] for vertex in region['vertices'])
selected.update(range(report['rear_strap_surface']['original_vertex_count'], len(original['POSITION'])))
selected = np.array(sorted(selected))
selected = selected[(original['POSITION'][selected, 1] > .551) & (original['POSITION'][selected, 1] < .623)]
strap_posed, plate_posed = posed(original), posed(plate)
strap_faces = faces[np.isin(faces, selected).any(1)]
strap_ray = rays(strap_posed[strap_faces])
triangles = plate_posed[plate_faces]
plate_ray = rays(triangles)
normal = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
normal *= np.where(normal[:, 2:3] > 0, -1, 1)
clearance = .001 / 1.8
contacts = []
removed = np.flatnonzero(np.isin(faces, selected).any(1))
new_values = {name: list(array) for name, array in original.items()}
new_faces, cache, normal_blends = [], {}, {}
source_points = list(original['POSITION'])


def weighted_joints(ids, bary):
    result = np.zeros(len(names))
    for vertex, fraction in zip(ids, bary):
        for joint, weight in zip(original['JOINTS_0'][vertex], original['WEIGHTS_0'][vertex]):
            result[joint] += fraction * weight
    return result


def pack(weights):
    joints = np.argsort(-weights)[:4]
    weights = np.maximum(weights[joints], 0)
    weights /= weights.sum()
    return np.where(weights > 0, joints, 0), weights


def emit(ids, bary):
    data = {name: bary @ array[ids] for name, array in original.items() if name not in ['JOINTS_0', 'WEIGHTS_0']}
    rest = data['POSITION'].copy()
    key = tuple(np.round(np.concatenate([rest, data['NORMAL'], data['TEXCOORD_0']]), 7))
    if key in cache:
        return cache[key]
    old_weights = weighted_joints(ids, bary)
    joints, weights = pack(old_weights)
    old_matrix = transform(joints, weights)
    world = (old_matrix @ np.append(rest, 1))[:3]
    blend = smooth((rest[1] - .551) / .007) * (1 - smooth((rest[1] - .613) / .009))
    z, plate_bary, hits = plate_ray(world)
    hits &= (z < -.015) & (abs(normal[:, 2]) > .35)
    candidates = np.flatnonzero(hits)
    if len(candidates) and blend > 0:
        face = candidates[np.argmin(z[candidates])]
        zs, _, leather_hits = strap_ray(world)
        leather_hits &= abs(zs - world[2]) < .02
        inner_z = max(world[2], zs[leather_hits].max()) if leather_hits.any() else world[2]
        layer = inner_z - world[2]
        target = world.copy()
        target[2] = z[face] - clearance / abs(normal[face, 2]) - layer
        joint_weights = old_weights * (1 - blend)
        for pv, fraction in zip(plate_faces[face], plate_bary[face]):
            for joint, weight in zip(plate['JOINTS_0'][pv], plate['WEIGHTS_0'][pv]):
                joint_weights[joint] += weight * fraction * blend
        joints, weights = pack(joint_weights)
        matrix = transform(joints, weights)
        data['POSITION'] = (np.linalg.inv(matrix) @ np.append(world + blend * (target - world), 1))[:3]
        if blend > .999999 and layer < 1e-7:
            contacts.append({'vertex': len(new_values['POSITION']), 'plate_vertices': plate_faces[face].tolist(), 'barycentric': plate_bary[face].tolist(), 'normal': normal[face].tolist(), 'gap': clearance})
    data['JOINTS_0'], data['WEIGHTS_0'] = joints, weights
    for name in ['NORMAL', 'TANGENT']:
        data[name][:3] /= np.linalg.norm(data[name][:3])
    data['TANGENT'][3] = -1 if data['TANGENT'][3] < 0 else 1
    index = len(new_values['POSITION'])
    for name, value in data.items():
        new_values[name].append(value)
    normal_blends[index] = blend if len(candidates) else 0
    source_points.append(rest)
    cache[key] = index
    return index


def subdivide(ids, bary):
    points = bary @ original['POSITION'][ids]
    lengths = [np.linalg.norm(points[i] - points[j]) for i, j in [(0, 1), (1, 2), (2, 0)]]
    edge = int(np.argmax(lengths))
    limit = .0035 if points[:, 1].max() > .588 else .007
    if lengths[edge] > limit:
        i, j = [(0, 1), (1, 2), (2, 0)][edge]
        k = 3 - i - j
        middle = (bary[i] + bary[j]) / 2
        subdivide(ids, np.array([bary[i], middle, bary[k]]))
        subdivide(ids, np.array([middle, bary[j], bary[k]]))
    else:
        new_faces.append([emit(ids, point) for point in bary])


for face in removed:
    subdivide(faces[face], np.eye(3))
new_points = np.array(new_values['POSITION'])
new_normals = np.zeros_like(new_points)
for face in new_faces:
    triangle = new_points[face]
    n = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
    for vertex in face:
        new_normals[vertex] += n
for vertex in range(len(original['POSITION']), len(new_points)):
    n = new_normals[vertex]
    if np.linalg.norm(n) < 1e-12:
        continue
    n /= np.linalg.norm(n)
    n = n * normal_blends[vertex] + new_values['NORMAL'][vertex] * (1 - normal_blends[vertex])
    n /= np.linalg.norm(n)
    new_values['NORMAL'][vertex] = n
    tangent = new_values['TANGENT'][vertex]
    tangent[:3] -= n * (n @ tangent[:3])
    tangent[:3] /= np.linalg.norm(tangent[:3])
for name, array in new_values.items():
    metadata = doc['accessors'][primitives[0]['attributes'][name]]
    index = add_accessor(doc, binary, np.array(array), metadata['type'], metadata['componentType'])
    primitives[0]['attributes'][name] = index
    doc['bufferViews'][doc['accessors'][index]['bufferView']]['target'] = 34962
indices = np.concatenate([np.delete(faces, removed, axis=0), new_faces]).astype('<u4')
primitives[0]['indices'] = add_accessor(doc, binary, indices.reshape(-1, 1), 'SCALAR', 5125)
doc['bufferViews'][doc['accessors'][primitives[0]['indices']]['bufferView']]['target'] = 34963
doc['buffers'][0]['byteLength'] = len(binary)
doc['nodes'][0]['extras']['fitting_version'] = 40
OUTPUT.mkdir(exist_ok=True)
np.save(OUTPUT / 'surface-source-positions.npy', np.array(source_points))
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Fit upper rear leather tabs, their connector detail, and lower strap transitions to the posed hip plates, preserving leather thickness with 1 mm inner clearance at 1.8 m character height.',
              upper_rear_strap_surface={'removed_faces': removed.tolist(), 'original_vertex_count': len(original['POSITION']), 'new_vertex_count': len(new_points), 'new_faces': new_faces, 'replaced_vertices': np.unique(faces[removed]).tolist(), 'contacts': contacts, 'clearance_m': .001, 'character_height_m': 1.8},
              triangles=sum(doc['accessors'][p['indices']]['count'] // 3 for p in primitives),
              preserved=['front straps', 'boot clips', 'plates', 'UVs', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'new_vertices': len(new_points) - len(original['POSITION']), 'triangles': report['triangles'], 'contacts': len(contacts)}))
