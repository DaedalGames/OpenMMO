import * as THREE from 'three'
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js'
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { ArmorEquipment } from '../network/networkTypes'
import { getItemDef } from '../data/itemDefs'
import { loadGLB } from './gltfCache'
import { MODULAR_FEMALE_DIRECTORY } from './modelPaths'
import { bindModularPart, skinnedParts } from './modularCharacter'
import { femaleOutfitMask } from './female-outfit-mask'

const slots = ['top', 'bottom', 'boots', 'gloves', 'helmet'] as const
type Slot = (typeof slots)[number]
type Style = 'plate' | 'barbarian'
const prefixes: Record<Style, string> = { plate: '', barbarian: 'barbarian_' }
const styles = Object.keys(prefixes) as Style[]
const partName = (style: Style, slot: Slot | 'hair') =>
  `${prefixes[style]}${slot}`
export const FEMALE_PARTS = styles.flatMap((style) =>
  (['hair', ...slots] as const).map((slot) => partName(style, slot))
)
/** Boots parts in the order their baked variants follow the bare value. */
export const FEMALE_BOOTS_PARTS = styles.map((style) =>
  partName(style, 'boots')
)
// Baked tracks carry [bare, ...boots] values; this property picks one per character.
export const FEMALE_BOOTS_PROPERTY = 'femaleBoots'
// glTF allows one channel per node and path, so boots values ship as companion animations.
export const femaleBootsClipName = (clip: string, boots: string) =>
  `${clip}|${FEMALE_BOOTS_PROPERTY}:${boots}`
let model: Promise<GLTF> | undefined
const packs = new Map<string, Promise<GLTF>>()

export function assembleFemaleCharacter(
  base: GLTF,
  sources: GLTF[]
): THREE.Group {
  const scene = clone(base.scene) as THREE.Group
  base.scene.traverse((node) => {
    const association = base.parser.associations.get(node)
    if (
      node instanceof THREE.SkinnedMesh &&
      association?.meshes === 0 &&
      association.primitives === 0
    )
      scene.getObjectByName(node.name)!.userData.female_body = true
  })
  scene.userData.modular_character = true
  scene.userData.female_parts = {}
  for (const [i, name] of FEMALE_PARTS.entries()) {
    scene.userData.female_parts[name] = sources[i].scene.userData
    for (const mesh of bindModularPart(scene, sources[i].scene)) {
      mesh.userData.female_part = name
      mesh.visible = name === 'hair'
    }
  }
  for (const mesh of skinnedParts(scene)) mesh.frustumCulled = false
  scene.userData.female_grip = Object.fromEntries(
    base.animations
      .find((clip) => clip.name === 'idle_armed')!
      .tracks.filter((track) =>
        /^RightHand(Thumb|Index|Middle|Ring|Pinky)[123]\.quaternion$/.test(
          track.name
        )
      )
      .map((track) => [
        track.name.split('.')[0],
        Array.from(track.values.slice(0, 4)),
      ])
  )
  return scene
}

export function loadFemaleCharacter(): Promise<GLTF> {
  return (model ??= Promise.all(
    ['base', ...FEMALE_PARTS].map((name) =>
      loadGLB(`${MODULAR_FEMALE_DIRECTORY}/${name}.glb`)
    )
  )
    .then(([base, ...sources]) => {
      const scene = assembleFemaleCharacter(base, sources)
      const animations = pairFemaleClips(scene, base.animations)
      return { ...base, scene, scenes: [scene], animations }
    })
    .catch((error) => {
      model = undefined
      throw error
    }))
}

export function loadFemaleAnimationPack(path: string): Promise<GLTF> {
  let pending = packs.get(path)
  if (!pending) {
    pending = Promise.all([loadFemaleCharacter(), loadGLB(path)])
      .then(([{ scene }, pack]) => ({
        ...pack,
        animations: pairFemaleClips(scene, pack.animations),
      }))
      .catch((error) => {
        packs.delete(path)
        throw error
      })
    packs.set(path, pending)
  }
  return pending
}

function canonical(values: Float32Array, offset: number, rest: number[]) {
  let dot = 0
  for (let i = 0; i < 4; i++) dot += values[offset + i] * rest[i]
  if (dot < 0) for (let i = 0; i < 4; i++) values[offset + i] *= -1
}

/** Zips each clip's companion boots animations into `<node>.femaleBoots` [bare, ...boots] tracks. */
function pairFemaleClips(
  scene: THREE.Object3D,
  clips: THREE.AnimationClip[]
): THREE.AnimationClip[] {
  const byName = new Map(clips.map((clip) => [clip.name, clip]))
  const companions = new Set(
    clips.flatMap((clip) =>
      FEMALE_BOOTS_PARTS.map((boots) => femaleBootsClipName(clip.name, boots))
    )
  )
  const width = FEMALE_BOOTS_PARTS.length + 1
  return clips
    .filter((clip) => !companions.has(clip.name))
    .map((clip) => {
      const variants = FEMALE_BOOTS_PARTS.map((boots) => {
        const variant = byName.get(femaleBootsClipName(clip.name, boots))
        if (!variant) throw new Error(`부츠 보정 동작이 없습니다: ${clip.name}`)
        return variant
      })
      const tracks = clip.tracks.slice()
      for (const { name } of variants[0].tracks) {
        const index = tracks.findIndex((track) => track.name === name)
        const bare = tracks[index]
        const sources = variants.map((variant) =>
          variant.tracks.find((track) => track.name === name)
        )
        if (
          !bare ||
          sources.some((track) => track?.times.length !== bare.times.length)
        )
          throw new Error(`부츠 보정 트랙이 맞지 않습니다: ${name}`)
        const [node] = name.split('.')
        const size = bare.getValueSize()
        const rest =
          size === 4 ? scene.getObjectByName(node)!.quaternion.toArray() : []
        const values = new Float32Array(bare.values.length * width)
        for (let i = 0; i < bare.times.length; i++) {
          for (const [v, track] of [bare, ...sources].entries()) {
            const offset = (i * width + v) * size
            for (let j = 0; j < size; j++)
              values[offset + j] = track!.values[i * size + j]
            if (size === 4) canonical(values, offset, rest)
          }
        }
        tracks[index] = new THREE.KeyframeTrack(
          `${node}.${FEMALE_BOOTS_PROPERTY}`,
          bare.times,
          values
        )
      }
      return new THREE.AnimationClip(
        clip.name,
        clip.duration,
        tracks,
        clip.blendMode
      )
    })
}

