import copy
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from lib.glb import read_glb, write_glb
from lib.glb_accessors import accessor, add_accessor
from outfits.female_boot_pose import heel_pose

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_boots/tripo_v1'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v3'
OUTPUT.mkdir(exist_ok=True)
REPORT = ROOT / 'doc/assets/modular-female-barbarian-boots-fitting-v3.json'
KNIGHT_FITTING = ROOT / 'assets/items/female_knight_boots/fitted_v5/fitting.json'
CHARACTER_HEIGHT_M = 1.8
SOLE_GAP = .0015
RING_CLEARANCE = .0065
MAX_RING_THICKNESS = .006
STRAP_CLEARANCE = .002
TOE_MARGIN = .004
HEEL_MARGIN = .003
SHOE_YAW_ADJUSTMENT_DEGREES = -7
LEFT_LATERAL_OFFSET = .0055
LEFT_REARWARD_OFFSET = .003
RIGHT_TOE_LIFT = .003
RIGHT_TOE_FOLLOW = .45
RIGHT_INSTEP_LIFT = .004
RIGHT_INSTEP_CLEARANCE = .001


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def smooth_share(points, share, radius=.004):
    distance, neighbors = cKDTree(points).query(points, min(32, len(points)))
    kernel = np.exp(-(distance / radius) ** 2)
    for _ in range(2):
        share = (kernel * share[neighbors]).sum(1) / kernel.sum(1)
    return share


def islands(points, faces):
    _, welded = np.unique(np.round(points, 6), axis=0, return_inverse=True)
    welded = welded.ravel()
    edges = welded[faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2)]
    _, labels = connected_components(coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                                                shape=(welded.max() + 1,) * 2), directed=False)
    return labels[welded]


class Surface:
    """Posed skin queries."""

    def __init__(self, points, faces, normals):
        self.mesh = trimesh.Trimesh(points, faces, process=False)
        self.a, self.b, self.c = (points[faces[:, k]] for k in range(3))
        weights = np.array([(u, v) for u in np.linspace(0, 1, 7) for v in np.linspace(0, 1, 7) if u + v <= 1])
        samples = (self.a[:, None] * (1 - weights.sum(1))[None, :, None] + self.b[:, None] * weights[None, :, 0, None]
                   + self.c[:, None] * weights[None, :, 1, None])
        face_normal = np.cross(self.b - self.a, self.c - self.a)
        face_normal /= np.linalg.norm(face_normal, axis=1, keepdims=True)
        vertex_normal = (normals[faces[:, 0]][:, None] * (1 - weights.sum(1))[None, :, None]
                         + normals[faces[:, 1]][:, None] * weights[None, :, 0, None]
                         + normals[faces[:, 2]][:, None] * weights[None, :, 1, None])
        self.samples = samples.reshape(-1, 3)
        self.normals = vertex_normal.reshape(-1, 3)
        self.normals /= np.linalg.norm(self.normals, axis=1, keepdims=True)
        self.tree = cKDTree(self.samples)

    def signed(self, points):
        closest, distance, triangles = trimesh.proximity.closest_point(self.mesh, points)
        normals = self.mesh.face_normals[triangles]
        return np.einsum('ij,ij->i', points - closest, normals), normals

    def ray(self, origin, direction, limit=1.):
        e1, e2 = self.b - self.a, self.c - self.a
        h = np.cross(direction, e2)
        det = (e1 * h).sum(1)
        valid = np.abs(det) > 1e-12
        inv = np.where(valid, 1 / np.where(valid, det, 1), 0)
        s = origin - self.a
        u = (s * h).sum(1) * inv
        q = np.cross(s, e1)
        v = (q @ direction) * inv
        t = (q * e2).sum(1) * inv
        hit = valid & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0) & (t < limit)
        return t[hit].min() if hit.any() else None


base, base_raw = read_glb(BODY)
heel_matrices, pose_config = heel_pose(base, base_raw)
body_primitive = base['meshes'][0]['primitives'][0]
bv = accessor(base, base_raw, body_primitive['attributes']['POSITION'])
bn = accessor(base, base_raw, body_primitive['attributes']['NORMAL'])
bf = accessor(base, base_raw, body_primitive['indices']).reshape(-1, 3)
body_joints = accessor(base, base_raw, body_primitive['attributes']['JOINTS_0'])
body_weights = accessor(base, base_raw, body_primitive['attributes']['WEIGHTS_0'])
deform = np.einsum('nk,nkij->nij', body_weights, heel_matrices[body_joints])
posed = np.einsum('nij,nj->ni', deform, np.column_stack([bv, np.ones(len(bv))]))[:, :3]
posed_normals = np.einsum('nij,nj->ni', deform[:, :3, :3], bn)
posed_normals /= np.linalg.norm(posed_normals, axis=1, keepdims=True)
body_labels = islands(bv, bf)
skin_label = np.bincount(body_labels).argmax()
leg = bf[(body_labels[bf[:, 0]] == skin_label) & (posed[bf, 1] < .30).all(1) & (posed[bf, 0] < -.03).all(1)]
skin = Surface(posed, leg, posed_normals)
foot = posed[np.unique(leg)]
foot = foot[foot[:, 1] < .10]
names = [base['nodes'][i]['name'] for i in base['skins'][0]['joints']]
node_index = {node.get('name'): i for i, node in enumerate(base['nodes'])}
toe_base = np.array(pose_config['posed_foot_positions_before_root_lift']['RightToeBase'])

