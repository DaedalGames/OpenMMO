import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'
await ensureFemalePreview('animations')

const directory = 'assets/items/female_knight_bottom/tripo_v1'
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load('assets/modular_human_female_01/rig_v1/female-base.glb')
  const prepared = JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json'))
  for (const data of prepared.clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex(entry => entry.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  const versions = []
  for (const version of ['v17', 'v21']) {
    const path = `${directory}/fitted_${version}/bottom_female_knight.glb`
    const meshes = bindModularPart(base.scene, (await load(path)).scene)
    const position = meshes[0].geometry.attributes.position
    const selected = JSON.parse(readFileSync(`${directory}/fitted_${version}/fitting.json`)).vertices
    const sections = [-1, 1].map(side => [.568, .535, .489, .423].map(height => {
      const vertices = selected.filter(i => position.getX(i) * side > 0 && Math.abs(position.getY(i) - height) < .003)
      assert.ok(vertices.length > 0)
      return vertices
    }))
    versions.push({ meshes, sections, selected: new Set(selected), path, sha256: hash(path) })
  }
  for (const [index, mesh] of versions[0].meshes.entries()) {
    const geometry = versions[1].meshes[index].geometry
    assert.deepEqual(geometry.index.array, mesh.geometry.index.array)
    for (const [name, before] of Object.entries(mesh.geometry.attributes)) {
      const after = geometry.attributes[name]
      for (let vertex = 0; vertex < before.count; vertex++) {
        if (index !== 0 || !versions[1].selected.has(vertex) || ['skinIndex', 'skinWeight'].includes(name)) continue
        for (let k = 0; k < before.itemSize; k++) assert.equal(after.getComponent(vertex, k), before.getComponent(vertex, k))
      }
    }
  }
  const sample = clipSampler(base.scene, { samples: 61, restore: versions[0].meshes[0].skeleton.bones })
  const clips = []
  for (const clip of base.animations) {
    const maximumBend = [0, 0]
    for (const _ of sample(clip)) versions.forEach(({ meshes, sections }, version) => {
      for (const section of sections) {
        const points = section.map(vertices => vertices.reduce((sum, vertex) => sum.add(meshes[0].getVertexPosition(vertex, new THREE.Vector3())), new THREE.Vector3()).divideScalar(vertices.length))
        for (let k = 1; k < points.length - 1; k++) {
          const incoming = points[k].clone().sub(points[k - 1])
          const outgoing = points[k + 1].clone().sub(points[k])
          maximumBend[version] = Math.max(maximumBend[version], THREE.MathUtils.radToDeg(incoming.angleTo(outgoing)))
        }
      }
    })
    if (['idle1', 'idle_armed'].includes(clip.name)) {
      assert.ok(maximumBend[0] > 30)
      assert.ok(maximumBend[1] < 12)
    }
    if (clip.name === 'walk') assert.ok(maximumBend[1] < maximumBend[0] / 2)
    clips.push({ name: clip.name, samples: 61, previous_maximum_bend_degrees: maximumBend[0], maximum_bend_degrees: maximumBend[1] })
  }
  const report = {
    date: '2026-10-13', sources: versions.map(({ path, sha256 }) => ({ path, sha256 })),
    unchanged_front_strap_geometry_and_thickness: true, clips,
    scope: 'Angles between four strap cross-section centers. Idle and walking regression checks; extreme poses can still fold or intersect the body.'
  }
  writeFileSync(`${directory}/fitted_v21/bend-validation.json`, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
} finally {
  await server.close()
}
