import assert from 'node:assert/strict'
import * as THREE from '../../client/node_modules/three/build/three.module.js'

function aim(bone, child, target) {
  const origin = bone.getWorldPosition(new THREE.Vector3())
  const rotation = new THREE.Quaternion().setFromUnitVectors(
    child.getWorldPosition(new THREE.Vector3()).sub(origin).normalize(), target.clone().sub(origin).normalize())
    .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
  bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(rotation))
  bone.updateMatrixWorld(true)
}

function solveLimb(upper, lower, end, target, pole, endRotation) {
  const origin = upper.getWorldPosition(new THREE.Vector3())
  const joint = lower.getWorldPosition(new THREE.Vector3())
  const a = origin.distanceTo(joint), b = joint.distanceTo(end.getWorldPosition(new THREE.Vector3()))
  const direction = target.clone().sub(origin)
  const distance = direction.length()
  assert.ok(distance < a + b && distance > Math.abs(a - b), `${upper.name}: unreachable target ${distance}`)
  direction.normalize()
  const along = (a * a - b * b + distance * distance) / (2 * distance)
  const bend = pole.clone().sub(origin)
  bend.addScaledVector(direction, -bend.dot(direction)).normalize()
  const elbow = origin.clone().addScaledVector(direction, along)
    .addScaledVector(bend, Math.sqrt(Math.max(0, a * a - along * along)))
  aim(upper, lower, elbow)
  aim(lower, end, target)
  end.quaternion.copy(end.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(endRotation))
  end.updateMatrixWorld(true)
}

