import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const directory = 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
const bottomPath = `${directory}/bottom_female_barbarian.glb`
const runtime = 'client/public/models/characters/modular_female'
const runtimeBase = `${runtime}/base.glb`, runtimeBottom = `${runtime}/barbarian_bottom.glb`
const stitchedBeltSeams = 68

function seamGroups(snapshots) {
  const groups = new Map()
  for (const { mesh, points } of snapshots)
    points.forEach((point, i) => {
      const key = point.toArray().map(v => v.toFixed(6)).join(',')
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key).push({ mesh, i })
    })
  return [...groups.values()].filter(group =>
    group.some(v => v.mesh.userData.panel === 'belt') &&
    group.some(v => v.mesh.userData.panel !== 'belt'))
}

const restPoints = mesh => {
  const position = mesh.geometry.attributes.position
  return Array.from({ length: position.count }, (_, i) => new THREE.Vector3().fromBufferAttribute(position, i))
}

const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { updatePeltPhysics, disposePeltPhysics } = await server.ssrLoadModule('/src/lib/effects/pelt-rig.ts')
  const { scene: sourceBody } = await load(basePath)
  const sourceParts = bindModularPart(sourceBody, (await load(bottomPath)).scene)
  let sourceSkin
  sourceBody.traverse(object => { if (object.isSkinnedMesh && !sourceSkin) sourceSkin = object })
  sourceBody.updateMatrixWorld(true)
  const sourceBones = sourceSkin.skeleton.bones
  const sourceSnapshots = sourceParts.map(mesh => {
    assert.equal(mesh.skeleton.bones.length, sourceBones.length)
    for (let i = 0; i < sourceBones.length; i++) {
      assert.equal(mesh.skeleton.bones[i], sourceBones[i])
      assert.deepEqual(mesh.skeleton.boneInverses[i].elements, sourceSkin.skeleton.boneInverses[i].elements)
    }
    const { skinWeight: weights, skinIndex: joints } = mesh.geometry.attributes
    const points = restPoints(mesh)
    points.forEach((rest, i) => {
      assert.ok(rest.distanceTo(mesh.getVertexPosition(i, new THREE.Vector3())) < 1e-6)
      assert.ok(Math.abs(weights.getX(i) + weights.getY(i) + weights.getZ(i) + weights.getW(i) - 1) < 1e-6)
      for (let k = 0; k < 4; k++)
        if (weights.getComponent(i, k))
          assert.ok(!/Shoulder|Arm|Hand|Neck|Head|Spine1|Spine2/.test(sourceBones[joints.getComponent(i, k)].name))
    })
    return { mesh, points }
  })
  assert.equal(seamGroups(sourceSnapshots).length, stitchedBeltSeams)

  // Motion runs on the packaged GLB because only it carries the robe_physics the game uses.
  const { scene: body, animations } = await load(runtimeBase)
  const parts = bindModularPart(body, (await load(runtimeBottom)).scene)
  const panels = parts.filter(mesh => mesh.userData.robe_physics)
  assert.equal(panels.length, 4)
  body.updateMatrixWorld(true)
  const baseBones = parts[0].skeleton.bones.length
  const snapshots = parts.map(mesh => {
    const points = restPoints(mesh)
    const config = mesh.userData.robe_physics
    const edges = []
    if (config) {
      const fixed = new Set(config.fixed_vertices)
      const driven = i => !fixed.has(i) && points[i].y < config.driven_below_m
      const index = mesh.geometry.index
      for (let i = 0; i < index.count; i += 3)
        for (let k = 0; k < 3; k++) {
          const a = index.getX(i + k), b = index.getX(i + (k + 1) % 3)
          const length = points[a].distanceTo(points[b])
          if (length > .0054 && driven(a) && driven(b)) edges.push([a, b, length])
        }
    }
    return { mesh, geometry: mesh.geometry, points, edges }
  })
  const seams = seamGroups(snapshots)
  assert.equal(seams.length, stitchedBeltSeams)
  const samples = 17
  const sample = clipSampler(body, { samples, restore: parts[0].skeleton.bones })
  const clips = []
  for (const clip of animations.filter(clip => !clip.name.includes('|'))) {
    let maximumRatio = 0, seamGap = 0
    for (const _ of sample(clip)) {
      updatePeltPhysics(body, 0, null, 1 / 60, true)
      for (const panel of panels) assert.equal(panel.skeleton, panels[0].skeleton)
      for (const group of seams) {
        const belt = group.find(v => v.mesh.userData.panel === 'belt')
        const anchor = belt.mesh.getVertexPosition(belt.i, new THREE.Vector3())
        for (const { mesh, i } of group)
          seamGap = Math.max(seamGap, anchor.distanceTo(mesh.getVertexPosition(i, new THREE.Vector3())))
      }
      for (const { mesh, points, edges } of snapshots) {
        const posed = points.map((_, i) => mesh.getVertexPosition(i, new THREE.Vector3()))
        assert.ok(posed.every(p => p.toArray().every(Number.isFinite)))
        for (const [a, b, length] of edges)
          maximumRatio = Math.max(maximumRatio, posed[a].distanceTo(posed[b]) / length)
      }
    }
    assert.ok(seamGap < 1.8e-6, `${clip.name}: belt seam gap ${seamGap}`)
    // Coarse hem columns shear the fur; a centerline tear shows up as tens of times longer edges.
    assert.ok(maximumRatio < 8, `${clip.name}: robe edge stretch ${maximumRatio}`)
    clips.push({ name: clip.name, samples, maximum_driven_edge_length_ratio: maximumRatio, maximum_belt_seam_gap: seamGap })
  }
  disposePeltPhysics(body)
  for (const { mesh, geometry } of snapshots) {
    assert.equal(mesh.geometry, geometry)
    assert.equal(mesh.skeleton.bones.length, baseBones)
  }
  const report = { date: '2026-10-16',
    source: { base: { path: basePath, sha256: hash(basePath) }, bottom: { path: bottomPath, sha256: hash(bottomPath) },
      triangles: sourceParts.reduce((n, mesh) => n + mesh.geometry.index.count / 3, 0),
      vertices: sourceSnapshots.reduce((n, p) => n + p.points.length, 0), bones: sourceBones.length, parts: sourceParts.length,
      stitched_belt_seams: stitchedBeltSeams, exact_bind_compatibility: true, normalized_weights: true,
      unchanged_rest_shape: true, no_upper_body_influence: true },
    runtime: { base: { path: runtimeBase, sha256: hash(runtimeBase) }, bottom: { path: runtimeBottom, sha256: hash(runtimeBottom) },
      robe_panels: panels.length, shared_robe_skeleton: true, physics_geometry_restored_on_dispose: true, clips },
    scope: 'Static binding checks on the fitting GLB; robe-rig motion on the packaged GLB across all base clips: finite deformation, belt seam gap, stretch of robe-driven edges and disposal. No body collision check.' }
  writeFileSync('doc/assets/modular-female-barbarian-bottom-animation-v1.json', JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(clips))
} finally {
  await server.close()
}
