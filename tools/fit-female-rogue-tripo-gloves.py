"""Fit the Tripo glove details and snaps to the female hand shell."""
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

from lib.glb import read_glb, write_glb, view_bytes
from lib.glb_accessors import accessor, add_accessor
from outfits import female_rogue_gloves as helpers
from outfits.rogue_layers import compact_weights
from outfits.rogue_glove_texture import bake

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/items/female_rogue_gloves/tripo_v1/source/model_url.glb'
OUT = SOURCE.parent.parent / 'fitted_v1'
io, surface = helpers.io, helpers.surface
FINGERS = helpers.FINGERS


def source_regions(points, faces):
    unique, inverse = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    welded = inverse[faces]
    edges = np.unique(np.sort(welded[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)
    lengths = np.linalg.norm(unique[edges[:, 0]] - unique[edges[:, 1]], axis=1)
    graph = coo_matrix((np.r_[lengths, lengths], (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])), shape=(len(unique),) * 2).tocsr()
    _, groups = connected_components(graph, directed=False)
    main = groups == np.bincount(groups).argmax()
    distal = welded[(unique[welded, 1] > .35).all(1)]
    e = distal[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)
    _, distal_groups = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=graph.shape), directed=False)
    seeds = [np.flatnonzero(distal_groups == g) for g in np.unique(distal_groups) if np.sum(distal_groups == g) > 5]
    seeds.sort(key=lambda rows: -unique[rows, 2].mean())
    assert len(seeds) == 4
    seeds.append(np.flatnonzero(main & (unique[:, 1] > .11) & (unique[:, 2] < -.275)))
    assert len(seeds[-1]) > 5
    distances = np.array([dijkstra(graph, directed=False, indices=rows, min_only=True) for rows in seeds])
    labels = distances.argmin(0)
    labels[~main] = -1
    tips = []
    for rows in seeds:
        near = unique[rows[np.argsort(unique[rows, 1])[-12:]]]
        tips.append((near.min(0) + near.max(0)) / 2)
    return labels[inverse], groups[inverse], inverse, np.array(tips)


def fit_snaps(points, faces, components, uv, shell, shell_faces, shell_joints, shell_weights, names, bones, side):
    axis, width, dorsal = helpers.hand_frame(bones, side)
    dense = np.zeros((len(shell), len(names)))
    np.put_along_axis(dense, shell_joints, shell_weights, axis=1)
    expanded = np.arange(len(shell_faces) * 3).reshape(-1, 3)
    payload = np.column_stack([dense[shell_faces].reshape(-1, len(names)), np.repeat(np.arange(len(shell_faces)), 3), np.tile(np.eye(3), (len(shell_faces), 1))])
    center = bones[side + 'Hand'] - axis * .012
    low, high = surface.ray_bounds(center[None], dorsal, shell[shell_faces], .08)
    positions, triangles, coords, joint_rows, weight_rows, records = [], [], [], [], [], []
    main = np.bincount(components).argmax()
    offset = 0
    for component in np.unique(components):
        if component == main:
            continue
        selected = faces[(components[faces] == component).all(1)]
        used, indices = np.unique(selected, return_inverse=True)
        source = points[used]
        unique = np.unique(source, axis=0)
        source_center = unique.mean(0)
        sign = 1 if source_center[0] > .09 else -1
        distance = high[0] if sign > 0 else low[0]
        assert np.isfinite(distance)
        anchor, normal, values = surface.nearest_surface((center + dorsal * distance)[None], (shell[shell_faces].reshape(-1, 3), expanded, payload))
        anchor, normal, values = anchor[0], normal[0], values[0]
        _, _, axes = np.linalg.svd(unique - source_center, full_matrices=False)
        source_normal = axes[-1] * np.sign(axes[-1, 0] * sign)
        source_axis = io.unit(np.array([0., 1., 0.]) - source_normal * source_normal[1])
        source_width = np.cross(source_axis, source_normal)
        target_axis = io.unit(axis - normal * (axis @ normal))
        target_width = np.cross(target_axis, normal)
        local = (source - source_center) @ np.array([source_width, source_axis, source_normal]).T * .105
        local[:, 2] -= local[:, 2].min() + .0001
        support = anchor + local[:, :2] @ np.array([target_width, target_axis])
        contact, contact_normals, contact_values = surface.nearest_surface(support, (shell[shell_faces].reshape(-1, 3), expanded, payload))
        fitted = contact + contact_normals * local[:, 2, None]
        joints, weights = compact_weights(contact_values[:, :len(names)])
        coords.append(uv[used] * [.5, 1.])
        positions.append(fitted)
        triangles.append(indices.reshape(-1, 3) + offset)
        joint_rows.append(joints)
        weight_rows.append(weights)
        records.append({'component': int(component), 'surface': 'dorsal' if sign > 0 else 'palmar', 'vertices': [offset, offset + len(used)], 'anchor_triangle': shell_faces[int(round(values[len(names)]))].tolist(), 'anchor_barycentrics': values[-3:].tolist(), 'anchor_m': anchor.tolist(), 'normal': normal.tolist(), 'embed_m': .0001, 'placement': 'Curved cuff contact, with per-vertex surface weights'})
        offset += len(used)
    return np.vstack(positions), np.vstack(triangles), np.vstack(coords), np.vstack(joint_rows), np.vstack(weight_rows), records


