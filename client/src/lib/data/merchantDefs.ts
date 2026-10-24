import merchantsJson from '../../../../data/merchants.json'

export interface MerchantDefinition {
  id: string
  npcName: string
  sellRatePercent: number
  /** Semicolon-separated item def ids. */
  catalog?: string
  currencyItem?: string
  catalogPrices?: string
  discountBudget?: number
  playerDiscountCap?: number
}

export function exchangePrice(
  merchant: MerchantDefinition,
  itemDefId: string
): number | undefined {
  const entry = merchant.catalogPrices
    ?.split(';')
    .find((entry) => entry.split(':')[0] === itemDefId)
  const price = Number(entry?.split(':')[1])
  return Number.isSafeInteger(price) && price > 0 ? price : undefined
}

const merchantDefs = merchantsJson as Record<string, MerchantDefinition>

const byNpcName = new Map(
  Object.values(merchantDefs).map((def) => [def.npcName, def])
)

/** Merchant lookup by NPC character name (NPCs are agent-controlled players).
 *  Non-merchant traders live in traderDefs.ts; use getNpcCapabilities there
 *  to decide how an NPC can be interacted with. */
export function getMerchantByNpcName(
  npcName: string
): MerchantDefinition | undefined {
  return byNpcName.get(npcName)
}

const stocked = new Set(
  Object.values(merchantDefs).flatMap((def) =>
    (def.catalog ?? '')
      .split(';')
      .map((id) => id.trim())
      .filter(Boolean)
  )
)

/** Whether any merchant shelf carries the item. */
export function isStockedByAnyMerchant(itemDefId: string): boolean {
  return stocked.has(itemDefId)
}

export default merchantDefs
