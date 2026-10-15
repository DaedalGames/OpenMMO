from pathlib import Path

import bpy
import numpy as np
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
data = np.load(ROOT / 'assets/modular_human_female_01/underwear_fit_v1/source-influences.npz')
tree = KDTree(len(data['positions']))
for i, point in enumerate(data['positions']):
    tree.insert(point, i)
tree.balance()
body = bpy.data.objects['female_body']
names = data['bone_names'].tolist()
changed = 0
for vertex in body.data.vertices:
    point = body.matrix_world @ vertex.co
    _, index, distance = tree.find((point.x, point.z, -point.y))
    if distance > .000002:
        continue
    for group in list(vertex.groups):
        if body.vertex_groups[group.group].name in names:
            body.vertex_groups[group.group].remove([vertex.index])
    for joint, weight in zip(data['corrected_joints'][index], data['corrected_weights'][index]):
        if weight > 0:
            body.vertex_groups[names[joint]].add([vertex.index], float(weight), 'REPLACE')
    changed += 1
assert changed > 20, f'Underwear source did not match: {changed} vertices'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.blend'))
print(f'Synchronized {changed} underwear source vertices')
