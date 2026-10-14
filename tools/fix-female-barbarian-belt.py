import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
REPAIR = DIRECTORY / 'belt_repair_v2'
SOURCE = (ROOT / sys.argv[1]).resolve() if len(sys.argv) > 1 else DIRECTORY / 'belt_repair_v1/before.glb'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
INSET = .002

REPAIR.mkdir(exist_ok=True)
doc, original = read_glb(SOURCE)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
binary = bytearray(original)
primitive, = doc['meshes'][0]['primitives']
attributes = primitive['attributes']
positions = accessor(doc, original, attributes['POSITION'])
triangles = accessor(doc, original, primitive['indices']).reshape(-1, 3)
assert len(triangles) == 3256 and len(positions) == 4796
assert np.allclose(positions[triangles[2595]].mean(0), [-.00295, .59637, -.05770], atol=1e-5)

fit = np.load(DIRECTORY / 'fit-data.npz')
fitted = fit['fitted']
_, nearest = cKDTree(np.c_[fitted[:, 0], fitted[:, 2], -fitted[:, 1]]).query(positions)
belt = fit['belt'][nearest]
centers = positions[triangles].mean(1)
normals = np.cross(positions[triangles[:, 1]] - positions[triangles[:, 0]],
                   positions[triangles[:, 2]] - positions[triangles[:, 0]])
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
lining = belt[triangles].all(1) & (centers[:, 2] < -.025) & (centers[:, 1] > .58) & (normals[:, 2] > .35)
assert lining[1417] and lining[2595]
_, welded = np.unique(positions.round(6), axis=0, return_inverse=True)
moved = np.isin(welded, welded[np.unique(triangles[lining])])
result = positions.copy()
axis = np.array([0, -.005607772618532181])
inward = axis - positions[moved][:, [0, 2]]
inward /= np.linalg.norm(inward, axis=1, keepdims=True)
result[np.ix_(moved, [0, 2])] += inward * INSET
assert np.array_equal(result[~moved], positions[~moved])
assert np.allclose(np.linalg.norm(result[moved] - positions[moved], axis=1), INSET, atol=1e-7)
metadata = doc['accessors'][attributes['POSITION']]
attributes['POSITION'] = add_accessor(doc, binary, result, metadata['type'], metadata['componentType'])
doc['bufferViews'][doc['accessors'][attributes['POSITION']]['bufferView']]['target'] = 34962
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT, doc, binary)

report = {
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': source_hash,
    'output': str(OUTPUT.relative_to(ROOT)),
    'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Inset the rear belt lining toward the pelvis by 2 mm, preserving welded seams; restore original UVs instead of recoloring the crossing backfaces.',
    'triangles': len(triangles),
    'lining_triangles': np.flatnonzero(lining).tolist(),
    'moved_vertices': int(moved.sum()),
    'inset': INSET,
    'vertices': len(positions),
    'textures_uvs_weights_and_indices_unchanged': True,
}
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
fitting_path = ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json'
fitting = json.loads(fitting_path.read_text())
fitting['rigging'].update(sha256=report['output_sha256'], vertices=report['vertices'])
fitting.pop('belt_uv_repair', None)
fitting['belt_lining_repair'] = str((REPAIR / 'repair.json').relative_to(ROOT))
fitting_path.write_text(json.dumps(fitting, indent=2) + '\n')
print(json.dumps(report, indent=2))
