"""Fit the preserved bard top and transfer the canonical male rig."""
import importlib.util
import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import factorized
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import view_bytes
from outfits.rogue_layers import compact_weights
from outfits.radial_sections import radii, section_basis

spec = importlib.util.spec_from_file_location('modular_fit', ROOT / 'tools/fit-modular-rogue.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
io = fit.io
OUTPUT = ROOT / 'assets/modular_human_male_01/bard/tripo_top_v1'
SOURCE = ROOT / 'assets/items/bard_starter/tripo_top_v1/source.glb'
TORSO_SCALE = [1.02, .95, .80]
TORSO_OFFSET = [0, .94, -.035]


def align(original):
    points = original * TORSO_SCALE + TORSO_OFFSET
    edge = np.interp(original[:, 1], [0, .25, .45, .60, .76], [.27, .22, .19, .16, .12])
    sleeve = io.smoothstep((abs(original[:, 0]) - edge) / .045)
    for side, sign in [('Left', 1), ('Right', -1)]:
        start = np.array([sign * .23, .575, .0])
        end = np.array([sign * .464, .19, .095])
        target_start = fit.BONES[side + 'Arm'] + [0, .025, 0]
        target_end = fit.BONES[side + 'Hand'] + [0, .012, 0]
        axis, target_axis = io.unit(end - start), io.unit(target_end - target_start)
        radial = io.unit(np.cross(axis, [0, 0, 1]))
        target_radial = io.unit(np.cross(target_axis, [0, 0, 1]))
        depth, target_depth = np.cross(axis, radial), np.cross(target_axis, target_radial)
        local = original - start
        along = (local @ axis) / np.linalg.norm(end - start)
        target = target_start + along[:, None] * (target_end - target_start)
        radius = np.interp(along, [0, .55, 1], [.95, .85, .72])
        target += (local @ radial)[:, None] * target_radial * radius[:, None]
        target += (local @ depth)[:, None] * target_depth * radius[:, None]
        amount = sleeve * (original[:, 0] * sign > 0)
        points += (target - points) * amount[:, None]
    return points, sleeve


def fit_openings(points, faces, source):
    body, body_faces, _ = fit.body_surface(('neck', 'upper_arms', 'forearms', 'hands'))
    interfaces = json.loads((ROOT / 'assets/modular_human_male_01/interfaces/v1/interfaces.json').read_text())
    records = []
    for entry in interfaces['interfaces']:
        name = entry['name']
        if name not in ['neck_base', 'glove_short_Left', 'glove_short_Right']:
            continue
        center, axis = np.array(entry['center']), np.array(entry['normal'])
        axis = io.unit(axis)
        basis, second = section_basis(axis)
        if name == 'neck_base':
            mask = (source[:, 1] > .67) & (abs(source[:, 0]) < .14)
            stations = np.linspace(-.02, .095, 24)
            limit = .18
            margin = .006
        else:
            sign = 1 if name.endswith('Left') else -1
            mask = source[:, 0] * sign > .32
            stations = np.linspace(-.065, .20, 40)
            limit = .12
            margin = .014
        original = points.copy()
        inners = [radii(body[body_faces], center + axis * offset, axis, limit) for offset in stations]
        for _ in range(4):
            profiles = []
            for offset, inner in zip(stations, inners):
                outer = radii(points[faces], center + axis * offset, axis, limit)
                valid = np.isfinite(inner) & np.isfinite(outer) & (outer > .005)
                scale = np.ones(64)
                scale[valid] = np.maximum((inner[valid] + margin) / outer[valid], 1)
                profiles.append(np.minimum(scale, 1.7))
            profiles = np.asarray(profiles)
            along = (points - center) @ axis
            radial = points - center - along[:, None] * axis
            theta = np.arctan2(radial @ second, radial @ basis) % (2 * np.pi)
            angles = np.linspace(0, 2 * np.pi, 65)
            scale = np.ones(len(points))
            for index in np.flatnonzero(mask):
                angular = [np.interp(theta[index], angles, np.r_[row, row[0]]) for row in profiles]
                scale[index] = np.interp(along[index], stations, angular)
            if name == 'neck_base':
                blend = io.smoothstep((source[:, 1] - .67) / .035)
            else:
                blend = io.smoothstep((abs(source[:, 0]) - .32) / .075)
            points += radial * ((scale - 1) * blend)[:, None]
        records.append(dict(interface=name, margin_m=margin, iterations=4,
                            maximum_displacement_m=float(np.linalg.norm(points - original, axis=1).max())))
    return records


def outer_faces(points, faces):
    triangles = points[faces]
    centers = triangles.mean(1)
    normals = io.unit(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]))
    remove = np.zeros(len(faces), dtype=bool)
    for sign in [-1, 1]:
        start = np.array([sign * .23, .575, .0])
        end = np.array([sign * .464, .19, .099])
        axis = io.unit(end - start)
        along = (centers - start) @ axis
        radial = centers - start - along[:, None] * axis
        radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-8)
        cuff = (centers[:, 0] * sign > .41) & (centers[:, 1] < .255)
        inward = np.sum(normals * radial, axis=1) < -.15
        cap = (normals @ axis > .65) & (along > np.linalg.norm(end - start) * .94)
        remove |= cuff & (inward | cap)
    collar = (centers[:, 1] > .69) & (abs(centers[:, 0]) < .055) & (centers[:, 2] < .09)
    remove |= collar & (np.ptp(triangles, axis=1).max(1) > .032) & (normals[:, 1] > .5)
    return ~remove


