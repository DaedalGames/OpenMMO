import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.ndimage import gaussian_filter

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v22'
OUTPUT = DIRECTORY / 'fitted_v23'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '453e60295a9508e110292c07c5b344d6bfded25fe86a3a33fe480a04b34327ff'
body_path = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
body, body_binary = read_glb(body_path)
primitive = body['meshes'][0]['primitives'][0]
body_points = accessor(body, body_binary, primitive['attributes']['POSITION'])
body_faces = accessor(body, body_binary, primitive['indices']).reshape(-1, 3)
triangles = body_points[body_faces]
triangles = triangles[(triangles[:, :, 1].max(1) > .53) & (triangles[:, :, 1].min(1) < .66)
                      & (abs(triangles[:, :, 0]).max(1) < .16)]
a, ab, ac = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
heights = np.linspace(.53, .66, 53)
angles = np.linspace(-np.pi / 2, .1, 61)
body_radii = {}
for side in [-1, 1]:
    grid = np.empty((len(heights), len(angles)))
    for j, angle in enumerate(angles):
        direction = np.array([side * np.cos(angle), 0, np.sin(angle)])
        h = np.cross(direction, ac)
        determinant = (ab * h).sum(1)
        valid = abs(determinant) > 1e-12
        inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
        for i, height in enumerate(heights):
            offset = [0, height, -.004] - a
            u = (offset * h).sum(1) * inverse
            cross = np.cross(offset, ab)
            v = (cross * direction).sum(1) * inverse
            distance = (cross * ac).sum(1) * inverse
            hits = distance[valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (distance > 0)]
            assert len(hits)
            grid[i, j] = hits.max()
    body_radii[side] = RectBivariateSpline(heights, angles, gaussian_filter(grid, .7))


def smooth(values):
    t = np.clip(values, 0, 1)
    return t * t * (3 - 2 * t)


def bend(points):
    radial = points - [0, 0, -.004]
    radial[:, 1] = 0
    radius = np.linalg.norm(radial, axis=1)
    angle = np.arctan2((points[:, 2] + .004 - .1 * (points[:, 1] - .525)) / .092,
                       abs(points[:, 0]) / .124)
    falloff = smooth((points[:, 1] - .54) / .08) * smooth((-angle - .1) / .85)
    body_radius = np.zeros(len(points))
    for side in [-1, 1]:
        selected = points[:, 0] * side > 0
        body_radius[selected] = body_radii[side].ev(points[selected, 1], np.arctan2(radial[selected, 2], abs(radial[selected, 0])))
    height = points[:, 1]
    start = np.sqrt(1 - (.05 / .1305) ** 2)
    rate = .05 / (.1305 ** 2 * start)
    lower = start + rate * .025 * (1 - np.exp(-np.maximum(0, .575 - height) / .025))
    shell_radius = np.where(height < .575, lower, np.sqrt(np.maximum(.01, 1 - ((height - .525) / .1305) ** 2)))
    cosine, sine = abs(radial[:, 0]) / radius, radial[:, 2] / radius
    shift = .1 * (height - .525)
    qa = cosine ** 2 / .124 ** 2 + sine ** 2 / .092 ** 2
    qb = -2 * sine * shift / .092 ** 2
    qc = shift ** 2 / .092 ** 2 - shell_radius ** 2
    reference_radius = (-qb + np.sqrt(qb ** 2 - 4 * qa * qc)) / (2 * qa)
    available = np.maximum(0, reference_radius - body_radius - .0015)
    desired = .027 * falloff
    amount = np.maximum(0, (desired + available - np.sqrt((desired - available) ** 2 + .0005 ** 2)) / 2)
    return points - radial / radius[:, None] * amount[:, None]


doc, binary = read_glb(source)
binary = bytearray(binary)
cache = {}
changes = []
for index in [1, 2, 3]:
    attrs = doc['meshes'][0]['primitives'][index]['attributes']
    points = accessor(doc, binary, attrs['POSITION']).astype(float)
    result = bend(points)
    selected = np.flatnonzero(np.linalg.norm(result - points, axis=1) > 1e-12)
    jacobian = np.stack([
        (bend(points + axis * 1e-6) - bend(points - axis * 1e-6)) / 2e-6
        for axis in np.eye(3)
    ], axis=2)
    assert np.linalg.det(jacobian).min() > .1
    values = {'POSITION': result}
    normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
    normals[selected] = np.linalg.solve(jacobian[selected].transpose(0, 2, 1), normals[selected, :, None])[:, :, 0]
    normals[selected] /= np.linalg.norm(normals[selected], axis=1, keepdims=True)
    values['NORMAL'] = normals
    if 'TANGENT' in attrs:
        tangents = accessor(doc, binary, attrs['TANGENT']).astype(float)
        tangents[selected, :3] = np.einsum('nij,nj->ni', jacobian[selected], tangents[selected, :3])
        tangents[selected, :3] /= np.linalg.norm(tangents[selected, :3], axis=1, keepdims=True)
        values['TANGENT'] = tangents
    for name, data in values.items():
        original = attrs[name]
        if original not in cache:
            cache[original] = add_accessor(doc, binary, data, 'VEC4' if name == 'TANGENT' else 'VEC3')
            doc['bufferViews'][doc['accessors'][cache[original]]['bufferView']]['target'] = 34962
        attrs[name] = cache[original]
    changes.append({'primitive': index, 'vertices': selected.tolist(),
                    'maximum_displacement': float(np.linalg.norm(result - points, axis=1).max()),
                    'minimum_jacobian_determinant': float(np.linalg.det(jacobian).min())})

doc['nodes'][0]['extras']['fitting_version'] = 23
doc['buffers'][0]['byteLength'] = len(binary)
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update({
    'date': '2026-10-13', 'source': str(source.relative_to(ROOT)), 'source_sha256': source_hash,
    'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'method': 'Bend both rear plate shoulders radially toward the waist with smooth height and angular falloffs; deform the attached seams and rivets with the same field.',
    'rear_plate_changes': changes,
    'rear_plate_bend': {'maximum_offset': .027, 'height_range': [.54, .62], 'angular_range': [-.95, -.1]},
    'body_clearance_target': .0015,
    'body_source': str(body_path.relative_to(ROOT)),
    'body_sha256': hashlib.sha256(body_path.read_bytes()).hexdigest(),
    'preserved': ['all leather and buckles', 'central guards', 'front plates', 'lower hems', 'skin weights', 'UVs', 'indices', 'materials', 'textures', 'bones', 'inverse binds', 'occlusion mask'],
    'additional_api_credits': 0,
})
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'changes': [{k: len(v) if k == 'vertices' else v for k, v in change.items()} for change in changes]}))
