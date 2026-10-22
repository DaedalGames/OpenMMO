import * as THREE from 'three'
import { MeshBasicNodeMaterial, MeshStandardNodeMaterial } from 'three/webgpu'
import {
  abs,
  atan,
  color,
  float,
  max,
  min,
  mix,
  mx_fractal_noise_float,
  mx_noise_float,
  mx_worley_noise_vec2,
  normalGeometry,
  positionGeometry,
  sin,
  smoothstep,
  uniform,
  uv,
  vec3,
} from 'three/tsl'
import { createRng } from '../utils/simplex-noise'
import {
  ZERO_SCALE,
  dustMaterial,
  instancedMesh,
  landTime,
  placeDust,
  placeRocks,
  rubble,
  type Dust,
  type Rock,
} from './dormant-wake'
import {
  basalt,
  drop,
  placeSparks,
  shardGeometry,
  sparkMaterial,
  type Spark,
} from './ground-eruption'
import type { BodyFootprint } from './earth-roar'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type N = any

/** `FORMATION_BREAK.strike_ms` and `cast_ms` on the server. */
export const FORMATION_BREAK_STRIKE_MS = 2800
export const FORMATION_BREAK_CAST_MS = 4400
/** `Pools::ticks * tick_ms`: how long the magma burns after the strike. */
export const FORMATION_BREAK_POOL_MS = 10_000
/** The shock front crosses the fan in this long. */
const WAVE_MS = 450
const COOL_MS = 2600
const END_MS = FORMATION_BREAK_STRIKE_MS + 4200
const GROUND_LIFT = 0.04
const FAULTS = 4
const SHARDS_PER_FAULT = 5
const SLABS = 44
const DEBRIS = 72
const SEEP = 18
const ROLL = 48
const PLUMES = 14
const SPARKS = 40
const SHARDS = FAULTS * SHARDS_PER_FAULT

const smooth = THREE.MathUtils.smoothstep

/** A fault's sideways wander at `r` m, in radians; the decal follows the
 *  same curve so the shards stand in its cracks. */
function wander(r: number, k: number, seed: number) {
  return (
    0.07 * Math.sin(r * 0.8 + k * 2.1 + seed) +
    0.03 * Math.sin(r * 2.3 + k * 5.7 + seed * 1.7)
  )
}

function wanderNode(r: N, k: number, seed: N) {
  return sin(
    r
      .mul(0.8)
      .add(k * 2.1)
      .add(seed)
  )
    .mul(0.07)
    .add(
      sin(
        r
          .mul(2.3)
          .add(k * 5.7)
          .add(seed.mul(1.7))
      ).mul(0.03)
    )
}

/** A plate of broken ground: a squashed box with chipped corners. */
function slabGeometry() {
  const geometry = new THREE.BoxGeometry(1, 1, 1, 2, 2, 2)
  const pos = geometry.getAttribute('position')
  const rand = createRng(31)
  const moved = new Map<string, [number, number, number]>()
  for (let i = 0; i < pos.count; i++) {
    const [x, y, z] = [pos.getX(i), pos.getY(i), pos.getZ(i)]
    const key = `${x.toFixed(3)},${y.toFixed(3)},${z.toFixed(3)}`
    let p = moved.get(key)
    if (!p) {
      const edge = Math.abs(x) > 0.4 || Math.abs(z) > 0.4
      const chip = edge ? 0.7 + rand() * 0.35 : 0.9 + rand() * 0.2
      // The underside crumbles away narrower than the turf.
      const under = y < 0 ? 0.6 + rand() * 0.25 : y > 0 ? 1 : 0.85
      p = [
        x * chip * under + (rand() - 0.5) * 0.12,
        y + (rand() - 0.5) * (y < 0 ? 0.6 : 0.3),
        z * chip * under + (rand() - 0.5) * 0.12,
      ]
      moved.set(key, p)
    }
    pos.setXYZ(i, p[0], p[1], p[2])
  }
  const flat = geometry.toNonIndexed()
  geometry.dispose()
  flat.computeVertexNormals()
  return flat
}

