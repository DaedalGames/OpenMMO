"""Check snap contact with the animated cuff, including its rear surface."""
import importlib.util
import json
from pathlib import Path

import numpy as np

from outfits.skinning import deform

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/items/female_rogue_gloves/tripo_v1/fitted_v1'
spec = importlib.util.spec_from_file_location('gloves', ROOT / 'tools/fit-female-rogue-tripo-gloves.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
data = np.load(OUT / 'fit-data.npz')
fitting = json.loads((OUT / 'fitting.json').read_text())
poses = [{'clip': 'rest', 'time': 0, 'matrices': np.repeat(np.eye(4)[None], 65, axis=0).transpose(0, 2, 1).reshape(65, 16).tolist()}]
poses.extend(json.loads((OUT / 'validation-poses.json').read_text()))
records = []
for side in ['Right', 'Left']:
    points, faces, joints, weights = [data[f'{side}_{key}'] for key in ['positions', 'faces', 'joints', 'weights']]
    side_record = fitting['sides'][side]
    shell_faces = faces[:side_record['hand_shell_triangles']]
    for snap in side_record['snap_attachments']:
        start, end = snap['vertices']
        normal = np.array(snap['normal'])
        depth = points[start:end] @ normal
        rear = np.flatnonzero(depth < depth.min() + .00015) + start
        for pose in poses:
            matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
            glove = deform(points, joints, weights, matrices)
            closest, normals, _ = fit.surface.nearest_surface(glove[rear], (glove, shell_faces, weights))
            gap = np.sum((glove[rear] - closest) * normals, axis=1)
            records.append({'side': side, 'surface': snap['surface'], 'clip': pose['clip'], 'time': pose['time'], 'maximum_rear_gap_m': float(gap.max()), 'minimum_rear_gap_m': float(gap.min()), 'nearest_rear_contact_m': float(np.abs(gap).min())})
report = {'glove_sha256': fit.helpers.digest(OUT / 'gloves_female_rogue.glb'), 'poses_per_side': len(poses), 'snap_count': 4, 'scope': 'Actual rear snap vertices measured against the animated glove shell, including local cuff curvature and skinning.', 'records': records}
(OUT / 'snap-validation.json').write_text(json.dumps(report, indent=2) + '\n')
summary = {key: max(row[key] for row in records) for key in ['maximum_rear_gap_m', 'nearest_rear_contact_m']}
summary['minimum_rear_gap_m'] = min(row['minimum_rear_gap_m'] for row in records)
print(json.dumps(summary, indent=2))
assert summary['maximum_rear_gap_m'] < .0005
assert summary['nearest_rear_contact_m'] < .0003
assert summary['minimum_rear_gap_m'] > -.0006
