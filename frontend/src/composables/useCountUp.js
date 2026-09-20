import { inject, onBeforeUnmount, ref, toValue, watch } from 'vue'

const easeOutCubic = (progress) => 1 - ((1 - progress) ** 3)

export function useCountUp(target, options = {}) {
  const entranceDelay = options.delay ?? inject('overviewEntranceDelay', 0)
  let entranceTimer
  const duration = options.duration ?? 1000
  const easing = options.easing ?? easeOutCubic
  const displayed = ref(0)
  let animationFrameId
  let firstStagingFrameId
  let secondStagingFrameId
  let hasStarted = false

  const reducedMotion = () => (
    typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  )

  const targetValue = () => {
    const value = Number(toValue(target))
    return Number.isFinite(value) ? value : 0
  }

  const cancel = () => {
    clearTimeout(entranceTimer)
    cancelAnimationFrame(animationFrameId)
    cancelAnimationFrame(firstStagingFrameId)
    cancelAnimationFrame(secondStagingFrameId)
  }

  const animateTo = (nextValue = targetValue()) => {
    cancelAnimationFrame(animationFrameId)

    if (reducedMotion() || duration <= 0) {
      displayed.value = Math.round(nextValue)
      return
    }

    const startValue = displayed.value
    const difference = nextValue - startValue
    const startedAt = performance.now()

    const update = (time) => {
      const progress = Math.max(0, Math.min((time - startedAt) / duration, 1))
      displayed.value = Math.round(startValue + difference * easing(progress))

      if (progress < 1) animationFrameId = requestAnimationFrame(update)
    }

    animationFrameId = requestAnimationFrame(update)
  }

  const restart = () => {
    cancel()
    hasStarted = false
    displayed.value = 0

    if (reducedMotion()) {
      hasStarted = true
      displayed.value = Math.round(targetValue())
      return
    }

    firstStagingFrameId = requestAnimationFrame(() => {
      secondStagingFrameId = requestAnimationFrame(() => {
        const begin = () => { hasStarted = true; animateTo() }
        if (entranceDelay) entranceTimer = setTimeout(begin, entranceDelay)
        else begin()
      })
    })
  }

  watch(
    targetValue,
    (nextValue) => {
      if (hasStarted) animateTo(nextValue)
    },
  )

  onBeforeUnmount(cancel)

  return {
    displayed,
    animateTo,
    restart,
    cancel,
  }
}
