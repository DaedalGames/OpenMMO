import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

parser = argparse.ArgumentParser()
parser.add_argument('directory', nargs='?', default='assets/items/female_barbarian_boots/tripo_v1/fitted_v3')
parser.add_argument('--ring', choices=['middle', 'lower', 'front', 'front-side'], default='middle')
parser.add_argument('--panel', choices=[0, 1], type=int, default=0)
parser.add_argument('--side', choices=['right', 'left'], default='right')
parser.add_argument('--stride', type=int, default=1)
parser.add_argument('--reference-data', type=Path)
args = parser.parse_args()
directory = Path(args.directory)
prefix = 'clearance' if args.side == 'right' else 'clearance-left'
manifest = json.loads((directory / f'{prefix}-poses.json').read_text())
source_hash = hashlib.sha256((directory / 'boots_female_barbarian.glb').read_bytes()).hexdigest()
assert source_hash == manifest['source_sha256'], 'Regenerate poses for the current sandal'
fit = np.load(args.reference_data or directory / 'fit-data.npz')
faces = np.array(manifest['boot_faces']).reshape(-1, 3)
wall_key = {'middle': 'wall_{}_0', 'lower': 'lower_wall_{}', 'front': 'front_wall_{}', 'front-side': f'front_side_{{}}_{args.panel}'}[args.ring]
inner_faces, outer_faces = (faces[fit[wall_key.format(kind)]] for kind in ['inner', 'outer'])
body_count = len(manifest['body_indices'])
poses = np.fromfile(directory / f'{prefix}-poses.bin', dtype=np.float32).reshape(
    -1, body_count + manifest['boot_vertices'], 3)


def edges(triangles):
    return np.unique(np.sort(triangles[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)


def crossings(points, segments, mesh):
    origins = points[segments[:, 0]]
    delta = points[segments[:, 1]] - origins
    lengths = np.linalg.norm(delta, axis=1)
    valid = lengths > 1.8e-8
    origins, delta, lengths = origins[valid], delta[valid], lengths[valid]
    locations, rays, _ = mesh.ray.intersects_location(origins, delta / lengths[:, None])
    distance = np.linalg.norm(locations - origins[rays], axis=1)
    return int(((distance > 1.8e-7) & (distance < lengths[rays] - 1.8e-7)).sum())


inner_edges, outer_edges = edges(inner_faces), edges(outer_faces)
probe_vertices = np.unique(outer_faces)
probe_edges = outer_edges
if args.ring.startswith('front'):
    _, welded = np.unique(np.round(fit['source_right'] if args.side == 'right' and 'source_right' in fit else fit['source'], 6), axis=0, return_inverse=True)
    welded = welded.ravel()
    shared = np.isin(welded, np.unique(welded[inner_faces]))
    probe_vertices = probe_vertices[~shared[probe_vertices]]
    probe_edges = probe_edges[~shared[probe_edges].all(1)]
frames = []
minimum = {'distance': float('inf')}
for frame in range(0, len(poses), args.stride):
    points = poses[frame, body_count:]
    inner = trimesh.Trimesh(points, inner_faces, process=False)
    outer = trimesh.Trimesh(points, outer_faces, process=False)
    probes = np.vstack([points[probe_vertices], points[outer_faces].mean(1), points[probe_edges].mean(1)])
    _, distance, _ = trimesh.proximity.closest_point(inner, probes)
    depth = float(distance.min())
    hits = crossings(points, outer_edges, inner) + crossings(points, inner_edges, outer)
    frames.append({**manifest['poses'][frame], 'minimum_distance': depth, 'edge_surface_crossings': hits})
    if depth < minimum['distance']:
        minimum = {'distance': depth, **manifest['poses'][frame]}
    if frame % 61 == 0:
        print(json.dumps({'frame': frame, 'minimum': minimum, 'crossings': hits}), flush=True)

minimum_gap = .00009 if args.ring.startswith('front') else .00036
label = f'Front strap side {args.panel}' if args.ring == 'front-side' else 'Front toe strap' if args.ring == 'front' else f'{args.ring.capitalize()} ankle ring'
report = {'required_minimum_m': minimum_gap, 'source_sha256': source_hash, 'side': args.side, 'ring': args.ring, 'frame_count': len(frames), 'stride': args.stride,
          'minimum': minimum, 'frames_with_crossings': sum(
              entry['edge_surface_crossings'] > 0 for entry in frames), 'frames': frames,
          'scope': f'{label} outer-wall vertices, face centers and edge midpoints against its inner wall; '
                   'segment-to-surface intersection rays in both directions. Excludes other regions; front probes omit shared seam vertices/edges.'}
(directory / f'{f"front-strap-side-{args.panel}" if args.ring == "front-side" else "front-strap" if args.ring == "front" else "lower-ring" if args.ring == "lower" else "ring"}-wall-{args.side}-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ['frame_count', 'minimum', 'frames_with_crossings']}), flush=True)
if minimum['distance'] < minimum_gap or report['frames_with_crossings']:
    raise SystemExit(f'{label} walls overlap; see wall report')