/** Turf on top, packed earth and stones on the broken sides. */
function slabMaterial() {
  const material = new MeshStandardNodeMaterial()
  material.flatShading = true
  material.metalness = 0
  const p = positionGeometry
  const grain = mx_fractal_noise_float(p.mul(vec3(4, 6, 4)), 3, 2, 0.5)
  const top = smoothstep(0.55, 0.85, normalGeometry.y)
  const turf = mix(color('#2c3a1b'), color('#4a4526'), grain.mul(0.7).add(0.5))
  const earth = mix(color('#2a1d13'), color('#4a3726'), grain.mul(0.6).add(0.5))
  const stones = smoothstep(0.45, 0.6, mx_noise_float(p.mul(9)))
  material.colorNode = mix(
    mix(earth, color('#6d665c'), stones.mul(0.6)),
    turf,
    top
  )
  material.roughnessNode = float(1)
  return material
}

interface Slab {
  x: number
  z: number
  /** Facing of its outward edge. */
  bearing: number
  width: number
  depth: number
  thick: number
  at: number
  lift: number
  tilt: number
  rest: number
  restTilt: number
  roll: number
}

interface Shard {
  x: number
  z: number
  height: number
  width: number
  lean: number
  bearing: number
  turn: number
  at: number
}

/** Terraclash smashing the fan in front of it: faults creep out from its
 *  fists while it winds up, then a shock front heaves the ground into plates,
 *  drives basalt up the faults and rolls a wall of dust ahead of it. */
export class FormationBreakEffect {
  readonly group = new THREE.Group()
  private charge = uniform(0)
  private heat = uniform(0)
  private front = uniform(0)
  private fade = uniform(0)
  private seed = uniform(0)
  private faultAngles = uniform(new THREE.Vector4())
  private fanGeometry: THREE.CircleGeometry
  private fanMaterial = new MeshBasicNodeMaterial()
  private fan: THREE.Mesh
  private shardGeometry = shardGeometry()
  private shardMaterial = basalt(this.heat)
  private slabGeometry = slabGeometry()
  private slabMaterial = slabMaterial()
  private planeGeometry = new THREE.PlaneGeometry(1, 1)
  private rockGeometry = rubble()
  private rockMaterial = basalt()
  private dustMaterial = dustMaterial()
  private sparkMaterial = sparkMaterial()
  private shardMesh: THREE.InstancedMesh
  private slabMesh: THREE.InstancedMesh
  private rockMesh: THREE.InstancedMesh
  private dustMesh: THREE.InstancedMesh
  private sparkMesh: THREE.InstancedMesh
  private shards: Shard[] = []
  private slabs: Slab[] = []
  private debris: Rock[] = []
  private dust: Dust[] = []
  private sparks: Spark[] = []
  private elapsedMs = END_MS
  private dummy = new THREE.Object3D()
  private tint = new THREE.Color()
  private axis = new THREE.Vector3()
  private quat = new THREE.Quaternion()
  private euler = new THREE.Euler()

  /** The fan starts here, just past the body's front. */
  private near: number

