export async function readModelResponse(response, onProgress) {
  const total = Number(response.headers.get('content-length'))
  if (!response.body || !Number.isFinite(total) || total <= 0) {
    onProgress(null)
    return response.arrayBuffer()
  }

  const reader = response.body.getReader()
  const chunks = []
  let loaded = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
    loaded += value.byteLength
    onProgress(Math.min(99, Math.round(loaded / total * 100)))
  }
  const bytes = new Uint8Array(loaded)
  let offset = 0
  for (const chunk of chunks) {
    bytes.set(chunk, offset)
    offset += chunk.byteLength
  }
  return bytes.buffer
}
