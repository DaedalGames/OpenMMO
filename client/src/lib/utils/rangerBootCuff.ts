import { createBootCuff } from './bootCuff'
import cuff from '../data/rangerBootCuff.json'

export const rangerBootCuff = createBootCuff(cuff)
export const rangerBootRim = rangerBootCuff.rim