def hand_uv(shell, shell_faces, source, source_faces, source_uv, tips, bones, side):
    wrist = bones[side + 'Hand']
    axis, width, normal = helpers.hand_frame(bones, side)
    basis = np.array([width, axis])
    controls, targets = [], []
    for height, along, center, span, radius in [(-.48, -.025, .07, .21, .031), (-.36, 0, .07, .21, .032), (-.18, .04, .04, .285, .039), (.05, .08, .065, .31, .041)]:
        for sign in [-1, 0, 1]:
            controls.append([sign * radius, along])
            targets.append([-center + sign * span, height])
    roots = np.array([[-.09, .22, tips[0, 2]], [-.09, .26, tips[1, 2]], [-.09, .27, tips[2, 2]], [-.09, .25, tips[3, 2]], [-.09, -.07, -.205]])
    for i, finger in enumerate(FINGERS):
        root, middle, end = [bones[f'{side}Hand{finger}{j}'] for j in [1, 2, 3]]
        opening = middle * .85 + end * .15
        src_axis = io.unit((tips[i] - roots[i])[[2, 1]] * [-1, 1])
        src_width = np.array([src_axis[1], -src_axis[0]])
        target_axis = io.unit((opening - root) @ basis.T)
        target_width = np.array([target_axis[1], -target_axis[0]])
        for src_center, target_center in [(roots[i], root), (tips[i], opening)]:
            for sign in [-1, 0, 1]:
                controls.append((target_center - wrist) @ basis.T + target_width * sign * [.0075, .009, .009, .009, .011][i])
                targets.append(src_center[[2, 1]] * [-1, 1] + src_width * sign * [.063, .07, .07, .07, .06][i])
    return RBFInterpolator(np.array(controls), np.array(targets), kernel='thin_plate_spline', smoothing=1e-6)


