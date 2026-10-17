# Archival: pre-2026-10-17 source units (rig height 1); reproduce with assets.lock @ 1e291c68.
import hashlib
import json
import math
import subprocess
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'assets/items/female_barbarian_bottom/tripo_v1'
SOURCE = DIRECTORY / 'source/model_url.glb'
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
OUTPUT = DIRECTORY / 'fitted_v1'
OUTPUT.mkdir(exist_ok=True)
SCALE = .25
BELT_HEIGHT = .595
BELT_SOURCE_BOTTOM = .23
BELT_CLEARANCE = .004
FUR_CLEARANCE = .006
LEG_SHARE = .8
SMOOTHING = 16


def smooth(value):
    t = np.clip(value, 0, 1)
    return t * t * (3 - 2 * t)


def islands(points, faces):
    _, first, welded = np.unique(np.round(points, 6), axis=0, return_index=True, return_inverse=True)
    welded = welded.ravel()
    parent = np.arange(len(first))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for face in faces:
        roots = [find(welded[v]) for v in face]
        for r in roots[1:]:
            parent[find(r)] = find(roots[0])
    return np.array([find(welded[i]) for i in range(len(points))]), welded, first


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY), bone_heuristic='TEMPERANCE')
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
body = bpy.data.objects['female_body']
body_points = np.array([body.matrix_world @ vertex.co for vertex in body.data.vertices])
body_faces = [polygon.vertices[:] for polygon in body.data.polygons]
body_labels, _, _ = islands(body_points, body_faces)
skin_label = np.bincount(body_labels).argmax()
skin_faces = [face for face in body_faces if body_labels[face[0]] == skin_label]
# The belt sits over the panty waistband, so clearance is measured against skin and panties together.
lower_faces = [face for face in body_faces if (body_points[list(face), 2] < .70).all()
               and (np.abs(body_points[list(face), 0]) < .2).all()]
surface = BVHTree.FromPolygons([Vector(p) for p in body_points], lower_faces)
names = [bone.name for bone in rig.data.bones]

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
garment = next(obj for obj in set(bpy.data.objects) - before if obj.type == 'MESH')
garment.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z') @ garment.matrix_world)
garment.matrix_world = Matrix.Identity(4)
mesh = garment.data
source = np.array([vertex.co for vertex in mesh.vertices])
source_normals = np.array([normal.vector for normal in mesh.corner_normals])
loop_vertices = np.array([loop.vertex_index for loop in mesh.loops])
faces = np.array([polygon.vertices[:] for polygon in mesh.polygons])
labels, _, _ = islands(source, faces)
sizes = np.bincount(labels)
# Tripo leaves seam vertices up to 1e-3 apart; snap them (after finding the parts) so the fit cannot open cracks.
seams = KDTree(len(source))
for i, p in enumerate(source):
    seams.insert(Vector(p), i)
seams.balance()
for i in range(len(source)):
    for _, j, _ in seams.find_range(Vector(source[i]), 1e-3):
        source[j] = source[min(i, j)]
for vertex, p in zip(mesh.vertices, source):
    vertex.co = p
_, welded, first = islands(source, faces)
main = labels == sizes.argmax()

parts = {}
for label in np.unique(labels):
    if label == sizes.argmax():
        continue
    group = labels == label
    lo, hi = source[group].min(0), source[group].max(0)
    if hi[2] - lo[2] > .4 and hi[0] - lo[0] < .1:
        kind = 'cord'
    elif hi[1] < -.25 and lo[2] > .15:
        kind = 'medallion'
    elif group.sum() > 300:
        kind = 'fur'
    else:
        kind = 'fitting'
    parts.setdefault(kind, []).append(group)
assert len(parts['cord']) == 1 and len(parts['medallion']) == 1
cord, medallion = parts['cord'][0], parts['medallion'][0]
fittings = parts.get('fitting', [])
belt = main & (source[:, 2] > BELT_SOURCE_BOTTOM)
fur = ~belt & ~cord & ~medallion & ~np.any(fittings, axis=0)

