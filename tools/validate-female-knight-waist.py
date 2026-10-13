import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
VERSION = sys.argv[1] if len(sys.argv) > 1 else 'v19'
assert VERSION in ['v19', 'v20', 'v21']
BUCKLE = VERSION in ['v20', 'v21']
TARGET = DIRECTORY / f'fitted_{VERSION}'
before, before_binary = read_glb(DIRECTORY / f'fitted_v{int(VERSION[1:]) - 1}/bottom_female_knight.glb')
after, binary = read_glb(TARGET / 'bottom_female_knight.glb')
fitting = json.loads((TARGET / 'fitting.json').read_text())
changed = np.array(fitting['buckle_vertices' if BUCKLE else 'waist_vertices'])
editable = ['POSITION', 'NORMAL', 'TANGENT'] + (['JOINTS_0', 'WEIGHTS_0'] if BUCKLE else [])
for field in ['materials', 'images', 'textures', 'skins', 'animations']:
    assert before.get(field) == after.get(field), field
for index, (old, new) in enumerate(zip(before['meshes'][0]['primitives'], after['meshes'][0]['primitives'], strict=True)):
    assert np.array_equal(accessor(before, before_binary, old['indices']), accessor(after, binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a = accessor(before, before_binary, attribute)
        b = accessor(after, binary, new['attributes'][name])
        if index == 0 and name in editable:
            unchanged = np.ones(len(a), dtype=bool)
            unchanged[changed] = False
            assert np.array_equal(a[unchanged], b[unchanged]), name
            assert np.array_equal(a[fitting['vertices']], b[fitting['vertices']]), name
            if name in ['NORMAL', 'TANGENT']:
                assert np.max(abs(np.linalg.norm(b[changed, :3], axis=1) - 1)) < 1e-6
            if BUCKLE and name == 'POSITION':
                for part in fitting.get('buckle_parts', [{'vertices': changed}]):
                    vertices = np.array(part['vertices'])
                    original_distances = np.linalg.norm(a[vertices, None] - a[None, vertices], axis=2)
                    actual_distances = np.linalg.norm(b[vertices, None] - b[None, vertices], axis=2)
                    assert np.max(abs(original_distances - actual_distances)) < 1e-6
        else:
            assert np.array_equal(a, b), name
leather, plate = after['meshes'][0]['primitives'][:2]
points = accessor(after, binary, leather['attributes']['POSITION']).astype(float)
faces = accessor(after, binary, leather['indices']).reshape(-1, 3)
plate_points = accessor(after, binary, plate['attributes']['POSITION']).astype(float)
plate_faces = accessor(after, binary, plate['indices']).reshape(-1, 3)
triangles = plate_points[plate_faces]
a = triangles[:, 0]
ab, ac = triangles[:, 1] - a, triangles[:, 2] - a
faces = faces[np.isin(faces, changed).all(1)]
triangles = points[faces]
normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
radial = triangles.mean(1) - [0, 0, -.004]
radial[:, 1] = 0
faces = faces[(normals * radial).sum(1) > 0]
gaps = {1: []} if VERSION == 'v20' else {-1: [], 1: []}
for face in faces:
    for u, v in [(1/3, 1/3), (.1, .1), (.8, .1), (.1, .8), (.45, .1), (.1, .45), (.45, .45)]:
        point = points[face[0]] * (1 - u - v) + points[face[1]] * u + points[face[2]] * v
        if not BUCKLE and (abs(point[0]) <= .06 or point[2] <= -.025):
            continue
        origin = np.array([0, point[1], -.004])
        direction = point - origin
        radius = np.linalg.norm(direction)
        direction /= radius
        h = np.cross(direction, ac)
        det = (ab * h).sum(1)
        valid = abs(det) > 1e-12
        inverse = np.divide(1, det, out=np.zeros_like(det), where=valid)
        offset = origin - a
        bu = (offset * h).sum(1) * inverse
        cross = np.cross(offset, ab)
        bv = (cross * direction).sum(1) * inverse
        distance = (cross * ac).sum(1) * inverse
        hits = distance[valid & (bu >= 0) & (bv >= 0) & (bu + bv <= 1) & (distance > 0)]
        if len(hits):
            gaps[int(np.sign(point[0]))].append(float(radius - hits.max()))
results = []
for side, values in gaps.items():
    assert len(values) > (500 if BUCKLE else 1000)
    assert min(values) > .0005, (side, min(values))
    results.append({'side': side, 'samples': len(values), 'minimum_radial_clearance': min(values), 'crossed_samples': 0})
report = {
    'date': '2026-10-13', 'sha256': hashlib.sha256((TARGET / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
    'sides': results,
    'preserved': ['plate geometry', 'front hanging straps', 'topology', 'UVs', 'materials', 'textures', 'rig'] + (['waist belt', 'unchanged buckles', 'buckle and short strap shape'] if BUCKLE else ['skin weights']),
    'scope': 'Seven interior samples per outward triangle in ' + ('the moved buckle and short strap' if BUCKLE else 'the marked lateral waist region (abs(x) > 0.06, z > -0.025)') + ', rest pose. Not a full animated collision test.'
}
(TARGET / ('buckle-validation.json' if BUCKLE else 'waist-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
