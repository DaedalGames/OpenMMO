import { persistedString } from './persisted'

export const INVENTORY_SORT_MODES = [
  'category',
  'heavy',
  'light',
  'expensive',
  'name',
  'recent',
  'oldest',
] as const
export type InventorySortMode = (typeof INVENTORY_SORT_MODES)[number]

export const inventorySortMode = persistedString<InventorySortMode>(
  'onlinerpg_inventorySortMode',
  'category',
  (value): value is InventorySortMode =>
    (INVENTORY_SORT_MODES as readonly string[]).includes(value)
)
