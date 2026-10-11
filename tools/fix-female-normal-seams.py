"""Neutralize local normal-map seams in the existing UV atlas."""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter

from lib.glb import read_glb, view_bytes, write_glb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/modular_human_female_01'


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=['brows', 'ear', 'opposite-ear'], default='brows')
    region = parser.parse_args().region
    ear = region != 'brows'
    opposite = region == 'opposite-ear'
    sources = {
        'brows': ('lips_v1/base-lips-v1.glb', 'brow_normals_v1'),
        'ear': ('eyelashes_v14/base-eyelashes-v14.glb', 'ear_normals_v1'),
        'opposite-ear': ('ear_normals_v1/base-ear-normals-v1.glb', 'ear_normals_v2'),
    }
    source_name, out_name = sources[region]
    source, out = BASE / source_name, BASE / out_name
    doc, binary = read_glb(source)
    primitive = doc['meshes'][0]['primitives'][0]

    def accessor(index):
        item = doc['accessors'][index]
        view = doc['bufferViews'][item['bufferView']]
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[item['type']]
        dtype = {5123: '<u2', 5125: '<u4', 5126: '<f4'}[item['componentType']]
        assert view.get('byteStride', np.dtype(dtype).itemsize * width) == np.dtype(dtype).itemsize * width
        return np.frombuffer(binary, dtype, item['count'] * width,
                             view.get('byteOffset', 0) + item.get('byteOffset', 0)).reshape(-1, width)

    positions = accessor(primitive['attributes']['POSITION'])
    uv = accessor(primitive['attributes']['TEXCOORD_0'])
    triangles = accessor(primitive['indices']).reshape(-1, 3)
    texture = doc['materials'][primitive['material']]['normalTexture']['index']
    image = doc['images'][doc['textures'][texture]['source']]
    before = np.array(Image.open(io.BytesIO(view_bytes(doc, binary, image['bufferView']))))
    height, width = before.shape[:2]
    mask = np.zeros((height, width), dtype=np.float32)
    bounds = positions[triangles]
    if ear:
        side_x = -bounds[:, :, 0] if opposite else bounds[:, :, 0]
        candidates = ((side_x.min(1) < -.032) &
                      (bounds[:, :, 1].min(1) < .944) & (bounds[:, :, 1].max(1) > .916) &
                      (bounds[:, :, 2].min(1) < .003) & (bounds[:, :, 2].max(1) > -.018))
    else:
        candidates = ((bounds[:, :, 0].min(1) < .037) & (bounds[:, :, 0].max(1) > -.037) &
                      (bounds[:, :, 1].min(1) < .958) & (bounds[:, :, 1].max(1) > .941) &
                      (bounds[:, :, 2].max(1) > .025))
    for tri in triangles[candidates]:
        coords = uv[tri] * [width, height] - .5
        x0, y0 = np.maximum(np.floor(coords.min(0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(coords.max(0)).astype(int), [width - 1, height - 1])
        if x0 > x1 or y0 > y1:
            continue
        a, b, c = coords
        denominator = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(denominator) < 1e-8:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        dx, dy = xx - a[0], yy - a[1]
        wb = (dx * (c[1] - a[1]) - dy * (c[0] - a[0])) / denominator
        wc = ((b[0] - a[0]) * dy - (b[1] - a[1]) * dx) / denominator
        wa = 1 - wb - wc
        inside = (wa >= -1e-6) & (wb >= -1e-6) & (wc >= -1e-6)
        p = wa[..., None] * positions[tri[0]] + wb[..., None] * positions[tri[1]] + wc[..., None] * positions[tri[2]]
        x, y, z = p[..., 0], p[..., 1], p[..., 2]
        if ear:
            weight = 1 - smoothstep(-.037, -.032, -x if opposite else x)
            weight *= smoothstep(.916, .920, y) * (1 - smoothstep(.940, .944, y))
            weight *= smoothstep(-.018, -.014, z) * (1 - smoothstep(-.002, .003, z)) * inside
        else:
            weight = smoothstep(.003, .007, abs(x)) * (1 - smoothstep(.033, .037, abs(x)))
            weight *= smoothstep(.941, .945, y) * (1 - smoothstep(.954, .958, y))
            weight *= smoothstep(.025, .033, z) * inside
        area = np.s_[y0:y1 + 1, x0:x1 + 1]
        mask[area] = np.maximum(mask[area], weight)
    mask = maximum_filter(mask, size=5)
    support = mask > 0
    after = before.copy()
    normal = before[support, :3].astype(np.float32) / 127.5 - 1
    normal[:, :2] *= 1 - mask[support, None]
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-8)
    after[support, :3] = np.clip(np.rint((normal + 1) * 127.5), 0, 255).astype(np.uint8)
    assert np.array_equal(after[~support], before[~support])
    encoded = io.BytesIO()
    Image.fromarray(after).save(encoded, format='PNG')
    original_views = [view_bytes(doc, binary, i) for i in range(len(doc['bufferViews']))]
    packed = bytearray()
    for index, view in enumerate(doc['bufferViews']):
        payload = encoded.getvalue() if index == image['bufferView'] else original_views[index]
        packed.extend(b'\0' * (-len(packed) % 4))
        view['byteOffset'], view['byteLength'] = len(packed), len(payload)
        packed.extend(payload)
    doc['buffers'][0]['byteLength'] = len(packed)
    image['mimeType'] = 'image/png'
    out.mkdir(exist_ok=True)
    model_path = out / f'base-{out_name.replace("_", "-")}.glb'
    blend_path = model_path.with_suffix('.blend')
    write_glb(model_path, doc, packed)
    exported, data = read_glb(model_path)
    for index, original in enumerate(original_views):
        if index != image['bufferView']:
            assert view_bytes(exported, data, index) == original
    subprocess.run(['blender', '-b', '--python-expr',
                    'import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); '
                    f'bpy.ops.import_scene.gltf(filepath={str(model_path)!r}); '
                    'bpy.context.preferences.filepaths.save_version = 0; bpy.ops.file.pack_all(); '
                    f'bpy.ops.wm.save_as_mainfile(filepath={str(blend_path)!r})'], check=True)
    report = {
        'source': str(source.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
        'region': region,
        'mask_x': [.032, .037] if opposite else [-.037, -.032] if ear else [.003, .007, .033, .037],
        'mask_x_uses_absolute_value': not ear,
        'mask_y': [.916, .920, .940, .944] if ear else [.941, .945, .954, .958],
        'mask_z': [-.018, -.014, -.002, .003] if ear else [.025, .033],
        'uv_gutter_pixels': 2,
        'support_pixels': int(support.sum()),
        'normal_changed_pixels': int(np.any(after != before, axis=2).sum()),
        'pixels_outside_support_unchanged': True,
        'all_other_buffer_views_unchanged': True,
        'triangles': sum(doc['accessors'][p['indices']]['count'] // 3 for mesh in doc['meshes'] for p in mesh['primitives']),
    }
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
