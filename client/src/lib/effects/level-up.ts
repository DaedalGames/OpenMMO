import * as THREE from 'three'
import { MeshBasicNodeMaterial } from 'three/webgpu'
import {
  attribute,
  color,
  exp,
  float,
  mix,
  normalView,
  uniform,
  uv,
} from 'three/tsl'
import type { EnchantLight } from '../utils/enchantLight'

export const LEVEL_UP_DURATION = 3
const LEVEL_UP_RISE = 2.3
export const LEVEL_UP_ORBS = 3
const TRAIL = 30
const TRAIL_STEP = 0.011
const REDUCED_TRAIL = 6
const STREAKS = 14
const HALOS = 3
const LIGHT_INTENSITY = 45
const TURNS = 2.25
const TOP = 3.8
const FADE_FROM = 1.9
const COLUMN_RADIUS = 0.68
const COLUMN_HEIGHT = 3.2

export function spiralPoint(u: number, orb: number, target: THREE.Vector3) {
  const radius = 0.72
  const angle = (orb / LEVEL_UP_ORBS + u * TURNS) * Math.PI * 2
  return target.set(
    Math.cos(angle) * radius,
    0.1 + (TOP - 0.1) * u,
    Math.sin(angle) * radius
  )
}

const heightFade = (y: number) =>
  1 - THREE.MathUtils.smoothstep(y, FADE_FROM, TOP)

function glowMaterial() {
  const material = new MeshBasicNodeMaterial()
  material.transparent = true
  material.depthWrite = false
  material.blending = THREE.AdditiveBlending
  material.side = THREE.DoubleSide
  material.toneMapped = false
  return material
}

export class LevelUpEffect {
  readonly group = new THREE.Group()
  readonly light: EnchantLight = {
    playerId: -1,
    position: new THREE.Vector3(),
    intensity: 0,
  }
  private floorGeometry = new THREE.PlaneGeometry(1, 1)
  private spriteGeometry = new THREE.PlaneGeometry(1, 1)
  private haloGeometry = new THREE.PlaneGeometry(1.55, 1.55).rotateX(
    -Math.PI / 2
  )
  private columnGeometry = new THREE.CylinderGeometry(
    1,
    1,
    1,
    32,
    1,
    true
  ).translate(0, 0.5, 0)
  private spriteMaterial = glowMaterial()
  private haloMaterial = glowMaterial()
  private floorMaterial = glowMaterial()
  private columnMaterial = glowMaterial()
  private floorOpacity = uniform(0)
  private columnOpacity = uniform(0)
  private gold = new THREE.Color('#ffb43c')
  private white = new THREE.Color('#fffbe8')
  private tint = new THREE.Color()
  private haloGlow = new THREE.InstancedBufferAttribute(
    new Float32Array(HALOS),
    1
  )
  private sprites: THREE.InstancedMesh
  private halos: THREE.InstancedMesh
  private floor = new THREE.Mesh(this.floorGeometry, this.floorMaterial)
  private column = new THREE.Mesh(this.columnGeometry, this.columnMaterial)
  private dummy = new THREE.Object3D()
  private matrix = new THREE.Matrix4()

  constructor() {
    const radius = uv().sub(0.5).length().mul(2)
    this.spriteMaterial.opacityNode = exp(radius.mul(2.6).pow(2).negate()).add(
      exp(radius.mul(9).pow(2).negate())
    )
    this.haloMaterial.colorNode = color('#ffe1a0')
    this.haloMaterial.opacityNode = exp(
      radius.sub(0.85).mul(30).pow(2).negate()
    )
      .add(exp(radius.sub(0.85).mul(8).pow(2).negate()).mul(0.25))
      .mul(attribute<'float'>('aLevelUpHalo', 'float'))
    this.floorMaterial.colorNode = mix(
      color('#ffc04d'),
      color('#fff8e0'),
      exp(radius.mul(2.2).pow(2).negate())
    )
    this.floorMaterial.opacityNode = exp(
      radius.sub(0.8).mul(16).pow(2).negate()
    )
      .add(float(1).sub(radius).max(0).pow(1.5).mul(0.7))
      .mul(this.floorOpacity)
    const rim = float(1).sub(normalView.z.abs())
    this.columnMaterial.colorNode = mix(
      color('#ffbf55'),
      color('#fff3cf'),
      rim.pow(3)
    )
    this.columnMaterial.opacityNode = rim
      .pow(2.5)
      .mul(0.8)
      .add(0.06)
      .mul(uv().y.smoothstep(0, 0.08))
      .mul(float(1).sub(uv().y).pow(1.4))
      .mul(this.columnOpacity)
    this.haloGeometry.setAttribute('aLevelUpHalo', this.haloGlow)
    this.haloGlow.setUsage(THREE.DynamicDrawUsage)
    this.sprites = new THREE.InstancedMesh(
      this.spriteGeometry,
      this.spriteMaterial,
      LEVEL_UP_ORBS * TRAIL + STREAKS
    )
    this.sprites.instanceColor = new THREE.InstancedBufferAttribute(
      new Float32Array(this.sprites.count * 3),
      3
    ).setUsage(THREE.DynamicDrawUsage)
    this.halos = new THREE.InstancedMesh(
      this.haloGeometry,
      this.haloMaterial,
      HALOS
    )
    for (const mesh of [this.sprites, this.halos])
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
    this.floor.rotation.x = -Math.PI / 2
    this.floor.position.y = 0.04
    this.column.scale.set(COLUMN_RADIUS, COLUMN_HEIGHT, COLUMN_RADIUS)
    this.group.add(this.floor, this.column, this.halos, this.sprites)
    this.group.traverse((object) => {
      object.frustumCulled = false
    })
    this.clear()
  }

