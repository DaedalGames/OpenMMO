import hashlib
import json
import subprocess
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor
from outfits.skinning import deform

DIRECTORY = ROOT / 'assets/items/female_rogue_skirt/tripo_v1/fitted_v1'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
SKIRT = DIRECTORY / 'bottom_female_rogue.glb'
TOP = ROOT / 'assets/items/female_rogue_top/tripo_v1/fitted_v1/top_female_rogue.glb'


def load_mesh(path):
    doc, raw = read_glb(path)
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    return (doc, accessor(doc, raw, attrs['POSITION']), accessor(doc, raw, primitive['indices']).reshape(-1, 3),
            accessor(doc, raw, attrs['JOINTS_0']).astype(int), accessor(doc, raw, attrs['WEIGHTS_0']))


base, bp, bf, bj, bw = load_mesh(BODY)
doc, tp, tf, tj, tw = load_mesh(SKIRT)
_, inverse = np.unique(np.round(bp, 6), axis=0, return_inverse=True)
inverse = inverse.ravel()
parent = np.arange(inverse.max() + 1)


def root(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for face in inverse[bf]:
    a = root(face[0])
    for b in face[1:]:
        parent[root(b)] = a
labels = np.array([root(i) for i in inverse])
main = np.bincount(labels).argmax()
skin_faces = bf[(labels[bf] == main).all(1)]
top_surface = BVHTree.FromPolygons([Vector(p) for p in tp], tf.tolist())
_, raw = read_glb(BODY)
normal = accessor(base, raw, base['meshes'][0]['primitives'][0]['attributes']['NORMAL'])
covered = np.zeros(len(bp), dtype=bool)
for i in np.flatnonzero((labels == main) & (bp[:, 1] > .94) & (bp[:, 1] < 1.10)):
    hit, _, _, distance = top_surface.ray_cast(Vector(bp[i]), Vector(normal[i]), .045)
    covered[i] = hit is not None and bp[i, 1] > .94
for _ in range(2):
    boundary_faces = (covered[bf].any(1)) & ~covered[bf].all(1)
    covered[np.unique(bf[boundary_faces])] = False
hidden = covered[bf].all(1)
mask = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
        'skirt_sha256': hashlib.sha256(SKIRT.read_bytes()).hexdigest(), 'mesh_index': 0, 'primitive_index': 0,
        'source_triangles': len(bf), 'primitive_triangles': len(bf),
        'hide_triangle_indices': np.flatnonzero(hidden).tolist(),
        'underwear_triangles': 0, 'covered_skin_triangles': int(hidden.sum()),
        'scope': 'Candidate reversible coverage mask on the exact base. Inward-eroded pelvis skin with a garment hit within 45mm; open hem and underwear retained. Runtime registration and mixed equipment validation separate.'}
