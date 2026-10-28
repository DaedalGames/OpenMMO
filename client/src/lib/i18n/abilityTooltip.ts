import type { SkillTooltipParams } from '../actions/skillTooltip'
import { RAGE, type ABILITIES } from '../data/abilities'
import { DAGGER_SKILL } from '../data/daggerSkill'
import { translate, type Locale } from './index'

export function abilityTooltip(
  ability: SkillTooltipParams & { id: (typeof ABILITIES)[number]['id'] },
  language: Locale
): SkillTooltipParams {
  const text = (key: Parameters<typeof translate>[0]) =>
    translate(key, {}, language)
  const seconds = (ms: number) =>
    translate('duration.seconds', { count: ms / 1000 }, language)
  return {
    name: text(`ability.${ability.id}.name`),
    description: text(`ability.${ability.id}.description`),
    stats:
      ability.id === DAGGER_SKILL.clip
        ? [
            { label: text('skill.type'), value: text('skill.combatSkill') },
            { label: text('stat.damage'), value: '100% × 2' },
            { label: text('skill.class'), value: text('class.rogue') },
            { label: text('skill.weapon'), value: text('weapon.dagger') },
            {
              label: text('skill.cooldown'),
              value: seconds(DAGGER_SKILL.cooldownMs),
            },
          ]
        : ability.id === RAGE.id
          ? [
              { label: text('skill.type'), value: text('skill.combatSkill') },
              {
                label: text('stat.damage'),
                value: text('ability.rage.damage'),
              },
              { label: text('stat.guard'), value: '-2' },
              { label: text('skill.class'), value: text('class.barbarian') },
              {
                label: text('skill.weapon'),
                value: text('ability.rage.weapon'),
              },
              { label: text('skill.duration'), value: seconds(10_000) },
              { label: text('skill.cooldown'), value: seconds(20_000) },
            ]
          : ability.stats,
    details:
      ability.id === RAGE.id ? [text('ability.rage.details')] : ability.details,
  }
}
