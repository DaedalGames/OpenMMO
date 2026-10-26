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

DIRECTORY = ROOT / 'assets/items/female_rogue_top/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v5'
OUTPUT = DIRECTORY / 'fitted_v6'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'


def smooth(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


doc, raw = read_glb(SOURCE / 'top_female_rogue.glb')
raw = bytearray(raw)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, raw, attrs['POSITION']).astype(float)
faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
joints = accessor(doc, raw, attrs['JOINTS_0']).astype(int)
weights = accessor(doc, raw, attrs['WEIGHTS_0'])
first, welded, _ = welded_islands(points, faces)
neighbors = [set() for _ in first]
for face in welded[faces]:
    for a, b in zip(face, np.roll(face, 1)):
        if a != b:
            neighbors[a].add(int(b))
            neighbors[b].add(int(a))

base, binary = read_glb(BODY)
body = base['meshes'][0]['primitives'][0]
ba = body['attributes']
bp = accessor(base, binary, ba['POSITION'])
bf = accessor(base, binary, body['indices']).reshape(-1, 3)
bj = accessor(base, binary, ba['JOINTS_0']).astype(int)
bw = accessor(base, binary, ba['WEIGHTS_0'])
_, _, labels = welded_islands(bp, bf)
skin_labels = labels == np.bincount(labels).argmax()
skin = skin_labels & (bp[:, 0] < -.14) & (bp[:, 1] > 1.04)
arm_faces = bf[skin[bf].all(1)]
skin_faces = bf[skin_labels[bf].all(1)]
names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
arm = [names.index(name) for name in ['RightArm', 'RightForeArm']]
arm_weight = (weights*np.isin(joints, arm)).sum(1)
falloff = smooth((-points[:, 0]-.15)/.065)*smooth((points[:, 1]-1.12)/.05)*(1-smooth((points[:, 1]-1.43)/.06))*smooth((arm_weight-.4)/.4)
affected = falloff > 0
queries = faces[affected[faces].any(1)]
surface = BVHTree.FromPolygons([Vector(p) for p in bp], arm_faces.tolist())
delta = np.zeros_like(points)
for i in np.flatnonzero(affected):
    hit, _, _, distance = surface.find_nearest(Vector(points[i]))
    if distance > .010:
        direction = points[i]-np.array(hit)
        delta[i] = -direction*(1-.010/distance)*falloff[i]
unique = delta[first]
for _ in range(4):
    updated = unique.copy()
    for i in np.flatnonzero(affected[first]):
        adjacent = list(neighbors[i])
        if adjacent:
            updated[i] = .85*unique[i]+.15*unique[adjacent].mean(0)
    unique = updated
delta = unique[welded]
unique = (points+delta)[first]
for _ in range(4):
    updated = unique.copy()
    for i in np.flatnonzero(affected[first]):
        adjacent = list(neighbors[i])
        if adjacent:
            updated[i] += .20*falloff[first[i]]*(unique[adjacent].mean(0)-unique[i])
    unique = updated
delta = unique[welded]-points

poses = json.loads((OUTPUT / 'idle1-poses.json').read_text())
assert poses['base_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
frames = []
for sample in [None, *poses['samples']]:
    matrices = np.tile(np.eye(4), (65, 1, 1)) if sample is None else np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    posed_body = deform(bp, bj, bw, matrices)
    blended = np.einsum('nk,nkij->nij', weights, matrices[joints])
    frames.append((BVHTree.FromPolygons([Vector(p) for p in posed_body], skin_faces.tolist()),
                   blended[:, :3, :3], blended[:, :3, 3], np.linalg.inv(blended[:, :3, :3])))
fit_frames = [frames[i] for i in np.linspace(0, len(frames)-1, 10).astype(int)]
barycentric = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3), (.5, .5, 0), (.5, 0, .5), (0, .5, .5)]
sample_faces = [(bary, queries[np.einsum('fk,k->f', affected[queries], bary) > 0]) for bary in barycentric]
for _ in range(30):
    correction = np.zeros((len(first), 3))
    counts = np.zeros(len(first))
    deficit = 0
    for surface, linear, translation, inverse in fit_frames:
        posed = np.einsum('nij,nj->ni', linear, points+delta)+translation
        for bary, triangles in sample_faces:
            for face, p in zip(triangles, np.einsum('fkj,k->fj', posed[triangles], bary)):
                hit, normal, _, _ = surface.find_nearest(Vector(p))
                gap = np.dot(p-np.array(hit), normal)
                if gap >= .005:
                    continue
                deficit = max(deficit, .005-gap)
                for i in set(welded[face[affected[face]]]):
                    correction[i] += inverse[first[i]] @ (np.array(normal)*(.005-gap))
                    counts[i] += 1
    delta += (1.2*correction/np.maximum(counts[:, None], 1))[welded]
    if deficit < .0002:
        break

