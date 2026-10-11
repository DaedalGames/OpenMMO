"""Check mirrored source preservation and posed clearance through the cuff band."""
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import view_bytes
from outfits.radial_sections import clearance
from outfits.skinning import deform

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bard', ROOT / 'tools/fit-tripo-bard-boots.py')
bard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bard)
fit, io = bard.fit, bard.io


def arrays(doc, binary, primitive):
    attrs = primitive['attributes']
    return [io.accessor(doc, binary, attrs[name]) for name in ['POSITION', 'JOINTS_0', 'WEIGHTS_0']] + [
        io.accessor(doc, binary, primitive['indices']).reshape(-1, 3)]


def main():
    assets = ROOT / 'assets/items/bard_starter/tripo_boots_v1'
    path = bard.OUTPUT / 'boots_bard.glb'
    source, raw = fit.read_glb(bard.SOURCE)
    doc, binary = fit.read_glb(path)
    original = source['meshes'][0]['primitives'][0]
    faces = io.accessor(source, raw, original['indices']).reshape(-1, 3)
    uv = io.accessor(source, raw, original['attributes']['TEXCOORD_0'])
    assert [view_bytes(source, raw, i['bufferView']) for i in source['images']] == [
        view_bytes(doc, binary, i['bufferView']) for i in doc['images']]
    boots = {}
    for index, side in enumerate(['Right', 'Left']):
        primitive = doc['meshes'][index]['primitives'][0]
        points, joints, weights, triangles = arrays(doc, binary, primitive)
        assert np.array_equal(triangles, faces if side == 'Right' else faces[:, ::-1])
        assert np.array_equal(uv, io.accessor(doc, binary, primitive['attributes']['TEXCOORD_0']))
        allowed = {fit.NAMES.index(side + bone) for bone in ['Leg', 'Foot', 'ToeBase']}
        assert all(int(j) in allowed for j in joints[weights > 1e-6])
        boots[side] = points, joints, weights, triangles
    assert np.array_equal(boots['Right'][0] * [-1, 1, 1], boots['Left'][0])
    pants_doc, pants_raw = fit.read_glb(assets / 'pants-bard-boots-review.glb')
    pants, joints, weights, pants_faces = arrays(pants_doc, pants_raw, pants_doc['meshes'][0]['primitives'][0])
    animation = json.loads((ROOT / 'doc/assets/modular-bard-tripo-boots-animation-v1.json').read_text())
    for record in animation['sources'] + [animation['snapshot']]:
        assert fit.digest(ROOT / record['path']) == record['sha256']
    poses = json.loads((assets / 'validation-poses.json').read_text())
    assert len(poses) == 91
    rows = []
    for pose in [dict(clip='rest', time=0, matrices=np.tile(np.eye(4).reshape(-1), (65, 1)).tolist()), *poses]:
        matrices = np.asarray(pose['matrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        trousers = deform(pants, joints, weights, matrices)
        for side, sign in [('Right', -1), ('Left', 1)]:
            points, skin, influence, triangles = boots[side]
            shoes = deform(points, skin, influence, matrices)
            own = pants_faces[pants[pants_faces].mean(1)[:, 0] * sign > 0]
            matrix = matrices[fit.NAMES.index(side + 'Leg')]
            axis = matrix[:3, :3] @ [0, 1, 0]
            axis /= np.linalg.norm(axis)
            for height in [.45, .47, .49, .51, .52]:
                center = (matrix @ [sign * .157, height, -.038, 1])[:3]
                result = clearance(shoes[triangles], trousers[own], center, axis, limit=.2)
                assert result['common_rays'] >= 20, (pose['clip'], side, height, result)
                assert result['negative_rays'] == 0, (pose['clip'], side, height, result)
                rows.append(dict(clip=pose['clip'], time=pose['time'], side=side, height_m=height, **result))
    result = dict(date='2026-10-11', source=bard.record(bard.SOURCE), output=bard.record(path),
        exact_mirror_winding_uv_texture_and_side_bones=True, validation=fit.validate(path),
        cuff_sections=len(rows), rays_per_section=64,
        minimum_cuff_band_clearance_m=min(r['minimum_clearance_m'] for r in rows),
        negative_rays=sum(r['negative_rays'] for r in rows),
        missing_boot_rays=sum(r['missing_garment_rays'] for r in rows),
        sections=rows,
        scope='Rest and 91 game poses; five sections through each boot cuff. Missing rays near the open cuff are recorded, not treated as closed wall. No full triangle collision or mixed-equipment certification.')
    (ROOT / 'doc/assets/modular-bard-tripo-boots-validation-v1.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'sections'}))


if __name__ == '__main__':
    main()