  constructor(
    private range: number,
    private halfAngle: number,
    body: BodyFootprint
  ) {
    this.near = body.front
    // Circle angles run from +X toward -Z once laid flat; the fan faces +Z.
    this.fanGeometry = new THREE.CircleGeometry(
      range,
      64,
      -Math.PI / 2 - halfAngle,
      halfAngle * 2
    )
    this.buildDecal()
    this.fan = new THREE.Mesh(this.fanGeometry, this.fanMaterial)
    this.fan.rotation.x = -Math.PI / 2
    this.fan.position.y = GROUND_LIFT
    this.fan.renderOrder = 2

    this.shardMesh = instancedMesh(
      this.shardGeometry,
      this.shardMaterial,
      SHARDS
    )
    this.slabMesh = instancedMesh(this.slabGeometry, this.slabMaterial, SLABS)
    this.rockMesh = instancedMesh(this.rockGeometry, this.rockMaterial, DEBRIS)
    this.dustMesh = instancedMesh(
      this.planeGeometry,
      this.dustMaterial,
      SEEP + ROLL + PLUMES
    )
    this.sparkMesh = instancedMesh(
      this.planeGeometry,
      this.sparkMaterial,
      SPARKS
    )
    for (const mesh of [this.shardMesh, this.slabMesh, this.rockMesh]) {
      mesh.castShadow = true
      mesh.receiveShadow = true
    }
    this.group.add(
      this.fan,
      this.slabMesh,
      this.shardMesh,
      this.rockMesh,
      this.dustMesh,
      this.sparkMesh
    )
    this.group.visible = false
  }

  /** Faults running out from the fists, with cracks branching off them and a
   *  fracture along the fan's edge so it reads on low settings too. */
  private buildDecal() {
    const R = this.range
    const half = this.halfAngle
    const p = uv().sub(0.5).mul(2)
    const r = p.length().mul(R)
    const a = atan(p.x, p.y.negate())
    const q = p.mul(R)
    const angles = [
      this.faultAngles.x,
      this.faultAngles.y,
      this.faultAngles.z,
      this.faultAngles.w,
    ]
    // Faults kink and wander off the shared curve by up to ~0.4m.
    const kink = mx_fractal_noise_float(
      vec3(q.mul(0.9), this.seed),
      3,
      2.3,
      0.55
    )
      .mul(0.32)
      .add(mx_noise_float(vec3(q.mul(4.5), 3.1)).mul(0.05))
    let fault: N = float(99)
    for (let k = 0; k < FAULTS; k++) {
      const off = a.sub(angles[k]).sub(wanderNode(r, k, this.seed))
      fault = min(fault, abs(off.mul(r).sub(kink)))
    }
    const cells = mx_worley_noise_vec2(vec3(q.mul(0.75), this.seed), 1)
    const web = cells.y.sub(cells.x).mul(1.3)
    const fine = mx_worley_noise_vec2(vec3(q.mul(2.2), this.seed.add(4)), 1)
    const hair = fine.y.sub(fine.x).mul(0.45)
    const nearFault = drop(0.4, 2.5, fault)
    const ragged = mx_fractal_noise_float(vec3(q.mul(0.6), 6.1), 2, 2, 0.5)
    const edgeDist = abs(
      min(abs(a).sub(half).mul(r).negate(), r.sub(R * 0.97).negate())
    ).add(ragged.mul(0.25))

    const reach = mix(this.near, R, this.charge.pow(0.7))
    const grown = drop(
      reach.sub(0.5),
      reach.add(0.2),
      r.add(mx_noise_float(vec3(q.mul(0.5), 1.7)).mul(0.8))
    ).mul(smoothstep(this.near - 0.8, this.near, r))
    const opened = drop(
      this.front.sub(0.8),
      this.front.add(0.4),
      r.add(ragged.mul(0.6))
    )
    // A fault's width wanders; the strike rips it open, widest by the fists.
    const vary = mx_noise_float(vec3(q.mul(0.45), 8.8))
      .mul(0.5)
      .add(0.75)
    const faultWidth = mix(0.025, 0.06, this.charge)
      .add(opened.mul(drop(this.near, R, r).mul(0.14).add(0.06)))
      .mul(vary)
    const faultCrack = drop(faultWidth.mul(0.5), faultWidth, fault).mul(grown)
    const faultCore = drop(0, faultWidth.mul(0.35), fault).mul(grown)
    // Branches spread from the faults while it winds up, everywhere once it
    // lands.
    const churn = mx_fractal_noise_float(vec3(q.mul(0.35), 9.4), 3, 2, 0.5)
    const branchReach = max(
      nearFault.mul(max(this.charge, opened)),
      opened.mul(smoothstep(0.05, 0.45, churn))
    )
    const branchCrack = drop(
      0.012,
      0.04,
      web.add(float(1).sub(branchReach).mul(0.4))
    ).mul(grown)
    const hairCrack = drop(0.01, 0.03, hair)
      .mul(opened)
      .mul(smoothstep(0.15, 0.5, churn).mul(0.4))
    // The edge is a broken fracture, not a line.
    const edgeCrack = drop(0.03, 0.09, edgeDist)
      .mul(grown)
      .mul(smoothstep(-0.2, 0.25, ragged).mul(0.6).add(0.4))
    const crack = max(max(faultCrack, branchCrack), max(edgeCrack, hairCrack))

    const flicker = mx_noise_float(vec3(q.mul(0.5), this.charge.mul(16)))
      .mul(0.35)
      .add(0.8)
    // Embers deep in the faults while it winds up; the strike lays them bare.
    const ember = mix(
      this.charge.pow(3).mul(0.5),
      this.heat.mul(1.5),
      opened
    ).mul(flicker)
    const glow = max(faultCore, edgeCrack.mul(0.25)).mul(ember)
    const hot = mix(
      mix(color('#5a0e02'), color('#d2410c'), glow.min(1)),
      color('#ffc27a'),
      smoothstep(0.9, 1.6, glow)
    )
    // Torn, churned earth over the struck ground, patchy rather than a sheet
    // and thinning out raggedly before the fan's edge.
    const inside = smoothstep(0.5, 2, edgeDist.add(ragged.mul(1.2)))
    const struck = opened
      .mul(smoothstep(-0.35, 0.3, churn).mul(0.5).add(0.15))
      .mul(inside)
    const soil = max(nearFault.mul(this.charge).mul(0.25).mul(grown), struck)
    const dirt = mix(
      color('#2e2218'),
      color('#4a3a2a'),
      churn.mul(0.5).add(0.5)
    )

    const m = this.fanMaterial
    m.transparent = true
    m.depthWrite = false
    m.toneMapped = false
    m.polygonOffset = true
    m.polygonOffsetFactor = -2
    m.colorNode = mix(
      mix(dirt, color('#080504'), crack),
      hot.mul(glow.mul(1.2).add(0.5)),
      glow.min(1)
    )
    m.opacityNode = max(crack.mul(0.92), soil)
      .max(glow.min(1))
      .mul(this.fade)
      .mul(drop(R * 0.99, R, r))
  }

