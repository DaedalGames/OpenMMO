<script lang="ts">
  import { T, useThrelte } from '@threlte/core'
  import { onMount } from 'svelte'
  import * as THREE from 'three'
  import type { WebGPURenderer } from 'three/webgpu'
  import type { LocalPlayer } from '../../stores/gameStore'
  import {
    PREWARM_LEVEL_UP_EFFECTS,
    takeLevelUps,
    type LevelUp,
  } from '../../stores/levelUpEffectStore'
  import { teleportLoading } from '../../stores/debugStore'
  import { currentDungeonDepth } from '../../stores/dungeonStore'
  import {
    selectEnchantLight,
    type EnchantLight,
  } from '../../utils/enchantLight'
  import { LevelUpEffect, LEVEL_UP_DURATION } from '../../effects/level-up'
  import { playLevelUpSound } from '../../managers/sfxManager'

  const NEAR_SQ = 15 ** 2
  const CROWDED = 6

  let {
    currentPlayer,
    getAnchor,
    setPose,
  }: {
    currentPlayer: LocalPlayer | null
    getAnchor: (playerId: number, target: THREE.Vector3) => boolean
    setPose: (playerId: number, until: number) => void
  } = $props()
  const group = new THREE.Group()
  const feet = new THREE.Vector3()
  const frustum = new THREE.Frustum()
  const matrix = new THREE.Matrix4()
  const { camera, renderer, scene } = useThrelte()
  const slots: { system: LevelUpEffect; event: LevelUp | null }[] = []
  const lights: EnchantLight[] = []
  let prepared = false
  let active = 0

  function addSlot() {
    const slot = { system: new LevelUpEffect(), event: null }
    slots.push(slot)
    lights.push(slot.system.light)
    group.add(slot.system.group)
    return slot
  }

  function release(slot: (typeof slots)[number]) {
    if (slot.event) active--
    slot.event = null
    slot.system.clear()
  }

  const expired = (event: LevelUp | null, now: number) =>
    !event || now - event.startedAt >= LEVEL_UP_DURATION * 1000

  const near = (position: THREE.Vector3, player: LocalPlayer) =>
    (position.x - player.position.x) ** 2 +
      (position.z - player.position.z) ** 2 <=
    NEAR_SQ

  function clear() {
    takeLevelUps()
    slots.forEach(release)
  }

  $effect(() => {
    void $currentDungeonDepth
    void $teleportLoading
    clear()
  })

  onMount(() => {
    let cancelled = false
    for (let i = 0; i < PREWARM_LEVEL_UP_EFFECTS; i++)
      addSlot().system.group.visible = true
    void (renderer as unknown as WebGPURenderer)
      .compileAsync(group, $camera, scene)
      .catch((error) => console.error('Level-up shader warmup failed', error))
      .finally(() => {
        if (!cancelled) {
          clear()
          prepared = true
        }
      })
    return () => {
      cancelled = true
      clear()
      slots.forEach((slot) => slot.system.dispose())
    }
  })

  export function update() {
    if (!prepared || !$camera) return
    const player = currentPlayer
    if (!player || $teleportLoading) {
      clear()
      return
    }
    const events = takeLevelUps()
    if (events.length === 0 && active === 0) return
    const now = Date.now()
    for (const event of events) {
      if (expired(event, now)) continue
      const local = event.playerId === player.id
      if (local) playLevelUpSound()
      else if (getAnchor(event.playerId, feet) && near(feet, player))
        playLevelUpSound(0.5)
      const slot =
        (local
          ? slots[0]
          : slots.find(
              (entry, i) => i > 0 && entry.event?.playerId === event.playerId
            )) ??
        slots.find((entry, i) => i > 0 && expired(entry.event, now)) ??
        addSlot()
      if (!slot.event) active++
      slot.event = event
      slot.system.light.playerId = event.playerId
      setPose(event.playerId, event.startedAt + LEVEL_UP_DURATION * 1000)
    }
    matrix.multiplyMatrices(
      $camera.projectionMatrix,
      $camera.matrixWorldInverse
    )
    frustum.setFromProjectionMatrix(matrix, $camera.coordinateSystem)
    const crowded = active > CROWDED
    for (const slot of slots) {
      const event = slot.event
      if (!event) continue
      const local = event.playerId === player.id
      if (expired(event, now) || (local && player.health <= 0)) {
        release(slot)
        continue
      }
      if (
        !getAnchor(event.playerId, feet) ||
        (!local && !frustum.containsPoint(feet))
      ) {
        slot.system.clear()
        continue
      }
      slot.system.update(
        (now - event.startedAt) / 1000,
        feet,
        $camera,
        crowded || (!local && !near(feet, player))
      )
    }
  }

  export function getLight(): EnchantLight | null {
    if (!currentPlayer) return null
    return selectEnchantLight(lights, currentPlayer.id, currentPlayer.position)
  }
</script>

<T is={group} />
