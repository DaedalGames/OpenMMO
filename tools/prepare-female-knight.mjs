import assert from 'node:assert/strict'
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { NodeIO, PropertyType, VertexLayout } from '@gltf-transform/core'
import { ALL_EXTENSIONS, EXTTextureWebP } from '@gltf-transform/extensions'
import { prune } from '@gltf-transform/functions'
import sharp from 'sharp'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { GLTFExporter } from '../client/node_modules/three/examples/jsm/exporters/GLTFExporter.js'
import { headlessThree, hash } from './lib/headless-three.mjs'
import { dependencies, output as previewOutput } from './lib/female-preview.mjs'
import { ensureFemalePreview } from './lib/ensure-female-preview.mjs'

const output = 'client/public/models/characters/modular_female'
const metersPerSourceUnit = 1.8
function bakeDimensions(doc) {
  const root = doc.getRoot()
  const scaled = new Set()
  const scaleAccessor = (accessor, matrix = false) => {
    if (!accessor || scaled.has(accessor)) return
    scaled.add(accessor)
    const values = accessor.getArray().slice()
    for (let i = 0; i < values.length; i++) {
      if (!matrix || [12, 13, 14].includes(i % 16)) values[i] *= metersPerSourceUnit
    }
    accessor.setArray(values)
  }
  for (const node of root.listNodes()) node.setTranslation(node.getTranslation().map(v => v * metersPerSourceUnit))
  for (const mesh of root.listMeshes()) {
    for (const primitive of mesh.listPrimitives()) {
      scaleAccessor(primitive.getAttribute('POSITION'))
      for (const target of primitive.listTargets()) scaleAccessor(target.getAttribute('POSITION'))
    }
  }
  for (const skin of root.listSkins()) scaleAccessor(skin.getInverseBindMatrices(), true)
  for (const animation of root.listAnimations()) {
    for (const channel of animation.listChannels()) {
      if (channel.getTargetPath() === 'translation') scaleAccessor(channel.getSampler().getOutput())
    }
  }
  for (const scene of root.listScenes()) scene.setExtras({ ...scene.getExtras(), meters_per_source_unit: metersPerSourceUnit })
  for (const node of root.listNodes()) {
    const pelt = node.getExtras().pelt_physics
    if (!pelt) continue
    const scale = values => values.map(v => v * metersPerSourceUnit)
    node.setExtras({
      ...node.getExtras(),
      pelt_physics: {
        ...pelt,
        unit: metersPerSourceUnit,
        pivot: scale(pelt.pivot),
        length: pelt.length * metersPerSourceUnit,
        ...(pelt.attachment_depth !== undefined && { attachment_depth: pelt.attachment_depth * metersPerSourceUnit }),
        colliders: pelt.colliders.map(c => ({ ...c, center: scale(c.center), radii: scale(c.radii) })),
      },
    })
  }
}
const sources = {
  base: 'assets/modular_human_female_01/rig_v1/female-base.glb',
  hair: 'assets/modular_human_female_01/hair/tripo_knight_bob_v1/fitted_v1/hair_female_knight_bob.glb',
  top: 'assets/items/female_knight_top/tripo_v1/fitted_v3/top_female_knight.glb',
  bottom: 'assets/items/female_knight_bottom/tripo_v1/fitted_v42/bottom_female_knight.glb',
  boots: 'assets/items/female_knight_boots/fitted_v5/boots_female_knight.glb',
  gloves: 'assets/items/female_knight_gloves/tripo_v1/fitted_v3/gloves_female_knight.glb',
  helmet: 'assets/items/female_knight_helmet/tripo_v1/fitted_v1/helmet_female_knight.glb',
  barbarian_hair: 'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/hair_bob_barbarian_helmet.glb',
  barbarian_top: 'assets/items/female_barbarian_top/tripo_v1/fitted_v1/top_female_barbarian.glb',
  barbarian_bottom: 'assets/items/female_barbarian_bottom/tripo_v1/fitted_v1/bottom_female_barbarian.glb',
  barbarian_boots: 'assets/items/female_barbarian_boots/tripo_v1/fitted_v3/boots_female_barbarian.glb',
  barbarian_gloves: 'assets/items/female_barbarian_bracers/tripo_v1/fitted_v1/gloves_female_barbarian.glb',
  barbarian_helmet: 'assets/items/female_barbarian_helmet/tripo_v2/fitted_v1/helmet_female_barbarian.glb',
}
const packs = ['locomotion', 'combat_melee', 'social', 'fishing', 'combat_ranged', 'offhand', 'enchant_armor', 'great_sword', 'riding', 'dagger_preview']
const packFlag = process.argv.indexOf('--pack')
const selectedPack = packFlag === -1 ? undefined : process.argv[packFlag + 1]
if (selectedPack !== undefined && !packs.includes(selectedPack)) throw new Error(`--pack requires one of: ${packs.join(', ')}`)
const builtPacks = selectedPack ? [selectedPack] : packs
mkdirSync(`${output}/animations`, { recursive: true })
const reportPath = 'doc/assets/female-knight-runtime-sources.json'
const report = { date: '2026-10-16', inputs: {}, outputs: {} }
const record = (path) => { report.inputs[path] = hash(path) }
for (const path of ['tools/prepare-female-knight.mjs', 'client/src/lib/utils/female-clip-bake.ts', 'client/src/lib/utils/female-boot-ground.ts']) record(path)
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS)
// Replaces the file instead of rewriting it, since worktrees may hard-link these GLBs.
async function write(path, doc) {
  // Pelt rigs rewrite positions in place, which interleaved attributes do not support.
  const pelt = doc.getRoot().listNodes().some(node => node.getExtras().pelt_physics)
  io.setVertexLayout(pelt ? VertexLayout.SEPARATE : VertexLayout.INTERLEAVED)
  writeFileSync(`${path}.tmp`, await io.writeBinary(doc))
  renameSync(`${path}.tmp`, path)
}
sharp.cache(false)
sharp.concurrency(2)
for (const [name, source] of Object.entries(sources)) {
  record(source)
  if (selectedPack) continue
  const doc = await io.read(source)
  const scene = doc.getRoot().listScenes()[0]
  const metadata = { ...scene.getExtras(), female_part: name }
  if (!/^(base|(barbarian_)?hair)$/.test(name)) {
    const path = source.replace(/[^/]+$/, 'body-occlusion.json')
    record(path)
    metadata.body_mask = JSON.parse(readFileSync(path))
  }
  if (name === 'gloves') {
    const path = source.replace(/[^/]+$/, 'top-occlusion.json')
    record(path)
    metadata.sleeve_mask = JSON.parse(readFileSync(path))
  }
  scene.setExtras(metadata)
  if (name === 'base') {
    for (const node of doc.getRoot().listNodes()) {
      const mesh = node.getMesh()
      if (mesh) node.setExtras({ ...node.getExtras(), female_body: mesh === doc.getRoot().listMeshes()[0] })
    }
  }
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const primitive of mesh.listPrimitives()) {
      const joints = primitive.getAttribute('JOINTS_0')
      const weights = primitive.getAttribute('WEIGHTS_0')
      if (!joints || !weights) continue
      const indices = joints.getArray().slice()
      for (let i = 0; i < indices.length; i++) if (weights.getArray()[i] === 0) indices[i] = 0
      joints.setArray(indices)
    }
  }
  const colors = new Set(doc.getRoot().listMaterials().map(m => m.getBaseColorTexture()))
  for (const texture of doc.getRoot().listTextures()) {
    if (/eyelash/i.test(texture.getName())) continue
    const color = colors.has(texture)
    const image = await sharp(texture.getImage()).resize({ width: color ? 2048 : 1024, height: color ? 2048 : 1024, fit: 'inside', withoutEnlargement: true })
      .webp(color ? { quality: 94, effort: 5 } : { quality: 90, smartSubsample: true, effort: 5 }).toBuffer()
    texture.setImage(image).setMimeType('image/webp')
  }
  doc.createExtension(EXTTextureWebP).setRequired(true)
  bakeDimensions(doc)
  // Fitting sources carry unreferenced accessors from earlier iterations.
  await doc.transform(prune({ propertyTypes: [PropertyType.ACCESSOR], keepAttributes: true, keepIndices: true }))
  const path = `${output}/${name}.glb`
  await write(path, doc)
  console.log(path)
}
// Bakes from the written GLBs so the values match what the client loads; companion animations carry the boots variants.
async function bakeBootsAndGrip(module, load) {
  const female = await module('/src/lib/utils/femaleCharacter.ts')
  const { bakeFemaleClips } = await module('/src/lib/utils/female-clip-bake.ts')
  const [base, ...parts] = await Promise.all(['base', ...female.FEMALE_PARTS].map(name => load(`${output}/${name}.glb`)))
  const scene = female.assembleFemaleCharacter(base, parts)
  for (const path of [...(selectedPack ? [] : [`${output}/base.glb`]), ...builtPacks.map(name => `${output}/animations/${name}.glb`)]) {
    const gltf = path.endsWith('/base.glb') ? base : await load(path)
    const bakes = bakeFemaleClips(scene, gltf.animations)
    const doc = await io.read(path)
    const root = doc.getRoot()
    const buffer = root.listBuffers()[0]
    const nodes = new Map(root.listNodes().map(node => [THREE.PropertyBinding.sanitizeNodeName(node.getName()), node]))
    const accessor = (type, array) => doc.createAccessor().setType(type).setArray(array).setBuffer(buffer)
    const animations = root.listAnimations()
    assert.deepEqual(animations.map(a => a.getName()), bakes.map(b => b.name))
    for (const [i, animation] of animations.entries()) {
      const channel = track => {
        const [name, property] = track.name.split('.')
        const target = { quaternion: 'rotation', position: 'translation' }[property]
        const node = nodes.get(name)
        assert.ok(node && target, track.name)
        return { node, target, found: animation.listChannels().find(c => c.getTargetNode() === node && c.getTargetPath() === target) }
      }
      for (const track of bakes[i].grip) {
        const { node, target, found } = channel(track)
        const sampler = doc.createAnimationSampler().setInterpolation('LINEAR')
          .setInput(accessor('SCALAR', new Float32Array(track.times))).setOutput(accessor('VEC4', new Float32Array(track.values)))
        animation.addSampler(sampler)
        if (found) {
          const old = found.getSampler()
          found.setSampler(sampler)
          disposeSampler(old)
        } else animation.addChannel(doc.createAnimationChannel().setTargetNode(node).setTargetPath(target).setSampler(sampler))
      }
      for (const [boots, tracks] of Object.entries(bakes[i].boots)) {
        const companion = doc.createAnimation(female.femaleBootsClipName(animation.getName(), boots))
        for (const track of tracks) {
          const { node, target, found } = channel(track)
          assert.ok(found, track.name)
          const bare = found.getSampler()
          const sampler = doc.createAnimationSampler().setInterpolation(bare.getInterpolation())
            .setInput(bare.getInput()).setOutput(accessor(bare.getOutput().getType(), new Float32Array(track.values)))
          companion.addSampler(sampler).addChannel(doc.createAnimationChannel().setTargetNode(node).setTargetPath(target).setSampler(sampler))
        }
      }
    }
    await write(path, doc)
    console.log(`${path}: baked ${bakes.length} clips`)
  }
}

