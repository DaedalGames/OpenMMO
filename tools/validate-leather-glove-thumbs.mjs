import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, loadClips, clipSampler, root } from './lib/headless-three.mjs'

const { server, sources, load } = await headlessThree()
try {
  const { bindModularPart, modularAnimationClips } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const body = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const before = bindModularPart(body, (await load('assets/modular_human_male_01/gloves/shape_sources/leather-before-thumb-v1.glb')).scene)[0]
  const after = bindModularPart(body, (await load('assets/modular_human_male_01/fitted/gloves_leather.glb')).scene)[0]
  const oldPositions = before.geometry.attributes.position
  const newPositions = after.geometry.attributes.position
  assert.equal(oldPositions.count, newPositions.count)
  assert.deepEqual(before.geometry.index.array, after.geometry.index.array)
  for (const name of ['uv', 'skinIndex', 'skinWeight'])
    assert.deepEqual(before.geometry.attributes[name].array, after.geometry.attributes[name].array)
  const oldPoint = new THREE.Vector3(), newPoint = new THREE.Vector3()
  const changed = Array.from({ length: oldPositions.count }, (_, i) =>
    oldPoint.fromBufferAttribute(oldPositions, i).distanceTo(newPoint.fromBufferAttribute(newPositions, i)) > 1e-8)
  const sides = ['Left', 'Right'].map(side => {
    const indices = changed.flatMap((moved, i) => moved && oldPositions.getX(i) * (side === 'Left' ? 1 : -1) > 0 ? [i] : [])
    assert.ok(indices.length > 0)
    return { side, indices }
  })
  const sampleClip = clipSampler(body, { samples: 25 })
  const poses = []
  for (const clip of await loadClips(body, load, modularAnimationClips)) {
    let maximumDisplacement = 0
    for (const _ of sampleClip(clip)) {
      before.skeleton.update()
      after.skeleton.update()
      for (let i = 0; i < oldPositions.count; i++) {
        before.applyBoneTransform(i, oldPoint.fromBufferAttribute(oldPositions, i))
        after.applyBoneTransform(i, newPoint.fromBufferAttribute(newPositions, i))
        assert.ok(Number.isFinite(newPoint.x) && Number.isFinite(newPoint.y) && Number.isFinite(newPoint.z))
        const distance = oldPoint.distanceTo(newPoint)
        if (!changed[i]) assert.ok(distance < 1e-7)
        else maximumDisplacement = Math.max(maximumDisplacement, distance)
      }
    }
    assert.ok(maximumDisplacement < .031)
    poses.push({ clip: clip.name, samples: 25, maximum_displacement_m: maximumDisplacement })
  }
  const report = {
    date: '2026-10-10', sources,
    triangles: after.geometry.index.count / 3,
    affected_vertices: sides.map(({ side, indices }) => ({ side, count: indices.length })),
    preserved: ['topology', 'UV', 'weights', 'posed positions of unchanged vertices'], poses,
    scope: 'Seven canonical clips, 25 poses each; finite positions and bounded thumb deformation. Not an all-pose collision test.',
  }
  writeFileSync(new URL('doc/assets/modular-leather-glove-thumbs-animation-v1.json', root), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report.poses))
} finally {
  await server.close()
}