type Outfit = Record<Slot, Style | null>

interface FemaleState {
  mask: ReturnType<typeof femaleOutfitMask>
  refreshBoots: () => void
  equipped?: Outfit
}

const states = new WeakMap<THREE.Object3D, FemaleState>()

function femaleScene(root: THREE.Object3D) {
  return root.userData.female_parts
    ? root
    : root.children.find((child) => child.userData.female_parts)
}

// PropertyMixer skips unchanged values, so a boots toggle re-applies the last values.
function installBootsSwitch(scene: THREE.Object3D, state: FemaleState) {
  const offsets = scene.userData.female_parts.boots.heel_pose
    .local_quaternion_offsets as Record<string, number[]>
  const targets: [THREE.Object3D, THREE.Vector3 | THREE.Quaternion, number][] =
    Object.keys(offsets).map((name) => {
      const bone = scene.getObjectByName(name)!
      return [bone, bone.quaternion, 4]
    })
  const hips = scene.getObjectByName('Hips')!
  targets.push([hips, hips.position, 3])
  const width = FEMALE_BOOTS_PARTS.length + 1
  const refreshes = targets.map(([node, target, size]) => {
    const values = new Float32Array(size * width)
    let ready = false
    const select = () => {
      if (!ready) return
      const boots = state.equipped?.boots
      const variant = boots ? styles.indexOf(boots) + 1 : 0
      target.fromArray(values, variant * size)
      if (target instanceof THREE.Quaternion) target.normalize()
    }
    Object.assign(node, {
      [FEMALE_BOOTS_PROPERTY]: {
        fromArray(array: ArrayLike<number>, offset: number) {
          for (let i = 0; i < values.length; i++) values[i] = array[offset + i]
          ready = true
          select()
        },
        toArray(array: number[], offset: number) {
          for (let v = 0; v < width; v++)
            target.toArray(array, offset + v * size)
          return array
        },
      },
    })
    return select
  })
  return () => refreshes.forEach((refresh) => refresh())
}

const femaleStyle = (itemId: string | null | undefined): Style | null => {
  if (!itemId) return null
  const item = getItemDef(itemId)
  return item?.material === 'leather' ||
    item?.worldModel?.startsWith('armor/barbarian_')
    ? 'barbarian'
    : 'plate'
}

export function applyFemaleArmor(
  root: THREE.Object3D,
  armor?: ArmorEquipment
): boolean {
  const scene = femaleScene(root)
  if (!scene) return false
  const equipped: Outfit = {
    top: femaleStyle(armor?.chest),
    bottom: femaleStyle(armor?.pants),
    boots: femaleStyle(armor?.boots),
    gloves: femaleStyle(armor?.hands),
    helmet: femaleStyle(armor?.head),
  }
  let state = states.get(scene)
  if (
    state?.equipped &&
    slots.every((slot) => state!.equipped![slot] === equipped[slot])
  )
    return true
  const meshes = skinnedParts(scene)
  const part = (name: string) =>
    meshes.filter((mesh) => mesh.userData.female_part === name)
  if (!state) {
    const { female_parts } = scene.userData
    const body = meshes.find((mesh) => mesh.userData.female_body)!
    const mask = femaleOutfitMask()
    for (const style of styles)
      for (const slot of slots) {
        const name = partName(style, slot)
        mask.register(name, female_parts[name].body_mask, body)
      }
    mask.register('sleeves', female_parts.gloves.sleeve_mask, part('top')[0])
    state = { mask, refreshBoots: () => {} }
    state.refreshBoots = installBootsSwitch(scene, state)
    states.set(scene, state)
  }
  const hair =
    equipped.helmet === 'plate'
      ? null
      : partName(equipped.helmet ?? 'plate', 'hair')
  for (const style of styles) {
    const name = partName(style, 'hair')
    for (const mesh of part(name)) mesh.visible = name === hair
  }
  const shown: Record<string, boolean> = {
    sleeves: equipped.top === 'plate' && equipped.gloves === 'plate',
  }
  for (const style of styles)
    for (const slot of slots) {
      const name = partName(style, slot)
      shown[name] = equipped[slot] === style
      for (const mesh of part(name)) mesh.visible = shown[name]
    }
  state.mask.setEquippedAll(shown)
  const bootsChanged = state.equipped?.boots !== equipped.boots
  state.equipped = equipped
  if (bootsChanged) state.refreshBoots()
  return true
}

export function disposeFemaleCharacter(root: THREE.Object3D) {
  const scene = femaleScene(root)
  if (!scene) return
  states.get(scene)?.mask.dispose()
  states.delete(scene)
}
