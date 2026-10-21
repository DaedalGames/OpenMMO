import type { Position } from '../network/networkTypes'

/** A `FieldBossWaking` event; times are `Date.now()` ms. */
export interface FieldBossWake {
  monster: string
  position: Position
  startedAt: number
  collapseMs: number
}

const pending: FieldBossWake[] = []
const NONE: readonly FieldBossWake[] = []

export function pushFieldBossWake(wake: FieldBossWake) {
  pending.push(wake)
}

/** Polled every frame, so the usual empty answer allocates nothing. */
export function takeFieldBossWakes(): readonly FieldBossWake[] {
  return pending.length ? pending.splice(0) : NONE
}