center = np.array([(source[belt, 0].min() + source[belt, 0].max()) / 2,
                   (source[belt, 1].min() + source[belt, 1].max()) / 2,
                   (source[belt, 2].min() + source[belt, 2].max()) / 2])
section = body_points[(np.abs(body_points[:, 2] - BELT_HEIGHT) < .01) & (np.abs(body_points[:, 0]) < .16)]
anchor = np.array([0, (section[:, 1].min() + section[:, 1].max()) / 2, BELT_HEIGHT])
points = (source - center) * SCALE + anchor


def signed(p):
    location, normal, _, _ = surface.find_nearest(Vector(p))
    offset = p - np.array(location)
    normal = np.array(normal)
    return np.linalg.norm(offset) * (1 if offset @ normal >= 0 else -1), normal


depth = np.zeros(len(points))
outward = np.zeros_like(points)
for i, p in enumerate(points):
    depth[i], outward[i] = signed(p)
tree = KDTree(len(points))
for i, p in enumerate(points):
    tree.insert(Vector(p), i)
tree.balance()
inner = np.array([min(depth[j] for _, j, _ in tree.find_range(Vector(p), .008) if belt[j]) if belt[i] else depth[i]
                  for i, p in enumerate(points)])
layer = depth - inner

# Belt: the inner face is drawn onto the hips; outer layers keep their thickness through ARAP.
targets = points.copy()
contact = belt & (layer < .002)
targets[contact] = points[contact] + outward[contact] * (BELT_CLEARANCE - depth[contact])[:, None]
fixed = contact.copy()

belt_index = np.flatnonzero(contact)
belt_tree = KDTree(len(belt_index))
for k, i in enumerate(belt_index):
    belt_tree.insert(Vector(points[i]), k)
belt_tree.balance()


def follow_belt(group, reach=.03):
    # Rigid pieces ride the mean offset of the belt contact around them.
    near = set()
    for p in points[group]:
        near.update(belt_index[k] for _, k, _ in belt_tree.find_range(Vector(p), reach))
    near = list(near) or [belt_index[belt_tree.find(Vector(points[group].mean(0)))[1]]]
    return points[group] + (targets[near] - points[near]).mean(0)


rigid_groups = [medallion] + fittings
for group in rigid_groups:
    rigid = follow_belt(group)
    away = np.r_[rigid.mean(0)[:2] - anchor[:2], 0]
    away /= np.linalg.norm(away)
    for _ in range(60):
        if min(signed(p)[0] for p in rigid) >= FUR_CLEARANCE:
            break
        rigid += away * .001
    targets[group] = rigid
    fixed |= group
targets[cord] = points[cord] + (targets[medallion] - points[medallion]).mean(0)
fixed |= cord

# Fur islands with no belt contact hang from the band: pin their tops to the belt's motion.
for group in parts.get('fur', []):
    top = group & (source[:, 2] > BELT_SOURCE_BOTTOM - .03)
    for i in np.flatnonzero(top):
        k = belt_index[belt_tree.find(Vector(points[i]))[1]]
        targets[i] = points[i] + targets[k] - points[k]
    fixed |= top



stiffness = np.where(fur | cord, 0., 1.)[:, None].repeat(3, 1)
np.savez(OUTPUT / 'arap-input.npz', points=points, faces=faces, colors=stiffness, fixed=fixed, targets=targets)
subprocess.run([str(ROOT / '.venv/bin/python'), str(ROOT / 'tools/outfits/fit_female_knight_top_surface.py'),
                str(OUTPUT / 'arap-input.npz')], check=True)
arap = np.load(OUTPUT / 'arap-result.npz')
result = arap['points'].copy()

