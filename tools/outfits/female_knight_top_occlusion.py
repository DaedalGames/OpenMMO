import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor

BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = ROOT / 'assets/items/female_knight_top/tripo_v1/fitted_v2/body-occlusion.json'
doc, binary = read_glb(BODY)
primitive = doc['meshes'][0]['primitives'][0]
p = accessor(doc, binary, primitive['attributes']['POSITION'])
f = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
_, welded = np.unique(np.round(p, 6), axis=0, return_inverse=True)
welded = welded.ravel()
edges = welded[f[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
_, labels = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(welded.max() + 1,) * 2), directed=False)
face_labels = labels[welded[f[:, 0]]]
main = np.bincount(face_labels).argmax()
underwear = np.zeros(len(f), dtype=bool)
for label in np.unique(face_labels):
    if label == main:
        continue
    mask = face_labels == label
    q = p[np.unique(f[mask])]
    if q[:, 1].min() > .64 and q[:, 1].max() < .86:
        underwear |= mask
covered = (p[:, 1] > .709) & (p[:, 1] < .851) & (np.abs(p[:, 0]) < .105)
for sign in [1, -1]:
    start = np.array([sign * .089, .810, -.026])
    end = np.array([sign * .178, .697, -.026])
    axis = (end - start) / np.linalg.norm(end - start)
    along = (p - start) @ axis
    radius = np.linalg.norm(p - start - along[:, None] * axis, axis=1)
    covered |= (along > -.012) & (along < .140) & (radius < .045) & (p[:, 0] * sign > .075)
skin = covered[f].all(1) & (face_labels == main)
record = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'top': 'top_female_knight', 'mesh_index': 0, 'primitive_index': 0, 'source_triangles': sum(doc['accessors'][part['indices']]['count'] // 3 for part in doc['meshes'][0]['primitives']), 'primitive_triangles': len(f), 'hide_triangle_indices': np.flatnonzero(skin | underwear).tolist(),
          'underwear_triangles': int(underwear.sum()), 'covered_skin_triangles': int(skin.sum()),
          'visible_triangles': int((~(skin | underwear)).sum()) + sum(doc['accessors'][part['indices']]['count'] // 3 for part in doc['meshes'][0]['primitives'][1:]),
          'scope': 'Reversible equipment mask on this exact body. Entire upper underwear including bow; torso and upper arms inside armor with hem/cuff margins. Abdomen, head, hands and distal forearms retained. Restore full index buffer on unequip/load failure.'}
OUTPUT.write_text(json.dumps(record, indent=2) + '\n')
print({key: record[key] for key in ['underwear_triangles', 'covered_skin_triangles', 'visible_triangles']})
