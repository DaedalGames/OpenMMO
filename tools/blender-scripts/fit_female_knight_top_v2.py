# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
import hashlib
import json
import math
import subprocess
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_knight_top/tripo_v1'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v2'
OUTPUT.mkdir(exist_ok=True)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def regions(p):
    x, y, z = p.T
    boundary = .083 - .023 * smooth((z - .81) / .05)
    arm = smooth((np.abs(x) - boundary) / .012)
    plate = (1 - smooth((np.abs(x) - .076) / .010)) * np.maximum(smooth((-.015 - y) / .025), smooth((y - .043) / .018))
    arm *= 1 - plate
    cap = smooth((z - .798) / .035)
    neck = smooth((z - .854) / .020) * (1 - arm)
    return arm, cap, neck


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['female_body']
body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
surface = BVHTree.FromPolygons(body_points, [p.vertices[:] for p in body.data.polygons])
joints = {bone.name: np.array(rig.matrix_world @ bone.head) for bone in rig.pose.bones}
names = [bone.name for bone in rig.data.bones]
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
top = next(obj for obj in set(bpy.data.objects) - before if obj.type == 'MESH')
transform = Matrix.Translation(Vector((0, .004, .768))) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Scale(.32, 4)
top.data.transform(transform @ top.matrix_world)
top.matrix_world = Matrix.Identity(4)
mesh = top.data
source = np.array([vertex.co for vertex in mesh.vertices])
source_normals = np.array([normal.vector for normal in mesh.corner_normals])
loop_vertices = np.array([loop.vertex_index for loop in mesh.loops])
faces = np.array([polygon.vertices[:] for polygon in mesh.polygons])
arm, cap, neck = regions(source)


def fit(p):
    arm_field, _, _ = regions(p)
    result = p.copy()
    front = smooth((.042 - p[:, 1]) / .050)
    bust = smooth((p[:, 2] - .675) / .045) * (1 - smooth((p[:, 2] - .805) / .045))
    bust *= 1 - arm_field
    result[:, 0] *= 1 + .10 * bust
    result[:, 1] += (p[:, 1] - .026) * .18 * bust * front

    for side, sign in [('Left', 1), ('Right', -1)]:
        own = p[:, 0] * sign > 0
        pivot = np.array([sign * .112, .024, .820])
        target = joints[side + 'Arm'] + np.array([sign * .012, 0, .006])
        direction = joints[side + 'ForeArm'] - joints[side + 'Arm']
        delta = math.atan2(abs(direction[0]), -direction[2]) - math.atan(.15)
        angle = np.full(len(p), -sign * delta)
        offset = p - pivot
        direction = np.array([sign * .15, 0, -1.])
        direction /= np.linalg.norm(direction)
        along = offset @ direction
        radial = offset - along[:, None] * direction
        cloth_scale = 1 - .04 * (1 - smooth((p[:, 2] - .735) / .020))
        offset = along[:, None] * direction + radial * cloth_scale[:, None]
        rotated = offset.copy()
        rotated[:, 0] = np.cos(angle) * offset[:, 0] + np.sin(angle) * offset[:, 2]
        rotated[:, 2] = -np.sin(angle) * offset[:, 0] + np.cos(angle) * offset[:, 2]
        mapped = rotated + target
        result[own] = result[own] * (1 - arm_field[own, None]) + mapped[own] * arm_field[own, None]
    return result


points = fit(source)
image = next(image for image in bpy.data.images if image.name.startswith('Color_93a31e72'))
pixels = np.empty(image.size[0] * image.size[1] * 4, dtype=np.float32)
image.pixels.foreach_get(pixels)
pixels = pixels.reshape(image.size[1], image.size[0], 4)
uv = np.array([loop.uv for loop in mesh.uv_layers.active.data])
uv_pixels = np.clip(np.floor(uv * np.array(image.size)).astype(int), 0, np.array(image.size) - 1)
loop_colors = pixels[uv_pixels[:, 1], uv_pixels[:, 0], :3]
colors = np.zeros((len(source), 3))
np.add.at(colors, loop_vertices, loop_colors)
colors /= np.maximum(np.bincount(loop_vertices, minlength=len(source))[:, None], 1)

fixed_torso = (np.abs(source[:, 0]) < .083) & ((source[:, 1] < -.022) | (source[:, 1] > .047))
fixed_top = source[:, 2] > .842
fixed_cuffs = (source[:, 2] < .741) & (np.abs(source[:, 0]) > .100)
fixed = fixed_torso | fixed_top | fixed_cuffs
points[fixed_top] = source[fixed_top]
np.savez(OUTPUT / 'arap-input.npz', points=source, faces=faces,
         colors=colors, fixed=fixed, targets=points)
subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'tools/outfits/fit_female_knight_top_surface.py'),
                str(OUTPUT / 'arap-input.npz')], check=True)
arap = np.load(OUTPUT / 'arap-result.npz')
points = arap['points'].copy()
initial = points.copy()
ray_samples = []
for x in np.linspace(-.095, .095, 49):
    for z in np.linspace(.695, .837, 39):
        point, _, _, _ = surface.ray_cast(Vector((x, -.3, z)), Vector((0, 1, 0)))
        if point is not None:
            ray_samples.append((x, z, point.y))
ray_samples = np.array(ray_samples)
corrections = []
for iteration in range(5):
    plate = BVHTree.FromPolygons([Vector(p) for p in points], faces.tolist())
    constraints = []
    for x, z, body_y in ray_samples:
        point, normal, _, _ = plate.ray_cast(Vector((x, -.3, z)), Vector((0, 1, 0)))
        if point is not None and point.y < .015 and normal.y < -.25 and abs(x) < .087 and .705 < z < .825:
            residual = point.y - (body_y - .008)
            if .0003 < residual < .035:
                constraints.append((x, z, residual))
    corrections.append({'iteration': iteration, 'constraints': len(constraints),
                        'maximum_deficit': max((c[2] for c in constraints), default=0)})
    if not constraints:
        break
    c = np.array(constraints)
    xz = points[:, [0, 2]]
    distance = ((xz[:, None] - c[None, :, :2]) / np.array([.023, .021])) ** 2
    displacement = (np.exp(-distance.sum(2) / 2) * c[None, :, 2]).max(1)
    front = smooth((.035 - points[:, 1]) / .035)
    points[:, 1] -= displacement * front * (1 - arm)

normal_values = np.einsum('nij,nj->ni', arap['rotations'][loop_vertices], source_normals)
normal_values /= np.linalg.norm(normal_values, axis=1, keepdims=True)
for vertex, point in zip(mesh.vertices, points):
    vertex.co = point
mesh.update()
mesh.normals_split_custom_set(normal_values.tolist())

weights = np.zeros((len(points), len(names)))
index = {name: i for i, name in enumerate(names)}
arm = regions(points)[0]
plate = ((source[:, 1] < -.025) & (np.abs(source[:, 0]) < .096) & (source[:, 2] < .825)) | ((source[:, 1] > .055) & (np.abs(source[:, 0]) < .087))
arm[plate] = 0
cap_attach = smooth((np.abs(source[:, 0]) - .064) / .010) * smooth((source[:, 2] - .805) / .008)
soft_arm = (np.abs(source[:, 0]) > .098) & (source[:, 2] < .754)
arm = np.maximum(arm, np.maximum(cap_attach, soft_arm.astype(float)))
torso = 1 - arm
weights[:, index['Spine1']] = torso * .90
weights[:, index['Spine2']] = torso * .10
weights[:, index['Neck']] = 0
for side, sign in [('Left', 1), ('Right', -1)]:
    own = points[:, 0] * sign > 0
    axis = joints[side + 'ForeArm'] - joints[side + 'Arm']
    length = np.linalg.norm(axis)
    distance = (points - joints[side + 'Arm']) @ (axis / length)
    elbow = smooth((distance - length + .027) / .055)
    cloth = 1 - smooth((source[:, 2] - .738) / .020)
    forearm = np.maximum(elbow * cloth, 1 - smooth((source[:, 2] - .682) / .030))
    shoulder = smooth((source[:, 2] - .786) / .025)
    weights[own, index[side + 'Shoulder']] += arm[own] * shoulder[own]
    weights[own, index[side + 'Arm']] += arm[own] * (1 - shoulder[own]) * (1 - forearm[own])
    weights[own, index[side + 'ForeArm']] += arm[own] * (1 - shoulder[own]) * forearm[own]

