"""Create the Terraclash token item and icon in Blender: a granite chip with
the seal rune of Terraclash's chest glowing in magma orange."""
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_render import add_light, export_glb, principled, render_icon

ROOT = Path(__file__).resolve().parents[2]
RADIUS = 0.04
THICKNESS = 0.016

bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(7)
granite = principled("TokenGranite", (0.13, 0.09, 0.065, 1), 0.88)
magma = principled("TokenMagma", (1.0, 0.22, 0.02, 1), 0.5)
bsdf = magma.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Emission Color"].default_value = (1.0, 0.22, 0.02, 1)
bsdf.inputs["Emission Strength"].default_value = 1.6

# Uneven rim and a chipped underside, but a flat top so the rune sits flush.
bm = bmesh.new()
sides = 9
top, bottom = [], []
for i in range(sides):
    t = i / sides * math.tau + random.uniform(-0.15, 0.15)
    r = RADIUS * random.uniform(0.82, 1.0)
    top.append(bm.verts.new((r * math.cos(t), r * math.sin(t), THICKNESS)))
    rb = r * random.uniform(0.78, 0.9)
    z = random.uniform(0.0, 0.004)
    bottom.append(bm.verts.new((rb * math.cos(t), rb * math.sin(t), z)))
bm.faces.new(top)
bm.faces.new(list(reversed(bottom)))
for i in range(sides):
    j = (i + 1) % sides
    bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.002, segments=1, affect="EDGES")
mesh = bpy.data.meshes.new("TokenStone")
bm.to_mesh(mesh)
bm.free()
mesh.materials.append(granite)
stone = bpy.data.objects.new("TokenStone", mesh)
bpy.context.collection.objects.link(stone)
lowest = min(v.co.z for v in mesh.vertices)
top_z = max(v.co.z for v in mesh.vertices)

bpy.ops.mesh.primitive_torus_add(
    major_radius=RADIUS * 0.45,
    minor_radius=0.0024,
    major_segments=40,
    minor_segments=8,
    location=(0, 0, top_z),
)
ring = bpy.context.object
ring.scale.z = 0.5
ring.data.materials.append(magma)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, top_z), rotation=(0, 0, math.radians(-12)))
bar = bpy.context.object
bar.scale = (0.0042, RADIUS * 1.2, 0.0024)
bar.data.materials.append(magma)

objects = [stone, ring, bar]
for obj in objects:
    obj.location.z -= lowest
    obj.select_set(True)
bpy.context.view_layer.objects.active = stone
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
token = bpy.context.object
token.name = "terraclash_token"

source = ROOT / "assets/items/terraclash_token"
source.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(source / "terraclash_token.blend"))
export_glb([token], str(ROOT / "client/public/models/objects/terraclash_token.glb"))

world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.3, 1)
bpy.context.scene.world = world
add_light((0, 0, 2), 30, 1)
add_light((-1, 1, 1), 25, 1)
icon = ROOT / "client/public/items/objects/terraclash_token.png"
render_icon([token], str(icon), (math.radians(-38), 0, math.radians(-8)), 1.12)
