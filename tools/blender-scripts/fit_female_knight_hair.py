import hashlib
import json
import math
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/modular_human_female_01/hair/tripo_knight_v1'
SOURCE = DIRECTORY / 'rear_filled_v1/hair_female_knight-rear-filled-v1.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v1'
OUTPUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
if rig.animation_data:
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
body_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
body_points, body_faces = [], []
for obj in body_objects:
    start = len(body_points)
    body_points.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
    body_faces.extend(tuple(start + i for i in p.vertices) for p in obj.data.polygons)
surface = BVHTree.FromPolygons(body_points, body_faces)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
hair = [obj for obj in set(bpy.data.objects) - before if obj.type == 'MESH']
transform = Matrix.Translation((0, .0054, 1.4508)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Diagonal((.576, .684, .72, 1))
clearance = .0063

def scalp_correction(point):
    nearest, normal, _, distance = surface.find_nearest(point)
    signed = (point - nearest).dot(normal)
    if signed < clearance and distance < .072:
        return normal * (clearance - signed)
    return Vector((0, 0, 0))

fitting = []
for obj in sorted(hair, key=lambda obj: obj.name):
    if 'tripo' in obj.name:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
        remaining, groups = set(bm.verts), []
        while remaining:
            group, pending = set(), [next(iter(remaining))]
            while pending:
                vertex = pending.pop()
                if vertex in group:
                    continue
                group.add(vertex)
                pending.extend(edge.other_vert(vertex) for edge in vertex.link_edges if edge.other_vert(vertex) not in group)
            remaining -= group
            groups.append(group)
        lining = min(groups, key=len)
        bmesh.ops.delete(bm, geom=list(lining), context='VERTS')
        bm.to_mesh(obj.data)
        bm.free()
    obj.data.transform(transform @ obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    obj.name = 'hair_female_knight_' + ('rear' if 'rear' in obj.name else 'front')
    points = np.array([vertex.co[:] for vertex in obj.data.vertices], dtype=float)
    initial = points.copy()
    h = points[:, 2]
    transition = (1 + np.tanh((points[:, 1] - .0054) / .0144)) / 2
    front_shift = np.interp(h, [1.08, 1.17, 1.26, 1.35, 1.422, 1.494, 1.566, 1.62, 1.836], [.009, .027, .063, .099, .126, .09, .0144, 0, 0])
    back_shift = np.interp(h, [1.08, 1.26, 1.44, 1.53, 1.602, 1.836], [.0324, .036, .0306, .018, 0, 0])
    points[:, 1] += back_shift * transition - front_shift * (1 - transition)
    for iteration in range(4):
        for i, point in enumerate(points):
            if point[2] > 1.629:
                points[i] += scalp_correction(Vector(point))
    for vertex, point in zip(obj.data.vertices, points):
        vertex.co = point
    obj.data.update()
    obj['part_id'] = 'hair_female_knight'
    obj['rig_id'] = 'human_female_01_local_v1'
    fitting.append({'mesh': obj.name, 'vertices': len(points),
                    'maximum_clearance_displacement': float(np.linalg.norm(points - initial, axis=1).max()),
                    'changed_vertices': int((np.linalg.norm(points - initial, axis=1) > 1.8e-6).sum())})
bpy.ops.object.select_all(action='DESELECT')
for obj in hair:
    obj.select_set(True)
bpy.context.view_layer.objects.active = hair[0]
target = OUTPUT / 'hair-fitted-unskinned.glb'
bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True)
report = {'date': '2026-10-12', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'transform_blender': {'scale': [.576, .684, .72], 'rotation_z_degrees': -90, 'translation': [0, .0054, 1.4508]},
          'clearance_target_m': clearance, 'fitting': fitting,
          'method': 'Remove redundant isolated central curtain replaced by the rear fill; fit crown to female scalp; nearest-surface scalp clearance and continuous front/back drape offsets around the torso.'}
(ROOT / 'doc/assets/modular-female-knight-hair-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Review')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .18, .18, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .7
center = Vector((0, 0, 1.512))
for location, energy in [((3.6, -5.4, 5.4), 712.8), ((-3.6, -1.8, 3.6), 486), ((0, 5.4, 3.6), 648)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.data.energy, light.data.size = energy, 5.4
    light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type, camera.data.ortho_scale = 'ORTHO', .936
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 700, 850
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
for name, offset in [('front', (0, -5.4, 0)), ('side', (5.4, 0, 0)), ('back', (0, 5.4, 0)), ('angle', (3.6, -5.4, .18))]:
    camera.location = center + Vector(offset)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUTPUT / f'fit-{name}.png')
    bpy.ops.render.render(write_still=True)
print(json.dumps(report))
