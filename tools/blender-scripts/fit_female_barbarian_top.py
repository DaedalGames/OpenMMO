import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_barbarian_top/tripo_v1'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v1'
OUTPUT.mkdir(exist_ok=True)
SCALE = .21
OFFSET = (-.028, .003, .779)
BUST_WIDTH = 1.18
BUST_DEPTH = 1.27
CLEARANCE = .006
STRAP_CLEARANCE = .002
JEWEL_CLEARANCE = .003
SMOOTHING = 16
PREVIEW = '--preview' in sys.argv
PAULDRON_BONE = next((a.split('=')[1] for a in sys.argv if a.startswith('--pauldron=')), 'RightShoulder')


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['female_body']
body_points = np.array([body.matrix_world @ vertex.co for vertex in body.data.vertices])
body_faces = [polygon.vertices[:] for polygon in body.data.polygons]

# The base mesh carries its underwear as separate islands; fit against skin only.
_, body_first, body_welded = np.unique(np.round(body_points, 6), axis=0, return_index=True, return_inverse=True)
body_welded = body_welded.ravel()
parent = np.arange(len(body_first))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for face in body_faces:
    roots = [find(body_welded[v]) for v in face]
    for r in roots[1:]:
        parent[find(r)] = find(roots[0])
labels = np.array([find(i) for i in range(len(body_first))])
skin_label = np.bincount(labels).argmax()
skin_faces = [face for face in body_faces if labels[body_welded[face[0]]] == skin_label]
surface = BVHTree.FromPolygons([Vector(p) for p in body_points], skin_faces)
joints = {bone.name: np.array(rig.matrix_world @ bone.head) for bone in rig.pose.bones}
names = [bone.name for bone in rig.data.bones]

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
top = next(obj for obj in set(bpy.data.objects) - before if obj.type == 'MESH')
transform = Matrix.Translation(Vector(OFFSET)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Scale(SCALE, 4)
top.data.transform(transform @ top.matrix_world)
top.matrix_world = Matrix.Identity(4)
mesh = top.data
source = np.array([vertex.co for vertex in mesh.vertices])
source_normals = np.array([normal.vector for normal in mesh.corner_normals])
loop_vertices = np.array([loop.vertex_index for loop in mesh.loops])
faces = np.array([polygon.vertices[:] for polygon in mesh.polygons])
x, y, z = source.T

pauldron = (x < -.062) & (z > .808)
jewel = (np.abs(x) < .02) & (z < .742) & (y < -.035)
bust = smooth((z - .695) / .03) * (1 - smooth((z - .80) / .03)) * smooth((.02 - y) / .03)

points = source.copy()
points[:, 0] *= 1 + (BUST_WIDTH - 1) * bust
points[:, 1] = y + (y - .0) * (BUST_DEPTH - 1) * bust


def signed(p):
    location, normal, _, _ = surface.find_nearest(Vector(p))
    offset = p - np.array(location)
    normal = np.array(normal)
    return np.linalg.norm(offset) * (1 if offset @ normal >= 0 else -1), normal


depth = np.zeros(len(points))
outward = np.zeros_like(points)
for i, p in enumerate(points):
    depth[i], outward[i] = signed(p)

tree = KDTree(len(points))
for i, p in enumerate(points):
    tree.insert(Vector(p), i)
tree.balance()
inner = np.array([min(depth[j] for _, j, _ in tree.find_range(Vector(p), .010)) for p in points])
layer = depth - inner
front = smooth((-.02 - points[:, 1]) / .02) * smooth((points[:, 2] - .70) / .02) * (1 - smooth((points[:, 2] - .79) / .015))
front *= 1 - smooth((np.abs(points[:, 0]) - .025) / .015)
straps = (points[:, 2] > .795) & ~pauldron
# The underbust band sits as close as the straps; its rim showed a dark gap from below.
underband = 1 - smooth((points[:, 2] - .70) / .015)
wanted = np.where(straps, STRAP_CLEARANCE, CLEARANCE - (CLEARANCE - STRAP_CLEARANCE) * underband) + layer
# Only the cleavage bridge is kept off the skin; cups, straps and band are drawn onto it.
wanted = np.where(front > .5, np.maximum(wanted, np.minimum(depth, CLEARANCE + layer + .02)), wanted)
targets = points + outward * (wanted - depth)[:, None]

# The band spans the fold under the bust, so seen from below its lower edge hung 1-2 cm in front
# of the sternum. Rest the lower edge near the centre on the ribs and let the strip tilt into the fold.
band = (1 - smooth((source[:, 2] - .705) / .01)) * (1 - smooth((np.abs(points[:, 0]) - .03) / .015))
band *= (points[:, 1] < -.02) & ~pauldron & ~jewel
back = np.array([0, 1, 0])
for i in np.where(band > 0)[0]:
    hit = surface.ray_cast(Vector(targets[i]), Vector(back), .05)
    if hit[0] is None:
        continue
    low, high = 0, max(hit[3] - wanted[i], 0) * band[i]
    for _ in range(12):
        mid = (low + high) / 2
        low, high = (mid, high) if signed(targets[i] + mid * back)[0] >= .002 + layer[i] else (low, mid)
    targets[i] += low * back

shoulder = joints['RightArm']
lift = np.array([-.55, 0, .83])
lift /= np.linalg.norm(lift)
rigid = points[pauldron].copy()
for step in range(80):
    clearance = min(signed(p)[0] for p in rigid)
    if clearance >= CLEARANCE:
        break
    rigid += lift * .001
targets[pauldron] = rigid
around = (np.linalg.norm(points[:, [0, 2]] - points[jewel][:, [0, 2]].mean(0), axis=1) < .035) & ~jewel
rigid = points[jewel] + (targets[around] - points[around]).mean(0)
for step in range(40):
    if min(signed(p)[0] for p in rigid) >= JEWEL_CLEARANCE:
        break
    rigid[:, 1] -= .0005
targets[jewel] = rigid


def vertex_colors(image):
    pixels = np.empty(image.size[0] * image.size[1] * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(image.size[1], image.size[0], 4)
    uv = np.array([loop.uv for loop in mesh.uv_layers.active.data])
    uv_pixels = np.clip(np.floor(uv * np.array(image.size)).astype(int), 0, np.array(image.size) - 1)
    colors = np.zeros((len(source), 3))
    np.add.at(colors, loop_vertices, pixels[uv_pixels[:, 1], uv_pixels[:, 0], :3])
    return colors / np.maximum(np.bincount(loop_vertices, minlength=len(source))[:, None], 1)


# ARAP stiffness has always sampled the body texture (first Color_ image); kept so the reviewed fit doesn't shift.
colors = vertex_colors(next(image for image in bpy.data.images if image.name.startswith('Color_')))
own = vertex_colors(next(node.image for node in top.active_material.node_tree.nodes
                         if node.type == 'TEX_IMAGE' and node.image.name.startswith('Color_')))
saturation = 1 - own.min(1) / np.maximum(own.max(1), 1e-6)
# The ring hinges where it threads the plate; swing it back so it rests on the band, not in mid-air.
ring = jewel & (source[:, 2] < .716) & (saturation > .45)
rigid = targets[ring]
pivot = rigid[rigid[:, 2] > rigid[:, 2].max() - .002].mean(0)
for degrees in range(45, 0, -1):
    tilted = (np.array(Matrix.Rotation(math.radians(degrees), 3, 'X')) @ (rigid - pivot).T).T + pivot
    if min(signed(p)[0] for p in tilted) >= JEWEL_CLEARANCE:
        targets[ring] = tilted
        break
contact = (layer < .002) & ~pauldron & ~jewel
fixed = contact | pauldron | jewel

np.savez(OUTPUT / 'arap-input.npz', points=points, faces=faces, colors=colors, fixed=fixed, targets=targets)
subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'tools/outfits/fit_female_knight_top_surface.py'),
                str(OUTPUT / 'arap-input.npz')], check=True)
