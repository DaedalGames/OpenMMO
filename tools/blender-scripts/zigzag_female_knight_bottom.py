# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v7'
OUTPUT = DIRECTORY / 'fitted_v8'
OUTPUT.mkdir(exist_ok=True)
EDGE_OFFSETS = [[-.25, .075, .03, -.055], [0, .035, .065, -.055], [0, .055, -.065, -.35]]
PANEL_SIZES = [320, 320, 290] * 2


def deform(points, level):
    result = points.copy()
    x, height, z = points.T
    center_z = -.004 + .10 * (height - .525)
    angle = np.arctan2((z - center_z) / .092, abs(x) / .124)
    radius = np.hypot(x / .124, (z - center_z) / .092)
    top = .6345 - .012 * np.sin(angle) ** 2 + .002 * np.sin(angle) if level == 0 else [.0, .578, .528][level]
    bottom = [.575, .525, .475][level]
    fraction = np.clip((top - height) / (top - bottom), 0, 1)
    delta = np.interp(fraction, [0, 1 / 3, 2 / 3, 1], EDGE_OFFSETS[level])
    influence = np.clip((angle - .25) / .85, 0, 1)
    influence = influence * influence * (3 - 2 * influence)
    adjusted = angle + influence * delta
    active = angle > .25
    result[active, 0] = np.sign(x[active]) * .124 * radius[active] * np.cos(adjusted[active])
    result[active, 2] = center_z[active] + .092 * radius[active] * np.sin(adjusted[active])
    return result


doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
primitives = doc['meshes'][0]['primitives']
attrs = primitives[1]['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
tangents = accessor(doc, binary, attrs['TANGENT']).astype(float)
assert len(points) == sum(PANEL_SIZES)
new_points, new_normals, new_tangents = points.copy(), normals.copy(), tangents.copy()
offset, edge_records = 0, []
for panel, count in enumerate(PANEL_SIZES):
    level = panel % 3
    selection = slice(offset, offset + count)
    original = points[selection]
    moved = deform(original, level)
    jacobian = np.zeros((count, 3, 3))
    for axis in range(3):
        step = np.eye(3)[axis] * 1e-6
        jacobian[:, :, axis] = (deform(original + step, level) - deform(original - step, level)) / 2e-6
    assert np.linalg.det(jacobian).min() > .1
    normal = np.linalg.solve(jacobian.transpose(0, 2, 1), normals[selection, :, None])[..., 0]
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    tangent = np.einsum('nij,nj->ni', jacobian, tangents[selection, :3])
    tangent -= normal * (normal * tangent).sum(1, keepdims=True)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    new_points[selection], new_normals[selection], new_tangents[selection, :3] = moved, normal, tangent
    for start in [offset + 256, offset + 273]:
        rivet = slice(start, start + 17)
        center = points[rivet].mean(0)
        derivative = np.column_stack([(deform((center + np.eye(3)[axis] * 1e-6)[None], level)[0]
                                      - deform((center - np.eye(3)[axis] * 1e-6)[None], level)[0]) / 2e-6
                                     for axis in range(3)])
        u, _, vh = np.linalg.svd(derivative)
        rotation = u @ vh
        new_points[rivet] = deform(center[None], level)[0] + (points[rivet] - center) @ rotation.T
        new_normals[rivet] = normals[rivet] @ rotation.T
        new_tangents[rivet, :3] = tangents[rivet, :3] @ rotation.T
    edge = [offset + row * 15 + 14 for row in range(4)]
    edge_records.append({'side': -1 if panel < 3 else 1, 'level': level, 'vertex_indices': edge,
                         'before': points[edge].tolist(), 'after': new_points[edge].tolist()})
    offset += count

new_attributes = {}
for name, values, kind in [('POSITION', new_points, 'VEC3'), ('NORMAL', new_normals, 'VEC3'), ('TANGENT', new_tangents, 'VEC4')]:
    index = add_accessor(doc, binary, values, kind)
    doc['bufferViews'][doc['accessors'][index]['bufferView']]['target'] = 34962
    new_attributes[name] = index
for primitive in primitives[1:]:
    for name, index in new_attributes.items():
        if name in primitive['attributes']:
            primitive['attributes'][name] = index
doc['nodes'][0]['extras']['fitting_version'] = 8
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
for key in ['validation', 'changes', 'user_correction_reference']:
    report.pop(key, None)
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)),
              source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Shape the front inner edge of each side plate into a pointed zigzag by redistributing its existing vertices along the unchanged shell surface. Move plate caps, seams and rivets coherently; retain all original straps and central guards.',
              edge_angle_offsets=EDGE_OFFSETS, edge_vertices=edge_records,
              maximum_displacement=float(np.linalg.norm(new_points - points, axis=1).max()),
              status='Edge candidate; validation pending')
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'female-knight-bottom-fitted.blend'))
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and obj.name.startswith('bottom_female_knight'):
        bpy.data.objects.remove(obj, do_unlink=True)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(target), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects) - before
for obj in imported:
    if obj.type == 'MESH':
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
        obj.parent = None
for obj in imported:
    if obj.type == 'ARMATURE':
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.file.pack_all()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-knight-bottom-fitted.blend'))
print(json.dumps({'sha256': report['sha256'], 'maximum_displacement': report['maximum_displacement']}))
