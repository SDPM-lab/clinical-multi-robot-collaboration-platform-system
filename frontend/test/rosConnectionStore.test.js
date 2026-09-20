import { describe, expect, it } from 'vitest'
import { rosConnectionStates, rosConnectionStore } from '@/stores/rosConnectionStore.js'

describe('ROS 2 connection state', () => {
  it('defaults to disconnected and exposes all three real connection states', () => {
    rosConnectionStore.markDisconnected()
    expect(rosConnectionStore.state.value).toBe('disconnected')
    expect(rosConnectionStore.status.value.label).toBe('ROS 2 未連線')
    expect(Object.keys(rosConnectionStates)).toEqual(['connected', 'connecting', 'disconnected'])
  })

  it('can be updated later by a rosbridge or heartbeat adapter', () => {
    rosConnectionStore.markConnecting()
    expect(rosConnectionStore.status.value.color).toBe('#C59A52')
    rosConnectionStore.markConnected()
    expect(rosConnectionStore.status.value.color).toBe('#6F9B7B')
    rosConnectionStore.markDisconnected()
  })
})
