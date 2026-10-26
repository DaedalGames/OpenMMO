import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const animationPath = 'assets/modular_human_female_01/preview/animations.json'
const output = process.argv[2] ?? 'assets/items/female_rogue_top/tripo_v1/fitted_v5'
const motion = process.argv[3] ?? 'sit_idle'
const { server, load } = await headlessThree()
try {
  await ensureFemalePreview('animations')
  const base = await load(basePath)
  let body
  base.scene.traverse(node => { if (node.isSkinnedMesh && !body) body = node })
  const clips = new Map(base.animations.map(clip => [clip.name, clip]))
  for (const data of JSON.parse(readFileSync(animationPath)).clips) {
    const clip = THREE.AnimationClip.parse(data)
    clips.set(clip.name, clip)
  }
  assert.ok(motion === 'all' || clips.has(motion), `The female preview has no ${motion} clip`)
  const samples = []
  const count = motion === 'all' ? 33 : 61
  const sampler = clipSampler(base.scene, { samples: count, restore: body.skeleton.bones })
  for (const clip of motion === 'all' ? clips.values() : [clips.get(motion)]) {
    for (const { sample, time } of sampler(clip)) {
      samples.push({ clip: clip.name, sample, phase: sample / (count - 1), time,
        matrices: body.skeleton.bones.map((bone, i) => new THREE.Matrix4()
          .multiplyMatrices(bone.matrixWorld, body.skeleton.boneInverses[i]).elements) })
    }
  }
  mkdirSync(output, { recursive: true })
  writeFileSync(`${output}/${motion === 'sit_idle' ? 'sit' : motion}-poses.json`, JSON.stringify({ base_sha256: hash(basePath),
    animations_sha256: hash(animationPath), clip: motion, samples }))
  console.log(`Exported ${samples.length} actual preview ${motion} poses`)
} finally {
  await server.close()
}
