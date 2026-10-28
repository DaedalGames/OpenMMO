import * as THREE from 'three'
import { MeshBasicNodeMaterial } from 'three/webgpu'
import { instancedMesh } from './dormant-wake'
import {
  color,
  exp,
  float,
  instanceColor,
  mix,
  normalView,
  sin,
  uniform,
  uv,
} from 'three/tsl'

export const RAGE_AURA_LIMIT = 32
export const RAGE_FADE_IN = 0.25
export const RAGE_FADE_OUT = 0.6
const WISPS = 8
const SHELL_HEIGHT = 1.9
const PULSE_HZ = 1.4
const GOLDEN_ANGLE = 2.399963229728653

export type RageAura = {
  feet: THREE.Vector3
  strength: number
  seed: number
}

// instanceColor carries (alpha, heat, 1); dividing it back out of the colour
// cancels the automatic instance-colour multiply.
const alpha = instanceColor.x
const heat = instanceColor.y
const instanceScale = instanceColor.max(0.001)

function auraMaterial() {
  const material = new MeshBasicNodeMaterial()
  material.transparent = true
  material.depthWrite = false
  material.side = THREE.DoubleSide
  material.toneMapped = false
  return material
}

export class RageAuraEffect {
  readonly group = new THREE.Group()
  private time = uniform(0)
  private shellGeometry = new THREE.CylinderGeometry(
    0.5,
    0.6,
    SHELL_HEIGHT,
    24,
    1,
    true
  ).translate(0, SHELL_HEIGHT / 2, 0)
  private wispGeometry = new THREE.PlaneGeometry(1, 1).translate(0, 0.5, 0)
  private shellMaterial = auraMaterial()
  private wispMaterial = auraMaterial()
  private shells: THREE.InstancedMesh
  private wisps: THREE.InstancedMesh
  private dummy = new THREE.Object3D()
  private matrix = new THREE.Matrix4()
  private code = new THREE.Color()

  constructor() {
    const rim = float(1).sub(normalView.z.abs())
    const height = uv().y
    const shimmer = sin(
      uv()
        .x.mul(Math.PI * 10)
        .add(height.mul(7))
        .sub(this.time.mul(5))
    )
      .mul(0.25)
      .add(0.75)
    this.shellMaterial.colorNode = mix(
      color('#d0160c'),
      color('#ff4a30'),
      rim.pow(3)
    ).div(instanceScale)
    this.shellMaterial.opacityNode = rim
      .pow(2)
      .mul(0.3)
      .add(0.02)
      .mul(height.smoothstep(0, 0.12))
      .mul(float(1).sub(height).pow(1.6))
      .mul(shimmer)
      .mul(alpha)

    const across = uv().x.sub(0.5).mul(2)
    this.wispMaterial.colorNode = mix(
      color('#e01a10'),
      color('#ff6a44'),
      heat
    ).div(instanceScale)
    this.wispMaterial.opacityNode = exp(across.mul(2.4).pow(2).negate())
      .mul(uv().y.smoothstep(0, 0.3))
      .mul(float(1).sub(uv().y).pow(1.3))
      .mul(alpha)

    this.shells = instancedMesh(
      this.shellGeometry,
      this.shellMaterial,
      RAGE_AURA_LIMIT
    )
    this.wisps = instancedMesh(
      this.wispGeometry,
      this.wispMaterial,
      RAGE_AURA_LIMIT * WISPS
    )
    this.group.add(this.shells, this.wisps)
    this.group.visible = false
  }

  update(auras: readonly RageAura[], seconds: number, camera: THREE.Camera) {
    const count = Math.min(auras.length, RAGE_AURA_LIMIT)
    this.group.visible = count > 0
    if (count === 0) return
    this.time.value = seconds
    let wisp = 0
    for (let i = 0; i < count; i++) {
      const { feet, strength, seed } = auras[i]
      const pulse =
        0.82 + 0.18 * Math.sin(seconds * PULSE_HZ * Math.PI * 2 + seed * 6)
      this.code.setRGB(strength * pulse, 0, 1)
      this.shells.setMatrixAt(i, this.matrix.makeTranslation(feet))
      this.shells.setColorAt(i, this.code)

      this.dummy.rotation.set(
        0,
        Math.atan2(camera.position.x - feet.x, camera.position.z - feet.z),
        0
      )
      for (let w = 0; w < WISPS; w++) {
        const phase = (Math.sin((seed + w) * 12.9898) * 0.5 + 0.5) % 1
        const life = (seconds * (0.55 + phase * 0.3) + phase) % 1
        const angle = seed * 7 + w * GOLDEN_ANGLE
        const reach = 0.38 + phase * 0.22
        this.dummy.position.set(
          feet.x + Math.cos(angle) * reach,
          feet.y + 0.15 + life * 1.7,
          feet.z + Math.sin(angle) * reach
        )
        this.dummy.scale.set(
          0.14 + phase * 0.06,
          (0.45 + phase * 0.25) * (1 - life * 0.4),
          1
        )
        this.dummy.updateMatrix()
        this.wisps.setMatrixAt(wisp, this.dummy.matrix)
        this.code.setRGB(
          Math.sin(Math.PI * life) * strength * 0.75,
          1 - life,
          1
        )
        this.wisps.setColorAt(wisp, this.code)
        wisp++
      }
    }
    this.shells.count = count
    this.wisps.count = wisp
    for (const mesh of [this.shells, this.wisps]) {
      mesh.instanceMatrix.needsUpdate = true
      mesh.instanceColor!.needsUpdate = true
    }
  }

  clear() {
    this.group.visible = false
  }

  dispose() {
    for (const mesh of [this.shells, this.wisps]) mesh.dispose()
    this.shellGeometry.dispose()
    this.wispGeometry.dispose()
    this.shellMaterial.dispose()
    this.wispMaterial.dispose()
    this.group.clear()
    this.group.removeFromParent()
  }
}
