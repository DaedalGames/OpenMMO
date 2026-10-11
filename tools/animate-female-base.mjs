import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, hash } from './lib/headless-three.mjs'

const output = 'assets/modular_human_female_01/rig_v1/'
const gripClips = new Set(['idle1', 'walk', 'run', 'jump', 'combat_idle', 'slash1'])

function relaxedIdle(root, armed) {
  const clip = armed.clone()
  clip.name = 'idle1'
  root.updateMatrixWorld(true)
  const leftHand = root.getObjectByName('LeftHand')
  const rightHand = root.getObjectByName('RightHand')
  const relativeRotation = (hand, bone) => hand.getWorldQuaternion(new THREE.Quaternion()).invert()
    .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
  const mirror = q => new THREE.Quaternion(q.x, -q.y, -q.z, q.w)
  const joints = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'].flatMap(finger =>
    Array.from({ length: 3 }, (_, i) => {
      const left = root.getObjectByName(`LeftHand${finger}${i + 1}`)
      const right = root.getObjectByName(`RightHand${finger}${i + 1}`)
      const reference = clip.tracks.find(t => t.name === `${left.name}.quaternion`)
      const track = clip.tracks.find(t => t.name === `${right.name}.quaternion`)
      assert.ok(reference && track, `${clip.name} is missing finger rotations`)
      return { left, right, track, reference, sample: reference.createInterpolant(), values: [],
        leftRest: left.quaternion.clone(), rightRest: right.quaternion.clone(),
        inverseLeftRest: relativeRotation(leftHand, left).invert(),
        rightRelativeRest: relativeRotation(rightHand, right) }
    })
  )
  const times = [...new Set(joints.flatMap(j => [...j.reference.times]))].sort((a, b) => a - b)
  for (const time of times) {
    for (const joint of joints) joint.left.quaternion.fromArray(joint.sample.evaluate(time))
    root.updateMatrixWorld(true)
    for (const joint of joints) {
      const delta = relativeRotation(leftHand, joint.left).multiply(joint.inverseLeftRest)
      const desired = rightHand.getWorldQuaternion(new THREE.Quaternion())
        .multiply(mirror(delta)).multiply(joint.rightRelativeRest)
      joint.right.quaternion.copy(joint.right.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desired))
      joint.right.updateMatrixWorld(true)
      joint.values.push(...joint.right.quaternion.toArray())
    }
  }
  for (const joint of joints) {
    joint.track.times = new Float32Array(times)
    joint.track.values = new Float32Array(joint.values)
    joint.left.quaternion.copy(joint.leftRest)
    joint.right.quaternion.copy(joint.rightRest)
  }
  root.updateMatrixWorld(true)
  return clip
}

