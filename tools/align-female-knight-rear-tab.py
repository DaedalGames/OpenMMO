import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
parser = argparse.ArgumentParser()
parser.add_argument('--version', choices=['v30', 'v31'], default='v30')
version = parser.parse_args().version
opposite = version == 'v31'
SOURCE = DIRECTORY / ('fitted_v30' if opposite else 'fitted_v29')
OUTPUT = DIRECTORY / f'fitted_{version}'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == ('27f55c844dfc8cbe1c62084ab101802a18fee49c3412d3b9082d05296fcc134e' if opposite else '4504da62f5e4cf6e8ec8118b5175587a704a5d744ed34af6cc511184be164b13')
report = json.loads((SOURCE / 'fitting.json').read_text())
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
attrs = doc['meshes'][0]['primitives'][0]['attributes']
original = {name: accessor(doc, binary, attrs[name]) for name in ['POSITION', 'NORMAL', 'TANGENT']}
values = {name: array.copy() for name, array in original.items()}


def width_angle(points):
    points = np.unique(points, axis=0)
    coefficients = np.linalg.lstsq(np.c_[points[:, :2], np.ones(len(points))], points[:, 2], rcond=None)[0]
    return float(np.degrees(np.arctan(coefficients[0])))


regions = [region for region in report['rear_tab_regions'] if (region['center_x'] < 0) == opposite]
shared_points = []
for region in regions:
    points = original['POSITION'][region['vertices']].astype(float)
    full = points[:, 1] <= .616 if region['folded_tab'] else points[:, 1] >= .599
    shared_points.append(points[full])
shared_pivot = np.unique(np.concatenate(shared_points), axis=0).mean(0)
records = []
for region in regions:
    vertices = np.array(region['vertices'])
    points = original['POSITION'][vertices].astype(float)
    folded = region['folded_tab']
    full = points[:, 1] <= .616 if folded else points[:, 1] >= .599
    pivot = shared_pivot if opposite else np.unique(points[full], axis=0).mean(0)
    degrees = 12 if opposite else -22.5 if folded else 21

    def deform(points):
        t = np.clip((.623 - points[:, 1]) / .007 if folded else (points[:, 1] - .584) / .014, 0, 1)
        angle = np.radians(degrees) * t * t * (3 - 2 * t)
        delta = points - pivot
        result = points.copy()
        result[:, 0] = pivot[0] + np.cos(angle) * delta[:, 0] + np.sin(angle) * delta[:, 2]
        result[:, 2] = pivot[2] - np.sin(angle) * delta[:, 0] + np.cos(angle) * delta[:, 2]
        return result

    result = deform(points)
    jacobian = np.stack([(deform(points + axis * 1e-6) - deform(points - axis * 1e-6)) / 2e-6 for axis in np.eye(3)], axis=2)
    assert np.linalg.det(jacobian).min() > .999
    normals = np.linalg.solve(jacobian.transpose(0, 2, 1), original['NORMAL'][vertices, :, None]).squeeze(-1)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    tangents = np.einsum('nij,nj->ni', jacobian, original['TANGENT'][vertices, :3])
    tangents -= normals * np.sum(normals * tangents, axis=1)[:, None]
    tangents /= np.linalg.norm(tangents, axis=1)[:, None]
    values['POSITION'][vertices] = result
    values['NORMAL'][vertices] = normals
    values['TANGENT'][vertices, :3] = tangents
    before_distances = np.linalg.norm(points[full, None] - points[None, full], axis=-1)
    after_distances = np.linalg.norm(result[full, None] - result[None, full], axis=-1)
    np.testing.assert_allclose(after_distances, before_distances, atol=1e-8)
    inner, outer = np.argmin(abs(points[full, 0])), np.argmax(abs(points[full, 0]))
    depth = result[full, 2] - points[full, 2]
    assert (depth[outer] > 0 > depth[inner]) if folded or opposite else (depth[inner] > 0 > depth[outer])
    records.append({'part': 'folded leather tab' if folded else 'buckle and connecting strap',
                    'vertices': vertices.tolist(), 'pivot': pivot.tolist(), 'yaw_degrees': degrees,
                    'width_angle_before': width_angle(points[full]), 'width_angle_after': width_angle(result[full]),
                    'inner_depth_delta': float(depth[inner]), 'outer_depth_delta': float(depth[outer]),
                    'rigid_distance_error': float(abs(after_distances - before_distances).max())})
assert len(records) == 2
if not opposite:
    assert abs(records[0]['width_angle_after'] - records[1]['width_angle_after']) < 1, records
changed = np.concatenate([record['vertices'] for record in records])
for name, array in values.items():
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.shape[1] * 4) == array.shape[1] * 4
    start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[start:start + array.nbytes] = array.tobytes()
    if name == 'POSITION':
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = int(version[1:])
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method=('Rotate the wearer-right rear tab and upper buckle together by 12 degrees counterclockwise from above, around a shared pivot, fading into the waist belt and lower strap.' if opposite else 'Align the wearer-left rear folded leather tab and its buckle with opposite 22.5-degree and 21-degree yaw rotations, fading into the waist belt and lower strap.'),
              rear_tab_vertices=changed.tolist(), rear_tab_alignment=records,
              preserved=['opposite rear tab and buckle', 'lowered rear guard', 'front leather', 'waist belt', 'lower straps and buckles', 'plates', 'UVs', 'textures', 'weights', 'topology', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
before, old_binary = read_glb(source)
after, new_binary = read_glb(target)
for index, old in enumerate(before['meshes'][0]['primitives']):
    new = after['meshes'][0]['primitives'][index]
    np.testing.assert_array_equal(accessor(before, old_binary, old['indices']), accessor(after, new_binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a, b = accessor(before, old_binary, attribute), accessor(after, new_binary, new['attributes'][name])
        if index == 0 and name in values:
            keep = np.ones(len(a), dtype=bool)
            keep[changed] = False
            np.testing.assert_array_equal(a[keep], b[keep])
        else:
            np.testing.assert_array_equal(a, b)
np.testing.assert_array_equal(original['POSITION'][:, 1], values['POSITION'][:, 1])
for name in ['NORMAL', 'TANGENT']:
    np.testing.assert_allclose(np.linalg.norm(values[name][changed, :3], axis=1), 1, atol=1e-6)
validation = {'sha256': report['sha256'], 'changed_vertices': len(changed), 'parts': records,
              'preserved': report['preserved'], 'normalized_shading_frames': True}
(OUTPUT / 'alignment-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps({'sha256': report['sha256'], 'parts': [{key: value for key, value in record.items() if key != 'vertices'} for record in records]}))
