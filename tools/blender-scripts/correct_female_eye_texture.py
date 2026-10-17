# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
"""Project an edited eye reference onto the existing female character UVs."""
from pathlib import Path
import argparse
import json
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/modular_human_female_01/eyes_v1'
SOURCE = ROOT / 'assets/modular_human_female_01/tripo_api_v1/base-review.glb'
VERSION = 'v1'
PROJECTION = (-.12, .78, .24)
EYE_CENTERS = [(433 / 1024, 366 / 1024), (584 / 1024, 363 / 1024)]
EYE_RADIUS = (49 / 1024, 29 / 1024)
NORMAL_ATTENUATION = .85


def export_texture_only_glb():
    data = SOURCE.read_bytes()
    json_size = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + json_size])
    binary = data[28 + json_size:]
    material = document['materials'][0]
    replacements = {}
    textures = [
        (material['pbrMetallicRoughness']['baseColorTexture']['index'], OUT / f'base-color-eyes-{VERSION}.png'),
    ]
    if NORMAL_ATTENUATION:
        textures.append((material['normalTexture']['index'], OUT / f'normal-eyes-{VERSION}.png'))
    for index, path in textures:
        image = document['images'][document['textures'][index]['source']]
        replacements[image['bufferView']] = path.read_bytes()
        image['mimeType'] = 'image/png'
    packed = bytearray()
    for index, view in enumerate(document['bufferViews']):
        offset = view.get('byteOffset', 0)
        payload = replacements.get(index, binary[offset:offset + view['byteLength']])
        packed.extend(b'\0' * (-len(packed) % 4))
        view['byteOffset'], view['byteLength'] = len(packed), len(payload)
        packed.extend(payload)
    document['buffers'][0]['byteLength'] = len(packed)
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    packed.extend(b'\0' * (-len(packed) % 4))
    result = struct.pack('<III', 0x46546C67, 2, 28 + len(encoded) + len(packed))
    result += struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
    result += struct.pack('<II', len(packed), 0x004E4942) + packed
    (OUT / f'base-eyes-{VERSION}.glb').write_bytes(result)


