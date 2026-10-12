import hashlib
import importlib.util
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/modular_human_female_01/hair/tripo_knight_v1/model_url.glb'
REFERENCE = ROOT / 'doc/images/characters/modular_human_female_01/parts/knight/hair_female_knight-back-v1.png'
OUTPUT = SOURCE.parent / 'rear_filled_v1'
OUTPUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
originals = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
image = bpy.data.images.load(str(REFERENCE))
width, height = image.size
source_points, source_faces = [], []
for obj in originals:
    start = len(source_points)
    source_points.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
    source_faces.extend(tuple(start + i for i in poly.vertices) for poly in obj.data.polygons)
surface = BVHTree.FromPolygons(source_points, source_faces)
rows, columns = 37, 29
levels = np.array([-.48, -.4, -.3, -.2, -.1, 0, .1, .2, .3, .4, .45, .48, .498])
depths = np.array([-.025, -.095, -.135, -.165, -.187, -.192, -.188, -.205, -.215, -.205, -.183, -.13, -.035])
edge_depths = np.array([-.01, -.03, -.025, -.035, -.07, -.08, -.048, -.032, -.07, -.13, -.145, -.11, -.035])
halves = np.array([.04, .14, .2, .23, .224, .19, .173, .17, .158, .135, .102, .071, .006])
vertices, uvs, faces = [], [], []
for row in range(rows):
    t = row / (rows - 1)
    base_z = .498 - .95 * t
    half = float(np.interp(base_z, levels, halves))
    py = 38 + t * 1062
    uv_half = float(np.interp(py, [38, 160, 300, 500, 800, 1000, 1100], [65, 180, 220, 215, 280, 295, 260]))
    left, right = 510 - uv_half, 510 + uv_half
    rear = float(np.interp(base_z, levels, depths))
    edge = float(np.interp(base_z, levels, edge_depths))
    for column in range(columns):
        s = -1 + 2 * column / (columns - 1)
        end_shape = .070 * math.sin(1.5 * math.pi * s) ** 2
        z = base_z + end_shape * max(0, (t - .8) / .2) ** 2
        y = s * half
        curve = math.sqrt(max(0, 1 - s * s))
        relief = .004 * math.cos(s * math.pi * 5 + math.sin(t * math.pi * 3))
        relief *= math.sin(math.pi * t) * (1 - s * s)
        x = edge + (rear - edge) * curve - relief
        hit = surface.ray_cast(Vector((-1, y, z)), Vector((1, 0, 0)))[0]
        if hit is not None and z > .415:
            x = min(x, float(hit.x) - .003)
        vertices.append((x, y, z))
        px = left + (s + 1) / 2 * (right - left)
        uvs.append(((px + .5) / width, 1 - (py + .5) / height))
        if row and column:
            a = row * columns + column
            faces.append((a - columns - 1, a - columns, a, a - 1))
mesh = bpy.data.meshes.new('Rear crown and curtain')
mesh.from_pydata(vertices, [], faces)
mesh.update()
uv = mesh.uv_layers.new(name='Rear reference projection')
for polygon in mesh.polygons:
    polygon.use_smooth = True
    for loop in polygon.loop_indices:
        uv.data[loop].uv = uvs[mesh.loops[loop].vertex_index]
patch = bpy.data.objects.new('hair_knight_rear_fill', mesh)
bpy.context.collection.objects.link(patch)
material = bpy.data.materials.new('Blonde rear hair')
material.use_nodes = True
shader = material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Roughness'].default_value = .6
texture = material.node_tree.nodes.new('ShaderNodeTexImage')
texture.image = image
material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
mesh.materials.append(material)
bpy.ops.object.select_all(action='DESELECT')
patch.select_set(True)
bpy.context.view_layer.objects.active = patch
nodes, links = material.node_tree.nodes, material.node_tree.links
coordinates = nodes.new('ShaderNodeTexCoord')
stretch = nodes.new('ShaderNodeVectorMath')
stretch.operation = 'MULTIPLY'
stretch.inputs[1].default_value = (1, .008, 1)
links.new(coordinates.outputs['UV'], stretch.inputs[0])
grain = nodes.new('ShaderNodeTexNoise')
grain.inputs['Scale'].default_value = 850
grain.inputs['Detail'].default_value = 2
links.new(stretch.outputs['Vector'], grain.inputs['Vector'])
bump = nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = .22
bump.inputs['Distance'].default_value = .001
links.new(grain.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], shader.inputs['Normal'])
normal_image = bpy.data.images.new('Rear fine strand normal', width=2048, height=2048)
normal_image.colorspace_settings.name = 'Non-Color'
baked = nodes.new('ShaderNodeTexImage')
baked.image = normal_image
nodes.active = baked
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 8
bpy.ops.object.bake(type='NORMAL', margin=8, use_clear=True)
normal_image.filepath_raw = str(OUTPUT / 'rear-strand-normal.png')
normal_image.file_format = 'PNG'
normal_image.save()
normal = nodes.new('ShaderNodeNormalMap')
links.new(baked.outputs['Color'], normal.inputs['Color'])
links.new(normal.outputs['Normal'], shader.inputs['Normal'])
for node in [coordinates, stretch, grain, bump]:
    nodes.remove(node)
for obj in originals:
    obj.select_set(True)
target = OUTPUT / 'hair_female_knight-rear-filled-v1.glb'
bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'hair_female_knight-rear-filled-v1.blend'))
spec = importlib.util.spec_from_file_location('review', ROOT / 'tools/blender-scripts/review_outfit_sources.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
report, low, high = review.diagnostics(originals + [patch])
report.update(date='2026-10-12', source=str(SOURCE.relative_to(ROOT)),
              source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              reference=str(REFERENCE.relative_to(ROOT)), reference_sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
              method='Add curved rear crown and continuous hair curtain with shallow lock relief, projected rear concept UVs, with a double-sided hair surface and baked fine-strand tangent normals. Original meshes unchanged.',
              status='Local repair candidate; not fitted or rigged', extra_api_credits=0)
(ROOT / 'doc/assets/modular-female-knight-hair-rear-filled-v1.json').write_text(json.dumps(report, indent=2) + '\n')
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new('Review world')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .18, .18, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .7
for location, energy in [((3, -3, 3), 230), ((3, 3, 1), 160), ((-3, 0, 2), 200)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    light = bpy.context.object
    light.data.energy, light.data.size = energy, 3
    light.rotation_euler = (-light.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type, camera.data.ortho_scale = 'ORTHO', 1.22
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 600, 800
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
for name, offset in [('front', (4, 0, 0)), ('side', (0, 4, 0)), ('back', (-4, 0, 0)), ('angle', (-4, 3, 1)), ('top', (0, 0, 4))]:
    camera.location = Vector(offset)
    camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUTPUT / f'{name}.png')
    bpy.ops.render.render(write_still=True)
print(json.dumps(report), flush=True)
