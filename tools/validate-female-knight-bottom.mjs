import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const version = process.argv[2] ?? 'v17'
assert.ok(['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25', 'v26', 'v27', 'v28', 'v29', 'v30', 'v31', 'v32', 'v33'].includes(version))
const directory = `assets/items/female_knight_bottom/tripo_v1/fitted_${version}`
const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const partPath = `${directory}/bottom_female_knight.glb`
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { femaleOutfitMask } = await server.ssrLoadModule('/src/previews/female-outfit-mask.ts')
  const base = await load(basePath)
  const previewAnimations = 'assets/modular_human_female_01/preview/animations.json'
  const prepared = JSON.parse(readFileSync(previewAnimations))
  for (const data of prepared.clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex(entry => entry.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  const body = base.scene
  const bottoms = bindModularPart(body, (await load(partPath)).scene)
  assert.ok(bottoms.length > 0)
  body.updateMatrixWorld(true)
  const skeleton = bottoms[0].skeleton
  let bodyMesh
  body.traverse(object => { if (object.isSkinnedMesh && !bodyMesh) bodyMesh = object })
  assert.equal(skeleton.bones.length, 65)
  for (let i = 0; i < 65; i++) {
    assert.equal(skeleton.bones[i], bodyMesh.skeleton.bones[i])
    assert.deepEqual(skeleton.boneInverses[i].elements, bodyMesh.skeleton.boneInverses[i].elements)
  }
  const regions = bottoms.map(bottom => {
    assert.equal(bottom.skeleton, skeleton)
    const position = bottom.geometry.attributes.position
    const joints = bottom.geometry.attributes.skinIndex
    const weights = bottom.geometry.attributes.skinWeight
    const rest = []
    for (let i = 0; i < position.count; i++) {
      const point = bottom.getVertexPosition(i, new THREE.Vector3())
      assert.ok(point.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 1e-6)
      rest.push(point)
      let sum = 0
      for (let k = 0; k < 4; k++) {
        const weight = weights.getComponent(i, k)
        sum += weight
        if (!weight) continue
        const name = skeleton.bones[joints.getComponent(i, k)].name
        assert.ok(['Hips', 'LeftUpLeg', 'RightUpLeg'].includes(name))
        assert.ok(name !== (point.x > 0 ? 'RightUpLeg' : 'LeftUpLeg'))
      }
      assert.ok(Math.abs(sum - 1) < 1e-6)
    }
    const index = bottom.geometry.index
    const rigidEdges = []
    for (let i = 0; i < index.count; i += 3) {
      for (let k = 0; k < 3; k++) {
        const a = index.getX(i + k), b = index.getX(i + (k + 1) % 3)
        const rigid = vertex => weights.getX(vertex) > .99999
        if (rigid(a) && rigid(b) && joints.getX(a) === joints.getX(b)) {
          const length = rest[a].distanceTo(rest[b])
          if (length > .001) rigidEdges.push([a, b, length])
        }
      }
    }
    return { bottom, rest, rigidEdges, triangles: index.count / 3 }
  })
  const rigidEdgeCount = regions.reduce((sum, region) => sum + region.rigidEdges.length, 0)
  assert.ok(rigidEdgeCount > 3000)
  const attachmentPairs = []
  const bucklePairs = []
  if (['v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25', 'v26', 'v27', 'v28', 'v29', 'v30', 'v31', 'v32', 'v33'].includes(version)) {
    const fitting = JSON.parse(readFileSync(`${directory}/fitting.json`))
    for (const [index, vertices] of (fitting.opening_vertex_groups ?? []).entries())
      bucklePairs.push({ vertices, anchor: fitting.tab_vertices[index] })
    const selected = new Set(fitting.vertices)
    const waist = new Set(fitting.waist_vertices ?? [])
    const buckle = new Set(fitting.buckle_vertices ?? [])
    const rear = new Set(fitting.rear_strap_vertices ?? [])
    const leather = new Set(fitting.rear_leather_vertices ?? [])
    const strapUV = new Set(fitting.strap_uv_vertices ?? [])
    const previous = (await load(fitting.source)).scene
    const meshes = []
    previous.traverse(object => { if (object.isSkinnedMesh) meshes.push(object) })
    assert.equal(bottoms.length, meshes.length)
    for (let mesh = 0; mesh < bottoms.length; mesh++) {
      const actual = bottoms[mesh].geometry, original = meshes[mesh].geometry
      const plate = new Set(fitting.rear_plate_changes?.find(change => change.primitive === mesh)?.vertices ?? [])
      const replacement = mesh === 0 ? fitting.rear_guard_replacement : undefined
      const replaced = new Set(replacement?.destination_vertices ?? [])
      const tabs = new Set(mesh === 0 ? [...(fitting.rear_tab_vertices ?? []), ...(fitting.guard_bend_vertices ?? [])] : [])
      const translated = new Set(mesh === fitting.rear_guard_translation?.primitive ? fitting.rear_guard_translation.vertices : [])
      if (replacement) {
        const removed = new Set(replacement.removed_face_indices)
        const mapping = new Map(replacement.source_vertices.map((vertex, i) => [vertex, replacement.destination_vertices[i]]))
        const expected = Array.from(original.index.array).filter((_, i) => !removed.has(Math.floor(i / 3)))
        for (const face of replacement.source_face_indices)
          for (let k = 0; k < 3; k++) expected.push(mapping.get(original.index.getX(face * 3 + k)))
        assert.deepEqual(Array.from(actual.index.array), expected)
      } else assert.deepEqual(actual.index.array, original.index.array)
      for (const [name, attribute] of Object.entries(actual.attributes)) {
        const before = original.attributes[name]
        assert.equal(attribute.count, before.count + (replacement ? replacement.destination_vertices.length - replacement.removed_vertices.length : 0))
        for (let vertex = 0; vertex < attribute.count; vertex++) {
          if (translated.has(vertex) && name === 'position') {
            for (let k = 0; k < 3; k++)
              assert.equal(attribute.getComponent(vertex, k), Math.fround(before.getComponent(vertex, k) + fitting.rear_guard_translation.offset[k]))
            continue
          }
          if (tabs.has(vertex) && ['position', 'normal', 'tangent'].includes(name)) continue
          if (replaced.has(vertex)) continue
          if (plate.has(vertex) && ['position', 'normal', 'tangent'].includes(name)) continue
          if (mesh === 0 && strapUV.has(vertex) && ['uv', 'tangent'].includes(name)) continue
          if (mesh === 0 && leather.has(vertex) && name === 'position') continue
          if (mesh === 0 && rear.has(vertex) && ['skinIndex', 'skinWeight'].includes(name)) continue
          if (mesh === 0 && selected.has(vertex) && name !== 'uv') continue
          if (mesh === 0 && buckle.has(vertex) && name !== 'uv') continue
          if (mesh === 0 && waist.has(vertex) && ['position', 'normal', 'tangent'].includes(name)) continue
          for (let k = 0; k < attribute.itemSize; k++)
            assert.equal(attribute.getComponent(vertex, k), before.getComponent(vertex, k))
        }
      }
    }
    const { bottom, rest } = regions[0]
    const { skinIndex, skinWeight } = bottom.geometry.attributes
    const hips = vertex => skeleton.bones[skinIndex.getX(vertex)].name === 'Hips' && skinWeight.getX(vertex) === 1
    const belt = rest.flatMap((point, vertex) => !selected.has(vertex) && Math.abs(point.x) > .025 && Math.abs(point.x) < .06 && point.y > .57 && point.y < .61 && point.z > .04 && hips(vertex) ? [vertex] : [])
    for (const vertex of selected) {
      if (rest[vertex].y < (fitting.attachment_min_y ?? .575)) continue
      assert.ok(hips(vertex))
      const anchor = belt.reduce((best, candidate) => rest[vertex].distanceTo(rest[candidate]) < rest[vertex].distanceTo(rest[best]) ? candidate : best)
      const distance = rest[vertex].distanceTo(rest[anchor])
      assert.ok(distance < .006, `strap attachment distance ${distance}`)
      attachmentPairs.push({ vertex, anchor, distance })
    }
    assert.ok(attachmentPairs.length > 10)
  }
  const clips = []
  const sample = clipSampler(body, { samples: 61, restore: skeleton.bones })
  for (const clip of base.animations) {
    let maximumMotion = 0, maximumRigidStretch = 0, maximumAttachmentDrift = 0, maximumBuckleGap = 0
    for (const _ of sample(clip)) {
      for (const { bottom, rest, rigidEdges } of regions) {
        const posed = rest.map((_, i) => bottom.getVertexPosition(i, new THREE.Vector3()))
        for (let i = 0; i < posed.length; i++) {
          assert.ok(posed[i].toArray().every(Number.isFinite))
          maximumMotion = Math.max(maximumMotion, posed[i].distanceTo(rest[i]))
        }
        for (const [a, b, length] of rigidEdges)
          maximumRigidStretch = Math.max(maximumRigidStretch, Math.abs(posed[a].distanceTo(posed[b]) / length - 1))
      }
      for (const { vertex, anchor, distance } of attachmentPairs) {
        const bottom = bottoms[0]
        const a = bottom.getVertexPosition(vertex, new THREE.Vector3())
        const b = bottom.getVertexPosition(anchor, new THREE.Vector3())
        maximumAttachmentDrift = Math.max(maximumAttachmentDrift, Math.abs(a.distanceTo(b) - distance))
      }
      for (const { vertices, anchor } of bucklePairs) {
        const center = vertices.reduce((sum, vertex) => sum.add(bottoms[0].getVertexPosition(vertex, new THREE.Vector3())), new THREE.Vector3()).divideScalar(vertices.length)
        maximumBuckleGap = Math.max(maximumBuckleGap, center.distanceTo(bottoms[0].getVertexPosition(anchor, new THREE.Vector3())))
      }
    }
    assert.ok(maximumRigidStretch < .001, `${clip.name}: plate stretch ${maximumRigidStretch}`)
    assert.ok(maximumAttachmentDrift < 1e-6, `${clip.name}: strap attachment drift ${maximumAttachmentDrift}`)
    assert.ok(maximumBuckleGap < .004, `${clip.name}: side buckle gap ${maximumBuckleGap}`)
    clips.push({ name: clip.name, samples: 61, maximum_motion: maximumMotion, maximum_rigid_edge_stretch: maximumRigidStretch, maximum_attachment_drift: maximumAttachmentDrift, ...(bucklePairs.length ? { maximum_buckle_gap: maximumBuckleGap } : {}) })
  }
  const original = bodyMesh.geometry
  const originalIndices = Array.from(original.index.array)
  const topMask = JSON.parse(readFileSync('assets/items/female_knight_top/tripo_v1/fitted_v3/body-occlusion.json'))
  const bottomMask = JSON.parse(readFileSync(`${directory}/body-occlusion.json`))
  const mask = femaleOutfitMask(base)
  assert.throws(() => mask.register('invalid', { ...bottomMask, primitive_triangles: 1 }))
  assert.equal(bodyMesh.geometry, original)
  mask.register('top', topMask)
  mask.setEquipped('top', true)
  mask.register('bottom', bottomMask)
  const cases = []
  for (const [top, lower] of [[true, true], [false, true], [false, false], [true, false], [true, true]]) {
    mask.setEquipped('top', top)
    mask.setEquipped('bottom', lower)
    const hidden = new Set([...(top ? topMask.hide_triangle_indices : []), ...(lower ? bottomMask.hide_triangle_indices : [])])
    const expected = originalIndices.filter((_, offset) => !hidden.has(Math.floor(offset / 3)))
    assert.deepEqual(Array.from(bodyMesh.geometry.index.array), expected)
    cases.push({ top, bottom: lower, hidden_triangles: hidden.size })
  }
  mask.unregister('bottom')
  assert.equal(bodyMesh.geometry.index.count, original.index.count - topMask.hide_triangle_indices.length * 3)
  mask.dispose()
  assert.equal(bodyMesh.geometry, original)
  const report = {
    date: ['v1', 'v2'].includes(version) ? '2026-10-12' : '2026-10-13', base: { path: basePath, sha256: hash(basePath) },
    bottom: { path: partPath, sha256: hash(partPath) }, triangles: regions.reduce((sum, region) => sum + region.triangles, 0), meshes: bottoms.length, bones: 65,
    preview_animations: { path: previewAnimations, sha256: hash(previewAnimations) },
    exact_runtime_bind: true, unchanged_rest_shape: true, normalized_weights: true, no_opposite_leg_influence: true,
    rigid_edges_checked: rigidEdgeCount, attachment_vertices_checked: attachmentPairs.length, clips, reversible_mask_union: cases,
    scope: 'Runtime binding and deformation validity; rigid regions retain edge lengths. This does not prove collision-free motion or watertight geometry.'
  }
  writeFileSync(`${directory}/runtime-validation.json`, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ ...report, clips: clips.map(clip => clip.name) }))
} finally {
  await server.close()
}
