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
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
BOTTOM = DIRECTORY / 'bottom_female_barbarian.glb'
REACH = .012
INSET = .01


def mesh(path, all_parts=False):
    doc, binary = read_glb(path)
    points, normals, faces = [], [], []
    offset = 0
    for part in doc['meshes'] if all_parts else doc['meshes'][:1]:
        primitive = part['primitives'][0]
        attributes = primitive['attributes']
        vertices = accessor(doc, binary, attributes['POSITION'])
        points.append(vertices)
        normals.append(accessor(doc, binary, attributes['NORMAL']))
        faces.append(accessor(doc, binary, primitive['indices']).reshape(-1, 3) + offset)
        offset += len(vertices)
    return doc, np.concatenate(points), np.concatenate(normals), np.concatenate(faces)


doc, p, n, f = mesh(BODY)
_, bottom_points, _, bottom_faces = mesh(BOTTOM, all_parts=True)
_, welded = np.unique(np.round(p, 6), axis=0, return_inverse=True)
welded = welded.ravel()
edges = welded[f[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
_, labels = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(welded.max() + 1,) * 2), directed=False)
face_labels = labels[welded[f[:, 0]]]
main = np.bincount(face_labels).argmax()
panties = np.zeros(len(f), dtype=bool)
for label in np.unique(face_labels):
    q = p[np.unique(f[face_labels == label])]
    if label != main and q[:, 1].max() < .66:
        panties |= face_labels == label

# Mask covered skin conservatively; keep the fur openings visible.
fit = np.load(DIRECTORY / 'fit-data.npz')
blender = fit['fitted']
_, nearest = cKDTree(np.c_[blender[:, 0], blender[:, 2], -blender[:, 1]]).query(bottom_points)


def covered_by(faces_used, candidates, reach):
    a, b, c = (bottom_points[faces_used[:, k]] for k in range(3))
    e1, e2 = b - a, c - a
    hit = np.zeros(len(p), dtype=bool)
    for i in candidates:
        h = np.cross(n[i], e2)
        det = (e1 * h).sum(1)
        valid = np.abs(det) > 1e-12
        inv = np.where(valid, 1 / np.where(valid, det, 1), 0)
        s = p[i] - a
        u = (s * h).sum(1) * inv
        q = np.cross(s, e1)
        v = (q * n[i]).sum(1) * inv
        t = (q * e2).sum(1) * inv
        hit[i] = (valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0) & (t < reach)).any()
    return hit


belt_faces = bottom_faces[fit['belt'][nearest][bottom_faces].all(1)]
hit = covered_by(belt_faces, np.flatnonzero((p[:, 1] > .54) & (p[:, 1] < .66) & (np.abs(p[:, 0]) < .16)), REACH)
covered = hit.copy()
for label_mask in [labels[welded] == main, labels[welded] != main]:
    group = np.flatnonzero(label_mask)
    tree = cKDTree(p[group])
    for i in np.flatnonzero(hit & label_mask):
        if not hit[group[tree.query_ball_point(p[i], INSET)]].all():
            covered[i] = False
hidden = covered[f].all(1)
waistband = panties & (p[f, 1].min(1) > .585)
hidden |= waistband
source_triangles = sum(doc['accessors'][part['indices']]['count'] // 3 for part in doc['meshes'][0]['primitives'])
record = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'bottom': 'bottom_female_barbarian', 'bottom_sha256': hashlib.sha256(BOTTOM.read_bytes()).hexdigest(),
          'mesh_index': 0, 'primitive_index': 0, 'source_triangles': source_triangles, 'primitive_triangles': len(f),
          'hide_triangle_indices': np.flatnonzero(hidden).tolist(),
          'covered_skin_triangles': int((hidden & (face_labels == main)).sum()),
          'covered_panty_triangles': int((hidden & panties).sum()),
          'removed_panty_waistband_triangles': int(waistband.sum()),
          'visible_triangles': source_triangles - int(hidden.sum()),
          'scope': f'Reversible equipment mask on this exact body. Covered skin and panties use a normal ray within {REACH} and an inset of {INSET}; panty waistband faces entirely above 0.585 m are also hidden. Lower panties stay visible under the open fur panels. Restore full index buffer on unequip/load failure.'}
(DIRECTORY / 'body-occlusion.json').write_text(json.dumps(record, indent=2) + '\n')
print({key: record[key] for key in ['covered_skin_triangles', 'covered_panty_triangles', 'visible_triangles']})
