"""Project the Tripo PBR onto continuous dorsal and palmar hand charts."""
from io import BytesIO

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from lib.glb import view_bytes


def bake(doc, raw, points, faces, uv, inverse, low, high, output):
    size = 1024
    maps = [np.asarray(Image.open(BytesIO(view_bytes(doc, raw, im['bufferView']))).convert('RGB')) for im in doc['images']]
    atlases = []
    for image, fill in zip(maps, [(0, 0, 0), (255, 180, 0), (128, 128, 255)]):
        atlas = Image.new('RGB', (4096, 2048), fill)
        atlas.paste(Image.fromarray(image).resize((2048, 2048), Image.Resampling.LANCZOS), (0, 0))
        atlases.append(atlas)
    planar = points[:, [2, 1]] * [-1, 1]
    triangles = planar[faces]
    edges = np.stack([triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]], axis=-1)
    inverses = np.linalg.pinv(edges)
    tree = cKDTree(triangles.mean(1))
    geometry = points[faces]
    ab, ac = geometry[:, 1] - geometry[:, 0], geometry[:, 2] - geometry[:, 0]
    normals = np.cross(ab, ac)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    tex = uv[faces]
    du, dv = tex[:, 1] - tex[:, 0], tex[:, 2] - tex[:, 0]
    determinant = du[:, 0] * dv[:, 1] - du[:, 1] * dv[:, 0]
    safe = np.where(abs(determinant) > 1e-10, determinant, 1)
    tangent = (ab * dv[:, 1, None] - ac * du[:, 1, None]) / safe[:, None]
    bitangent = (ac * du[:, 0, None] - ab * dv[:, 0, None]) / safe[:, None]
    tangent -= normals * np.sum(tangent * normals, axis=1, keepdims=True)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-10)
    handedness = np.where(np.sum(np.cross(normals, tangent) * bitangent, axis=1) > 0, 1, -1)
    bitangent = np.cross(normals, tangent) * handedness[:, None]
    colors = [[np.empty((size * size, 3), dtype=np.uint8) for _ in maps] for _ in range(2)]

    def sample(image, coordinates):
        pixel = np.clip(coordinates, 0, 1) * [image.shape[1] - 1, image.shape[0] - 1]
        first = pixel.astype(int)
        second = np.minimum(first + 1, [image.shape[1] - 1, image.shape[0] - 1])
        blend = pixel - first
        upper = image[first[:, 1], first[:, 0]] * (1 - blend[:, 0, None]) + image[first[:, 1], second[:, 0]] * blend[:, 0, None]
        lower = image[second[:, 1], first[:, 0]] * (1 - blend[:, 0, None]) + image[second[:, 1], second[:, 0]] * blend[:, 0, None]
        return upper * (1 - blend[:, 1, None]) + lower * blend[:, 1, None]

    for start in range(0, size * size, 4096):
        indices = np.arange(start, min(start + 4096, size * size))
        grid = np.column_stack([(indices % size + .5) / size, (indices // size + .5) / size])
        queries = inverse(low + grid * (high - low))
        near = tree.query(queries, k=48)[1]
        coordinates = np.einsum('nkij,nkj->nki', inverses[near], queries[:, None] - triangles[near, 0])
        bary = np.concatenate([1 - coordinates.sum(-1, keepdims=True), coordinates], axis=-1)
        depth = np.sum(bary * geometry[near, :, 0], axis=-1)
        hit = bary.min(-1) >= -1e-5
        for chart in range(2):
            scores = np.where(hit, depth * (1 if chart == 0 else -1), -np.inf)
            selected = scores.argmax(1)
            selected[~hit.any(1)] = 0
            rows = np.arange(len(indices))
            chosen = near[rows, selected]
            weights = np.clip(bary[rows, selected], 0, 1)
            weights /= weights.sum(1, keepdims=True)
            coords = (uv[faces[chosen]] * weights[..., None]).sum(1)
            for i in [0, 1]:
                colors[chart][i][indices] = sample(maps[i], coords).clip(0, 255).astype(np.uint8)
            n = sample(maps[2], coords) / 127.5 - 1
            world = tangent[chosen] * n[:, 0, None] + bitangent[chosen] * n[:, 1, None] + normals[chosen] * n[:, 2, None]
            destination = np.array([1. if chart == 0 else -1., 0, 0])
            axis = np.cross(normals[chosen], destination)
            cosine = normals[chosen] @ destination
            rotated = world + np.cross(axis, world) + np.cross(axis, np.cross(axis, world)) / np.maximum(1 + cosine[:, None], 1e-6)
            encoded = np.column_stack([-rotated[:, 2], rotated[:, 1], rotated @ destination])
            encoded[:, 2] = np.maximum(encoded[:, 2], .05)
            encoded /= np.maximum(np.linalg.norm(encoded, axis=1, keepdims=True), 1e-10)
            colors[chart][2][indices] = ((encoded + 1) * 127.5).clip(0, 255).astype(np.uint8)
    for chart in range(2):
        for i, atlas in enumerate(atlases):
            atlas.paste(Image.fromarray(colors[chart][i].reshape(size, size, 3)), (2048, chart * size))
    result = []
    output.mkdir(exist_ok=True)
    for name, atlas in zip(['base-color', 'orm', 'normal'], atlases):
        data = BytesIO()
        atlas.save(data, format='PNG')
        contents = data.getvalue()
        (output / (name + '.png')).write_bytes(contents)
        result.append(contents)
    return result
