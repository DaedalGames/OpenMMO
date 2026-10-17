import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely import constrained_delaunay_triangles, set_precision
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from scipy.optimize import LinearConstraint, linprog, minimize

from lib.glb import read_glb, write_glb, view_bytes
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1'
HELMET = DIRECTORY / 'helmet_female_barbarian.glb'
HAIR = ROOT / 'assets/modular_human_female_01/hair'
SOURCES = {'bob': HAIR / 'tripo_knight_bob_v1/fitted_v1/hair_female_knight_bob.glb',
           'knight': HAIR / 'tripo_knight_v1/fitted_v1/hair_female_knight.glb'}
CENTER = np.array([0., 1.692, -.0072])
MARGIN = .00216
SECTORS = 180
CHEEK_TOP = 1.6938
CHEEK_BACK = -.0396
EAR_RESTORE_FRONT = .045
TIP_RESTORE_FRONT = .072
TIP_RESTORE_TOP = 1.5966
spec = importlib.util.spec_from_file_location('plate_io', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def opening(cheeks=True):
    doc, raw = read_glb(HELMET)
    primitive = doc['meshes'][0]['primitives'][0]
    points = accessor(doc, raw, primitive['attributes']['POSITION']).astype(float) - CENTER
    faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    shell = trimesh.Trimesh(points, faces, process=False)
    if cheeks:
        triangles = shell.triangles
    else:
        crown = shell.slice_plane([0, CHEEK_TOP - CENTER[1], 0], [0, 1, 0])
        rear = shell.slice_plane([0, 0, CHEEK_BACK - CENTER[2]], [0, 0, -1])
        triangles = np.vstack([crown.triangles, rear.triangles])
    angles = np.arange(SECTORS * 8) * 2 * np.pi / (SECTORS * 8)
    ratios = []
    for angle in angles:
        radial = np.array([np.sin(angle), 0., np.cos(angle)])
        normal = np.cross(radial, [0, 1, 0])
        values = triangles @ normal
        candidates = []
        for edge in range(3):
            a, b = triangles[:, edge], triangles[:, (edge + 1) % 3]
            va, vb = values[:, edge], values[:, (edge + 1) % 3]
            valid = (va * vb <= 0) & (abs(va - vb) > 1.8e-12)
            hit = a[valid] + (b - a)[valid] * (va[valid] / (va - vb)[valid])[:, None]
            radius = hit @ radial
            candidates.extend((hit[radius > .027, 1] / radius[radius > .027]).tolist())
        if not candidates:
            raise ValueError('Helmet opening has an uncovered radial sector')
        ratios.append(min(candidates))
    ratios = np.array(ratios)
    profile = np.array([min(ratios[(np.arange(i * 8 - 8, i * 8 + 9)) % len(ratios)]) for i in range(SECTORS)])
    angles = np.arange(SECTORS + 1) * 2 * np.pi / SECTORS
    radial = np.column_stack([np.sin(angles), np.cos(angles)])
    heights = np.r_[profile, profile[0]]
    slopes = np.array([np.linalg.solve(radial[i:i + 2], heights[i:i + 2]) for i in range(SECTORS)])
    return radial, slopes


def clip(polygon, values):
    result = []
    for i, point in enumerate(polygon):
        j = (i + 1) % len(polygon)
        if values[i] >= -1.8e-12:
            result.append(point)
        if (values[i] >= 0) != (values[j] >= 0):
            result.append(point + (polygon[j] - point) * values[i] / (values[i] - values[j]))
    return np.array(result)


def fit_behind_cheeks(points, faces, normals, tangents=None):
    doc, raw = read_glb(HELMET)
    primitive = doc['meshes'][0]['primitives'][0]
    helmet = accessor(doc, raw, primitive['attributes']['POSITION'])
    helmet_faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    before = points.copy()
    for side in [-1, 1]:
        guard = helmet_faces[((helmet[helmet_faces, 0] * side > .036).all(1))
                             & (helmet[helmet_faces, 1].mean(1) < CHEEK_TOP + .0054)
                             & (helmet[helmet_faces, 2].mean(1) > CHEEK_BACK)]
        triangles = helmet[guard].astype(float)
        polygons = [Polygon(triangle[:, 1:]) for triangle in triangles]
        valid = [i for i, polygon in enumerate(polygons) if polygon.area > 3.24e-12]
        triangles = triangles[valid]
        polygons = [polygons[i] for i in valid]
        tree = STRtree(polygons)
        low = np.floor((triangles[:, :, 1:].min((0, 1)) - .0288) / .0144) * .0144
        size = np.ceil((triangles[:, :, 1:].max((0, 1)) + .0288 - low) / .0144).astype(int) + 1
        lookup = np.full(tuple(size), -1, dtype=int)
        lookup[1:-1, 1:-1] = np.arange(np.prod(size - 2)).reshape(tuple(size - 2))
        coordinates = (points[:, 1:] - low) / .0144
        cells = np.floor(coordinates).astype(int)
        fraction = coordinates - cells
        basis = np.zeros((len(points), int(np.prod(size - 2))))
        for dy, dz in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            nodes = cells + [dy, dz]
            inside = ((nodes >= 0) & (nodes < size)).all(1) & (points[:, 0] * side > .0018)
            ids = np.flatnonzero(inside)
            variables = lookup[nodes[ids, 0], nodes[ids, 1]]
            keep = variables >= 0
            share = np.prod(np.where(np.array([dy, dz]), fraction[ids], 1 - fraction[ids]), axis=1)
            basis[ids[keep], variables[keep]] = share[keep]
        rows, deficits = [], []
        candidates = faces[(points[faces, 0] * side > .0018).all(1)]
        for face in candidates:
            triangle = points[face].astype(float)
            matrix = (triangle[1:, 1:] - triangle[0, 1:]).T
            if abs(np.linalg.det(matrix)) < 3.24e-12:
                continue
            polygon = Polygon(triangle[:, 1:])
            for index in tree.query(polygon, predicate='intersects'):
                overlap = polygon.intersection(polygons[index])
                if overlap.area < 3.24e-12:
                    continue
                xy = np.array(overlap.exterior.coords)[:-1]
                uv = np.linalg.solve(matrix, (xy - triangle[0, 1:]).T).T
                bary = np.column_stack([1 - uv.sum(1), uv])
                wall = triangles[index]
                uv = np.linalg.solve((wall[1:, 1:] - wall[0, 1:]).T, (xy - wall[0, 1:]).T).T
                wall_x = wall[0, 0] + uv @ (wall[1:, 0] - wall[0, 0])
                rows.extend((bary * triangle[:, 0] * side) @ basis[face] * 1000)
                deficits.extend((bary @ triangle[:, 0] * side - wall_x * side + MARGIN) * 1000)
        if not rows:
            continue
        matrix, deficit = np.array(rows), np.array(deficits)
        initial = linprog(np.ones(basis.shape[1]), A_ub=-matrix, b_ub=-deficit, bounds=(0, .75), method='highs')
        if not initial.success:
            raise ValueError('Restored hair cannot fit behind cheek guards')
        result = minimize(lambda value: .5 * value @ value, initial.x, jac=lambda value: value,
                          constraints=LinearConstraint(matrix, deficit, np.inf), bounds=[(0, .75)] * basis.shape[1],
                          method='SLSQP', options={'ftol': 1e-9, 'maxiter': 300})
        if not result.success or (matrix @ result.x - deficit).min() < -1.8e-5:
            raise ValueError('Cheek guard fit did not converge')
        points[:, 0] *= 1 - basis @ result.x
    moved = np.linalg.norm(points - before, axis=1) > 1.8e-8
    if moved.any():
        geometric = trimesh.Trimesh(points, faces, process=False).vertex_normals
        normals[moved] = geometric[moved]
        if tangents is not None:
            tangents[moved, :3] -= (tangents[moved, :3] * normals[moved]).sum(1)[:, None] * normals[moved]
            tangents[moved, :3] /= np.linalg.norm(tangents[moved, :3], axis=1, keepdims=True)
    return {'vertices': int(moved.sum()), 'maximum_displacement': float(np.linalg.norm(points - before, axis=1).max())}


def trim(source, output, radial, slopes, cheek_slopes):
    doc, original = read_glb(source)
    raw = bytearray(original)
    images = [view_bytes(doc, original, image['bufferView']) for image in doc['images']]
    records = []
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            attrs = {name: accessor(doc, original, index) for name, index in primitive['attributes'].items()}
            points = attrs['POSITION'].astype(float)
            faces = accessor(doc, original, primitive['indices']).reshape(-1, 3)
            local = points - CENTER
            result, bary_rows, source_rows = [], [], []
            cache = {}

            def vertex(face, bary):
                bary = bary.clip(0, 1)
                bary /= bary.sum()
                key = tuple(sorted((int(index), round(float(value), 10)) for index, value in zip(face, bary) if value > 1e-9))
                if key not in cache:
                    cache[key] = len(bary_rows)
                    bary_rows.append(bary)
                    source_rows.append(face)
                return cache[key]

            for face in faces:
                triangle = local[face]
                theta = np.unwrap(np.arctan2(triangle[:, 0], triangle[:, 2]))
                start = int(np.floor(theta.min() * SECTORS / (2 * np.pi)))
                end = int(np.floor(theta.max() * SECTORS / (2 * np.pi)))
                sectors = np.arange(start, end + 1) % SECTORS
                heights = slopes[sectors] @ triangle[:, [0, 2]].T - triangle[:, 1] - MARGIN
                cheek_heights = cheek_slopes[sectors] @ triangle[:, [0, 2]].T - triangle[:, 1] - MARGIN
                restored = points[face, 2].max() <= EAR_RESTORE_FRONT or (points[face, 2].max() <= TIP_RESTORE_FRONT and points[face, 1].max() <= TIP_RESTORE_TOP)
                if cheek_heights.min() >= 0 or (heights.min() >= 0 and restored):
                    result.append([vertex(face, bary) for bary in np.eye(3)])
                    continue
                if heights.max() < 0:
                    continue
                pieces = []
                for sector in sectors:
                    polygon = np.eye(3)
                    a, b = radial[sector:sector + 2]
                    for normal in [np.array([a[1], 0, -a[0]]), np.array([-b[1], 0, b[0]])]:
                        polygon = clip(polygon, (polygon @ triangle) @ normal)
                        if len(polygon) < 3:
                            break
                    if len(polygon) < 3:
                        continue
                    for field, restore in [(cheek_slopes, False), (slopes, True)]:
                        values = (polygon @ triangle)[:, [0, 2]] @ field[sector] - (polygon @ triangle)[:, 1] - MARGIN
                        part = clip(polygon, values)
                        if not restore:
                            if len(part) >= 3:
                                pieces.append(Polygon(part[:, 1:]))
                            continue
                        for front, top in [(EAR_RESTORE_FRONT, None), (TIP_RESTORE_FRONT, TIP_RESTORE_TOP)]:
                            restored = clip(part, front - (part @ points[face])[:, 2]) if len(part) >= 3 else part
                            if top is not None and len(restored) >= 3:
                                restored = clip(restored, top - (restored @ points[face])[:, 1])
                            if len(restored) >= 3:
                                pieces.append(Polygon(restored[:, 1:]))
                if pieces:
                    region = set_precision(unary_union(pieces), 1e-10).simplify(1e-9, preserve_topology=True)
                    for piece in constrained_delaunay_triangles(region).geoms:
                        xy = np.array(piece.exterior.coords)[:3]
                        bary = np.column_stack([1 - xy.sum(1), xy])
                        if np.linalg.det(bary[1:, 1:] - bary[0, 1:]) < 0:
                            bary = bary[::-1]
                        xyz = bary @ points[face]
                        if np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])) > 3.24e-12:
                            result.append([vertex(face, row) for row in bary])
            bary = np.array(bary_rows)
            parents = np.array(source_rows)
            converted = {}
            for name, values in attrs.items():
                if name in ['JOINTS_0', 'WEIGHTS_0']:
                    continue
                data = np.einsum('nk,nkj->nj', bary, values[parents])
                if name in ['NORMAL', 'TANGENT']:
                    data[:, :3] /= np.linalg.norm(data[:, :3], axis=1, keepdims=True)
                if name == 'TANGENT':
                    data[:, 3] = np.where(data[:, 3] >= 0, 1, -1)
                converted[name] = data.astype(np.float32)
            joints, weights = attrs['JOINTS_0'], attrs['WEIGHTS_0']
            shares = np.zeros((len(bary), len(doc['skins'][0]['joints'])))
            np.add.at(shares, (np.arange(len(bary))[:, None, None], joints[parents]), bary[:, :, None] * weights[parents])
            bones = np.argsort(-shares, axis=1)[:, :4]
            converted['JOINTS_0'] = bones.astype(np.uint16)
            converted['WEIGHTS_0'] = np.take_along_axis(shares, bones, axis=1).astype(np.float32)
            converted['WEIGHTS_0'] /= converted['WEIGHTS_0'].sum(1, keepdims=True)
            cheek_fit = fit_behind_cheeks(converted['POSITION'], np.array(result), converted['NORMAL'], converted.get('TANGENT'))
            primitive['attributes'] = {name: add_accessor(doc, raw, values, 'VEC' + str(values.shape[1]),
                                                       5123 if name == 'JOINTS_0' else 5126)
                                       for name, values in converted.items()}
            primitive['indices'] = add_accessor(doc, raw, np.array(result, dtype=np.uint32).reshape(-1, 1), 'SCALAR', 5125)
            records.append({'mesh': mesh['name'], 'original_triangles': len(faces), 'triangles': len(result), 'vertices': len(bary),
                            'cheek_fit': cheek_fit})
    raw = io.compact(doc, raw)
    assert images == [view_bytes(doc, raw, image['bufferView']) for image in doc['images']]
    write_glb(output, doc, raw)
    return {'source': str(source.relative_to(ROOT)), 'source_sha256': digest(source),
            'output': str(output.relative_to(ROOT)), 'output_sha256': digest(output), 'meshes': records}


