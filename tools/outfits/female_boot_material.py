import copy
from io import BytesIO

import numpy as np
from PIL import Image

from lib.glb import view_bytes
from lib.glb_accessors import accessor, add_accessor


def match_cuff_leather(doc, binary, matrices):
    source = doc['meshes'][0]['primitives'][0]
    attrs = source['attributes']
    points = accessor(doc, binary, attrs['POSITION'])
    joints = accessor(doc, binary, attrs['JOINTS_0'])
    weights = accessor(doc, binary, attrs['WEIGHTS_0'])
    deformation = np.einsum('nk,nkij->nij', weights, matrices[joints])
    points = np.einsum('nij,nj->ni', deformation, np.c_[points, np.ones(len(points))])[:, :3]
    faces = accessor(doc, binary, source['indices']).reshape(-1, 3)
    uv = accessor(doc, binary, attrs['TEXCOORD_0'])
    material = doc['materials'][source['material']]['pbrMetallicRoughness']
    image_index = doc['textures'][material['baseColorTexture']['index']]['source']
    pixels = np.asarray(Image.open(BytesIO(view_bytes(doc, binary, doc['images'][image_index]['bufferView']))).convert('RGB'))
    barycentric = np.array([
        [1 - u - v, u, v] for u in np.linspace(.08, .84, 6)
        for v in np.linspace(.08, .84, 6) if u + v < .95
    ])
    samples = np.einsum('sc,fcd->fsd', barycentric, uv[faces])
    coords = np.rint(samples * [pixels.shape[1] - 1, pixels.shape[0] - 1]).astype(int)
    rgb = pixels[coords[:, :, 1], coords[:, :, 0]].astype(float)
    dark = (rgb.mean(2) < 90) & ((rgb[:, :, 0] - rgb[:, :, 2]) < 23)
    selected = (points[faces][:, :, 1].min(1) > .36) & (dark.mean(1) > .65)
    assert selected.sum() == 106, 'Review cuff material selection after source changes'
    leather = next(i for i, value in enumerate(doc['materials']) if value['name'] == 'concept_knee_leather')
    projection = np.column_stack([.465 + points[:, 2] * .65, .255 + (.49 - points[:, 1]) * 1.05])
    for mesh in doc['meshes']:
        original = mesh['primitives'][0]
        replacement = copy.deepcopy(original)
        triangles = accessor(doc, binary, original['indices']).reshape(-1, 3)
        used, remapped = np.unique(triangles[selected], return_inverse=True)
        original['indices'] = add_accessor(doc, binary, triangles[~selected].reshape(-1, 1), 'SCALAR', 5125)
        replacement['indices'] = add_accessor(doc, binary, remapped.reshape(-1, 1), 'SCALAR', 5125)
        for name, index in original['attributes'].items():
            metadata = doc['accessors'][index]
            values = projection if name == 'TEXCOORD_0' else accessor(doc, binary, index)
            replacement['attributes'][name] = add_accessor(doc, binary, values[used], metadata['type'], metadata['componentType'])
        replacement['material'] = leather
        replacement['extras'] = {'part': 'upper_cuff_navy_leather'}
        mesh['primitives'].append(replacement)
    return {
        'reference': 'assets/items/female_knight_boots/references/user-navy-cuff-material.png',
        'material': doc['materials'][leather]['name'],
        'triangles_per_boot': int(selected.sum()),
        'method': 'Reuse the knee leather material and project its navy region onto the dark upper cuff faces',
        'geometry_weights_and_embedded_images_unchanged': True,
    }
