import { translate, type MessageKey } from '../i18n'
import { itemDisplayName } from '../data/itemDefs'
import { addChatMessage } from '../stores/gameStore'
import { altarOffering } from '../stores/altarStore'
import { pushFieldBossWake } from '../stores/fieldBossWakeStore'
import type { Position } from './networkTypes'

/** `AltarStatus` in shared/src/messages.rs, serde externally tagged. */
type AltarStatus =
  | 'no_offering'
  | 'not_full_moon'
  | 'raid_active'
  | { ready: { offering: string; monster: string } }
  | { offering_equipped: { offering: string } }

type FieldRaidOutcome = 'defeated' | 'moon_set' | 'wiped'

const OUTCOME_KEYS: Record<FieldRaidOutcome, MessageKey> = {
  defeated: 'fieldRaid.defeated',
  moon_set: 'fieldRaid.moonSet',
  wiped: 'fieldRaid.wiped',
}

const STATUS_KEYS: Record<Exclude<AltarStatus, object>, MessageKey> = {
  no_offering: 'altar.noOffering',
  not_full_moon: 'altar.notFullMoon',
  raid_active: 'altar.raidActive',
}

export function monsterName(id: string): string {
  return translate(`monsterName.${id}` as MessageKey) || id
}

function systemLine(text: string) {
  addChatMessage({ text, sender: 'system' })
}

export function handleAltarStatus(data: {
  object_id: number
  status: AltarStatus
}) {
  const { status } = data
  if (typeof status === 'string') {
    systemLine(translate(STATUS_KEYS[status]))
  } else if ('ready' in status) {
    altarOffering.set({ objectId: data.object_id, ...status.ready })
  } else {
    const item = itemDisplayName(status.offering_equipped.offering)
    systemLine(translate('altar.offeringEquipped', { item }))
  }
}

export function handleFieldRaidNotice(data: {
  monster: string
  outcome: FieldRaidOutcome
  reward: string | null
}) {
  systemLine(
    translate(OUTCOME_KEYS[data.outcome], {
      monster: monsterName(data.monster),
    })
  )
  if (data.reward) {
    systemLine(
      translate('fieldRaid.reward', { item: itemDisplayName(data.reward) })
    )
  }
}

export function handleFieldBossWaking(data: {
  monster: string
  position: Position
  wake_in_ms: number
}) {
  pushFieldBossWake({
    monster: data.monster,
    position: data.position,
    startedAt: Date.now(),
    collapseMs: data.wake_in_ms,
  })
}
