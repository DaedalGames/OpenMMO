import * as THREE from 'three'

export interface RobePhysics {
  waist_height_m: number
  hem_height_m: number
  center_z_m: number
  waist_radii_m: [number, number]
  vertices?: number[]
  // Without `vertices`, vertices below this height that are not fixed follow the hem.
  driven_below_m?: number
  fixed_vertices?: number[]
  // Fraction of the clearance angle to apply; a short skirt reads better grazing the thigh than flaring.
  lift?: number
  // With colliders, moving legs still drive the hem by this much so running keeps its bounce.
  follow?: number
  blend_m?: number
  max_angle?: number
  // Limits which hem columns drive this mesh, so a flap moves as one piece instead of splaying sideways.
  columns_deg?: [number, number]
  // With colliders, each hem column lifts only until it clears them instead of following the thigh axis.
  colliders?: {
    bone: string
    center: [number, number, number]
    radii: [number, number, number]
  }[]
}

const COLUMNS = 4
// Front and back columns sit on the centerline, so both legs share one control there.
const CONTROLS = [
  { sides: [0, 1], column: 0 },
  { sides: [0, 1], column: COLUMNS - 1 },
  ...[0, 1].flatMap((side) =>
    Array.from({ length: COLUMNS - 2 }, (_, i) => ({
      sides: [side],
      column: i + 1,
    }))
  ),
]
const controlIndex = (side: number, column: number) =>
  column === 0
    ? 0
    : column === COLUMNS - 1
      ? 1
      : 1 + side * (COLUMNS - 2) + column
function controlFrame(config: RobePhysics, index: number) {
  const { sides, column } = CONTROLS[index]
  const angle = (column / (COLUMNS - 1)) * Math.PI
  const outward = new THREE.Vector3(
    (sides[0] === 0 ? 1 : -1) * Math.sin(angle),
    0,
    Math.cos(angle)
  )
  const pivot = new THREE.Vector3(
    outward.x * config.waist_radii_m[0],
    config.waist_height_m,
    config.center_z_m + outward.z * config.waist_radii_m[1]
  )
  return { outward, pivot }
}
const STEP = 1 / 30
const MAX_ANGLE = 1.65
const SWEEP = 0.05
// Thigh swing (rad/s) at which `follow` applies in full; standing poses hang on clearance alone.
const ACTIVE_SPEED = 3
const CLEARANCE = 1.06
const baseSkeletons = new WeakMap<THREE.SkinnedMesh, THREE.Skeleton>()
const geometries = new WeakMap<
  THREE.BufferGeometry,
  {
    geometry: THREE.BufferGeometry
    users: number
    hems: (THREE.Vector3 | null)[]
  }
>()
const hinges = new WeakMap<THREE.Skeleton, Hinge[]>()

export function robeBaseSkeleton(mesh: THREE.SkinnedMesh) {
  return baseSkeletons.get(mesh) ?? mesh.skeleton
}

function bindSkeleton(mesh: THREE.SkinnedMesh, skeleton: THREE.Skeleton) {
  mesh.bind(skeleton, mesh.bindMatrix.clone())
  // Rebuild main and shadow passes for the new bone-buffer size.
  mesh.dispose()
}

function drivenVertices(
  positions: THREE.BufferAttribute | THREE.InterleavedBufferAttribute,
  config: RobePhysics
) {
  if (config.vertices) return config.vertices
  const fixed = new Set(config.fixed_vertices)
  const below = config.driven_below_m ?? config.waist_height_m
  const vertices: number[] = []
  for (let i = 0; i < positions.count; i++)
    if (!fixed.has(i) && positions.getY(i) < below) vertices.push(i)
  return vertices
}

