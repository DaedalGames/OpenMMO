import * as THREE from 'three'
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'

export function femaleTopMask(base: GLTF, value: unknown) {
  const mask = value as {
    mesh_index: number
    primitive_index: number
    primitive_triangles: number
    hide_triangle_indices: number[]
  } | null
  if (
    !mask ||
    !Number.isInteger(mask.mesh_index) ||
    !Number.isInteger(mask.primitive_index) ||
    !Number.isInteger(mask.primitive_triangles) ||
    !Array.isArray(mask.hide_triangle_indices) ||
    mask.hide_triangle_indices.some(
      (index) =>
        !Number.isInteger(index) ||
        index < 0 ||
        index >= mask.primitive_triangles
    )
  )
    throw new Error('상의 가림 정보가 올바르지 않습니다.')
  let body: THREE.Mesh | undefined
  base.scene.traverse((node) => {
    const association = base.parser.associations.get(node)
    if (
      node instanceof THREE.Mesh &&
      association?.meshes === mask.mesh_index &&
      association.primitives === mask.primitive_index
    )
      body = node
  })
  const original = body?.geometry
  const index = original?.index
  if (
    !body ||
    !original ||
    !index ||
    index.count !== mask.primitive_triangles * 3
  )
    throw new Error('몸체와 상의 가림 정보가 일치하지 않습니다.')
  const hidden = new Set(mask.hide_triangle_indices)
  const covered = original.clone()
  covered.setIndex(
    new THREE.BufferAttribute(
      index.array.filter((_, offset) => !hidden.has(Math.floor(offset / 3))),
      1
    )
  )
  const mesh = body
  return {
    setEquipped(equipped: boolean) {
      mesh.geometry = equipped ? covered : original
    },
    dispose() {
      mesh.geometry = original
      covered.dispose()
    },
  }
}
