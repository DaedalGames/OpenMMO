import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { headlessThree, clipSampler, hash } from './lib/headless-three.mjs'

const directory = 'assets/items/female_knight_helmet/tripo_v1/fitted_v1'
const basePath = 'assets/modular_human_female_01/rig_v1/female-base.glb'
const partPath = `${directory}/helmet_female_knight.glb`
const { server, load } = await headlessThree()
try {
  const { bindModularPart } = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const base = await load(basePath)
  for (const data of JSON.parse(readFileSync('assets/modular_human_female_01/preview/animations.json')).clips) {
    const clip = THREE.AnimationClip.parse(data)
    const index = base.animations.findIndex(entry => entry.name === clip.name)
    if (index < 0) base.animations.push(clip)
    else base.animations[index] = clip
  }
  let body
  base.scene.traverse(node => { if (node.isSkinnedMesh && !body) body = node })
  const [helmet, ...others] = bindModularPart(base.scene, (await load(partPath)).scene)
  assert.equal(others.length, 0)
  assert.equal(helmet.geometry.index.count / 3, 2166)
  base.scene.updateMatrixWorld(true)
  const { bones, boneInverses } = helmet.skeleton
  assert.equal(bones.length, 65)
  bones.forEach((bone, i) => {
    assert.equal(bone, body.skeleton.bones[i])
    assert.deepEqual(boneInverses[i].elements, body.skeleton.boneInverses[i].elements)
  })
  const head = bones.find(bone => bone.name === 'Head')
  const inverseHead = head.matrixWorld.clone().invert()
  const { position, skinIndex, skinWeight } = helmet.geometry.attributes
  const rest = [], local = [], edges = []
  for (let i = 0; i < position.count; i++) {
    const point = helmet.getVertexPosition(i, new THREE.Vector3())
    assert.ok(point.distanceTo(new THREE.Vector3().fromBufferAttribute(position, i)) < 1e-6)
    assert.equal(bones[skinIndex.getX(i)].name, 'Head')
    assert.deepEqual([skinWeight.getX(i),skinWeight.getY(i),skinWeight.getZ(i),skinWeight.getW(i)], [1,0,0,0])
    rest.push(point)
    local.push(point.clone().applyMatrix4(inverseHead))
  }
  const index = helmet.geometry.index
  for (let i = 0; i < index.count; i += 3)
    for (let j = 0; j < 3; j++) {
      const a = index.getX(i+j), b = index.getX(i+(j+1)%3)
      const length = rest[a].distanceTo(rest[b])
      if (length > 1e-5) edges.push([a,b,length])
    }
  const clips = []
  const sample = clipSampler(base.scene, {samples:61, restore:bones})
  for (const clip of base.animations) {
    let attachmentError = 0, rigidError = 0
    for (const _ of sample(clip)) {
      const points = rest.map((_, i) => helmet.getVertexPosition(i, new THREE.Vector3()))
      for (let i = 0; i < points.length; i++) {
        assert.ok(points[i].toArray().every(Number.isFinite))
        attachmentError = Math.max(attachmentError,points[i].distanceTo(local[i].clone().applyMatrix4(head.matrixWorld)))
      }
      for (const [a,b,length] of edges) rigidError = Math.max(rigidError,Math.abs(points[a].distanceTo(points[b])/length-1))
    }
    assert.ok(attachmentError < 1e-5,`${clip.name}: detached helmet`)
    assert.ok(rigidError < 1e-4,`${clip.name}: deformed plate`)
    clips.push({name:clip.name,samples:61,maximum_attachment_error:attachmentError,maximum_rigid_error:rigidError})
  }
  const report = {base_sha256:hash(basePath),helmet_sha256:hash(partPath),triangles:2166,bones:65,exact_bind_compatibility:true,head_weight:1,clips,scope:'Rigid attachment and finite motion; appearance and collar contact reviewed separately.'}
  writeFileSync(`${directory}/animation-validation.json`,JSON.stringify(report,null,2)+'\n')
  console.log(JSON.stringify(report))
} finally { await server.close() }
