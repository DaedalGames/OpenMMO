import { readFile, writeFile } from 'node:fs/promises'
import { gzipSync } from 'node:zlib'
import { NodeIO, PropertyType, VertexLayout } from '@gltf-transform/core'
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions'
import { dedup, meshopt, prune, weld } from '@gltf-transform/functions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'

const [source, output, ...flags] = process.argv.slice(2)
const lossless = flags.length === 1 && flags[0] === '--lossless'
if (!source || !output || (flags.length && !lossless)) {
  console.error('Usage: node tools/compress-glb-meshes.mjs SOURCE.glb OUTPUT.glb [--lossless]')
  process.exit(1)
}

await Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready])
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({
    'meshopt.encoder': MeshoptEncoder,
    'meshopt.decoder': MeshoptDecoder,
  })
  .setVertexLayout(VertexLayout.SEPARATE)
const original = await readFile(source)
const document = await io.readBinary(original)
if (document.getRoot().listExtensionsUsed().some(e => e.extensionName === 'EXT_meshopt_compression')) {
  throw new Error('Use the uncompressed source to avoid repeated quantization.')
}
if (lossless) {
  await document.transform(prune({ propertyTypes: [PropertyType.MATERIAL, PropertyType.TEXTURE] }))
  // Without quantize(), this encoder preserves the original accessor values.
  document.createExtension(EXTMeshoptCompression).setRequired(true)
    .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE })
} else {
  await document.transform(
    dedup(),
    weld(),
    prune(),
    meshopt({ encoder: MeshoptEncoder, level: 'medium' })
  )
}
const compressed = await io.writeBinary(document)
await writeFile(output, compressed)
console.log(`${original.length} → ${compressed.length} bytes`)
console.log(`gzip level 6: ${gzipSync(original, { level: 6 }).length} → ${gzipSync(compressed, { level: 6 }).length} bytes`)