(DIRECTORY / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')

samples = json.loads((DIRECTORY / 'animation-samples.json').read_text())
validation = json.loads((DIRECTORY / 'animation-validation.json').read_text())
assert validation['base_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
assert validation['skirt_sha256'] == hashlib.sha256(SKIRT.read_bytes()).hexdigest()
report = {}
for sample in [{'clip': 'rest', 'sample': 0, 'phase': 0, 'matrices': np.tile(np.eye(4).T.ravel(), (65, 1)).tolist()}, *samples]:
    matrices = np.array(sample['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    body_points = deform(bp, bj, bw, matrices)
    top_points = deform(tp, tj, tw, matrices)
    surface = BVHTree.FromPolygons([Vector(p) for p in body_points], skin_faces.tolist())
    metrics = []
    skin_hidden = hidden[(labels[bf] == main).all(1)]
    for query in [top_points, top_points[tf].mean(1)]:
        signed = []
        unmasked = []
        for p in query:
            hit, normal, face, _ = surface.find_nearest(Vector(p))
            value = float(np.dot(p - np.array(hit), normal))
            signed.append(value)
            if not skin_hidden[face]:
                unmasked.append(value)
        for values in [signed, unmasked]:
            values = np.array(values)
            metrics.append({'minimum_m': float(values.min()), 'deeper_than_3mm': int((values < -.003).sum())})
    result = {'phase': sample['phase'], 'vertices_full_skin': metrics[0], 'vertices_visible_skin': metrics[1],
              'centroids_full_skin': metrics[2], 'centroids_visible_skin': metrics[3]}
    name = sample['clip']
    if name not in report or result['centroids_full_skin']['deeper_than_3mm'] > report[name]['centroids_full_skin']['deeper_than_3mm']:
        report[name] = result
(DIRECTORY / 'clearance-validation.json').write_text(json.dumps({'body_sha256': validation['base_sha256'],
    'skirt_sha256': validation['skirt_sha256'],
    'scope': 'Signed nearest full-skin triangle distance at garment vertices and triangle centroids, 33 samples per clip. Visible counts exclude queries whose nearest full-skin triangle is masked; visual review remains necessary.', 'clips': report}, indent=2) + '\n')
print(json.dumps(report), flush=True)
if '--metrics-only' in sys.argv:
    sys.exit(0)

(DIRECTORY / 'review').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
body = bpy.data.objects['female_body']
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SKIRT), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects) - before
top = next(o for o in imported if o.type == 'MESH')
for modifier in top.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
top.parent = rig
for obj in imported:
    if obj.type == 'ARMATURE':
        bpy.data.objects.remove(obj, do_unlink=True)

tree = KDTree(len(body.data.polygons))
for face in body.data.polygons:
    c = body.matrix_world @ face.center
    tree.insert(Vector((c.x, c.z, -c.y)), face.index)
tree.balance()
top_mask = json.loads((ROOT / 'assets/items/female_rogue_top/tripo_v1/fitted_v1/body-occlusion.json').read_text())
hidden[top_mask['hide_triangle_indices']] = True
matched = {tree.find(Vector(c))[1] for c in bp[bf[hidden]].mean(1)}
assert len(matched) == int(hidden.sum())
edit = bmesh.new()
edit.from_mesh(body.data)
edit.faces.ensure_lookup_table()
bmesh.ops.delete(edit, geom=[edit.faces[i] for i in matched], context='FACES')
edit.to_mesh(body.data)
edit.free()
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(TOP), bone_heuristic='TEMPERANCE')
for obj in set(bpy.data.objects) - before:
    if obj.type == 'MESH':
        obj.parent = rig
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
    elif obj.type == 'ARMATURE':
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.view_layer.update()
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Rogue studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .19, .22, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .7
for location, energy in [((2, -3, 3), 400), ((-3, -1, 2), 240), ((1, 3, 3), 450)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.data.energy, light.data.size = energy, 3
    light.rotation_euler = (Vector((0, 0, 1.35)) - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 700
scene.view_settings.view_transform = 'AgX'


def render(name, offset, center, scale):
    camera.location = Vector(center) + Vector(offset)
    camera.rotation_euler = (Vector(center) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(DIRECTORY / 'review' / f'{name}.png')
    bpy.ops.render.render(write_still=True)


for name, offset in [('front', (0, -3, 0)), ('side', (3, 0, 0)), ('back', (0, 3, 0)), ('angle', (2, -3, .2))]:
    render(name, offset, (0, 0, 1.05), 1.0)
conversion = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
canonical = [base['nodes'][j]['name'] for j in base['skins'][0]['joints']]
ordered = sorted(rig.pose.bones, key=lambda b: len(b.parent_recursive))
for bone in ordered:
    bone.rotation_mode = 'QUATERNION'
    for channel in ['location', 'rotation_quaternion', 'scale']:
        bone.keyframe_insert(data_path=channel, frame=1)
scene.timeline_markers.new('Rest', frame=1)
for index, name in enumerate(dict.fromkeys(s['clip'] for s in samples), 1):
    phase = report[name]['phase']
    snapshot = min((s for s in samples if s['clip'] == name), key=lambda s: abs(s['phase'] - phase))
    scene.frame_set(index * 10)
    matrices = dict(zip(canonical, snapshot['matrices']))
    for bone in ordered:
        deformation = Matrix(np.array(matrices[bone.name]).reshape(4, 4).T.tolist())
        bone.matrix = rig.matrix_world.inverted() @ conversion @ deformation @ conversion.inverted() @ rig.matrix_world @ bone.bone.matrix_local
        bpy.context.view_layer.update()
        for channel in ['location', 'rotation_quaternion', 'scale']:
            bone.keyframe_insert(data_path=channel, frame=index * 10)
    scene.timeline_markers.new(name, frame=index * 10)
    center = rig.matrix_world @ rig.pose.bones['Hips'].head
    render(name, (1.5, -3, .5), center, 1.2)
    if name in ['run', 'slash1', 'sit_idle', 'walk']:
        render(name + '_back', (-1.5, 3, .5), center, 1.35)
scene.frame_set(1)
scene.frame_end = index * 10
for layer in rig.animation_data.action.layers:
    for strip in layer.strips:
        for slot in rig.animation_data.action.slots:
            channels = strip.channelbag(slot)
            if channels:
                for curve in channels.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'CONSTANT'
rig.animation_data.action.name = 'Rogue fitting - sampled game poses'
references = bpy.data.collections.new('Original Tripo source - hidden')
scene.collection.children.link(references)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'assets/items/female_rogue_skirt/tripo_v1/source/model_url.glb'))
for obj in set(bpy.data.objects) - before:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    references.objects.link(obj)
references.hide_render = references.hide_viewport = True
bpy.ops.object.select_all(action='DESELECT')
top.select_set(True)
bpy.context.view_layer.objects.active = top
camera.location = (2, -3, 1.25)
camera.rotation_euler = (Vector((0, 0, 1.05)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.ortho_scale = 1.0
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(DIRECTORY / 'female-rogue-skirt.blend'))
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(DIRECTORY / 'review/front.png'), '-i', str(DIRECTORY / 'review/back.png'),
                '-filter_complex', 'hstack=inputs=2', '-frames:v', '1',
                str(DIRECTORY / 'review/fitting.png')], check=True)
