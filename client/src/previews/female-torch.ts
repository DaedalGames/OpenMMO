import * as THREE from 'three'
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { groundRetargetedClips } from '../lib/utils/characterAnimationUtils'

export const femaleTorchMotions: Record<string, string> = {
  idle1: 'torch_idle1',
  walk: 'torch_walk',
  run: 'torch_run',
  combat_idle: 'torch_combat_idle',
}

function swordTorchIdle(model: THREE.Object3D, idle: THREE.AnimationClip) {
  const clip = idle.clone()
  clip.name = 'torch_sword_idle1'
  model.updateMatrixWorld(true)
  const arm = model.getObjectByName('RightArm')!
  const parent = arm.parent!.getWorldQuaternion(new THREE.Quaternion())
  const outward = new THREE.Quaternion().setFromEuler(
    new THREE.Euler(
      0,
      THREE.MathUtils.degToRad(-20),
      THREE.MathUtils.degToRad(-5)
    )
  )
  const correction = parent.clone().invert().multiply(outward).multiply(parent)
  const track = clip.tracks.find(
    (track) => track.name === 'RightArm.quaternion'
  )!
  const rotation = new THREE.Quaternion()
  for (let i = 0; i < track.values.length; i += 4) {
    rotation
      .fromArray(track.values, i)
      .premultiply(correction)
      .normalize()
      .toArray(track.values, i)
  }
  return clip
}

export function mirroredSwordGrip(
  model: THREE.Object3D,
  armed: THREE.AnimationClip
) {
  const rig = clone(model)
  rig.updateMatrixWorld(true)
  const rightHand = rig.getObjectByName('RightHand')!
  const leftHand = rig.getObjectByName('LeftHand')!
  const relative = (hand: THREE.Object3D, bone: THREE.Object3D) =>
    hand
      .getWorldQuaternion(new THREE.Quaternion())
      .invert()
      .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
  const joints = armed.tracks
    .filter((track) =>
      /^RightHand(Thumb|Index|Middle|Ring|Pinky)[123]\.quaternion$/.test(
        track.name
      )
    )
    .map((track) => {
      const right = rig.getObjectByName(track.name.split('.')[0])!
      const left = rig.getObjectByName(right.name.replace('Right', 'Left'))!
      return {
        track,
        right,
        left,
        inverseRest: relative(rightHand, right).invert(),
        leftRest: relative(leftHand, left),
      }
    })
  for (const { right, track } of joints)
    right.quaternion.fromArray(track.values)
  rig.updateMatrixWorld(true)
  return joints.map(({ right, left, inverseRest, leftRest }) => {
    const delta = relative(rightHand, right).multiply(inverseRest)
    const mirrored = new THREE.Quaternion(delta.x, -delta.y, -delta.z, delta.w)
    const desired = leftHand
      .getWorldQuaternion(new THREE.Quaternion())
      .multiply(mirrored)
      .multiply(leftRest)
    left.quaternion.copy(
      left
        .parent!.getWorldQuaternion(new THREE.Quaternion())
        .invert()
        .multiply(desired)
    )
    left.updateMatrixWorld(true)
    return new THREE.QuaternionKeyframeTrack(
      `${left.name}.quaternion`,
      [0],
      left.quaternion.toArray()
    )
  })
}

function withTorchArms(
  base: THREE.AnimationClip,
  torch: THREE.AnimationClip,
  leftOnly = false
) {
  const clip = base.clone()
  clip.name = `torch_${base.name}`
  const isArmTrack = (track: THREE.KeyframeTrack) =>
    (leftOnly
      ? /^Left(Shoulder|Arm|ForeArm|Hand)/
      : /^(Left|Right)(Shoulder|Arm|ForeArm|Hand)/
    ).test(track.name)
  clip.tracks = clip.tracks.filter((track) => !isArmTrack(track))
  for (const source of torch.tracks.filter(isArmTrack)) {
    const track = source.clone()
    for (let i = 0; i < track.times.length; i++)
      track.times[i] *= clip.duration / torch.duration
    if (track.name.endsWith('.quaternion') && track.times.length > 1) {
      const first = new THREE.Quaternion().fromArray(track.values)
      const last = new THREE.Quaternion().fromArray(
        track.values,
        track.values.length - 4
      )
      const correction = last.invert().multiply(first)
      for (let i = 0; i < track.times.length; i++) {
        const blend = THREE.MathUtils.smoothstep(
          track.times[i] / clip.duration,
          0.8,
          1
        )
        new THREE.Quaternion()
          .fromArray(track.values, i * 4)
          .multiply(new THREE.Quaternion().slerp(correction, blend))
          .normalize()
          .toArray(track.values, i * 4)
      }
    }
    clip.tracks.push(track)
  }
  return clip
}

