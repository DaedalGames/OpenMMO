# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor

DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v11'
VERSION = sys.argv[sys.argv.index('--version') + 1] if '--version' in sys.argv else 'v18'
assert VERSION in ['v13', 'v14', 'v15', 'v16', 'v17', 'v18']
OUTPUT = DIRECTORY / f'fitted_{VERSION}'
OUTPUT.mkdir(exist_ok=True)
source = SOURCE / 'bottom_female_knight.glb'
assert hashlib.sha256(source.read_bytes()).hexdigest() == '53f853b29a4a91752bb1b3d20c5633b7ff97feea310be3f6a3545bcf1e3148e2'
doc, binary = read_glb(source)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION'])
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
selected = []
for label in np.unique(labels[faces]):
    vertices = np.unique(faces[labels[faces[:, 0]] == label])
    bounds = points[vertices]
    front_side = bounds[:, 0].min() > .04 or (VERSION in ['v15', 'v16', 'v17', 'v18'] and bounds[:, 0].max() < -.04)
    if front_side and bounds[:, 2].min() > .065 and bounds[:, 1].max() < .58:
        selected.extend(vertices.tolist())
selected = np.array(sorted(selected))
assert len(selected) == (584 if VERSION in ['v15', 'v16', 'v17', 'v18'] else 292)
side = np.sign(points[selected, 0]).astype(float)
if VERSION == 'v13':
    t = np.clip((points[selected, 1] - .52) / .05, 0, 1)
    depth = -.017 * t * t * (3 - 2 * t)
    slope = -.017 * 6 * t * (1 - t) / .05
    vertical_offset, attachment_height = .005, .572
else:
    slope = np.full(len(selected), -.015 / .157)
    depth = -.002 + slope * (points[selected, 1] - .42)
    vertical_offset, attachment_height = -.001, .566
points[selected] += np.column_stack([-.013 * side, np.full(len(selected), vertical_offset), depth])
normals = accessor(doc, binary, attrs['NORMAL'])
normals[selected, 1] -= slope * normals[selected, 2]
normals[selected] /= np.linalg.norm(normals[selected], axis=1, keepdims=True)
tangents = accessor(doc, binary, attrs['TANGENT'])
tangents[selected, 2] += slope * tangents[selected, 1]
tangents[selected, :3] /= np.linalg.norm(tangents[selected, :3], axis=1, keepdims=True)
thickened = np.array([], dtype=int)
if VERSION in ['v16', 'v17', 'v18']:
    thickened = selected[((side < 0) | (VERSION in ['v17', 'v18'])) & (points[selected, 1] > .425) & (points[selected, 1] < .569)]
    _, groups = np.unique(np.round(points[thickened], 6), axis=0, return_inverse=True)
    normal_z = np.bincount(groups, weights=normals[thickened, 2])
    direction = np.sign(normal_z[groups])
    height = points[thickened, 1].astype(float)
    lower = np.clip((height - .425) / .018, 0, 1)
    upper = np.clip((.569 - height) / .012, 0, 1)
    lower_smooth = lower * lower * (3 - 2 * lower)
    upper_smooth = upper * upper * (3 - 2 * upper)
    thickness = .00045 * direction
    points[thickened, 2] += thickness * lower_smooth * upper_smooth
    derivative = thickness * (6 * lower * (1 - lower) / .018 * upper_smooth - lower_smooth * 6 * upper * (1 - upper) / .012)
    normals[thickened, 1] -= derivative * normals[thickened, 2]
    normals[thickened] /= np.linalg.norm(normals[thickened], axis=1, keepdims=True)
    tangents[thickened, 2] += derivative * tangents[thickened, 1]
    tangents[thickened, :3] /= np.linalg.norm(tangents[thickened, :3], axis=1, keepdims=True)
names = [doc['nodes'][index]['name'] for index in doc['skins'][0]['joints']]
joints = accessor(doc, binary, attrs['JOINTS_0'])
weights = accessor(doc, binary, attrs['WEIGHTS_0'])
blend_length = .145 if VERSION == 'v18' else .045
leg = np.clip((attachment_height - points[selected, 1]) / blend_length, 0, 1)
leg = leg * leg * (3 - 2 * leg)
joints[selected] = 0
joints[selected, 0] = names.index('Hips')
joints[selected, 1] = [names.index('LeftUpLeg' if value > 0 else 'RightUpLeg') for value in side]
weights[selected] = np.column_stack([1 - leg, leg, np.zeros((len(selected), 2))])
swap = selected[leg > .5]
joints[swap] = joints[swap][:, [1, 0, 2, 3]]
weights[swap] = weights[swap][:, [1, 0, 2, 3]]
joints[selected] = np.where(weights[selected] > 0, joints[selected], 0)
for name, values, kind, component in [
    ('POSITION', points, 'VEC3', 5126), ('NORMAL', normals, 'VEC3', 5126),
    ('TANGENT', tangents, 'VEC4', 5126), ('JOINTS_0', joints, 'VEC4', 5123),
    ('WEIGHTS_0', weights, 'VEC4', 5126),
]:
    attrs[name] = add_accessor(doc, binary, values, kind, component)
    doc['bufferViews'][doc['accessors'][attrs[name]]['bufferView']]['target'] = 34962
doc['nodes'][0]['extras']['fitting_version'] = int(VERSION[1:])
doc['buffers'][0]['byteLength'] = len(binary)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = {
    'date': '2026-10-13', 'source': str(source.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'output': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'method': f'Move {"both front straps and tips" if VERSION in ["v15", "v16", "v17", "v18"] else "the wearer-left front strap and tip"} inward 0.013. Blend each attachment from the pelvis to its own thigh.',
    'thickened_vertices': thickened.tolist(),
    'maximum_surface_offset': .00045 if VERSION in ['v16', 'v17', 'v18'] else 0,
    'vertical_offset_from_v11': vertical_offset,
    'depth_profile': 'Smoothstep recession of the upper end.' if VERSION == 'v13' else 'Full-length affine shear to remove the upper bend and expose the buckle opening.',
    'attachment_min_y': attachment_height + .003,
    'leg_weight_blend_length': blend_length,
    'primitive': 0, 'vertices': selected.tolist(),
    'preserved': ['other components', 'UVs', 'indices', 'materials', 'embedded textures', 'bones', 'inverse binds', 'occlusion mask'],
    'new_meshes': 0, 'additional_api_credits': 0,
}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'moved_vertices': len(selected)}))

if '--blend' in sys.argv:
    import bpy

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