function fitRightHandGrip(root, clip) {
  if (!gripClips.has(clip.name)) return
  root.updateMatrixWorld(true)
  const position = name => root.getObjectByName(name).getWorldPosition(new THREE.Vector3())
  const joints = Array.from({ length: 3 }, (_, i) => {
    const index = root.getObjectByName(`RightHandIndex${i + 1}`)
    const middle = root.getObjectByName(`RightHandMiddle${i + 1}`)
    const indexDirection = position(`RightHandIndex${i + 2}`).sub(position(index.name)).normalize()
    const middleDirection = position(`RightHandMiddle${i + 2}`).sub(position(middle.name)).normalize()
    const correction = middle.getWorldQuaternion(new THREE.Quaternion()).invert()
      .multiply(new THREE.Quaternion().setFromUnitVectors(indexDirection, middleDirection))
      .multiply(index.getWorldQuaternion(new THREE.Quaternion()))
    const track = clip.tracks.find(t => t.name === `${index.name}.quaternion`)
    const reference = clip.tracks.find(t => t.name === `${middle.name}.quaternion`)
    assert.ok(track && reference, `${clip.name} is missing finger rotations`)
    return { index, middle, correction, track, reference,
      indexRest: index.quaternion.clone(), middleRest: middle.quaternion.clone(),
      sample: reference.createInterpolant(), values: [] }
  })
  const thumbs = Array.from({ length: 3 }, (_, i) => {
    const bone = root.getObjectByName(`RightHandThumb${i + 1}`)
    const track = clip.tracks.find(t => t.name === `${bone.name}.quaternion`)
    assert.ok(track, `${clip.name} is missing ${bone.name}`)
    return { bone, track, rest: bone.quaternion.clone(), sample: track.createInterpolant(), values: [] }
  })
  const times = [...new Set([
    ...joints.flatMap(j => [...j.track.times, ...j.reference.times]),
    ...thumbs.flatMap(j => [...j.track.times]),
  ])].sort((a, b) => a - b)
  for (const time of times) {
    for (const joint of joints) joint.middle.quaternion.fromArray(joint.sample.evaluate(time))
    for (const joint of thumbs) joint.bone.quaternion.fromArray(joint.sample.evaluate(time))
    root.updateMatrixWorld(true)
    for (const joint of joints) {
      const desired = joint.middle.getWorldQuaternion(new THREE.Quaternion()).multiply(joint.correction)
      joint.index.quaternion.copy(joint.index.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desired))
      joint.index.updateMatrixWorld(true)
      joint.values.push(...joint.index.quaternion.toArray())
    }
    const across = position('RightHandIndex1').sub(position('RightHandPinky1')).normalize()
    const contact = position('RightHandIndex1').lerp(position('RightHandIndex2'), .2)
      .addScaledVector(across, .006)
    for (let iteration = 0; iteration < 48; iteration++) {
      for (let i = thumbs.length - 1; i >= 0; i--) {
        const bone = thumbs[i].bone
        const origin = bone.getWorldPosition(new THREE.Vector3())
        const from = position('RightHandThumb4').sub(origin).normalize()
        const to = contact.clone().sub(origin).normalize()
        const delta = new THREE.Quaternion().setFromUnitVectors(from, to)
          .slerp(new THREE.Quaternion(), .3)
        const desired = delta.multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
        bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desired))
        bone.updateMatrixWorld(true)
      }
    }
    for (const joint of thumbs) joint.values.push(...joint.bone.quaternion.toArray())
  }
  for (const joint of thumbs) {
    joint.track.times = new Float32Array(times)
    joint.track.values = new Float32Array(joint.values)
    joint.bone.quaternion.copy(joint.rest)
  }
  for (const joint of joints) {
    joint.track.times = new Float32Array(times)
    joint.track.values = new Float32Array(joint.values)
    joint.index.quaternion.copy(joint.indexRest)
    joint.middle.quaternion.copy(joint.middleRest)
  }
  root.updateMatrixWorld(true)
}

