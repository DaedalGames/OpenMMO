import * as THREE from 'three'
import { DORMANT_SINK_MS, DormantWakeEffect, wakeBounds } from './dormant-wake'
import { shake } from './dormant-sleep'
import { playMonsterSound } from '../managers/sfxManager'

// The body starts to shake once the Death clip has slumped.
const CRUMBLE_START_MS = 1800
const CRUMBLE_COLLAPSE_MS = 700
/** Ms into the death the body bursts into rubble. */
export const CRUMBLE_BURST_MS = CRUMBLE_START_MS + CRUMBLE_COLLAPSE_MS
const CRUMBLE_GONE_MS = CRUMBLE_BURST_MS + DORMANT_SINK_MS

/** A fallen stone boss shaking apart: the wake's dust and rocks burst from
 *  its body as it sinks into the ground. */
export class DeathCrumble {
  private effect: DormantWakeEffect | undefined
  private box = new THREE.Box3()
  private height = 0
  private started = false
  private burst = false

  constructor(
    private scene: THREE.Object3D,
    private sound: string
  ) {}

  private ensureEffect() {
    if (!this.effect) {
      this.effect = new DormantWakeEffect()
      this.scene.add(this.effect.group)
    }
    return this.effect
  }

  /** Compiled ahead: the crumble plays at the raid's most watched moment. */
  warm(renderer: unknown, camera: THREE.Camera, scene: THREE.Scene) {
    this.ensureEffect().warm(renderer, camera, scene, () => !this.started)
  }

  /** Shakes and sinks `body` (placed for this frame) `elapsedMs` into the
   *  death and hides `model` once it is under; false once nothing is left
   *  to show. */
  update(
    body: THREE.Object3D,
    model: THREE.Object3D,
    ground: number,
    elapsedMs: number,
    camera: THREE.Camera
  ) {
    const t = elapsedMs - CRUMBLE_START_MS
    if (t < 0) return true
    if (!this.started) {
      // Came into view after it had already crumbled away.
      if (elapsedMs >= CRUMBLE_GONE_MS) {
        model.visible = false
        return false
      }
      this.started = true
      const bounds = wakeBounds(this.box.setFromObject(model), ground)
      this.height = bounds.height
      this.ensureEffect().start(bounds, CRUMBLE_COLLAPSE_MS)
    }
    const showing = this.effect!.update(t, camera)
    if (!this.burst && t >= CRUMBLE_COLLAPSE_MS) {
      this.burst = true
      playMonsterSound(this.sound)
    }

    model.visible = elapsedMs < CRUMBLE_GONE_MS
    if (!model.visible) return showing
    const rumble = Math.min(1, t / CRUMBLE_COLLAPSE_MS)
    const sink = Math.max(0, (t - CRUMBLE_COLLAPSE_MS) / DORMANT_SINK_MS)
    shake(body, t / 1000, 0.03 + 0.12 * rumble * rumble)
    body.position.y -= sink * sink * this.height * 0.6
    return true
  }

  dispose() {
    this.effect?.group.removeFromParent()
    this.effect?.dispose()
  }
}
