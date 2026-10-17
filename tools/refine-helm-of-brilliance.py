import argparse
import gzip
import importlib.util
import itertools
import json
import shutil
from pathlib import Path

import numpy as np
import trimesh

from lib.glb import read_glb, write_glb, view_bytes
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fit', ROOT / 'tools/fit-helm-of-brilliance.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)
parser = argparse.ArgumentParser()
parser.add_argument('sex', choices=['male', 'female'])
sex = parser.parse_args().sex
directory = fit.DIRECTORY / 'fitted_v1' / sex
initial = directory / 'initial'
initial.mkdir(exist_ok=True)
for name in ['helmet_brilliance.glb', 'fitting.json', 'skin-clearance-validation.json']:
    if not (initial / name).exists():
        shutil.copy2(directory / name, initial / name)
report = json.loads((initial / 'fitting.json').read_text())
diagnostic = json.loads((initial / 'skin-clearance-validation.json').read_text())
poses = json.loads(gzip.decompress((directory / 'skin-motion.json.gz').read_bytes()))
topology = json.loads(gzip.decompress((directory / 'skin-topology.json.gz').read_bytes()))
rest = np.array(poses[0]['points'])
moving = np.array(topology['moving_indices'])
skin_faces = np.array(topology['faces'])
order = sorted(range(len(poses)), key=lambda i: -diagnostic['poses'][i]['contact_count'])
skin_managers = {}


def skin_manager(index):
    if index not in skin_managers:
        vertices = rest.copy()
        if index:
            vertices[moving] = np.array(poses[index]['points'])
        manager = trimesh.collision.CollisionManager()
        manager.add_object('skin', trimesh.Trimesh(vertices, skin_faces, process=False))
        skin_managers[index] = manager
    return skin_managers[index]


doc, binary = read_glb(initial / 'helmet_brilliance.glb')
original_images = [view_bytes(doc, binary, image['bufferView']) for image in doc['images']]
primitive = doc['meshes'][0]['primitives'][0]
attrs = primitive['attributes']
points = accessor(doc, binary, attrs['POSITION']).astype(float)
faces = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
cutoff = report['brow_y'] - .035


def deform(vertices, front, rear, forward, inward):
    result = vertices.copy()
    blend = fit.io.smoothstep((vertices[:, 2] + .02) / .08)
    lift = rear * (1 - blend) + front * blend
    fade = fit.io.smoothstep((cutoff - vertices[:, 1]) / .18)
    result[:, 1] += lift * fade
    result[:, 2] += forward * blend * fade
    result[:, 0] -= inward * np.sign(vertices[:, 0]) * blend * fade
    return result


chosen = None
options = list(itertools.product(np.arange(0, .0801, .01),
                                [0] if sex == 'female' else np.arange(0, .0801, .01),
                                np.arange(-.04, .0601, .02) if sex == 'female' else [0],
                                np.arange(-.04, .0401, .01) if sex == 'female' else [0]))
options.sort(key=lambda option: sum(value ** 2 for value in option))
for front, rear, forward, inward in options:
    vertices = deform(points, front, rear, forward, inward)
    manager = trimesh.collision.CollisionManager()
    manager.add_object('helmet', trimesh.Trimesh(vertices, faces, process=False))
    if any(manager.in_collision_other(skin_manager(index)) for index in order):
        continue
    chosen = float(front), float(rear), float(forward), float(inward)
    print(json.dumps({'sex': sex, 'front_lift': front, 'rear_lift': rear,
                      'front_forward': forward, 'front_inward': inward,
                      'verified_poses': len(poses)}), flush=True)
    break
assert chosen is not None, 'No guard refinement clears all sampled poses'
front, rear, forward, inward = chosen
fitted = deform(points, front, rear, forward, inward)
normal = accessor(doc, binary, attrs['NORMAL'])
normal = fit.io.transformed_normals(points, normal, lambda vertices: deform(vertices, front, rear, forward, inward))
raw = bytearray(binary)
attrs['POSITION'] = add_accessor(doc, raw, fitted, 'VEC3')
attrs['NORMAL'] = add_accessor(doc, raw, normal, 'VEC3')
uv = accessor(doc, binary, attrs['TEXCOORD_0'])
attrs['TANGENT'] = add_accessor(doc, raw, fit.io.tangents(fitted, normal, uv, faces), 'VEC4')
raw = fit.io.compact(doc, raw)
assert np.isfinite(fitted).all() and np.isfinite(normal).all()
assert original_images == [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
target = directory / 'helmet_brilliance.glb'
write_glb(target, doc, raw)
report['output']['sha256'] = fit.digest(target)
report['guard_refinement'] = {
    'front_maximum_raise_m': front, 'rear_maximum_raise_m': rear,
    'front_maximum_forward_m': forward,
    'front_maximum_inward_m': inward,
    'fade_top_y': cutoff, 'fade_height_m': .18,
    'maximum_vertex_displacement_m': float(np.linalg.norm(fitted - points, axis=1).max()),
    'reason': 'Initial raw fit intersects the neck/shoulder in runtime poses. Shorten the lower cheek/neck guards with a smooth vertical deformation; retain brow, dome, crystal and wings.',
    'initial_intersecting_samples': diagnostic['intersecting_samples'],
    'refined_intersecting_samples': 0, 'verified_pose_samples': len(poses),
    'preserved': ['indices', 'UVs', 'texture bytes', 'Head weights', 'canonical bind matrices'],
}
report['clearance_m']['scope'] = 'Radial measurements precede local guard refinement; final skin intersections are checked separately with FCL.'
report['status'] = 'Refined fit; requires fresh animation validation and rendered review'
(directory / 'fitting.json').write_text(json.dumps(report, indent=2) + '\n')
