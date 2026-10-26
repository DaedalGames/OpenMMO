import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const directory = 'assets/items/female_rogue_garters/fitted_v1'
const bodyPath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const bootPath = 'assets/items/female_rogue_boots/tripo_v1/fitted_v3/boots_female_rogue.glb'
const skirtPath = 'assets/items/female_rogue_skirt/tripo_v1/fitted_v6/bottom_female_rogue.glb'
const partPath = `${directory}/garters_female_rogue.glb`
const fitting = JSON.parse(readFileSync(`${directory}/fitting.json`))
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { femaleBootGround } = await server.ssrLoadModule('/src/lib/utils/female-boot-ground.ts')
  const { femaleSeatOffset } = await server.ssrLoadModule('/src/previews/female-seat.ts')
  const { updateModularPoseCorrectives } = await server.ssrLoadModule('/src/lib/utils/modularPoseCorrectives.ts')
  const base = await load(bodyPath)
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const i = base.animations.findIndex(entry => entry.name === clip.name)
    if (i < 0) base.animations.push(clip)
    else base.animations[i] = clip
  }
  let body
  base.scene.traverse(object => {
    const association = base.parser.associations.get(object)
    if (object.isSkinnedMesh && association?.meshes === 0 && association.primitives === 0) body = object
  })
  const bootAsset = await load(bootPath)
  const boots = bindModularPart(base.scene, bootAsset.scene)
  const [skirt] = bindModularPart(base.scene, (await load(skirtPath)).scene)
  const parts = bindModularPart(base.scene, (await load(partPath)).scene)
  assert.equal(parts.length, 2)
  const leather = parts.find(mesh => mesh.name.endsWith('_leather'))
  assert.equal(leather.geometry.attributes.position.count, 4*17*4)
  const ground = femaleBootGround(base.scene, body, boots, bootAsset.scene.userData.heel_pose)
  for (const mesh of parts) {
    assert.equal(mesh.skeleton.bones.length, 65)
    for (let i = 0; i < 65; i++) {
      assert.equal(mesh.skeleton.bones[i], body.skeleton.bones[i])
      assert.deepEqual(mesh.skeleton.boneInverses[i].elements, body.skeleton.boneInverses[i].elements)
    }
    const weights = mesh.geometry.attributes.skinWeight
    const joints = mesh.geometry.attributes.skinIndex
    for (let i = 0; i < weights.count; i++) {
      let sum = 0
      for (let k = 0; k < 4; k++) {
        const weight = weights.getComponent(i, k)
        assert.ok(Number.isFinite(weight) && weight >= 0)
        sum += weight
        assert.ok(Number.isInteger(joints.getComponent(i, k)) && joints.getComponent(i, k) < 65)
      }
      assert.ok(Math.abs(sum-1) < 1e-6)
    }
  }
  const p = new THREE.Vector3()
  const center = (mesh, start, count) => {
    const result = new THREE.Vector3()
    for (let i = 0; i < count; i++) result.add(mesh.getVertexPosition(start+i, p))
    return result.divideScalar(count)
  }
  const clips = []
  const sampler = clipSampler(base.scene, { samples: 61, restore: body.skeleton.bones })
  for (const clip of base.animations) {
    updateModularPoseCorrectives(base.scene, clip.name)
    let topError = 0, bottomError = 0
    for (const { sample } of sampler(clip)) {
      ground.apply(clip.name === 'sit_idle' ? femaleSeatOffset : undefined, clip.name)
      for (const mesh of parts) {
        assert.equal(mesh.morphTargetInfluences[mesh.morphTargetDictionary.pose_sit_idle], clip.name === 'sit_idle' ? 1 : 0)
        for (let i = 0; i < mesh.geometry.attributes.position.count; i++)
          assert.ok(mesh.getVertexPosition(i, p).toArray().every(Number.isFinite))
      }
      for (const [i, anchor] of fitting.anchors.entries()) {
        const top = new THREE.Vector3()
        anchor.top_face.forEach((index, k) => top.addScaledVector(skirt.getVertexPosition(index, p), anchor.top_barycentric[k]))
        const bottom = new THREE.Vector3()
        const boot = boots.find(mesh => mesh.name.endsWith(anchor.name.startsWith('right') ? '_right' : '_left'))
        for (const index of anchor.bottom_vertices) bottom.add(boot.getVertexPosition(index, p))
        bottom.divideScalar(anchor.bottom_vertices.length)
        topError = Math.max(topError, top.distanceTo(center(leather, i*68, 4)))
        bottomError = Math.max(bottomError, bottom.distanceTo(center(leather, i*68+64, 4)))
      }
      ground.restore()
    }
    clips.push({ name: clip.name, samples: 61, maximum_skirt_attachment_error_m: topError,
      maximum_boot_attachment_error_m: bottomError })
  }
  const report = { date: '2026-10-26', asset_sha256: hash(partPath), triangles: fitting.triangles,
    exact_65_bone_bind: true, normalized_four_weights: true, finite_deformation: true,
    conditional_seated_morph: true, clips,
    scope: 'Actual preview clips with boot heel and seated leg corrections. Strap cap centers compared to the actual deformed skirt triangles and boot cuff vertices.' }
  writeFileSync(`${directory}/runtime-validation.json`, JSON.stringify(report, null, 2)+'\n')
  console.log(JSON.stringify(report, null, 2))
  assert.ok(clips.every(clip => clip.maximum_skirt_attachment_error_m < .003), 'Skirt attachment separated')
  assert.ok(clips.every(clip => clip.maximum_boot_attachment_error_m < .003), 'Boot attachment separated')
} finally {
  await server.close()
}
