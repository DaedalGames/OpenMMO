import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'
await ensureFemalePreview('animations')

const version = process.argv[2] ?? 'v39'
assert.ok(['v39', 'v40'].includes(version))
const directory = `assets/items/female_knight_bottom/tripo_v1/fitted_${version}`
const path = `${directory}/bottom_female_knight.glb`
const fitting = JSON.parse(readFileSync(`${directory}/fitting.json`))
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load('assets/modular_human_female_01/rig_v1/female-base.glb')
  const meshes = bindModularPart(base.scene, (await load(path)).scene)
  const [leather, plate] = meshes
  const previous = await load(fitting.source)
  const originals = []
  previous.scene.traverse(object => { if (object.isSkinnedMesh) originals.push(object) })
  const changed = new Set(fitting.upper_rear_strap_surface?.replaced_vertices ?? [])
  for (let i = 0; i < meshes.length; i++) {
    for (const [name, attribute] of Object.entries(originals[i].geometry.attributes)) {
      const actual = meshes[i].geometry.attributes[name]
      for (let vertex = 0; vertex < attribute.count; vertex++) {
        for (let k = 0; k < attribute.itemSize; k++)
          assert.equal(actual.getComponent(vertex, k), attribute.getComponent(vertex, k))
      }
    }
    if (i > 0) assert.deepEqual(meshes[i].geometry.index.array, originals[i].geometry.index.array)
  }
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex(c => c.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  const contacts = [...fitting.rear_strap_surface.contacts.filter(contact => !changed.has(contact.vertex)), ...(fitting.upper_rear_strap_surface?.contacts ?? [])]
  const signs = contacts.map(contact => {
    const p = contact.plate_vertices.map(i => new THREE.Vector3().fromBufferAttribute(plate.geometry.attributes.position, i))
    return Math.sign(new THREE.Triangle(...p).getNormal(new THREE.Vector3()).z) > 0 ? -1 : 1
  })
  const sample = clipSampler(base.scene, {samples:61, restore:leather.skeleton.bones})
  const clips = []
  for (const clip of base.animations) {
    let min = Infinity, max = -Infinity, lowerMin = Infinity, referenceError = 0
    for (const { sample: frame } of sample(clip)) {
      for (const [index, contact] of contacts.entries()) {
        const points = contact.plate_vertices.map(i => plate.getVertexPosition(i, new THREE.Vector3()))
        const surface = points.reduce((sum, point, k) => sum.addScaledVector(point, contact.barycentric[k]), new THREE.Vector3())
        const normal = new THREE.Triangle(...points).getNormal(new THREE.Vector3()).multiplyScalar(signs[index])
        const gap = leather.getVertexPosition(contact.vertex, new THREE.Vector3()).sub(surface).dot(normal) * 1800
        min = Math.min(min, gap); max = Math.max(max, gap)
        if (contact.vertex < (fitting.upper_rear_strap_surface?.original_vertex_count ?? Infinity)) lowerMin = Math.min(lowerMin, gap)
        if (clip.name === 'idle1' && frame === 0) referenceError = Math.max(referenceError, Math.abs(gap - 1))
      }
    }
    if (clip.name === 'idle1') assert.ok(referenceError < .001, `1 mm fitting error: ${referenceError}`)
    if (['idle1', 'idle_armed'].includes(clip.name)) assert.ok(min > 0, `${clip.name}: contact crosses plate ${min}`)
    if (clip.name === 'walk') assert.ok(lowerMin > 0, `walk: preserved lower contact crosses plate ${lowerMin}`)
    clips.push({name:clip.name, frames:61, minimum_gap_mm:min, maximum_gap_mm:max, ...(clip.name === 'idle1' ? {reference_maximum_error_mm:referenceError} : {})})
  }
  const report = {date:'2026-10-13',sha256:hash(path),contact_samples:contacts.length,unchanged_unselected_vertices_and_other_parts:true,upper_contact_samples:fitting.upper_rear_strap_surface?.contacts.length ?? 0,clips,scope:'Signed distance of fitted inner strap vertices to their corresponding plate triangles. Plate edges and end transitions are excluded; this is not a full triangle collision test.'}
  writeFileSync(`${directory}/surface-validation.json`,JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify(report))
} finally { await server.close() }
