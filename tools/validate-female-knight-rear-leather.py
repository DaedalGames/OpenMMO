import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
TARGET = DIRECTORY / 'fitted_v25'
before, old_binary = read_glb(DIRECTORY / 'fitted_v24/bottom_female_knight.glb')
after, binary = read_glb(TARGET / 'bottom_female_knight.glb')
fitting = json.loads((TARGET / 'fitting.json').read_text())
changed = np.array(fitting['rear_leather_vertices'])
for old, new in zip(before['meshes'][0]['primitives'], after['meshes'][0]['primitives'], strict=True):
    assert np.array_equal(accessor(before, old_binary, old['indices']), accessor(after, binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a, b = accessor(before, old_binary, attribute), accessor(after, binary, new['attributes'][name])
        if old is before['meshes'][0]['primitives'][0] and name == 'POSITION':
            assert np.array_equal(a[:, :2], b[:, :2])
            other = np.ones(len(a), dtype=bool)
            other[changed] = False
            assert np.array_equal(a[other], b[other])
            assert np.max(abs(a - b)) < .001501
        else:
            assert np.array_equal(a, b), name
for name in ['materials', 'textures', 'images', 'skins']:
    assert before[name] == after[name]
assert (TARGET / 'body-occlusion.json').read_bytes() == (DIRECTORY / 'fitted_v24/body-occlusion.json').read_bytes()
primitive = before['meshes'][0]['primitives'][0]
points = accessor(before, old_binary, primitive['attributes']['POSITION']).astype(float)
new_points = accessor(after, binary, after['meshes'][0]['primitives'][0]['attributes']['POSITION']).astype(float)
faces = accessor(before, old_binary, primitive['indices']).reshape(-1, 3)
regions, pairs = [], []
for vertices in fitting['rear_leather_regions']:
    region_faces = faces[np.isin(faces[:, 0], vertices)]
    triangles = points[region_faces]
    a = triangles[:, 0]
    ab, ac = triangles[:, 1] - a, triangles[:, 2] - a
    denominator = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    area = np.linalg.norm(np.cross(ab, ac), axis=1)
    gaps = [[], []]
    for i in np.flatnonzero((denominator < -.5 * area) & (triangles[:, :, 2].max(1) < -.035)):
        for bary in [[1/3]*3, [.6, .2, .2], [.2, .6, .2], [.2, .2, .6]]:
            origin = np.array(bary) @ triangles[i]
            offset = origin - a
            valid = abs(denominator) > 1e-12
            u = np.divide(offset[:, 0] * ac[:, 1] - offset[:, 1] * ac[:, 0], denominator, out=np.zeros(len(a)), where=valid)
            v = np.divide(ab[:, 0] * offset[:, 1] - ab[:, 1] * offset[:, 0], denominator, out=np.zeros(len(a)), where=valid)
            hits = np.flatnonzero((u > .001) & (v > .001) & (u + v < .999) & (denominator > .5 * area) & (triangles[:, :, 2].max(1) < -.015))
            if len(hits) != 1:
                continue
            j = hits[0]
            inner_bary = [1 - u[j] - v[j], u[j], v[j]]
            for positions, result in zip([points, new_points], gaps):
                result.append(float(np.array(inner_bary) @ positions[region_faces[j], 2] - np.array(bary) @ positions[region_faces[i], 2]))
            pairs.append({'outer': region_faces[i].tolist(), 'inner': region_faces[j].tolist(), 'outer_bary': bary, 'inner_bary': inner_bary})
    assert len(gaps[0]) > 100
    assert min(gaps[1]) > .00015
    regions.append({'samples': len(gaps[0]), 'before_minimum_gap': min(gaps[0]), 'before_crossed': sum(gap <= 0 for gap in gaps[0]), 'after_minimum_gap': min(gaps[1]), 'after_crossed': 0})
report = {'date': '2026-10-13', 'sha256': hashlib.sha256((TARGET / 'bottom_female_knight.glb').read_bytes()).hexdigest(), 'regions': regions,
          'preserved': fitting['preserved'], 'scope': 'Interior samples of broad rear leather faces, paired across Z in the rest pose. Excludes sidewalls and unpaired triangles.'}
(TARGET / 'thickness-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(TARGET / 'thickness-samples.json').write_text(json.dumps(pairs, indent=2) + '\n')
print(json.dumps(report))
