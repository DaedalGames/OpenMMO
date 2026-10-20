import * as THREE from 'three'
import type { WebGPURenderer } from 'three/webgpu'
import { CSMShadowNode } from 'three/addons/csm/CSMShadowNode.js'
import type { GraphicsPreset } from '../../stores/graphicsSettings'
import { pcfShadowFilter } from '../../utils/pointShadow'

const CSM_MAX_FAR = 200
const CSM_CASCADES = 2

export function setupCsmShadow(light: THREE.DirectionalLight): void {
  const csm = new CSMShadowNode(light, {
    cascades: CSM_CASCADES,
    maxFar: CSM_MAX_FAR,
    mode: 'practical',
    lightMargin: 100,
  })
  csm.fade = true
  // Same render-group uniform churn as pointShadow.ts: three@0.186.1 rebuilds
  // the fade graph on every shader build, and the cascades' cloned shadows
  // drop filterNode, so they fall back to the per-build PCF filter.
  const internals = csm as unknown as {
    _setupFade(): unknown
    _init(builder: unknown): void
  }
  const setupFade = internals._setupFade.bind(csm)
  let fadeNode: unknown
  internals._setupFade = () => (fadeNode ??= setupFade())
  const init = internals._init.bind(csm)
  internals._init = (builder) => {
    init(builder)
    for (const cascade of csm.lights)
      cascade.shadow!.filterNode = pcfShadowFilter
  }
  light.shadow.shadowNode = csm
}

export function setDirectionalShadowIntensity(
  light: THREE.DirectionalLight,
  intensity: number
): void {
  light.shadow.intensity = intensity
  const csm = light.shadow.shadowNode
  if (csm instanceof CSMShadowNode) {
    // CSM keeps a separate shadow for each cascade.
    for (const cascade of csm.lights) {
      if (cascade.shadow) cascade.shadow.intensity = intensity
    }
  }
}

const _tmpVec2 = new THREE.Vector2()

export function applyGraphicsPreset(
  renderer: WebGPURenderer,
  preset: GraphicsPreset,
  directionalLight: THREE.DirectionalLight | null | undefined
): void {
  const newRatio = Math.min(window.devicePixelRatio, preset.pixelRatioCap)
  if (renderer.getPixelRatio() !== newRatio) {
    renderer.setPixelRatio(newRatio)
    const sz = renderer.getSize(_tmpVec2)
    renderer.setSize(sz.width, sz.height)
  }

  if (directionalLight?.shadow) {
    const cur = directionalLight.shadow.mapSize
    if (cur.x !== preset.shadowMapSize) {
      cur.set(preset.shadowMapSize, preset.shadowMapSize)
      directionalLight.shadow.needsUpdate = true
    }
  }
}
