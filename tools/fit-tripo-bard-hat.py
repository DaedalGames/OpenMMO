"""Fit the bard hat over the canonical head and crop hair, then bind to Head."""

import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import view_bytes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'assets/modular_human_male_01/bard/tripo_hat_v1'
spec = importlib.util.spec_from_file_location('fit', ROOT / 'tools/fit-modular-rogue.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
io = fit.io


def ray_distances(triangles, origin, direction):
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    cross = np.cross(direction, edge2)
    determinant = np.einsum('ij,ij->i', edge1, cross)
    valid = np.abs(determinant) > 1e-10
    inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
    delta = origin - triangles[:, 0]
    u = np.einsum('ij,ij->i', delta, cross) * inverse
    q = np.cross(delta, edge1)
    v = (q @ direction) * inverse
    distance = np.einsum('ij,ij->i', edge2, q) * inverse
    return distance[valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (distance > 0)]


def rim_clearances(points, faces, head, sign, axis=2):
    measurements = []
    for height in [1.83, 1.835, 1.84, 1.85, 1.86]:
        origin, direction = np.array([0, height, 0]), np.zeros(3)
        direction[axis] = sign
        skull = ray_distances(head[0][head[1]], origin, direction).max()
        lining = ray_distances(points[faces], origin, direction).min()
        measurements.append(dict(height_m=height, gap_mm=float((lining - skull) * 1000)))
    return measurements


def fit_head_shell(points, faces, head):
    triangles = head[0][head[1]]
    result = points.copy()
    for i, point in enumerate(points):
        origin = np.array([0, point[1], 0])
        radius = np.linalg.norm(point[[0, 2]])
        direction = (point - origin) / max(radius, 1e-10)
        hits = ray_distances(triangles, origin, direction)
        if not len(hits):
            continue
        side = np.clip((abs(direction[0]) - .65) / .25, 0, 1)
        limit = hits.max() + .010 - .007 * side
        if radius < limit:
            correction = .9 * (limit - radius)
            result[i] += direction * correction
    _, seam = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    for _ in range(8):
        corrections_by_vertex = np.zeros(seam.max() + 1)
        for face in faces:
            vertices = result[face]
            samples = [vertices.mean(0), *(vertices + np.roll(vertices, 1, axis=0)) / 2]
            for point in samples:
                origin = np.array([0, point[1], 0])
                radius = np.linalg.norm(point[[0, 2]])
                direction = (point - origin) / max(radius, 1e-10)
                hits = ray_distances(triangles, origin, direction)
                if not len(hits):
                    continue
                side = np.clip((abs(direction[0]) - .65) / .25, 0, 1)
                deficit = hits.max() + .004 - .0025 * side - radius
                if deficit > .0001:
                    np.maximum.at(corrections_by_vertex, seam[face], deficit * 1.4)
        if not corrections_by_vertex.any():
            break
        radius = np.linalg.norm(result[:, [0, 2]], axis=1)
        result[:, [0, 2]] *= (1 + corrections_by_vertex[seam] / radius)[:, None]
    displacement = np.linalg.norm(result - points, axis=1)
    return result, dict(vertices=int(np.count_nonzero(displacement > 1e-9)),
                        maximum_radial_correction_mm=float(displacement.max() * 1000))


def main():
    source = ROOT / 'assets/items/bard_starter/tripo_hat_v1/source.glb'
    assert fit.digest(source) == 'd8b486c7275ec3eb3ef76bea0a606063a1a5ab3fd24d64f697990b02d5c17827'
    doc, raw = fit.read_glb(source)
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = io.accessor(doc, raw, attrs['POSITION'])
    uv = io.accessor(doc, raw, attrs['TEXCOORD_0'])
    faces = io.accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    scale, offset = [.40, .43, .40], [0, 1.795, 0]
    fitted = points * scale + offset
    rear = np.clip((.045 - fitted[:, 2]) / .095, 0, 1)
    rear = rear * rear * (3 - 2 * rear)
    lower = np.clip((1.91 - fitted[:, 1]) / .06, 0, 1)
    lower = lower * lower * (3 - 2 * lower)
    fitted[:, 0] *= 1 - .12 * rear
    fitted[:, 2] += .052 * rear
    fitted[:, 1] -= .015 * rear * lower
    front = np.clip((fitted[:, 2] - .015) / .085, 0, 1)
    front = front * front * (3 - 2 * front)
    front_lower = np.clip((1.84 - fitted[:, 1]) / .03, 0, 1)
    front_lower = front_lower * front_lower * (3 - 2 * front_lower)
    fitted[:, 2] -= (.006 + .028 * front_lower) * front
    fitted[:, 1] -= .15 * np.maximum(fitted[:, 1] - 1.90, 0)
    fitted[:, 0] *= np.where(fitted[:, 0] < 0, .82, .89)
    contact = np.clip((fitted[:, 1] - 1.82) / .02, 0, 1)
    contact *= np.clip((1.92 - fitted[:, 1]) / .04, 0, 1)
    contact *= np.clip((.07 - np.abs(fitted[:, 2])) / .04, 0, 1)
    fitted[:, 0] -= np.where(fitted[:, 0] < 0, -.002, .006) * contact
    hair_path = io.PARTS / 'fitted/hair_crop.glb'
    head = fit.body_surface(('head',))
    fitted, shell = fit_head_shell(fitted, faces, head)
    rear_gaps = rim_clearances(fitted, faces, head, -1)
    front_gaps = rim_clearances(fitted, faces, head, 1)
    side_gaps = {name: rim_clearances(fitted, faces, head, sign, axis=0)
                 for name, sign in [('negative_x', -1), ('positive_x', 1)]}
    assert all(0 < row['gap_mm'] < 10 for row in rear_gaps), rear_gaps
    assert all(0 < row['gap_mm'] < 10 for row in front_gaps), front_gaps
    assert all(0 < row['gap_mm'] < 8 for rows in side_gaps.values() for row in rows), side_gaps
    samples = np.vstack([fitted, fitted[faces].mean(1)])
    nearest, _, _ = fit.nearest_surface(samples, head)
    clearance = np.linalg.norm(samples - nearest, axis=1)
    assert clearance.min() > .0002, float(clearance.min())
    joints = np.zeros((len(fitted), 4), dtype=np.uint16)
    joints[:, 0] = fit.NAMES.index('Head')
    weights = np.zeros((len(fitted), 4))
    weights[:, 0] = 1
    normals = io.smooth_normals(fitted, faces)
    images = [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    binary = bytearray(raw)
    skin = io.add_skin_attributes(doc, binary, fitted, normals, joints, weights)
    skin['TEXCOORD_0'] = io.add_accessor(doc, binary, uv, 'VEC2')
    doc['meshes'] = [dict(name='helmet_bard', primitives=[dict(attributes=skin,
        material=primitive['material'], indices=io.add_accessor(doc, binary, faces.reshape(-1, 1), 'SCALAR', 5125))])]
    fit.with_rig(doc, binary, 'helmet_bard', 'tripo_bard_hat_v1')
    binary = io.compact(doc, binary)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / 'helmet_bard.glb'
    fit.write_glb(target, doc, binary)
    assert images == [view_bytes(doc, binary, image['bufferView']) for image in doc['images']]
    fitted_attrs = doc['meshes'][0]['primitives'][0]['attributes']
    assert np.array_equal(uv, io.accessor(doc, binary, fitted_attrs['TEXCOORD_0']))
    report = dict(date='2026-10-11', fitting_revision=5, head_shell=shell,
        side_clearance_mm=side_gaps,
        lateral_cage=dict(negative_x_scale=.82, positive_x_scale=.89,
                          temple_inset_m=[.002, .006],
                          contact_height_m=[1.82, 1.84, 1.88, 1.92]),
        lateral_extent_m=[float(fitted[:, 0].min()), float(fitted[:, 0].max())],
        front_clearance_mm=front_gaps,
        front_cage=dict(lower_backward_shift_m=.034, upper_backward_shift_m=.006,
                        height_blend_y_m=[1.81, 1.84], depth_blend_z_m=[.015, .10]),
        crown=dict(height_scale=.85, pivot_y_m=1.90),
        rear_clearance_mm=rear_gaps,
        rear_cage=dict(forward_shift_m=.052, lower_rim_drop_m=.015,
                       rear_width_scale=.88, depth_blend_z_m=[-.05, .045],
                       height_blend_y_m=[1.85, 1.91]),
        sources=[dict(path=str(p.relative_to(ROOT)), sha256=fit.digest(p)) for p in
                 [source, io.PARTS / 'fitted/base.glb', hair_path]],
        output=dict(path=str(target.relative_to(ROOT)), sha256=fit.digest(target)),
        initial_transform=dict(scale=scale, translation_m=offset),
        head_clearance_mm=float(clearance.min() * 1000),
        clearance_method='Unsigned nearest-head distance at hat vertices and triangle centers; separate triangle-overlap checks required',
        triangles=len(faces), texture_bytes_preserved=True, uv_preserved=True,
        skinning='All vertices rigidly weighted 1.0 to the canonical Head bone',
        validation=fit.validate(target), scope='Fitted candidate; runtime motion and intersections validated separately')
    (ROOT / 'doc/assets/modular-bard-tripo-hat-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
