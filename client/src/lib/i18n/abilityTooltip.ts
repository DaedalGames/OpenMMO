import type { SkillTooltipParams } from '../actions/skillTooltip'
import type { ABILITIES } from '../data/abilities'
import { DAGGER_SKILL } from '../data/daggerSkill'
import { translate, type Locale } from './index'

export function abilityTooltip(
  ability: SkillTooltipParams & { id: (typeof ABILITIES)[number]['id'] },
  language: Locale
): SkillTooltipParams {
  const text = (key: Parameters<typeof translate>[0]) =>
    translate(key, {}, language)
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
              value: translate(
                'duration.seconds',
                { count: DAGGER_SKILL.cooldownMs / 1000 },
                language
              ),
            },
          ]
        : ability.stats,
    details: ability.details,
  }
}
