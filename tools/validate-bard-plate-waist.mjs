import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, loadClips, clipSampler, hash, root } from './lib/headless-three.mjs'

function sectionHeights(surfaces, x, front) {
  const heights = []
  for (const { points, index } of surfaces) {
    for (let i = 0; i < index.count; i += 3) {
      const vertices = [0, 1, 2].map(j => points[index.getX(i + j)])
      for (let j = 0; j < 3; j++) {
        const a = vertices[j], b = vertices[(j + 1) % 3]
        if ((a.x - x) * (b.x - x) > 0 || Math.abs(a.x - b.x) < 1e-8) continue
        const t = (x - a.x) / (b.x - a.x)
        const y = THREE.MathUtils.lerp(a.y, b.y, t)
        const z = THREE.MathUtils.lerp(a.z, b.z, t)
        if (y > 0.85 && y < 1.18 && (front ? z > 0.02 : z < -0.065)) heights.push(y)
      }
    }
  }
  assert.ok(heights.length, `Missing ${front ? 'front' : 'back'} section at ${x}`)
  return heights
}

function rearClearance(armor, trousers) {
  const triangles = armor.flatMap(({ points, index }) =>
    Array.from({ length: index.count / 3 }, (_, i) =>
      [0, 1, 2].map(j => points[index.getX(i * 3 + j)])))
    .filter(vertices => vertices.every(point => point.z < -0.03) &&
      Math.min(...vertices.map(point => point.y)) < 1.16)
  const { points, index } = trousers
  const samples = [...points]
  for (let i = 0; i < index.count; i += 3) {
    const vertices = [0, 1, 2].map(j => points[index.getX(i + j)])
    if (vertices.every(point => point.y < 0.88 || point.z > -0.04)) continue
    samples.push(vertices.reduce((sum, point) => sum.add(point), new THREE.Vector3()).divideScalar(3))
    for (let j = 0; j < 3; j++) samples.push(vertices[j].clone().lerp(vertices[(j + 1) % 3], 0.5))
  }
  let minimum = Infinity, compared = 0, worst
  for (const point of samples) {
    if (point.z > -0.04 || point.y < 0.88 || point.y > 1.16 || Math.abs(point.x) > 0.21) continue
    let outer = Infinity
    for (const [a, b, c] of triangles) {
      const denominator = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
      if (Math.abs(denominator) < 1e-10) continue
      const u = ((b.y - c.y) * (point.x - c.x) + (c.x - b.x) * (point.y - c.y)) / denominator
      const v = ((c.y - a.y) * (point.x - c.x) + (a.x - c.x) * (point.y - c.y)) / denominator
      if (u < 0 || v < 0 || u + v > 1) continue
      outer = Math.min(outer, u * a.z + v * b.z + (1 - u - v) * c.z)
    }
    if (!Number.isFinite(outer)) continue
    compared++
    if (point.z - outer < minimum) {
      minimum = point.z - outer
      worst = { pants: point.toArray(), armor_z: outer }
    }
  }
  assert.ok(compared > 0)
  return { minimum, compared, worst }
}

