import { describe, expect, it } from 'vitest'
import {
  dungeonShortNames,
  matchDungeons,
  parseTpArgs,
  resolveTpDestination,
} from './tp-args'

describe('parseTpArgs', () => {
  it('parses x z with y defaulting to 0', () => {
    expect(parseTpArgs('-1450 4720')).toEqual({ x: -1450, z: 4720, y: 0 })
  })

  it('parses an explicit y', () => {
    expect(parseTpArgs('-1443.5 4711.5 -19.3')).toEqual({
      x: -1443.5,
      z: 4711.5,
      y: -19.3,
    })
  })

  it('tolerates extra whitespace', () => {
    expect(parseTpArgs('  10   20  ')).toEqual({ x: 10, z: 20, y: 0 })
  })

  it('rejects wrong argument counts', () => {
    expect(parseTpArgs('')).toBeNull()
    expect(parseTpArgs('5')).toBeNull()
    expect(parseTpArgs('1 2 3 4')).toBeNull()
  })

  it('rejects non-numeric input', () => {
    expect(parseTpArgs('abc 5')).toBeNull()
    expect(parseTpArgs('5 5.5.5')).toBeNull()
  })

  it('rejects non-finite values', () => {
    expect(parseTpArgs('Infinity 0')).toBeNull()
    expect(parseTpArgs('0 -Infinity')).toBeNull()
    expect(parseTpArgs('1e999 0')).toBeNull()
    expect(parseTpArgs('0 0 NaN')).toBeNull()
  })

  it('rejects values that overflow f32 on the wire', () => {
    expect(parseTpArgs('0 1e39')).toBeNull()
    expect(parseTpArgs('1e39 0')).toBeNull()
  })
})

describe('resolveTpDestination', () => {
  const dests = [
    { name: 'spawn', x: 0 },
    { name: 'old/d1', dungeonId: 'old_crypt', x: 1 },
    { name: 'old-boss/d1-boss', dungeonId: 'old_crypt', boss: true, x: 2 },
    { name: 'Snowpeak', x: 3 },
    { name: 'skeleton/d2', dungeonId: 'skeleton_crypt', x: 4 },
  ]
  const dungeons = [{ id: 'old_crypt' }, { id: 'skeleton_crypt' }]
  const resolve = (token: string) =>
    resolveTpDestination(token, dests, dungeons)?.x

  it('resolves by case-insensitive name', () => {
    expect(resolve('SNOWPEAK')).toBe(3)
  })

  it('resolves dungeons the way the floor form does', () => {
    expect(resolve('old')).toBe(1)
    expect(resolve('D1')).toBe(1)
    expect(resolve('old_crypt')).toBe(1)
    expect(resolve('d1-boss')).toBe(2)
    expect(resolve('skeleton')).toBe(4)
    expect(resolve('old/d1')).toBeUndefined()
    expect(resolve('crypt')).toBeUndefined()
    expect(resolve('d2-boss')).toBeUndefined()
  })

  it('resolves by 1-based index', () => {
    expect(resolveTpDestination('1', dests, dungeons)?.name).toBe('spawn')
    expect(resolveTpDestination('4', dests, dungeons)?.name).toBe('Snowpeak')
  })

  it('returns null for unknown names and out-of-range indices', () => {
    expect(resolveTpDestination('nowhere', dests, dungeons)).toBeNull()
    expect(resolveTpDestination('0', dests, dungeons)).toBeNull()
    expect(resolveTpDestination('6', dests, dungeons)).toBeNull()
  })
})

describe('matchDungeons', () => {
  const dungeons = [
    { id: 'old_crypt' },
    { id: 'orc_warrens' },
    { id: 'skeleton_crypt' },
  ]
  const ids = (token: string) => matchDungeons(token, dungeons).map((d) => d.id)

  it('takes a dN alias by list order', () => {
    expect(ids('D3')).toEqual(['skeleton_crypt'])
    expect(ids('d4')).toEqual([])
  })

  it('prefers an exact id', () => {
    expect(ids('Skeleton_Crypt')).toEqual(['skeleton_crypt'])
  })

  it('matches one id part', () => {
    expect(ids('skeleton')).toEqual(['skeleton_crypt'])
    expect(ids('orc')).toEqual(['orc_warrens'])
  })

  it('returns every dungeon a shared part names', () => {
    expect(ids('crypt')).toEqual(['old_crypt', 'skeleton_crypt'])
  })
})

describe('dungeonShortNames', () => {
  it('uses the first word only where last words collide', () => {
    const names = dungeonShortNames([
      'old_crypt',
      'orc_warrens',
      'skeleton_crypt',
    ])
    expect(names).toEqual(['old', 'warrens', 'skeleton'])
  })
})