export async function femaleSeated(root, { server, load }) {
  const { femaleSeat, femaleSeatOffset } = await server.ssrLoadModule('/src/previews/female-seat.ts')
  const source = await load('client/public/models/characters/modular_male/animations/social.glb')
  const donor = await load('assets/modular_human_male_01/fitted/base.glb')
  const chair = (await load(`client/public/models/${femaleSeat.chair.model}`)).scene
  chair.updateMatrixWorld(true)
  const ray = new THREE.Raycaster(new THREE.Vector3(0, 3.6, .072), new THREE.Vector3(0, -1, 0))
  const seatY = ray.intersectObject(chair, true)[0].point.y - femaleSeatOffset
  const seatContactY = seatY - femaleSeat.seatCompression
  const clip = source.animations.find(c => c.name === 'sit_idle').clone()
  const ratio = root.getObjectByName('Hips').position.y / donor.scene.getObjectByName('Hips').position.y
  for (const track of clip.tracks) {
    if (!track.name.endsWith('.position')) continue
    const name = track.name.split('.')[0]
    const from = donor.scene.getObjectByName(name).position, to = root.getObjectByName(name).position
    for (let i = 0; i < track.values.length; i += 3)
      new THREE.Vector3().fromArray(track.values, i).sub(from).multiplyScalar(ratio).add(to).toArray(track.values, i)
  }
  const bones = [], meshes = []
  root.traverse(node => {
    if (node.isBone) bones.push({ node, p: node.position.clone(), q: node.quaternion.clone(), s: node.scale.clone() })
    if (node.isSkinnedMesh) meshes.push(node)
  })
  const body = meshes[0], attributes = body.geometry.attributes
  const used = [...new Set(body.geometry.index.array)]
  const restPoint = i => new THREE.Vector3().fromBufferAttribute(attributes.position, i)
  const butt = used.filter(i => { const p = restPoint(i); return p.y > .828 && p.y < 1.026 && p.z < -.081 && Math.abs(p.x) > .045 })
  const legVertices = new Set(used.filter(i => { const p = restPoint(i); return p.y < 1.008 && Math.abs(p.x) < .324 }))
  const legFaces = []
  const indices = body.geometry.index.array
  for (let i = 0; i < indices.length; i += 3) {
    const face = Array.from(indices.slice(i, i + 3))
    if (face.every(index => legVertices.has(index))) legFaces.push(face)
  }
  const sides = ['Left', 'Right'].map((side, index) => ({
    side, sign: index === 0 ? 1 : -1,
    shoulder: root.getObjectByName(`${side}Shoulder`),
    thigh: root.getObjectByName(`${side}UpLeg`), shin: root.getObjectByName(`${side}Leg`), foot: root.getObjectByName(`${side}Foot`),
    arm: root.getObjectByName(`${side}Arm`), forearm: root.getObjectByName(`${side}ForeArm`), hand: root.getObjectByName(`${side}Hand`),
    handVertices: used.filter(i => Array.from({ length: 4 }, (_, k) => k).some(k =>
      attributes.skinWeight.array[i * 4 + k] > .25 && body.skeleton.bones[attributes.skinIndex.array[i * 4 + k]].name.startsWith(`${side}Hand`))),
    footVertices: used.filter(i => { const p = restPoint(i); return p.y < .117 && p.x * (index === 0 ? 1 : -1) > 0 }),
  }))
  const hip = root.getObjectByName('Hips')
  const spine = root.getObjectByName('Spine')
  const neck = root.getObjectByName('Neck'), head = root.getObjectByName('Head')
  root.updateMatrixWorld(true)
  const localForward = new THREE.Vector3(0, 0, 1)
    .applyQuaternion(head.getWorldQuaternion(new THREE.Quaternion()).invert())
  const changed = [hip, spine, neck, head, ...sides.flatMap(s => [s.thigh, s.shin, s.foot, s.shoulder, s.arm, s.forearm, s.hand])]
  const values = new Map(changed.map(bone => [bone.name, []]))
  const hipPositions = [], times = []
  const mixer = new THREE.AnimationMixer(root)
  const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1)
  action.clampWhenFinished = true
  action.play()
  const position = bone => bone.getWorldPosition(new THREE.Vector3())
  const skin = i => body.applyBoneTransform(i, restPoint(i)).applyMatrix4(body.matrixWorld)
  const update = () => { root.updateMatrixWorld(true); body.skeleton.update() }
  const frames = Math.ceil(clip.duration * 60) + 1
  for (let frame = 0; frame < frames; frame++) {
    const time = clip.duration * frame / (frames - 1)
    mixer.setTime(time)
    spine.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), THREE.MathUtils.degToRad(8)))
    update()
    const forward = localForward.clone().applyQuaternion(head.getWorldQuaternion(new THREE.Quaternion()))
    const level = new THREE.Vector3(forward.x, 0, forward.z).normalize()
    const lift = new THREE.Quaternion().setFromUnitVectors(forward, level)
    for (const [bone, fraction] of [[neck, .35], [head, .65]]) {
      const rotation = new THREE.Quaternion().slerp(lift, fraction)
        .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
      bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(rotation))
      bone.updateMatrixWorld(true)
    }
    const targets = sides.map(s => ({
      ankle: new THREE.Vector3(s.sign * .189, position(s.foot).y - Math.min(...s.footVertices.map(i => skin(i).y)) - femaleSeatOffset, .459),
      footRotation: s.foot.getWorldQuaternion(new THREE.Quaternion()),
      handRotation: s.hand.getWorldQuaternion(new THREE.Quaternion()),
    }))
    for (const s of sides) {
      const drop = new THREE.Quaternion().setFromAxisAngle(
        new THREE.Vector3(0, 0, 1), THREE.MathUtils.degToRad(-s.sign * 29))
      s.shoulder.quaternion.premultiply(drop)
    }
    hip.position.set(0, seatY + .099, -.009)
    for (let iteration = 0; iteration < 4; iteration++) {
      update()
      sides.forEach((s, i) => solveLimb(s.thigh, s.shin, s.foot, targets[i].ankle,
        new THREE.Vector3(s.sign * .198, .54, 1.08), targets[i].footRotation))
      update()
      hip.position.y += seatContactY - Math.min(...butt.map(i => skin(i).y))
    }
    update()
    sides.forEach((s, i) => solveLimb(s.thigh, s.shin, s.foot, targets[i].ankle,
      new THREE.Vector3(s.sign * .198, .54, 1.08), targets[i].footRotation))
    update()
    const surface = new Map([...legVertices].map(i => [i, skin(i)]))
    const triangles = legFaces.map(face => {
      const [a, b, c] = face.map(i => surface.get(i))
      return { a, b, c, minX: Math.min(a.x, b.x, c.x), maxX: Math.max(a.x, b.x, c.x),
        minZ: Math.min(a.z, b.z, c.z), maxZ: Math.max(a.z, b.z, c.z) }
    })
    const top = point => {
      let height = -Infinity
      for (const { a, b, c, minX, maxX, minZ, maxZ } of triangles) {
        if (point.x < minX || point.x > maxX || point.z < minZ || point.z > maxZ) continue
        const denominator = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z)
        if (Math.abs(denominator) < 3.24e-10) continue
        const u = ((b.z - c.z) * (point.x - c.x) + (c.x - b.x) * (point.z - c.z)) / denominator
        const v = ((c.z - a.z) * (point.x - c.x) + (a.x - c.x) * (point.z - c.z)) / denominator
        if (u >= 0 && v >= 0 && u + v <= 1) height = Math.max(height, u * a.y + v * b.y + (1 - u - v) * c.y)
      }
      return height
    }
    sides.forEach((s, i) => {
      const knee = position(s.shin)
      const target = new THREE.Vector3(knee.x, knee.y + .216, knee.z - .162)
      const shoulder = position(s.arm)
      const pole = new THREE.Vector3(s.sign * .189, shoulder.y - .252, shoulder.z - .081)
      for (let iteration = 0; iteration < 3; iteration++) {
        solveLimb(s.arm, s.forearm, s.hand, target, pole, targets[i].handRotation)
        update()
        const clearance = Math.min(...s.handVertices.map(index => { const p = skin(index); return p.y - top(p) }))
        assert.ok(Number.isFinite(clearance), `${s.side} hand misses the knee`)
        target.y += .0027 - clearance
      }
    })
    update()
    times.push(time)
    hipPositions.push(...hip.position.toArray())
    for (const bone of changed) values.get(bone.name).push(...bone.quaternion.toArray())
  }
  mixer.stopAllAction()
  mixer.uncacheRoot(root)
  for (const { node, p, q, s } of bones) { node.position.copy(p); node.quaternion.copy(q); node.scale.copy(s) }
  root.updateMatrixWorld(true)
  const replaced = new Set(changed.map(bone => `${bone.name}.quaternion`).concat('Hips.position'))
  clip.tracks = clip.tracks.filter(track => !replaced.has(track.name))
  clip.tracks.push(new THREE.VectorKeyframeTrack('Hips.position', times, hipPositions))
  for (const bone of changed) clip.tracks.push(new THREE.QuaternionKeyframeTrack(`${bone.name}.quaternion`, times, values.get(bone.name)))
  assert.ok(clip.validate())
  return clip
}
