import assert from 'node:assert/strict'
import { readFile, rename, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS, EXTTextureWebP } from '@gltf-transform/extensions'
import sharp from 'sharp'

const [source, output] = process.argv.slice(2)
assert.ok(source && output, 'Usage: node tools/optimize-hearthbound-rug.mjs SOURCE.glb OUTPUT.glb')
const input = await readFile(source)
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const doc = await io.readBinary(input)
const root = doc.getRoot()
const textures = root.listTextures()
assert.equal(textures.length, 1)
const texture = textures[0]
assert.equal(texture.getMimeType(), 'image/png')
assert.ok(root.listMaterials().every(material => material.getBaseColorTexture() === texture && material.getAlphaMode() === 'MASK'))
const image = await sharp(texture.getImage()).webp({ quality: 94, effort: 6 }).toBuffer()
texture.setImage(image).setMimeType('image/webp')
doc.createExtension(EXTTextureWebP).setRequired(true)
const result = await io.writeBinary(doc)
assert.ok(result.length < input.length)
await writeFile(`${output}.tmp`, result)
await rename(`${output}.tmp`, output)
console.log(`${input.length} → ${result.length} bytes`)
console.log(`gzip level 6: ${gzipSync(input, { level: 6 }).length} → ${gzipSync(result, { level: 6 }).length} bytes`)
