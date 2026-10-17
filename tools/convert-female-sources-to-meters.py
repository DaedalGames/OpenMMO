"""One-off migration (2026-10-17): scale the modular female sources from rig height 1 to meters.

Patches float bytes in place so accessor/bufferView layout stays byte-identical for the GLB tools.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from lib.glb import read_glb, write_glb

ROOT = Path(__file__).resolve().parents[1]
METERS = 1.8
# Pre-migration hashes; a second run must not scale twice.
GLBS = {
    'assets/modular_human_female_01/rig_v1/female-base.glb': '9564457e8b23275aaf8cd0ff74c318baa4bbfa6b1c8afe608037cf7f40cf0982',
    'assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/hair_female_knight_bob.glb': '2ecb64f5217e559bf8ca8d440d02226892c087b5acacc32f6f69a3d22fa02f75',
    'assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/hair_female_knight.glb': '2f8d3f21d7218039c24ae06b69a16c325260ebe3dc7b917a6eec245f3173653b',
    'assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/hair-fitted-unskinned.glb': 'c194861c20eb4bdbc9bab9886b43224b743a96fd3b9e8aba1cd60785f88663b5',
    'assets/modular_human_female_01/hair/tripo_knight_v1/fitted_v1/hair-fitted-unskinned.glb': 'f69866469667abfa3d0f278cff33571ecf9ff718420a09f3913f65a70e93d6f0',
    'assets/items/female_knight_top/tripo_v1/fitted_v3/top_female_knight.glb': 'c59793ce0e545f7eb1615bc75478469eaa8c803c1d88269509e11b5aa3f0fb60',
    'assets/items/female_knight_bottom/tripo_v1/fitted_v42/bottom_female_knight.glb': '19bcab0f877c9117ec9558b9fe0a87c3ead55e4452894738f6b43512b10e3fb6',
    'assets/items/female_knight_boots/fitted_v5/boots_female_knight.glb': '853c04f9a7e60e540f17f76ceff1b5fada1a4411c8e2899652bd0e33c2fe6bc6',
    'assets/items/female_knight_boots/fitted_v4/boots_female_knight.glb': 'e6832aad3c3a6936d70a92725c11979ac8c09fabe45bd79458ee7368cfcb8b45',
    'assets/items/female_knight_gloves/tripo_v1/fitted_v3/gloves_female_knight.glb': '167517380ef102d36cfd258bb7feb0b27811f7cb7596304f71c6f368f3fd7c27',
    'assets/items/female_knight_helmet/tripo_v1/fitted_v1/helmet_female_knight.glb': '6bc22f6f1a1b086edcbac38c1167729050c34cf04a7d3ef49d428fe5625a2c35',
    'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair_bob_barbarian_helmet.glb': 'fc351d8e892285f79b416f789e9f3f0daf68af576b1b925d97101d76ade8978f',
    'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair_knight_barbarian_helmet.glb': '7d241179ff6fc7eedc73075fc9366e493e0e7ba2580d67273c33784bab955729',
    'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/helmet_female_barbarian.glb': 'ae8c47f1a44b6b0cdafcd0a844dc6a2d0735a8b8e522832ee320a19cde37a63b',
    'assets/items/female_barbarian_top/tripo_v1/fitted_v1/top_female_barbarian.glb': 'a4e1fcc82855ce611e3c7c702d2c7d4cbd2b144fedf7acb1f4ff4a90f5ee29b9',
    'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb': 'e6259943201a9778efc4204b689f1001550bdc0947058524a21403719fc3cb39',
    'assets/items/female_barbarian_boots/tripo_v1/fitted_v3/boots_female_barbarian.glb': '4c1bc190650987b5af1b7e87a232b225761a9e4202c4bd032146d2178486ccb4',
    'assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/gloves_female_barbarian.glb': '1a35d963b864c8f7efd301820c1952d579b7ec24ba8213f4aed6c8da7546dcf1',
}
BASE = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scaled(values):
    return (np.asarray(values, dtype=np.float64) * METERS).tolist()


def scale_glb(path):
    gltf, binary = read_glb(path)
    binary = bytearray(binary)
    accessors = {}
    for mesh in gltf['meshes']:
        for primitive in mesh['primitives']:
            for attributes in [primitive['attributes'], *primitive.get('targets', [])]:
                if 'POSITION' in attributes:
                    accessors[attributes['POSITION']] = False
    for skin in gltf.get('skins', []):
        if 'inverseBindMatrices' in skin:
            accessors[skin['inverseBindMatrices']] = True
    for animation in gltf.get('animations', []):
        for channel in animation['channels']:
            if channel['target']['path'] == 'translation':
                accessors[animation['samplers'][channel['sampler']]['output']] = False
    sizes = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    for index, matrix in accessors.items():
        accessor = gltf['accessors'][index]
        view = gltf['bufferViews'][accessor['bufferView']]
        assert accessor['componentType'] == 5126 and 'byteStride' not in view and 'sparse' not in accessor
        width = sizes[accessor['type']]
        start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        end = start + accessor['count'] * width * 4
        values = np.frombuffer(binary[start:end], dtype='<f4').reshape(-1, width).astype(np.float64)
        if matrix:
            values[:, 12:15] *= METERS
        else:
            values *= METERS
        values = values.astype('<f4')
        binary[start:end] = values.tobytes()
        if 'min' in accessor:
            accessor['min'] = values.min(0).astype(np.float64).tolist()
            accessor['max'] = values.max(0).astype(np.float64).tolist()
    for node in gltf['nodes']:
        if 'translation' in node:
            node['translation'] = scaled(node['translation'])
        pelt = node.get('extras', {}).get('pelt_physics')
        if pelt:
            pelt['pivot'] = scaled(pelt['pivot'])
            pelt['length'] = pelt['length'] * METERS
            if 'attachment_depth' in pelt:
                pelt['attachment_depth'] = pelt['attachment_depth'] * METERS
            for collider in pelt['colliders']:
                collider['center'] = scaled(collider['center'])
                collider['radii'] = scaled(collider['radii'])
            # Keeps pelt-rig's built-in distances and forces at the scale they were tuned at.
            pelt['unit'] = METERS
    for scene in gltf['scenes']:
        if 'heel_pose' in scene.get('extras', {}):
            scale_heel_pose(scene['extras']['heel_pose'])
    temporary = path.with_name(path.name + '.tmp')
    write_glb(temporary, gltf, bytes(binary))
    temporary.replace(path)


def scale_heel_pose(pose):
    for key in ['rest_foot_positions', 'posed_foot_positions_before_root_lift']:
        pose[key] = {name: scaled(value) for name, value in pose[key].items()}
    for key in ['foot_geometry_vertical_shift', 'body_toe_floor_before_root_lift']:
        if key in pose:
            pose[key] *= METERS


def edit_json(path, change):
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def edit_npz(path, keys):
    with np.load(path) as archive:
        arrays = {key: archive[key] for key in archive.files}
    for key in keys:
        arrays[key] = (arrays[key].astype(np.float64) * METERS).astype(arrays[key].dtype)
    temporary = path.with_name(path.name + '.tmp.npz')
    np.savez(temporary, **arrays)
    temporary.replace(path)


def knight_boots_fitting(data):
    data['posed_floor_offset'] *= METERS
    scale_heel_pose(data['heel_pose'])
    for key in ['cuff_clearance_height_ramp', 'cuff_inner_back_height_band']:
        data[key] = scaled(data[key])


def knight_boots_fit_v4(data):
    knight_boots_fitting(data)
    for section in data['section_clearances']:
        section['height'] *= METERS


def heel_animation_offsets(clips):
    for clip in clips:
        for lift in clip['lifts']:
            lift['lift'] *= METERS
            lift['hips'] = scaled(lift['hips'])


def underwear_fitting(data):
    data['patch_centers'] = scaled(data['patch_centers'])
    for key in ['full_transfer_radius', 'falloff_radius']:
        data[key] *= METERS


def cheek_anchors(data):
    data['body_sha256'] = digest(BASE)
    for view in [data, *data['additional_views']]:
        view['camera'] = scaled(view['camera'])
        view['targets'] = scaled(view['targets'])
        if 'depth_tolerance' in view:
            view['depth_tolerance'] *= METERS


# Only rig-space arrays scale; Tripo-space `source` arrays (half extent 0.5) keep their units.
SIDECARS = {
    'assets/items/female_knight_boots/fitted_v5/heel-pose.json':
        ('c41cdf112f945a493769281c1e9588c29b257666af395be37f1274220824590c', lambda p: edit_json(p, scale_heel_pose)),
    'assets/items/female_knight_boots/fitted_v5/fitting.json':
        ('b0652de315ddff52fba88a0d886c7a813dc76af3f1a4929fb04cfe6e11ad1237', lambda p: edit_json(p, knight_boots_fitting)),
    'assets/items/female_knight_boots/fitted_v4/heel-pose.json':
        ('c41cdf112f945a493769281c1e9588c29b257666af395be37f1274220824590c', lambda p: edit_json(p, scale_heel_pose)),
    'assets/items/female_knight_boots/fitted_v4/fitting.json':
        ('fd72ecd901cbd5f46508a49aa5b80b84f4df0b4ba6ce9062385b3189c3c78aab', lambda p: edit_json(p, knight_boots_fit_v4)),
    'assets/items/female_knight_boots/fitted_v5/heel-animation-offsets.json':
        ('18e7afc4992d6bf892c3371b74b999144e6c58ac62977bb2f2a0984c89502272', lambda p: edit_json(p, heel_animation_offsets)),
    'assets/items/female_barbarian_boots/tripo_v1/fitted_v3/heel-animation-offsets.json':
        ('9425378a2c109b2422a9b0753eaa1554cd9e8a517454bc67a8ad4e29fa246ede', lambda p: edit_json(p, heel_animation_offsets)),
    'assets/modular_human_female_01/underwear_fit_v1/fitting.json':
        ('c0ba24f8f46c5309e21d529376da4dc10267bf0547648b01e5231770684c0bf6', lambda p: edit_json(p, underwear_fitting)),
    'assets/modular_human_female_01/underwear_fit_v1/source-influences.npz':
        ('0085b6f0b74e67d8f00e089a393e360a21ea3fbb57aa3cdee3782dc1b67fe8f7', lambda p: edit_npz(p, ['positions'])),
    'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair-cheek-coverage-anchors.json':
        ('5a13d89f6ce58b46846982aaf9beeeb911d7004496af0ba9eb47ade758d9a463', lambda p: edit_json(p, cheek_anchors)),
    'assets/items/female_knight_gloves/tripo_v1/fitted_v3/fit-data.npz':
        ('ed51943a6446d3525dbb4a515686abd83ee8ac132f206e2073c3309a4a8b5549', lambda p: edit_npz(p, ['Right_positions', 'Left_positions'])),
    'assets/items/female_knight_top/tripo_v1/fitted_v3/sleeve-adjustment.npz':
        ('48e3e54e7223e30ed6d6a78627fd7fb7741497ceeddd68620288baed84665753', lambda p: edit_npz(p, ['previous', 'source', 'points'])),
    'assets/items/female_barbarian_top/tripo_v1/fitted_v1/fit-data.npz':
        ('75bb7b6f4938244e3c3224481d543f5d8491bffe1dc7bc294faed5cd67e541fc', lambda p: edit_npz(p, ['source', 'fitted', 'depth'])),
    'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/fit-data.npz':
        ('bcfe9ea3e6050ca49ed8a835725aeefc683b9fd0ed39f1040d6ad0c0462b7a3c', lambda p: edit_npz(p, ['fitted', 'depth'])),
    'assets/items/female_barbarian_boots/tripo_v1/fitted_v3/fit-data.npz':
        ('f0c9b29d8a31188027d40f923da40b6bb43a6315ff8a6f60de62f2774c5f7239', lambda p: edit_npz(p, ['start', 'fitted', 'left_fitted', 'depth'])),
}


def main():
    for relative, expected in GLBS.items():
        path = ROOT / relative
        assert digest(path) == expected, f'{relative} is not the pre-migration source'
        scale_glb(path)
        print(relative, digest(path))
    for relative, (expected, convert) in SIDECARS.items():
        path = ROOT / relative
        assert digest(path) == expected, f'{relative} is not the pre-migration source'
        convert(path)
        print(relative, digest(path))


if __name__ == '__main__':
    main()
