<template>
  <div class="application-content" :inert="isPortrait ? '' : null">
    <RouterView />
  </div>
  <section v-if="isPortrait" ref="orientationNotice" class="orientation-notice" role="dialog" aria-modal="true" aria-labelledby="orientation-title" tabindex="-1">
    <Laptop :size="36" aria-hidden="true" />
    <h1 id="orientation-title">{{ t('orientation.title') }}</h1>
    <p>{{ t('orientation.description') }}</p>
  </section>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { Laptop } from '@lucide/vue'
import { RouterView } from 'vue-router'
import { t } from '@/i18n/index.js'

const isPortrait = useMediaQuery('(orientation: portrait)')
const orientationNotice = ref(null)
let previousFocus = null

watch(isPortrait, async portrait => {
  if (portrait) {
    previousFocus = document.activeElement
    await nextTick()
    orientationNotice.value?.focus()
  } else {
    await nextTick()
    previousFocus?.focus?.()
    previousFocus = null
  }
}, { immediate: true })

const keepFocusInNotice = event => {
  if (isPortrait.value && orientationNotice.value && !orientationNotice.value.contains(event.target)) orientationNotice.value.focus()
}
onMounted(() => document.addEventListener('focusin', keepFocusInNotice))
onBeforeUnmount(() => document.removeEventListener('focusin', keepFocusInNotice))
</script>

<style scoped>
.application-content{width:100%;height:100%}
.orientation-notice{position:fixed;z-index:2147483647;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:24px;text-align:center;color:#303638;background:#e8edf2}
.orientation-notice svg{color:#e28245}
.orientation-notice h1{margin:0;font-size:22px;font-weight:600}
.orientation-notice p{margin:0;font-size:14px;color:#66706e}
</style>
