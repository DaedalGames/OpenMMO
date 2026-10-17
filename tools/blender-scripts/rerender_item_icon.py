"""Re-render an item icon from its shipped GLB with the export_item_asset.py recipe.

    blender -b --python-exit-code 1 -P tools/blender-scripts/rerender_item_icon.py -- \
        --name barbarian_bracers --category armor --icon-rotation -65 -8 -12 \
        --exposure -1.2 --keep-side +x
"""

import argparse
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_render import add_light, render_icon

REPO = Path(__file__).resolve().parents[2]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--name", required=True)
parser.add_argument("--category", default="objects")
parser.add_argument("--icon-rotation", type=float, nargs=3, default=(28, -8, -12),
                    metavar=("X", "Y", "Z"))
parser.add_argument("--turn", type=float, default=0,
                    help="degrees about the vertical axis, applied before --icon-rotation")
parser.add_argument("--exposure", type=float, default=0)
parser.add_argument("--keep-side", choices=("+x", "-x"),
                    help="drop geometry on the other side of X=0, for paired items")
parser.add_argument("--out", type=Path, help="icon path; defaults to the shipped icon")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(REPO / f"client/public/models/{args.category}/{args.name}.glb"))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if args.keep_side:
    sign = 1 if args.keep_side == "+x" else -1
    for obj in meshes:
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        mesh.transform(obj.matrix_world)
        doomed = [v for v in mesh.verts if v.co.x * sign < 0]
        mesh.transform(obj.matrix_world.inverted())
        bmesh.ops.delete(mesh, geom=doomed, context="VERTS")
        mesh.to_mesh(obj.data)
        mesh.free()
turn = Matrix.Rotation(math.radians(args.turn), 4, "Z")
for obj in meshes:
    obj.matrix_world = turn @ obj.matrix_world
bpy.context.view_layer.update()
size =max(max(obj.dimensions) for obj in meshes)
for obj in meshes:
    obj.scale = tuple(s * 0.5 / size for s in obj.scale)
    obj.location = obj.location * (0.5 / size)

for location, energy in (
    ((0.7, -0.9, 1.1), 45),
    ((-1.0, -0.6, 0.4), 14),
    ((-0.4, 1.0, 0.8), 22),
):
    add_light(location, energy, 1.5)
scene = bpy.context.scene
scene.world = bpy.data.worlds.new("IconWorld")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes["Background"]
background.inputs["Color"].default_value = (0.55, 0.57, 0.62, 1)
background.inputs["Strength"].default_value = 1.2
scene.view_settings.exposure = args.exposure
out = args.out or REPO / f"client/public/items/{args.category}/{args.name}.png"
render_icon(meshes, str(out), tuple(math.radians(a) for a in args.icon_rotation), margin=1.10)
