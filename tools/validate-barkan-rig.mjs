import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { GLTFLoader } from '../client/node_modules/three/examples/jsm/loaders/GLTFLoader.js'

const root = new URL('../', import.meta.url)
const game = process.argv.includes('--game')
const modelPath = game ? 'client/public/models/monsters/barkan.glb' : 'assets/monsters/barkan/rig_v1/barkan.glb'
const sourcePath = 'assets/monsters/barkan/tripo_v2/wing_holes.glb'
const read = path => readFileSync(new URL(path, root))
const container = path => {
  const bytes = read(path), length = bytes.readUInt32LE(12)
  return { doc: JSON.parse(bytes.subarray(20, 20 + length)), binary: bytes.subarray(28 + length) }
}
const imageHashes = ({ doc, binary }) => Object.fromEntries(doc.images.map(image => {
  const view = doc.bufferViews[image.bufferView]
  const offset = view.byteOffset ?? 0
  return [image.name, createHash('sha256').update(binary.subarray(offset, offset + view.byteLength)).digest('hex')]
}))
const raw = container(modelPath)
assert.deepEqual(imageHashes(raw), imageHashes(container(sourcePath)))
for (const node of raw.doc.nodes) assert.deepEqual(node.scale ?? [1, 1, 1], [1, 1, 1], node.name)
assert.ok(raw.doc.animations.every(animation => animation.channels.every(channel => channel.target.path !== 'scale')))
globalThis.self = globalThis
const loader = new GLTFLoader().register(() => ({ name: 'geometry-only', loadMaterial: async () => new THREE.MeshBasicMaterial() }))
const load = path => {
  const bytes = read(path)
  return loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')
}
const result = await load(modelPath)
const meshes = []
result.scene.traverse(node => { if (node.isSkinnedMesh) meshes.push(node) })
assert.equal(meshes.length, 1)
const mesh = meshes[0], geometry = mesh.geometry
assert.equal(geometry.index.count / 3, 12086)
assert.equal(mesh.skeleton.bones.length, 103)
const bones = mesh.skeleton.bones
const rest = bones.map(bone => ({ bone, p: bone.position.clone(), q: bone.quaternion.clone(), s: bone.scale.clone() }))
result.scene.updateMatrixWorld(true)
const segments = bones.filter(bone => bone.parent?.isBone).map(bone => ({ bone,
  length: bone.getWorldPosition(new THREE.Vector3()).distanceTo(bone.parent.getWorldPosition(new THREE.Vector3())) }))
const used = [...new Set(geometry.index.array)]
const vertex = new THREE.Vector3(), original = new THREE.Vector3()
const snapshot = () => {
  result.scene.updateMatrixWorld(true)
  mesh.skeleton.update()
  const box = new THREE.Box3(), values = new Float32Array(used.length * 3)
  for (const [index, id] of used.entries()) {
    mesh.getVertexPosition(id, vertex).applyMatrix4(mesh.matrixWorld)
    assert.ok(vertex.toArray().every(Number.isFinite))
    box.expandByPoint(vertex)
    vertex.toArray(values, index * 3)
  }
  return { box, values }
}
const bind = snapshot()
assert.ok(Math.abs(bind.box.getSize(new THREE.Vector3()).y - 2.5) < 1e-4)
assert.ok(Math.abs(bind.box.min.y) < 1e-4)
let weightError = 0, bindError = 0
for (const id of used) {
  original.fromBufferAttribute(geometry.attributes.position, id).applyMatrix4(mesh.matrixWorld)
  mesh.getVertexPosition(id, vertex).applyMatrix4(mesh.matrixWorld)
  bindError = Math.max(bindError, original.distanceTo(vertex))
  const weights = Array.from(geometry.attributes.skinWeight.array.subarray(id * 4, id * 4 + 4))
  const joints = Array.from(geometry.attributes.skinIndex.array.subarray(id * 4, id * 4 + 4))
  assert.ok(weights.every(weight => Number.isFinite(weight) && weight >= 0 && weight <= 1))
  assert.ok(joints.every(index => index >= 0 && index < bones.length))
  weightError = Math.max(weightError, Math.abs(weights.reduce((a, b) => a + b) - 1))
}
assert.ok(bindError < .0001, `Bind drift ${bindError}`)
assert.ok(weightError < 1e-6)
assert.deepEqual(result.animations.map(clip => clip.name).sort(), game ? ['Attack', 'Death', 'Idle', 'Walk'] : ['Idle', 'Walk', 'WingFold'])
if (game) {
  const def = JSON.parse(read('data/monsters.json')).barkan
  assert.equal(def.model, 'monsters/barkan.glb')
  assert.equal(def.scale ?? 1, 1)
  assert.equal(def.walkSpeed, 3)
  assert.equal(def.runSpeed, 3)
  assert.equal(def.animRun, 'Walk')
  assert.ok(!def.weapon)
  const clips = new Set(result.animations.map(clip => clip.name))
  for (const [key, value] of Object.entries(def)) if (key.startsWith('anim') && value) assert.ok(clips.has(value), `${key}: ${value}`)
  const dungeon = JSON.parse(read('data/dungeons.json')).sundered_bastion
  assert.equal(dungeon.chestTier, 5)
  assert.equal(dungeon.floors, 25)
  assert.equal(dungeon.boss, 'barkan')
}
const mixer = new THREE.AnimationMixer(result.scene)
const restore = () => {
  mixer.stopAllAction()
  for (const { bone, p, q, s } of rest) { bone.position.copy(p); bone.quaternion.copy(q); bone.scale.copy(s) }
  result.scene.updateMatrixWorld(true)
}
const checks = []
const idlePosture = { maximum_torso_tilt_degrees: 0, maximum_arm_abduction_degrees: 0,
  maximum_hand_height_above_hips_m: -Infinity, minimum_hand_separation_m: Infinity,
  maximum_head_motion_degrees: 0, loop_max_vertex_gap_m: 0 }
