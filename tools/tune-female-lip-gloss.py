"""Soften lip normal-map artifacts and retain a smooth dielectric gloss."""
import hashlib
import io
import json
import struct
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/modular_human_female_01/eye_normals_v1/base-eye-normals-v1.glb'
OUT = ROOT / 'assets/modular_human_female_01/lips_v1'


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    raw = SOURCE.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]
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
    material = doc['materials'][primitive['material']]
    maps = {
        'normal': material['normalTexture']['index'],
        'orm': material['pbrMetallicRoughness']['metallicRoughnessTexture']['index'],
    }
    images = {}
    for name, index in maps.items():
        image = doc['images'][doc['textures'][index]['source']]
        view = doc['bufferViews'][image['bufferView']]
        payload = binary[view['byteOffset']:view['byteOffset'] + view['byteLength']]
        images[name] = (image, np.array(Image.open(io.BytesIO(payload))))
    height, width = images['normal'][1].shape[:2]
    assert images['orm'][1].shape[:2] == (height, width)
    mask = np.zeros((height, width), dtype=np.float32)
    lower_mask = np.zeros_like(mask)
    bounds = positions[triangles]
    candidates = ((bounds[:, :, 0].min(1) < .016) & (bounds[:, :, 0].max(1) > -.015) &
                  (bounds[:, :, 1].min(1) < .906) & (bounds[:, :, 1].max(1) > .892) &
                  (bounds[:, :, 2].max(1) > .034))
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
        radius = np.sqrt(((p[..., 0] - .0007) / .0148) ** 2 + ((p[..., 1] - .899) / .0066) ** 2)
        weight = (1 - smoothstep(.78, 1, radius)) * smoothstep(.032, .038, p[..., 2]) * inside
        area = np.s_[y0:y1 + 1, x0:x1 + 1]
        mask[area] = np.maximum(mask[area], weight)
        lower_mask[area] = np.maximum(lower_mask[area], weight * (1 - smoothstep(.899, .901, p[..., 1])))
    mask = maximum_filter(mask, size=5)
    lower_mask = maximum_filter(lower_mask, size=5)
    support = mask > 0
    replacements = {}
    changes = {}
    for name, (image, before) in images.items():
        after = before.copy()
        values = before[support, :3].astype(np.float32)
        weight = mask[support, None]
        if name == 'normal':
            normal = values / 127.5 - 1
            normal[:, :2] *= 1 - .94 * weight
            normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-8)
            values = (normal + 1) * 127.5
        else:
            roughness = .34 * mask[support] - .04 * lower_mask[support]
            values[:, 1] = values[:, 1] * (1 - mask[support]) + 255 * roughness
            values[:, 2] *= 1 - mask[support]
        after[support, :3] = np.clip(np.rint(values), 0, 255).astype(np.uint8)
        assert np.array_equal(after[~support], before[~support])
        if name == 'orm':
            assert np.array_equal(after[:, :, 0], before[:, :, 0])
        changes[name] = int(np.any(after != before, axis=2).sum())
        encoded = io.BytesIO()
        Image.fromarray(after).save(encoded, format='PNG')
        replacements[image['bufferView']] = encoded.getvalue()
        image['mimeType'] = 'image/png'
    packed = bytearray()
    for index, view in enumerate(doc['bufferViews']):
        original = binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
        payload = replacements.get(index, original)
        packed.extend(b'\0' * (-len(packed) % 4))
        view['byteOffset'], view['byteLength'] = len(packed), len(payload)
        packed.extend(payload)
        if index not in replacements:
            assert packed[view['byteOffset']:view['byteOffset'] + view['byteLength']] == original
    doc['buffers'][0]['byteLength'] = len(packed)
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    packed.extend(b'\0' * (-len(packed) % 4))
    glb = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(packed))
    glb += struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
    glb += struct.pack('<II', len(packed), 0x004e4942) + packed
    OUT.mkdir(exist_ok=True)
    model_path = OUT / 'base-lips-v1.glb'
    blend_path = OUT / 'base-lips-v1.blend'
    model_path.write_bytes(glb)
    subprocess.run(['blender', '-b', '--python-expr',
                    'import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); '
                    f'bpy.ops.import_scene.gltf(filepath={str(model_path)!r}); '
                    'bpy.context.preferences.filepaths.save_version = 0; '
                    'bpy.ops.file.pack_all(); '
                    f'bpy.ops.wm.save_as_mainfile(filepath={str(blend_path)!r})'], check=True)
    report = {
        'source': str(SOURCE.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'output_sha256': hashlib.sha256(glb).hexdigest(),
        'lip_mask_center_xy': [.0007, .899],
        'lip_mask_radius_xy': [.0148, .0066],
        'normal_xy_strength': .06,
        'upper_roughness': .34,
        'lower_roughness': .30,
        'metalness': 0,
        'uv_gutter_pixels': 2,
        'support_pixels': int(support.sum()),
        'changed_pixels': changes,
        'pixels_outside_support_unchanged': True,
        'other_buffer_views_unchanged': True,
        'geometry_uv_materials_base_color_occlusion_unchanged': True,
        'triangles': sum(doc['accessors'][p['indices']]['count'] // 3 for mesh in doc['meshes'] for p in mesh['primitives']),
    }
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
