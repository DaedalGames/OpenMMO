import * as THREE from 'three'

export const BARKAN_ATTACK_FOLLOW_THROUGH = {
  start: 0.66,
  slowStart: 0.7,
  slowFull: 0.82,
  slowEnd: 1.1,
  resume: 1.35,
  slowRate: 0.4,
  twistPeak: 1.02,
  twistHold: 1.12,
  twists: { Spine: 17, Spine1: 15, Spine2: 13, Neck: -18 },
} as const

const FPS = 60
const cache = new WeakMap<THREE.AnimationClip, THREE.AnimationClip>()

export function barkanAttackSourceTime(time: number) {
  const { slowStart, slowFull, slowEnd, resume, slowRate } =
    BARKAN_ATTACK_FOLLOW_THROUGH
  const steps = Math.ceil(time * 1000)
  let source = 0
  for (let step = 0; step < steps; step++) {
    const at = ((step + 0.5) * time) / steps
    const slow =
      THREE.MathUtils.smoothstep(at, slowStart, slowFull) *
      (1 - THREE.MathUtils.smoothstep(at, slowEnd, resume))
    source += (time / steps) * (1 - (1 - slowRate) * slow)
  }
  return source
}

export function barkanAttackTwist(time: number, duration: number) {
  const { start, twistPeak, twistHold } = BARKAN_ATTACK_FOLLOW_THROUGH
  return (
    THREE.MathUtils.smootherstep(time, start, twistPeak) *
    (1 - THREE.MathUtils.smootherstep(time, twistHold, duration - 0.1))
  )
}

// The source chop already bottoms out near the floor, so the extra swing is a
// torso turn about world up: the blade travels further without dropping.
export function withBarkanAttackFollowThrough(clip: THREE.AnimationClip) {
  if (clip.name !== 'Attack') return clip
  const cached = cache.get(clip)
  if (cached) return cached
  let frames = Math.ceil(clip.duration * FPS)
  while (barkanAttackSourceTime(frames / FPS) < clip.duration) frames++
  const duration = frames / FPS
  const { start } = BARKAN_ATTACK_FOLLOW_THROUGH
  const times = Array.from(clip.tracks[0].times).filter((time) => time < start)
  for (let frame = Math.ceil(start * FPS); frame <= frames; frame++)
    times.push(frame / FPS)
  const sources = times.map((time) =>
    Math.min(barkanAttackSourceTime(time), clip.duration)
  )
  const sample = (name: string) => {
    const track = clip.tracks.find(
      (track) => track.name === `${name}.quaternion`
    )!
    const interpolant = track.createInterpolant()
    return sources.map((time) =>
      new THREE.Quaternion().fromArray(interpolant.evaluate(time))
    )
  }
  const chain = ['Hips', 'Spine', 'Spine1', 'Spine2'].map(sample)
  const parents = chain.map((_, depth) =>
    sources.map((_, frame) => {
      const world = new THREE.Quaternion()
      for (let index = 0; index <= depth; index++)
        world.multiply(chain[index][frame])
      return world
    })
  )
  const twisted = new Map(
    Object.entries(BARKAN_ATTACK_FOLLOW_THROUGH.twists).map(
      ([name, degrees], depth) => [
        `${name}.quaternion`,
        { parent: parents[depth], angle: THREE.MathUtils.degToRad(degrees) },
      ]
    )
  )
  const up = new THREE.Vector3(0, 1, 0)
  const axis = new THREE.Vector3()
  const turn = new THREE.Quaternion()
  const pose = new THREE.Quaternion()
  const tracks = clip.tracks.map((track) => {
    const interpolant = track.createInterpolant()
    const size = track.getValueSize()
    const values: number[] = []
    sources.forEach((time, frame) => {
      const value = Array.from(interpolant.evaluate(time) as ArrayLike<number>)
      const twist = twisted.get(track.name)
      if (twist) {
        const inverse = twist.parent[frame].clone().invert()
        axis.copy(up).applyQuaternion(inverse)
        turn.setFromAxisAngle(
          axis,
          twist.angle * barkanAttackTwist(times[frame], duration)
        )
        pose.fromArray(value).premultiply(turn).normalize().toArray(value)
      }
      values.push(...value.slice(0, size))
    })
    const TrackType = track.constructor as new (
      name: string,
      times: number[],
      values: number[]
    ) => THREE.KeyframeTrack
    return new TrackType(track.name, times, values)
  })
  const result = new THREE.AnimationClip(clip.name, duration, tracks)
  cache.set(clip, result)
  return result
}
