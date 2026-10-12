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
SOURCE = DIRECTORY / 'fitted_v5'
OUTPUT = DIRECTORY / 'fitted_v6'
OUTPUT.mkdir(exist_ok=True)
doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
plate = doc['meshes'][0]['primitives'][1]
attrs = plate['attributes']
uv = accessor(doc, binary, attrs['TEXCOORD_0'])
uv = np.array([.405, .280]) + uv * np.array([.060, .030])
attrs['TEXCOORD_0'] = add_accessor(doc, binary, uv, 'VEC2')
points = accessor(doc, binary, attrs['POSITION']).astype(float)
normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
faces = accessor(doc, binary, plate['indices']).reshape(-1, 3)
a, b, c = faces.T
ab, ac = points[b] - points[a], points[c] - points[a]
uv_ab, uv_ac = uv[b] - uv[a], uv[c] - uv[a]
det = uv_ab[:, 0] * uv_ac[:, 1] - uv_ab[:, 1] * uv_ac[:, 0]
valid = abs(det) > 1e-12
t1, t2 = np.zeros_like(points), np.zeros_like(points)
directions = (ab[valid] * uv_ac[valid, 1, None] - ac[valid] * uv_ab[valid, 1, None]) / det[valid, None]
bitangents = (ac[valid] * uv_ab[valid, 0, None] - ab[valid] * uv_ac[valid, 0, None]) / det[valid, None]
for corners in faces[valid].T:
    np.add.at(t1, corners, directions)
    np.add.at(t2, corners, bitangents)
tangents = t1 - normals * (normals * t1).sum(1, keepdims=True)
invalid = np.linalg.norm(tangents, axis=1) < 1e-8
tangents[invalid] = np.cross(normals[invalid], np.eye(3)[np.argmin(abs(normals[invalid]), axis=1)])
tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
handedness = np.where((np.cross(normals, tangents) * t2).sum(1) < 0, -1, 1)
attrs['TANGENT'] = add_accessor(doc, binary, np.column_stack([tangents, handedness]), 'VEC4')
for name in ['TEXCOORD_0', 'TANGENT']:
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
plate['material'] = 0
doc['materials'].pop(1)
for primitive in doc['meshes'][0]['primitives']:
    if primitive['material'] > 1:
        primitive['material'] -= 1
doc['nodes'][0]['extras']['fitting_version'] = 6
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
for name in ['body-occlusion.json', 'shell-data.npz']:
    shutil.copy2(SOURCE / name, OUTPUT / name)
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)),
              source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Keep V5 geometry, normals and rig. Assign the original central guard material to the side plates, mapping their UVs to a flat metal patch of the same color, ORM and normal textures; add UV-compatible tangents.',
              material_correction='Side plates and central guards now share material index 0, with identical texture references and PBR factors.',
              metal_patch_uv=[.405, .280, .465, .310],
              status='Material matching candidate; visual and preservation validation pending',
              preserved_scope='All V5 positions, normals, triangle indices, skin weights, bones and embedded texture bytes. Side-plate UVs, tangents and material assignment changed.')
report.pop('validation', None)
report['retained_previous_candidate'] = 'fitted_v5: accepted shape baseline; plain silver material differs from original armor.'
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
print(json.dumps({'sha256': report['sha256'], 'metal_patch_uv': report['metal_patch_uv']}))
