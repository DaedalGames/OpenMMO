"""Check bard skin influences, preserved source data and body cross sections."""
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bard', ROOT / 'tools/fit-tripo-bard-top.py')
bard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bard)
fit, io = bard.fit, bard.io
from outfits.radial_sections import clearance
from outfits.skinning import deform, deform_dense


def main():
    path = bard.OUTPUT / 'top_bard.glb'
    doc, binary = fit.read_glb(path)
    source, raw = fit.read_glb(bard.SOURCE)
    primitive = doc['meshes'][0]['primitives'][0]
    original = source['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = io.accessor(doc, binary, attrs['POSITION'])
    faces = io.accessor(doc, binary, primitive['indices']).reshape(-1, 3)
    source_points = io.accessor(source, raw, original['attributes']['POSITION'])
    joints = io.accessor(doc, binary, attrs['JOINTS_0'])
    weights = io.accessor(doc, binary, attrs['WEIGHTS_0'])
    original_faces = io.accessor(source, raw, original['indices']).reshape(-1, 3)
    fitting = json.loads((ROOT / 'doc/assets/modular-bard-tripo-top-fitting-v1.json').read_text())
    retained = np.ones(len(original_faces), dtype=bool)
    retained[fitting['removed_inner_cuff_and_collar_faces']] = False
    assert np.array_equal(faces, original_faces[retained])
    assert np.array_equal(io.accessor(doc, binary, attrs['TEXCOORD_0']), io.accessor(source, raw, original['attributes']['TEXCOORD_0']))
    assert [bard.view_bytes(doc, binary, i['bufferView']) for i in doc['images']] == [bard.view_bytes(source, raw, i['bufferView']) for i in source['images']]
    for side, sign in [('Left', 1), ('Right', -1)]:
        cuff = source_points[:, 0] * sign > .39
        allowed = {fit.NAMES.index(side + name) for name in ['Arm', 'ForeArm', 'Hand']}
        assert all(int(j) in allowed for j in joints[cuff][weights[cuff] > 1e-6]), 'Cuff attached to torso, pelvis or opposite arm'
    hem = (source_points[:, 1] < .12) & (abs(source_points[:, 0]) < .28)
    assert all('Arm' not in fit.NAMES[j] and 'Hand' not in fit.NAMES[j] for j in joints[hem][weights[hem] > 1e-5])
    body_points, body_faces, _ = fit.body_surface(('torso', 'neck', 'upper_arms', 'forearms', 'hands', 'legs'))
    interface_path = ROOT / 'assets/modular_human_male_01/interfaces/v1/interfaces.json'
    interfaces = json.loads(interface_path.read_text())
    sections = []
    for entry in interfaces['interfaces']:
        if entry['name'] not in ['neck_base', 'waist', 'glove_short_Left', 'glove_short_Right']:
            continue
        for offset in [0, .015, .030]:
            axis = np.array(entry['normal'])
            axis /= np.linalg.norm(axis)
            center = np.array(entry['center']) + axis * offset
            result = clearance(points[faces], body_points[body_faces], center, axis,
                               .12 if entry['name'].startswith('glove') else .35)
            sections.append(dict(interface=entry['name'], offset_m=offset, **result))
    animation = json.loads((ROOT / 'doc/assets/modular-bard-tripo-top-animation-v1.json').read_text())
    for entry in animation['sources']:
        assert fit.digest(ROOT / entry['path']) == entry['sha256']
    poses = json.loads((bard.OUTPUT / 'validation-poses.json').read_text())
    arms, arm_faces, arm_weights = fit.body_surface(('forearms', 'hands'))
    motion = []
    for pose in poses:
        matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        cloth = deform(points, joints, weights, matrices)
        body = deform_dense(arms, arm_weights, matrices)
        samples = []
        for entry in interfaces['interfaces']:
            if not entry['name'].startswith('glove_short_'):
                continue
            side = entry['name'].rsplit('_', 1)[1]
            sign = 1 if side == 'Left' else -1
            sleeve_faces = (source_points[faces].mean(1)[:, 0] * sign > .32)
            same_arm = arms[arm_faces].mean(1)[:, 0] * sign > .20
            matrix = matrices[fit.NAMES.index(side + 'ForeArm')]
            axis = matrix[:3, :3] @ np.array(entry['normal'])
            axis /= np.linalg.norm(axis)
            center = (matrix @ np.r_[entry['center'], 1])[:3]
            for offset in [0, .015, .030]:
                result = clearance(cloth[faces[sleeve_faces]], body[arm_faces[same_arm]], center + axis * offset, axis, .12)
                samples.append(dict(side=side, offset_m=offset, **result))
        motion.append(dict(clip=pose['clip'], time=pose['time'], sections=samples))
    wrist_sections = [section for pose in motion for section in pose['sections']]
    assert len(poses) == 91
    assert all(section['common_rays'] == 64 and section['negative_rays'] == 0 for section in wrist_sections)
    assert all(section['negative_rays'] == 0 for section in sections)
    report = dict(date='2026-10-10', status='Canonical rig, source preservation, region isolation and sampled wrist clearance passed',
                  source=fit.digest(bard.SOURCE), output=fit.validate(path),
                  retained_source_faces_and_uv_and_texture_verified=True, cuffs_only_same_side_arm_bones=True,
                  hem_has_no_arm_or_hand_weights=True, interface_sha256=fit.digest(interface_path),
                  rest_sections=sections,
                  wrist_motion_sections=motion,
                  wrist_motion_summary=dict(poses=len(poses), sections=len(wrist_sections), rays_per_section=64,
                                            minimum_clearance_m=min(section['minimum_clearance_m'] for section in wrist_sections),
                                            missing_rays=0, negative_rays=0),
                  interpretation='Rays cover visible openings and multiple cloth layers. Missing rays are not automatically defects; inspect cuff and collar renders. Mixed gloves/pants are not certified.')
    target = ROOT / 'doc/assets/modular-bard-tripo-top-validation-v1.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(sections, indent=2))


if __name__ == '__main__':
    main()
