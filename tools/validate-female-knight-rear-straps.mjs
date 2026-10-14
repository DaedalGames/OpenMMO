import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'
await ensureFemalePreview('animations')

const directory = 'assets/items/female_knight_bottom/tripo_v1'
const fitting = JSON.parse(readFileSync(`${directory}/fitted_v22/fitting.json`))
const changed = new Set(fitting.rear_strap_vertices)
const sections = [
  [[1876, 2492], [2447, 2461], [1427, 1446], [1300, 1328]],
  [[4715, 4674], [4618, 4605], [4033, 3780], [3923, 3889]],
]
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load('assets/modular_human_female_01/rig_v1/female-base.glb')
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex(entry => entry.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  const paths = ['v21', 'v22'].map(version => `${directory}/fitted_${version}/bottom_female_knight.glb`)
  const versions = []
  for (const path of paths) versions.push(bindModularPart(base.scene, (await load(path)).scene))
  let differences = 0
  for (const [index, before] of versions[0].entries()) {
    const after = versions[1][index].geometry
    assert.deepEqual(after.index.array, before.geometry.index.array)
    for (const [name, attribute] of Object.entries(before.geometry.attributes)) {
      for (let vertex = 0; vertex < attribute.count; vertex++) {
        const editable = index === 0 && changed.has(vertex) && ['skinIndex', 'skinWeight'].includes(name)
        for (let k = 0; k < attribute.itemSize; k++) {
          if (editable) differences += Number(attribute.getComponent(vertex, k) !== after.attributes[name].getComponent(vertex, k))
          else assert.equal(after.attributes[name].getComponent(vertex, k), attribute.getComponent(vertex, k))
        }
      }
    }
  }
  assert.ok(differences > 0)
  const position = versions[1][0].geometry.attributes.position
  const restWidths = sections.map(side => side.map(([a, b]) => new THREE.Vector3().fromBufferAttribute(position, a).distanceTo(new THREE.Vector3().fromBufferAttribute(position, b))))
  const sample = clipSampler(base.scene, { samples: 61, restore: versions[1][0].skeleton.bones })
  const clips = []
  for (const clip of base.animations) {
    const metrics = versions.map(() => ({ maximum_section_twist_degrees: 0, minimum_width_ratio: Infinity, maximum_width_ratio: 0 }))
    for (const _ of sample(clip)) versions.forEach((meshes, version) => {
      const mesh = meshes[0], metric = metrics[version]
      sections.forEach((side, s) => {
        const directions = side.map(([a, b], k) => {
          const width = mesh.getVertexPosition(b, new THREE.Vector3()).sub(mesh.getVertexPosition(a, new THREE.Vector3()))
          const ratio = width.length() / restWidths[s][k]
          metric.minimum_width_ratio = Math.min(metric.minimum_width_ratio, ratio)
          metric.maximum_width_ratio = Math.max(metric.maximum_width_ratio, ratio)
          return width.normalize()
        })
        for (let k = 1; k < directions.length; k++) metric.maximum_section_twist_degrees = Math.max(metric.maximum_section_twist_degrees, THREE.MathUtils.radToDeg(directions[k].angleTo(directions[k - 1])))
      })
    })
    assert.ok(metrics[1].minimum_width_ratio > .7, clip.name)
    assert.ok(metrics[1].maximum_width_ratio < 1.001, clip.name)
    if (['idle1', 'idle_armed', 'walk'].includes(clip.name)) {
      assert.ok(metrics[0].maximum_section_twist_degrees > 40, clip.name)
      assert.ok(metrics[1].maximum_section_twist_degrees < 20, clip.name)
    }
    clips.push({ name: clip.name, samples: 61, before: metrics[0], after: metrics[1] })
  }
  const report = {
    date: '2026-10-13', sources: paths.map(path => ({ path, sha256: hash(path) })),
    changed_weight_vertices: changed.size, unchanged_geometry_and_other_weights: true, clips,
    scope: 'Rear strap cross-section rotation and width throughout the animation clips; not a full outfit collision test.',
  }
  writeFileSync(`${directory}/fitted_v22/rear-strap-validation.json`, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
} finally {
  await server.close()
}
