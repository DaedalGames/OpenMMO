import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import trimesh

from lib.glb import read_glb
from lib.glb_accessors import accessor

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('sex', choices=['male', 'female'])
parser.add_argument('--directory', type=Path)
args = parser.parse_args()
sex = args.sex
directory = ROOT / (args.directory or Path('assets/items/helm_of_brilliance/tripo_v2/fitted_v3') / sex)
poses = json.loads(gzip.decompress((directory / 'skin-motion.json.gz').read_bytes()))
topology = json.loads(gzip.decompress((directory / 'skin-topology.json.gz').read_bytes()))
doc, binary = read_glb(directory / 'helmet_brilliance.glb')
primitive = doc['meshes'][0]['primitives'][0]
points = accessor(doc, binary, primitive['attributes']['POSITION'])
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
manager = trimesh.collision.CollisionManager()
manager.add_object('helmet', trimesh.Trimesh(points, faces, process=False))
rest = np.array(poses[0]['points'])
moving = np.array(topology['moving_indices'])
skin_faces = np.array(topology['faces'])
results = []
for pose in poses:
    vertices = rest.copy()
    if pose['name'] != 'rest':
        vertices[moving] = np.array(pose['points'])
    skin = trimesh.Trimesh(vertices, skin_faces, process=False)
    collision, contacts = manager.in_collision_single(skin, return_data=True)
    results.append({'name': pose['name'], 'time': pose['time'], 'intersecting': bool(collision),
                    'contact_count': len(contacts),
                    'contact_points': [contact.point.tolist() for contact in contacts[:12]]})
report = {
    'date': '2026-10-17', 'sex': sex,
    'skin_vertices': len(rest), 'moving_skin_vertices': len(moving),
    'skin_triangles': len(skin_faces), 'samples': len(results),
    'intersecting_samples': sum(pose['intersecting'] for pose in results),
    'method': 'FCL BVH triangle-surface intersection against runtime-skinned body geometry in Head rest space; includes skin faces above the upper-torso cutoff, rest, four explicit head rotations and 33 samples per animation clip. Rigid Head vertices retain their rest positions in Head space.',
    'scope': 'Canonical skin and neck with hair hidden. Clothes, hair under the helmet and custom body proportions are outside this check.',
    'poses': results,
}
(directory / 'skin-clearance-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'poses'}))
assert report['intersecting_samples'] == 0, 'Skin surface intersections require fitting corrections'
