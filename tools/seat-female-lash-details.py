"""Locally align marked upper lashes while retaining ribbon widths and topology."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/modular_human_female_01'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['v13', 'v14'], default='v13')
    version = parser.parse_args().version
    refine = version == 'v14'
    previous = 'v13' if refine else 'v12'
    source = BASE / f'eyelashes_{previous}/base-eyelashes-{previous}.glb'
    out = BASE / f'eyelashes_{version}'
    doc, source_binary = read_glb(source)
    binary = bytearray(source_binary)
    primitive = doc['meshes'][0]['primitives'][2]

    def read(index):
        item = doc['accessors'][index]
        view = doc['bufferViews'][item['bufferView']]
        width = {'VEC3': 3, 'SCALAR': 1}[item['type']]
        dtype = {5126: '<f4', 5123: '<u2', 5125: '<u4'}[item['componentType']]
        assert view.get('byteStride', np.dtype(dtype).itemsize * width) == np.dtype(dtype).itemsize * width
        offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
        return np.frombuffer(binary, dtype, item['count'] * width, offset).reshape(-1, width)

    positions = read(primitive['attributes']['POSITION'])
    normals = read(primitive['attributes']['NORMAL'])
    faces = read(primitive['indices']).reshape(-1, 3)
    before = positions.copy()
    before_normals = normals.copy()
    roots = before.reshape(-1, 9, 2, 3)[:, 0].mean(axis=1).astype(float)
    changes = {}
    if refine:
        for strand, fade in zip(range(3, 11), [.4, .65, .85, 1, 1, 1, .8, .45]):
            changes[strand] = ('raise_root_curve', np.array([0, .00020, .00004]) * fade)
        for strand, fade in zip(range(12, 23), [.5, .8, 1, 1, 1, 1, 1, 1, .85, .6, .3]):
            changes[strand] = ('tilt_forward', np.deg2rad(10 * fade))
    else:
        for strand in (14, 15):
            weight = (roots[strand, 0] - roots[13, 0]) / (roots[16, 0] - roots[13, 0])
            target = roots[13] * (1 - weight) + roots[16] * weight
            delta = target - roots[strand]
            delta[0] = 0
            changes[strand] = ('lower_raised_root', delta)
        for strand, fade in zip(range(3, 11), [.5, .75, 1, 1, 1, 1, .75, .5]):
            changes[strand] = ('expose_buried_root', np.array([0, 0, .00018 * fade]))
    records = []
    affected = np.zeros(len(positions), dtype=bool)
    translation_weights = [1, .8, .4, .1] if refine else [1, .75, .25]
    for strand, (reason, delta) in changes.items():
        start = strand * 18
        rotating = reason == 'tilt_forward'
        if rotating:
            axis = before[start + 1].astype(float) - before[start]
            axis /= np.linalg.norm(axis)
            direction = before[start + 16:start + 18].mean(axis=0) - roots[strand]
            if np.cross(axis, direction)[2] < 0:
                axis *= -1
            relative = before[start:start + 18].astype(float) - roots[strand]
            rotated = (relative * np.cos(delta) + np.cross(axis, relative) * np.sin(delta) +
                       np.outer(relative @ axis, axis) * (1 - np.cos(delta)))
            positions[start:start + 18] = roots[strand] + rotated
            positions[start:start + 2] = before[start:start + 2]
            assert positions[start + 16:start + 18, 2].mean() > before[start + 16:start + 18, 2].mean()
            records.append({'strand': strand, 'reason': reason, 'angle_degrees': float(np.rad2deg(delta)),
                            'axis': axis.tolist(), 'root_pair_unchanged': True})
        else:
            for segment, weight in enumerate(translation_weights):
                pair = slice(start + 2 * segment, start + 2 * segment + 2)
                positions[pair] = before[pair].astype(float) + delta * weight
            unchanged_start = start + 2 * len(translation_weights)
            assert np.array_equal(positions[unchanged_start:start + 18], before[unchanged_start:start + 18])
            records.append({'strand': strand, 'reason': reason, 'root_delta': delta.tolist()})
        local_faces = faces[faces[:, 0] // 18 == strand] - start
        strip = positions[start:start + 18].astype(float)
        accumulated = np.zeros((18, 3))
        for face in local_faces:
            cross = np.cross(strip[face[1]] - strip[face[0]], strip[face[2]] - strip[face[0]])
            assert np.linalg.norm(cross) > 1e-13
            accumulated[face] += cross
        lengths = np.linalg.norm(accumulated, axis=1)
        assert (lengths > 0).all()
        accumulated /= lengths[:, None]
        accumulated[np.sum(accumulated * before_normals[start:start + 18], axis=1) < 0] *= -1
        count = 18 if rotating else 2 * (len(translation_weights) + 1)
        normals[start:start + count] = accumulated[:count]
        affected[start:start + count] = True
        assert np.allclose(np.linalg.norm(np.diff(strip.reshape(9, 2, 3), axis=1), axis=2),
                           np.linalg.norm(np.diff(before[start:start + 18].reshape(9, 2, 3), axis=1), axis=2), atol=1e-7)
    assert np.array_equal(positions[~affected], before[~affected])
    assert np.array_equal(normals[~affected], before_normals[~affected])
    assert np.isfinite(positions).all() and np.isfinite(normals).all()
    doc['accessors'][primitive['attributes']['POSITION']].update(
        min=positions.min(axis=0).tolist(), max=positions.max(axis=0).tolist())
    out.mkdir(exist_ok=True)
    path = out / f'base-eyelashes-{version}.glb'
    write_glb(path, doc, binary)
    subprocess.run(['blender', '-b', '--python-expr',
                    'import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); '
                    f'bpy.ops.import_scene.gltf(filepath={str(path)!r}); '
                    'bpy.context.preferences.filepaths.save_version = 0; bpy.ops.file.pack_all(); '
                    f'bpy.ops.wm.save_as_mainfile(filepath={str(path.with_suffix(".blend"))!r})'], check=True)
    report = {'source': str(source.relative_to(ROOT)),
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'output_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'primitive': 2, 'side': 'positive X upper lashes', 'strands': records,
              'segment_translation_weights': translation_weights + [0] * (9 - len(translation_weights)),
              'changed_position_vertices': int(np.any(positions != before, axis=1).sum()),
              'changed_normal_vertices': int(np.any(normals != before_normals, axis=1).sum()),
              'unselected_vertices_unchanged': True, 'widths_preserved': True,
              'triangle_count': 22175}
    if not refine:
        report['outer_62_5_percent_positions_unchanged'] = True
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