let idleHeadStart
const fingerChecks = []
for (const side of ['Left', 'Right']) {
  for (const finger of ['Thumb', 'Index', 'Middle', 'Ring']) {
    restore()
    const name = `${side}Hand${finger}`
    const end = result.scene.getObjectByName(`${name}4`).getWorldPosition(new THREE.Vector3())
    const ids = used.filter(id => original.fromBufferAttribute(geometry.attributes.position, id).applyMatrix4(mesh.matrixWorld).distanceTo(end) < .025)
    assert.ok(ids.length >= 3, `${name}: tip surface missing`)
    const before = ids.map(id => mesh.getVertexPosition(id, new THREE.Vector3()).applyMatrix4(mesh.matrixWorld))
    let ownWeight = 1
    for (const id of ids) {
      let sum = 0
      for (let k = 0; k < 4; k++) {
        if (bones[geometry.attributes.skinIndex.array[id * 4 + k]].name.startsWith(name)) sum += geometry.attributes.skinWeight.array[id * 4 + k]
      }
      ownWeight = Math.min(ownWeight, sum)
    }
    assert.ok(ownWeight > .8, `${name}: tip weight ${ownWeight}`)
    result.scene.getObjectByName(`${name}2`).rotateX(Math.PI / 4)
    result.scene.updateMatrixWorld(true); mesh.skeleton.update()
    const movement = Math.max(...ids.map((id, index) => mesh.getVertexPosition(id, vertex).applyMatrix4(mesh.matrixWorld).distanceTo(before[index])))
    assert.ok(movement > .003, `${name}: joint does not bend its fingertip`)
    fingerChecks.push({ name, tip_vertices: ids.length, minimum_own_weight: ownWeight, bend_movement_m: movement })
  }
}
restore()
for (const clip of result.animations) {
  assert.ok(clip.validate(), clip.name)
  restore()
  const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1)
  action.clampWhenFinished = true
  action.play()
  let floorMin = Infinity, floorMax = -Infinity, diagonal = 0
  const frames = Math.ceil(clip.duration * 24)
  let wingMotion = 0, bodyMotion = 0
  let firstPose, loopGap = 0
  let boneLengthError = 0
  const rootBounds = new THREE.Box3()
  for (let frame = 0; frame <= frames; frame++) {
    mixer.setTime(Math.min(clip.duration, frame / 24))
    const pose = snapshot()
    for (const { bone, length } of segments) {
      const currentLength = bone.getWorldPosition(new THREE.Vector3()).distanceTo(bone.parent.getWorldPosition(new THREE.Vector3()))
      boneLengthError = Math.max(boneLengthError, Math.abs(currentLength - length))
    }
    rootBounds.expandByPoint(result.scene.getObjectByName('Hips').getWorldPosition(new THREE.Vector3()))
    if (clip.name === 'Idle') {
      const point = name => result.scene.getObjectByName(name).getWorldPosition(new THREE.Vector3())
      const hips = point('Hips'), torso = point('Neck').sub(hips)
      idlePosture.maximum_torso_tilt_degrees = Math.max(idlePosture.maximum_torso_tilt_degrees,
        THREE.MathUtils.radToDeg(Math.atan2(Math.hypot(torso.x, torso.z), torso.y)))
      for (const side of ['Left', 'Right']) {
        const arm = point(`${side}ForeArm`).sub(point(`${side}Arm`))
        idlePosture.maximum_arm_abduction_degrees = Math.max(idlePosture.maximum_arm_abduction_degrees,
          THREE.MathUtils.radToDeg(Math.atan2(Math.hypot(arm.x, arm.z), -arm.y)))
        idlePosture.maximum_hand_height_above_hips_m = Math.max(idlePosture.maximum_hand_height_above_hips_m,
          point(`${side}Hand`).y - hips.y)
      }
      idlePosture.minimum_hand_separation_m = Math.min(idlePosture.minimum_hand_separation_m,
        point('LeftHand').distanceTo(point('RightHand')))
      const head = result.scene.getObjectByName('Head').getWorldQuaternion(new THREE.Quaternion())
      idleHeadStart ??= head.clone()
      idlePosture.maximum_head_motion_degrees = Math.max(idlePosture.maximum_head_motion_degrees,
        THREE.MathUtils.radToDeg(head.angleTo(idleHeadStart)))
    }
    firstPose ??= pose.values.slice()
    if (frame === frames) {
      for (let index = 0; index < pose.values.length; index += 3) {
        loopGap = Math.max(loopGap,
          Math.hypot(...pose.values.subarray(index, index + 3).map((value, axis) => value - firstPose[index + axis])))
      }
      if (clip.name === 'Idle') idlePosture.loop_max_vertex_gap_m = loopGap
    }
    floorMin = Math.min(floorMin, pose.box.min.y)
    floorMax = Math.max(floorMax, pose.box.min.y)
    diagonal = Math.max(diagonal, pose.box.getSize(new THREE.Vector3()).length())
    if (clip.name === 'WingFold' && frame === 24) {
      for (const [index, id] of used.entries()) {
        const offset = index * 3
        const movement = Math.hypot(...pose.values.subarray(offset, offset + 3).map((v, k) => v - bind.values[offset + k]))
        original.fromBufferAttribute(geometry.attributes.position, id)
        if (original.z < -.5 && original.y > 1.5) wingMotion = Math.max(wingMotion, movement)
        if (original.z > -.15 && original.y < 2.2) bodyMotion = Math.max(bodyMotion, movement)
      }
    }
  }
  assert.ok(Math.abs(floorMin) < .0002 && Math.abs(floorMax) < .0002, `${clip.name}: ground ${floorMin} to ${floorMax}`)
  assert.ok(boneLengthError < .0001, `${clip.name}: bone length changes by ${boneLengthError}m`)
  assert.ok(diagonal < (['Attack', 'Death'].includes(clip.name) ? 5 : 4.5), `${clip.name}: mesh stretches beyond expected bounds`)
  if (clip.name === 'Walk') {
    assert.ok(rootBounds.max.x - rootBounds.min.x < .18, `Walk lateral sway: ${rootBounds.max.x - rootBounds.min.x}m`)
    assert.ok(Math.max(Math.abs(rootBounds.min.x), Math.abs(rootBounds.max.x)) < .1, 'Walk must stay centered')
    assert.ok(loopGap < .001, `Walk loop gap: ${loopGap}m`)
  }
  if (clip.name === 'WingFold') {
    assert.ok(wingMotion > .3, `Wing motion ${wingMotion}`)
    assert.ok(bodyMotion < .0001, `Wing fold moves the body ${bodyMotion}`)
  }
  checks.push({ clip: clip.name, duration: clip.duration, frames: frames + 1,
    floor_min_m: floorMin, floor_max_m: floorMax, maximum_diagonal_m: diagonal, loop_max_vertex_gap_m: loopGap,
    root_min_m: rootBounds.min.toArray(), root_max_m: rootBounds.max.toArray(), maximum_bone_length_error_m: boneLengthError,
    ...(clip.name === 'WingFold' ? { wing_movement_m: wingMotion, body_movement_m: bodyMotion } : {}) })
}
restore()
const report = {
  model: modelPath, sha256: createHash('sha256').update(read(modelPath)).digest('hex'),
  units: 'meters', runtime_scale: 1, height_m: bind.box.getSize(new THREE.Vector3()).y,
  floor_m: bind.box.min.y, joints: bones.length, triangles: geometry.index.count / 3,
  maximum_bind_drift_m: bindError, maximum_weight_sum_error: weightError,
  textures_identical_to_source: true, node_and_animation_scales: 'identity', clips: checks,
  finger_checks: fingerChecks, idle_posture: idlePosture,
}
console.log(JSON.stringify(report, null, 2))
