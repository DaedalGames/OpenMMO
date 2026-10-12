import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
VERSION = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'v11'
assert VERSION in ['v9', 'v10', 'v11']
SOURCE = DIRECTORY / f'fitted_v{int(VERSION[1:]) - 1}'
OUTPUT = DIRECTORY / f'fitted_{VERSION}'
OUTPUT.mkdir(exist_ok=True)
HEIGHTS = np.array([.475, .51033, .525, .54267, .575, .60978, .62713])
ANGLES = np.array([.75, 1.155, 1.07, 1.165, 1.065, 1.175, .85])
slopes = np.diff(ANGLES) / np.diff(HEIGHTS)
derivatives = np.zeros(len(HEIGHTS))
derivatives[0], derivatives[-1] = slopes[0], slopes[-1]
for i in range(1, len(HEIGHTS) - 1):
    if slopes[i - 1] * slopes[i] > 0:
        derivatives[i] = 2 / (1 / slopes[i - 1] + 1 / slopes[i])


def rounded_angle(height):
    index = int(np.clip(np.searchsorted(HEIGHTS, height) - 1, 0, len(HEIGHTS) - 2))
    span = HEIGHTS[index + 1] - HEIGHTS[index]
    t = np.clip((height - HEIGHTS[index]) / span, 0, 1)
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * ANGLES[index]
            + (t ** 3 - 2 * t ** 2 + t) * span * derivatives[index]
            + (-2 * t ** 3 + 3 * t ** 2) * ANGLES[index + 1]
            + (t ** 3 - t ** 2) * span * derivatives[index + 1])


EDGE_HEIGHTS = np.array([.475, .495, .525, .529, .535, .575])
EDGE_WIDTHS = np.array([.091, .061, .0595, .051, .0515,
                       .124 * np.sqrt(1 - (.05 / .1305) ** 2) * np.cos(1.065)])
CORNER_RADIUS_HEIGHT = .0012


def front_angle(height):
    if VERSION == 'v9' or height >= .575:
        return rounded_angle(height)
    rates = np.diff(EDGE_WIDTHS) / np.diff(EDGE_HEIGHTS)
    width = EDGE_WIDTHS[0] + rates[0] * (height - EDGE_HEIGHTS[0])
    for i in range(1, len(EDGE_HEIGHTS) - 1):
        distance = height - EDGE_HEIGHTS[i]
        if distance <= -CORNER_RADIUS_HEIGHT:
            hinge = 0
        elif distance >= CORNER_RADIUS_HEIGHT:
            hinge = distance
        else:
            hinge = (distance + CORNER_RADIUS_HEIGHT) ** 2 / (4 * CORNER_RADIUS_HEIGHT)
        width += (rates[i] - rates[i - 1]) * hinge
    start = np.sqrt(1 - (.05 / .1305) ** 2)
    rate = .05 / (.1305 ** 2 * start)
    radius = start + rate * .025 * (1 - np.exp(-(.575 - height) / .025))
    return np.arccos(width / (.124 * radius))


def base_surface(side, height, angle, relief):
    if height >= .575:
        radius = np.sqrt(1 - ((height - .525) / .1305) ** 2)
        slope = -(height - .525) / (.1305 ** 2 * radius)
    else:
        start = np.sqrt(1 - (.05 / .1305) ** 2)
        rate = .05 / (.1305 ** 2 * start)
        decay = np.exp(-(.575 - height) / .025)
        radius = start + rate * .025 * (1 - decay)
        slope = -rate * decay
    blend = np.clip((angle - .25) / .85, 0, 1)
    blend = blend * blend * (3 - 2 * blend)
    adjusted = angle + blend * (front_angle(height) - 1.1)
    normal = np.array([side * np.cos(adjusted) / .124,
                       -slope - .10 * np.sin(adjusted) / .092, np.sin(adjusted) / .092])
    normal /= np.linalg.norm(normal)
    point = np.array([side * .124 * radius * np.cos(adjusted), height,
                      -.004 + .10 * (height - .525) + .092 * radius * np.sin(adjusted)])
    return point + relief * normal, normal


