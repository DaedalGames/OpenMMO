import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import { headlessThree, root } from './lib/headless-three.mjs'

const { server, sources, load } = await headlessThree()
try {
  const { bindModularPart, showModularOutfit, skinnedParts, BARD_MODULAR_OUTFIT } =
    await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const body = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const hat = bindModularPart(body, (await load('assets/modular_human_male_01/bard/tripo_hat_v1/helmet_bard.glb')).scene)
  const variants = {}
  for (const [id, path] of [
    ['hair_crop', 'fitted/hair_crop.glb'],
    ['hair_wavy_bone', 'hair/tripo_wavy_v1/hair_wavy_bone.glb'],
    ['hair_ranger', 'hair/tripo_ranger_v1/hair_ranger.glb'],
  ]) {
    const meshes = bindModularPart(body, (await load(`assets/modular_human_male_01/${path}`)).scene)
    const originals = meshes.map(mesh => mesh.geometry)
    const parts = new Map([['helmet_bard', hat], [id, meshes]])
    showModularOutfit(skinnedParts(body), parts, { ...BARD_MODULAR_OUTFIT, hair: id, helmet: 'bard' })
    variants[id] = meshes.map(mesh => ({
      positions: Array.from(mesh.geometry.attributes.position.array),
      uv: Array.from(mesh.geometry.attributes.uv.array),
      indices: Array.from(mesh.geometry.index.array),
    }))
    assert.ok(meshes.every(mesh => mesh.visible))
    showModularOutfit(skinnedParts(body), parts, { ...BARD_MODULAR_OUTFIT, hair: id })
    assert.ok(meshes.every((mesh, i) => mesh.geometry === originals[i]))
    for (const mesh of meshes) mesh.removeFromParent()
  }
  const output = 'assets/modular_human_male_01/bard/tripo_hat_v1/equipped-hair.json'
  writeFileSync(new URL(output, root), JSON.stringify({ sources, variants }) + '\n')
  console.log('Validated hair restoration; exported equipped geometry for intersection checks.')
} finally {
  await server.close()
}
