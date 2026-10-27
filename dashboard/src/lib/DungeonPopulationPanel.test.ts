import { describe, expect, it } from 'vitest'
import { render } from 'svelte/server'
import DungeonPopulationPanel from './DungeonPopulationPanel.svelte'
import type { DungeonPopulation } from './dungeonPopulation'

const history: DungeonPopulation = {
  from: 0,
  until: 86400,
  sample_interval_seconds: 60,
  band_floors: 5,
  dungeons: [{ id: 'old_crypt', name: 'Old Crypt', floors: 5 }, { id: 'orc_warrens', name: 'Orc Warrens', floors: 10 }],
  current: [{ dungeon: 'orc_warrens', band: 6, players: 3 }],
  samples: [
    { timestamp: 60, sample_count: 1, bands: [{ dungeon: 'old_crypt', band: 1, players: 2 }] },
    { timestamp: 120, sample_count: 1, bands: [{ dungeon: 'orc_warrens', band: 6, players: 4 }] },
  ],
}
const resource = (value: DungeonPopulation | null) => ({ history: value, loading: value === null, refreshing: false, error: '', refresh() {} })

describe('dungeon population panel', () => {
  it('tables current players per band and charts every dungeon', () => {
    const { body } = render(DungeonPopulationPanel, { props: { resource: resource(history) } })
    expect(body).toContain('던전 층별 인원')
    expect(body).toContain('6–10층')
    expect(body).toMatch(/class="num strong[^"]*">3</)
    expect(body).toContain('던전별 인원 그래프')
    expect(body).toContain('기간 최고 4명')
    expect(body).toContain('Orc Warrens 층별')
  })

  it('waits for the first response', () => {
    const { body } = render(DungeonPopulationPanel, { props: { resource: resource(null) } })
    expect(body).toContain('던전 인원 기록을 불러오고 있어요')
  })
})
