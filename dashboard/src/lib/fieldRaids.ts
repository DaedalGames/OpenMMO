export interface FieldRaidCounts {
  boss: string
  name: string
  summons: number
  defeated: number
  moon_set: number
  dawn: number
  wiped: number
  last_defeated_at: number | null
}

export interface FieldRaids {
  until: number
  collection_started_at: number
  bosses: FieldRaidCounts[]
}

const count = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 0
const text = (value: unknown): value is string => typeof value === 'string' && value.length > 0

const validBoss = (boss: FieldRaidCounts) =>
  text(boss.boss) && text(boss.name)
  && [boss.summons, boss.defeated, boss.moon_set, boss.dawn, boss.wiped].every(count)
  && failures(boss) + boss.defeated <= boss.summons
  && (boss.last_defeated_at === null || count(boss.last_defeated_at))

export function parseFieldRaids(value: unknown): FieldRaids {
  const data = value as FieldRaids
  if (!data || typeof data !== 'object' || !count(data.until) || !count(data.collection_started_at)
    || !Array.isArray(data.bosses) || !data.bosses.every((boss) => boss && typeof boss === 'object' && validBoss(boss))) {
    throw new Error('Invalid field raids response')
  }
  return data
}

export const failures = (boss: FieldRaidCounts) => boss.moon_set + boss.dawn + boss.wiped

export const successRate = (boss: FieldRaidCounts) => {
  const settled = boss.defeated + failures(boss)
  return settled === 0 ? null : boss.defeated / settled * 100
}
