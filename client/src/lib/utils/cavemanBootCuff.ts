import { createBootCuff } from './bootCuff'
import cuff from '../data/cavemanBootCuff.json'

export const cavemanBootCuff = createBootCuff(cuff)
export const cavemanBootRim = cavemanBootCuff.rim
