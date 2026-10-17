# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_knight_top/tripo_v1'
OUTPUT = DIRECTORY / 'fitted_v3'
OUTPUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['female_body']
body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
body_faces = [polygon.vertices[:] for polygon in body.data.polygons]
surface = BVHTree.FromPolygons(body_points, body_faces)
names = [bone.name for bone in rig.data.bones]
body_weights = np.zeros((len(body_points), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        name = body.vertex_groups[group.group].name
        if name in names:
            body_weights[vertex.index, names.index(name)] = group.weight

data = np.load(DIRECTORY / 'fitted_v2/fit-data.npz')
source, previous = data['source'], data['fitted']
points = previous.copy()
weights = np.zeros((len(points), len(names)))
for column in range(4):
    np.add.at(weights, (np.arange(len(points)), data['joints'][:, column]), data['weights'][:, column])


def smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


amount = smooth((.723 - source[:, 2]) / .030) * smooth((np.abs(source[:, 0]) - .095) / .008)
details = []
for side, sign in [('Left', 1), ('Right', -1)]:
    elbow = np.array(rig.matrix_world @ rig.pose.bones[side + 'ForeArm'].head)
    wrist = np.array(rig.matrix_world @ rig.pose.bones[side + 'Hand'].head)
    axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
    selected = np.flatnonzero((source[:, 0] * sign > 0) & (amount > 0))
    radial_clearances = []
    for i in selected:
        along = (previous[i] - elbow) @ axis
        center = elbow + along * axis
        radial = previous[i] - center
        radius = np.linalg.norm(radial)
        direction = radial / radius
        center += axis * (.038 * smooth((along + .035) / .055))
        point, _, face, _ = surface.ray_cast(Vector(center), Vector(direction), .08)
        if point is None:
            point, _, face, _ = surface.find_nearest(Vector(previous[i]))
        skin_radius = np.linalg.norm(np.array(point) - center)
        target_radius = skin_radius + .008 + .20 * radius
        target = center + direction * target_radius
        points[i] = previous[i] + amount[i] * (target - previous[i])
        vertices = body_faces[face]
        barycentric = np.array(barycentric_transform(point, *[body_points[j] for j in vertices],
                                                     Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
        barycentric = np.maximum(barycentric, 0)
        barycentric /= barycentric.sum()
        transferred = barycentric @ body_weights[list(vertices)]
        weights[i] = (1 - amount[i]) * weights[i] + amount[i] * transferred
        radial_clearances.append(float(np.linalg.norm(points[i] - center) - skin_radius))
    details.append({'side': side, 'vertices': len(selected), 'minimum_radial_clearance': min(radial_clearances)})

np.savez(OUTPUT / 'sleeve-adjustment.npz', previous=previous, source=source, points=points,
         weights=weights, bone_names=np.array(names), amount=amount)
report = {'method': 'Recenter and widen sleeve lining around actual forearm surface, extending the cuff below the elbow crease; barycentric skin weights at radial surface correspondence. Smooth transition below the upper-arm plates.',
          'sides': details, 'maximum_displacement': float(np.linalg.norm(points - previous, axis=1).max()),
          'fully_adjusted_vertices': int((amount > .999).sum()), 'unchanged_vertices': int((amount == 0).sum())}
(OUTPUT / 'sleeve-adjustment.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
