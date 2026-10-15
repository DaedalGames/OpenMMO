import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const directory = 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
const base = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { updatePeltPhysics, disposePeltPhysics } = await server.ssrLoadModule('/src/lib/effects/pelt-rig.ts')
  const results = []
  for (const filename of ['thigh_contact_v1/before.glb', 'bottom_female_barbarian.glb']) {
    const path = `${directory}/${filename}`
    const { scene: body, animations } = await load(base)
    let skin
    body.traverse(object => { if (object.isSkinnedMesh && !skin) skin = object })
    const parts = bindModularPart(body, (await load(path)).scene)
    const references = new Map(parts.map(mesh => [mesh, mesh.geometry.attributes.position.clone()]))
    const sample = clipSampler(body, { samples: 3, restore: skin.skeleton.bones })
    const records = []
    for (const { sample: index } of sample(animations.find(clip => clip.name === 'combat_idle'))) {
      updatePeltPhysics(body, 0, null, 1 / 60, true)
      skin.computeBoundingSphere()
      const hip = new THREE.Matrix4().multiplyMatrices(skin.skeleton.bones[0].matrixWorld, skin.skeleton.boneInverses[0])
      const record = { sample: index }
      for (const panel of ['left', 'right']) {
        const camera = new THREE.Vector3(panel === 'left' ? .48 : -.48, .65, .30).applyMatrix4(hip)
        const ray = new THREE.Raycaster()
        const mesh = parts.find(part => part.userData.panel === panel)
        const reference = references.get(mesh), indices = mesh.geometry.index
        let checked = 0, occluded = 0, maximumDepth = 0
        const triangles = mesh.userData.pelt_physics.bend.constraint_triangles ?? indices.count / 3
        for (let i = 0; i < triangles * 3; i += 3) {
          const rest = new THREE.Vector3(), point = new THREE.Vector3()
          for (let k = 0; k < 3; k++) {
            rest.add(new THREE.Vector3().fromBufferAttribute(reference, indices.getX(i + k)))
            point.add(mesh.getVertexPosition(indices.getX(i + k), new THREE.Vector3()))
          }
          rest.divideScalar(3)
          point.divideScalar(3)
          if (rest.z < .015 || rest.y < .525 || rest.y > .56) continue
          checked++
          ray.set(camera, point.clone().sub(camera).normalize())
          const hit = ray.intersectObject(skin, false)[0]
          if (!hit) continue
          const depth = camera.distanceTo(point) - hit.distance
          if (depth > .001) {
            occluded++
            maximumDepth = Math.max(maximumDepth, depth)
          }
        }
        record[panel] = { checked, occluded, maximum_depth: maximumDepth }
      }
      records.push(record)
    }
    disposePeltPhysics(body)
    results.push({ path, sha256: hash(path), records })
  }
  for (const [i, record] of results[1].records.entries()) {
    assert.equal(record.left.checked, 37)
    assert.equal(record.right.checked, 24)
    assert.ok(record.left.occluded <= 2)
    assert.equal(record.right.occluded, 0)
    assert.ok(record.left.occluded < results[0].records[i].left.occluded)
  }
  const report = {
    base: { path: base, sha256: hash(base) },
    scope: 'Three combat-idle poses; upper front side-pelt triangle centroids viewed from each side against the actual posed body. Depth tolerance 1 mm. Two left root samples remain occluded; not a complete surface or animation collision audit.',
    results,
  }
  writeFileSync('doc/assets/modular-female-barbarian-thigh-contact-v1.json', JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(results.map(result => ({ path: result.path, occluded: result.records.map(record => [record.left.occluded, record.right.occluded]) }))))
} finally {
  await server.close()
}
