import assert from 'node:assert/strict'
import * as THREE from '../../client/node_modules/three/build/three.module.js'

export const catwalkSource = 'assets/modular_human_female_01/rig_v1/catwalk-source.glb'

export async function femaleCatwalk(root, previous, { server, load }) {
  const source = await load(catwalkSource)
  const runtime = await server.ssrLoadModule('/src/lib/utils/characterAnimationUtils.ts')
  const [motion] = await runtime.retargetAnimationsForCharacterModel(root, source.scene, source.animations)
  assert.equal(motion.name, 'walk_cat')
  const tracks = new Map(previous.tracks.map(track => {
    const copy = track.clone()
    copy.times = new Float32Array([0, motion.duration])
    copy.values = new Float32Array([...track.values.slice(0, track.getValueSize()),
      ...track.values.slice(0, track.getValueSize())])
    return [copy.name, copy]
  }))
  for (const track of motion.tracks) {
    if (!/Hand(Thumb|Index|Middle|Ring|Pinky)/.test(track.name)) tracks.set(track.name, track.clone())
  }
  const clip = new THREE.AnimationClip('walk', motion.duration, [...tracks.values()])
  const hips = tracks.get('Hips.position')
  const ratio = root.getObjectByName('Hips').position.y / source.scene.getObjectByName('Hips').position.y
  for (let i = 0; i < hips.times.length; i++) {
    for (const axis of [0, 2]) hips.values[i * 3 + axis] *= ratio
  }
  for (const track of clip.tracks) {
    const size = track.getValueSize()
    const first = Array.from(track.values.slice(0, size))
    const last = Array.from(track.values.slice(-size))
    for (let i = 0; i < track.times.length; i++) {
      const phase = track.times[i] / clip.duration
      const blend = THREE.MathUtils.smoothstep(phase, .8, 1)
      if (track.name === 'Hips.position') {
        for (let axis = 0; axis < 3; axis++)
          track.values[i * size + axis] -= (last[axis] - first[axis]) * phase
      } else if (size === 4 && blend > 0) {
        const correction = new THREE.Quaternion().fromArray(last).invert()
          .multiply(new THREE.Quaternion().fromArray(first))
        new THREE.Quaternion().fromArray(track.values, i * 4)
          .multiply(new THREE.Quaternion().slerp(correction, blend)).normalize().toArray(track.values, i * 4)
      }
    }
  }
  const meshes = [], rest = []
  root.traverse(node => {
    if (node.isBone) rest.push({ node, p: node.position.clone(), q: node.quaternion.clone(), s: node.scale.clone() })
    if (node.isSkinnedMesh) meshes.push(node)
  })
  const mixer = new THREE.AnimationMixer(root)
  const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1)
  action.clampWhenFinished = true
  action.play()
  const frames = Math.ceil(clip.duration * 60) + 1
  const times = [], positions = [], vertex = new THREE.Vector3()
  const legs = ['Left', 'Right'].map(side => ({
    thigh: root.getObjectByName(`${side}UpLeg`), foot: root.getObjectByName(`${side}Foot`),
    thighValues: [], footValues: [],
  }))
  const shoulders = ['Left', 'Right'].map(side => ({
    shoulder: root.getObjectByName(`${side}Shoulder`), arm: root.getObjectByName(`${side}Arm`),
    angle: THREE.MathUtils.degToRad(side === 'Left' ? -6 : 6),
    shoulderValues: [], armValues: [],
  }))
  for (let frame = 0; frame < frames; frame++) {
    const time = clip.duration * frame / (frames - 1)
    mixer.setTime(time)
    root.updateMatrixWorld(true)
    for (const { shoulder, arm, angle, shoulderValues, armValues } of shoulders) {
      const armRotation = arm.getWorldQuaternion(new THREE.Quaternion())
      const parentRotation = shoulder.parent.getWorldQuaternion(new THREE.Quaternion())
      const axis = new THREE.Vector3(0, 0, 1).applyQuaternion(parentRotation)
      const rotation = new THREE.Quaternion().setFromAxisAngle(axis, angle)
        .multiply(shoulder.getWorldQuaternion(new THREE.Quaternion()))
      shoulder.quaternion.copy(parentRotation.invert().multiply(rotation))
      shoulder.updateMatrixWorld(true)
      arm.quaternion.copy(arm.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(armRotation))
      arm.updateMatrixWorld(true)
      shoulderValues.push(...shoulder.quaternion.toArray())
      armValues.push(...arm.quaternion.toArray())
    }
    const hipX = root.getObjectByName('Hips').getWorldPosition(new THREE.Vector3()).x
    for (const { thigh, foot, thighValues, footValues } of legs) {
      const origin = thigh.getWorldPosition(new THREE.Vector3())
      const ankle = foot.getWorldPosition(new THREE.Vector3())
      const footRotation = foot.getWorldQuaternion(new THREE.Quaternion())
      const target = ankle.clone()
      target.x = hipX + (ankle.x - hipX) * .28
      const turn = new THREE.Quaternion().setFromUnitVectors(
        ankle.sub(origin).normalize(), target.sub(origin).normalize())
      const rotation = turn.multiply(thigh.getWorldQuaternion(new THREE.Quaternion()))
      thigh.quaternion.copy(thigh.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(rotation))
      thigh.updateMatrixWorld(true)
      foot.quaternion.copy(foot.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(footRotation))
      foot.updateMatrixWorld(true)
      thighValues.push(...thigh.quaternion.toArray())
      footValues.push(...foot.quaternion.toArray())
    }
    let floor = Infinity
    for (const mesh of meshes) {
      mesh.skeleton.update()
      for (let i = 0; i < mesh.geometry.attributes.position.count; i++) {
        vertex.fromBufferAttribute(mesh.geometry.attributes.position, i)
        mesh.applyBoneTransform(i, vertex).applyMatrix4(mesh.matrixWorld)
        floor = Math.min(floor, vertex.y)
      }
    }
    const position = root.getObjectByName('Hips').position.clone()
    position.y -= floor
    times.push(time)
    positions.push(...position.toArray())
  }
  mixer.stopAllAction()
  mixer.uncacheRoot(root)
  for (const { node, p, q, s } of rest) { node.position.copy(p); node.quaternion.copy(q); node.scale.copy(s) }
  root.updateMatrixWorld(true)
  clip.tracks = clip.tracks.filter(track => track.name !== 'Hips.position')
  clip.tracks.push(new THREE.VectorKeyframeTrack('Hips.position', times, positions))
  for (const { thigh, foot, thighValues, footValues } of legs) {
    clip.tracks = clip.tracks.filter(track => ![`${thigh.name}.quaternion`, `${foot.name}.quaternion`].includes(track.name))
    clip.tracks.push(new THREE.QuaternionKeyframeTrack(`${thigh.name}.quaternion`, times, thighValues),
      new THREE.QuaternionKeyframeTrack(`${foot.name}.quaternion`, times, footValues))
  }
  for (const { shoulder, arm, shoulderValues, armValues } of shoulders) {
    clip.tracks = clip.tracks.filter(track => ![`${shoulder.name}.quaternion`, `${arm.name}.quaternion`].includes(track.name))
    clip.tracks.push(new THREE.QuaternionKeyframeTrack(`${shoulder.name}.quaternion`, times, shoulderValues),
      new THREE.QuaternionKeyframeTrack(`${arm.name}.quaternion`, times, armValues))
  }
  assert.ok(clip.validate())
  return clip
}
