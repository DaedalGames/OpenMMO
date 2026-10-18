import * as THREE from 'three'

const cache = new WeakMap<THREE.AnimationClip, THREE.AnimationClip>()
const curl = [30, 60, 35].map(THREE.MathUtils.degToRad)
const armSpread = THREE.MathUtils.degToRad(-22)

export function withBarkanRuneGrip(clip: THREE.AnimationClip) {
  const cached = cache.get(clip)
  if (cached) return cached
  const result = clip.clone()
  const quaternion = new THREE.Quaternion()
  const rotation = new THREE.Quaternion()
  const axis = new THREE.Vector3(1, 0, 0)
  for (const track of result.tracks) {
    const match =
      /^RightHand(?:Index|Middle|Ring|Pinky)([123])\.quaternion$/.exec(
        track.name
      )
    const spreadArm =
      ['Idle', 'Walk'].includes(clip.name) &&
      /^(?:Left|Right)Arm\.quaternion$/.test(track.name)
    if (!match && !spreadArm) continue
    rotation.setFromAxisAngle(
      axis,
      spreadArm ? armSpread : curl[Number(match![1]) - 1]
    )
    for (let offset = 0; offset < track.values.length; offset += 4) {
      quaternion.fromArray(track.values, offset).multiply(rotation).normalize()
      quaternion.toArray(track.values, offset)
    }
  }
  cache.set(clip, result)
  return result
}
