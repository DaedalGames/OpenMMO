import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

parser = argparse.ArgumentParser()
parser.add_argument('directory', nargs='?', default='assets/items/female_barbarian_boots/tripo_v1/fitted_v3')
parser.add_argument('--reference-data', type=Path)
parser.add_argument('--stride', type=int, default=1)
args = parser.parse_args()
directory = Path(args.directory)
manifest = json.loads((directory / 'clearance-poses.json').read_text())
sha = hashlib.sha256((directory / 'boots_female_barbarian.glb').read_bytes()).hexdigest()
assert sha == manifest['source_sha256'], 'Regenerate current right-foot poses'
fit = np.load(args.reference_data or directory / 'fit-data.npz')
face_ids = fit['right_panel_faces']
faces = np.array(manifest['boot_faces']).reshape(-1, 3)[face_ids]
body_count = len(manifest['body_indices'])
poses = np.fromfile(directory / 'clearance-poses.bin', dtype=np.float32).reshape(
    -1, body_count + manifest['boot_vertices'], 3)
frames = []
for frame in range(0, len(poses), args.stride):
    points = poses[frame, body_count:]
    panel = points[np.unique(faces)].astype(float)
    center = panel.mean(0)
    _, axes = np.linalg.eigh((panel - center).T @ (panel - center))
    local = (points.astype(float) - center) @ axes[:, [2, 1, 0]]
    triangles = local[faces]
    polygons = [Polygon(triangle[:, :2]) for triangle in triangles]
    near, crossing = [], []
    for a in range(len(faces)):
        for b in range(a):
            overlap = polygons[a].intersection(polygons[b])
            if overlap.area < 1e-11:
                continue
            if overlap.geom_type != 'Polygon':
                raise ValueError('Unexpected panel intersection geometry')
            xy = np.array(overlap.exterior.coords)[:-1]
            heights = []
            for index in [a, b]:
                triangle = triangles[index]
                matrix = (triangle[1:, :2] - triangle[0, :2]).T
                uv = np.linalg.solve(matrix, (xy - triangle[0, :2]).T).T
                heights.append(triangle[0, 2] + uv @ (triangle[1:, 2] - triangle[0, 2]))
            gap = heights[0] - heights[1]
            pair = [int(face_ids[a]), int(face_ids[b])]
            if np.abs(gap).max() < .00005:
                near.append(pair)
            if gap.min() < -1e-7 and gap.max() > 1e-7:
                crossing.append(pair)
    frames.append({**manifest['poses'][frame], 'near_coplanar_pairs': near, 'crossing_pairs': crossing})
report = {'source_sha256': sha, 'mesh': 'boots_female_barbarian_right', 'frame_count': len(frames),
          'stride': args.stride, 'panel_faces': face_ids.tolist(),
          'frames_with_near_coplanar_overlap': sum(bool(f['near_coplanar_pairs']) for f in frames),
          'frames_with_crossings': sum(bool(f['crossing_pairs']) for f in frames), 'frames': frames,
          'scope': 'Right marked outer panel, including outer/outer overlap. Intersect triangle projections in a fitted '
                   'panel frame; compare exact affine depth over the overlap polygon. Shared edges alone are excluded '
                   'by the positive-area threshold. Near-coplanar threshold 0.09 mm; overlap area 1e-11 source units squared.'}
(directory / 'right-panel-self-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['frame_count', 'frames_with_near_coplanar_overlap', 'frames_with_crossings']}))
if report['frames_with_near_coplanar_overlap'] or report['frames_with_crossings']:
    raise SystemExit('Right outer panel overlaps itself')
