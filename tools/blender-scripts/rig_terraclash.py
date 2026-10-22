"""Rig the awake Terraclash and bake its clips.

blender -b --python tools/blender-scripts/rig_terraclash.py -- SRC.glb OUT.glb BLEND

Landmarks come from slicing the 9 m game mesh (front +Z, up +Y in glTF).
Rock limbs are rigid, so weights are inverse-distance to bone segments,
limited per region so an arm never pulls on the torso.
"""
import math
import sys

import bpy
import numpy as np
from mathutils import Euler, Quaternion, Vector

args = sys.argv[sys.argv.index('--') + 1:]
src, out, blend = args[:3]
FPS = 30


def g(x, y, z):
    """glTF (x, y-up, z-front) to Blender (x, -z, y)."""
    return Vector((x, -z, y))


BONES = {
    # name: (head, tail, parent)
    'Root': (g(0, 0, 0), g(0, 1.0, 0), None),
    'Hips': (g(0, 1.0, 0), g(0, 3.0, 0), 'Root'),
    'Spine': (g(0, 3.0, 0), g(0, 4.8, 0), 'Hips'),
    'Chest': (g(0, 4.8, 0), g(0, 6.4, -0.3), 'Spine'),
    'Head': (g(0, 6.4, -0.3), g(0, 8.6, 0.6), 'Chest'),
}
for side, s in (('L', 1), ('R', -1)):
    BONES[f'Shoulder.{side}'] = (g(1.2 * s, 6.0, -0.5), g(3.0 * s, 6.3, -0.6), 'Chest')
    BONES[f'UpperArm.{side}'] = (g(3.0 * s, 6.3, -0.6), g(3.8 * s, 3.8, -0.8), f'Shoulder.{side}')
    BONES[f'LowerArm.{side}'] = (g(3.8 * s, 3.8, -0.8), g(3.6 * s, 1.9, 1.4), f'UpperArm.{side}')
    BONES[f'Hand.{side}'] = (g(3.6 * s, 1.9, 1.4), g(3.7 * s, 0.3, 2.3), f'LowerArm.{side}')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
mesh.name = 'terraclash'

arm_data = bpy.data.armatures.new('TerraclashRig')
rig = bpy.data.objects.new('TerraclashRig', arm_data)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name, (head, tail, parent) in BONES.items():
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = head, tail
    b.roll = 0
    if parent:
        b.parent = arm_data.edit_bones[parent]
        b.use_connect = (b.head - b.parent.tail).length < 1e-4
bpy.ops.object.mode_set(mode='OBJECT')


def region_bones(co):
    """Bones allowed to influence a vertex at glTF-space `co`."""
    x, y = co.x, co.z
    for side, s in (('L', 1), ('R', -1)):
        if x * s > 2.15 and y < 5.6:
            return [f'UpperArm.{side}', f'LowerArm.{side}', f'Hand.{side}']
        if x * s > 1.6 and y >= 5.6:
            return [f'Shoulder.{side}', f'UpperArm.{side}', 'Chest']
    if y > 6.4 and abs(x) < 1.6:
        return ['Chest', 'Head']
    return ['Hips', 'Spine', 'Chest']


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


# Each fist touches the torso base at ground level; those shared faces would
# stretch when an arm lifts, so cut them.
import bmesh  # noqa: E402
bm = bmesh.new()
bm.from_mesh(mesh.data)
is_arm = [region_bones(mesh.matrix_world @ v.co)[0].startswith('UpperArm') for v in bm.verts]
bridges = [f for f in bm.faces
           if len({is_arm[v.index] for v in f.verts}) == 2
           and max((mesh.matrix_world @ v.co).z for v in f.verts) < 2.0]
bmesh.ops.delete(bm, geom=bridges, context='FACES')
bm.to_mesh(mesh.data)
bm.free()
print('BRIDGE_FACES_CUT', len(bridges))

groups = {n: mesh.vertex_groups.new(name=n) for n in BONES if n != 'Root'}
for v in mesh.data.vertices:
    co = mesh.matrix_world @ v.co
    names = region_bones(co)
    w = np.array([1.0 / max(seg_dist(co, BONES[n][0], BONES[n][1]), 0.15) ** 6 for n in names])
    w /= w.sum()
    for n, wi in zip(names, w):
        if wi > 0.01:
            groups[n].add([v.index], float(wi), 'REPLACE')

mod = mesh.modifiers.new('Armature', 'ARMATURE')
mod.object = rig
mesh.parent = rig

# --- animation -------------------------------------------------------------
pose = rig.pose.bones
for pb in pose:
    pb.rotation_mode = 'QUATERNION'


def arm_rot(name, axis, deg):
    """Pose-local quaternion for a rotation about an armature-space axis."""
    rest = rig.data.bones[name].matrix_local.to_quaternion()
    q = Quaternion(Vector(axis).normalized(), math.radians(deg))
    return rest.inverted() @ q @ rest


def key(frame, rots):
    """rots: {bone: [(axis, deg), ...]} composed in armature space."""
    for pb in pose:
        q = Quaternion()
        for axis, deg in rots.get(pb.name, []):
            q = arm_rot(pb.name, axis, deg) @ q
        pb.rotation_quaternion = q
        pb.keyframe_insert('rotation_quaternion', frame=frame)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
# Blender: +X = creature's left, -Y = front, +Z = up. +X tips an upward bone
# forward and a downward one back; +Y swings +X-side limbs down/inward and
# -X-side limbs up/outward.


