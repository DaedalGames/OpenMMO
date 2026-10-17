import * as THREE from 'three'
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'

interface OutfitMask {
  mesh_index: number
  primitive_index: number
  primitive_triangles: number
  hide_triangle_indices: number[]
  vertex_adjustments?: VertexAdjustment[]
}

interface VertexAdjustment {
  vertex: number
  position: [number, number, number]
  normal: [number, number, number]
}

export function femaleOutfitMask(base?: GLTF) {
  const states = new Map<
    THREE.Mesh,
    {
      original: THREE.BufferGeometry
      covered?: THREE.BufferGeometry
    }
  >()
  const slots = new Map<
    string,
    { mesh: THREE.Mesh; hidden: Set<number>; adjustments: VertexAdjustment[] }
  >()
  const equipped = new Set<string>()
  const apply = () => {
    for (const [mesh, state] of states) {
      const hidden = new Set<number>()
      const adjustments = new Map<number, VertexAdjustment>()
      for (const name of equipped) {
        const slot = slots.get(name)!
        if (slot.mesh === mesh) {
          for (const index of slot.hidden) hidden.add(index)
          for (const item of slot.adjustments)
            adjustments.set(item.vertex, item)
        }
      }
      mesh.geometry = state.original
      state.covered?.dispose()
      state.covered = undefined
      if (hidden.size || adjustments.size) {
        const covered = state.original.clone()
        if (hidden.size)
          covered.setIndex(
            new THREE.BufferAttribute(
              state.original.index!.array.filter(
                (_, offset) => !hidden.has(Math.floor(offset / 3))
              ),
              1
            )
          )
        for (const item of adjustments.values()) {
          covered.attributes.position.setXYZ(item.vertex, ...item.position)
          covered.attributes.normal.setXYZ(item.vertex, ...item.normal)
          const tangent = covered.attributes.tangent
          if (tangent) {
            const n = new THREE.Vector3(...item.normal)
            const t = new THREE.Vector3().fromBufferAttribute(
              tangent,
              item.vertex
            )
            t.addScaledVector(n, -t.dot(n)).normalize()
            tangent.setXYZ(item.vertex, t.x, t.y, t.z)
          }
        }
        mesh.geometry = state.covered = covered
      }
    }
  }
  const toggle = (name: string, enabled: boolean) => {
    if (enabled && !slots.has(name))
      throw new Error('의상 가림 정보가 없습니다.')
    if (equipped.has(name) === enabled) return false
    if (enabled) equipped.add(name)
    else equipped.delete(name)
    return true
  }
  return {
    register(name: string, value: unknown, target?: THREE.Mesh) {
      const mask = value as OutfitMask | null
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
        throw new Error('의상 가림 정보가 올바르지 않습니다.')
      let body: THREE.Mesh | undefined = target
      if (!target)
        base?.scene.traverse((node) => {
          const association = base.parser.associations.get(node)
          if (
            node instanceof THREE.Mesh &&
            association?.meshes === mask.mesh_index &&
            association.primitives === mask.primitive_index
          )
            body = node
        })
      const original = body && (states.get(body)?.original ?? body.geometry)
      const index = original?.index
      if (
        !body ||
        !original ||
        !index ||
        index.count !== mask.primitive_triangles * 3
      )
        throw new Error('몸체와 의상 가림 정보가 일치하지 않습니다.')
      if (slots.has(name))
        throw new Error('의상 가림 정보가 이미 등록되었습니다.')
      const adjustments = mask.vertex_adjustments ?? []
      if (
        !Array.isArray(adjustments) ||
        adjustments.some(
          (item) =>
            !item ||
            !Number.isInteger(item.vertex) ||
            item.vertex < 0 ||
            item.vertex >= original.attributes.position.count ||
            !Array.isArray(item.position) ||
            item.position.length !== 3 ||
            !item.position.every(Number.isFinite) ||
            !Array.isArray(item.normal) ||
            item.normal.length !== 3 ||
            !item.normal.every(Number.isFinite)
        ) ||
        (adjustments.length > 0 && !original.attributes.normal)
      )
        throw new Error('의상 정점 보정 정보가 올바르지 않습니다.')
      if (!states.has(body)) states.set(body, { original })
      slots.set(name, {
        mesh: body,
        hidden: new Set(mask.hide_triangle_indices),
        adjustments,
      })
    },
    setEquipped(name: string, enabled: boolean) {
      if (toggle(name, enabled)) apply()
    },
    setEquippedAll(entries: Record<string, boolean>) {
      let changed = false
      for (const [name, enabled] of Object.entries(entries))
        changed = toggle(name, enabled) || changed
      if (changed) apply()
    },
    unregister(name: string) {
      const wasEquipped = equipped.delete(name)
      slots.delete(name)
      if (wasEquipped) apply()
    },
    dispose() {
      for (const [mesh, state] of states) {
        mesh.geometry = state.original
        state.covered?.dispose()
      }
      states.clear()
      slots.clear()
      equipped.clear()
    },
  }
}