  update(
    elapsed: number,
    feet: THREE.Vector3,
    camera: THREE.Camera,
    reduced = false
  ) {
    if (elapsed >= LEVEL_UP_DURATION) {
      this.clear()
      return
    }
    this.group.visible = true
    this.group.position.copy(feet)
    const fadeIn = THREE.MathUtils.smoothstep(elapsed, 0, 0.15)
    const fadeOut =
      1 -
      THREE.MathUtils.smoothstep(
        elapsed,
        LEVEL_UP_DURATION - 0.8,
        LEVEL_UP_DURATION
      )
    const rise = elapsed / LEVEL_UP_RISE
    const yaw = Math.atan2(
      camera.position.x - feet.x,
      camera.position.z - feet.z
    )

    this.floorOpacity.value =
      fadeIn * fadeOut * (0.45 + 0.55 * Math.exp(-elapsed * 3))
    this.floor.scale.setScalar(1.7 + (1 - Math.exp(-elapsed * 4)) * 0.45)
    this.column.visible = !reduced
    this.columnOpacity.value = fadeIn * fadeOut * 0.55

    this.halos.visible = !reduced
    if (!reduced) {
      for (let i = 0; i < HALOS; i++) {
        const life = THREE.MathUtils.clamp((elapsed - i * 0.3) / 1.3, 0, 1)
        this.matrix.makeTranslation(0, 0.1 + life ** 0.8 * 2.6, 0)
        this.halos.setMatrixAt(i, this.matrix)
        this.haloGlow.setX(i, Math.sin(Math.PI * life) * 0.9)
      }
      this.halos.instanceMatrix.needsUpdate = true
      this.haloGlow.needsUpdate = true
    }

    const trail = reduced ? REDUCED_TRAIL : TRAIL
    let index = 0
    for (let step = 0; step < trail; step++) {
      const u = rise - step * TRAIL_STEP
      if (u < 0) break
      if (u > 1) continue
      const tail = 1 - step / TRAIL
      for (let orb = 0; orb < LEVEL_UP_ORBS; orb++) {
        spiralPoint(u, orb, this.dummy.position)
        const glow = heightFade(this.dummy.position.y)
        this.dummy.quaternion.copy(camera.quaternion)
        this.dummy.scale.setScalar(step === 0 ? 0.6 : 0.3 * tail + 0.08)
        this.dummy.updateMatrix()
        this.sprites.setMatrixAt(index, this.dummy.matrix)
        this.setGlow(index, fadeIn * glow * tail ** 1.4)
        index++
      }
    }
    if (!reduced) {
      for (let i = 0; i < STREAKS; i++) {
        const angle = i * 2.399963229728653
        const seed = Math.sin(i * 12.9898) * 0.5 + 0.5
        const life = (elapsed * (0.55 + seed * 0.35) + seed) % 1
        const length = 0.7 + seed * 1.1
        const reach = COLUMN_RADIUS * (0.8 + (i % 3) * 0.1)
        this.dummy.position.set(
          Math.cos(angle) * reach,
          life * (COLUMN_HEIGHT - length * 0.5) + length * 0.3,
          Math.sin(angle) * reach
        )
        this.dummy.rotation.set(0, yaw, 0)
        this.dummy.scale.set(0.07, length, 1)
        this.dummy.updateMatrix()
        this.sprites.setMatrixAt(index, this.dummy.matrix)
        this.setGlow(index, Math.sin(Math.PI * life) * fadeIn * fadeOut * 0.75)
        index++
      }
    }
    this.sprites.count = index
    this.sprites.instanceMatrix.needsUpdate = true
    this.sprites.instanceColor!.needsUpdate = true

    spiralPoint(Math.min(1, rise), 0, this.light.position)
    this.light.intensity = reduced
      ? 0
      : LIGHT_INTENSITY * fadeIn * heightFade(this.light.position.y)
    this.light.position.add(feet)
  }

  private setGlow(index: number, glow: number) {
    this.tint
      .copy(this.gold)
      .lerp(this.white, glow ** 3)
      .multiplyScalar(glow)
    this.sprites.setColorAt(index, this.tint)
  }

  clear() {
    this.group.visible = false
    this.light.intensity = 0
  }

  dispose() {
    this.clear()
    this.sprites.dispose()
    this.halos.dispose()
    this.floorGeometry.dispose()
    this.spriteGeometry.dispose()
    this.haloGeometry.dispose()
    this.columnGeometry.dispose()
    this.spriteMaterial.dispose()
    this.haloMaterial.dispose()
    this.floorMaterial.dispose()
    this.columnMaterial.dispose()
    this.group.clear()
    this.group.removeFromParent()
  }
}