def clip(name, frames, cyclic=False):
    act = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = act
    for f, rots in frames:
        key(round(f * FPS) + 1, rots)
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    bag = action_get_channelbag_for_slot(act, rig.animation_data.action_slot)
    for fc in bag.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
        if cyclic:
            fc.modifiers.new('CYCLES')
    track = rig.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, 1, act)
    rig.animation_data.action = None
    return act


rest = {}
breath = {'Chest': [(X, -2)], 'Head': [(X, 2)],
          'UpperArm.L': [(Y, -1)], 'UpperArm.R': [(Y, 1)]}
clip('Idle', [(0, rest), (2.0, breath), (4.0, rest)], cyclic=True)

lift = {'Spine': [(Z, -10), (X, -4)], 'Chest': [(Z, -8)], 'Head': [(X, -8)],
        'Shoulder.R': [(Y, 20)], 'UpperArm.R': [(X, -100), (Y, -15)],
        'LowerArm.R': [(X, -40)], 'Hand.R': [(X, -20)]}
slam = {'Spine': [(Z, 6), (X, 10)], 'Chest': [(Z, 4), (X, 8)], 'Head': [(X, 6)],
        'Shoulder.R': [(Y, -6)], 'UpperArm.R': [(X, -18)], 'LowerArm.R': [(X, 10)],
        'Hand.R': [(X, 6)]}


def slam_clip(name, lift, slam):
    clip(name, [(0, rest), (0.9, lift), (1.15, lift), (1.4, slam), (1.9, slam), (2.6, rest)])


slam_clip('Attack', lift, slam)


def mirror(rots):
    """Swap sides; reflecting across X keeps X rotations and flips Y/Z ones."""
    swap = {'.R': '.L', '.L': '.R'}
    return {(n[:-2] + swap[n[-2:]] if n[-2:] in swap else n):
            [(axis, deg if axis == X else -deg) for axis, deg in r]
            for n, r in rots.items()}


slam_clip('AttackLeft', mirror(lift), mirror(slam))

roar_rots = {'Spine': [(X, -8)], 'Chest': [(X, -14)], 'Head': [(X, -30)],
             'Shoulder.L': [(Y, -15)], 'Shoulder.R': [(Y, 15)],
             'UpperArm.L': [(Y, -20), (X, -30)], 'UpperArm.R': [(Y, 20), (X, -30)],
             'LowerArm.L': [(X, -30)], 'LowerArm.R': [(X, -30)]}
crouch = {'Spine': [(X, 6)], 'Chest': [(X, 10)], 'Head': [(X, 12)]}
gather = {'Spine': [(X, 10)], 'Chest': [(X, 16)], 'Head': [(X, 18)],
          'Shoulder.L': [(Y, 8)], 'Shoulder.R': [(Y, -8)]}
# The roar's damage lands at 4.0s (EARTH_ROAR.strike_ms); the long gather is
# the time raiders get to drink.
clip('Roar', [(0, rest), (1.2, crouch), (3.4, gather), (4.0, roar_rots), (5.4, roar_rots),
              (6.2, rest)])



def both(rots, trunk):
    """Both arms posed alike, the trunk set apart since one side's twist
    would cancel the other's."""
    arms = {n: r for n, r in {**mirror(rots), **rots}.items()
            if n not in ('Spine', 'Chest', 'Head')}
    return {**arms, **trunk}


# FORMATION_BREAK: both fists rise overhead and come down on the fan in
# front at 2.8s (strike_ms).
heave = both({'Shoulder.R': [(Y, 24)], 'UpperArm.R': [(X, -125), (Y, -10)],
              'LowerArm.R': [(X, -35)], 'Hand.R': [(X, -20)]},
             {'Spine': [(X, -8)], 'Chest': [(X, -12)], 'Head': [(X, -16)]})
smash = both(slam, {'Spine': [(X, 14)], 'Chest': [(X, 12)], 'Head': [(X, 8)]})
clip('Smash', [(0, rest), (1.6, heave), (2.45, heave), (2.8, smash), (3.6, smash),
               (4.4, rest)])

# EARTHQUAKE: a warning pound, then a heavier one at 3.5s (strike_ms).
raise_low = both({'Shoulder.R': [(Y, 12)], 'UpperArm.R': [(X, -60), (Y, -10)],
                  'LowerArm.R': [(X, -25)]},
                 {'Spine': [(X, -3)], 'Chest': [(X, -5)], 'Head': [(X, -6)]})
pound = both(slam, {'Spine': [(X, 16)], 'Chest': [(X, 14)], 'Head': [(X, 10)]})
clip('Quake', [(0, rest), (0.8, raise_low), (1.15, pound), (1.5, pound), (2.6, heave),
               (3.15, heave), (3.5, pound), (4.3, pound), (5.0, rest)])

hit = {'Chest': [(X, -6)], 'Head': [(X, -8)], 'Spine': [(X, -3)]}
clip('Hit', [(0, rest), (0.15, hit), (0.6, rest)])

slump = {'Spine': [(X, 12)], 'Chest': [(X, 18)], 'Head': [(X, 35)],
         'Shoulder.L': [(Y, 8)], 'Shoulder.R': [(Y, -8)],
         'UpperArm.L': [(Y, -12)], 'UpperArm.R': [(Y, 12)]}
clip('Death', [(0, rest), (0.4, hit), (2.4, slump)])
clip('Dead', [(0, slump), (1.0, slump)])

bpy.context.scene.render.fps = FPS
bpy.ops.wm.save_as_mainfile(filepath=blend)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=out, export_format='GLB', export_animations=True,
    export_animation_mode='NLA_TRACKS', export_image_format='WEBP',
    export_image_quality=90)
print('RIGGED', len(mesh.data.vertices), 'verts', len(BONES), 'bones')
