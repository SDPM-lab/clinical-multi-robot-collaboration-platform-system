<script setup>
import { computed, watch } from 'vue'
import { CheckCircle2, Clock3, LoaderCircle } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import GlassPanel from './GlassPanel.vue'

const props = defineProps({
  data: {
    type: Object,
    default: null,
  },
  completion: { type: Number, default: 0 },
  animationKey: { type: Number, default: 0 },
})

const completedTarget = computed(() => props.data?.completed ?? 0)
const activeTarget = computed(() => props.data?.inProgress ?? 0)
const waitingTarget = computed(() => props.data?.waiting ?? 0)
const completionTarget = computed(() => props.completion)

const { displayed: completed, restart: restartCompleted } = useCountUp(completedTarget, { duration: 2200 })
const { displayed: active, restart: restartActive } = useCountUp(activeTarget, { duration: 2100 })
const { displayed: waiting, restart: restartWaiting } = useCountUp(waitingTarget, { duration: 2100 })
const { displayed: displayedCompletion, restart: restartCompletion } = useCountUp(completionTarget, { duration: 2300 })

watch(() => props.animationKey, () => {
  restartCompleted()
  restartActive()
  restartWaiting()
  restartCompletion()
})
</script>

<template>
  <GlassPanel title="今日任務">
    <template #header-meta><small class="demo-label">展示資料</small></template>
    <dl class="panel-list">
      <div class="panel-row">
        <dt><CheckCircle2 :size="17" />已完成</dt>
        <dd>{{ completed }}</dd>
      </div>
      <div class="panel-row">
        <dt><LoaderCircle :size="17" />執行中</dt>
        <dd>{{ active }}</dd>
      </div>
      <div class="panel-row">
        <dt><Clock3 :size="17" />等待中</dt>
        <dd>{{ waiting }}</dd>
      </div>
    </dl>
    <div class="task-progress">
      <div class="task-progress__meta">
        <span>今日任務進度</span>
        <strong>{{ displayedCompletion }}%</strong>
      </div>
      <div class="task-progress__track">
        <span
          class="task-progress__fill"
          :style="{ width: `${displayedCompletion}%` }"
        ></span>
      </div>
    </div>
  </GlassPanel>
</template>

<style scoped>
.demo-label { color: var(--text-secondary); font-size: 12.5px; font-weight: 500; opacity: 0.78; }
.panel-list { margin: 0; }
.panel-row { display: flex; align-items: center; justify-content: space-between; min-height: 36px; gap: 14px; }
.panel-row dt { display: flex; align-items: center; gap: 10px; color: var(--text-secondary); font-size: 14px; }
.panel-row dt :deep(svg) { color: var(--wood-accent); stroke-width: 1.7; }
.panel-row dd { margin: 0; color: var(--text-primary); font-size: 16px; font-weight: 650; }
.task-progress { margin-top: 7px; }
.task-progress__meta { display: flex; justify-content: space-between; margin-bottom: 8px; color: var(--text-secondary); font-size: 12.5px; }
.task-progress__meta strong { color: var(--text-primary); font-weight: 650; }
.task-progress__track { height: 7px; overflow: hidden; background: var(--progress-track); border-radius: 5px; }
.task-progress__fill { display: block; height: 100%; background: var(--accent-orange); border-radius: 4px; }
</style>
