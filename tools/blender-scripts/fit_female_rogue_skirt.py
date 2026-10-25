import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.mesh_components import welded_islands as islands

SOURCE = ROOT / 'assets/items/female_rogue_skirt/tripo_v1/source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = SOURCE.parents[1] / 'fitted_v4'
OUTPUT.mkdir(exist_ok=True)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['female_body']
bp = np.array([body.matrix_world @ v.co for v in body.data.vertices])
bf = np.array([p.vertices[:] for p in body.data.polygons])
_, _, labels = islands(bp, bf)
skin_label = np.bincount(labels).argmax()
skin_faces = bf[(labels[bf] == skin_label).all(1)]
surface = BVHTree.FromPolygons([Vector(p) for p in bp], skin_faces.tolist())
underwear_faces = []
for label in np.unique(labels):
    q = bp[labels == label]
    if label != skin_label and len(q) > 100 and q[:, 2].min() > .85 and q[:, 2].max() < 1.15:
        underwear_faces.extend(bf[(labels[bf] == label).all(1)].tolist())
clearance_faces = np.concatenate([skin_faces, np.array(underwear_faces, dtype=int)])
clearance_surface = BVHTree.FromPolygons([Vector(p) for p in bp], clearance_faces.tolist())
names = [bone.name for bone in rig.data.bones]
body_weights = np.zeros((len(bp), len(names)))
for v in body.data.vertices:
    for group in v.groups:
        name = body.vertex_groups[group.group].name
        if name in names:
            body_weights[v.index, names.index(name)] = group.weight

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
skirt = next(o for o in set(bpy.data.objects) - before if o.type == 'MESH')
skirt.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z'))
skirt.matrix_world = Matrix.Identity(4)
mesh = skirt.data
source = np.array([v.co for v in mesh.vertices])
faces = np.array([p.vertices[:] for p in mesh.polygons])
first, welded, labels = islands(source, faces)

points = source * .426
points[:, 2] += .9825
height = points[:, 2].copy()
points[:, 0] *= np.interp(height, [.835, .98, 1.07, 1.13], [1.04, 1.04, .94, .85])
points[:, 1] += np.interp(height, [.835, .98, 1.13], [.01, .03, -.015])
points[:, 2] = .835 + (points[:, 2] - .835) * .89
points[:, 0] *= .87
points[:, 1] = .015 + (points[:, 1] - .015) * .89
main_label = max(np.unique(labels), key=lambda label: len(np.unique(welded[labels == label])))
main_vertices = labels == main_label
rim = smooth((points[:, 2] - 1.005) / .055)
for i in np.flatnonzero(main_vertices & (rim > 0)):
    hit, normal, _, _ = surface.find_nearest(Vector(points[i]))
    target = np.array(hit) + np.array(normal) * .003
    points[i, :2] += .85 * rim[i] * (target[:2] - points[i, :2])

def clear_rest(points, iterations=24):
    main_faces = faces[main_vertices[faces].all(1)]
    barycentric = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3),
                   (.5, .5, 0), (.5, 0, .5), (0, .5, .5)]
    for _ in range(iterations):
        delta = np.zeros((len(first), 3))
        count = np.zeros(len(first))
        maximum = 0
        for bary in barycentric:
            for face, p in zip(main_faces, np.einsum('fkj,k->fj', points[main_faces], bary)):
                axis = np.array([p[0], p[1]-.015, 0])
                axis /= np.linalg.norm(axis)
                hit, _, _, distance = clearance_surface.ray_cast(Vector(p+axis*.1), Vector(-axis), .2)
                if hit is None:
                    continue
                gap = distance-.1
                rear = smooth((p[1]-.01)/.06)
                clearance = .004 + .003*rear
                if gap < clearance:
                    change = axis*(clearance-gap)
                    for i in set(welded[face]):
                        delta[i] += change
                        count[i] += 1
                    maximum = max(maximum, clearance-gap)
        points += 1.15*(delta/np.maximum(count[:, None], 1))[welded]
        if maximum < .0003:
            break
    return points


points = clear_rest(points)
weights = np.zeros((len(points), len(names)))
for i, p in enumerate(points):
    axis = np.array([p[0], p[1]-.015, 0])
    axis /= np.linalg.norm(axis)
    hit, _, fi, _ = clearance_surface.ray_cast(Vector(p+axis*.1), Vector(-axis), .2)
    if hit is None:
        hit, _, fi, _ = clearance_surface.find_nearest(Vector(p))
    indices = clearance_faces[fi]
    a, b, c = bp[indices]
    uv = np.linalg.lstsq(np.column_stack((b-a, c-a)), np.array(hit)-a, rcond=None)[0]
    bary = np.clip([1-uv.sum(), *uv], 0, 1)
    bary /= bary.sum()
    weights[i] = bary @ body_weights[indices]
    allowed = [names.index(n) for n in ['Hips', 'Spine', 'LeftUpLeg', 'RightUpLeg']]
    weights[i, [j for j in range(len(names)) if j not in allowed]] = 0
    weights[i] /= weights[i].sum()
    left = smooth((p[0] + .065) / .13)
    thigh = weights[i, names.index('LeftUpLeg')] + weights[i, names.index('RightUpLeg')]
    weights[i, names.index('LeftUpLeg')] = thigh * left
    weights[i, names.index('RightUpLeg')] = thigh * (1-left)

