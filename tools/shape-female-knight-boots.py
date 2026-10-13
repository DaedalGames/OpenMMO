import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from lib.glb import read_glb, view_bytes, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.female_boot_pose import heel_pose

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/items/female_knight_boots/fitted_v4'
OUTPUT = ROOT / 'assets/items/female_knight_boots/fitted_v5'
OUTPUT.mkdir(exist_ok=True)
doc, raw = read_glb(SOURCE / 'boots_female_knight.glb')
body, body_raw = read_glb(ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb')
matrices, _ = heel_pose(body, body_raw)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def posed(primitive):
    attrs = primitive['attributes']
    points = accessor(doc, raw, attrs['POSITION']).astype(float)
    joints = accessor(doc, raw, attrs['JOINTS_0'])
    weights = accessor(doc, raw, attrs['WEIGHTS_0'])
    deform = np.einsum('nk,nkij->nij', weights, matrices[joints])
    return np.einsum('nij,nj->ni', deform, np.c_[points, np.ones(len(points))])[:, :3]


triangles = np.concatenate([
    posed(p)[accessor(doc, raw, p['indices']).reshape(-1, 3)]
    for p in doc['meshes'][0]['primitives']
])
foot_triangles = triangles[triangles[:, :, 1].max(1) < .06]
tip = float(foot_triangles[:, :, 2].max())


def section_bounds(mesh, coordinate, axis, component):
    hits = []
    for a, b in [(mesh[:, 0], mesh[:, 1]), (mesh[:, 1], mesh[:, 2]), (mesh[:, 2], mesh[:, 0])]:
        select = (a[:, axis] < coordinate) != (b[:, axis] < coordinate)
        a, b = a[select], b[select]
        hits.extend(a + (b - a) * ((coordinate - a[:, axis]) / (b[:, axis] - a[:, axis]))[:, None])
    values = np.array(hits)[:, component]
    return values.min(), values.max()


foot_z = np.linspace(.025, tip - 1e-7, 800)
foot_bounds = np.array([section_bounds(foot_triangles, z, 2, 1) for z in foot_z])
shaft_y = np.linspace(.055, .32, 500)
shaft_bounds = np.array([section_bounds(triangles, y, 1, 2) for y in shaft_y])
front_delta = PchipInterpolator(
    [.04, .055, .075, .10, .13, .17, .23, .29, .33],
    [0, 0, .001, .012, .019, .018, .015, .001, 0],
)
rear_delta = PchipInterpolator(
    [.04, .06, .085, .115, .14, .18, .23, .29, .33],
    [0, 0, .006, .013, .010, .004, 0, 0, 0],
)
instep = PchipInterpolator([.025, .035, .045, .055, .065, .079], [.025, .015, .0055, -.0005, -.003, -.005])
toe_profile = PchipInterpolator([.040, .050, .065, .080, .100], [.040, .050, .060, .069, .083])


def toe_and_sole(points):
    result = points.copy()
    y, z = points[:, 1], points[:, 2]
    toe = (z > .040) & (y < .045)
    result[toe, 2] += (toe_profile(z[toe]) - z[toe]) * (1 - smooth((y[toe] - .015) / .030))
    forefoot = smooth((z - .030) / .015) * (1 - smooth((y + .004) / .016))
    result[:, 1] += .0015 * forefoot * smooth((y + .03027333) / .012)
    arch = smooth((.047 - z) / .025) * smooth((z + .012) / .025)
    arch *= smooth((y + .03027333) / .010) * (1 - smooth((y - .018) / .035))
    result[:, 2] -= .0035 * arch
    heel = smooth((y + .010) / .040) * (1 - smooth((y - .050) / .045))
    heel *= 1 - smooth((z - .004) / .016)
    result[:, 1] -= .48 * (z + .003) * heel
    return result


def reshape(points):
    result = points.copy()
    y, z = points[:, 1], points[:, 2]
    low = np.interp(y, shaft_y, shaft_bounds[:, 0])
    high = np.interp(y, shaft_y, shaft_bounds[:, 1])
    fraction = np.clip((z - low) / (high - low), 0, 1)
    shaft = (y > .04) & (y < .33)
    result[shaft, 2] += (
        front_delta(y[shaft]) * fraction[shaft]
        + rear_delta(y[shaft]) * (1 - fraction[shaft])
    )
    foot = (y < .055) & (z > .025)
    fz, fy = z[foot], y[foot]
    bottom = np.interp(fz, foot_z, foot_bounds[:, 0])
    top = np.interp(fz, foot_z, foot_bounds[:, 1])
    fraction = (fy - bottom) / np.maximum(top - bottom, 1e-9)
    arc = np.sqrt(np.maximum(0, 1 - (np.clip((fz - .079) / (tip - .079), 0, 1)) ** 2))
    new_top = np.where(fz < .079, instep(np.minimum(fz, .079)), -.017 + .012 * arc)
    new_bottom = np.where(fz < .079, bottom, -.017 - .012 * arc)
    target = new_bottom + fraction * (new_top - new_bottom)
    amount = smooth((fz - .025) / .022)
    result[foot, 1] += (target - fy) * amount
    return toe_and_sole(result)


def subdivide(values, faces):
    points = values[:, :3]
    edges = set()
    for face in faces:
        for a, b in zip(face, np.roll(face, -1)):
            p, q = points[a], points[b]
            if max(p[1], q[1]) < .06 and min(p[2], q[2]) > .035 and np.linalg.norm(p - q) > .006:
                edges.add(tuple(sorted((int(a), int(b)))))
    output = list(values)
    midpoints = {}
    for a, b in sorted(edges):
        midpoints[(a, b)] = len(output)
        output.append((values[a] + values[b]) / 2)
    result = []
    for a, b, c in faces:
        ab, bc, ca = [midpoints.get(tuple(sorted(edge))) for edge in [(a, b), (b, c), (c, a)]]
        count = sum(v is not None for v in [ab, bc, ca])
        if count == 0:
            result.append((a, b, c))
        elif count == 3:
            result.extend([(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)])
        else:
            for _ in range(2):
                if ab is not None and ((count == 1 and bc is None and ca is None) or (count == 2 and bc is not None)):
                    break
                a, b, c, ab, bc, ca = b, c, a, bc, ca, ab
            result.extend([(a, ab, c), (ab, b, c)] if count == 1 else [(a, ab, c), (ab, bc, c), (ab, b, bc)])
    return np.array(output), np.array(result)


binary = bytearray(raw)
minimum_area = float('inf')
maximum_change = 0
for mesh in doc['meshes'][:1]:
    for primitive in mesh['primitives']:
        attrs = primitive['attributes']
        points = posed(primitive)
        normals = accessor(doc, raw, attrs['NORMAL']).astype(float)
        uv = accessor(doc, raw, attrs['TEXCOORD_0'])
        joints = accessor(doc, raw, attrs['JOINTS_0'])
        weights = accessor(doc, raw, attrs['WEIGHTS_0'])
        deform = np.einsum('nk,nkij->nij', weights, matrices[joints])
        normals = np.linalg.solve(deform[:, :3, :3].transpose(0, 2, 1), normals[..., None])[..., 0]
        faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
        # Subdivide only rigid foot surfaces; interpolated joints remain exact.
        foot = (points[:, 1] < .06) & (points[:, 2] > .035)
        if foot.any():
            assert np.all(joints[foot] == joints[foot][0])
            assert np.allclose(weights[foot], weights[foot][0])
            values = np.column_stack([points, normals, uv, joints, weights])
            for _ in range(3):
                values, faces = subdivide(values, faces)
            points, normals, uv = values[:, :3], values[:, 3:6], values[:, 6:8]
            joints, weights = values[:, 8:12].astype(int), values[:, 12:16]
            deform = np.einsum('nk,nkij->nij', weights, matrices[joints])
        changed = reshape(points)
        maximum_change = max(maximum_change, float(np.linalg.norm(changed - points, axis=1).max()))
        jacobian = np.stack([
            (reshape(points + np.eye(3)[axis] * 1e-7) - reshape(points - np.eye(3)[axis] * 1e-7)) / 2e-7
            for axis in range(3)
        ], axis=2)
        normals = np.einsum('nij,nj->ni', np.linalg.pinv(jacobian.transpose(0, 2, 1)), normals)
        t = changed[faces]
        cross = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        area = np.linalg.norm(cross, axis=1)
        _, weld = np.unique(np.round(changed, 7), axis=0, return_inverse=True)
        accumulated = np.zeros((weld.max() + 1, 3))
        for corner in range(3):
            np.add.at(accumulated, weld[faces[:, corner]], cross)
        foot = (points[:, 1] < .055) & (points[:, 2] > .025)
        normals[foot] = accumulated[weld][foot]
        minimum_area = min(minimum_area, float(area.min()))
        assert np.isfinite(changed).all() and (area > 1e-12).all()
        points = np.linalg.solve(deform, np.c_[changed, np.ones(len(changed))][..., None])[:, :3, 0]
        normals = np.einsum('nji,nj->ni', deform[:, :3, :3], normals)
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        for name, data, kind, component in [
            ('POSITION', points, 'VEC3', 5126), ('NORMAL', normals, 'VEC3', 5126),
            ('TEXCOORD_0', uv, 'VEC2', 5126), ('JOINTS_0', joints, 'VEC4', 5123),
            ('WEIGHTS_0', weights, 'VEC4', 5126),
        ]:
            attrs[name] = add_accessor(doc, binary, data, kind, component)
        primitive['indices'] = add_accessor(doc, binary, faces.reshape(-1, 1), 'SCALAR', 5125)

names = [body['nodes'][i]['name'] for i in body['skins'][0]['joints']]
opposite = np.array([names.index(name.replace('Right', 'Left')) for name in names])
doc['meshes'][1]['primitives'] = copy.deepcopy(doc['meshes'][0]['primitives'])
for primitive in doc['meshes'][1]['primitives']:
    attrs = primitive['attributes']
    points = accessor(doc, binary, attrs['POSITION']).astype(float)
    normals = accessor(doc, binary, attrs['NORMAL']).astype(float)
    joints = accessor(doc, binary, attrs['JOINTS_0'])
    weights = accessor(doc, binary, attrs['WEIGHTS_0'])
    deformation = np.einsum('nk,nkij->nij', weights, matrices[joints])
    points = np.einsum('nij,nj->ni', deformation, np.c_[points, np.ones(len(points))])[:, :3]
    normals = np.linalg.solve(deformation[:, :3, :3].transpose(0, 2, 1), normals[..., None])[..., 0]
    points[:, 0] *= -1
    normals[:, 0] *= -1
    joints = opposite[joints]
    deformation = np.einsum('nk,nkij->nij', weights, matrices[joints])
    points = np.linalg.solve(deformation, np.c_[points, np.ones(len(points))][..., None])[:, :3, 0]
    normals = np.einsum('nji,nj->ni', deformation[:, :3, :3], normals)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)[:, ::-1]
    for name, data, kind, component in [
        ('POSITION', points, 'VEC3', 5126), ('NORMAL', normals, 'VEC3', 5126),
        ('JOINTS_0', joints, 'VEC4', 5123),
    ]:
        attrs[name] = add_accessor(doc, binary, data, kind, component)
    primitive['indices'] = add_accessor(doc, binary, faces.reshape(-1, 1), 'SCALAR', 5125)

