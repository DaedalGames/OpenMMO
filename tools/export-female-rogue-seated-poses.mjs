import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const animationPath = 'assets/modular_human_female_01/preview/animations.json'
const output = process.argv[2] ?? 'assets/items/female_rogue_top/tripo_v1/fitted_v5'
const { server, load } = await headlessThree()
try {
  await ensureFemalePreview('animations')
  const base = await load(basePath)
  let body
  base.scene.traverse(node => { if (node.isSkinnedMesh && !body) body = node })
  const data = JSON.parse(readFileSync(animationPath)).clips.find(clip => clip.name === 'sit_idle')
  const clip = data ? THREE.AnimationClip.parse(data) : base.animations.find(clip => clip.name === 'sit_idle')
  assert.ok(clip, 'The female preview has no sitting clip')
  const samples = []
  for (const { sample, time } of clipSampler(base.scene, { samples: 61, restore: body.skeleton.bones })(clip)) {
    samples.push({ phase: sample / 60, time,
      matrices: body.skeleton.bones.map((bone, i) => new THREE.Matrix4()
        .multiplyMatrices(bone.matrixWorld, body.skeleton.boneInverses[i]).elements) })
  }
  mkdirSync(output, { recursive: true })
  writeFileSync(`${output}/sit-poses.json`, JSON.stringify({ base_sha256: hash(basePath),
    animations_sha256: hash(animationPath), clip: clip.name, samples }))
  console.log(`Exported ${samples.length} actual preview sitting poses`)
} finally {
  await server.close()
}
