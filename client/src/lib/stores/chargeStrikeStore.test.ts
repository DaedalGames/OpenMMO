import { beforeEach, expect, it } from 'vitest'
import {
  beginChargeStrike,
  chargeDashPose,
  chargeImpactMs,
  chargeLandsAt,
  resetChargeStrikes,
} from './chargeStrikeStore'

beforeEach(resetChargeStrikes)

it('lands the tagged blow with the dash and forgets the charge after', () => {
  beginChargeStrike(7, 400, 1000)
  expect(chargeImpactMs(7, 1300)).toBe(100)
  expect(chargeImpactMs(7, 1450)).toBe(0)
  expect(chargeImpactMs(8, 1300)).toBe(0)
  expect(chargeLandsAt(7, 2300)).toBe(1400)
  expect(chargeLandsAt(7, 2400)).toBeUndefined()
  expect(chargeLandsAt(7, 1500)).toBeUndefined()
})

it('eases the dash in so it meets the monster at its fastest', () => {
  const dash = {
    from: { x: 0, y: 0, z: 0 },
    to: { x: 8, y: 2, z: 0 },
    rotation: 0,
    startedAt: 100,
    durationMs: 400,
  }
  expect(chargeDashPose(dash, 100)).toEqual({
    position: { x: 0, y: 0, z: 0 },
    speed: 10,
    done: false,
  })
  expect(chargeDashPose(dash, 300).position.x).toBeLessThan(4)
  expect(chargeDashPose(dash, 499).speed).toBeCloseTo(30, 0)
  expect(chargeDashPose(dash, 600)).toEqual({
    position: { x: 8, y: 2, z: 0 },
    speed: 0,
    done: true,
  })
})
