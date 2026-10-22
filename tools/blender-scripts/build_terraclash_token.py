"""Create the Terraclash shard item and icon in Blender: a granite fragment
broken from Terraclash's body, magma glowing in its cracks and the seal rune of
its chest on the face. The procedural rock is baked to 512² textures so the
GLB carries it."""
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_render import add_light, render_icon

ROOT = Path(__file__).resolve().parents[2]
SIZE = (0.21, 0.17, 0.06)
TEXTURE = 512
MAGMA = (1.0, 0.24, 0.03, 1)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 16


def node(tree, kind, location, **inputs):
    n = tree.nodes.new(kind)
    n.location = location
    for key, value in inputs.items():
        n.inputs[key].default_value = value
    return n


def shard_mesh():
    """A flattened, chipped block whose faces break along a few planes."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=SIZE, verts=bm.verts)
    # Lop off corners so the outline reads as broken rather than cut.
    for normal, offset in [
        ((1, 1, 0.3), 0.10),
        ((-1, 0.6, 0.4), 0.095),
        ((0.4, -1, 0.5), 0.075),
        ((-0.7, -0.8, -0.3), 0.085),
        ((0.9, -0.3, -0.6), 0.08),
        ((-0.2, 0.3, 1), 0.03),
    ]:
        length = math.sqrt(sum(c * c for c in normal))
        n = [c / length for c in normal]
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        cut = bmesh.ops.bisect_plane(
            bm, geom=geom, plane_co=[c * offset for c in n], plane_no=n, clear_outer=True
        )
        bmesh.ops.contextual_create(bm, geom=[e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
    mesh = bpy.data.meshes.new("TerraclashShard")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("terraclash_token", mesh)
    scene.collection.objects.link(obj)
    return obj


def roughen(obj):
    """Subdivide and displace for a rough, faceted rock surface, then thin it out."""
    sub = obj.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 5
    for name, kind, scale, strength in [("facets", "VORONOI", 0.04, 0.012), ("grain", "CLOUDS", 0.01, 0.004)]:
        tex = bpy.data.textures.new(name, kind)
        tex.noise_scale = scale
        disp = obj.modifiers.new(name, "DISPLACE")
        disp.texture = tex
        disp.texture_coords = "OBJECT"
        disp.strength = strength
        disp.mid_level = 0.5
    dec = obj.modifiers.new("dec", "DECIMATE")
    dec.ratio = 0.035
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.shade_smooth()


def rock_material():
    """Speckled dark granite, magma in the Voronoi cracks, the seal rune on top."""
    mat = bpy.data.materials.new("TerraclashShardRock")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = node(tree, "ShaderNodeOutputMaterial", (1400, 0))
    bsdf = node(tree, "ShaderNodeBsdfPrincipled", (1100, 0))
    tree.links.new(bsdf.outputs[0], out.inputs[0])
    coord = node(tree, "ShaderNodeTexCoord", (-1200, 0))
    obj_co = coord.outputs["Object"]

    # Granite: mottled base plus fine light and dark grains.
    mottle = node(tree, "ShaderNodeTexNoise", (-900, 300), Scale=14.0, Detail=10.0, Roughness=0.65)
    tree.links.new(obj_co, mottle.inputs["Vector"])
    grain = node(tree, "ShaderNodeTexVoronoi", (-900, 50), Scale=520.0, Randomness=1.0)
    tree.links.new(obj_co, grain.inputs["Vector"])
    base_ramp = node(tree, "ShaderNodeValToRGB", (-600, 300))
    base_ramp.color_ramp.elements[0].position = 0.3
    base_ramp.color_ramp.elements[0].color = (0.045, 0.034, 0.026, 1)
    base_ramp.color_ramp.elements[1].position = 0.75
    base_ramp.color_ramp.elements[1].color = (0.16, 0.12, 0.085, 1)
    tree.links.new(mottle.outputs["Fac"], base_ramp.inputs["Fac"])
    grain_ramp = node(tree, "ShaderNodeValToRGB", (-600, 50))
    grain_ramp.color_ramp.elements[0].position = 0.7
    grain_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    grain_ramp.color_ramp.elements[1].position = 0.9
    grain_ramp.color_ramp.elements[1].color = (0.55, 0.5, 0.45, 1)
    tree.links.new(grain.outputs["Distance"], grain_ramp.inputs["Fac"])
    speckle = node(tree, "ShaderNodeMix", (-300, 200))
    speckle.data_type = "RGBA"
    speckle.blend_type = "SCREEN"
    speckle.inputs["Factor"].default_value = 0.18
    tree.links.new(base_ramp.outputs["Color"], speckle.inputs["A"])
    tree.links.new(grain_ramp.outputs["Color"], speckle.inputs["B"])

    # Cracks: thin bands along Voronoi cell borders, warped by noise.
    warp = node(tree, "ShaderNodeTexNoise", (-1000, -300), Scale=6.0, Detail=4.0)
    tree.links.new(obj_co, warp.inputs["Vector"])
    warp_mix = node(tree, "ShaderNodeMix", (-800, -300))
    warp_mix.data_type = "VECTOR"
    warp_mix.inputs["Factor"].default_value = 0.14
    tree.links.new(obj_co, warp_mix.inputs["A"])
    tree.links.new(warp.outputs["Color"], warp_mix.inputs["B"])
    cells = node(tree, "ShaderNodeTexVoronoi", (-600, -300), Scale=5.5)
    cells.feature = "DISTANCE_TO_EDGE"
    tree.links.new(warp_mix.outputs["Result"], cells.inputs["Vector"])
    crack = node(tree, "ShaderNodeMapRange", (-400, -300))
    crack.inputs["From Min"].default_value = 0.0
    crack.inputs["From Max"].default_value = 0.014
    crack.inputs["To Min"].default_value = 1.0
    crack.inputs["To Max"].default_value = 0.0
    tree.links.new(cells.outputs["Distance"], crack.inputs["Value"])

    # Rune: a ring and a slanted bar, only on the upward face.
    sep = node(tree, "ShaderNodeSeparateXYZ", (-900, -700))
    tree.links.new(obj_co, sep.inputs[0])
    radius = node(tree, "ShaderNodeVectorMath", (-700, -650))
    radius.operation = "LENGTH"
    flat = node(tree, "ShaderNodeCombineXYZ", (-800, -650))
    tree.links.new(sep.outputs["X"], flat.inputs["X"])
    tree.links.new(sep.outputs["Y"], flat.inputs["Y"])
    tree.links.new(flat.outputs[0], radius.inputs[0])
    ring = node(tree, "ShaderNodeMapRange", (-500, -650))
    ring.inputs["From Min"].default_value = 0.0
    ring.inputs["From Max"].default_value = 0.006
    ring.inputs["To Min"].default_value = 1.0
    ring.inputs["To Max"].default_value = 0.0
    ring_off = node(tree, "ShaderNodeMath", (-600, -650))
    ring_off.operation = "ABSOLUTE"
    ring_sub = node(tree, "ShaderNodeMath", (-650, -600))
    ring_sub.operation = "SUBTRACT"
    ring_sub.inputs[1].default_value = 0.042
    tree.links.new(radius.outputs["Value"], ring_sub.inputs[0])
    tree.links.new(ring_sub.outputs[0], ring_off.inputs[0])
    tree.links.new(ring_off.outputs[0], ring.inputs["Value"])
    # Bar along a line tilted 12° from +Y: distance is |x cos - y sin|.
    tilt = math.radians(12)
    bx = node(tree, "ShaderNodeMath", (-700, -850), **{})
    bx.operation = "MULTIPLY"
    bx.inputs[1].default_value = math.cos(tilt)
    tree.links.new(sep.outputs["X"], bx.inputs[0])
    by = node(tree, "ShaderNodeMath", (-700, -900))
    by.operation = "MULTIPLY"
    by.inputs[1].default_value = math.sin(tilt)
    tree.links.new(sep.outputs["Y"], by.inputs[0])
    bd = node(tree, "ShaderNodeMath", (-550, -870))
    bd.operation = "SUBTRACT"
    tree.links.new(bx.outputs[0], bd.inputs[0])
    tree.links.new(by.outputs[0], bd.inputs[1])
    babs = node(tree, "ShaderNodeMath", (-450, -870))
    babs.operation = "ABSOLUTE"
    tree.links.new(bd.outputs[0], babs.inputs[0])
    bar = node(tree, "ShaderNodeMapRange", (-350, -870))
    bar.inputs["From Min"].default_value = 0.0
    bar.inputs["From Max"].default_value = 0.005
    bar.inputs["To Min"].default_value = 1.0
    bar.inputs["To Max"].default_value = 0.0
    tree.links.new(babs.outputs[0], bar.inputs["Value"])
    bar_len = node(tree, "ShaderNodeMapRange", (-350, -1000))
    bar_len.inputs["From Min"].default_value = 0.058
    bar_len.inputs["From Max"].default_value = 0.064
    bar_len.inputs["To Min"].default_value = 1.0
    bar_len.inputs["To Max"].default_value = 0.0
    tree.links.new(radius.outputs["Value"], bar_len.inputs["Value"])
    bar_cut = node(tree, "ShaderNodeMath", (-200, -900))
    bar_cut.operation = "MULTIPLY"
    tree.links.new(bar.outputs[0], bar_cut.inputs[0])
    tree.links.new(bar_len.outputs[0], bar_cut.inputs[1])
    rune = node(tree, "ShaderNodeMath", (-100, -700))
    rune.operation = "MAXIMUM"
    tree.links.new(ring.outputs[0], rune.inputs[0])
    tree.links.new(bar_cut.outputs[0], rune.inputs[1])
    up = node(tree, "ShaderNodeSeparateXYZ", (-300, -500))
    geo = node(tree, "ShaderNodeNewGeometry", (-500, -500))
    tree.links.new(geo.outputs["Normal"], up.inputs[0])
    up_mask = node(tree, "ShaderNodeMapRange", (-150, -500))
    up_mask.inputs["From Min"].default_value = 0.6
    up_mask.inputs["From Max"].default_value = 0.85
    tree.links.new(up.outputs["Z"], up_mask.inputs["Value"])
    rune_top = node(tree, "ShaderNodeMath", (50, -650))
    rune_top.operation = "MULTIPLY"
    tree.links.new(rune.outputs[0], rune_top.inputs[0])
    tree.links.new(up_mask.outputs[0], rune_top.inputs[1])

    glow = node(tree, "ShaderNodeMath", (200, -400))
    glow.operation = "MAXIMUM"
    tree.links.new(crack.outputs[0], glow.inputs[0])
    tree.links.new(rune_top.outputs[0], glow.inputs[1])

    color = node(tree, "ShaderNodeMix", (500, 200))
    color.data_type = "RGBA"
    color.inputs["B"].default_value = (0.25, 0.035, 0.005, 1)
    tree.links.new(glow.outputs[0], color.inputs["Factor"])
    # Scorched rock along each crack.
    scorch = node(tree, "ShaderNodeMapRange", (200, 0))
    scorch.inputs["From Min"].default_value = 0.0
    scorch.inputs["From Max"].default_value = 0.04
    scorch.inputs["To Min"].default_value = 0.8
    scorch.inputs["To Max"].default_value = 0.0
    tree.links.new(cells.outputs["Distance"], scorch.inputs["Value"])
    charred = node(tree, "ShaderNodeMix", (350, 150))
    charred.data_type = "RGBA"
    charred.inputs["B"].default_value = (0.012, 0.008, 0.006, 1)
    tree.links.new(scorch.outputs["Result"], charred.inputs["Factor"])
    tree.links.new(speckle.outputs["Result"], charred.inputs["A"])
    tree.links.new(charred.outputs["Result"], color.inputs["A"])
    tree.links.new(color.outputs["Result"], bsdf.inputs["Base Color"])

    rough = node(tree, "ShaderNodeMapRange", (500, -50))
    rough.inputs["To Min"].default_value = 0.92
    rough.inputs["To Max"].default_value = 0.55
    tree.links.new(glow.outputs[0], rough.inputs["Value"])
    tree.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])

    bsdf.inputs["Emission Color"].default_value = MAGMA
    tree.links.new(glow.outputs[0], bsdf.inputs["Emission Strength"])

    # Cracks and the rune sit sunk below the rock; grain gives the bump.
    height = node(tree, "ShaderNodeMath", (500, -250))
    height.operation = "SUBTRACT"
    tree.links.new(mottle.outputs["Fac"], height.inputs[0])
    tree.links.new(glow.outputs[0], height.inputs[1])
    bump = node(tree, "ShaderNodeBump", (800, -250), Strength=0.6, Distance=0.002)
    tree.links.new(height.outputs[0], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def bake(obj, mat):
    """Bake colour, roughness, normal and glow, then rewire the material to the images."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    images = {}
    for name, kind, colorspace in [
        ("color", "DIFFUSE", "sRGB"),
        ("roughness", "ROUGHNESS", "Non-Color"),
        ("normal", "NORMAL", "Non-Color"),
        ("emission", "EMIT", "sRGB"),
    ]:
        img = bpy.data.images.new(f"terraclash_shard_{name}", TEXTURE, TEXTURE)
        img.colorspace_settings.name = colorspace
        target = tree.nodes.new("ShaderNodeTexImage")
        target.image = img
        tree.nodes.active = target
        bake = scene.render.bake
        bake.use_pass_direct = bake.use_pass_indirect = False
        bake.use_pass_color = True
        bake.margin = 8
        bpy.ops.object.bake(type=kind)
        img.pack()
        images[name] = img
        tree.nodes.remove(target)

    tree.nodes.clear()
    out = node(tree, "ShaderNodeOutputMaterial", (600, 0))
    bsdf = node(tree, "ShaderNodeBsdfPrincipled", (300, 0))
    tree.links.new(bsdf.outputs[0], out.inputs[0])

    def image(name, y):
        n = tree.nodes.new("ShaderNodeTexImage")
        n.image = images[name]
        n.location = (-300, y)
        return n

    tree.links.new(image("color", 300).outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(image("roughness", 0).outputs["Color"], bsdf.inputs["Roughness"])
    normal_map = node(tree, "ShaderNodeNormalMap", (0, -300))
    tree.links.new(image("normal", -300).outputs["Color"], normal_map.inputs["Color"])
    tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    tree.links.new(image("emission", -600).outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0


shard = shard_mesh()
roughen(shard)
material = rock_material()
shard.data.materials.append(material)
bake(shard, material)

lowest = min(v.co.z for v in shard.data.vertices)
for v in shard.data.vertices:
    v.co.z -= lowest

source = ROOT / "assets/items/terraclash_token"
source.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(source / "terraclash_token.blend"))
for obj in scene.objects:
    obj.select_set(obj is shard)
bpy.ops.export_scene.gltf(
    filepath=str(ROOT / "client/public/models/objects/terraclash_token.glb"),
    export_format="GLB",
    use_selection=True,
    export_image_format="WEBP",
    export_image_quality=90,
)

world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.3, 1)
scene.world = world
add_light((0, 0, 2), 30, 1)
add_light((-1, 1, 1), 25, 1)
icon = ROOT / "client/public/items/objects/terraclash_token.png"
render_icon([shard], str(icon), (math.radians(-38), 0, math.radians(-8)), 1.08)
