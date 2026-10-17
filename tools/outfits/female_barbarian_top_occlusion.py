import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor

BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
DIRECTORY = ROOT / 'assets/items/female_barbarian_top/tripo_v1/fitted_v1'
TOP = DIRECTORY / 'top_female_barbarian.glb'
REACH = .0216
INSET = .036


def mesh(path):
    doc, binary = read_glb(path)
    primitive = doc['meshes'][0]['primitives'][0]
    attributes = primitive['attributes']
    return (doc, accessor(doc, binary, attributes['POSITION']), accessor(doc, binary, attributes['NORMAL']),
            accessor(doc, binary, primitive['indices']).reshape(-1, 3))


doc, p, n, f = mesh(BODY)
_, top_points, _, top_faces = mesh(TOP)
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
    if q[:, 1].min() > 1.152 and q[:, 1].max() < 1.548:
        underwear |= mask

# Skin counts as covered when a ray along its normal meets the top within REACH.
# Only the rigid cups hide skin; the pauldron and straps move apart from the skin beneath them.
fit = np.load(DIRECTORY / 'fit-data.npz')
blender = fit['fitted']
_, nearest = cKDTree(np.c_[blender[:, 0], blender[:, 2], -blender[:, 1]]).query(top_points)
cup_faces = top_faces[fit['cups'][nearest][top_faces].all(1)]
a, b, c = (top_points[cup_faces[:, k]] for k in range(3))
e1, e2 = b - a, c - a
candidates = np.flatnonzero((p[:, 1] > 1.188) & (p[:, 1] < 1.584) & (labels[welded] == main))
hit = np.zeros(len(p), dtype=bool)
for i in candidates:
    h = np.cross(n[i], e2)
    det = (e1 * h).sum(1)
    valid = np.abs(det) > 3.24e-12
    inv = np.where(valid, 1 / np.where(valid, det, 1), 0)
    s = p[i] - a
    u = (s * h).sum(1) * inv
    q = np.cross(s, e1)
    v = (q * n[i]).sum(1) * inv
    t = (q * e2).sum(1) * inv
    hit[i] = (valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0) & (t < REACH)).any()
skin_vertices = np.flatnonzero(labels[welded] == main)
tree = cKDTree(p[skin_vertices])
covered = hit.copy()
for i in np.flatnonzero(hit):
    if not hit[skin_vertices[tree.query_ball_point(p[i], INSET)]].all():
        covered[i] = False
skin = covered[f].all(1) & (face_labels == main)
source_triangles = sum(doc['accessors'][part['indices']]['count'] // 3 for part in doc['meshes'][0]['primitives'])
record = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'top': 'top_female_barbarian', 'top_sha256': hashlib.sha256(TOP.read_bytes()).hexdigest(),
          'mesh_index': 0, 'primitive_index': 0, 'source_triangles': source_triangles, 'primitive_triangles': len(f),
          'hide_triangle_indices': np.flatnonzero(skin | underwear).tolist(),
          'underwear_triangles': int(underwear.sum()), 'covered_skin_triangles': int(skin.sum()),
          'visible_triangles': source_triangles - int((skin | underwear).sum()),
          'scope': f'Reversible equipment mask on this exact body. Entire upper underwear including bow; skin whose normal ray meets the rigid cups within {REACH} and lies at least {INSET} inside the covered rim. Restore full index buffer on unequip/load failure.'}
(DIRECTORY / 'body-occlusion.json').write_text(json.dumps(record, indent=2) + '\n')
print({key: record[key] for key in ['underwear_triangles', 'covered_skin_triangles', 'visible_triangles']})
