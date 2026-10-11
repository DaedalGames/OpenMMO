import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, hash } from './lib/headless-three.mjs'
import { femaleCatwalk, catwalkSource } from './lib/female-catwalk.mjs'

const directory = 'assets/modular_human_female_01/rig_v1/'
const context = await headlessThree()
try {
  const base = await context.load(directory + 'female-base.glb')
  const walk = await femaleCatwalk(base.scene, base.animations.find(clip => clip.name === 'walk'), context)
  writeFileSync(directory + 'clips.json', JSON.stringify({
    sources: [{ path: catwalkSource, sha256: hash(catwalkSource) }],
    clips: base.animations.map(clip => THREE.AnimationClip.toJSON(clip.name === 'walk' ? walk : clip)),
  }) + '\n')
} finally { await context.server.close() }
