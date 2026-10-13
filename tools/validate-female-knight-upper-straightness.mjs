import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const version = process.argv[2] ?? 'v41'
assert.ok(['v41', 'v42'].includes(version))
const directory = `assets/items/female_knight_bottom/tripo_v1/fitted_${version}`
const path = `${directory}/bottom_female_knight.glb`
const fitting = JSON.parse(readFileSync(`${directory}/fitting.json`))
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load('assets/modular_human_female_01/rig_v1/female-base.glb')
  const meshes = bindModularPart(base.scene, (await load(path)).scene)
  const originals = []
  const previous = await load(fitting.source)
  previous.scene.traverse(object => { if (object.isSkinnedMesh) originals.push(object) })
  const changed = new Set(fitting.smooth_second_buckle?.vertices ?? fitting.straight_upper_rear_straps.vertices)
  for (let i = 0; i < meshes.length; i++) {
    assert.deepEqual(meshes[i].geometry.index.array, originals[i].geometry.index.array)
    for (const [name, attribute] of Object.entries(originals[i].geometry.attributes)) {
      const actual = meshes[i].geometry.attributes[name]
      assert.equal(actual.count, attribute.count)
      for (let vertex = 0; vertex < attribute.count; vertex++) {
        if (i === 0 && changed.has(vertex) && name !== 'uv') continue
        for (let k = 0; k < attribute.itemSize; k++)
          assert.equal(actual.getComponent(vertex, k), attribute.getComponent(vertex, k))
      }
    }
  }
  const clip = base.animations.find(clip => clip.name === 'idle1')
  assert.ok(clip)
  const leather = meshes[0]
  const sampler = clipSampler(base.scene, { samples: 61, restore: leather.skeleton.bones })
  let maximumReferenceError = 0, checked = 0, transitionChecked = 0, maximumTransitionError = 0, maximumJoinAngle = 0
  for (const region of fitting.smooth_second_buckle?.regions ?? []) {
    const upper = fitting.straight_upper_rear_straps.regions.find(entry => entry.side === region.side)
    const direction = new THREE.Vector3(...upper.bottom).sub(new THREE.Vector3(...upper.top)).normalize()
    const tangent = new THREE.Vector3(...region.start_tangent).normalize()
    maximumJoinAngle = Math.max(maximumJoinAngle, direction.angleTo(tangent))
  }
  assert.ok(maximumJoinAngle < 1e-7)
  for (const { sample: frame } of sampler(clip)) {
    if (frame !== 0) continue
    for (const region of fitting.smooth_second_buckle?.regions ?? []) {
      for (const point of region.samples) {
        const actual = leather.getVertexPosition(point.vertex, new THREE.Vector3())
        maximumTransitionError = Math.max(maximumTransitionError, actual.distanceTo(new THREE.Vector3(...point.position)))
        transitionChecked++
      }
    }
    for (const region of fitting.straight_upper_rear_straps.regions) {
      const bottom = new THREE.Vector3(...region.bottom), top = new THREE.Vector3(...region.top)
      const across = new THREE.Vector3(...region.across), outward = new THREE.Vector3(...region.outward)
      for (const point of region.samples) {
        const expected = bottom.clone().lerp(top, point.t).addScaledVector(across, point.lateral * point.width).addScaledVector(outward, point.layer)
        const actual = leather.getVertexPosition(point.vertex, new THREE.Vector3())
        maximumReferenceError = Math.max(maximumReferenceError, actual.distanceTo(expected))
        checked++
      }
    }
  }
  assert.ok(checked > 2000)
  assert.ok(maximumTransitionError < 1e-7)
  if (version === 'v42') assert.ok(transitionChecked > 1000)
  assert.ok(maximumReferenceError < 1e-7, `Straight ribbon deviation: ${maximumReferenceError}`)
  const report = {sha256: hash(path), reference_pose:'idle1 at time 0', checked_vertices:checked, maximum_reference_error_mm:maximumReferenceError * 1800, transition_vertices_checked:transitionChecked,maximum_transition_error_mm:maximumTransitionError * 1800,maximum_join_angle_degrees:maximumJoinAngle * 180 / Math.PI,unchanged_topology_uvs_and_unselected_attributes:true, scope:'Straight tapered ribbons from waist to the second buckle; waist and lower strap blend regions are excluded. Other poses are covered by runtime deformation checks, not a straightness or collision guarantee.'}
  writeFileSync(`${directory}/straightness-validation.json`, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
} finally { await server.close() }
