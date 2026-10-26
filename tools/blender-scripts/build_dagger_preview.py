"""Retarget the two supplied FBX clips into a separate preview pack."""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_animations as exporter
from import_mixamo_animation import import_mixamo_animation

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
clips = {
    "dagger_inward": "Stable Sword Inward Slash.fbx",
    "dagger_outward": "Stable Sword Outward Slash.fbx",
    "dagger_stab": "Stabbing.fbx",
}
for filename in clips.values():
    if not (args.source / filename).is_file():
        raise FileNotFoundError(args.source / filename)

# Mixamo's stab rises above the shoulder; aim it level at chest height instead.
STAB_ELEVATION = math.radians(-8)
STAB_WRIST = math.radians(-15)
# Cut most of the frozen full-extension pose so the recovery fits a 1.2 s swing.
STAB_HOLD = (17, 26)


def rotate_about_head(arm, bone, rotation):
    world = arm.matrix_world.to_quaternion()
    local = (world.inverted() @ rotation @ world).to_matrix().to_4x4()
    head = bone.head.copy()
    bone.matrix = Matrix.Translation(head) @ local @ Matrix.Translation(-head) @ bone.matrix
    bpy.context.view_layer.update()


def level_stab(arm, action):
    scene = bpy.context.scene
    upper, hand = arm.pose.bones["RightArm"], arm.pose.bones["RightHand"]
    first, last = map(int, action.frame_range)
    hands = {}
    for frame in range(first, last + 1):
        scene.frame_set(frame)
        hands[frame] = arm.matrix_world @ hand.head
    peak = max(hands, key=lambda f: (hands[f] - hands[first]).xy.length)
    forward = hands[peak] - hands[first]
    forward.z = 0
    reach = forward.length
    forward.normalize()
    side = forward.cross(Vector((0, 0, 1)))
    previous = {}
    for frame in range(first, last + 1):
        scene.frame_set(frame)
        progress = (hands[frame] - hands[first]).dot(forward) / reach
        t = min(max((progress - 0.3) / 0.6, 0), 1)
        weight = t * t * (3 - 2 * t)
        if weight > 0:
            reach_vector = arm.matrix_world @ hand.head - arm.matrix_world @ upper.head
            elevation = math.asin(reach_vector.z / reach_vector.length)
            rotate_about_head(arm, upper, Quaternion(side, (STAB_ELEVATION - elevation) * weight))
            rotate_about_head(arm, hand, Quaternion(side, STAB_WRIST * weight))
        for bone in (upper, hand):
            if bone.name in previous:
                bone.rotation_quaternion.make_compatible(previous[bone.name])
            previous[bone.name] = bone.rotation_quaternion.copy()
            bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)


def cut_frames(action, first, last):
    removed = last - first + 1
    for curve in exporter.iter_fcurves(action):
        for key in reversed(list(curve.keyframe_points)):
            if first <= key.co.x <= last:
                curve.keyframe_points.remove(key)
        for key in curve.keyframe_points:
            if key.co.x > last:
                key.co.x -= removed
                key.handle_left.x -= removed
                key.handle_right.x -= removed
        curve.update()


bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets/all_animation.blend"))
arm = bpy.data.objects["Armature_combat"]
exporter.clear_nla_tracks(arm)
arm.animation_data.action = None

for name, filename in clips.items():
    bpy.context.scene.render.fps = 30
    import_mixamo_animation(str(args.source / filename), name, arm.name, save=False)
    action = bpy.data.actions[name]
    arm.animation_data.action = action
    arm.animation_data.action_slot = action.slots[0]
    if name == "dagger_stab":
        level_stab(arm, action)
    hips = arm.pose.bones["Hips"]
    first, last = map(int, action.frame_range)
    bpy.context.scene.frame_set(first)
    origin = (arm.matrix_world @ hips.matrix).translation.copy()
    axes = arm.matrix_world.to_3x3() @ hips.bone.matrix_local.to_3x3()
    samples = []
    motion = []
    for frame in range(first, last + 1):
        bpy.context.scene.frame_set(frame)
        displacement = (arm.matrix_world @ hips.matrix).translation - origin
        correction = axes.inverted() @ Vector((displacement.x, displacement.y, 0))
        samples.append((frame, hips.location - correction))
        hand = (arm.matrix_world @ arm.pose.bones["RightHand"].matrix).translation
        if (frame - first) % 3 == 0:
            motion.append([frame - first, *[round(v, 3) for v in hand]])
    for frame, position in samples:
        hips.location = position
        hips.keyframe_insert(data_path="location", frame=frame, group="Hips")
    if name == "dagger_stab":
        cut_frames(action, first + STAB_HOLD[0], first + STAB_HOLD[1])
    for curve in exporter.iter_fcurves(action):
        for key in curve.keyframe_points:
            key.co.x -= first
            key.handle_left.x -= first
            key.handle_right.x -= first
        curve.update()
    action.use_fake_user = True
    print("DAGGER_MOTION", name, json.dumps(motion))

arm.animation_data.action = None
# The shipped slash clips and their combo windows are timed at 24 fps.
bpy.context.scene.render.fps = 24
bpy.context.scene.frame_start = 0
exporter.strip_bone_name_prefixes(arm)
exporter.rebind_action_slots_to_target(arm)
exporter.push_actions_to_nla(arm, [bpy.data.actions[name] for name in clips])
exporter.select_export_objects(arm)
exporter.export_glb(str(ROOT / "client/public/models/animations/dagger_preview.glb"))
