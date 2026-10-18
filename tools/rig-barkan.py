import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/monsters/barkan/tripo_v2/wing_holes.glb'
DONOR = ROOT / 'assets/modular_human_male_01/fitted/base.glb'
OUT = ROOT / 'assets/monsters/barkan/rig_v1'
RIG_ID = 'barkan_meters_v1'


def world_matrices(doc):
    result = {}
    def visit(index, parent):
        node = doc['nodes'][index]
        if 'matrix' in node:
            matrix = np.asarray(node['matrix']).reshape(4, 4).T
        else:
            matrix = np.eye(4)
            matrix[:3, :3] = Rotation.from_quat(node.get('rotation', [0, 0, 0, 1])).as_matrix() @ np.diag(node.get('scale', [1, 1, 1]))
            matrix[:3, 3] = node.get('translation', [0, 0, 0])
        result[index] = parent @ matrix
        for child in node.get('children', []):
            visit(child, result[index])
    for index in doc['scenes'][0]['nodes']:
        visit(index, np.eye(4))
    return result


def landmarks():
    points = dict(Hips=[0, 1.12, -.02], Spine=[0, 1.30, -.01],
                  Spine1=[0, 1.48, -.015], Spine2=[0, 1.68, -.02],
                  Neck=[0, 1.91, .015], Head=[0, 2.055, .045],
                  HeadTop_End=[0, 2.175, .035])
    left = dict(UpLeg=[.205, 1.075, -.02], Leg=[.285, .67, -.015],
                Foot=[.36, .15, -.09], ToeBase=[.38, .065, .18],
                Toe_End=[.39, .035, .35], Shoulder=[.095, 1.84, -.025],
                Arm=[.335, 1.745, .005], ForeArm=[.64, 1.645, .035],
                Hand=[.965, 1.615, .005])
    fingers = {
        'Index': ([1.09, 1.645, .032], [1.249, 1.588, .041]),
        'Middle': ([1.095, 1.646, -.041], [1.269, 1.570, -.039]),
        'Ring': ([1.08, 1.620, -.120], [1.207, 1.548, -.121]),
        'Pinky': ([1.065, 1.635, -.133], [1.195, 1.600, -.145]),
        'Thumb': ([1.015, 1.575, .070], [1.118, 1.512, .067]),
    }
    for finger, (start, end) in fingers.items():
        for index, t in enumerate([0, .38, .72, 1], 1):
            left[f'Hand{finger}{index}'] = (np.array(start) * (1 - t) + np.array(end) * t).tolist()
    for name, point in left.items():
        points['Left' + name] = point
        points['Right' + name] = [-point[0], point[1], point[2]]
    right = {
        'Index': ([-1.09, 1.645, .059], [-1.237, 1.588, .068]),
        'Middle': ([-1.095, 1.646, -.012], [-1.258, 1.570, -.012]),
        'Ring': ([-1.08, 1.620, -.094], [-1.198, 1.548, -.095]),
        'Thumb': ([-1.015, 1.575, .095], [-1.105, 1.512, .091]),
    }
    for finger, (start, end) in right.items():
        for index, t in enumerate([0, .38, .72, 1], 1):
            points[f'RightHand{finger}{index}'] = (np.array(start) * (1 - t) + np.array(end) * t).tolist()
    return {name: np.asarray(point, dtype=float) for name, point in points.items()}


