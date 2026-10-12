import hashlib
import json
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
VERSION = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'v2'
assert VERSION in ['v2', 'v3']
MEASURE_ONLY = '--measure-only' in sys.argv
OUTPUT = ROOT / f'assets/items/female_knight_top/tripo_v1/fitted_{VERSION}'
TOP = OUTPUT / 'top_female_knight.glb'
REVIEW = OUTPUT / 'review'
REVIEW.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
body = bpy.data.objects['female_body']
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(TOP), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects) - before
top = next(obj for obj in imported if obj.type == 'MESH')
fit_data = np.load(OUTPUT / 'sleeve-adjustment.npz') if VERSION == 'v3' else np.load(OUTPUT / 'fit-data.npz')
fit_points = fit_data['points'] if VERSION == 'v3' else fit_data['fitted']
tree = KDTree(len(fit_points))
for i, point in enumerate(fit_points):
    tree.insert(point, i)
tree.balance()
cuff_indices = {}
original_surface = np.load(ROOT / 'assets/items/female_knight_top/tripo_v1/fitted_v2/fit-data.npz')
unique_source, source_indices = np.unique(np.round(original_surface['source'], 7), axis=0, return_inverse=True)
source_edges = np.sort(source_indices[original_surface['faces'][:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)], axis=1)
source_edges, counts = np.unique(source_edges, axis=0, return_counts=True)
boundary = {tuple(point) for point in unique_source[np.unique(source_edges[counts == 1])]}
rim_indices = set()
for vertex in top.data.vertices:
    _, i, _ = tree.find(top.matrix_world @ vertex.co)
    source = fit_data['source'][i]
    if abs(source[0]) > .103 and source[2] < .690:
        cuff_indices[vertex.index] = 1 if source[0] > 0 else -1
        if tuple(np.round(source, 7)) in boundary:
            rim_indices.add(vertex.index)
world = top.matrix_world.copy()
top.parent = rig
top.matrix_world = world
for modifier in top.modifiers:
    if modifier.type == 'ARMATURE':
        modifier.object = rig
for obj in imported:
    if obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
clips = sorted({track.strips[0].action.name for track in rig.animation_data.nla_tracks if track.strips})
for track in rig.animation_data.nla_tracks:
    track.mute = True
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
unmasked = body.copy()
unmasked.data = body.data.copy()
bpy.context.collection.objects.link(unmasked)
unmasked.name = 'female_body_unmasked_reference'
unmasked.hide_render = True
unmasked.hide_set(True)
rest_body_points = np.array([unmasked.matrix_world @ vertex.co for vertex in unmasked.data.vertices])
arm_faces = {}
for sign in [1, -1]:
    selected = (rest_body_points[:, 0] * sign > .12) & (rest_body_points[:, 2] > .55) & (rest_body_points[:, 2] < .79)
    arm_faces[sign] = [polygon.vertices[:] for polygon in unmasked.data.polygons if selected[list(polygon.vertices)].all()]
mask = json.loads((OUTPUT / 'body-occlusion.json').read_text())
assert mask['body_sha256'] == hashlib.sha256(BODY.read_bytes()).hexdigest()
assert len(body.data.polygons) == mask['source_triangles']
bm = bmesh.new()
bm.from_mesh(body.data)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in mask['hide_triangle_indices']], context='FACES')
bm.to_mesh(body.data)
bm.free()
body['equipment_mask'] = f'female_knight_top_{VERSION}'
body['source_body_sha256'] = mask['body_sha256']
for action in bpy.data.actions:
    action.use_fake_user = True
rig.show_in_front = True
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
if not MEASURE_ONLY:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-knight-top-fitted.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Review')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.25, .25, .25, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
for location, energy in [((2, -3, 3), 300), ((-2, -1, 2), 200), ((0, 3, 2), 250)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.data.energy, light.data.size = energy, 3
    light.rotation_euler = (Vector((0, 0, .75)) - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type, camera.data.ortho_scale = 'ORTHO', .58
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 900
scene.view_settings.view_transform = 'AgX'


def render(name, offset):
    if MEASURE_ONLY:
        return
    center = rig.matrix_world @ rig.pose.bones['Spine1'].head + Vector((0, 0, .07))
    camera.location = center + Vector(offset)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(REVIEW / f'{name}.png')
    bpy.ops.render.render(write_still=True)


def evaluated(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    faces = [polygon.vertices[:] for polygon in mesh.polygons]
    evaluated.to_mesh_clear()
    return points, faces


def measure():
    points, faces = evaluated(unmasked)
    surface = BVHTree.FromPolygons(points, faces)
    arm_surfaces = {sign: BVHTree.FromPolygons(points, polygons) for sign, polygons in arm_faces.items()}
    top_points, top_faces = evaluated(top)
    worst, inside, cuff_worst, cuff_inside, own_worst, own_inside, rim_worst, rim_inside = 1, 0, 1, 0, 1, 0, 1, 0
    for i, point in enumerate(top_points):
        nearest, normal, _, _ = surface.find_nearest(point)
        distance = (point - nearest).dot(normal)
        worst = min(worst, distance)
        inside += distance < -.003
        if i in cuff_indices:
            cuff_worst = min(cuff_worst, distance)
            cuff_inside += distance < 0
            nearest, normal, _, _ = arm_surfaces[cuff_indices[i]].find_nearest(point)
            own_distance = (point - nearest).dot(normal)
            own_worst = min(own_worst, own_distance)
            own_inside += own_distance < 0
            if i in rim_indices:
                rim_worst = min(rim_worst, own_distance)
                rim_inside += own_distance < 0
    return {'minimum_signed_distance': worst, 'vertices_deeper_than_3mm': inside,
            'cuff_minimum_signed_distance': cuff_worst, 'cuff_inside_vertices': cuff_inside,
            'cuff_own_arm_minimum_signed_distance': own_worst, 'cuff_own_arm_inside_vertices': own_inside,
            'opening_rim_minimum_signed_distance': rim_worst, 'opening_rim_inside_vertices': rim_inside,
            'opening_rim_checked_vertices': len(rim_indices),
            'cuff_checked_vertices': len(cuff_indices)}


rest = measure()
for name, offset in [('front', (0, -3, .01)), ('back', (0, 3, .01)), ('side', (3, 0, .01)), ('angle', (1.6, -3, .3))]:
    render('rest-' + name, offset)
results = []
for name in clips:
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = action.frame_range
    samples = []
    for phase in np.linspace(0, 1, 17):
        frame = start + (end - start) * phase
        scene.frame_set(int(frame), subframe=frame % 1)
        samples.append({'frame': frame, 'phase': phase, **measure()})
    worst = min(samples, key=lambda s: s['minimum_signed_distance'])
    results.append({'clip': name, 'samples': samples, 'worst': worst})
    frame = worst['frame']
    scene.frame_set(int(frame), subframe=frame % 1)
    render('pose-' + name, (1.6, -3, .3))
    if name in ['combat_idle', 'run', 'jump', 'slash1', 'sit_idle']:
        render('side-' + name, (3, 0, .15))
    print(name, worst, flush=True)
report_path = ROOT / f'doc/assets/modular-female-knight-top-fitting-{VERSION}.json'
report = json.loads(report_path.read_text())
report['review'] = {'rest': rest, 'clips': results, 'tool': f'Blender {bpy.app.version_string}',
                    'top_sha256': hashlib.sha256(TOP.read_bytes()).hexdigest(),
                    'scope': 'Clearance measured against unmasked reference; renders use recorded reversible covered-skin and upper-underwear mask. Worst sampled frames.'}
report_path.write_text(json.dumps(report, indent=2) + '\n')
