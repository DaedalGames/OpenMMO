import { describe, expect, it } from 'vitest'
import { bandLabel, bandPlayers, dungeonBands, parseDungeonPopulation } from './dungeonPopulation'

const orc = { id: 'orc_warrens', name: 'Orc Warrens', floors: 10 }
const crypt = { id: 'old_crypt', name: 'Old Crypt', floors: 5 }
const data = {
  from: 1_800_000_000,
  until: 1_800_086_400,
  sample_interval_seconds: 60,
  band_floors: 5,
  dungeons: [crypt, orc],
  current: [{ dungeon: 'orc_warrens', band: 6, players: 3 }],
  samples: [
    { timestamp: 1_800_000_060, sample_count: 1, bands: [] },
    { timestamp: 1_800_000_120, sample_count: 1, bands: [{ dungeon: 'orc_warrens', band: 1, players: 2 }, { dungeon: 'orc_warrens', band: 6, players: 1 }] },
  ],
}

describe('dungeon population', () => {
  it('accepts per-band counts and hourly averages', () => {
    expect(parseDungeonPopulation(data)).toEqual(data)
    const hourly = { ...data, until: data.from + 168 * 3600, sample_interval_seconds: 3600, samples: [{ timestamp: data.from, sample_count: 60, bands: [{ dungeon: 'old_crypt', band: 1, players: 0.5 }] }] }
    expect(parseDungeonPopulation(hourly, 168)).toEqual(hourly)
  })

  it('rejects bands outside a dungeon and malformed samples', () => {
    for (const bands of [
      [{ dungeon: 'old_crypt', band: 6, players: 1 }],
      [{ dungeon: 'orc_warrens', band: 2, players: 1 }],
      [{ dungeon: 'unknown', band: 1, players: 1 }],
      [{ dungeon: 'orc_warrens', band: 1, players: 0 }],
      [null],
    ]) {
      expect(() => parseDungeonPopulation({ ...data, samples: [{ timestamp: data.until, sample_count: 1, bands }] })).toThrow()
    }
    expect(() => parseDungeonPopulation({ ...data, current: [{ dungeon: 'orc_warrens', band: 6, players: 1.5 }] })).toThrow()
    expect(() => parseDungeonPopulation({ ...data, samples: [data.samples[1], data.samples[0]] })).toThrow()
    expect(() => parseDungeonPopulation({ ...data, sample_interval_seconds: 3600 })).toThrow()
    expect(() => parseDungeonPopulation(data, 168)).toThrow()
    expect(() => parseDungeonPopulation({ ...data, dungeons: [orc, orc] })).toThrow()
    expect(() => parseDungeonPopulation(null)).toThrow()
  })

  it('labels bands and sums players', () => {
    expect(dungeonBands(orc, 5)).toEqual([1, 6])
    expect(dungeonBands({ ...orc, floors: 12 }, 5)).toEqual([1, 6, 11])
    expect(bandLabel(11, { ...orc, floors: 12 }, 5)).toBe('11–12층')
    expect(bandLabel(6, orc, 5)).toBe('6–10층')
    const counts = data.samples[1].bands
    expect(bandPlayers(counts, 'orc_warrens')).toBe(3)
    expect(bandPlayers(counts, 'orc_warrens', 6)).toBe(1)
    expect(bandPlayers(counts, 'old_crypt')).toBe(0)
  })
})