export function levelGaze(model: THREE.Object3D, clip: THREE.AnimationClip) {
  const rig = clone(model)
  rig.updateMatrixWorld(true)
  const neck = rig.getObjectByName('Neck')!
  const head = rig.getObjectByName('Head')!
  const localForward = new THREE.Vector3(0, 0, 1).applyQuaternion(
    head.getWorldQuaternion(new THREE.Quaternion()).invert()
  )
  const mixer = new THREE.AnimationMixer(rig)
  const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1)
  action.clampWhenFinished = true
  action.play()
  const times: number[] = [],
    neckValues: number[] = [],
    headValues: number[] = []
  const frames = Math.ceil(clip.duration * 60)
  for (let i = 0; i <= frames; i++) {
    const time = (clip.duration * i) / frames
    mixer.setTime(time)
    rig.updateMatrixWorld(true)
    const forward = localForward
      .clone()
      .applyQuaternion(head.getWorldQuaternion(new THREE.Quaternion()))
    const lift = new THREE.Quaternion().setFromUnitVectors(
      forward,
      new THREE.Vector3(forward.x, 0, forward.z).normalize()
    )
    for (const [bone, fraction] of [
      [neck, 0.35],
      [head, 0.65],
    ] as const) {
      const desired = new THREE.Quaternion()
        .slerp(lift, fraction)
        .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
      bone.quaternion.copy(
        bone
          .parent!.getWorldQuaternion(new THREE.Quaternion())
          .invert()
          .multiply(desired)
      )
      bone.updateMatrixWorld(true)
    }
    times.push(time)
    neckValues.push(...neck.quaternion.toArray())
    headValues.push(...head.quaternion.toArray())
  }
  mixer.stopAllAction()
  mixer.uncacheRoot(rig)
  clip.tracks = clip.tracks.filter(
    (track) => !['Neck.quaternion', 'Head.quaternion'].includes(track.name)
  )
  clip.tracks.push(
    new THREE.QuaternionKeyframeTrack('Neck.quaternion', times, neckValues),
    new THREE.QuaternionKeyframeTrack('Head.quaternion', times, headValues)
  )
}

export async function femaleTorchClips(
  model: THREE.Object3D,
  pack: GLTF,
  armed: THREE.AnimationClip,
  walk: THREE.AnimationClip,
  combatIdle: THREE.AnimationClip
) {
  const sourceHip = pack.scene.getObjectByName('Hips')!
  const targetHip = model.getObjectByName('Hips')!
  const ratio = targetHip.position.y / sourceHip.position.y
  const position = new THREE.Vector3()
  const grip = mirroredSwordGrip(model, armed)
  const clips = pack.animations
    .filter((clip) => Object.values(femaleTorchMotions).includes(clip.name))
    .map((original) => {
      let clip = original.clone()
      for (const track of clip.tracks) {
        const [name, property] = track.name.split('.')
        if (property !== 'position') continue
        const source = pack.scene.getObjectByName(name)!
        const target = model.getObjectByName(name)!
        for (let i = 0; i < track.values.length; i += 3) {
          position
            .fromArray(track.values, i)
            .sub(source.position)
            .multiplyScalar(ratio)
            .add(target.position)
            .toArray(track.values, i)
        }
      }
      const replaced = new Set(grip.map((track) => track.name))
      clip.tracks = clip.tracks.filter((track) => !replaced.has(track.name))
      clip.tracks.push(...grip.map((track) => track.clone()))
      if (clip.name === 'torch_walk') clip = withTorchArms(walk, clip)
      if (['torch_idle1', 'torch_walk'].includes(clip.name))
        levelGaze(model, clip)
      return clip
    })
  const grounded = await groundRetargetedClips(
    model,
    clips.filter((clip) => clip.name !== 'torch_walk'),
    {
      plantedClips: ['torch_idle1'],
      baselineClips: ['torch_run'],
      soleClearance: 0,
    }
  )
  grounded.push(
    clips.find((clip) => clip.name === 'torch_walk')!,
    withTorchArms(
      combatIdle,
      grounded.find((clip) => clip.name === 'torch_idle1')!,
      true
    ),
    swordTorchIdle(model, grounded.find((clip) => clip.name === 'torch_idle1')!)
  )
  return grounded
}
