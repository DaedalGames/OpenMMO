import assert from 'node:assert/strict'
import { readFile, rename, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS, EXTTextureWebP } from '@gltf-transform/extensions'
import sharp from 'sharp'

const [source, output] = process.argv.slice(2)
assert.ok(source && output, 'Usage: node tools/optimize-ysolde-tent.mjs SOURCE.glb OUTPUT.glb')
const input = await readFile(source)
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
const doc = await io.readBinary(input)
const root = doc.getRoot()
const colors = new Set(root.listMaterials().map(material => material.getBaseColorTexture()).filter(Boolean))
assert.equal(colors.size, 2)
for (const texture of colors) {
  assert.equal(texture.getMimeType(), 'image/jpeg')
  const data = await sharp(texture.getImage())
    .resize({ width: 1024, height: 1024, fit: 'inside', withoutEnlargement: true })
    .webp({ quality: 94, effort: 6 }).toBuffer()
  texture.setImage(data).setMimeType('image/webp')
}
doc.createExtension(EXTTextureWebP).setRequired(true)
const result = await io.writeBinary(doc)
assert.ok(result.length < input.length)
await writeFile(`${output}.tmp`, result)
await rename(`${output}.tmp`, output)
console.log(`${input.length} → ${result.length} bytes`)
console.log(`gzip level 6: ${gzipSync(input, { level: 6 }).length} → ${gzipSync(result, { level: 6 }).length} bytes`)
