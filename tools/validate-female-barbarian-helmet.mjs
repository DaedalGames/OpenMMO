import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'
await ensureFemalePreview('animations')

const directory = 'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1'
const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const partPath = `${directory}/helmet_female_barbarian.glb`
const TOLERANCE = 0.00054
const CENTER = new THREE.Vector3(0, 1.692, -0.0072)

const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule(
    '/src/lib/utils/modularCharacter.ts'
  )
  const base = await load(basePath)
  for (const data of JSON.parse(
    readFileSync('assets/modular_human_female_01/preview/animations.json')
  ).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex((entry) => entry.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  let body
  base.scene.traverse((node) => {
    if (node.isSkinnedMesh && base.parser.associations.get(node)?.primitives === 0)
      body = node
  })
  const skeleton = body.skeleton
  const [helmet] = bindModularPart(base.scene, (await load(partPath)).scene)
  assert.equal(helmet.skeleton.bones.length, 65)
  for (let i = 0; i < 65; i++) {
    assert.equal(helmet.skeleton.bones[i], skeleton.bones[i])
    assert.deepEqual(helmet.skeleton.boneInverses[i].elements, skeleton.boneInverses[i].elements)
  }
  const head = skeleton.bones.findIndex((bone) => bone.name === 'Head')
  const { position, skinIndex, skinWeight } = helmet.geometry.attributes
  for (let i = 0; i < position.count; i++) {
    assert.equal(skinIndex.getX(i), head)
    assert.equal(skinWeight.getX(i), 1)
  }
  const triangles = []
  const index = helmet.geometry.index
  for (let i = 0; i < index.count; i += 3) {
    const triangle = new THREE.Triangle(
      ...[0, 1, 2].map((k) => new THREE.Vector3().fromBufferAttribute(position, index.getX(i + k)))
    )
    triangles.push({ triangle, normal: triangle.getNormal(new THREE.Vector3()) })
  }
  const box = new THREE.Box3().setFromBufferAttribute(position).expandByScalar(0.0072)
  const target = new THREE.Vector3()
  const depth = (point) => {
    if (!box.containsPoint(point)) return 0
    let best = Infinity,
      sign = 1
    for (const { triangle, normal } of triangles) {
      triangle.closestPointToPoint(point, target)
      const distance = target.distanceTo(point)
      if (distance < best) {
        best = distance
        sign = Math.sign(point.clone().sub(target).dot(normal))
      }
    }
    return sign < 0 && best > TOLERANCE && best < 0.0072 && crosses(point) ? best : 0
  }
  // Require a shell crossing because the bands are open.
  const ray = new THREE.Ray(),
    hit = new THREE.Vector3()
  const crosses = (point) => {
    const length = point.distanceTo(CENTER)
    ray.set(CENTER, point.clone().sub(CENTER).normalize())
    return triangles.some(({ triangle: { a, b, c } }) => {
      const found = ray.intersectTriangle(a, b, c, false, hit)
      return found && hit.distanceTo(CENTER) < length
    })
  }

  const attributes = body.geometry.attributes
  const name = (i) => {
    let best = 0,
      bone = ''
    for (let k = 0; k < 4; k++)
      if (attributes.skinWeight.getComponent(i, k) > best) {
        best = attributes.skinWeight.getComponent(i, k)
        bone = skeleton.bones[attributes.skinIndex.getComponent(i, k)].name
      }
    return bone
  }
  const headWeight = (i) => {
    let weight = 0
    for (let k = 0; k < 4; k++)
      if (attributes.skinIndex.getComponent(i, k) === head)
        weight += attributes.skinWeight.getComponent(i, k)
    return weight
  }
  const all = [...Array(attributes.position.count).keys()]
  const moving = all.filter((i) => headWeight(i) < 0.999)
  const point = new THREE.Vector3(),
    local = new THREE.Matrix4()
  const measure = (probe) => {
    base.scene.updateMatrixWorld(true)
    skeleton.update()
    local.multiplyMatrices(skeleton.bones[head].matrixWorld, skeleton.boneInverses[head]).invert()
    const hits = []
    for (const i of probe) {
      body.getVertexPosition(i, point).applyMatrix4(local)
      const d = depth(point)
      if (d) hits.push({ vertex: i, bone: name(i), depth_m: d })
    }
    return hits
  }
  const summary = (clip, samples) => {
    const hits = samples.flatMap(({ time, hits }) => hits.map((hit) => ({ ...hit, time })))
    return {
      name: clip,
      samples: samples.length,
      penetrating_samples: new Set(hits.map((hit) => hit.time)).size,
      regions: [...new Set(hits.map((hit) => hit.bone))],
      worst: hits.reduce((a, b) => (b.depth_m > (a?.depth_m ?? 0) ? b : a), null),
    }
  }
  const clips = [summary('rest', [{ time: 0, hits: measure(all) }])]
  const sample = clipSampler(base.scene, { samples: 33, restore: skeleton.bones })
  for (const clip of base.animations) {
    const samples = []
    for (const { time } of sample(clip)) samples.push({ time, hits: measure(moving) })
    clips.push(summary(clip.name, samples))
  }
  const report = {
    base_sha256: hash(basePath),
    helmet_sha256: hash(partPath),
    moving_probe_vertices: moving.length,
    tolerance_m: TOLERANCE,
    method:
      'Bind with the runtime bindModularPart. In Head rest space, flag body vertices behind the nearest helmet face within 7.2 mm whose segment from the head center crosses the helmet. Rest checks every body vertex; clips check vertices not fully bound to Head, 33 samples per preview clip.',
    clips,
  }
  writeFileSync(`${directory}/animation-validation.json`, JSON.stringify(report, null, 2) + '\n')
  for (const clip of clips)
    console.log(clip.name, clip.penetrating_samples, clip.regions.join(','), clip.worst?.depth_m?.toFixed(4) ?? '-')
} finally {
  await server.close()
}
