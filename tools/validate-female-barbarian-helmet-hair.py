import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from lib.glb import read_glb
from lib.glb_accessors import accessor

DIRECTORY = Path('assets/items/female_barbarian_helmet/tripo_v2/fitted_v1')
doc, raw = read_glb(DIRECTORY / 'helmet_female_barbarian.glb')
primitive = doc['meshes'][0]['primitives'][0]
points = accessor(doc, raw, primitive['attributes']['POSITION'])
faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
shell = trimesh.Trimesh(points, faces, process=False)
shell_edges = np.unique(np.sort(faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)


def crossings(points, edges, surface):
    origin = points[edges[:, 0]]
    vector = points[edges[:, 1]] - origin
    length = np.linalg.norm(vector, axis=1)
    valid = length > 1.8e-8
    origin, vector, length = origin[valid], vector[valid], length[valid]
    hit, rays, _ = surface.ray.intersects_location(origin, vector / length[:, None])
    distance = np.linalg.norm(hit - origin[rays], axis=1)
    return int(((distance > 1.8e-7) & (distance < length[rays] - 1.8e-7)).sum())


report = {'helmet_sha256': hashlib.sha256((DIRECTORY / 'helmet_female_barbarian.glb').read_bytes()).hexdigest(),
          'scope': 'Actual runtime binding, rest plus 17 samples per preview clip. '
          'In canonical Head space, test hair edges against helmet surfaces and helmet edges against hair surfaces. '
          'Measure hair vertices, face centers and edge midpoints against helmet triangles. '
          'Reuse rigid Head-space geometry within 3.6e-6 m; exclude probes outside the helmet box '
          'expanded by 0.009 m, which provides a distance lower bound.', 'hair': {}}
for name in ['bob', 'knight']:
    manifest = json.loads((DIRECTORY / f'hair-{name}-poses.json').read_text())
    assert manifest['helmet_sha256'] == report['helmet_sha256']
    assert manifest['hair_sha256'] == hashlib.sha256((DIRECTORY / f'hair_{name}_barbarian_helmet.glb').read_bytes()).hexdigest()
    count = sum(mesh['vertices'] for mesh in manifest['meshes'])
    frames = np.fromfile(DIRECTORY / f'hair-{name}-poses.bin', dtype=np.float32).reshape(-1, count, 3)
    offset, parts = 0, []
    for mesh in manifest['meshes']:
        part_faces = np.array(mesh['faces']).reshape(-1, 3) + offset
        part_edges = np.unique(np.sort(part_faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)
        parts.append((part_faces, part_edges))
        offset += mesh['vertices']
    minimum = float('inf')
    records = []
    rigid_cache = {}
    for index, vertices in enumerate(frames):
        hits, gap = 0, float('inf')
        for part_index, (part_faces, part_edges) in enumerate(parts):
            ids = np.unique(part_faces)
            drift = np.linalg.norm(vertices[ids] - frames[0, ids], axis=1).max()
            if part_index in rigid_cache and drift < 3.6e-6:
                cached_hits, cached_gap = rigid_cache[part_index]
                hits += cached_hits
                gap = min(gap, cached_gap - float(drift))
                continue
            hair = trimesh.Trimesh(vertices, part_faces, process=False)
            probes = np.vstack([vertices[ids], vertices[part_faces].mean(1), vertices[part_edges].mean(1)])
            candidates = probes[((probes >= shell.bounds[0] - .009) & (probes <= shell.bounds[1] + .009)).all(1)]
            part_gap = .009
            if len(candidates):
                _, distance, _ = trimesh.proximity.closest_point(shell, candidates)
                part_gap = min(part_gap, float(distance.min()))
            part_hits = crossings(vertices, part_edges, shell) + crossings(points, shell_edges, hair)
            gap = min(gap, part_gap)
            hits += part_hits
            if index == 0:
                rigid_cache[part_index] = (part_hits, part_gap)
        minimum = min(minimum, gap)
        records.append({**manifest['frames'][index], 'minimum_distance': gap, 'crossings': hits})
    report['hair'][name] = {'hair_sha256': manifest['hair_sha256'], 'frame_count': len(records),
                            'minimum_distance': minimum, 'maximum_rigid_error': manifest['maximum_rigid_error'],
                            'frames_with_crossings': sum(frame['crossings'] > 0 for frame in records), 'frames': records}
    print(name, len(records), minimum, report['hair'][name]['frames_with_crossings'], flush=True)
(DIRECTORY / 'hair-animation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert all(value['minimum_distance'] > .00036 and value['frames_with_crossings'] == 0 for value in report['hair'].values())