doc, raw = read_glb(SOURCE)
primitive = doc['meshes'][0]['primitives'][0]
matrix = np.array(doc['nodes'][0]['matrix']).reshape(4, 4).T
source = accessor(doc, raw, primitive['attributes']['POSITION']) @ matrix[:3, :3].T + matrix[:3, 3]
source_normals = accessor(doc, raw, primitive['attributes']['NORMAL']) @ matrix[:3, :3].T
uv = accessor(doc, raw, primitive['attributes']['TEXCOORD_0'])
faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
labels = islands(source, faces)
for i, j in cKDTree(source).query_pairs(1e-3):
    source[max(i, j)] = source[min(i, j)]
sizes = np.bincount(labels)
main = labels == sizes.argmax()
buckles = [labels == label for label in np.flatnonzero((sizes > 0) & (sizes < 100))]
rings = [labels == label for label in np.flatnonzero(sizes >= 100) if label != sizes.argmax()]
rings.append(main & (source[:, 1] > .09))
ring_any = np.any(rings, axis=0)
lower = main & ~ring_any

foot_origin = np.array(pose_config['posed_foot_positions_before_root_lift']['RightFoot'])
forward = toe_base - foot_origin
forward[1] = 0
forward /= np.linalg.norm(forward)
yaw = np.deg2rad(SHOE_YAW_ADJUSTMENT_DEGREES)
forward = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0],
                    [-np.sin(yaw), 0, np.cos(yaw)]]) @ forward
up = np.array([0., 1., 0.])
lateral = np.cross(up, forward)
foot_frame = np.column_stack([lateral, up, forward])
foot_local = foot @ foot_frame
toe_local = toe_base @ foot_frame
foot_length = np.ptp(foot_local[:, 2]) + TOE_MARGIN + HEEL_MARGIN
sole = lower & (source[:, 1] < -.4)
toe_tip = source[sole, 0].min()
heel_back = source[lower, 0].max()
scale = foot_length / (heel_back - toe_tip)
points_local = np.column_stack([source[:, 2], source[:, 1], -source[:, 0]]) * scale
normals_local = np.column_stack([source_normals[:, 2], source_normals[:, 1], -source_normals[:, 0]])
forefoot_local = foot_local[foot_local[:, 2] > toe_local[2] - .01]
points_local += np.array([
    (forefoot_local[:, 0].min() + forefoot_local[:, 0].max()) / 2 - (points_local[sole, 0].min() + points_local[sole, 0].max()) / 2,
    foot_local[:, 1].min() - SOLE_GAP - points_local[sole & (source[:, 1] > -.47), 1].max(),
    foot_local[:, 2].max() + TOE_MARGIN - points_local[:, 2].max(),
])
points = points_local @ foot_frame.T
normals = normals_local @ foot_frame.T
start = points.copy()

targets = points.copy()
fixed = np.zeros(len(points), dtype=bool)
up = np.array([0., 1., 0.])
toe_strap = (source[:, 0] < -.1) & (source[:, 1] > -.42)
footbed = lower & (normals[:, 1] > .5) & (source[:, 1] < -.05) & ~toe_strap
for i in np.flatnonzero(footbed):
    hit = skin.ray(points[i] - up * .01, up, .06)
    if hit is not None:
        targets[i, 1] = points[i, 1] - .01 + hit - SOLE_GAP
        fixed[i] = True
ground = -json.loads(KNIGHT_FITTING.read_text())['posed_floor_offset']
sole_bottom = lower & (normals[:, 1] < -.5) & (source[:, 1] < -.45) & (source[:, 0] < .1)
targets[sole_bottom, 1] = ground
fixed |= sole_bottom
post = lower & (source[:, 0] > .3) & (source[:, 1] < -.25)
seat = lower & (source[:, 0] > .2) & (source[:, 1] > -.25) & (source[:, 1] < -.05)
tip = post & (source[:, 1] < -.49)
targets[tip, 1] = ground
fixed |= tip

section_heights = np.arange(-.02, .16, .002)
section_centers = []
for height in section_heights:
    section = skin.samples[np.abs(skin.samples[:, 1] - height) < .002]
    section_centers.append((section.min(0) + section.max(0)) / 2)
