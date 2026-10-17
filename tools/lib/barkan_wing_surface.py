import json
import sys
from pathlib import Path

import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon
from shapely.ops import unary_union


def main(source, destination):
    data = json.loads(Path(source).read_text())
    cutters = unary_union([Polygon(record['outline_yz']) for record in data['cutters']])
    output = []
    changed = 0
    for face in data['faces']:
        attributes = np.asarray(face['attributes'])
        world = np.asarray(face['world'])
        center = world.mean(axis=0)
        if center[0] >= -.015 or abs(center[1]) <= .23 or center[2] <= .21:
            output.append(attributes.tolist())
            continue
        projected = world[:, 1:]
        polygon = Polygon(projected)
        if polygon.area < 1e-15 or not cutters.intersects(polygon):
            output.append(attributes.tolist())
            continue
        remaining = polygon.difference(cutters)
        if remaining.equals(polygon):
            output.append(attributes.tolist())
            continue
        changed += 1
        basis = (projected[1:] - projected[0]).T
        determinant = np.linalg.det(basis)
        for triangle in constrained_delaunay_triangles(remaining).geoms:
            coordinates = np.asarray(triangle.exterior.coords[:3])
            if triangle.area < 1e-15:
                continue
            weights = np.linalg.solve(basis, (coordinates - projected[0]).T).T
            weights = np.column_stack([1 - weights.sum(axis=1), weights])
            values = weights @ attributes
            if np.linalg.det((coordinates[1:] - coordinates[0]).T) * determinant < 0:
                values = values[[0, 2, 1]]
            output.append(values.tolist())
    Path(destination).write_text(json.dumps({'faces': output, 'changed_source_faces': changed}))


if __name__ == '__main__':
    main(*sys.argv[1:])
