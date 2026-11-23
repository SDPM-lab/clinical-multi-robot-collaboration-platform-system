import { expect, it } from 'vitest'
import { readModelResponse } from '@/components/dispatch/readModelResponse.js'

it('reports download progress while retaining the complete model bytes', async () => {
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array([1, 2]))
      controller.enqueue(new Uint8Array([3, 4]))
      controller.close()
    },
  })
  const progress = []
  const response = new Response(stream, { headers: { 'content-length': '4' } })
  const result = await readModelResponse(response, value => progress.push(value))
  expect([...new Uint8Array(result)]).toEqual([1, 2, 3, 4])
  expect(progress).toEqual([50, 99])
})

it('shows indeterminate progress when the response size is unavailable', async () => {
  const progress = []
  const result = await readModelResponse(new Response(new Uint8Array([1, 2])), value => progress.push(value))
  expect([...new Uint8Array(result)]).toEqual([1, 2])
  expect(progress).toEqual([null])
})
