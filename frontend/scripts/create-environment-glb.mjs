import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

import { EMBEDDED_DYNAMIC_ROOTS } from '../src/config/sceneAssets.js'

const sourceUrl = new URL('../public/models/hospital.glb', import.meta.url)
const outputUrl = new URL('../public/models/hospital_environment.glb', import.meta.url)
const dynamicRootNames = new Set([
  ...EMBEDDED_DYNAMIC_ROOTS.robots,
  ...EMBEDDED_DYNAMIC_ROOTS.characters,
])

const source = await readFile(sourceUrl)
const jsonChunkLength = source.readUInt32LE(12)
const jsonChunkType = source.readUInt32LE(16)

if (jsonChunkType !== 0x4e4f534a) {
  throw new Error('Invalid GLB: the first chunk is not JSON.')
}

const json = JSON.parse(
  source.subarray(20, 20 + jsonChunkLength).toString('utf8').replace(/[\u0000 ]+$/, ''),
)
const activeScene = json.scenes?.[json.scene ?? 0]

if (!activeScene) {
  throw new Error('Invalid GLB: no active scene was found.')
}

const dynamicNodeIndexes = json.nodes
  .map((node, index) => (dynamicRootNames.has(node.name) ? index : null))
  .filter((index) => index !== null)

const missingNames = [...dynamicRootNames].filter(
  (name) => !json.nodes.some((node) => node.name === name),
)

if (missingNames.length > 0) {
  throw new Error(`Dynamic roots not found: ${missingNames.join(', ')}`)
}

const nonRootIndexes = dynamicNodeIndexes.filter((index) => !activeScene.nodes.includes(index))
if (nonRootIndexes.length > 0) {
  throw new Error(`Dynamic objects are no longer scene roots: ${nonRootIndexes.join(', ')}`)
}

const excludedIndexes = new Set(dynamicNodeIndexes)
activeScene.nodes = activeScene.nodes.filter((index) => !excludedIndexes.has(index))

const encodedJson = Buffer.from(JSON.stringify(json))
const paddingLength = (4 - (encodedJson.length % 4)) % 4
const paddedJson = Buffer.concat([encodedJson, Buffer.alloc(paddingLength, 0x20)])
const remainingChunks = source.subarray(20 + jsonChunkLength)
const output = Buffer.alloc(20 + paddedJson.length + remainingChunks.length)

source.copy(output, 0, 0, 12)
output.writeUInt32LE(output.length, 8)
output.writeUInt32LE(paddedJson.length, 12)
output.writeUInt32LE(0x4e4f534a, 16)
paddedJson.copy(output, 20)
remainingChunks.copy(output, 20 + paddedJson.length)

await writeFile(outputUrl, output)

console.log(`Created ${fileURLToPath(outputUrl)}`)
console.log(`Excluded scene roots: ${[...dynamicRootNames].join(', ')}`)
