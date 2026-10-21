<script lang="ts">
  import { T, useThrelte } from '@threlte/core'
  import { onMount } from 'svelte'
  import * as THREE from 'three'
  import type { WebGPURenderer } from 'three/webgpu'
  import type { LocalPlayer } from '../../stores/gameStore'
  import { currentDungeonDepth } from '../../stores/dungeonStore'
  import { playerVisualFloorLevel } from '../../stores/housingStore'
  import {
    takeGroundEruptions,
    type GroundEruption,
  } from '../../stores/groundEruptionStore'
  import {
    GroundEruptionAssets,
    GroundEruptionEffect,
  } from '../../effects/ground-eruption'
  import { unwrapWorldXNear } from '../../terrain/world-wrap'

  let { currentPlayer }: { currentPlayer: LocalPlayer | null } = $props()
  const { camera, renderer, scene } = useThrelte()
  const group = new THREE.Group()
  const slots: {
    effect: GroundEruptionEffect
    event: GroundEruption | null
  }[] = []
  let prepared = false
  let seed = 1

  onMount(() => {
    let disposed = false
    const assets = new GroundEruptionAssets()
    for (let i = 0; i < 6; i++) {
      const effect = new GroundEruptionEffect(assets)
      slots.push({ effect, event: null })
      group.add(effect.group)
      effect.start(1, 1.5, i + 1)
    }
    void (renderer as unknown as WebGPURenderer)
      .compileAsync(group, $camera, scene)
      .catch((error) =>
        console.error('Ground eruption shader warmup failed', error)
      )
      .finally(() => {
        if (disposed) return
        slots.forEach(({ effect }) => effect.clear())
        prepared = true
      })
    return () => {
      disposed = true
      slots.forEach(({ effect }) => effect.dispose())
      assets.dispose()
    }
  })

  export function update() {
    if (!prepared || !$camera) return
    const now = Date.now()
    for (const event of takeGroundEruptions()) {
      const slot =
        slots.find((entry) => !entry.event) ??
        slots.reduce((oldest, entry) =>
          entry.event!.startedAt < oldest.event!.startedAt ? entry : oldest
        )
      slot.event = event
      slot.effect.start(event.impactMs, event.radius, seed++)
    }
    const floor =
      $currentDungeonDepth > 0
        ? -$currentDungeonDepth
        : Math.max(0, $playerVisualFloorLevel)
    for (const slot of slots) {
      const event = slot.event
      if (!event) continue
      const elapsed = now - event.startedAt
      if (!currentPlayer || !slot.effect.update(elapsed, $camera)) {
        slot.event = null
        slot.effect.clear()
        continue
      }
      slot.effect.group.visible = event.floorLevel === floor
      slot.effect.group.position.set(
        unwrapWorldXNear(currentPlayer.position.x, event.position.x),
        event.position.y,
        event.position.z
      )
    }
  }
</script>

<T is={group} />
