import { translate, type Locale, type MessageKey } from './index'

const names = new Map<string, MessageKey>([['Ysolde', 'npc.ysolde']])

export function npcDisplayName(name: string, language?: Locale): string {
  const key = names.get(name)
  return key ? translate(key, {}, language) : name
}