section_centers = np.array(section_centers)


def axis_at(height):
    return np.array([np.interp(height, section_heights, section_centers[:, 0]), height,
                     np.interp(height, section_heights, section_centers[:, 2])])


for ring in rings:
    center = (points[ring].min(0) + points[ring].max(0)) / 2
    offset = points[ring][:, [0, 2]] - center[[0, 2]]
    radius = np.linalg.norm(offset, axis=1)
    direction = offset / radius[:, None]
    slot = ((np.arctan2(direction[:, 1], direction[:, 0]) + np.pi) / (2 * np.pi) * 48).astype(int) % 48
    inner = np.array([radius[slot == k].min() if (slot == k).any() else np.nan for k in range(48)])
    valid = np.isfinite(inner)
    inner = np.interp(np.arange(48), np.flatnonzero(valid), inner[valid], period=48)
    depth_over_inner = np.minimum(radius - inner[slot], MAX_RING_THICKNESS)
    for k, i in enumerate(np.flatnonzero(ring)):
        ray = np.array([direction[k, 0], 0, direction[k, 1]])
        origin = axis_at(points[i, 1])
        hit = skin.ray(origin + ray * .15, -ray, .15)
        if hit is not None:
            targets[i] = origin + ray * (.15 - hit + RING_CLEARANCE + depth_over_inner[k])
    fixed |= ring
for buckle in buckles:
    nearest = cKDTree(points[ring_any]).query(points[buckle].mean(0))[1]
    k = np.flatnonzero(ring_any)[nearest]
    moved = points[buckle] + targets[k] - points[k]
    away = np.r_[moved.mean(0)[[0, 2]] - axis_at(moved[:, 1].mean())[[0, 2]], 0][[0, 2, 1]]
    away /= np.linalg.norm(away)
    for _ in range(20):
        if skin.signed(moved)[0].min() >= RING_CLEARANCE:
            break
        moved += away * .0005
    targets[buckle] = moved
    fixed |= buckle

np.savez(OUTPUT / 'arap-input.npz', points=points, faces=faces, fixed=fixed, targets=targets,
         colors=np.where(ring_any[:, None] | np.any(buckles, axis=0)[:, None], 1., 0.).repeat(3, 1))
subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'tools/outfits/fit_female_knight_top_surface.py'),
                str(OUTPUT / 'arap-input.npz')], check=True)
arap = np.load(OUTPUT / 'arap-result.npz')
fitted = arap['points'].copy()
rotations = arap['rotations']

free = (~fixed | ring_any | toe_strap) & ~post & ~sole_bottom
sample_weights = np.array([(u, v, 1 - u - v) for u in np.linspace(0, 1, 5)
                           for v in np.linspace(0, 1, 5) if u + v <= 1])
_, welded = np.unique(np.round(source, 6), axis=0, return_inverse=True)
welded = welded.ravel()
for iteration in range(25):
    probes = np.einsum('sk,fkj->fsj', sample_weights, fitted[faces]).reshape(-1, 3)
    distance, direction = skin.signed(probes)
    gap = np.where(np.any(ring_any[faces], axis=1), RING_CLEARANCE, STRAP_CLEARANCE)
    deficit = (gap[:, None] - distance.reshape(-1, len(sample_weights))).clip(0)
    movable = free[faces]
    correction = np.zeros_like(fitted)
    counts = np.zeros(len(fitted))
    for sample, bary in enumerate(sample_weights):
        influence = movable * bary
        divisor = (influence ** 2).sum(1)
        bad = (deficit[:, sample] > .00001) & (divisor > 0)
        displacement = direction.reshape(-1, len(sample_weights), 3)[:, sample] * deficit[:, sample, None]
        for corner in range(3):
            factor = np.divide(influence[:, corner], divisor, out=np.zeros(len(faces)), where=divisor > 0)
            active = bad & (influence[:, corner] > 0)
            np.add.at(correction, faces[active, corner], displacement[active] * factor[active, None])
            np.add.at(counts, faces[active, corner], 1)
    welded_correction = np.zeros((welded.max() + 1, 3))
    welded_counts = np.zeros(welded.max() + 1)
    np.add.at(welded_correction, welded, correction)
    np.add.at(welded_counts, welded, counts)
    step = welded_correction[welded] / np.maximum(welded_counts[welded, None], 1)
    step *= np.minimum(1, .0005 / np.maximum(np.linalg.norm(step, axis=1), 1e-12))[:, None]
    fitted += step * .8
    if np.linalg.norm(step, axis=1).max() < .00001:
        break

fitted[:, 1] = np.maximum(fitted[:, 1], ground)
final_depth = skin.signed(fitted)[0]
fitted_normals = np.einsum('nij,nj->ni', rotations, normals)
fitted_normals /= np.linalg.norm(fitted_normals, axis=1, keepdims=True)