arap = np.load(OUTPUT / 'arap-result.npz')
points = arap['points'].copy()
for i, point in enumerate(points):
    distance, normal = signed(point)
    if distance < .001:
        points[i] += normal * (.001 - distance)
final_depth = np.array([signed(p)[0] for p in points])

normal_values = np.einsum('nij,nj->ni', arap['rotations'][loop_vertices], source_normals)
normal_values /= np.linalg.norm(normal_values, axis=1, keepdims=True)
for vertex, point in zip(mesh.vertices, points):
    vertex.co = point
mesh.update()
mesh.normals_split_custom_set(normal_values.tolist())
index = {name: i for i, name in enumerate(names)}
body_weights = np.zeros((len(body_points), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        name = body.vertex_groups[group.group].name
        if name in index:
            body_weights[vertex.index, index[name]] = group.weight
skin_vertices = np.unique([v for face in skin_faces for v in face])
skin_tree = KDTree(len(skin_vertices))
for i in skin_vertices:
    skin_tree.insert(Vector(body_points[i]), int(i))
skin_tree.balance()
weights = np.zeros((len(points), len(names)))
for i, p in enumerate(points):
    neighbors = skin_tree.find_n(Vector(p), 8)
    factors = np.array([1 / max(distance, .001) ** 2 for _, _, distance in neighbors])
    weights[i] = (body_weights[[j for _, j, _ in neighbors]] * factors[:, None]).sum(0) / factors.sum()

cups = ((bust > .5) & (points[:, 1] < -.02) & ~pauldron) | jewel
# Cups follow the skin so they stay on the breasts when the arms move; the jewel and pauldron are hard shells.
rigid_groups = [jewel, pauldron]
weights[jewel] = 0
weights[jewel, index['Spine1']], weights[jewel, index['Spine2']] = .9, .1
weights[pauldron] = 0
weights[pauldron, index[PAULDRON_BONE]] = 1

edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
_, first, welded = np.unique(np.round(source, 7), axis=0, return_index=True, return_inverse=True)
welded = welded.ravel()
adj = [[] for _ in first]
for a, b in welded[edges]:
    if a != b:
        adj[a].append(b)
        adj[b].append(a)
locked = np.zeros(len(first), dtype=bool)
for group in rigid_groups:
    locked[welded[group]] = True
unique_weights = weights[first].copy()
original_weights = unique_weights.copy()
for _ in range(SMOOTHING):
    updated = unique_weights.copy()
    for i, neighbors in enumerate(adj):
        if not locked[i] and neighbors:
            updated[i] = .5 * unique_weights[i] + .5 * unique_weights[neighbors].mean(0)
    unique_weights = updated
# Cups take smoothed skin weights; straps away from the shells keep the skin's own weights so they move with it.
shell_points = points[jewel | pauldron]
shells = KDTree(len(shell_points))
for i, point in enumerate(shell_points):
    shells.insert(Vector(point), i)
shells.balance()
reach = smooth((np.array([shells.find(Vector(point))[2] for point in points]) - .005) / .025)[:, None]
reach[cups & ~jewel] = 0
weights = reach * weights + (1 - reach) * unique_weights[welded]
for side, sign in [('Left', -1), ('Right', 1)]:
    opposite = [index[name] for name in names if name.startswith(side) and ('Shoulder' in name or 'Arm' in name)]
    weights[np.ix_(points[:, 0] * sign > 0, opposite)] = 0
weights /= weights.sum(1, keepdims=True)

order = np.argsort(weights, axis=1)[:, ::-1][:, :4]
values = np.take_along_axis(weights, order, axis=1)
values[values < .02] = 0
values /= values.sum(1, keepdims=True)
order[values == 0] = 0
for name, data in [('_RIG_JOINTS', order.astype(np.float32)), ('_RIG_WEIGHTS', values.astype(np.float32))]:
    attribute = mesh.attributes.new(name, 'FLOAT_COLOR', 'POINT')
    attribute.data.foreach_set('color', data.ravel())
top.name = mesh.name = 'top_female_barbarian'
bpy.ops.object.select_all(action='DESELECT')
top.select_set(True)
bpy.context.view_layer.objects.active = top
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'top-fitted-unskinned.glb'), export_format='GLB', use_selection=True,
                         export_tangents=True, export_attributes=True, export_normals=True)
