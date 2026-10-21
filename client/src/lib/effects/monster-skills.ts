import * as THREE from 'three'
import { BARKAN_RUNE_SLASH } from '../utils/barkanRuneSlash'
import { createBarkanRuneSlashEffect } from './barkan-rune-slash'
import { BarkanFireFan } from './barkan-fire-fan'
import {
  EarthRoarEffect,
  EARTH_ROAR_CAST_MS,
  EARTH_ROAR_STRIKE_MS,
} from './earth-roar'
import type { MessageKey } from '../i18n'
import { playDungeonSound } from '../managers/sfxManager'

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
    /** Chat line warning everyone the skill can reach. */
    warning?: MessageKey
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
    warning: 'monsterSkill.earthRoar',
    createEffects(scene, _model, _weapon, _clip, cast, footprint) {
      const [halfWidth = 0, front = 0, back = 0] = (footprint ?? '')
        .split('|')
        .map(Number)
      const roar = new EarthRoarEffect(cast.range, { halfWidth, front, back })
      scene.add(roar.group)
      let roared = false
      return {
        start(origin) {
          roar.start(origin)
          roared = false
        },
        update(time, active, deltaTime, camera) {
          // The dungeon's wake-up roar until Terraclash has its own, timed
          // to peak as the dust wall leaves.
          if (active && !roared && time * 1000 >= EARTH_ROAR_STRIKE_MS - 600) {
            roared = true
            playDungeonSound('reset')
          }
          roar.update(deltaTime, camera)
        },
        dispose() {
          roar.dispose()
        },
      }
    },
  },
}
