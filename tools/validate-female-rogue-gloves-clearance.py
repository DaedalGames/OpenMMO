"""Audit glove vertices and triangle centers against the posed hand surface."""
import json
import sys
from pathlib import Path

import numpy as np

from outfits import female_rogue_gloves as fit
from outfits.skinning import deform, deform_dense

ROOT = Path(__file__).resolve().parents[1]
_, _, names, _, body = fit.knight.setup_body()
OUT = ROOT / (sys.argv[sys.argv.index('--directory') + 1] if '--directory' in sys.argv else 'assets/items/female_rogue_gloves/tripo_v1/fitted_v1')
data = np.load(OUT / 'fit-data.npz')
poses = [{'clip': 'rest', 'time': 0, 'matrices': np.repeat(np.eye(4)[None], len(names), axis=0).transpose(0, 2, 1).reshape(len(names), 16).tolist()}]
poses.extend(json.loads((OUT / 'validation-poses.json').read_text()))
records = []
hidden = set(json.loads((OUT / 'body-occlusion.json').read_text())['hide_triangle_indices'])
for side in ['Right', 'Left']:
    ids = [i for i, name in enumerate(names) if name.startswith(side) and ('Hand' in name or 'ForeArm' in name)]
    face_ids = np.flatnonzero(body[2][:, ids].sum(1)[body[1]].mean(1) > .5)
    faces = body[1][face_ids]
    hidden_faces = np.repeat([int(i in hidden) for i in face_ids], 3)[:, None]
    expanded = np.arange(len(faces) * 3).reshape(-1, 3)
    points, joints, weights, triangles = [data[f'{side}_{name}'] for name in ['positions', 'joints', 'weights', 'faces']]
    _, unique = np.unique(np.round(points, 6), axis=0, return_index=True)
    for pose in poses:
        matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        skin = deform_dense(body[0], body[2], matrices)
        glove = deform(points, joints, weights, matrices)
        samples = np.vstack([glove[unique], glove[triangles].mean(1)])
        signed, covered = [], []
        for start in range(0, len(samples), 256):
            chunk = samples[start:start + 256]
            closest, normals, coverage = fit.surface.nearest_surface(chunk, (skin[faces].reshape(-1, 3), expanded, hidden_faces))
            signed.extend(np.sum((chunk - closest) * normals, axis=1))
            covered.extend(coverage[:, 0] > .99)
        signed = np.array(signed)
        records.append({'side': side, 'clip': pose['clip'], 'time': pose['time'], 'sample_count': len(samples), 'minimum_signed_distance_m': float(signed.min()), 'samples_deeper_than_2mm': int((signed < -.002).sum()), 'exposed_skin_samples_deeper_than_2mm': int(((signed < -.002) & ~np.array(covered)).sum())})
    print(side, 'audited', len(poses), 'poses', flush=True)
report = {'scope': 'Nearest-triangle signed distances for unique glove vertices and triangle centers against the same full unmasked hand/forearm. Includes closed-finger contact; not a continuous collision proof.', 'poses_per_side': len(poses), 'records': records}
(OUT / 'clearance-validation.json').write_text(json.dumps(report, indent=2) + '\n')
worst = min(records, key=lambda row: row['minimum_signed_distance_m'])
print(json.dumps({'worst': worst, 'samples_deeper_than_2mm': sum(row['samples_deeper_than_2mm'] for row in records), 'exposed_skin_samples_deeper_than_2mm': sum(row['exposed_skin_samples_deeper_than_2mm'] for row in records)}, indent=2))
