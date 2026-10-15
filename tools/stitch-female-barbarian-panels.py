import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
REPAIR = DIRECTORY / 'panel_seam_repair_v1'
SOURCE = REPAIR / 'before.glb'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
doc, original = read_glb(SOURCE)
nodes = {node['mesh']: node for node in doc['nodes'] if 'mesh' in node}
arrays = []
groups = {}
for m, mesh in enumerate(doc['meshes']):
    primitive, = mesh['primitives']
    attributes = primitive['attributes']
    values = {name: accessor(doc, original, index) for name, index in attributes.items()}
    arrays.append(values)
    for i, point in enumerate(values['POSITION']):
        groups.setdefault(tuple(point.round(6)), []).append((m, i))
seams = [rows for rows in groups.values()
         if len({m for m, _ in rows}) > 1 and any(nodes[m]['extras']['panel'] == 'belt' for m, _ in rows)]
attachments = {m: set() for m in range(len(arrays))}
for rows in seams:
    belt, index = next((m, i) for m, i in rows if nodes[m]['extras']['panel'] == 'belt')
    for m, i in rows:
        for name in ['JOINTS_0', 'WEIGHTS_0']:
            assert np.array_equal(arrays[m][name][i], arrays[belt][name][index]), 'Seam skin weights differ.'
        if 'pelt_physics' in nodes[m]['extras']:
            attachments[m].add(i)
for m, ids in attachments.items():
    if ids:
        nodes[m]['extras']['pelt_physics']['attachment_vertices'] = sorted(ids)
write_glb(OUTPUT, doc, original)
report = {
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output': str(OUTPUT.relative_to(ROOT)),
    'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Stitch the original coincident belt-to-fur boundaries with explicit pelt attachments; retain their existing shared skin weights and bake posed anchors into the simulated frame.',
    'seam_groups': len(seams),
    'attachments': {nodes[m]['extras']['panel']: sorted(ids) for m, ids in attachments.items() if ids},
    'positions_uvs_normals_indices_weights_materials_and_rig_unchanged': True,
}
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
fitting_path = ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json'
fitting = json.loads(fitting_path.read_text())
fitting['rigging']['sha256'] = report['output_sha256']
fitting['panel_seam_repair'] = str((REPAIR / 'repair.json').relative_to(ROOT))
fitting_path.write_text(json.dumps(fitting, indent=2) + '\n')
print(json.dumps({**report, 'attachments': {k: len(v) for k, v in report['attachments'].items()}}, indent=2))
