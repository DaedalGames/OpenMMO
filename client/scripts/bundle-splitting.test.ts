import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'
import type { OutputChunk, RollupOutput } from 'rollup'
import { build } from 'vite'
import { expect, it } from 'vitest'

async function bundle(version: string) {
  const result = await build({
    root: fileURLToPath(new URL('../', import.meta.url)),
    logLevel: 'error',
    define: { __APP_VERSION__: JSON.stringify(version) },
    build: { write: false, copyPublicDir: false, reportCompressedSize: false },
  })
  return (result as RollupOutput).output.filter(
    (output): output is OutputChunk => output.type === 'chunk'
  )
}

function staticChunks(
  chunks: OutputChunk[],
  root = chunks.find((chunk) => chunk.isEntry)!
) {
  const byName = new Map(chunks.map((chunk) => [chunk.fileName, chunk]))
  const initial = new Set<OutputChunk>()
  const visit = (chunk: OutputChunk) => {
    if (initial.has(chunk)) return
    initial.add(chunk)
    for (const dependency of chunk.imports) visit(byName.get(dependency)!)
  }
  visit(root)
  return [...initial]
}

it('defers scenes and editors while keeping libraries cached across app updates', async () => {
  const first = await bundle('bundle-test-first')
  const initial = staticChunks(first)
  const initialModules = initial.flatMap((chunk) => Object.keys(chunk.modules))
  for (const module of [
    '/SceneCanvas.svelte',
    '/GameScene.svelte',
    '/GameHud.svelte',
    '/MapEditorTools.svelte',
    '/MapEditorPanel.svelte',
    '/HousingEditorCursor.svelte',
    '/HousingEditorPanel.svelte',
    '/three.webgpu.js',
  ]) {
    expect(
      initialModules.some((id) => id.endsWith(module)),
      module
    ).toBe(false)
    expect(
      first.some((chunk) =>
        Object.keys(chunk.modules).some((id) => id.endsWith(module))
      ),
      module
    ).toBe(true)
  }

  const game = first.find((chunk) =>
    Object.keys(chunk.modules).some((id) => id.endsWith('/GameScene.svelte'))
  )!
  const gameImports = staticChunks(first, game)
  for (const module of [
    '/MapEditorTools.svelte',
    '/MapEditorPanel.svelte',
    '/HousingEditorCursor.svelte',
    '/HousingEditorPanel.svelte',
  ]) {
    expect(
      gameImports.some((chunk) =>
        Object.keys(chunk.modules).some((id) => id.endsWith(module))
      )
    ).toBe(false)
  }

  const second = await bundle('bundle-test-second')
  const libraries = (chunks: OutputChunk[]) =>
    chunks
      .filter((chunk) => /^(vendor|three-|threlte)/.test(chunk.name))
      .map((chunk) => chunk.fileName)
      .sort()
  expect(libraries(first).length).toBeGreaterThanOrEqual(4)
  expect(libraries(second)).toEqual(libraries(first))
  expect(second.find((chunk) => chunk.isEntry)!.fileName).not.toBe(
    first.find((chunk) => chunk.isEntry)!.fileName
  )

  console.info(
    'Initial JavaScript gzip bytes:',
    initial.reduce(
      (total, chunk) => total + gzipSync(chunk.code, { level: 6 }).length,
      0
    )
  )
}, 60_000)
