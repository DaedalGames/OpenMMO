import { expect, it, vi } from 'vitest'
import { DirectionalLight, RenderTarget } from 'three'
import type { WebGPURenderer } from 'three/webgpu'
import type { GraphicsPreset } from '../../stores/graphicsSettings'
import { applyGraphicsPreset } from './renderer-quality'

it('leaves shadow texture lifetime to the renderer during quality changes', () => {
  vi.stubGlobal('window', { devicePixelRatio: 1 })
  try {
    const light = new DirectionalLight()
    light.shadow.mapSize.set(1024, 1024)
    const map = new RenderTarget(1024, 1024)
    light.shadow.map = map
    const dispose = vi.spyOn(map, 'dispose')
    const renderer = { getPixelRatio: () => 1 } as WebGPURenderer
    applyGraphicsPreset(
      renderer,
      { pixelRatioCap: 1, shadowMapSize: 512 } as GraphicsPreset,
      light
    )
    expect(light.shadow.mapSize.toArray()).toEqual([512, 512])
    expect(light.shadow.needsUpdate).toBe(true)
    expect(light.shadow.map).toBe(map)
    expect(dispose).not.toHaveBeenCalled()
    map.dispose()
  } finally {
    vi.unstubAllGlobals()
  }
})
