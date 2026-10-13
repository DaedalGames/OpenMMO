import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d

from lib.glb import read_glb, view_bytes, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.radial_sections import clearance, radii
from outfits.female_boot_pose import heel_pose

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/items/female_knight_boots/sole_v3/boot_right.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = ROOT / 'assets/items/female_knight_boots/fitted_v4'
OUTPUT.mkdir(exist_ok=True)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def sections(triangles, height):
    result = []
    for a, b in [(triangles[:, 0], triangles[:, 1]), (triangles[:, 1], triangles[:, 2]), (triangles[:, 2], triangles[:, 0])]:
        pick = (a[:, 1] < height) != (b[:, 1] < height)
        a, b = a[pick], b[pick]
        result.extend(a + (b - a) * ((height - a[:, 1]) / (b[:, 1] - a[:, 1]))[:, None])
    return np.array(result)


doc, raw = read_glb(SOURCE)
base, base_raw = read_glb(BODY)
heel_matrices, pose_config = heel_pose(base, base_raw)
primitives = copy.deepcopy(doc['meshes'][0]['primitives'])
source_points = [accessor(doc, raw, p['attributes']['POSITION']).astype(float) for p in primitives]
source_normals = [accessor(doc, raw, p['attributes']['NORMAL']).astype(float) for p in primitives]
source_uv = [accessor(doc, raw, p['attributes']['TEXCOORD_0']) for p in primitives]
source_faces = [accessor(doc, raw, p['indices']).reshape(-1, 3) for p in primitives]
t = source_points[0][source_faces[0]]
n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
cap = (t[:, :, 1].min(1) > .30) & (n[:, 1] > .3)
source_faces[0] = source_faces[0][~cap]
packed = np.column_stack([source_points[0], source_normals[0], source_uv[0]])
split_vertices, split_faces = [], []


def clip_polygon(polygon, axis, value, above):
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        inside_a = a[axis] >= value if above else a[axis] <= value
        inside_b = b[axis] >= value if above else b[axis] <= value
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(a + (b - a) * ((value - a[axis]) / (b[axis] - a[axis])))
    return result


for face in source_faces[0]:
    polygons = [list(packed[face])]
    for axis, threshold in [(1, -.29), (1, .075), (1, .225), (0, -.12)]:
        divided = []
        for polygon in polygons:
            values = [p[axis] for p in polygon]
            if min(values) < threshold < max(values):
                divided.extend([clip_polygon(polygon, axis, threshold, above) for above in [False, True]])
            else:
                divided.append(polygon)
        polygons = divided
    for polygon in polygons:
        start = len(split_vertices)
        split_vertices.extend(polygon)
        split_faces.extend([(start, start + j, start + j + 1) for j in range(1, len(polygon) - 1)])
