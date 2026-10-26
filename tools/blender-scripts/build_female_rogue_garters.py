import copy
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.mesh_components import welded_islands
from outfits.skinning import deform

OUTPUT = ROOT / 'assets/items/female_rogue_garters/fitted_v1'
OUTPUT.mkdir(parents=True, exist_ok=True)
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
SKIRT = ROOT / 'assets/items/female_rogue_skirt/tripo_v1/fitted_v6/bottom_female_rogue.glb'
BOOTS = ROOT / 'assets/items/female_rogue_boots/tripo_v1/fitted_v3/boots_female_rogue.glb'
ROWS = 17
WIDTH = .014
THICKNESS = .0018


def unit(values):
    return values/np.maximum(np.linalg.norm(values, axis=-1, keepdims=True), 1e-12)


def smooth(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


def load(path, index=0):
    doc, raw = read_glb(path)
    p = doc['meshes'][index]['primitives'][0]
    a = p['attributes']
    x = accessor(doc, raw, a['POSITION']).astype(float)
    f = accessor(doc, raw, p['indices']).reshape(-1, 3)
    j = accessor(doc, raw, a['JOINTS_0']).astype(int)
    w = accessor(doc, raw, a['WEIGHTS_0'])
    dense = np.zeros((len(x), 65))
    for k in range(4):
        np.add.at(dense, (np.arange(len(x)), j[:, k]), w[:, k])
    delta = accessor(doc, raw, p['targets'][0]['POSITION']) if p.get('targets') else np.zeros_like(x)
    return doc, raw, x, f, dense, delta


def compact_weights(dense):
    j = np.argsort(-dense, axis=1)[:, :4]
    w = np.take_along_axis(dense, j, axis=1)
    w /= w.sum(1, keepdims=True)
    return j, w


def barycentric(p, triangle):
    a, b, c = triangle
    uv = np.linalg.lstsq(np.column_stack((b-a, c-a)), p-a, rcond=None)[0]
    result = np.clip([1-uv.sum(), *uv], 0, 1)
    return result/result.sum()


base, _, bp, bf, bw, _ = load(BODY)
_, _, body_labels = welded_islands(bp, bf)
skin = body_labels == np.bincount(body_labels).argmax()
sd, _, sp, sf, sw, sm = load(SKIRT)
_, _, skirt_labels = welded_islands(sp, sf)
cloth = skirt_labels == np.bincount(skirt_labels).argmax()
cloth_faces = sf[cloth[sf].all(1)]
skirt_surface = BVHTree.FromPolygons([Vector(p) for p in sp], cloth_faces.tolist())
source_doc, source_raw = read_glb(BOOTS)
poses = json.loads((BOOTS.parent / 'animation-samples.json').read_text())
frames = [({'clip': 'rest', 'phase': 0}, np.tile(np.eye(4), (65, 1, 1)))]
frames += [(s, np.array(s['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)) for s in poses]
fitting_frames = [entry for entry in frames if entry[0]['clip'] != 'sit_idle' and round(entry[0]['phase']*60) % 15 == 0]
seated_frames = [entry for entry in frames if entry[0]['clip'] == 'sit_idle']
middle_matrices = seated_frames[len(seated_frames)//2][1]
straps = []
for boot_index, side in enumerate(['right', 'left']):
    _, _, xp, xf, xw, xm = load(BOOTS, boot_index)
    _, _, labels = welded_islands(xp, xf)
    candidates = [np.flatnonzero(labels == label) for label in np.unique(labels)
                  if (labels == label).sum() < 200 and xp[labels == label, 1].mean() > .74]
    assert len(candidates) == 1
    stud = candidates[0]
    for facing, sign in [('front', 1), ('back', -1)]:
        bottom = xp[stud].mean(0)
        if sign < 0:
            ids = np.flatnonzero((xp[:, 1] > .738) & (xp[:, 2] < -.04))
            score = np.abs(xp[ids, 0]-bottom[0])+2*np.abs(xp[ids, 1]-.753)
            stud = ids[np.argsort(score)[:3]]
            bottom = xp[stud].mean(0)
        bottom_weight = xw[stud].mean(0)
        bottom_morph = xm[stud].mean(0)
        hem_candidates = np.flatnonzero(cloth & (sp[:, 1] < .91) & (sp[:, 2]*sign > .025))
        hem = hem_candidates[np.argmin(3*np.abs(sp[hem_candidates, 0]-bottom[0])+sp[hem_candidates, 1])]
        origin = Vector((bottom[0], sp[hem, 1]+.008, sign*.4))
        hit, _, face, _ = skirt_surface.ray_cast(origin, Vector((0, 0, -sign)), .8)
        assert hit is not None
        triangle = cloth_faces[face]
        bary = barycentric(np.array(hit), sp[triangle])
        top = bary @ sp[triangle]
        top[2] -= sign*.0005
        top_weight = bary @ sw[triangle]
        top_morph = bary @ sm[triangle]
        local_skin = skin & (np.abs(bp[:, 0]) < .30) & (bp[:, 0]*(1 if side == 'left' else -1) > .025) & (bp[:, 1] > .62) & (bp[:, 1] < 1.02)
        skin_faces = bf[local_skin[bf].all(1)]
        surface = BVHTree.FromPolygons([Vector(p) for p in bp], skin_faces.tolist())
        centers, dense = [], []
        for t in np.linspace(0, 1, ROWS):
            p = top*(1-t)+bottom*t
            hit, _, face, distance = surface.ray_cast(Vector(p+[0, 0, sign*.20]), Vector((0, 0, -sign)), .4)
            if hit is None:
                hit, _, face, _ = surface.find_nearest(Vector(p))
            indices = skin_faces[face]
            weight = barycentric(np.array(hit), bp[indices]) @ bw[indices]
            if 0 < t < 1 and (p[2]-hit[2])*sign < .004:
                p[2] = hit[2]+sign*.004
            a, b = 1-smooth(t/.18), smooth((t-.82)/.18)
            weight = weight*(1-a-b)+a*top_weight+b*bottom_weight
            centers.append(p)
            dense.append(weight)
        centers, dense = np.array(centers), np.array(dense)
        j, w = compact_weights(dense)
        offsets = np.array([[-WIDTH/2, 0, sign*THICKNESS/2], [WIDTH/2, 0, sign*THICKNESS/2],
                            [-WIDTH/2, 0, -sign*THICKNESS/2], [WIDTH/2, 0, -sign*THICKNESS/2]])
        points = (centers[:, None]+offsets).reshape(-1, 3)
        joint, weight = np.repeat(j, 4, axis=0), np.repeat(w, 4, axis=0)
        triangles = []
        for row in range(ROWS-1):
            for a, b in [(0, 1), (1, 3), (3, 2), (2, 0)]:
                v = row*4+a
                q = row*4+b
                triangles += [[v, q, q+4], [v, q+4, v+4]]
        triangles += [[0, 2, 3], [0, 3, 1], [4*(ROWS-1), 4*(ROWS-1)+1, 4*(ROWS-1)+3],
                      [4*(ROWS-1), 4*(ROWS-1)+3, 4*(ROWS-1)+2]]
        triangles = np.array(triangles)
        if sign > 0:
            triangles = triangles[:, ::-1]
        straps.append({'name': f'{side}_{facing}', 'points': points, 'faces': triangles,
                       'joints': joint, 'weights': weight, 'top': top, 'bottom': bottom,
                       'top_weight': top_weight, 'bottom_weight': bottom_weight,
                       'top_morph': top_morph, 'bottom_morph': bottom_morph,
                       'top_face': triangle.copy(), 'top_barycentric': bary.copy(),
                       'bottom_vertices': stud.copy(), 'boot_mesh': boot_index,
                       'sign': sign, 'skin_faces': skin_faces})


def pose_point(point, dense, matrices):
    return np.einsum('b,bij,j->i', dense, matrices, np.r_[point, 1])[:3]


for strap in straps:
    p, j, w = strap['points'], strap['joints'], strap['weights']
    blended = np.einsum('nk,nkij->nij', w, middle_matrices[j])
    inverse = np.linalg.inv(blended[:, :3, :3])
    body = np.einsum('nb,bij,nj->ni', bw, middle_matrices, np.c_[bp, np.ones(len(bp))])[:, :3]
    surface = BVHTree.FromPolygons([Vector(v) for v in body], strap['skin_faces'].tolist())
    top = pose_point(strap['top']+strap['top_morph'], strap['top_weight'], middle_matrices)
    bottom = pose_point(strap['bottom']+strap['bottom_morph'], strap['bottom_weight'], middle_matrices)
    target = []
    for row, t in enumerate(np.linspace(0, 1, ROWS)):
        p0 = top*(1-t)+bottom*t
        linear = blended[row*4, :3, :3]
        outward = unit(linear @ np.array([0., 0., float(strap['sign'])]))
        across = unit(linear @ np.array([1., 0., 0.]))
        if 0 < t < 1:
            hit, _, _, distance = surface.ray_cast(Vector(p0+outward*.2), Vector(-outward), .4)
            if hit is not None and distance-.2 < .004:
                p0 += outward*(.004-(distance-.2))
        target.extend([p0-across*WIDTH/2+outward*THICKNESS/2, p0+across*WIDTH/2+outward*THICKNESS/2,
                       p0-across*WIDTH/2-outward*THICKNESS/2, p0+across*WIDTH/2-outward*THICKNESS/2])
    target = np.array(target)
    strap['seated'] = np.einsum('nij,nj->ni', inverse, target-blended[:, :3, 3])
    for sitting, samples in [(False, fitting_frames), (True, seated_frames[::10])]:
        positions = strap['seated'] if sitting else strap['points']
        cached = []
        for _, matrices in samples:
            skin_points = np.einsum('nb,bij,nj->ni', bw, matrices, np.c_[bp, np.ones(len(bp))])[:, :3]
            linear = np.einsum('nk,nkij->nij', w, matrices[j])
            cached.append((BVHTree.FromPolygons([Vector(v) for v in skin_points], strap['skin_faces'].tolist()),
                           linear[:, :3, :3], linear[:, :3, 3], np.linalg.inv(linear[:, :3, :3])))
        for iteration in range(16):
            correction = np.zeros((ROWS, 3))
            worst = np.zeros(ROWS)
            for surface, linear, translation, inverse in cached:
                posed = np.einsum('nij,nj->ni', linear, positions)+translation
                for row in range(1, ROWS-1):
                    for k in range(4):
                        i = row*4+k
                        hit, normal, _, _ = surface.find_nearest(Vector(posed[i]))
                        gap = np.dot(posed[i]-np.array(hit), normal)
                        deficit = .003-gap
                        if deficit > worst[row]:
                            worst[row] = deficit
                            correction[row] = inverse[i] @ (np.array(normal)*deficit)
            if worst.max() < .00015:
                break
            positions += np.repeat(correction, 4, axis=0)*.8
        print(json.dumps({'strap': strap['name'], 'sitting': sitting, 'remaining_deficit_m': float(worst.max())}), flush=True)

leather_points, leather_seated, leather_faces, leather_joints, leather_weights = [], [], [], [], []
metal_points, metal_seated, metal_faces, metal_joints, metal_weights = [], [], [], [], []


def box(center, across, along, outward, size):
    frame = np.column_stack([across, along, outward])
    cube = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                     [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]])*np.array(size)/2
    indices = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
                        [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    if np.linalg.det(frame) < 0:
        indices = indices[:, ::-1]
    return cube @ frame.T+center, indices


for strap in straps:
    offset = sum(len(p) for p in leather_points)
    leather_faces.append(strap['faces']+offset)
    leather_points.append(strap['points'])
    leather_seated.append(strap['seated'])
    leather_joints.append(strap['joints'])
    leather_weights.append(strap['weights'])
    row = 7
    j, w = strap['joints'][row*4], strap['weights'][row*4]
    blend = np.einsum('k,kij->ij', w, middle_matrices[j])
    inverse = np.linalg.inv(blend[:3, :3])
    configurations = []
    for positions, matrices in [(strap['points'], np.tile(np.eye(4), (65, 1, 1))), (strap['seated'], middle_matrices)]:
        posed = deform(positions, strap['joints'], strap['weights'], matrices).reshape(ROWS, 4, 3)
        center = posed[row].mean(0)
        across = unit(posed[row, 1]-posed[row, 0])
        along = unit(posed[row+1].mean(0)-posed[row-1].mean(0))
        outward = unit(posed[row, 0]-posed[row, 2])
        center += outward*.0024
        boxes = []
        for dx, dy, size in [(-.008, 0, (.0018, .014, .0023)), (.008, 0, (.0018, .014, .0023)),
                             (0, -.0061, (.018, .0018, .0023)), (0, .0061, (.018, .0018, .0023)),
                             (0, 0, (.012, .0013, .0016))]:
            boxes.append(box(center+across*dx+along*dy, across, along, outward, size))
        configurations.append(boxes)
    for (positions, indices), (seat, _) in zip(*configurations):
        offset = sum(len(p) for p in metal_points)
        metal_points.append(positions)
        metal_seated.append((seat-blend[:3, 3]) @ inverse.T)
        metal_faces.append(indices+offset)
        metal_joints.append(np.tile(j, (len(positions), 1)))
        metal_weights.append(np.tile(w, (len(positions), 1)))

doc = copy.deepcopy(source_doc)
doc['accessors'] = []
doc['bufferViews'] = []
binary = bytearray()
for key in ['images', 'textures', 'samplers']:
    doc.pop(key, None)
doc['skins'][0]['inverseBindMatrices'] = add_accessor(doc, binary,
    accessor(source_doc, source_raw, source_doc['skins'][0]['inverseBindMatrices']), 'MAT4')
color = np.array(json.loads((BOOTS.parent / 'fitting.json').read_text())['parts'][0]['leather_color_srgb'])/255
color = np.where(color <= .04045, color/12.92, ((color+.055)/1.055)**2.4)
leather = {'name': 'rogue_garter_black_leather', 'pbrMetallicRoughness': {
    'baseColorFactor': [*color.tolist(), 1], 'metallicFactor': 0, 'roughnessFactor': .55}}
doc['materials'] = [leather, {'name': 'rogue_garter_silver_adjusters',
    'pbrMetallicRoughness': {'baseColorFactor': [.48, .50, .52, 1], 'metallicFactor': .85, 'roughnessFactor': .28}}]
doc['meshes'] = []
for index, (name, p, sit, f, j, w) in enumerate([
    ('garters_female_rogue_leather', leather_points, leather_seated, leather_faces, leather_joints, leather_weights),
    ('garters_female_rogue_metal', metal_points, metal_seated, metal_faces, metal_joints, metal_weights)]):
    p, sit, f, j, w = map(np.concatenate, (p, sit, f, j, w))

    def normals(positions):
        result = np.zeros_like(positions)
        face_normals = np.cross(positions[f[:, 1]]-positions[f[:, 0]], positions[f[:, 2]]-positions[f[:, 0]])
        for corner in range(3):
            np.add.at(result, f[:, corner], face_normals)
        return unit(result)

    normal, seat_normal = normals(p), normals(sit)
    attributes = {'POSITION': add_accessor(doc, binary, p, 'VEC3'),
                  'NORMAL': add_accessor(doc, binary, normal, 'VEC3'),
                  'JOINTS_0': add_accessor(doc, binary, j, 'VEC4', 5123),
                  'WEIGHTS_0': add_accessor(doc, binary, w, 'VEC4')}
    if index == 0:
        uv = np.array([[u, row/(ROWS-1)] for _ in straps for row in range(ROWS) for u in [0, 1, 0, 1]])
        attributes['TEXCOORD_0'] = add_accessor(doc, binary, uv, 'VEC2')
    doc['meshes'].append({'name': name, 'weights': [0], 'extras': {'targetNames': ['pose_sit_idle']},
        'primitives': [{'attributes': attributes, 'indices': add_accessor(doc, binary, f.reshape(-1, 1), 'SCALAR', 5123),
                        'material': index, 'targets': [{'POSITION': add_accessor(doc, binary, sit-p, 'VEC3'),
                                                      'NORMAL': add_accessor(doc, binary, seat_normal-normal, 'VEC3')}]}]})
    doc['nodes'][index].update(name=name, extras={'rig_id': 'human_female_01_local_v1', 'part_id': 'garters_female_rogue'})
doc['scenes'][0]['extras'].pop('heel_pose', None)
doc['buffers'][0]['byteLength'] = len(binary)
write_glb(OUTPUT / 'garters_female_rogue.glb', doc, binary)
report = {'date': '2026-10-26', 'revision': 'v1', 'strap_count': 4, 'width_m': WIDTH, 'thickness_m': THICKNESS,
          'triangles': sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives']),
          'sources': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [BODY, SKIRT, BOOTS]},
          'anchors': [{k: value.tolist() if isinstance(value, np.ndarray) else value for k, value in s.items()
                       if k in ['name', 'top', 'bottom', 'top_weight', 'bottom_weight', 'top_morph', 'bottom_morph',
                                'top_face', 'top_barycentric', 'bottom_vertices', 'boot_mesh']} for s in straps],
          'method': 'Four modeled leather ribbons with silver adjusters. Skin weights blend between actual skirt hem, thigh skin and boot cuff; sitting shape follows the accepted skirt and boot correctives.',
          'no_new_api_requests': True}
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if k != 'anchors'}), flush=True)

bpy.ops.wm.open_mainfile(filepath=str(BOOTS.parent / 'female-rogue-boots-fitted.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.pose.bones.get('Hips'))
reference = bpy.data.objects['boots_female_rogue_right']
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(OUTPUT / 'garters_female_rogue.glb'), bone_heuristic='TEMPERANCE')
imported = set(bpy.data.objects)-before
for obj in imported:
    if obj.type == 'MESH':
        obj.parent = rig
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = rig
        obj.data.shape_keys.animation_data_create()
        obj.data.shape_keys.animation_data.action = reference.data.shape_keys.animation_data.action
for obj in imported:
    if obj.type == 'ARMATURE':
        bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'female-rogue-garters.blend'))
