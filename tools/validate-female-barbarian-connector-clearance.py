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
args = parser.parse_args()
directory = Path(args.directory)
prefix = 'clearance' if args.side == 'right' else 'clearance-left'
manifest = json.loads((directory / f'{prefix}-poses.json').read_text())
source_hash = hashlib.sha256((directory / 'boots_female_barbarian.glb').read_bytes()).hexdigest()
assert source_hash == manifest['source_sha256'], 'Regenerate poses for the current sandal'
fit = np.load(directory / 'fit-data.npz')
faces = np.array(manifest['boot_faces']).reshape(-1, 3)
first = int(fit['original_vertex_count'])
connector_faces = faces[(faces >= first).all(1) & np.isin((faces - first) % 4, [2, 3]).all(1)]
band_faces = faces[(fit['rings'] | fit['buckles'])[faces].any(1)]
anchors = fit[f'connector_anchors_{args.side}']
body_count = len(manifest['body_indices'])
poses = np.fromfile(directory / f'{prefix}-poses.bin', dtype=np.float32).reshape(
    -1, body_count + manifest['boot_vertices'], 3)


def edges(triangles):
    return np.unique(np.sort(triangles[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)


def crossings(points, segments, mesh):
    origins = points[segments[:, 0]]
    delta = points[segments[:, 1]] - origins
    lengths = np.linalg.norm(delta, axis=1)
    valid = lengths > 1e-8
    origins, delta, lengths = origins[valid], delta[valid], lengths[valid]
    locations, rays, _ = mesh.ray.intersects_location(origins, delta / lengths[:, None])
    distance = np.linalg.norm(locations - origins[rays], axis=1)
    return int(((distance > 1e-7) & (distance < lengths[rays] - 1e-7)).sum())


connector_edges, band_edges = edges(connector_faces), edges(band_faces)
frames = []
minimum = {'distance': float('inf')}
maximum_attachment = {'distance': 0}
for frame in range(0, len(poses), args.stride):
    points = poses[frame, body_count:]
    bands = trimesh.Trimesh(points, band_faces, process=False)
    connector = trimesh.Trimesh(points, connector_faces, process=False)
    probes = np.vstack([points[np.unique(connector_faces)], points[connector_faces].mean(1), points[connector_edges].mean(1)])
    _, distance, _ = trimesh.proximity.closest_point(bands, probes)
    depth = float(distance.min())
    hits = crossings(points, connector_edges, bands) + crossings(points, band_edges, connector)
    anchor_points = np.einsum('nk,nkj->nj', anchors[:, 4:], points[anchors[:, 1:4].astype(int)])
    attachment = float(np.linalg.norm(points[anchors[:, 0].astype(int)] - anchor_points, axis=1).max())
    result = {**manifest['poses'][frame], 'minimum_distance': depth, 'edge_surface_crossings': hits,
              'maximum_attachment_distance': attachment}
    frames.append(result)
    if depth < minimum['distance']:
        minimum = {'distance': depth, **manifest['poses'][frame]}
    if attachment > maximum_attachment['distance']:
        maximum_attachment = {'distance': attachment, **manifest['poses'][frame]}
    if frame % 61 == 0:
        print(json.dumps({'frame': frame, 'minimum': minimum, 'crossings': hits}), flush=True)

report = {'source_sha256': source_hash, 'side': args.side, 'frame_count': len(frames), 'stride': args.stride,
          'meters_per_source_unit': 1.8, 'minimum': minimum, 'maximum_attachment_distance': maximum_attachment,
          'attachment_points': len(anchors), 'frames_with_crossings': sum(
              entry['edge_surface_crossings'] > 0 for entry in frames), 'frames': frames,
          'scope': 'Exposed connector outer-face vertices, centers and edge midpoints against ankle rings/buckles; '
                   'segment-to-surface rays in both directions. Inner contact is intentionally embedded; '
                   'stored attachment points are compared with the corresponding posed ring triangles.'}
(directory / f'connector-layer-{args.side}-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ['frame_count', 'minimum', 'maximum_attachment_distance', 'frames_with_crossings']}), flush=True)
if minimum['distance'] < .0002 or report['frames_with_crossings'] or maximum_attachment['distance'] > .0015:
    raise SystemExit('Connector attachment or exposed-surface clearance failed; see connector layer report')
