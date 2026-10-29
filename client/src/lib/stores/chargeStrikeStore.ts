import { writable } from 'svelte/store'
import type { Position } from '../network/networkTypes'
import { shortestWrappedDeltaX } from '../terrain/world-wrap'

/** Valhalla Charge: when each charger's dash lands (Date.now() ms). */
const landings = new Map<number, number>()
const CHARGE_WINDOW_MS = 1000
/** The stab starts this long before the dash lands and is held this long after. */
export const CHARGE_STAB_LEAD_MS = 300
export const CHARGE_STAB_HOLD_MS = 450

/** Waiting for a monster click, as when the charge was cast with no target. */
export const chargeTargeting = writable(false)

export function cancelChargeTargeting() {
  chargeTargeting.set(false)
}

export type ChargeDash = {
  from: Position
  to: Position
  rotation: number
  startedAt: number
  durationMs: number
}

/** Where the dash has the body at `now`. It eases in, so the body meets the
 *  monster at top speed. */
export function chargeDashPose(dash: ChargeDash, now: number) {
  const duration = Math.max(1, dash.durationMs)
  const t = Math.min(1, Math.max(0, (now - dash.startedAt) / duration))
  const f = t * (0.5 + 0.5 * t)
  const dx = shortestWrappedDeltaX(dash.from.x, dash.to.x)
  const dz = dash.to.z - dash.from.z
  return {
    position: {
      x: dash.from.x + dx * f,
      y: dash.from.y + (dash.to.y - dash.from.y) * f,
      z: dash.from.z + dz * f,
    },
    speed: t < 1 ? (Math.hypot(dx, dz) / (duration / 1000)) * (0.5 + t) : 0,
    done: t >= 1,
  }
}

export function beginChargeStrike(
  playerId: number,
  durationMs: number,
  now = Date.now()
) {
  landings.set(playerId, now + durationMs)
}

/** When `playerId`'s dash lands, while the charge is still playing out. */
export function chargeLandsAt(playerId: number, now = Date.now()) {
  if (landings.size === 0) return undefined
  const at = landings.get(playerId)
  if (at === undefined || now - at < CHARGE_WINDOW_MS) return at
  landings.delete(playerId)
  return undefined
}

/** Ms until the charge's blow lands, for the swing the server tagged. */
export function chargeImpactMs(playerId: number, now = Date.now()) {
  return Math.max(0, (chargeLandsAt(playerId, now) ?? now) - now)
}

export function resetChargeStrikes() {
  landings.clear()
}
