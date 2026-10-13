import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const directory = 'assets/items/female_knight_bottom/tripo_v1/fitted_v25'
const path = `${directory}/bottom_female_knight.glb`
const pairs = JSON.parse(readFileSync(`${directory}/thickness-samples.json`))
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load('assets/modular_human_female_01/rig_v1/female-base.glb')
  const mesh = bindModularPart(base.scene, (await load(path)).scene)[0]
  const clips = base.animations
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = clips.findIndex(entry => entry.name === clip.name)
    if (index < 0) clips.push(clip)
    else clips[index] = clip
  }
  const sample = clipSampler(base.scene, { samples: 61, restore: mesh.skeleton.bones })
  const vertices = [...new Set(pairs.flatMap(pair => [...pair.outer, ...pair.inner]))]
  const reports = []
  for (const clip of clips) {
    let minimumGap = Infinity, crossed = 0
    for (const _ of sample(clip)) {
      const positions = new Map(vertices.map(vertex => [vertex, mesh.getVertexPosition(vertex, new THREE.Vector3())]))
      const point = (ids, bary) => ids.reduce((sum, vertex, index) => sum.addScaledVector(positions.get(vertex), bary[index]), new THREE.Vector3())
      for (const pair of pairs) {
        const [a, b, c] = pair.outer.map(vertex => positions.get(vertex))
        const normal = b.clone().sub(a).cross(c.clone().sub(a)).normalize()
        const gap = point(pair.outer, pair.outer_bary).sub(point(pair.inner, pair.inner_bary)).dot(normal)
        minimumGap = Math.min(minimumGap, gap)
        crossed += Number(gap <= 0)
      }
    }
    if (['idle1', 'idle_armed', 'walk'].includes(clip.name)) {
      assert.equal(crossed, 0, `${clip.name}: crossed leather layers`)
      assert.ok(minimumGap > .00005, `${clip.name}: ${minimumGap}`)
    }
    reports.push({ name: clip.name, frames: 61, samples_per_frame: pairs.length, minimum_gap: minimumGap, crossed_samples: crossed })
  }
  const report = { date: '2026-10-13', sha256: hash(path), clips: reports, scope: 'Signed separation of paired broad leather faces through animation. Idle and walking asserted; other clips recorded. Not a full collision test.' }
  writeFileSync(`${directory}/animated-thickness-validation.json`, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
} finally {
  await server.close()
}
