import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/modular_human_female_01/hair/tripo_knight_bob_v1'
SOURCE = DIRECTORY / 'model_url.glb'
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
body = bpy.data.objects['female_body']
body_points = [body.matrix_world @ v.co for v in body.data.vertices]
surface = BVHTree.FromPolygons(body_points, [p.vertices[:] for p in body.data.polygons])
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
hair = next(obj for obj in set(bpy.data.objects) - before if obj.type == 'MESH')

def uv_triangles(mesh):
    uv = mesh.uv_layers.active.data
    return Counter(tuple(tuple(round(c, 6) for c in uv[i].uv) for i in p.loop_indices)
                   for p in mesh.polygons)

source_uvs = uv_triangles(hair.data)
transform = Matrix.Translation((0, .004, .925)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Diagonal((.145, .145, .17, 1))
hair.data.transform(transform @ hair.matrix_world)
hair.matrix_world = Matrix.Identity(4)
for vertex in hair.data.vertices:
    t = max(0, min(1, (vertex.co.z - .84) / .105))
    vertex.co.z += .02 * (1 - t * t * (3 - 2 * t))
bm = bmesh.new()
bm.from_mesh(hair.data)

def signed_distance(point):
    nearest, normal, _, _ = surface.find_nearest(point)
    return (point - nearest).dot(normal)

internal = [face for face in bm.faces
            if all(abs(v.co.x) < .035 and v.co.y > -.025 and v.co.z < .956
                   and signed_distance(v.co) < -.002 for v in face.verts)
            and signed_distance(face.calc_center_median()) < -.002]
removed = len(internal)
bmesh.ops.delete(bm, geom=internal, context='FACES')
bm.to_mesh(hair.data)
bm.free()

hair_offset = Vector((0, -.002, .0035))

def smoothstep(low, high, value):
    t = max(0, min(1, (value - low) / (high - low)))
    return t * t * (3 - 2 * t)

for vertex in hair.data.vertices:
    vertex.co += hair_offset
    p = vertex.co
    p.y += .0035 * smoothstep(.005, .04, p.y) * smoothstep(.90, .93, p.z)
hair.data.update()

right_front_pivot = Vector((0, -.015, 0))
right_front_angle = -12

def turn_right_front(point):
    weight = smoothstep(.003, .035, -point.x) * smoothstep(-.020, .040, -point.y)
    weight *= 1 - smoothstep(.960, .995, point.z)
    rotation = Matrix.Rotation(math.radians(right_front_angle) * weight, 3, 'Z')
    return right_front_pivot + rotation @ (point - right_front_pivot)

corner_normals = [normal.vector.copy() for normal in hair.data.corner_normals]
normal_transforms = {}
right_front_displacements = []
for vertex in hair.data.vertices:
    before = vertex.co.copy()
    after = turn_right_front(before)
    displacement = (after - before).length
    if displacement < 1e-8:
        continue
    columns = []
    for axis in range(3):
        delta = Vector((0, 0, 0))
        delta[axis] = 1e-5
        columns.append((turn_right_front(before + delta) - turn_right_front(before - delta)) / 2e-5)
    normal_transforms[vertex.index] = Matrix(columns).inverted()
    vertex.co = after
    right_front_displacements.append(displacement)
for loop in hair.data.loops:
    transform = normal_transforms.get(loop.vertex_index)
    if transform is not None:
        corner_normals[loop.index] = (transform @ corner_normals[loop.index]).normalized()
hair.data.normals_split_custom_set(corner_normals)
hair.data.update()
rear_clearances = []
for polygon in hair.data.polygons:
    if polygon.center.y <= .025 or polygon.center.z <= .925:
        continue
    a, b, c = [hair.data.vertices[i].co for i in polygon.vertices]
    for i in range(5):
        for j in range(5 - i):
            point = (a * i + b * j + c * (4 - i - j)) / 4
            rear_clearances.append(signed_distance(point))
assert min(rear_clearances) > 0, 'Rear hair intersects the scalp'
assert not (uv_triangles(hair.data) - source_uvs), 'Retained UVs changed'
hair.name = 'hair_female_knight_bob'
hair['part_id'] = hair.name
hair['rig_id'] = 'human_female_01_local_v1'
bpy.ops.object.select_all(action='DESELECT')
hair.select_set(True)
bpy.context.view_layer.objects.active = hair
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'hair-fitted-unskinned.glb'), export_format='GLB', use_selection=True, export_tangents=True)
report = {
    'date': '2026-10-12', 'tool': f'Blender {bpy.app.version_string}',
    'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
    'transform_blender': {'scale': [.145, .145, .17], 'rotation_z_degrees': -90, 'translation': [0, .004, .925]},
    'tip_shortening': {'offset': .02, 'smooth_falloff_height_range': [.84, .945]},
    'whole_hair_offset_blender': list(hair_offset),
    'right_front_turn': {'angle_degrees': right_front_angle, 'pivot_blender': list(right_front_pivot),
                         'side_falloff': [.003, .035], 'front_falloff': [-.020, .040],
                         'crown_falloff': [.960, .995], 'vertices_moved': len(right_front_displacements),
                         'maximum_displacement': max(right_front_displacements, default=0),
                         'normals': 'Inverse-transpose deformation Jacobian; UVs and image bytes preserved.'},
    'rear_clearance': {'backward_offset': .0035, 'depth_falloff': [.005, .04],
                       'height_falloff': [.90, .93], 'rest_surface_samples': len(rear_clearances),
                       'minimum_sampled_rest_clearance': min(rear_clearances)},
    'removed_internal_triangles': removed, 'triangles': len(hair.data.polygons),
    'bounds_blender': [[min(v.co[i] for v in hair.data.vertices) for i in range(3)],
                       [max(v.co[i] for v in hair.data.vertices) for i in range(3)]],
    'method': 'Fit original bob; shorten tips; remove embedded central faces; translate the whole hair; offset the rear for scalp clearance; smoothly turn the right front around the vertical axis. Preserve retained UVs and original textures; no decimation.',
    'source_file_preserved': True,
    'retained_uvs_unchanged': True,
}
(ROOT / 'doc/assets/modular-female-knight-bob-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Review')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .18, .18, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .7
center = Vector((0, 0, .925))
for location, energy in [((2, -3, 3), 220), ((-2, -1, 2), 150), ((0, 3, 2), 200)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.data.energy, light.data.size = energy, 3
    light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type, camera.data.ortho_scale = 'ORTHO', .225
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 650, 750
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
for name, offset in [('front', (0, -3, 0)), ('side', (3, 0, 0)), ('back', (0, 3, 0)), ('angle', (2, -3, .1))]:
    camera.location = center + Vector(offset)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUTPUT / f'fit-{name}.png')
    bpy.ops.render.render(write_still=True)
