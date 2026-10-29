import * as THREE from 'three'

const KICK_MS = 220
const KICK_PX = 9

let kick: { startedAt: number; direction: THREE.Vector3 } | null = null
let applied = false
const from = new THREE.Vector3()
const to = new THREE.Vector3()

/** A jolt along `rotation` (world heading), as when a charge slams home. */
export function kickCamera(rotation: number, now = performance.now()) {
  kick = {
    startedAt: now,
    direction: new THREE.Vector3(Math.sin(rotation), 0, Math.cos(rotation)),
  }
}

/** Shifts the projection, not the camera, so the follow offset never drifts. */
export function applyCameraKick(
  camera: THREE.OrthographicCamera,
  focus: { x: number; y: number; z: number },
  width: number,
  height: number,
  now = performance.now()
) {
  const t = kick ? (now - kick.startedAt) / KICK_MS : 1
  if (!kick || t >= 1 || width <= 0 || height <= 0) {
    kick = null
    if (applied) camera.clearViewOffset()
    applied = false
    return
  }
  from.set(focus.x, focus.y, focus.z).project(camera)
  to.set(focus.x, focus.y, focus.z).add(kick.direction).project(camera)
  const dx = (to.x - from.x) * width
  const dy = (from.y - to.y) * height
  const length = Math.hypot(dx, dy) || 1
  const amount = KICK_PX * (1 - t) * (1 - t) * Math.sin(t * Math.PI * 2.5)
  camera.setViewOffset(
    width,
    height,
    -(dx / length) * amount,
    -(dy / length) * amount,
    width,
    height
  )
  applied = true
}
