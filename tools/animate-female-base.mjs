import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, hash } from './lib/headless-three.mjs'

const output = 'assets/modular_human_female_01/rig_v1/'
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
    baked.push(THREE.AnimationClip.toJSON(clip))
    console.log(clip.name, frames, 'floor correction', Math.min(...corrections).toFixed(4), Math.max(...corrections).toFixed(4))
    sourceMixer.stopAllAction(); mixer.stopAllAction()
    sourceMixer.uncacheRoot(donor); mixer.uncacheRoot(target)
  }
  writeFileSync(new URL('../' + output + 'clips.json', import.meta.url), JSON.stringify({
    method: 'Existing local rotation tracks applied to the fitted bone axes; rest-offset translation scaling; 60 Hz floor matching to the source silhouette with per-clip sole offset removed, preserving airborne motion.',
    sources: sources.map(path => ({ path, sha256: hash(path) })), hip_ratio: ratio, clips: baked,
  }) + '\n')
} finally { await server.close() }
