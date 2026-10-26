import assert from 'node:assert/strict'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'

await ensureFemalePreview('animations')
const directory = process.argv[2] ?? 'assets/items/female_rogue_gloves/tripo_v1/fitted_v1'
const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const partPath = `${directory}/gloves_female_rogue.glb`
const skinReferences = existsSync(`${directory}/skin-reference.json`)
  ? JSON.parse(readFileSync(`${directory}/skin-reference.json`))
  : undefined
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { femaleOutfitMask } = await server.ssrLoadModule('/src/lib/utils/female-outfit-mask.ts')
  const base = await load(basePath)
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const i = base.animations.findIndex(entry => entry.name === clip.name)
    if (i < 0) base.animations.push(clip)
    else base.animations[i] = clip
  }
  let body
  base.scene.traverse(node => {
    if (node.isSkinnedMesh && base.parser.associations.get(node)?.primitives === 0) body = node
  })
  const skeleton = body.skeleton
  const meshes = bindModularPart(base.scene, (await load(partPath)).scene)
  assert.equal(meshes.length, 2)
  base.scene.updateMatrixWorld(true)
  const parts = meshes.map(mesh => {
    assert.equal(mesh.skeleton.bones.length, 65)
    for (let i = 0; i < 65; i++) {
      assert.equal(mesh.skeleton.bones[i], skeleton.bones[i])
      assert.deepEqual(mesh.skeleton.boneInverses[i].elements, skeleton.boneInverses[i].elements)
    }
    const { position, skinWeight, skinIndex, normal, tangent } = mesh.geometry.attributes
    assert.ok([...normal.array, ...tangent.array].every(Number.isFinite))
    const rest = []
    for (let i = 0; i < position.count; i++) {
      const p = mesh.getVertexPosition(i, new THREE.Vector3())
      assert.ok(p.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 1e-6)
      const side = p.x < 0 ? 'Right' : 'Left'
      let sum = 0
      for (let k = 0; k < 4; k++) {
        const w = skinWeight.getComponent(i, k)
        assert.ok(Number.isFinite(w) && w >= 0)
        sum += w
        if (!w) continue
        const name = skeleton.bones[skinIndex.getComponent(i, k)].name
        assert.ok(name.startsWith(side) && /ForeArm|Hand/.test(name), name)
      }
      assert.ok(Math.abs(sum - 1) < 1e-6)
      rest.push(p)
    }
    const reference = (skinReferences?.[mesh.name.endsWith('right') ? 'right' : 'left'] ?? []).map(p => new THREE.Vector3(...p))
    const edges = [], rigid = [], seams = new Map()
    const index = mesh.geometry.index
    for (let i = 0; i < position.count; i++) {
      const key = rest[i].toArray().map(value => Math.round(value * 1e6)).join(',')
      if (!seams.has(key)) seams.set(key, [])
      seams.get(key).push(i)
    }
    for (let i = 0; i < index.count; i += 3) for (let k = 0; k < 3; k++) {
      const a = index.getX(i + k), b = index.getX(i + (k + 1) % 3)
      const length = rest[a].distanceTo(rest[b])
      if (length < .0015) continue
      edges.push([a, b, length])
      if (skinWeight.getX(a) > .99999 && skinWeight.getX(b) > .99999 && skinIndex.getX(a) === skinIndex.getX(b)) rigid.push([a, b, length])
    }
    return { mesh, rest, reference, edges, rigid, seams: [...seams.values()].filter(rows => rows.length > 1) }
  })
  const mask = femaleOutfitMask(base)
  const geometry = body.geometry
  const coverage = JSON.parse(readFileSync(`${directory}/body-occlusion.json`))
  mask.register('rogue-gloves', coverage)
  mask.setEquipped('rogue-gloves', true)
  assert.equal(body.geometry.index.count, geometry.index.count - coverage.hide_triangle_indices.length * 3)
  mask.setEquipped('rogue-gloves', false)
  assert.equal(body.geometry, geometry)
  mask.dispose()
  const clips = [], poses = []
  const sampler = clipSampler(base.scene, { samples: 33, restore: skeleton.bones })
  for (const clip of base.animations) {
    let maximumEdgeRatio = 0, maximumRigidChange = 0, maximumSeamGap = 0, maximumSkinOffset = 0, maximumShellEdgeExcess = 0, maximumSkinEdgeRatio = 0, worstEdge
    for (const { time, sample } of sampler(clip)) {
      for (const { mesh, rest, reference, edges, rigid, seams } of parts) {
        const positions = rest.map((_, i) => mesh.getVertexPosition(i, new THREE.Vector3()))
        const skin = reference.map((p, i) => mesh.applyBoneTransform(i, p.clone()))
        for (let i = 0; i < skin.length; i++) maximumSkinOffset = Math.max(maximumSkinOffset, positions[i].distanceTo(skin[i]))
        assert.ok(positions.every(p => p.toArray().every(Number.isFinite)))
        for (const [a, b, length] of edges) {
          const ratio = positions[a].distanceTo(positions[b]) / length
          if (ratio > maximumEdgeRatio) {
            maximumEdgeRatio = ratio
            worstEdge = { mesh: mesh.name, a, b, length, time }
          }
        }
        for (const [a, b] of edges) if (a < skin.length && b < skin.length) {
          maximumShellEdgeExcess = Math.max(maximumShellEdgeExcess, positions[a].distanceTo(positions[b]) - skin[a].distanceTo(skin[b]))
          maximumSkinEdgeRatio = Math.max(maximumSkinEdgeRatio, skin[a].distanceTo(skin[b]) / reference[a].distanceTo(reference[b]))
        }
        for (const [a, b, length] of rigid) maximumRigidChange = Math.max(maximumRigidChange, Math.abs(positions[a].distanceTo(positions[b]) / length - 1))
        for (const rows of seams) for (const i of rows) maximumSeamGap = Math.max(maximumSeamGap, positions[i].distanceTo(positions[rows[0]]))
      }
      if (sample % 4 === 0) poses.push({ clip: clip.name, time, matrices: skeleton.bones.map((bone, i) => new THREE.Matrix4().multiplyMatrices(bone.matrixWorld, skeleton.boneInverses[i]).toArray()) })
    }
    clips.push({ name: clip.name, samples: 33, maximum_edge_ratio: maximumEdgeRatio, underlying_skin_edge_ratio: maximumSkinEdgeRatio, maximum_shell_edge_excess_m: maximumShellEdgeExcess, maximum_skin_offset_m: maximumSkinOffset, maximum_rigid_change: maximumRigidChange, maximum_seam_gap_m: maximumSeamGap, worst_edge: worstEdge })
  }
  const report = { date: '2026-10-26', body_sha256: hash(basePath), glove_sha256: hash(partPath), bones: 65, triangles: meshes.reduce((sum, mesh) => sum + mesh.geometry.index.count / 3, 0), exact_bind_compatibility: true, normalized_weights: true, no_opposite_side_influence: true, body_mask_restores: true, clips }
  writeFileSync(`${directory}/runtime-validation.json`, JSON.stringify(report, null, 2) + '\n')
  writeFileSync(`${directory}/validation-poses.json`, JSON.stringify(poses) + '\n')
  console.log(JSON.stringify(report, null, 2))
  assert.ok(clips.every(clip => clip.maximum_rigid_change < 1e-4), 'Rigid cuff deformation')
  assert.ok(clips.every(clip => clip.maximum_seam_gap_m < 2e-6), 'UV seams separated')
  assert.ok(clips.every(clip => clip.maximum_skin_offset_m < .00351), 'Glove separated from its skin reference')
  assert.ok(clips.every(clip => clip.maximum_shell_edge_excess_m < .00701), 'Stretch beyond the underlying skin')
  if (!skinReferences) assert.ok(clips.every(clip => clip.maximum_edge_ratio < 3.5), 'Excessive source glove stretch')
} finally {
  await server.close()
}
