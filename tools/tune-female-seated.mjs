import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree } from './lib/headless-three.mjs'
import { femaleSeated } from './lib/female-seated.mjs'

const directory = 'assets/modular_human_female_01/rig_v1/'
const context = await headlessThree()
try {
  const base = await context.load(directory + 'female-base.glb')
  const seated = await femaleSeated(base.scene, context)
  writeFileSync(directory + 'clips.json', JSON.stringify({
    clips: base.animations.map(clip => THREE.AnimationClip.toJSON(clip.name === 'sit_idle' ? seated : clip)),
  }) + '\n')
} finally { await context.server.close() }
