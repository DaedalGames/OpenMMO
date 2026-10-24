import * as THREE from 'three'

export const EXCAVATION_CLIP_PATH = '/models/animations/ysolde_excavation.glb'
export const EXCAVATION_TOOL_PATH = '/models/props/excavation_trowel.glb'

export function poseExcavationTool(prop: THREE.Object3D): void {
  prop.name = 'ysolde_excavation_trowel'
  prop.position.set(0, 0.1, 0.03)
  prop.rotation.set(Math.PI / 2, 0, 0)
}

export function excavationFingerGrip(
  root: THREE.Object3D,
  clip?: THREE.AnimationClip
) {
  return (
    clip?.tracks.flatMap((track) => {
      const name = track.name.replace('.quaternion', '')
      if (!/^RightHand(Thumb|Index|Middle|Ring|Pinky)[123]$/.test(name))
        return []
      const bone = root.getObjectByName(name)
      return bone
        ? [{ bone, rotation: new THREE.Quaternion().fromArray(track.values) }]
        : []
    }) ?? []
  )
}

export function applyExcavationGrip(
  grip: ReturnType<typeof excavationFingerGrip>
): void {
  for (const { bone, rotation } of grip) bone.quaternion.copy(rotation)
}
