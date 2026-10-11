"""Export the existing catwalk source without changing the shared animation library."""
import importlib.util
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('export_animations', Path(__file__).with_name('export_animations.py'))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/all_animation.blend'))
armature = exporter.get_armature()
exporter.strip_bone_name_prefixes(armature)
exporter.rebind_action_slots_to_target(armature)
exporter.clear_nla_tracks(armature)
exporter.push_actions_to_nla(armature, [bpy.data.actions['walk_cat']])
armature.animation_data.action = None
exporter.select_export_objects(armature)
exporter.export_glb(str(ROOT / 'assets/modular_human_female_01/rig_v1/catwalk-source.glb'))
