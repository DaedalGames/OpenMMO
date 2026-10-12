import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
VERSION = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'v4'
assert VERSION in ['v1', 'v2', 'v3', 'v4']
OUTPUT = DIRECTORY / f'fitted_{VERSION}'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT.mkdir(exist_ok=True)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


doc, binary = read_glb(SOURCE)
binary = bytearray(binary)
base, base_binary = read_glb(BODY)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
original = accessor(doc, binary, attrs['POSITION'])
node = doc['nodes'][0]
matrix = np.array(node['matrix']).reshape(4, 4).T
rotation = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]]) @ matrix[:3, :3]
source = original @ rotation.T
points = source * .27
points[:, 1] += .645 - source[:, 1].max() * .27
points[:, 2] += .010
initial = points.copy()
body_primitive = base['meshes'][0]['primitives'][0]
body_points = accessor(base, base_binary, body_primitive['attributes']['POSITION'])
body_faces = accessor(base, base_binary, body_primitive['indices']).reshape(-1, 3)
lower_faces = body_faces[(abs(body_points[body_faces, 0]) < .14).all(1)
                         & (body_points[body_faces, 1] < .66).all(1)]
surface = BVHTree.FromPolygons([Vector(p) for p in body_points], lower_faces.tolist())
pushes = []
for i, point in enumerate(points):
    center = np.array([0., point[1], -.015])
    if abs(point[0]) > .055:
        center[0] = np.sign(point[0]) * .060 * float(1 - smooth((point[1] - .50) / .07))
    offset = point - center
    radius = np.linalg.norm(offset)
    direction = offset / radius
    hit, _, _, _ = surface.ray_cast(Vector(center + direction * .22), Vector(-direction), .22)
    if hit is None:
        continue
    body_radius = np.dot(np.array(hit) - center, direction)
    desired = max(radius, body_radius + .008 + .15 * radius)
    points[i] = center + direction * desired
    pushes.append(desired - radius)

faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
waist_review = None
if VERSION in ['v2', 'v3', 'v4']:
    previous = points.copy()
    garment = BVHTree.FromPolygons([Vector(p) for p in previous], faces.tolist())
    previous_mask = json.loads((DIRECTORY / 'fitted_v1/body-occlusion.json').read_text())
    skin_face_mask = (abs(body_points[body_faces, 0]) < .14).all(1) & (body_points[body_faces, 1] < .66).all(1)
    skin_face_mask[previous_mask['hide_triangle_indices']] = False
    skin_surface = BVHTree.FromPolygons([Vector(p) for p in body_points], body_faces[skin_face_mask].tolist())
    before_gaps, after_gaps = [], []
    for i, point in enumerate(previous):
        amount = float(smooth((point[1] - .56) / .05))
        if amount == 0:
            continue
        center = np.array([0., point[1], -.015])
        offset = point - center
        radius = np.linalg.norm(offset)
        direction = offset / radius
        hit, _, _, _ = skin_surface.ray_cast(Vector(center + direction * .22), Vector(-direction), .22)
        if hit is None:
            continue
        body_radius = np.dot(np.array(hit) - center, direction)
        inner, _, _, _ = garment.ray_cast(Vector(center), Vector(direction), .22)
        relief = 0 if inner is None else min(.004, .6 * max(0, radius - np.dot(np.array(inner) - center, direction)))
        target_radius = body_radius + .004 + relief
        fitted_radius = radius * (1 - amount) + target_radius * amount
        points[i] = center + direction * fitted_radius
        if point[1] >= .615:
            before_gaps.append(radius - body_radius)
            after_gaps.append(fitted_radius - body_radius)
    waist_review = {
        'region_min_height': .615, 'vertices': len(after_gaps),
        'before_radial_clearance': {'min': float(min(before_gaps)), 'median': float(np.median(before_gaps)), 'max': float(max(before_gaps))},
        'after_radial_clearance': {'min': float(min(after_gaps)), 'median': float(np.median(after_gaps)), 'max': float(max(after_gaps))},
        'maximum_inward_displacement': float(np.linalg.norm(points - previous, axis=1).max()),
        'blend_height_range': [.56, .61], 'lower_vertices_unchanged': bool(np.array_equal(points[previous[:, 1] <= .56], previous[previous[:, 1] <= .56])),
        'scope': 'Rest pose radial clearance to actual skin triangles; lower underwear excluded. Preserve small plate/strap relief. Motion collision approval remains separate.'
    }
    assert min(after_gaps) >= .00399 and max(after_gaps) <= .00801

