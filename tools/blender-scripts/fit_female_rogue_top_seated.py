import hashlib
import json
import sys
from pathlib import Path

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
SOURCE = DIRECTORY / 'fitted_v4/top_female_rogue.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v5'


def smooth(value):
    t = np.clip(value, 0, 1)
    return t*t*(3-2*t)


doc, binary = read_glb(SOURCE)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
joints = accessor(doc, binary, attrs['JOINTS_0']).astype(int)
weights = accessor(doc, binary, attrs['WEIGHTS_0'])
first, welded, labels = welded_islands(points, faces)
main = max(np.unique(labels), key=lambda label: len(np.unique(welded[labels == label])))
lower = labels == main
for label in np.unique(labels):
    if points[labels == label, 1].max() < 1.27:
        lower |= labels == label
falloff = (1-smooth((points[:, 1]-1.20)/.08))*(1-smooth((np.abs(points[:, 0])-.18)/.03))*lower
affected = falloff > 0
queries = faces[affected[faces].all(1)]
placket = (np.abs(points[:, 0]-.013) < .025) & (points[:, 2] > .08)
neighbors = [set() for _ in first]
for face in welded[faces]:
    for a, b in zip(face, np.roll(face, 1)):
        if a != b:
            neighbors[a].add(int(b))
            neighbors[b].add(int(a))

base, raw = read_glb(BODY)
body_primitive = base['meshes'][0]['primitives'][0]
ba = body_primitive['attributes']
bp = accessor(base, raw, ba['POSITION'])
bf = accessor(base, raw, body_primitive['indices']).reshape(-1, 3)
bj = accessor(base, raw, ba['JOINTS_0']).astype(int)
bw = accessor(base, raw, ba['WEIGHTS_0'])
_, _, body_labels = welded_islands(bp, bf)
skin = np.bincount(body_labels).argmax()
torso = (body_labels == skin) & (bp[:, 1] > 1.015) & (bp[:, 1] < 1.48) & (np.abs(bp[:, 0]) < .20)
skin_faces = bf[torso[bf].all(1)]
poses = json.loads((OUTPUT / 'sit-poses.json').read_text())
assert poses['base_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
frames = []
for sample in poses['samples']:
    matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    body = deform(bp, bj, bw, matrices)
    blended = np.einsum('nk,nkij->nij', weights, matrices[joints])
    frames.append((BVHTree.FromPolygons([Vector(p) for p in body], skin_faces.tolist()),
                   blended[:, :3, :3], blended[:, :3, 3], np.linalg.inv(blended[:, :3, :3])))
fit_frames = [frames[i] for i in np.linspace(0, len(frames)-1, 9).astype(int)]
delta = np.zeros_like(points)
barycentric = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3),
               (.5, .5, 0), (.5, 0, .5), (0, .5, .5)]
for iteration in range(36):
    correction, count = np.zeros((len(first), 3)), np.zeros(len(first))
    maximum = 0
    for surface, linear, translation, inverse in fit_frames:
        posed = np.einsum('nij,nj->ni', linear, points+delta)+translation
        for bary in barycentric:
            for face, p in zip(queries, np.einsum('fkj,k->fj', posed[queries], bary)):
                hit, normal, _, _ = surface.find_nearest(Vector(p))
                signed = np.dot(p-np.array(hit), normal)
                if signed >= .006:
                    continue
                error = min(.006-signed, .015)
                maximum = max(maximum, .006-signed)
                for i in set(welded[face[affected[face]]]):
                    vertex = first[i]
                    change = inverse[vertex] @ (np.array(normal)*error)
                    if placket[vertex]:
                        change[0] = 0
                    correction[i] += change*falloff[vertex]
                    count[i] += 1
    unique = delta[first]+1.1*correction/np.maximum(count[:, None], 1)
    updated = unique.copy()
    for i in np.flatnonzero(affected[first]):
        adjacent = list(neighbors[i])
        if adjacent:
            updated[i] += .08*falloff[first[i]]*(unique[adjacent].mean(0)-unique[i])
        if placket[first[i]]:
            updated[i, 0] = 0
    updated[~affected[first]] = 0
    delta = updated[welded]
    print(json.dumps({'iteration': iteration+1, 'maximum_clearance_deficit_m': maximum,
                      'maximum_offset_m': float(np.linalg.norm(delta, axis=1).max())}), flush=True)
    if maximum < .0005:
        break

