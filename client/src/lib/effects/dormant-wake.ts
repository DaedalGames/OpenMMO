import * as THREE from 'three'
import { MeshBasicNodeMaterial, MeshStandardNodeMaterial } from 'three/webgpu'
import {
  color,
  float,
  instanceColor,
  mix,
  mx_noise_float,
  uv,
  vec3,
} from 'three/tsl'
import { createRng } from '../utils/simplex-noise'
import { SLEEP_SINK_MS, sleepSink } from './dormant-sleep'

/** Dust lingers this long after the collapse, hiding the boss's arrival. */
const DORMANT_WAKE_TAIL_MS = 5000
/** The stand-in sinks over this long from the collapse. */
export const DORMANT_SINK_MS = 700
export const GRAVITY = 18
const LOW_DUST = 36
const BIG_DUST = 56
const PEBBLES = 34
const ROCKS = 40
const EMBERS = 36

/** The stand-in's world box: centre on the ground, half extents, height. */
export interface WakeBounds {
  x: number
  y: number
  z: number
  halfX: number
  halfZ: number
  height: number
}

interface Dust {
  at: number
  life: number
  x: number
  y: number
  z: number
  vx: number
  vy: number
  vz: number
  size: number
  grow: number
  peak: number
  seed: number
  shade: number
  roll: number
}

export interface Rock {
  at: number
  x: number
  y: number
  z: number
  vx: number
  vy: number
  vz: number
  size: number
  /** Seconds to first touchdown. */
  land: number
  stretch: THREE.Vector3
  spin: THREE.Vector3
}

interface Ember {
  at: number
  life: number
  x: number
  z: number
  rise: number
  drift: number
  size: number
}

export const ZERO_SCALE = new THREE.Matrix4().makeScale(0, 0, 0)

/** Per-frame particles: every instance hidden, colour (1, 1, 1). */
export function instancedMesh(
  geometry: THREE.BufferGeometry,
  material: THREE.Material,
  count: number
) {
  const mesh = new THREE.InstancedMesh(geometry, material, count)
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
  mesh.instanceColor = new THREE.InstancedBufferAttribute(
    new Float32Array(count * 3).fill(1),
    3
  ).setUsage(THREE.DynamicDrawUsage)
  mesh.frustumCulled = false
  for (let i = 0; i < count; i++) mesh.setMatrixAt(i, ZERO_SCALE)
  return mesh
}

/** Seconds until a chunk launched from `r.y` first touches the ground. */
export function landTime(r: Rock) {
  return (r.vy + Math.sqrt(r.vy * r.vy + 2 * GRAVITY * r.y)) / GRAVITY
}

/** Soft billboard puffs; per-instance colour is (alpha, noise seed, shade). */
export function dustMaterial() {
  const material = new MeshStandardNodeMaterial()
  material.transparent = true
  material.depthWrite = false
  material.roughness = 1
  material.metalness = 0
  // instanceColor multiplies the colour on its own; dividing it back out
  // keeps only the shade.
  const ic = instanceColor
  const r = uv().sub(0.5).length().mul(2)
  const lumps = mx_noise_float(vec3(uv().mul(3.2), ic.y.mul(37)))
    .mul(0.5)
    .add(0.5)
  material.colorNode = color('#8a7a62').mul(ic.z).div(ic.max(0.001))
  material.opacityNode = float(1)
    .sub(r)
    .clamp(0, 1)
    .pow(1.6)
    .mul(mix(0.35, 1.25, lumps))
    .clamp(0, 1)
    .mul(ic.x)
  return material
}

/** A lumpy chunk; per-instance stretch makes the variety. */
export function rubble(): THREE.BufferGeometry {
  const geometry = new THREE.IcosahedronGeometry(0.5, 0)
  const pos = geometry.getAttribute('position')
  const rand = createRng(7)
  const offsets = new Map<string, number>()
  for (let i = 0; i < pos.count; i++) {
    // Non-indexed: shared corners must move together to stay closed.
    const key = `${pos.getX(i).toFixed(3)},${pos.getY(i).toFixed(3)},${pos.getZ(i).toFixed(3)}`
    let k = offsets.get(key)
    if (k === undefined) offsets.set(key, (k = 0.7 + rand() * 0.5))
    pos.setXYZ(i, pos.getX(i) * k, pos.getY(i) * k, pos.getZ(i) * k)
  }
  geometry.computeVertexNormals()
  return geometry
}

