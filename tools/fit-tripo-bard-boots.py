"""Fit the delivered right boot and mirror it onto the canonical male rig."""
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import view_bytes
from outfits.radial_sections import radii

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/items/bard_starter/tripo_boots_v1/source.glb'
OUTPUT = ROOT / 'assets/modular_human_male_01/bard/tripo_boots_v1'
SPEC = ROOT / 'doc/assets/modular-bard-tripo-boots-fitting-v1.json'


def helper(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boots = helper('ranger_boots', 'tools/fit-tripo-ranger-boots.py')
fit, io, surface = boots.fit, boots.io, boots.surface


def record(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=fit.digest(path))


def fit_points(raw, faces):
    result = raw * [.70, .55, .54] + [-.1664, -.006, .025]
    result[:, 0] -= .10 * (result[:, 2] + .045)
    heights = np.linspace(.20, .965, 80)
    profiles = np.array([io.section_bounds(raw[faces], np.array([0, y, 0]),
        np.array([0, 1, 0]), np.array([[1, 0, 0], [0, 0, 1]])) for y in heights])
    centers = profiles.mean(1)
    radius = (profiles[:, 1] - profiles[:, 0]) / 2
    vertices, indices, _ = fit.body_surface(('feet', 'ankles', 'legs'), -1)
    skin = vertices[indices]
    for i in np.flatnonzero(result[:, 1] > .10):
        y = result[i, 1]
        center = np.array([np.interp(raw[i, 1], heights, centers[:, j]) for j in range(2)])
        scale = np.array([np.interp(min(raw[i, 1], .77), heights, radius[:, j]) for j in range(2)])
        cross = (raw[i, [0, 2]] - center) / scale
        length = np.linalg.norm(cross)
        direction = cross / max(length, 1e-9)
        low, high = io.section_bounds(skin, np.array([0, y, 0]), np.array([0, 1, 0]),
                                      np.array([[1, 0, 0], [0, 0, 1]]))
        origin = (low + high) / 2
        distance = surface.ray_surface(skin, [origin[0], y, origin[1]],
                                       [direction[0], 0, direction[1]])
        assert distance is not None
        clearance = .014 + .006 * io.smoothstep((y - .36) / .09)
        target = origin + direction * max((distance + clearance) * length, distance + .009)
        blend = io.smoothstep((y - .10) / .075)
        result[i, [0, 2]] = result[i, [0, 2]] * (1 - blend) + target * blend
    return result


def cuff_profile(left, faces, target):
    height = .455
    center = np.array([.157, height, -.038])
    distances = np.min([radii(left[faces], center + [0, y - height, 0],
        np.array([0., 1, 0]), samples=128) for y in np.linspace(.445, .525, 17)], axis=0)
    assert np.isfinite(distances).all()
    # section_basis(+Y) begins at +X and advances toward -Z.
    distances = distances[np.mod(-np.arange(128), 128)]
    profile = [[height, round(float(r), 8)] for r in distances]
    data = dict(source=str(target.relative_to(ROOT)), sha256=fit.digest(target),
        origin=center[[0, 2]].tolist(), leftLeg=fit.NAMES.index('LeftLeg'),
        rightLeg=fit.NAMES.index('RightLeg'), overlap=.01, inset=.009, taper=.06, hold=.09,
        profile=profile)
    path = ROOT / 'client/src/lib/data/bardBootCuff.json'
    path.write_text(json.dumps(data, indent=2) + '\n')
    return dict(path=str(path.relative_to(ROOT)), measured_section_height_m=height,
        hem_height_m=height - data['overlap'], inset_m=data['inset'],
        minimum_section_radius_m=float(distances.min()), samples=128,
        sampled_height_range_m=[.445, .525], rigid_tuck_through_height_m=.535)


def clear_foot(points, faces):
    unique, inverse = np.unique(points, axis=0, return_inverse=True)
    triangles = inverse[faces]
    selected = triangles[unique[triangles, 1].max(1) < .155]
    body = fit.body_surface(('feet', 'ankles', 'legs'), -1)
    samples = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                        [1 / 3] * 3, [.5, .5, 0], [.5, 0, .5], [0, .5, .5]])
    history = []
    for _ in range(14):
        positions = np.einsum('sk,fkj->fsj', samples, unique[selected]).reshape(-1, 3)
        corrections, distances = [], []
        for start in range(0, len(positions), 256):
            batch = positions[start:start + 256]
            nearest, normals, _ = fit.nearest_surface(batch, body, candidates=96)
            signed = np.sum((batch - nearest) * normals, axis=1)
            corrections.extend(normals * np.clip(.004 - signed, 0, .008)[:, None])
            distances.extend(signed)
        correction = np.asarray(corrections).reshape(-1, len(samples), 3)
        delta, totals = np.zeros_like(unique), np.zeros(len(unique))
        for sample, weights in enumerate(samples):
            active = np.linalg.norm(correction[:, sample], axis=1) > 1e-7
            for corner, amount in enumerate(weights):
                np.add.at(delta, selected[:, corner], correction[:, sample] * amount)
                np.add.at(totals, selected[:, corner], active * amount)
        delta /= np.maximum(totals, 1)[:, None]
        unique += delta
        history.append(dict(minimum_sample_clearance_m=float(min(distances)),
                            maximum_correction_m=float(np.linalg.norm(delta, axis=1).max())))
    return unique[inverse], history


