import {
  Bone,
  BoxGeometry,
  Group,
  Mesh,
  MeshBasicMaterial,
  Vector3,
} from 'three'
import { describe, expect, it } from 'vitest'
import { reparentGroundItem } from './groundItemAttachment'

describe('ground item pickup size', () => {
  it.each([1, 1.8, 3])(
    'preserves item size through repeated pickup and cancellation at character scale %s',
    (characterScale) => {
      const world = new Group()
      const ground = new Group()
      const character = new Group()
      character.scale.setScalar(characterScale)
      character.position.set(12, 4, -3)
      character.rotation.y = 0.7
      const arm = new Bone()
      const hand = new Bone()
      character.add(arm)
      arm.add(hand)
      hand.position.set(0.1, 0.5, 0)
      world.add(ground, character)
      const model = new Group()
      model.scale.setScalar(0.25)
      const geometry = new BoxGeometry(2, 3, 1)
      const material = new MeshBasicMaterial()
      model.add(new Mesh(geometry, material))
      ground.add(model)
      const original = model.getWorldScale(new Vector3())
      const scale = new Vector3()
      for (let i = 0; i < 3; i++) {
        model.position.set(0, 0.08, 0)
        model.rotation.set(0, 0, 0)
        reparentGroundItem(model, hand)
        expect(model.parent).toBe(hand)
        expect(model.getWorldScale(scale).distanceTo(original)).toBeLessThan(
          1e-10
        )
        expect(model.position.toArray()).toEqual([0, 0.08, 0])
        model.position.set(0, 0.02, 0)
        reparentGroundItem(model, ground)
        expect(model.getWorldScale(scale).distanceTo(original)).toBeLessThan(
          1e-10
        )
        expect(
          model.scale.distanceTo(new Vector3(0.25, 0.25, 0.25))
        ).toBeLessThan(1e-10)
      }
      geometry.dispose()
      material.dispose()
    }
  )
})