function sharedGeometry(
  original: THREE.BufferGeometry,
  config: RobePhysics,
  hips: number,
  boneCount: number
) {
  let shared = geometries.get(original)
  if (shared) {
    shared.users++
    return shared
  }
  const geometry = original.clone()
  const positions = geometry.getAttribute('position')
  const joints = geometry.getAttribute('skinIndex') as THREE.BufferAttribute
  const weights = geometry.getAttribute('skinWeight') as THREE.BufferAttribute
  const hems: (THREE.Vector3 | null)[] = CONTROLS.map(() => null)
  const blendWidth = config.blend_m ?? 0.06
  const anchors = (config.fixed_vertices ?? []).map((i) =>
    new THREE.Vector3().fromBufferAttribute(positions, i)
  )
  const point = new THREE.Vector3()
  for (const i of drivenVertices(positions, config)) {
    const x = positions.getX(i)
    const theta = THREE.MathUtils.clamp(
      Math.atan2(Math.abs(x), positions.getZ(i) - config.center_z_m),
      THREE.MathUtils.degToRad(config.columns_deg?.[0] ?? 0),
      THREE.MathUtils.degToRad(config.columns_deg?.[1] ?? 180)
    )
    const across = (theta / Math.PI) * (COLUMNS - 1)
    const column = Math.min(Math.floor(across), COLUMNS - 2)
    const blend = across - column
    point.fromBufferAttribute(positions, i)
    let nearest = Infinity
    for (const anchor of anchors)
      nearest = Math.min(nearest, anchor.distanceToSquared(point))
    // Fixed belt anchors can sit below driven vertices, so fade in by distance too.
    const near =
      1 - THREE.MathUtils.smoothstep(Math.sqrt(nearest), 0, blendWidth)
    const amount = Math.min(
      THREE.MathUtils.smoothstep(
        (config.driven_below_m ?? config.waist_height_m) - point.y,
        0,
        blendWidth
      ),
      1 - near
    )
    const side = x >= 0 ? 0 : 1
    // Near fixed anchors keep their skin weights so the seam stays closed; elsewhere the hips carry the rest.
    const influences = new Map<number, number>()
    const add = (bone: number, weight: number) =>
      influences.set(bone, (influences.get(bone) ?? 0) + weight)
    for (let k = 0; k < 4; k++)
      add(
        joints.getComponent(i, k),
        weights.getComponent(i, k) * (1 - amount) * near
      )
    add(hips, (1 - amount) * (1 - near))
    add(boneCount + controlIndex(side, column), amount * (1 - blend))
    add(boneCount + controlIndex(side, column + 1), amount * blend)
    const strongest = [...influences].sort((p, q) => q[1] - p[1]).slice(0, 4)
    const total = strongest.reduce((sum, [, weight]) => sum + weight, 0)
    while (strongest.length < 4) strongest.push([0, 0])
    const [j0, j1, j2, j3] = strongest.map(([bone]) => bone)
    const [w0, w1, w2, w3] = strongest.map(([, weight]) => weight / total)
    joints.setXYZW(i, j0, j1, j2, j3)
    weights.setXYZW(i, w0, w1, w2, w3)
    const dominant = controlIndex(side, blend < 0.5 ? column : column + 1)
    const lowest = hems[dominant]
    if (!lowest || point.y < lowest.y + config.waist_height_m)
      hems[dominant] = point.clone().sub(controlFrame(config, dominant).pivot)
  }
  geometry.computeBoundingSphere()
  shared = { geometry, users: 1, hems }
  geometries.set(original, shared)
  return shared
}

// Meshes with the same base skeleton, bind matrix and waist share one set of hem bones.
type Hinge = ReturnType<typeof createHinge>

