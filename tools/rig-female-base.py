"""Fit the modular skeleton and bind the preserved female surface locally."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/modular_human_female_01/ear_normals_v2/base-ear-normals-v2.glb'
DONOR = ROOT / 'assets/modular_human_male_01/fitted/base.glb'
OUT = ROOT / 'assets/modular_human_female_01/rig_v1'
spec = importlib.util.spec_from_file_location('plate_io', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
RIG_ID = 'human_female_01_local_v1'


def landmarks():
    points = dict(Hips=[0, .568, -.022], Spine=[0, .635, -.021],
                  Spine1=[0, .709, -.029], Spine2=[0, .783, -.031],
                  Neck=[0, .856, -.025], Head=[0, .901, -.008], HeadTop_End=[0, .993, -.008])
    left = dict(UpLeg=[.060, .550, -.017], Leg=[.092, .322, -.028],
                Foot=[.130, .055, -.022], ToeBase=[.142, .012, .040],
                Toe_End=[.150, .008, .073], Shoulder=[.034, .825, -.026],
                Arm=[.089, .810, -.026], ForeArm=[.178, .697, -.026],
                Hand=[.263, .601, -.019])
    fingers = {
        'Index': ([.300, .552, .002], [.327, .519, .002]),
        'Middle': ([.300, .548, -.011], [.334, .517, -.011]),
        'Ring': ([.295, .551, -.025], [.329, .520, -.026]),
        'Pinky': ([.286, .558, -.037], [.318, .529, -.038]),
    }
    for finger, (start, end) in fingers.items():
        for index, t in enumerate([0, .42, .75, 1], 1):
            left[f'Hand{finger}{index}'] = (np.array(start) * (1 - t) + np.array(end) * t).tolist()
    for index, p in enumerate([[.270, .579, -.004], [.275, .557, .004],
                              [.282, .542, .010], [.288, .533, .012]], 1):
        left[f'HandThumb{index}'] = p
    for name, p in left.items():
        points['Left' + name] = p
        points['Right' + name] = [-p[0], p[1], p[2]]
    # The source hands are not mirror images.
    points['RightHand'] = [-.26354, .60084, -.00281]
    right_fingers = {
        'Index': ([-.30264, .54704, .02136], [-.32630, .51897, .02208]),
        'Middle': ([-.30010, .54792, .00744], [-.33411, .51701, .00955]),
        'Ring': ([-.29598, .55093, -.00684], [-.33006, .52001, -.00573]),
        'Pinky': ([-.28774, .55792, -.01938], [-.31981, .52900, -.01839]),
    }
    for finger, (start, end) in right_fingers.items():
        for index, t in enumerate([0, .42, .75, 1], 1):
            points[f'RightHand{finger}{index}'] = (
                np.array(start) * (1 - t) + np.array(end) * t
            ).tolist()
    for index, p in enumerate([[-.26964, .57884, .01258], [-.27418, .55684, .02085],
                              [-.28083, .54185, .02726], [-.28671, .53286, .02962]], 1):
        points[f'RightHandThumb{index}'] = p
    return {name: np.array(p, dtype=float) for name, p in points.items()}


def world_matrices(doc):
    result = {}
    def visit(index, parent):
        n = doc['nodes'][index]
        if 'matrix' in n:
            local = np.array(n['matrix']).reshape(4, 4).T
        else:
            local = np.eye(4)
            local[:3, :3] = Rotation.from_quat(n.get('rotation', [0, 0, 0, 1])).as_matrix() @ np.diag(n.get('scale', [1, 1, 1]))
            local[:3, 3] = n.get('translation', [0, 0, 0])
        result[index] = parent @ local
        for child in n.get('children', []):
            visit(child, result[index])
    for index in doc['scenes'][0]['nodes']:
        visit(index, np.eye(4))
    return result


def match_clothing_weights(points, faces, weights):
    _, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    triangles = welded[faces]
    edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
    count = int(welded.max()) + 1
    _, labels = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(count, count)), directed=False)
    body = np.argmax(np.bincount(labels))
    body_faces = faces[labels[triangles[:, 0]] == body]
    attached = np.flatnonzero((labels[welded] != body) & (points[:, 1] < .87))
    spec = importlib.util.spec_from_file_location('rogue_fit', ROOT / 'tools/fit-modular-rogue.py')
    transfer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transfer)
    surface = points, body_faces, weights.copy()
    for start in range(0, len(attached), 128):
        indices = attached[start:start + 128]
        _, _, weights[indices] = transfer.nearest_surface(points[indices], surface)
    return len(attached)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    doc, binary = io.read_glb(SOURCE)
    binary = bytearray(binary)
    donor = io.BASE
    old_world = world_matrices(donor)
    ids = donor['skins'][0]['joints']
    names = [donor['nodes'][i]['name'] for i in ids]
    positions = landmarks()
    assert set(positions) == set(names), set(names) - set(positions)
    parents = {c: i for i, n in enumerate(donor['nodes']) for c in n.get('children', []) if c in ids}
    new_world = {}
    for index in ids:
        name = donor['nodes'][index]['name']
        children = [c for c in donor['nodes'][index].get('children', []) if c in ids]
        primary = {'Hips': 'Spine', 'Spine2': 'Neck', 'LeftHand': 'LeftHandMiddle1', 'RightHand': 'RightHandMiddle1'}.get(name)
        child = next((c for c in children if donor['nodes'][c]['name'] == primary), children[0] if children else None)
        rotation = old_world[index][:3, :3]
        if child is not None:
            a = old_world[child][:3, 3] - old_world[index][:3, 3]
            b = positions[donor['nodes'][child]['name']] - positions[name]
            a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
            cross = np.cross(a, b)
            if np.linalg.norm(cross) > 1e-8:
                rotation = Rotation.from_rotvec(cross / np.linalg.norm(cross) * np.arctan2(np.linalg.norm(cross), a @ b)).as_matrix() @ rotation
        new_world[index] = np.eye(4)
        new_world[index][:3, :3] = rotation
        new_world[index][:3, 3] = positions[name]
    offset = len(doc['nodes'])
    mapping = {old: offset + i for i, old in enumerate(ids)}
    for index in ids:
        parent = parents.get(index)
        local = np.linalg.inv(new_world[parent]) @ new_world[index] if parent in new_world else new_world[index]
        n = {'name': donor['nodes'][index]['name'], 'translation': local[:3, 3].tolist(),
             'rotation': Rotation.from_matrix(local[:3, :3]).as_quat().tolist()}
        children = [mapping[c] for c in donor['nodes'][index].get('children', []) if c in mapping]
        if children:
            n['children'] = children
        doc['nodes'].append(n)
    armature = len(doc['nodes'])
    doc['nodes'].append({'name': 'Armature', 'children': [mapping[i] for i in ids if parents.get(i) not in mapping], 'extras': {'rig_id': RIG_ID}})
    doc['scenes'][0]['nodes'].append(armature)
    doc['scenes'][0]['extras'] = {'rig_id': RIG_ID}
    inverse = np.array([np.linalg.inv(new_world[i]).T.reshape(16) for i in ids])
    doc['skins'] = [{'joints': list(mapping.values()), 'inverseBindMatrices': io.add_accessor(doc, binary, inverse, 'MAT4'), 'skeleton': mapping[ids[names.index('Hips')]]}]
    for n in doc['nodes'][:offset]:
        if 'mesh' in n:
            n['skin'] = 0
            n['name'] = 'female_body'
            n['extras'] = {'rig_id': RIG_ID, 'part_id': 'female_base'}
    primitives = doc['meshes'][0]['primitives']
    original_attributes = [copy.deepcopy(p['attributes']) for p in primitives]
    for p in primitives:
        count = doc['accessors'][p['attributes']['POSITION']]['count']
        joints = np.full((count, 4), names.index('Head'), dtype=np.uint16)
        weights = np.zeros((count, 4)); weights[:, 0] = 1
        joints[weights == 0] = 0
        p['attributes']['JOINTS_0'] = io.add_accessor(doc, binary, joints, 'VEC4', 5123)
        p['attributes']['WEIGHTS_0'] = io.add_accessor(doc, binary, weights, 'VEC4')
    with tempfile.TemporaryDirectory(prefix='female-bind-') as temp:
        temp = Path(temp)
        input_path = temp / 'input.glb'
        weights_path = temp / 'weights.npz'
        doc['buffers'][0]['byteLength'] = len(binary)
        io.write_glb(input_path, doc, binary)
        subprocess.run(['blender', '-b', '-t', '4', '--python', str(ROOT / 'tools/blender-scripts/bind_female_base.py'), '--', str(input_path), str(weights_path)], check=True)
        data = np.load(weights_path)
        body = io.accessor(doc, binary, primitives[0]['attributes']['POSITION'])
        distance, nearest = cKDTree(data['positions']).query(body)
        used = np.unique(io.accessor(doc, binary, primitives[0]['indices']))
        assert distance[used].max() < 1e-6, distance[used].max()
        dense = data['weights'][nearest]
        assert np.isfinite(dense).all() and (dense.sum(1) > 0).all()
        faces = io.accessor(doc, binary, primitives[0]['indices']).reshape(-1, 3)
        clothing_vertices = match_clothing_weights(body, faces, dense)
        head = body[:, 1] > .889
        dense[head] = 0
        dense[head, names.index('Head')] = 1
        joints = np.argsort(dense, axis=1)[:, -4:][:, ::-1]
        weights = np.take_along_axis(dense, joints, axis=1)
        weights /= weights.sum(1, keepdims=True)
        joints[weights == 0] = 0
        primitives[0]['attributes']['JOINTS_0'] = io.add_accessor(doc, binary, joints, 'VEC4', 5123)
        primitives[0]['attributes']['WEIGHTS_0'] = io.add_accessor(doc, binary, weights, 'VEC4')
    for primitive in primitives:
        for attribute in ['JOINTS_0', 'WEIGHTS_0']:
            accessor = doc['accessors'][primitive['attributes'][attribute]]
            doc['bufferViews'][accessor['bufferView']]['target'] = 34962
    doc['buffers'][0]['byteLength'] = len(binary)
    output = OUT / 'female-base.glb'
    io.write_glb(output, doc, binary)
    report = {'date': date.today().isoformat(), 'rig_id': RIG_ID, 'method': '65-bone modular hierarchy fitted to female anatomical landmarks with independently fitted right-hand joints; Blender bone-heat binding; rigid head binding for separate eyelashes; four normalized influences',
              'sources': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in [SOURCE, DONOR]],
              'source_conditions': 'Original Tripo API and image-edit source/license records remain applicable; donor Mixamo skeleton uses the existing project license. Local processing only, no paid generation.',
              'height': 1, 'joints': len(names), 'landmarks': {k: v.tolist() for k, v in positions.items()},
              'triangles': sum(doc['accessors'][p['indices']]['count'] // 3 for p in primitives),
              'body_vertices': len(body), 'unweighted_vertices': int((weights.sum(1) == 0).sum()),
              'clothing_vertices_with_body_surface_weights': clothing_vertices,
              'max_weight_sum_error': float(abs(weights.sum(1) - 1).max()),
              'source_geometry_uv_normals_materials_images_preserved': all(all(p['attributes'][k] == v for k, v in original.items()) for p, original in zip(primitives, original_attributes)),
              'output': str(output.relative_to(ROOT))}
    (OUT / 'binding.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['joints', 'triangles', 'unweighted_vertices', 'max_weight_sum_error']}))


def embed_animations():
    path = OUT / 'female-base.glb'
    doc, binary = io.read_glb(path)
    if doc.get('animations'):
        animation_accessors = {s[k] for a in doc['animations'] for s in a['samplers'] for k in ['input', 'output']}
        first_accessor = min(animation_accessors)
        assert animation_accessors == set(range(first_accessor, len(doc['accessors'])))
        animation_views = {doc['accessors'][i]['bufferView'] for i in animation_accessors}
        first_view = min(animation_views)
        assert animation_views == set(range(first_view, len(doc['bufferViews'])))
        binary = binary[:doc['bufferViews'][first_view].get('byteOffset', 0)]
        doc['accessors'] = doc['accessors'][:first_accessor]
        doc['bufferViews'] = doc['bufferViews'][:first_view]
    binary = bytearray(binary)
    clips = json.loads((OUT / 'clips.json').read_text())
    indices = {n['name']: i for i, n in enumerate(doc['nodes'])}
    doc['animations'] = []
    for clip in clips['clips']:
        animation = dict(name=clip['name'], channels=[], samplers=[])
        for track in clip['tracks']:
            name, property_name = track['name'].split('.')
            width = 4 if property_name == 'quaternion' else 3
            values = np.array(track['values']).reshape(-1, width)
            times = np.array(track['times']).reshape(-1, 1)
            input_index = io.add_accessor(doc, binary, times, 'SCALAR')
            doc['accessors'][input_index].update(min=[float(times.min())], max=[float(times.max())])
            output_index = io.add_accessor(doc, binary, values, f'VEC{width}')
            animation['channels'].append({'sampler': len(animation['samplers']), 'target': {
                'node': indices[name], 'path': {'quaternion': 'rotation', 'position': 'translation', 'scale': 'scale'}[property_name]}})
            animation['samplers'].append({'input': input_index, 'output': output_index, 'interpolation': 'LINEAR'})
        doc['animations'].append(animation)
    doc['buffers'][0]['byteLength'] = len(binary)
    io.write_glb(path, doc, binary)
    print('Embedded:', ', '.join(a['name'] for a in doc['animations']))


if __name__ == '__main__':
    if '--animations' in sys.argv:
        embed_animations()
    else:
        build()
