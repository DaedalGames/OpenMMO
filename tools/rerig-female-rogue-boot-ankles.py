"""Bind the rogue boot ankle to the anatomical ankle instead of the lower shin."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, view_bytes, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.female_boot_pose import heel_pose, node_worlds
from outfits.rogue_layers import compact_weights
from outfits.skinning import deform

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_rogue_boots/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v3/boots_female_rogue.glb'
OUTPUT = DIRECTORY / 'fitted_v5'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'


def smooth(values):
    t = np.clip(values, 0, 1)
    return t * t * (3 - 2 * t)


def main():
    OUTPUT.mkdir(exist_ok=True)
    doc, original = read_glb(SOURCE)
    binary = bytearray(original)
    base, body_raw = read_glb(BODY)
    matrices, _ = heel_pose(base, body_raw)
    names = [base['nodes'][i]['name'] for i in base['skins'][0]['joints']]
    worlds = node_worlds(base)
    nodes = {node.get('name'): i for i, node in enumerate(base['nodes'])}
    bp = base['meshes'][0]['primitives'][0]
    ba = bp['attributes']
    body_points = accessor(base, body_raw, ba['POSITION'])
    body_faces = accessor(base, body_raw, bp['indices']).reshape(-1, 3)
    body_joints = accessor(base, body_raw, ba['JOINTS_0']).astype(int)
    body_weights = accessor(base, body_raw, ba['WEIGHTS_0'])
    posed_body = deform(body_points, body_joints, body_weights, matrices)
    body_dense = np.zeros((len(body_points), len(names)))
    np.put_along_axis(body_dense, body_joints, body_weights, axis=1)
    spec = importlib.util.spec_from_file_location('surface', ROOT / 'tools/fit-modular-rogue.py')
    surface = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(surface)
    records, morphs = [], []
    for mesh in doc['meshes']:
        primitive = mesh['primitives'][0]
        attrs = primitive['attributes']
        points = accessor(doc, original, attrs['POSITION']).astype(float)
        normals = accessor(doc, original, attrs['NORMAL']).astype(float)
        joints = accessor(doc, original, attrs['JOINTS_0']).astype(int)
        weights = accessor(doc, original, attrs['WEIGHTS_0']).astype(float)
        side = 'Right' if mesh['name'].endswith('right') else 'Left'
        posed = deform(points, joints, weights, matrices)
        changed = (posed[:, 1] > .075) & (posed[:, 1] < .27)
        own = [names.index(side + name) for name in ['Leg', 'Foot', 'ToeBase']]
        skin_faces = body_faces[(body_dense[:, own].sum(1)[body_faces] > .5).all(1)]
        _, _, transferred = surface.nearest_surface(posed[changed], (posed_body, skin_faces, body_dense), candidates=64)
        permitted = [names.index(side + name) for name in ['Leg', 'Foot', 'ToeBase']]
        transferred[:, [i for i in range(len(names)) if i not in permitted]] = 0
        transferred[:, names.index(side + 'Foot')] += transferred[:, names.index(side + 'ToeBase')]
        transferred[:, names.index(side + 'ToeBase')] = 0
        transferred /= transferred.sum(1, keepdims=True)
        sole = 1 - smooth((posed[changed, 1] - .075) / .02)
        transferred *= 1 - sole[:, None]
        transferred[:, names.index(side + 'Foot')] += sole
        ankle = worlds[nodes[side + 'Foot'], :3, 3]
        forward = worlds[nodes[side + 'ToeBase'], :3, 3] - ankle
        forward[1] = 0
        forward /= np.linalg.norm(forward)
        local = posed[changed]
        instep = smooth(((local - ankle) @ forward - .005) / .035)
        instep *= 1 - smooth((local[:, 1] - .10) / .035)
        foot = np.maximum(transferred[:, names.index(side + 'Foot')], instep)
        foot *= 1 - smooth((local[:, 1] - .115) / .025)
        transferred[:, names.index(side + 'Foot')] = foot
        transferred[:, names.index(side + 'Leg')] = 1 - foot
        dense = np.zeros((len(points), len(names)))
        np.put_along_axis(dense, joints, weights, axis=1)
        dense[changed] = transferred
        new_joints, new_weights = compact_weights(dense)
        new_joints[~changed], new_weights[~changed] = joints[~changed], weights[~changed]
        old_matrix = np.einsum('nk,nkij->nij', weights, matrices[joints])
        new_matrix = np.einsum('nk,nkij->nij', new_weights, matrices[new_joints])

        def transform(values):
            target = deform(values, joints, weights, matrices)
            result = np.linalg.solve(new_matrix, np.column_stack([target, np.ones(len(target))])[..., None])[:, :3, 0]
            result[~changed] = values[~changed]
            return result

        fitted = transform(points)
        equipped_normal = np.einsum('nij,nj->ni', old_matrix[:, :3, :3], normals)
        normal = np.linalg.solve(new_matrix[:, :3, :3], equipped_normal[..., None])[..., 0]
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        normal[~changed] = normals[~changed]
        attrs['POSITION'] = add_accessor(doc, binary, fitted, 'VEC3')
        attrs['NORMAL'] = add_accessor(doc, binary, normal, 'VEC3')
        attrs['JOINTS_0'] = add_accessor(doc, binary, new_joints, 'VEC4', 5123)
        attrs['WEIGHTS_0'] = add_accessor(doc, binary, new_weights, 'VEC4')
        targets = []
        for target in primitive.pop('targets', []):
            delta = accessor(doc, original, target['POSITION'])
            assert np.allclose(delta[changed], 0, atol=1e-8)
            targets.append({name: accessor(doc, original, index) for name, index in target.items()})
        morphs.append(targets)
        high = changed & (posed[:, 1] >= .17)
        records.append({'side': side, 'changed_vertices': int(changed.sum()), 'maximum_foot_weight_above_170mm': float(dense[high, names.index(side + 'Foot')].max()), 'transfer': 'Same-side anatomical skin in the heel-equipped pose; no lower-shin Foot override.'})
    spec = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
    plate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plate)
    binary = bytearray(plate.compact(doc, binary))
    for mesh, targets in zip(doc['meshes'], morphs):
        if targets:
            mesh['primitives'][0]['targets'] = [{name: add_accessor(doc, binary, values, 'VEC3') for name, values in target.items()} for target in targets]
    doc['buffers'][0]['byteLength'] = len(binary)
    source, _ = read_glb(SOURCE)
    assert [view_bytes(doc, binary, i['bufferView']) for i in doc['images']] == [view_bytes(source, original, i['bufferView']) for i in source['images']]
    target = OUTPUT / SOURCE.name
    write_glb(target, doc, binary)
    for name in ['body-occlusion.json', 'heel-pose.json']:
        (OUTPUT / name).write_bytes((SOURCE.parent / name).read_bytes())
    report = {'date': '2026-10-26', 'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(), 'triangles': 4210, 'rig_id': 'human_female_01_local_v1', 'correction': 'Transfer anatomical ankle skin weights in the heel-equipped pose and inverse-bind the original v3 shape. Remove the synthetic Foot influence extending into the shin. Preserve equipped shape, sole/heel rigidity, UVs, PBR and seated cuff morph.', 'parts': records, 'status': 'Pending motion and visual review; no new generation.'}
    (OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
