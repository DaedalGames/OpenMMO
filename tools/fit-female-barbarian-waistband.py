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
REPAIR = DIRECTORY / 'waistband_repair_v1'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
SOURCE = (ROOT / sys.argv[1]).resolve() if len(sys.argv) > 1 else REPAIR / 'before.glb'

doc, original = read_glb(SOURCE)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
binary = bytearray(original)
primitive, = doc['meshes'][0]['primitives']
attributes = primitive['attributes']
points = accessor(doc, original, attributes['POSITION'])
fit = np.load(DIRECTORY / 'fit-data.npz')
fitted = fit['fitted']
_, nearest = cKDTree(np.c_[fitted[:, 0], fitted[:, 2], -fitted[:, 1]]).query(points)
selected = fit['belt'][nearest] & (points[:, 1] > .602)
blend = np.clip((points[:, 1] - .602) / .009, 0, 1)
blend = blend * blend * (3 - 2 * blend)
result = points.copy()
result[selected, 1] += .004 * blend[selected]
triangles = accessor(doc, original, primitive['indices']).reshape(-1, 3)
lining_faces = json.loads((DIRECTORY / 'belt_repair_v2/repair.json').read_text())['lining_triangles']
_, welded = np.unique(points.round(6), axis=0, return_inverse=True)
lining = np.isin(welded, welded[np.unique(triangles[lining_faces])]) & selected
axis = np.array([0, -.005607772618532181])
inward = axis - points[lining][:, [0, 2]]
inward /= np.linalg.norm(inward, axis=1, keepdims=True)
result[np.ix_(lining, [0, 2])] += inward * (.0015 * blend[lining])[:, None]
assert np.array_equal(points[~selected], result[~selected])
assert np.array_equal(points[~lining][:, [0, 2]], result[~lining][:, [0, 2]])
metadata = doc['accessors'][attributes['POSITION']]
attributes['POSITION'] = add_accessor(doc, binary, result, metadata['type'], metadata['componentType'])
doc['bufferViews'][doc['accessors'][attributes['POSITION']]['bufferView']]['target'] = 34962
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT, doc, binary)
report = {
    'source': str(SOURCE.relative_to(ROOT)),
    'output': str(OUTPUT.relative_to(ROOT)),
    'source_sha256': source_hash,
    'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Raise the belt upper rim by up to 4 mm, blending between heights 0.602 and 0.611 m to cover the white underwear painted on the body.',
    'moved_vertices': int(selected.sum()),
    'maximum_height_change': float((result[:, 1] - points[:, 1]).max()),
    'upper_lining_inset': .0015,
    'textures_uvs_indices_and_weights_unchanged': True,
}
REPAIR.mkdir(exist_ok=True)
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
fitting_path = ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json'
fitting = json.loads(fitting_path.read_text())
fitting['rigging']['sha256'] = report['output_sha256']
fitting['waistband_repair'] = str((REPAIR / 'repair.json').relative_to(ROOT))
fitting_path.write_text(json.dumps(fitting, indent=2) + '\n')
print(json.dumps(report, indent=2))
