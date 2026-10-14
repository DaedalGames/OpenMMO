import type { DepthTexture, LightShadow, PointLight, RenderTarget } from 'three'
import { PointShadowNode, type NodeBuilder } from 'three/webgpu'

type ShadowTarget = { shadowMap: RenderTarget; depthTexture: DepthTexture }
type TargetFactory = (shadow: LightShadow, builder: NodeBuilder) => ShadowTarget

export function setupPointShadow(light: PointLight): void {
  if (light.shadow.shadowNode) return
  const node = new PointShadowNode(light, light.shadow) as PointShadowNode & {
    setupRenderTarget: TargetFactory
  }
  const createTarget = node.setupRenderTarget.bind(node)
  node.setupRenderTarget = (shadow, builder) => {
    const target = createTarget(shadow, builder)
    // Allocate before compileAsync binds it; the first shadow pass must not recreate it.
    builder.renderer.initRenderTarget(target.shadowMap)
    return target
  }
  light.shadow.shadowNode = node
}
