import argparse
import hashlib
import json
import sys
import subprocess
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, view_bytes, write_glb


def restore_textures(source, output):
    original, original_binary = read_glb(source)
    exported, exported_binary = read_glb(output)
    textures = {image['name']: image for image in original['images']}
    replacement = {}
    for image in exported['images']:
        old = textures[image['name']]
        replacement[image['bufferView']] = view_bytes(original, original_binary, old['bufferView'])
        image['mimeType'] = old['mimeType']
    binary = bytearray()
    for index, view in enumerate(exported['bufferViews']):
        binary.extend(b'\0' * (-len(binary) % 4))
        payload = replacement.get(index, view_bytes(exported, exported_binary, index))
        view['byteOffset'] = len(binary)
        view['byteLength'] = len(payload)
        binary.extend(payload)
    exported['buffers'][0]['byteLength'] = len(binary)
    write_glb(output, exported, bytes(binary))


def make_cutter(record, collection):
    outline = record['outline_yz']
    count = len(outline)
    vertices = [(x, y, z) for x in (record['x_min'], record['x_max']) for y, z in outline]
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces.extend((i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count))
    mesh = bpy.data.meshes.new(record['name'])
    mesh.from_pydata(vertices, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(record['name'], mesh)
    collection.objects.link(obj)
    obj.display_type = 'WIRE'
    return obj


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--cutters', type=Path, default=ROOT / 'doc/assets/barkan-wing-hole-cutters.json')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.source.resolve()))
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    obj.name = 'Barkan - wing holes'
    before = len(obj.data.polygons)
    bpy.context.view_layer.objects.active = obj
    collection = bpy.data.collections.new('Wing cutters - Boolean sources')
    bpy.context.scene.collection.children.link(collection)
    records = json.loads(args.cutters.read_text())['cutters']
    for record in records:
        make_cutter(record, collection)
    faces = []
    source_mesh = obj.data
    for polygon in source_mesh.polygons:
        attributes, world = [], []
        for index in polygon.loop_indices:
            point = source_mesh.vertices[source_mesh.loops[index].vertex_index].co
            uv = source_mesh.uv_layers.active.data[index].uv
            normal = source_mesh.corner_normals[index].vector
            attributes.append([*point, *uv, *normal])
            world.append(list(obj.matrix_world @ point))
        faces.append({'attributes': attributes, 'world': world})
    with tempfile.TemporaryDirectory(prefix='barkan-wing-cut-') as temporary:
        incoming, outgoing = Path(temporary) / 'source.json', Path(temporary) / 'cut.json'
        incoming.write_text(json.dumps({'faces': faces, 'cutters': records}))
        subprocess.run([
            str(ROOT / '.venv/bin/python'), str(ROOT / 'tools/lib/barkan_wing_surface.py'),
            str(incoming), str(outgoing),
        ], check=True)
        result = json.loads(outgoing.read_text())
    positions, uvs, normals, triangles = [], [], [], []
    vertex_map = {}
    for face in result['faces']:
        indices = []
        for value in face:
            key = tuple(value)
            if key not in vertex_map:
                vertex_map[key] = len(positions)
                positions.append(value[:3])
            indices.append(vertex_map[key])
            uvs.append(value[3:5])
            normals.append(value[5:])
        triangles.append(indices)
    mesh = bpy.data.meshes.new('Barkan - cut wing surfaces')
    mesh.from_pydata(positions, [], triangles)
    mesh.materials.append(source_mesh.materials[0])
    uv_layer = mesh.uv_layers.new(name=source_mesh.uv_layers.active.name)
    for loop, uv in zip(uv_layer.data, uvs):
        loop.uv = uv
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.normals_split_custom_set(normals)
    obj.data = mesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    topology = {
        'boundary_edges': sum(edge.is_boundary for edge in bm.edges),
        'non_manifold_edges': sum(not edge.is_manifold for edge in bm.edges),
        'loose_vertices': sum(not vertex.link_faces for vertex in bm.verts),
    }
    bm.free()
    obj.data.calc_loop_triangles()
    collection.hide_render = True
    collection.hide_viewport = True
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()), export_format='GLB', use_selection=True,
        export_image_format='WEBP', export_image_quality=90,
    )
    restore_textures(args.source, args.output)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.type = 'MATERIAL'
                area.spaces.active.region_3d.view_location = Vector((0, 0, .05))
                area.spaces.active.region_3d.view_distance = 1.5
                area.spaces.active.region_3d.view_rotation = Vector((4, -1, .7)).to_track_quat('Z', 'Y')
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.with_suffix('.blend').resolve()))
    report = {
        'source': str(args.source),
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'output': str(args.output),
        'output_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'method': 'Surface difference with extruded front/back contours, intersection vertices interpolated on original triangles',
        'changed_source_faces': result['changed_source_faces'],
        'cutters': len(records),
        'triangles_before': before,
        'triangles_after': len(obj.data.loop_triangles),
        'textures': 'Original embedded WebP bytes preserved without re-encoding',
        **topology,
    }
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
