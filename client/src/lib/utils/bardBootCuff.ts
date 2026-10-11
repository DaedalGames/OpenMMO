import { createBootCuff } from './bootCuff'
import cuff from '../data/bardBootCuff.json'

export const bardBootCuff = createBootCuff(cuff)
export const bardBootRim = bardBootCuff.rim