np.savez(OUTPUT / 'fit-data.npz', source=source, fitted=points, faces=faces, pauldron=pauldron, cups=cups,
         contact=contact, jewel=jewel, depth=final_depth, joints=order, weights=values, bone_names=np.array(names))
summary = lambda group: {names[i]: round(float(w), 3) for i, w in enumerate(weights[group].mean(0)) if w > .01}
report = {'date': '2026-10-15', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'output_dir': str(OUTPUT.relative_to(ROOT)), 'triangles': len(faces),
          'alignment': {'scale': SCALE, 'offset_blender': OFFSET, 'rotation_z_degrees': -90},
          'bust': {'width_factor': BUST_WIDTH, 'depth_factor': BUST_DEPTH, 'clearance': CLEARANCE, 'strap_clearance': STRAP_CLEARANCE,
                   'jewel_clearance': JEWEL_CLEARANCE},
          'method': 'Global alignment, bust pre-scale, then ARAP with contact vertices targeted to body surface plus layer offset. Cups bridge the cleavage (push-out only); the lower band edge near the centre rests on the ribs. Pauldron and gem plate placed rigidly outside the skin; the ring hinges back from the plate onto the band.',
          'arap': {'iterations': int(arap['iterations']), 'last_maximum_vertex_step': float(arap['residual']),
                   'fixed_vertices': int(fixed.sum())},
          'rest_clearance': {'penetrating_vertices': int((final_depth < 0).sum()), 'minimum': float(final_depth.min())},
          'weights': {'cups': summary(cups), 'pauldron': summary(pauldron), 'pauldron_bone': PAULDRON_BONE,
                      'method': 'Inverse-distance transfer from skin; cups take smoothed skin weights, the jewel Spine1 0.9/Spine2 0.1 and the pauldron one shoulder bone (both rigid); straps and band smoothed across the welded surface.'},
          'no_new_api_requests': True, 'status': 'Candidate; validation pending'}
