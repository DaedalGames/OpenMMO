import { beforeEach, describe, expect, it } from 'vitest'
import { queueLevelUp, takeLevelUps } from './levelUpEffectStore'

beforeEach(() => {
  takeLevelUps()
})
describe('level-up event queue', () => {
  it('delivers once and coalesces repeats from one player', () => {
    queueLevelUp(7)
    queueLevelUp(8)
    queueLevelUp(7)
    expect(takeLevelUps().map((event) => event.playerId)).toEqual([8, 7])
    expect(takeLevelUps()).toEqual([])
  })
})
