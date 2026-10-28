<script lang="ts">
  import { T, useThrelte } from '@threlte/core'
  import { onMount } from 'svelte'
  import * as THREE from 'three'
  import type { WebGPURenderer } from 'three/webgpu'
  import type { LocalPlayer, RemotePlayer } from '../../stores/gameStore'
  import { teleportLoading } from '../../stores/debugStore'
  import {
    RAGE_AURA_LIMIT,
    RAGE_FADE_IN,
    RAGE_FADE_OUT,
    RageAuraEffect,
    type RageAura,
  } from '../../effects/rage-aura'

  let {
    currentPlayer,
    otherPlayers,
    getAnchor,
  }: {
    currentPlayer: LocalPlayer | null
    otherPlayers: Map<number, RemotePlayer>
    getAnchor: (playerId: number, target: THREE.Vector3) => boolean
  } = $props()
  const effect = new RageAuraEffect()
  const { camera, renderer, scene } = useThrelte()
  // Imperative only (frame loop) — never read from the template.
  // eslint-disable-next-line svelte/prefer-svelte-reactivity
  const strengths = new Map<number, number>()
  const pool: RageAura[] = []
  const auras: RageAura[] = []
  const frustum = new THREE.Frustum()
  const matrix = new THREE.Matrix4()
  const sphere = new THREE.Sphere(new THREE.Vector3(), 1.6)
  let prepared = false
  let elapsed = 0

  onMount(() => {
    let cancelled = false
    const warm = { feet: new THREE.Vector3(), strength: 0, seed: 0 }
    effect.update([warm], 0, $camera)
    void (renderer as unknown as WebGPURenderer)
      .compileAsync(effect.group, $camera, scene)
      .catch((error) => console.error('Rage aura shader warmup failed', error))
      .finally(() => {
        if (!cancelled) {
          effect.clear()
          prepared = true
        }
      })
    return () => {
      cancelled = true
      effect.dispose()
    }
  })

  function fade(id: number, raging: boolean, dt: number) {
    if (!raging && !strengths.has(id)) return
    const previous = strengths.get(id) ?? 0
    const next = raging
      ? Math.min(1, previous + dt / RAGE_FADE_IN)
      : Math.max(0, previous - dt / RAGE_FADE_OUT)
    if (next > 0) strengths.set(id, next)
    else strengths.delete(id)
  }

  export function update(dt: number) {
    if (!prepared || !$camera) return
    const player = currentPlayer
    if (!player || $teleportLoading) {
      strengths.clear()
      effect.clear()
      return
    }
    elapsed += dt
    fade(player.id, !!player.raging && player.health > 0, dt)
    for (const other of otherPlayers.values())
      fade(other.id, !!other.raging && other.health > 0, dt)
    if (strengths.size === 0) {
      effect.clear()
      return
    }
    matrix.multiplyMatrices(
      $camera.projectionMatrix,
      $camera.matrixWorldInverse
    )
    frustum.setFromProjectionMatrix(matrix, $camera.coordinateSystem)
    auras.length = 0
    for (const [id, strength] of strengths) {
      if (id !== player.id && !otherPlayers.has(id)) {
        strengths.delete(id)
        continue
      }
      const aura = (pool[auras.length] ??= {
        feet: new THREE.Vector3(),
        strength: 0,
        seed: 0,
      })
      if (!getAnchor(id, aura.feet)) continue
      sphere.center.copy(aura.feet).y += 1
      if (!frustum.intersectsSphere(sphere)) continue
      aura.strength = strength
      aura.seed = (id * 0.618034) % 1
      auras.push(aura)
    }
    if (auras.length > RAGE_AURA_LIMIT) {
      const { x, z } = player.position
      const distance = (aura: RageAura) =>
        (aura.feet.x - x) ** 2 + (aura.feet.z - z) ** 2
      auras.sort((a, b) => distance(a) - distance(b))
    }
    effect.update(auras, elapsed, $camera)
  }
</script>

<T is={effect.group} />
