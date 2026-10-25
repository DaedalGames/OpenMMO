import type { RoomData } from '../types/housing'

export const FLOOR_THICKNESS = 0.1
export const LANDING_DEPTH = 0.5

export type WallDirection = 'north' | 'south' | 'east' | 'west'

export interface WallDirInfo {
  isNS: boolean
  isFront: boolean
  opposite: WallDirection
}

export const WALL_DIR_INFO: Record<WallDirection, WallDirInfo> = {
  north: { isNS: true, isFront: false, opposite: 'south' },
  south: { isNS: true, isFront: true, opposite: 'north' },
  east: { isNS: false, isFront: false, opposite: 'west' },
  west: { isNS: false, isFront: true, opposite: 'east' },
}

export function floorYBase(floorLevel: number, wallHeight: number): number {
  return floorLevel * (wallHeight + FLOOR_THICKNESS)
}

export function getStairwellYOffset(
  room: RoomData,
  houseOriginX: number,
  houseOriginZ: number,
  wx: number,
  wz: number
): number {
  const { localX, localZ, sizeX, sizeZ, wallHeight, floorLevel } = room
  const alongZ = sizeZ >= sizeX
  const stairLen = alongZ ? sizeZ : sizeX
  const totalRise = wallHeight + FLOOR_THICKNESS
  const baseY = floorYBase(floorLevel, wallHeight)
  const reversed = room.stairReversed ?? false

  const roomStartX = houseOriginX + localX
  const roomStartZ = houseOriginZ + localZ
  let posAlongStair = alongZ ? wz - roomStartZ : wx - roomStartX
  if (reversed) posAlongStair = stairLen - posAlongStair

  const t = Math.max(0, Math.min(stairLen, posAlongStair))

  if (t <= LANDING_DEPTH) return baseY + FLOOR_THICKNESS / 2
  if (t >= stairLen - LANDING_DEPTH)
    return baseY + totalRise + FLOOR_THICKNESS / 2

  const stairT = (t - LANDING_DEPTH) / (stairLen - LANDING_DEPTH * 2)
  return baseY + stairT * totalRise + FLOOR_THICKNESS / 2
}
