import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const directory = 'assets/items/female_barbarian_top/tripo_v1/fitted_v1'
const topPath = `${directory}/top_female_barbarian.glb`
const mask = JSON.parse(readFileSync(`${directory}/body-occlusion.json`))
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { scene: body, animations } = await load(basePath)
  const [top, ...rest_] = bindModularPart(body, (await load(topPath)).scene)
  assert.equal(rest_.length, 0)
  body.updateMatrixWorld(true)
  const bones = top.skeleton.bones
  let bodyMesh
  body.traverse(object => { if (object.isSkinnedMesh && !bodyMesh) bodyMesh = object })
  assert.equal(bones.length, 65)
  for (let i = 0; i < bones.length; i++) {
    assert.equal(bones[i], bodyMesh.skeleton.bones[i])
    const actual = top.skeleton.boneInverses[i].elements
    const expected = bodyMesh.skeleton.boneInverses[i].elements
    assert.ok(actual.every((v, k) => Math.abs(v - expected[k]) < 1e-7))
  }
  const position = top.geometry.attributes.position
  const weights = top.geometry.attributes.skinWeight
  const joints = top.geometry.attributes.skinIndex
  const rest = []
  const signature = []
  for (let i = 0; i < position.count; i++) {
    const point = top.getVertexPosition(i, new THREE.Vector3())
    assert.ok(point.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 1e-6)
    rest.push(point)
    assert.ok(Math.abs(weights.getX(i) + weights.getY(i) + weights.getZ(i) + weights.getW(i) - 1) < 1e-6)
    const influences = []
    for (let k = 0; k < 4; k++) {
      const weight = weights.getComponent(i, k)
      if (!weight) continue
      const name = bones[joints.getComponent(i, k)].name
      influences.push(`${name}:${weight.toFixed(4)}`)
      if (Math.abs(point.x) < 1e-4) continue
      const side = point.x > 0 ? 'Right' : 'Left'
      assert.ok(!(name.startsWith(side) && /Shoulder|Arm/.test(name)), `opposite-side ${name}`)
    }
    signature.push(influences.sort().join(' '))
  }
  const counts = new Map()
  for (const key of signature) counts.set(key, (counts.get(key) ?? 0) + 1)
  const common = (test) => [...counts].filter(([key]) => test(key)).sort((a, b) => b[1] - a[1])[0]?.[0]
  const named = { jewel: common(key => /Spine1/.test(key) && !/Shoulder|Arm/.test(key)), pauldron: common(key => /^Right(Shoulder|Arm):1.0000$/.test(key)) }
  assert.ok(named.jewel && named.pauldron, 'rigid shells not found')
  // Soft cups follow the skin; their edge change is reported, not bounded.
  const cup = rest.map((point, i) => point.y > .70 && point.y < .80 && point.z > .03 && signature[i] !== named.jewel && signature[i] !== named.pauldron)

  const index = top.geometry.index
  const rigidEdges = Object.fromEntries(Object.keys(named).map(name => [name, []]))
  const allEdges = [], cupEdges = []
  for (let i = 0; i < index.count; i += 3)
    for (let k = 0; k < 3; k++) {
      const a = index.getX(i + k), b = index.getX(i + (k + 1) % 3)
      const length = rest[a].distanceTo(rest[b])
      if (length > .003) allEdges.push([a, b, length])
      for (const [name, key] of Object.entries(named))
        if (length > .001 && signature[a] === key && signature[b] === key) rigidEdges[name].push([a, b, length])
      if (length > .003 && cup[a] && cup[b]) cupEdges.push([a, b, length])
    }
  for (const edges of Object.values(rigidEdges)) assert.ok(edges.length > 100)

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
    let maximumMotion = 0, maximumEdgeRatio = 0, deepest = 0, worstCount = 0, worstRegions = {}, cupStretch = 0
    const rigid = Object.fromEntries(Object.keys(named).map(name => [name, 0]))
    const posed = []
    for (const _ of sample(clip)) {
      for (let i = 0; i < position.count; i++) {
        const point = top.getVertexPosition(i, new THREE.Vector3())
        assert.ok(point.toArray().every(Number.isFinite))
        posed[i] = point
        maximumMotion = Math.max(maximumMotion, point.distanceTo(rest[i]))
      }
      for (const [a, b, length] of allEdges)
        maximumEdgeRatio = Math.max(maximumEdgeRatio, posed[a].distanceTo(posed[b]) / length)
      for (const [name, edges] of Object.entries(rigidEdges))
        for (const [a, b, length] of edges)
          rigid[name] = Math.max(rigid[name], Math.abs(posed[a].distanceTo(posed[b]) / length - 1))
      for (const [a, b, length] of cupEdges)
        cupStretch = Math.max(cupStretch, Math.abs(posed[a].distanceTo(posed[b]) / length - 1))
      const values = depth(posed)
      let count = 0
      const regions = { cups: 0, pauldron: 0, straps: 0 }
      values.forEach((value, i) => {
        const loss = restDepth[i] - value
        if (value < -.002 && loss > .002) {
          count++
          deepest = Math.max(deepest, -value)
          regions[cup[i] || signature[i] === named.jewel ? 'cups' : signature[i] === named.pauldron ? 'pauldron' : 'straps']++
        }
      })
      if (count > worstCount) worstRegions = regions
      worstCount = Math.max(worstCount, count)
    }
    assert.ok(maximumEdgeRatio < 6, `${clip.name}: garment edge stretched ${maximumEdgeRatio} times`)
    for (const [name, value] of Object.entries(rigid)) assert.ok(value < .03, `${clip.name}: ${name} distorted by ${value}`)
    clips.push({ name: clip.name, samples: 121, maximum_motion: maximumMotion, maximum_edge_length_ratio: maximumEdgeRatio,
      maximum_rigid_edge_length_change: rigid, maximum_cup_edge_length_change: cupStretch, maximum_penetrating_vertices: worstCount, penetrating_regions_at_worst: worstRegions, maximum_penetration: deepest })
  }
  const report = { date: '2026-10-14', base: { path: basePath, sha256: hash(basePath) }, top: { path: topPath, sha256: hash(topPath) },
    triangles: index.count / 3, vertices: position.count, bones: bones.length, exact_bind_compatibility: true, normalized_weights: true,
    unchanged_rest_shape: true, no_opposite_arm_influence: true,
    rigid_shells: Object.fromEntries(Object.entries(named).map(([name, key]) => [name, { influences: key, vertices: counts.get(key), checked_edges: rigidEdges[name].length }])),
    clips,
    scope: 'Runtime binding through bindModularPart, rest shape, finite deformation, rigid jewel/pauldron, reported soft-cup edge change, and penetration (>2 mm deeper than rest) against the nearest visible skin vertex along its skinned normal. Approximate: not a full mesh collision test.' }
  writeFileSync(new URL('../doc/assets/modular-female-barbarian-top-animation-v1.json', import.meta.url), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ rigid_shells: report.rigid_shells, clips: clips.map(c => [c.name, c.maximum_penetrating_vertices, +c.maximum_penetration.toFixed(4), +c.maximum_cup_edge_length_change.toFixed(4), +c.maximum_rigid_edge_length_change.pauldron.toFixed(4)]) }, null, 1))
} finally {
  await server.close()
}
