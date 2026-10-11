"""Fit bard trousers and repair the contaminated front belt UVs."""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import factorized
from scipy.spatial import cKDTree

from lib.glb import view_bytes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/items/bard_starter/tripo_pants_v1/source.glb'
OUTPUT = ROOT / 'assets/modular_human_male_01/bard/tripo_pants_v1'
spec = importlib.util.spec_from_file_location('pants', ROOT / 'tools/fit-tripo-pants.py')
pants = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pants)
fit, io = pants.fit, pants.io
BELT_FACES = np.array([893, 894, 895, 896, 909, 910, 975, 976, 979, 980, 985, 986, 2117, 2118])
BELT_RIM_FACES = np.array([313, 891, 892, 897, 898, 911, 912, 973, 974, 981, 982,
    2113, 2114, 2115, 2116, 318, 913, 914, 915, 916, 923, 924, 977, 978, 983, 984,
    987, 988, 2141, 2142, 2201, 2202,
    68, 69, 70, 72, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780,
    783, 784, 785, 786, 787, 788, 901, 902, 903, 904, 905, 906, 907, 908,
    917, 918, 919, 920])


def belt_uv(original, uv, faces):
    top = np.array([410, 403, 428, 476, 481, 484, 1993, 2141])
    bottom = np.array([390, 374, 401, 474, 478, 1949, 1952, 2092])
    centers = (original[top] + original[bottom]) / 2
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(centers, axis=0), axis=1))]
    along = distance / distance[-1]
    rows = 1130 + 260 * along
    left = np.interp(rows, [1130, 1230, 1320, 1390], [875, 871, 871, 877])
    right = np.interp(rows, [1130, 1230, 1320, 1390], [930, 929, 931, 937])
    donor = np.concatenate([np.column_stack([left, rows]), np.column_stack([right, rows])]) / 2048
    selected = np.r_[top, bottom, 426, 399]
    donor = np.concatenate([donor, donor[[2, len(top) + 2]]])
    vertex_map = np.r_[np.arange(len(original)), selected]
    repaired_uv = np.concatenate([uv, donor.astype(uv.dtype)])
    remap = {int(old): len(original) + i for i, old in enumerate(selected)}
    repaired_faces = faces.copy()
    repaired_faces[BELT_FACES] = [[remap[int(v)] for v in face] for face in faces[BELT_FACES]]
    return vertex_map, repaired_uv, repaired_faces


def record(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=fit.digest(path))


def initial_fit(points):
    result = points.astype(float).copy()
    result[:, 1] = np.interp(points[:, 1], [0, .40, .73, .99951171875], [.181, .553, .87, 1.15])
    waist = io.smoothstep((result[:, 1] - .90) / .18)
    result[:, 0] *= .85 + .23 * waist
    result[:, 2] = points[:, 2] * (.95 + .20 * waist) - .027
    return result


def fit_seat_weights(points, joints, weights):
    path = ROOT / 'assets/modular_human_male_01/fitted/pants_plate.glb'
    reference, raw = fit.read_glb(path)
    names = [reference['nodes'][node]['name'] for node in reference['skins'][0]['joints']]
    positions, faces, dense = [], [], []
    for mesh in reference['meshes']:
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            vertices = io.accessor(reference, raw, attrs['POSITION'])
            indices = io.accessor(reference, raw, primitive['indices']).reshape(-1, 3)
            skin = io.accessor(reference, raw, attrs['JOINTS_0'])
            values = io.accessor(reference, raw, attrs['WEIGHTS_0'])
            mapped = np.array([fit.NAMES.index(name) for name in names])[skin]
            influence = np.zeros((len(vertices), len(fit.NAMES)))
            np.add.at(influence, (np.arange(len(vertices))[:, None], mapped), values)
            faces.extend(indices + len(positions))
            positions.extend(vertices)
            dense.extend(influence)
    amount = io.smoothstep((points[:, 1] - .80) / .08)
    amount *= 1 - io.smoothstep((points[:, 1] - 1.015) / .07)
    selected = np.flatnonzero(amount > 0)
    _, _, target = fit.nearest_surface(points[selected],
        (np.asarray(positions), np.asarray(faces), np.asarray(dense)), candidates=96)
    hip = target[:, fit.NAMES.index('Hips')].copy()
    left = io.smoothstep((points[selected, 0] + .075) / .15)
    target[:] = 0
    target[:, fit.NAMES.index('Hips')] = hip
    target[:, fit.NAMES.index('LeftUpLeg')] = (1 - hip) * left
    target[:, fit.NAMES.index('RightUpLeg')] = (1 - hip) * (1 - left)
    current = np.zeros_like(target)
    np.add.at(current, (np.arange(len(selected))[:, None], joints[selected]), weights[selected])
    blend = amount[selected, None]
    joints[selected], weights[selected] = pants.compact_weights(current * (1 - blend) + target * blend)
    return dict(reference=record(path), affected_welded_vertices=len(selected),
        method='Barycentric plate-trouser pelvis influence around the entire hip, with smooth left/right thigh sharing and blends at waist and thighs')


