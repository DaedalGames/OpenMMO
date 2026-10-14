import { describe, expect, it, vi } from 'vitest'
import { PointLight, WebGPUCoordinateSystem } from 'three'
import { CubeRenderTarget, type NodeBuilder } from 'three/webgpu'
import { setupPointShadow } from './pointShadow'

function builder() {
  return {
    renderer: {
      reversedDepthBuffer: false,
      coordinateSystem: WebGPUCoordinateSystem,
      initRenderTarget: vi.fn(),
    },
    createCubeRenderTarget: (size: number) => new CubeRenderTarget(size),
  }
}

describe('point shadow allocation before pipeline warmup', () => {
  it('initializes the complete cube target before its depth texture can be sampled', () => {
    const light = new PointLight()
    light.shadow.mapSize.set(512, 512)
    setupPointShadow(light)
    const node = light.shadow.shadowNode as unknown as {
      setupRenderTarget(
        shadow: typeof light.shadow,
        builder: NodeBuilder
      ): {
        shadowMap: CubeRenderTarget
        depthTexture: unknown
      }
    }
    const context = builder()
    const target = node.setupRenderTarget(
      light.shadow,
      context as unknown as NodeBuilder
    )
    expect(target.shadowMap.width).toBe(512)
    expect(target.shadowMap.depthTexture).toBe(target.depthTexture)
    expect(context.renderer.initRenderTarget).toHaveBeenCalledExactlyOnceWith(
      target.shadowMap
    )
    target.shadowMap.dispose()
  })

  it('does not replace a previously installed shadow node', () => {
    const light = new PointLight()
    setupPointShadow(light)
    const node = light.shadow.shadowNode
    setupPointShadow(light)
    expect(light.shadow.shadowNode).toBe(node)
  })
})
