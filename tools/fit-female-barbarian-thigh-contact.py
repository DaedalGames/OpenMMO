import hashlib
import json
from pathlib import Path

from lib.glb import read_glb, write_glb

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
REPAIR = DIRECTORY / 'thigh_contact_v1'
SOURCE = REPAIR / 'before.glb'
OUTPUT = DIRECTORY / 'bottom_female_barbarian.glb'
doc, original = read_glb(SOURCE)
binary = original
for node in doc['nodes']:
    panel = node.get('extras', {}).get('panel')
    if panel not in ['left', 'right']:
        continue
    config = node['extras']['pelt_physics']
    sign = 1 if panel == 'left' else -1
    config['colliders'][0]['radii'][2] = .072
    config['colliders'].append({
        'bone': 'LeftUpLeg' if sign > 0 else 'RightUpLeg',
        'center': [sign * .065, .505, -.010],
        'radii': [.050, .085, .065],
    })
write_glb(OUTPUT, doc, binary)
report = {
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output': str(OUTPUT.relative_to(ROOT)),
    'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'method': 'Add proximal thigh ellipsoids and increase the main thigh depth radius from 57 to 72 mm; keep side fur outside the posed upper thighs using the existing pelt solver.',
    'positions_indices_uvs_normals_weights_materials_rig_and_attachments_unchanged': True,
}
(REPAIR / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
fitting_path = ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json'
fitting = json.loads(fitting_path.read_text())
fitting['rigging']['sha256'] = report['output_sha256']
fitting['rigging']['vertices'] = sum(doc['accessors'][mesh['primitives'][0]['attributes']['POSITION']]['count'] for mesh in doc['meshes'])
fitting['triangles'] = sum(doc['accessors'][mesh['primitives'][0]['indices']]['count'] // 3 for mesh in doc['meshes'])
fitting['thigh_contact_repair'] = str((REPAIR / 'repair.json').relative_to(ROOT))
fitting_path.write_text(json.dumps(fitting, indent=2) + '\n')
print(json.dumps(report, indent=2))
