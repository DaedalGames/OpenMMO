import * as THREE from 'three'
import { BARKAN_RUNE_SLASH } from '../utils/barkanRuneSlash'
import { createBarkanRuneSlashEffect } from './barkan-rune-slash'
import { BarkanFireFan } from './barkan-fire-fan'
import {
  EarthRoarEffect,
  parseFootprint,
  EARTH_ROAR_CAST_MS,
  EARTH_ROAR_STRIKE_MS,
} from './earth-roar'
import {
  FormationBreakEffect,
  FORMATION_BREAK_CAST_MS,
  FORMATION_BREAK_POOL_MS,
  FORMATION_BREAK_STRIKE_MS,
} from './formation-break'
import {
  EarthquakeEffect,
  EARTHQUAKE_CAST_MS,
  EARTHQUAKE_STRIKE_MS,
} from './earthquake'
import { preloadMonsterSound } from '../managers/sfxManager'

export interface MonsterSkillCast {
  rotation: number
  range: number
  halfAngle: number
}

export interface MonsterSkillEffects {
  /** Aim the effects at a cast standing at `origin`. */
  start(origin: THREE.Vector3, cast: MonsterSkillCast): void
  /** `time` is the skill clip time; `active` is false between casts. */
  update(
    time: number,
    active: boolean,
    deltaTime: number,
    camera: THREE.Camera | undefined
  ): void
  dispose(): void
}

// Seconds after a cast before its effects stop updating; covers the last
// flames' lifetime.
const SETTLE_SECONDS = 1
/** Telegraphed monster skills by the server's `MonsterSkillId`. */
export const MONSTER_SKILLS: Record<
  string,
  {
    clip: string
    durationMs: number
    /** Played once per cast as the clip passes `atMs`. */
    sound?: { url: string; atMs: number }
    /** The cast's marked spots split open at `impactMs` with `sound`, then
     *  stay molten `lingerMs` longer. */
    marks?: { impactMs: number; lingerMs?: number; sound?: string }
    createEffects(
      scene: THREE.Object3D,
      model: THREE.Object3D,
      weapon: THREE.Object3D | undefined,
      clip: THREE.AnimationClip,
      cast: MonsterSkillCast,
      /** monsters.csv `footprint`, `halfWidth|front|back`. */
      footprint: string | undefined
    ): MonsterSkillEffects
  }
> = {
  rune_slash: {
    clip: 'RuneSlash',
    durationMs: BARKAN_RUNE_SLASH.duration * 1000,
    createEffects(scene, model, weapon, clip, cast) {
      const blade = createBarkanRuneSlashEffect(model, weapon!, clip, {
        light: false,
        bounds: false,
      })
      const fan = new BarkanFireFan(cast.range, cast.halfAngle)
      scene.add(fan.group, fan.particleGroup)
      let idle = 0
      return {
        start(origin, next) {
          fan.group.position.copy(origin)
          fan.group.rotation.y = next.rotation
        },
        update(time, active, deltaTime, camera) {
          idle = active ? 0 : idle + deltaTime
          fan.particleGroup.visible = idle <= SETTLE_SECONDS
          if (!fan.particleGroup.visible) return
          blade.update(time, active)
          fan.update(time, active, deltaTime, camera)
        },
        dispose() {
          blade.dispose()
          fan.dispose()
        },
      }
    },
  },
  earth_roar: {
    clip: 'Roar',
    durationMs: EARTH_ROAR_CAST_MS,
    // The roar takes 0.3s to reach full voice.
    sound: {
      url: '/sounds/terraclash-roar.ogg',
      atMs: EARTH_ROAR_STRIKE_MS - 300,
    },
    createEffects(scene, _model, _weapon, _clip, cast, footprint) {
      const roar = new EarthRoarEffect(cast.range, parseFootprint(footprint))
      scene.add(roar.group)
      return {
        start(origin) {
          roar.start(origin)
        },
        update(_time, _active, deltaTime, camera) {
          roar.update(deltaTime, camera)
        },
        dispose() {
          roar.dispose()
        },
      }
    },
  },
  formation_break: {
    clip: 'Smash',
    durationMs: FORMATION_BREAK_CAST_MS,
    sound: {
      url: '/sounds/terraclash-smash.ogg',
      atMs: FORMATION_BREAK_STRIKE_MS,
    },
    marks: {
      impactMs: FORMATION_BREAK_STRIKE_MS,
      lingerMs: FORMATION_BREAK_POOL_MS,
    },
    createEffects(scene, _model, _weapon, _clip, cast, footprint) {
      const smash = new FormationBreakEffect(
        cast.range,
        cast.halfAngle,
        parseFootprint(footprint)
      )
      scene.add(smash.group)
      return {
        start(origin, next) {
          smash.start(origin, next.rotation)
        },
        update(_time, _active, deltaTime, camera) {
          smash.update(deltaTime, camera)
        },
        dispose() {
          smash.dispose()
        },
      }
    },
  },
  earthquake: {
    clip: 'Quake',
    durationMs: EARTHQUAKE_CAST_MS,
    // The swell runs 3.03s and peaks as it ends.
    sound: {
      url: '/sounds/terraclash-quake.ogg',
      atMs: EARTHQUAKE_STRIKE_MS - 3030,
    },
    marks: {
      impactMs: EARTHQUAKE_STRIKE_MS,
      sound: '/sounds/terraclash-eruption.ogg',
    },
    createEffects(scene, _model, _weapon, _clip, _cast, footprint) {
      const quake = new EarthquakeEffect(parseFootprint(footprint))
      scene.add(quake.group)
      return {
        start(origin) {
          quake.start(origin)
        },
        update(_time, _active, deltaTime, camera) {
          quake.update(deltaTime, camera)
        },
        dispose() {
          quake.dispose()
        },
      }
    },
  },
}

export function preloadMonsterSkillSounds() {
  for (const { sound, marks } of Object.values(MONSTER_SKILLS)) {
    if (sound) preloadMonsterSound(sound.url)
    if (marks?.sound) preloadMonsterSound(marks.sound)
  }
}
