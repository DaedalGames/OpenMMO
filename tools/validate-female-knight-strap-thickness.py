import json
import sys
from pathlib import Path

import numpy as np

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
VERSION = sys.argv[1] if len(sys.argv) > 1 else 'v17'
assert VERSION in ['v16', 'v17']


def load(version):
    directory = DIRECTORY / f'fitted_{version}'
    doc, binary = read_glb(directory / 'bottom_female_knight.glb')
    fitting = json.loads((directory / 'fitting.json').read_text())
    return doc, binary, fitting


def clearances(doc, binary, fitting, side):
    primitive = doc['meshes'][0]['primitives'][0]
    points = accessor(doc, binary, primitive['attributes']['POSITION'])
    faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
    selected = np.array(fitting['vertices'])
    faces = faces[np.isin(faces[:, 0], selected) & (points[faces[:, 0], 0] * side > 0)]
    triangles = points[faces].astype(float)
    a, ab, ac = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    denominator = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    area = np.linalg.norm(np.cross(ab, ac), axis=1)
    valid = (abs(denominator) > 1e-12) & (abs(denominator) > .7 * area)
    gaps = []
    for height in np.linspace(.445, .556, 36):
        for x in side * np.linspace(.03, .075, 181):
            offset = np.array([x, height, 0]) - a
            u = np.divide(offset[:, 0] * ac[:, 1] - offset[:, 1] * ac[:, 0], denominator, out=np.zeros(len(a)), where=valid)
            v = np.divide(ab[:, 0] * offset[:, 1] - ab[:, 1] * offset[:, 0], denominator, out=np.zeros(len(a)), where=valid)
            hit = valid & (u > .02) & (v > .02) & (u + v < .98)
            front, back = np.flatnonzero(hit & (denominator > 0)), np.flatnonzero(hit & (denominator < 0))
            depth = a[:, 2] + u * ab[:, 2] + v * ac[:, 2]
            if len(front) == len(back) == 1:
                gaps.append(float(depth[front[0]] - depth[back[0]]))
    return gaps


before, before_binary, old_fitting = load('v15')
after, after_binary, fitting = load(VERSION)
sides = [-1, 1] if VERSION == 'v17' else [-1]
results = []
for side in sides:
    old_gaps = clearances(before, before_binary, old_fitting, side)
    gaps = clearances(after, after_binary, fitting, side)
    assert len(gaps) > 1000 and len(old_gaps) > 1000
    assert min(gaps) > .00015
    assert min(gaps) > min(old_gaps)
    results.append({
        'side': side, 'samples': len(gaps), 'previous_samples': len(old_gaps),
        'previous_crossed_samples': sum(gap <= 0 for gap in old_gaps),
        'previous_minimum_gap': min(old_gaps), 'minimum_gap': min(gaps),
        'crossed_samples': 0,
    })
changed = np.array(fitting['thickened_vertices'])
assert before['materials'] == after['materials']
assert before['skins'] == after['skins']
for index, (old, new) in enumerate(zip(before['meshes'][0]['primitives'], after['meshes'][0]['primitives'], strict=True)):
    assert np.array_equal(accessor(before, before_binary, old['indices']), accessor(after, after_binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a = accessor(before, before_binary, attribute)
        b = accessor(after, after_binary, new['attributes'][name])
        if index == 0 and name in ['POSITION', 'NORMAL', 'TANGENT']:
            other = np.ones(len(a), dtype=bool)
            other[changed] = False
            assert np.array_equal(a[other], b[other]), name
            if name == 'POSITION':
                assert np.array_equal(a[:, :2], b[:, :2])
                assert np.max(abs(a[:, 2] - b[:, 2])) < .000451
        else:
            assert np.array_equal(a, b), name
report = {
    'date': '2026-10-13', 'sha256': fitting['sha256'],
    'sides': results, 'thickened_vertices': len(changed),
    'preserved': ['buckles', 'strap tips', 'XY positions', 'topology', 'UVs', 'weights', 'materials', 'skeleton'],
    'scope': 'Rest-pose broad front/back faces with |normal.z| > 0.7, excluding narrow sidewalls; not a full animated collision proof.',
}
(DIRECTORY / f'fitted_{VERSION}/thickness-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