leg_bone, foot_bone, toe_bone = (names.index('Right' + name) for name in ['Leg', 'Foot', 'ToeBase'])
heel_top = fitted[seat, 1].max()
ring_bottom = fitted[ring_any, 1].min()
shin = np.where(np.any(buckles, axis=0) | ring_any, 1, smooth((fitted[:, 1] - heel_top) / max(ring_bottom - heel_top, .01)))
toe = (1 - shin) * .2 * smooth((fitted[:, 2] - (toe_base[2] - .008)) / .03) * smooth((fitted[:, 1] - ground - .002) / .01)
weights = np.column_stack([shin, 1 - shin - toe, toe, np.zeros(len(fitted))])
joints = np.tile([leg_bone, foot_bone, toe_bone, 0], (len(fitted), 1))
ring_points = cKDTree(fitted[ring_any])
strap = ~ring_any & ~np.any(buckles, axis=0) & (fitted[:, 1] > heel_top)
skin_mesh = skin.mesh
closest, _, triangle = trimesh.proximity.closest_point(skin_mesh, fitted)
barycentric = trimesh.triangles.points_to_barycentric(skin_mesh.triangles[triangle], closest).clip(0, 1)
barycentric /= barycentric.sum(1, keepdims=True)
transferred = np.zeros((len(fitted), len(names)))
for corner in range(3):
    vertex = leg[triangle, corner]
    for influence in range(4):
        np.add.at(transferred, (np.arange(len(fitted)), body_joints[vertex, influence]),
                  barycentric[:, corner] * body_weights[vertex, influence])
flexible = ring_any
weights[flexible] = transferred[flexible][:, [leg_bone, foot_bone, toe_bone, 0]]
weights[flexible] /= weights[flexible].sum(1, keepdims=True)
for ring in rings:
    share = smooth_share(fitted[ring], weights[ring, 1] + weights[ring, 2])
    weights[ring] = np.column_stack([1 - share, share, np.zeros((ring.sum(), 2))])
strap &= ~toe_strap
nearest = np.flatnonzero(ring_any)[ring_points.query(fitted[strap])[1]]
blend = np.clip((fitted[strap, 1] - heel_top) / max(ring_bottom - heel_top, .01), 0, 1)[:, None]
weights[strap] = (1 - blend) * np.array([0, 1, 0, 0]) + blend * weights[nearest]
for buckle in buckles:
    nearest = ring_points.query(fitted[buckle].mean(0), 20)[1]
    weights[buckle] = weights[np.flatnonzero(ring_any)[nearest]].mean(0)

toe_share = .35 * smooth((fitted[:, 1] - ground - .004) / .02) * smooth((fitted[:, 2] - toe_base[2] + .015) / .04)
weights[toe_strap, 0] = 0
weights[toe_strap, 1] = 1 - toe_share[toe_strap]
weights[toe_strap, 2] = toe_share[toe_strap]
weights[toe_strap, 3] = 0

original_vertex_count = len(fitted)
rear_sections = []
for ring in rings:
    rear = ring & (np.abs(fitted[:, 0] - axis_at(fitted[ring, 1].mean())[0]) < .012)
    rear_sections.append((fitted[ring, 1].mean(), fitted[rear, 2].min()))
rear_sections.sort()
rear_sections = np.array(rear_sections)
heights = np.linspace(fitted[ring_any, 1].min() + .001, fitted[ring_any, 1].max() - .001, 19)
connector = []
for y in heights:
    center = axis_at(y)
    rear_z = np.interp(y, rear_sections[:, 0], rear_sections[:, 1])
    for x_offset, thickness in [(-.005, 0), (.005, 0), (.005, .0015), (-.005, .0015)]:
        x = center[0] + x_offset
        hit = skin.ray(np.array([x, y, -.2]), np.array([0., 0., 1.]))
        z = min(-.2 + hit - .0035, rear_z - .0005) if hit is not None else rear_z - .0005
        connector.append([x, y, z - thickness])
connector = np.array(connector)
connector_faces = []
for row in range(len(heights) - 1):
    for side in range(4):
        a, b = row * 4 + side, row * 4 + (side + 1) % 4
        connector_faces.extend([[a, b, b + 4], [a, b + 4, a + 4]])
