import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_rogue_top/tripo_v1'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v1'
OUTPUT.mkdir(exist_ok=True)


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def islands(points, faces):
    _, inverse = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    inverse = inverse.ravel()
    parent = np.arange(inverse.max() + 1)

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for face in faces:
        a = root(inverse[face[0]])
        for v in face[1:]:
            parent[root(inverse[v])] = a
    return np.array([root(i) for i in inverse])


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['female_body']
bp = np.array([body.matrix_world @ v.co for v in body.data.vertices])
bf = np.array([f.vertices[:] for f in body.data.polygons])
labels = islands(bp, bf)
skin_label = np.bincount(labels).argmax()
skin_faces = bf[(labels[bf] == skin_label).all(1)]
surface = BVHTree.FromPolygons([Vector(p) for p in bp], skin_faces.tolist())
names = [bone.name for bone in rig.data.bones]
bones = {bone.name: np.array(rig.matrix_world @ bone.head) for bone in rig.pose.bones}
body_weights = np.zeros((len(bp), len(names)))
for v in body.data.vertices:
    for group in v.groups:
        name = body.vertex_groups[group.group].name
        if name in names:
            body_weights[v.index, names.index(name)] = group.weight

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
top = next(o for o in set(bpy.data.objects) - before if o.type == 'MESH')
transform = Matrix.Translation((0, 0, 1.28)) @ Matrix.Rotation(-math.pi / 2 - math.atan2(.1606722474, .9870077968), 4, 'Z') @ Matrix.Scale(.6, 4)
top.data.transform(transform @ top.matrix_world)
top.matrix_world = Matrix.Identity(4)
mesh = top.data
source = np.array([v.co for v in mesh.vertices])
faces = np.array([f.vertices[:] for f in mesh.polygons])
x, y, z = source.T
points = source.copy()
points[:, 0] -= .006
points[:, 2] = np.interp(z, [1.0, 1.13, 1.27, 1.39, 1.47, 1.55], [1.05, 1.18, 1.365, 1.465, 1.515, 1.565])

threshold = np.interp(z, [1.0, 1.23, 1.34, 1.43, 1.48, 1.55], [.17, .175, .175, .155, .18, .30])
sleeve = smooth((np.abs(x) - threshold) / .035)
sleeve *= 1 - smooth((y - .065) / .05) * smooth((z - 1.38) / .06)
sleeve_centers = np.zeros_like(points)
sleeve_radials = np.zeros_like(points)
for side, sign in [('Left', 1), ('Right', -1)]:
    chosen = x * sign > 0
    shoulder = np.array([sign * .19, 0, 1.43])
    axis = np.array([sign * .20, 0, -.98])
    axis /= np.linalg.norm(axis)
    across = np.array([.98, 0, sign * .20])
    local = source - shoulder
    along = local @ axis
    u = local @ across
    v = local[:, 1]
    upper = bones[side + 'Arm']
    elbow = bones[side + 'ForeArm']
    hand = bones[side + 'Hand']
    upper_axis = (elbow - upper) / np.linalg.norm(elbow - upper)
    lower_axis = (hand - elbow) / np.linalg.norm(hand - elbow)
    fraction = smooth((along - .17) / .065)
    direction = (1 - fraction[:, None]) * upper_axis + fraction[:, None] * lower_axis
    direction /= np.linalg.norm(direction, axis=1)[:, None]
    center = upper + np.minimum(along / .21, 1)[:, None] * (elbow - upper)
    center += np.maximum(along - .21, 0)[:, None] * lower_axis
    radial_axis = np.column_stack([-direction[:, 2], np.zeros(len(points)), direction[:, 0]])
    radial_axis *= sign
    if sign < 0:
        u = -u
    radial = u[:, None] * radial_axis + v[:, None] * np.array([0, 1, 0])
    sleeve_centers[chosen] = center[chosen]
    sleeve_radials[chosen] = radial[chosen]
    mapped = center + radial
    blend = sleeve * chosen
    points = points * (1 - blend[:, None]) + mapped * blend[:, None]

_, first, welded = np.unique(np.round(source, 7), axis=0, return_index=True, return_inverse=True)
welded = welded.ravel()
edges = np.unique(np.sort(welded[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)], axis=1), axis=0)
adj = [set() for _ in first]
for a, b in edges:
    if a != b:
        adj[a].add(int(b))
        adj[b].add(int(a))
displacement = (points - source)[first]
for _ in range(12):
    updated = displacement.copy()
    for i, neighbors in enumerate(adj):
        if neighbors:
            updated[i] = .65 * displacement[i] + .35 * displacement[list(neighbors)].mean(0)
    displacement = updated
