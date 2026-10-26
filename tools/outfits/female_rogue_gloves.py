"""Build the female rogue glove shell and attach the canonical rig."""
import copy
import hashlib
import importlib.util
from pathlib import Path

import numpy as np

from lib.glb_accessors import accessor, add_accessor
from outfits.rogue_layers import clip_garment, compact_weights, edge_loops

ROOT = Path(__file__).resolve().parents[2]
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
spec = importlib.util.spec_from_file_location('knight_gloves', ROOT / 'tools/fit-female-knight-gloves.py')
knight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knight)
surface = knight.surface_tools
io = knight.io
FINGERS = knight.FINGERS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hand_frame(bones, side):
    axis = io.unit(bones[side + 'HandMiddle1'] - bones[side + 'Hand'])
    across = bones[side + 'HandIndex1'] - bones[side + 'HandPinky1']
    across = io.unit(across - axis * (across @ axis))
    return axis, across, io.unit(np.cross(axis, across)) * (1 if side == 'Right' else -1)


def cut_field(positions, dense, names, bones, side):
    wrist = bones[side + 'Hand']
    axis = io.unit(wrist - bones[side + 'ForeArm'])
    distance = -.020 - (positions - wrist) @ axis
    field = np.array([dense[:, [i for i, name in enumerate(names) if name.startswith(side + 'Hand' + finger)]].sum(1) for finger in FINGERS]).T
    labels = field.argmax(1)
    for i, finger in enumerate(FINGERS):
        root, middle, end = [bones[f'{side}Hand{finger}{j}'] for j in [1, 2, 3]]
        opening = middle * .85 + end * .15
        axis = io.unit(opening - root)
        rows = (labels == i) & (field[:, i] > .05)
        cut = (positions[rows] - opening) @ axis
        if finger == 'Thumb':
            web = bones[side + 'HandIndex1'] - root
            web = io.unit(web - axis * (web @ axis))
            cut -= .010 * io.smoothstep(((positions[rows] - opening) @ web - .010) / .014)
        distance[rows] = np.maximum(distance[rows], cut)
    return distance


def hand_shell(body, names, bones, side):
    own = [i for i, name in enumerate(names) if name.startswith(side) and ('Hand' in name or 'ForeArm' in name)]
    faces = body[1][body[2][:, own].sum(1)[body[1]].mean(1) > .5]
    web = (bones[side + 'HandIndex1'] + bones[side + 'HandThumb2']) / 2
    nearby = np.exp(-np.sum((body[0] - web) ** 2, axis=1) / .045 ** 2)
    offset = .003 - .0027 * nearby
    positions = body[0] + io.smooth_normals(body[0], body[1]) * offset[:, None]
    distance = cut_field(positions, body[2], names, bones, side)
    points, faces, payload = clip_garment(positions, faces, np.column_stack([np.zeros((len(positions), 2)), body[2], body[0]]), distance)
    dense = payload[:, 2:2 + len(names)]
    skin_reference = payload[:, -3:][faces].reshape(-1, 3)
    _, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    loops = edge_loops(welded[faces])
    assert len(loops) == 6, f'{side}: expected five finger openings and wrist, got {len(loops)}'
    points, dense = points[faces].reshape(-1, 3), dense[faces].reshape(-1, len(names))
    faces = np.arange(len(points)).reshape(-1, 3)
    joints, weights = compact_weights(dense)
    return points, faces, joints, weights, skin_reference


def attach_rig(doc, raw, base, base_raw):
    ids = base['skins'][0]['joints']
    remap = {old: i for i, old in enumerate(ids)}
    doc['nodes'] = [copy.deepcopy(base['nodes'][i]) for i in ids]
    for node in doc['nodes']:
        if 'children' in node:
            node['children'] = [remap[i] for i in node['children'] if i in remap]
    children = {child for node in doc['nodes'] for child in node.get('children', [])}
    doc['nodes'].append({'name': 'Armature', 'children': [i for i in range(len(ids)) if i not in children]})
    skin = copy.deepcopy(base['skins'][0])
    skin['joints'] = list(range(len(ids)))
    skin['skeleton'] = remap[skin['skeleton']]
    skin['inverseBindMatrices'] = add_accessor(doc, raw, accessor(base, base_raw, skin['inverseBindMatrices']), 'MAT4')
    doc['skins'] = [skin]
    scene_nodes = [len(ids)]
    for i, side in enumerate(['right', 'left']):
        scene_nodes.append(len(doc['nodes']))
        doc['nodes'].append({'name': f'gloves_female_rogue_{side}', 'mesh': i, 'skin': 0, 'extras': {'rig_id': 'human_female_01_local_v1', 'part_id': 'gloves_female_rogue'}})
    doc['scenes'] = [{'nodes': scene_nodes, 'extras': {'rig_id': 'human_female_01_local_v1'}}]
    doc['scene'] = 0
    doc.pop('animations', None)
