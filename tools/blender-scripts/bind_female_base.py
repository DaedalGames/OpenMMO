"""Compute bone-heat weights without round-tripping the source materials."""
import sys
import json
import struct
from pathlib import Path

import bpy
import bmesh
import numpy as np

source, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source), bone_heuristic='TEMPERANCE')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = next(o for o in bpy.data.objects if o.type == 'MESH')
body.vertex_groups.clear()
for modifier in list(body.modifiers):
    body.modifiers.remove(modifier)
bm = bmesh.new()
bm.from_mesh(body.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != 0], context='FACES')
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
bm.to_mesh(body.data)
bm.free()
for bone in rig.data.bones:
    bone.use_deform = bool(bone.children) or bone.name == 'Head'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
positions = np.array([body.matrix_world @ v.co for v in body.data.vertices])
positions = positions[:, [0, 2, 1]] * np.array([1, 1, -1])
raw = source.read_bytes()
gltf = json.loads(raw[20:20 + struct.unpack_from('<I', raw, 12)[0]])
names = [gltf['nodes'][i]['name'] for i in gltf['skins'][0]['joints']]
weights = np.zeros((len(positions), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        name = body.vertex_groups[group.group].name
        if name in names:
            weights[vertex.index, names.index(name)] = group.weight
assert (weights.sum(1) > 0).all(), f'{(weights.sum(1) == 0).sum()} unweighted vertices'
np.savez(output, positions=positions, weights=weights)
print(f'Bound {len(positions)} welded vertices to {len(names)} bones', flush=True)