packed = np.array(split_vertices)
source_points[0], source_normals[0], source_uv[0] = packed[:, :3], packed[:, 3:6], packed[:, 6:]
source_faces[0] = np.array(split_faces)
centroids = source_points[0][source_faces[0]].mean(1)
face_regions = np.where(centroids[:, 1] > .225, 0, np.where(centroids[:, 1] > -.29, 1, 2))
face_regions[(centroids[:, 1] > .075) & (centroids[:, 1] <= .225)] = 4
face_regions[(centroids[:, 0] < -.12) & (centroids[:, 1] < -.46)] = 3
keys, inverse = np.unique(np.column_stack([source_faces[0].ravel(), np.repeat(face_regions, 3)]), axis=0, return_inverse=True)
front_regions = keys[:, 1]
source_points[0] = source_points[0][keys[:, 0]]
source_normals[0] = source_normals[0][keys[:, 0]]
source_uv[0] = source_uv[0][keys[:, 0]]
source_faces[0] = inverse.reshape(-1, 3)
source_triangles = np.concatenate([v[f] for v, f in zip(source_points, source_faces)])
bp = base['meshes'][0]['primitives'][0]
bv = accessor(base, base_raw, bp['attributes']['POSITION'])
bf = accessor(base, base_raw, bp['indices']).reshape(-1, 3)
body_joints = accessor(base, base_raw, bp['attributes']['JOINTS_0'])
body_weights = accessor(base, base_raw, bp['attributes']['WEIGHTS_0'])
posed_body = np.einsum('nkij,nj,nk->ni', heel_matrices[body_joints], np.column_stack([bv, np.ones(len(bv))]), body_weights)[:, :3]
posed_toe_floor = float(posed_body[bv[:, 1] < .08, 1].min())
foot_shift = posed_toe_floor - .003 + .00550714823
pose_config['foot_geometry_vertical_shift'] = foot_shift
pose_config['body_toe_floor_before_root_lift'] = posed_toe_floor
pose_config['body_sha256'] = hashlib.sha256(BODY.read_bytes()).hexdigest()
right_skin = bv[bf[(bv[bf, 0] < 0).all(1) & (bv[bf, 1] < .53).all(1)]]
height_curve = PchipInterpolator([-.5, -.31, .075, .145, .28, .5], [-.0056, .078, .287, .322, .39, .49])
heights = np.linspace(.075, .50, 150)
body_centers = []
body_extents = []
for y in heights:
    section = sections(right_skin, y)
    center = (section.min(0) + section.max(0)) / 2
    center[1] = y
    body_centers.append(center)
    body_extents.append((section.max(0) - section.min(0)) / 2)
body_centers = gaussian_filter1d(np.array(body_centers), 2, axis=0)
body_centers[:, 1] = heights
body_extents = gaussian_filter1d(np.array(body_extents), 2, axis=0)
source_heights = np.linspace(-.31, .405, 100)
source_centers = []
source_extents = []
for y in source_heights:
    section = sections(source_triangles, y)
    source_centers.append((section.min(0) + section.max(0)) / 2)
    source_extents.append((section.max(0) - section.min(0)) / 2)
source_centers = gaussian_filter1d(np.array(source_centers), 3, axis=0)
source_extents = gaussian_filter1d(np.array(source_extents), 3, axis=0)

liner_material = len(doc['materials'])
doc['materials'].append({'name': 'joint_leather_liner', 'pbrMetallicRoughness': {'baseColorFactor': [.018, .022, .026, 1], 'metallicFactor': 0, 'roughnessFactor': .85}, 'doubleSided': True})
for low, high in [(.06, .30), (-.33, -.23)]:
    vertices, normals, uv, faces = [], [], [], []
    for row, y in enumerate(np.linspace(low, high, 10)):
        cx = np.interp(y, source_heights, source_centers[:, 0])
        cz = np.interp(y, source_heights, source_centers[:, 2])
        rx = np.interp(y, source_heights, source_extents[:, 0]) * .87
        rz = np.interp(y, source_heights, source_extents[:, 2]) * .87
        measured = radii(source_triangles, np.array([cx, y, cz]), np.array([0., 1., 0.]), samples=128)
        for column, angle in enumerate(np.linspace(0, 2 * np.pi, 33)):
            distance = .72 * measured[(-column * 4) % 128]
            if not np.isfinite(distance):
                distance = .72 * min(rx, rz)
            vertices.append([cx + distance * np.cos(angle), y, cz + distance * np.sin(angle)])
            normals.append([np.cos(angle) / rx, 0, np.sin(angle) / rz])
            uv.append([column / 32, row / 9])
            if row < 9 and column < 32:
                a = row * 33 + column
                faces.extend([(a, a + 33, a + 34), (a, a + 34, a + 1)])
    source_points.append(np.array(vertices))
    normal = np.array(normals)
    source_normals.append(normal / np.linalg.norm(normal, axis=1, keepdims=True))
    source_uv.append(np.array(uv))
    source_faces.append(np.array(faces))
    primitives.append({'material': liner_material})


CHARACTER_HEIGHT_M = 1.8
CLEARANCE_M = .001


