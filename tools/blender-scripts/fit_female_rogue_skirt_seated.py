import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.mesh_components import welded_islands
from outfits.skinning import deform

DIRECTORY = ROOT / 'assets/items/female_rogue_skirt/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v4/bottom_female_rogue.glb'
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
cloth_vertices = labels == main
cloth_faces = faces[cloth_vertices[faces].all(1)]
front = smooth((points[:, 2]+.005)/.045)
rear = smooth((-points[:, 2]-.015)/.045)
hem_height = .858-.024*smooth((-points[:, 2]-.015)/.11)
hem = 1-smooth((points[:, 1]-hem_height)/.14)
waist = smooth((points[:, 1]-.93)/.055)

base, raw = read_glb(BODY)
body_primitive = base['meshes'][0]['primitives'][0]
ba = body_primitive['attributes']
bp = accessor(base, raw, ba['POSITION'])
bf = accessor(base, raw, body_primitive['indices']).reshape(-1, 3)
bj = accessor(base, raw, ba['JOINTS_0']).astype(int)
bw = accessor(base, raw, ba['WEIGHTS_0'])
body_region = (bp[:, 1] > .45) & (bp[:, 1] < 1.16) & (np.abs(bp[:, 0]) < .26)
body_faces = bf[body_region[bf].all(1)]
leg_faces = bf[(body_region & (bp[:, 1] < 1.015))[bf].all(1)]
poses = json.loads((OUTPUT / 'sit-poses.json').read_text())
assert poses['base_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
frames = []
leg_surfaces = []
for sample in poses['samples']:
    matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    body = deform(bp, bj, bw, matrices)
    blended = np.einsum('nk,nkij->nij', weights, matrices[joints])
    frames.append((BVHTree.FromPolygons([Vector(p) for p in body], body_faces.tolist()),
                   blended[:, :3, :3], blended[:, :3, 3], np.linalg.inv(blended[:, :3, :3]), body))
    leg_surfaces.append(BVHTree.FromPolygons([Vector(p) for p in body], leg_faces.tolist()))
fit_indices = np.linspace(0, len(frames)-1, 9).astype(int)
fit_frames = [frames[i] for i in fit_indices]
surface, linear, translation, inverse, body = frames[len(frames)//2]
middle_linear, middle_inverse = linear.copy(), inverse.copy()
posed = np.einsum('nij,nj->ni', linear, points)+translation
base_posed = posed.copy()
target = posed.copy()
matrices = np.array(poses['samples'][len(frames)//2]['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
pelvis = points @ matrices[0, :3, :3].T+matrices[0, :3, 3]
rigid_waist = smooth((points[:, 1]-.96)/.05)*cloth_vertices
target += rigid_waist[:, None]*(pelvis-target)
hem_z = .275
thigh = (np.abs(body[:, 2]-hem_z) < .018) & (np.abs(body[:, 0]) < .20) & body_region
hem_y = float(body[thigh, 1].max())+.010
front_hem = front*hem*cloth_vertices
rim_height = 1.066+.020*smooth(np.abs(points[:, 0])/.13)
length = np.clip((rim_height-points[:, 1])/(rim_height-hem_height), 0, 1)
x = points[:, 0]/.20
features = np.column_stack([np.ones(len(points)), x, x*x, x**4, length, length**2,
                            x*length, x*x*length, x**4*length, x*x*length**2])
selected = cloth_vertices & (front > .8)
profile = features @ np.linalg.lstsq(features[selected], points[selected, 2], rcond=None)[0]
relief = (points[:, 2]-profile)*.8*(1-hem)+.2*(points[:, 2]-.10)*hem
front_y = .685*(1-length)+hem_y*length+relief
waist_z = .095-.055*smooth(np.abs(points[:, 0])/.17)
front_z = waist_z*(1-length)+hem_z*length-.2*(points[:, 1]-hem_height)*hem
blend = front*cloth_vertices
target[:, 1] += blend*(front_y-target[:, 1])
target[:, 2] += blend*(front_z-target[:, 2])
rear_drop = (.035-.007*smooth(np.abs(points[:, 0])/.15))*rear*waist*cloth_vertices
target[:, 1] -= rear_drop
delta = np.einsum('nij,nj->ni', inverse, target-posed)
initial_delta = delta.copy()
tree = KDTree(len(first))
for i, p in enumerate(points[first]):
    tree.insert(Vector(p), i)
tree.balance()
close = [[entry[1] for entry in tree.find_range(Vector(p), .004)
          if cloth_vertices[first[entry[1]]]] for p in points[first]]
flat_tree = KDTree(len(first))
for i, p in enumerate(points[first]):
    flat_tree.insert(Vector((p[0], p[1], 0)), i)
flat_tree.balance()
for i in np.flatnonzero(selected[first]):
    p = points[first[i]]
    close[i] = [entry[1] for entry in flat_tree.find_range(Vector((p[0], p[1], 0)), .004)
                if selected[first[entry[1]]]]
neighbors = [set() for _ in first]
for face in welded[cloth_faces]:
    for a, b in zip(face, np.roll(face, 1)):
        if a != b:
            neighbors[a].add(int(b))
            neighbors[b].add(int(a))
barycentric = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3),
               (.5, .5, 0), (.5, 0, .5), (0, .5, .5)]
for iteration in range(36):
    correction, count = np.zeros((len(first), 3)), np.zeros(len(first))
    maximum = 0
    for frame in fit_indices:
        surface, linear, translation, inverse, _ = frames[frame]
        posed = np.einsum('nij,nj->ni', linear, points+delta)+translation
        for bary in barycentric:
            for face, p in zip(cloth_faces, np.einsum('fkj,k->fj', posed[cloth_faces], bary)):
                reference = np.array(bary) @ points[face]
                hit, normal, _, _ = surface.find_nearest(Vector(p))
                signed = np.dot(p-np.array(hit), normal)
                movement = np.array(normal)
                gap = signed
                front_panel = reference[2] > .035 and np.array(bary) @ length[face] > .25
                if front_panel:
                    hit, _, _, distance = leg_surfaces[frame].ray_cast(Vector(p+[0, .18, 0]), Vector((0, -1, 0)), .36)
                    if hit is None:
                        continue
                    gap = distance-.18
                    movement = np.array([0., 1., 0.])
                if gap >= .008:
                    continue
                maximum = max(maximum, .008-gap)
                error = min(.008-gap, .02)
                if (reference[2] < -.04 and reference[1] > 1.0) or (reference[2] > .035 and not front_panel):
                    movement[1] = 0
                    movement /= max(np.dot(movement, normal), .15)
                change = movement*error
                change *= min(1, .004/max(np.linalg.norm(change), 1e-12))
                for i in set(welded[face]):
                    vertex = first[i]
                    correction[i] += inverse[vertex] @ change
                    count[i] += 1
    unique = delta[first]+1.1*correction/np.maximum(count[:, None], 1)
    world_correction = np.einsum('nij,nj->ni', middle_linear[first], unique-initial_delta[first])
    updated_world = world_correction.copy()
    for i in np.flatnonzero(cloth_vertices[first]):
        adjacent = list(neighbors[i])
        if close[i]:
            updated_world[i] = world_correction[close[i]].mean(0)
        if adjacent:
            relaxation = .12*(1-front_hem[first[i]])
            updated_world[i] += relaxation*(world_correction[adjacent].mean(0)-world_correction[i])
    updated = initial_delta[first]+np.einsum('nij,nj->ni', middle_inverse[first], updated_world)
    delta = updated[welded]
    print(json.dumps({'iteration': iteration+1, 'maximum_deficit_m': maximum}), flush=True)
    if maximum < .0006:
        break

cloth = BVHTree.FromPolygons([Vector(p) for p in points], cloth_faces.tolist())
corrected_cloth = base_posed+np.einsum('nij,nj->ni', middle_linear, delta)
for label in np.unique(labels):
    if label == main:
        continue
    ids = np.flatnonzero(labels == label)
    following = []
    axes = []
    for i in ids:
        _, _, face, _ = cloth.find_nearest(Vector(points[i]))
        indices = cloth_faces[face]
        a, b, c = points[indices]
        old_normal = np.cross(b-a, c-a)
        old_normal /= np.linalg.norm(old_normal)
        pa, pb, pc = corrected_cloth[indices]
        new_normal = np.cross(pb-pa, pc-pa)
        new_normal /= np.linalg.norm(new_normal)
        coordinates = np.linalg.solve(np.column_stack((b-a, c-a, old_normal)), points[i]-a)
        following.append(pa+np.column_stack((pb-pa, pc-pa, new_normal)) @ coordinates)
        radial = np.array([points[i, 0], 0, points[i, 2]+.015])
        axes.append(new_normal*(1 if np.dot(old_normal, radial) >= 0 else -1))
    following = np.array(following)
    center, target_center = base_posed[ids].mean(0), following.mean(0)
    u, _, vt = np.linalg.svd((base_posed[ids]-center).T @ (following-target_center))
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    original_center = points[ids].mean(0)
    loop = np.ptp(points[ids, 1]) > .025 and (abs(original_center[0]) > .055 or original_center[2] < -.02)
    flexible = loop and original_center[2] < -.02
    target_world = following if flexible else (base_posed[ids]-center) @ rotation+target_center
    delta[ids] = np.einsum('nij,nj->ni', middle_inverse[ids], target_world-base_posed[ids])
    for _ in range(8):
        corrections = np.zeros((len(ids), 3))
        counts = np.zeros(len(ids))
        for frame in np.linspace(0, len(frames)-1, 9).astype(int):
            _, linear, translation, inverse, _ = frames[frame]
            posed = np.einsum('nij,nj->ni', linear, points+delta)+translation
            surface = BVHTree.FromPolygons([Vector(p) for p in posed], cloth_faces.tolist())
            for k, i in enumerate(ids):
                axis = axes[k]
                hit, _, _, distance = surface.ray_cast(Vector(posed[i]+axis*.08), Vector(-axis), .16)
                if hit is None:
                    continue
                gap = distance-.08
                target_gap = float(np.clip(gap, .001, .006 if loop else .009))
                if abs(target_gap-gap) > .0001:
                    corrections[k] += inverse[i] @ (axis*(target_gap-gap))
                    counts[k] += 1
        changes = corrections/np.maximum(counts[:, None], 1)
        if not np.any(counts):
            break
        if flexible:
            delta[ids] += changes
        else:
            world_changes = np.einsum('nij,nj->ni', middle_linear[ids], changes)
            shift = world_changes[np.linalg.norm(world_changes, axis=1).argmax()]
            delta[ids] += np.einsum('nij,j->ni', middle_inverse[ids], shift)

_, linear, translation, inverse, _ = frames[len(frames)//2]
morphed = np.einsum('nij,nj->ni', linear, points+delta)+translation
normal_sum = np.zeros((len(first), 3))
normals = np.cross(morphed[faces[:, 1]]-morphed[faces[:, 0]], morphed[faces[:, 2]]-morphed[faces[:, 0]])
for k in range(3):
    np.add.at(normal_sum, welded[faces[:, k]], normals)
world_normal = normal_sum[welded]
new_normal = np.einsum('nij,nj->ni', inverse, world_normal)
new_normal /= np.maximum(np.linalg.norm(new_normal, axis=1, keepdims=True), 1e-12)
old_normal = accessor(doc, binary, attrs['NORMAL'])
target = {'POSITION': add_accessor(doc, binary, delta, 'VEC3'),
          'NORMAL': add_accessor(doc, binary, new_normal-old_normal, 'VEC3')}
if 'TANGENT' in attrs:
    tangent = accessor(doc, binary, attrs['TANGENT'])[:, :3]
    corrected = tangent-new_normal*np.einsum('ij,ij->i', tangent, new_normal)[:, None]
    corrected /= np.maximum(np.linalg.norm(corrected, axis=1, keepdims=True), 1e-12)
    target['TANGENT'] = add_accessor(doc, binary, corrected-tangent, 'VEC3')
primitive['targets'] = [target]
doc['meshes'][0]['weights'] = [0]
doc['meshes'][0].setdefault('extras', {})['targetNames'] = ['pose_sit_idle']
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT / 'bottom_female_rogue.glb', doc, binary)
report = {'date': '2026-10-26', 'revision': 'v5', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'body_sha256': poses['base_sha256'],
          'morph': 'pose_sit_idle', 'default_weight': 0, 'triangles': len(faces),
          'front_hem_target_y_m': hem_y, 'front_hem_target_z_m': hem_z, 'rear_center_waist_drop_m': .035,
          'maximum_offset_m': float(np.linalg.norm(delta, axis=1).max()),
          'base_geometry_and_skinning_preserved': True, 'original_uv_and_texture_bytes_preserved': True,
          'no_new_api_requests': True}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
