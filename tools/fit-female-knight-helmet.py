"""Fit the open visor helmet and bind it rigidly to the canonical female Head."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from lib.glb import read_glb, write_glb, view_bytes
from lib.glb_accessors import accessor, add_accessor

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / 'assets/modular_human_female_01/rig_v1/female-base.glb'
DIRECTORY = ROOT / 'assets/items/female_knight_helmet/tripo_v1'
OUT = DIRECTORY / 'fitted_v1'
spec = importlib.util.spec_from_file_location('io', ROOT / 'tools/fit-modular-plate.py')
io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(io)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    source = DIRECTORY / 'source/model_url.glb'
    assert digest(source) == '7de873e925d7b1eda0c2aa0c50cab6c8a0b7ff57d44408c4824bfbdbb5e6d73a'
    assert digest(BODY) == '9564457e8b23275aaf8cd0ff74c318baa4bbfa6b1c8afe608037cf7f40cf0982'
    base, base_raw = read_glb(BODY)
    doc, source_raw = read_glb(source)
    source_images = [view_bytes(doc, source_raw, im['bufferView']) for im in doc['images']]
    raw = bytearray(source_raw)
    primitive = doc['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    points = accessor(doc, raw, attrs['POSITION'])
    uv = accessor(doc, raw, attrs['TEXCOORD_0'])
    faces = accessor(doc, raw, primitive['indices']).reshape(-1, 3)
    scale, offset = [.18, .18, .155], [0, .966, -.002]
    fitted = np.column_stack([-points[:, 2], points[:, 1], points[:, 0]]) * scale + offset
    skin = base['skins'][0]
    ids = skin['joints']
    names = [base['nodes'][i]['name'] for i in ids]
    joints = np.zeros((len(points), 4), dtype=np.uint16)
    joints[:, 0] = names.index('Head')
    weights = np.zeros((len(points), 4)); weights[:, 0] = 1
    normals = io.smooth_normals(fitted, faces)
    attrs = io.add_skin_attributes(doc, raw, fitted, normals, joints, weights)
    attrs['TEXCOORD_0'] = add_accessor(doc, raw, uv, 'VEC2')
    attrs['TANGENT'] = add_accessor(doc, raw, io.tangents(fitted, normals, uv, faces), 'VEC4')
    doc['meshes'] = [{'name': 'helmet_female_knight', 'primitives': [{'attributes': attrs, 'indices': add_accessor(doc, raw, faces.reshape(-1, 1), 'SCALAR', 5125), 'material': primitive['material']}]}]
    remap = {old: i for i, old in enumerate(ids)}
    doc['nodes'] = [copy.deepcopy(base['nodes'][i]) for i in ids]
    for bone in doc['nodes']:
        if 'children' in bone:
            bone['children'] = [remap[i] for i in bone['children'] if i in remap]
    children = {i for bone in doc['nodes'] for i in bone.get('children', [])}
    rig_id = 'human_female_01_local_v1'
    doc['nodes'].append({'name': 'Armature', 'children': [i for i in range(len(ids)) if i not in children], 'extras': {'rig_id': rig_id}})
    doc['nodes'].append({'name': 'helmet_female_knight', 'mesh': 0, 'skin': 0, 'extras': {'rig_id': rig_id, 'part_id': 'helmet_female_knight'}})
    doc['scenes'] = [{'nodes': [len(ids), len(ids)+1], 'extras': {'rig_id': rig_id}}]; doc['scene'] = 0
    skin = copy.deepcopy(skin)
    skin['joints'] = [remap[i] for i in ids]; skin['skeleton'] = remap[skin['skeleton']]
    skin['inverseBindMatrices'] = add_accessor(doc, raw, accessor(base, base_raw, skin['inverseBindMatrices']), 'MAT4')
    doc['skins'] = [skin]; doc.pop('animations', None)
    raw = io.compact(doc, raw)
    assert [view_bytes(doc, raw, im['bufferView']) for im in doc['images']] == source_images
    target = OUT / 'helmet_female_knight.glb'; write_glb(target, doc, raw)
    body_primitive = base['meshes'][0]['primitives'][0]
    mask = {'mesh_index': 0, 'primitive_index': 0, 'primitive_triangles': base['accessors'][body_primitive['indices']]['count']//3, 'hide_triangle_indices': []}
    (OUT / 'body-occlusion.json').write_text(json.dumps(mask, indent=2)+'\n')
    report = {'date':'2026-10-14','source_sha256':digest(source),'body_sha256':digest(BODY),'output_sha256':digest(target),'triangles':len(faces),'scale_xyz':scale,'offset_xyz':offset,'source_axis_mapping':'[-z,y,x]','rig_id':rig_id,'bones':len(ids),'weights':'Head 100%; rigid helmet including raised visor','texture_bytes_preserved':True,'hair':'Hide selected hair while helmet is equipped; restore selection on removal','status':'Pending fit and motion review'}
    (OUT / 'fitting.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
