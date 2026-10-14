"""Remove the underwear baked into the female base skin texture."""
import hashlib
import io
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, maximum_filter
from scipy.sparse import coo_matrix, diags
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import cg
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
SOURCE = ROOT / 'assets/modular_human_female_01/ear_normals_v2/base-ear-normals-v2.glb'
OUT = ROOT / 'assets/modular_human_female_01/underwear_skin_v1'
REACH = .025
FOOTPRINT = .009
RIDGE_REACH = .04
PADDING = 8


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def image(doc, binary, index):
    view = doc['bufferViews'][doc['images'][index]['bufferView']]
    offset = view.get('byteOffset', 0)
    return Image.open(io.BytesIO(bytes(binary[offset:offset + view['byteLength']])))


doc, binary = read_glb(SOURCE)
primitive = doc['meshes'][0]['primitives'][0]
material = doc['materials'][primitive['material']]
indices = {'color': material['pbrMetallicRoughness']['baseColorTexture']['index'],
           'normal': material['normalTexture']['index'],
           'orm': material['pbrMetallicRoughness']['metallicRoughnessTexture']['index']}
sources = {name: doc['textures'][index]['source'] for name, index in indices.items()}
maps = {name: np.array(image(doc, binary, source).convert('RGB')).astype(np.float32) / 255 for name, source in sources.items()}
height, width = maps['color'].shape[:2]
p = accessor(doc, binary, primitive['attributes']['POSITION'])
uv = accessor(doc, binary, primitive['attributes']['TEXCOORD_0'])
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)

_, welded = np.unique(np.round(p, 6), axis=0, return_inverse=True)
welded = welded.ravel()
edges = welded[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
_, labels = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(welded.max() + 1,) * 2), directed=False)
vertex_labels = labels[welded]
skin_label = np.bincount(vertex_labels).argmax()
underwear = np.flatnonzero((vertex_labels != skin_label) & (p[:, 1] > .64) & (p[:, 1] < .86))
underwear_tree = cKDTree(p[underwear])
near, _ = underwear_tree.query(p)
skin_faces = faces[(vertex_labels[faces[:, 0]] == skin_label) & (near[faces] < RIDGE_REACH).any(1)]

def rasterize(triangle):
    coords = uv[triangle] * [width, height] - .5
    x0, y0 = np.maximum(np.floor(coords.min(0)).astype(int), 0)
    x1, y1 = np.minimum(np.ceil(coords.max(0)).astype(int), [width - 1, height - 1])
    a, b, c = coords
    denominator = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if x0 > x1 or y0 > y1 or abs(denominator) < 1e-9:
        return np.empty(0, dtype=int), np.empty((0, 3))
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    gx, gy = gx.ravel(), gy.ravel()
    w1 = ((gx - a[0]) * (c[1] - a[1]) - (gy - a[1]) * (c[0] - a[0])) / denominator
    w2 = ((b[0] - a[0]) * (gy - a[1]) - (b[1] - a[1]) * (gx - a[0])) / denominator
    w0 = 1 - w1 - w2
    inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
    return gy[inside] * width + gx[inside], np.c_[w0[inside], w1[inside], w2[inside]]


# Rasterize nearby skin into texels with their surface positions.
texels, points = [], []
for triangle in skin_faces:
    found, weights = rasterize(triangle)
    texels.append(found)
    points.append(weights @ p[triangle])
texels = np.concatenate(texels)
points = np.concatenate(points)
texels, unique = np.unique(texels, return_index=True)
points = points[unique]
distance, _ = underwear_tree.query(points)

color = maps['color'].reshape(-1, 3)[texels]
value = color.max(1)
saturation = (value - color.min(1)) / np.maximum(value, 1e-6)
whiteness = smoothstep(.24, .10, saturation) * smoothstep(.50, .68, value)
# The footprint is replaced outright so painted seams and shadow lines go too; beyond it only white spill, dark marks and seam ridges.
tree = cKDTree(points)
_, neighbors = tree.query(points, k=25)
darkness = smoothstep(.05, .10, np.median(value[neighbors], axis=1) - value)
ridge = smoothstep(.10, .25, np.linalg.norm(maps['normal'].reshape(-1, 3)[texels] - [.5, .5, 1], axis=1))
weight = np.maximum.reduce([smoothstep(FOOTPRINT + .003, FOOTPRINT, distance),
                            np.maximum(whiteness, darkness) * smoothstep(REACH, .012, distance),
                            ridge * smoothstep(RIDGE_REACH, RIDGE_REACH - .01, distance)])
grid = np.zeros(height * width, dtype=np.float32)
grid[texels] = weight
grid = maximum_filter(grid.reshape(height, width), size=5).ravel()
alpha = np.clip(grid[texels] * 1.5, 0, 1)
dirty = alpha > .02

