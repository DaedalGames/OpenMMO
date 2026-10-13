import * as THREE from 'three'

export function femaleBootGround(
  model: THREE.Object3D,
  body: THREE.SkinnedMesh,
  boots: THREE.SkinnedMesh[],
  config: { local_quaternion_offsets: Record<string, number[]> }
) {
  const offsets = Object.entries(config.local_quaternion_offsets).map(
    ([name, values]) => {
      const bone = model.getObjectByName(name)
      if (!(bone instanceof THREE.Bone) || values.length !== 4)
        throw new Error('부츠의 발 자세 정보가 올바르지 않습니다.')
      return {
        bone,
        rotation: new THREE.Quaternion().fromArray(values),
        original: bone.quaternion.clone(),
      }
    }
  )
  const legStates = ['LeftUpLeg', 'LeftLeg', 'RightUpLeg', 'RightLeg'].map(
    (name) => {
      const bone = model.getObjectByName(name) as THREE.Bone
      return { bone, original: bone.quaternion.clone() }
    }
  )
  const states = [...offsets, ...legStates]
  let applied = false
  const sample = (mesh: THREE.SkinnedMesh, height: number) => {
    const position = mesh.geometry.attributes.position
    const indices: number[] = []
    for (let i = 0; i < position.count; i++)
      if (position.getY(i) < height) indices.push(i)
    return { mesh, indices }
  }
  const feet = sample(body, 0.08)
  const soles = boots.map((mesh) => sample(mesh, 0.18))
  const point = new THREE.Vector3()
  const aim = (bone: THREE.Bone, child: THREE.Bone, target: THREE.Vector3) => {
    const origin = bone.getWorldPosition(new THREE.Vector3())
    const rotation = new THREE.Quaternion()
      .setFromUnitVectors(
        child.getWorldPosition(new THREE.Vector3()).sub(origin).normalize(),
        target.clone().sub(origin).normalize()
      )
      .multiply(bone.getWorldQuaternion(new THREE.Quaternion()))
    bone.quaternion.copy(
      bone
        .parent!.getWorldQuaternion(new THREE.Quaternion())
        .invert()
        .multiply(rotation)
    )
    bone.updateMatrixWorld(true)
  }
  const liftFoot = (side: string, amount: number) => {
    const upper = model.getObjectByName(`${side}UpLeg`) as THREE.Bone
    const lower = model.getObjectByName(`${side}Leg`) as THREE.Bone
    const end = model.getObjectByName(`${side}Foot`) as THREE.Bone
    const origin = upper.getWorldPosition(new THREE.Vector3())
    const knee = lower.getWorldPosition(new THREE.Vector3())
    const ankle = end.getWorldPosition(new THREE.Vector3())
    const rotation = end.getWorldQuaternion(new THREE.Quaternion())
    const a = origin.distanceTo(knee),
      b = knee.distanceTo(ankle)
    const target = ankle.clone().add(new THREE.Vector3(0, amount, 0))
    const direction = target.clone().sub(origin)
    const distance = THREE.MathUtils.clamp(
      direction.length(),
      Math.abs(a - b) + 1e-6,
      a + b - 1e-6
    )
    direction.normalize()
    const along = (a * a - b * b + distance * distance) / (2 * distance)
    const bend = knee.clone().sub(origin)
    bend.addScaledVector(direction, -bend.dot(direction)).normalize()
    const joint = origin
      .clone()
      .addScaledVector(direction, along)
      .addScaledVector(bend, Math.sqrt(Math.max(0, a * a - along * along)))
    aim(upper, lower, joint)
    aim(lower, end, target)
    end.quaternion.copy(
      end
        .parent!.getWorldQuaternion(new THREE.Quaternion())
        .invert()
        .multiply(rotation)
    )
    end.updateMatrixWorld(true)
  }
  const minimum = (entries: typeof soles) => {
    let result = Infinity
    for (const { mesh, indices } of entries)
      for (const index of indices)
        result = Math.min(result, mesh.getVertexPosition(index, point).y)
    return result
  }
  const restore = () => {
    if (!applied) return
    for (const { bone, original } of states) bone.quaternion.copy(original)
    applied = false
  }
  return {
    restore,
    apply(seatOffset?: number) {
      restore()
      model.updateMatrixWorld(true)
      const originalFloor = minimum([feet])
      for (const state of states) state.original.copy(state.bone.quaternion)
      for (const state of offsets)
        state.bone.quaternion.multiply(state.rotation)
      applied = true
      model.updateMatrixWorld(true)
      if (seatOffset !== undefined) {
        for (const side of ['Left', 'Right']) {
          const entries = soles.filter(({ mesh }) => {
            const x = mesh.geometry.attributes.position.getX(0)
            return side === 'Left' ? x > 0 : x < 0
          })
          const amount = Math.max(0, -minimum(entries) - seatOffset)
          if (amount > 0) liftFoot(side, amount)
        }
        model.updateMatrixWorld(true)
        return 0
      }
      const lift = originalFloor - minimum(soles)
      return Number.isFinite(lift) ? Math.max(0, lift) : 0
    },
  }
}
