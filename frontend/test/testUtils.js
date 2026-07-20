import { mount } from '@vue/test-utils'

export function withSetup(composableFn) {
  let result
  const app = mount({
    setup() {
      result = composableFn()
      return () => null
    },
  })
  return { result, app }
}