/** Where a ballistic chunk is `t` s after launch from height `y` above the
 *  ground, with one damped bounce, then at rest. */
export function ballistic(r: Rock, t: number, out: THREE.Vector3): number {
  const land = r.land
  if (t < land) {
    out.set(
      r.x + r.vx * t,
      r.y + r.vy * t - 0.5 * GRAVITY * t * t,
      r.z + r.vz * t
    )
    return -1
  }
  const lx = r.x + r.vx * land
  const lz = r.z + r.vz * land
  const bounceVy = (GRAVITY * land - r.vy) * 0.3
  const hop = (2 * bounceVy) / GRAVITY
  const tb = Math.min(t - land, hop)
  out.set(
    lx + r.vx * 0.35 * tb,
    Math.max(0, bounceVy * tb - 0.5 * GRAVITY * tb * tb),
    lz + r.vz * 0.35 * tb
  )
  return t - land - hop
}

/** Dust, falling stones and embers as a dormant boss shakes off its rock
 *  shell: a rumble up to `collapseMs`, then the shell bursts. Times are ms
 *  from the offering. `startSleep` plays it the other way: the boss grinds
 *  down into the ground and the shell closes over it. */
export class DormantWakeEffect {
  readonly group = new THREE.Group()
  private planeGeometry = new THREE.PlaneGeometry(1, 1)
  private rockGeometry = rubble()
  private dustMaterial = dustMaterial()
  private rockMaterial = new MeshStandardNodeMaterial()
  private emberMaterial = new MeshBasicNodeMaterial()
  private dustMesh: THREE.InstancedMesh
  private rockMesh: THREE.InstancedMesh
  private emberMesh: THREE.InstancedMesh
  private dust: Dust[] = []
  private rocks: Rock[] = []
  private embers: Ember[] = []
  private collapseMs = 0
  private dummy = new THREE.Object3D()
  private roll = new THREE.Quaternion()
  private forward = new THREE.Vector3(0, 0, 1)
  private point = new THREE.Vector3()
  private tint = new THREE.Color()

  constructor() {
    const r = uv().sub(0.5).length().mul(2)
    this.rockMaterial.color = new THREE.Color('#ffffff')
    this.rockMaterial.roughness = 0.95
    this.rockMaterial.metalness = 0
    this.rockMaterial.flatShading = true
    this.emberMaterial.transparent = true
    this.emberMaterial.depthWrite = false
    this.emberMaterial.blending = THREE.AdditiveBlending
    this.emberMaterial.toneMapped = false
    this.emberMaterial.colorNode = mix(
      color('#ff5a1a'),
      color('#ffd27a'),
      float(1).sub(r).clamp(0, 1)
    )
    this.emberMaterial.opacityNode = float(1).sub(r).clamp(0, 1).pow(2)

    this.dustMesh = instancedMesh(
      this.planeGeometry,
      this.dustMaterial,
      LOW_DUST + BIG_DUST
    )
    this.rockMesh = instancedMesh(
      this.rockGeometry,
      this.rockMaterial,
      PEBBLES + ROCKS
    )
    this.emberMesh = instancedMesh(
      this.planeGeometry,
      this.emberMaterial,
      EMBERS
    )
    this.rockMesh.castShadow = true
    this.group.add(this.dustMesh, this.rockMesh, this.emberMesh)
    this.clear()
  }

  private begin(b: WakeBounds, collapseMs: number) {
    const rand = createRng(Math.floor(b.x * 131 + b.z * 17))
    this.collapseMs = collapseMs
    this.group.position.set(b.x, b.y, b.z)
    this.group.visible = true
    const rim = () => {
      const a = rand() * Math.PI * 2
      const k = 1 + rand() * 0.25
      return [Math.cos(a) * b.halfX * k, Math.sin(a) * b.halfZ * k, a] as const
    }
    const inside = (k: number) => [
      (rand() * 2 - 1) * b.halfX * k,
      (rand() * 2 - 1) * b.halfZ * k,
    ]
    return { rand, rim, inside }
  }