def base_fit(points):
    y = points[:, 1]
    h = height_curve(y)
    front = (.080 - points[:, 0]) * .44 - .022
    lateral = (points[:, 2] + .0095) * .44 - .132
    foot = np.column_stack([lateral, h + foot_shift, front])
    center = np.column_stack([np.interp(h, heights, body_centers[:, k]) for k in range(3)])
    center[:, 1] = h
    sx = np.interp(y, source_heights, source_centers[:, 0])
    sz = np.interp(y, source_heights, source_centers[:, 2])
    radius_x = np.interp(h, heights, body_extents[:, 0]) + CLEARANCE_M / CHARACTER_HEIGHT_M
    radius_z = np.interp(h, heights, body_extents[:, 2]) + CLEARANCE_M / CHARACTER_HEIGHT_M
    scale_x = radius_x / np.interp(y, source_heights, source_extents[:, 2])
    scale_z = radius_z / np.interp(y, source_heights, source_extents[:, 0])
    shaft = center.copy()
    shaft[:, 0] += (points[:, 2] - sz) * scale_x
    shaft[:, 2] += (sx - points[:, 0]) * scale_z
    amount = smooth((y + .31) / .09)
    return foot * (1 - amount[:, None]) + shaft * amount[:, None]


allowance_heights = np.linspace(.12, .48, 121)
allowance_scales = np.ones((len(allowance_heights), 4))


def fit(points):
    result = base_fit(points)
    height = result[:, 1]
    blend = smooth((height - .09) / .05)
    for axis, positive, negative in [(0, 0, 2), (2, 3, 1)]:
        center = np.interp(height, heights, body_centers[:, axis])
        delta = result[:, axis] - center
        a = np.interp(height, allowance_heights, allowance_scales[:, positive])
        b = np.interp(height, allowance_heights, allowance_scales[:, negative])
        scale = 1 + (np.where(delta >= 0, a, b) - 1) * blend
        result[:, axis] = center + delta * scale
    return result


for _ in range(3):
    outer = np.concatenate([fit(v)[f] for v, f in zip(source_points[:17], source_faces[:17])])
    factors = []
    for height in allowance_heights:
        center = np.array([np.interp(height, heights, body_centers[:, k]) for k in range(3)])
        skin_radius = radii(right_skin, center, np.array([0., 1., 0.]), samples=4)
        shell_radius = radii(outer, center, np.array([0., 1., 0.]), samples=4)
        valid = np.isfinite(skin_radius) & np.isfinite(shell_radius)
        factor = np.full(4, np.nan)
        factor[valid] = np.clip((skin_radius[valid] + CLEARANCE_M / CHARACTER_HEIGHT_M) / shell_radius[valid], 1, 1.8)
        factors.append(factor)
    factors = np.array(factors)
    for axis in range(4):
        valid = np.isfinite(factors[:, axis])
        factors[:, axis] = np.interp(allowance_heights, allowance_heights[valid], factors[valid, axis])
    allowance_scales *= gaussian_filter1d(factors, 4, axis=0)


names = [base['nodes'][i]['name'] for i in base['skins'][0]['joints']]


def skin_weights(points, part, side):
    y, x = points[:, 1], points[:, 0]
    thigh = smooth((y - .205) / .045)
    foot = 1 - smooth((y + .305) / .065)
    if part in [15, 16]:
        thigh, foot = np.zeros(len(y)), np.ones(len(y))
    elif part == 2:
        thigh = smooth((y - .075) / .205)
        foot = np.zeros(len(y))
    elif part in [1, 3, 4]:
        thigh, foot = np.zeros(len(y)), np.zeros(len(y))
    elif 5 <= part <= 14:
        thigh, foot = np.full(len(y), .5), np.zeros(len(y))
    toe = .20 * smooth((-.075 - x) / .075) * (1 - smooth((y + .41) / .065))
    weights = np.column_stack([thigh, (1 - thigh) * (1 - foot), (1 - thigh) * foot * (1 - toe), (1 - thigh) * foot * toe])
    joints = np.tile([names.index(side + suffix) for suffix in ['UpLeg', 'Leg', 'Foot', 'ToeBase']], (len(y), 1))
    if part == 0:
        weights = np.vstack([np.eye(4), [.5, .5, 0, 0]])[front_regions]
    elif part == 17:
        t = smooth((y - .06) / .24)
        weights = np.column_stack([t, 1 - t, np.zeros(len(y)), np.zeros(len(y))])
    order = np.argsort(-weights, axis=1)
    return np.take_along_axis(joints, order, 1), np.take_along_axis(weights, order, 1)