connector_faces.extend([[0, 2, 1], [0, 3, 2]])
last = (len(heights) - 1) * 4
connector_faces.extend([[last, last + 1, last + 2], [last, last + 2, last + 3]])
connector_faces = np.array(connector_faces)
connector_mesh = trimesh.Trimesh(connector, connector_faces, process=False)
closest, _, triangle = trimesh.proximity.closest_point(skin_mesh, connector)
barycentric = trimesh.triangles.points_to_barycentric(skin_mesh.triangles[triangle], closest).clip(0, 1)
barycentric /= barycentric.sum(1, keepdims=True)
connector_weights = np.zeros((len(connector), len(names)))
for corner in range(3):
    vertex = leg[triangle, corner]
    for influence in range(4):
        np.add.at(connector_weights, (np.arange(len(connector)), body_joints[vertex, influence]),
                  barycentric[:, corner] * body_weights[vertex, influence])
connector_weights = connector_weights[:, [leg_bone, foot_bone, toe_bone, 0]]
connector_weights /= connector_weights.sum(1, keepdims=True)
connector_share = smooth_share(connector, connector_weights[:, 1] + connector_weights[:, 2], .008)
connector_weights = np.column_stack([1 - connector_share, connector_share, np.zeros((len(connector), 2))])
leather_faces = faces[(post[faces]).all(1)]
uv_triangle = uv[leather_faces[np.argmax(trimesh.triangles.area(fitted[leather_faces]))]]
connector_uv = []
for row in range(len(heights)):
    for corner in range(4):
        u, v = (.2 if corner in [0, 3] else .4), .2 + .3 * row / (len(heights) - 1)
        connector_uv.append(uv_triangle[0] * (1 - u - v) + uv_triangle[1] * u + uv_triangle[2] * v)
fitted = np.vstack([fitted, connector])
fitted_normals = np.vstack([fitted_normals, connector_mesh.vertex_normals])
faces = np.vstack([faces, connector_faces + original_vertex_count])
uv = np.vstack([uv, connector_uv])
joints = np.vstack([joints, np.tile([leg_bone, foot_bone, toe_bone, 0], (len(connector), 1))])
weights = np.vstack([weights, connector_weights])
for key in ['ring_any', 'fixed', 'post', 'seat', 'toe_strap', 'strap']:
    globals()[key] = np.r_[globals()[key], np.zeros(len(connector), dtype=bool)]
buckles = [np.r_[mask, np.zeros(len(connector), dtype=bool)] for mask in buckles]
source = np.vstack([source, np.zeros_like(connector)])
start = np.vstack([start, connector])
final_depth = skin.signed(fitted)[0]

order = np.argsort(-weights, axis=1)
joints, weights = np.take_along_axis(joints, order, 1), np.take_along_axis(weights, order, 1)

