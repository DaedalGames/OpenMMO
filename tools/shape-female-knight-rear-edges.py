import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator, interp1d

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v26', DIRECTORY / 'fitted_v27'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '3a06960a0bf90a1d4daea0992e6b05865ff07b71aaeac52e1a6ca0f038be86b5'
doc, binary = read_glb(source)
original_binary = bytes(binary)
binary = bytearray(binary)
primitives = doc['meshes'][0]['primitives']
plate = accessor(doc, binary, primitives[1]['attributes']['POSITION']).astype(float)
starts = [0, 412, 824, 1206, 1618, 2030]
ends = [412, 824, 1206, 1618, 2030, 2412]
profiles = {}
for panel, start in enumerate(starts):
    rear, front = plate[start:start + 4], plate[start + 92:start + 105]
    assert np.all(rear[:, 2] < 0) and np.all(front[:, 2] > 0)
    heights = rear[::-1, 1]
    target_heights = heights.copy()
    if panel % 3 == 1:
        target_heights[1:3] = [.52976, .55264]
    elif panel % 3 == 2:
        target_heights[1:3] = [.495, .516]
    center = -.004 + .1 * (rear[:, 1] - .525)
    angle = np.arctan2((rear[:, 2] - center) / .092, abs(rear[:, 0]) / .124)
    radius = np.hypot(rear[:, 0] / .124, (rear[:, 2] - center) / .092)
    profiles[panel] = (
        interp1d(heights, target_heights, fill_value='extrapolate'),
        PchipInterpolator(front[::-1, 1], abs(front[::-1, 0])),
        PchipInterpolator(heights, angle[::-1]),
        PchipInterpolator(heights, radius[::-1]),
    )


def deform(points, panel):
    result = points.copy()
    x, height, z = points.T
    center = -.004 + .1 * (height - .525)
    angle = np.arctan2((z - center) / .092, abs(x) / .124)
    radius = np.hypot(x / .124, (z - center) / .092)
    active = angle < -.4
    if not np.any(active):
        return result
    move_height, width, edge_angle, edge_radius = profiles[panel]
    edge = edge_angle(height)
    t = np.clip((-angle - .4) / (-edge - .4), 0, 1)
    influence = t * t * (3 - 2 * t)
    new_height = height + influence * (move_height(height) - height)
    target_width = width(np.clip(new_height, width.x[0], width.x[-1]))
    target_angle = -np.arccos(np.clip(target_width / (.124 * edge_radius(height)), .01, .99))
    adjusted = angle + influence * (target_angle - edge)
    result[active, 0] = np.sign(x[active]) * .124 * radius[active] * np.cos(adjusted[active])
    result[active, 1] = new_height[active]
    result[active, 2] = -.004 + .1 * (new_height[active] - .525) + .092 * radius[active] * np.sin(adjusted[active])
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
            ids = list(range(start, start + 4))
            edge_records.append({'side': -1 if panel < 3 else 1, 'level': panel % 3, 'vertices': ids, 'before': points[ids].tolist(), 'after': result[ids].tolist()})

doc['nodes'][0]['extras']['fitting_version'] = 27
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Match rear inner plate edges to the existing front width profiles, with a late middle-plate corner and flared lower hem. Redistribute rear rows and rotate along the fitted elliptical shell; carry seams and rear rivets with the deformation.',
              rear_plate_changes=changes, rear_edge_vertices=edge_records,
              preserved=['all leather and UV fixes', 'guards', 'front plates', 'topology', 'UVs', 'weights', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256':report['sha256'], 'changes': [{k: len(v) if k == 'vertices' else v for k,v in entry.items()} for entry in changes]}))
