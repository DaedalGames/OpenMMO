"""Preserve the runtime-tucked bard pants for the Blender assembly review."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bard', ROOT / 'tools/fit-tripo-bard-boots.py')
bard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bard)
fit, io = bard.fit, bard.io
source = io.PARTS / 'bard/tripo_pants_v1/pants_bard.glb'
doc, raw = fit.read_glb(source)
geometry = json.load(sys.stdin)
binary = bytearray(raw)
primitive = doc['meshes'][0]['primitives'][0]
for name, attribute, size, kind in [
    ('POSITION', 'position', 3, 'VEC3'), ('NORMAL', 'normal', 3, 'VEC3'),
    ('TEXCOORD_0', 'uv', 2, 'VEC2'), ('JOINTS_0', 'skinIndex', 4, 'VEC4'),
    ('WEIGHTS_0', 'skinWeight', 4, 'VEC4'),
]:
    values = np.array(geometry[attribute]).reshape(-1, size)
    primitive['attributes'][name] = io.add_accessor(doc, binary, values, kind,
        5123 if name == 'JOINTS_0' else 5126)
primitive['indices'] = io.add_accessor(doc, binary,
    np.array(geometry['indices']).reshape(-1, 1), 'SCALAR', 5125)
primitive['attributes'].pop('TANGENT', None)
binary = io.compact(doc, binary)
target = ROOT / 'assets/items/bard_starter/tripo_boots_v1/pants-bard-boots-review.glb'
fit.write_glb(target, doc, binary)
print(json.dumps(bard.record(target)))
