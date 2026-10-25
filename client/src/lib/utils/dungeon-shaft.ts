import type { DungeonShaft } from '../managers/dungeonManager'
import type { DungeonGeoCtx } from './dungeon-geo-constants'

export function shaftRect(shaft: DungeonShaft, ctx: DungeonGeoCtx) {
  return shaft.alongZ
    ? { x: shaft.x, z: shaft.z, w: ctx.shaftW, d: ctx.shaftLen }
    : { x: shaft.x, z: shaft.z, w: ctx.shaftLen, d: ctx.shaftW }
}

/** Half-open cell membership, matching Rust. */
export function rectContains(
  r: { x: number; z: number; w: number; d: number },
  x: number,
  z: number
): boolean {
  return x >= r.x && x < r.x + r.w && z >= r.z && z < r.z + r.d
}

export function shaftContains(
  shaft: DungeonShaft,
  ctx: DungeonGeoCtx,
  x: number,
  z: number
): boolean {
  return rectContains(shaftRect(shaft, ctx), x, z)
}

/** Cell at run position i (0 = entry/shallow end), lateral offset wOff. */
export function shaftStepCell(
  shaft: DungeonShaft,
  ctx: DungeonGeoCtx,
  i: number,
  wOff: number
): { x: number; z: number } {
  const run = shaft.reversed ? ctx.shaftLen - 1 - i : i
  return shaft.alongZ
    ? { x: shaft.x + wOff, z: shaft.z + run }
    : { x: shaft.x + run, z: shaft.z + wOff }
}
