import hashlib
import json
import shutil
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from lib.glb import read_glb, view_bytes, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_knight_bottom/tripo_v1'
SOURCE, OUTPUT = DIRECTORY / 'fitted_v25', DIRECTORY / 'fitted_v26'
source = SOURCE / 'bottom_female_knight.glb'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '459fbb4caf6c090bfe3a8fd2fcd7b15c970cd21cb101024899dc0fa16216c952'
doc, binary = read_glb(source)
binary = bytearray(binary)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION'])
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
uv = accessor(doc, binary, attrs['TEXCOORD_0'])
original_uv = uv.copy()
parents = np.arange(len(points))


def root(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


for face in faces:
    for corner in face[1:]:
        parents[root(corner)] = root(face[0])
labels = np.array([root(index) for index in range(len(points))])
side_islands = [2448, 2460, 4619, 4703]
face_islands = [2498, 2519, 4605, 4733]
changed = np.flatnonzero(np.isin(labels, side_islands + face_islands))
assert len(changed) == 105
for label in side_islands + face_islands:
    vertices = np.flatnonzero(labels == label)
    local = original_uv[vertices]
    unit = (local - local.min(0)) / np.ptp(local, axis=0)
    if label in side_islands:
        uv[vertices] = [.04, .696] + unit * [.25, .002]
    else:
        if points[vertices, 0].mean() < 0:
            unit[:, 0] = 1 - unit[:, 0]
        uv[vertices, 0] = .008 + unit[:, 0] * .339
        uv[vertices, 1] = np.interp(.9208 + unit[:, 1] * .0382,
                                   [.9208, .931, .936, .943, .959],
                                   [.933, .934, .936, .943, .955])

normals = accessor(doc, binary, attrs['NORMAL'])
tangents = accessor(doc, binary, attrs['TANGENT'])
affected_faces = faces[np.isin(faces[:, 0], changed)]
tangent_sum = np.zeros_like(points, dtype=float)
bitangent_sum = np.zeros_like(points, dtype=float)
for face in affected_faces:
    a, b = points[face[1:]].astype(float) - points[face[0]]
    u, v = uv[face[1:]].astype(float) - uv[face[0]]
    determinant = u[0] * v[1] - u[1] * v[0]
    assert abs(determinant) > 1e-12
    weight = np.linalg.norm(np.cross(a, b))
    tangent_sum[face] += weight * (a * v[1] - b * u[1]) / determinant
    bitangent_sum[face] += weight * (b * u[0] - a * v[0]) / determinant
for vertex in changed:
    normal = normals[vertex].astype(float)
    normal /= np.linalg.norm(normal)
    tangent = tangent_sum[vertex] - normal * np.dot(normal, tangent_sum[vertex])
    tangent /= np.linalg.norm(tangent)
    tangents[vertex, :3] = tangent
    tangents[vertex, 3] = 1 if np.dot(np.cross(normal, tangent), bitangent_sum[vertex]) >= 0 else -1
assert np.isfinite(tangents).all()

for name, values in [('TEXCOORD_0', uv), ('TANGENT', tangents)]:
    metadata = doc['accessors'][attrs[name]]
    view = doc['bufferViews'][metadata['bufferView']]
    assert view.get('byteStride', values.shape[1] * 4) == values.shape[1] * 4
    start = view.get('byteOffset', 0) + metadata.get('byteOffset', 0)
    binary[start:start + values.nbytes] = values.tobytes()
doc['nodes'][0]['extras']['fitting_version'] = 26
OUTPUT.mkdir(exist_ok=True)
target = OUTPUT / 'bottom_female_knight.glb'
write_glb(target, doc, binary)
shutil.copy2(SOURCE / 'body-occlusion.json', OUTPUT / 'body-occlusion.json')
report = json.loads((SOURCE / 'fitting.json').read_text())
report.update(date='2026-10-13', source=str(source.relative_to(ROOT)), source_sha256=source_hash,
              output=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              method='Remap eight rear strap UV islands to existing leather-only atlas regions, retaining the brass rivet on broad faces. Recompute tangent frames for the remapped normal texture.',
              strap_uv_vertices=changed.tolist(),
              preserved=['geometry', 'thickness', 'normals', 'indices', 'weights', 'textures', 'materials', 'rig', 'other UVs and tangents', 'occlusion mask'])
(OUTPUT / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')

before, old_binary = read_glb(source)
after, new_binary = read_glb(target)
for index, old in enumerate(before['meshes'][0]['primitives']):
    new = after['meshes'][0]['primitives'][index]
    assert np.array_equal(accessor(before, old_binary, old['indices']), accessor(after, new_binary, new['indices']))
    for name, attribute in old['attributes'].items():
        a, b = accessor(before, old_binary, attribute), accessor(after, new_binary, new['attributes'][name])
        if index == 0 and name in ['TEXCOORD_0', 'TANGENT']:
            other = np.ones(len(a), dtype=bool)
            other[changed] = False
            assert np.array_equal(a[other], b[other])
        else:
            assert np.array_equal(a, b), name
for i in range(len(doc['images'])):
    assert view_bytes(before, old_binary, before['images'][i]['bufferView']) == view_bytes(after, new_binary, after['images'][i]['bufferView'])
for key in ['materials', 'skins', 'textures']:
    assert before[key] == after[key]
color = np.asarray(Image.open(BytesIO(view_bytes(doc, binary, doc['images'][0]['bufferView'])))).astype(float)
metal = np.asarray(Image.open(BytesIO(view_bytes(doc, binary, doc['images'][1]['bufferView']))))[:, :, 2]
barycentric = np.array([[1-u-v, u, v] for u in np.linspace(.02, .96, 24) for v in np.linspace(.02, .96, 24) if u + v < .98])
counts = []
for coords in [original_uv, uv]:
    samples = np.einsum('sc,fcd->fsd', barycentric, coords[affected_faces]).reshape(-1, 2)
    pixels = np.rint(samples * [color.shape[1]-1, color.shape[0]-1]).astype(int)
    rgb = color[pixels[:, 1], pixels[:, 0]]
    metallic = metal[pixels[:, 1], pixels[:, 0]]
    silver = (rgb.max(1) - rgb.min(1) < rgb.max(1) * .25) & (metallic > 110)
    counts.append(int(silver.sum()))
assert counts[0] > 100 and counts[1] == 0, counts
validation = {'date': '2026-10-13', 'sha256': report['sha256'], 'changed_vertices': len(changed),
              'changed_triangles': len(affected_faces), 'samples': len(samples), 'silver_samples_before_after': counts,
              'preserved': report['preserved'], 'scope': 'Interior UV samples classify low-saturation metallic atlas texels; gold rivets remain permitted. Geometry and embedded textures are byte-identical.'}
(OUTPUT / 'uv-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation))