# Harmonic fill over a 3D neighbor graph so UV islands stay continuous across seams.
_, neighbors = tree.query(points, k=9)
rows = np.repeat(np.arange(len(points)), 8)
cols = neighbors[:, 1:].ravel()
graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(points),) * 2).tocsr()
graph = ((graph + graph.T) > 0).astype(np.float64)
laplacian = (diags(np.asarray(graph.sum(1)).ravel()) - graph).tocsr()
unknown, known = np.flatnonzero(dirty), np.flatnonzero(~dirty)
system = laplacian[unknown][:, unknown]
coupling = laplacian[unknown][:, known]
filled = {}
for name in ['color', 'orm']:
    values = maps[name].reshape(-1, 3)[texels].astype(np.float64)
    result = values.copy()
    for channel in range(3):
        solution, info = cg(system, -coupling @ values[known, channel], rtol=1e-6, maxiter=4000)
        assert info == 0, f'{name} fill did not converge'
        result[unknown, channel] = solution
    filled[name] = result

flat = np.array([.5, .5, 1.0])
for name, values in [('color', filled['color']), ('orm', filled['orm']),
                     ('normal', np.tile(flat, (len(texels), 1)))]:
    data = maps[name].reshape(-1, 3)
    original = data[texels].copy()
    data[texels] = original * (1 - alpha[:, None]) + values * alpha[:, None]

# Copy fixed texels into neighboring atlas padding so filtering does not pull old marks back in.
covered = np.zeros(height * width, dtype=bool)
for triangle in faces:
    covered[rasterize(triangle)[0]] = True
changed = np.zeros(height * width, dtype=bool)
changed[texels[dirty]] = True
# Only padding whose nearest covered texel was repainted, so other islands (the underwear) keep their own edges.
gap, (iy, ix) = distance_transform_edt(~covered.reshape(height, width), return_indices=True)
source_index = (iy * width + ix).ravel()
padding = ~covered & (gap.ravel() <= PADDING) & changed[source_index]
for name in maps:
    data = maps[name].reshape(-1, 3)
    data[padding] = data[source_index[padding]]

OUT.mkdir(parents=True, exist_ok=True)
encoded = {}
for name, data in maps.items():
    buffer = io.BytesIO()
    Image.fromarray(np.clip(np.rint(data * 255), 0, 255).astype(np.uint8)).save(buffer, format='PNG', optimize=True)
    encoded[name] = buffer.getvalue()


def replace_images(path):
    target, data = read_glb(path)
    replacements = {target['images'][index]['bufferView']: encoded[name] for name, index in sources.items()}
    packed = bytearray()
    for number, view in enumerate(target['bufferViews']):
        offset = view.get('byteOffset', 0)
        chunk = replacements.get(number, bytes(data[offset:offset + view['byteLength']]))
        view['byteOffset'] = len(packed)
        view['byteLength'] = len(chunk)
        packed += chunk
        packed += b'\0' * (-len(packed) % 4)
    target['buffers'][0]['byteLength'] = len(packed)
    write_glb(path, target, packed)
    return hashlib.sha256(path.read_bytes()).hexdigest()


if '--dry-run' in sys.argv:
    raise SystemExit(f'dry run: {int(dirty.sum())} texels filled, {int(padding.sum())} padding')
if '--output' in sys.argv:
    preview = Path(sys.argv[sys.argv.index('--output') + 1])
    preview.write_bytes(BODY.read_bytes())
    raise SystemExit(f'preview written: {replace_images(preview)}')
before = hashlib.sha256(BODY.read_bytes()).hexdigest()
after = replace_images(BODY)
if before == after and (OUT / 'report.json').exists():
    before = json.loads((OUT / 'report.json').read_text())['target_sha256_before']
report = {'date': date.today().isoformat(), 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'target': str(BODY.relative_to(ROOT)), 'target_sha256_before': before, 'target_sha256_after': after,
          'maps': {name: hashlib.sha256(encoded[name]).hexdigest() for name in encoded},
          'rasterized_texels': int(len(texels)), 'filled_texels': int(dirty.sum()), 'padding_texels': int(padding.sum()),
          'method': f'Skin texels within {FOOTPRINT} m of the upper underwear and bow, plus near-white or locally dark texels within {REACH} m and normal-map ridges within {RIDGE_REACH} m, are replaced by a harmonic fill over a 3D nearest-neighbor texel graph (color and ORM); the normal map is flattened there. Geometry, UVs, rig and animations are unchanged.',
          'note': 'Images are rebuilt from the pre-rig source texture, so rerunning is idempotent. Rerun after tools/rig-female-base.py.'}
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['rasterized_texels', 'filled_texels', 'padding_texels', 'target_sha256_after']}))
