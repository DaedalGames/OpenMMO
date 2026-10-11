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
  const { femaleSeatOffset } = await server.ssrLoadModule('/src/previews/female-seat.ts')
  const original = await load(originalPath), result = await load(path)
  const originalMeshes = [], meshes = []
  original.scene.traverse(n => { if (n.isMesh) originalMeshes.push(n) })
  result.scene.traverse(n => { if (n.isSkinnedMesh) meshes.push(n) })
  assert.equal(meshes.length, originalMeshes.length)
  assert.equal(result.animations.length, 9)
  const unarmedIdle = result.animations.find(c => c.name === 'idle1')
  const armedIdle = result.animations.find(c => c.name === 'idle_armed')
  assert.ok(unarmedIdle && armedIdle, 'Both equipment-specific idle clips must exist')
  assert.equal(unarmedIdle.duration, armedIdle.duration)
  for (const track of unarmedIdle.tracks) {
    const armedTrack = armedIdle.tracks.find(t => t.name === track.name)
    assert.ok(armedTrack, track.name)
    if (!/^RightHand(Thumb|Index|Middle|Ring|Pinky)\d\.quaternion$/.test(track.name)) {
      assert.deepEqual(track.times, armedTrack.times)
      assert.deepEqual(track.values, armedTrack.values, `Idle body or left-hand motion changed: ${track.name}`)
    }
  }
  const sourceAnimations = (await load('assets/modular_human_male_01/animations/animations.glb')).animations
  for (const [clipName, neckDegrees, headDegrees] of [['idle1', -1.5, -6.5]]) {
    const source = sourceAnimations.find(c => c.name === clipName)
    const adjusted = result.animations.find(c => c.name === clipName)
    for (const [name, liftDegrees] of [['Neck', neckDegrees], ['Head', headDegrees]]) {
      const sourceTrack = source.tracks.find(t => t.name === `${name}.quaternion`)
      const track = adjusted.tracks.find(t => t.name === sourceTrack.name)
      assert.deepEqual(track.times, sourceTrack.times)
      const correction = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0),
        THREE.MathUtils.degToRad(liftDegrees))
      for (let i = 0; i < track.values.length; i += 4) {
        const expected = new THREE.Quaternion().fromArray(sourceTrack.values, i).multiply(correction).normalize()
        const actual = new THREE.Quaternion().fromArray(track.values, i).normalize()
        assert.ok(actual.angleTo(expected) < 1e-6, `${clipName}: ${name} gaze lift differs from the source motion`)
      }
    }
  }
  const walkClip = result.animations.find(c => c.name === 'walk')
  for (const track of walkClip.tracks) {
    const size = track.getValueSize()
    const first = track.values.slice(0, size), last = track.values.slice(-size)
    const error = size === 4
      ? new THREE.Quaternion().fromArray(first).normalize().angleTo(new THREE.Quaternion().fromArray(last).normalize())
      : Math.max(...first.map((value, i) => Math.abs(value - last[i])))
    assert.ok(error < 1e-6, `Catwalk loop discontinuity: ${track.name} (${error})`)
  }
  const relaxedFingerTracks = unarmedIdle.tracks.filter(t =>
    /^RightHand(Thumb|Index|Middle|Ring|Pinky)[123]\.quaternion$/.test(t.name))
  assert.equal(relaxedFingerTracks.length, 15)
  for (const reference of relaxedFingerTracks) {
    const track = walkClip.tracks.find(t => t.name === reference.name)
    assert.ok(track, reference.name)
    const expected = new THREE.Quaternion().fromArray(reference.values).normalize()
    for (let i = 0; i < track.values.length; i += 4) {
      const actual = new THREE.Quaternion().fromArray(track.values, i).normalize()
      assert.ok(actual.angleTo(expected) < 1e-6, `Walk does not use the relaxed hand: ${track.name}`)
    }
  }
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
  const restJoint = name => result.scene.getObjectByName(name).getWorldPosition(new THREE.Vector3())
  const palmForward = restJoint('RightHandMiddle1').sub(restJoint('RightHand')).normalize()
  const indexAnchorOffset = restJoint('RightHandIndex1').sub(restJoint('RightHandMiddle1')).dot(palmForward)
  assert.ok(indexAnchorOffset >= 0 && indexAnchorOffset < .006,
    `Right index anchor is recessed toward the wrist or too far forward: ${indexAnchorOffset}`)
  const handMesh = meshes[0]
  const handGeometry = handMesh.geometry.attributes
  const tipAnchors = {
    Left: {
      Thumb: [.288, .533, .013], Index: [.328, .516, .003],
      Middle: [.336, .514, -.011], Ring: [.331, .516, -.026],
      Pinky: [.320, .526, -.038],
    },
    Right: {
      Thumb: [-.287, .533, .031], Index: [-.327, .516, .024],
      Middle: [-.335, .514, .010], Ring: [-.332, .516, -.006],
      Pinky: [-.322, .526, -.019],
    },
  }
  const fingertips = []
  for (const [side, anchors] of Object.entries(tipAnchors)) {
    for (const [finger, anchor] of Object.entries(anchors)) {
      const name = `${side}Hand${finger}`
      const center = new THREE.Vector3().fromArray(anchor)
      const indices = samples[0].indices.filter(i =>
        p.fromBufferAttribute(handGeometry.position, i).distanceTo(center) < .004
      )
      assert.ok(indices.length >= 3, `${name} tip surface is missing`)
      let minimumOwnWeight = 1
      for (const i of indices) {
        let ownWeight = 0
        for (let k = 0; k < 4; k++) {
          const joint = handGeometry.skinIndex.array[i * 4 + k]
          if (bones[joint].name.startsWith(name))
            ownWeight += handGeometry.skinWeight.array[i * 4 + k]
        }
        minimumOwnWeight = Math.min(minimumOwnWeight, ownWeight)
      }
      assert.ok(minimumOwnWeight > .95, `${name} tip follows another finger: ${minimumOwnWeight}`)
      fingertips.push({ name, indices, minimumOwnWeight })
    }
  }
  const tipCenter = ({ indices }) => {
    const center = new THREE.Vector3()
    for (const i of indices) {
      p.fromBufferAttribute(handGeometry.position, i)
      handMesh.applyBoneTransform(i, p).applyMatrix4(handMesh.matrixWorld)
      center.add(p)
    }
    return center.divideScalar(indices.length)
  }
  const tipRest = fingertips.map(tipCenter)
  const fingerChecks = []
  for (const [index, tip] of fingertips.entries()) {
    const bone = result.scene.getObjectByName(`${tip.name}2`)
    const rotation = bone.quaternion.clone()
    bone.rotateX(Math.PI / 4)
    result.scene.updateMatrixWorld(true)
    handMesh.skeleton.update()
    const movement = tipCenter(tip).distanceTo(tipRest[index])
    const neighborMovement = Math.max(...fingertips.map((other, i) =>
      i === index ? 0 : tipCenter(other).distanceTo(tipRest[i])
    ))
    bone.quaternion.copy(rotation)
    result.scene.updateMatrixWorld(true)
    handMesh.skeleton.update()
    assert.ok(movement > .005, `${tip.name} does not bend at its second joint`)
    assert.ok(neighborMovement < .001, `${tip.name} bends another fingertip`)
    fingerChecks.push({ finger: tip.name, minimum_own_weight: tip.minimumOwnWeight,
      isolated_bend_movement: movement, maximum_neighbor_movement: neighborMovement })
  }
  console.log(JSON.stringify({ fingers: fingerChecks }))
  const handRelativeRotation = (side, finger, joint) => result.scene.getObjectByName(`${side}Hand`)
    .getWorldQuaternion(new THREE.Quaternion()).invert()
    .multiply(result.scene.getObjectByName(`${side}Hand${finger}${joint}`).getWorldQuaternion(new THREE.Quaternion()))
  const relaxedJoints = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'].flatMap(finger =>
    Array.from({ length: 3 }, (_, i) => ({ finger, joint: i + 1,
      inverseLeftRest: handRelativeRotation('Left', finger, i + 1).invert(),
      inverseRightRest: handRelativeRotation('Right', finger, i + 1).invert() }))
  )
  let maximumIdleMirrorError = 0
  let maximumWalkAnkleOffset = 0
  const sampler = clipSampler(result.scene, { samples: 121, restore: bones })
  const poses = [], checks = []
  const minimumTimes = []
  const gripClips = new Set(['run', 'jump', 'combat_idle', 'slash1'])
  const jointPosition = name => result.scene.getObjectByName(name).getWorldPosition(new THREE.Vector3())
  for (const clip of result.animations) {
    assert.ok(clip.validate())
    let minY = Infinity, maxFloor = -Infinity, maxExtent = 0, facialError = 0
    const gripAngles = gripClips.has(clip.name)
      ? Array.from({ length: 3 }, () => ({ minimum: Infinity, maximum: -Infinity }))
      : undefined
    const times = []
    for (const { sample, time } of sampler(clip)) {
      if (clip.name === 'walk') {
        const hipX = jointPosition('Hips').x
        for (const side of ['Left', 'Right']) {
          const offset = Math.abs(jointPosition(`${side}Foot`).x - hipX)
          maximumWalkAnkleOffset = Math.max(maximumWalkAnkleOffset, offset)
          assert.ok(offset < .04, `Catwalk foot leaves the narrow path: ${offset}`)
        }
      }
      if (clip.name === 'idle1') {
        for (const { finger, joint, inverseLeftRest, inverseRightRest } of relaxedJoints) {
          const left = handRelativeRotation('Left', finger, joint).multiply(inverseLeftRest)
          const right = handRelativeRotation('Right', finger, joint).multiply(inverseRightRest)
          const difference = right.normalize().angleTo(new THREE.Quaternion(left.x, -left.y, -left.z, left.w).normalize())
          maximumIdleMirrorError = Math.max(maximumIdleMirrorError, difference)
          assert.ok(difference < 1e-4, `${finger}${joint} does not mirror the relaxed left hand: ${difference}`)
        }
      }
      if (clip.name === 'idle_armed') {
        const hand = result.scene.getObjectByName('RightHand')
        const center = new THREE.Vector3(.028, .064, .011)
        const axis = new THREE.Vector3(Math.cos(.2), Math.sin(.2), 0)
        for (const finger of ['Index', 'Middle', 'Ring', 'Pinky']) {
          const points = [1, 2, 3, 4].map(i => hand.worldToLocal(jointPosition(`RightHand${finger}${i}`)))
          const segments = points.slice(1).map((p, i) => p.clone().sub(points[i]))
          const pip = THREE.MathUtils.radToDeg(segments[0].angleTo(segments[1]))
          const dip = THREE.MathUtils.radToDeg(segments[1].angleTo(segments[2]))
          assert.ok(pip >= 70 && pip <= 105 && dip >= 30 && dip <= 75,
            `${finger} does not close smoothly around the sword: ${pip}, ${dip}`)
          for (let i = 0; i < 3; i++) {
            for (let step = 0; step <= 10; step++) {
              const radial = points[i].clone().lerp(points[i + 1], step / 10).sub(center)
              radial.addScaledVector(axis, -radial.dot(axis))
              assert.ok(radial.length() >= .009 && radial.length() <= .017,
                `${finger} crosses or floats away from the handle axis: ${radial.length()}`)
            }
          }
        }
        const thumbTip = hand.worldToLocal(jointPosition('RightHandThumb4'))
        const indexTip = hand.worldToLocal(jointPosition('RightHandIndex4'))
        assert.ok(thumbTip.distanceTo(indexTip) < .01, 'Thumb does not close over the index finger')
      }
      if (gripAngles) {
        const directions = [
          jointPosition('RightHandMiddle1').sub(jointPosition('RightHand')),
          ...Array.from({ length: 3 }, (_, i) =>
            jointPosition(`RightHandIndex${i + 2}`).sub(jointPosition(`RightHandIndex${i + 1}`))
          ),
        ]
        for (let i = 0; i < 3; i++) {
          const middleDirection = jointPosition(`RightHandMiddle${i + 2}`).sub(jointPosition(`RightHandMiddle${i + 1}`))
          const difference = THREE.MathUtils.radToDeg(directions[i + 1].angleTo(middleDirection))
          assert.ok(difference < 5, `${clip.name}: right index segment ${i + 1} diverges from the middle grip: ${difference}`)
        }
        const across = jointPosition('RightHandIndex1').sub(jointPosition('RightHandPinky1')).normalize()
        const contact = jointPosition('RightHandIndex1').lerp(jointPosition('RightHandIndex2'), .2)
          .addScaledVector(across, .006)
        const thumbGap = jointPosition('RightHandThumb4').distanceTo(contact)
        assert.ok(thumbGap < .002, `${clip.name}: thumb misses the side of the index grip: ${thumbGap}`)
        for (const [i, [minimum, maximum]] of [[45, 100], [15, 90], [15, 80]].entries()) {
          const degrees = THREE.MathUtils.radToDeg(directions[i].angleTo(directions[i + 1]))
          assert.ok(degrees >= minimum && degrees <= maximum,
            `${clip.name}: right index joint ${i + 1} has an abrupt grip bend: ${degrees}`)
          gripAngles[i].minimum = Math.min(gripAngles[i].minimum, degrees)
          gripAngles[i].maximum = Math.max(gripAngles[i].maximum, degrees)
        }
      }
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
      if (clip.name === 'sit_idle') floor += femaleSeatOffset
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
    if (gripAngles) check.right_index_grip_angles_degrees = gripAngles
    checks.push(check); minimumTimes.push({ clip: clip.name, times })
    console.log(JSON.stringify(check))
  }
  const report = { source: { path: originalPath, sha256: hash(originalPath) }, output: { path, sha256: hash(path) },
    bone_count: bones.length, used_vertices: usedVertices, unchanged_geometry_normals_uv_indices: true, unchanged_materials_and_embedded_images: true,
    maximum_rest_error: restError, maximum_weight_sum_error: weightError,
    right_index_anchor_longitudinal_offset_from_middle: indexAnchorOffset,
    idle_variants: { original_left_hand_and_body_tracks_preserved: true, maximum_mirrored_rotation_error_radians: maximumIdleMirrorError },
    armed_idle_handle: { all_four_fingers_wrap_handle: true, thumb_over_index: true, sampled_frames: 121 },
    idle_gaze: { neck_lift_degrees: 1.5, head_lift_degrees: 6.5, both_idle_variants_identical: true },
    catwalk: { source_action: 'walk_cat', closed_loop: true, maximum_ankle_offset_from_pelvis: maximumWalkAnkleOffset },
    walk_hand: { default_matches_unarmed_idle: true, right_finger_tracks: 15 },
    fingers: fingerChecks, clips: checks }
  writeFileSync(new URL('../' + directory + 'validation.json', import.meta.url), JSON.stringify(report, null, 2) + '\n')
  writeFileSync(new URL('../' + directory + 'animation-snapshots.json', import.meta.url), JSON.stringify(poses) + '\n')
  writeFileSync(new URL('../' + directory + 'floor-samples.json', import.meta.url), JSON.stringify(minimumTimes) + '\n')
  assert.equal(meshes.reduce((sum, mesh) => sum + mesh.geometry.index.count / 3, 0), 22175)
} finally { await server.close() }