fitted = [fit(v) for v in source_points]
binary = bytearray(raw)
doc['meshes'], doc['nodes'] = [], []
for side in ['Right', 'Left']:
    parts = []
    for i, (primitive, points, original, faces) in enumerate(zip(primitives, fitted, source_points, source_faces)):
        points, faces = points.copy(), faces.copy()
        jacobian = np.stack([(fit(original + np.eye(3)[j] * 1e-5) - fit(original - np.eye(3)[j] * 1e-5)) / 2e-5 for j in range(3)], axis=2)
        normal = source_normals[i]
        normal = np.linalg.solve(jacobian.transpose(0, 2, 1), normal[..., None])[..., 0]
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        if side == 'Left':
            points[:, 0] *= -1
            normal[:, 0] *= -1
            faces = faces[:, ::-1]
        joints, weights = skin_weights(original, i, side)
        deformation = np.einsum('nk,nkij->nij', weights, heel_matrices[joints])
        points = np.linalg.solve(deformation, np.column_stack([points, np.ones(len(points))])[..., None])[:, :3, 0]
        normal = np.einsum('nji,nj->ni', deformation[:, :3, :3], normal)
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        attrs = {'POSITION': add_accessor(doc, binary, points, 'VEC3'),
                 'NORMAL': add_accessor(doc, binary, normal, 'VEC3'),
                 'TEXCOORD_0': add_accessor(doc, binary, source_uv[i], 'VEC2'),
                 'JOINTS_0': add_accessor(doc, binary, joints, 'VEC4', 5123),
                 'WEIGHTS_0': add_accessor(doc, binary, weights, 'VEC4')}
        parts.append({'attributes': attrs, 'material': primitive['material'],
                      'indices': add_accessor(doc, binary, faces.reshape(-1, 1), 'SCALAR', 5125)})
    index = len(doc['meshes'])
    doc['meshes'].append({'name': f'boots_female_knight_{side.lower()}', 'primitives': parts})
    doc['nodes'].append({'name': f'boots_female_knight_{side.lower()}', 'mesh': index, 'skin': 0,
                         'extras': {'rig_id': 'human_female_01_local_v1', 'part_id': 'boots_female_knight'}})
ids = base['skins'][0]['joints']
mapping = {index: len(doc['nodes']) + i for i, index in enumerate(ids)}
for index in ids:
    node = copy.deepcopy(base['nodes'][index])
    if 'children' in node:
        node['children'] = [mapping[i] for i in node['children'] if i in mapping]
    doc['nodes'].append(node)
children = {child for index in ids for child in base['nodes'][index].get('children', [])}
doc['scenes'] = [{'nodes': [0, 1, len(doc['nodes'])], 'extras': {'rig_id': 'human_female_01_local_v1', 'heel_pose': pose_config}}]
doc['nodes'].append({'name': 'Armature', 'children': [mapping[i] for i in ids if i not in children]})
doc['skins'] = [{'joints': [mapping[i] for i in ids], 'skeleton': mapping[base['skins'][0]['skeleton']],
                 'inverseBindMatrices': add_accessor(doc, binary, accessor(base, base_raw, base['skins'][0]['inverseBindMatrices']), 'MAT4')}]
spec = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
plate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plate)
binary = plate.compact(doc, binary)
write_glb(OUTPUT / 'boots_female_knight.glb', doc, binary)
assert [view_bytes(doc, binary, im['bufferView']) for im in doc['images']] == [view_bytes(base_doc, raw, im['bufferView']) for base_doc in [read_glb(SOURCE)[0]] for im in base_doc['images']]
rim_angles = np.linspace(0, 2 * np.pi, 128, endpoint=False)
rim_heights = np.full(128, .405)
outer_thigh = fitted[0][source_faces[0]]
for y in np.linspace(.40, .495, 160):
    center = np.array([np.interp(y, heights, body_centers[:, k]) for k in range(3)])
    hits = radii(outer_thigh, center, np.array([0., 1., 0.]), samples=128)
    rim_heights[np.isfinite(hits)] = y
