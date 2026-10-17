export const PREWARM_LEVEL_UP_EFFECTS = 4
export type LevelUp = {
  playerId: number
  startedAt: number
}
const NONE: LevelUp[] = []
let pending: LevelUp[] = []

export function queueLevelUp(playerId: number) {
  pending = pending.filter((event) => event.playerId !== playerId)
  pending.push({ playerId, startedAt: Date.now() })
}

export function takeLevelUps(): readonly LevelUp[] {
  if (pending.length === 0) return NONE
  const events = pending
  pending = []
  return events
}
