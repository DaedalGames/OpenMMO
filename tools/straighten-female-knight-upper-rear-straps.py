import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v40', DIRECTORY / 'fitted_v41'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '92bc4eff66a88567164c779723b887d94dfd72ba079cff61e4e8208e981058f3'
doc, binary = read_glb(source)
binary = bytearray(binary)
report = json.loads((SOURCE / 'fitting.json').read_text())
primitive = doc['meshes'][0]['primitives'][0]
original = {name: accessor(doc, binary, index) for name, index in primitive['attributes'].items()}
values = {name: array.copy() for name, array in original.items()}
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
parameters = np.load(SOURCE / 'surface-source-positions.npy')
assert parameters.shape == original['POSITION'].shape
names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
matrices = np.repeat(np.eye(4)[None], len(names), axis=0)
pose = json.loads((DIRECTORY / 'fitted_v37/strap-poses.json').read_text())[1]
for name, matrix in zip(['Hips', 'LeftUpLeg', 'RightUpLeg'], pose['matrices']):
    matrices[names.index(name)] = np.array(matrix).reshape(4, 4).T
skin = (matrices[original['JOINTS_0']] * original['WEIGHTS_0'][:, :, None, None]).sum(1)
world = np.einsum('vij,vj->vi', skin, np.column_stack([original['POSITION'], np.ones(len(parameters))]))[:, :3]
new_world = world.copy()
used = np.unique(faces)
upper_start = report['upper_rear_strap_surface']['original_vertex_count']
bottom, top = .575, .623
records, changed, blends = [], [], {}
plate = doc['meshes'][0]['primitives'][1]
plate_attrs = {name: accessor(doc, binary, index) for name, index in plate['attributes'].items()}
plate_skin = (matrices[plate_attrs['JOINTS_0']] * plate_attrs['WEIGHTS_0'][:, :, None, None]).sum(1)
plate_world = np.einsum('vij,vj->vi', plate_skin, np.column_stack([plate_attrs['POSITION'], np.ones(len(plate_skin))]))[:, :3]
plate_faces = accessor(doc, binary, plate['indices']).reshape(-1, 3)
plate_triangles = plate_world[plate_faces]
pa = plate_triangles[:, 0]
pu, pv = plate_triangles[:, 1] - pa, plate_triangles[:, 2] - pa
pd = pu[:, 0] * pv[:, 1] - pu[:, 1] * pv[:, 0]
pinv = np.divide(1, pd, out=np.zeros_like(pd), where=abs(pd) > 1e-12)
pn = np.cross(pu, pv)
pn /= np.maximum(np.linalg.norm(pn, axis=1, keepdims=True), 1e-12)


def plate_hit(point):
    delta = point - pa
    bu = (delta[:, 0] * pv[:, 1] - delta[:, 1] * pv[:, 0]) * pinv
    bv = (pu[:, 0] * delta[:, 1] - pu[:, 1] * delta[:, 0]) * pinv
    z = pa[:, 2] + bu * pu[:, 2] + bv * pv[:, 2]
    hits = np.flatnonzero((abs(pd) > 1e-12) & (bu >= 0) & (bv >= 0) & (bu + bv <= 1) & (z < -.015))
    if not len(hits):
        return None
    face = hits[np.argmin(z[hits])]
    return z[face], abs(pn[face, 2])



def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def weights_at(ids, bary):
    weights = np.zeros(len(names))
    for vertex, fraction in zip(ids, bary):
        for joint, weight in zip(original['JOINTS_0'][vertex], original['WEIGHTS_0'][vertex]):
            weights[joint] += weight * fraction
    return weights