def wing_landmarks():
    points = {
        'WingRoot': [.16, 1.73, -.27],
        'WingArm': [.38, 2.02, -.43],
        'WingWrist': [.625, 2.43, -.75],
        'WingHook_End': [.47, 2.405, -.78],
    }
    for index, (middle, tip) in enumerate([
        ([.97, 2.13, -1.14], [1.26, 1.69, -1.43]),
        ([.865, 2.01, -.96], [1.005, 1.65, -1.09]),
        ([.72, 1.99, -.70], [.77, 1.52, -.79]),
        ([.52, 1.94, -.46], [.48, 1.46, -.46]),
    ], 1):
        points[f'WingFinger{index}'] = points['WingWrist']
        points[f'WingFinger{index}Mid'] = middle
        points[f'WingFinger{index}_End'] = tip
    parents = {'WingRoot': 'Spine2', 'WingArm': 'WingRoot', 'WingWrist': 'WingArm',
               'WingHook_End': 'WingWrist'}
    for index in range(1, 5):
        parents[f'WingFinger{index}'] = 'WingArm'
        parents[f'WingFinger{index}Mid'] = f'WingFinger{index}'
        parents[f'WingFinger{index}_End'] = f'WingFinger{index}Mid'
    result, relationships = {}, {}
    for side, sign in [('Left', 1), ('Right', -1)]:
        for name, point in points.items():
            result[side + name] = np.asarray(point, dtype=float) * [sign, 1, 1]
            parent = parents[name]
            relationships[side + name] = parent if parent == 'Spine2' else side + parent
    return result, relationships


def chain_landmarks():
    points, parents = {}, {}
    for side, sign in [('Left', 1), ('Right', -1)]:
        for name, point, parent in [
            ('WristChain', [.865, 1.59, -.015], 'ForeArm'),
            ('WristChainMid', [.865, 1.40, -.015], 'WristChain'),
            ('WristChain_End', [.865, 1.22, -.015], 'WristChainMid'),
        ]:
            points[side + name] = np.asarray(point) * [sign, 1, 1]
            parents[side + name] = side + parent
    return points, parents


def rotate_between(before, after):
    a, b = before / np.linalg.norm(before), after / np.linalg.norm(after)
    cross = np.cross(a, b)
    sine = np.linalg.norm(cross)
    return Rotation.from_rotvec(cross / sine * np.arctan2(sine, a @ b)).as_matrix() if sine > 1e-9 else np.eye(3)


def wing_fraction(points):
    threshold = .25 + .18 * np.exp(-(abs(points[:, 0]) / .45) ** 4)
    amount = np.clip((-points[:, 2] - threshold + .025) / .07, 0, 1)
    return amount * (points[:, 1] > 1.40)


def distance_to_segment(points, start, end):
    vector = end - start
    t = np.clip((points - start) @ vector / (vector @ vector), 0, 1)
    return np.linalg.norm(points - start - t[:, None] * vector, axis=1)


def transfer_body_weights(donor, binary, old_world, new_world, names, positions, children, points):
    ids = donor['skins'][0]['joints']
    donor_names = [donor['nodes'][index]['name'] for index in ids]
    warped, surfaces = [], []
    transforms = []
    for index, name in zip(ids, donor_names):
        targets = [child for child in children[name] if 'Wing' not in child]
        primary = {'Hips': 'Spine', 'Spine2': 'Neck', 'LeftHand': 'LeftHandMiddle1', 'RightHand': 'RightHandMiddle1'}.get(name)
        child = primary or (targets[0] if targets else None)
        rotation = new_world[name][:3, :3] @ old_world[index][:3, :3].T
        width = 1.5 if name in ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head'] else 1.4
        stretch = np.eye(3) * width
        if child:
            old_child = ids[donor_names.index(child)]
            before = old_world[old_child][:3, 3] - old_world[index][:3, 3]
            after = positions[child] - positions[name]
            axis = before / np.linalg.norm(before)
            stretch += (np.linalg.norm(after) / np.linalg.norm(before) - width) * np.outer(axis, axis)
        matrix = np.eye(4)
        matrix[:3, :3] = rotation @ stretch
        matrix[:3, 3] = positions[name] - matrix[:3, :3] @ old_world[index][:3, 3]
        transforms.append(matrix)
    for node in donor['nodes']:
        if 'mesh' not in node or 'skin' not in node:
            continue
        for primitive in donor['meshes'][node['mesh']]['primitives']:
            attributes = primitive['attributes']
            vertices = accessor(donor, binary, attributes['POSITION'])
            joints = accessor(donor, binary, attributes['JOINTS_0'])
            weights = accessor(donor, binary, attributes['WEIGHTS_0'])
            used = np.unique(accessor(donor, binary, primitive['indices']))
            result = np.zeros_like(vertices, dtype=float)
            dense = np.zeros((len(vertices), len(names)))
            for k in range(4):
                for joint in np.unique(joints[:, k]):
                    mask = joints[:, k] == joint
                    matrix = transforms[int(joint)]
                    result[mask] += (vertices[mask] @ matrix[:3, :3].T + matrix[:3, 3]) * weights[mask, k, None]
                    dense[mask, names.index(donor_names[int(joint)])] += weights[mask, k]
            warped.append(result[used])
            surfaces.append(dense[used])
    vertices, weights = np.concatenate(warped), np.concatenate(surfaces)
    distance, nearest = cKDTree(vertices).query(points, k=8)
    blend = 1 / np.maximum(distance, .003) ** 3
    blend /= blend.sum(1, keepdims=True)
    dense = np.einsum('nk,nkj->nj', blend, weights[nearest])
    return dense, distance[:, 0]


