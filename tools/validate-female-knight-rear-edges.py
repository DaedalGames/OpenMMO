import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from lib.glb import read_glb, view_bytes
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, TARGET = DIRECTORY / 'fitted_v26', DIRECTORY / 'fitted_v27'
before, old_binary = read_glb(SOURCE / 'bottom_female_knight.glb')
after, binary = read_glb(TARGET / 'bottom_female_knight.glb')
fitting = json.loads((TARGET / 'fitting.json').read_text())
changes = {entry['primitive']: entry['vertices'] for entry in fitting['rear_plate_changes']}
for index, (old, new) in enumerate(zip(before['meshes'][0]['primitives'], after['meshes'][0]['primitives'], strict=True)):
    assert np.array_equal(accessor(before, old_binary, old['indices']), accessor(after, binary, new['indices']))
    old_points = accessor(before, old_binary, old['attributes']['POSITION'])
    for name, attribute in old['attributes'].items():
        a, b = accessor(before, old_binary, attribute), accessor(after, binary, new['attributes'][name])
        if index in changes and name in ['POSITION', 'NORMAL', 'TANGENT']:
            unchanged = np.ones(len(a), dtype=bool)
            unchanged[changes[index]] = False
            assert np.array_equal(a[unchanged], b[unchanged]), (index, name)
            assert np.array_equal(a[old_points[:, 2] >= 0], b[old_points[:, 2] >= 0]), (index, name, 'front')
            assert np.isfinite(b).all()
            if name != 'POSITION':
                assert np.max(abs(np.linalg.norm(b[:, :3], axis=1) - 1)) < 1e-6
        else:
            assert np.array_equal(a, b), (index, name)
for key in ['materials', 'images', 'textures', 'skins', 'animations']:
    assert before.get(key) == after.get(key)
for image in before['images']:
    assert view_bytes(before, old_binary, image['bufferView']) == view_bytes(after, binary, image['bufferView'])
assert (SOURCE / 'body-occlusion.json').read_bytes() == (TARGET / 'body-occlusion.json').read_bytes()
old_points = accessor(before, old_binary, before['meshes'][0]['primitives'][1]['attributes']['POSITION'])
points = accessor(after, binary, after['meshes'][0]['primitives'][1]['attributes']['POSITION'])
profiles = []
for edge in fitting['rear_edge_vertices']:
    ids = np.array(edge['vertices'])
    front = old_points[ids[0] + 92:ids[0] + 105][::-1]
    width = PchipInterpolator(front[:, 1], abs(front[:, 0]))
    target = width(np.clip(points[ids, 1], front[0, 1], front[-1, 1]))
    error = float(np.max(abs(abs(points[ids, 0]) - target)))
    assert error < 1e-6
    assert np.all(np.diff(points[ids, 1]) < 0)
    if edge['level'] == 1:
        assert abs(points[ids[-1], 0]) > abs(points[ids[-2], 0]) + .006
    if edge['level'] == 2:
        assert abs(points[ids[-1], 0]) > abs(points[ids[-2], 0]) + .025
    profiles.append({'side': edge['side'], 'level': edge['level'], 'maximum_front_width_error': error})
for old, new in zip(before['meshes'][0]['primitives'][1:], after['meshes'][0]['primitives'][1:]):
    faces = accessor(after, binary, new['indices']).reshape(-1, 3)
    a = accessor(before, old_binary, old['attributes']['POSITION'])[faces].astype(float)
    b = accessor(after, binary, new['attributes']['POSITION'])[faces].astype(float)
    area_before = np.linalg.norm(np.cross(a[:, 1]-a[:, 0], a[:, 2]-a[:, 0]), axis=1)
    area_after = np.linalg.norm(np.cross(b[:, 1]-b[:, 0], b[:, 2]-b[:, 0]), axis=1)
    assert np.all(area_after[area_before > 1e-12] > 1e-12)
report = {'date': '2026-10-13', 'sha256': hashlib.sha256((TARGET / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
          'edge_profiles': profiles, 'preserved': fitting['preserved'],
          'scope': 'Rear edge widths match sampled front profiles. Unchanged front and leather attributes, normalized shading vectors and nondegenerate triangles checked. Not a full collision test.'}
(TARGET / 'edge-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
