import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
TARGET = DIRECTORY / 'fitted_v23'
before, old_binary = read_glb(DIRECTORY / 'fitted_v22/bottom_female_knight.glb')
after, binary = read_glb(TARGET / 'bottom_female_knight.glb')
fitting = json.loads((TARGET / 'fitting.json').read_text())
changes = {entry['primitive']: entry['vertices'] for entry in fitting['rear_plate_changes']}
for field in ['materials', 'images', 'textures', 'skins', 'animations']:
    assert before.get(field) == after.get(field), field
for index, (old, new) in enumerate(zip(before['meshes'][0]['primitives'], after['meshes'][0]['primitives'], strict=True)):
    assert np.array_equal(accessor(before, old_binary, old['indices']), accessor(after, binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a = accessor(before, old_binary, attribute)
        b = accessor(after, binary, new['attributes'][name])
        if index in changes and name in ['POSITION', 'NORMAL', 'TANGENT']:
            untouched = np.ones(len(a), dtype=bool)
            untouched[changes[index]] = False
            assert np.array_equal(a[untouched], b[untouched]), (index, name)
            if name == 'POSITION':
                assert np.array_equal(a[:, 1], b[:, 1])
                assert np.max(np.linalg.norm(a - b, axis=1)) < .027
            else:
                assert np.max(abs(np.linalg.norm(b[:, :3], axis=1) - 1)) < 1e-6
        else:
            assert np.array_equal(a, b), (index, name)
for image in before.get('images', []):
    view = before['bufferViews'][image['bufferView']]
    start, size = view.get('byteOffset', 0), view['byteLength']
    assert old_binary[start:start + size] == binary[start:start + size]
assert (TARGET / 'body-occlusion.json').read_bytes() == (DIRECTORY / 'fitted_v22/body-occlusion.json').read_bytes()


def samples(doc, data):
    leather, plate = doc['meshes'][0]['primitives'][:2]
    points = accessor(doc, data, leather['attributes']['POSITION'])
    faces = accessor(doc, data, leather['indices']).reshape(-1, 3)
    plate_points = accessor(doc, data, plate['attributes']['POSITION'])
    plate_faces = accessor(doc, data, plate['indices']).reshape(-1, 3)
    triangles = plate_points[plate_faces]
    a, ab, ac = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    triangles = points[faces]
    center = triangles.mean(1)
    normal = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    radial = center - [0, 0, -.004]
    radial[:, 1] = 0
    selected = ((normal * radial).sum(1) > 0) & (center[:, 2] < -.04) & (abs(center[:, 0]) > .035) & (abs(center[:, 0]) < .09) & (center[:, 1] > .56)
    gaps = []
    for face in faces[selected]:
        for u, v in [(1/3, 1/3), (.1, .1), (.8, .1), (.1, .8), (.45, .1), (.1, .45), (.45, .45)]:
            point = (points[face[0]] * (1 - u - v) + points[face[1]] * u + points[face[2]] * v).astype(float)
            origin = np.array([0, point[1], -.004])
            direction = point - origin
            radius = np.linalg.norm(direction)
            direction /= radius
            h = np.cross(direction, ac)
            determinant = (ab * h).sum(1)
            valid = abs(determinant) > 1e-12
            inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
            offset = origin - a
            bu = (offset * h).sum(1) * inverse
            cross = np.cross(offset, ab)
            bv = (cross * direction).sum(1) * inverse
            distance = (cross * ac).sum(1) * inverse
            hits = distance[valid & (bu >= 0) & (bv >= 0) & (bu + bv <= 1) & (distance > 0)]
            if len(hits):
                gaps.append(float(radius - hits.max()))
    return {'samples': len(gaps), 'minimum_radial_gap': min(gaps), 'crossed_samples': sum(gap <= 0 for gap in gaps)}


previous, current = samples(before, old_binary), samples(after, binary)
assert current['samples'] == previous['samples'] > 1000
assert current['crossed_samples'] < previous['crossed_samples'] / 20
assert current['minimum_radial_gap'] > -.001
report = {
    'date': '2026-10-13', 'sha256': hashlib.sha256((TARGET / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
    'preserved': ['all leather and buckles', 'central guards', 'all skin weights', 'unselected plate vertices', 'UVs', 'indices', 'embedded textures', 'materials', 'rig', 'occlusion'],
    'previous_leather_contact': previous, 'leather_contact': current,
    'scope': 'Seven interior samples per outward leather triangle at the rear waist, rest pose. Small residual overlap remains at the innermost leather edge; not a complete animated collision test.',
}
(TARGET / 'plate-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
