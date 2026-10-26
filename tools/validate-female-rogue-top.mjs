import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const directory = 'assets/items/female_rogue_top/tripo_v1/fitted_v6'
const sourcePath = 'assets/items/female_rogue_top/tripo_v1/fitted_v5/top_female_rogue.glb'
const topPath = `${directory}/top_female_rogue.glb`
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { updateModularPoseCorrectives } = await server.ssrLoadModule('/src/lib/utils/modularPoseCorrectives.ts')
  const { scene: body, animations } = await load(basePath)
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = animations.findIndex(entry => entry.name === clip.name)
    if (index < 0) animations.push(clip)
    else animations[index] = clip
  }
  const [top, ...extra] = bindModularPart(body, (await load(topPath)).scene)
  const [accepted] = bindModularPart(body, (await load(sourcePath)).scene)
  assert.equal(extra.length, 0)
  let reference
  body.traverse(object => { if (object.isSkinnedMesh && !reference) reference = object })
  body.updateMatrixWorld(true)
  const bones = top.skeleton.bones
  assert.equal(bones.length, 65)
  for (let i = 0; i < bones.length; i++) {
    assert.equal(bones[i], reference.skeleton.bones[i])
    assert.deepEqual(top.skeleton.boneInverses[i].elements, reference.skeleton.boneInverses[i].elements)
  }
  const position = top.geometry.attributes.position
  const sourcePosition = accepted.geometry.attributes.position
  const unchanged = Array.from({ length: position.count }, (_, i) =>
    new THREE.Vector3().fromBufferAttribute(position, i).equals(
      new THREE.Vector3().fromBufferAttribute(sourcePosition, i)))
  assert.ok(unchanged.some(value => !value))
  for (let i = 0; i < position.count; i++) {
    if (!unchanged[i]) assert.ok(sourcePosition.getX(i) < -.15)
  }
  for (const name of ['skinIndex', 'skinWeight', 'uv'])
    assert.deepEqual(top.geometry.attributes[name].array, accepted.geometry.attributes[name].array)
  assert.deepEqual(top.geometry.index.array, accepted.geometry.index.array)
  assert.deepEqual(top.geometry.morphAttributes.position[0].array,
    accepted.geometry.morphAttributes.position[0].array)
  const weights = top.geometry.attributes.skinWeight
  const joints = top.geometry.attributes.skinIndex
  const rest = []
  for (let i = 0; i < position.count; i++) {
    const point = top.getVertexPosition(i, new THREE.Vector3())
    assert.ok(point.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 2e-6)
    rest.push(point)
    let sum = 0
    for (let k = 0; k < 4; k++) {
      const value = weights.getComponent(i, k)
      assert.ok(Number.isFinite(value) && value >= 0)
      sum += value
      const joint = joints.getComponent(i, k)
      assert.ok(Number.isInteger(joint) && joint >= 0 && joint < 65)
      if (!value || Math.abs(point.x) < .005) continue
      const name = bones[joint].name
      assert.ok(!(name.startsWith(point.x > 0 ? 'Right' : 'Left') && /Shoulder|Arm/.test(name)))
    }
    assert.ok(Math.abs(sum - 1) < 1e-6)
  }
  const edges = []
  const indices = top.geometry.index
  for (let i = 0; i < indices.count; i += 3)
    for (let k = 0; k < 3; k++) {
      const a = indices.getX(i + k), b = indices.getX(i + (k + 1) % 3)
      const length = rest[a].distanceTo(rest[b])
      if (length > .005) edges.push([a, b, length])
    }
  const samples = clipSampler(body, { samples: 33, restore: bones })
  const snapshots = [], clips = []
  let uneditedMaximumDifference = 0
  for (const clip of animations) {
    updateModularPoseCorrectives(body, clip.name)
    assert.equal(top.morphTargetInfluences[top.morphTargetDictionary.pose_sit_idle], clip.name === 'sit_idle' ? 1 : 0)
    let maximumMotion = 0, maximumEdgeRatio = 0, worstEdge
    for (const { sample, time } of samples(clip)) {
      const posed = rest.map((_, i) => top.getVertexPosition(i, new THREE.Vector3()))
      for (let i = 0; i < posed.length; i++) {
        if (unchanged[i])
          uneditedMaximumDifference = Math.max(uneditedMaximumDifference,
            posed[i].distanceTo(accepted.getVertexPosition(i, new THREE.Vector3())))
      }
      posed.forEach((p, i) => {
        assert.ok(p.toArray().every(Number.isFinite))
        maximumMotion = Math.max(maximumMotion, p.distanceTo(rest[i]))
      })
      for (const [a, b, length] of edges) {
        const ratio = posed[a].distanceTo(posed[b]) / length
        if (ratio > maximumEdgeRatio) {
          maximumEdgeRatio = ratio
          worstEdge = { rest_points: [rest[a].toArray(), rest[b].toArray()], length,
            influences: [a, b].map(i => Array.from({length: 4}, (_, k) => [bones[joints.getComponent(i,k)].name, weights.getComponent(i,k)])) }
        }
      }
      snapshots.push({ clip: clip.name, sample, time, phase: sample / 32,
        matrices: bones.map((bone, i) => new THREE.Matrix4().multiplyMatrices(bone.matrixWorld, top.skeleton.boneInverses[i]).elements) })
    }
    clips.push({ name: clip.name, samples: 33, maximum_motion_m: maximumMotion, maximum_edge_ratio: maximumEdgeRatio, worst_edge: worstEdge })
  }
  writeFileSync(`${directory}/animation-samples.json`, JSON.stringify(snapshots))
  assert.equal(uneditedMaximumDifference, 0)
  const report = { date: '2026-10-26', base_sha256: hash(basePath), top_sha256: hash(topPath),
    triangles: indices.count / 3, vertices: position.count, bones: bones.length,
    exact_runtime_bind: true, normalized_weights: true, finite_deformation: true, no_opposite_arm_influence: true,
    seated_corrective_preserved: true, unedited_vertices_maximum_difference_m: uneditedMaximumDifference,
    changed_vertices: unchanged.filter(value => !value).length,
    source_sha256: hash(sourcePath),
    clips, scope: 'Actual preview clips and modular binding. Right sleeve geometry fitted; unedited vertices match v5 in every clip. Skin weights, UVs, topology and seated position corrective preserved. Clearance and visual review recorded separately.' }
  writeFileSync(`${directory}/animation-validation.json`, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
  assert.ok(clips.every(c => c.maximum_edge_ratio < 5), 'Excessive edge stretching; see worst_edge in report')
} finally {
  await server.close()
}