points = source + displacement[welded]
for i in np.flatnonzero(sleeve > .65):
    center = sleeve_centers[i]
    radial = sleeve_radials[i]
    length = np.linalg.norm(radial)
    direction = radial / max(length, 1e-8)
    hit, _, _, distance = surface.ray_cast(Vector(center), Vector(direction), .18)
    if hit is not None:
        radius = distance + .009 + max(length - .045, 0) * .5
        points[i] = center + direction * radius

hood = smooth((.17 - np.abs(x)) / .07) * smooth((y - .06) / .05) * smooth((z - 1.39) / .06)
for iteration in range(4):
    for i, p in enumerate(points):
        hit, normal, _, distance = surface.find_nearest(Vector(p))
        n = np.array(normal)
        signed = np.dot(p - np.array(hit), n)
        clearance = .010 if sleeve[i] > .5 else .009
        if signed < clearance:
            points[i] += n * (clearance - signed)

def clear_faces(points, iterations, clearance, detailed=False):
    barycentric = [(1/3, 1/3, 1/3), (.5, .5, 0), (0, .5, .5), (.5, 0, .5)]
    if detailed:
        barycentric += [(a / 4, b / 4, (4 - a - b) / 4) for a in range(5) for b in range(5 - a)]
    for iteration in range(iterations):
        correction = np.zeros((len(first), 3))
        counts = np.zeros(len(first))
        deepest = 0
        for bary in barycentric:
            samples = np.einsum('fkj,k->fj', points[faces], bary)
            for face, p in zip(faces, samples):
                hit, normal, _, _ = surface.find_nearest(Vector(p))
                signed = np.dot(p - np.array(hit), normal)
                if signed < clearance:
                    delta = np.array(normal) * (clearance - signed)
                    for vertex in set(welded[face]):
                        correction[vertex] += delta
                        counts[vertex] += 1
                    deepest = max(deepest, clearance - signed)
        if deepest < .0002:
            break
        correction /= np.maximum(counts[:, None], 1)
        points += correction[welded] * 1.25
    return points


points = clear_faces(points, 24, .003)

shoulder_region = (source[first, 2] > 1.40) & (np.abs(source[first, 0]) > .14)
for _ in range(4):
    q = points[first].copy()
    updated = q.copy()
    for i in np.flatnonzero(shoulder_region):
        if adj[i]:
            updated[i] = .7 * q[i] + .3 * q[list(adj[i])].mean(0)
    points = updated[welded]
for i, p in enumerate(points):
    hit, normal, _, _ = surface.find_nearest(Vector(p))
    signed = np.dot(p - np.array(hit), normal)
    if signed < .007:
        points[i] += np.array(normal) * (.007 - signed)

weights = np.zeros((len(points), len(names)))
for i, p in enumerate(points):
    hit, _, fi, _ = surface.find_nearest(Vector(p))
    indices = skin_faces[fi]
    a, b, c = bp[indices]
    mat = np.column_stack((b - a, c - a))
    uv = np.linalg.lstsq(mat, np.array(hit) - a, rcond=None)[0]
    bary = np.clip([1 - uv.sum(), *uv], 0, 1)
    bary /= bary.sum()
    weights[i] = bary @ body_weights[indices]
    if hood[i]:
        weights[i] *= 1 - hood[i]
        weights[i, names.index('Spine2')] += .85 * hood[i]
        weights[i, names.index('Neck')] += .15 * hood[i]

unique_weights = weights[first].copy()
for _ in range(6):
    updated = unique_weights.copy()
    for i, neighbors in enumerate(adj):
        if neighbors:
            updated[i] = .5 * unique_weights[i] + .5 * unique_weights[list(neighbors)].mean(0)
    unique_weights = updated
weights = unique_weights[welded]
part_labels = islands(source, faces)
for label in np.unique(part_labels):
    chosen = part_labels == label
    if len(np.unique(welded[chosen])) < 120:
        weights[chosen] = weights[chosen].mean(0)
for side, sign in [('Left', -1), ('Right', 1)]:
    opposite = [j for j, name in enumerate(names) if name.startswith(side) and ('Shoulder' in name or 'Arm' in name)]
    weights[np.ix_(points[:, 0] * sign > .005, opposite)] = 0
order = np.argsort(weights, axis=1)[:, -4:][:, ::-1]
values = np.take_along_axis(weights, order, axis=1)
values[values < .005] = 0
values /= values.sum(1, keepdims=True)
order[values == 0] = 0