spec = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
plate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plate)
original_images = [view_bytes(doc, raw, im['bufferView']) for im in doc['images']]
binary = plate.compact(doc, binary)
assert original_images == [view_bytes(doc, binary, im['bufferView']) for im in doc['images']]
destination = OUTPUT / 'boots_female_knight.glb'
write_glb(destination, doc, binary)
for name in ['body-occlusion.json', 'heel-pose.json']:
    shutil.copy2(SOURCE / name, OUTPUT / name)
fitting = json.loads((SOURCE / 'fitting.json').read_text())
fitting.pop('section_clearances')
fitting['base_fitting_source'] = str(SOURCE.relative_to(ROOT) / 'fitting.json')
fitting['status'] = 'Side profile edited after anatomical fitting; original section clearances no longer apply'
fitting['triangles'] = sum(doc['accessors'][p['indices']]['count'] // 3 for m in doc['meshes'] for p in m['primitives'])
(OUTPUT / 'fitting.json').write_text(json.dumps(fitting, indent=2) + '\n')
report = {
    'date': '2026-10-13', 'source': str(SOURCE.relative_to(ROOT) / 'boots_female_knight.glb'),
    'source_sha256': hashlib.sha256((SOURCE / 'boots_female_knight.glb').read_bytes()).hexdigest(),
    'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
    'method': 'Equipped-pose silhouette deformation, inverse-skinned into the original bind pose',
    'reference': 'User supplied target and annotated yellow instep, red rear ankle, blue shin curves',
    'revision': 'Shorter blunt toe, slightly fuller sole and arch, and heel-cup boundary rising diagonally toward the rear',
    'toe_sole_reference': 'assets/items/female_knight_boots/references/user-toe-sole-outline.png',
    'profile_axes': {'front': '+Z, toward toe', 'rear': '-Z, toward heel', 'height': '+Y'},
    'textures_unchanged': True, 'uv_interpolated_only_for_subdivision': True,
    'rig_and_heel_pose_unchanged': True, 'maximum_vertex_displacement': maximum_change,
    'minimum_double_triangle_area': minimum_area,
    'triangles': sum(doc['accessors'][p['indices']]['count'] // 3 for m in doc['meshes'] for p in m['primitives']),
    'source_conditions': 'Existing ImageGen ChatGPT Pro 20x and Tripo asset; local geometry edit, no new generation',
}
(OUTPUT / 'side-profile.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