  /** Lay out every particle for one wake around `b`. */
  start(b: WakeBounds, collapseMs: number) {
    const { rand, rim, inside } = this.begin(b, collapseMs)

    this.dust.length = 0
    for (let i = 0; i < LOW_DUST; i++) {
      const [x, z, a] = rim()
      const out = 0.4 + rand() * 0.6
      this.dust.push({
        at: (i / LOW_DUST) * collapseMs * 0.95,
        life: 1400 + rand() * 900,
        x,
        y: 0.2,
        z,
        vx: Math.cos(a) * out,
        vy: 0.35 + rand() * 0.4,
        vz: Math.sin(a) * out,
        size: 1.6 + rand() * 1.2,
        grow: 2.2 + rand() * 1.6,
        peak: 0.7 + rand() * 0.2,
        seed: rand(),
        shade: 0.75 + rand() * 0.2,
        roll: rand() * Math.PI * 2,
      })
    }
    for (let i = 0; i < BIG_DUST; i++) {
      const [x, z] = inside(0.9)
      const a = Math.atan2(z / b.halfZ, x / b.halfX) + (rand() - 0.5) * 0.6
      const out = 2.5 + rand() * 4
      this.dust.push({
        at: collapseMs + rand() * 350,
        life: 3400 + rand() * 1600,
        x,
        y: rand() * b.height * 0.85,
        z,
        vx: Math.cos(a) * out,
        vy: 0.4 + rand() * 1.6,
        vz: Math.sin(a) * out,
        size: 4 + rand() * 3,
        grow: 5 + rand() * 4,
        peak: 0.8 + rand() * 0.2,
        seed: rand(),
        shade: 0.85 + rand() * 0.25,
        roll: rand() * Math.PI * 2,
      })
    }

    this.rocks.length = 0
    for (let i = 0; i < PEBBLES; i++) {
      // On the flank of a roughly conical shell, so they show as they fall.
      const h = 0.3 + rand() * 0.6
      const a = rand() * Math.PI * 2
      const ox = Math.cos(a) * (1.05 - h)
      const oz = Math.sin(a) * (1.05 - h)
      this.rocks.push({
        at: 250 + rand() * (collapseMs - 250),
        x: ox * b.halfX,
        y: b.height * h,
        z: oz * b.halfZ,
        vx: ox * 2.5,
        vy: rand() * 1.5,
        vz: oz * 2.5,
        size: 0.25 + rand() * 0.3,
        land: 0,
        stretch: new THREE.Vector3(1 + rand() * 0.6, 0.6 + rand() * 0.4, 1),
        spin: new THREE.Vector3(rand(), rand(), rand()).multiplyScalar(8),
      })
    }
    for (let i = 0; i < ROCKS; i++) {
      const [x, z] = inside(0.8)
      const a = Math.atan2(z / b.halfZ, x / b.halfX) + (rand() - 0.5) * 0.5
      const out = 3 + rand() * 5
      this.rocks.push({
        at: collapseMs + rand() * 180,
        x,
        y: b.height * (0.3 + rand() * 0.6),
        z,
        vx: Math.cos(a) * out,
        vy: 2 + rand() * 5,
        vz: Math.sin(a) * out,
        size: 0.5 + rand() * 0.9,
        land: 0,
        stretch: new THREE.Vector3(1 + rand() * 0.6, 0.6 + rand() * 0.4, 1),
        spin: new THREE.Vector3(rand(), rand(), rand()).multiplyScalar(6),
      })
    }
    this.finishRocks(rand)

    this.embers.length = 0
    for (let i = 0; i < EMBERS; i++) {
      const [x, z] = inside(0.9)
      this.embers.push({
        at: collapseMs * 0.4 + rand() * (collapseMs * 0.6 + 1500),
        life: 900 + rand() * 900,
        x,
        z,
        rise: 1.5 + rand() * 2.5,
        drift: (rand() - 0.5) * 1.2,
        size: 0.12 + rand() * 0.18,
      })
    }
  }