function fitIdleHandle(root, clip) {
  const hand = root.getObjectByName('RightHand')
  const position = name => root.getObjectByName(name).getWorldPosition(new THREE.Vector3())
  const setDirection = (bone, direction) => {
    const current = position(bone.children.find(b => b.isBone).name).sub(position(bone.name)).normalize()
    const desired = new THREE.Quaternion().setFromUnitVectors(current, direction)
      .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
    bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desired))
    bone.updateMatrixWorld(true)
  }
  const curls = { Index: [56, 88, 37], Middle: [62, 96, 49], Ring: [50, 92, 53], Pinky: [20, 78, 63] }
  const states = []
  for (const finger of ['Thumb', ...Object.keys(curls)]) {
    for (let i = 1; i <= 3; i++) {
      const bone = root.getObjectByName(`RightHand${finger}${i}`)
      states.push({ bone, rest: bone.quaternion.clone() })
    }
  }
  root.updateMatrixWorld(true)
  const handRotation = hand.getWorldQuaternion(new THREE.Quaternion())
  for (const [finger, angles] of Object.entries(curls)) {
    let angle = 0
    for (const [i, degrees] of angles.entries()) {
      angle += THREE.MathUtils.degToRad(degrees)
      const direction = new THREE.Vector3(-Math.sin(.2) * Math.cos(angle),
        Math.cos(.2) * Math.cos(angle), Math.sin(angle))
      if (i === 0) {
        const spread = { Index: -.12, Middle: 0, Ring: .10, Pinky: .18 }[finger]
        direction.addScaledVector(new THREE.Vector3(Math.cos(.2), Math.sin(.2), 0), spread).normalize()
      }
      direction.applyQuaternion(handRotation)
      setDirection(root.getObjectByName(`RightHand${finger}${i + 1}`), direction)
    }
  }
  const thumb = [1, 2, 3, 4].map(i => root.getObjectByName(`RightHandThumb${i}`))
  const origin = position(thumb[0].name)
  const end = hand.localToWorld(new THREE.Vector3(.024, .056, .027))
  const upperLength = position(thumb[1].name).distanceTo(origin)
  const lowerLength = position(thumb[2].name).distanceTo(position(thumb[1].name))
  const distance = origin.distanceTo(end)
  assert.ok(distance < upperLength + lowerLength, 'Thumb target is out of reach')
  const forward = end.clone().sub(origin).normalize()
  const along = (upperLength ** 2 - lowerLength ** 2 + distance ** 2) / (2 * distance)
  const outward = new THREE.Vector3(.5, 0, 1).applyQuaternion(handRotation)
  outward.addScaledVector(forward, -outward.dot(forward)).normalize()
  const elbow = origin.clone().addScaledVector(forward, along)
    .addScaledVector(outward, Math.sqrt(upperLength ** 2 - along ** 2))
  setDirection(thumb[0], elbow.sub(origin).normalize())
  setDirection(thumb[1], end.sub(position(thumb[1].name)).normalize())
  const tip = hand.localToWorld(new THREE.Vector3(.014, .061, .026))
  setDirection(thumb[2], tip.sub(position(thumb[2].name)).normalize())
  for (const { bone, rest } of states) {
    const track = clip.tracks.find(t => t.name === `${bone.name}.quaternion`)
    assert.ok(track, bone.name)
    for (let k = 0; k < track.values.length; k += 4) bone.quaternion.toArray(track.values, k)
    bone.quaternion.copy(rest)
  }
  root.updateMatrixWorld(true)
}

function liftIdleGaze(clip) {
  for (const [name, degrees] of [['Neck', -1.5], ['Head', -6.5]]) {
    const track = clip.tracks.find(t => t.name === `${name}.quaternion`)
    assert.ok(track, name)
    const lift = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), THREE.MathUtils.degToRad(degrees))
    for (let i = 0; i < track.values.length; i += 4)
      new THREE.Quaternion().fromArray(track.values, i).multiply(lift).normalize().toArray(track.values, i)
  }
}

