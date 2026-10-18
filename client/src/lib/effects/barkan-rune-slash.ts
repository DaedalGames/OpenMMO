import * as THREE from 'three'
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { BARKAN_RUNE_SLASH } from '../utils/barkanRuneSlash'

export function createBarkanRuneSlashEffect(
  model: THREE.Object3D,
  weapon: THREE.Object3D,
  clip: THREE.AnimationClip
) {
  const materials: {
    material: THREE.MeshStandardMaterial
    intensity: number
  }[] = []
  weapon.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return
    for (const material of Array.isArray(node.material)
      ? node.material
      : [node.material])
      if (
        material instanceof THREE.MeshStandardMaterial &&
        material.emissiveMap
      )
        materials.push({ material, intensity: material.emissiveIntensity })
  })
  const light = new THREE.PointLight('#ff7c24', 0, 3, 2)
  light.position.set(0.8, 0, 0)
  weapon.add(light)
  const ghost = clone(model)
  const ghostWeapon = ghost.getObjectByName(weapon.name)!
  const mixer = new THREE.AnimationMixer(ghost)
  const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1).play()
  action.clampWhenFinished = true
  const bounds = new THREE.Box3()
  for (let index = 0; index <= 60; index++) {
    mixer.setTime((clip.duration * index) / 60)
    ghost.updateMatrixWorld(true)
    bounds.union(new THREE.Box3().setFromObject(ghostWeapon, true))
  }
  const segments = 48
  const positions: number[] = []
  const colors: number[] = []
  const indices: number[] = []
  const point = new THREE.Vector3()
  for (let index = 0; index <= segments; index++) {
    mixer.setTime(
      THREE.MathUtils.lerp(
        BARKAN_RUNE_SLASH.strikeStart,
        BARKAN_RUNE_SLASH.strikeEnd,
        index / segments
      )
    )
    ghost.updateMatrixWorld(true)
    for (const x of [0.25, 1.1, 1.617]) {
      ghost.worldToLocal(ghostWeapon.localToWorld(point.set(x, 0, 0)))
      positions.push(...point.toArray())
      colors.push(1, 0.45, 0.08, 0)
    }
    if (index < segments) {
      const a = index * 3
      for (let row = 0; row < 2; row++)
        indices.push(
          a + row,
          a + row + 1,
          a + row + 3,
          a + row + 1,
          a + row + 4,
          a + row + 3
        )
    }
  }
  mixer.stopAllAction()
  mixer.uncacheRoot(ghost)
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(positions, 3)
  )
  const colorAttribute = new THREE.Float32BufferAttribute(colors, 4)
  geometry.setAttribute('color', colorAttribute)
  geometry.setIndex(indices)
  const material = new THREE.MeshBasicMaterial({
    color: '#ffbe65',
    vertexColors: true,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    depthWrite: false,
    toneMapped: false,
  })
  const trail = new THREE.Mesh(geometry, material)
  trail.name = 'BarkanRuneSlashTrail'
  trail.frustumCulled = false
  model.add(trail)
  return {
    bounds,
    update(time: number, active: boolean) {
      const enabled = active && weapon.visible
      const charge = THREE.MathUtils.smoothstep(time, 0.15, 0.65)
      const fade =
        1 -
        THREE.MathUtils.smoothstep(
          time,
          BARKAN_RUNE_SLASH.strikeEnd,
          BARKAN_RUNE_SLASH.strikeEnd + 0.35
        )
      const strength = enabled ? charge * fade : 0
      for (const { material, intensity } of materials)
        material.emissiveIntensity = intensity + strength * 12
      light.intensity = strength * 5
      const progress = THREE.MathUtils.clamp(
        (time - BARKAN_RUNE_SLASH.strikeStart) /
          (BARKAN_RUNE_SLASH.strikeEnd - BARKAN_RUNE_SLASH.strikeStart),
        0,
        1
      )
      const end = Math.floor(progress * segments)
      const start = Math.max(0, end - 16)
      geometry.setDrawRange(start * 12, (end - start) * 12)
      for (let index = 0; index <= segments; index++) {
        const age = THREE.MathUtils.clamp(
          (index - start) / Math.max(1, end - start),
          0,
          1
        )
        colorAttribute.setW(index * 3 + 1, age * age)
      }
      colorAttribute.needsUpdate = true
      material.opacity = enabled
        ? (1 -
            THREE.MathUtils.smoothstep(
              time,
              BARKAN_RUNE_SLASH.strikeEnd,
              BARKAN_RUNE_SLASH.strikeEnd + 0.22
            )) *
          0.7
        : 0
      trail.visible =
        enabled &&
        time >= BARKAN_RUNE_SLASH.strikeStart &&
        time < BARKAN_RUNE_SLASH.strikeEnd + 0.22
    },
    dispose() {
      for (const { material, intensity } of materials)
        material.emissiveIntensity = intensity
      light.removeFromParent()
      trail.removeFromParent()
      geometry.dispose()
      material.dispose()
    },
  }
}
