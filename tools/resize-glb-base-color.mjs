import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import sharp from 'sharp'

const [source, output, sizeArg] = process.argv.slice(2)
const size = Number(sizeArg)
assert.ok(source && output && Number.isSafeInteger(size) && size > 0,
  'Usage: node tools/resize-glb-base-color.mjs SOURCE.glb OUTPUT.glb MAX_SIZE')
const original = readFileSync(source)
assert.equal(original.readUInt32LE(0), 0x46546c67)
assert.equal(original.readUInt32LE(4), 2)
assert.equal(original.readUInt32LE(8), original.length)
const jsonLength = original.readUInt32LE(12)
const json = JSON.parse(original.subarray(20, 20 + jsonLength))
const binStart = 28 + jsonLength
assert.equal(original.readUInt32LE(binStart - 4), 0x004e4942)
assert.equal(original.readUInt32LE(binStart - 8) + binStart, original.length)
const binary = original.subarray(binStart)
const images = new Set(json.materials.flatMap(material => {
  const info = material.pbrMetallicRoughness?.baseColorTexture
  if (!info) return []
  const texture = json.textures[info.index]
  return [texture.extensions?.EXT_texture_webp?.source ?? texture.source]
}))
assert.equal(images.size, 1, 'Expected one embedded base color image')
const image = json.images[[...images][0]]
assert.equal(image.mimeType, 'image/webp')
const view = json.bufferViews[image.bufferView]
assert.equal(view.buffer, 0)
const start = view.byteOffset ?? 0
const input = binary.subarray(start, start + view.byteLength)
const metadata = await sharp(input).metadata()
assert.ok(Math.max(metadata.width, metadata.height) > size)
const converted = await sharp(input)
  .resize({ width: size, height: size, fit: 'inside', withoutEnlargement: true })
  .webp({ quality: 94, effort: 5 }).toBuffer()
assert.ok(converted.length < input.length)
const oldSpan = Math.ceil(input.length / 4) * 4
const newSpan = Math.ceil(converted.length / 4) * 4
const delta = newSpan - oldSpan
const bin = Buffer.concat([
  binary.subarray(0, start), converted, Buffer.alloc(newSpan - converted.length),
  binary.subarray(start + oldSpan),
])
view.byteLength = converted.length
for (const other of json.bufferViews) {
  if (other !== view && other.buffer === 0 && (other.byteOffset ?? 0) >= start + oldSpan)
    other.byteOffset += delta
  const compressed = other.extensions?.EXT_meshopt_compression
  if (compressed?.buffer === 0 && (compressed.byteOffset ?? 0) >= start + oldSpan)
    compressed.byteOffset += delta
}
json.buffers[0].byteLength += delta
const text = Buffer.from(JSON.stringify(json))
const jsonChunk = Buffer.concat([text, Buffer.alloc((4 - text.length % 4) % 4, 0x20)])
const header = Buffer.alloc(20)
header.writeUInt32LE(0x46546c67, 0)
header.writeUInt32LE(2, 4)
header.writeUInt32LE(28 + jsonChunk.length + bin.length, 8)
header.writeUInt32LE(jsonChunk.length, 12)
header.writeUInt32LE(0x4e4f534a, 16)
const binHeader = Buffer.alloc(8)
binHeader.writeUInt32LE(bin.length, 0)
binHeader.writeUInt32LE(0x004e4942, 4)
const optimized = Buffer.concat([header, jsonChunk, binHeader, bin])
writeFileSync(output, optimized)
console.log(JSON.stringify({
  sourceBytes: original.length, outputBytes: optimized.length,
  sourceGzipBytes: gzipSync(original, { level: 6 }).length,
  outputGzipBytes: gzipSync(optimized, { level: 6 }).length,
  colorBeforeBytes: input.length, colorAfterBytes: converted.length,
  sourceDimensions: [metadata.width, metadata.height], maxSize: size,
}, null, 2))