animation_fit = []
pose_path = OUTPUT / 'animation-samples.json'
if '--animation-clearance' in sys.argv:
    assert pose_path.exists(), 'Run the runtime validator once to export canonical animation samples'
    validation = json.loads((OUTPUT / 'animation-validation.json').read_text())
    assert validation['base_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
    from outfits.skinning import deform
    base_doc, _ = read_glb(BODY)
    canonical = [base_doc['nodes'][j]['name'] for j in base_doc['skins'][0]['joints']]
    conversion = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    named_order = [canonical.index(name) for name in names]
    body_order = np.argsort(body_weights, axis=1)[:, -4:]
    body_values = np.take_along_axis(body_weights, body_order, axis=1)
    arm_columns = [j for j, name in enumerate(names) if 'Arm' in name or 'Hand' in name]
    arm_skin = body_weights[:, arm_columns].sum(1) > .35
    torso_faces = skin_faces[~arm_skin[skin_faces].any(1)]
    poses = [(np.tile(np.eye(4), (65, 1, 1)), surface, BVHTree.FromPolygons([Vector(p) for p in bp], torso_faces.tolist()))]
    for sample in json.loads(pose_path.read_text()):
        if sample['sample'] % 4:
            continue
        matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)[named_order]
        matrices = conversion @ matrices @ conversion.T
        posed_body = deform(bp, body_order, body_values, matrices)
        posed_surface = BVHTree.FromPolygons([Vector(p) for p in posed_body], skin_faces.tolist())
        torso_surface = BVHTree.FromPolygons([Vector(p) for p in posed_body], torso_faces.tolist())
        poses.append((matrices, posed_surface, torso_surface))
    for iteration in range(8):
        correction = np.zeros((len(first), 3))
        counts = np.zeros(len(first))
        deepest = 0
        for pose_index, (matrices, posed_surface, torso_surface) in enumerate(poses):
            blended = np.einsum('nk,nkij->nij', values, matrices[order])
            inverse_linear = np.linalg.inv(blended[:, :3, :3])
            posed = np.einsum('nij,nj->ni', blended[:, :3, :3], points) + blended[:, :3, 3]
            for query, indices in [(posed, np.arange(len(points))[:, None]), (posed[faces].mean(1), faces)]:
                for p, vertices in zip(query, indices):
                    tree = posed_surface if pose_index == 0 or sleeve[vertices].mean() > .5 else torso_surface
                    hit, normal, _, _ = tree.find_nearest(Vector(p))
                    signed = np.dot(p - np.array(hit), normal)
                    if signed < .003:
                        deepest = max(deepest, .003 - signed)
                        delta = np.array(normal) * min(.003 - signed, .018)
                        for vertex in vertices:
                            correction[welded[vertex]] += inverse_linear[vertex] @ delta
                            counts[welded[vertex]] += 1
        correction /= np.maximum(counts[:, None], 1)
        for _ in range(2):
            updated = correction.copy()
            for i, neighbors in enumerate(adj):
                if neighbors:
                    updated[i] = .7 * correction[i] + .3 * correction[list(neighbors)].mean(0)
            correction = updated
        length = np.linalg.norm(correction, axis=1)
        correction *= np.minimum(1, .008 / np.maximum(length, 1e-10))[:, None]
        points += correction[welded] * 1.2
        animation_fit.append({'iteration': iteration + 1, 'maximum_penetration_before_m': deepest, 'maximum_rest_correction_m': float(length.max())})
        print('Animation clearance', animation_fit[-1], flush=True)
        if deepest < .001:
            break

points = clear_faces(points, 24, .007, detailed=True)

for vertex, point in zip(mesh.vertices, points):
    vertex.co = point
mesh.update()
face_normals = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
normal_sum = np.zeros((len(first), 3))
for k in range(3):
    np.add.at(normal_sum, welded[faces[:, k]], face_normals)
normal_sum /= np.maximum(np.linalg.norm(normal_sum, axis=1, keepdims=True), 1e-12)
mesh.normals_split_custom_set([normal_sum[welded[loop.vertex_index]] for loop in mesh.loops])
for group in list(top.vertex_groups):
    top.vertex_groups.remove(group)
for name in names:
    top.vertex_groups.new(name=name)
for i in range(len(points)):
    for j, weight in zip(order[i], values[i]):
        if weight:
            top.vertex_groups[int(j)].add([i], float(weight), 'REPLACE')
modifier = top.modifiers.new('Female rig', 'ARMATURE')
modifier.object = rig
top.parent = rig
top.name = mesh.name = 'top_female_rogue'
for key, data in [('_RIG_JOINTS', order), ('_RIG_WEIGHTS', values)]:
    attr = mesh.attributes.new(key, 'FLOAT_COLOR', 'POINT')
    attr.data.foreach_set('color', data.astype(np.float32).ravel())