def refine_wrist_motion(points, faces, weights, source):
    path = OUTPUT / 'validation-poses.json'
    poses = json.loads(path.read_text())
    animation = json.loads((ROOT / 'doc/assets/modular-bard-tripo-top-animation-v1.json').read_text())
    inputs = [entry for entry in animation['sources'] if entry['path'] != str((OUTPUT / 'top_bard.glb').relative_to(ROOT))]
    for entry in inputs:
        assert fit.digest(ROOT / entry['path']) == entry['sha256']
    interfaces = json.loads((ROOT / 'assets/modular_human_male_01/interfaces/v1/interfaces.json').read_text())
    body, body_faces, body_weights = fit.body_surface(('forearms', 'hands'))
    body_homogeneous = np.column_stack([body, np.ones(len(body))])
    sides = {sign: (faces[source[faces].mean(1)[:, 0] * sign > .32], body_faces[body[body_faces].mean(1)[:, 0] * sign > .20])
             for sign in [1, -1]}
    original = points.copy()
    counts = []
    for _ in range(4):
        corrections = np.zeros_like(points)
        hits = np.zeros(len(points))
        for pose in poses:
            matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
            transforms = np.einsum('vb,bij->vij', weights, matrices)
            posed = np.einsum('vij,vj->vi', transforms, np.column_stack([points, np.ones(len(points))]))[:, :3]
            skin = np.einsum('vij,vj->vi', np.einsum('vb,bij->vij', body_weights, matrices), body_homogeneous)[:, :3]
            for entry in interfaces['interfaces']:
                if not entry['name'].startswith('glove_short_'):
                    continue
                side = entry['name'].rsplit('_', 1)[1]
                sleeve_faces, arm_faces = sides[1 if side == 'Left' else -1]
                matrix = matrices[fit.NAMES.index(side + 'ForeArm')]
                axis = io.unit(matrix[:3, :3] @ np.array(entry['normal']))
                center = (matrix @ np.r_[entry['center'], 1])[:3]
                basis, second = section_basis(axis)
                for offset in [0, .015, .030]:
                    origin = center + axis * offset
                    outer, indices = radii(posed[sleeve_faces], origin, axis, .12, return_faces=True)
                    inner = radii(skin[arm_faces], origin, axis, .12)
                    valid = np.isfinite(outer) & np.isfinite(inner)
                    bad = np.flatnonzero(valid & (outer < inner + .002))
                    for ray in bad:
                        theta = ray * 2 * np.pi / 64
                        delta = (basis * np.cos(theta) + second * np.sin(theta)) * (inner[ray] + .003 - outer[ray])
                        vertices = sleeve_faces[indices[ray]]
                        for vertex in vertices:
                            corrections[vertex] += np.linalg.solve(transforms[vertex, :3, :3], delta)
                            hits[vertex] += 1
        changed = hits > 0
        counts.append(int(changed.sum()))
        if not changed.any():
            break
        points[changed] += corrections[changed] / hits[changed, None]
    return dict(pose_source=str(path.relative_to(ROOT)), pose_sha256=fit.digest(path), inputs=inputs,
                samples=len(poses), modified_vertex_counts=counts,
                maximum_displacement_m=float(np.linalg.norm(points - original, axis=1).max()))


