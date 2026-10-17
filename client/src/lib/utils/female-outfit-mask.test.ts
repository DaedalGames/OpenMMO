import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import { femaleOutfitMask } from './female-outfit-mask'

const earFit = {
  mesh_index: 0,
  primitive_index: 0,
  primitive_triangles: 2,
  hide_triangle_indices: [],
  vertex_adjustments: [
    { vertex: 0, position: [0.2, 0.3, 0], normal: [0, 0, 1] },
  ],
}

describe('femaleOutfitMask vertex fitting', () => {
  it('combines fitting with clothing masks and restores each independently', () => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry())
    const original = mesh.geometry
    const positions = original.attributes.position.array.slice()
    const indices = original.index!.array.slice()
    const masks = femaleOutfitMask()
    masks.register('helmet', earFit, mesh)
    masks.register(
      'top',
      { ...earFit, hide_triangle_indices: [1], vertex_adjustments: [] },
      mesh
    )
    masks.setEquipped('helmet', true)
    expect(mesh.geometry.index!.array).toEqual(indices)
    expect(mesh.geometry.attributes.position.getX(0)).toBeCloseTo(0.2)
    expect(original.attributes.position.array).toEqual(positions)
    masks.setEquipped('top', true)
    expect(mesh.geometry.index!.count).toBe(3)
    expect(mesh.geometry.attributes.position.getX(0)).toBeCloseTo(0.2)
    masks.setEquipped('helmet', false)
    expect(mesh.geometry.index!.count).toBe(3)
    expect(mesh.geometry.attributes.position.array).toEqual(positions)
    masks.setEquipped('top', false)
    expect(mesh.geometry).toBe(original)
    masks.dispose()
    original.dispose()
  })

  it('keeps shared geometry intact for other wearers and restores on disposal', () => {
    const original = new THREE.PlaneGeometry()
    const first = new THREE.Mesh(original)
    const second = new THREE.Mesh(original)
    const masks = femaleOutfitMask()
    masks.register('helmet', earFit, first)
    masks.setEquipped('helmet', true)
    expect(second.geometry).toBe(original)
    expect(first.geometry).not.toBe(second.geometry)
    masks.dispose()
    expect(first.geometry).toBe(original)
    original.dispose()
  })

  it.each([
    { vertex: 4, position: [0, 0, 0], normal: [0, 0, 1] },
    { vertex: 0, position: [Number.NaN, 0, 0], normal: [0, 0, 1] },
    { vertex: 0, position: [0, 0, 0], normal: [0, 1] },
  ])('rejects incompatible vertex adjustments %#', (adjustment) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry())
    const masks = femaleOutfitMask()
    expect(() =>
      masks.register(
        'helmet',
        { ...earFit, vertex_adjustments: [adjustment] },
        mesh
      )
    ).toThrow()
    masks.dispose()
    mesh.geometry.dispose()
  })
})