for side in [-1, 1]:
    selected = used[(used >= upper_start) & (parameters[used, 0] * side > 0)]
    side_faces = faces[np.isin(faces, selected).all(1)]
    triangles = parameters[side_faces]
    a = triangles[:, 0]
    u, v = triangles[:, 1] - a, triangles[:, 2] - a
    det = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    inv = np.divide(1, det, out=np.zeros_like(det), where=abs(det) > 1e-12)

    def bounds(height):
        crossings = []
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            lo, hi = triangles[:, i], triangles[:, j]
            mask = ((lo[:, 1] <= height) & (hi[:, 1] >= height) | (hi[:, 1] <= height) & (lo[:, 1] >= height)) & (abs(hi[:, 1] - lo[:, 1]) > 1e-12)
            t = (height - lo[mask, 1]) / (hi[mask, 1] - lo[mask, 1])
            crossings.extend((lo[mask] + t[:, None] * (hi[mask] - lo[mask]))[:, 0])
        return min(crossings), max(crossings)

    def surface(x, y):
        delta = np.array([x, y, 0]) - a
        bu = (delta[:, 0] * v[:, 1] - delta[:, 1] * v[:, 0]) * inv
        bv = (u[:, 0] * delta[:, 1] - u[:, 1] * delta[:, 0]) * inv
        z = a[:, 2] + bu * u[:, 2] + bv * v[:, 2]
        hits = np.flatnonzero((abs(det) > 1e-12) & (bu >= -1e-5) & (bv >= -1e-5) & (bu + bv <= 1.00001))
        if not len(hits):
            return None
        face = hits[np.argmax(z[hits])]
        bary = np.array([1 - bu[face] - bv[face], bu[face], bv[face]])
        return z[face], bary @ world[side_faces[face]], weights_at(side_faces[face], bary)

    endpoints, widths, directions, end_weights = [], [], [], []
    for height in [bottom, top]:
        xmin, xmax = bounds(height)
        center = (xmin + xmax) / 2
        sample = surface(center, height)
        assert sample is not None
        endpoints.append(sample[1])
        end_weights.append(sample[2])
        left, right = surface(xmin + .0002, height), surface(xmax - .0002, height)
        direction = right[1] - left[1]
        widths.append(np.linalg.norm(direction) + .0004)
        directions.append(direction / np.linalg.norm(direction))
    low, high = endpoints
    along = high - low
    along /= np.linalg.norm(along)
    across = directions[1].copy()
    across -= along * (along @ across)
    across /= np.linalg.norm(across)
    offset = 0.
    for t in np.linspace(0, .95, 80):
        width = widths[0] * (1 - t) + widths[1] * t
        for lateral in np.linspace(-.5, .5, 17):
            point = low * (1 - t) + high * t + across * lateral * width
            hit = plate_hit(point)
            if hit is not None:
                z, nz = hit
                offset = max(offset, (point[2] - z + .001 / 1.8 / max(nz, .2)) / (1 - t))
    low[2] -= offset
    along = high - low
    along /= np.linalg.norm(along)
    outward = np.cross(across, along)
    outward /= np.linalg.norm(outward)
    outward *= -1 if outward[2] > 0 else 1
    samples = []
    for vertex in selected:
        p = parameters[vertex]
        if not .561 < p[1] < top:
            continue
        actual_bounds = bounds(p[1])
        center_x = sum(actual_bounds) / 2
        lateral = (p[0] - center_x) / (actual_bounds[1] - actual_bounds[0])
        inner = surface(p[0], p[1])
        if inner is None:
            layer = .001
        else:
            layer = np.clip(inner[0] - p[2], 0, .005)
        t = (p[1] - bottom) / (top - bottom)
        width = widths[0] * (1 - t) + widths[1] * t
        target = low * (1 - t) + high * t + across * lateral * width + outward * layer
        blend = smooth((p[1] - .561) / (bottom - .561))
        if p[1] > .621:
            blend *= 1 - smooth((p[1] - .621) / .002)
        new_world[vertex] = world[vertex] * (1 - blend) + target * blend
        weights = weights_at([vertex], [1]) * (1 - blend) + (end_weights[0] * (1 - np.clip(t, 0, 1)) + end_weights[1] * np.clip(t, 0, 1)) * blend
        joints = np.argsort(-weights)[:4]
        weights = np.maximum(weights[joints], 0)
        weights /= weights.sum()
        joints = np.where(weights > 0, joints, 0)
        matrix = (matrices[joints] * weights[:, None, None]).sum(0)
        values['POSITION'][vertex] = np.linalg.solve(matrix, np.append(new_world[vertex], 1))[:3]
        values['JOINTS_0'][vertex], values['WEIGHTS_0'][vertex] = joints, weights
        changed.append(int(vertex))
        blends[int(vertex)] = blend
        if blend == 1:
            samples.append({'vertex': int(vertex), 't': float(t), 'lateral': float(lateral), 'width': float(width), 'layer': float(layer)})
    records.append({'side': side, 'bottom': low.tolist(), 'top': high.tolist(), 'across': across.tolist(), 'outward': outward.tolist(), 'widths': widths, 'outward_lower_endpoint_offset': offset, 'samples': samples})

changed_set = set(changed)
accumulated = np.zeros_like(world)
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
doc['nodes'][0]['extras']['fitting_version'] = 41
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(source=str(source.relative_to(ROOT)), source_sha256=source_hash, output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Straighten both rear leather straps from the waist through the second buckle into tapered planar ribbons in the idle reference pose, blending into the existing waist and lower straps.',
              straight_upper_rear_straps={'vertices': changed, 'regions': records},
              preserved=['front straps', 'boot clips', 'plates', 'topology', 'UVs', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'changed_vertices': len(changed)}))
