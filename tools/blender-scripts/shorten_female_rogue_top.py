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

DIRECTORY = ROOT / 'assets/items/female_rogue_top/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v1/top_female_rogue.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v4'
OUTPUT.mkdir(exist_ok=True)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t*t*(3-2*t)


doc, binary = read_glb(SOURCE)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
original = points.copy()
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
first, welded, labels = welded_islands(points, faces)
base, raw = read_glb(BODY)
body_primitive = base['meshes'][0]['primitives'][0]
bp = accessor(base, raw, body_primitive['attributes']['POSITION'])
bf = accessor(base, raw, body_primitive['indices']).reshape(-1, 3)
_, _, body_labels = welded_islands(bp, bf)
main = np.bincount(body_labels).argmax()
skin_faces = bf[(body_labels[bf] == main).all(1)]
surface = BVHTree.FromPolygons([Vector(p) for p in bp], skin_faces.tolist())
lift = .036 * (1-smooth((points[:, 1]-1.13)/.15))
lift *= 1-smooth((np.abs(points[:, 0])-.16)/.04)
points[:, 1] += lift
changed = lift > 1e-9
for label in np.unique(labels):
    chosen = labels == label
    if chosen.sum() < 120 and changed[chosen].all():
        points[chosen, 1] = original[chosen, 1] + lift[chosen].mean()
main_label = max(np.unique(labels), key=lambda label: len(np.unique(welded[labels == label])))
main_vertices = labels == main_label
placket = (1-smooth((np.abs(original[:, 0]-.013)-.025)/.045))
placket *= smooth((original[:, 2]-.04)/.04)*main_vertices
for i in np.flatnonzero(changed & main_vertices):
    hit, normal, _, _ = surface.find_nearest(Vector(points[i]))
    target = np.array(hit) + np.array(normal)*.009
    blend = 1-smooth((original[i, 1]-1.13)/.15)
    points[i, [0, 2]] += blend * (target[[0, 2]]-points[i, [0, 2]]) * [1-placket[i], 1]
edges = welded[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
neighbors = [set() for _ in first]
for a, b in edges:
    if a != b:
        neighbors[a].add(int(b))
        neighbors[b].add(int(a))
blend = (1-smooth((original[first, 1]-1.13)/.15)) * main_vertices[first] * changed[first]
for _ in range(18):
    unique = points[first].copy()
    for i in np.flatnonzero(blend):
        adjacent = list(neighbors[i])
        if adjacent:
            mean = points[first[adjacent]].mean(0)
            unique[i, [0, 2]] += .3*blend[i]*(mean[[0, 2]]-unique[i, [0, 2]]) * [1-placket[first[i]], 1]
    points = unique[welded]
for _ in range(20):
    delta, count = np.zeros((len(first), 3)), np.zeros(len(first))
    maximum = 0
    for bary in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3), (.5, .5, 0), (0, .5, .5), (.5, 0, .5)]:
        for face, p in zip(faces, np.einsum('fkj,k->fj', points[faces], bary)):
            if not (changed[face] & main_vertices[face]).any():
                continue
            hit, normal, _, _ = surface.find_nearest(Vector(p))
            signed = np.dot(p-np.array(hit), normal)
            if signed < .006:
                change = np.array(normal)*(.006-signed)
                change[1] = 0
                for i in set(welded[face[changed[face] & main_vertices[face]]]):
                    delta[i] += change * [1-placket[first[i]], 1, 1]
                    count[i] += 1
                maximum = max(maximum, .006-signed)
    points += 1.2*(delta/np.maximum(count[:, None], 1))[welded]
    if maximum < .0002:
        break