cloth_faces = faces[(labels[faces] == main).all(1)]
cloth = BVHTree.FromPolygons([Vector(p) for p in points], cloth_faces.tolist())
for label in np.unique(labels):
    selected = labels == label
    if label == main or not lower[selected].all() or points[selected, 2].mean() < .06:
        continue
    ids = np.flatnonzero(selected)
    following = []
    for i in ids:
        hit, _, face, _ = cloth.find_nearest(Vector(points[i]))
        indices = cloth_faces[face]
        a, b, c = points[indices]
        uv = np.linalg.lstsq(np.column_stack((b-a, c-a)), np.array(hit)-a, rcond=None)[0]
        bary = np.clip([1-uv.sum(), *uv], 0, 1)
        bary /= bary.sum()
        following.append(points[i]+bary @ delta[indices])
    following = np.array(following)
    source_center, target_center = points[ids].mean(0), following.mean(0)
    u, _, vt = np.linalg.svd((points[ids]-source_center).T @ (following-target_center))
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    delta[ids] = (points[ids]-source_center) @ rotation+target_center-points[ids]
    for _ in range(8):
        changes = []
        for _, linear, translation, inverse in fit_frames:
            posed = np.einsum('nij,nj->ni', linear, points+delta)+translation
            surface = BVHTree.FromPolygons([Vector(p) for p in posed], cloth_faces.tolist())
            for i in ids:
                hit, normal, _, _ = surface.find_nearest(Vector(posed[i]))
                gap = np.dot(posed[i]-np.array(hit), normal)
                if gap < .0015:
                    changes.append(inverse[i] @ (np.array(normal)*(.0015-gap)))
        if not changes:
            break
        delta[ids] += max(changes, key=np.linalg.norm)

metrics = {'before': {'minimum_m': 1., 'deeper_than_1mm': 0},
           'after': {'minimum_m': 1., 'deeper_than_1mm': 0}}
for surface, linear, translation, _ in frames:
    for name, shift in [('before', 0), ('after', delta)]:
        posed = np.einsum('nij,nj->ni', linear, points+shift)+translation
        for positions in [posed[affected], posed[queries].mean(1)]:
            for p in positions:
                hit, normal, _, _ = surface.find_nearest(Vector(p))
                signed = float(np.dot(p-np.array(hit), normal))
                metrics[name]['minimum_m'] = min(metrics[name]['minimum_m'], signed)
                metrics[name]['deeper_than_1mm'] += int(signed < -.001)

assert metrics['after']['deeper_than_1mm'] == 0
assert metrics['after']['minimum_m'] > .003
morphed = points+delta
normal_sum = np.zeros((len(first), 3))
normals = np.cross(morphed[faces[:, 1]]-morphed[faces[:, 0]], morphed[faces[:, 2]]-morphed[faces[:, 0]])
for k in range(3):
    np.add.at(normal_sum, welded[faces[:, k]], normals)
normal_sum /= np.maximum(np.linalg.norm(normal_sum, axis=1, keepdims=True), 1e-12)
old_normal = accessor(doc, binary, attrs['NORMAL'])
changed = np.linalg.norm(delta, axis=1) > 1e-9
new_normal = old_normal.copy()
new_normal[changed] = normal_sum[welded[changed]]
target = {'POSITION': add_accessor(doc, binary, delta, 'VEC3'),
          'NORMAL': add_accessor(doc, binary, new_normal-old_normal, 'VEC3')}
if 'TANGENT' in attrs:
    old_tangent = accessor(doc, binary, attrs['TANGENT'])[:, :3]
    tangent = old_tangent-new_normal*np.einsum('ij,ij->i', old_tangent, new_normal)[:, None]
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-12)
    tangent[~changed] = old_tangent[~changed]
    target['TANGENT'] = add_accessor(doc, binary, tangent-old_tangent, 'VEC3')
primitive['targets'] = [target]
mesh = doc['meshes'][0]
mesh['weights'] = [0]
mesh.setdefault('extras', {})['targetNames'] = ['pose_sit_idle']
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT / 'top_female_rogue.glb', doc, binary)
report = {'revision': 'v5', 'date': '2026-10-26', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body_sha256': poses['base_sha256'], 'animations_sha256': poses['animations_sha256'],
          'triangles': len(faces), 'morph': 'pose_sit_idle', 'default_weight': 0,
          'changed_vertices': int(changed.sum()), 'fit_frames': len(fit_frames), 'validation_frames': len(frames),
          'maximum_offset_m': float(np.linalg.norm(delta, axis=1).max()),
          'seated_clearance': metrics,
          'clearance_scope': 'Lower corset vertices and complete lower faces against torso skin; upper straps, sleeves, and self-overlapping arms excluded.',
          'lower_front_accessories_follow_cloth_rigidly': True,
          'base_geometry_and_skinning_preserved': True,
          'original_uv_and_textures_preserved': True, 'no_new_api_requests': True}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
