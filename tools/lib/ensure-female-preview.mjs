import { readFile, stat } from 'node:fs/promises'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { fileURLToPath } from 'node:url'
import { root, directory, signature, output } from './female-preview.mjs'

const execute = promisify(execFile)

// Preview files are local build output, not synced through assets.lock.
export async function ensureFemalePreview(name) {
  const current = await signature(name)
  try {
    const manifest = JSON.parse(await readFile(new URL(`${name}.manifest.json`, directory), 'utf8'))
    if (manifest.signature === current) {
      await stat(output(name))
      if (name === 'animations') await stat(new URL(output(name).href + '.gz'))
      return
    }
  } catch (error) {
    if (error.code !== 'ENOENT' && !(error instanceof SyntaxError)) throw error
  }
  await execute(process.execPath, [fileURLToPath(new URL('tools/build-female-preview.mjs', root)), name],
    { cwd: fileURLToPath(root), maxBuffer: 1024 * 1024 })
}