def main():
    assert fit.digest(SOURCE) == 'ad7fbb83f55dfdd32c3e14272983b26dea422e0a46ecf1b4a7b2644d2c094c82'
    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc, raw = fit.read_glb(SOURCE)
    primitive = doc['meshes'][0]['primitives'][0]
    original = io.accessor(doc, raw, primitive['attributes']['POSITION'])
    uv = io.accessor(doc, raw, primitive['attributes']['TEXCOORD_0'])
    faces = io.accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    images = [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    source_points, inverse = np.unique(original, axis=0, return_inverse=True)
    welded_faces = inverse[faces]
    edges = np.unique(np.sort(np.concatenate([welded_faces[:, [0, 1]],
        welded_faces[:, [1, 2]], welded_faces[:, [2, 0]]]), axis=1), axis=0)
    rows, cols = np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]]
    adjacency = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(source_points),) * 2)
    count, component = connected_components(adjacency)
    assert count == 3
    main_component = component == np.bincount(component).argmax()
    points = initial_fit(source_points)
    points, cuffs = pants.fit_cuffs(points, welded_faces)
    points, waist = pants.fit_waist(points, welded_faces, main_component, maximum_y=1.09, clearance=.009)
    aligned = points.copy()
    laplacian = sparse.diags(np.asarray(adjacency.sum(1)).ravel()) - adjacency
    smoother = factorized((sparse.eye(len(points)) + .7 * laplacian).tocsc())
    iterations = []
    for step in range(30):
        correction = np.zeros_like(points)
        correction[main_component], clearance = pants.surface_clearance(
            points[main_component], ('legs', 'ankles', 'feet', 'torso'))
        delta = smoother(correction)
        points += delta
        iterations.append(dict(step=step, minimum_signed_distance_m=float(clearance.min()),
                               maximum_correction_m=float(np.linalg.norm(delta, axis=1).max())))
    points, face_clearance = pants.clear_faces(points, welded_faces, main_component, smoother,
        fixed_below=.12, regions=('legs', 'ankles', 'feet', 'torso'))
    for side, sign in [('Left', 1), ('Right', -1)]:
        center, axis, _, _, _ = fit.ankle_interface(side)
        selected = (points[:, 0] * sign > 0) & (points[:, 1] < .40)
        offset = points[selected] - center
        radial = offset - (offset @ axis)[:, None] * axis
        ease = .004 * (1 - io.smoothstep((points[selected, 1] - .29) / .11))
        points[selected] += io.unit(radial) * ease[:, None]
    main_indices = np.flatnonzero(main_component)
    for group in np.unique(component[~main_component]):
        selected = component == group
        neighbors = cKDTree(aligned[main_component]).query(aligned[selected], k=8)[1]
        points[selected] = aligned[selected] + np.mean((points - aligned)[main_indices[neighbors]], axis=1)
    joints, weights = pants.skin_weights(points, adjacency, np.ones(len(points), dtype=bool))
    seat = fit_seat_weights(points, joints, weights)
    accessories = []
    for group in np.unique(component[~main_component]):
        selected = component == group
        bone = 'LeftUpLeg' if source_points[selected, 1].mean() < .70 else 'Hips'
        if bone == 'Hips':
            neighbors = cKDTree(points[main_component]).query(points[selected].mean(0), k=8)[1]
            nearest = main_indices[neighbors]
            dense = np.zeros((1, len(fit.NAMES)))
            np.add.at(dense[0], joints[nearest].ravel(), weights[nearest].ravel() / len(nearest))
            joints[selected], weights[selected] = pants.compact_weights(dense)
        else:
            joints[selected] = 0
            weights[selected] = 0
            joints[selected, 0] = fit.NAMES.index(bone)
            weights[selected, 0] = 1
        accessories.append(dict(component=int(group), vertices=int(selected.sum()),
            attachment='Average of eight nearest cloth weights' if bone == 'Hips' else bone))
    belt_vertices = np.unique(welded_faces[np.r_[BELT_FACES, BELT_RIM_FACES]])
    belt_ease = .012 * np.minimum(io.smoothstep((source_points[belt_vertices, 0] + .21) / .035),
                                 io.smoothstep((.11 - source_points[belt_vertices, 0]) / .045))
    points[belt_vertices, 2] += belt_ease
    binary = bytearray(raw)
    positions = points[inverse]
    normals = io.smooth_normals(positions, faces)
    vertex_map, repaired_uv, repaired_faces = belt_uv(original, uv, faces)
    primitive['attributes'].update(io.add_skin_attributes(doc, binary, positions[vertex_map], normals[vertex_map],
                                                        joints[inverse][vertex_map], weights[inverse][vertex_map]))
    primitive['attributes']['TEXCOORD_0'] = io.add_accessor(doc, binary, repaired_uv, 'VEC2')
    primitive['indices'] = io.add_accessor(doc, binary, repaired_faces.reshape(-1), 'SCALAR', 5123)
    if 'TANGENT' in primitive['attributes']:
        primitive['attributes']['TANGENT'] = io.add_accessor(doc, binary,
            io.tangents(positions[vertex_map], normals[vertex_map], repaired_uv, repaired_faces), 'VEC4')
    doc['meshes'][0]['name'] = 'pants_bard_tripo'
    fit.with_rig(doc, binary, 'pants_bard', 'tripo_bard_pants_v1')
    binary = io.compact(doc, binary)
    target = OUTPUT / 'pants_bard.glb'
    fit.write_glb(target, doc, binary)
    assert np.array_equal(uv, repaired_uv[:len(uv)])
    assert np.array_equal(faces, vertex_map[repaired_faces])
    assert images == [view_bytes(doc, binary, image['bufferView']) for image in doc['images']]
    report = dict(date='2026-10-11', status='Fitted and rigged candidate; animation and visual checks follow',
        source=record(SOURCE), base=record(ROOT / 'assets/modular_human_male_01/fitted/base.glb'),
        interfaces=record(ROOT / 'assets/modular_human_male_01/interfaces/v1/interfaces.json'),
        rig_id='human_male_01_mixamo_candidate_v2', source_triangles=len(faces),
        seat_rigging=seat,
        preserved_source_triangles_and_embedded_texture=True,
        belt_uv_repair=dict(faces=BELT_FACES.tolist(), duplicated_vertices=len(vertex_map) - len(original),
            donor='Existing leather strip in the original 2048px atlas, rows 1130–1390',
            unchanged='All other face UVs, skinning and embedded JPEG'),
        belt_clearance=dict(maximum_forward_ease_m=.012, welded_vertices=len(belt_vertices),
            reason='Fitted cloth intersected the front diagonal belt; ease the belt and its thickness rims together'),
        anatomical_mapping=dict(source_y=[0, .40, .73, .99951171875], target_y_m=[.181, .553, .87, 1.15]),
        cuffs=cuffs, waist=waist, ankle_connections=pants.ankle_references(),
        ankle_motion_ease=dict(radial_m=.004, fade_y_m=[.29, .40],
            reason='Right ankle skin crossed the cuff by 2mm in sampled slash pose; preserve source topology'),
        detached_accessories=accessories, clearance_iterations=iterations, face_clearance=face_clearance,
        validation=fit.validate(target))
    (ROOT / 'doc/assets/modular-bard-tripo-pants-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['validation'], indent=2))


if __name__ == '__main__':
    main()