cloth_faces = faces[main_vertices[faces].all(1)]
cloth = BVHTree.FromPolygons([Vector(p) for p in points], cloth_faces.tolist())
joint_ids = accessor(doc, binary, attrs['JOINTS_0']).astype(int)
joint_values = accessor(doc, binary, attrs['WEIGHTS_0'])
dense = np.zeros((len(points), 65))
np.add.at(dense, (np.arange(len(points))[:, None], joint_ids), joint_values)
for label in np.unique(labels):
    chosen = labels == label
    if label == main_label or not changed[chosen].any():
        continue
    chosen &= changed
    center = points[chosen].mean(0)
    outward = np.array([center[0], 0, center[2]+.02])
    outward /= np.linalg.norm(outward)
    ids = np.flatnonzero(chosen)
    hits, gaps = [], []
    for i in ids:
        hit, _, _, _ = cloth.ray_cast(Vector(points[i]+outward*.08), Vector(-outward), .16)
        if hit is None:
            hit, _, _, _ = cloth.find_nearest(Vector(points[i]))
        hits.append(np.array(hit))
        gaps.append(np.dot(points[i]-np.array(hit), outward))
    gaps = np.array(gaps)
    offsets = .0015 + .002*(gaps-gaps.min())/max(np.ptp(gaps), 1e-9)
    points[chosen] = np.array(hits)+offsets[:, None]*outward
    for i in ids:
        hit, _, fi, _ = cloth.find_nearest(Vector(points[i]))
        indices = cloth_faces[fi]
        a, b, c = points[indices]
        uv = np.linalg.lstsq(np.column_stack((b-a, c-a)), np.array(hit)-a, rcond=None)[0]
        bary = np.clip([1-uv.sum(), *uv], 0, 1)
        bary /= bary.sum()
        dense[i] = bary @ dense[indices]
order = np.argsort(dense, axis=1)[:, -4:][:, ::-1]
values = np.take_along_axis(dense, order, axis=1)
values /= values.sum(1, keepdims=True)
attrs['JOINTS_0'] = add_accessor(doc, binary, order.astype(np.uint16), 'VEC4', 5123)
attrs['WEIGHTS_0'] = add_accessor(doc, binary, values, 'VEC4')

normal_sum = np.zeros((len(first), 3))
face_normals = np.cross(points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]])
for k in range(3):
    np.add.at(normal_sum, welded[faces[:, k]], face_normals)
normal_sum /= np.maximum(np.linalg.norm(normal_sum, axis=1, keepdims=True), 1e-12)
normals = accessor(doc, binary, attrs['NORMAL'])
normals[changed] = normal_sum[welded[changed]]
attrs['POSITION'] = add_accessor(doc, binary, points, 'VEC3')
attrs['NORMAL'] = add_accessor(doc, binary, normals, 'VEC3')
if 'TANGENT' in attrs:
    tangent = accessor(doc, binary, attrs['TANGENT'])
    tangent[changed, :3] -= normals[changed] * np.einsum('ij,ij->i', tangent[changed, :3], normals[changed])[:, None]
    tangent[changed, :3] /= np.maximum(np.linalg.norm(tangent[changed, :3], axis=1, keepdims=True), 1e-12)
    attrs['TANGENT'] = add_accessor(doc, binary, tangent, 'VEC4')
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT / 'top_female_rogue.glb', doc, binary)
report = {'revision': 'v4', 'date': '2026-10-26', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(), 'triangles': len(faces),
          'hem_raise_m': .036, 'hem_before_minimum_m': float(original[:, 1].min()),
          'hem_after_minimum_m': float(points[:, 1].min()), 'changed_vertices': int(changed.sum()),
          'method': 'Raise and smooth the lower corset while anchoring the front placket width to the accepted source; refit depth clearance and lower accessories while preserving sleeves, UVs and textures.',
          'placket_center_x_m': .013, 'placket_protected_half_width_m': .025,
          'placket_horizontal_maximum_change_m': float(np.abs(points[placket == 1, 0]-original[placket == 1, 0]).max()),
          'existing_skeleton_preserved': True, 'lower_accessories_follow_cloth': True,
          'lower_corset_smoothing_iterations': 18, 'upper_geometry_preserved': True,
          'original_uv_and_textures_preserved': True, 'no_new_api_requests': True}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
