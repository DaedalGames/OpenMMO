import copy

import numpy as np
from scipy.spatial.transform import Rotation

from lib.glb_accessors import accessor


def node_worlds(doc):
    parents = {child: i for i, node in enumerate(doc['nodes']) for child in node.get('children', [])}
    worlds = {}

    def world(index):
        if index in worlds:
            return worlds[index]
        node = doc['nodes'][index]
        matrix = np.eye(4)
        if 'matrix' in node:
            matrix = np.array(node['matrix']).reshape(4, 4).T
        else:
            matrix[:3, :3] = Rotation.from_quat(node.get('rotation', [0, 0, 0, 1])).as_matrix() @ np.diag(node.get('scale', [1, 1, 1]))
            matrix[:3, 3] = node.get('translation', [0, 0, 0])
        worlds[index] = world(parents[index]) @ matrix if index in parents else matrix
        return worlds[index]

    return np.array([world(i) for i in range(len(doc['nodes']))])


def heel_pose(base, binary, degrees=30):
    rest = node_worlds(base)
    posed = copy.deepcopy(base)
    indices = {node.get('name'): i for i, node in enumerate(base['nodes'])}
    offsets = {}
    for side in ['Left', 'Right']:
        foot, toe = [indices[side + name] for name in ['Foot', 'ToeBase']]
        forward = rest[toe, :3, 3] - rest[foot, :3, 3]
        forward[1] = 0
        forward /= np.linalg.norm(forward)
        axis = np.cross([0, 1, 0], forward)
        for index, angle in [(foot, degrees), (toe, -degrees)]:
            local_axis = rest[index, :3, :3].T @ axis
            delta = Rotation.from_rotvec(local_axis * np.deg2rad(angle))
            node = posed['nodes'][index]
            node['rotation'] = (Rotation.from_quat(node['rotation']) * delta).as_quat().tolist()
            offsets[node['name']] = delta.as_quat().tolist()
    worlds = node_worlds(posed)
    skin = base['skins'][0]
    inverse = accessor(base, binary, skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    deformation = worlds[skin['joints']] @ inverse
    return deformation, {'pitch_degrees': degrees, 'local_quaternion_offsets': offsets,
                         'rest_foot_positions': {name: rest[i, :3, 3].tolist() for name, i in indices.items() if name in offsets},
                         'posed_foot_positions_before_root_lift': {name: worlds[i, :3, 3].tolist() for name, i in indices.items() if name in offsets}}