unique = weights[first]
contact_weights = unique.copy()
tree = KDTree(len(first))
for i, p in enumerate(points[first]):
    tree.insert(Vector(p), i)
tree.balance()
nearby = [tree.find_range(Vector(p), .025) for p in points[first]]
for _ in range(3):
    updated = unique.copy()
    for i, adjacent in enumerate(nearby):
        ids = [item[1] for item in adjacent]
        kernel = np.exp(-(np.array([item[2] for item in adjacent]) / .012)**2)
        updated[i] = (unique[ids] * kernel[:, None]).sum(0) / kernel.sum()
    unique = updated
contact_blend = smooth((points[first, 2] - .94) / .04)[:, None]
unique = unique * (1-contact_blend) + contact_weights * contact_blend
weights = unique[welded]
main_faces = faces[main_vertices[faces].all(1)]
cloth_surface = BVHTree.FromPolygons([Vector(p) for p in points], main_faces.tolist())
accessory_fit = []
for label in np.unique(labels):
    chosen = labels == label
    if label == main_label:
        continue
    center = points[chosen].mean(0)
    outward = center.copy()
    outward[1] -= .015
    outward[2] = 0
    outward /= np.linalg.norm(outward)
    original_accessory = points[chosen].copy()
    if abs(center[0]) < .04 and center[1] < -.06:
        points[chosen, 2] += .0001
    hits, gaps = [], []
    for p in points[chosen]:
        hit, _, _, distance = cloth_surface.ray_cast(Vector(p + outward * .08), Vector(-outward), .16)
        if hit is None:
            hit, _, _, _ = cloth_surface.find_nearest(Vector(p))
        hits.append(np.array(hit))
        gaps.append(np.dot(p-np.array(hit), outward))
    gaps = np.array(gaps)
    loop = (abs(center[0]) > .055 or center[1] > .02) and np.ptp(points[chosen, 2]) > .025
    backing = .0008 if loop else .0012
    thickness = .0018 if loop else .003
    offsets = backing + thickness*(gaps-gaps.min())/max(np.ptp(gaps), 1e-9)
    points[chosen] = np.array(hits) + offsets[:, None]*outward
    component_faces = faces[(labels[faces] == label).all(1)]
    for _ in range(40):
        correction = np.zeros((len(first), 3))
        counts = np.zeros(len(first))
        maximum = 0
        for bary in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3), (.5, .5, 0), (0, .5, .5), (.5, 0, .5)]:
            for face, p in zip(component_faces, np.einsum('fkj,k->fj', points[component_faces], bary)):
                axis = np.array([p[0], p[1]-.015, 0])
                axis /= np.linalg.norm(axis)
                hit, _, _, distance = cloth_surface.ray_cast(Vector(p+axis*.06), Vector(-axis), .12)
                if hit is None:
                    continue
                gap = distance-.06
                error = float(np.clip(gap, .0016, .0038)-gap)
                maximum = max(maximum, abs(error))
                for vertex in set(welded[face]):
                    correction[vertex] += axis*error
                    counts[vertex] += 1
        points[chosen] += 1.15*(correction/np.maximum(counts[:, None], 1))[welded[chosen]]
        if maximum < .0001:
            break
    if abs(center[0]) < .04 and center[1] < -.06:
        points[chosen] += outward*.0005
    for i in np.flatnonzero(chosen):
        axis = np.array([points[i, 0], points[i, 1]-.015, 0])
        axis /= np.linalg.norm(axis)
        hit, _, fi, _ = cloth_surface.ray_cast(Vector(points[i]+axis*.06), Vector(-axis), .12)
        if hit is None:
            hit, _, fi, _ = cloth_surface.find_nearest(Vector(points[i]))
        indices = main_faces[fi]
        a, b, c = points[indices]
        uv = np.linalg.lstsq(np.column_stack((b-a, c-a)), np.array(hit)-a, rcond=None)[0]
        bary = np.clip([1-uv.sum(), *uv], 0, 1)
        bary /= bary.sum()
        weights[i] = bary @ weights[indices]
    accessory_fit.append({'component': int(label), 'initial_backing_gap_m': backing,
                          'initial_maximum_gap_m': backing+thickness,
                          'maximum_correction_m': float(np.linalg.norm(points[chosen]-original_accessory, axis=1).max()),
                          'center_blender': points[chosen].mean(0).tolist()})
order = np.argsort(weights, axis=1)[:, -4:][:, ::-1]
values = np.take_along_axis(weights, order, axis=1)
values[values < .002] = 0
values /= values.sum(1, keepdims=True)
order[values == 0] = 0


for v, p in zip(mesh.vertices, points):
    v.co = p
