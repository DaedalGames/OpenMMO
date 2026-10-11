import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, loadClips, clipSampler, hash, root } from './lib/headless-three.mjs'

const { server, load, sources } = await headlessThree()
try {
  const { skinnedParts, bindModularPart, showModularOutfit, modularAnimationClips } =
    await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const body = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const top = bindModularPart(body, (await load('assets/modular_human_male_01/bard/tripo_top_v1/top_bard.glb')).scene)[0]
  const pants = bindModularPart(body, (await load('assets/modular_human_male_01/bard/tripo_pants_v1/pants_bard.glb')).scene)[0]
  const original = top.geometry, originalPants = pants.geometry
  const parts = new Map([['top_bard', [top]], ['pants_bard', [pants]]])
  const outfit = { hair: 'none', top: 'bard', pants: 'bard', gloves: 'none', boots: 'none', helmet: 'none' }
  const skin = skinnedParts(body)
  showModularOutfit(skin, parts, outfit)
  assert.notEqual(top.geometry, original)
  assert.equal(pants.geometry, originalPants)
  const fitted = top.geometry
  body.updateMatrixWorld(true)
  const hips = pants.skeleton.bones.find(bone => bone.name === 'Hips')
  const rest = hips.matrixWorld.clone(), frame = new THREE.Matrix4()
  const surface = mesh => {
    const points = Array.from({ length: mesh.geometry.attributes.position.count }, (_, i) =>
      mesh.getVertexPosition(i, new THREE.Vector3()).applyMatrix4(mesh.matrixWorld).applyMatrix4(frame))
    const index = mesh.geometry.index
    return Array.from({ length: index.count / 3 }, (_, i) =>
      [0, 1, 2].map(j => points[index.getX(i * 3 + j)]))
      .filter(face => face.every(p => p.z < -0.02) &&
        Math.min(...face.map(p => p.y)) < 1.14 && Math.max(...face.map(p => p.y)) > 0.9)
  }
  const ray = new THREE.Ray(new THREE.Vector3(), new THREE.Vector3(0, 0, 1))
  const hit = new THREE.Vector3()
  const depth = triangles => {
    let closest = Infinity
    for (const face of triangles) {
      if (ray.intersectTriangle(...face, false, hit)) closest = Math.min(closest, hit.z)
    }
    return closest
  }
  const clips = await loadClips(body, load, modularAnimationClips)
  const sample = clipSampler(body, { samples: 25, restore: pants.skeleton.bones })
  const motion = []
  for (const clip of clips) {
    let minimum = Infinity, compared = 0, worst
    for (const { time } of sample(clip)) {
      pants.skeleton.update()
      frame.copy(rest).multiply(hips.matrixWorld.clone().invert())
      const outer = surface(top), inner = surface(pants)
      for (let x = -0.2; x <= 0.20001; x += 0.01) {
        for (let y = 0.92; y <= 1.14001; y += 0.01) {
          ray.origin.set(x, y, -1)
          const coat = depth(outer), trousers = depth(inner)
          if (!Number.isFinite(coat) || !Number.isFinite(trousers)) continue
          compared++
          const clearance = trousers - coat
          if (clearance < minimum) {
            minimum = clearance
            worst = { time, x, y, coat_z: coat, pants_z: trousers }
          }
        }
      }
    }
    assert.ok(compared > 0)
    motion.push({ clip: clip.name, samples: 25, compared, minimum_clearance_m: minimum, worst })
  }
  showModularOutfit(skin, parts, { ...outfit, top: 'none' })
  assert.equal(top.geometry, original)
  showModularOutfit(skin, parts, outfit)
  assert.equal(top.geometry, fitted)
  parts.delete('pants_bard')
  showModularOutfit(skin, parts, outfit)
  assert.notEqual(top.geometry, fitted)
  const report = { date: '2026-10-11', sources,
    implementation: ['client/src/lib/utils/modularCharacter.ts', 'client/src/lib/utils/modularClothing.ts'].map(path => ({ path, sha256: hash(path) })),
    motion, minimum_clearance_m: Math.min(...motion.map(m => m.minimum_clearance_m)),
    scope: 'Rear overlap on a 10mm Hips-frame XY grid, seven clips at 25 times; only rays intersecting both garments. Includes belt surfaces. Open tails are excluded where no top surface exists; not an exhaustive collision certificate.',
    pants_geometry_unchanged: true, cached_variant_and_restoration: true }
  console.log(JSON.stringify(report, null, 2))
  if (!process.env.MEASURE_ONLY) {
    assert.ok(report.minimum_clearance_m > 0.001, 'Bard vest intersects trousers')
    writeFileSync(new URL('doc/assets/modular-bard-vest-overlap-validation-v1.json', root), JSON.stringify(report, null, 2) + '\n')
  }
} finally {
  await server.close()
}