CONTACT_HEIGHTS = np.array([.575, .585, .595, .605, .615, .625, .633, .643])
CONTACT_WIDTHS = np.array([.0555, .0425, .0358, .033, .0315, .032, .0355, .043])
CONTACT_DEPTHS = {
    -1: np.array([.075, .06062, .05796, .05368, .04971, .04805, .04412, .029]),
    1: np.array([.075, .06090, .05908, .05578, .04990, .04931, .04385, .029]),
}


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def fitted_surface(side, height, angle):
    point = base_surface(side, height, angle, 0)[0]
    amount = smooth((height - .54) / .045)
    if angle <= .35 or amount == 0:
        return point
    anchor = base_surface(side, height, .35, 0)[0]
    previous_edge = base_surface(side, height, 1.1, 0)[0]
    width_blend = smooth((height - .575) / .010)
    width = abs(previous_edge[0]) * (1 - width_blend) + (.031 + 10 * (height - .618) ** 2) * width_blend
    depth = .0735 - .20 * (height - .54) - 1.5 * (height - .54) ** 2
    target = np.array([side * width, height, depth])
    tangent = base_surface(side, height, .35001, 0)[0] - base_surface(side, height, .34999, 0)[0]
    tangent /= np.linalg.norm(tangent)
    distance = np.linalg.norm(target - anchor)
    tuck = smooth((height - .617) / .015)
    p1 = anchor + tangent * distance * (1 / 3 - (1 / 3 - .05) * tuck)
    end_slope = .12 + .23 * tuck
    p2 = target - np.array([-side, 0, end_slope]) / np.sqrt(1 + end_slope ** 2) * distance / 3
    t = np.clip((angle - .35) / .75, 0, 1)
    curved = (1 - t) ** 3 * anchor + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * target
    return point * (1 - amount) + curved * amount


def surface(side, height, angle, relief):
    if VERSION != 'v11' or height <= .54:
        return base_surface(side, height, angle, relief)
    point = fitted_surface(side, height, angle)
    dy = fitted_surface(side, height + 1e-6, angle) - fitted_surface(side, height - 1e-6, angle)
    da = fitted_surface(side, height, angle + 1e-6) - fitted_surface(side, height, angle - 1e-6)
    normal = side * np.cross(dy, da)
    normal /= np.linalg.norm(normal)
    return point + relief * normal, normal


doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
positions, normals, uvs, sides = [], [], [], []
faces, seam_faces, outer_faces, edge_records = [], [], [], []


def vertex(point, normal, side, uv=(0, 0)):
    index = len(positions)
    positions.append(point)
    normals.append(normal)
    uvs.append(uv)
    sides.append(side)
    return index


def triangle(a, b, c, destination):
    pa, pb, pc = (np.array(positions[i]) for i in [a, b, c])
    if np.dot(np.cross(pb - pa, pc - pa), sum(normals[i] for i in [a, b, c])) < 0:
        b, c = c, b
    destination.append([a, b, c])


