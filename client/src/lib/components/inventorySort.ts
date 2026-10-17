import type { EquipSlot, ItemInstance } from '../network/networkTypes'
import {
  ammoAverageDamage,
  getItemDef,
  isConsumable,
  itemDisplayName,
} from '../data/itemDefs'
import type { Locale } from '../i18n'
import type { InventorySortMode } from '../stores/inventorySortSettings'

type Category = EquipSlot | 'ammo' | 'dungeon_key' | 'consumable' | 'misc'

// Follow CharacterPanel's slot order, with ammo beside the main hand.
const CATEGORY_ORDER: Category[] = [
  'head',
  'main_hand',
  'ammo',
  'off_hand',
  'chest',
  'ear',
  'neck',
  'belt',
  'pants',
  'boots',
  'ring',
  'ring_left',
  'hands',
  'back',
  'shirt',
  'consumable',
  'dungeon_key',
  'misc',
]

/** Kinds that earn their own run in the bag despite wearing no slot. */
const UNWORN_CATEGORIES: Category[] = ['ammo', 'dungeon_key']
const nameCollator = new Intl.Collator(undefined, { numeric: true })

function categoryOf(itemDefId: string): Category {
  const def = getItemDef(itemDefId)
  if (def?.equipSlot) return def.equipSlot
  const own = UNWORN_CATEGORIES.find((c) => c === def?.category)
  if (own) return own
  if (def && isConsumable(def)) return 'consumable'
  return 'misc'
}

export function inventoryGroupKey(item: ItemInstance): string {
  return !item.locked && getItemDef(item.item_def_id)?.stackable === true
    ? `${item.item_def_id}:${item.enchant}`
    : `unique:${item.instance_id}`
}

export function compareInventoryOrder(
  itemDefIdA: string,
  quantityA: number,
  itemDefIdB: string,
  quantityB: number
): number {
  const categoryDiff =
    CATEGORY_ORDER.indexOf(categoryOf(itemDefIdA)) -
    CATEGORY_ORDER.indexOf(categoryOf(itemDefIdB))
  if (categoryDiff !== 0) return categoryDiff

  const defA = getItemDef(itemDefIdA)
  const defB = getItemDef(itemDefIdB)

  // Sort ammo by damage, matching the default selection.
  const damageDiff =
    (defB ? ammoAverageDamage(defB) : 0) - (defA ? ammoAverageDamage(defA) : 0)
  if (damageDiff !== 0) return damageDiff

  const nameA = defA?.name ?? itemDefIdA
  const nameB = defB?.name ?? itemDefIdB
  const nameDiff = nameCollator.compare(nameA, nameB)
  return nameDiff !== 0 ? nameDiff : quantityB - quantityA
}

interface SortEntry {
  item: ItemInstance
  /** Bag index of the group's last part; the server appends pickups. */
  newest: number
}

function stackWeight(item: ItemInstance): number {
  return (getItemDef(item.item_def_id)?.weight ?? 1) * item.quantity
}

function compareByMode(
  a: SortEntry,
  b: SortEntry,
  mode: InventorySortMode,
  language?: Locale
): number {
  switch (mode) {
    case 'heavy':
      return stackWeight(b.item) - stackWeight(a.item)
    case 'light':
      return stackWeight(a.item) - stackWeight(b.item)
    case 'name':
      return nameCollator.compare(
        itemDisplayName(a.item.item_def_id, a.item.enchant, language),
        itemDisplayName(b.item.item_def_id, b.item.enchant, language)
      )
    case 'recent':
      return b.newest - a.newest
    case 'category':
      return 0
  }
}

/** Merges same-item/enchant stackable stacks, then sorts by `mode`, falling
 *  back to equip slot, name, and quantity. Client-side only. */
export function sortBag(
  bag: readonly ItemInstance[],
  mode: InventorySortMode = 'category',
  language?: Locale
): ItemInstance[] {
  const merged = new Map<string, SortEntry>()
  bag.forEach((item, index) => {
    const key = inventoryGroupKey(item)
    const existing = merged.get(key)
    if (existing) {
      existing.item.quantity += item.quantity
      existing.newest = index
    } else {
      merged.set(key, { item: { ...item }, newest: index })
    }
  })

  return [...merged.values()]
    .sort(
      (a, b) =>
        compareByMode(a, b, mode, language) ||
        compareInventoryOrder(
          a.item.item_def_id,
          a.item.quantity,
          b.item.item_def_id,
          b.item.quantity
        )
    )
    .map((entry) => entry.item)
}