body_right = bv.copy()
body_right[:, 0] = -abs(body_right[:, 0])
body_center = np.column_stack([np.interp(bv[:, 1], heights, body_centers[:, k]) for k in range(3)])
body_angle = np.arctan2(-(body_right[:, 2] - body_center[:, 2]), body_right[:, 0] - body_center[:, 0]) % (2 * np.pi)
cut_height = np.interp(body_angle, np.r_[rim_angles, 2 * np.pi], np.r_[rim_heights, rim_heights[0]]) - .010
hide = np.flatnonzero((bv[bf, 1] < cut_height[bf]).all(1)).tolist()
mask = {'mesh_index': 0, 'primitive_index': 0, 'primitive_triangles': len(bf), 'hide_triangle_indices': hide,
        'source_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
        'description': 'Covered legs and feet; angular cuff boundary with 0.010 overlap; restored when boots are removed or unavailable.',
        'cuff_angles': rim_angles.tolist(), 'cuff_heights': rim_heights.tolist()}
(OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
(OUTPUT / 'heel-pose.json').write_text(json.dumps(pose_config, indent=2) + '\n')
triangles = np.concatenate([v[f] for v, f in zip(fitted, source_faces)])
plate_triangles = np.concatenate([v[f] for v, f in zip(fitted[:17], source_faces[:17])])
measurements = []
for y in [.12, .18, .24, .28, .32, .36, .40, .435]:
    center = np.array([np.interp(y, heights, body_centers[:, k]) for k in range(3)])
    measurement = clearance(plate_triangles, right_skin, center, np.array([0., 1., 0.]), samples=96)
    measurement['minimum_clearance_m'] *= CHARACTER_HEIGHT_M
    outer = radii(plate_triangles, center, np.array([0., 1., 0.]), samples=256)
    inner = radii(right_skin, center, np.array([0., 1., 0.]), samples=256)
    common = np.isfinite(outer) & np.isfinite(inner)
    gap = (outer - inner) * CHARACTER_HEIGHT_M
    measurement['median_clearance_m'] = float(np.median(gap[common]))
    measurement['cardinal_clearance_m'] = {name: float(gap[index]) if common[index] else None for name, index in [('inner', 0), ('back', 64), ('outer', 128), ('front', 192)]}
    measurements.append({'height': y, **measurement})
report = {'date': '2026-10-13', 'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
          'body': {'path': str(BODY.relative_to(ROOT)), 'sha256': hashlib.sha256(BODY.read_bytes()).hexdigest()},
          'rig_id': 'human_female_01_local_v1', 'method': 'Anatomical knee/ankle height mapping, actual female leg radial clearance, mirrored X with reversed winding, regional four-influence weights and exact canonical bind matrices',
          'source_conditions': 'Existing user reference, ImageGen ChatGPT Pro 20x and paid Tripo sources; local fitting only, no new API calls',
          'triangles': sum(len(f) for f in source_faces) * 2, 'removed_upper_cap_faces_per_boot': int(cap.sum()), 'hidden_body_triangles': len(hide),
          'posed_floor_offset': float(-triangles[:, :, 1].min()), 'section_clearances': measurements,
          'heel_pose': pose_config, 'geometry_space': 'Inverse-skinned from equipped heel pose into the unchanged canonical bind pose',
          'clearance_target_m': CLEARANCE_M, 'character_height_m': CHARACTER_HEIGHT_M,
          'clearance_method': 'Smooth anatomical cross-sections with four directional clearance correction; retain plate profiles, target one-millimetre allowance and taper to unchanged ankle and foot',
          'status': 'Fitting candidate; motion review follows; no production registration'}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