for side in [-1, 1]:
    for level in range(3):
        angles = np.linspace(-1.25, 1.1, 15)
        bottom, relief = [.575, .525, .475][level], [.0006, .0003, 0][level]
        layers = []
        for inner in [False, True]:
            columns = []
            for column, angle in enumerate(angles):
                top = .6345 - .012 * np.sin(angle) ** 2 + .002 * np.sin(angle) if level == 0 else [.0, .578, .528][level]
                if VERSION == 'v11' and level == 0:
                    top += .003
                rows = 12 if column >= 10 else 3
                grid = []
                samples = np.linspace(0, 1, rows + 1)
                if VERSION in ['v10', 'v11'] and level == 1 and rows == 12:
                    samples = np.array([0, .12, .24, .36, .48, .60, .72, .80, .86, .91, .95, .98, 1])
                for t in samples:
                    height = top * (1 - t) + bottom * t
                    point, normal = surface(side, height, angle, relief - (.0012 if inner else 0))
                    grid.append(vertex(point, -normal if inner else normal, side, (column / 14, t)))
                columns.append(grid)
            for left, right in zip(columns, columns[1:]):
                a = b = 0
                while a < len(left) - 1 or b < len(right) - 1:
                    next_a = uvs[left[a + 1]][1] if a < len(left) - 1 else np.inf
                    next_b = uvs[right[b + 1]][1] if b < len(right) - 1 else np.inf
                    before = len(faces)
                    if next_a <= next_b:
                        triangle(left[a], right[b], left[a + 1], faces)
                        a += 1
                    else:
                        triangle(left[a], right[b], right[b + 1], faces)
                        b += 1
                    if not inner:
                        outer_faces.extend(faces[before:])
            layers.append(columns)
        outer, inner = layers
        perimeter = [(col, 0) for col in range(15)] + [(14, row) for row in range(1, len(outer[14]))]
        perimeter += [(col, len(outer[col]) - 1) for col in range(13, -1, -1)]
        perimeter += [(0, row) for row in range(len(outer[0]) - 2, 0, -1)]
        for i, (col, row) in enumerate(perimeter):
            next_col, next_row = perimeter[(i + 1) % len(perimeter)]
            a, b = outer[col][row], outer[next_col][next_row]
            c, d = inner[next_col][next_row], inner[col][row]
            normal = np.cross(positions[b] - positions[a], positions[d] - positions[a])
            normal /= np.linalg.norm(normal)
            cap = [vertex(positions[v].copy(), normal.copy(), side) for v in [a, b, c, d]]
            triangle(*cap[:3], faces)
            triangle(cap[0], cap[2], cap[3], faces)
        edge_records.append({'side': side, 'level': level, 'vertex_indices': outer[-1]})
        if level < 2:
            strip = []
            for height in [bottom - .00035, bottom + .00055]:
                strip.append([vertex(*surface(side, height, angle, .00075), side) for angle in angles])
            for col in range(14):
                triangle(strip[0][col], strip[0][col + 1], strip[1][col + 1], seam_faces)
                triangle(strip[0][col], strip[1][col + 1], strip[1][col], seam_faces)

points, normal, uv = np.array(positions), np.array(normals), np.array(uvs)
uv = [.405, .280] + uv * [.060, .030]
bone_names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
leg = np.clip((.615 - points[:, 1]) / .055, 0, 1)
leg = leg * leg * (3 - 2 * leg)
weights = np.column_stack([1 - leg, leg, np.zeros((len(points), 2))])
joints = np.zeros((len(points), 4), dtype=np.uint16)
joints[:, 0] = bone_names.index('Hips')
joints[:, 1] = [bone_names.index('LeftUpLeg' if side > 0 else 'RightUpLeg') for side in sides]
swap = weights[:, 1] > weights[:, 0]
weights[swap], joints[swap] = weights[swap][:, [1, 0, 2, 3]], joints[swap][:, [1, 0, 2, 3]]
joints[weights == 0] = 0
indices = np.array(faces)
a, b, c = indices.T
ab, ac = points[b] - points[a], points[c] - points[a]
uv_ab, uv_ac = uv[b] - uv[a], uv[c] - uv[a]
det = uv_ab[:, 0] * uv_ac[:, 1] - uv_ab[:, 1] * uv_ac[:, 0]
valid = abs(det) > 1e-12
t1, t2 = np.zeros_like(points), np.zeros_like(points)
direction = (ab[valid] * uv_ac[valid, 1, None] - ac[valid] * uv_ab[valid, 1, None]) / det[valid, None]
bitangent = (ac[valid] * uv_ab[valid, 0, None] - ab[valid] * uv_ac[valid, 0, None]) / det[valid, None]
for corners in indices[valid].T:
    np.add.at(t1, corners, direction)
    np.add.at(t2, corners, bitangent)
