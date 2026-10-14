import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb
from lib.glb_accessors import accessor

BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
OUTPUT = DIRECTORY / 'review'
OUTPUT.mkdir(exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
body = bpy.data.objects['female_body']
# The mask indexes glTF triangles; Blender reorders faces, so match them by centroid.
doc, binary = read_glb(BODY)
primitive = doc['meshes'][0]['primitives'][0]
positions = accessor(doc, binary, primitive['attributes']['POSITION'])
triangles = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
hide = json.loads((DIRECTORY / 'body-occlusion.json').read_text())['hide_triangle_indices']
centers = positions[triangles[hide]].mean(1)
edit = bmesh.new()
edit.from_mesh(body.data)
tree = KDTree(len(edit.faces))
for face in edit.faces:
    center = body.matrix_world @ face.calc_center_median()
    tree.insert((center.x, center.z, -center.y), face.index)
tree.balance()
edit.faces.ensure_lookup_table()
matched = {tree.find(center)[1] for center in centers}
assert len(matched) == len(hide)
bmesh.ops.delete(edit, geom=[edit.faces[i] for i in matched], context='FACES')
edit.to_mesh(body.data)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(DIRECTORY / 'bottom_female_barbarian.glb'), bone_heuristic='TEMPERANCE')
for obj in set(bpy.data.objects) - before:
    if obj.type == 'MESH':
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.12, .14, .16, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
center = Vector((0, .01, .50))
for offset, power in [((1.5, -2, 1.5), 60), ((-2, -1, 1), 35), ((0, 2.5, 1.5), 45)]:
    bpy.ops.object.light_add(type='AREA', location=center + Vector(offset))
    light = bpy.context.object
    light.data.energy = power
    light.data.size = 2
    light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .42
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 800
scene.view_settings.view_transform = 'AgX'
for view, offset in [('front', (0, -1, 0)), ('left', (1, 0, 0)), ('back', (0, 1, 0)), ('angle', (-.7, -.7, .15)),
                     ('below', (0, -.5, -.85))]:
    camera.location = center + Vector(offset)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUTPUT / f'{view}.png')
    bpy.ops.render.render(write_still=True)