curve_review = None
if VERSION in ['v3', 'v4']:
    previous = points.copy()
    edges = previous[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]

    def half_width(height, edge_points):
        a, b = edge_points[:, 0], edge_points[:, 1]
        pick = ((a[:, 1] < height) & (b[:, 1] >= height)) | ((b[:, 1] < height) & (a[:, 1] >= height))
        a, b = a[pick], b[pick]
        section = a + (b - a) * ((height - a[:, 1]) / (b[:, 1] - a[:, 1]))[:, None]
        return float(abs(section[:, 0]).max())

    top_height, bottom_height = .635, .565
    heights = np.linspace(bottom_height, top_height, 501)
    old_widths = np.array([half_width(height, edges) for height in heights])
    hip_width, waist_width = old_widths[0], old_widths[-1]
    t = (top_height - heights) / (top_height - bottom_height)
    target_widths = waist_width + (hip_width - waist_width) * (2 * t - t * t)
    for i, point in enumerate(previous):
        if not bottom_height < point[1] < top_height or abs(point[0]) <= .035:
            continue
        old_width = np.interp(point[1], heights, old_widths)
        target_width = np.interp(point[1], heights, target_widths)
        outward = max(0, target_width - old_width)
        side_amount = float(smooth((abs(point[0]) - .035) / (old_width - .035)))
        points[i, 0] += np.sign(point[0]) * outward * side_amount
    new_edges = points[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
    sample_heights = np.linspace(bottom_height, top_height, 15)
    curve_review = {
        'method': 'Convex quadratic side silhouette loft between fitted waist and hip anchors; outward-only lateral deformation with smooth falloff toward central guards.',
        'height_range': [bottom_height, top_height], 'waist_half_width': float(waist_width), 'hip_half_width': float(hip_width),
        'maximum_outward_displacement': float(np.linalg.norm(points - previous, axis=1).max()),
        'belt_vertices_unchanged': bool(np.array_equal(points[previous[:, 1] >= top_height], previous[previous[:, 1] >= top_height])),
        'lower_vertices_unchanged': bool(np.array_equal(points[previous[:, 1] <= bottom_height], previous[previous[:, 1] <= bottom_height])),
        'center_vertices_unchanged': bool(np.array_equal(points[abs(previous[:, 0]) <= .035], previous[abs(previous[:, 0]) <= .035])),
        'profile': [{'height': float(height), 'before_half_width': half_width(height, edges),
                     'after_half_width': half_width(height, new_edges)} for height in sample_heights],
    }

depth_review = None
if VERSION == 'v4':
    previous = points.copy()
    skin_edges = body_points[body_faces[skin_face_mask][:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
    heights = np.linspace(points[:, 1].min(), .645, 501)
    front_envelope = []
    for height in heights:
        a, b = skin_edges[:, 0], skin_edges[:, 1]
        pick = ((a[:, 1] < height) & (b[:, 1] >= height)) | ((b[:, 1] < height) & (a[:, 1] >= height))
        a, b = a[pick], b[pick]
        section = a + (b - a) * ((height - a[:, 1]) / (b[:, 1] - a[:, 1]))[:, None]
        front_envelope.append(max(.050, float(section[:, 2].max()) + .006))
    anchors = np.interp(points[:, 1], heights, front_envelope)
    transition = .010
    t = np.clip((points[:, 2] - anchors + transition) / (2 * transition), 0, 1)
    excess = np.where(points[:, 2] >= anchors + transition,
                      points[:, 2] - anchors, 2 * transition * (t ** 3 - .5 * t ** 4))
    amount = .70 * smooth((.635 - points[:, 1]) / .055)
    points[:, 2] -= amount * excess
    moved = points[:, 2] < previous[:, 2] - 1e-8
    depth_review = {
        'method': 'Compress forward projection toward a height-dependent plane outside the skin front envelope; smooth depth and height transitions. Rear surface and front-view coordinates remain unchanged.',
        'maximum_compression': .70, 'skin_envelope_clearance': .006,
        'minimum_anchor_depth': .050, 'depth_transition_half_width': transition,
        'height_transition': [.580, .635], 'moved_vertices': int(moved.sum()),
        'maximum_inward_displacement': float((previous[:, 2] - points[:, 2]).max()),
        'front_view_coordinates_unchanged': bool(np.array_equal(previous[:, :2], points[:, :2])),
        'belt_vertices_unchanged': bool(np.array_equal(previous[previous[:, 1] >= .635], points[previous[:, 1] >= .635])),
        'rear_vertices_unchanged': bool(np.array_equal(previous[previous[:, 2] <= 0], points[previous[:, 2] <= 0])),
        'sample_anchors': [{'height': float(height), 'depth': float(np.interp(height, heights, front_envelope))}
                           for height in [.635, .620, .600, .580, .560, .540, .520, .500, .480, .460, .440, .420]],
    }

normals = accessor(doc, binary, attrs['NORMAL']) @ rotation.T
unique, first, welded = np.unique(np.round(initial, 7), axis=0, return_index=True, return_inverse=True)
local_rotations = np.repeat(np.eye(3)[None], len(first), axis=0)
for i in range(len(first)):
    distances = np.linalg.norm(unique - unique[i], axis=1)
    neighbors = np.argsort(distances)[1:13]
    old = unique[neighbors] - unique[i]
    new = points[first[neighbors]] - points[first[i]]
    jacobian = np.linalg.lstsq(np.vstack([old, np.eye(3) * .0003]),
                              np.vstack([new, np.eye(3) * .0003]), rcond=None)[0].T
    u, _, vt = np.linalg.svd(jacobian)
    if np.linalg.det(u @ vt) < 0:
        u[:, -1] *= -1
    local_rotations[i] = u @ vt
normals = np.einsum('nij,nj->ni', local_rotations[welded], normals)
normals /= np.linalg.norm(normals, axis=1, keepdims=True)

uv = accessor(doc, binary, attrs['TEXCOORD_0'])
tan1, tan2 = np.zeros_like(points), np.zeros_like(points)
a, b, c = faces.T
ab, ac = points[b] - points[a], points[c] - points[a]
uv_ab, uv_ac = uv[b] - uv[a], uv[c] - uv[a]
determinant = uv_ab[:, 0] * uv_ac[:, 1] - uv_ab[:, 1] * uv_ac[:, 0]
assert np.all(abs(determinant) > 1e-12)
directions = (ab * uv_ac[:, 1, None] - ac * uv_ab[:, 1, None]) / determinant[:, None]
bitangents = (ac * uv_ab[:, 0, None] - ab * uv_ac[:, 0, None]) / determinant[:, None]
for corners in faces.T:
    np.add.at(tan1, corners, directions)
    np.add.at(tan2, corners, bitangents)
tangents = tan1 - normals * (normals * tan1).sum(1, keepdims=True)
invalid = np.linalg.norm(tangents, axis=1) < 1e-8
tangents[invalid] = np.cross(normals[invalid], np.eye(3)[np.argmin(abs(normals[invalid]), axis=1)])
tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
handedness = np.where((np.cross(normals, tangents) * tan2).sum(1) < 0, -1, 1)
tangents = np.column_stack([tangents, handedness])

skin = base['skins'][0]
ids = skin['joints']
names = [base['nodes'][index]['name'] for index in ids]
weights = np.zeros((len(points), len(names)))
leg = smooth((.615 - points[:, 1]) / .055)
central = abs(source[:, 0]) < .23
leg[central] = 0
weights[:, names.index('Hips')] = 1 - leg
for side, sign in [('Left', 1), ('Right', -1)]:
    own = source[:, 0] * sign > 0
    weights[own, names.index(side + 'UpLeg')] = leg[own]
order = np.argsort(weights, axis=1)[:, ::-1][:, :4]
values = np.take_along_axis(weights, order, axis=1)
values /= values.sum(1, keepdims=True)
order[values == 0] = 0

for key, value, kind, component in [
    ('POSITION', points, 'VEC3', 5126),
    ('NORMAL', normals, 'VEC3', 5126),
    ('TANGENT', tangents, 'VEC4', 5126),
    ('JOINTS_0', order, 'VEC4', 5123),
    ('WEIGHTS_0', values, 'VEC4', 5126),
]:
    attrs[key] = add_accessor(doc, binary, value, kind, component)
    doc['bufferViews'][doc['accessors'][attrs[key]]['bufferView']]['target'] = 34962

mapping = {index: len(doc['nodes']) + i for i, index in enumerate(ids)}
for index in ids:
    bone = copy.deepcopy(base['nodes'][index])
    if 'children' in bone:
        bone['children'] = [mapping[i] for i in bone['children'] if i in mapping]
    doc['nodes'].append(bone)
children = {child for index in ids for child in base['nodes'][index].get('children', [])}
rig_id = 'human_female_01_local_v1'
doc['scenes'][0]['nodes'].append(len(doc['nodes']))
doc['nodes'].append({'name': 'Armature', 'children': [mapping[i] for i in ids if i not in children],
                     'extras': {'rig_id': rig_id}})
doc['scenes'][0]['extras'] = {'rig_id': rig_id}
doc['skins'] = [{'joints': [mapping[i] for i in ids], 'skeleton': mapping[skin['skeleton']],
                 'inverseBindMatrices': add_accessor(doc, binary, accessor(base, base_binary, skin['inverseBindMatrices']), 'MAT4')}]
node.pop('matrix')
node.update(name='bottom_female_knight', skin=0,
            extras={'rig_id': rig_id, 'part_id': 'bottom_female_knight', 'fitting_version': int(VERSION[1:])})
doc['meshes'][0]['name'] = 'bottom_female_knight'
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)

_, body_welded = np.unique(np.round(body_points, 6), axis=0, return_inverse=True)
adjacency = [set() for _ in range(body_welded.max() + 1)]
for face in body_welded[body_faces]:
    for a, b in [(face[0], face[1]), (face[1], face[2]), (face[2], face[0])]:
        adjacency[a].add(b)
        adjacency[b].add(a)
labels = np.full(len(adjacency), -1)
for seed in range(len(adjacency)):
    if labels[seed] >= 0:
        continue
    labels[seed] = seed
    todo = [seed]
    while todo:
        for neighbor in adjacency[todo.pop()]:
            if labels[neighbor] < 0:
                labels[neighbor] = seed
                todo.append(neighbor)
face_labels = labels[body_welded[body_faces[:, 0]]]
main = np.bincount(face_labels).argmax()
hidden = np.zeros(len(body_faces), dtype=bool)
for label in np.unique(face_labels):
    if label == main:
        continue
    selection = face_labels == label
    p = body_points[np.unique(body_faces[selection])]
    if p[:, 1].min() > .45 and p[:, 1].max() < .65:
        hidden |= selection
mask = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
        'mesh_index': 0, 'primitive_index': 0, 'primitive_triangles': len(body_faces),
        'hide_triangle_indices': np.flatnonzero(hidden).tolist(), 'underwear_triangles': int(hidden.sum()),
        'covered_skin_triangles': 0, 'scope': 'Lower underwear only; skin remains for open plate gaps. Union with equipped top mask; restore on unequip/failure.'}
(OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
np.savez(OUTPUT / 'fit-data.npz', source=source, initial=initial, fitted=points, faces=faces,
         joints=order, weights=values, bone_names=np.array(names))
report = {'date': '2026-10-13' if VERSION in ['v3', 'v4'] else '2026-10-12', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
          'triangles': len(faces), 'bones': len(names), 'rig_id': rig_id,
          'method': 'X-forward source to Z-forward; 0.27 uniform initial scale, belt top at 0.645; local radial fitting against actual female body triangles, with thigh-centered lower rays. Hip-bound belt/central guards and same-side thigh plates/straps.',
          'maximum_radial_push': float(max(pushes)), 'source_bounds': [source.min(0).tolist(), source.max(0).tolist()],
          'fitted_bounds': [points.min(0).tolist(), points.max(0).tolist()],
          'preserved': ['original triangles', 'UVs', 'embedded texture bytes', 'materials', 'canonical bone hierarchy and inverse bind matrices'],
          'mask': {'lower_underwear_triangles': int(hidden.sum()), 'skin_triangles_hidden': 0},
          'status': 'Preview fitting candidate; motion and visual validation pending', 'additional_api_credits': 0}
if waist_review is not None:
    report['waist_adjustment'] = waist_review
    report['method'] += ' Upper belt and hip plates contracted to actual skin with 0.004 clearance plus at most 0.004 plate/strap relief; smooth transition over heights 0.56-0.61.'
if curve_review is not None:
    report['convex_side_adjustment'] = curve_review
    report['method'] += ' Side plates expanded onto convex waist-to-hip silhouette; belt, central guard and lower anchors retained.'
    report['waist_adjustment']['scope'] = 'V2 contraction measurements before convex side correction; top belt at height >= 0.635 remains identical. See convex_side_adjustment for the final profile.'
if depth_review is not None:
    report['front_depth_adjustment'] = depth_review
    report['method'] += ' Front plate and strap projection reduced without changing frontal silhouette or rear geometry.'
    report['convex_side_adjustment']['scope'] = 'V3 lateral correction measurements before V4 depth correction; frontal coordinates remain unchanged. See front_depth_adjustment for final depth.'
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
body_reference = bpy.data.objects['female_body']
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.ops.import_scene.gltf(filepath=str(target), bone_heuristic='TEMPERANCE')
part = bpy.data.objects['bottom_female_knight']
own_rig = part.find_armature()
for modifier in part.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
part.parent = None
bpy.data.objects.remove(own_rig, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/items/female_knight_top/tripo_v1/fitted_v3/top_female_knight.glb'), bone_heuristic='TEMPERANCE')
top = bpy.data.objects['top_female_knight']
own_rig = top.find_armature()
for modifier in top.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
top.parent = None
bpy.data.objects.remove(own_rig, do_unlink=True)
bpy.context.view_layer.update()
top_mask = json.loads((ROOT / 'assets/items/female_knight_top/tripo_v1/fitted_v3/body-occlusion.json').read_text())
hidden_faces = set(mask['hide_triangle_indices']) | set(top_mask['hide_triangle_indices'])
visible_body = body_reference.copy()
visible_body.data = body_reference.data.copy()
visible_body.name = 'female_body_equipped'
bpy.context.collection.objects.link(visible_body)
bm = bmesh.new()
bm.from_mesh(visible_body.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(hidden_faces)], context='FACES_ONLY')
bm.to_mesh(visible_body.data)
bm.free()
visible_body.data.update()
body_reference.name = 'female_body_reference_unmasked'
body_reference.hide_render = True
body_reference.hide_set(True)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-knight-bottom-fitted.blend'))
print(json.dumps(report), flush=True)
