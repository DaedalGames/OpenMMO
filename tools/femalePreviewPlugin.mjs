import { readFile, stat } from 'node:fs/promises'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { fileURLToPath } from 'node:url'
import { root, directory, sources, signature, output } from './lib/female-preview.mjs'

const execute = promisify(execFile)
const pending = new Map()

async function prepare(name) {
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

export function femalePreviewPlugin() {
  return {
    name: 'female-preview-assets',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const match = /^\/__female-preview\/(base|bob|knight)\.glb$|^\/__female-preview\/(animations)\.json$/.exec(req.url?.split('?')[0] ?? '')
        if (req.method !== 'GET' || !match) return next()
        const name = match[1] ?? match[2]
        if (!Object.hasOwn(sources, name)) return next()
        if (!pending.has(name)) pending.set(name, prepare(name).finally(() => pending.delete(name)))
        void pending.get(name).then(async () => {
          const compressed = name === 'animations' && /\bgzip\b/.test(req.headers['accept-encoding'] ?? '')
          const target = compressed ? new URL(output(name).href + '.gz') : output(name)
          const info = await stat(target)
          const etag = `W/"${info.size}-${info.mtimeMs}"`
          res.setHeader('Cache-Control', 'private, no-cache')
          res.setHeader('ETag', etag)
          if (name === 'animations') res.setHeader('Vary', 'Accept-Encoding')
          if (req.headers['if-none-match'] === etag) {
            res.statusCode = 304
            res.end()
            return
          }
          const bytes = await readFile(target)
          res.setHeader('Content-Type', name === 'animations' ? 'application/json' : 'model/gltf-binary')
          if (compressed) res.setHeader('Content-Encoding', 'gzip')
          res.setHeader('Content-Length', bytes.length)
          res.end(bytes)
        }).catch(next)
      })
    },
  }
}