  /** Lay out one smash from `origin` facing `rotation`. */
  start(origin: THREE.Vector3, rotation: number) {
    const seed = Math.floor(origin.x * 37 + origin.z * 71 + rotation * 997)
    const rand = createRng(seed)
    this.group.position.copy(origin)
    this.group.rotation.y = rotation
    this.group.visible = true
    this.elapsedMs = 0
    this.seed.value = (seed % 1000) / 100
    const R = this.range
    const half = this.halfAngle
    const strike = FORMATION_BREAK_STRIKE_MS
    // When the front reaches `d` m, decelerating as it spreads.
    const reached = (d: number) =>
      strike +
      WAVE_MS * Math.pow(Math.max(0, d - this.near) / (R - this.near), 1.3)

    const angles: number[] = []
    for (let k = 0; k < FAULTS; k++) {
      const slot = (k + 0.5) / FAULTS
      angles.push((slot * 2 - 1) * half * 0.85 + (rand() - 0.5) * 0.18)
    }
    this.faultAngles.value.set(angles[0], angles[1], angles[2], angles[3])
    const faultAt = (k: number, d: number) =>
      angles[k] + wander(d, k, this.seed.value)

    this.shards.length = 0
    for (let k = 0; k < FAULTS; k++) {
      for (let i = 0; i < SHARDS_PER_FAULT; i++) {
        const d =
          this.near +
          1 +
          ((i + rand() * 0.6) / SHARDS_PER_FAULT) * (R - this.near - 1.8)
        const b = faultAt(k, d)
        const near = 1 - (d - this.near) / (R - this.near)
        this.shards.push({
          x: Math.sin(b) * d,
          z: Math.cos(b) * d,
          height: (0.9 + rand() * 1.1) * (0.6 + near * 0.8),
          width: 0.28 + rand() * 0.22,
          lean: 0.25 + rand() * 0.35,
          bearing: b + (rand() - 0.5) * 0.6,
          turn: rand() * Math.PI * 2,
          at: reached(d) + rand() * 40,
        })
      }
    }

    this.slabs.length = 0
    for (let i = 0; i < SLABS; i++) {
      const d = this.near + 0.8 + Math.sqrt(rand()) * (R - this.near - 1.5)
      const b = (rand() * 2 - 1) * half * 0.95
      const near = 1 - (d - this.near) / (R - this.near)
      // Most pitch away from the fists; some fall back toward them.
      const back = rand() < 0.25
      this.slabs.push({
        x: Math.sin(b) * d,
        z: Math.cos(b) * d,
        bearing: b + (rand() - 0.5) * 1.6 + (back ? Math.PI : 0),
        width: 0.6 + rand() * 0.8,
        depth: 0.55 + rand() * 0.6,
        thick: 0.45 + rand() * 0.35,
        at: reached(d) + rand() * 60,
        lift: (0.35 + rand() * 0.5) * (0.5 + near * 0.7),
        tilt: (0.35 + rand() * 0.45) * (0.6 + near * 0.5),
        rest: rand() * 0.15,
        restTilt: 0.08 + rand() * 0.45,
        roll: (rand() - 0.5) * 1.2,
      })
    }
    for (let i = 0; i < SLABS; i++) {
      const v = 0.8 + rand() * 0.35
      this.tint.setRGB(v, v, v)
      this.slabMesh.setColorAt(i, this.tint)
    }
    this.slabMesh.instanceColor!.needsUpdate = true

    this.debris.length = 0
    for (let i = 0; i < DEBRIS; i++) {
      const onFault = i < DEBRIS * 0.6
      const d = this.near + 0.5 + rand() * (R - this.near - 1)
      const b = onFault
        ? faultAt(i % FAULTS, d)
        : (rand() * 2 - 1) * half * 0.95
      const big = rand() < 0.25
      const out = big ? 1 + rand() * 2 : 2 + rand() * 4
      const spread = b + (rand() - 0.5) * 0.9
      const rock: Rock = {
        at: reached(d) + rand() * 80,
        x: Math.sin(b) * d,
        y: 0.1,
        z: Math.cos(b) * d,
        vx: Math.sin(spread) * out,
        vy: big ? 3 + rand() * 3 : 5 + rand() * 6,
        vz: Math.cos(spread) * out,
        size: big ? 0.3 + rand() * 0.3 : 0.06 + rand() * 0.14,
        land: 0,
        stretch: new THREE.Vector3(1 + rand() * 0.7, 0.55 + rand() * 0.4, 1),
        spin: new THREE.Vector3(rand(), rand(), rand()).multiplyScalar(10),
      }
      rock.land = landTime(rock)
      this.debris.push(rock)
    }
    for (let i = 0; i < DEBRIS; i++) {
      // Clods of earth among the stone.
      const earth = rand() < 0.45
      const v = 0.7 + rand() * 0.4
      this.tint.setRGB(
        (earth ? 0.8 : 1) * v,
        (earth ? 0.62 : 0.96) * v,
        (earth ? 0.44 : 0.92) * v
      )
      this.rockMesh.setColorAt(i, this.tint)
    }
    this.rockMesh.instanceColor!.needsUpdate = true

    this.dust.length = 0
    for (let i = 0; i < SEEP; i++) {
      const k = i % FAULTS
      const d = this.near + 0.5 + rand() * (R - this.near - 2) * 0.8
      const b = faultAt(k, d)
      this.dust.push({
        at: 600 + (d / R) * 1200 + rand() * 900,
        life: 1100 + rand() * 700,
        x: Math.sin(b) * d,
        y: 0,
        z: Math.cos(b) * d,
        vx: 0,
        vy: 0.35 + rand() * 0.3,
        vz: 0,
        size: 0.35 + rand() * 0.3,
        grow: 0.8,
        peak: 0.3 + rand() * 0.15,
        seed: rand(),
        shade: 0.8,
        roll: rand() * Math.PI * 2,
      })
    }
    for (let i = 0; i < ROLL; i++) {
      const d = this.near + 0.5 + (i / ROLL) * (R - this.near - 1)
      const b = (rand() * 2 - 1) * half
      const out = 1.5 + rand() * 2.5
      this.dust.push({
        at: reached(d) + rand() * 120,
        life: 2000 + rand() * 1200,
        x: Math.sin(b) * d,
        y: 0.1,
        z: Math.cos(b) * d,
        vx: Math.sin(b) * out,
        vy: 0.2 + rand() * 0.5,
        vz: Math.cos(b) * out,
        size: 1.4 + rand() * 1.2,
        grow: 2.5 + rand() * 2,
        peak: 0.75 + rand() * 0.2,
        seed: rand(),
        shade: 0.75 + rand() * 0.25,
        roll: rand() * Math.PI * 2,
      })
    }
    for (let i = 0; i < PLUMES; i++) {
      const k = i % FAULTS
      const d = this.near + 1 + rand() * (R - this.near - 2.5)
      const b = faultAt(k, d)
      this.dust.push({
        at: reached(d) + 80 + rand() * 250,
        life: 2600 + rand() * 1200,
        x: Math.sin(b) * d,
        y: 0.4,
        z: Math.cos(b) * d,
        vx: 0,
        vy: 1.4 + rand() * 1.2,
        vz: 0,
        size: 1.2 + rand() * 0.8,
        grow: 2.8 + rand() * 1.5,
        peak: 0.55 + rand() * 0.2,
        seed: rand(),
        shade: 0.7 + rand() * 0.2,
        roll: rand() * Math.PI * 2,
      })
    }

    this.sparks.length = 0
    for (let i = 0; i < SPARKS; i++) {
      const k = i % FAULTS
      const d = this.near + 0.5 + rand() * (R - this.near - 1.5)
      const b = faultAt(k, d)
      const out = 0.5 + rand() * 2.5
      const side = b + (rand() - 0.5) * 1.2
      this.sparks.push({
        at: reached(d) + rand() * 120,
        x: Math.sin(b) * d,
        y: 0.1,
        z: Math.cos(b) * d,
        vx: Math.sin(side) * out,
        vy: 3 + rand() * 5,
        vz: Math.cos(side) * out,
        life: 400 + rand() * 600,
        size: 0.05 + rand() * 0.06,
      })
    }
  }

