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
SOURCE = DIRECTORY / 'fitted_v6'
OUTPUT = DIRECTORY / 'fitted_v7'
OUTPUT.mkdir(exist_ok=True)
START, DECAY = .575, .025
CENTER_Y, RADIUS_Y, CENTER_Z, TILT = .525, .1305, -.004, .10
R0 = np.sqrt(1 - ((START - CENTER_Y) / RADIUS_Y) ** 2)
SLOPE = (START - CENTER_Y) / (RADIUS_Y ** 2 * R0)


def deform(points, attachment=False):
    result = points.copy()
    height = points[:, 1]
    active = (height < START) & (height > .45)
    h = height[active]
    old_radius = np.sqrt(1 - ((h - CENTER_Y) / RADIUS_Y) ** 2)
    new_radius = R0 + SLOPE * DECAY * (1 - np.exp(-(START - h) / DECAY))
    amount = np.ones(len(h))
    if attachment:
        t = np.clip((h - .45) / .025, 0, 1)
        amount = t * t * (3 - 2 * t)
    scale = 1 + (new_radius / old_radius - 1) * amount
    center_z = CENTER_Z + TILT * (h - CENTER_Y)
    result[active, 0] *= scale
    result[active, 2] = center_z + (points[active, 2] - center_z) * scale
    return result


doc, binary = read_glb(SOURCE / 'bottom_female_knight.glb')
binary = bytearray(binary)
primitives = doc['meshes'][0]['primitives']
cache, changes = {}, []
for part_index, primitive in enumerate(primitives):
    attrs = primitive['attributes']
    points = accessor(doc, binary, attrs['POSITION']).astype(float)
    selected = np.ones(len(points), dtype=bool)
    if part_index == 0:
        faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
        _, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
        parents = np.arange(welded.max() + 1)

        def root(index):
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        for face in welded[faces]:
            for corner in face[1:]:
                parents[root(corner)] = root(face[0])
        labels = np.array([root(index) for index in welded])
        selected[:] = False
        for label in np.unique(labels[np.unique(faces)]):
            vertices = np.flatnonzero(labels == label)
            bounds = points[vertices]
            if bounds[:, 1].min() < .45 and bounds[:, 1].max() < .615 and abs(bounds[:, 0].mean()) > .04:
                selected[vertices] = True
    attachment = part_index == 0
    moved = points.copy()
    moved[selected] = deform(points[selected], attachment)
    jacobian = np.repeat(np.eye(3)[None], len(points), axis=0)
    for axis in range(3):
        step = np.eye(3)[axis] * 1e-6
        jacobian[selected, :, axis] = (deform(points[selected] + step, attachment) - deform(points[selected] - step, attachment)) / 2e-6
    normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
    normals = np.linalg.solve(jacobian.transpose(0, 2, 1), normals[..., None])[..., 0]
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    values = {'POSITION': moved, 'NORMAL': normals}
    if 'TANGENT' in attrs:
        tangent = accessor(doc, binary, attrs['TANGENT']).astype(float)
        tangent[:, :3] = np.einsum('nij,nj->ni', jacobian, tangent[:, :3])
        tangent[:, :3] -= normals * (normals * tangent[:, :3]).sum(1, keepdims=True)
        tangent[:, :3] /= np.linalg.norm(tangent[:, :3], axis=1, keepdims=True)
        values['TANGENT'] = tangent
    for name, value in values.items():
        key = (attrs[name], attachment)
        if key not in cache:
            cache[key] = add_accessor(doc, binary, value, 'VEC4' if name == 'TANGENT' else 'VEC3')
            doc['bufferViews'][doc['accessors'][cache[key]]['bufferView']]['target'] = 34962
        attrs[name] = cache[key]
    changes.append({'primitive': part_index, 'moved_vertices': int((np.linalg.norm(moved - points, axis=1) > 1e-8).sum()),
                    'maximum_displacement': float(np.linalg.norm(moved - points, axis=1).max())})

doc['nodes'][0]['extras']['fitting_version'] = 7
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
for key in ['validation', 'preserved_scope', 'retained_previous_candidate']:
    report.pop(key, None)
report.update(source=str((SOURCE / 'bottom_female_knight.glb').relative_to(ROOT)),
              source_sha256=hashlib.sha256((SOURCE / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Continue the rounded upper shell below height .575 with an exponential profile whose curvature decreases toward the hem. Transform attached straps, surface normals and tangents consistently.',
              lower_profile={'start_height': START, 'decay_length': DECAY, 'start_radius_factor': float(R0), 'start_downward_slope': float(SLOPE)},
              changes=changes, status='Shape candidate; validation pending')
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
print(json.dumps({'sha256': report['sha256'], 'changes': changes}))
