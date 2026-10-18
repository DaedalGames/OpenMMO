import * as THREE from 'three'
import { MeshBasicNodeMaterial } from 'three/webgpu'
import {
  color,
  mix,
  mx_noise_float,
  smoothstep,
  uniform,
  uv,
  vec3,
} from 'three/tsl'
import { BARKAN_RUNE_SLASH } from '../utils/barkanRuneSlash'
import { FireParticles, type FireTuning } from './fire-particles'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type N = any

const ANGULAR_SEGMENTS = 48
const RADIAL_SEGMENTS = 12
const GROUND_LIFT = 0.04
const smooth = THREE.MathUtils.smoothstep

// u runs across the fan from the model's right (-X) to its left (+X), the way
// the blade sweeps; v runs out from the monster.
function fanGeometry(range: number, halfAngle: number) {
  const positions: number[] = []
  const uvs: number[] = []
  const indices: number[] = []
  for (let a = 0; a <= ANGULAR_SEGMENTS; a++) {
    const u = a / ANGULAR_SEGMENTS
    const bearing = -halfAngle + u * 2 * halfAngle
    for (let r = 0; r <= RADIAL_SEGMENTS; r++) {
      const v = r / RADIAL_SEGMENTS
      const radius = 0.35 + v * (range - 0.35)
      positions.push(
        Math.sin(bearing) * radius,
        GROUND_LIFT,
        Math.cos(bearing) * radius
      )
      uvs.push(u, v)
      if (a < ANGULAR_SEGMENTS && r < RADIAL_SEGMENTS) {
        const i = a * (RADIAL_SEGMENTS + 1) + r
        const j = i + RADIAL_SEGMENTS + 1
        indices.push(i, j, i + 1, i + 1, j, j + 1)
      }
    }
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(positions, 3)
  )
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  geometry.setIndex(indices)
  return geometry
}

/** Fire that follows the rune slash's blade across the fan it strikes. Lives in
 *  world space. */
export class BarkanFireFan {
  readonly group = new THREE.Group()
  private readonly geometry: THREE.BufferGeometry
  private readonly material = new MeshBasicNodeMaterial()
  private readonly mesh: THREE.Mesh
  private readonly sweep = uniform(0)
  private readonly burn = uniform(0)
  private readonly clock = uniform(0)
  private readonly particles: FireParticles
  private readonly tuning: FireTuning
  private readonly local = new THREE.Vector3()
  private sweepProgress = 0

  constructor(
    private readonly range: number,
    private readonly halfAngle: number
  ) {
    this.geometry = fanGeometry(range, halfAngle)
    const material = this.material
    material.transparent = true
    material.depthWrite = false
    material.blending = THREE.AdditiveBlending
    material.side = THREE.DoubleSide
    material.toneMapped = false
    const u: N = uv().x
    const v: N = uv().y
    const t: N = this.clock
    const noise: N = mx_noise_float(
      vec3(u.mul(9), v.mul(5).sub(t.mul(2.4)), t.mul(0.7))
    )
      .mul(0.5)
      .add(0.5)
    // No drawn outline: the fire thins out in noisy patches toward every edge.
    const patches: N = mx_noise_float(vec3(u.mul(4), v.mul(3), t.mul(0.4)))
      .mul(0.5)
      .add(0.5)
    const edges: N = smoothstep(0.0, 0.3, u)
      .mul(smoothstep(1.0, 0.7, u))
      .mul(smoothstep(0.0, 0.2, v))
      .mul(smoothstep(1.0, 0.5, v))
    const body: N = smoothstep(0.35, 0.75, edges.mul(patches.add(0.55)))
    const swept: N = smoothstep(u.sub(0.15), u, this.sweep)
    const heat: N = noise.mul(swept).mul(body)
    const burnAlpha: N = swept
      .mul(noise.pow(2).mul(0.8).add(0.08))
      .mul(body)
      .mul(this.burn)
    material.colorNode = mix(
      color('#8a1004'),
      mix(color('#ff4a0e'), color('#ffb347'), heat.pow(3)),
      heat.mul(this.burn)
    )
    material.opacityNode = burnAlpha.min(1)
    this.mesh = new THREE.Mesh(this.geometry, material)
    this.mesh.frustumCulled = false
    this.mesh.renderOrder = 2
    this.mesh.visible = false
    this.group.add(this.mesh)

    this.tuning = {
      maxParticles: 220,
      spawnRate: 0,
      particleSize: 0.7,
      buoyancy: 1.2,
      turbulence: { amp: 0.6, fx: 7, fz: 6 },
      spawn: (p) => this.spawnFlame(p),
    }
    this.particles = new FireParticles(this.tuning)
  }

  /** Particles live in world space beside the fan. */
  get particleGroup() {
    return this.particles.group
  }

  private spawnFlame(p: Parameters<FireTuning['spawn']>[0]) {
    const u = Math.random() * this.sweepProgress
    const bearing =
      -this.halfAngle + u * 2 * this.halfAngle + (Math.random() - 0.5) * 0.25
    const radius = 0.6 + Math.sqrt(Math.random()) * (this.range - 1.1)
    this.local.set(Math.sin(bearing) * radius, 0.05, Math.cos(bearing) * radius)
    this.group.localToWorld(this.local)
    p.x = this.local.x
    p.y = this.local.y
    p.z = this.local.z
    p.vx = (Math.random() - 0.5) * 0.3
    p.vy = 0.4 + Math.random() * 0.6
    p.vz = (Math.random() - 0.5) * 0.3
    p.maxAge = 0.35 + Math.random() * 0.45
    p.baseScale = 0.7 + Math.random() * 0.8
  }

  /** `time` is the RuneSlash clip time; `active` is false when no cast runs. */
  update(
    time: number,
    active: boolean,
    deltaTime: number,
    camera: THREE.Camera | undefined
  ) {
    const timing = BARKAN_RUNE_SLASH
    // The blade turns about evenly over the sweep; the fire follows it into
    // and across the fan.
    const [from, to] = timing.sweepBearings
    const bearing = THREE.MathUtils.degToRad(
      THREE.MathUtils.mapLinear(
        time,
        timing.sweepStart,
        timing.sweepEnd,
        from,
        to
      )
    )
    this.sweepProgress = active
      ? THREE.MathUtils.clamp(
          (bearing + this.halfAngle) / (2 * this.halfAngle),
          0,
          1
        )
      : 0
    const burn = active
      ? smooth(time, timing.sweepStart - 0.02, timing.sweepStart + 0.05) *
        (1 - smooth(time, timing.sweepEnd + 0.5, timing.recoveryEnd))
      : 0
    this.sweep.value = this.sweepProgress
    this.burn.value = burn
    this.clock.value += deltaTime
    this.mesh.visible = burn > 0.001
    this.group.updateMatrixWorld()
    this.tuning.spawnRate =
      burn > 0.05 ? 260 * burn * (time < timing.sweepEnd + 0.3 ? 1 : 0.45) : 0
    this.particles.update(deltaTime, camera)
  }

  dispose() {
    this.group.removeFromParent()
    this.geometry.dispose()
    this.material.dispose()
    this.particles.dispose()
  }
}
