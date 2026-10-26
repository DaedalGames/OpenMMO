import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.mesh_components import welded_islands
from outfits.skinning import deform

DIRECTORY = ROOT / 'assets/items/female_rogue_skirt/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v5'
OUTPUT = DIRECTORY / 'fitted_v6'
OUTPUT.mkdir(exist_ok=True)

doc, raw = read_glb(SOURCE / 'bottom_female_rogue.glb')
raw = bytearray(raw)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, raw, attrs['POSITION']).astype(float)
faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
joints = accessor(doc, raw, attrs['JOINTS_0']).astype(int)
weights = accessor(doc, raw, attrs['WEIGHTS_0'])
target = primitive['targets'][0]
seated_delta = accessor(doc, raw, target['POSITION'])
seated = points+seated_delta
_, welded, labels = welded_islands(points, faces)
main = max(np.unique(labels), key=lambda label: (labels == label).sum())
parts = {'cloth': main}
for label in np.unique(labels):
    q = points[labels == label]
    center = q.mean(0)
    count = len(np.unique(welded[labels == label]))
    if center[2] < .04 or label == main:
        continue
    if abs(center[0]) < .04:
        name = {20: 'buckle_face', 32: 'buckle_backing', 96: 'buckle_frame',
                40: 'pin_right', 53: 'pin_left'}[count]
    elif count == 28:
        name = 'belt_tail'
    else:
        name = ('loop_' if count == 44 else 'rivet_')+('left' if center[0] > 0 else 'right')
    assert name not in parts
    parts[name] = int(label)
layers = [('belt_tail', ['cloth']),
          ('loop_left', ['cloth', 'belt_tail']), ('loop_right', ['cloth']),
          ('rivet_left', ['loop_left', 'belt_tail']), ('rivet_right', ['loop_right']),
          ('buckle_backing', ['cloth']), ('buckle_face', ['cloth', 'buckle_backing']),
          ('buckle_frame', ['cloth', 'buckle_backing', 'buckle_face']),
          ('pin_left', ['buckle_frame', 'buckle_face', 'buckle_backing']),
          ('pin_right', ['buckle_frame', 'buckle_face', 'buckle_backing'])]
