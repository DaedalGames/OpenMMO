import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from lib.glb import read_glb, view_bytes, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.female_boot_pose import heel_pose
from outfits.skinning import deform

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_rogue_boots/tripo_v1'
SOURCE = DIRECTORY / 'fitted_v1'
RED_INNER_HEEL = '--red-inner-heel' in sys.argv
REVISION = 'v3' if RED_INNER_HEEL else 'v2'
OUTPUT = DIRECTORY / f'fitted_{REVISION}'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT.mkdir(exist_ok=True)
doc, source_raw = read_glb(SOURCE / 'boots_female_rogue.glb')
binary = bytearray(source_raw)
base, body_raw = read_glb(BODY)
matrices, _ = heel_pose(base, body_raw)
material = doc['materials'][0]['pbrMetallicRoughness']
image = doc['images'][doc['textures'][material['baseColorTexture']['index']]['source']]
pixels = np.asarray(Image.open(io.BytesIO(view_bytes(doc, source_raw, image['bufferView']))).convert('RGB')).astype(float)
height, width = pixels.shape[:2]
red_pixels = (pixels[:, :, 0] > 55) & (pixels[:, :, 0] > 1.6*pixels[:, :, 1]) & (pixels[:, :, 0] > 1.6*pixels[:, :, 2])
red_distance = distance_transform_edt(~red_pixels)
inside_red_distance = distance_transform_edt(red_pixels)


def colors(uv):
    x = np.clip((uv[..., 0]*width).astype(int), 0, width-1)
    y = np.clip((uv[..., 1]*height).astype(int), 0, height-1)
    return pixels[y, x]


