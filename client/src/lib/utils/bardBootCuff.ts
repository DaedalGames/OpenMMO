import { createBootCuff } from './bootCuff'
import cuff from '../data/bardBootCuff.json'

export const {
  rim: bardBootRim,
  distance: bardPantsBootDistance,
  tuck: tuckPantsIntoBardBoots,
} = createBootCuff(cuff)
