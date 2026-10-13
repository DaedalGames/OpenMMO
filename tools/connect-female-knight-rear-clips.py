import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v37', DIRECTORY / 'fitted_v38'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '9c4148fc05cbe19900fc546fa2eaaa94024e2c4696342b4cc88ce2c3ac718756'
doc, original_binary = read_glb(source)
binary = bytearray(original_binary)
report = json.loads((SOURCE / 'fitting.json').read_text())
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
original = {name: accessor(doc, binary, index) for name, index in attrs.items()}
values = {name: array.copy() for name, array in original.items()}
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
points = original['POSITION'].astype(float)
_, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
parents = np.arange(welded.max() + 1)


def root(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


for face in welded[faces]:
    for vertex in face[1:]:
        parents[root(vertex)] = root(face[0])
labels = np.array([root(index) for index in welded])
vertices = np.flatnonzero(np.isin(labels, labels[[1236, 1272, 3780, 3845]]))
boots_path = ROOT / 'assets/items/female_knight_boots/fitted_v4/boots_female_knight.glb'
boots, boot_binary = read_glb(boots_path)
records = []

for side in [-1, 1]:
    selected = vertices[(original['POSITION'][vertices, 0] * side > 0) & (original['POSITION'][vertices, 1] < .425)]
    points = original['POSITION'][selected].astype(float)
    clip = np.ones(len(points), dtype=bool)
    clip_points = points[clip]
    center = clip_points.mean(0)
    _, _, axes = np.linalg.svd(clip_points - center, full_matrices=False)
    normal = -axes[-1] * np.sign(axes[-1, 2])
    boot = boots['meshes'][0 if side < 0 else 1]['primitives'][0]
    boot_points = accessor(boots, boot_binary, boot['attributes']['POSITION'])
    triangles = boot_points[accessor(boots, boot_binary, boot['indices']).reshape(-1, 3)].astype(float)
    a = triangles[:, 0]
    u, v = triangles[:, 1] - a, triangles[:, 2] - a
    determinant = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    valid = abs(determinant) > 1e-12
    inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)

    def surface(point):
        delta = point - a
        bu = (delta[:, 0] * v[:, 1] - delta[:, 1] * v[:, 0]) * inverse
        bv = (u[:, 0] * delta[:, 1] - u[:, 1] * delta[:, 0]) * inverse
        z = a[:, 2] + bu * u[:, 2] + bv * v[:, 2]
        hits = z[valid & (bu >= 0) & (bv >= 0) & (bu + bv <= 1) & (z < 0)]
        return float(hits.min()) if len(hits) else None

    initial_offset = np.array([-.005 if side < 0 else .009, .018, 0])
    shifted = clip_points + initial_offset
    samples = []
    for x in np.linspace(shifted[:, 0].min() + .001, shifted[:, 0].max() - .001, 9):
        for y in np.linspace(.405, .427, 13):
            z = surface(np.array([x, y, 0]))
            if z is not None:
                samples.append([x, y, z])
    samples = np.array(samples)
    coefficients = np.linalg.lstsq(np.column_stack([samples[:, :2], np.ones(len(samples))]), samples[:, 2], rcond=None)[0]
    target_normal = np.array([coefficients[0], coefficients[1], -1])
    target_normal /= np.linalg.norm(target_normal)
    axis = np.cross(normal, target_normal)
    cosine = normal @ target_normal
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    rotation = np.eye(3) + skew + skew @ skew / (1 + cosine)
    pivot = clip_points[clip_points[:, 1] > .414].mean(0)
    translation = initial_offset.copy()

    def deform(p):
        return (p - pivot) @ rotation.T + pivot + translation

    candidate = original['POSITION'].astype(float).copy()
    candidate[selected] = deform(points)
    clip_vertices = selected[clip]
    clip_faces = faces[np.isin(faces, clip_vertices).all(1)]
    barycentric = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1/3, 1/3, 1/3], [.6, .2, .2], [.2, .6, .2], [.2, .2, .6]])
    face_samples = np.einsum('sc,fcd->fsd', barycentric, candidate[clip_faces]).reshape(-1, 3)
    gaps = [z - point[2] for point in face_samples if (z := surface(point)) is not None]
    assert len(gaps) > 100
    translation[2] = min(gaps) - .0007
    assert abs(translation[2]) < .04
    values['POSITION'][selected] = deform(points)
    jacobian = np.stack([(deform(points + axis * 1e-6) - deform(points - axis * 1e-6)) / 2e-6 for axis in np.eye(3)], axis=2)
    assert np.linalg.det(jacobian).min() > .5
    normals = np.linalg.solve(jacobian.transpose(0, 2, 1), original['NORMAL'][selected, :, None])[:, :, 0]
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    tangents = np.einsum('nij,nj->ni', jacobian, original['TANGENT'][selected, :3])
    tangents -= normals * (normals * tangents).sum(1, keepdims=True)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    values['NORMAL'][selected] = normals
    values['TANGENT'][selected, :3] = tangents
    np.testing.assert_allclose(rotation @ normal, target_normal, atol=1e-8)
    np.testing.assert_allclose(values['POSITION'][clip_vertices], (clip_points - pivot) @ rotation.T + pivot + translation, atol=3e-8)
    records.append({'side': side, 'vertices': selected.tolist(), 'clip_vertices': clip_vertices.tolist(), 'pivot': pivot.tolist(), 'rotation': rotation.tolist(), 'translation': translation.tolist(),
                    'rotation_degrees': float(np.degrees(np.arccos(cosine))), 'original_normal': normal.tolist(), 'boot_surface_normal': target_normal.tolist(),
                    'surface_samples': len(samples), 'minimum_sampled_clearance': float(min(gaps) - translation[2]), 'clearance_samples': len(gaps),
                    'maximum_surface_fit_error': float(abs(samples[:, 2] - np.column_stack([samples[:, :2], np.ones(len(samples))]) @ coefficients).max())})