def main():
    radial, cheek_slopes = opening()
    _, slopes = opening(cheeks=False)
    report = {'helmet_sha256': digest(HELMET), 'center': CENTER.tolist(), 'margin_m': MARGIN,
              'sectors': SECTORS, 'ear_restoration': {'cheek_top_y': CHEEK_TOP, 'cheek_back_z': CHEEK_BACK,
              'restore_front_z': EAR_RESTORE_FRONT, 'tip_restore_front_z': TIP_RESTORE_FRONT,
              'tip_restore_top_y': TIP_RESTORE_TOP, 'lateral_fit_margin': MARGIN},
              'method': 'Keep the full-shell cut at the front. Restore hair behind the ears below a separate crown/back-rim '
              'curtain, retaining the lower cheek-tip strand farther forward. Fit inside the cheek guards using exact projected triangle overlap constraints and a shared '
              'bilinear lateral-scale field with a fixed zero boundary. '
              'Interpolate cut vertices, UVs, normals, tangents and skinning; preserve original embedded textures.', 'hair': {}}
    for name, source in SOURCES.items():
        report['hair'][name] = trim(source, DIRECTORY / f'hair_{name}_barbarian_helmet.glb', radial, slopes, cheek_slopes)
    (DIRECTORY / 'hair-trim.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