barycentric = np.array([(a/8, b/8, (8-a-b)/8) for a in range(9) for b in range(9-a)])
report = []
for mesh in doc['meshes']:
    primitive = mesh['primitives'][0]
    attrs = primitive['attributes']
    points = accessor(doc, source_raw, attrs['POSITION'])
    uv = accessor(doc, source_raw, attrs['TEXCOORD_0'])
    faces = accessor(doc, source_raw, primitive['indices']).reshape(-1, 3)
    joints = accessor(doc, source_raw, attrs['JOINTS_0']).astype(int)
    weights = accessor(doc, source_raw, attrs['WEIGHTS_0'])
    posed = deform(points, joints, weights, matrices)
    normals = np.cross(posed[faces[:, 1]]-posed[faces[:, 0]], posed[faces[:, 2]]-posed[faces[:, 0]])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    samples = np.einsum('fkc,bk->fbc', uv[faces], barycentric)
    rgb = colors(samples)
    red = (rgb[..., 0] > 55) & (rgb[..., 0] > 1.6*rgb[..., 1]) & (rgb[..., 0] > 1.6*rgb[..., 2])
    side = red.any(1) & (normals[:, 1] > -.5) & (posed[faces].mean(1)[:, 1] < .1)
    underside = red.any(1) & (normals[:, 1] <= -.5)
    heel_inner = np.zeros(len(faces), dtype=bool)
    if RED_INNER_HEEL:
        center = posed[faces].mean(1)
        heel_inner = (center[:, 1] < .04) & (center[:, 2] < -.05) & (normals[:, 2] > .7) & (normals[:, 1] > -.5)
        assert heel_inner.any()
        side &= ~heel_inner
    assert side.any() and underside.any()
    centers = uv[faces].mean(1)
    center_rgb = colors(centers)
    px = np.clip((centers[:, 0]*width).astype(int), 0, width-1)
    py = np.clip((centers[:, 1]*height).astype(int), 0, height-1)
    foot = (posed[faces].mean(1)[:, 1] < .14) & (posed[faces].mean(1)[:, 1] > -.04)
    leather = foot & (np.ptp(center_rgb, axis=1) < 12) & (center_rgb.mean(1) > 12) & (center_rgb.mean(1) < 80) & (red_distance[py, px] > 24)
    candidates = np.flatnonzero(leather)
    assert len(candidates) > 0
    median = np.median(center_rgb[candidates], axis=0)
    donor = candidates[np.linalg.norm(center_rgb[candidates]-median, axis=1).argmin()]
    donor_uv = centers[donor]
    groups = [(side, donor_uv)]
    if RED_INNER_HEEL:
        candidates = np.flatnonzero(underside & (inside_red_distance[py, px] > 24))
        assert len(candidates) > 0
        median = np.median(center_rgb[candidates], axis=0)
        red_donor = candidates[np.linalg.norm(center_rgb[candidates]-median, axis=1).argmin()]
        red_uv = centers[red_donor]
        groups.append((heel_inner, red_uv))
    duplicated = np.concatenate([np.unique(faces[selected]) for selected, _ in groups])
    origin = np.concatenate([np.arange(len(points)), duplicated])
    output_faces = faces.copy()
    color_uv = uv[origin].copy()
    offset = len(points)
    for selected, color in groups:
        vertices = np.unique(faces[selected])
        remap = np.arange(len(points))
        remap[vertices] = np.arange(offset, offset+len(vertices))
        output_faces[selected] = remap[faces[selected]]
        color_uv[offset:offset+len(vertices)] = color
        offset += len(vertices)
    for name, index in list(attrs.items()):
        item = doc['accessors'][index]
        attrs[name] = add_accessor(doc, binary, accessor(doc, source_raw, index)[origin], item['type'], item['componentType'])
    for target in primitive.get('targets', []):
        for name, index in list(target.items()):
            target[name] = add_accessor(doc, binary, accessor(doc, source_raw, index)[origin], 'VEC3')
    attrs['TEXCOORD_1'] = add_accessor(doc, binary, color_uv, 'VEC2')
    primitive['indices'] = add_accessor(doc, binary, output_faces.reshape(-1, 1), 'SCALAR', 5125)
    np.testing.assert_array_equal(origin[output_faces], faces)
    np.testing.assert_array_equal(color_uv[output_faces[underside]], uv[faces[underside]])
    unchanged = ~(side | heel_inner)
    np.testing.assert_array_equal(color_uv[output_faces[unchanged]], uv[faces[unchanged]])
    report.append({'mesh': mesh['name'], 'triangles': len(faces), 'side_triangles': np.flatnonzero(side).tolist(),
                   'preserved_red_underside_triangles': int(underside.sum()),
                   'source_vertices': len(points), 'duplicated_source_vertices': duplicated.tolist(),
                   'leather_color_uv': donor_uv.tolist(), 'leather_color_srgb': center_rgb[donor].tolist()})
    if RED_INNER_HEEL:
        report[-1].update(red_inner_heel_triangles=np.flatnonzero(heel_inner).tolist(),
                          red_heel_color_uv=red_uv.tolist(), red_heel_color_srgb=center_rgb[red_donor].tolist())
material['baseColorTexture']['texCoord'] = 1
material['metallicRoughnessTexture']['texCoord'] = 1
doc['buffers'][0]['byteLength'] = len(binary)
output = OUTPUT / 'boots_female_rogue.glb'
write_glb(output, doc, binary)
for name in ['body-occlusion.json', 'heel-pose.json']:
    (OUTPUT / name).write_bytes((SOURCE / name).read_bytes())
summary = {'revision': REVISION, 'date': '2026-10-26', 'source': str(SOURCE.relative_to(ROOT)),
           'source_sha256': hashlib.sha256((SOURCE / 'boots_female_rogue.glb').read_bytes()).hexdigest(),
           'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'parts': report,
           'method': 'Assign side-facing red sole triangles to existing black leather through a second color and ORM UV channel; preserve underside UVs, original detail normals and all PBR images.',
           'surface_geometry_skinning_morphs_and_original_uv0_preserved': True,
           'texture_bytes_and_red_underside_preserved': True, 'triangles': sum(p['triangles'] for p in report),
           'no_new_api_requests': True}
if RED_INNER_HEEL:
    summary['method'] += ' Keep the heel column face toward the toe red; preserve black lateral and rear faces.'
(OUTPUT / 'fitting.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({k: v for k, v in summary.items() if k != 'parts'}, indent=2))
