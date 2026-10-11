"""Check preserved source data, rig isolation and posed ankle/waist clearance."""
import importlib.util
import json
from pathlib import Path

import numpy as np

from outfits.radial_sections import clearance
from outfits.skinning import deform, deform_dense

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bard', ROOT / 'tools/fit-tripo-bard-pants.py')
bard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bard)
fit, io = bard.fit, bard.io


def section(cloth, body, center, axis, rear=False):
    if rear:
        return clearance(cloth, body, center, axis, samples=128, angles=(.35, np.pi - .35))
    return clearance(cloth, body, center, axis)


def hip_panels(points, faces, joints, weights):
    triangles = points[faces]
    centers = triangles.mean(1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    area = np.linalg.norm(normals, axis=1)
    normals /= area[:, None]
    selected = (abs(centers[:, 0]) > .15) & (centers[:, 1] > .90) & (centers[:, 1] < .99)
    selected &= (centers[:, 2] > -.08) & (triangles[:, :, 2].max(1) < .04)
    selected &= (normals[:, 0] * np.sign(centers[:, 0]) > .55) & (area > .0004)
    indices = np.flatnonzero(selected)
    assert len(indices) > 0
    dense = np.zeros((len(points), len(fit.NAMES)))
    np.add.at(dense, (np.arange(len(points))[:, None], joints), weights)
    return indices, normals[indices], dense[faces[indices]].mean(1)


def main():
    path = bard.OUTPUT / 'pants_bard.glb'
    doc, binary = fit.read_glb(path)
    source, raw = fit.read_glb(bard.SOURCE)
    primitive, original = doc['meshes'][0]['primitives'][0], source['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = io.accessor(doc, binary, attrs['POSITION'])
    faces = io.accessor(doc, binary, primitive['indices']).reshape(-1, 3)
    joints = io.accessor(doc, binary, attrs['JOINTS_0'])
    weights = io.accessor(doc, binary, attrs['WEIGHTS_0'])
    original_faces = io.accessor(source, raw, original['indices']).reshape(-1, 3)
    original_points = io.accessor(source, raw, original['attributes']['POSITION'])
    original_uv = io.accessor(source, raw, original['attributes']['TEXCOORD_0'])
    vertex_map, expected_uv, expected_faces = bard.belt_uv(original_points, original_uv, original_faces)
    actual_uv = io.accessor(doc, binary, attrs['TEXCOORD_0'])
    assert np.array_equal(faces, expected_faces)
    assert np.array_equal(actual_uv, expected_uv)
    assert np.array_equal(vertex_map[faces], original_faces)
    changed = np.any(actual_uv[faces] != original_uv[original_faces], axis=(1, 2))
    assert np.array_equal(np.flatnonzero(changed), bard.BELT_FACES)
    for values in [points, io.accessor(doc, binary, attrs['NORMAL']), joints, weights]:
        assert np.array_equal(values[len(original_points):], values[vertex_map[len(original_points):]])
    assert [bard.view_bytes(doc, binary, image['bufferView']) for image in doc['images']] == [bard.view_bytes(source, raw, image['bufferView']) for image in source['images']]
    for side, sign in [('Left', 1), ('Right', -1)]:
        lower = (points[:, 0] * sign > 0) & (points[:, 1] < .55)
        allowed = {fit.NAMES.index(side + bone) for bone in ['UpLeg', 'Leg', 'Foot']}
        assert all(int(j) in allowed for j in joints[lower][weights[lower] > 1e-6])
    body_points, body_faces, body_weights = fit.body_surface(('torso', 'legs', 'ankles', 'feet'))
    rest = []
    for height in [1.04, 1.08, 1.11]:
        rest.append(dict(region='waist', height_m=height, **section(points[faces], body_points[body_faces],
            np.array([0, height, -.02]), np.array([0, 1., 0]))))
    for side, sign in [('Left', 1), ('Right', -1)]:
        cloth_faces = faces[points[faces].mean(1)[:, 0] * sign > 0]
        skin_faces = body_faces[body_points[body_faces].mean(1)[:, 0] * sign > 0]
        for height in [.30, .40, .553, .70, .80]:
            x = np.interp(height, [.111, .553, 1.014], [.1664, .141, .0958]) * sign
            rest.append(dict(region=side, height_m=height, **section(points[cloth_faces], body_points[skin_faces],
                np.array([x, height, -.025]), np.array([0, 1., 0]))))
        center, axis, _, _, _ = fit.ankle_interface(side)
        for offset in [-.025, 0, .025]:
            rest.append(dict(region=side + '_ankle', offset_m=offset,
                **section(points[cloth_faces], body_points[skin_faces], center + axis * offset, axis)))
    animation_path = ROOT / 'doc/assets/modular-bard-tripo-pants-animation-v1.json'
    animation = json.loads(animation_path.read_text())
    for entry in animation['sources']:
        assert fit.digest(ROOT / entry['path']) == entry['sha256']
    poses = json.loads((bard.OUTPUT / 'validation-poses.json').read_text())
    assert len(poses) == 91
    panel_ids, panel_normals, panel_weights = hip_panels(points, faces, joints, weights)
    motion, waist_motion, hip_motion = [], [], []
    for pose in poses:
        matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        cloth = deform(points, joints, weights, matrices)
        panels = cloth[faces[panel_ids]]
        normals = np.cross(panels[:, 1] - panels[:, 0], panels[:, 2] - panels[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        rotations = np.linalg.inv(matrices[:, :3, :3]).transpose(0, 2, 1)
        expected = np.einsum('fb,bij,fj->fi', panel_weights, rotations, panel_normals)
        expected /= np.linalg.norm(expected, axis=1)[:, None]
        alignment = np.sum(normals * expected, axis=1)
        hip_motion.append(dict(clip=pose['clip'], time=pose['time'],
            minimum_normal_alignment=float(alignment.min()),
            reversed_panels=int((alignment < 0).sum()),
            worst_face=int(panel_ids[alignment.argmin()])))
        skin = deform_dense(body_points, body_weights, matrices)
        inverse_hips = np.linalg.inv(matrices[fit.NAMES.index('Hips')])
        waist_cloth = (np.column_stack([cloth, np.ones(len(cloth))]) @ inverse_hips.T)[:, :3]
        waist_skin = (np.column_stack([skin, np.ones(len(skin))]) @ inverse_hips.T)[:, :3]
        for height in [1.045, 1.06, 1.075, 1.09, 1.105]:
            waist_motion.append(dict(clip=pose['clip'], time=pose['time'], height_m=height,
                **section(waist_cloth[faces], waist_skin[body_faces],
                    np.array([0, height, -.02]), np.array([0., 1., 0.]), rear=True)))
        for side, sign in [('Left', 1), ('Right', -1)]:
            center, axis, _, _, dense = fit.ankle_interface(side)
            matrix = np.einsum('b,bij->ij', dense, matrices)
            local_cloth = (np.column_stack([cloth, np.ones(len(cloth))]) @ np.linalg.inv(matrix).T)[:, :3]
            local_skin = (np.column_stack([skin, np.ones(len(skin))]) @ np.linalg.inv(matrix).T)[:, :3]
            cloth_faces = faces[(points[faces].mean(1)[:, 0] * sign > 0) & (points[faces, 1].max(1) < .40)]
            skin_faces = body_faces[(body_points[body_faces].mean(1)[:, 0] * sign > 0) & (body_points[body_faces, 1].max(1) < .40)]
            for offset in [-.025, 0, .025]:
                motion.append(dict(clip=pose['clip'], time=pose['time'], side=side, offset_m=offset,
                    **section(local_cloth[cloth_faces], local_skin[skin_faces], center + axis * offset, axis)))
    report = dict(date='2026-10-11', output=fit.validate(path), source=bard.record(bard.SOURCE),
        base=bard.record(ROOT / 'assets/modular_human_male_01/fitted/base.glb'),
        interface=bard.record(ROOT / 'assets/modular_human_male_01/interfaces/v1/interfaces.json'),
        poses=bard.record(bard.OUTPUT / 'validation-poses.json'),
        preserved_source_triangles_and_texture=True, belt_uv_changed_faces=np.flatnonzero(changed).tolist(),
        duplicated_vertices_preserve_geometry_normals_and_skinning=True,
        lower_legs_only_same_side_bones=True,
        outer_hip_motion=hip_motion,
        outer_hip_motion_summary=dict(poses=len(poses), face_ids=panel_ids.tolist(),
            minimum_normal_alignment=min(s['minimum_normal_alignment'] for s in hip_motion),
            reversed_panels=sum(s['reversed_panels'] for s in hip_motion),
            scope='Outer rear hip cloth panels above 2 square cm; posed normals compared with bone-transformed rest normals. Excludes front flexion folds and small belt details.'),
        rest_sections=rest, ankle_motion_sections=motion,
        rear_waist_motion_sections=waist_motion,
        rear_waist_motion_summary=dict(poses=len(poses), sections=len(waist_motion),
            frame='Hips deformation inverse; rear angles 0.35 < theta < pi - 0.35 on a 128-ray ring',
            minimum_clearance_m=min(s['minimum_clearance_m'] for s in waist_motion if s['common_rays']),
            negative_rays=sum(s['negative_rays'] for s in waist_motion),
            missing_garment_rays=sum(s['missing_garment_rays'] for s in waist_motion),
            missing_body_rays=sum(s['missing_body_rays'] for s in waist_motion)),
        ankle_motion_summary=dict(poses=len(poses), sections=len(motion), rays_per_section=64,
            minimum_clearance_m=min(s['minimum_clearance_m'] for s in motion if s['common_rays']),
            negative_rays=sum(s['negative_rays'] for s in motion),
            missing_garment_rays=sum(s['missing_garment_rays'] for s in motion),
            missing_body_rays=sum(s['missing_body_rays'] for s in motion)),
        scope='Same-side ankle sections in the shared ankle deformation frame; rear waist sections in the Hips frame; rest waist/leg sections. Not a full triangle collision or mixed-outfit certification.')
    target = ROOT / 'doc/assets/modular-bard-tripo-pants-validation-v1.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(rest=rest, ankles=report['ankle_motion_summary'],
        rear_waist=report['rear_waist_motion_summary'], outer_hip=report['outer_hip_motion_summary']), indent=2))
    assert all(s['missing_garment_rays'] == 0 and s['common_rays'] >= 60
               and s['negative_rays'] == 0 for s in rest + motion)
    assert all(s['missing_garment_rays'] == 0 and s['missing_body_rays'] == 0
               and s['minimum_clearance_m'] > .002 for s in waist_motion)
    assert all(s['minimum_normal_alignment'] > .5 for s in hip_motion)


if __name__ == '__main__':
    main()