  update(deltaTime: number, camera: THREE.Camera | undefined) {
    if (!this.group.visible || !camera) return
    this.elapsedMs += deltaTime * 1000
    if (this.elapsedMs >= END_MS) {
      this.group.visible = false
      return
    }
    const ms = this.elapsedMs
    const since = ms - FORMATION_BREAK_STRIKE_MS
    const R = this.range
    this.charge.value = Math.min(1, ms / FORMATION_BREAK_STRIKE_MS)
    this.front.value =
      since < 0
        ? 0
        : this.near +
          (R - this.near + 1) * Math.pow(Math.min(1, since / WAVE_MS), 0.77)
    this.heat.value = since < 0 ? 0 : 1 - smooth(since, 0, COOL_MS)
    this.fade.value =
      Math.min(1, ms / 300) * (1 - smooth(ms, END_MS - 1200, END_MS))
    this.updateShards(ms)
    this.updateSlabs(ms)
    placeSparks(this.sparkMesh, this.sparks, ms, camera)
    placeRocks(this.rockMesh, this.debris, ms, 0.5)
    placeDust(this.dustMesh, this.dust, ms, camera)
  }

  private updateShards(ms: number) {
    for (let i = 0; i < this.shards.length; i++) {
      const s = this.shards[i]
      const t = ms - s.at
      if (t < 0 || t >= 1900) {
        this.shardMesh.setMatrixAt(i, ZERO_SCALE)
        continue
      }
      // Punch up past full height, settle, then grind back down.
      const up =
        t < 110
          ? Math.sin(((t / 110) * Math.PI) / 2) * 1.12
          : t < 260
            ? 1.12 - 0.12 * ((t - 110) / 150)
            : 1
      const sink = Math.max(0, (t - 1000) / 900)
      this.dummy.position.set(s.x, -s.height * sink * sink * 1.05, s.z)
      // Lean away from the fists.
      this.dummy.rotation.set(
        Math.cos(s.bearing) * s.lean,
        s.turn,
        -Math.sin(s.bearing) * s.lean
      )
      this.dummy.scale.set(s.width, s.height * up, s.width)
      this.dummy.updateMatrix()
      this.shardMesh.setMatrixAt(i, this.dummy.matrix)
    }
    this.shardMesh.instanceMatrix.needsUpdate = true
  }

