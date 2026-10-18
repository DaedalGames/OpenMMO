import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree } from './lib/headless-three.mjs'

const { server, load } = await headlessThree({
  material: () => new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }),
})
try {
  const { createBarkanRuneSlash, BARKAN_RUNE_SLASH: timing } =
    await server.ssrLoadModule('/src/lib/utils/barkanRuneSlash.ts')
  const { withBarkanRuneGrip } = await server.ssrLoadModule(
    '/src/lib/utils/barkanRuneGrip.ts'
  )
  const { retargetAnimationsForCharacterModel } = await server.ssrLoadModule(
    '/src/lib/utils/characterAnimationUtils.ts'
  )
  const [base, social, melee, sword] = await Promise.all([
    load('assets/monsters/barkan/rig_v1/barkan.glb'),
    load('client/public/models/characters/modular_male/animations/social.glb'),
    load(
      'client/public/models/characters/modular_male/animations/combat_melee.glb'
    ),
    load('client/public/models/weapons/rune_blade.glb'),
  ])
  const model = base.scene
  const originals = [social, melee].map((pack) =>
    pack.animations.map((clip) =>
      JSON.stringify(THREE.AnimationClip.toJSON(clip))
    )
  )
  const [[enchant], [slash]] = await Promise.all([
    retargetAnimationsForCharacterModel(
      model,
      social.scene,
      social.animations.filter((clip) => clip.name === 'enchant_weapon')
    ),
    retargetAnimationsForCharacterModel(
      model,
      melee.scene,
      melee.animations.filter((clip) => clip.name === 'slash1')
    ),
  ])
  const weapon = sword.scene
  weapon.name = 'BarkanRuneBlade'
  weapon.position.set(0.019808135, 0.082672966, 0.04)
  weapon.rotation.z = THREE.MathUtils.degToRad(-3)
  model.getObjectByName('RightHand').add(weapon)
  const idle = withBarkanRuneGrip(
    base.animations.find((clip) => clip.name === 'Idle')
  )
  model.updateMatrixWorld(true)
  melee.scene.updateMatrixWorld(true)
  const profile = JSON.parse(
    readFileSync(
      new URL(
        '../assets/modular_human_male_01/animations/hand-grips.json',
        import.meta.url
      )
    )
  )
  const slashGrip = model
    .getObjectByName('RightHand')
    .getWorldQuaternion(new THREE.Quaternion())
    .invert()
    .multiply(
      melee.scene
        .getObjectByName('RightHand')
        .getWorldQuaternion(new THREE.Quaternion())
    )
    .multiply(new THREE.Quaternion().fromArray(profile.iron_sword.quaternion))
  const clip = createBarkanRuneSlash(model, idle, enchant, slash, slashGrip)
  assert.equal(clip.duration, timing.duration)
  assert.equal(withBarkanRuneGrip(clip), clip)
  const bones = []
  const bodies = []
  model.traverse((node) => {
    if (node.isBone) bones.push(node)
  })
  model.traverse((mesh) => {
    if (!mesh.isSkinnedMesh) return
    const { skinIndex, skinWeight } = mesh.geometry.attributes
    const indices = mesh.geometry.index.array
    const faces = new Set()
    for (let face = 0; face < indices.length / 3; face++) {
      let weight = 0
      for (let corner = 0; corner < 3; corner++)
        for (let slot = 0; slot < 4; slot++) {
          const vertex = indices[face * 3 + corner]
          if (
            /^(Hips|Spine[12]?|Neck|Head)$/.test(
              mesh.skeleton.bones[skinIndex.getComponent(vertex, slot)].name
            )
          )
            weight += skinWeight.getComponent(vertex, slot)
        }
      if (weight > 1.5) faces.add(face)
    }
    bodies.push({ mesh, faces })
  })
  const raycaster = new THREE.Raycaster()
  const collisions = []
  const tracks = new Map(
    clip.tracks.map((track) => [track.name, track.createInterpolant()])
  )
  const mixer = new THREE.AnimationMixer(model)
  const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1).play()
  action.clampWhenFinished = true
  let floor = Infinity,
    bladeUp = -Infinity,
    maximumJointStep = 0
  let previous, first, last
  const sweep = new THREE.Box3()
  for (let frame = 0; frame <= timing.duration * 120; frame++) {
    const time = frame / 120
    mixer.setTime(time)
    model.updateMatrixWorld(true)
    const pose = bones.map((bone) => bone.quaternion.clone())
    for (const bone of bones) {
      assert.ok(
        [...bone.position.toArray(), ...bone.quaternion.toArray()].every(
          Number.isFinite
        )
      )
      assert.ok(Math.abs(bone.quaternion.length() - 1) < 1e-5)
    }
    if (previous)
      pose.forEach((rotation, index) => {
        if (
          /^(Right(?:Shoulder|Arm|ForeArm|Hand)|Spine[12]?)$/.test(
            bones[index].name
          )
        )
          maximumJointStep = Math.max(
            maximumJointStep,
            rotation.angleTo(previous[index])
          )
      })
    previous = pose
    if (frame === 0) first = pose
    last = pose
    floor = Math.min(floor, new THREE.Box3().setFromObject(weapon, true).min.y)
    const tip = weapon.localToWorld(new THREE.Vector3(1.617, 0, 0))
    if (time >= timing.windup && time <= timing.strikeEnd) {
      for (const { mesh } of bodies) {
        mesh.skeleton.update()
        mesh.computeBoundingSphere()
      }
      let pierced = false
      for (const across of [-0.12, 0, 0.12]) {
        const start = weapon.localToWorld(new THREE.Vector3(0.25, across, 0))
        const end = weapon.localToWorld(new THREE.Vector3(1.617, across, 0))
        raycaster.set(start, end.clone().sub(start).normalize())
        raycaster.far = start.distanceTo(end)
        for (const { mesh, faces } of bodies)
          if (
            raycaster
              .intersectObject(mesh, false)
              .some((hit) => faces.has(hit.faceIndex))
          )
            pierced = true
      }
      if (pierced) collisions.push(Number(time.toFixed(4)))
    }
    if (time > 0.5 && time < timing.windup) {
      const bottom = weapon.localToWorld(new THREE.Vector3(0, 0, 0))
      const direction = tip.clone().sub(bottom).normalize()
      assert.ok(
        direction.y > 0.995,
        'The telegraph must hold the blade upright'
      )
      bladeUp = Math.max(bladeUp, tip.y)
    }
    if (time >= timing.strikeStart && time <= timing.strikeEnd)
      sweep.expandByPoint(tip)
    if (
      frame % 2 === 0 &&
      time >= timing.transitionEnd + timing.swingEase &&
      time <
        timing.transitionEnd +
          slash.duration -
          timing.slashEntry +
          timing.swingEase / 2
    ) {
      for (const track of slash.tracks) {
        if (
          !/^(Right(?:Shoulder|Arm|ForeArm|Hand)|Spine[12]?)\.quaternion$/.test(
            track.name
          )
        )
          continue
        if (
          track.name === 'RightArm.quaternion' &&
          time <
            timing.transitionEnd +
              1.2 -
              timing.slashEntry +
              timing.swingEase / 2
        )
          continue
        const expected = new THREE.Quaternion().fromArray(
          track
            .createInterpolant()
            .evaluate(
              time -
                timing.transitionEnd +
                timing.slashEntry -
                timing.swingEase / 2
            )
        )
        const actual = new THREE.Quaternion().fromArray(
          tracks.get(track.name).evaluate(time)
        )
        assert.ok(
          actual.angleTo(expected) < 0.003,
          `${track.name} must preserve slash1`
        )
      }
    }
  }
  first.forEach((rotation, index) =>
    assert.ok(rotation.angleTo(last[index]) < 0.003, 'Return to idle')
  )
  assert.ok(
    maximumJointStep < 0.18,
    `Discontinuous arm rotation: ${maximumJointStep}`
  )
  assert.ok(floor > 0, `Sword below ground: ${floor}`)
  assert.ok(
    sweep.getSize(new THREE.Vector3()).x > 1.5,
    'Slash crosses the front'
  )
  assert.deepEqual(
    collisions,
    [],
    'The rune blade must clear the head and torso throughout the transition and strike'
  )
  ;[social, melee].forEach((pack, index) =>
    pack.animations.forEach((clip, i) =>
      assert.equal(
        JSON.stringify(THREE.AnimationClip.toJSON(clip)),
        originals[index][i]
      )
    )
  )
  console.log(
    JSON.stringify(
      {
        source_clips: ['enchant_weapon', 'slash1'],
        duration_s: clip.duration,
        sampled_frames: timing.duration * 120 + 1,
        minimum_blade_clearance_m: floor,
        raised_blade_tip_m: bladeUp,
        maximum_joint_step_degrees: THREE.MathUtils.radToDeg(maximumJointStep),
        blade_tip_sweep_m: sweep.getSize(new THREE.Vector3()).toArray(),
        body_intersections: collisions,
        source_clips_preserved: true,
      },
      null,
      2
    )
  )
} finally {
  await server.close()
}
