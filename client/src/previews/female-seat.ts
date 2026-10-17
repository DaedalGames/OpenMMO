import { getObjectDef } from '../lib/data/objectCatalog'

export const femaleSeat = {
  seatCompression: 0.03,
  chair: getObjectDef('chair')!,
}

export const femaleSeatOffset = femaleSeat.chair.interactOffset?.y ?? 0
