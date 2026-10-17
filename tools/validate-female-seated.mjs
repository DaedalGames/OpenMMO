import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler } from './lib/headless-three.mjs'

const context = await headlessThree()
try {
  const { femaleSeat, femaleSeatOffset } = await context.server.ssrLoadModule('/src/previews/female-seat.ts')
  const base = await context.load('assets/modular_human_female_01/rig_v1/female-base.glb')
  const chair = (await context.load(`client/public/models/${femaleSeat.chair.model}`)).scene
  chair.updateMatrixWorld(true)
  const raycaster = new THREE.Raycaster(new THREE.Vector3(0, 3.6, .072), new THREE.Vector3(0, -1, 0))
  const seatY = raycaster.intersectObject(chair, true)[0].point.y - femaleSeatOffset
  const expectedSeatGap = -femaleSeat.seatCompression
  const meshes = []
  base.scene.traverse(node => { if (node.isSkinnedMesh) meshes.push(node) })
  const mesh = meshes[0], a = mesh.geometry.attributes, index = mesh.geometry.index.array
  const used = [...new Set(index)]
  const point = i => new THREE.Vector3().fromBufferAttribute(a.position, i)
  const lower = new Set(used.filter(i => { const p = point(i); return p.y < 1.008 && Math.abs(p.x) < .324 }))
  const triangles = []
  for (let i = 0; i < index.length; i += 3) {
    const face = Array.from(index.slice(i, i + 3))
    if (face.every(v => lower.has(v))) triangles.push(face)
  }
  const hands = ['Left', 'Right'].map(side => used.filter(i => [0, 1, 2, 3].some(k =>
    a.skinWeight.array[i * 4 + k] > .25 && mesh.skeleton.bones[a.skinIndex.array[i * 4 + k]].name.startsWith(`${side}Hand`))))
  const seat = used.filter(i => { const p = point(i); return p.y > .828 && p.y < 1.026 && p.z < -.081 && Math.abs(p.x) > .045 })
  base.scene.updateMatrixWorld(true)
  const head = base.scene.getObjectByName('Head')
  const localForward = new THREE.Vector3(0, 0, 1)
    .applyQuaternion(head.getWorldQuaternion(new THREE.Quaternion()).invert())
  let maximumHeadPitch = 0, maximumElbowOffset = 0
  let minimumHandGap = Infinity, maximumContactGap = -Infinity, minimumSeatGap = Infinity, maximumSeatGap = -Infinity
  const ray = new THREE.Ray(), intersection = new THREE.Vector3()
  for (const {} of clipSampler(base.scene, { samples: 61, restore: mesh.skeleton.bones })(base.animations.find(c => c.name === 'sit_idle'))) {
    const forward = localForward.clone().applyQuaternion(head.getWorldQuaternion(new THREE.Quaternion()))
    const pitch = Math.abs(THREE.MathUtils.radToDeg(Math.asin(forward.y)))
    assert.ok(pitch < 1, `Seated gaze is not level: ${pitch}`)
    maximumHeadPitch = Math.max(maximumHeadPitch, pitch)
    for (const side of ['Left', 'Right']) {
      const elbow = base.scene.getObjectByName(`${side}ForeArm`).getWorldPosition(new THREE.Vector3())
      assert.ok(Math.abs(elbow.x) < .216, `Elbow is too far from the body: ${elbow.x}`)
      maximumElbowOffset = Math.max(maximumElbowOffset, Math.abs(elbow.x))
    }
    mesh.skeleton.update()
    const positions = new Map(used.map(i => [i, mesh.applyBoneTransform(i, point(i)).applyMatrix4(mesh.matrixWorld)]))
    const faces = triangles.map(face => {
      const points = face.map(i => positions.get(i))
      return { points, minX: Math.min(...points.map(p => p.x)), maxX: Math.max(...points.map(p => p.x)),
        minZ: Math.min(...points.map(p => p.z)), maxZ: Math.max(...points.map(p => p.z)) }
    })
    for (const hand of hands) {
      let contact = Infinity
      for (const i of hand) {
        const p = positions.get(i)
        ray.set(new THREE.Vector3(p.x, 3.6, p.z), new THREE.Vector3(0, -1, 0))
        let top = -Infinity
        for (const { points, minX, maxX, minZ, maxZ } of faces) {
          if (p.x < minX || p.x > maxX || p.z < minZ || p.z > maxZ) continue
          if (ray.intersectTriangle(...points, false, intersection)) top = Math.max(top, intersection.y)
        }
        contact = Math.min(contact, p.y - top)
      }
      assert.ok(Number.isFinite(contact) && contact > .0009 && contact < .0054, `Hand/knee clearance: ${contact}`)
      minimumHandGap = Math.min(minimumHandGap, contact)
      maximumContactGap = Math.max(maximumContactGap, contact)
    }
    const gap = Math.min(...seat.map(i => positions.get(i).y)) - seatY
    assert.ok(Math.abs(gap - expectedSeatGap) < .0009, `Seat compression: ${gap}`)
    minimumSeatGap = Math.min(minimumSeatGap, gap)
    maximumSeatGap = Math.max(maximumSeatGap, gap)
  }
  const report = { samples: 61, chair_model: femaleSeat.chair.model, interaction_offset: femaleSeat.chair.interactOffset,
    seat_compression: femaleSeat.seatCompression,
    maximum_head_pitch_degrees: maximumHeadPitch, maximum_elbow_offset: maximumElbowOffset,
    minimum_hand_surface_gap: minimumHandGap, maximum_hand_contact_gap: maximumContactGap,
    minimum_seat_gap: minimumSeatGap, maximum_seat_gap: maximumSeatGap }
  writeFileSync('assets/modular_human_female_01/rig_v1/seated-validation.json', JSON.stringify(report, null, 2) + '\n')
  console.log(report)
} finally { await context.server.close() }
