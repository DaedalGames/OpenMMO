import { createBootCuff } from './bootCuff'
import cuff from '../data/priestBootCuff.json'

export const priestBootCuff = createBootCuff(cuff)
export const priestBootRim = priestBootCuff.rim
