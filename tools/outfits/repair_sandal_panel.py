import numpy as np
from shapely import constrained_delaunay_triangles, set_precision
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


def repair_panel(points, faces, face_ids, uv, joints, weights, source, frame, bone_count, leather_bounds):
    old_points = points.copy()
    old_joints, old_weights = joints.copy(), weights.copy()
    patch = faces[face_ids].copy()
    local = old_points @ frame
    triangles = local[patch]
    polygon = set_precision(unary_union([Polygon(triangle[:, :2]) for triangle in triangles]), 1.8e-9)
    if polygon.geom_type != 'Polygon':
        raise ValueError('Sandal side panel is disconnected')
    polygon = Polygon(polygon.exterior, [ring for ring in polygon.interiors if Polygon(ring).area > 3.24e-12])
    rebuilt = [np.array(triangle.exterior.coords)[:3] for triangle in constrained_delaunay_triangles(polygon).geoms
               if triangle.area > 3.24e-14]
    if len(rebuilt) > len(face_ids):
        raise ValueError('Sandal panel exceeds its triangle budget')
    if (len(face_ids) - len(rebuilt)) % 2:
        boundary = np.array(polygon.exterior.coords)[:-1]
        lengths = np.linalg.norm(np.roll(boundary, -1, axis=0) - boundary, axis=1)
        start = lengths.argmax()
        a, b = boundary[start], boundary[(start + 1) % len(boundary)]
        for index, triangle in enumerate(rebuilt):
            for edge in range(3):
                u, v = triangle[edge], triangle[(edge + 1) % 3]
                if min(np.linalg.norm(u - a) + np.linalg.norm(v - b),
                       np.linalg.norm(u - b) + np.linalg.norm(v - a)) < 1.8e-8:
                    other = triangle[(edge + 2) % 3]
                    middle = (u + v) / 2
                    rebuilt[index:index + 1] = [np.array([u, middle, other]), np.array([middle, v, other])]
                    break
            else:
                continue
            break
    while len(rebuilt) < len(face_ids):
        index = np.argmax([abs(np.linalg.det(triangle[1:] - triangle[0])) for triangle in rebuilt])
        triangle = rebuilt.pop(index)
        center = triangle.mean(0)
        rebuilt.extend([np.array([triangle[edge], triangle[(edge + 1) % 3], center]) for edge in range(3)])
    vertices = np.unique(patch)
    elsewhere = np.unique(faces[~np.isin(np.arange(len(faces)), face_ids)])
    private = set(np.setdiff1d(vertices, elsewhere).tolist())
    mapped, allocated, rebuilt_indices = {}, set(), []
    source_override = source.copy()
    orientation = np.sign(np.median(np.linalg.det(triangles[:, 1:, :2] - triangles[:, :1, :2])))
    for triangle in rebuilt:
        indices = []
        for xy in triangle:
            key = tuple(np.round(xy, 9))
            if key not in mapped:
                nearby = vertices[np.linalg.norm(local[vertices, :2] - xy, axis=1) < 3.6e-8]
                pool = sorted(private - allocated)
                if not pool:
                    raise ValueError('Sandal panel has no private vertex slots')
                vertex = pool[0]
                if len(nearby):
                    reference = max(nearby, key=lambda value: local[value, 2])
                    points[vertex] = old_points[reference]
                    joints[vertex] = old_joints[reference]
                    weights[vertex] = old_weights[reference]
                    source_override[vertex] = source[reference]
                else:
                    candidates = []
                    for parent, old in enumerate(triangles):
                        matrix = (old[1:, :2] - old[0, :2]).T
                        if abs(np.linalg.det(matrix)) < 3.24e-14:
                            continue
                        value = np.linalg.solve(matrix, xy - old[0, :2])
                        bary = np.r_[1 - value.sum(), value]
                        if bary.min() >= -1e-6:
                            candidates.append((parent, bary.clip(0, 1)))
                    if not candidates:
                        raise ValueError('Sandal panel vertex is outside its original footprint')
                    parent, bary = max(candidates, key=lambda entry: entry[1] @ triangles[entry[0], :, 2])
                    bary /= bary.sum()
                    corners = patch[parent]
                    height = max(value @ triangles[index, :, 2] for index, value in candidates)
                    boundary_distance = polygon.boundary.distance(Point(xy))
                    height += .0009 * min(1., boundary_distance / .0036)
                    points[vertex] = np.r_[xy, height] @ frame.T
                    source_override[vertex] = bary @ source[corners]
                    shares = np.zeros(bone_count)
                    np.add.at(shares, old_joints[corners].ravel(), (bary[:, None] * old_weights[corners]).ravel())
                    bones = np.argsort(-shares)[:4]
                    joints[vertex] = bones
                    weights[vertex] = shares[bones] / shares[bones].sum()
                bounds = np.array(polygon.bounds).reshape(2, 2)
                fraction = (xy - bounds[0]) / (bounds[1] - bounds[0])
                uv[vertex] = leather_bounds[0] + fraction * (leather_bounds[1] - leather_bounds[0])
                allocated.add(vertex)
                mapped[key] = vertex
            indices.append(mapped[key])
        area = np.linalg.det(triangle[1:] - triangle[0])
        rebuilt_indices.append(indices if np.sign(area) == orientation else indices[::-1])
    faces[face_ids] = rebuilt_indices
    changed = np.zeros(len(points), dtype=bool)
    changed[np.unique(np.r_[patch.ravel(), np.array(rebuilt_indices).ravel()])] = True
    return source_override, changed, {
        'faces': len(face_ids), 'footprint_area': float(polygon.area),
        'allocated_vertices': len(allocated), 'repurposed_private_vertices': int(np.any(points != old_points, axis=1).sum()),
        'triangle_overlap_area': float(sum(Polygon(triangle).area for triangle in rebuilt) - polygon.area),
    }
