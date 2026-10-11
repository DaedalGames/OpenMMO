import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, hash, clipSampler } from './lib/headless-three.mjs'

const directory = 'assets/modular_human_female_01/rig_v1/'
const originalPath = 'assets/modular_human_female_01/ear_normals_v2/base-ear-normals-v2.glb'
const path = directory + 'female-base.glb'
const raw = path => {
  const bytes = readFileSync(new URL('../' + path, import.meta.url))
  const length = bytes.readUInt32LE(12)
  return { doc: JSON.parse(bytes.subarray(20, 20 + length)), binary: bytes.subarray(28 + length) }
}
const before = raw(originalPath), after = raw(path)
assert.deepEqual(after.doc.materials, before.doc.materials)
assert.deepEqual(after.doc.textures, before.doc.textures)
assert.deepEqual(after.doc.images, before.doc.images)
for (const image of before.doc.images) {
  const view = before.doc.bufferViews[image.bufferView]
  const start = view.byteOffset ?? 0
  assert.deepEqual(after.binary.subarray(start, start + view.byteLength), before.binary.subarray(start, start + view.byteLength))
}
const { server, load } = await headlessThree()
try {
  const original = await load(originalPath), result = await load(path)
  const originalMeshes = [], meshes = []
  original.scene.traverse(n => { if (n.isMesh) originalMeshes.push(n) })
  result.scene.traverse(n => { if (n.isSkinnedMesh) meshes.push(n) })
  assert.equal(meshes.length, originalMeshes.length)
  assert.equal(result.animations.length, 8)
  const bones = meshes[0].skeleton.bones
  assert.equal(bones.length, 65)
  const p = new THREE.Vector3(), q = new THREE.Vector3()
  let restError = 0, weightError = 0, usedVertices = 0
  const samples = meshes.map((mesh, index) => {
    const old = originalMeshes[index]
    for (const attribute of ['position', 'normal', 'uv'])
      assert.deepEqual(mesh.geometry.attributes[attribute]?.array, old.geometry.attributes[attribute]?.array, attribute)
    assert.deepEqual(mesh.geometry.index.array, old.geometry.index.array)
    const indices = [...new Set(mesh.geometry.index.array)]
    usedVertices += indices.length
    mesh.skeleton.update()
    for (const i of indices) {
      p.fromBufferAttribute(mesh.geometry.attributes.position, i)
      q.copy(p)
      mesh.applyBoneTransform(i, q)
      restError = Math.max(restError, p.distanceTo(q))
      const w = mesh.geometry.attributes.skinWeight, j = mesh.geometry.attributes.skinIndex
      const weights = [w.getX(i), w.getY(i), w.getZ(i), w.getW(i)]
      weightError = Math.max(weightError, Math.abs(weights.reduce((a, b) => a + b) - 1))
      for (const v of weights) assert.ok(Number.isFinite(v) && v >= 0 && v <= 1)
      for (const v of [j.getX(i), j.getY(i), j.getZ(i), j.getW(i)]) assert.ok(v < bones.length)
    }
    return { mesh, indices }
  })
  assert.ok(restError < 1e-6, 'Rest surface drift')
  assert.ok(weightError < 1e-6, 'Unnormalized weights')
  const sampler = clipSampler(result.scene, { samples: 121, restore: bones })
  const poses = [], checks = []
  const minimumTimes = []
  for (const clip of result.animations) {
    assert.ok(clip.validate())
    let minY = Infinity, maxFloor = -Infinity, maxExtent = 0, facialError = 0
    const times = []
    for (const { sample, time } of sampler(clip)) {
      let floor = Infinity
      const box = new THREE.Box3()
      const headDelta = new THREE.Matrix4().multiplyMatrices(
        result.scene.getObjectByName('Head').matrixWorld,
        meshes[0].skeleton.boneInverses[bones.findIndex(b => b.name === 'Head')]
      )
      for (const { mesh, indices } of samples) {
        mesh.skeleton.update()
        for (const i of indices) {
          p.fromBufferAttribute(mesh.geometry.attributes.position, i)
          const face = p.y > .889
          q.copy(p).applyMatrix4(headDelta)
          mesh.applyBoneTransform(i, p).applyMatrix4(mesh.matrixWorld)
          assert.ok(p.toArray().every(Number.isFinite), clip.name)
          floor = Math.min(floor, p.y)
          box.expandByPoint(p)
          if (face) facialError = Math.max(facialError, p.distanceTo(q))
        }
      }
      minY = Math.min(minY, floor)
      maxFloor = Math.max(maxFloor, floor)
      maxExtent = Math.max(maxExtent, box.getSize(q).length())
      times.push({ time, floor })
      if ([0, 48, 90, 120].includes(sample)) {
        const skeleton = meshes[0].skeleton
        poses.push({ clip: clip.name, fraction: sample / 120, time,
          bone_deformation_matrices: Object.fromEntries(skeleton.bones.map((b, i) => [b.name,
            new THREE.Matrix4().multiplyMatrices(b.matrixWorld, skeleton.boneInverses[i]).toArray()])) })
      }
    }
    assert.ok(minY > -.002, `${clip.name} penetrates the floor: ${minY}`)
    assert.ok(minY < .002, `${clip.name} never reaches the floor: ${minY}`)
    assert.ok(maxExtent < 2, `${clip.name} has an exploded surface`)
    assert.ok(facialError < 1e-6, `${clip.name} distorts the face`)
    const check = { clip: clip.name, frames: 121, minimum_y: minY, maximum_floor_y: maxFloor, maximum_extent: maxExtent, maximum_face_rigid_error: facialError }
    checks.push(check); minimumTimes.push({ clip: clip.name, times })
    console.log(JSON.stringify(check))
  }
  const report = { source: { path: originalPath, sha256: hash(originalPath) }, output: { path, sha256: hash(path) },
    bone_count: bones.length, used_vertices: usedVertices, unchanged_geometry_normals_uv_indices: true, unchanged_materials_and_embedded_images: true,
    maximum_rest_error: restError, maximum_weight_sum_error: weightError, clips: checks }
  writeFileSync(new URL('../' + directory + 'validation.json', import.meta.url), JSON.stringify(report, null, 2) + '\n')
  writeFileSync(new URL('../' + directory + 'animation-snapshots.json', import.meta.url), JSON.stringify(poses) + '\n')
  writeFileSync(new URL('../' + directory + 'floor-samples.json', import.meta.url), JSON.stringify(minimumTimes) + '\n')
  assert.equal(meshes.reduce((sum, mesh) => sum + mesh.geometry.index.count / 3, 0), 22175)
} finally { await server.close() }
