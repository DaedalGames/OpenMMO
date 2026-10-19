import type * as THREE from 'three'

/** How solid the invisibility cloak wearer looks to themselves. */
const SEE_THROUGH_OPACITY = 0.3

type MaterialSlot = THREE.Material | THREE.Material[]

interface Faded {
  original: MaterialSlot
  faded: MaterialSlot
  castShadow: boolean
}

function fade(material: THREE.Material): THREE.Material {
  const clone = material.clone()
  clone.transparent = true
  clone.opacity = material.opacity * SEE_THROUGH_OPACITY
  return clone
}

function dispose(slot: MaterialSlot) {
  for (const material of Array.isArray(slot) ? slot : [slot]) material.dispose()
}

/** Fades a character to a ghost while `on`. Runs per frame so gear loaded or
 *  reskinned later fades too; clones keep materials shared with others solid. */
export class SeeThrough {
  private meshes = new Map<THREE.Mesh, Faded>()

  update(root: THREE.Object3D | undefined, on: boolean) {
    if (!on) return this.restore()
    root?.traverse((child) => {
      const mesh = child as THREE.Mesh
      if (!mesh.isMesh) return
      const known = this.meshes.get(mesh)
      if (known?.faded === mesh.material) return
      if (known) dispose(known.faded)
      const original = mesh.material
      const faded = Array.isArray(original)
        ? original.map(fade)
        : fade(original)
      this.meshes.set(mesh, {
        original,
        faded,
        castShadow: known?.castShadow ?? mesh.castShadow,
      })
      mesh.material = faded
      mesh.castShadow = false
    })
  }

  restore() {
    for (const [mesh, { original, faded, castShadow }] of this.meshes) {
      if (mesh.material === faded) mesh.material = original
      mesh.castShadow = castShadow
      dispose(faded)
    }
    this.meshes.clear()
  }
}