function createHinge(
  base: THREE.Skeleton,
  bindMatrix: THREE.Matrix4,
  config: RobePhysics,
  key: string
) {
  const hips = base.bones.findIndex((bone) => bone.name === 'Hips')
  const legs = ['Left', 'Right'].map((side) => {
    const upper = base.bones.find((bone) => bone.name === side + 'UpLeg')
    const lower = base.bones.find((bone) => bone.name === side + 'Leg')
    if (!upper || !lower) throw new Error('Missing robe leg bones')
    return {
      upper,
      lower,
      direction: new THREE.Vector3(),
      previous: new THREE.Vector3(),
      activity: 0,
    }
  })
  if (hips < 0) throw new Error('Missing robe hip bone')
  const hip = base.bones[hips]
  const toHip = base.boneInverses[hips].clone().multiply(bindMatrix)
  const down = new THREE.Vector3(0, -1, 0).transformDirection(toHip)
  const controls = CONTROLS.map(({ sides }, i) => {
    const { outward, pivot: rest } = controlFrame(config, i)
    const pivot = rest.clone().applyMatrix4(toHip)
    const restAxis = new THREE.Vector3(0, -1, 0).cross(outward).normalize()
    outward.transformDirection(toHip)
    const bone = new THREE.Bone()
    bone.name = `RobeHem${i}`
    bone.position.copy(pivot)
    hip.add(bone)
    const inverse = new THREE.Matrix4()
      .makeTranslation(pivot.clone().negate())
      .multiply(base.boneInverses[hips])
    return {
      bone,
      inverse,
      outward,
      axis: new THREE.Vector3().crossVectors(down, outward).normalize(),
      sides,
      rest,
      restAxis,
      hem: new THREE.Vector3(),
      limits: [] as number[],
      angle: 0,
      velocity: 0,
    }
  })
  const shields = (config.colliders ?? []).map((collider) => ({
    bone: base.bones.findIndex((bone) => bone.name === collider.bone),
    rest: new THREE.Matrix4()
      .makeScale(...collider.radii)
      .setPosition(...collider.center),
    toUnit: new THREE.Matrix4(),
  }))
  if (shields.some((shield) => shield.bone < 0))
    throw new Error('Missing robe collider bone')
  const skin = (target: THREE.Matrix4, index: number) =>
    target
      .multiplyMatrices(base.bones[index].matrixWorld, base.boneInverses[index])
      .multiply(bindMatrix)
  const hipSkin = new THREE.Matrix4()
  const start = new THREE.Vector3()
  const end = new THREE.Vector3()
  const swing = new THREE.Quaternion()
  const skeleton = new THREE.Skeleton(
    [...base.bones, ...controls.map((control) => control.bone)],
    [...base.boneInverses, ...controls.map((control) => control.inverse)]
  )
  const inverseHip = new THREE.Matrix4()
  const point = new THREE.Vector3()
  const anchor = new THREE.Vector3()
  const previousAnchor = new THREE.Vector3()
  const lift = config.lift ?? 1
  const maxAngle = config.max_angle ?? MAX_ANGLE
  const follow = config.follow ?? 0
  let accumulator = 0
  let initialized = false

  function refresh() {
    inverseHip.copy(hip.matrixWorld).invert()
    anchor.setFromMatrixPosition(hip.matrixWorld)
    for (const leg of legs) {
      leg.direction
        .setFromMatrixPosition(leg.lower.matrixWorld)
        .sub(point.setFromMatrixPosition(leg.upper.matrixWorld))
        .transformDirection(inverseHip)
    }
    if (!shields.length) return
    skin(hipSkin, hips)
    for (const shield of shields)
      skin(shield.toUnit, shield.bone)
        .multiply(shield.rest)
        .invert()
        .multiply(hipSkin)
  }

  // Contact already present in the bind pose is accepted so the rest shape stays put.
  function extend(hems: (THREE.Vector3 | null)[]) {
    const toUnit = new THREE.Matrix4()
    for (const [i, control] of controls.entries()) {
      const hem = hems[i]
      if (hem && hem.lengthSq() > control.hem.lengthSq()) control.hem.copy(hem)
      control.limits = shields.map((shield) => {
        toUnit
          .multiplyMatrices(bindMatrix, shield.rest)
          .invert()
          .multiply(bindMatrix)
        return Math.min(CLEARANCE, distance(control, 0, toUnit))
      })
    }
  }

  function distance(
    control: (typeof controls)[number],
    angle: number,
    toUnit: THREE.Matrix4
  ) {
    start.copy(control.rest).applyMatrix4(toUnit)
    end
      .copy(control.hem)
      .applyQuaternion(swing.setFromAxisAngle(control.restAxis, angle))
      .add(control.rest)
      .applyMatrix4(toUnit)
      .sub(start)
    const t = THREE.MathUtils.clamp(
      -start.dot(end) / Math.max(end.lengthSq(), 1e-12),
      0,
      1
    )
    return start.addScaledVector(end, t).lengthSq()
  }

  function clear(control: (typeof controls)[number], angle: number) {
    for (const [i, shield] of shields.entries())
      if (distance(control, angle, shield.toUnit) < control.limits[i])
        return false
    return true
  }

  function contact(control: (typeof controls)[number]) {
    if (clear(control, 0)) return 0
    let low = 0
    for (let high = SWEEP; high <= maxAngle; high += SWEEP) {
      if (!clear(control, high)) {
        low = high
        continue
      }
      for (let i = 0; i < 4; i++) {
        const middle = (low + high) / 2
        if (clear(control, middle)) high = middle
        else low = middle
      }
      return high
    }
    return maxAngle
  }

  function stride(control: (typeof controls)[number]) {
    let angle = 0
    for (const side of control.sides) {
      const leg = legs[side].direction
      const forward = Math.max(0, leg.dot(control.outward))
      if (forward < 0.005) continue
      const margin = 0.12 * THREE.MathUtils.smoothstep(forward, 0, 0.3)
      angle = Math.max(angle, Math.atan2(forward, leg.dot(down)) + margin)
    }
    return angle
  }

  function activity(control: (typeof controls)[number]) {
    let value = 0
    for (const side of control.sides)
      value = Math.max(value, legs[side].activity)
    return value
  }

  function minimum(control: (typeof controls)[number]) {
    const target = shields.length
      ? Math.max(
          contact(control) * lift,
          stride(control) * follow * activity(control)
        )
      : stride(control) * lift
    return THREE.MathUtils.clamp(target, 0, maxAngle)
  }

  function draw() {
    for (const control of controls) {
      control.bone.quaternion.setFromAxisAngle(control.axis, control.angle)
      control.bone.updateMatrixWorld(true)
    }
  }

  function reset() {
    refresh()
    for (const leg of legs) {
      leg.previous.copy(leg.direction)
      leg.activity = 0
    }
    for (const control of controls) {
      control.angle = minimum(control)
      control.velocity = 0
    }
    previousAnchor.copy(anchor)
    accumulator = 0
    initialized = true
    draw()
  }

  function update(visible: boolean, dt: number, requestedStep: number) {
    if (!visible) {
      initialized = false
      return
    }
    if (!initialized || dt > 0.25) {
      reset()
      return
    }
    const step = Math.max(STEP, Math.min(requestedStep, 1 / 15))
    accumulator += Math.max(0, dt)
    if (accumulator + 1e-10 < step) return
    accumulator %= step
    refresh()
    if (
      anchor.distanceToSquared(previousAnchor) >
      2.25 * hip.matrixWorld.getMaxScaleOnAxis() ** 2
    ) {
      reset()
      return
    }
    previousAnchor.copy(anchor)
    const settle = 1 - Math.exp(-8 * step)
    for (const leg of legs) {
      const speed = leg.direction.angleTo(leg.previous) / step
      leg.previous.copy(leg.direction)
      leg.activity +=
        (Math.min(1, speed / ACTIVE_SPEED) - leg.activity) * settle
    }
    for (const control of controls) {
      const target = minimum(control)
      control.velocity =
        (control.velocity + (target - control.angle) * 65 * step) *
        Math.exp(-12 * step)
      control.angle = THREE.MathUtils.clamp(
        control.angle + control.velocity * step,
        target,
        maxAngle
      )
      if (
        (control.angle === target && control.velocity < 0) ||
        control.angle === maxAngle
      )
        control.velocity = 0
    }
    draw()
  }

  function dispose() {
    for (const control of controls) control.bone.removeFromParent()
    skeleton.dispose()
  }

  return {
    key,
    bindMatrix: bindMatrix.clone(),
    hips,
    skeleton,
    users: new Set<THREE.SkinnedMesh>(),
    lead: null as THREE.SkinnedMesh | null,
    extend,
    update,
    reset,
    dispose,
  }
}

