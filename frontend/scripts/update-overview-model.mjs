import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const frontendRoot = fileURLToPath(new URL('..', import.meta.url))
const projectRoot = path.resolve(frontendRoot, '..')
const blendPath = path.join(projectRoot, 'blender/scenes/hospital_overview.blend')
const exportScript = path.join(projectRoot, 'blender/scripts/export_hospital_overview_glb.py')
const modelPath = path.join(frontendRoot, 'public/models/hospital_overview.glb')
const dataPath = path.join(frontendRoot, 'src/data/clinicOverviewData.js')
const urlPattern = /export const clinicOverviewModelUrl = '\/models\/hospital_overview\.glb\?v=[a-f0-9]+'/g
const windowsBlenderRoot = '/mnt/c/Program Files/Blender Foundation'

function run(binary, args, options = {}) {
  const result = spawnSync(binary, args, {
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
    ...options,
  })
  if (result.error || result.status !== 0) {
    const output = [result.stdout, result.stderr].filter(Boolean).join('\n')
    throw new Error(binary + ' failed: ' + (result.error?.message || output.trim().split('\n').slice(-35).join('\n')))
  }
  return result.stdout.trim()
}

function findBlender() {
  if (process.env.BLENDER_BIN) return process.env.BLENDER_BIN
  if (process.platform === 'linux' && existsSync(windowsBlenderRoot)) {
    const versions = readdirSync(windowsBlenderRoot)
      .map((name) => ({ name, match: /^Blender (\d+)\.(\d+)$/.exec(name) }))
      .filter(({ match }) => match && (Number(match[1]) > 5 || (Number(match[1]) === 5 && Number(match[2]) >= 2)))
      .sort((a, b) => Number(b.match[1]) - Number(a.match[1]) || Number(b.match[2]) - Number(a.match[2]))
    for (const { name } of versions) {
      const binary = path.join(windowsBlenderRoot, name, 'blender.exe')
      if (existsSync(binary)) return binary
    }
  }
  return process.platform === 'win32' ? 'blender.exe' : 'blender'
}

function isWindowsBlender(binary) {
  return process.platform === 'win32' || (process.platform === 'linux' && binary.toLowerCase().endsWith('.exe'))
}

function blenderPath(localPath, windowsBinary) {
  if (process.platform === 'linux' && windowsBinary) return run('wslpath', ['-w', localPath])
  return localPath
}

function localExportPath(exportedPath, windowsBinary) {
  if (process.platform === 'linux' && windowsBinary) return run('wslpath', ['-u', exportedPath])
  return exportedPath
}

function validateGlb(bytes) {
  if (bytes.length < 20 || bytes.toString('ascii', 0, 4) !== 'glTF' || bytes.readUInt32LE(8) !== bytes.length) {
    throw new Error('Blender produced an invalid GLB header or file length.')
  }
  if (bytes.toString('ascii', 16, 20) !== 'JSON') throw new Error('GLB JSON chunk is missing.')
  const jsonLength = bytes.readUInt32LE(12)
  if (20 + jsonLength > bytes.length) throw new Error('GLB JSON chunk is incomplete.')
  const gltf = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString())
  if (gltf.asset?.version !== '2.0' || !gltf.nodes?.length || !gltf.meshes?.length || !gltf.scenes?.[gltf.scene ?? 0]?.nodes?.length) {
    throw new Error('Exported GLB has no usable default scene.')
  }
  return { nodes: gltf.nodes.length, meshes: gltf.meshes.length }
}

if (!existsSync(blendPath)) throw new Error('Missing Blender file: ' + blendPath)
const sourceStat = statSync(blendPath)
const blender = findBlender()
const windowsBinary = isWindowsBlender(blender)
const output = run(blender, [
  '--background', blenderPath(blendPath, windowsBinary),
  '--python', blenderPath(exportScript, windowsBinary),
])
const exportedPath = output.match(/^OVERVIEW_GLB_PATH=(.+)$/m)?.[1]?.trim()
if (!exportedPath) throw new Error('Blender did not report an exported GLB.\n' + output.split('\n').slice(-35).join('\n'))
const localPath = localExportPath(exportedPath, windowsBinary)
const tempDirectory = path.dirname(localPath)
try {
  const bytes = readFileSync(localPath)
  const { nodes, meshes } = validateGlb(bytes)
  const currentSourceStat = statSync(blendPath)
  if (currentSourceStat.size !== sourceStat.size || currentSourceStat.mtimeMs !== sourceStat.mtimeMs) {
    throw new Error('The Blender file changed during export. Run the command again.')
  }
  const revision = createHash('sha256').update(bytes).digest('hex').slice(0, 8)
  const source = readFileSync(dataPath, 'utf8')
  const matches = [...source.matchAll(urlPattern)]
  if (matches.length !== 1) throw new Error('Expected exactly one overview model URL in ' + dataPath)
  const updated = source.replace(urlPattern, "export const clinicOverviewModelUrl = '/models/hospital_overview.glb?v=" + revision + "'")

  if (!existsSync(modelPath) || !readFileSync(modelPath).equals(bytes)) {
    const staging = modelPath + '.tmp-' + process.pid
    try {
      writeFileSync(staging, bytes)
      renameSync(staging, modelPath)
    } finally {
      if (existsSync(staging)) rmSync(staging)
    }
  }
  if (updated !== source) {
    const staging = dataPath + '.tmp-' + process.pid
    try {
      writeFileSync(staging, updated)
      renameSync(staging, dataPath)
    } finally {
      if (existsSync(staging)) rmSync(staging)
    }
  }
  console.log('Updated hospital overview: ' + nodes + ' nodes, ' + meshes + ' meshes, ' + statSync(modelPath).size + ' bytes')
  console.log('Model URL: /models/hospital_overview.glb?v=' + revision)
  console.log('Reload the open dashboard tab to see the new model.')
} finally {
  if (path.basename(tempDirectory).startsWith('hospital-overview-export-')) rmSync(tempDirectory, { recursive: true, force: true })
}
