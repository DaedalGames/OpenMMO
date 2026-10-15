import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const directory = 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1'
const bottomPath = `${directory}/bottom_female_barbarian.glb`
const fitting = JSON.parse(readFileSync(`${directory}/panel_weights_v1/repair.json`))
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { updatePeltPhysics, disposePeltPhysics } = await server.ssrLoadModule('/src/lib/effects/pelt-rig.ts')
  const { scene: body, animations } = await load(basePath)
  const parts = bindModularPart(body, (await load(bottomPath)).scene)
  const [baseline] = bindModularPart(body, (await load(fitting.source)).scene)
  baseline.visible = false
  let skin
  body.traverse(object => { if (object.isSkinnedMesh && !skin) skin = object })
  body.updateMatrixWorld(true)
  const bones = skin.skeleton.bones
  const snapshots = parts.map(mesh => {
    assert.equal(mesh.skeleton.bones.length, bones.length)
    for (let i = 0; i < bones.length; i++) {
      assert.equal(mesh.skeleton.bones[i], bones[i])
      assert.deepEqual(mesh.skeleton.boneInverses[i].elements, skin.skeleton.boneInverses[i].elements)
    }
    const geometry = mesh.geometry, position = geometry.attributes.position
    const weights = geometry.attributes.skinWeight, joints = geometry.attributes.skinIndex
    const points = []
    for (let i = 0; i < position.count; i++) {
      const rest = new THREE.Vector3().fromBufferAttribute(position, i)
      assert.ok(rest.distanceTo(mesh.getVertexPosition(i, new THREE.Vector3())) < 1e-6)
      points.push(rest)
      assert.ok(Math.abs(weights.getX(i) + weights.getY(i) + weights.getZ(i) + weights.getW(i) - 1) < 1e-6)
      for (let k = 0; k < 4; k++)
        if (weights.getComponent(i, k))
          assert.ok(!/Shoulder|Arm|Hand|Neck|Head|Spine1|Spine2/.test(bones[joints.getComponent(i, k)].name))
    }
    const edges = []
    const config = mesh.userData.pelt_physics
    for (let i = 0; i < geometry.index.count; i += 3)
      for (let k = 0; k < 3; k++) {
        const a = geometry.index.getX(i + k), b = geometry.index.getX(i + (k + 1) % 3)
        const length = points[a].distanceTo(points[b])
        if (length < .003) continue
        if (config && (points[a].y > config.pivot[1] - .025 || points[b].y > config.pivot[1] - .025)) continue
        edges.push([a, b, length])
      }
    return { mesh, geometry, points, edges }
  })
  const samples = 17
  const sample = clipSampler(body, { samples, restore: bones })
  const clips = []
  const inverseHip = new THREE.Matrix4(), hipSkin = new THREE.Matrix4(), point = new THREE.Vector3()
  for (const clip of animations) {
    let maximumRatio = 0, widthRatio = 0, colliderPoints = 0, beforeWidthRatio = 0, beforeColliderPoints = 0
    for (const _ of sample(clip)) {
      updatePeltPhysics(body, 0, null, 1 / 60, true)
      hipSkin.multiplyMatrices(bones[0].matrixWorld, skin.skeleton.boneInverses[0])
      inverseHip.copy(hipSkin).invert()
      let inside = 0, beforeInside = 0
      for (const { mesh, points, edges } of snapshots) {
        const posed = points.map((_, i) => mesh.getVertexPosition(i, new THREE.Vector3()))
        assert.ok(posed.every(p => p.toArray().every(Number.isFinite)))
        for (const [a, b, length] of edges)
          maximumRatio = Math.max(maximumRatio, posed[a].distanceTo(posed[b]) / length)
        const config = mesh.userData.pelt_physics
        if (!config) continue
        const sourceIds = fitting.parts[mesh.userData.panel]
        if (mesh.userData.panel === 'front') {
          const ids = points.map((p, i) => p.y < config.pivot[1] - .035 ? i : -1).filter(i => i >= 0)
          const restWidth = Math.max(...ids.map(i => points[i].x)) - Math.min(...ids.map(i => points[i].x))
          const values = ids.map(i => posed[i].clone().applyMatrix4(inverseHip).x)
          widthRatio = Math.max(widthRatio, (Math.max(...values) - Math.min(...values)) / restWidth)
          const before = ids.map(i => baseline.getVertexPosition(sourceIds[i], new THREE.Vector3()).applyMatrix4(inverseHip).x)
          beforeWidthRatio = Math.max(beforeWidthRatio, (Math.max(...before) - Math.min(...before)) / restWidth)
        }
        if (!['left', 'right'].includes(mesh.userData.panel)) continue
        for (const collider of config.colliders) {
          const index = bones.findIndex(bone => bone.name === collider.bone)
          const world = new THREE.Matrix4().multiplyMatrices(bones[index].matrixWorld, skin.skeleton.boneInverses[index])
            .multiply(new THREE.Matrix4().makeScale(...collider.radii).setPosition(...collider.center)).invert()
          for (let i = 0; i < posed.length; i++)
            if (points[i].y < config.pivot[1] - .025) {
              if (point.copy(posed[i]).applyMatrix4(world).lengthSq() < 1) inside++
              if (baseline.getVertexPosition(sourceIds[i], point).applyMatrix4(world).lengthSq() < 1) beforeInside++
            }
        }
      }
      colliderPoints = Math.max(colliderPoints, inside)
      beforeColliderPoints = Math.max(beforeColliderPoints, beforeInside)
    }
    assert.ok(widthRatio < 1.15, `${clip.name}: front panel width ${widthRatio}`)
    clips.push({ name: clip.name, samples, maximum_edge_length_ratio: maximumRatio, maximum_front_width_ratio: widthRatio,
      maximum_side_vertices_inside_thigh_collider: colliderPoints,
      before_front_width_ratio: beforeWidthRatio, before_side_vertices_inside_thigh_collider: beforeColliderPoints })
  }
  disposePeltPhysics(body)
  for (const { mesh, geometry } of snapshots) assert.equal(mesh.geometry, geometry)
  const report = { date: '2026-10-15', base: { path: basePath, sha256: hash(basePath) }, bottom: { path: bottomPath, sha256: hash(bottomPath) },
    triangles: snapshots.reduce((n, p) => n + p.geometry.index.count / 3, 0), vertices: snapshots.reduce((n, p) => n + p.points.length, 0),
    bones: bones.length, parts: parts.length, exact_bind_compatibility: true, normalized_weights: true,
    unchanged_rest_shape: true, no_upper_body_influence: true, physics_geometry_restored_on_dispose: true, clips,
    scope: 'Runtime binding and existing pelt bending/collision across all base clips; front width, lower-panel edge stretch, finite deformation, collider overlap and disposal. Collider counts approximate body contact; not a triangle collision audit.' }
  writeFileSync('doc/assets/modular-female-barbarian-bottom-animation-v1.json', JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(clips))
} finally {
  await server.close()
}
