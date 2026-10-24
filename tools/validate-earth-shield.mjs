import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { GLTFLoader } from '../client/node_modules/three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from '../client/node_modules/three/examples/jsm/libs/meshopt_decoder.module.js'

globalThis.self = globalThis
const source = 'assets/items/earth_shield/tripo_v1'
const paths = process.argv.slice(2)
const tripoIndex = paths.indexOf('--tripo')
let tripo = tripoIndex >= 0
if (tripo) paths.splice(tripoIndex, 1)
const reportIndex = paths.indexOf('--report')
const reportPath = reportIndex < 0 ? `${source}/validation.json` : paths.splice(reportIndex, 2)[1]
if (!paths.length) {
  paths.push(`${source}/earth_shield.glb`, 'client/public/models/armor/earth_shield.glb')
  tripo = true
}
const loader = new GLTFLoader().register(() => ({
  name: 'geometry-only',
  loadMaterial: async () => new THREE.MeshBasicMaterial(),
}))
loader.setMeshoptDecoder(MeshoptDecoder)
const reports = []
for (const path of paths) {
  const bytes = readFileSync(resolve(path))
  assert.equal(bytes.readUInt32LE(0), 0x46546c67)
  assert.equal(bytes.readUInt32LE(4), 2)
  assert.equal(bytes.readUInt32LE(8), bytes.length)
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)))
  const compressed = json.extensionsUsed?.includes('EXT_meshopt_compression')
  const tolerance = compressed ? 1e-4 : 1e-5
  assert.equal(json.materials.length, 1)
  const material = json.materials[0]
  assert.ok(material.pbrMetallicRoughness.baseColorTexture)
  assert.ok(material.pbrMetallicRoughness.metallicRoughnessTexture)
  assert.ok(material.normalTexture)
  if (!tripo) {
    assert.ok(material.emissiveTexture)
    assert.ok(material.emissiveFactor.some(value => value > 0))
  }
  assert.ok(!material.doubleSided)
  assert.ok(!material.alphaMode || material.alphaMode === 'OPAQUE')
  assert.ok(json.images.every(image => image.bufferView !== undefined && !image.uri))
  const asset = await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')
  const bounds = new THREE.Box3().setFromObject(asset.scene)
  const size = bounds.getSize(new THREE.Vector3())
  assert.ok(Math.abs(size.x - (tripo ? 0.533464 : 0.54)) < 0.005)
  assert.ok(Math.abs(size.y - 0.80) < tolerance)
  assert.ok(Math.abs(bounds.min.y + (tripo ? 0.53405 : 0.46)) < tolerance)
  assert.ok(Math.abs(bounds.max.y - (tripo ? 0.26595 : 0.34)) < tolerance)
  let triangles = 0
  let vertices = 0
  let meshes = 0
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3()
  const edge1 = new THREE.Vector3(), edge2 = new THREE.Vector3()
  asset.scene.traverse(node => {
    if (!compressed) assert.deepEqual(node.scale.toArray(), [1, 1, 1])
    if (!node.isMesh) return
    meshes++
    if (!compressed) assert.ok(node.getWorldPosition(new THREE.Vector3()).length() < 1e-6)
    const geometry = node.geometry
    const { position, normal, uv, tangent } = geometry.attributes
    assert.ok(position && normal && uv && tangent)
    for (const attribute of [position, normal, uv, tangent]) {
      assert.ok(attribute.array.every(Number.isFinite))
    }
    assert.ok(uv.array.every(value => value >= -1e-6 && value <= 1.000001))
    for (let i = 0; i < normal.count; i++) {
      assert.ok(Math.abs(Math.hypot(normal.getX(i), normal.getY(i), normal.getZ(i)) - 1) < (compressed ? 0.001 : 1e-4))
      assert.ok(Math.abs(Math.hypot(tangent.getX(i), tangent.getY(i), tangent.getZ(i)) - 1) < (compressed ? 0.001 : 1e-4))
      assert.equal(Math.abs(tangent.getW(i)), 1)
    }
    const index = geometry.index.array
    for (let i = 0; i < index.length; i += 3) {
      a.fromBufferAttribute(position, index[i])
      b.fromBufferAttribute(position, index[i + 1])
      c.fromBufferAttribute(position, index[i + 2])
      assert.ok(edge1.subVectors(b, a).cross(edge2.subVectors(c, a)).lengthSq() > 1e-20, `Degenerate triangle ${i / 3}`)
    }
    triangles += index.length / 3
    vertices += position.count
  })
  assert.equal(meshes, 1)
  assert.ok(triangles > 0 && triangles <= 6000)
  reports.push({ path, bytes: bytes.length, triangles, vertices, meshes, materials: json.materials.length,
    dimensions_gltf_m: size.toArray(), bounds_gltf_m: [bounds.min.toArray(), bounds.max.toArray()],
    texture_mime_types: json.images.map(image => image.mimeType), passed: true })
}
writeFileSync(resolve(reportPath), JSON.stringify(reports, null, 2) + '\n')
console.log(JSON.stringify(reports, null, 2))
