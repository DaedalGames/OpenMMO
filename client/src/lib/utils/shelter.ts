import type { ObjectDef, ObjectPlacement } from '../stores/editorStore'
import type { Position } from '../network/networkTypes'
import { shortestWrappedDeltaX } from '../terrain/world-wrap'

export function normalizeYaw(yaw: number): number {
  return ((yaw % 360) + 360) % 360
}

export function isInsideShelter(
  point: Position,
  placement: ObjectPlacement,
  cutaway: NonNullable<ObjectDef['cutaway']>
): boolean {
  const yaw = (placement.rotation * Math.PI) / 180
  const dx = shortestWrappedDeltaX(placement.x, point.x)
  const dz = point.z - placement.z
  const x = dx * Math.cos(yaw) - dz * Math.sin(yaw)
  const z = dx * Math.sin(yaw) + dz * Math.cos(yaw)
  const y = point.y - placement.y
  return (
    Math.abs(x) < cutaway.width / 2 &&
    Math.abs(z) < cutaway.depth / 2 &&
    y > -0.3 &&
    y < cutaway.height
  )
}
