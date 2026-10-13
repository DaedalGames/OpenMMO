import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v33', DIRECTORY / 'fitted_v34'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '69b2bdde2e7496f670632d4ab967ac75951629f843dccddcd852d08fadd3d60b'
doc, binary = read_glb(source)
original_binary = bytes(binary)
binary = bytearray(binary)
primitives = doc['meshes'][0]['primitives']
plate = accessor(doc, binary, primitives[1]['attributes']['POSITION']).astype(float)
starts = [0, 412, 824, 1206, 1618, 2030]
ends = [412, 824, 1206, 1618, 2030, 2412]
profiles = {}
for panel, start in enumerate(starts):
    front = plate[start + 92:start + 105][::-1]
    profiles[panel] = PchipInterpolator(front[:, 1], np.column_stack((abs(front[:, 0]), front[:, 2])))


def deform(points, panel):
    result = points.copy()
    x, height, z = points.T
    center = -.004 + .1 * (height - .525)
    angle = np.arctan2((z - center) / .092, abs(x) / .124)
    old_edge = profiles[panel](height)
    edge_angle = np.arctan2((old_edge[:, 1] - center) / .092, old_edge[:, 0] / .124)
    t = np.clip((angle - .25) / (edge_angle - .25), 0, 1)
    influence = t * t * (3 - 2 * t)
    fraction = (.62996 - height) / (.62996 - .475)
    width = .03256 + (.091 - .03256) * (.15 * fraction + .85 * fraction ** 2)
    depth = .044 + .06 * fraction - .05028 * fraction ** 2
    result[:, 0] += np.sign(x) * influence * (width - old_edge[:, 0])
    result[:, 2] += influence * (depth - old_edge[:, 1])
    return result


changes, edge_records = [], []
written = set()
for index in [1, 2, 3]:
    attrs = primitives[index]['attributes']
    points = accessor(doc, original_binary, attrs['POSITION']).astype(float)
    normals = accessor(doc, original_binary, attrs['NORMAL']).astype(float)
    tangent = accessor(doc, original_binary, attrs['TANGENT']).astype(float) if 'TANGENT' in attrs else None
    result, new_normals = points.copy(), normals.copy()
    new_tangent = tangent.copy() if tangent is not None else None
    if index in [1, 3]:
        panels = [np.arange(start, end) for start, end in zip(starts, ends)]
    else:
        panels = []
        for side in [-1, 1]:
            for level in range(3):
                low, high = [( .58, 1), (.53, .58), (0, .53)][level]
                panels.append(np.flatnonzero((points[:, 0] * side > 0) & (points[:, 1] > low) & (points[:, 1] <= high)))
    determinants = []
    for panel, vertices in enumerate(panels):
        original = points[vertices]
        moved = deform(original, panel)
        active = np.linalg.norm(moved - original, axis=1) > 1e-10
        selected = vertices[active]
        if not len(selected):
            continue
        original = points[selected]
        jacobian = np.stack([(deform(original + axis * 1e-6, panel) - deform(original - axis * 1e-6, panel)) / 2e-6 for axis in np.eye(3)], axis=2)
        determinants.extend(np.linalg.det(jacobian))
        assert np.linalg.det(jacobian).min() > .05
        result[selected] = deform(original, panel)
        normal = np.linalg.solve(jacobian.transpose(0, 2, 1), normals[selected, :, None])[:, :, 0]
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        new_normals[selected] = normal
        if tangent is not None:
            direction = np.einsum('nij,nj->ni', jacobian, tangent[selected, :3])
            direction -= normal * (direction * normal).sum(1, keepdims=True)
            direction /= np.linalg.norm(direction, axis=1, keepdims=True)
            new_tangent[selected, :3] = direction
    if index == 2:
        result, new_normals = points.copy(), normals.copy()
        faces = accessor(doc, original_binary, primitives[index]['indices']).reshape(-1, 3)
        parents = np.arange(len(points))

        def root(vertex):
            while parents[vertex] != vertex:
                parents[vertex] = parents[parents[vertex]]
                vertex = parents[vertex]
            return vertex

        for face in faces:
            for vertex in face[1:]:
                parents[root(vertex)] = root(face[0])
        used = np.unique(faces)
        labels = np.array([root(vertex) for vertex in used])
        for label in np.unique(labels):
            vertices = used[labels == label]
            center = points[vertices].mean(0)
            panel = (0 if center[0] < 0 else 3) + (0 if center[1] > .58 else 1 if center[1] > .53 else 2)
            moved = deform(center[None], panel)[0]
            if np.linalg.norm(moved - center) < 1e-10:
                continue
            jacobian = np.column_stack([(deform((center + axis * 1e-6)[None], panel)[0] - deform((center - axis * 1e-6)[None], panel)[0]) / 2e-6 for axis in np.eye(3)])
            u, _, vh = np.linalg.svd(jacobian)
            rotation = u @ vh
            assert np.linalg.det(rotation) > .999
            result[vertices] = moved + (points[vertices] - center) @ rotation.T
            new_normals[vertices] = normals[vertices] @ rotation.T
    selected = np.flatnonzero(np.linalg.norm(result - points, axis=1) > 1e-10)
    values = {'POSITION': result, 'NORMAL': new_normals}
    if tangent is not None:
        values['TANGENT'] = new_tangent
    for name, data in values.items():
        attribute = attrs[name]
        if attribute in written:
            continue
        metadata = doc['accessors'][attribute]
        view = doc['bufferViews'][metadata['bufferView']]
        values32 = data.astype('<f4')
        assert view.get('byteStride', values32.shape[1] * 4) == values32.shape[1] * 4
        offset = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
        binary[offset:offset + values32.nbytes] = values32.tobytes()
        if name == 'POSITION':
            metadata.update(min=values32.min(0).tolist(), max=values32.max(0).tolist())
        written.add(attribute)
    changes.append({'primitive': index, 'vertices': selected.tolist(), 'maximum_displacement': float(np.linalg.norm(result-points, axis=1).max()), 'minimum_jacobian_determinant': float(min(determinants))})
    if index == 1:
        for panel, start in enumerate(starts):
            ids = list(range(start + 92, start + 105))
            edge_records.append({'side': -1 if panel < 3 else 1, 'level': panel % 3, 'vertices': ids, 'before': points[ids].tolist(), 'after': result[ids].tolist()})

doc['nodes'][0]['extras']['fitting_version'] = 34
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.pop('rear_plate_changes', None)
report.pop('rear_guard_replacement', None)
report.pop('rear_guard_translation', None)
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Fair both front plate edges with continuous quadratic width and depth profiles. Blend the displacement into each side shell, transform shading frames, and carry rivets rigidly.',
              front_plate_changes=changes, front_edge_vertices=edge_records,
              preserved=['all leather and UV fixes', 'guards', 'rear plates', 'topology', 'UVs', 'weights', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256':report['sha256'], 'changes': [{k: len(v) if k == 'vertices' else v for k,v in entry.items()} for entry in changes]}))
