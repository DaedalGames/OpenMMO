import { Object3D, Vector3 } from 'three'

export function reparentGroundItem(model: Object3D, parent: Object3D): void {
  const worldScale = model.getWorldScale(new Vector3())
  const parentScale = parent.getWorldScale(new Vector3())
  parent.add(model)
  model.scale.copy(worldScale).divide(parentScale)
}
