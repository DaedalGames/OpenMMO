import type { Position } from '../network/networkTypes'

/** A `FieldBossWaking` event; times are `Date.now()` ms. */
export interface FieldBossWake {
  monster: string
  position: Position
  startedAt: number
  collapseMs: number
}

/** A `FieldBossSleeping` event; the boss sinks from `sinkAt` (`Date.now()` ms). */
export interface FieldBossSleep {
  monster: string
  position: Position
  sinkAt: number
}

const pending: FieldBossWake[] = []
const pendingSleeps: FieldBossSleep[] = []
const NONE: readonly never[] = []

export function pushFieldBossWake(wake: FieldBossWake) {
  pending.push(wake)
}

export function pushFieldBossSleep(sleep: FieldBossSleep) {
  pendingSleeps.push(sleep)
}

/** Polled every frame, so the usual empty answer allocates nothing. */
export function takeFieldBossWakes(): readonly FieldBossWake[] {
  return pending.length ? pending.splice(0) : NONE
}

export function takeFieldBossSleeps(): readonly FieldBossSleep[] {
  return pendingSleeps.length ? pendingSleeps.splice(0) : NONE
}