binary = bytearray(raw)
meshes, nodes = [], []
left_fit = {}
right_fitted = fitted.copy()
right_weights = weights.copy()
right_toe_lift = RIGHT_TOE_LIFT
for side in ['Right', 'Left']:
    points_side, normals_side, faces_side, joints_side = fitted.copy(), fitted_normals.copy(), faces.copy(), joints.copy()
    weights_side = weights.copy()
    if side == 'Right':
        strap_progress = np.clip((points_side[:, 1] - ground - .005) / .02, 0, 1)
        points_side[:, 1] += RIGHT_INSTEP_LIFT * smooth(strap_progress) * toe_strap
        strap_slope = RIGHT_INSTEP_LIFT * 6 * strap_progress * (1 - strap_progress) / .02 * toe_strap
        normals_side[:, 1] /= 1 + strap_slope
        normals_side /= np.linalg.norm(normals_side, axis=1, keepdims=True)
        _, strap_direction = skin.signed(points_side)
        points_side += (RIGHT_INSTEP_CLEARANCE * smooth(strap_progress) * toe_strap)[:, None] * strap_direction
        toe_start = toe_local[2] + .038
        toe_span = (points_side @ forward).max() - toe_start
        toe_progress = np.clip((points_side @ forward - toe_start) / toe_span, 0, 1)
        ankle_progress = np.clip((points_side[:, 1] - heel_top) / (ring_bottom - heel_top), 0, 1)
        ankle_share = 1 - smooth(ankle_progress)
        lift_share = toe_progress ** 2 * ankle_share
        triangles = points_side[faces]
        face_normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        top = ((source[faces, 1] < -.4).all(1)
               & (face_normals[:, 1] > .4 * np.linalg.norm(face_normals, axis=1)))
        probes = np.einsum('sk,fkj->fsj', sample_weights, triangles[top]).reshape(-1, 3)
        probe_share = np.einsum('sk,fk->fs', sample_weights, lift_share[faces[top]]).reshape(-1)
        for probe, share in zip(probes, probe_share):
            if share < .001:
                continue
            hit = skin.ray(probe, up, .04)
            if hit is not None:
                clearance = min(SOLE_GAP * .2, hit * .2)
                right_toe_lift = min(right_toe_lift, (hit - clearance) / share)
        points_side[:, 1] += right_toe_lift * lift_share
        slope = right_toe_lift * 2 * toe_progress / toe_span * ankle_share
        gradient = slope[:, None] * forward
        gradient[:, 1] = -right_toe_lift * toe_progress ** 2 * 6 * ankle_progress * (1 - ankle_progress) / (ring_bottom - heel_top)
        normals_side -= gradient * (normals_side[:, 1] / (1 + gradient[:, 1]))[:, None]
        normals_side /= np.linalg.norm(normals_side, axis=1, keepdims=True)
        follow_start = toe_local[2] + .026
        follow_span = (points_side @ forward).max() - follow_start
        follow_progress = np.clip((points_side @ forward - follow_start) / follow_span, 0, 1)
        toe_follow = RIGHT_TOE_FOLLOW * follow_progress ** 2 * ankle_share
        weights_side *= 1 - toe_follow[:, None]
        weights_side += (joints_side == toe_bone) * toe_follow[:, None]
        right_weights = weights_side.copy()
        right_fitted = points_side.copy()
        final_depth = skin.signed(points_side)[0]
    if side == 'Left':
        points_side[:, 0] *= -1
        normals_side[:, 0] *= -1
        faces_side = faces_side[:, ::-1]
        transition = np.clip((points_side[:, 1] - heel_top) / (ring_bottom - heel_top), 0, 1)
        offset = lateral * [1, 1, -1] * LEFT_LATERAL_OFFSET - forward * [-1, 1, 1] * LEFT_REARWARD_OFFSET
        points_side += (1 - smooth(transition))[:, None] * offset
        slope = -6 * transition * (1 - transition) / (ring_bottom - heel_top)
        normals_side[:, 1] -= slope * (normals_side @ offset)
        normals_side /= np.linalg.norm(normals_side, axis=1, keepdims=True)
        for name in ['Leg', 'Foot', 'ToeBase']:
            joints_side[joints == names.index('Right' + name)] = names.index('Left' + name)
        left_faces = bf[(body_labels[bf[:, 0]] == skin_label) & (posed[bf, 1] < .30).all(1)
                        & (posed[bf, 0] > .03).all(1)]
        left_skin = Surface(posed, left_faces, posed_normals)
        front_neighborhood = np.zeros(len(fitted), dtype=bool)
        front_neighborhood[np.unique(faces[toe_strap[faces].any(1)])] = True
        front_neighborhood &= points_side[:, 1] > ground + .004
        adjustable = ring_any | front_neighborhood | (np.arange(len(fitted)) >= original_vertex_count)
        for _ in range(5):
            distance, direction = left_skin.signed(points_side)
            inside = adjustable & (distance < STRAP_CLEARANCE + .0025)
            points_side[inside] += direction[inside] * (STRAP_CLEARANCE + .0025 - distance[inside])[:, None]
        points_side[:, 1] = np.maximum(points_side[:, 1], ground)
        left_bones = [names.index('Left' + suffix) for suffix in ['Leg', 'Foot', 'ToeBase']]
        for ring in rings:
            ring = np.r_[ring, np.zeros(len(connector), dtype=bool)]
            closest, _, triangles = trimesh.proximity.closest_point(left_skin.mesh, points_side[ring])
            bary = trimesh.triangles.points_to_barycentric(left_skin.mesh.triangles[triangles], closest).clip(0, 1)
            bary /= bary.sum(1, keepdims=True)
            skin_vertices = left_faces[triangles]
            foot_share = np.sum(bary * np.sum(
                ((body_joints[skin_vertices] == left_bones[1]) | (body_joints[skin_vertices] == left_bones[2]))
                * body_weights[skin_vertices], axis=2), axis=1)
            foot_share = smooth_share(points_side[ring], foot_share)
            weights_side[ring] = np.column_stack([1 - foot_share, foot_share, np.zeros((ring.sum(), 2))])
            joints_side[ring] = [*left_bones, 0]
        near = np.flatnonzero(ring_any)[cKDTree(points_side[ring_any]).query(points_side[strap])[1]]
        left_blend = np.clip((points_side[strap, 1] - heel_top) / max(ring_bottom - heel_top, .01), 0, 1)[:, None]
        weights_side[strap] = (1 - left_blend) * np.array([0, 1, 0, 0]) + left_blend * weights_side[near]
        joints_side[strap] = [*left_bones, 0]
        for buckle in buckles:
            near = cKDTree(points_side[ring_any]).query(points_side[buckle].mean(0), 20)[1]
            ring_vertices = np.flatnonzero(ring_any)[near]
            weights_side[buckle] = weights_side[ring_vertices].mean(0)
            joints_side[buckle] = [*left_bones, 0]
        left_fit = {'left_fitted': points_side.copy(), 'left_joints': joints_side.copy(), 'left_weights': weights_side.copy()}
    deformation = np.einsum('nk,nkij->nij', weights_side, heel_matrices[joints_side])
    bind = np.linalg.solve(deformation, np.column_stack([points_side, np.ones(len(points_side))])[..., None])[:, :3, 0]
    bind_normals = np.einsum('nji,nj->ni', deformation[:, :3, :3], normals_side)
    bind_normals /= np.linalg.norm(bind_normals, axis=1, keepdims=True)
    attributes = {'POSITION': add_accessor(doc, binary, bind.astype(np.float32), 'VEC3'),
                  'NORMAL': add_accessor(doc, binary, bind_normals.astype(np.float32), 'VEC3'),
                  'TEXCOORD_0': add_accessor(doc, binary, uv, 'VEC2'),
                  'JOINTS_0': add_accessor(doc, binary, joints_side.astype(np.uint16), 'VEC4', 5123),
                  'WEIGHTS_0': add_accessor(doc, binary, weights_side.astype(np.float32), 'VEC4')}
    for key in ['POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0']:
        doc['bufferViews'][doc['accessors'][attributes[key]]['bufferView']]['target'] = 34962
    meshes.append({'name': f'boots_female_barbarian_{side.lower()}', 'primitives': [{
        'attributes': attributes, 'material': primitive['material'],
        'indices': add_accessor(doc, binary, faces_side.reshape(-1, 1).astype(np.uint32), 'SCALAR', 5125)}]})
    nodes.append({'name': f'boots_female_barbarian_{side.lower()}', 'mesh': len(meshes) - 1, 'skin': 0,
                  'extras': {'rig_id': 'human_female_01_local_v1', 'part_id': 'boots_female_barbarian'}})
