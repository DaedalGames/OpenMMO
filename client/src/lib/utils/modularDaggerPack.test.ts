import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import * as THREE from 'three'
import { describe, expect, it, vi } from 'vitest'
import {
  applyCharacterArmor,
  disposeCharacterSkeletons,
  loadCharacterAnimationPack,
  loadCharacterModel,
} from './characterModel'
import { createCharacterModelRoot } from './characterAnimationUtils'
import { createDaggerComboClip } from './daggerSkillAnimation'
import { DAGGER_SKILL } from '../data/daggerSkill'
import { getWeaponAnimation } from '../data/weaponAnimationDefs'
import { PLAYER_ATTACK_IMPACT_DELAY_MS } from '../data/combatTiming'
import { loadWeaponAnimations } from './weaponAnimations'
import { poseMainHandProp } from './handProps'
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

const packPath = (directory: string) =>
  resolve('public', `${directory.slice(1)}/animations/${packFile}`)

describe('modular Double Slash packs', () => {
  for (const [name, modelPath, directory] of rigs) {
    const pack = packPath(directory)
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

describe('modular dagger stab', () => {
  for (const [name, modelPath, directory] of rigs) {
    it.skipIf(!existsSync(packPath(directory)))(
      `thrusts level at chest height and recovers on the ${name} rig`,
      async () => {
        const source = await loadCharacterModel(modelPath)
        const { modelRoot } = createCharacterModelRoot(source.scene)
        await applyCharacterArmor(modelRoot, {})
        const profile = getWeaponAnimation('worn_dagger')!
        expect(profile).toBe(getWeaponAnimation('dagger'))
        const clips = await loadWeaponAnimations(modelPath, modelRoot, profile)
        const stab = clips.get(profile.attack!)!
        const hand = modelRoot.getObjectByName('RightHand')!
        const prop = new THREE.Group()
        poseMainHandProp(prop, 'worn_dagger', undefined, modelPath)
        hand.add(prop)
        const mixer = new THREE.AnimationMixer(modelRoot)
        const action = mixer.clipAction(stab).setLoop(THREE.LoopOnce, 1)
        action.clampWhenFinished = true
        action.play()
        const sample = (seconds: number) => {
          mixer.setTime(seconds)
          modelRoot.updateMatrixWorld(true)
          return hand.getWorldPosition(new THREE.Vector3())
        }
        const start = sample(0)
        const impact = sample(PLAYER_ATTACK_IMPACT_DELAY_MS / 1000)
        const blade = new THREE.Vector3(1, 0, 0).applyQuaternion(
          prop.getWorldQuaternion(new THREE.Quaternion())
        )
        const shoulder = modelRoot
          .getObjectByName('RightArm')!
          .getWorldPosition(new THREE.Vector3())
        expect(blade.z).toBeGreaterThan(0.7)
        expect(Math.abs(blade.y)).toBeLessThan(0.25)
        expect(impact.y).toBeLessThan(shoulder.y)
        expect(impact.z - start.z).toBeGreaterThan(0.5)
        expect(sample(stab.duration).distanceTo(start)).toBeLessThan(0.05)
        mixer.stopAllAction()
        mixer.uncacheRoot(modelRoot)
        disposeCharacterSkeletons(modelRoot)
      },
      30000
    )
  }
})
