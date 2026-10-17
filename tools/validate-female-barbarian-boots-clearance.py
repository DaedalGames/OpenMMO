import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

parser = argparse.ArgumentParser()
parser.add_argument('directory', nargs='?', default='assets/items/female_barbarian_boots/tripo_v1/fitted_v3')
parser.add_argument('--side', choices=['right', 'left'], default='right')
parser.add_argument('--stride', type=int, default=1)
parser.add_argument('--motions', nargs='+')
parser.add_argument('--regions', nargs='+', choices=['ankle', 'front', 'connector', 'heel'])
parser.add_argument('--output')
args = parser.parse_args()
directory = Path(args.directory)
prefix = 'clearance' if args.side == 'right' else 'clearance-left'
manifest = json.loads((directory / f'{prefix}-poses.json').read_text())
source_hash = hashlib.sha256((directory / 'boots_female_barbarian.glb').read_bytes()).hexdigest()
assert source_hash == manifest['source_sha256'], 'Regenerate poses for the current sandal'
body_count = len(manifest['body_indices'])
boot_count = manifest['boot_vertices']
poses = np.fromfile(directory / f'{prefix}-poses.bin', dtype=np.float32).reshape(-1, body_count + boot_count, 3)
body_faces = np.array(manifest['body_faces'])
boot_faces = np.array(manifest['boot_faces']).reshape(-1, 3)
fit = np.load(directory / 'fit-data.npz')
source = fit['source']
front = (source[:, 0] < -.1) & (source[:, 1] > -.42)
connector = np.arange(boot_count) >= int(fit.get('original_vertex_count', boot_count))
regions = {'ankle': fit['rings'] | fit['buckles'], 'front': front, 'connector': connector}
if 'heel_straps' in fit:
    regions['heel'] = fit['heel_straps']
if args.regions:
    regions = {name: regions[name] for name in args.regions}
barycentric = np.array([[1/3, 1/3, 1/3], [.5, .5, 0], [0, .5, .5], [.5, 0, .5]])
minimum = {name: {'distance': float('inf')} for name in regions}
frames = []
for frame in range(0, len(poses), args.stride):
    if args.motions and manifest['poses'][frame]['name'] not in args.motions:
        continue
    body, boots = poses[frame, :body_count], poses[frame, body_count:]
    mesh = trimesh.Trimesh(body, body_faces, process=False)
    result = dict(manifest['poses'][frame])
    for name, mask in regions.items():
        faces = boot_faces[mask[boot_faces].any(1)]
        if not len(faces):
            continue
        probes = np.vstack([boots[mask], np.einsum('sk,fkj->fsj', barycentric, boots[faces]).reshape(-1, 3)])
        closest, distance, triangles = trimesh.proximity.closest_point(mesh, probes)
        normals = mesh.face_normals[triangles]
        signed = np.einsum('ij,ij->i', probes - closest, normals)
        depth = float(signed.min())
        result[name] = {'minimum_distance': depth, 'penetrating_samples': int((signed < -.00036).sum())}
        if depth < minimum[name]['distance']:
            minimum[name] = {'distance': depth, **manifest['poses'][frame]}
    frames.append(result)
    if frame % 61 == 0:
        print(json.dumps({'frame': frame, 'minimum': minimum}), flush=True)
if not frames:
    raise SystemExit('No matching poses; check --motions and --stride')

report = {'source_sha256': source_hash, 'side': args.side, 'selected_motions': args.motions,
          'selected_regions': list(regions),
          'frame_count': len(frames), 'stride': args.stride, 'minimum': minimum, 'frames': frames,
          'scope': 'Sandal vertices, face centers and edge midpoints against exact posed skin triangles after the reversible sole mask.'}
(directory / (args.output or f'{prefix}-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'frames': len(frames), 'minimum': minimum}), flush=True)

if any(value['distance'] < -.00036 for value in minimum.values()):
    raise SystemExit('Sandal intersects visible skin; see clearance report')
