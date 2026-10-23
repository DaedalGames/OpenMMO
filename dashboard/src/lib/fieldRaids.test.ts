import { describe, expect, it } from 'vitest'
import { failures, parseFieldRaids, successRate } from './fieldRaids'

const terraclash = {
  boss: 'terraclash', name: 'Terraclash', summons: 5, defeated: 3, moon_set: 0, dawn: 0, wiped: 1, last_defeated_at: 1_799_990_000,
}
const data = { until: 1_800_000_100, collection_started_at: 1_799_000_000, bosses: [terraclash] }

describe('field raids', () => {
  it('accepts per-boss counts', () => {
    expect(parseFieldRaids(data)).toEqual(data)
    expect(parseFieldRaids({ ...data, bosses: [{ ...terraclash, summons: 0, defeated: 0, wiped: 0, last_defeated_at: null }] })).toBeTruthy()
  })

  it('rejects malformed counts and more outcomes than summons', () => {
    for (const boss of [
      { ...terraclash, summons: -1 }, { ...terraclash, defeated: 1.5 }, { ...terraclash, wiped: 3 },
      { ...terraclash, name: '' }, { ...terraclash, last_defeated_at: 'x' }, null,
    ]) {
      expect(() => parseFieldRaids({ ...data, bosses: [boss] })).toThrow()
    }
    expect(() => parseFieldRaids(null)).toThrow()
  })

  it('rates success over settled raids only', () => {
    expect(failures(terraclash)).toBe(1)
    expect(successRate(terraclash)).toBe(75)
    expect(successRate({ ...terraclash, defeated: 0, wiped: 0 })).toBeNull()
  })
})