metrics = {}
for name, offset in [('before', 0), ('after', delta)]:
    gaps, distances = [], []
    for surface, linear, translation, _ in frames:
        posed = np.einsum('nij,nj->ni', linear, points+offset)+translation
        for bary, triangles in sample_faces:
            for p in np.einsum('fkj,k->fj', posed[triangles], bary):
                hit, normal, _, distance = surface.find_nearest(Vector(p))
                gaps.append(float(np.dot(p-np.array(hit), normal)))
                distances.append(distance)
    metrics[name] = {'minimum_signed_gap_m': min(gaps), 'maximum_distance_m': max(distances),
                     'deeper_than_1mm': sum(g < -.001 for g in gaps), 'samples': len(gaps)}
assert metrics['after']['minimum_signed_gap_m'] > .0001, metrics
assert metrics['after']['deeper_than_1mm'] == 0
changed = np.linalg.norm(delta, axis=1) > 1e-9
assert not changed[points[:, 0] >= -.15].any()
assert not accessor(doc, raw, primitive['targets'][0]['POSITION'])[changed].any()
result = points+delta
normal_sum = np.zeros((len(first), 3))
face_normal = np.cross(result[faces[:, 1]]-result[faces[:, 0]], result[faces[:, 2]]-result[faces[:, 0]])
for k in range(3):
    np.add.at(normal_sum, welded[faces[:, k]], face_normal)
normal_sum /= np.maximum(np.linalg.norm(normal_sum, axis=1, keepdims=True), 1e-12)
normal_changed = np.zeros(len(first), dtype=bool)
normal_changed[welded[faces[changed[faces].any(1)]]] = True
normal_changed = normal_changed[welded]
normals = accessor(doc, raw, attrs['NORMAL'])
normals[normal_changed] = normal_sum[welded[normal_changed]]
attrs['POSITION'] = add_accessor(doc, raw, result, 'VEC3')
attrs['NORMAL'] = add_accessor(doc, raw, normals, 'VEC3')
if 'TANGENT' in attrs:
    tangent = accessor(doc, raw, attrs['TANGENT'])
    adjusted = tangent[:, :3]-normals*np.einsum('ij,ij->i', tangent[:, :3], normals)[:, None]
    adjusted /= np.maximum(np.linalg.norm(adjusted, axis=1, keepdims=True), 1e-12)
    tangent[normal_changed, :3] = adjusted[normal_changed]
    attrs['TANGENT'] = add_accessor(doc, raw, tangent, 'VEC4')
doc['buffers'][0]['byteLength'] = len(raw)
target = OUTPUT / 'top_female_rogue.glb'
write_glb(target, doc, raw)
mask = json.loads((SOURCE / 'body-occlusion.json').read_text())
mask['top_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
(OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2)+'\n')
report = {'revision': 'v6', 'date': '2026-10-26', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256((SOURCE / 'top_female_rogue.glb').read_bytes()).hexdigest(),
          'body_sha256': poses['base_sha256'], 'animations_sha256': poses['animations_sha256'],
          'changed_vertices': int(changed.sum()), 'maximum_offset_m': float(np.linalg.norm(delta, axis=1).max()),
          'triangles': len(faces), 'idle_validation_frames': len(frames)-1, 'right_sleeve_clearance': metrics,
          'scope': 'Right sleeve fit in bind pose and idle1. Moving vertices and barycentric samples on affected and boundary triangles against full body skin; stationary boundary samples excluded.',
          'left_sleeve_and_corset_preserved': True, 'skin_weights_and_seated_morph_preserved': True,
          'uv_textures_and_body_mask_indices_preserved': True, 'no_new_api_requests': True}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'female-rogue-top.blend'))
old = next(o for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys and 'pose_sit_idle' in o.data.shape_keys.key_blocks)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(target), bone_heuristic='TEMPERANCE')
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
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-rogue-top.blend'))
