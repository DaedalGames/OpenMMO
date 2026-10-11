import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import * as THREE from '../client/node_modules/three/build/three.module.js'
import { clipSampler, hash, headlessThree, loadClips, root } from './lib/headless-three.mjs'

const directory = 'assets/items/bard_starter/tripo_boots_v1/'
const cuff = JSON.parse(readFileSync(new URL('client/src/lib/data/bardBootCuff.json', root)))
assert.equal(hash(cuff.source), cuff.sha256)
const { server, load, sources } = await headlessThree({
  material: () => new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }),
})
try {
  const mod = await server.ssrLoadModule('/src/lib/utils/modularCharacter.ts')
  const { bardBootRim } = await server.ssrLoadModule('/src/lib/utils/bardBootCuff.ts')
  const { computeSoleGroundOffset } = await server.ssrLoadModule('/src/lib/utils/characterAnimationUtils.ts')
  const body = (await load('assets/modular_human_male_01/fitted/base.glb')).scene
  const skin = mod.skinnedParts(body), parts = new Map()
  for (const [id, path] of Object.entries({
    hair_crop: 'fitted/hair_crop.glb', top_bard: 'bard/tripo_top_v1/top_bard.glb',
    pants_bard: 'bard/tripo_pants_v1/pants_bard.glb', boots_bard: 'bard/tripo_boots_v1/boots_bard.glb',
  })) parts.set(id, mod.bindModularPart(body, (await load('assets/modular_human_male_01/' + path)).scene))
  const tris = (meshes) => meshes.reduce((n, m) => n + m.geometry.index.count / 3, 0)
  const preserved = tris(skin) + tris([...parts.values()].flat())
  const pants = parts.get('pants_bard')[0], boots = parts.get('boots_bard')
  const original = pants.geometry
  const selected = mod.showModularOutfit(skin, parts, mod.BARD_MODULAR_OUTFIT)
  assert.ok(selected.has('boots_bard'))
  assert.equal(tris(boots), 3406)
  const trimmed = pants.geometry
  assert.notEqual(trimmed, original)
  body.updateMatrixWorld(true)
  const soleOffset = computeSoleGroundOffset(body)
  const raycaster = new THREE.Raycaster(), point = new THREE.Vector3()
  const hems = []
  let minGap = Infinity
  for (let i = 0; i < trimmed.attributes.position.count; i++) {
    point.fromBufferAttribute(trimmed.attributes.position, i)
    const rim = bardBootRim(point)
    if (Math.abs(point.y - (rim.height - cuff.overlap)) > 1e-6) continue
    assert.ok(rim.radius <= rim.innerRadius + 1e-6)
    const side = point.x > 0 ? 'Left' : 'Right'
    const leg = pants.skeleton.bones.find((b) => b.name === side + 'Leg')
    assert.equal(trimmed.attributes.skinWeight.getX(i), 1)
    assert.equal(pants.skeleton.bones[trimmed.attributes.skinIndex.getX(i)], leg)
    const origin = new THREE.Vector3(Math.sign(point.x) * cuff.origin[0], point.y, cuff.origin[1])
    raycaster.set(origin, point.clone().sub(origin).normalize())
    const hits = raycaster.intersectObjects(boots, false)
    assert.ok(hits.length, `Missing cuff wall at hem ${i}`)
    const gap = hits[0].distance - point.distanceTo(origin)
    assert.ok(gap > .0005, `Hem ${i} crosses cuff by ${-gap}m`)
    minGap = Math.min(minGap, gap)
    hems.push({ i, leg, local: point.clone().applyMatrix4(leg.matrixWorld.clone().invert()) })
  }
  assert.ok(hems.length > 20)
  const snapshot = JSON.parse(execFileSync(fileURLToPath(new URL('.venv/bin/python', root)),
    ['tools/export-bard-boot-pants.py'], { cwd: fileURLToPath(root), encoding: 'utf8', maxBuffer: 8 * 1024 * 1024,
      input: JSON.stringify(Object.fromEntries([
        ...Object.entries(trimmed.attributes).map(([n, a]) => [n, Array.from(a.array)]),
        ['indices', Array.from(trimmed.index.array)],
      ])),
    }))
  const clips = await loadClips(body, load, mod.modularAnimationClips)
  const sample = clipSampler(body, { samples: 13, restore: pants.skeleton.bones })
  let maximumMotionError = 0, maximumSeamGap = 0
  const seams = boots.map((mesh) => {
    const positions = mesh.geometry.attributes.position, groups = new Map(), pairs = []
    for (let i = 0; i < positions.count; i++) {
      const key = [positions.getX(i), positions.getY(i), positions.getZ(i)].join(',')
      if (groups.has(key)) pairs.push([groups.get(key), i])
      else groups.set(key, i)
    }
    return { mesh, pairs }
  })
  const snapshots = [], poses = []
  for (const clip of clips) {
    for (const { sample: index, time } of sample(clip)) {
      for (const mesh of [pants, ...boots]) {
        for (let i = 0; i < mesh.geometry.attributes.position.count; i++) {
          mesh.getVertexPosition(i, point)
          assert.ok(point.toArray().every(Number.isFinite))
        }
      }
      for (const { i, leg, local } of hems) {
        pants.getVertexPosition(i, point).applyMatrix4(leg.matrixWorld.clone().invert())
        maximumMotionError = Math.max(maximumMotionError, point.distanceTo(local))
      }
      for (const { mesh, pairs } of seams)
        for (const [a, b] of pairs)
          maximumSeamGap = Math.max(maximumSeamGap,
            mesh.getVertexPosition(a, new THREE.Vector3()).distanceTo(mesh.getVertexPosition(b, point)))
      const matrices = pants.skeleton.bones.map((b, i) =>
        new THREE.Matrix4().multiplyMatrices(b.matrixWorld, pants.skeleton.boneInverses[i]).toArray())
      poses.push({ clip: clip.name, time, matrices })
      if (index === 5) snapshots.push({ clip: clip.name, time,
        bone_deformation_matrices: Object.fromEntries(pants.skeleton.bones.map((b, i) => [b.name, matrices[i]])) })
    }
  }
  assert.ok(maximumMotionError < 1e-5)
  assert.ok(maximumSeamGap < 1e-7)
  const equipped = [...skin, ...[...parts].filter(([id]) => selected.has(id)).flatMap(([, meshes]) => meshes)]
  const budget = { preserved_glb_triangles_including_hidden: preserved,
    runtime_triangles_including_hidden: tris(equipped), visible_triangles: tris(equipped.filter((m) => m.visible)),
    face_triangles: 1505, scope: 'Body, crop hair, bard top, pants and boots; no gloves or weapon' }
  mod.showModularOutfit(skin, parts, { ...mod.BARD_MODULAR_OUTFIT, boots: 'none' })
  assert.equal(pants.geometry, original)
  assert.ok(boots.every((m) => !m.visible))
  assert.ok(skin.filter((m) => mod.region(m) === 'feet').every((m) => m.visible))
  mod.showModularOutfit(skin, parts, mod.BARD_MODULAR_OUTFIT)
  assert.equal(pants.geometry, trimmed)
  parts.delete('boots_bard')
  mod.showModularOutfit(skin, parts, mod.BARD_MODULAR_OUTFIT)
  assert.equal(pants.geometry, original)
  assert.ok(skin.filter((m) => mod.region(m) === 'feet').every((m) => m.visible))
  const report = { date: '2026-10-11', sources, sole_offset_m: soleOffset,
    hem_vertices: hems.length, minimum_actual_cuff_wall_clearance_m: minGap,
    maximum_hem_relative_to_leg_motion_error_m: maximumMotionError, maximum_boot_uv_seam_gap_m: maximumSeamGap,
    clips: clips.map((c) => c.name), motion_samples: poses.length, snapshot, budget,
    boot_removal_and_missing_asset_restore_pants_and_feet: true,
    scope: 'Actual GLB binding, cuff wall intersections at hem vertices, rigid hem motion and finite boot/pants vertices in 91 poses; not a full surface collision or mixed-outfit certification.' }
  writeFileSync(new URL(directory + 'animation-snapshots.json', root), JSON.stringify(snapshots) + '\n')
  writeFileSync(new URL(directory + 'validation-poses.json', root), JSON.stringify(poses) + '\n')
  writeFileSync(new URL('doc/assets/modular-bard-tripo-boots-animation-v1.json', root), JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report))
} finally {
  await server.close()
}
