import type { SkillTooltipParams } from '../actions/skillTooltip'
import {
  BATTLE_HYMN,
  HEALING_PRAYER,
  PRIMAL_ROAR,
  RAGE,
  VALHALLA_CHARGE,
  type ABILITIES,
} from '../data/abilities'
import { DAGGER_SKILL } from '../data/daggerSkill'
import {
  battle_hymn_stats,
  healing_prayer_stats,
  primal_roar_stats,
  valhalla_charge_stats,
} from '../wasm/onlinerpg_shared'
import { translate, type Locale } from './index'

export function abilityTooltip(
  ability: SkillTooltipParams & { id: (typeof ABILITIES)[number]['id'] },
  language: Locale
): SkillTooltipParams {
  const text = (key: Parameters<typeof translate>[0]) =>
    translate(key, {}, language)
  const seconds = (ms: number) =>
    translate('duration.seconds', { count: ms / 1000 }, language)
  const combatSkill = {
    label: text('skill.type'),
    value: text('skill.combatSkill'),
  }

  function stats() {
    switch (ability.id) {
      case DAGGER_SKILL.clip:
        return [
          combatSkill,
          { label: text('stat.damage'), value: '100% × 2' },
          { label: text('skill.class'), value: text('class.rogue') },
          { label: text('skill.weapon'), value: text('weapon.dagger') },
          {
            label: text('skill.cooldown'),
            value: seconds(DAGGER_SKILL.cooldownMs),
          },
        ]
      case RAGE.id:
        return [
          combatSkill,
          { label: text('stat.damage'), value: text('ability.rage.damage') },
          { label: text('stat.guard'), value: '-2' },
          { label: text('skill.class'), value: text('class.barbarian') },
          { label: text('skill.weapon'), value: text('ability.rage.weapon') },
          { label: text('skill.duration'), value: seconds(10_000) },
          { label: text('skill.cooldown'), value: seconds(20_000) },
        ]
      case PRIMAL_ROAR.id: {
        const roar = primal_roar_stats() as {
          radius_m: number
          stun_ms: number
          shield_ms: number
          cooldown_ms: number
        }
        return [
          combatSkill,
          { label: text('skill.class'), value: text('class.caveman') },
          { label: text('skill.radius'), value: `${roar.radius_m} m` },
          { label: text('skill.stun'), value: seconds(roar.stun_ms) },
          {
            label: text('stat.tempHp'),
            value: text('ability.primal_roar.tempHp'),
          },
          { label: text('skill.duration'), value: seconds(roar.shield_ms) },
          { label: text('skill.cooldown'), value: seconds(roar.cooldown_ms) },
        ]
      }
      case VALHALLA_CHARGE.id: {
        const charge = chargeStats()
        return [
          combatSkill,
          { label: text('skill.class'), value: text('class.valkyrie') },
          {
            label: text('skill.weapon'),
            value: text('ability.valhalla_charge.weapon'),
          },
          {
            label: text('skill.range'),
            value: `${charge.min_range_m}–${charge.max_range_m} m`,
          },
          {
            label: text('skill.slow'),
            value: translate(
              'ability.valhalla_charge.slow',
              {
                percent: charge.slow_percent,
                seconds: seconds(charge.slow_ms),
              },
              language
            ),
          },
          { label: text('skill.cooldown'), value: seconds(charge.cooldown_ms) },
        ]
      }
      case HEALING_PRAYER.id: {
        const prayer = healing_prayer_stats() as {
          range_m: number
          cooldown_ms: number
          dice: string
        }
        return [
          { label: text('skill.type'), value: text('skill.magic') },
          { label: text('skill.class'), value: text('class.priest') },
          {
            label: text('skill.target'),
            value: text('ability.healing_prayer.target'),
          },
          {
            label: text('skill.healing'),
            value: translate(
              'ability.healing_prayer.amount',
              { dice: prayer.dice },
              language
            ),
          },
          { label: text('skill.range'), value: `${prayer.range_m} m` },
          { label: text('skill.cooldown'), value: seconds(prayer.cooldown_ms) },
        ]
      }
      case BATTLE_HYMN.id: {
        const hymn = battle_hymn_stats() as {
          radius_m: number
          cast_ms: number
          duration_ms: number
        }
        return [
          { label: text('skill.type'), value: text('skill.magic') },
          { label: text('skill.class'), value: text('class.bard') },
          {
            label: text('skill.equipment'),
            value: text('ability.battle_hymn.equipment'),
          },
          {
            label: text('skill.target'),
            value: text('ability.battle_hymn.target'),
          },
          { label: text('skill.radius'), value: `${hymn.radius_m} m` },
          {
            label: text('skill.effect'),
            value: text('ability.battle_hymn.buffDescription'),
          },
          { label: text('skill.castTime'), value: seconds(hymn.cast_ms) },
          {
            label: text('skill.duration'),
            value: translate(
              'duration.minutes',
              { count: hymn.duration_ms / 60_000 },
              language
            ),
          },
        ]
      }
      default:
        return ability.stats
    }
  }

  function details() {
    if (
      ability.id === RAGE.id ||
      ability.id === PRIMAL_ROAR.id ||
      ability.id === HEALING_PRAYER.id ||
      ability.id === BATTLE_HYMN.id
    )
      return [text(`ability.${ability.id}.details`)]
    if (ability.id !== VALHALLA_CHARGE.id) return ability.details
    const charge = chargeStats()
    return [
      translate(
        'ability.valhalla_charge.details',
        {
          min: charge.min_range_m,
          max: charge.max_range_m,
          short: seconds(charge.short_slow_ms),
        },
        language
      ),
    ]
  }

  return {
    name: text(`ability.${ability.id}.name`),
    description: text(`ability.${ability.id}.description`),
    stats: stats(),
    details: details(),
  }
}

function chargeStats() {
  return valhalla_charge_stats() as {
    min_range_m: number
    max_range_m: number
    slow_percent: number
    slow_ms: number
    short_slow_ms: number
    cooldown_ms: number
  }
}