function acquireHinge(mesh: THREE.SkinnedMesh, config: RobePhysics) {
  const base = mesh.skeleton
  const key = [
    config.waist_height_m,
    config.center_z_m,
    ...config.waist_radii_m,
    config.lift ?? 1,
    config.max_angle ?? MAX_ANGLE,
    config.follow ?? 0,
    JSON.stringify(config.colliders ?? null),
  ].join()
  let list = hinges.get(base)
  if (!list) hinges.set(base, (list = []))
  let hinge = list.find(
    (candidate) =>
      candidate.key === key && candidate.bindMatrix.equals(mesh.bindMatrix)
  )
  if (!hinge) {
    hinge = createHinge(base, mesh.bindMatrix, config, key)
    list.push(hinge)
  }
  hinge.users.add(mesh)
  hinge.lead ??= mesh
  return hinge
}

function releaseHinge(
  base: THREE.Skeleton,
  hinge: Hinge,
  mesh: THREE.SkinnedMesh
) {
  hinge.users.delete(mesh)
  if (hinge.lead === mesh)
    hinge.lead = hinge.users.values().next().value ?? null
  if (hinge.users.size) return
  hinge.dispose()
  const list = hinges.get(base)!
  list.splice(list.indexOf(hinge), 1)
  if (!list.length) hinges.delete(base)
}

export function createRobeRig(
  mesh: THREE.SkinnedMesh,
  config: RobePhysics,
  onDispose?: () => void
) {
  const original = mesh.geometry
  const originalSkeleton = mesh.skeleton
  const hinge = acquireHinge(mesh, config)
  const shared = sharedGeometry(
    original,
    config,
    hinge.hips,
    originalSkeleton.bones.length
  )
  const geometry = shared.geometry
  hinge.extend(shared.hems)
  const originalBounds = mesh.boundingSphere
  mesh.boundingSphere = geometry.boundingSphere!.clone()
  mesh.boundingSphere.radius +=
    2 * (config.waist_height_m - config.hem_height_m)
  mesh.geometry = geometry
  bindSkeleton(mesh, hinge.skeleton)
  baseSkeletons.set(mesh, originalSkeleton)
  let active = true

  function reset() {
    if (active) hinge.reset()
  }

  function update(dt: number, _wind: unknown = null, requestedStep = STEP) {
    if (active && hinge.lead === mesh)
      hinge.update(mesh.visible, dt, requestedStep)
  }

  function dispose() {
    if (!active) return
    active = false
    mesh.geometry = original
    bindSkeleton(mesh, originalSkeleton)
    baseSkeletons.delete(mesh)
    mesh.boundingSphere = originalBounds
    releaseHinge(originalSkeleton, hinge, mesh)
    if (--shared.users === 0) {
      geometry.dispose()
      geometries.delete(original)
    }
    mesh.removeEventListener('removed', dispose)
    onDispose?.()
  }
  mesh.addEventListener('removed', dispose)
  return { update, reset, dispose }
}

export type RobeRig = ReturnType<typeof createRobeRig>
