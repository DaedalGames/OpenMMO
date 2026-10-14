import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'
import {
  loadCharacterAnimationPack,
  loadCharacterModel,
} from './characterModel'
import { createCharacterModelRoot } from './characterAnimationUtils'
import { createDaggerComboClip } from './daggerSkillAnimation'
import { DAGGER_SKILL } from '../data/daggerSkill'
import {
  MODULAR_FEMALE_DIRECTORY,
  MODULAR_FEMALE_MODEL_PATH,
  MODULAR_MALE_DIRECTORY,
  MODULAR_MALE_MODEL_PATH,
} from './modelPaths'

vi.mock('./gltfCache', async (importOriginal) => {
  const original = await importOriginal<typeof import('./gltfCache')>()
  return {
    ...original,
    loadGLB: vi.fn(async (path: string) => {
      const { loadHeadlessGlb } = await import('./headless-glb.fixture')
      return loadHeadlessGlb(path.slice(1))
    }),
  }
})

const packFile = DAGGER_SKILL.pack.split('/').pop()
const rigs = [
  ['male', MODULAR_MALE_MODEL_PATH, MODULAR_MALE_DIRECTORY],
  ['female', MODULAR_FEMALE_MODEL_PATH, MODULAR_FEMALE_DIRECTORY],
] as const

describe('modular Double Slash packs', () => {
  for (const [name, modelPath, directory] of rigs) {
    const pack = resolve(
      'public',
      `${directory.slice(1)}/animations/${packFile}`
    )
    it.skipIf(!existsSync(pack))(
      `loads dagger_inward and dagger_outward on the ${name} rig`,
      async () => {
        const source = await loadCharacterModel(modelPath)
        const { modelRoot } = createCharacterModelRoot(source.scene)
        const { animations } = await loadCharacterAnimationPack(
          modelPath,
          `/models/${DAGGER_SKILL.pack}`
        )
        const clips = new Map(animations.map((clip) => [clip.name, clip]))
        const inward = clips.get('dagger_inward')!
        const outward = clips.get('dagger_outward')!
        expect(inward.duration).toBeCloseTo(53 / 24, 3)
        expect(outward.duration).toBeCloseTo(49 / 24, 3)
        for (const clip of [inward, outward]) {
          expect(clip.validate()).toBe(true)
          for (const track of clip.tracks)
            expect(
              modelRoot.getObjectByName(track.name.split('.')[0]),
              track.name
            ).toBeDefined()
        }
        const combo = createDaggerComboClip(inward, outward)
        expect(combo.validate()).toBe(true)
        expect(combo.duration).toBeCloseTo(DAGGER_SKILL.duration, 6)
      },
      30000
    )
  }
})
