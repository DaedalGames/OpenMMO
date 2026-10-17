import type { LocalizedMessage } from '../i18n'

// Lower bound of COIN_PILE_JACKPOT_COPPER in server/src/game_state/inventory.rs.
const COIN_PILE_JACKPOT_MIN_COPPER = 5000

export function isCoinPileJackpot(localization?: LocalizedMessage | null) {
  return (
    localization?.code === 'server.goldPickedUp' &&
    Number(localization.params.amount) >= COIN_PILE_JACKPOT_MIN_COPPER
  )
}
