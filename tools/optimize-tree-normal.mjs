import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { gzipSync } from 'node:zlib'

const [source, output] = process.argv.slice(2)
assert.ok(source && output && source !== output, 'Usage: node tools/optimize-tree-normal.mjs SOURCE.glb OUTPUT.glb')
const original = readFileSync(source)
assert.equal(original.readUInt32LE(0), 0x46546c67)
assert.equal(original.readUInt32LE(8), original.length)
const jsonLength = original.readUInt32LE(12)
const json = JSON.parse(original.subarray(20, 20 + jsonLength))
const binStart = 28 + jsonLength
assert.equal(original.readUInt32LE(binStart - 4), 0x004e4942)
const binary = original.subarray(binStart)
const image = json.images.find(image => image.name === 'bark_willow_nor_gl_2k')
assert.equal(image?.mimeType, 'image/png')
const view = json.bufferViews[image.bufferView]
const start = view.byteOffset ?? 0
const png = binary.subarray(start, start + view.byteLength)
assert.equal(png[24], 16, 'Expected the original 16-bit normal map')
const result = spawnSync('ffmpeg', [
  '-v', 'error', '-i', 'pipe:0', '-frames:v', '1', '-pix_fmt', 'rgb24',
  '-compression_level', '9', '-f', 'image2pipe', '-c:v', 'png', 'pipe:1',
], { input: png, maxBuffer: 8 * 1024 * 1024 })
assert.equal(result.status, 0, result.stderr?.toString())
const converted = result.stdout
assert.equal(converted[24], 8)
assert.deepEqual(converted.subarray(16, 24), png.subarray(16, 24))
assert.ok(converted.length < png.length)
const oldSpan = Math.ceil(png.length / 4) * 4
const newSpan = Math.ceil(converted.length / 4) * 4
const delta = newSpan - oldSpan
const bin = Buffer.concat([
  binary.subarray(0, start), converted, Buffer.alloc(newSpan - converted.length),
  binary.subarray(start + oldSpan),
])
view.byteLength = converted.length
for (const other of json.bufferViews) {
  if (other !== view && (other.byteOffset ?? 0) > start) other.byteOffset += delta
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
  normalBeforeBytes: png.length, normalAfterBytes: converted.length,
}, null, 2))
