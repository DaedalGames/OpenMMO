import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.ndimage import gaussian_filter, maximum_filter

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v18'
OUTPUT = DIRECTORY / 'fitted_v19'
OUTPUT.mkdir(exist_ok=True)
assert hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest() == 'd5af12f58dd33fd32baddfbdfd60f7c4a5cd826a2d4330d3d152b092fe3537e3'
doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
primitive, plate = doc['meshes'][0]['primitives'][:2]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
original = points.copy()
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
plate_points = accessor(doc, binary, plate['attributes']['POSITION']).astype(float)
plate_faces = accessor(doc, binary, plate['indices']).reshape(-1, 3)
triangles = plate_points[plate_faces]
a, ab, ac = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]


def radius_at(side, height, angle):
    origin = np.array([0, height, -.004])
    direction = np.array([side * np.cos(angle), 0, np.sin(angle)])
    h = np.cross(direction, ac)
    det = np.einsum('ij,ij->i', ab, h)
    valid = abs(det) > 1e-12
    inv = np.divide(1, det, out=np.zeros_like(det), where=valid)
    offset = origin - a
    u = np.einsum('ij,ij->i', offset, h) * inv
    q = np.cross(offset, ab)
    v = q @ direction * inv
    distance = np.einsum('ij,ij->i', ac, q) * inv
    hits = distance[valid & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (distance > 0)]
    return float(hits.max()) if len(hits) else 0


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
labels = np.array([root(index) for index in welded])
selected = []
for label in np.unique(labels[faces]):
    vertices = np.unique(faces[labels[faces[:, 0]] == label])
    bounds = points[vertices]
    if len(vertices) > 1000 or (bounds[:, 1].min() > .566 and np.min(abs(bounds[:, 0])) > .075):
        selected.extend(vertices.tolist())
selected = np.array(sorted(selected))
heights = np.linspace(.565, .655, 46)
angles = np.linspace(-1.5, 1.5, 61)
fields = {}
clearance = .0015
for side in [-1, 1]:
    vertices = selected[points[selected, 0] * side > 0]
    angle = np.arctan2(points[vertices, 2] + .004, abs(points[vertices, 0]))
    radius = np.hypot(points[vertices, 0], points[vertices, 2] + .004)
    required = np.array([max(0, radius_at(side, points[i, 1], theta) + clearance - r) for i, theta, r in zip(vertices, angle, radius)])
    grid = np.zeros((len(heights), len(angles)))
    yi = np.clip(np.rint((points[vertices, 1] - heights[0]) / (heights[1] - heights[0])).astype(int), 0, len(heights) - 1)
    ai = np.clip(np.rint((angle - angles[0]) / (angles[1] - angles[0])).astype(int), 0, len(angles) - 1)
    np.maximum.at(grid, (yi, ai), required)
    grid = gaussian_filter(maximum_filter(grid, size=(9, 9)), sigma=(2, 2))
    for _ in range(3):
        field = RectBivariateSpline(heights, angles, grid)
        missing = np.maximum(0, required - field.ev(points[vertices, 1], angle))
        adjustment = np.zeros_like(grid)
        np.maximum.at(adjustment, (yi, ai), missing)
        grid += gaussian_filter(maximum_filter(adjustment, size=(9, 9)), sigma=(2, 2))
    fields[side] = RectBivariateSpline(heights, angles, grid)


def deform(values, side):
    radius = np.hypot(values[:, 0], values[:, 2] + .004)
    angle = np.arctan2(values[:, 2] + .004, abs(values[:, 0]))
    offset = np.maximum(0, fields[side].ev(values[:, 1], angle))
    blend = np.clip((abs(values[:, 0]) - .055) / .02, 0, 1)
    blend = blend * blend * (3 - 2 * blend)
    upper = np.clip((values[:, 1] - .59) / .02, 0, 1)
    upper = upper * upper * (3 - 2 * upper)
    offset *= 1 - (1 - blend) * (1 - upper)
    lateral = np.clip((angle + 1) / .5, 0, 1)
    offset *= lateral * lateral * (3 - 2 * lateral)
    result = values.copy()
    result[:, 0] *= (radius + offset) / radius
    result[:, 2] = -.004 + (values[:, 2] + .004) * (radius + offset) / radius
    return result


normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
tangents = accessor(doc, binary, attrs['TANGENT']).astype(float)
for side in [-1, 1]:
    vertices = selected[points[selected, 0] * side > 0]
    values = points[vertices].copy()
    points[vertices] = deform(values, side)
    jacobian = np.stack([(deform(values + axis * 1e-6, side) - deform(values - axis * 1e-6, side)) / 2e-6 for axis in np.eye(3)], axis=2)
    normals[vertices] = np.linalg.solve(jacobian.transpose(0, 2, 1), normals[vertices, :, None])[:, :, 0]
    normals[vertices] /= np.linalg.norm(normals[vertices], axis=1, keepdims=True)
    tangents[vertices, :3] = np.einsum('ijk,ik->ij', jacobian, tangents[vertices, :3])
    tangents[vertices, :3] /= np.linalg.norm(tangents[vertices, :3], axis=1, keepdims=True)
for name, values, kind in [('POSITION', points, 'VEC3'), ('NORMAL', normals, 'VEC3'), ('TANGENT', tangents, 'VEC4')]:
    attrs[name] = add_accessor(doc, binary, values, kind, 5126)
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
doc['nodes'][0]['extras']['fitting_version'] = 19
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)),
              source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Fit the waist leather and short side straps outside the plate with a shared smooth radial displacement field; transform normals and tangents with its Jacobian.',
              waist_vertices=selected.tolist(), maximum_displacement=float(np.linalg.norm(points - original, axis=1).max()),
              displacement_grid={'heights': heights.tolist(), 'angles': angles.tolist(), 'maximum_filter_size': [9, 9], 'gaussian_sigma': [2, 2]},
              clearance=clearance, preserved=['plate geometry', 'front hanging straps', 'UVs', 'topology', 'skin weights', 'materials', 'textures', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'vertices': len(selected), 'maximum_displacement': report['maximum_displacement']}))
