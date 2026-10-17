import * as THREE from 'three'
import { describe, expect, it } from 'vitest'
import { LEVEL_UP_ORBS, spiralPoint } from './level-up'

describe('level-up spiral', () => {
  it('rises from the feet past the head at a constant radius', () => {
    const start = spiralPoint(0, 0, new THREE.Vector3())
    const end = spiralPoint(1, 0, new THREE.Vector3())
    expect(start.y).toBeLessThan(0.2)
    expect(end.y).toBeGreaterThan(3)
    expect(Math.hypot(end.x, end.z)).toBeCloseTo(Math.hypot(start.x, start.z))
  })
  it('spaces the orbs evenly around the body', () => {
    const points = Array.from({ length: LEVEL_UP_ORBS }, (_, orb) =>
      spiralPoint(0.4, orb, new THREE.Vector3())
    )
    const angles = points.map((p) => Math.atan2(p.z, p.x))
    const gap = (a: number, b: number) =>
      Math.abs(((b - a + 3 * Math.PI) % (2 * Math.PI)) - Math.PI)
    expect(gap(angles[0], angles[1])).toBeCloseTo((2 * Math.PI) / 3, 5)
  })
})
