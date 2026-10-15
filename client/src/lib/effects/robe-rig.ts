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
}

const COLUMNS = 4
const STEP = 1 / 30
const MAX_ANGLE = 1.65
const baseSkeletons = new WeakMap<THREE.SkinnedMesh, THREE.Skeleton>()
const geometries = new WeakMap<
  THREE.BufferGeometry,
  { geometry: THREE.BufferGeometry; users: number }
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
  for (const i of drivenVertices(positions, config)) {
    const x = positions.getX(i)
    const theta = Math.atan2(Math.abs(x), positions.getZ(i) - config.center_z_m)
    const across = (theta / Math.PI) * (COLUMNS - 1)
    const column = Math.min(Math.floor(across), COLUMNS - 2)
    const blend = across - column
    const amount = THREE.MathUtils.smoothstep(
      config.waist_height_m - positions.getY(i),
      0,
      0.06
    )
    const first = boneCount + (x >= 0 ? 0 : COLUMNS) + column
    joints.setXYZW(i, hips, first, first + 1, 0)
    weights.setXYZW(i, 1 - amount, amount * (1 - blend), amount * blend, 0)
  }
  geometry.computeBoundingSphere()
  shared = { geometry, users: 1 }
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
    return { upper, lower, direction: new THREE.Vector3() }
  })
  if (hips < 0) throw new Error('Missing robe hip bone')
  const hip = base.bones[hips]
  const toHip = base.boneInverses[hips].clone().multiply(bindMatrix)
  const down = new THREE.Vector3(0, -1, 0).transformDirection(toHip)
  const controls = Array.from({ length: COLUMNS * 2 }, (_, i) => {
    const side = Math.floor(i / COLUMNS)
    const angle = ((i % COLUMNS) / (COLUMNS - 1)) * Math.PI
    const outward = new THREE.Vector3(
      (side === 0 ? 1 : -1) * Math.sin(angle),
      0,
      Math.cos(angle)
    )
    const pivot = new THREE.Vector3(
      outward.x * config.waist_radii_m[0],
      config.waist_height_m,
      config.center_z_m + outward.z * config.waist_radii_m[1]
    ).applyMatrix4(toHip)
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
      side,
      angle: 0,
      velocity: 0,
    }
  })
  const skeleton = new THREE.Skeleton(
    [...base.bones, ...controls.map((control) => control.bone)],
    [...base.boneInverses, ...controls.map((control) => control.inverse)]
  )
  const inverseHip = new THREE.Matrix4()
  const point = new THREE.Vector3()
  const anchor = new THREE.Vector3()
  const previousAnchor = new THREE.Vector3()
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
  }

  function minimum(control: (typeof controls)[number]) {
    const leg = legs[control.side].direction
    const forward = Math.max(0, leg.dot(control.outward))
    if (forward < 0.005) return 0
    const margin = 0.12 * THREE.MathUtils.smoothstep(forward, 0, 0.3)
    return THREE.MathUtils.clamp(
      Math.atan2(forward, leg.dot(down)) + margin,
      0,
      MAX_ANGLE
    )
  }

  function draw() {
    for (const control of controls) {
      control.bone.quaternion.setFromAxisAngle(control.axis, control.angle)
      control.bone.updateMatrixWorld(true)
    }
  }

  function reset() {
    refresh()
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
    for (const control of controls) {
      const target = minimum(control)
      control.velocity =
        (control.velocity + (target - control.angle) * 65 * step) *
        Math.exp(-12 * step)
      control.angle = THREE.MathUtils.clamp(
        control.angle + control.velocity * step,
        target,
        MAX_ANGLE
      )
      if (
        (control.angle === target && control.velocity < 0) ||
        control.angle === MAX_ANGLE
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
