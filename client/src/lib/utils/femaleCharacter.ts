import * as THREE from 'three'
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js'
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { ArmorEquipment } from '../network/networkTypes'
import { loadGLB } from './gltfCache'
import { MODULAR_FEMALE_DIRECTORY } from './modelPaths'
import { bindModularPart, skinnedParts } from './modularCharacter'
import { femaleOutfitMask } from './female-outfit-mask'

const armorParts = ['top', 'bottom', 'boots', 'gloves', 'helmet'] as const
const parts = ['hair', ...armorParts] as const
// Baked tracks carry [bare, boots] values; this property picks one per character.
export const FEMALE_BOOTS_PROPERTY = 'femaleBoots'
// glTF allows one channel per node and path, so boots values ship as a companion animation.
export const FEMALE_BOOTS_CLIP_SUFFIX = `|${FEMALE_BOOTS_PROPERTY}`
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
  for (const [i, name] of parts.entries()) {
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
    ['base', ...parts].map((name) =>
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

/** Zips each clip's companion boots animation into `<node>.femaleBoots` [bare, boots] tracks. */
function pairFemaleClips(
  scene: THREE.Object3D,
  clips: THREE.AnimationClip[]
): THREE.AnimationClip[] {
  const variants = new Map(
    clips
      .filter((clip) => clip.name.endsWith(FEMALE_BOOTS_CLIP_SUFFIX))
      .map((clip) => [
        clip.name.slice(0, -FEMALE_BOOTS_CLIP_SUFFIX.length),
        clip,
      ])
  )
  return clips
    .filter((clip) => !clip.name.endsWith(FEMALE_BOOTS_CLIP_SUFFIX))
    .map((clip) => {
      const variant = variants.get(clip.name)
      if (!variant) throw new Error(`부츠 보정 동작이 없습니다: ${clip.name}`)
      const tracks = clip.tracks.slice()
      for (const boots of variant.tracks) {
        const index = tracks.findIndex((track) => track.name === boots.name)
        const bare = tracks[index]
        if (!bare || bare.times.length !== boots.times.length)
          throw new Error(`부츠 보정 트랙이 맞지 않습니다: ${boots.name}`)
        const [node] = boots.name.split('.')
        const size = boots.getValueSize()
        const rest =
          size === 4 ? scene.getObjectByName(node)!.quaternion.toArray() : []
        const values = new Float32Array(bare.values.length * 2)
        for (let i = 0; i < bare.times.length; i++) {
          for (let j = 0; j < size; j++) {
            values[i * size * 2 + j] = bare.values[i * size + j]
            values[i * size * 2 + size + j] = boots.values[i * size + j]
          }
          if (size !== 4) continue
          canonical(values, i * 8, rest)
          canonical(values, i * 8 + 4, rest)
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

type ArmorKey = Record<(typeof armorParts)[number], boolean>

interface FemaleState {
  mask: ReturnType<typeof femaleOutfitMask>
  refreshBoots: () => void
  equipped?: ArmorKey
}

const states = new WeakMap<THREE.Object3D, FemaleState>()

function femaleScene(root: THREE.Object3D) {
  return root.userData.female_parts
    ? root
    : root.children.find((child) => child.userData.female_parts)
}

// PropertyMixer skips unchanged values, so a boots toggle re-applies the last pair.
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
  const refreshes = targets.map(([node, target, size]) => {
    const pair = new Float32Array(size * 2)
    let ready = false
    const select = () => {
      if (!ready) return
      target.fromArray(pair, state.equipped?.boots ? size : 0)
      if (target instanceof THREE.Quaternion) target.normalize()
    }
    Object.assign(node, {
      [FEMALE_BOOTS_PROPERTY]: {
        fromArray(array: ArrayLike<number>, offset: number) {
          for (let i = 0; i < pair.length; i++) pair[i] = array[offset + i]
          ready = true
          select()
        },
        toArray(array: number[], offset: number) {
          target.toArray(array, offset)
          target.toArray(array, offset + size)
          return array
        },
      },
    })
    return select
  })
  return () => refreshes.forEach((refresh) => refresh())
}

export function applyFemaleArmor(
  root: THREE.Object3D,
  armor?: ArmorEquipment
): boolean {
  const scene = femaleScene(root)
  if (!scene) return false
  // Plate is the only female outfit so far, so any armor in a slot shows it.
  const equipped: ArmorKey = {
    top: !!armor?.chest,
    bottom: !!armor?.pants,
    boots: !!armor?.boots,
    gloves: !!armor?.hands,
    helmet: !!armor?.head,
  }
  let state = states.get(scene)
  if (
    state?.equipped &&
    armorParts.every((name) => state!.equipped![name] === equipped[name])
  )
    return true
  const meshes = skinnedParts(scene)
  const part = (name: string) =>
    meshes.filter((mesh) => mesh.userData.female_part === name)
  if (!state) {
    const { female_parts } = scene.userData
    const body = meshes.find((mesh) => mesh.userData.female_body)!
    const mask = femaleOutfitMask()
    for (const name of armorParts)
      mask.register(name, female_parts[name].body_mask, body)
    mask.register('sleeves', female_parts.gloves.sleeve_mask, part('top')[0])
    state = { mask, refreshBoots: () => {} }
    state.refreshBoots = installBootsSwitch(scene, state)
    states.set(scene, state)
  }
  for (const mesh of part('hair')) mesh.visible = !equipped.helmet
  for (const name of armorParts)
    for (const mesh of part(name)) mesh.visible = equipped[name]
  state.mask.setEquippedAll({
    ...equipped,
    sleeves: equipped.top && equipped.gloves,
  })
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
