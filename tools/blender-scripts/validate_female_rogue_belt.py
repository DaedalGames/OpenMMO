import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor
from outfits.mesh_components import welded_islands
from outfits.skinning import deform

DIRECTORY = ROOT / 'assets/items/female_rogue_skirt/tripo_v1/fitted_v4'
SKIRT = DIRECTORY / 'bottom_female_rogue.glb'
doc, raw = read_glb(SKIRT)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, raw, attrs['POSITION'])
faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
joints = accessor(doc, raw, attrs['JOINTS_0']).astype(int)
weights = accessor(doc, raw, attrs['WEIGHTS_0'])
_, welded, labels = welded_islands(points, faces)
main = max(np.unique(labels), key=lambda label: len(np.unique(welded[labels == label])))
cloth_faces = faces[(labels[faces] == main).all(1)]
loops = {}
for label in np.unique(labels):
    chosen = labels == label
    q = points[chosen]
    if len(np.unique(welded[chosen])) == 44 and q[:, 2].mean() > .04 and np.ptp(q[:, 1]) > .025:
        loops['left' if q[:, 0].mean() > 0 else 'right'] = np.flatnonzero(chosen)
    if len(np.unique(welded[chosen])) == 96 and abs(q[:, 0].mean()) < .04 and q[:, 2].mean() > .04:
        loops['buckle'] = np.flatnonzero(chosen)
assert len(loops) == 3
body, body_raw = read_glb(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
body_primitive = body['meshes'][0]['primitives'][0]
ba = body_primitive['attributes']
bp = accessor(body, body_raw, ba['POSITION'])
bf = accessor(body, body_raw, body_primitive['indices']).reshape(-1, 3)
bj = accessor(body, body_raw, ba['JOINTS_0']).astype(int)
bw = accessor(body, body_raw, ba['WEIGHTS_0'])
_, _, body_labels = welded_islands(bp, bf)
panty_faces = []
for label in np.unique(body_labels):
    q = bp[body_labels == label]
    if len(q) > 100 and q[:, 1].min() > .85 and q[:, 1].max() < 1.15:
        panty_faces.extend(bf[(body_labels[bf] == label).all(1)].tolist())
back = (labels == main) & (points[:, 1] > .99) & (points[:, 1] < 1.075) & (points[:, 2] < -.06) & (np.abs(points[:, 0]) < .09)
directions = np.column_stack([points[:, 0], np.zeros(len(points)), points[:, 2]+.015])
directions /= np.maximum(np.linalg.norm(directions, axis=1, keepdims=True), 1e-12)
samples = json.loads((DIRECTORY / 'animation-samples.json').read_text())
samples.insert(0, {'clip': 'rest', 'matrices': np.tile(np.eye(4).T.ravel(), (65, 1)).tolist()})
report = {}
underwear_report = {}
for sample in samples:
    matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    posed = deform(points, joints, weights, matrices)
    blended = np.einsum('nk,nkij->nij', weights, matrices[joints])
    posed_directions = np.einsum('nij,nj->ni', blended[:, :3, :3], directions)
    posed_directions /= np.maximum(np.linalg.norm(posed_directions, axis=1, keepdims=True), 1e-12)
    surface = BVHTree.FromPolygons([Vector(p) for p in posed], cloth_faces.tolist())
    result = report.setdefault(sample['clip'], {})
    for name, indices in loops.items():
        part_faces = faces[(labels[faces] == labels[indices[0]]).all(1)]
        queries = np.concatenate([posed[indices], posed[part_faces].mean(1)])
        axes = np.concatenate([posed_directions[indices], posed_directions[part_faces].mean(1)])
        normals = np.cross(posed[part_faces[:, 1]]-posed[part_faces[:, 0]], posed[part_faces[:, 2]]-posed[part_faces[:, 0]])
        face_axes = axes[len(indices):]
        exposed = np.einsum('ij,ij->i', normals, face_axes) > .15*np.linalg.norm(normals, axis=1)
        exposed_queries = np.concatenate([np.zeros(len(indices), dtype=bool), exposed])
        metrics = result.setdefault(name, {'minimum_gap_m': 1., 'maximum_gap_m': -1., 'buried_samples': 0,
                                          'exposed_minimum_gap_m': 1., 'exposed_buried_samples': 0, 'exposed_samples': 0, 'ray_misses': 0})
        for p, axis, outer in zip(queries, axes, exposed_queries):
            axis /= np.linalg.norm(axis)
            hit, _, _, distance = surface.ray_cast(Vector(p+axis*.06), Vector(-axis), .12)
            if hit is None:
                metrics['ray_misses'] += 1
                continue
            gap = distance-.06
            metrics['minimum_gap_m'] = min(metrics['minimum_gap_m'], gap)
            metrics['maximum_gap_m'] = max(metrics['maximum_gap_m'], gap)
            metrics['buried_samples'] += int(gap < -.001)
            if outer:
                metrics['exposed_samples'] += 1
                metrics['exposed_minimum_gap_m'] = min(metrics['exposed_minimum_gap_m'], gap)
                metrics['exposed_buried_samples'] += int(gap < -.001)
    if sample['clip'] in ['rest', 'idle1', 'walk']:
        body_points = deform(bp, bj, bw, matrices)
        panties = BVHTree.FromPolygons([Vector(p) for p in body_points], panty_faces)
        metrics = underwear_report.setdefault(sample['clip'], {'minimum_gap_m': 1., 'piercing_samples': 0, 'ray_misses': 0})
        back_faces = cloth_faces[back[cloth_faces].all(1)]
        queries = np.concatenate([posed[back], posed[back_faces].mean(1)])
        axes = np.concatenate([posed_directions[back], posed_directions[back_faces].mean(1)])
        for p, axis in zip(queries, axes):
            axis /= np.linalg.norm(axis)
            hit, _, _, distance = panties.ray_cast(Vector(p+axis*.05), Vector(-axis), .1)
            if hit is None:
                metrics['ray_misses'] += 1
                continue
            gap = distance-.05
            metrics['minimum_gap_m'] = min(metrics['minimum_gap_m'], gap)
            metrics['piercing_samples'] += int(gap < -.001)
output = {'skirt_sha256': hashlib.sha256(SKIRT.read_bytes()).hexdigest(),
          'scope': 'Outermost skirt ray clearance at both front loops and buckle, rest plus 33 frames per clip. Exposed face centroids check visible burial; all vertices and centroids check backing overlap and floating. Backing overlap is limited to 3mm. Rear waistband rays also check lower underwear during rest, idle and walk.',
          'maximum_gap_limits_m': {'left': .006, 'right': .006, 'buckle': .007},
          'clips': report, 'rear_underwear': underwear_report}
(DIRECTORY / 'belt-validation.json').write_text(json.dumps(output, indent=2)+'\n')
print(json.dumps(output), flush=True)
assert all(report[clip][side]['exposed_buried_samples'] == 0 for clip in ['rest', 'idle1', 'walk'] for side in loops)
assert all(report[clip][side]['minimum_gap_m'] > -.003 for clip in ['rest', 'idle1', 'walk'] for side in loops)
assert all(report[clip][side]['exposed_samples'] > 0 for clip in ['rest', 'idle1', 'walk'] for side in loops)
assert all(report[clip][side]['maximum_gap_m'] < output['maximum_gap_limits_m'][side] for clip in ['rest', 'idle1', 'walk'] for side in loops)
assert all(metrics['piercing_samples'] == 0 for metrics in underwear_report.values())