const { server, load, sources } = await headlessThree()
try {
  const { skinnedParts, bindModularPart, showModularOutfit, modularAnimationClips } =
    await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const body = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const skin = skinnedParts(body)
  const pants = bindModularPart(body, (await load('assets/modular_human_male_01/bard/tripo_pants_v1/pants_bard.glb')).scene)[0]
  const top = bindModularPart(body, (await load('assets/modular_human_male_01/fitted/top_plate.glb')).scene)
  const original = pants.geometry, parts = new Map([['pants_bard', [pants]], ['top_plate', top]])
  const outfit = { hair: 'none', top: 'plate', pants: 'bard', gloves: 'none', boots: 'none', helmet: 'none' }
  showModularOutfit(skin, parts, outfit)
  const fitted = pants.geometry
  assert.notEqual(fitted, original)
  for (let i = 0; i < fitted.attributes.skinWeight.count; i++) {
    const weight = [0, 1, 2, 3].reduce((sum, j) => sum + fitted.attributes.skinWeight.getComponent(i, j), 0)
    assert.ok(Math.abs(weight - 1) < 1e-6)
  }
  body.updateMatrixWorld(true)
  const hips = pants.skeleton.bones.find(bone => bone.name === 'Hips')
  const rest = hips.matrixWorld.clone(), frame = new THREE.Matrix4()
  const surface = mesh => ({
    index: mesh.geometry.index,
    points: Array.from({ length: mesh.geometry.attributes.position.count }, (_, i) => {
      const point = mesh.getVertexPosition(i, new THREE.Vector3()).applyMatrix4(mesh.matrixWorld).applyMatrix4(frame)
      assert.ok(point.toArray().every(Number.isFinite))
      return point
    }),
  })
  const clips = await loadClips(body, load, modularAnimationClips)
  const sample = clipSampler(body, { samples: 25, restore: pants.skeleton.bones })
  const motion = []
  for (const clip of clips) {
    let minimum = Infinity, worst, rearMinimum = Infinity, rearWorst, rearCompared = 0
    for (const { time } of sample(clip)) {
      pants.skeleton.update()
      frame.copy(rest).multiply(hips.matrixWorld.clone().invert())
      const armor = top.map(surface), trousers = [surface(pants)]
      const rear = rearClearance(armor, trousers[0])
      assert.ok(rear.minimum > 0.001, `${clip.name} rear penetration at ${time}: ${rear.minimum}`)
      rearCompared += rear.compared
      if (rear.minimum < rearMinimum) {
        rearMinimum = rear.minimum
        rearWorst = { time, ...rear.worst }
      }
      for (const x of [-0.08, -0.04, 0, 0.04, 0.08]) {
        for (const front of [true, false]) {
          const lowerArmor = Math.min(...sectionHeights(armor, x, front))
          const upperPants = Math.max(...sectionHeights(trousers, x, front))
          const overlap = upperPants - lowerArmor
          assert.ok(overlap > 0.002, `${clip.name} at ${time}, x=${x}, front=${front}: ${overlap}`)
          if (overlap < minimum) {
            minimum = overlap
            worst = { time, x, front, armor_min_y: lowerArmor, pants_max_y: upperPants }
          }
        }
      }
    }
    motion.push({ clip: clip.name, samples: 25, minimum_vertical_overlap_m: minimum, worst,
      minimum_rear_depth_clearance_m: rearMinimum, rear_compared_samples: rearCompared, rear_worst: rearWorst })
  }
  for (const style of ['none', 'bard', 'linen']) {
    showModularOutfit(skin, parts, { ...outfit, top: style })
    assert.equal(pants.geometry, original)
  }
  showModularOutfit(skin, parts, outfit)
  assert.equal(pants.geometry, fitted)
  parts.delete('top_plate')
  showModularOutfit(skin, parts, outfit)
  assert.equal(pants.geometry, original)
  const report = {
    date: '2026-10-11', sources,
    implementation: ['client/src/lib/utils/modularClothing.ts', 'client/src/lib/utils/modularCharacter.ts'].map(path => ({ path, sha256: hash(path) })),
    motion, poses: 175, front_back_sections: 1750,
    minimum_vertical_overlap_m: Math.min(...motion.map(entry => entry.minimum_vertical_overlap_m)),
    minimum_rear_depth_clearance_m: Math.min(...motion.map(entry => entry.minimum_rear_depth_clearance_m)),
    original_triangles: original.index.count / 3, fitted_triangles: fitted.index.count / 3,
    normalized_weights: true, cached_variant_and_source_restoration: true,
    scope: 'Hips-frame vertical overlap in five front/back sections plus rear depth against the outer armor surface at pants vertices, face centers and edge midpoints. Sampled poses and surfaces; not an exhaustive triangle collision certificate.',
  }
  writeFileSync(new URL('doc/assets/modular-bard-plate-waist-validation-v1.json', root), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
} finally {
  await server.close()
}
