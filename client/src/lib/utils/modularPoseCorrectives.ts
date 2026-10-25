import * as THREE from 'three'

export function updateModularPoseCorrectives(
  root: THREE.Object3D,
  clip: string
) {
  root.traverse((node) => {
    if (!(node instanceof THREE.SkinnedMesh)) return
    if (!node.morphTargetDictionary || !node.morphTargetInfluences) return
    for (const [name, index] of Object.entries(node.morphTargetDictionary)) {
      if (name.startsWith('pose_'))
        node.morphTargetInfluences[index] = name === `pose_${clip}` ? 1 : 0
    }
  })
}
