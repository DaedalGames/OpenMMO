import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, loadClips, clipSampler, root } from './lib/headless-three.mjs'

const { server, sources, load } = await headlessThree({ meshopt: true })
try {
  const { bindModularPart, modularAnimationClips } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const body = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const paths = [
    'assets/modular_human_male_01/gloves/shape_sources/plate-before-thumb-v1.glb',
    'assets/modular_human_male_01/fitted/gloves_plate.glb',
    'client/public/models/characters/modular_male/gloves_plate.glb',
  ]
  const parts = []
  for (const path of paths) parts.push(bindModularPart(body, (await load(path)).scene))
  const [before, after, runtime] = parts
  assert.equal(after.length, 3)
  assert.equal(before.length, after.length)
  assert.equal(runtime.length, after.length)
  const point = new THREE.Vector3(), oldPoint = new THREE.Vector3(), runtimePoint = new THREE.Vector3()
  const changed = after.map((mesh, p) => {
    const old = before[p].geometry, current = mesh.geometry, packed = runtime[p].geometry
    assert.deepEqual(old.index.array, current.index.array)
    for (const name of ['uv', 'skinIndex', 'skinWeight'])
      assert.deepEqual(old.attributes[name]?.array, current.attributes[name]?.array)
    for (const [name, attribute] of Object.entries(current.attributes))
      assert.deepEqual(attribute.array, packed.attributes[name].array)
    const canonicalFaces = index => {
      const faces = []
      for (let i = 0; i < index.count; i += 3) {
        const face = [index.getX(i), index.getX(i + 1), index.getX(i + 2)]
        const first = face.indexOf(Math.min(...face))
        faces.push([...face.slice(first), ...face.slice(0, first)].join(','))
      }
      return faces.sort()
    }
    assert.deepEqual(canonicalFaces(current.index), canonicalFaces(packed.index))
    return Array.from({ length: current.attributes.position.count }, (_, i) =>
      point.fromBufferAttribute(current.attributes.position, i)
        .distanceTo(oldPoint.fromBufferAttribute(old.attributes.position, i)) > 1e-8)
  })
  assert.equal(changed[1].filter(Boolean).length, 0)
  assert.equal(changed[2].filter(Boolean).length, 0)
  const bones = []
  body.traverse(node => { if (node.isBone) bones.push(node) })
  const sampleClip = clipSampler(body, { samples: 25, restore: bones })
  const poses = []
  for (const clip of await loadClips(body, load, modularAnimationClips)) {
    let maximumDisplacement = 0, runtimeDifference = 0
    for (const _ of sampleClip(clip)) {
      for (const meshes of parts) for (const mesh of meshes) mesh.skeleton.update()
      for (let p = 0; p < after.length; p++) {
        const positions = after[p].geometry.attributes.position
        for (let i = 0; i < positions.count; i++) {
          before[p].applyBoneTransform(i, oldPoint.fromBufferAttribute(before[p].geometry.attributes.position, i))
          after[p].applyBoneTransform(i, point.fromBufferAttribute(positions, i))
          runtime[p].applyBoneTransform(i, runtimePoint.fromBufferAttribute(runtime[p].geometry.attributes.position, i))
          for (const p of [point, runtimePoint]) assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z))
          const distance = point.distanceTo(oldPoint)
          if (!changed[p][i]) assert.ok(distance < 1e-7)
          maximumDisplacement = Math.max(maximumDisplacement, distance)
          runtimeDifference = Math.max(runtimeDifference, point.distanceTo(runtimePoint))
        }
      }
    }
    assert.ok(maximumDisplacement < .015)
    assert.ok(runtimeDifference < 1e-7)
    poses.push({ clip: clip.name, samples: 25, maximum_displacement_m: maximumDisplacement, runtime_difference_m: runtimeDifference })
  }
  const report = {
    date: '2026-10-10', sources,
    triangles: after.reduce((sum, mesh) => sum + mesh.geometry.index.count / 3, 0),
    changed_vertices_by_primitive: changed.map(vertices => vertices.filter(Boolean).length),
    preserved: ['topology', 'UV', 'weights', 'cuffs and lining', 'posed positions of unchanged vertices'],
    poses,
    scope: 'Seven canonical clips, 25 poses each; bounded thumb deformation and identical native/runtime geometry. Not an all-pose collision test.',
  }
  writeFileSync(new URL('doc/assets/modular-plate-glove-thumbs-animation-v1.json', root), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
} finally {
  await server.close()
}