  /** Lay out a boss sinking back under its shell at `b`: grinding dust and
   *  scree while it sinks, a choking cloud as it goes under, its fire dying. */
  startSleep(b: WakeBounds) {
    const sinkMs = SLEEP_SINK_MS
    const { rand, rim, inside } = this.begin(b, sinkMs)

    this.dust.length = 0
    for (let i = 0; i < LOW_DUST; i++) {
      const [x, z, a] = rim()
      const out = 0.5 + rand() * 0.8
      this.dust.push({
        at: (i / LOW_DUST) * sinkMs * 0.9,
        life: 1600 + rand() * 1000,
        x,
        y: 0.2,
        z,
        vx: Math.cos(a) * out,
        vy: 0.5 + rand() * 0.6,
        vz: Math.sin(a) * out,
        size: 1.8 + rand() * 1.4,
        grow: 2.6 + rand() * 1.8,
        peak: 0.75 + rand() * 0.2,
        seed: rand(),
        shade: 0.75 + rand() * 0.2,
        roll: rand() * Math.PI * 2,
      })
    }
    for (let i = 0; i < BIG_DUST; i++) {
      // Rolling in from the rim and billowing up as the ground closes.
      const [x, z, a] = rim()
      const out = 0.8 + rand() * 1.6
      this.dust.push({
        at: sinkMs * 0.45 + rand() * sinkMs * 0.6,
        life: 3000 + rand() * 1800,
        x: x * 0.8,
        y: rand() * b.height * 0.4,
        z: z * 0.8,
        vx: Math.cos(a) * out,
        vy: 0.8 + rand() * 1.4,
        vz: Math.sin(a) * out,
        size: 4 + rand() * 3,
        grow: 4 + rand() * 4,
        peak: 0.8 + rand() * 0.2,
        seed: rand(),
        shade: 0.85 + rand() * 0.25,
        roll: rand() * Math.PI * 2,
      })
    }

    this.rocks.length = 0
    for (let i = 0; i < PEBBLES + ROCKS; i++) {
      // Scree shed off the flanks of the sinking body.
      const h = 0.15 + rand() * 0.75
      const a = rand() * Math.PI * 2
      const ox = Math.cos(a) * (1.05 - h * 0.6)
      const oz = Math.sin(a) * (1.05 - h * 0.6)
      const big = i >= PEBBLES
      const at = rand() * sinkMs * 0.85
      this.rocks.push({
        at,
        x: ox * b.halfX,
        y: b.height * h * (1 - sleepSink(at)),
        z: oz * b.halfZ,
        vx: ox * (1 + rand() * 1.5),
        vy: rand() * 1.2,
        vz: oz * (1 + rand() * 1.5),
        size: big ? 0.45 + rand() * 0.6 : 0.2 + rand() * 0.3,
        land: 0,
        stretch: new THREE.Vector3(1 + rand() * 0.6, 0.6 + rand() * 0.4, 1),
        spin: new THREE.Vector3(rand(), rand(), rand()).multiplyScalar(6),
      })
    }
    this.finishRocks(rand)

    this.embers.length = 0
    for (let i = 0; i < EMBERS; i++) {
      const [x, z] = inside(0.7)
      this.embers.push({
        at: rand() * sinkMs * 0.9,
        life: 700 + rand() * 700,
        x,
        z,
        rise: 1 + rand() * 1.5,
        drift: (rand() - 0.5) * 0.8,
        size: 0.1 + rand() * 0.14,
      })
    }
  }

  private finishRocks(rand: () => number) {
    for (const r of this.rocks) r.land = landTime(r)
    for (let i = 0; i < this.rocks.length; i++) {
      // Granite with some of the shell's moss.
      const v = 0.75 + rand() * 0.35
      const moss = rand() < 0.3
      this.tint.setRGB(
        (moss ? 0.34 : 0.46) * v,
        (moss ? 0.37 : 0.41) * v,
        (moss ? 0.2 : 0.35) * v,
        THREE.SRGBColorSpace
      )
      this.rockMesh.setColorAt(i, this.tint)
    }
    this.rockMesh.instanceColor!.needsUpdate = true
  }

  /** False once the dust has settled. */
  update(elapsedMs: number, camera: THREE.Camera): boolean {
    if (elapsedMs >= this.collapseMs + DORMANT_WAKE_TAIL_MS) {
      this.clear()
      return false
    }
    this.updateDust(elapsedMs, camera)
    this.updateRocks(elapsedMs)
    this.updateEmbers(elapsedMs, camera)
    return true
  }