  private updateSlabs(ms: number) {
    for (let i = 0; i < this.slabs.length; i++) {
      const s = this.slabs[i]
      const t = (ms - s.at) / 1000
      if (t < 0) {
        this.slabMesh.setMatrixAt(i, ZERO_SCALE)
        continue
      }
      // Heave, drop back hard, and settle half out of the ground.
      const heave = t < 0.22 ? Math.sin((t / 0.22) * (Math.PI / 2)) : 1
      const fall = smooth(t, 0.22, 0.55)
      const bounce =
        t > 0.55 && t < 0.8 ? Math.sin(((t - 0.55) / 0.25) * Math.PI) * 0.06 : 0
      const lift = THREE.MathUtils.lerp(s.lift * heave, s.rest, fall) + bounce
      const tilt = THREE.MathUtils.lerp(s.tilt * heave, s.restTilt, fall)
      const sink = smooth(ms, END_MS - 1500, END_MS - 200)
      // Pitch the far edge up about the line across the fan.
      this.axis.set(Math.cos(s.bearing), 0, -Math.sin(s.bearing))
      this.quat.setFromAxisAngle(this.axis, -tilt)
      this.euler.set(0, s.bearing, s.roll * heave)
      this.dummy.quaternion.setFromEuler(this.euler)
      this.dummy.quaternion.premultiply(this.quat)
      this.dummy.position.set(
        s.x,
        lift - s.thick * 0.55 - sink * (s.thick + 0.6),
        s.z
      )
      this.dummy.scale.set(s.width, s.thick, s.depth)
      this.dummy.updateMatrix()
      this.slabMesh.setMatrixAt(i, this.dummy.matrix)
    }
    this.slabMesh.instanceMatrix.needsUpdate = true
  }

  dispose() {
    this.group.removeFromParent()
    for (const g of [
      this.fanGeometry,
      this.shardGeometry,
      this.slabGeometry,
      this.planeGeometry,
      this.rockGeometry,
    ])
      g.dispose()
    for (const m of [
      this.fanMaterial,
      this.shardMaterial,
      this.slabMaterial,
      this.rockMaterial,
      this.dustMaterial,
      this.sparkMaterial,
    ])
      m.dispose()
    for (const m of [
      this.shardMesh,
      this.slabMesh,
      this.rockMesh,
      this.dustMesh,
      this.sparkMesh,
    ])
      m.dispose()
  }
}
