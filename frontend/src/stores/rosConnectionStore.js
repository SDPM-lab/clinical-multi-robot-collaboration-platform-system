import { computed, readonly, ref } from 'vue'

export const rosConnectionStates = Object.freeze({
  connected: Object.freeze({ color: '#6F9B7B', label: 'ROS 2 已連線' }),
  connecting: Object.freeze({ color: '#C59A52', label: 'ROS 2 連線中' }),
  disconnected: Object.freeze({ color: '#C96561', label: 'ROS 2 未連線' }),
})

const state = ref('disconnected')

const setState = (nextState) => {
  if (!(nextState in rosConnectionStates)) throw new Error(`Unknown ROS connection state: ${nextState}`)
  state.value = nextState
}

export const rosConnectionStore = Object.freeze({
  state: readonly(state),
  status: computed(() => rosConnectionStates[state.value]),
  setState,
  markConnected: () => setState('connected'),
  markConnecting: () => setState('connecting'),
  markDisconnected: () => setState('disconnected'),
})