mesh.update()
normal = np.cross(points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]])
normal_sum = np.zeros((len(first), 3))
for k in range(3):
    np.add.at(normal_sum, welded[faces[:, k]], normal)
normal_sum /= np.maximum(np.linalg.norm(normal_sum, axis=1, keepdims=True), 1e-12)
mesh.normals_split_custom_set([normal_sum[welded[loop.vertex_index]] for loop in mesh.loops])
for group in list(skirt.vertex_groups):
    skirt.vertex_groups.remove(group)
for name in names:
    skirt.vertex_groups.new(name=name)
for i in range(len(points)):
    for j, weight in zip(order[i], values[i]):
        if weight:
            skirt.vertex_groups[int(j)].add([i], float(weight), 'REPLACE')
modifier = skirt.modifiers.new('Female rig', 'ARMATURE')
modifier.object = rig
skirt.parent = rig
skirt.name = mesh.name = 'bottom_female_rogue'
for key, data in [('_RIG_JOINTS', order), ('_RIG_WEIGHTS', values)]:
    mesh.attributes.new(key, 'FLOAT_COLOR', 'POINT').data.foreach_set('color', data.astype(np.float32).ravel())
bpy.ops.object.select_all(action='DESELECT')
skirt.select_set(True)
bpy.context.view_layer.objects.active = skirt
intermediate = OUTPUT / 'geometry.glb'
modifier.show_viewport = modifier.show_render = False
bpy.ops.export_scene.gltf(filepath=str(intermediate), export_format='GLB', use_selection=True,
                          export_animations=False, export_skins=False, export_attributes=True, export_tangents=True)
modifier.show_viewport = modifier.show_render = True
doc, raw = read_glb(intermediate)
raw = bytearray(raw)
base, base_raw = read_glb(BODY)
attrs = doc['meshes'][0]['primitives'][0]['attributes']
source_order = accessor(doc, raw, attrs.pop('_RIG_JOINTS')).astype(np.uint16)
source_values = accessor(doc, raw, attrs.pop('_RIG_WEIGHTS'))
canonical = [base['nodes'][j]['name'] for j in base['skins'][0]['joints']]
remap_order = np.array([canonical.index(name) for name in names])
attrs['JOINTS_0'] = add_accessor(doc, raw, remap_order[source_order], 'VEC4', 5123)
attrs['WEIGHTS_0'] = add_accessor(doc, raw, source_values, 'VEC4')
ids = base['skins'][0]['joints']
remap = {old: new for new, old in enumerate(ids)}
doc['nodes'] = [copy.deepcopy(base['nodes'][i]) for i in ids]
for node in doc['nodes']:
    if 'children' in node:
        node['children'] = [remap[i] for i in node['children'] if i in remap]
children = {i for node in doc['nodes'] for i in node.get('children', [])}
doc['nodes'].append({'name': 'Armature', 'children': [i for i in range(len(ids)) if i not in children]})
doc['nodes'].append({'name': skirt.name, 'mesh': 0, 'skin': 0,
                     'extras': {'rig_id': 'human_female_01_local_v1', 'part_id': skirt.name}})
skin = copy.deepcopy(base['skins'][0])
skin['joints'] = list(range(len(ids)))
if 'skeleton' in skin:
    skin['skeleton'] = remap[skin['skeleton']]
skin['inverseBindMatrices'] = add_accessor(doc, raw, accessor(base, base_raw, base['skins'][0]['inverseBindMatrices']), 'MAT4')
doc['skins'] = [skin]
doc['scenes'] = [{'nodes': [len(ids), len(ids)+1]}]
doc['scene'] = 0
doc.pop('animations', None)
doc['buffers'] = [{'byteLength': len(raw)}]
write_glb(OUTPUT / 'bottom_female_rogue.glb', doc, raw)
intermediate.unlink()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-rogue-skirt.blend'))
report = {'date': '2026-10-25', 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(), 'triangles': len(faces),
          'bones': len(names), 'blender_version': bpy.app.version_string, 'units': 'metres',
          'revision': 'v4', 'accessory_fitting': accessory_fit,
          'shape_adjustment': {'height_scale_from_hem': .89,
          'hem_anchor_m': .835, 'width_scale': .87, 'depth_scale': .89,
          'upper_edge_lowering_m': .0324, 'front_radial_clearance_m': .004, 'rim_clearance_m': .003,
          'rim_contact_blend': .85, 'rear_radial_underwear_clearance_m': .007,
          'waist_body_weight_blend_m': [.94, .98],
          'accessory_relaxation_target_m': [.0016, .0038], 'buckle_height_offset_m': .0001, 'buckle_outward_bias_m': .0005},
          'method': 'Low-rise waist with radial skin and underwear clearance; waistband weights sampled from the same outer body surface; per-vertex accessory projection and relaxation against the outer cloth with barycentric weight transfer; exact canonical hierarchy and inverse bind matrices.',
          'no_new_api_requests': True,
          'status': 'Fitted and rigged; validation and visual review recorded separately'}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
