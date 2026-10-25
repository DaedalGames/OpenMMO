import { expect, it } from 'vitest'
import * as THREE from 'three'
import { updateModularPoseCorrectives } from './modularPoseCorrectives'

it('activates the seated corrective and restores other motions', () => {
  const root = new THREE.Group()
  const mesh = new THREE.SkinnedMesh()
  mesh.morphTargetDictionary = { pose_sit_idle: 0, expression: 1 }
  mesh.morphTargetInfluences = [0, 0.4]
  root.add(mesh)

  updateModularPoseCorrectives(root, 'sit_idle')
  expect(mesh.morphTargetInfluences).toEqual([1, 0.4])
  for (const clip of ['idle1', 'walk', 'run', 'rest']) {
    updateModularPoseCorrectives(root, clip)
    expect(mesh.morphTargetInfluences).toEqual([0, 0.4])
    updateModularPoseCorrectives(root, 'sit_idle')
  }
})

it('handles parts equipped while the seated animation is paused', () => {
  const root = new THREE.Group()
  updateModularPoseCorrectives(root, 'sit_idle')
  const mesh = new THREE.SkinnedMesh()
  mesh.morphTargetDictionary = { pose_sit_idle: 0 }
  mesh.morphTargetInfluences = [0]
  root.add(mesh, new THREE.Mesh())

  updateModularPoseCorrectives(root, 'sit_idle')
  expect(mesh.morphTargetInfluences).toEqual([1])
})
