import * as THREE from 'three'
import { describe, expect, it, vi } from 'vitest'
import {
  loadCharacterModel,
  applyCharacterArmor,
  disposeCharacterSkeletons,
  loadCharacterAnimationPack,
} from './characterModel'
import { createCharacterModelRoot } from './characterAnimationUtils'
import {
  MODULAR_FEMALE_DIRECTORY,
  MODULAR_FEMALE_MODEL_PATH,
  getCharacterModelPath,
  CHARACTER_ANIMATION_PACK_PATHS,
} from './modelPaths'
import { skinnedParts } from './modularCharacter'
import { FEMALE_BOOTS_PROPERTY } from './femaleCharacter'
import { poseMainHandProp } from './handProps'

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
const armor = {
  head: 'worn_plate_helmet',
  chest: 'worn_breastplate',
  pants: 'worn_plate_greaves',
  boots: 'worn_plate_boots',
  hands: 'worn_plate_gauntlets',
}
const count = (root: THREE.Object3D, part?: string) =>
  skinnedParts(root)
    .filter(
      (m) =>
        m.visible && (part === undefined || m.userData.female_part === part)
    )
    .reduce((sum, m) => sum + m.geometry.index!.count / 3, 0)

describe('female knight starter outfit', () => {
  it('stores game dimensions in the rig and keeps attached props at unit scale', async () => {
    const source = await loadCharacterModel(MODULAR_FEMALE_MODEL_PATH)
    const { modelRoot } = createCharacterModelRoot(source.scene)
    modelRoot.traverse((node) => {
      for (const value of node.scale.toArray()) expect(value).toBeCloseTo(1, 6)
    })
    const body = skinnedParts(modelRoot).find((m) => m.userData.female_body)!
    body.geometry.computeBoundingBox()
    const height = body.geometry.boundingBox!.getSize(new THREE.Vector3()).y
    expect(height).toBeGreaterThan(1.7)
    expect(height).toBeLessThan(1.9)
    const prop = new THREE.Group()
    poseMainHandProp(
      prop,
      'worn_iron_sword',
      undefined,
      MODULAR_FEMALE_MODEL_PATH
    )
    modelRoot.getObjectByName('RightHand')!.add(prop)
    const scale = prop.getWorldScale(new THREE.Vector3())
    for (const value of scale.toArray()) expect(value).toBeCloseTo(1, 6)
    disposeCharacterSkeletons(modelRoot)
  })
  it('uses the modular female player while keeping NPCs and other classes unchanged', () => {
    expect(getCharacterModelPath('knight', 'female')).toBe(
      MODULAR_FEMALE_MODEL_PATH
    )
    expect(getCharacterModelPath('knight', 'female', true)).toBe(
      '/models/characters/female_knight.glb'
    )
    expect(getCharacterModelPath('rogue', 'female')).toBe(
      '/models/characters/female_rogue.glb'
    )
  })
  it('equips all five parts, restores hair and sleeves, and isolates character masks', async () => {
    const source = await loadCharacterModel(MODULAR_FEMALE_MODEL_PATH)
    const { modelRoot: first } = createCharacterModelRoot(source.scene)
    const { modelRoot: second } = createCharacterModelRoot(source.scene)
    const original = count(second)
    await applyCharacterArmor(first, armor)
    expect(count(first, 'helmet')).toBe(2166)
    expect(count(first, 'hair')).toBe(0)
    expect(count(first)).toBe(51538)
    expect(count(second)).toBe(original)
    const covered = count(first, 'top')
    await applyCharacterArmor(first, { ...armor, head: null, hands: null })
    expect(count(first, 'hair')).toBeGreaterThan(0)
    expect(count(first, 'helmet')).toBe(0)
    expect(count(first, 'gloves')).toBe(0)
    expect(count(first, 'top')).toBe(covered + 720)
    await applyCharacterArmor(first, {})
    expect(count(first)).toBe(original)
    disposeCharacterSkeletons(first)
    disposeCharacterSkeletons(second)
  })
  it('shows plate for non-plate armor until other female outfits exist', async () => {
    const source = await loadCharacterModel(MODULAR_FEMALE_MODEL_PATH)
    const { modelRoot: plate } = createCharacterModelRoot(source.scene)
    const { modelRoot: leather } = createCharacterModelRoot(source.scene)
    await applyCharacterArmor(plate, armor)
    await applyCharacterArmor(leather, {
      head: 'leather_helmet',
      chest: 'worn_rogue_top',
      pants: 'leather_pants',
      boots: 'leather_boots',
      hands: 'leather_gloves',
    })
    expect(count(leather)).toBe(count(plate))
    disposeCharacterSkeletons(plate)
    disposeCharacterSkeletons(leather)
  })
  it('plays baked runtime motions with a rigid helmet and finite boot correction', async () => {
    const source = await loadCharacterModel(MODULAR_FEMALE_MODEL_PATH)
    const { modelRoot } = createCharacterModelRoot(source.scene)
    await applyCharacterArmor(modelRoot, armor)
    const mixer = new THREE.AnimationMixer(modelRoot)
    const helmet = skinnedParts(modelRoot).find(
      (m) => m.userData.female_part === 'helmet'
    )!
    const hips = modelRoot.getObjectByName('Hips')!
    const a = new THREE.Vector3(),
      b = new THREE.Vector3()
    let length: number | undefined
    for (const path of Object.values(CHARACTER_ANIMATION_PACK_PATHS)) {
      const pack = await loadCharacterAnimationPack(
        MODULAR_FEMALE_MODEL_PATH,
        path
      )
      expect(pack.animations.length).toBeGreaterThan(0)
      for (const clip of pack.animations) {
        mixer.stopAllAction()
        mixer.clipAction(clip).play()
        const lift = clip.tracks.find(
          (track) => track.name === `Hips.${FEMALE_BOOTS_PROPERTY}`
        )!
        for (const time of [0, clip.duration / 2, clip.duration * 0.99]) {
          mixer.setTime(time)
          modelRoot.updateMatrixWorld(true)
          const handScale = modelRoot
            .getObjectByName('RightHand')!
            .getWorldScale(new THREE.Vector3())
          for (const value of handScale.toArray())
            expect(value).toBeCloseTo(1, 5)
          helmet.getVertexPosition(0, a)
          helmet.getVertexPosition(20, b)
          expect(a.toArray().every(Number.isFinite)).toBe(true)
          length ??= a.distanceTo(b)
          expect(a.distanceTo(b)).toBeCloseTo(length, 5)
          expect(hips.quaternion.length()).toBeCloseTo(1, 5)
        }
        for (let i = 0; i < lift.values.length; i += 6) {
          const boots = lift.values[i + 4] - lift.values[i + 1]
          expect(boots).toBeGreaterThanOrEqual(-1e-6)
          expect(boots).toBeLessThan(0.2)
        }
      }
    }
    mixer.stopAllAction()
    disposeCharacterSkeletons(modelRoot)
  }, 30000)
  it('bakes heel pose, ground lift and sword grip into clips, switched by boots', async () => {
    const source = await loadCharacterModel(MODULAR_FEMALE_MODEL_PATH)
    const { modelRoot } = createCharacterModelRoot(source.scene)
    await applyCharacterArmor(modelRoot, armor)
    const { heel_pose } = source.scene.userData.female_parts.boots
    const pack = await loadCharacterAnimationPack(
      MODULAR_FEMALE_MODEL_PATH,
      CHARACTER_ANIMATION_PACK_PATHS.locomotion
    )
    const { loadHeadlessGlb } = await import('./headless-glb.fixture')
    const raw = (
      await loadHeadlessGlb(
        `${MODULAR_FEMALE_DIRECTORY.slice(1)}/animations/locomotion.glb`
      )
    ).animations.find((clip) => clip.name === 'walk')!
    const walk = pack.animations.find((clip) => clip.name === 'walk')!
    const track = (clip: THREE.AnimationClip, name: string) =>
      clip.tracks.find((track) => track.name === name)!
    const offset = new THREE.Quaternion().fromArray(
      heel_pose.local_quaternion_offsets.LeftFoot
    )
    const foot = track(walk, `LeftFoot.${FEMALE_BOOTS_PROPERTY}`).values
    const bare = track(raw, 'LeftFoot.quaternion').values
    const q = new THREE.Quaternion()
    for (const i of [0, 10, 40]) {
      const expected = q.fromArray(bare, i * 4)
      const angle = (start: number) =>
        new THREE.Quaternion()
          .fromArray(foot, i * 8 + start)
          .angleTo(start ? expected.clone().multiply(offset) : expected)
      expect(angle(0)).toBeLessThan(1e-3)
      expect(angle(4)).toBeLessThan(1e-3)
    }
    for (const [bone, quaternion] of Object.entries(
      source.scene.userData.female_grip as Record<string, number[]>
    ))
      expect(Array.from(track(walk, `${bone}.quaternion`).values)).toEqual([
        ...quaternion,
        ...quaternion,
      ])

    const mixer = new THREE.AnimationMixer(modelRoot)
    mixer.clipAction(walk).play()
    const scene = modelRoot.children[0]
    const body = skinnedParts(modelRoot).find((m) => m.userData.female_body)!
    const soles = skinnedParts(modelRoot).filter(
      (m) => m.userData.female_part === 'boots'
    )
    const lowest = (meshes: THREE.SkinnedMesh[]) => {
      let y = Infinity
      const point = new THREE.Vector3()
      for (const mesh of meshes)
        for (let i = 0; i < mesh.geometry.attributes.position.count; i++)
          y = Math.min(y, mesh.getVertexPosition(i, point).y)
      return y
    }
    for (const time of [0, walk.duration / 3, (walk.duration * 2) / 3]) {
      await applyCharacterArmor(modelRoot, { ...armor, boots: null })
      mixer.setTime(time)
      modelRoot.updateMatrixWorld(true)
      const floor = lowest([body])
      const expected = new THREE.Quaternion().fromArray(
        track(raw, 'LeftFoot.quaternion').createInterpolant().evaluate(time)
      )
      expect(
        modelRoot.getObjectByName('LeftFoot')!.quaternion.angleTo(expected)
      ).toBeLessThan(1e-3)
      await applyCharacterArmor(modelRoot, armor)
      mixer.setTime(time)
      modelRoot.updateMatrixWorld(true)
      expect(Math.abs(lowest(soles) - floor)).toBeLessThan(0.01)
      expect(scene.position.y).toBe(0)
    }
    mixer.stopAllAction()
    disposeCharacterSkeletons(modelRoot)
  }, 30000)
})