# The panels hug the thighs once the belt is drawn in. Push them out with one smooth field over
# height and angle around the pelvis, so overlapping panels move together and keep their order.
axis = np.array([0, anchor[1]])
ANGLES = 120
low = result[fur, 2].min()
HEIGHTS = int((result[fur, 2].max() - low) / .004) + 1


def radial(points):
    offset = points[:, :2] - axis
    radius = np.linalg.norm(offset, axis=1)
    return radius, offset / radius[:, None]


def shortfall(i, radius, direction):
    hit = surface.ray_cast(Vector((*(axis + direction * .3), result[i, 2])), Vector((*-direction, 0)), .3)
    return 0 if hit[0] is None else np.linalg.norm(np.array(hit[0])[:2] - axis) + FUR_CLEARANCE - radius


total = np.zeros(len(result))
for _ in range(4):
    radius, direction = radial(result)
    angle = np.arctan2(direction[:, 1], direction[:, 0])
    cell = np.c_[((angle + np.pi) / (2 * np.pi) * ANGLES).astype(int) % ANGLES,
                 np.clip(((result[:, 2] - low) / .004).astype(int), 0, HEIGHTS - 1)]
    deficit = np.zeros((ANGLES, HEIGHTS))
    for i in np.flatnonzero(fur):
        deficit[tuple(cell[i])] = max(deficit[tuple(cell[i])], shortfall(i, radius[i], direction[i]))
    if deficit.max() < .0005:
        break
    # Fur drapes: whatever pushes a panel out also holds out the panel below it.
    for h in range(HEIGHTS - 2, -1, -1):
        deficit[:, h] = np.maximum(deficit[:, h], deficit[:, h + 1])
    for _ in range(3):
        deficit = np.maximum(deficit, np.maximum.reduce([np.roll(deficit, 1, 0), np.roll(deficit, -1, 0),
                                                         np.pad(deficit, ((0, 0), (1, 0)))[:, :-1], np.pad(deficit, ((0, 0), (0, 1)))[:, 1:]]))
    for _ in range(6):
        deficit = (2 * deficit + np.roll(deficit, 1, 0) + np.roll(deficit, -1, 0)) / 4
        deficit = (2 * deficit + np.pad(deficit, ((0, 0), (1, 0)), mode='edge')[:, :-1] + np.pad(deficit, ((0, 0), (0, 1)), mode='edge')[:, 1:]) / 4
    push = np.where(fur, deficit[cell[:, 0], cell[:, 1]], 0)
    result[:, :2] += direction * push[:, None]
    total += push
push = total
print('fur pushed max', float(push.max()), 'vertices', int((push > .001).sum()), flush=True)
points_fitted = result.copy()

# The braid hangs off the front panel in the source; lay each height slice of it onto the panel.
panel = BVHTree.FromPolygons([Vector(p) for p in points_fitted], faces[fur[faces].all(1)].tolist())
cord_points = points_fitted[cord]
slices = np.round(cord_points[:, 2] / .004).astype(int)
for value in np.unique(slices):
    ring = slices == value
    rear = cord_points[ring][cord_points[ring][:, 1].argmax()]
    hit = panel.ray_cast(Vector(rear - np.array([0, .05, 0])), Vector((0, 1, 0)), .15)
    if hit[0] is not None:
        cord_points[ring, 1] += hit[0].y - .001 - rear[1]
points_fitted[cord] = cord_points

for i, point in enumerate(points_fitted):
    if any(group[i] for group in rigid_groups):
        continue
    distance, normal = signed(point)
    if distance >= .001:
        continue
    if fur[i] or cord[i]:
        # Normals under the crotch point down; a vertical shove would squash the panel flat.
        normal = np.r_[point[:2] - axis, 0]
        normal /= np.linalg.norm(normal)
        for _ in range(40):
            point = point + normal * .0005
            if signed(point)[0] >= .001:
                break
        points_fitted[i] = point
    else:
        points_fitted[i] += normal * (.001 - distance)
final_depth = np.array([signed(p)[0] for p in points_fitted])

