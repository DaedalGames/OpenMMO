import { describe, expect, it } from 'vitest'
import { isCoinPileJackpot } from './coinPileJackpot'

const pickup = (amount: string) => ({
  code: 'server.goldPickedUp',
  params: { amount },
})

describe('isCoinPileJackpot', () => {
  it('flags only jackpot-sized coin pile payouts', () => {
    expect(isCoinPileJackpot(pickup('5000'))).toBe(true)
    expect(isCoinPileJackpot(pickup('15000'))).toBe(true)
    expect(isCoinPileJackpot(pickup('10'))).toBe(false)
    expect(
      isCoinPileJackpot({ code: 'server.other', params: { amount: '9000' } })
    ).toBe(false)
    expect(isCoinPileJackpot(null)).toBe(false)
  })
})