def main():
    assert fit.digest(SOURCE) == 'b3ee950470e6287bf2cb65d55a342317fdf3dd03a774fe9ddda5cb060681923c'
    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc, raw = fit.read_glb(SOURCE)
    primitive = doc['meshes'][0]['primitives'][0]
    original = io.accessor(doc, raw, primitive['attributes']['POSITION']).astype(float)
    uv = io.accessor(doc, raw, primitive['attributes']['TEXCOORD_0'])
    faces = io.accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    images = [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    right = fit_points(original, faces)
    right, foot_clearance = clear_foot(right, faces)
    binary = bytearray(raw)
    doc['meshes'] = []
    for side in ['Right', 'Left']:
        points, triangles = right.copy(), faces.copy()
        if side == 'Left':
            points[:, 0] *= -1
            triangles = triangles[:, ::-1]
        joints, weights = boots.weights(points, side)
        attrs = io.add_skin_attributes(doc, binary, points, io.smooth_normals(points, triangles), joints, weights)
        attrs['TEXCOORD_0'] = io.add_accessor(doc, binary, uv, 'VEC2')
        doc['meshes'].append(dict(name='bard_boot_' + side.lower(), primitives=[dict(attributes=attrs,
            material=primitive['material'], indices=io.add_accessor(doc, binary, triangles.reshape(-1, 1), 'SCALAR', 5125))]))
    fit.with_rig(doc, binary, 'boots_bard', 'tripo_bard_boots_v1')
    binary = io.compact(doc, binary)
    target = OUTPUT / 'boots_bard.glb'
    fit.write_glb(target, doc, binary)
    assert images == [view_bytes(doc, binary, image['bufferView']) for image in doc['images']]
    report = dict(date='2026-10-11', source=record(SOURCE), base=record(io.PARTS / 'fitted/base.glb'),
        interfaces=record(io.PARTS / 'interfaces/v1/interfaces.json'),
        method='Fit right calf to current body sections, retain open cuff and original topology/UV/texture, mirror X with reversed triangle winding and side-specific Leg/Foot/ToeBase weights.',
        initial_transform=dict(scale=[.70, .55, .54], translation=[-.1664, -.006, .025],
                               right_foot_x_shear_per_z=-.10),
        source_triangles=len(faces), mirrored_triangles=len(faces) * 2,
        foot_clearance_iterations=foot_clearance,
        preserved_source_topology_uv_and_embedded_texture=True,
        cuff=cuff_profile(points, triangles, target), skin_cut_height_m=.43,
        validation=fit.validate(target))
    SPEC.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['validation']))


if __name__ == '__main__':
    main()