bpy.ops.object.select_all(action='DESELECT')
top.select_set(True)
bpy.context.view_layer.objects.active = top
intermediate = OUTPUT / 'geometry.glb'
modifier.show_viewport = modifier.show_render = False
bpy.ops.export_scene.gltf(filepath=str(intermediate), export_format='GLB', use_selection=True,
                          export_animations=False, export_skins=False, export_attributes=True, export_tangents=True)
modifier.show_viewport = modifier.show_render = True

doc, raw = read_glb(intermediate)
raw = bytearray(raw)
base, base_raw = read_glb(BODY)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
source_order = accessor(doc, raw, attrs.pop('_RIG_JOINTS')).astype(np.uint16)
source_values = accessor(doc, raw, attrs.pop('_RIG_WEIGHTS'))
canonical_names = [base['nodes'][j]['name'] for j in base['skins'][0]['joints']]
remap_order = np.array([canonical_names.index(name) for name in names])
attrs['JOINTS_0'] = add_accessor(doc, raw, remap_order[source_order], 'VEC4', 5123)
attrs['WEIGHTS_0'] = add_accessor(doc, raw, source_values, 'VEC4')
ids = base['skins'][0]['joints']
remap = {old: new for new, old in enumerate(ids)}
doc['nodes'] = [copy.deepcopy(base['nodes'][i]) for i in ids]
for node in doc['nodes']:
    if 'children' in node:
        node['children'] = [remap[i] for i in node['children'] if i in remap]
children = {i for node in doc['nodes'] for i in node.get('children', [])}
doc['nodes'].append({'name': 'Armature', 'children': [i for i in range(len(ids)) if i not in children]})
doc['nodes'].append({'name': 'top_female_rogue', 'mesh': 0, 'skin': 0, 'extras': {'rig_id': 'human_female_01_local_v1', 'part_id': 'top_female_rogue'}})
skin = copy.deepcopy(base['skins'][0])
skin['joints'] = list(range(len(ids)))
if 'skeleton' in skin:
    skin['skeleton'] = remap[skin['skeleton']]
skin['inverseBindMatrices'] = add_accessor(doc, raw, accessor(base, base_raw, base['skins'][0]['inverseBindMatrices']), 'MAT4')
doc['skins'] = [skin]
doc['scenes'] = [{'nodes': [len(ids), len(ids) + 1]}]
doc['scene'] = 0
doc.pop('animations', None)
doc['buffers'] = [{'byteLength': len(raw)}]
write_glb(OUTPUT / 'top_female_rogue.glb', doc, raw)
intermediate.unlink()
np.savez(OUTPUT / 'fit-data.npz', source=source, points=points, faces=faces, sleeve=sleeve, hood=hood,
         joints=order, weights=values, bone_names=np.array(names))

# Hide only the separate upper underwear for the fitting review.
underwear = np.zeros(len(bf), dtype=bool)
for label in np.unique(labels):
    q = bp[labels == label]
    if label != skin_label and q[:, 2].min() > 1.15 and q[:, 2].max() < 1.55:
        underwear |= (labels[bf] == label).all(1)
edit = bmesh.new()
edit.from_mesh(body.data)
edit.faces.ensure_lookup_table()
bmesh.ops.delete(edit, geom=[edit.faces[i] for i in np.flatnonzero(underwear)], context='FACES')
edit.to_mesh(body.data)
edit.free()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-rogue-top.blend'))
bpy.context.view_layer.update()
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.color_type = 'TEXTURE'
scene.display.shading.light = 'STUDIO'
scene.render.resolution_x = scene.render.resolution_y = 1000
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 1.12
scene.camera = camera
(OUTPUT / 'review').mkdir(exist_ok=True)
for name, offset in [('front', (0, -3, 0)), ('back', (0, 3, 0)), ('side', (3, 0, 0)), ('angle', (2, -3, .2))]:
    center = Vector((0, 0, 1.28))
    camera.location = center + Vector(offset)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUTPUT / 'review' / f'{name}.png')
    bpy.ops.render.render(write_still=True)
report = {'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'triangles': len(faces), 'vertices': len(points), 'bones': len(names), 'date': '2026-10-25',
          'method': 'Piecewise torso height alignment, articulated sleeve mapping to actual female arm joints, skin clearance projection, barycentric skin weight transfer, rigid accessory islands, canonical hierarchy and exact inverse bind matrices.',
          'animation_clearance_iterations': animation_fit, 'no_new_api_requests': True, 'status': 'Fitted and rigged; animation review pending'}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
