import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { GLTFLoader } from '../client/node_modules/three/examples/jsm/loaders/GLTFLoader.js'
import { withBarkanRuneGrip } from '../client/src/lib/utils/barkanRuneGrip.ts'
import { BARKAN_ATTACK_FOLLOW_THROUGH, withBarkanAttackFollowThrough } from '../client/src/lib/utils/barkanAttack.ts'

globalThis.self = globalThis
const root = new URL('../', import.meta.url)
const read = path => readFileSync(new URL(path, root))
const bytes = read('client/public/models/weapons/rune_blade.glb')
const jsonLength = bytes.readUInt32LE(12)
const document = JSON.parse(bytes.subarray(20, 20 + jsonLength))
const loader = new GLTFLoader().register(() => ({
  name: 'geometry-only',
  loadMaterial: async () => new THREE.MeshBasicMaterial(),
}))
const load = path => {
  const data = read(path)
  return loader.parseAsync(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), '')
}
const { scene: weapon } = await load('client/public/models/weapons/rune_blade.glb')
const bounds = new THREE.Box3().setFromObject(weapon)
const length = bounds.max.x - bounds.min.x
assert.ok(Math.abs(length - 2.1) < 1e-5)
assert.ok(Math.abs(bounds.min.x + 0.483) < 1e-5)
assert.ok(Math.abs(bounds.max.x - 1.617) < 1e-5)
let triangles = 0
weapon.traverse(node => {
  assert.deepEqual(node.scale.toArray(), [1, 1, 1])
  if (node.isMesh) triangles += node.geometry.index.count / 3
})
assert.equal(triangles, 4518)
assert.ok(document.materials.some(material => material.emissiveTexture && material.emissiveFactor.some(value => value > 0)))
assert.ok(document.materials.every(material => !material.doubleSided))
const def = JSON.parse(read('data/monsters.json')).barkan
assert.equal(def.weapon, 'weapons/rune_blade.glb')
assert.equal(def.weaponBone, 'RightHand')
const checks = []
const enclosesGrip = (hand, finger, grip, padding = 0) => {
  const points = [1, 2, 3, 4].map(index => hand.worldToLocal(
    hand.getObjectByName(`RightHand${finger}${index}`).getWorldPosition(new THREE.Vector3())
  ))
  const sides = points.map((point, index) => {
    const next = points[(index + 1) % points.length]
    return (next.y - point.y) * (grip.z - point.z) - (next.z - point.z) * (grip.y - point.y)
  })
  if (sides.every(side => side >= -1e-6) || sides.every(side => side <= 1e-6)) return true
  return points.some((point, index) => {
    const next = points[(index + 1) % points.length]
    const dy = next.y - point.y, dz = next.z - point.z
    const t = THREE.MathUtils.clamp(((grip.y - point.y) * dy + (grip.z - point.z) * dz) / (dy * dy + dz * dz), 0, 1)
    return Math.hypot(grip.y - point.y - dy * t, grip.z - point.z - dz * t) <= padding
  })
}
const followThrough = []
const tipYaw = (sword) => {
  const tip = sword.localToWorld(new THREE.Vector3(1.617, 0, 0))
  return THREE.MathUtils.radToDeg(Math.atan2(tip.x, tip.z))
}
function checkFollowThrough(model, sword, original, clip) {
  const bodies = []
  model.traverse(mesh => {
    if (!mesh.isSkinnedMesh) return
    const { skinIndex, skinWeight } = mesh.geometry.attributes
    const indices = mesh.geometry.index.array
    const faces = new Set()
    for (let face = 0; face < indices.length / 3; face++) {
      let weight = 0
      for (let corner = 0; corner < 3; corner++)
        for (let slot = 0; slot < 4; slot++) {
          const vertex = indices[face * 3 + corner]
          if (/^(Hips|Spine[12]?|Neck|Head|(?:Left|Right)(?:UpLeg|Leg))$/.test(mesh.skeleton.bones[skinIndex.getComponent(vertex, slot)].name))
            weight += skinWeight.getComponent(vertex, slot)
        }
      if (weight > 1.5) faces.add(face)
    }
    bodies.push({ mesh, faces })
  })
  const bones = []
  model.traverse(node => { if (node.isBone) bones.push(node) })
  const raycaster = new THREE.Raycaster()
  const measure = (motion) => {
    const mixer = new THREE.AnimationMixer(model)
    const action = mixer.clipAction(motion).setLoop(THREE.LoopOnce, 1)
    action.clampWhenFinished = true
    action.play()
    const poses = [], yaws = [], pierced = []
    let maximumStep = 0
    for (let frame = 0; frame <= Math.ceil(motion.duration * 120); frame++) {
      const time = Math.min(frame / 120, motion.duration)
      mixer.setTime(time)
      model.updateMatrixWorld(true)
      const pose = bones.map(bone => bone.quaternion.clone())
      if (poses.length)
        pose.forEach((rotation, index) => {
          if (/^(Right(?:Shoulder|Arm|ForeArm|Hand)|Spine[12]?|Neck)$/.test(bones[index].name))
            maximumStep = Math.max(maximumStep, rotation.angleTo(poses.at(-1)[index]))
        })
      poses.push(pose)
      yaws.push({ time, yaw: tipYaw(sword) })
      for (const { mesh } of bodies) {
        mesh.skeleton.update()
        mesh.computeBoundingSphere()
      }
      for (const across of [-0.12, 0, 0.12]) {
        const start = sword.localToWorld(new THREE.Vector3(0.25, across, 0))
        const end = sword.localToWorld(new THREE.Vector3(1.617, across, 0))
        raycaster.set(start, end.clone().sub(start).normalize())
        raycaster.far = start.distanceTo(end)
        if (bodies.some(({ mesh, faces }) => raycaster.intersectObject(mesh, false).some(hit => faces.has(hit.faceIndex)))) {
          pierced.push(Number(time.toFixed(4)))
          break
        }
      }
    }
    mixer.stopAllAction()
    mixer.uncacheRoot(model)
    const swing = yaws.filter(({ time }) => time >= BARKAN_ATTACK_FOLLOW_THROUGH.start)
    const peak = swing.reduce((best, sample) => (sample.yaw > best.yaw ? sample : best))
    return { poses, maximumStep, peak, pierced }
  }
  const before = measure(original)
  const after = measure(clip)
  const untouched = Math.floor(BARKAN_ATTACK_FOLLOW_THROUGH.start * 120)
  for (let frame = 0; frame <= untouched; frame++)
    before.poses[frame].forEach((rotation, index) =>
      assert.ok(rotation.angleTo(after.poses[frame][index]) < 0.003, `Attack windup and strike must match the source at ${frame / 120}s`))
  before.poses.at(-1).forEach((rotation, index) =>
    assert.ok(rotation.angleTo(after.poses.at(-1)[index]) < 0.003, 'Attack must end in the source pose'))
  assert.ok(after.peak.yaw > before.peak.yaw + 20, `Follow-through must carry the blade further: ${before.peak.yaw} -> ${after.peak.yaw}`)
  assert.ok(after.maximumStep <= before.maximumStep + 1e-3, `Follow-through adds a joint jump: ${after.maximumStep}`)
  assert.deepEqual(after.pierced, before.pierced, 'Follow-through must not cut into the body or legs')
  return {
    source_duration_s: original.duration, duration_s: clip.duration,
    source_peak: before.peak, peak: after.peak,
    maximum_joint_step_degrees: THREE.MathUtils.radToDeg(after.maximumStep),
    source_body_intersections: before.pierced, body_intersections: after.pierced,
  }
}
for (const path of ['assets/monsters/barkan/rig_v1/barkan.glb', 'client/public/models/monsters/barkan.glb']) {
  const character = await load(path)
  const sword = weapon.clone(true)
  sword.position.set(def.weaponOffsetX ?? 0, def.weaponOffset ?? 0, def.weaponOffsetZ ?? 0)
  const angles = String(def.weaponRotation ?? '0|0|0').split('|').map(Number)
  sword.rotation.set(...angles.map(THREE.MathUtils.degToRad))
  const hand = character.scene.getObjectByName(def.weaponBone)
  assert.ok(hand)
  hand.add(sword)
  const pinkyPivot = new THREE.Vector3(-0.14, 0, 0).applyQuaternion(sword.quaternion).add(sword.position)
  assert.ok(pinkyPivot.distanceTo(new THREE.Vector3(-0.12, 0.09, 0.04)) < 1e-6, 'Rotation must preserve the pinky contact point')
  const shaftDirection = new THREE.Vector3(1, 0, 0).applyQuaternion(sword.quaternion)
  const indexAxisY = sword.position.y + shaftDirection.y * (0.08 - sword.position.x) / shaftDirection.x
  assert.ok(indexAxisY < 0.081 && indexAxisY > 0.078, 'Index side should move about 1cm toward the wrist')
  const mixer = new THREE.AnimationMixer(character.scene)
  let body
  character.scene.traverse(node => { if (node.isSkinnedMesh) body = node })
  const geometry = body.geometry
  const surfaces = ['Left', 'Right'].map(side => {
    const handVertices = [], thighVertices = []
    for (const id of new Set(geometry.index.array)) {
      let handWeight = 0, thighWeight = 0
      for (let slot = 0; slot < 4; slot++) {
        const offset = id * 4 + slot
        const name = body.skeleton.bones[geometry.attributes.skinIndex.array[offset]].name
        const weight = geometry.attributes.skinWeight.array[offset]
        if (name.startsWith(`${side}Hand`)) handWeight += weight
        if (name === `${side}UpLeg`) thighWeight += weight
      }
      if (handWeight > 0.6) handVertices.push(id)
      if (thighWeight > 0.6) thighVertices.push(id)
    }
    assert.ok(handVertices.length > 100 && thighVertices.length > 100)
    return { side, sign: side === 'Left' ? 1 : -1, handVertices, thighVertices }
  })
  const vertex = new THREE.Vector3()
  for (const original of character.animations) {
    const shaped = withBarkanAttackFollowThrough(original)
    const clip = withBarkanRuneGrip(shaped)
    assert.equal(withBarkanRuneGrip(withBarkanAttackFollowThrough(original)), clip)
    assert.equal(clip.duration, shaped.duration)
    if (clip.name === 'Attack') followThrough.push(checkFollowThrough(character.scene, sword, withBarkanRuneGrip(original), clip))
    for (const [index, track] of clip.tracks.entries()) {
      const source = shaped.tracks[index]
      assert.deepEqual(track.times, source.times)
      const changesArm = ['Idle', 'Walk'].includes(clip.name) && /^(?:Left|Right)Arm\.quaternion$/.test(track.name)
      if (!changesArm && !/^RightHand(?:Index|Middle|Ring|Pinky)[123]\.quaternion$/.test(track.name))
        assert.deepEqual(track.values, source.values)
      else assert.notDeepEqual(track.values, source.values)
    }
    mixer.stopAllAction()
    const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1)
    action.clampWhenFinished = true
    action.play()
    let floor = Infinity, reach = 0, minimumHandThighGap = Infinity
    const handThighGap = { Left: Infinity, Right: Infinity }
    for (let frame = 0; frame <= Math.ceil(clip.duration * 24); frame++) {
      mixer.setTime(Math.min(frame / 24, clip.duration))
      character.scene.updateMatrixWorld(true)
      if (['Idle', 'Walk'].includes(clip.name)) {
        body.skeleton.update()
        for (const { side, sign, handVertices, thighVertices } of surfaces) {
          const handBounds = new THREE.Box3()
          for (const id of handVertices)
            handBounds.expandByPoint(body.getVertexPosition(id, vertex).applyMatrix4(body.matrixWorld))
          let thighOuter = -Infinity
          for (const id of thighVertices) {
            body.getVertexPosition(id, vertex).applyMatrix4(body.matrixWorld)
            if (vertex.y >= handBounds.min.y - 0.02 && vertex.y <= handBounds.max.y + 0.02)
              thighOuter = Math.max(thighOuter, vertex.x * sign)
          }
          const handInner = sign === 1 ? handBounds.min.x : -handBounds.max.x
          const gap = handInner - thighOuter
          assert.ok(gap >= 0.005, `${path} ${clip.name} ${frame}: ${side} hand too close to thigh ${gap}`)
          minimumHandThighGap = Math.min(minimumHandThighGap, gap)
          handThighGap[side] = Math.min(handThighGap[side], gap)
        }
        for (const finger of ['Index', 'Middle', 'Ring']) {
          const knuckleX = hand.worldToLocal(hand.getObjectByName(`RightHand${finger}1`).getWorldPosition(new THREE.Vector3())).x
          const axisPoint = sword.position.clone().addScaledVector(shaftDirection, (knuckleX - sword.position.x) / shaftDirection.x)
          assert.ok(enclosesGrip(hand, finger, axisPoint, 0.008), `${path} ${clip.name} ${frame}: handle outside ${finger} grip`)
        }
        assert.ok(!enclosesGrip(hand, 'Middle', new THREE.Vector3(0.02, 0.17, 0.07)), 'Rejected floating grip must stay outside the fingers')
      }
      const box = new THREE.Box3().setFromObject(sword, true)
      assert.ok([...box.min.toArray(), ...box.max.toArray()].every(Number.isFinite))
      floor = Math.min(floor, box.min.y)
      reach = Math.max(reach, box.max.z)
      const measured = sword.localToWorld(new THREE.Vector3(1.617, 0, 0))
        .distanceTo(sword.localToWorld(new THREE.Vector3(-0.483, 0, 0)))
      assert.ok(Math.abs(measured - 2.1) < 1e-5)
    }
    assert.ok(floor >= 0, `${path} ${clip.name}: sword below floor ${floor}`)
    checks.push({ model: path, clip: clip.name, minimum_weapon_y_m: floor, maximum_forward_reach_m: reach,
      minimum_hand_thigh_gap_m: Number.isFinite(minimumHandThighGap) ? minimumHandThighGap : undefined,
      hand_thigh_gap_by_side_m: Number.isFinite(minimumHandThighGap) ? handThighGap : undefined })
  }
}
assert.equal(followThrough.length, 1)
console.log(JSON.stringify({ triangles, length_m: length, checks, attack_follow_through: followThrough }, null, 2))