body_weights = np.zeros((len(body.data.vertices), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        name = body.vertex_groups[group.group].name
        if name in index:
            body_weights[vertex.index, index[name]] = group.weight
tree = KDTree(len(body.data.vertices))
for vertex, point in zip(body.data.vertices, body_points):
    tree.insert(point, vertex.index)
tree.balance()
for i in np.flatnonzero(soft_arm):
    side = 'Left' if points[i, 0] > 0 else 'Right'
    neighbors = tree.find_n(Vector(points[i]), 6)
    factors = np.array([1 / max(distance, .0001) ** 2 for _, _, distance in neighbors])
    dense = (body_weights[[j for _, j, _ in neighbors]] * factors[:, None]).sum(0)
    a, b = index[side + 'Arm'], index[side + 'ForeArm']
    ratio = dense[b] / max(dense[a] + dense[b], 1e-8)
    ratio = max(ratio, float(1 - smooth((source[i, 2] - .682) / .030)))
    weights[i] = 0
    weights[i, a], weights[i, b] = 1 - ratio, ratio

edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
_, first, welded = np.unique(np.round(source, 7), axis=0, return_index=True, return_inverse=True)
adj = [[] for _ in first]
for a, b in welded[edges]:
    adj[a].append(b)
    adj[b].append(a)
labels = np.full(len(first), -1)
for seed in range(len(first)):
    if labels[seed] >= 0:
        continue
    labels[seed] = seed
    todo = [seed]
    while todo:
        for neighbor in adj[todo.pop()]:
            if labels[neighbor] < 0:
                labels[neighbor] = seed
                todo.append(neighbor)
unique_weights = weights[first].copy()
dominant = unique_weights.argmax(1)
fixed_weights = np.ones(len(first), dtype=bool)
for _ in range(3):
    previous = fixed_weights.copy()
    for i, neighbors in enumerate(adj):
        fixed_weights[i] = previous[i] and all(previous[j] and dominant[j] == dominant[i] for j in neighbors)
original_weights = unique_weights.copy()
for _ in range(80):
    updated = unique_weights.copy()
    for i, neighbors in enumerate(adj):
        if not fixed_weights[i] and neighbors:
            updated[i] = .35 * unique_weights[i] + .65 * unique_weights[neighbors].mean(0)
    updated[fixed_weights] = original_weights[fixed_weights]
    unique_weights = updated
weights = unique_weights[welded]

large = np.bincount(labels).argmax()
for component in np.unique(labels):
    if component == large:
        continue
    selection = labels[welded] == component
    center = source[selection].mean(0)
    garment = np.flatnonzero(labels[welded] == large)
    near = garment[np.argsort(np.linalg.norm(source[garment] - center, axis=1))[:4]]
    weights[selection] = weights[near].mean(0)

order = np.argsort(weights, axis=1)[:, ::-1][:, :4]
values = np.take_along_axis(weights, order, axis=1)
values /= values.sum(1, keepdims=True)
values[values < 1e-5] = 0
values /= values.sum(1, keepdims=True)
order[values == 0] = 0
for name, data in [('_RIG_JOINTS', order.astype(np.float32)), ('_RIG_WEIGHTS', values.astype(np.float32))]:
    attribute = mesh.attributes.new(name, 'FLOAT_COLOR', 'POINT')
    attribute.data.foreach_set('color', data.ravel())
top.name = mesh.name = 'top_female_knight'
bpy.ops.object.select_all(action='DESELECT')
top.select_set(True)
bpy.context.view_layer.objects.active = top
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'top-fitted-unskinned.glb'), export_format='GLB', use_selection=True,
                         export_tangents=True, export_attributes=True, export_normals=True)
np.savez(OUTPUT / 'fit-data.npz', source=source, fitted=points, faces=faces, arm=arm, cap=cap, neck=neck,
         joints=order, weights=values, bone_names=np.array(names))
report = {'date': '2026-10-12', 'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'output_dir': str(OUTPUT.relative_to(ROOT)), 'triangles': len(faces), 'bone_names': names,
          'method': 'Original connected Tripo surface; as-rigid-as-possible sleeve fitting with fixed torso and shoulder-cap handles; enlarged bust fitted to actual female surface; uniform thorax weights and cloth-only elbow blending.',
          'bust': {'width_factor': 1.10, 'depth_factor': 1.18, 'target_front_clearance': .008, 'surface_corrections': corrections,
                   'maximum_extra_front_displacement': float(np.max(initial[:, 1] - points[:, 1]))},
          'source_bounds_blender': [source.min(0).tolist(), source.max(0).tolist()],
          'fitted_bounds_blender': [points.min(0).tolist(), points.max(0).tolist()],
          'arap': {'iterations': int(arap['iterations']), 'last_maximum_vertex_step': float(arap['residual']), 'fixed_vertices': int(fixed.sum())},
          'no_new_api_requests': True, 'status': 'Candidate; validation pending'}
(ROOT / 'doc/assets/modular-female-knight-top-fitting-v2.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report['bust']), flush=True)
