"""Build Ysolde's small excavation trowel in metres."""
import json
import math
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/items/excavation_trowel'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1


def material(name, color, metal, roughness, wood=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = roughness
    rng = np.random.default_rng(1024 if wood else 2401)
    y, x = np.mgrid[0:256, 0:256] / 256
    grain = np.sin((y * 45 + .3 * np.sin(x * 12)) * math.tau) ** 10
    shade = .88 + rng.normal(0, .035, x.shape) - grain * (.26 if wood else .08)
    pixels = np.ones((256, 256, 4), dtype=np.float32)
    pixels[:, :, :3] = np.clip(shade[:, :, None] * np.array(color), 0, 1)
    image = bpy.data.images.new(name + 'Albedo', width=256, height=256)
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    mat.node_tree.links.new(tex.outputs['Color'], shader.inputs['Base Color'])
    return mat


wood = material('Worn walnut handle', (.24, .12, .052), 0, .72, True)
iron = material('Soil stained forged steel', (.23, .25, .23), .72, .59)
brass = material('Aged ferrule', (.28, .19, .075), .65, .5)
parts = []


def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    parts.append(obj)
    return obj


def lathe(name, profile, mat, sides=20):
    vertices = [(along, r * math.cos(j * math.tau / sides), r * math.sin(j * math.tau / sides)) for along, r in profile for j in range(sides)]
    faces = []
    for i in range(len(profile) - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces += [tuple(reversed(range(sides))), tuple((len(profile) - 1) * sides + j for j in range(sides))]
    obj = mesh(name, vertices, faces, mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


lathe('Carved wooden grip', [(-.078, .008), (-.072, .016), (-.055, .019), (.025, .017), (.059, .013), (.066, .011)], wood)
lathe('Steel tang', [(.055, .007), (.091, .007), (.111, .004)], iron, 12)
lathe('Handle ferrule', [(.049, .014), (.052, .0145), (.066, .012), (.07, .011)], brass, 16)
rows = [(.09, .008), (.115, .027), (.16, .036), (.205, .028), (.23, .010), (.24, .001)]
vertices = []
for x, width in rows:
    for side in [-1, 0, 1]:
        vertices.append((x, side * width, .005 + abs(side) * .009))
for x, width in rows:
    for side in [-1, 0, 1]:
        vertices.append((x, side * width, .002 + abs(side) * .009))
faces = []
n = len(rows) * 3
for layer in [0, n]:
    for row in range(len(rows) - 1):
        for side in range(2):
            a = layer + row * 3 + side
            face = (a, a + 1, a + 4, a + 3)
            faces.append(face if layer == 0 else tuple(reversed(face)))
edge = [i * 3 for i in range(len(rows))] + [n - 2, n - 1] + [i * 3 + 2 for i in reversed(range(len(rows) - 1))] + [1]
for a, b in zip(edge, edge[1:] + edge[:1]):
    faces.append((a, b, b + n, a + n))
blade = mesh('Concave pointed spade', vertices, faces, iron)
bevel = blade.modifiers.new('Forged rounded edges', 'BEVEL')
bevel.width = .0008
bevel.segments = 2
bpy.context.view_layer.objects.active = blade
bpy.ops.object.modifier_apply(modifier=bevel.name)
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'excavation_trowel.blend'))
runtime = ROOT / 'client/public/models/props/excavation_trowel.glb'
runtime.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(runtime), export_format='GLB', use_selection=True, export_animations=False, export_extras=True)
triangles = sum(len(p.vertices) - 2 for obj in parts for p in obj.data.polygons)
record = {'date': '2026-10-24', 'source': 'Original procedural Blender geometry and NumPy-generated textures', 'license': 'Project-authored asset; repository license', 'tool': bpy.app.version_string, 'tier': 'Local Blender; no paid generation', 'size_m': [.318, .072, .038], 'triangles': triangles, 'texture_resolution': 256, 'runtime': str(runtime.relative_to(ROOT)), 'bytes': runtime.stat().st_size}
(OUT / 'provenance.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
