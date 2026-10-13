"""Measure gauntlet clearance against each arm through sampled game poses."""
import importlib.util
import json
from pathlib import Path

import numpy as np

from outfits.skinning import deform, deform_dense

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fitting', ROOT / 'tools/fit-female-knight-gloves.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
_, _, names, _, body = fit.setup_body()
data = np.load(fit.OUT / 'fit-data.npz')
poses = json.loads((fit.OUT / 'validation-poses.json').read_text())
results = []
for side in ['Right', 'Left']:
    if f'{side}_positions' not in data:
        continue
    ids = [i for i, name in enumerate(names) if name.startswith(side) and ('Hand' in name or 'Arm' in name)]
    faces = body[1][(body[2][:, ids].sum(1)[body[1]].mean(1) > .5)]
    regions = {'hand':data['source'][:, 1] < -.18, 'forearm':(data['source'][:, 1] >= -.18) & (data['source'][:, 1] < .20), 'elbow':data['source'][:, 1] >= .20}
    for pose in poses:
        matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        skin = deform_dense(body[0], body[2], matrices)
        points = deform(data[f'{side}_positions'], data[f'{side}_joints'], data[f'{side}_weights'], matrices)
        nearest, normals, _ = fit.surface_tools.nearest_surface(points, (skin, faces, np.zeros((len(skin), 1))))
        signed = np.sum((points-nearest)*normals, axis=1)
        results.append({'side':side, 'clip':pose['clip'], 'time':pose['time'], 'regions':{name:{'minimum_signed_distance':float(signed[mask].min()), 'vertices_deeper_than_2mm':int(np.sum(signed[mask]<-.002))} for name, mask in regions.items()}})
report = {'scope':'Nearest-surface signed distance of gauntlet vertices to the same unmasked arm. Covered skin and lining contact are reported; this is not a proof of continuous collision-free motion.', 'poses_per_side':len(poses), 'results':results}
(fit.OUT / 'clearance-validation.json').write_text(json.dumps(report, indent=2)+'\n')
for region in ['hand', 'forearm', 'elbow']:
    worst = min(results, key=lambda row:row['regions'][region]['minimum_signed_distance'])
    print(region, worst['side'], worst['clip'], worst['regions'][region])
