import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash, loadClips, CANONICAL_CLIPS_WITH_DYING } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'

const sex = process.argv[2]
assert.ok(['male', 'female'].includes(sex))
const directory = process.argv[3] ?? `assets/items/helm_of_brilliance/tripo_v2/fitted_v1/${sex}`
const fitting = JSON.parse(readFileSync(`${directory}/fitting.json`))
const basePath = fitting.body.path
const partPath = `${directory}/helmet_brilliance.glb`
if (sex === 'female') await ensureFemalePreview('animations')
const { server, load } = await headlessThree()
try {
  const { bindModularPart, modularAnimationClips } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load(basePath)
  const clips = sex === 'female'
    ? [...base.animations]
    : await loadClips(base.scene, load, modularAnimationClips, CANONICAL_CLIPS_WITH_DYING)
  if (sex === 'female')
    for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
      const clip = THREE.AnimationClip.parse(data)
      const index = clips.findIndex(entry => entry.name === clip.name)
      if (index < 0) clips.push(clip)
      else clips[index] = clip
    }
  const bodyMeshes = []
  base.scene.traverse(node => { if (node.isSkinnedMesh) bodyMeshes.push(node) })
  const [helmet, ...others] = bindModularPart(base.scene, (await load(partPath)).scene)
  assert.equal(others.length, 0)
  assert.equal(helmet.geometry.index.count / 3, 3685)
  base.scene.updateMatrixWorld(true)
  const { bones, boneInverses } = helmet.skeleton
  assert.equal(bones.length, 65)
  bones.forEach((bone, index) => {
    assert.equal(bone, bodyMeshes[0].skeleton.bones[index])
    assert.deepEqual(boneInverses[index].elements, bodyMeshes[0].skeleton.boneInverses[index].elements)
  })
  const head = bones.find(bone => bone.name === 'Head')
  const restHead = head.matrixWorld.clone()
  const inverseHead = restHead.clone().invert()
  const { position, skinIndex, skinWeight } = helmet.geometry.attributes
  const rest = [], local = [], edges = []
  for (let i = 0; i < position.count; i++) {
    const point = helmet.getVertexPosition(i, new THREE.Vector3())
    assert.ok(point.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 2e-6)
    assert.equal(bones[skinIndex.getX(i)].name, 'Head')
    assert.deepEqual([skinWeight.getX(i), skinWeight.getY(i), skinWeight.getZ(i), skinWeight.getW(i)], [1, 0, 0, 0])
    rest.push(point)
    local.push(point.clone().applyMatrix4(inverseHead))
  }
  const index = helmet.geometry.index
  for (let i = 0; i < index.count; i += 3)
    for (let corner = 0; corner < 3; corner++) {
      const a = index.getX(i + corner), b = index.getX(i + (corner + 1) % 3)
      const length = rest[a].distanceTo(rest[b])
      if (length > 2e-5) edges.push([a, b, length])
    }
  const probes = bodyMeshes.flatMap(mesh => {
    if (sex === 'male' && !['head', 'neck', 'torso', 'upper_arms'].includes(mesh.userData.region)) return []
    const attributes = mesh.geometry.attributes
    return Array.from({ length: attributes.position.count }, (_, i) => i)
      .filter(i => attributes.position.getY(i) > fitting.brow_y - .40)
      .map(i => ({ mesh, i, rigid: [0, 1, 2, 3].some(k =>
        mesh.skeleton.bones[attributes.skinIndex.getComponent(i, k)].name === 'Head' &&
        attributes.skinWeight.getComponent(i, k) >= .999999) }))
  })
  const movingProbes = probes.filter(probe => !probe.rigid)
  const lookup = new Map(bodyMeshes.map(mesh => [mesh, new Map()]))
  probes.forEach(({ mesh, i }, global) => lookup.get(mesh).set(i, global))
  const skinFaces = []
  for (const mesh of bodyMeshes) {
    const index = mesh.geometry.index
    const mapping = lookup.get(mesh)
    for (let i = 0; i < index.count; i += 3) {
      const face = [0, 1, 2].map(k => mapping.get(index.getX(i + k)))
      if (face.every(vertex => vertex !== undefined)) skinFaces.push(face)
    }
  }
  writeFileSync(`${directory}/skin-topology.json.gz`, gzipSync(JSON.stringify({
    faces: skinFaces, moving_indices: probes.flatMap((probe, i) => probe.rigid ? [] : [i]),
  })))
  const snapshots = [], clearance = [], reportClips = []
  const temporary = new THREE.Vector3()
  const toRest = new THREE.Matrix4()
  const recordPose = (name, time) => {
    base.scene.updateMatrixWorld(true)
    helmet.skeleton.update()
    toRest.copy(restHead).multiply(head.matrixWorld.clone().invert())
    clearance.push({ name, time, points: (name === 'rest' ? probes : movingProbes).map(({ mesh, i }) =>
      mesh.getVertexPosition(i, temporary).applyMatrix4(toRest).toArray()) })
  }
  recordPose('rest', 0)
  const restRotation = head.quaternion.clone()
  for (const [name, axis, angle] of [
    ['look-left', new THREE.Vector3(0, 1, 0), Math.PI / 4],
    ['look-right', new THREE.Vector3(0, 1, 0), -Math.PI / 4],
    ['look-up', new THREE.Vector3(1, 0, 0), -Math.PI / 9],
    ['look-down', new THREE.Vector3(1, 0, 0), Math.PI / 9],
  ]) {
    head.quaternion.copy(restRotation).multiply(new THREE.Quaternion().setFromAxisAngle(axis, angle))
    recordPose(name, 0)
    snapshots.push({ clip: name, time: 0,
      bone_deformation_matrices: Object.fromEntries(bones.map((bone, i) => [bone.name,
        new THREE.Matrix4().multiplyMatrices(bone.matrixWorld, boneInverses[i]).toArray()])),
    })
  }
  head.quaternion.copy(restRotation)
  base.scene.updateMatrixWorld(true)
  const sampler = clipSampler(base.scene, { samples: 33, restore: bones })
  for (const clip of clips) {
    let attachmentError = 0, rigidError = 0
    for (const { sample, time } of sampler(clip)) {
      const points = rest.map((_, i) => helmet.getVertexPosition(i, new THREE.Vector3()))
      for (let i = 0; i < points.length; i++) {
        assert.ok(points[i].toArray().every(Number.isFinite))
        attachmentError = Math.max(attachmentError, points[i].distanceTo(local[i].clone().applyMatrix4(head.matrixWorld)))
      }
      for (const [a, b, length] of edges)
        rigidError = Math.max(rigidError, Math.abs(points[a].distanceTo(points[b]) / length - 1))
      recordPose(clip.name, time)
      if (sample === 16) snapshots.push({
        clip: clip.name, time,
        bone_deformation_matrices: Object.fromEntries(bones.map((bone, i) => [bone.name,
          new THREE.Matrix4().multiplyMatrices(bone.matrixWorld, boneInverses[i]).toArray()])),
      })
    }
    assert.ok(attachmentError < 2e-5, `${clip.name}: detached helmet`)
    assert.ok(rigidError < 1e-4, `${clip.name}: metal deformed`)
    reportClips.push({ name: clip.name, samples: 33, maximum_attachment_error_m: attachmentError, maximum_rigid_error_relative: rigidError })
  }
  const report = {
    date: '2026-10-17', sex, body_sha256: hash(basePath), helmet_sha256: hash(partPath),
    triangles: 3685, bones: 65, exact_bind_compatibility: true, head_weight: 1,
    clips: reportClips, skin_probe_vertices: probes.length, moving_skin_probe_vertices: movingProbes.length,
    scope: 'Runtime modular binding, rigid attachment and finite animation checked. Skin clearance and rendered appearance reviewed separately.',
  }
  writeFileSync(`${directory}/animation-validation.json`, JSON.stringify(report, null, 2) + '\n')
  writeFileSync(`${directory}/animation-snapshots.json`, JSON.stringify(snapshots) + '\n')
  writeFileSync(`${directory}/skin-motion.json.gz`, gzipSync(JSON.stringify(clearance)))
  console.log(JSON.stringify(report))
} finally {
  await server.close()
}
