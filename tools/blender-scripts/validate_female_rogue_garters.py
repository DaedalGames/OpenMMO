import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor
from outfits.mesh_components import welded_islands
from outfits.skinning import deform

DIRECTORY = ROOT / 'assets/items/female_rogue_garters/fitted_v1'


def load(path):
    d, r = read_glb(path)
    p = d['meshes'][0]['primitives'][0]
    a = p['attributes']
    return (accessor(d, r, a['POSITION']), accessor(d, r, p['indices']).reshape(-1, 3),
            accessor(d, r, a['JOINTS_0']).astype(int), accessor(d, r, a['WEIGHTS_0']),
            accessor(d, r, p['targets'][0]['POSITION']) if p.get('targets') else 0)


bp, bf, bj, bw, _ = load(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
_, _, labels = welded_islands(bp, bf)
skin = (labels == np.bincount(labels).argmax()) & (np.abs(bp[:, 0]) < .30) & (bp[:, 1] > .62) & (bp[:, 1] < 1.02)
skin_faces = [bf[(skin & (bp[:, 0]*sign > .025))[bf].all(1)] for sign in [-1, 1]]
points, faces, joints, weights, seated = load(DIRECTORY / 'garters_female_rogue.glb')
samples = json.loads((ROOT / 'assets/items/female_rogue_boots/tripo_v1/fitted_v3/animation-samples.json').read_text())
samples.insert(0, {'clip': 'rest', 'phase': 0, 'matrices': np.tile(np.eye(4).T.ravel(), (65, 1)).tolist()})
vertices = [np.arange(i*68+4, i*68+64) for i in range(4)]
triangles = [faces[i*132+8:i*132+120] for i in range(4)]
report = {}
for sample in samples:
    matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    skin_points = deform(bp, bj, bw, matrices)
    surfaces = [BVHTree.FromPolygons([Vector(p) for p in skin_points], f.tolist()) for f in skin_faces]
    posed = deform(points+(seated if sample['clip'] == 'sit_idle' else 0), joints, weights, matrices)
    metrics = report.setdefault(sample['clip'], {'minimum_gap_m': 1., 'deeper_than_1mm': 0, 'samples': 0})
    for i in range(4):
        for query, p in enumerate(np.concatenate([posed[vertices[i]], posed[triangles[i]].mean(1)])):
            hit, normal, face, distance = surfaces[i//2].find_nearest(Vector(p))
            gap = float(np.dot(p-np.array(hit), normal))
            if gap < metrics['minimum_gap_m']:
                metrics['worst'] = {'phase': sample['phase'], 'strap': i, 'query': query,
                                    'point': p.tolist(), 'hit': list(hit), 'distance_m': distance,
                                    'body_triangle': skin_faces[i//2][face].tolist()}
            metrics['minimum_gap_m'] = min(metrics['minimum_gap_m'], gap)
            metrics['deeper_than_1mm'] += int(gap < -.001)
            metrics['samples'] += 1

result = {'asset_sha256': hashlib.sha256((DIRECTORY / 'garters_female_rogue.glb').read_bytes()).hexdigest(),
          'clips': report, 'scope': 'Visible ribbon vertices and triangle centers against same-leg thigh skin, bind pose plus 61 frames for all 14 actual preview motions with boot corrections. Tucked end rows and contact with hands or other limbs excluded.'}
(DIRECTORY / 'clearance-validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2), flush=True)
assert all(m['deeper_than_1mm'] == 0 for m in report.values()), 'Visible straps penetrate thigh skin'
