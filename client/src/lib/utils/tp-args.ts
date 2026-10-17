/** Parse `/tp <x> <z> [y]`; null when malformed. The wire format is f32, so
 *  values must stay finite after rounding (1e39 would arrive as Infinity). */
export function parseTpArgs(
  args: string
): { x: number; z: number; y: number } | null {
  const parts = args.trim().split(/\s+/)
  if (parts.length < 2 || parts.length > 3) return null
  const [x, z, y = 0] = parts.map(Number)
  if (![x, z, y].every((v) => Number.isFinite(Math.fround(v)))) return null
  return { x, z, y }
}

/** Resolve a single-token `/tp` argument: a 1-based list index, a place
 *  name, or a dungeon named as for `/tp <dungeon> <floor>` (`matchDungeons`),
 *  with `-boss` for its boss room. */
export function resolveTpDestination<
  T extends { name: string; dungeonId?: string; boss?: boolean },
>(token: string, destinations: T[], dungeons: { id: string }[]): T | null {
  const trimmed = token.trim()
  if (/^\d+$/.test(trimmed)) {
    return destinations[parseInt(trimmed, 10) - 1] ?? null
  }
  const lower = trimmed.toLowerCase()
  const place = destinations.find(
    (d) => !d.dungeonId && d.name.toLowerCase() === lower
  )
  if (place) return place
  const base = lower.replace(/-boss$/, '')
  const boss = base !== lower
  const matches = matchDungeons(base, dungeons)
  if (matches.length !== 1) return null
  return (
    destinations.find(
      (d) => d.dungeonId === matches[0].id && !!d.boss === boss
    ) ?? null
  )
}

/** `d1`, `d2`, … for the dungeons in list (CSV) order. */
export const dungeonAlias = (index: number) => `d${index + 1}`

/** Dungeons a `/tp` token names: a `dN` alias or an exact id, else every
 *  dungeon with the token as one `_` part of its id ("skeleton" →
 *  skeleton_crypt). */
export function matchDungeons<T extends { id: string }>(
  token: string,
  dungeons: T[]
): T[] {
  const lower = token.toLowerCase()
  const aliased = dungeons.find((_, i) => dungeonAlias(i) === lower)
  if (aliased) return [aliased]
  const exact = dungeons.filter((d) => d.id === lower)
  if (exact.length > 0) return exact
  return dungeons.filter((d) => d.id.split('_').includes(lower))
}

/** `/tp` name of each dungeon id, in order: its last word, or its first where
 *  two ids share a last word (old_crypt → old, skeleton_crypt → skeleton). */
export function dungeonShortNames(ids: string[]): string[] {
  const words = ids.map((id) => id.split('_'))
  const lasts = words.map((w) => w[w.length - 1])
  return words.map((w, i) =>
    lasts.indexOf(lasts[i]) !== lasts.lastIndexOf(lasts[i]) ? w[0] : lasts[i]
  )
}