(ROOT / 'doc/assets/modular-female-barbarian-top-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report['weights']), flush=True)

if PREVIEW:
    import bmesh
    edit = bmesh.new()
    edit.from_mesh(body.data)
    edit.faces.ensure_lookup_table()
    bmesh.ops.delete(edit, geom=[f for f in edit.faces if labels[body_welded[f.verts[0].index]] != skin_label
                                 and .64 < body_points[f.verts[0].index][2] < .86], context='FACES')
    edit.to_mesh(body.data)
    print('preview hidden body faces', len(body_faces) - len(body.data.polygons), flush=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'TEXTURE'
    scene.render.resolution_x = scene.render.resolution_y = 700
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = .32
    scene.camera = camera
    center = Vector((0, 0, .78))
    for view, offset in [('front', (0, -1, 0)), ('left', (1, 0, 0)), ('back', (0, 1, 0)), ('right', (-1, 0, 0))]:
        camera.location = center + Vector(offset)
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUTPUT / 'preview' / f'{view}.png')
        bpy.ops.render.render(write_still=True)

print(json.dumps({'penetrating': int((final_depth < 0).sum()), 'min_depth': float(final_depth.min()),
                  'pauldron': int(pauldron.sum()), 'jewel': int(jewel.sum()), 'fixed': int(fixed.sum()),
                  'arap_iterations': int(arap['iterations'])}), flush=True)
