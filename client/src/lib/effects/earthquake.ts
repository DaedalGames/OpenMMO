import * as THREE from 'three'
import { createRng } from '../utils/simplex-noise'
import { EARTHQUAKE_STRIKE_MS } from '../data/monsterSkills'
import {
  dustMaterial,
  instancedMesh,
  landTime,
  placeDust,
  placeRocks,
  rockMaterial,
  rubble,
  tintRocks,
  type Dust,
  type Rock,
} from './dormant-wake'
import type { BodyFootprint } from './earth-roar'

/** The warning pound in the `Quake` clip. */
const FIRST_POUND_MS = 1150
const END_MS = EARTHQUAKE_STRIKE_MS + 2600
const DUST_PER_POUND = 24
const ROCKS_PER_POUND = 16

/** Dust and stones thrown up around the body by each pound; the marks that
 *  split open are ground eruptions. */
export class EarthquakeEffect {
  readonly group = new THREE.Group()
  private planeGeometry = new THREE.PlaneGeometry(1, 1)
  private rockGeometry = rubble()
  private dustMaterial = dustMaterial()
  private rockMaterial = rockMaterial()
  private dustMesh: THREE.InstancedMesh
  private rockMesh: THREE.InstancedMesh
  private dust: Dust[] = []
  private rocks: Rock[] = []
  private elapsedMs = END_MS
  private halfX: number
  private halfZ: number

  constructor(body: BodyFootprint) {
    this.halfX = body.halfWidth
    this.halfZ = (body.front + body.back) / 2
    this.dustMesh = instancedMesh(
      this.planeGeometry,
      this.dustMaterial,
      DUST_PER_POUND * 2
    )
    this.rockMesh = instancedMesh(
      this.rockGeometry,
      this.rockMaterial,
      ROCKS_PER_POUND * 2
    )
    this.rockMesh.castShadow = true
    this.group.add(this.dustMesh, this.rockMesh)
    this.group.visible = false
  }

  start(origin: THREE.Vector3) {
    const rand = createRng(Math.floor(origin.x * 53 + origin.z * 29))
    this.group.position.copy(origin)
    this.group.visible = true
    this.elapsedMs = 0
    this.dust.length = 0
    this.rocks.length = 0
    for (const [at, power] of [
      [FIRST_POUND_MS, 0.6],
      [EARTHQUAKE_STRIKE_MS, 1],
    ]) {
      for (let i = 0; i < DUST_PER_POUND; i++) {
        const a = rand() * Math.PI * 2
        const out = (3 + rand() * 4) * power
        this.dust.push({
          at: at + rand() * 200,
          life: 1500 + rand() * 900,
          x: Math.cos(a) * this.halfX * 1.05,
          y: 0.2,
          z: Math.sin(a) * this.halfZ * 1.05,
          vx: Math.cos(a) * out,
          vy: 0.4 + rand() * 0.8,
          vz: Math.sin(a) * out,
          size: (2 + rand() * 1.5) * power,
          grow: (3 + rand() * 2) * power,
          peak: 0.75 + rand() * 0.2,
          seed: rand(),
          shade: 0.8 + rand() * 0.2,
        })
      }
      for (let i = 0; i < ROCKS_PER_POUND; i++) {
        const a = rand() * Math.PI * 2
        const out = (2 + rand() * 4) * power
        const rock: Rock = {
          at: at + rand() * 100,
          x: Math.cos(a) * this.halfX,
          y: 0.2,
          z: Math.sin(a) * this.halfZ,
          vx: Math.cos(a) * out,
          vy: (3 + rand() * 4) * power,
          vz: Math.sin(a) * out,
          size: 0.25 + rand() * 0.45,
          land: 0,
          stretch: new THREE.Vector3(1 + rand() * 0.6, 0.6 + rand() * 0.4, 1),
          spin: new THREE.Vector3(rand(), rand(), rand()).multiplyScalar(7),
        }
        rock.land = landTime(rock)
        this.rocks.push(rock)
      }
    }
    tintRocks(this.rockMesh, rand, 0)
  }

  update(deltaTime: number, camera: THREE.Camera | undefined) {
    if (!this.group.visible || !camera) return
    this.elapsedMs += deltaTime * 1000
    if (this.elapsedMs >= END_MS) {
      this.group.visible = false
      return
    }
    placeDust(this.dustMesh, this.dust, this.elapsedMs, camera)
    placeRocks(this.rockMesh, this.rocks, this.elapsedMs, 0.6)
  }

  dispose() {
    this.group.removeFromParent()
    this.planeGeometry.dispose()
    this.rockGeometry.dispose()
    this.dustMaterial.dispose()
    this.rockMaterial.dispose()
    this.dustMesh.dispose()
    this.rockMesh.dispose()
  }
}