def finish_weights(points, dense, names, positions, children):
    wing = wing_fraction(points)
    for side, sign in [('Left', 1), ('Right', -1)]:
        side_mask = points[:, 0] * sign > 0
        indices = np.flatnonzero(side_mask & (wing > 0))
        segments = [name for name in names if name.startswith(side + 'Wing') and children.get(name)]
        distances = np.column_stack([
            distance_to_segment(points[indices], positions[name], positions[children[name][0]])
            for name in segments
        ])
        weights = 1 / np.maximum(distances, .025) ** 3
        weights /= weights.sum(1, keepdims=True)
        dense[indices] *= 1 - wing[indices, None]
        for index, name in enumerate(segments):
            dense[indices, names.index(name)] += weights[:, index] * wing[indices]
        x, y, z = points[:, 0] * sign, points[:, 1], points[:, 2]
        def rigid(mask, name):
            mask &= side_mask & (wing == 0)
            dense[mask] = 0
            dense[mask, names.index(side + name)] = 1
        rigid((x > .77) & (x < .96) & (y > 1.13) & (y < 1.56), 'WristChain')
        chain = np.flatnonzero(side_mask & (wing == 0) & (x > .77) & (x < .96) & (y > 1.13) & (y < 1.56))
        bend = np.clip((1.44 - y[chain]) / .08, 0, 1)
        dense[chain, names.index(side + 'WristChain')] = 1 - bend
        dense[chain, names.index(side + 'WristChainMid')] = bend
        rigid((x > .75) & (x < .95) & (y >= 1.56) & (z > -.18), 'ForeArm')
        rigid((x >= .98) & (x < 1.065) & (y > 1.55) & (z > -.18), 'Hand')
        rigid((x > .18) & (x < .52) & (y > 1.72) & (y < 1.98) & (z > -.36), 'Shoulder')
        finger_mask = side_mask & (wing == 0) & ((x > 1.06) | ((x > .995) & (y < 1.59) & (z > .04))) & (y > 1.48) & (z > -.22)
        finger_indices = np.flatnonzero(finger_mask)
        groups = ['Thumb', 'Index', 'Middle', 'Ring']
        distances = np.column_stack([
            distance_to_segment(points[finger_indices], positions[side + 'Hand' + finger + '1'],
                                positions[side + 'Hand' + finger + '4']) for finger in groups
        ])
        chosen = distances.argmin(1)
        for index, finger in enumerate(groups):
            subset = finger_indices[chosen == index]
            segments = [side + 'Hand' + finger + str(i) for i in range(1, 4)]
            distances = np.column_stack([
                distance_to_segment(points[subset], positions[name], positions[children[name][0]])
                for name in segments
            ])
            weights = 1 / np.maximum(distances, .006) ** 4
            weights /= weights.sum(1, keepdims=True)
            blend = np.clip((x[subset] - (1.005 if finger == 'Thumb' else 1.065)) / .045, 0, 1)
            dense[subset] = 0
            dense[subset, names.index(side + 'Hand')] = 1 - blend
            for joint, name in enumerate(segments):
                dense[subset, names.index(name)] = weights[:, joint] * blend
    head = (wing == 0) & (points[:, 1] > 1.98) & (abs(points[:, 0]) < .40) & (points[:, 2] > -.35)
    dense[head] = 0
    dense[head, names.index('Head')] = 1
    waist = (points[:, 1] > 1.03) & (points[:, 1] < 1.24) & (abs(points[:, 0]) < .38)
    dense[waist] = 0
    dense[waist, names.index('Hips')] = 1
    return dense, wing


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    doc, binary = read_glb(SOURCE)
    binary = bytearray(binary)
    donor, donor_binary = read_glb(DONOR)
    old_world = world_matrices(donor)
    source_world = world_matrices(doc)
    mesh_node = next(i for i, node in enumerate(doc['nodes']) if 'mesh' in node)
    primitive = doc['meshes'][0]['primitives'][0]
    source_rotation = Rotation.from_euler('y', -90, degrees=True).as_matrix() @ source_world[mesh_node][:3, :3]
    points = accessor(doc, binary, primitive['attributes']['POSITION']) @ source_rotation.T
    factor = 2.5 / np.ptp(points[:, 1])
    offset = np.array([0, -points[:, 1].min() * factor, -.54])
    points = points * factor + offset
    primitive['attributes']['POSITION'] = add_accessor(doc, binary, points, 'VEC3')
    normals = accessor(doc, binary, primitive['attributes']['NORMAL']) @ source_rotation.T
    primitive['attributes']['NORMAL'] = add_accessor(doc, binary, normals, 'VEC3')
    if 'TANGENT' in primitive['attributes']:
        tangents = accessor(doc, binary, primitive['attributes']['TANGENT'])
        tangents[:, :3] = tangents[:, :3] @ source_rotation.T
        primitive['attributes']['TANGENT'] = add_accessor(doc, binary, tangents, 'VEC4')
    doc['nodes'][mesh_node] = {'name': 'Barkan', 'mesh': 0, 'skin': 0, 'extras': {'rig_id': RIG_ID}}
    ids = donor['skins'][0]['joints']
    names = [donor['nodes'][i]['name'] for i in ids]
    positions = landmarks()
    parents = {donor['nodes'][c]['name']: donor['nodes'][i]['name'] for i in ids
               for c in donor['nodes'][i].get('children', []) if c in ids}
    wing_points, wing_parents = wing_landmarks()
    chain_points, chain_parents = chain_landmarks()
    positions.update(wing_points)
    positions.update(chain_points)
    parents.update(wing_parents)
    parents.update(chain_parents)
    names.extend(wing_points)
    names.extend(chain_points)
    children = {name: [child for child in names if parents.get(child) == name] for name in names}
    new_world = {}
    for index in ids:
        name = donor['nodes'][index]['name']
        targets = children[name]
        primary = {'Hips': 'Spine', 'Spine2': 'Neck', 'LeftHand': 'LeftHandMiddle1', 'RightHand': 'RightHandMiddle1'}.get(name)
        child = primary or (targets[0] if targets else None)
        rotation = old_world[index][:3, :3]
        if child is not None:
            old_child = next(i for i in ids if donor['nodes'][i]['name'] == child)
            rotation = rotate_between(old_world[old_child][:3, 3] - old_world[index][:3, 3], positions[child] - positions[name]) @ rotation
        new_world[name] = np.eye(4)
        new_world[name][:3, :3] = rotation
        new_world[name][:3, 3] = positions[name]
    for name in [*wing_points, *chain_points]:
        targets = children[name]
        child = ('LeftWingHook_End' if name == 'LeftWingWrist' else 'RightWingHook_End') if name.endswith('WingWrist') else (targets[0] if targets else None)
        direction = positions[child] - positions[name] if child else np.array([0, .05, 0])
        matrix = np.eye(4)
        matrix[:3, :3] = rotate_between(np.array([0, 1, 0]), direction)
        matrix[:3, 3] = positions[name]
        new_world[name] = matrix
    mapping = {name: len(doc['nodes']) + index for index, name in enumerate(names)}
    for name in names:
        parent = parents.get(name)
        local = np.linalg.inv(new_world[parent]) @ new_world[name] if parent else new_world[name]
        node = {'name': name, 'translation': local[:3, 3].tolist(), 'rotation': Rotation.from_matrix(local[:3, :3]).as_quat().tolist()}
        if children[name]:
            node['children'] = [mapping[child] for child in children[name]]
        doc['nodes'].append(node)
    armature = len(doc['nodes'])
    doc['nodes'].append({'name': 'Armature', 'children': [mapping['Hips']], 'extras': {'rig_id': RIG_ID, 'height_m': 2.5, 'runtime_scale': 1}})
    doc['scenes'] = [{'nodes': [mesh_node, armature], 'extras': {'rig_id': RIG_ID, 'units': 'meters'}}]
    inverse = np.asarray([np.linalg.inv(new_world[name]).T.reshape(16) for name in names])
    doc['skins'] = [{'joints': list(mapping.values()), 'inverseBindMatrices': add_accessor(doc, binary, inverse, 'MAT4'), 'skeleton': mapping['Hips']}]
    count = len(points)
    joints = np.zeros((count, 4), dtype=np.uint16)
    weights = np.zeros((count, 4)); weights[:, 0] = 1
    primitive['attributes']['JOINTS_0'] = add_accessor(doc, binary, joints, 'VEC4', 5123)
    primitive['attributes']['WEIGHTS_0'] = add_accessor(doc, binary, weights, 'VEC4')
    dense, distance = transfer_body_weights(donor, donor_binary, old_world, new_world, names, positions, children, points)
    dense, wing = finish_weights(points, dense, names, positions, children)
    assert np.isfinite(dense).all() and (dense.sum(1) > 0).all()
    joints = np.argsort(dense, axis=1)[:, -4:][:, ::-1]
    weights = np.take_along_axis(dense, joints, axis=1)
    weights /= weights.sum(1, keepdims=True)
    joints[weights == 0] = 0
    for attribute, values, component in [('JOINTS_0', joints, 5123), ('WEIGHTS_0', weights, 5126)]:
        primitive['attributes'][attribute] = add_accessor(doc, binary, values, 'VEC4', component)
        view = doc['accessors'][primitive['attributes'][attribute]]['bufferView']
        doc['bufferViews'][view]['target'] = 34962
    doc['buffers'][0]['byteLength'] = len(binary)
    output = OUT / 'barkan.glb'
    write_glb(output, doc, binary)
    report = {
        'date': '2026-10-18', 'rig_id': RIG_ID, 'height_m': 2.5,
        'height_definition': 'Ground to highest horn/wing point in the bind pose',
        'units': 'meters', 'runtime_scale': 1,
        'geometry_scale_baked_before_binding': factor, 'geometry_offset_m': offset.tolist(),
        'sources': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in [SOURCE, DONOR]],
        'method': 'Locally fitted Mixamo-compatible human hierarchy; existing body weights transferred through a proportion-fitted donor surface; fitted fingers and independent wing chains',
        'rejected_attempt': 'Voxel proxy bone-heat binding failed to find a solution for this surface; no geometry from that proxy is retained.',
        'source_conditions': 'Existing Tripo and concept source/license records apply. Existing project Mixamo skeleton reused; local processing, no paid generation.',
        'joints': len(names), 'humanoid_joints': len(ids), 'wing_joints': len(wing_points),
        'chain_joints': len(chain_points),
        'triangles': doc['accessors'][primitive['indices']]['count'] // 3,
        'vertices': count, 'wing_vertices': int((wing > 0).sum()),
        'unweighted_vertices': int((weights.sum(1) == 0).sum()),
        'max_weight_sum_error': float(abs(weights.sum(1) - 1).max()),
        'body_proxy_max_transfer_distance_m': float(distance[wing == 0].max()),
        'landmarks_m': {name: point.tolist() for name, point in positions.items()},
        'output': str(output.relative_to(ROOT)),
    }
    (ROOT / 'doc/assets/barkan-rig-v1.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['height_m', 'joints', 'triangles', 'unweighted_vertices', 'body_proxy_max_transfer_distance_m']}))


if __name__ == '__main__':
    build()