normal_values = np.einsum('nij,nj->ni', arap['rotations'][loop_vertices], source_normals)
normal_values /= np.linalg.norm(normal_values, axis=1, keepdims=True)
for vertex, point in zip(mesh.vertices, points_fitted):
    vertex.co = point
mesh.update()


def ear_clip(loop):
    # Triangulate a small boundary loop in its best-fit plane.
    flat = points_fitted[loop] - points_fitted[loop].mean(0)
    axes = np.linalg.svd(flat)[2]
    uv = flat @ axes[:2].T
    flip = sum(uv[i - 1, 0] * uv[i, 1] - uv[i, 0] * uv[i - 1, 1] for i in range(len(uv))) < 0
    if flip:
        uv[:, 1] *= -1
    order, triangles = list(range(len(loop))), []
    while len(order) > 3:
        for k in range(len(order)):
            a, b, c = order[k - 1], order[k], order[(k + 1) % len(order)]
            ab, ac = uv[b] - uv[a], uv[c] - uv[a]
            if ab[0] * ac[1] - ab[1] * ac[0] <= 0:
                continue
            inside = False
            for o in order:
                if o in (a, b, c):
                    continue
                w = [(uv[q] - uv[o]) for q in (a, b, c)]
                signs = [w[i][0] * w[(i + 1) % 3][1] - w[i][1] * w[(i + 1) % 3][0] for i in range(3)]
                inside |= all(s > 0 for s in signs) or all(s < 0 for s in signs)
            if not inside:
                triangles.append((loop[a], loop[b], loop[c]))
                order.pop(k)
                break
        else:
            return []
    triangles.append(tuple(loop[o] for o in order))
    return [t[::-1] for t in triangles] if flip else triangles


# Tripo left small closed holes in the belt and fur (a V notch at the back showed the panties).
# Fill closed boundary loops of belt or fur only; the rings' and loops' openings are real.
edge_faces = {}
for face in faces:
    for k in range(3):
        a, b = face[k], face[(k + 1) % 3]
        edge_faces.setdefault(tuple(sorted((welded[a], welded[b]))), []).append((a, b))
boundary = {key: pairs[0] for key, pairs in edge_faces.items() if len(pairs) == 1}
following = {}
for a, b in boundary.values():
    following.setdefault(welded[b], []).append(a)
filled, visited = [], set()
for start in list(following):
    if start in visited or len(following[start]) != 1:
        continue
    loop, current = [], start
    while current not in visited and len(following.get(current, [])) == 1:
        visited.add(current)
        loop.append(following[current][0])
        current = welded[following[current][0]]
    perimeter = np.linalg.norm(points_fitted[loop] - np.roll(points_fitted[loop], -1, 0), axis=1).sum()
    if current == start and 3 <= len(loop) <= 16 and perimeter < .12 and (belt | fur)[loop].all():
        for triangle in ear_clip(loop):
            # A narrow twisted notch defeats the planar winding; face each fill away from the body.
            corners = points_fitted[list(triangle)]
            normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
            filled.append(triangle if normal[:2] @ (corners.mean(0)[:2] - axis) >= 0 else triangle[::-1])
fur_faces = faces[fur[faces].all(1)]
fur_centers = KDTree(len(fur_faces))
for k, face in enumerate(fur_faces):
    fur_centers.insert(Vector(points_fitted[face].mean(0)), k)
fur_centers.balance()
face_uvs = {}
for polygon in mesh.polygons:
    face_uvs[tuple(sorted(polygon.vertices))] = [mesh.uv_layers.active.data[l].uv[:] for l in polygon.loop_indices]


def fur_patch(triangle):
    # The notch edges are pale fur tips and belt rim; borrow the brown fur 2 cm below instead.
    k = fur_centers.find(Vector(points_fitted[list(triangle)].mean(0) - np.array([0, 0, .02])))[1]
    return face_uvs[tuple(sorted(fur_faces[k]))]