def arm_segments(points, side):
    indices = [fit.NAMES.index(side + name) for name in ['Arm', 'ForeArm', 'Hand']]
    start, end = fit.BONES[side + 'Arm'], fit.BONES[side + 'Hand']
    along = ((points - start) @ (end - start)) / np.sum((end - start) ** 2)
    forearm = io.smoothstep((along - .30) / .40)
    hand = io.smoothstep((along - .94) / .12) * .35
    return indices, [1 - forearm, forearm * (1 - hand), forearm * hand]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refine-motion', action='store_true')
    args = parser.parse_args()
    base = ROOT / 'assets/modular_human_male_01/fitted/base.glb'
    source_hash, base_hash = fit.digest(SOURCE), fit.digest(base)
    assert source_hash == '22d3bdc0c7556595584e6526cfd84a896cd4549d705a45d1deecc350ef59394f'
    assert base_hash == '0e629865af6c3feac3a4444e0cb2d5f2d3861bf2350d643cbff0f9858b83535a'
    doc, raw = fit.read_glb(SOURCE)
    assert len(doc['meshes']) == 1 and len(doc['meshes'][0]['primitives']) == 1
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    original = io.accessor(doc, raw, attrs['POSITION']).astype(float)
    source_translation = doc['nodes'][0].get('translation', [0, 0, 0])
    original += source_translation
    faces = io.accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    uv = io.accessor(doc, raw, attrs['TEXCOORD_0'])
    textures = [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    _, first, inverse = np.unique(np.round(original, 5), axis=0, return_index=True, return_inverse=True)
    welded = original[first]
    points, sleeve = align(welded)
    welded_faces = inverse[faces]
    retained = outer_faces(welded, welded_faces)
    edges = np.unique(np.sort(np.concatenate([welded_faces[:, [0, 1]], welded_faces[:, [1, 2]], welded_faces[:, [2, 0]]]), axis=1), axis=0)
    rows, cols = np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]]
    adjacency = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(points), len(points)))
    laplacian = sparse.diags(np.asarray(adjacency.sum(1)).ravel()) - adjacency
    smooth = factorized((sparse.eye(len(points)) + .6 * laplacian).tocsc())
    _, components = connected_components(adjacency, directed=False)
    garment = components == np.bincount(components).argmax()
    texture = np.asarray(Image.open(BytesIO(textures[0])))
    face_uv = uv[faces].mean(1)
    pixels = texture[np.clip((face_uv[:, 1] * (texture.shape[0] - 1)).astype(int), 0, texture.shape[0] - 1),
                     np.clip((face_uv[:, 0] * (texture.shape[1] - 1)).astype(int), 0, texture.shape[1] - 1)].astype(float)
    centers = welded[welded_faces].mean(1)
    cape_faces = (pixels[:, 1] > pixels[:, 0] * 1.3)
    cape_faces &= (centers[:, 1] > .37) | ((centers[:, 2] < -.10) & (centers[:, 1] > .22))
    cape_faces &= abs(centers[:, 0]) < np.interp(centers[:, 1], [.22, .37, .50, .60, .76], [.27, .27, .29, .34, .10])
    counts = np.bincount(welded_faces.ravel(), minlength=len(points))
    cape = np.bincount(welded_faces[cape_faces].ravel(), minlength=len(points)) / np.maximum(counts, 1)
    leather_faces = (pixels[:, 0] > pixels[:, 1] * 1.25) & (abs(centers[:, 0]) < .24)
    leather_faces &= (centers[:, 1] > .19) & (centers[:, 1] < .60)
    leather = np.bincount(welded_faces[leather_faces].ravel(), minlength=len(points)) / np.maximum(counts, 1)
    leather = io.smoothstep(leather / .35)
    leather *= 1 - io.smoothstep((welded[:, 1] - .42) / .12)
    cape = np.clip(smooth(cape), 0, 1)
    cape *= 1 - io.smoothstep((welded[:, 1] - .66) / .06)
    drape = cape * (1 - io.smoothstep((welded[:, 1] - .43) / .10))
    torso_alignment = welded * TORSO_SCALE + TORSO_OFFSET
    points += (torso_alignment - points) * drape[:, None]
    sleeve *= 1 - drape
    aligned = points.copy()
    surface = fit.body_surface(('torso', 'neck', 'upper_arms', 'forearms', 'legs'))
    iterations = []
    for step in range(30):
        near, normals, _ = fit.nearest_surface(points, surface, candidates=96)
        signed = np.sum((points - near) * normals, axis=1)
        correction = normals * (np.clip(.008 - signed, 0, .012) * garment)[:, None]
        correction = np.column_stack([smooth(correction[:, i]) for i in range(3)])
        points += correction
        iterations.append(dict(step=step, minimum_signed_distance_m=float(signed[garment].min()),
                               maximum_correction_m=float(np.linalg.norm(correction, axis=1).max())))
    main_tree = cKDTree(aligned[garment])
    outward = np.column_stack([points[:, 0], np.zeros(len(points)), points[:, 2] + .035])
    outward /= np.maximum(np.linalg.norm(outward, axis=1, keepdims=True), 1e-8)
    points += outward * (.020 * cape)[:, None]
    openings = fit_openings(points, welded_faces[retained], welded)
    for component in np.unique(components[~garment]):
        mask = components == component
        near = main_tree.query(aligned[mask].mean(0), k=12)[1]
        points[mask] = aligned[mask] + (points[garment] - aligned[garment])[near].mean(0)
    dense = np.zeros((len(points), len(fit.NAMES)))
    for side, sign in [('Left', 1), ('Right', -1)]:
        indices, segments = arm_segments(points, side)
        amount = sleeve * (welded[:, 0] * sign > 0)
        dense[:, indices] = np.column_stack(segments) * amount[:, None]
    spine = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck']
    _, _, torso_weights = fit.nearest_surface(points, fit.body_surface(('torso', 'neck', 'legs')), candidates=96)
    torso_weights[:, [i for i, name in enumerate(fit.NAMES) if name not in spine]] = 0
    empty = torso_weights.sum(1) < 1e-8
    torso_weights[empty, fit.NAMES.index('Hips')] = 1
    torso_weights /= torso_weights.sum(1, keepdims=True)
    trunk = 1 - dense.sum(1)
    dense += torso_weights * trunk[:, None]
    mantle = drape * io.smoothstep((-welded[:, 2] - .055) / .055)
    dense *= (1 - mantle)[:, None]
    dense[:, fit.NAMES.index('Spine2')] += mantle
    edge_weights = 1 / np.maximum(np.linalg.norm(points[rows] - points[cols], axis=1), .001) ** 2
    weighted = sparse.csr_matrix((edge_weights, (rows, cols)), shape=adjacency.shape)
    weight_laplacian = sparse.diags(np.asarray(weighted.sum(1)).ravel()) - weighted
    fidelity = 2 + 100 * sleeve
    diffuse = factorized((sparse.diags(fidelity) + .012 * weight_laplacian).tocsc())
    dense = np.maximum(np.column_stack([diffuse(dense[:, i] * fidelity) for i in range(len(fit.NAMES))]), 0)
    for side, sign in [('Left', 1), ('Right', -1)]:
        indices, _ = arm_segments(points, side)
        dense[:, indices] *= io.smoothstep(points[:, 0] * sign / .12)[:, None]
    dense /= dense.sum(1, keepdims=True)
    dense = dense * (1 - leather)[:, None] + torso_weights * leather[:, None]
    _, _, underlying = fit.nearest_surface(points, (points, welded_faces[leather_faces], dense), candidates=64)
    back_layer = cape * io.smoothstep((-welded[:, 2] - .06) / .04)
    back_layer *= 1 - io.smoothstep((abs(welded[:, 0]) - .15) / .06)
    dense = dense * (1 - back_layer)[:, None] + underlying * back_layer[:, None]
    finish = factorized((sparse.eye(len(points)) + .0005 * weight_laplacian).tocsc())
    dense = np.maximum(np.column_stack([finish(dense[:, i]) for i in range(len(fit.NAMES))]), 0)
    dense /= dense.sum(1, keepdims=True)
    for side, sign in [('Left', 1), ('Right', -1)]:
        distal = io.smoothstep((welded[:, 0] * sign - .31) / .065)
        indices, segments = arm_segments(points, side)
        dense *= (1 - distal)[:, None]
        for index, value in zip(indices, segments):
            dense[:, index] += value * distal
        _, _, wrist_weights = fit.nearest_surface(points, fit.body_surface(('forearms', 'hands'), sign), candidates=64)
        allowed = [fit.NAMES.index(side + name) for name in ['ForeArm', 'Hand']]
        wrist_weights[:, [i for i in range(len(fit.NAMES)) if i not in allowed]] = 0
        empty = wrist_weights.sum(1) < 1e-8
        wrist_weights[empty, allowed[0]] = 1
        wrist_weights /= wrist_weights.sum(1, keepdims=True)
        cuff_blend = io.smoothstep((welded[:, 0] * sign - .35) / .055)
        dense = dense * (1 - cuff_blend)[:, None] + wrist_weights * cuff_blend[:, None]
    hem = garment & (welded[:, 1] < .19) & (abs(welded[:, 0]) < .28)
    amount = io.smoothstep((.19 - welded[:, 1]) / .12) * hem
    dense *= (1 - amount)[:, None]
    dense[:, fit.NAMES.index('Hips')] += amount
    for side, sign in [('Left', 1), ('Right', -1)]:
        leg_amount = amount * .55 * io.smoothstep((points[:, 0] * sign - .025) / .10)
        dense[:, fit.NAMES.index('Hips')] -= leg_amount
        dense[:, fit.NAMES.index(side + 'UpLeg')] += leg_amount
    ornaments = []
    for component in np.unique(components[~garment]):
        mask = components == component
        near = main_tree.query(aligned[mask].mean(0), k=12)[1]
        shared = dense[garment][near].mean(0)
        dense[mask] = shared / shared.sum()
        ornaments.append(dict(vertices=int(mask.sum()), shared_weights=True))
    joints, weights = compact_weights(dense)
    motion_fit = None
    if args.refine_motion:
        compact = np.zeros_like(dense)
        np.add.at(compact, (np.arange(len(points))[:, None], joints), weights)
        motion_fit = refine_wrist_motion(points, welded_faces[retained], compact, welded)
    positions = points[inverse]
    binary = bytearray(raw)
    attrs.update(io.add_skin_attributes(doc, binary, positions, io.smooth_normals(positions, faces), joints[inverse], weights[inverse]))
    primitive['indices'] = io.add_accessor(doc, binary, faces[retained].reshape(-1, 1), 'SCALAR', 5125)
    attrs.pop('TANGENT', None)
    doc['meshes'][0]['name'] = 'top_bard_tripo'
    fit.with_rig(doc, binary, 'top_bard', 'tripo_v1')
    binary = io.compact(doc, binary)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / 'top_bard.glb'
    fit.write_glb(target, doc, binary)
    exported = doc['meshes'][0]['primitives'][0]
    assert np.array_equal(uv, io.accessor(doc, binary, exported['attributes']['TEXCOORD_0']))
    assert np.array_equal(faces[retained], io.accessor(doc, binary, exported['indices']).reshape(-1, 3))
    assert textures == [view_bytes(doc, binary, image['bufferView']) for image in doc['images']]
    report = dict(date='2026-10-10', status='Fitted and rigged candidate; motion and clearance review pending',
                  source=dict(path=str(SOURCE.relative_to(ROOT)), sha256=source_hash),
                  base=dict(path=str(base.relative_to(ROOT)), sha256=base_hash),
                  rig_id='human_male_01_mixamo_candidate_v2', interfaces='interfaces/v1',
                  source_triangles=len(faces), preserved_uv_and_embedded_texture=True,
                  removed_inner_cuff_and_collar_faces=np.flatnonzero(~retained).tolist(),
                  alignment=dict(source_translation=source_translation, torso_scale=TORSO_SCALE,
                                 torso_offset=TORSO_OFFSET, sleeve_source_start=[.23, .575, 0],
                                 sleeve_source_end=[.464, .19, .095], sleeve_radius_scales=[.95, .85, .72]),
                  correction_iterations=iterations, clearance_target_m=.008,
                  opening_section_fitting=openings,
                  wrist_motion_refinement=motion_fit,
                  skinning=dict(torso='Barycentric transfer restricted to torso spine bones', sleeve_fidelity=100, diffusion=.012,
                                opposite_arm_influences_removed=True, hem_maximum_same_side_thigh_weight=.55,
                                leather_arm_influence_suppression=True,
                                cuffs='Same-side forearm and hand surface weights',
                                rigid_ornaments=ornaments, cape_layer_offset_m=.020), validation=fit.validate(target))
    (ROOT / 'doc/assets/modular-bard-tripo-top-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['validation'], indent=2))


if __name__ == '__main__':
    main()
