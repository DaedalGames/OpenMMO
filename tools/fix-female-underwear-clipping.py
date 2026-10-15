import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
RUNTIME = ROOT / 'client/public/models/characters/modular_female/base.glb'
OUTPUT = ROOT / 'assets/modular_human_female_01/underwear_fit_v1'
SOURCE_SHA = 'd49dd18893b6de9289f6d35eb8946781d5db793e0bcba031e5672a4ce6e247c6'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch(path, doc, indices, joints, weights):
    data = bytearray(path.read_bytes())
    binary_start = 28 + int.from_bytes(data[12:16], 'little')
    attrs = doc['meshes'][0]['primitives'][0]['attributes']
    for name, values in [('JOINTS_0', joints), ('WEIGHTS_0', weights)]:
        item = doc['accessors'][attrs[name]]
        view = doc['bufferViews'][item['bufferView']]
        dtype = {5121: '<u1', 5123: '<u2', 5126: '<f4'}[item['componentType']]
        size = np.dtype(dtype).itemsize
        array = np.ndarray((item['count'], 4), dtype=dtype, buffer=data,
                           offset=binary_start + view.get('byteOffset', 0) + item.get('byteOffset', 0),
                           strides=(view.get('byteStride', 4 * size), size))
        array[indices] = values
    path.write_bytes(data)


def main():
    report_path = OUTPUT / 'fitting.json'
    if report_path.exists() and digest(BODY) == json.loads(report_path.read_text())['output_sha256']:
        print('Underwear weights already corrected')
        return
    assert digest(BODY) == SOURCE_SHA, 'Unexpected female base; review the source before fitting'
    doc, binary = read_glb(BODY)
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = accessor(doc, binary, attrs['POSITION'])
    faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
    joints = accessor(doc, binary, attrs['JOINTS_0'])
    weights = accessor(doc, binary, attrs['WEIGHTS_0'])
    names = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
    _, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    welded = welded.ravel()
    edges = welded[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
    _, components = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                                                    shape=(welded.max() + 1,) * 2), directed=False)
    labels = components[welded]
    skin, bra = np.argsort(np.bincount(labels))[-2:][::-1]
    bra_indices = np.flatnonzero(labels == bra)
    assert points[bra_indices, 1].min() > .69 and points[bra_indices, 1].max() < .86
    skin_faces = faces[(labels[faces[:, 0]] == skin) & (points[faces, 1].min(1) > .67)
                       & (points[faces, 1].max(1) < .87)]
    surface = trimesh.Trimesh(points, skin_faces, process=False)
    centers = np.array([[-.08002812, .73636216, .03854832], [.08002812, .73636216, .03854832]])
    radius = np.linalg.norm(points[bra_indices, None] - centers[None], axis=2).min(1)
    t = np.clip((radius - .012) / .015, 0, 1)
    influence = 1 - t * t * (3 - 2 * t)
    indices = bra_indices[influence > 0]
    influence = influence[influence > 0]
    closest, _, triangles = trimesh.proximity.closest_point(surface, points[indices])
    bary = trimesh.triangles.points_to_barycentric(surface.triangles[triangles], closest).clip(0, 1)
    bary /= bary.sum(1, keepdims=True)
    original = np.zeros((len(indices), len(names)))
    transferred = np.zeros_like(original)
    for slot in range(4):
        original[np.arange(len(indices)), joints[indices, slot]] += weights[indices, slot]
    for corner in range(3):
        vertices = skin_faces[triangles, corner]
        for slot in range(4):
            np.add.at(transferred, (np.arange(len(indices)), joints[vertices, slot]),
                      bary[:, corner] * weights[vertices, slot])
    combined = original * (1 - influence[:, None]) + transferred * influence[:, None]
    corrected_joints = np.argsort(-combined, axis=1)[:, :4]
    corrected_weights = np.take_along_axis(combined, corrected_joints, 1)
    corrected_weights /= corrected_weights.sum(1, keepdims=True)
    OUTPUT.mkdir(exist_ok=True)
    np.savez(OUTPUT / 'source-influences.npz', indices=indices, positions=points[indices],
             original_joints=joints[indices], original_weights=weights[indices],
             corrected_joints=corrected_joints, corrected_weights=corrected_weights,
             bone_names=np.array(names))
    patch(BODY, doc, indices, corrected_joints, corrected_weights)
    runtime_before = digest(RUNTIME)
    runtime_doc, runtime_binary = read_glb(RUNTIME)
    runtime_attrs = runtime_doc['meshes'][0]['primitives'][0]['attributes']
    runtime_points = accessor(runtime_doc, runtime_binary, runtime_attrs['POSITION'])
    assert np.allclose(runtime_points, points * 1.8, atol=2e-7)
    runtime_names = [runtime_doc['nodes'][i]['name'] for i in runtime_doc['skins'][0]['joints']]
    runtime_joints = np.array([runtime_names.index(names[i]) for i in corrected_joints.ravel()]).reshape(-1, 4)
    patch(RUNTIME, runtime_doc, indices, runtime_joints, corrected_weights)
    report = {'date': '2026-10-15', 'source_sha256': SOURCE_SHA, 'output_sha256': digest(BODY),
              'body': str(BODY.relative_to(ROOT)), 'runtime': str(RUNTIME.relative_to(ROOT)),
              'runtime_sha256_before': runtime_before, 'runtime_sha256_after': digest(RUNTIME),
              'changed_underwear_vertices': len(indices), 'patch_centers': centers.tolist(),
              'full_transfer_radius': .012, 'falloff_radius': .027,
              'method': 'Blend the lower outer cup weights toward barycentric skin weights, retaining four normalized influences.',
              'preserved': ['All positions, normals, UVs, indices, images, materials, skin weights, rig and animations']}
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
