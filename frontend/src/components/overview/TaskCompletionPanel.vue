<script setup>
import AnimatedProgressRing from './AnimatedProgressRing.vue'
import GlassPanel from './GlassPanel.vue'

defineProps({
  completion: { type: Number, required: true },
  animationKey: { type: Number, default: 0 },
})
</script>

<template>
  <GlassPanel class="completion-card">
    <AnimatedProgressRing
      :value="completion"
      :animation-key="animationKey"
    />
  </GlassPanel>
</template>

<style scoped>
.completion-card {
  position: relative;
  display: grid;
  height: 100%;
  padding: 10px;
  place-items: center;
}

.completion-card :deep(.glass-panel__content) { padding-top: 0; }
</style>
