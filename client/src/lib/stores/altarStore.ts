import { writable } from 'svelte/store'

export interface AltarOffering {
  objectId: number
  offering: string
  monster: string
}

/** Set by a `Ready` AltarStatus; the HUD shows the confirm dialog. */
export const altarOffering = writable<AltarOffering | null>(null)
