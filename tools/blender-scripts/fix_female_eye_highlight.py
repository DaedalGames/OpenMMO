# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
"""Repair the isolated lower-right-eye vertex-normal discontinuity."""
import hashlib
import json
import struct
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/modular_human_female_01/nose_v11/base-nose-v11.glb'
OUT = ROOT / 'assets/modular_human_female_01/eye_normals_v1'


def main():
    raw = SOURCE.read_bytes()
    json_size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + json_size])
    binary_start = 28 + json_size
    result = bytearray(raw)
    primitive = doc['meshes'][0]['primitives'][0]

    def attribute(name):
        accessor = doc['accessors'][primitive['attributes'][name]]
        view = doc['bufferViews'][accessor['bufferView']]
        assert accessor['componentType'] == 5126 and accessor['type'] == 'VEC3'
        assert view.get('byteStride', 12) == 12
        offset = binary_start + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        return np.frombuffer(result, dtype='<f4', count=accessor['count'] * 3, offset=offset).reshape(-1, 3)

    positions = attribute('POSITION')
    normals = attribute('NORMAL')
    before = normals.copy()
    anchor = np.array([-.0166432485, .9335613251, .0388790071])
    affected = np.flatnonzero(np.linalg.norm(positions - anchor, axis=1) < 1e-7)
    assert len(affected) == 5
    center = positions[affected[0]].copy()
    row = np.flatnonzero((np.abs(positions[:, 1] - center[1]) < 1e-7) &
                        (np.abs(positions[:, 0] - center[0]) < .002) &
                        (np.abs(positions[:, 2] - center[2]) < .0002))
    left_x = positions[row[positions[row, 0] < center[0] - 1e-7], 0].max()
    right_x = positions[row[positions[row, 0] > center[0] + 1e-7], 0].min()
    left = row[np.abs(positions[row, 0] - left_x) < 1e-7]
    right = row[np.abs(positions[row, 0] - right_x) < 1e-7]
    weight = float((center[0] - left_x) / (right_x - left_x))
    corrected = before[left].mean(axis=0) * (1 - weight) + before[right].mean(axis=0) * weight
    corrected /= np.linalg.norm(corrected)
    assert before[affected[0], 1] > .3 and corrected[1] < -.3
    normals[affected] = corrected
    changed = np.flatnonzero(np.any(normals != before, axis=1))
    assert np.array_equal(changed, affected)
    unchanged = np.ones(len(normals), dtype=bool)
    unchanged[affected] = False
    assert np.array_equal(normals[unchanged], before[unchanged])
    OUT.mkdir(exist_ok=True)
    path = OUT / 'base-eye-normals-v1.glb'
    path.write_bytes(result)
    report = {
        'source': str(SOURCE.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'output_sha256': hashlib.sha256(result).hexdigest(),
        'affected_vertex_indices': affected.tolist(),
        'surface_position': center.tolist(),
        'previous_normals': before[affected].tolist(),
        'corrected_normal': corrected.tolist(),
        'neighbor_indices': {'left': left.tolist(), 'right': right.tolist()},
        'method': 'Interpolate adjacent lower-eye rim normals by horizontal position; update all coincident UV-seam copies.',
        'triangles': 22175,
        'positions_uv_indices_materials_textures_unchanged': True,
    }
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'base-eye-normals-v1.blend'))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