doc['meshes'], doc['nodes'] = meshes, nodes
ids = base['skins'][0]['joints']
mapping = {index: len(doc['nodes']) + i for i, index in enumerate(ids)}
for index in ids:
    node = copy.deepcopy(base['nodes'][index])
    if 'children' in node:
        node['children'] = [mapping[i] for i in node['children'] if i in mapping]
    doc['nodes'].append(node)
children = {child for index in ids for child in base['nodes'][index].get('children', [])}
pose_config['body_sha256'] = hashlib.sha256(BODY.read_bytes()).hexdigest()
doc['scenes'] = [{'nodes': [0, 1, len(doc['nodes'])], 'extras': {'rig_id': 'human_female_01_local_v1', 'heel_pose': pose_config}}]
doc['scene'] = 0
doc['nodes'].append({'name': 'Armature', 'children': [mapping[i] for i in ids if i not in children]})
doc['skins'] = [{'joints': [mapping[i] for i in ids], 'skeleton': mapping[base['skins'][0]['skeleton']],
                 'inverseBindMatrices': add_accessor(doc, binary, accessor(base, base_raw, base['skins'][0]['inverseBindMatrices']), 'MAT4')}]
spec = importlib.util.spec_from_file_location('plate', ROOT / 'tools/fit-modular-plate.py')
plate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plate)
binary = plate.compact(doc, binary)
write_glb(OUTPUT / 'boots_female_barbarian.glb', doc, binary)

garment = Surface(np.vstack([right_fitted, left_fit['left_fitted']]), np.vstack([faces, faces[:, ::-1] + len(fitted)]),
                  np.vstack([fitted_normals, fitted_normals * [-1, 1, 1]]))
covered = np.zeros(len(bv), dtype=bool)
for i in np.flatnonzero((posed[:, 1] < .06) & (body_labels == skin_label) & (posed_normals[:, 1] < -.3)):
    covered[i] = garment.ray(posed[i], posed_normals[i], .012) is not None
skin_points = np.flatnonzero(body_labels == skin_label)
near = cKDTree(posed[skin_points])
for i in np.flatnonzero(covered):
    if not covered[skin_points[near.query_ball_point(posed[i], .005)]].all():
        covered[i] = False
hidden = covered[bf].all(1)
mask = {'body': str(BODY.relative_to(ROOT)), 'body_sha256': pose_config['body_sha256'],
        'mesh_index': 0, 'primitive_index': 0, 'primitive_triangles': len(bf),
        'hide_triangle_indices': np.flatnonzero(hidden).tolist(), 'covered_skin_triangles': int(hidden.sum()),
        'scope': 'Reversible equipment mask on this exact body. Underside skin of the foot whose posed normal ray meets the '
                 'footbed within 0.012 and lies 0.005 inside the covered area; everything else stays visible. Restore on unequip/load failure.'}
(OUTPUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2) + '\n')

np.savez(OUTPUT / 'fit-data.npz', source=source, start=start, fitted=right_fitted, faces=faces, fixed=fixed,
         rings=ring_any, buckles=np.any(buckles, axis=0), depth=final_depth, joints=joints, weights=right_weights,
         bone_names=np.array(names), original_vertex_count=original_vertex_count, **left_fit)
