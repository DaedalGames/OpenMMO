import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'assets/modular_human_female_01/underwear_fit_v1'
spec = importlib.util.spec_from_file_location('repair', ROOT / 'tools/fix-female-underwear-clipping.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
record = json.loads((OUTPUT / 'fitting.json').read_text())
patch = np.load(OUTPUT / 'source-influences.npz')
body = ROOT / record['body']
assert repair.digest(body) == record['output_sha256']
doc, binary = read_glb(body)
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION'])
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
joints = accessor(doc, binary, attrs['JOINTS_0'])
weights = accessor(doc, binary, attrs['WEIGHTS_0'])
assert np.all(weights >= 0) and np.allclose(weights.sum(1), 1, atol=1e-6)
assert joints.max() < len(doc['skins'][0]['joints'])
_, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
welded = welded.ravel()
edges = welded[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
_, components = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                                                shape=(welded.max() + 1,) * 2), directed=False)
labels = components[welded]
skin, bra = np.argsort(np.bincount(labels))[-2:][::-1]
skin_faces = faces[(labels[faces[:, 0]] == skin) & (points[faces, 1].min(1) > .67)
                   & (points[faces, 1].max(1) < .87)]
surface = trimesh.Trimesh(points, skin_faces, process=False)
candidate = faces[(labels[faces[:, 0]] == bra) & (points[faces, 2].mean(1) > .015)
                  & (points[faces, 1].mean(1) > .72) & (points[faces, 1].mean(1) < .81)]
_, _, nearest = trimesh.proximity.closest_point(surface, points[candidate].mean(1))
normals = trimesh.triangles.normals(points[candidate])[0]
exterior = candidate[np.einsum('ij,ij->i', normals, surface.face_normals[nearest]) > .5]
indices = np.unique(np.r_[skin_faces.ravel(), exterior.ravel()])
remap = np.full(len(points), -1)
remap[indices] = np.arange(len(indices))
bary = np.array([[1/3] * 3] + [(u, v, 1-u-v) for u in np.linspace(0, 1, 5)
                              for v in np.linspace(0, 1, 5) if u+v <= 1])
export = """
import {readFileSync, writeFileSync} from 'node:fs'
import * as THREE from './client/node_modules/three/build/three.module.js'
import {headlessThree, clipSampler} from './tools/lib/headless-three.mjs'
const directory = process.argv[1]
const manifest = JSON.parse(readFileSync(directory + '/manifest.json'))
const {server, load} = await headlessThree()
try {
  for (const kind of ['before', 'after']) {
    const base = await load(manifest[kind])
    let body
    base.scene.traverse(n => { if (n.isSkinnedMesh && base.parser.associations.get(n)?.primitives === 0) body = n })
    const data = [], poses = [], point = new THREE.Vector3()
    const capture = (name, time) => {
      base.scene.updateMatrixWorld(true); body.skeleton.update()
      const values = new Float32Array(manifest.indices.length * 3)
      manifest.indices.forEach((index, i) => body.getVertexPosition(index, point).toArray(values, i * 3))
      data.push(Buffer.from(values.buffer)); poses.push({name, time})
    }
    capture('rest', 0)
    const sample = clipSampler(base.scene, {samples: 61, restore: body.skeleton.bones})
    for (const frame of sample(base.animations.find(c => c.name === 'idle1'))) capture('idle1', frame.time)
    writeFileSync(directory + '/' + kind + '.bin', Buffer.concat(data))
    writeFileSync(directory + '/poses.json', JSON.stringify(poses))
  }
} finally { await server.close() }
"""
with tempfile.TemporaryDirectory(prefix='female-underwear-') as directory:
    directory = Path(directory)
    before = directory / 'before.glb'
    before.write_bytes(body.read_bytes())
    repair.patch(before, doc, patch['indices'], patch['original_joints'], patch['original_weights'])
    assert repair.digest(before) == record['source_sha256'], 'Bytes outside the recorded underwear weights changed'
    runtime_doc, _ = read_glb(ROOT / record['runtime'])
    runtime_names = [runtime_doc['nodes'][i]['name'] for i in runtime_doc['skins'][0]['joints']]
    original_joints = np.array([runtime_names.index(patch['bone_names'][i])
                                for i in patch['original_joints'].ravel()]).reshape(-1, 4)
    original_joints[patch['original_weights'] == 0] = 0
    runtime_before = directory / 'runtime-before.glb'
    runtime_before.write_bytes((ROOT / record['runtime']).read_bytes())
    repair.patch(runtime_before, runtime_doc, patch['indices'], original_joints, patch['original_weights'])
    assert repair.digest(runtime_before) == record['runtime_sha256_before'], 'Runtime changed outside the underwear weights'
    (directory / 'manifest.json').write_text(json.dumps({'before': str(before), 'after': str(body), 'indices': indices.tolist()}))
    subprocess.run(['node', '--input-type=module', '-e', export, str(directory)], cwd=ROOT, check=True)
    poses = json.loads((directory / 'poses.json').read_text())
    frames = [dict(pose) for pose in poses]
    for kind in ['before', 'after']:
        posed = np.fromfile(directory / f'{kind}.bin', np.float32).reshape(-1, len(indices), 3)
        for i, frame in enumerate(frames):
            surface = trimesh.Trimesh(posed[i], remap[skin_faces], process=False)
            probes = np.einsum('sk,fkj->fsj', bary, posed[i, remap[exterior]]).reshape(-1, 3)
            closest, _, triangles = trimesh.proximity.closest_point(surface, probes)
            depth = np.einsum('ij,ij->i', probes - closest, surface.face_normals[triangles])
            frame[kind] = {'minimum_distance': float(depth.min()), 'penetrating_samples': int((depth < 0).sum())}
minimum = {kind: min(frame[kind]['minimum_distance'] for frame in frames) for kind in ['before', 'after']}
report = {'source_sha256': record['source_sha256'], 'output_sha256': record['output_sha256'],
          'frame_count': len(frames), 'exterior_cup_triangles': len(exterior),
          'minimum_distance': minimum, 'frames': frames, 'meters_per_source_unit': 1.8,
          'only_recorded_underwear_weights_changed': True, 'runtime_only_recorded_weights_changed': True,
          'scope': 'Rest and 61 idle1 frames; outer cup vertices, face centers and a barycentric grid against exact posed skin.'}
(OUTPUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert minimum['before'] < 0, 'The original clipping was not reproduced'
assert minimum['after'] > 0, 'Underwear still intersects skin in rest or idle'
print(json.dumps({key: report[key] for key in ['frame_count', 'exterior_cup_triangles', 'minimum_distance']}, indent=2))