const { server, load } = await headlessThree()
try {
  const donor = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const target = (await load(output + 'female-base.glb')).scene
  const sources = [
    'assets/modular_human_male_01/animations/animations.glb',
    'client/public/models/characters/modular_male/animations/social.glb',
  ]
  const clips = []
  for (const path of sources) {
    const pack = await load(path)
    clips.push(...pack.animations.filter(c => path === sources[0] || c.name === 'sit_idle'))
  }
  const rest = root => {
    const states = []
    root.traverse(b => { if (b.isBone) states.push({ b, p: b.position.clone(), q: b.quaternion.clone(), s: b.scale.clone() }) })
    return () => { for (const { b, p, q, s } of states) { b.position.copy(p); b.quaternion.copy(q); b.scale.copy(s) } root.updateMatrixWorld(true) }
  }
  const resetDonor = rest(donor), resetTarget = rest(target)
  const sourceHip = donor.getObjectByName('Hips').position.clone()
  const targetHip = target.getObjectByName('Hips').position.clone()
  const ratio = targetHip.y / sourceHip.y
  const samplers = root => {
    const meshes = []
    root.traverse(m => {
      if (!m.isSkinnedMesh || m.userData.region === 'boot_ankles') return
      const used = [...new Set(m.geometry.index?.array ?? Array.from({ length: m.geometry.attributes.position.count }, (_, i) => i))]
      meshes.push([m, used])
    })
    return meshes
  }
  const donorMeshes = samplers(donor), targetMeshes = samplers(target)
  const p = new THREE.Vector3()
  const floor = meshes => {
    let min = Infinity
    for (const [mesh, indices] of meshes) {
      mesh.skeleton.update()
      for (const i of indices) {
        p.fromBufferAttribute(mesh.geometry.attributes.position, i)
        mesh.applyBoneTransform(i, p).applyMatrix4(mesh.matrixWorld)
        assert.ok(Number.isFinite(p.y))
        min = Math.min(min, p.y)
      }
    }
    return min
  }
  const baked = []
  for (const original of clips) {
    resetDonor(); resetTarget()
    const clip = original.clone()
    for (const track of clip.tracks) {
      const [name, property] = track.name.split('.')
      const sourceBone = donor.getObjectByName(name), targetBone = target.getObjectByName(name)
      assert.ok(sourceBone && targetBone, track.name)
      if (property === 'position') {
        for (let i = 0; i < track.values.length; i += 3) {
          p.fromArray(track.values, i).sub(sourceBone.position).multiplyScalar(ratio).add(targetBone.position).toArray(track.values, i)
        }
      }
    }
    fitRightHandGrip(target, clip)
    const sourceMixer = new THREE.AnimationMixer(donor), mixer = new THREE.AnimationMixer(target)
    for (const [m, c] of [[sourceMixer, original], [mixer, clip]]) {
      const action = m.clipAction(c).setLoop(THREE.LoopOnce, 1)
      action.clampWhenFinished = true
      action.play()
    }
    const frames = Math.ceil(clip.duration * 60) + 1
    const times = [], positions = [], corrections = [], sourceFloors = []
    for (let i = 0; i < frames; i++) {
      const time = clip.duration * i / (frames - 1)
      sourceMixer.setTime(time); mixer.setTime(time)
      donor.updateMatrixWorld(true); target.updateMatrixWorld(true)
      const desiredFloor = Math.max(0, floor(donorMeshes) * ratio)
      sourceFloors.push(desiredFloor)
      const correction = desiredFloor - floor(targetMeshes)
      times.push(time)
      positions.push(...target.getObjectByName('Hips').position.toArray().map((v, axis) => v + (axis === 1 ? correction : 0)))
      corrections.push(correction)
    }
    const soleOffset = Math.min(...sourceFloors)
    for (let i = 1; i < positions.length; i += 3) positions[i] -= soleOffset
    clip.tracks = clip.tracks.filter(t => t.name !== 'Hips.position')
    clip.tracks.push(new THREE.VectorKeyframeTrack('Hips.position', times, positions))
    if (clip.name === 'idle1') {
      liftIdleGaze(clip)
      clip.name = 'idle_armed'
      resetTarget()
      baked.push(THREE.AnimationClip.toJSON(relaxedIdle(target, clip)))
      fitIdleHandle(target, clip)
    }
    baked.push(THREE.AnimationClip.toJSON(clip))
    console.log(clip.name, frames, 'floor correction', Math.min(...corrections).toFixed(4), Math.max(...corrections).toFixed(4))
    sourceMixer.stopAllAction(); mixer.stopAllAction()
    sourceMixer.uncacheRoot(donor); mixer.uncacheRoot(target)
  }
  writeFileSync(new URL('../' + output + 'clips.json', import.meta.url), JSON.stringify({
    method: 'Existing local rotation tracks applied to the fitted bone axes; right index segments follow the middle finger grip directions with rest-axis compensation and the thumb closes onto the side of the proximal index phalanx for the six weapon-ready clips; separate unarmed idle preserving the original left-hand tracks and mirroring their hand-local rotation deltas onto the right-hand rest axes; armed idle closes all four fingers around the steel longsword handle with an opposed thumb; both idle variants lift neck/head by 1.5/6.5 degrees; rest-offset translation scaling; 60 Hz floor matching to the source silhouette with per-clip sole offset removed, preserving airborne motion.',
    sources: sources.map(path => ({ path, sha256: hash(path) })), hip_ratio: ratio, clips: baked,
  }) + '\n')
} finally { await server.close() }