assert len(parts) == 11
part_faces = {name: faces[(labels[faces] == label).all(1)] for name, label in parts.items()}
part_ids = {name: np.flatnonzero(labels == label) for name, label in parts.items()}
poses = json.loads((OUTPUT / 'all-poses.json').read_text())
assert poses['base_sha256'] == hashlib.sha256((ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb').read_bytes()).hexdigest()
assert poses['animations_sha256'] == hashlib.sha256((ROOT / 'assets/modular_human_female_01/preview/animations.json').read_bytes()).hexdigest()
snapshots = poses['samples']
rest = {'clip': 'rest', 'sample': 0, 'phase': 0, 'matrices': np.tile(np.eye(4).T.ravel(), (65, 1)).tolist()}
snapshots = [rest, *[s for s in snapshots if s['clip'] in ['idle1', 'idle_armed', 'walk', 'sit_idle']]]
states = {}
for seated_state in [False, True]:
    selected = [s for s in snapshots if (s['clip'] == 'sit_idle') == seated_state]
    samples = []
    for s in selected:
        matrices = np.array(s['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        linear = np.einsum('nk,nkij->nij', weights, matrices[joints])[:, :3, :3]
        samples.append((s, matrices, linear))
    states[seated_state] = samples

barycentric = np.array([(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3),
                        (.5, .5, 0), (.5, 0, .5), (0, .5, .5)])
queries = {}
for name, _ in layers:
    triangles = part_faces[name]
    normal = np.cross(points[triangles[:, 1]]-points[triangles[:, 0]], points[triangles[:, 2]]-points[triangles[:, 0]])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
    queries[name] = triangles[normal[:, 2] > .2]


def gaps(posed, linear, name, underneath):
    triangles = queries[name]
    axes = linear[:, :, 2]
    surface = BVHTree.FromPolygons([Vector(p) for p in posed],
                                  np.concatenate([part_faces[n] for n in underneath]).tolist())
    for bary in barycentric:
        positions = np.einsum('fkj,k->fj', posed[triangles], bary)
        directions = np.einsum('fkj,k->fj', axes[triangles], bary)
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        for p, axis in zip(positions, directions):
            hit, _, _, distance = surface.ray_cast(Vector(p+axis*.08), Vector(-axis), .16)
            if hit is not None:
                yield distance-.08


gap_target = .0015
offsets = {}
metrics = {}
for sitting, samples in states.items():
    original = seated if sitting else points
    offset = np.zeros_like(points)
    fit_samples = [entry for entry in samples if entry[0]['sample'] % 4 == 0 or entry[0]['sample'] == 32]
    for name, underneath in layers:
        for iteration in range(5):
            minimum = 1.
            for _, matrices, linear in fit_samples:
                posed = deform(original+offset, joints, weights, matrices)
                minimum = min(minimum, min(gaps(posed, linear, name, underneath), default=1.))
            if minimum >= gap_target-.00005:
                break
            offset[part_ids[name], 2] += gap_target-minimum+.0001
        assert np.max(offset[part_ids[name], 2]) < .025, (name, sitting)
    before, after = {}, {}
    for name, underneath in layers:
        for destination, shift in [(before, 0), (after, offset)]:
            minimum, close, count = 1., 0, 0
            for _, matrices, linear in samples:
                posed = deform(original+shift, joints, weights, matrices)
                for gap in gaps(posed, linear, name, underneath):
                    minimum = min(minimum, gap)
                    close += int(gap < .001)
                    count += 1
            destination[name] = {'minimum_gap_m': minimum if count else None, 'below_1mm': close, 'samples': count}
        if after[name]['samples']:
            assert after[name]['minimum_gap_m'] > .001, (name, sitting, after[name])
        else:
            assert sitting and before[name]['samples'] == 0, (name, sitting, before[name])
    state = 'seated' if sitting else 'other_poses'
    metrics[state] = {'frames': len(samples), 'before': before, 'after': after}
    offsets[sitting] = offset
    print(json.dumps({'state': state, 'offsets_m': {n: float(offset[ids, 2].max()) for n, ids in part_ids.items()}}), flush=True)

changed = offsets[False].any(1) | offsets[True].any(1)
assert not changed[labels == main].any()
assert not changed[points[:, 2] < 0].any()
new_points = points+offsets[False]
attrs['POSITION'] = add_accessor(doc, raw, new_points, 'VEC3')
seated_delta[changed] += (offsets[True]-offsets[False])[changed]
target['POSITION'] = add_accessor(doc, raw, seated_delta, 'VEC3')
doc['buffers'][0]['byteLength'] = len(raw)
output = OUTPUT / 'bottom_female_rogue.glb'
write_glb(output, doc, raw)
mask = json.loads((SOURCE / 'body-occlusion.json').read_text())
mask['skirt_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
(OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2)+'\n')
report = {'revision': 'v6', 'date': '2026-10-26', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256((SOURCE / 'bottom_female_rogue.glb').read_bytes()).hexdigest(),
          'body_sha256': poses['base_sha256'], 'animations_sha256': poses['animations_sha256'],
          'triangles': len(faces), 'changed_vertices': int(changed.sum()),
          'maximum_base_offset_m': float(offsets[False].max()), 'maximum_seated_offset_m': float(offsets[True].max()),
          'layer_target_gap_m': gap_target, 'layer_clearance': metrics,
          'scope': 'Seven samples per outward-facing decoration triangle, ray-tested against underlying layers in rest, idle1, idle_armed, walk and sit_idle. Sitting fitted independently.',
          'cloth_and_rear_geometry_and_seated_positions_preserved': True,
          'skin_weights_uv_textures_and_mask_indices_preserved': True, 'no_new_api_requests': True}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'female-rogue-skirt.blend'))
old = bpy.data.objects['bottom_female_rogue']
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(output), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects)-before
new = next(o for o in imported if o.type == 'MESH')
action = old.data.shape_keys.animation_data.action
old.data = new.data
old.data.shape_keys.animation_data_create()
old.data.shape_keys.animation_data.action = action
for obj in imported:
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-rogue-skirt.blend'))