def chart_uv(shell, faces, bones, side):
    axis, width, normal = helpers.hand_frame(bones, side)
    projected = (shell - bones[side + 'Hand']) @ np.array([width, axis]).T
    low, high = projected.min(0) - .002, projected.max(0) + .002
    uv = (projected - low) / (high - low)
    triangles = shell[faces]
    chart = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]) @ normal < 0
    uv[:, 0] = .5 + uv[:, 0] * .25
    uv[:, 1] = uv[:, 1] * .5 + np.repeat(chart, 3) * .5
    return uv, low, high


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert helpers.digest(SOURCE) == '3144f1d772d902f03a54fe4aff1106596e23ce7212fe473c91a284062c99f583'
    base, base_raw, names, bones, body = helpers.knight.setup_body()
    doc, original = read_glb(SOURCE)
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = accessor(doc, original, attrs['POSITION']).astype(float)
    faces = accessor(doc, original, primitive['indices']).reshape(-1, 3)
    uv = accessor(doc, original, attrs['TEXCOORD_0'])
    _, components, _, tips = source_regions(points, faces)
    raw = bytearray(original)
    shell, shell_faces, _, _, _ = helpers.hand_shell(body, names, bones, 'Right')
    _, low, high = chart_uv(shell, shell_faces, bones, 'Right')
    inverse = hand_uv(shell, shell_faces, points, faces, uv, tips, bones, 'Right')
    atlas = bake(doc, original, points, faces, uv, inverse, low, high, OUT / 'textures')
    for index, contents in enumerate(atlas):
        raw.extend(b'\0' * (-len(raw) % 4))
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(raw), 'byteLength': len(contents)})
        raw.extend(contents)
        doc['images'][index] = {'bufferView': view, 'mimeType': 'image/png', 'name': 'fitted_rogue_' + ['color', 'orm', 'normal'][index]}
    doc['meshes'] = []
    records, arrays, skin_references = {}, {}, {}
    for side in ['Right', 'Left']:
        shell, shell_faces, shell_joints, shell_weights, skin_reference = helpers.hand_shell(body, names, bones, side)
        coords, _, _ = chart_uv(shell, shell_faces, bones, side)
        snap_positions, snap_faces, snap_uv, snap_joints, snap_weights, attachments = fit_snaps(points, faces, components, uv, shell, shell_faces, shell_joints, shell_weights, names, bones, side)
        mapped = np.vstack([shell, snap_positions])
        triangles = np.vstack([shell_faces, snap_faces + len(shell)])
        coords = np.vstack([coords, snap_uv])
        joints = np.vstack([shell_joints, snap_joints])
        weights = np.vstack([shell_weights, snap_weights])
        for attachment in attachments:
            attachment['vertices'] = [value + len(shell) for value in attachment['vertices']]
        record = {'snap_attachments': attachments}
        skin_references[side.lower()] = skin_reference.tolist()
        record['hand_shell_triangles'] = len(shell_faces)
        record['native_snap_triangles'] = len(snap_faces)
        record['hand_uv_method'] = 'Continuous dorsal/palmar charts baked from all native Tripo PBR maps; normal vectors rotated into chart tangent space.'
        normals = io.smooth_normals(mapped, triangles)
        attributes = io.add_skin_attributes(doc, raw, mapped, normals, joints, weights)
        attributes['TEXCOORD_0'] = add_accessor(doc, raw, coords, 'VEC2')
        attributes['TANGENT'] = add_accessor(doc, raw, io.tangents(mapped, normals, coords, triangles), 'VEC4')
        doc['meshes'].append({'name': f'gloves_female_rogue_{side.lower()}', 'primitives': [{'attributes': attributes, 'indices': add_accessor(doc, raw, triangles.reshape(-1, 1), 'SCALAR', 5125), 'material': primitive['material']}]})
        arrays.update({f'{side}_positions': mapped, f'{side}_joints': joints, f'{side}_weights': weights, f'{side}_faces': triangles})
        records[side] = {**record, 'triangles': len(triangles), 'vertices': len(mapped)}
    helpers.attach_rig(doc, raw, base, base_raw)
    raw = io.compact(doc, raw)
    assert atlas == [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    target = OUT / 'gloves_female_rogue.glb'
    write_glb(target, doc, raw)
    np.savez(OUT / 'fit-data.npz', **arrays)
    (OUT / 'skin-reference.json').write_text(json.dumps(skin_references, separators=(',', ':')) + '\n')
    hidden = np.zeros(len(body[1]), dtype=bool)
    for side in ['Right', 'Left']:
        own = [i for i, name in enumerate(names) if name.startswith(side) and ('Hand' in name or 'ForeArm' in name)]
        inside = (helpers.cut_field(body[0], body[2], names, bones, side) < -.006) & (body[2][:, own].sum(1) > .5)
        hidden |= inside[body[1]].all(1)
    mask = {'body': str(helpers.BODY.relative_to(ROOT)), 'body_sha256': helpers.digest(helpers.BODY), 'mesh_index': 0, 'primitive_index': 0, 'primitive_triangles': len(body[1]), 'hide_triangle_indices': np.flatnonzero(hidden).tolist()}
    (OUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')
    report = {'date': '2026-10-26', 'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': helpers.digest(SOURCE)}, 'body_sha256': helpers.digest(helpers.BODY), 'output_sha256': helpers.digest(target), 'rig_id': 'human_female_01_local_v1', 'sides': records, 'triangles': sum(record['triangles'] for record in records.values()), 'pbr_source': 'Original Tripo color/ORM/normal projected into continuous hand charts and cuff atlas; originals preserved in tripo_v1/source', 'derived_texture_dimensions': [4096, 2048], 'native_snap_uvs_retained': True, 'hand_uv_correspondence': True, 'hand_shell_rebuilt_on_female_skin': True, 'body_hidden_triangles': int(hidden.sum()), 'method': 'Native Tripo metal snap retained; glove shell rebuilt on actual female skin with native skin weights. Source detail transferred through finger/palm correspondences. All native PBR maps projected into continuous hand charts, with corrected normal tangent space. No new AI textures or paid generation.', 'status': 'fitting candidate; pending visual and motion review'}
    (OUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
