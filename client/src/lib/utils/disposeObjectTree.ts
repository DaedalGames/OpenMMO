import type * as THREE from 'three'

/** Releases the renderer state of every object in `root`. three's WebGPU
 *  renderer keeps each drawn object (with its matrices, bindings and buffers)
 *  until the object or its material fires `dispose`; removing it from the
 *  scene is not enough. Shared geometries and materials are untouched. */
export function disposeObjectTree(root: THREE.Object3D): void {
  // The bare event: subclass dispose() overrides (lights, InstancedMesh) free more.
  root.traverse((obj) => obj.dispatchEvent({ type: 'dispose' }))
}

/** Disposes the materials of every mesh in `root`; only for per-instance clones. */
export function disposeMeshMaterials(root: THREE.Object3D): void {
  root.traverse((obj) => {
    const material = (obj as THREE.Mesh).material
    if (!material) return
    for (const m of Array.isArray(material) ? material : [material]) m.dispose()
  })
}