edit = bmesh.new()
edit.from_mesh(mesh)
edit.verts.ensure_lookup_table()
uv_layer = edit.loops.layers.uv.active
for triangle in filled:
    face = edit.faces.new([edit.verts[v] for v in triangle])
    face.smooth = True
    for corner, uv in zip(face.loops, fur_patch(triangle)):
        corner[uv_layer].uv = uv
edit.to_mesh(mesh)
edit.free()
vertex_normal = {v: normal_values[i] for i, v in enumerate(loop_vertices)}
normal_values = np.vstack([normal_values] + [[vertex_normal[v] for v in triangle] for triangle in filled])
faces = np.vstack([faces, np.array(filled, dtype=faces.dtype).reshape(-1, 3)])
print('filled holes with', len(filled), 'triangles', flush=True)
mesh.normals_split_custom_set(normal_values.tolist())

index = {name: i for i, name in enumerate(names)}
body_weights = np.zeros((len(body_points), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        name = body.vertex_groups[group.group].name
        if name in index:
            body_weights[vertex.index, index[name]] = group.weight
skin_vertices = np.unique([v for face in skin_faces for v in face])
skin_tree = KDTree(len(skin_vertices))
for i in skin_vertices:
    skin_tree.insert(Vector(body_points[i]), int(i))
skin_tree.balance()
weights = np.zeros((len(points_fitted), len(names)))
for i, p in enumerate(points_fitted):
    neighbors = skin_tree.find_n(Vector(p), 8)
    factors = np.array([1 / max(distance, .001) ** 2 for _, _, distance in neighbors])
    weights[i] = (body_weights[[j for _, j, _ in neighbors]] * factors[:, None]).sum(0) / factors.sum()

# Panels lean on the thighs only partly, growing with distance below the belt, so walking swings
# them instead of tearing them apart at the centre. The belt keeps the skin's own weights.
legs = [index[name] for name in names if 'Leg' in name or 'Foot' in name or 'Toe' in name]
belt_bottom = points_fitted[belt, 2].min()
cap = np.where(fur | cord, LEG_SHARE * smooth((belt_bottom - points_fitted[:, 2]) / .10), 1)
share = weights[:, legs].sum(1)
scale = np.where(share > cap, cap / np.maximum(share, 1e-9), 1)
weights[:, index['Hips']] += share * (1 - scale)
weights[:, legs] *= scale[:, None]
# Each fitting rides the bone that dominates the belt it hangs from: blending bones would bend a
# rigid ring, and a pelvis-only ring was swallowed by the thigh.
for group in rigid_groups:
    near = set()
    for p in points[group]:
        near.update(belt_index[k] for _, k, _ in belt_tree.find_range(Vector(p), .03))
    bone = (weights[sorted(near)] if near else weights[group]).mean(0).argmax()
    weights[group] = 0
    weights[group, bone] = 1
rigid_weights = [weights[group][0].copy() for group in rigid_groups]

edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
adj = [[] for _ in first]
for a, b in welded[edges]:
    if a != b:
        adj[a].append(b)
        adj[b].append(a)
locked = np.zeros(len(first), dtype=bool)
for group in rigid_groups:
    locked[welded[group]] = True
unique_weights = weights[first].copy()
for _ in range(SMOOTHING):
    updated = unique_weights.copy()
    for i, neighbors in enumerate(adj):
        if not locked[i] and neighbors:
            updated[i] = .5 * unique_weights[i] + .5 * unique_weights[neighbors].mean(0)
    unique_weights = updated
weights = unique_weights[welded]
# Snapping welded a few fitting vertices to the belt they touch; give them their piece's weights back.
for group, value in zip(rigid_groups, rigid_weights):
    weights[group] = value
fur_index = np.flatnonzero(fur)
fur_tree = KDTree(len(fur_index))
for k, i in enumerate(fur_index):
    fur_tree.insert(Vector(points_fitted[i]), k)
fur_tree.balance()
for i in np.flatnonzero(cord):
    weights[i] = weights[fur_index[fur_tree.find(Vector(points_fitted[i]))[1]]]
weights /= weights.sum(1, keepdims=True)

order = np.argsort(weights, axis=1)[:, ::-1][:, :4]
values = np.take_along_axis(weights, order, axis=1)
values[values < .02] = 0
values /= values.sum(1, keepdims=True)
order[values == 0] = 0
for name, data in [('_RIG_JOINTS', order.astype(np.float32)), ('_RIG_WEIGHTS', values.astype(np.float32))]:
    attribute = mesh.attributes.new(name, 'FLOAT_COLOR', 'POINT')
    attribute.data.foreach_set('color', data.ravel())
garment.name = mesh.name = 'bottom_female_barbarian'
bpy.ops.object.select_all(action='DESELECT')
garment.select_set(True)
bpy.context.view_layer.objects.active = garment
bpy.ops.export_scene.gltf(filepath=str(OUTPUT / 'bottom-fitted-unskinned.glb'), export_format='GLB', use_selection=True,
                         export_tangents=True, export_attributes=True, export_normals=True,
                         export_image_format='WEBP', export_image_quality=90)
np.savez(OUTPUT / 'fit-data.npz', source=source, fitted=points_fitted, faces=faces, belt=belt, fur=fur, cord=cord,
         medallion=medallion, fittings=np.any(fittings, axis=0), contact=contact, depth=final_depth,
         joints=order, weights=values, bone_names=np.array(names))
summary = lambda group: {names[i]: round(float(w), 3) for i, w in enumerate(weights[group].mean(0)) if w > .01}
report = {'date': '2026-10-15', 'source': str(SOURCE.relative_to(ROOT)),
          'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'body': str(BODY.relative_to(ROOT)), 'body_sha256': hashlib.sha256(BODY.read_bytes()).hexdigest(),
          'output_dir': str(OUTPUT.relative_to(ROOT)), 'triangles': len(faces),
          'alignment': {'scale': SCALE, 'rotation_z_degrees': -90, 'belt_center_height': BELT_HEIGHT,
                        'belt_center_depth': float(anchor[1])},
          'clearance': {'belt': BELT_CLEARANCE, 'fur': FUR_CLEARANCE},
          'parts': {'belt': int(belt.sum()), 'fur': int(fur.sum()), 'cord': int(cord.sum()),
                    'medallion': int(medallion.sum()), 'fittings': [int(g.sum()) for g in fittings]},
          'method': 'Uniform scale onto the hip section; belt inner face drawn onto skin and panties, fur pushed out only and '
                    'otherwise hung from the belt through ARAP; medallion, rings and loops ride the belt rigidly; the braid is '
                    'laid onto the front panel slice by slice.',
          'arap': {'iterations': int(arap['iterations']), 'last_maximum_vertex_step': float(arap['residual']),
                   'fixed_vertices': int(fixed.sum())},
          'rest_clearance': {'penetrating_vertices': int((final_depth < 0).sum()), 'minimum': float(final_depth.min())},
          'weights': {'belt': summary(belt), 'fur': summary(fur), 'leg_share_max': LEG_SHARE,
                      'method': 'Inverse-distance transfer from skin; panel leg influence capped by height below the belt with the '
                                'rest on Hips; the belt keeps skin weights; medallion, rings and loops rigid on the bone that dominates the belt around them; '
                                'smoothed across the welded surface; braid copies the panel under it.'},
          'no_new_api_requests': True, 'status': 'Candidate; validation pending'}
(ROOT / 'doc/assets/modular-female-barbarian-bottom-fitting-v1.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'penetrating': int((final_depth < 0).sum()), 'min_depth': float(final_depth.min()),
                  'parts': report['parts'], 'weights_fur': report['weights']['fur']}), flush=True)
