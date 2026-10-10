"""Reduce excess thumb volume against the canonical hands, preserving the glove rig."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb, view_bytes

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / 'assets/modular_human_male_01'
parser = argparse.ArgumentParser()
parser.add_argument('--part', choices=['leather', 'plate'], default='leather')
args = parser.parse_args()
SOURCE = PARTS / f'gloves/shape_sources/{args.part}-before-thumb-v1.glb'
TARGET = PARTS / f'fitted/gloves_{args.part}.glb'
REPORT = ROOT / f'doc/assets/modular-{args.part}-glove-thumbs-v1.json'
SOURCE_HASH = {
    'leather': '5baa3dc74cc60e78fc33ebb561b84a28751b3851aadadc79fbd4a29f9a0ac9c3',
    'plate': '9f533effca5d082daddc179971540a372a328c3caa95c934eb8092fbbffd7792',
}[args.part]
CLEARANCE = .006 if args.part == 'plate' else .004
spec = importlib.util.spec_from_file_location('fit', ROOT / 'tools/fit-modular-rogue.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
io = fit.io


def record(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=fit.digest(path))


def main():
    assert record(SOURCE)['sha256'] == SOURCE_HASH
    original, raw = read_glb(SOURCE)
    doc, _ = read_glb(SOURCE)
    binary = bytearray(raw)
    changes = []
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            points = io.accessor(doc, raw, attrs['POSITION'])
            joints = io.accessor(doc, raw, attrs['JOINTS_0'])
            weights = io.accessor(doc, raw, attrs['WEIGHTS_0'])
            adjusted = points.copy()
            first_change = len(changes)
            for side, sign in [('Left', 1), ('Right', -1)]:
                ids = [i for i, name in enumerate(fit.NAMES) if name.startswith(side + 'HandThumb')]
                influence = (weights * np.isin(joints, ids)).sum(1)
                origin = io.BONES[side + 'HandThumb1']
                axis = io.unit(io.BONES[side + 'HandThumb4'] - origin)
                along = (points - origin) @ axis
                amount = io.smoothstep((influence - .15) / .65) * io.smoothstep((along - .02) / .035)
                active = amount > 0
                if not active.any():
                    continue
                vertices, faces, skin = fit.body_surface(('hands',), sign)
                thumb = skin[:, ids].sum(1)
                faces = faces[thumb[faces].mean(1) > .5]
                nearest, normals, _ = fit.nearest_surface(points[active], (vertices, faces, skin))
                delta = points[active] - nearest
                distance = np.linalg.norm(delta, axis=1)
                factor = np.maximum(distance - CLEARANCE, 0) / np.maximum(distance, 1e-10) * amount[active]
                factor[np.sum(delta * normals, axis=1) < 0] = 0
                adjusted[active] -= delta * factor[:, None]
                changes.append(dict(mesh=mesh['name'], primitive=mesh['primitives'].index(primitive), side=side, vertices_changed=int(np.count_nonzero(factor)),
                    maximum_displacement_m=float(np.linalg.norm(points[active] - adjusted[active], axis=1).max())))
            faces = io.accessor(doc, raw, primitive['indices']).reshape(-1, 3)
            cross = lambda p: np.cross(p[faces[:, 1]] - p[faces[:, 0]], p[faces[:, 2]] - p[faces[:, 0]])
            original_cross = cross(points)
            _, weld = np.unique(np.round(points, 6), axis=0, return_inverse=True)
            for _ in range(24):
                folded = np.sum(original_cross * cross(adjusted), axis=1) <= 0
                if not folded.any():
                    break
                soften = np.isin(weld, weld[faces[folded]].ravel())
                adjusted[soften] = points[soften] + .75 * (adjusted[soften] - points[soften])
            assert np.all(np.sum(original_cross * cross(adjusted), axis=1) > 0)
            moved = np.linalg.norm(adjusted - points, axis=1) > 1e-8
            for change in changes[first_change:]:
                side = points[:, 0] * (1 if change['side'] == 'Left' else -1) > 0
                change['vertices_changed'] = int(np.count_nonzero(moved & side))
                change['maximum_displacement_m'] = float(np.linalg.norm(adjusted[side] - points[side], axis=1).max())
            normals = io.smooth_normals(adjusted, faces)
            normals[~moved] = io.accessor(doc, raw, attrs['NORMAL'])[~moved]
            attrs['POSITION'] = io.add_accessor(doc, binary, adjusted, 'VEC3')
            attrs['NORMAL'] = io.add_accessor(doc, binary, normals, 'VEC3')
            if 'TANGENT' in attrs:
                uv = io.accessor(doc, raw, attrs['TEXCOORD_0'])
                tangents = io.tangents(adjusted, normals, uv, faces)
                tangents[~moved] = io.accessor(doc, raw, attrs['TANGENT'])[~moved]
                attrs['TANGENT'] = io.add_accessor(doc, binary, tangents, 'VEC4')
    binary = io.compact(doc, binary)
    for old_mesh, mesh in zip(original['meshes'], doc['meshes']):
        for old, new in zip(old_mesh['primitives'], mesh['primitives']):
            assert np.array_equal(io.accessor(original, raw, old['indices']), io.accessor(doc, binary, new['indices']))
            for name, index in old['attributes'].items():
                values = io.accessor(doc, binary, new['attributes'][name])
                assert np.isfinite(values).all()
                if name not in ('POSITION', 'NORMAL', 'TANGENT'):
                    assert np.array_equal(io.accessor(original, raw, index), values), name
    assert original['nodes'] == doc['nodes']
    for old, new in zip(original['skins'], doc['skins']):
        assert np.array_equal(io.accessor(original, raw, old['inverseBindMatrices']),
                              io.accessor(doc, binary, new['inverseBindMatrices']))
    assert [view_bytes(original, raw, i['bufferView']) for i in original['images']] == [
        view_bytes(doc, binary, i['bufferView']) for i in doc['images']]
    if args.part == 'plate':
        io.validate_closed_gloves(doc, binary)
    temporary = TARGET.with_suffix('.tmp.glb')
    try:
        write_glb(temporary, doc, binary)
        known = {SOURCE_HASH, record(temporary)['sha256']}
        if REPORT.exists():
            known.add(json.loads(REPORT.read_text())['output']['sha256'])
        assert record(TARGET)['sha256'] in known, 'Glove changed after this edit; review before overwriting'
        temporary.replace(TARGET)
    finally:
        temporary.unlink(missing_ok=True)
    REPORT.write_text(json.dumps(dict(date='2026-10-10', source=record(SOURCE), output=record(TARGET),
        body=record(PARTS / 'fitted/base.glb'), changes=changes, target_clearance_m=CLEARANCE,
        method='Shrink only excess thumb volume toward its canonical skin surface; blend at the palm and keep the existing finger weights',
        preserved=['triangle topology', 'UV', 'textures', 'skin weights', 'skeleton and bind pose'],
        source_and_license=f'Existing Meshy {args.part} gloves; local geometry edit, no additional generation'), indent=2) + '\n')
    print(json.dumps(changes))


if __name__ == '__main__':
    main()
