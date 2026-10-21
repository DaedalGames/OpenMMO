import type { Position } from '../network/networkTypes'

/** A `MonsterGroundStrike` mark; times are `Date.now()` ms. */
export type GroundEruption = {
  position: Position
  floorLevel: number
  radius: number
  startedAt: number
  impactMs: number
}

const NONE: readonly GroundEruption[] = []
let pending: GroundEruption[] = []

export function playGroundEruption(event: GroundEruption) {
  pending.push(event)
}

export function takeGroundEruptions(): readonly GroundEruption[] {
  if (pending.length === 0) return NONE
  const events = pending
  pending = []
  return events
}

export function resetGroundEruptions() {
  pending = []
}
