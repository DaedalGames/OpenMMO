import { getObjectDef } from '../../data/objectCatalog'
import { objectManager } from '../../managers/objectManager'
import { housingManager } from '../../managers/housingManager'
import { roomContainsXZ } from '../../managers/housing-queries'
import type { TerrainHeightManager } from '../../managers/terrainHeightManager'
import type { TerrainGrassDataManager } from '../../managers/terrainGrassDataManager'
import type { ObjectPlacement } from '../../stores/editorStore'
import { rotatedRectAabb } from '../../utils/objectFootprint'

type Placement = Pick<
  ObjectPlacement,
  'type' | 'x' | 'z' | 'rotation' | 'floorLevel'
>

export function foundationHeight(
  placement: Placement,
  heights: Pick<TerrainHeightManager, 'getHeightAtWorldPosition'>
): number | null {
  const foundation = getObjectDef(placement.type)?.foundation
  if (!foundation || (placement.floorLevel ?? 0) !== 0) return null
  const nx = Math.ceil(foundation.width)
  const nz = Math.ceil(foundation.depth)
  const yaw = (placement.rotation * Math.PI) / 180
  const cos = Math.cos(yaw)
  const sin = Math.sin(yaw)
  let sum = 0
  for (let j = 0; j < nz; j++) {
    for (let i = 0; i < nx; i++) {
      const x = ((i + 0.5) / nx - 0.5) * foundation.width
      const z = ((j + 0.5) / nz - 0.5) * foundation.depth
      sum += heights.getHeightAtWorldPosition(
        placement.x + x * cos + z * sin,
        placement.z - x * sin + z * cos
      )
    }
  }
  return sum / (nx * nz)
}

export async function flattenObjectTerrain(
  placement: ObjectPlacement,
  heights: TerrainHeightManager,
  grass: TerrainGrassDataManager | null
): Promise<void> {
  const footprint = await objectManager.fetchFootprint(placement.type)
  if (!footprint || footprint.rects.length === 0) return
  const target =
    placement.y +
    footprint.minLocalY +
    (getObjectDef(placement.type)?.flattenBuryDepth ?? 0)
  const houses = housingManager.getAllHouses()
  const protectedGround = (x: number, z: number) =>
    houses.some((house) =>
      house.rooms.some(
        (room) =>
          room.floorLevel === 0 &&
          room.roomType !== 'stairwell' &&
          roomContainsXZ(house, room, x, z)
      )
    )
  for (const rect of footprint.rects) {
    heights.flattenRotatedRect(
      placement.x,
      placement.z,
      placement.rotation,
      rect.minX,
      rect.maxX,
      rect.minZ,
      rect.maxZ,
      target,
      2,
      protectedGround
    )
  }
  await heights.saveAllDirty()
  const yaw = (placement.rotation * Math.PI) / 180
  await grass?.removeGrassInRects(
    footprint.rects.map((rect) => {
      const world = rotatedRectAabb(
        rect.minX,
        rect.maxX,
        rect.minZ,
        rect.maxZ,
        yaw
      )
      return {
        minX: placement.x + world.minX,
        maxX: placement.x + world.maxX,
        minZ: placement.z + world.minZ,
        maxZ: placement.z + world.maxZ,
      }
    })
  )
}
