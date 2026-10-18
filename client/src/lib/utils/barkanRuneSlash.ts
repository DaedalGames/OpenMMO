import * as THREE from 'three'
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { EnchantWeaponGrip } from './enchantAnimation'

export const BARKAN_RUNE_SLASH = {
  windup: 1.6,
  slashEntry: 0.3,
  transitionEnd: 2.15,
  swingEase: 0.16,
  strikeStart: 2.25,
  strikeEnd: 2.78,
  // The blade's low sideways pass (doc/assets/barkan-rune-slash-bake.json);
  // the server's RUNE_SLASH strike_ms lands at sweepStart.
  sweepStart: 2.55,
  sweepEnd: 2.73,
  sweepBearings: [-81, 89],
  recoveryEnd: 3.9,
  duration: 4.2,
} as const

export function createBarkanRuneSlash(
  source: THREE.Object3D,
  grippedIdle: THREE.AnimationClip,
  enchant: THREE.AnimationClip,
  slash: THREE.AnimationClip,
  slashGrip: THREE.Quaternion
) {
  const model = clone(source)
  const bones: THREE.Bone[] = []
  const soles: { mesh: THREE.SkinnedMesh; vertices: number[] }[] = []
  model.traverse((node) => {
    if (node instanceof THREE.Bone) bones.push(node)
    if (!(node instanceof THREE.SkinnedMesh)) return
    const indices = node.geometry.getAttribute('skinIndex')
    const weights = node.geometry.getAttribute('skinWeight')
    const vertices = []
    for (let index = 0; index < indices.count; index++) {
      let weight = 0
      for (let slot = 0; slot < 4; slot++)
        if (
          /Foot|Toe/.test(
            node.skeleton.bones[indices.getComponent(index, slot)].name
          )
        )
          weight += weights.getComponent(index, slot)
      if (weight > 0.5) vertices.push(index)
    }
    soles.push({ mesh: node, vertices })
  })
  const hips = model.getObjectByName('Hips')!
  const rightArm = model.getObjectByName('RightArm')!
  const shoulderAxis = new THREE.Vector3(0, 0, 1).applyQuaternion(
    rightArm.parent!.getWorldQuaternion(new THREE.Quaternion()).invert()
  )
  const armClearance = 1
  const spreadArm = (angle: number) => {
    rightArm.quaternion.premultiply(
      new THREE.Quaternion().setFromAxisAngle(shoulderAxis, angle)
    )
    model.updateMatrixWorld(true)
  }
  const weapon = model.getObjectByName('BarkanRuneBlade')!
  const grip = new EnchantWeaponGrip(weapon)
  const mixer = new THREE.AnimationMixer(model)
  const sample = (clip: THREE.AnimationClip, time: number) => {
    mixer.stopAllAction()
    const action = mixer
      .clipAction(clip)
      .reset()
      .setLoop(THREE.LoopOnce, 1)
      .play()
    action.clampWhenFinished = true
    action.time = Math.min(time, clip.duration - 1e-6)
    mixer.update(0)
    return {
      rotations: bones.map((bone) => bone.quaternion.clone()),
      hips: hips.position.clone(),
    }
  }
  const idle = sample(grippedIdle, 0)
  const held = sample(enchant, 0)
  model.updateMatrixWorld(true)
  grip.update(1)
  const raisedSword = weapon.getWorldQuaternion(new THREE.Quaternion())
  sample(slash, BARKAN_RUNE_SLASH.slashEntry)
  model.updateMatrixWorld(true)
  spreadArm(armClearance)
  weapon.quaternion.copy(slashGrip)
  model.updateMatrixWorld(true)
  const readySword = weapon.getWorldQuaternion(new THREE.Quaternion())
  sample(grippedIdle, 0)
  grip.update(0)
  model.updateMatrixWorld(true)
  const chains = bones
    .filter((bone) => /WristChain$/.test(bone.name))
    .map((bone) => ({
      bone,
      rotation: bone.getWorldQuaternion(new THREE.Quaternion()),
    }))
  const times: number[] = []
  const rotations = bones.map(() => [] as number[])
  const rootPositions: number[] = []
  const weaponRotations: number[] = []
  const point = new THREE.Vector3()
  const smooth = (value: number) => THREE.MathUtils.smoothstep(value, 0, 1)
  const slashEnd =
    BARKAN_RUNE_SLASH.transitionEnd +
    slash.duration -
    BARKAN_RUNE_SLASH.slashEntry +
    BARKAN_RUNE_SLASH.swingEase / 2
  for (let frame = 0; frame <= BARKAN_RUNE_SLASH.duration * 60; frame++) {
    const time = frame / 60
    times.push(time)
    const attacking = time >= BARKAN_RUNE_SLASH.windup
    const elapsed = Math.max(0, time - BARKAN_RUNE_SLASH.transitionEnd)
    const advance =
      elapsed < BARKAN_RUNE_SLASH.swingEase
        ? (elapsed * elapsed) / (2 * BARKAN_RUNE_SLASH.swingEase)
        : elapsed - BARKAN_RUNE_SLASH.swingEase / 2
    const slashTime = BARKAN_RUNE_SLASH.slashEntry + advance
    const swing = attacking ? sample(slash, slashTime) : held
    const enter = smooth(time / 0.4)
    const transition = smooth(
      (time - BARKAN_RUNE_SLASH.windup) /
        (BARKAN_RUNE_SLASH.transitionEnd - BARKAN_RUNE_SLASH.windup)
    )
    const recovery = smooth(
      (time - slashEnd) / (BARKAN_RUNE_SLASH.recoveryEnd - slashEnd)
    )
    bones.forEach((bone, index) => {
      if (/^RightHand(?:Thumb|Index|Middle|Ring|Pinky)/.test(bone.name))
        bone.quaternion.copy(idle.rotations[index])
      else if (attacking)
        bone.quaternion
          .copy(held.rotations[index])
          .slerp(swing.rotations[index], transition)
          .slerp(idle.rotations[index], recovery)
      else
        bone.quaternion
          .copy(idle.rotations[index])
          .slerp(held.rotations[index], enter)
    })
    hips.position
      .copy(attacking ? held.hips : idle.hips)
      .lerp(attacking ? swing.hips : held.hips, attacking ? transition : enter)
      .lerp(idle.hips, recovery)
    model.updateMatrixWorld(true)
    if (attacking) {
      const spread =
        armClearance *
        (1 - smooth((slashTime - 0.65) / 0.55)) *
        transition *
        (1 - recovery)
      spreadArm(spread)
    }
    let lowest = Infinity
    for (const { mesh, vertices } of soles) {
      mesh.skeleton.update()
      for (const index of vertices)
        lowest = Math.min(
          lowest,
          mesh.getVertexPosition(index, point).applyMatrix4(mesh.matrixWorld).y
        )
    }
    if (Number.isFinite(lowest)) hips.position.y += 0.005 - lowest
    model.updateMatrixWorld(true)
    for (const { bone, rotation } of chains) {
      bone.quaternion.copy(
        bone
          .parent!.getWorldQuaternion(new THREE.Quaternion())
          .invert()
          .multiply(rotation)
      )
      bone.updateWorldMatrix(true, true)
    }
    if (attacking && time < BARKAN_RUNE_SLASH.transitionEnd) {
      weapon.quaternion.copy(
        weapon
          .parent!.getWorldQuaternion(new THREE.Quaternion())
          .invert()
          .multiply(raisedSword.clone().slerp(readySword, transition))
      )
    } else {
      grip.update(attacking ? 0 : enter)
      if (attacking) weapon.quaternion.slerp(slashGrip, 1 - recovery)
    }
    weapon.quaternion.toArray(weaponRotations, frame * 4)
    hips.position.toArray(rootPositions, frame * 3)
    bones.forEach((bone, index) =>
      bone.quaternion.toArray(rotations[index], frame * 4)
    )
  }
  mixer.stopAllAction()
  mixer.uncacheRoot(model)
  return new THREE.AnimationClip('RuneSlash', BARKAN_RUNE_SLASH.duration, [
    ...bones.map(
      (bone, index) =>
        new THREE.QuaternionKeyframeTrack(
          `${bone.name}.quaternion`,
          times,
          rotations[index]
        )
    ),
    new THREE.VectorKeyframeTrack('Hips.position', times, rootPositions),
    new THREE.QuaternionKeyframeTrack(
      `${weapon.name}.quaternion`,
      times,
      weaponRotations
    ),
  ])
}
