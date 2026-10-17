"""Fit mirrored bracers to both female forearms."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb, view_bytes
from lib.glb_accessors import accessor, add_accessor
from outfits.rogue_layers import wrist_section

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bracers/tripo_v1'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v1'
REPORT = ROOT / 'doc/assets/modular-female-barbarian-bracers-fitting-v1.json'
spec = importlib.util.spec_from_file_location('plate_io', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)
WRIST_OFFSET = .0117
LENGTH = .153
CLEARANCE = .00396
SOFTNESS = .00144
HIDE_MARGIN = .0072
# Tripo's plate faces +X; the wrist is at -Y.
SOURCE_BASIS = np.array([[0, 0, -1], [1, 0, 0]], dtype=float)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup_body():
    doc, raw = read_glb(BODY)
    skin = doc['skins'][0]
    names = [doc['nodes'][i]['name'] for i in skin['joints']]
    bind = accessor(doc, raw, skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    bones = dict(zip(names, np.linalg.inv(bind)[:, :3, 3]))
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = accessor(doc, raw, attrs['POSITION']).astype(float)
    faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    dense = np.zeros((len(points), len(names)))
    np.add.at(dense, (np.arange(len(points))[:, None], accessor(doc, raw, attrs['JOINTS_0'])), accessor(doc, raw, attrs['WEIGHTS_0']))
    return doc, raw, names, bones, points, faces, dense


def frame(bones, side):
    wrist = bones[side + 'Hand']
    axis = io.unit(bones[side + 'ForeArm'] - wrist)
    width = bones[side + 'HandIndex1'] - bones[side + 'HandPinky1']
    dorsal = np.cross(bones[side + 'HandMiddle1'] - wrist, width)
    dorsal = io.unit(dorsal - axis * np.dot(dorsal, axis))
    if side == 'Left':
        dorsal = -dorsal
    across = np.cross(dorsal, -axis)
    if side == 'Left':
        across = -across
    return wrist, axis, np.array([across, dorsal])


def fit_side(points, faces, body_points, body_faces, arm_faces, bones, side):
    wrist, axis, basis = frame(bones, side)
    theta = np.arange(128) * 2 * np.pi / 128
    radial = np.column_stack([np.cos(theta), np.sin(theta)])
    low, high = points[:, 1].min(), points[:, 1].max()
    source_rows = np.linspace(low + .1, high - .1, 40)
    source_sections = [wrist_section(points[faces], np.array([0, y, 0]), np.array([0, 1., 0]), SOURCE_BASIS, radial, outermost=False)
                       for y in source_rows]
    source_centers = np.array([center for center, _ in source_sections])
    source_radii = np.array([radius for _, radius in source_sections])
    scale = LENGTH / (high - low)
    heights = WRIST_OFFSET + (points[:, 1] - low) * scale
    rows = np.linspace(heights.min(), heights.max(), 48)
    triangles = body_points[body_faces[arm_faces]]
    sections = [wrist_section(triangles, wrist + axis * h, axis, basis, radial) for h in rows]
    centers = np.array([center for center, _ in sections])
    radii = np.array([radius for _, radius in sections])
    source_center = np.column_stack([np.interp(points[:, 1], source_rows, source_centers[:, j]) for j in range(2)])
    cross = (points @ SOURCE_BASIS.T) - source_center
    angles = np.arctan2(cross[:, 1], cross[:, 0])

    def sample(table, levels, coordinates):
        values = np.array([np.interp(angles, theta, row, period=2 * np.pi) for row in table])
        return np.array([np.interp(c, levels, values[:, i]) for i, c in enumerate(coordinates)])

    depth = (np.linalg.norm(cross, axis=1) - sample(source_radii, source_rows, points[:, 1])) * scale
    offset = CLEARANCE + SOFTNESS * np.logaddexp(0, depth / SOFTNESS)
    radius = sample(radii, rows, heights) + offset
    center = np.column_stack([np.interp(heights, rows, centers[:, j]) for j in range(2)])
    fitted = wrist + heights[:, None] * axis
    fitted += (center + radius[:, None] * np.column_stack([np.cos(angles), np.sin(angles)])) @ basis
    skin_radius = sample(radii, rows, heights)
    return fitted, dict(wrist=wrist.tolist(), axis=axis.tolist(), basis=basis.tolist(), scale=float(scale),
        axial_interval_m=[float(heights.min()), float(heights.max())],
        forearm_length_m=float(np.linalg.norm(bones[side + 'ForeArm'] - wrist)),
        minimum_offset_m=float(offset.min()), maximum_offset_m=float(offset.max()),
        rest_skin_gap_min_m=float((radius - skin_radius).min()))


def hidden_skin(body_points, body_faces, arm_vertices, bones, side, interval):
    wrist, axis, _ = frame(bones, side)
    along = (body_points - wrist) @ axis
    inside = arm_vertices & (along > interval[0] + HIDE_MARGIN) & (along < interval[1] - HIDE_MARGIN)
    return inside[body_faces].all(1)


def attach_rig(doc, raw, base, base_raw, sides):
    ids = base['skins'][0]['joints']
    remap = {old: i for i, old in enumerate(ids)}
    doc['nodes'] = [copy.deepcopy(base['nodes'][i]) for i in ids]
    for bone in doc['nodes']:
        if 'children' in bone:
            bone['children'] = [remap[i] for i in bone['children'] if i in remap]
    children = {child for bone in doc['nodes'] for child in bone.get('children', [])}
    armature = len(doc['nodes'])
    doc['nodes'].append({'name': 'Armature', 'children': [i for i in range(len(ids)) if i not in children], 'extras': {'rig_id': 'human_female_01_local_v1'}})
    doc['scenes'] = [{'nodes': [armature], 'extras': {'rig_id': 'human_female_01_local_v1'}}]
    doc['scene'] = 0
    skin = copy.deepcopy(base['skins'][0])
    skin['joints'] = [remap[i] for i in ids]
    skin['skeleton'] = remap[skin['skeleton']]
    skin['inverseBindMatrices'] = add_accessor(doc, raw, accessor(base, base_raw, skin['inverseBindMatrices']), 'MAT4')
    doc['skins'] = [skin]
    for i, side in enumerate(sides):
        doc['scenes'][0]['nodes'].append(len(doc['nodes']))
        doc['nodes'].append({'name': f'gloves_female_barbarian_{side.lower()}', 'mesh': i, 'skin': 0,
                             'extras': {'rig_id': 'human_female_01_local_v1', 'part_id': 'gloves_female_barbarian'}})
    doc.pop('animations', None)


def main():
    OUTPUT.mkdir(exist_ok=True)
    assert digest(SOURCE) == '458824b20bf340b427e781622894f34abcb96f270622b3a71d50109dd6ce5a9d'
    assert digest(BODY) == '3eb7c0a5f3c6b30aec0fbae0b70c8fd925e4cb91772647420007eee795a1e0a5'
    base, base_raw, names, bones, body_points, body_faces, dense = setup_body()
    doc, source_raw = read_glb(SOURCE)
    images = [view_bytes(doc, source_raw, image['bufferView']) for image in doc['images']]
    primitive = doc['meshes'][0]['primitives'][0]
    points = accessor(doc, source_raw, primitive['attributes']['POSITION']).astype(float)
    uv = accessor(doc, source_raw, primitive['attributes']['TEXCOORD_0'])
    faces = accessor(doc, source_raw, primitive['indices']).reshape(-1, 3)
    raw = bytearray(source_raw)
    doc['meshes'] = []
    sides, records, hide = ['Right', 'Left'], {}, np.zeros(len(body_faces), dtype=bool)
    for side in sides:
        arm = dense[:, [names.index(side + bone) for bone in ['Arm', 'ForeArm', 'Hand']]].sum(1)
        arm_faces = arm[body_faces].mean(1) > .5
        fitted, record = fit_side(points, faces, body_points, body_faces, arm_faces, bones, side)
        triangles = faces[:, ::-1] if side == 'Left' else faces
        normals = io.smooth_normals(fitted, triangles)
        joints = np.tile([names.index(side + 'ForeArm'), 0, 0, 0], (len(fitted), 1)).astype(np.uint16)
        weights = np.tile([1., 0, 0, 0], (len(fitted), 1))
        attrs = io.add_skin_attributes(doc, raw, fitted, normals, joints, weights)
        attrs['TEXCOORD_0'] = add_accessor(doc, raw, uv, 'VEC2')
        doc['meshes'].append({'name': f'gloves_female_barbarian_{side.lower()}', 'primitives': [{
            'attributes': attrs, 'material': primitive['material'],
            'indices': add_accessor(doc, raw, triangles.reshape(-1, 1).astype(np.uint32), 'SCALAR', 5125)}]})
        interval = np.array(record['axial_interval_m'])
        side_hide = hidden_skin(body_points, body_faces, arm > .99, bones, side, interval)
        hide |= side_hide
        records[side] = {**record, 'triangles': len(triangles), 'vertices': len(fitted), 'hidden_body_triangles': int(side_hide.sum())}
    attach_rig(doc, raw, base, base_raw, sides)
    raw = io.compact(doc, raw)
    assert images == [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    target = OUTPUT / 'gloves_female_barbarian.glb'
    write_glb(target, doc, raw)
    mask = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': digest(BODY), 'mesh_index': 0, 'primitive_index': 0,
            'primitive_triangles': len(body_faces), 'hide_triangle_indices': np.flatnonzero(hide).tolist(),
            'scope': f'Forearm skin fully inside each bracer, {HIDE_MARGIN * 1000:.1f} mm in from both openings; hands stay visible.'}
    (OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
    report = {'date': '2026-10-15', 'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': digest(SOURCE)},
              'body': {'path': str(BODY.relative_to(ROOT)), 'sha256': digest(BODY)},
              'output': {'path': str(target.relative_to(ROOT)), 'sha256': digest(target)},
              'rig_id': 'human_female_01_local_v1',
              'wrist_offset_m': WRIST_OFFSET, 'length_m': LENGTH,
              'clearance_m': CLEARANCE, 'sides': records, 'hidden_body_triangles': int(hide.sum()),
              'method': 'Map the source inner wall per height and angle onto 48 actual forearm sections plus clearance, keeping '
                        'relief above the inner wall at the uniform length scale. The source flare toward the elbow follows the forearm. '
                        'Left uses the mirrored frame on its own bones with reversed winding. Each bracer follows its ForeArm rigidly.',
              'original_topology_uv_and_embedded_textures_preserved': True, 'status': 'Candidate; preview-clip animation check passed (tools/validate-female-barbarian-bracers.mjs)'}
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({side: {k: records[side][k] for k in ['axial_interval_m', 'forearm_length_m', 'minimum_offset_m', 'maximum_offset_m', 'rest_skin_gap_min_m', 'hidden_body_triangles']} for side in sides}, indent=1))


if __name__ == '__main__':
    main()