for name in ['POSITION', 'NORMAL', 'TANGENT', 'JOINTS_0', 'WEIGHTS_0']:
    array = values[name]
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', array.strides[0]) == array.strides[0]
    offset = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[offset:offset + array.nbytes] = array.tobytes()
    if 'min' in metadata or 'max' in metadata:
        metadata.update(min=array.min(0).tolist(), max=array.max(0).tolist())
doc['nodes'][0]['extras']['fitting_version'] = 38
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Raise the rear clips onto the upper boot rims, align them to the rear plate surface, and retain the original strap contour and weights over the hip plates.',
              rear_clip_alignment=records,
              preserved=['clip dimensions and detail', 'waist anchors', 'all other geometry', 'unaffected weights', 'topology', 'UVs', 'textures', 'materials', 'rig', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
after, new_binary = read_glb(target)
changed = np.array([vertex for record in records for vertex in record['vertices']])
for index, primitive in enumerate(doc['meshes'][0]['primitives']):
    np.testing.assert_array_equal(accessor(doc, original_binary, primitive['indices']), accessor(after, new_binary, primitive['indices']))
    for name, attribute in primitive['attributes'].items():
        old, new = accessor(doc, original_binary, attribute), accessor(after, new_binary, attribute)
        keep = np.ones(len(old), dtype=bool)
        if index == 0 and name in ['POSITION', 'NORMAL', 'TANGENT', 'JOINTS_0', 'WEIGHTS_0']:
            keep[changed] = False
        np.testing.assert_array_equal(old[keep], new[keep])
validation = {'sha256': report['sha256'], 'unchanged_other_attributes': True, 'unchanged_clip_dimensions': True,
              'clips': [{key: value for key, value in record.items() if key not in ['vertices', 'clip_vertices']} for record in records]}
(OUTPUT / 'alignment-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation))
