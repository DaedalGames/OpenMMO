import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v4/bottom_female_knight.glb'
OUTPUT = DIRECTORY / 'fitted_v5'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT.mkdir(exist_ok=True)
doc, binary = read_glb(SOURCE)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION'])
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
_, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
parents = np.arange(welded.max() + 1)


def root(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


for face in welded[faces]:
    for corner in face[1:]:
        parents[root(corner)] = root(face[0])
labels = np.array([root(index) for index in welded[faces[:, 0]]])
candidates = []
for label in np.unique(labels):
    vertices = points[np.unique(faces[labels == label])]
    span = np.ptp(vertices, axis=0)
    if span[0] > .25 and span[1] > .18:
        candidates.append(label)
assert len(candidates) == 1
plate_faces = labels == candidates[0]
replace = plate_faces & (abs(points[faces].mean(1)[:, 0]) >= .044)
kept_faces = faces[~replace]
old_surface = BVHTree.FromPolygons([Vector(p) for p in points], faces[replace].tolist())

CENTER = np.array([0., .525, -.004])
RADII = np.array([.124, .1305, .092])
TILT = .10
ANGLE_MIN, ANGLE_MAX = -1.25, 1.10
HEM = .475
THICKNESS = .0012


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def shell(side, height, angle, relief=0):
    radius = np.sqrt(1 - ((height - CENTER[1]) / RADII[1]) ** 2)
    point = np.array([side * RADII[0] * radius * np.cos(angle), height,
                      CENTER[2] + TILT * (height - CENTER[1]) + RADII[2] * radius * np.sin(angle)])
    local = point - CENTER
    local[2] -= TILT * local[1]
    normal = local / RADII ** 2
    normal[1] -= TILT * normal[2]
    normal /= np.linalg.norm(normal)
    return point + normal * relief, normal


original_points = points.copy()
retained_vertices = set()
hanging_vertices = set()
for label in np.unique(labels[~replace]):
    vertices = np.unique(faces[labels == label])
    bounds = points[vertices]
    side_attachment = bounds[:, 1].min() > .55 and bounds[:, 1].max() < .621
    hanging_strap = bounds[:, 1].min() < .45 and bounds[:, 1].max() < .615 and abs(bounds[:, 0].mean()) > .04
    if side_attachment or hanging_strap:
        retained_vertices.update(vertices.tolist())
    if hanging_strap:
        hanging_vertices.update(vertices.tolist())
adornment_moves = []
for index in retained_vertices:
    point = points[index]
    amount = float(smooth((point[1] - .45) / .025) * (1 - smooth((point[1] - .625) / .015)))
    if amount == 0:
        continue
    center = np.array([0., point[1], CENTER[2] + TILT * (point[1] - CENTER[1])])
    offset = point - center
    radius = np.linalg.norm(offset)
    direction = offset / radius
    hit, _, _, _ = old_surface.ray_cast(Vector(center + direction * .22), Vector(-direction), .22)
    if hit is None and index not in hanging_vertices:
        continue
    old_radius = radius if hit is None else np.dot(np.array(hit) - center, direction)
    factor = np.sqrt(1 - ((point[1] - CENTER[1]) / RADII[1]) ** 2)
    target_radius = factor / np.sqrt((direction[0] / RADII[0]) ** 2 + (direction[2] / RADII[2]) ** 2)
    target_radius += .003 + np.clip(radius - old_radius, 0, .002) if index in hanging_vertices else radius - old_radius + .0006
    points[index] = center + direction * (radius + amount * (target_radius - radius))
    adornment_moves.append(float(np.linalg.norm(points[index] - original_points[index])))
attrs['POSITION'] = add_accessor(doc, binary, points, 'VEC3')
primitive['indices'] = add_accessor(doc, binary, kept_faces.reshape(-1, 1), 'SCALAR', 5125)
doc['bufferViews'][doc['accessors'][attrs['POSITION']]['bufferView']]['target'] = 34962
doc['bufferViews'][doc['accessors'][primitive['indices']]['bufferView']]['target'] = 34963

silver = len(doc['materials'])
doc['materials'].append({'name': 'smooth_convex_silver', 'pbrMetallicRoughness': {
    'baseColorFactor': [.57, .60, .64, 1], 'metallicFactor': 1, 'roughnessFactor': .29}})
brass = len(doc['materials'])
doc['materials'].append({'name': 'brass_plate_rivets', 'pbrMetallicRoughness': {
    'baseColorFactor': [.46, .29, .10, 1], 'metallicFactor': .85, 'roughnessFactor': .32}})
seam = len(doc['materials'])
doc['materials'].append({'name': 'fine_plate_seams', 'pbrMetallicRoughness': {
    'baseColorFactor': [.18, .20, .23, 1], 'metallicFactor': 1, 'roughnessFactor': .36}})
bone_names = [doc['nodes'][index]['name'] for index in doc['skins'][0]['joints']]
new_positions, new_normals, new_uv, new_sides = [], [], [], []
new_faces = {silver: [], brass: [], seam: []}


def vertex(position, normal, side, uv=(0, 0)):
    index = len(new_positions)
    new_positions.append(position)
    new_normals.append(normal)
    new_uv.append(uv)
    new_sides.append(side)
    return index


def triangle(a, b, c, material):
    pa, pb, pc = (np.array(new_positions[i]) for i in (a, b, c))
    normal = sum((np.array(new_normals[i]) for i in (a, b, c)))
    if np.dot(np.cross(pb - pa, pc - pa), normal) < 0:
        b, c = c, b
    new_faces[material].append([a, b, c])


def panel(side, level):
    columns, rows = 14, 3
    angles = np.linspace(ANGLE_MIN, ANGLE_MAX, columns + 1)
    bottom = [.575, .525, HEM][level]
    tops = (.6345 - .012 * np.sin(angles) ** 2 + .002 * np.sin(angles)) if level == 0 else np.full_like(angles, [.0, .578, .528][level])
    relief = [.0006, .0003, 0][level]
    layers = []
    for inner in [False, True]:
        grid = np.zeros((rows + 1, columns + 1), dtype=int)
        for row, t in enumerate(np.linspace(0, 1, rows + 1)):
            for col, angle in enumerate(angles):
                height = tops[col] * (1 - t) + bottom * t
                point, normal = shell(side, height, angle, relief)
                if inner:
                    point -= THICKNESS * normal
                    normal = -normal
                grid[row, col] = vertex(point, normal, side, (col / columns, t))
        for row in range(rows):
            for col in range(columns):
                a, b = grid[row, col], grid[row, col + 1]
                c, d = grid[row + 1, col + 1], grid[row + 1, col]
                triangle(a, b, c, silver)
                triangle(a, c, d, silver)
        layers.append(grid)
    outer, inner = layers
    perimeter = [(0, i) for i in range(columns + 1)] + [(i, columns) for i in range(1, rows + 1)] + [(rows, i) for i in range(columns - 1, -1, -1)] + [(i, 0) for i in range(rows - 1, 0, -1)]
    for k, (row, col) in enumerate(perimeter):
        next_row, next_col = perimeter[(k + 1) % len(perimeter)]
        a, b = outer[row, col], outer[next_row, next_col]
        c, d = inner[next_row, next_col], inner[row, col]
        normal = np.cross(np.array(new_positions[b]) - new_positions[a], np.array(new_positions[d]) - new_positions[a])
        normal /= np.linalg.norm(normal)
        cap = [vertex(np.array(new_positions[i]), normal, side) for i in [a, b, c, d]]
        triangle(*cap[:3], silver)
        triangle(cap[0], cap[2], cap[3], silver)
    for angle in [ANGLE_MIN + .16, ANGLE_MAX - .16]:
        point, normal = shell(side, bottom + .008, angle, relief + .0002)
        axis = np.cross(normal, [0, 1, 0])
        axis /= np.linalg.norm(axis)
        other = np.cross(normal, axis)
        tip = vertex(point + normal * .0013, normal, side)
        rings = []
        for phi in [.65, np.pi / 2]:
            ring = []
            for theta in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                radial = np.cos(theta) * axis + np.sin(theta) * other
                pos = point + .0013 * np.cos(phi) * normal + .0020 * np.sin(phi) * radial
                n = np.cos(phi) / .0013 * normal + np.sin(phi) / .0020 * radial
                n /= np.linalg.norm(n)
                ring.append(vertex(pos, n, side))
            rings.append(ring)
        for i in range(8):
            j = (i + 1) % 8
            triangle(tip, rings[0][i], rings[0][j], brass)
            triangle(rings[0][i], rings[1][i], rings[1][j], brass)
            triangle(rings[0][i], rings[1][j], rings[0][j], brass)
    if level < 2:
        strip = []
        for height in [bottom - .00035, bottom + .00055]:
            strip.append([vertex(*shell(side, height, angle, .00075), side) for angle in angles])
        for col in range(columns):
            triangle(strip[0][col], strip[0][col + 1], strip[1][col + 1], seam)
            triangle(strip[0][col], strip[1][col + 1], strip[1][col], seam)


for side in [-1, 1]:
    for level in range(3):
        panel(side, level)
positions = np.array(new_positions)
weights = np.zeros((len(positions), 4))
joints = np.zeros((len(positions), 4), dtype=np.uint16)
leg = smooth((.615 - positions[:, 1]) / .055)
weights[:, 0], weights[:, 1] = 1 - leg, leg
joints[:, 0] = bone_names.index('Hips')
joints[:, 1] = [bone_names.index('LeftUpLeg' if side > 0 else 'RightUpLeg') for side in new_sides]
swap = weights[:, 1] > weights[:, 0]
weights[swap] = weights[swap][:, [1, 0, 2, 3]]
joints[swap] = joints[swap][:, [1, 0, 2, 3]]
joints[weights == 0] = 0
new_attrs = {}
for name, values, kind, component in [('POSITION', positions, 'VEC3', 5126), ('NORMAL', new_normals, 'VEC3', 5126),
                                     ('TEXCOORD_0', new_uv, 'VEC2', 5126), ('JOINTS_0', joints, 'VEC4', 5123),
                                     ('WEIGHTS_0', weights, 'VEC4', 5126)]:
    new_attrs[name] = add_accessor(doc, binary, values, kind, component)
    doc['bufferViews'][doc['accessors'][new_attrs[name]]['bufferView']]['target'] = 34962
for material, indices in new_faces.items():
    index = add_accessor(doc, binary, np.array(indices).reshape(-1, 1), 'SCALAR', 5125)
    doc['bufferViews'][doc['accessors'][index]['bufferView']]['target'] = 34963
    doc['meshes'][0]['primitives'].append({'attributes': new_attrs.copy(), 'indices': index, 'material': material})
doc['nodes'][0]['extras']['fitting_version'] = 5
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
mask = json.loads((DIRECTORY / 'fitted_v4/body-occlusion.json').read_text())
(OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
np.savez(OUTPUT / 'shell-data.npz', positions=positions, normals=new_normals, faces=np.array(new_faces[silver]),
         joints=joints, weights=weights, removed_face_indices=np.flatnonzero(replace))
report = {
    'date': '2026-10-13', 'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
    'rig_id': 'human_female_01_local_v1', 'bones': len(bone_names),
    'method': 'Replace dented side plates with three thin overlapping sections of one analytic convex ellipsoid per side, analytic normals, clean silver PBR and brass dome rivets. Retain original belt, central guards and dangling straps; remap upper leather attachments radially onto the shell.',
    'shell': {'center': CENTER.tolist(), 'radii': RADII.tolist(), 'depth_shear_per_height': TILT, 'angle_range': [ANGLE_MIN, ANGLE_MAX],
              'hem_height': HEM, 'thickness': THICKNESS, 'panel_bottom_heights': [.575, .525, HEM],
              'columns': 14, 'rows_per_panel': 3},
    'triangles': len(kept_faces) + sum(map(len, new_faces.values())), 'removed_side_plate_triangles': int(replace.sum()),
    'retained_triangles': len(kept_faces), 'new_plate_triangles': len(new_faces[silver]), 'new_rivet_triangles': len(new_faces[brass]), 'new_seam_triangles': len(new_faces[seam]),
    'maximum_retained_attachment_displacement': max(adornment_moves),
    'material_correction': 'Original side color texture contains baked dent-like reflections; replaced side surfaces use a texture-free silver material without the original normal map. Original textures/material remain embedded for retained parts.',
    'additional_api_credits': 0, 'status': 'Preview candidate; validation pending'}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
body_reference = bpy.data.objects['female_body']
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
for path in [target, ROOT / 'assets/items/female_knight_top/tripo_v1/fitted_v3/top_female_knight.glb']:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), bone_heuristic='TEMPERANCE')
    imported = set(bpy.data.objects) - before
    for obj in imported:
        if obj.type == 'MESH':
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE':
                    modifier.object = rig
            obj.parent = None
    for obj in imported:
        if obj.type == 'ARMATURE':
            bpy.data.objects.remove(obj, do_unlink=True)
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
