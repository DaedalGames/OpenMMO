import { periods, type ChartHistory } from './metrics'

export type DungeonPopulationHours = 24 | 168 | 720
export const dungeonPopulationPeriods = periods.filter((period): period is Extract<typeof periods[number], { hours: DungeonPopulationHours }> =>
  period.hours === 24 || period.hours === 168 || period.hours === 720)

export interface DungeonInfo {
  id: string
  name: string
  floors: number
}

export interface DungeonBandCount {
  dungeon: string
  band: number
  players: number
}

export interface DungeonPopulationSample {
  timestamp: number
  sample_count: number
  bands: DungeonBandCount[]
}

export interface DungeonPopulation extends ChartHistory<DungeonPopulationSample> {
  band_floors: number
  dungeons: DungeonInfo[]
  current: DungeonBandCount[]
}

const count = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 0
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export function parseDungeonPopulation(value: unknown, hours: DungeonPopulationHours = 24): DungeonPopulation {
  const data = value as DungeonPopulation
  const period = dungeonPopulationPeriods.find((period) => period.hours === hours)
  if (!data || typeof data !== 'object' || !period || !count(data.from) || !count(data.until) ||
    data.until - data.from !== hours * 3600 || data.sample_interval_seconds !== period.interval ||
    !count(data.band_floors) || data.band_floors === 0 ||
    !Array.isArray(data.dungeons) || !Array.isArray(data.current) || !Array.isArray(data.samples)) {
    throw new Error('Invalid dungeon population')
  }
  const floors = new Map<string, number>()
  for (const dungeon of data.dungeons) {
    if (!dungeon || typeof dungeon.id !== 'string' || !dungeon.id || typeof dungeon.name !== 'string' ||
      !count(dungeon.floors) || dungeon.floors === 0 || floors.has(dungeon.id)) {
      throw new Error('Invalid dungeon population')
    }
    floors.set(dungeon.id, dungeon.floors)
  }
  const validBand = (players: (value: unknown) => boolean) => (entry: DungeonBandCount) =>
    entry && typeof entry.dungeon === 'string' && count(entry.band) && (entry.band - 1) % data.band_floors === 0 &&
    entry.band <= (floors.get(entry.dungeon) ?? 0) && players(entry.players) && entry.players > 0
  if (!data.current.every(validBand(count)) ||
    !data.samples.every((sample, index) => sample && count(sample.timestamp) &&
      sample.timestamp >= data.from && sample.timestamp <= data.until &&
      (index === 0 || sample.timestamp > data.samples[index - 1].timestamp) &&
      count(sample.sample_count) && sample.sample_count > 0 &&
      Array.isArray(sample.bands) && sample.bands.every(validBand(finite)))) {
    throw new Error('Invalid dungeon population')
  }
  return data
}

/** First floor of each band in the dungeon (1, 6, 11, ...). */
export const dungeonBands = (dungeon: DungeonInfo, bandFloors: number) =>
  Array.from({ length: Math.ceil(dungeon.floors / bandFloors) }, (_, index) => index * bandFloors + 1)

export const bandLabel = (band: number, dungeon: DungeonInfo, bandFloors: number) =>
  `${band}–${Math.min(band + bandFloors - 1, dungeon.floors)}층`

export const bandPlayers = (counts: DungeonBandCount[], dungeon: string, band?: number) =>
  counts.reduce((sum, entry) => entry.dungeon === dungeon && (band === undefined || entry.band === band) ? sum + entry.players : sum, 0)

const colors = ['#31594f', '#7870cf', '#bf7b38', '#c25a7c', '#3f86b5']

/** Chart lines: per-dungeon totals, or one dungeon's bands. */
export function seriesFor(history: DungeonPopulation, dungeon?: DungeonInfo) {
  const lines = dungeon
    ? dungeonBands(dungeon, history.band_floors).map((band) => ({ label: bandLabel(band, dungeon, history.band_floors), value: (sample: DungeonPopulationSample) => bandPlayers(sample.bands, dungeon.id, band) }))
    : history.dungeons.map((entry) => ({ label: entry.name, value: (sample: DungeonPopulationSample) => bandPlayers(sample.bands, entry.id) }))
  return lines.map((line, index) => ({ ...line, color: colors[index % colors.length] }))
}
