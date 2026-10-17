# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
"""Move nostril color down over the nose underside and bake into the original UVs."""
import hashlib
import argparse
import json
import struct
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/modular_human_female_01/eyelashes_v11/base-eyelashes-v11.glb'
OUT = ROOT / 'assets/modular_human_female_01/nose_v1'
TARGET = Vector((.001, -.044, .914))
UP = Vector((0, -1.3, 2)).normalized()
SCALE = .06
SHIFT = .0032
VERSION = 'v1'


def main():
    global OUT, SHIFT, VERSION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11'], default='v11')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    VERSION = args.version
    OUT = ROOT / f'assets/modular_human_female_01/nose_{VERSION}'
    SHIFT = {'v1': .0032, 'v2': .0046, 'v3': .0042, 'v4': .0042, 'v5': .0042, 'v6': .0042, 'v7': .0042, 'v8': .0042, 'v9': .0042, 'v10': .0042, 'v11': .0042}[VERSION]
    inward_shift = .0004 if VERSION in ('v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11') else 0
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    material = body.data.materials[0]
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    original_node = shader.inputs['Base Color'].links[0].from_node
    original = original_node.image
    normal_original = shader.inputs['Normal'].links[0].from_node.inputs['Color'].links[0].from_node.image
    orm_original = shader.inputs['Roughness'].links[0].from_node.inputs[0].links[0].from_node.image
    output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    emission = nodes.new('ShaderNodeEmission')
    links.new(original_node.outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs[0], output.inputs['Surface'])
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.render.resolution_x = scene.render.resolution_y = 2048
    scene.render.resolution_percentage = 100
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.location = TARGET + Vector((0, -2, -1.3))
    camera.rotation_euler = (TARGET - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = SCALE
    scene.camera = camera
    scene.render.filepath = str(OUT / 'nose-albedo-projection.png')
    bpy.ops.render.render(write_still=True)
    links.new(shader.outputs[0], output.inputs['Surface'])

    patch = body.copy()
    patch.data = body.data.copy()
    bpy.context.collection.objects.link(patch)
    bm = bmesh.new()
    bm.from_mesh(patch.data)
    remove = []
    for face in bm.faces:
        p = body.matrix_world @ face.calc_center_median()
        if face.material_index != 0 or not (abs(p.x) < .016 and .903 < p.z < .926 and p.y < -.03):
            remove.append(face)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bm.to_mesh(patch.data)
    bm.free()
    uv = patch.data.uv_layers.new(name='NoseProjection')
    for loop in patch.data.loops:
        p = patch.matrix_world @ patch.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((p.x - TARGET.x) / SCALE + .5, (p - TARGET).dot(UP) / SCALE + .5)
    patch.data.uv_layers.active_index = 0
    patch.data.uv_layers[0].active_render = True
    paint = material.copy()
    patch.data.materials.clear()
    patch.data.materials.append(paint)
    nodes, links = paint.node_tree.nodes, paint.node_tree.links
    nodes.clear()

    def math_node(operation, *values):
        node = nodes.new('ShaderNodeMath')
        node.operation = operation
        for index, value in enumerate(values):
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    coords = nodes.new('ShaderNodeUVMap')
    coords.uv_map = 'NoseProjection'
    xy = nodes.new('ShaderNodeSeparateXYZ')
    links.new(coords.outputs['UV'], xy.inputs[0])
    masks = []
    center_height = (Vector((0, -.0505, .912)) - TARGET).dot(UP) / SCALE + .5
    for x in [-.0035, .0058]:
        dx = math_node('DIVIDE', math_node('SUBTRACT', xy.outputs['X'], (x - TARGET.x) / SCALE + .5), .005 / SCALE)
        dy = math_node('DIVIDE', math_node('SUBTRACT', xy.outputs['Y'], center_height), .0065 / SCALE)
        radius = math_node('SQRT', math_node('ADD', math_node('MULTIPLY', dx, dx), math_node('MULTIPLY', dy, dy)))
        fade = nodes.new('ShaderNodeMapRange')
        fade.interpolation_type = 'SMOOTHERSTEP'
        fade.clamp = True
        links.new(radius, fade.inputs['Value'])
        for name, value in [('From Min', .7), ('From Max', 1), ('To Min', 1), ('To Max', 0)]:
            fade.inputs[name].default_value = value
        masks.append(fade.outputs[0])
    mask = math_node('MAXIMUM', *masks)
    sample_uv = nodes.new('ShaderNodeCombineXYZ')
    links.new(xy.outputs['X'], sample_uv.inputs['X'])
    links.new(math_node('ADD', xy.outputs['Y'], SHIFT / SCALE), sample_uv.inputs['Y'])
    if VERSION != 'v1':
        side = nodes.new('ShaderNodeMapRange')
        side.interpolation_type = 'SMOOTHERSTEP'
        side.clamp = True
        links.new(xy.outputs['X'], side.inputs['Value'])
        side.inputs['From Min'].default_value = (-.001 - TARGET.x) / SCALE + .5
        side.inputs['From Max'].default_value = (.003 - TARGET.x) / SCALE + .5
        centers = [Vector((-.00354, -.05167, .91304)), Vector((.0058, -.05334, .91304))]
        heights = [(p - TARGET).dot(UP) / SCALE + .5 for p in centers]
        center_v = math_node('ADD', heights[0], math_node('MULTIPLY', side.outputs[0], heights[1] - heights[0]))
        center_u = math_node('ADD', (centers[0].x - TARGET.x) / SCALE + .5,
                             math_node('MULTIPLY', side.outputs[0], (centers[1].x - centers[0].x) / SCALE))
        sample_u = math_node('ADD', center_u, math_node('DIVIDE', math_node('SUBTRACT', xy.outputs['X'], center_u), 1.25))
        if inward_shift:
            offset = math_node('MULTIPLY', math_node('SUBTRACT', math_node('MULTIPLY', side.outputs[0], 2), 1), inward_shift / (SCALE * 1.25))
            sample_u = math_node('ADD', sample_u, offset)
        relative_v = math_node('SUBTRACT', math_node('ADD', xy.outputs['Y'], SHIFT / SCALE), center_v)
        sample_v = math_node('ADD', center_v, math_node('DIVIDE', relative_v, 2))
        links.new(sample_u, sample_uv.inputs['X'])
        links.new(sample_v, sample_uv.inputs['Y'])
    shifted = nodes.new('ShaderNodeTexImage')
    shifted.image = bpy.data.images.load(str(OUT / 'nose-albedo-projection.png'))
    shifted.extension = 'EXTEND'
    links.new(sample_uv.outputs[0], shifted.inputs['Vector'])
    source = nodes.new('ShaderNodeTexImage')
    source.image = original
    mix = nodes.new('ShaderNodeMixRGB')
    links.new(mask, mix.inputs[0])
    links.new(source.outputs['Color'], mix.inputs[1])
    links.new(shifted.outputs['Color'], mix.inputs[2])
    emission = nodes.new('ShaderNodeEmission')
    links.new(mix.outputs[0], emission.inputs['Color'])
    if VERSION != 'v1':
        cavity_masks = []
        cavity_center = Vector((0, -.0473, .9113) if VERSION in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11') else (0, -.0475, .9105))
        cavity_height = (cavity_center - TARGET).dot(UP) / SCALE + .5
        cavity_radius = (.0025, .0027) if VERSION in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11') else (.0027, .003)
        cavity_centers_x = [-.0038 + inward_shift, .0065 - inward_shift]
        for x in cavity_centers_x:
            dx = math_node('DIVIDE', math_node('SUBTRACT', xy.outputs['X'], (x - TARGET.x) / SCALE + .5), cavity_radius[0] / SCALE)
            dy = math_node('DIVIDE', math_node('SUBTRACT', xy.outputs['Y'], cavity_height), cavity_radius[1] / SCALE)
            radius = math_node('SQRT', math_node('ADD', math_node('MULTIPLY', dx, dx), math_node('MULTIPLY', dy, dy)))
            fade = nodes.new('ShaderNodeMapRange')
            fade.interpolation_type = 'SMOOTHERSTEP'
            fade.clamp = True
            links.new(radius, fade.inputs['Value'])
            for name, value in [('From Min', .45), ('From Max', 1), ('To Min', 1), ('To Max', 0)]:
                fade.inputs[name].default_value = value
            cavity_masks.append(fade.outputs[0])
        cavity = nodes.new('ShaderNodeMixRGB')
        cavity_strength = .5 if VERSION in ('v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11') else 1
        cavity_mask = math_node('MULTIPLY', mask, math_node('MAXIMUM', *cavity_masks))
        links.new(math_node('MULTIPLY', cavity_mask, cavity_strength), cavity.inputs[0])
        links.new(mix.outputs[0], cavity.inputs[1])
        cavity.inputs[2].default_value = (.018, .010, .007, 1) if VERSION in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11') else (.006, .003, .002, 1)
        links.new(cavity.outputs[0], emission.inputs['Color'])
        if VERSION in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11'):
            openings = [
                [(722, 755), (692, 775), (672, 810), (650, 880), (710, 930), (780, 890), (775, 835), (740, 778)],
                [(906, 755), (884, 775), (878, 804), (870, 890), (960, 930), (990, 870), (955, 805), (923, 769)],
            ]
            hole_masks = []
            for polygon in openings:
                points = [(x / 1600, 1 - y / 1600) for x, y in polygon]
                distance = None
                for a, b in zip(points, points[1:] + points[:1]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    cross = math_node('SUBTRACT',
                        math_node('MULTIPLY', dx, math_node('SUBTRACT', xy.outputs['Y'], a[1])),
                        math_node('MULTIPLY', dy, math_node('SUBTRACT', xy.outputs['X'], a[0])))
                    edge = math_node('DIVIDE', cross, (dx * dx + dy * dy) ** .5)
                    distance = edge if distance is None else math_node('MINIMUM', distance, edge)
                fade = nodes.new('ShaderNodeMapRange')
                fade.interpolation_type = 'SMOOTHERSTEP'
                fade.clamp = True
                links.new(distance, fade.inputs['Value'])
                for name, value in [('From Min', -.0002 / SCALE), ('From Max', .00035 / SCALE), ('To Min', 0), ('To Max', 1)]:
                    fade.inputs[name].default_value = value
                hole_masks.append(fade.outputs[0])
            clean_uv = nodes.new('ShaderNodeCombineXYZ')
            links.new(xy.outputs['X'], clean_uv.inputs['X'])
            links.new(math_node('ADD', .625, math_node('MULTIPLY', .2, math_node('SUBTRACT', xy.outputs['Y'], .5))), clean_uv.inputs['Y'])
            skin = nodes.new('ShaderNodeTexImage')
            skin.image = shifted.image
            links.new(clean_uv.outputs[0], skin.inputs['Vector'])
            cleanup = nodes.new('ShaderNodeMixRGB')
            cleanup_mask = math_node('MULTIPLY', mask, math_node('SUBTRACT', 1, math_node('MAXIMUM', *hole_masks)))
            links.new(cleanup_mask, cleanup.inputs[0])
            links.new(cavity.outputs[0], cleanup.inputs[1])
            links.new(skin.outputs['Color'], cleanup.inputs[2])
            links.new(cleanup.outputs[0], emission.inputs['Color'])
            if VERSION in ('v7', 'v8', 'v9', 'v10', 'v11'):
                wall_center = (.00348, -.04835, .91075)
                wall_radius = (.0015, .0023, .00165) if VERSION in ('v8', 'v9', 'v10', 'v11') else (.00125, .0019, .0014)
                wall_strength = {'v7': .5, 'v8': .8, 'v9': .98, 'v10': .49, 'v11': .7}[VERSION]
                wall_plateau = .35 if VERSION in ('v10', 'v11') else (.55 if VERSION == 'v9' else (.35 if VERSION == 'v8' else 0))
                geometry = nodes.new('ShaderNodeNewGeometry')
                position = nodes.new('ShaderNodeSeparateXYZ')
                links.new(geometry.outputs['Position'], position.inputs[0])
                wall_regions = [(wall_center, wall_radius)]
                if VERSION in ('v9', 'v10', 'v11'):
                    wall_regions.append(((.0036, -.0478, .9121), (.0011, .0017, .0011)))
                if VERSION in ('v10', 'v11'):
                    wall_regions.extend([
                        ((-.00025, -.04815, .9107), wall_radius),
                        ((-.00030, -.0478, .91215), (.0011, .0017, .0011)),
                    ])
                radius = None
                for region_center, region_radius in wall_regions:
                    squared = []
                    for axis, center, extent in zip(position.outputs, region_center, region_radius):
                        delta = math_node('DIVIDE', math_node('SUBTRACT', axis, center), extent)
                        squared.append(math_node('MULTIPLY', delta, delta))
                    local_radius = math_node('SQRT', math_node('ADD', math_node('ADD', *squared[:2]), squared[2]))
                    radius = local_radius if radius is None else math_node('MINIMUM', radius, local_radius)
                fade = nodes.new('ShaderNodeMapRange')
                fade.interpolation_type = 'SMOOTHERSTEP'
                fade.clamp = True
                links.new(radius, fade.inputs['Value'])
                for name, value in [('From Min', wall_plateau), ('From Max', 1), ('To Min', wall_strength), ('To Max', 0)]:
                    fade.inputs[name].default_value = value
                wall = nodes.new('ShaderNodeMixRGB')
                wall_factor = math_node('MULTIPLY', mask, fade.outputs[0])
                if VERSION in ('v10', 'v11'):
                    entrance = nodes.new('ShaderNodeMapRange')
                    entrance.interpolation_type = 'SMOOTHERSTEP'
                    entrance.clamp = True
                    links.new(position.outputs['Y'], entrance.inputs['Value'])
                    for name, value in [('From Min', -.0502), ('From Max', -.0482), ('To Min', 0), ('To Max', 1)]:
                        entrance.inputs[name].default_value = value
                    wall_factor = math_node('MULTIPLY', wall_factor, entrance.outputs[0])
                links.new(wall_factor, wall.inputs[0])
                links.new(cleanup.outputs[0], wall.inputs[1])
                wall.inputs[2].default_value = (.075, .036, .018, 1) if VERSION in ('v8', 'v9', 'v10', 'v11') else (.085, .044, .025, 1)
                if VERSION in ('v9', 'v10', 'v11'):
                    wall.inputs[2].default_value = (.11193243, .04666509, .02028856, 1)
                links.new(wall.outputs[0], emission.inputs['Color'])
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(emission.outputs[0], output.inputs['Surface'])
    destination = nodes.new('ShaderNodeTexImage')
    target = bpy.data.images.new('Nostril color aligned', *original.size, alpha=False)
    original_pixels = np.empty(len(original.pixels), dtype=np.float32)
    original.pixels.foreach_get(original_pixels)
    target.pixels.foreach_set(original_pixels)
    destination.image = target
    nodes.active = destination
    bpy.ops.object.select_all(action='DESELECT')
    patch.select_set(True)
    bpy.context.view_layer.objects.active = patch
    scene.render.bake.use_clear = False
    scene.render.bake.margin = 4
    scene.render.bake.margin_type = 'EXTEND'
    bpy.ops.object.bake(type='EMIT')
    baked = [(target, original, f'base-color-nose-{VERSION}.png')]
    if VERSION != 'v1':
        links.new(mix.outputs[0], emission.inputs['Color'])
        links.remove(mix.inputs[2].links[0])
        for original_map, name, replacement, strength in [
            (normal_original, 'normal', (.5, .5, 1, 1), 1),
            (orm_original, 'orm', (1, .85, 0, 1), 1),
        ]:
            source.image = original_map
            mix.inputs[2].default_value = replacement
            if name == 'orm':
                lower = nodes.new('ShaderNodeMapRange')
                lower.interpolation_type = 'SMOOTHERSTEP'
                lower.clamp = True
                links.new(xy.outputs['Y'], lower.inputs['Value'])
                lower.inputs['From Min'].default_value = center_height - .001 / SCALE
                lower.inputs['From Max'].default_value = center_height + .0015 / SCALE
                lower.inputs['To Min'].default_value = 1
                lower.inputs['To Max'].default_value = 0
                factor = math_node('MULTIPLY', mask, lower.outputs[0])
            else:
                factor = math_node('MULTIPLY', mask, strength)
            links.new(factor, mix.inputs[0])
            image = bpy.data.images.new(f'Nostril {name}', *original_map.size, alpha=False)
            image.colorspace_settings.name = 'Non-Color'
            values = np.empty(len(original_map.pixels), dtype=np.float32)
            original_map.pixels.foreach_get(values)
            image.pixels.foreach_set(values)
            destination.image = image
            bpy.ops.object.bake(type='EMIT')
            baked.append((image, original_map, f'{name}-nose-{VERSION}.png'))
    support = bpy.data.images.new('Nose support', *original.size, alpha=False)
    support.colorspace_settings.name = 'Non-Color'
    destination.image = support
    links.new(mask, emission.inputs['Color'])
    scene.render.bake.use_clear = True
    bpy.ops.object.bake(type='EMIT')
    support_pixels = np.empty(len(support.pixels), dtype=np.float32)
    support.pixels.foreach_get(support_pixels)
    outside = support_pixels.reshape(-1, 4)[:, 0] <= 1e-5
    for image, original_map, name in baked:
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        before = np.empty(len(original_map.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        original_map.pixels.foreach_get(before)
        pixels.reshape(-1, 4)[outside] = before.reshape(-1, 4)[outside]
        image.pixels.foreach_set(pixels)
    for image, name in [(image, name) for image, _, name in baked] + [(support, 'nose-support-mask.png')]:
        image.filepath_raw = str(OUT / name)
        image.file_format = 'PNG'
        image.save()

    raw = SOURCE.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]
    material = doc['materials'][0]
    maps = [(material['pbrMetallicRoughness']['baseColorTexture']['index'], f'base-color-nose-{VERSION}.png')]
    if VERSION != 'v1':
        maps += [(material['normalTexture']['index'], f'normal-nose-{VERSION}.png'),
                 (material['pbrMetallicRoughness']['metallicRoughnessTexture']['index'], f'orm-nose-{VERSION}.png')]
    replacements = {}
    for index, name in maps:
        image = doc['images'][doc['textures'][index]['source']]
        image['mimeType'] = 'image/png'
        replacements[image['bufferView']] = (OUT / name).read_bytes()
    packed = bytearray()
    for index, view in enumerate(doc['bufferViews']):
        start = view.get('byteOffset', 0)
        payload = replacements.get(index, binary[start:start + view['byteLength']])
        packed.extend(b'\0' * (-len(packed) % 4))
        view['byteOffset'], view['byteLength'] = len(packed), len(payload)
        packed.extend(payload)
    doc['buffers'][0]['byteLength'] = len(packed)
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    packed.extend(b'\0' * (-len(packed) % 4))
    glb = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(packed))
    glb += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    glb += struct.pack('<II', len(packed), 0x004e4942) + packed
    path = OUT / f'base-nose-{VERSION}.glb'
    path.write_bytes(glb)
    wall_color = list(wall.inputs[2].default_value) if VERSION in ('v7', 'v8', 'v9', 'v10', 'v11') else None
    cavity_color = list(cavity.inputs[2].default_value) if VERSION != 'v1' else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'base-nose-{VERSION}.blend'))
    report = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'output_sha256': hashlib.sha256(glb).hexdigest(),
              'exterior_skin_cleanup': VERSION in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11'), 'projection_shift': SHIFT, 'changed_maps': ['baseColor', 'normal', 'ORM'] if VERSION != 'v1' else ['baseColor'],
              'cavity_center': list(cavity_center) if VERSION != 'v1' else None,
              'inward_shift_per_nostril': inward_shift,
              'cavity_centers_x': cavity_centers_x if VERSION != 'v1' else None,
              'cavity_radius': list(cavity_radius) if VERSION != 'v1' else None,
              'cavity_color_linear': cavity_color,
              'cavity_strength': cavity_strength if VERSION != 'v1' else None,
              'nostril_projection_scale': [1.25, 2] if VERSION != 'v1' else [1, 1],
              'outside_support_float_pixels_unchanged': True,
              'support_pixels': int((~outside).sum()), 'triangles': 22175}
    if VERSION in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11'):
        report['protected_openings_projection_1600px'] = openings
        report['skin_sample_v'] = '0.625 + 0.2 * (projection_v - 0.5)'
    if VERSION in ('v7', 'v8', 'v9', 'v10', 'v11'):
        report['inner_wall_patch'] = {'center': wall_center, 'radius': wall_radius, 'color_linear': wall_color, 'strength': wall_strength, 'plateau': wall_plateau, 'regions': wall_regions}
    if VERSION in ('v10', 'v11'):
        report['entrance_skin_gradient'] = {'axis': 'Blender world Y', 'skin_at': -.0502, 'inner_shading_at': -.0482, 'interpolation': 'SMOOTHERSTEP'}
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