def project_eyes(body):
    material = body.data.materials[0]
    shader = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    original_node = shader.inputs['Base Color'].links[0].from_node
    original = original_node.image
    target = bpy.data.images.new('Female base color - eyes corrected', *original.size, alpha=False)
    pixels = np.empty(len(original.pixels), dtype=np.float32)
    original.pixels.foreach_get(pixels)
    target.pixels.foreach_set(pixels)
    target.filepath_raw = str(OUT / f'base-color-eyes-{VERSION}.png')
    target.file_format = 'PNG'
    patch = body.copy()
    patch.data = body.data.copy()
    bpy.context.collection.objects.link(patch)
    bm = bmesh.new()
    bm.from_mesh(patch.data)
    remove = []
    for face in bm.faces:
        center = body.matrix_world @ face.calc_center_median()
        if face.material_index != 0 or not (abs(center.x) < .042 and .912 < center.z < .959 and center.y < -.02):
            remove.append(face)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bm.to_mesh(patch.data)
    bm.free()
    projection = patch.data.uv_layers.new(name='EyeProjection')
    for loop in patch.data.loops:
        point = patch.matrix_world @ patch.data.vertices[loop.vertex_index].co
        projection.data[loop.index].uv = ((point.x - PROJECTION[0]) / PROJECTION[2], (point.z - PROJECTION[1]) / PROJECTION[2])
    patch.data.uv_layers.active_index = 0
    patch.data.uv_layers[0].active_render = True
    paint = material.copy()
    patch.data.materials.clear()
    patch.data.materials.append(paint)
    nodes, links = paint.node_tree.nodes, paint.node_tree.links
    nodes.clear()

    def math_node(operation, a, b=None):
        node = nodes.new('ShaderNodeMath')
        node.operation = operation
        for index, value in enumerate([a, b]):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    position = nodes.new('ShaderNodeUVMap')
    position.uv_map = 'EyeProjection'
    xyz = nodes.new('ShaderNodeSeparateXYZ')
    links.new(position.outputs['UV'], xyz.inputs[0])
    u = xyz.outputs['X']
    v = xyz.outputs['Y']
    uv = nodes.new('ShaderNodeCombineXYZ')
    links.new(u, uv.inputs['X'])
    lower_band = None
    if VERSION == 'v6':
        right_eye = math_node('GREATER_THAN', u, .5)
        center = math_node('ADD', EYE_CENTERS[0][0],
                           math_node('MULTIPLY', right_eye, EYE_CENTERS[1][0] - EYE_CENTERS[0][0]))
        sample_u = math_node('ADD', center, math_node('DIVIDE', math_node('SUBTRACT', u, center), 1.08))
        anchor = (.939 - PROJECTION[1]) / PROJECTION[2]
        shifted_v = math_node('ADD', v, .00085 / PROJECTION[2])
        sample_v = math_node('ADD', anchor, math_node('DIVIDE', math_node('SUBTRACT', shifted_v, anchor), 1.05))
        links.new(sample_u, uv.inputs['X'])
        links.new(sample_v, uv.inputs['Y'])
    elif VERSION == 'v5':
        ramps = []
        for start, end, low, high in [(.9305, .932, 0, 1), (.934, .9355, 1, 0)]:
            ramp = nodes.new('ShaderNodeMapRange')
            ramp.interpolation_type = 'SMOOTHSTEP'
            ramp.clamp = True
            links.new(v, ramp.inputs['Value'])
            ramp.inputs['From Min'].default_value = (start - PROJECTION[1]) / PROJECTION[2]
            ramp.inputs['From Max'].default_value = (end - PROJECTION[1]) / PROJECTION[2]
            ramp.inputs['To Min'].default_value = low
            ramp.inputs['To Max'].default_value = high
            ramps.append(ramp.outputs[0])
        lower_band = math_node('MULTIPLY', *ramps)
        displacement = math_node('MULTIPLY', lower_band, .00065 / PROJECTION[2])
        links.new(math_node('ADD', v, displacement), uv.inputs['Y'])
    elif VERSION == 'v4':
        shift = nodes.new('ShaderNodeMapRange')
        shift.interpolation_type = 'SMOOTHSTEP'
        shift.clamp = True
        links.new(v, shift.inputs['Value'])
        shift.inputs['From Min'].default_value = (.933 - PROJECTION[1]) / PROJECTION[2]
        shift.inputs['From Max'].default_value = (.938 - PROJECTION[1]) / PROJECTION[2]
        shift.inputs['To Min'].default_value = 0
        shift.inputs['To Max'].default_value = .0009 / PROJECTION[2]
        links.new(math_node('ADD', v, shift.outputs[0]), uv.inputs['Y'])
    else:
        links.new(v, uv.inputs['Y'])
    edited = nodes.new('ShaderNodeTexImage')
    image_path = (ROOT / 'assets/modular_human_female_01/eyes_v3/face-albedo-edited.png'
                  if VERSION == 'v6' else OUT / ('face-albedo-front.png' if VERSION in ('v4', 'v5') else 'face-albedo-edited.png'))
    edited.image = bpy.data.images.load(str(image_path))
    edited.extension = 'EXTEND'
    links.new(uv.outputs[0], edited.inputs['Vector'])
    source = nodes.new('ShaderNodeTexImage')
    source.image = original
    masks = []
    for x, y in EYE_CENTERS:
        dx = math_node('DIVIDE', math_node('SUBTRACT', u, x), EYE_RADIUS[0])
        dy = math_node('DIVIDE', math_node('SUBTRACT', v, 1 - y), EYE_RADIUS[1])
        radius = math_node('SQRT', math_node('ADD', math_node('MULTIPLY', dx, dx), math_node('MULTIPLY', dy, dy)))
        fade = nodes.new('ShaderNodeMapRange')
        fade.interpolation_type = 'SMOOTHERSTEP'
        fade.clamp = True
        links.new(radius, fade.inputs['Value'])
        fade.inputs['From Min'].default_value = .85 if VERSION == 'v6' else .65
        fade.inputs['From Max'].default_value = 1
        fade.inputs['To Min'].default_value = 1
        fade.inputs['To Max'].default_value = 0
        masks.append(fade.outputs[0])
    mix = nodes.new('ShaderNodeMixRGB')
    mask = math_node('MAXIMUM', *masks)
    if lower_band is not None:
        mask = math_node('MULTIPLY', mask, lower_band)
    links.new(mask, mix.inputs[0])
    links.new(source.outputs['Color'], mix.inputs[1])
    links.new(edited.outputs['Color'], mix.inputs[2])
    emission = nodes.new('ShaderNodeEmission')
    links.new(mix.outputs[0], emission.inputs['Color'])
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(emission.outputs[0], output.inputs['Surface'])
    destination = nodes.new('ShaderNodeTexImage')
    destination.image = target
    nodes.active = destination
    bpy.ops.object.select_all(action='DESELECT')
    patch.select_set(True)
    bpy.context.view_layer.objects.active = patch
    bpy.context.scene.render.bake.use_clear = False
    bpy.context.scene.render.bake.margin = 4
    bpy.context.scene.render.bake.margin_type = 'EXTEND'
    bpy.ops.object.bake(type='EMIT')
    target.save()
    target.pack()
    original_node.image = target
    normal_map = shader.inputs['Normal'].links[0].from_node
    normal_node = normal_map.inputs['Color'].links[0].from_node
    normal_original = normal_node.image
    normal_target = bpy.data.images.new('Female eye normals corrected', *normal_original.size, alpha=False)
    normal_target.colorspace_settings.name = 'Non-Color'
    normal_pixels = np.empty(len(normal_original.pixels), dtype=np.float32)
    normal_original.pixels.foreach_get(normal_pixels)
    normal_target.pixels.foreach_set(normal_pixels)
    normal_target.filepath_raw = str(OUT / f'normal-eyes-{VERSION}.png')
    normal_target.file_format = 'PNG'
    source.image = normal_original
    links.remove(mix.inputs[2].links[0])
    mix.inputs[2].default_value = (.5, .5, 1, 1)
    links.new(math_node('MULTIPLY', mask, NORMAL_ATTENUATION), mix.inputs[0])
    destination.image = normal_target
    bpy.ops.object.bake(type='EMIT')
    normal_target.save()
    normal_target.pack()
    normal_node.image = normal_target
    mask_target = bpy.data.images.new('Eye edit support', *original.size, alpha=False)
    mask_target.colorspace_settings.name = 'Non-Color'
    destination.image = mask_target
    links.new(mask, emission.inputs['Color'])
    bpy.context.scene.render.bake.use_clear = True
    bpy.ops.object.bake(type='EMIT')
    mask_pixels = np.empty(len(mask_target.pixels), dtype=np.float32)
    mask_target.pixels.foreach_get(mask_pixels)
    outside = mask_pixels.reshape(-1, 4)[:, 0] <= 1e-5
    for before, after in [(original, target), (normal_original, normal_target)]:
        old = np.empty(len(before.pixels), dtype=np.float32)
        new = np.empty(len(after.pixels), dtype=np.float32)
        before.pixels.foreach_get(old)
        after.pixels.foreach_get(new)
        new.reshape(-1, 4)[outside] = old.reshape(-1, 4)[outside]
        after.pixels.foreach_set(new)
        after.save()
        after.pack()
    mask_target.filepath_raw = str(OUT / 'eye-support-mask.png')
    mask_target.file_format = 'PNG'
    mask_target.save()
    bpy.data.objects.remove(patch, do_unlink=True)


