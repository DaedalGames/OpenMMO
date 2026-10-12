import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, hash } from './lib/headless-three.mjs'
import { root, sources, output } from './lib/female-preview.mjs'

const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { femaleTorchClips, levelGaze } = await server.ssrLoadModule('/src/previews/female-torch.ts')
  const { scene, animations } = await load(sources.base)
  for (const name of ['bob', 'knight']) {
    const optimized = await load(`assets/modular_human_female_01/preview/${name}.glb`)
    const meshes = bindModularPart(scene, optimized.scene)
    for (const mesh of meshes) mesh.visible = name === 'bob'
  }
  const find = name => animations.find(clip => clip.name === name)
  const walk = find('walk'), combat = find('combat_idle')
  levelGaze(scene, combat)
  levelGaze(scene, walk)
  const torch = await femaleTorchClips(scene,
    await load('client/public/models/characters/modular_male/animations/offhand.glb'),
    find('idle_armed'), walk, combat)
  const prepared = JSON.parse(await readFile(output('animations'), 'utf8')).clips.map(clip => THREE.AnimationClip.parse(clip))
  let maxError = 0
  for (const original of [walk, combat, ...torch]) {
    const baked = prepared.find(clip => clip.name === original.name)
    assert.ok(baked, original.name)
    assert.equal(baked.duration, original.duration)
    assert.equal(baked.tracks.length, original.tracks.length)
    for (const track of original.tracks) {
      const candidate = baked.tracks.find(t => t.name === track.name)
      assert.ok(candidate, track.name)
      assert.deepEqual(candidate.times, track.times)
      assert.equal(candidate.values.length, track.values.length)
      for (let i = 0; i < track.values.length; i++)
        maxError = Math.max(maxError, Math.abs(candidate.values[i] - track.values[i]))
    }
  }
  assert.ok(maxError < 1e-6, `Baked animations changed: ${maxError}`)
  const report = { date: '2026-10-12', exact_hair_bind_compatibility: true,
    compared_clips: prepared.map(clip => clip.name), maximum_track_error: maxError,
    sources: Object.entries(sources).map(([name, path]) => ({ name, path, sha256: hash(path) })) }
  await writeFile(new URL('doc/assets/modular-female-preview-validation.json', root), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
} finally { await server.close() }