tangent = t1 - normal * (normal * t1).sum(1, keepdims=True)
invalid = np.linalg.norm(tangent, axis=1) < 1e-8
tangent[invalid] = np.cross(normal[invalid], np.eye(3)[np.argmin(abs(normal[invalid]), axis=1)])
tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
handedness = np.where((np.cross(normal, tangent) * t2).sum(1) < 0, -1, 1)
attributes = {}
for name, data, kind, component in [('POSITION', points, 'VEC3', 5126), ('NORMAL', normal, 'VEC3', 5126),
                                    ('TEXCOORD_0', uv, 'VEC2', 5126), ('JOINTS_0', joints, 'VEC4', 5123),
                                    ('WEIGHTS_0', weights, 'VEC4', 5126),
                                    ('TANGENT', np.column_stack([tangent, handedness]), 'VEC4', 5126)]:
    attributes[name] = add_accessor(doc, binary, data, kind, component)
    doc['bufferViews'][doc['accessors'][attributes[name]]['bufferView']]['target'] = 34962
for part, data in [(1, faces), (3, seam_faces)]:
    primitive = doc['meshes'][0]['primitives'][part]
    primitive['attributes'] = attributes.copy()
    if part == 3:
        primitive['attributes'].pop('TANGENT')
    primitive['indices'] = add_accessor(doc, binary, np.array(data).reshape(-1, 1), 'SCALAR', 5125)
    doc['bufferViews'][doc['accessors'][primitive['indices']]['bufferView']]['target'] = 34963
doc['nodes'][0]['extras']['fitting_version'] = int(VERSION[1:])
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
np.savez(OUTPUT / 'edge-data.npz', outer_faces=outer_faces)
report = json.loads((SOURCE / 'fitting.json').read_text())
for key in ['validation', 'failed_candidate', 'user_correction_reference', 'edge_angle_offsets', 'maximum_displacement']:
    report.pop(key, None)
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)),
              source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Rebuild the plate fronts with a shared C1 cubic edge profile, locally refined rows, and matching seams. Retain the V7 shell profile and V6 metal material; original straps, guards and rivets remain unchanged.',
              rounded_edge_profile={'heights': HEIGHTS.tolist(), 'angles': ANGLES.tolist(), 'derivatives': derivatives.tolist()},
              edge_vertices=edge_records, tessellation={'columns': 14, 'rows_per_column': [3] * 10 + [12] * 5}, triangles=sum(doc['accessors'][p['indices']]['count'] // 3 for p in doc['meshes'][0]['primitives']),
              new_plate_triangles=len(faces), new_seam_triangles=len(seam_faces), status='Rounded edge candidate; validation pending')
if VERSION in ['v10', 'v11']:
    report.update(method='Keep long, nearly straight front edges on the middle and lower plates; turn outward only near each bottom. Round only the local corners while preserving the upper profile, shell and metal material.',
                  lower_edge_profile={'heights': EDGE_HEIGHTS.tolist(), 'half_widths': EDGE_WIDTHS.tolist(),
                                      'corner_rounding_height': CORNER_RADIUS_HEIGHT},
                  status='Late-turn edge candidate; validation pending')
if VERSION == 'v11':
    report.update(method='Extend the upper rim beneath the waist belt and loft the front plate gently under the actual leather strap. Use convex Bezier cross sections with broad support and recompute surface normals; retain the lower edge profile and original leather geometry.',
                  leather_contact={'heights': CONTACT_HEIGHTS.tolist(), 'half_widths': CONTACT_WIDTHS.tolist(),
                                   'depths': {str(side): values.tolist() for side, values in CONTACT_DEPTHS.items()},
                                   'upper_rim_extension': .003, 'blend_height_range': [.54, .585],
                                   'target_width_polynomial': '.031 + 10 * (height - .618)^2',
                                   'target_depth_polynomial': '.0735 - .20 * (height - .54) - 1.5 * (height - .54)^2'},
                  status='Leather contact candidate; validation pending')
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'female-knight-bottom-fitted.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and obj.name.startswith('bottom_female_knight'):
        bpy.data.objects.remove(obj, do_unlink=True)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(target), bone_heuristic='TEMPERANCE')
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
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-knight-bottom-fitted.blend'))
print(json.dumps({'sha256': report['sha256'], 'triangles': report['triangles']}))
