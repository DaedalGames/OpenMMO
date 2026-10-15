import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'
const dir =
  process.argv[2] ?? 'assets/items/female_barbarian_boots/tripo_v1/fitted_v3'
const side = process.argv[3] ?? 'right'
if (!['right', 'left'].includes(side)) throw new Error('Expected right or left')
const prefix = side === 'right' ? 'clearance' : 'clearance-left'
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule(
    '/src/lib/utils/modularCharacter.ts'
  )
  const { femaleBootGround } = await server.ssrLoadModule(
    '/src/lib/utils/female-boot-ground.ts'
  )
  const { femaleSeatOffset } = await server.ssrLoadModule(
    '/src/previews/female-seat.ts'
  )
  const base = await load(
    'assets/modular_human_female_01/rig_v1/female-base.glb'
  )
  for (const data of JSON.parse(
    readFileSync('assets/modular_human_female_01/preview/animations.json')
  ).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex((entry) => entry.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  const asset = await load(`${dir}/boots_female_barbarian.glb`)
  const boots = bindModularPart(base.scene, asset.scene)
  let body
  base.scene.traverse((n) => {
    if (n.isSkinnedMesh && base.parser.associations.get(n)?.primitives === 0)
      body = n
  })
  const ground = femaleBootGround(
    base.scene,
    body,
    boots,
    asset.scene.userData.heel_pose
  )
  const indices = []
  const p = new THREE.Vector3()
  const bp = body.geometry.attributes.position
  for (let i = 0; i < bp.count; i++)
    if (
      (side === 'right' ? bp.getX(i) < -0.02 : bp.getX(i) > 0.02) &&
      bp.getY(i) < 0.28
    )
      indices.push(i)
  const remap = new Map(indices.map((v, i) => [v, i]))
  const hidden = new Set(
    JSON.parse(readFileSync(`${dir}/body-occlusion.json`)).hide_triangle_indices
  )
  const bf = body.geometry.index,
    faces = []
  for (let i = 0; i < bf.count; i += 3) {
    const tri = [bf.getX(i), bf.getX(i + 1), bf.getX(i + 2)]
    if (!hidden.has(i / 3) && tri.every((v) => remap.has(v)))
      faces.push(tri.map((v) => remap.get(v)))
  }
  const boot = boots.find((m) => m.name.endsWith(side))
  const poses = []
  const data = []
  const capture = (name, time) => {
    poses.push({ name, time })
    base.scene.updateMatrixWorld(true)
    body.skeleton.update()
    const values = new Float32Array(
      (indices.length + boot.geometry.attributes.position.count) * 3
    )
    let offset = 0
    for (const i of indices) {
      body.getVertexPosition(i, p)
      p.toArray(values, offset)
      offset += 3
    }
    for (let i = 0; i < boot.geometry.attributes.position.count; i++) {
      boot.getVertexPosition(i, p)
      p.toArray(values, offset)
      offset += 3
    }
    data.push(Buffer.from(values.buffer))
  }
  ground.apply()
  capture('rest', 0)
  ground.restore()
  const sample = clipSampler(base.scene, {
    samples: 61,
    restore: body.skeleton.bones,
  })
  for (const clip of base.animations)
    for (const { time } of sample(clip)) {
      ground.apply(
        clip.name === 'sit_idle' ? femaleSeatOffset : undefined,
        clip.name
      )
      capture(clip.name, time)
      ground.restore()
    }
  writeFileSync(`${dir}/${prefix}-poses.bin`, Buffer.concat(data))
  writeFileSync(
    `${dir}/${prefix}-poses.json`,
    JSON.stringify({
      side,
      source_sha256: hash(`${dir}/boots_female_barbarian.glb`),
      poses,
      body_indices: indices,
      body_faces: faces,
      boot_faces: Array.from(boot.geometry.index.array),
      boot_vertices: boot.geometry.attributes.position.count,
      bones: body.skeleton.bones.length,
    })
  )
  console.log({
    poses: poses.length,
    body: indices.length,
    boot: boot.geometry.attributes.position.count,
  })
} finally {
  await server.close()
}
