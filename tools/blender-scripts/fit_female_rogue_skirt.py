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

SOURCE = ROOT / 'assets/items/female_rogue_skirt/tripo_v1/source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = SOURCE.parents[1] / 'fitted_v1'
OUTPUT.mkdir(exist_ok=True)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def islands(points, faces):
    _, first, welded = np.unique(np.round(points, 6), axis=0, return_index=True, return_inverse=True)
    welded = welded.ravel()
    parent = np.arange(len(first))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for face in welded[faces]:
        a = root(face[0])
        for b in face[1:]:
            parent[root(b)] = a
    return first, welded, np.array([root(i) for i in welded])


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

def clear_rest(points, iterations=30):
    barycentric = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1/3, 1/3, 1/3),
                   (.5, .5, 0), (.5, 0, .5), (0, .5, .5)]
    for _ in range(iterations):
        delta = np.zeros((len(first), 3))
        count = np.zeros(len(first))
        maximum = 0
        for bary in barycentric:
            for face, p in zip(faces, np.einsum('fkj,k->fj', points[faces], bary)):
                hit, normal, _, _ = surface.find_nearest(Vector(p))
                signed = np.dot(p - np.array(hit), normal)
                if signed < .005:
                    change = np.array(normal) * (.005 - signed)
                    change[2] = 0
                    for i in set(welded[face]):
                        delta[i] += change
                        count[i] += 1
                    maximum = max(maximum, .005 - signed)
        points += 1.3 * (delta / np.maximum(count[:, None], 1))[welded]
        if maximum < .0003:
            break
    return points


points = clear_rest(points)
weights = np.zeros((len(points), len(names)))
for i, p in enumerate(points):
    hit, _, fi, _ = surface.find_nearest(Vector(p))
    indices = skin_faces[fi]
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
weights = unique[welded]
for label in np.unique(labels):
    chosen = labels == label
    if len(np.unique(welded[chosen])) < 120:
        weights[chosen] = weights[chosen].mean(0)
        weights[chosen, names.index('Hips')] += weights[chosen, names.index('LeftUpLeg')] + weights[chosen, names.index('RightUpLeg')]
        weights[np.ix_(chosen, [names.index('LeftUpLeg'), names.index('RightUpLeg')])] = 0
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
          'method': 'Aligned source axes, waist taper and skin clearance; barycentric skin weight transfer, spatial smoothing across nearby surfaces, rigid accessory islands; exact canonical hierarchy and inverse bind matrices.',
          'no_new_api_requests': True,
          'status': 'Fitted and rigged; validation and visual review recorded separately'}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