  private updateDust(elapsedMs: number, camera: THREE.Camera) {
    for (let i = 0; i < this.dust.length; i++) {
      const d = this.dust[i]
      const age = (elapsedMs - d.at) / d.life
      if (age < 0 || age >= 1) {
        this.hide(this.dustMesh, i)
        continue
      }
      const t = (elapsedMs - d.at) / 1000
      // Drag: the burst slows as it spreads.
      const travel = (1 - Math.exp(-1.6 * t)) / 1.6
      this.dummy.position.set(
        d.x + d.vx * travel,
        d.y + d.vy * t + d.size * 0.35,
        d.z + d.vz * travel
      )
      this.dummy.quaternion
        .copy(camera.quaternion)
        .multiply(this.roll.setFromAxisAngle(this.forward, d.roll + t * 0.3))
      this.dummy.scale.setScalar(d.size + d.grow * Math.sqrt(age))
      this.dummy.updateMatrix()
      this.dustMesh.setMatrixAt(i, this.dummy.matrix)
      const alpha =
        d.peak *
        Math.min(1, age / 0.12) *
        (1 - THREE.MathUtils.smoothstep(age, 0, 1))
      this.tint.setRGB(alpha, d.seed, d.shade)
      this.dustMesh.setColorAt(i, this.tint)
    }
    this.dustMesh.instanceMatrix.needsUpdate = true
    this.dustMesh.instanceColor!.needsUpdate = true
  }

  private updateRocks(elapsedMs: number) {
    for (let i = 0; i < this.rocks.length; i++) {
      const r = this.rocks[i]
      const t = (elapsedMs - r.at) / 1000
      if (t < 0) {
        this.hide(this.rockMesh, i)
        continue
      }
      const rest = ballistic(r, t, this.point)
      // Settled chunks sink out of sight rather than pop.
      const sink = rest < 0.9 ? 0 : Math.min(1, (rest - 0.9) / 0.8)
      if (sink >= 1) {
        this.hide(this.rockMesh, i)
        continue
      }
      const turning = rest < 0 ? t : t - rest
      this.dummy.position.copy(this.point)
      this.dummy.position.y += r.size * 0.4 - sink * r.size
      this.dummy.rotation.set(
        r.spin.x * turning,
        r.spin.y * turning,
        r.spin.z * turning
      )
      this.dummy.scale.copy(r.stretch).multiplyScalar(r.size)
      this.dummy.updateMatrix()
      this.rockMesh.setMatrixAt(i, this.dummy.matrix)
    }
    this.rockMesh.instanceMatrix.needsUpdate = true
  }

  private updateEmbers(elapsedMs: number, camera: THREE.Camera) {
    for (let i = 0; i < this.embers.length; i++) {
      const e = this.embers[i]
      const age = (elapsedMs - e.at) / e.life
      if (age < 0 || age >= 1) {
        this.hide(this.emberMesh, i)
        continue
      }
      const t = (elapsedMs - e.at) / 1000
      this.dummy.position.set(
        e.x + e.drift * t,
        0.2 + e.rise * t,
        e.z + Math.sin(t * 5 + i) * 0.2
      )
      this.dummy.quaternion.copy(camera.quaternion)
      this.dummy.scale.setScalar(e.size)
      this.dummy.updateMatrix()
      this.emberMesh.setMatrixAt(i, this.dummy.matrix)
      // Additive: a dimmer colour is the fade.
      const glow = Math.sin(Math.PI * age) * 1.6
      this.tint.setRGB(glow, glow, glow)
      this.emberMesh.setColorAt(i, this.tint)
    }
    this.emberMesh.instanceMatrix.needsUpdate = true
    this.emberMesh.instanceColor!.needsUpdate = true
  }

  private hide(mesh: THREE.InstancedMesh, i: number) {
    mesh.setMatrixAt(i, ZERO_SCALE)
  }

  clear() {
    this.group.visible = false
  }

  dispose() {
    this.planeGeometry.dispose()
    this.rockGeometry.dispose()
    this.dustMaterial.dispose()
    this.rockMaterial.dispose()
    this.emberMaterial.dispose()
    for (const m of [this.dustMesh, this.rockMesh, this.emberMesh]) m.dispose()
    this.group.clear()
  }
}
