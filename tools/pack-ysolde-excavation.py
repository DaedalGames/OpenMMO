"""Pack the authored Ysolde excavation clip with its original rig transforms."""
import copy
import json
import hashlib
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.glb import read_glb, write_glb

ROOT = Path(__file__).resolve().parents[1]
source, _ = read_glb(ROOT / 'assets/npcs/ysolde/rig_v1/ysolde.glb')
clip = json.loads((ROOT / 'assets/npcs/ysolde/excavation/clip.json').read_text())
nodes = [{k: copy.deepcopy(v) for k, v in node.items() if k not in ('mesh', 'skin', 'camera')} for node in source['nodes']]
indices = {node.get('name'): i for i, node in enumerate(nodes)}
gltf = {'asset': {'version': '2.0', 'generator': 'Original Ysolde excavation authoring'}, 'nodes': nodes, 'scenes': copy.deepcopy(source['scenes']), 'scene': source.get('scene', 0), 'bufferViews': [], 'accessors': [], 'animations': [{'name': clip['name'], 'samplers': [], 'channels': []}]}
binary = bytearray()


def accessor(values, kind, bounds=False):
    offset = len(binary)
    binary.extend(struct.pack('<' + 'f' * len(values), *values))
    view = len(gltf['bufferViews'])
    gltf['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(binary) - offset})
    count = len(values) // {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[kind]
    entry = {'bufferView': view, 'componentType': 5126, 'count': count, 'type': kind}
    if bounds:
        entry.update(min=[min(values)], max=[max(values)])
    gltf['accessors'].append(entry)
    return len(gltf['accessors']) - 1


animation = gltf['animations'][0]
for track in clip['tracks']:
    name, prop = track['name'].rsplit('.', 1)
    path = 'translation' if prop == 'position' else 'rotation'
    inp = accessor(track['times'], 'SCALAR', True)
    output = accessor(track['values'], 'VEC3' if prop == 'position' else 'VEC4')
    sampler = len(animation['samplers'])
    animation['samplers'].append({'input': inp, 'output': output, 'interpolation': 'LINEAR'})
    animation['channels'].append({'sampler': sampler, 'target': {'node': indices[name], 'path': path}})
gltf['buffers'] = [{'byteLength': len(binary)}]
path = ROOT / 'client/public/models/animations/ysolde_excavation.glb'
write_glb(path, gltf, bytes(binary))
record = ROOT / 'assets/npcs/ysolde/excavation/validation.json'
data = json.loads(record.read_text())
data.update(runtime=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
record.write_text(json.dumps(data, indent=2) + '\n')
print(path, path.stat().st_size)
