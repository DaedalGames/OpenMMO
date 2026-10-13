import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, view_bytes
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
TARGET = DIRECTORY / 'fitted_v24'
before, old_binary = read_glb(DIRECTORY / 'fitted_v23/bottom_female_knight.glb')
after, binary = read_glb(TARGET / 'bottom_female_knight.glb')
fitting = json.loads((TARGET / 'fitting.json').read_text())
replacement = fitting['rear_guard_replacement']
source = np.array(replacement['source_vertices'])
destination = np.array(replacement['destination_vertices'])
removed = np.array(replacement['removed_vertices'])
rotation = np.array(replacement['rotation'])
translation = np.array(replacement['translation'])
assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-12)
assert abs(np.linalg.det(rotation) - 1) < 1e-12
for field in ['materials', 'images', 'textures', 'skins', 'animations']:
    assert before.get(field) == after.get(field), field
for image in before.get('images', []):
    assert view_bytes(before, old_binary, image['bufferView']) == view_bytes(after, binary, image['bufferView'])
for index, (old, new) in enumerate(zip(before['meshes'][0]['primitives'], after['meshes'][0]['primitives'], strict=True)):
    old_faces = accessor(before, old_binary, old['indices']).reshape(-1, 3)
    new_faces = accessor(after, binary, new['indices']).reshape(-1, 3)
    if index == 0:
        kept = np.delete(old_faces, replacement['removed_face_indices'], axis=0)
        assert not np.isin(kept, removed).any()
        mapping = dict(zip(source, destination, strict=True))
        copied = np.array([[mapping[vertex] for vertex in face] for face in old_faces[replacement['source_face_indices']]])
        assert np.array_equal(new_faces, np.vstack([kept, copied]))
    else:
        assert np.array_equal(new_faces, old_faces)
    for name, attribute in old['attributes'].items():
        a = accessor(before, old_binary, attribute)
        b = accessor(after, binary, new['attributes'][name])
        if index != 0:
            assert np.array_equal(a, b), (index, name)
            continue
        untouched = np.setdiff1d(np.arange(len(a)), removed)
        assert np.array_equal(a[untouched], b[untouched]), name
        expected = a[source].copy()
        if name == 'POSITION':
            expected = expected @ rotation.T + translation
            distances_before = np.linalg.norm(a[source, None] - a[None, source], axis=2)
            distances_after = np.linalg.norm(b[destination, None] - b[None, destination], axis=2)
            maximum_distance_error = float(abs(distances_before - distances_after).max())
            assert maximum_distance_error < 1e-6
        elif name in ['NORMAL', 'TANGENT']:
            expected[:, :3] = expected[:, :3] @ rotation.T
            assert np.max(abs(np.linalg.norm(b[destination, :3], axis=1) - 1)) < 1e-6
        assert np.allclose(b[destination], expected, rtol=0, atol=1e-7), name
assert (TARGET / 'body-occlusion.json').read_bytes() == (DIRECTORY / 'fitted_v23/body-occlusion.json').read_bytes()
report = {
    'date': '2026-10-13', 'sha256': hashlib.sha256((TARGET / 'bottom_female_knight.glb').read_bytes()).hexdigest(),
    'copied_vertices': len(source), 'removed_triangles': len(replacement['removed_face_indices']),
    'copied_triangles': len(replacement['source_face_indices']), 'maximum_pairwise_distance_error': maximum_distance_error,
    'front_guard_unchanged': True, 'copied_uvs_and_weights': True,
    'unchanged_other_components': True, 'unchanged_materials_textures_rig_and_occlusion': True,
    'scope': 'Exact front-guard copy under a rigid transform and complete removal of the old rear guard; does not prove collision-free motion.',
}
(TARGET / 'guard-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
