import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const directory = 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
const bottomPath = `${directory}/bottom_female_barbarian.glb`
const mask = JSON.parse(readFileSync(`${directory}/body-occlusion.json`))
const fitting = JSON.parse(readFileSync('doc/assets/modular-female-barbarian-bottom-fitting-v1.json'))
const beltBottom = fitting.alignment.belt_center_height - .03
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { scene: body, animations } = await load(basePath)
  const [bottom, ...rest_] = bindModularPart(body, (await load(bottomPath)).scene)
  assert.equal(rest_.length, 0)
  body.updateMatrixWorld(true)
  const bones = bottom.skeleton.bones
  let bodyMesh
  body.traverse(object => { if (object.isSkinnedMesh && !bodyMesh) bodyMesh = object })
  assert.equal(bones.length, 65)
  for (let i = 0; i < bones.length; i++) {
    assert.equal(bones[i], bodyMesh.skeleton.bones[i])
    const actual = bottom.skeleton.boneInverses[i].elements
    const expected = bodyMesh.skeleton.boneInverses[i].elements
    assert.ok(actual.every((v, k) => Math.abs(v - expected[k]) < 1e-7))
  }
  const position = bottom.geometry.attributes.position
  const weights = bottom.geometry.attributes.skinWeight
  const joints = bottom.geometry.attributes.skinIndex
  const rest = []
  const signature = []
  for (let i = 0; i < position.count; i++) {
    const point = bottom.getVertexPosition(i, new THREE.Vector3())
    assert.ok(point.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 1e-6)
    rest.push(point)
    assert.ok(Math.abs(weights.getX(i) + weights.getY(i) + weights.getZ(i) + weights.getW(i) - 1) < 1e-6)
    const influences = []
    for (let k = 0; k < 4; k++) {
      const weight = weights.getComponent(i, k)
      if (!weight) continue
      const name = bones[joints.getComponent(i, k)].name
      assert.ok(!/Shoulder|Arm|Hand|Neck|Head|Spine1|Spine2/.test(name), `upper-body influence ${name}`)
      influences.push(`${name}:${weight.toFixed(4)}`)
    }
    signature.push(influences.sort().join(' '))
  }
  // Medallion, rings and loops are rigid: every vertex of a piece carries one shared weight set.
  const counts = new Map()
  for (const key of signature) counts.set(key, (counts.get(key) ?? 0) + 1)
  const index = bottom.geometry.index
  const parent = rest.map((_, i) => i)
  const find = i => { while (parent[i] !== i) i = parent[i] = parent[parent[i]]; return i }
  const welded = new Map()
  rest.forEach((point, i) => {
    const key = point.toArray().map(v => v.toFixed(6)).join()
    if (welded.has(key)) parent[find(i)] = find(welded.get(key)); else welded.set(key, i)
  })
  for (let i = 0; i < index.count; i += 3)
    for (let k = 1; k < 3; k++) parent[find(index.getX(i + k))] = find(index.getX(i))
  const pieceKeys = new Map()
  rest.forEach((_, i) => {
    const root = find(i)
    if (!pieceKeys.has(root)) pieceKeys.set(root, new Set())
    pieceKeys.get(root).add(signature[i])
  })
  const rigidKeys = new Set([...counts].filter(([key, count]) => count >= 30 &&
    [...pieceKeys.values()].some(keys => keys.size === 1 && keys.has(key))).map(([key]) => key))
  const shellEdges = [], allEdges = []
  for (let i = 0; i < index.count; i += 3)
    for (let k = 0; k < 3; k++) {
      const a = index.getX(i + k), b = index.getX(i + (k + 1) % 3)
      const length = rest[a].distanceTo(rest[b])
      if (length > .003) allEdges.push([a, b, length])
      if (length > .001 && signature[a] === signature[b] && rigidKeys.has(signature[a])) shellEdges.push([a, b, length])
    }
  assert.ok(shellEdges.length > 100)
  const region = rest.map((point, i) => rigidKeys.has(signature[i]) ? 'fittings' : point.y > beltBottom ? 'belt' : 'fur')

  // Depth is measured against the nearest visible skin vertex along its skinned normal.
  const hidden = new Set(mask.hide_triangle_indices)
  const bodyIndex = bodyMesh.geometry.index
  const visible = new Set()
  for (let t = 0; t < bodyIndex.count / 3; t++)
    if (!hidden.has(t)) for (let k = 0; k < 3; k++) visible.add(bodyIndex.getX(t * 3 + k))
  const skinRest = [...visible].map(j => [j, bodyMesh.getVertexPosition(j, new THREE.Vector3())])
  const bodyNormal = bodyMesh.geometry.attributes.normal
  const pairs = rest.map(point => {
    let best, distance = Infinity
    for (const [j, skin] of skinRest) {
      const d = skin.distanceToSquared(point)
      if (d < distance) { distance = d; best = j }
    }
    return best
  })
  const skinNormal = (j, matrix = new THREE.Matrix4(), target = new THREE.Vector3()) => {
    const elements = new Array(16).fill(0)
    for (let k = 0; k < 4; k++) {
      const weight = bodyMesh.geometry.attributes.skinWeight.getComponent(j, k)
      if (!weight) continue
      const bone = bodyMesh.skeleton.bones[bodyMesh.geometry.attributes.skinIndex.getComponent(j, k)]
      matrix.multiplyMatrices(bone.matrixWorld, bodyMesh.skeleton.boneInverses[bodyMesh.skeleton.bones.indexOf(bone)])
      matrix.elements.forEach((v, e) => { elements[e] += v * weight })
    }
    return target.fromBufferAttribute(bodyNormal, j).transformDirection(matrix.fromArray(elements))
  }
  const depth = (points) => points.map((point, i) => {
    const skin = bodyMesh.getVertexPosition(pairs[i], new THREE.Vector3())
    return point.clone().sub(skin).dot(skinNormal(pairs[i]))
  })
  const restDepth = depth(rest)
  const sample = clipSampler(body, { samples: 121, restore: bones })
  const clips = []
  for (const clip of animations) {
    let maximumMotion = 0, maximumEdgeRatio = 0, deepest = 0, worstCount = 0, worstRegions = {}, shellChange = 0
    const posed = []
    for (const _ of sample(clip)) {
      for (let i = 0; i < position.count; i++) {
        const point = bottom.getVertexPosition(i, new THREE.Vector3())
        assert.ok(point.toArray().every(Number.isFinite))
        posed[i] = point
        maximumMotion = Math.max(maximumMotion, point.distanceTo(rest[i]))
      }
      for (const [a, b, length] of allEdges)
        maximumEdgeRatio = Math.max(maximumEdgeRatio, posed[a].distanceTo(posed[b]) / length)
      for (const [a, b, length] of shellEdges)
        shellChange = Math.max(shellChange, Math.abs(posed[a].distanceTo(posed[b]) / length - 1))
      const values = depth(posed)
      let count = 0
      const regions = { belt: 0, fur: 0, fittings: 0 }
      values.forEach((value, i) => {
        if (value < -.002 && restDepth[i] - value > .002) {
          count++
          deepest = Math.max(deepest, -value)
          regions[region[i]]++
        }
      })
      if (count > worstCount) worstRegions = regions
      worstCount = Math.max(worstCount, count)
    }
    assert.ok(shellChange < .03, `${clip.name}: rigid fittings distorted by ${shellChange}`)
    clips.push({ name: clip.name, samples: 121, maximum_motion: maximumMotion, maximum_edge_length_ratio: maximumEdgeRatio,
      maximum_rigid_edge_length_change: shellChange, maximum_penetrating_vertices: worstCount,
      penetrating_regions_at_worst: worstRegions, maximum_penetration: deepest })
  }
  const report = { date: '2026-10-15', base: { path: basePath, sha256: hash(basePath) }, bottom: { path: bottomPath, sha256: hash(bottomPath) },
    triangles: index.count / 3, vertices: position.count, bones: bones.length, exact_bind_compatibility: true, normalized_weights: true,
    unchanged_rest_shape: true, no_upper_body_influence: true,
    rigid_fittings: { pieces: rigidKeys.size, vertices: signature.filter(key => rigidKeys.has(key)).length, checked_edges: shellEdges.length },
    clips,
    scope: 'Runtime binding through bindModularPart, rest shape, finite deformation, rigid medallion/rings/loops, edge stretch reported, and penetration (>2 mm deeper than rest) against the nearest visible skin vertex along its skinned normal. Approximate: not a full mesh collision test.' }
  writeFileSync(new URL('../doc/assets/modular-female-barbarian-bottom-animation-v1.json', import.meta.url), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(clips.map(c => [c.name, c.maximum_penetrating_vertices, +c.maximum_penetration.toFixed(4), +c.maximum_edge_length_ratio.toFixed(2), c.penetrating_regions_at_worst])))
} finally {
  await server.close()
}