function disposeSampler(sampler) {
  const accessors = [sampler.getInput(), sampler.getOutput()]
  sampler.dispose()
  for (const accessor of accessors) if (accessor.listParents().every(parent => parent.propertyType === 'Root')) accessor.dispose()
}

await ensureFemalePreview('animations')
const preparedPath = previewOutput('animations')
for (const path of dependencies('animations')) record(path)
const { server, load } = await headlessThree()
globalThis.FileReader = class {
  readAsArrayBuffer(blob) { blob.arrayBuffer().then(result => { this.result = result; this.onloadend?.() }) }
}
try {
  const runtime = await server.ssrLoadModule('/src/lib/utils/characterAnimationUtils.ts')
  const base = await load(sources.base)
  const corrected = new Map(base.animations.map(c => [c.name, c]))
  for (const data of JSON.parse(readFileSync(preparedPath)).clips) {
    const clip = THREE.AnimationClip.parse(data)
    corrected.set(clip.name, clip)
  }
  for (const name of ['idle2', 'idle3', 'idle4', 'idle5']) {
    const clip = corrected.get('idle1').clone(); clip.name = name; corrected.set(name, clip)
  }
  for (const name of builtPacks) {
    const source = `client/public/models/animations/${name}.glb`
    record(source)
    const pack = await load(source)
    const missing = pack.animations.filter(c => !corrected.has(c.name))
    let clips = await runtime.retargetAnimationsForCharacterModel(base.scene, pack.scene, missing)
    if (name !== 'riding') clips = await runtime.groundRetargetedClips(base.scene, clips)
    const byName = new Map(clips.map(c => [c.name, c]))
    const animations = pack.animations.map(c => corrected.get(c.name) ?? byName.get(c.name))
    const scene = base.scene.clone(true)
    const meshes = []; scene.traverse(n => { if (n.isMesh) meshes.push(n) })
    for (const mesh of meshes) mesh.removeFromParent()
    const bytes = await new GLTFExporter().parseAsync(scene, { binary: true, animations })
    const path = `${output}/animations/${name}.glb`
    const doc = await io.readBinary(new Uint8Array(bytes))
    bakeDimensions(doc)
    await write(path, doc)
    console.log(`${name}: ${animations.length} clips`)
  }
  await bakeBootsAndGrip(path => server.ssrLoadModule(path), load)
} finally { await server.close() }
for (const path of [...Object.keys(sources).map(name => `${output}/${name}.glb`), ...packs.map(name => `${output}/animations/${name}.glb`)]) report.outputs[path] = hash(path)
const previous = existsSync(reportPath) ? JSON.parse(readFileSync(reportPath)) : {}
if (selectedPack) report.inputs = { ...previous.inputs, ...report.inputs }
writeFileSync(reportPath, JSON.stringify({ ...previous, ...report }, null, 2) + '\n')
