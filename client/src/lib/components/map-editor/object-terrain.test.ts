import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { get } from 'svelte/store'
import { TerrainHeightManager } from '../../managers/terrainHeightManager'
import { objectManager } from '../../managers/objectManager'
import { housingManager } from '../../managers/housingManager'
import { furnitureManager } from '../../managers/furnitureManager'
import {
  encodeHeight,
  VERTS_PER_SIDE,
} from '../../managers/terrain-height-types'
import type { TerrainGrassDataManager } from '../../managers/terrainGrassDataManager'
import {
  currentEditorRegion,
  currentObjectData,
  selectedObjectPlacementId,
  editorHeightManager,
  editorGrassDataManager,
  type ObjectPlacement,
} from '../../stores/editorStore'
import { makeRoom } from '../../utils/house-room.fixture'
import { foundationHeight, flattenObjectTerrain } from './object-terrain'
import { duplicateSelectedPlacement, placeObject } from './object-edit'

const tent: ObjectPlacement = {
  id: 1,
  type: 'ysolde_tent',
  x: 0.25,
  y: 99,
  z: -0.3,
  rotation: 0,
  floorLevel: 0,
}

describe('tent terrain foundation', () => {
  let heights: TerrainHeightManager
  const removeGrassInRects = vi.fn().mockResolvedValue(undefined)
  const grass = { removeGrassInRects } as unknown as TerrainGrassDataManager

  beforeEach(() => {
    vi.useFakeTimers()
    heights = new TerrainHeightManager()
    const map = new Uint16Array(VERTS_PER_SIDE ** 2).fill(encodeHeight(6))
    map[32 * VERTS_PER_SIDE + 32] = encodeHeight(10)
    heights.setHeightmap(0, 0, map)
    vi.spyOn(heights, 'ensureOriginalHeightmap').mockImplementation(() => {})
    vi.spyOn(heights, 'saveAllDirty').mockResolvedValue(undefined)
    vi.spyOn(objectManager, 'saveObject').mockResolvedValue(true)
    vi.spyOn(housingManager, 'getAllHouses').mockReturnValue([])
    vi.spyOn(furnitureManager, 'isSolid').mockReturnValue(false)
    currentEditorRegion.set({ rx: 0, rz: 0 })
    currentObjectData.set({ placements: [] })
    selectedObjectPlacementId.set(null)
    editorHeightManager.set(heights)
    editorGrassDataManager.set(grass)
    removeGrassInRects.mockClear()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.restoreAllMocks()
    currentObjectData.set({ placements: [] })
    currentEditorRegion.set(null)
    selectedObjectPlacementId.set(null)
    editorHeightManager.set(null)
    editorGrassDataManager.set(null)
  })

  it('averages the rotated support area for the placement preview', () => {
    const terrain = { getHeightAtWorldPosition: (x: number) => x * x }
    expect(foundationHeight({ ...tent, x: 0, z: 0 }, terrain)).toBeCloseTo(
      1.5488
    )
    expect(
      foundationHeight({ ...tent, x: 0, z: 0, rotation: 90 }, terrain)
    ).toBeCloseTo(1.8432)
  })

  it.each([0, 90, 180, 270, 45])(
    'levels the floor and stake sites at yaw %s',
    async (rotation) => {
      await placeObject({ ...tent, rotation }, heights, grass)
      const placed = get(currentObjectData).placements[0]
      expect(placed.y).toBeGreaterThan(6)
      expect(placed.y).toBeLessThan(7)
      expect(objectManager.saveObject).toHaveBeenCalledWith(0, 0, {
        placements: [placed],
      })
      const yaw = (rotation * Math.PI) / 180
      for (const x of [-2.06, 0, 2.06]) {
        for (const z of [-2.23, 0, 2.23]) {
          const ground = heights.getHeightAtWorldPosition(
            tent.x + x * Math.cos(yaw) + z * Math.sin(yaw),
            tent.z - x * Math.sin(yaw) + z * Math.cos(yaw)
          )
          expect(Math.abs(ground - placed.y)).toBeLessThanOrEqual(0.026)
        }
      }
      expect(heights.getHeightAtWorldPosition(12, 12)).toBe(6)
      expect(heights.saveAllDirty).toHaveBeenCalledOnce()
      expect(removeGrassInRects).toHaveBeenCalledOnce()
      expect(removeGrassInRects.mock.calls[0][0][0]).toMatchObject({
        minX: expect.any(Number),
        maxX: expect.any(Number),
        minZ: expect.any(Number),
        maxZ: expect.any(Number),
      })
      expect(
        vi.mocked(objectManager.saveObject).mock.invocationCallOrder[0]
      ).toBeLessThan(
        vi.mocked(heights.saveAllDirty).mock.invocationCallOrder[0]
      )
    }
  )

  it('keeps the terrain unchanged when saving the placement fails', async () => {
    vi.mocked(objectManager.saveObject).mockResolvedValue(false)
    await placeObject(tent, heights, grass)
    expect(heights.getHeightAtWorldPosition(0, 0)).toBe(10)
    expect(heights.saveAllDirty).not.toHaveBeenCalled()
    expect(removeGrassInRects).not.toHaveBeenCalled()
  })

  it.each([
    { ...tent, floorLevel: 1 },
    { ...tent, type: 'bed' },
  ])(
    'preserves ordinary props and upper-floor placement heights',
    async (placement) => {
      await placeObject(placement, heights, grass)
      expect(get(currentObjectData).placements[0].y).toBe(99)
      expect(heights.saveAllDirty).not.toHaveBeenCalled()
      expect(removeGrassInRects).not.toHaveBeenCalled()
    }
  )

  it('levels an existing tent to its base rather than the buried stake tips', async () => {
    await flattenObjectTerrain({ ...tent, y: 8 }, heights, grass)
    expect(heights.getHeightAtWorldPosition(0, 0)).toBe(8)
    expect(heights.getHeightAtWorldPosition(2, 2)).toBe(8)
  })

  it('also prepares terrain when duplicating a tent', async () => {
    currentObjectData.set({ placements: [tent] })
    selectedObjectPlacementId.set(tent.id)
    await duplicateSelectedPlacement()
    const placements = get(currentObjectData).placements
    expect(placements[0]).toEqual(tent)
    expect(placements[1]).toMatchObject({ id: 2, x: 0.75, z: 0.2 })
    expect(placements[1].y).toBeLessThan(7)
    expect(heights.saveAllDirty).toHaveBeenCalledOnce()
  })

  it('protects existing ground-floor rooms in the blend area', async () => {
    vi.mocked(housingManager.getAllHouses).mockReturnValue([
      {
        id: 'neighbor',
        ownerId: 'local',
        origin: { x: 4, y: 6, z: -1 },
        rooms: [makeRoom({ sizeX: 2, sizeZ: 2 })],
      },
    ])
    await flattenObjectTerrain({ ...tent, y: 8 }, heights, grass)
    expect(heights.getHeightAtWorldPosition(4, 0)).toBe(6)
    expect(heights.getHeightAtWorldPosition(3, 0)).toBeGreaterThan(6)
  })
})