def main():
    global OUT, SOURCE, VERSION, PROJECTION, EYE_CENTERS, EYE_RADIUS, NORMAL_ATTENUATION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v1', 'v2', 'v3', 'v4', 'v5', 'v6'], default='v1')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    VERSION = args.version
    if VERSION == 'v2':
        parser.error('V2 input image was removed; use v3 or v6 with the retained image.')
    if VERSION in ('v2', 'v3', 'v4', 'v5', 'v6'):
        OUT = ROOT / f'assets/modular_human_female_01/eyes_{VERSION}'
        SOURCE = ROOT / 'assets/modular_human_female_01/eyelashes_v5/base-eyelashes-v5.glb'
        PROJECTION = (-.06, .873, .12)
        EYE_CENTERS = [(727 / 2048, 963 / 2048), (1340 / 2048, 960 / 2048)]
        EYE_RADIUS = (190 / 2048, 115 / 2048)
    if VERSION == 'v3':
        SOURCE = ROOT / 'assets/modular_human_female_01/eyelashes_v6/base-eyelashes-v6.glb'
        NORMAL_ATTENUATION = 0
    if VERSION == 'v4':
        SOURCE = ROOT / 'assets/modular_human_female_01/eyes_v3/base-eyes-v3.glb'
        NORMAL_ATTENUATION = 0
    if VERSION in ('v5', 'v6'):
        SOURCE = ROOT / 'assets/modular_human_female_01/eyelashes_v7/base-eyelashes-v7.glb'
        NORMAL_ATTENUATION = 0
    if VERSION == 'v6':
        EYE_RADIUS = (235 / 2048, 150 / 2048)
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    project_eyes(body)
    export_texture_only_glb()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(OUT / f'base-eyes-{VERSION}.glb'))
    scene.world = bpy.data.worlds.new('Review world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.3, .3, .3, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
    center = Vector((0, 0, .5))
    for pos, power in [((2, -3, 3), 220), ((-2, -1, 2), 150), ((0, 3, 2), 200)]:
        bpy.ops.object.light_add(type='AREA', location=pos)
        light = bpy.context.object
        light.data.energy = power
        light.data.size = 3
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = 'ORTHO'
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = 600, 800
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    for name, offset in [('head-front', (0, -3, 0)), ('head', (1.5, -3, .1)), ('head-other', (-1.5, -3, .1))]:
        target = Vector((0, 0, .88))
        camera.location = target + Vector(offset)
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = .30
        scene.render.filepath = str(OUT / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'base-eyes-{VERSION}.blend'))


if __name__ == '__main__':
    main()