report = {'date': '2026-10-15',
          'source': {'path': str(SOURCE.relative_to(ROOT)), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()},
          'body': {'path': str(BODY.relative_to(ROOT)), 'sha256': pose_config['body_sha256']},
          'output': str((OUTPUT / 'boots_female_barbarian.glb').relative_to(ROOT)),
          'rig_id': 'human_female_01_local_v1', 'triangles': int(len(faces) * 2), 'scale': float(scale),
          'heel_pose': {'pitch_degrees': pose_config['pitch_degrees'], 'shared_with': 'female_knight_boots', 'toe_animation_override': False},
          'shoe_yaw_degrees': {'right': float(np.rad2deg(np.arctan2(forward[0], forward[2]))), 'left': float(-np.rad2deg(np.arctan2(forward[0], forward[2])))},
          'shoe_yaw_adjustment_degrees': {'right': SHOE_YAW_ADJUSTMENT_DEGREES, 'left': -SHOE_YAW_ADJUSTMENT_DEGREES},
          'lateral_offset_source_units': {'right': 0, 'left': LEFT_LATERAL_OFFSET},
          'lateral_offset_m': {'right': 0, 'left': LEFT_LATERAL_OFFSET * CHARACTER_HEIGHT_M},
          'rearward_offset_source_units': {'right': 0, 'left': LEFT_REARWARD_OFFSET},
          'rearward_offset_m': {'right': 0, 'left': LEFT_REARWARD_OFFSET * CHARACTER_HEIGHT_M},
          'toe_lift_source_units': {'right': float(right_toe_lift), 'left': 0},
          'toe_lift_m': {'right': float(right_toe_lift * CHARACTER_HEIGHT_M), 'left': 0},
          'toe_animation_follow': {'right': RIGHT_TOE_FOLLOW, 'left': 0},
          'toe_profile': 'Quadratic toe lift and animation blend for a continuous, gradually increasing curve.',
          'instep_strap_lift_m': {'right': RIGHT_INSTEP_LIFT * CHARACTER_HEIGHT_M, 'left': 0},
          'instep_surface_offset_m': {'right': RIGHT_INSTEP_CLEARANCE * CHARACTER_HEIGHT_M, 'left': 0},
          'ground_source': str(KNIGHT_FITTING.relative_to(ROOT)),
          'posed_ground': float(ground), 'heel_height_m': float((fitted[seat, 1].min() - ground) * CHARACTER_HEIGHT_M),
          'meters_per_source_unit': CHARACTER_HEIGHT_M,
          'clearance_source_units': {'sole': SOLE_GAP, 'rings': RING_CLEARANCE, 'straps': STRAP_CLEARANCE},
          'clearance_m': {'sole': SOLE_GAP * CHARACTER_HEIGHT_M, 'rings': RING_CLEARANCE * CHARACTER_HEIGHT_M, 'straps': STRAP_CLEARANCE * CHARACTER_HEIGHT_M},
          'rest_clearance': {'penetrating_vertices': int((final_depth < 0).sum()), 'minimum': float(final_depth.min())},
          'arap': {'iterations': int(arap['iterations']), 'fixed_vertices': int(fixed.sum())},
          'hidden_body_triangles': int(hidden.sum()),
          'method': 'Rotate the shoe 7 degrees outward from the Foot-to-ToeBase heading to center the heel on the footbed; fit one right sandal on the shared 30-degree heel pose: uniform scale to foot length, footbed SOLE_GAP under '
                    'the posed sole, stiletto tip on the forefoot ground, rings radially RING_CLEARANCE off the ankle, ARAP for '
                    'the straps, outward push for any strap inside the skin. Mirror for the left and move its footbed outward '
                    'by LEFT_LATERAL_OFFSET and rearward by LEFT_REARWARD_OFFSET. Fade these translations '
                    'to zero at the ankle rings and refit the front straps. Curve the right toe tip upward, capped by '
                    'sampled footbed-to-skin clearance while preserving the ball contact. Use quadratic toe lift and animation '
                    'blends for a gradual curve, and raise the right instep strap while tapering to its sole attachments. Inverse-skin both into the '
                    'canonical bind pose and store heel_pose in scene extras like the knight boots.',
          'weights': 'Transfer ankle skin weights separately on both legs and smooth within 4 mm in source units. Buckles take the ring mean, the heel strap blends from Foot to the lower ring, and the new rear connector uses an 8 mm smoothing radius. Toe strap influence ramps to 0.35. The right toe tip additionally blends up to 0.45 toward ToeBase to follow the original toe animation. Ball contact, heel and stiletto remain on Foot. Existing foot and toe animation evaluation is unchanged.',
          'status': 'Candidate; validation pending'}
REPORT.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['scale', 'posed_ground', 'heel_height_m', 'rest_clearance', 'hidden_body_triangles', 'triangles']}))
