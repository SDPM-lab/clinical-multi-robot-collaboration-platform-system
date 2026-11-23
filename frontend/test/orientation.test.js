import { afterEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import App from '@/App.vue'

const portrait = ref(false)

vi.mock('@vueuse/core', () => ({ useMediaQuery: () => portrait }))
vi.mock('vue-router', () => ({ RouterView: { template: '<button type="button">Page action</button>' } }))
vi.mock('@/i18n/index.js', () => ({ t: key => key }))

afterEach(() => {
  portrait.value = false
  document.body.innerHTML = ''
})

it('blocks portrait interaction and restores the page in landscape', async () => {
  const wrapper = mount(App, { attachTo: document.body })
  const action = wrapper.get('button').element
  action.focus()

  portrait.value = true
  await nextTick()
  await nextTick()

  const notice = wrapper.get('[role="dialog"]').element
  expect(wrapper.get('.application-content').attributes()).toHaveProperty('inert')
  expect(document.activeElement).toBe(notice)

  const outsideButton = document.createElement('button')
  document.body.append(outsideButton)
  outsideButton.focus()
  expect(document.activeElement).toBe(notice)

  portrait.value = false
  await nextTick()
  await nextTick()

  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  expect(wrapper.get('.application-content').attributes()).not.toHaveProperty('inert')
  expect(document.activeElement).toBe(action)
  wrapper.unmount()
})