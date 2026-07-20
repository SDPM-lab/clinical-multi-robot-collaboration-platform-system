<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { getRobotTask } from '@/js/data/robotTasks.js'

const props = defineProps<{
  robots: Array<Record<string, any>>
}>()

const route = useRoute()
const router = useRouter()

const robotId = computed(() => route.params.id as string)
const taskId = computed(() => route.params.taskId as string)

const robot = computed(() =>
  props.robots.find(r => r.id === robotId.value) || null
)

const task = computed(() => getRobotTask(robotId.value, taskId.value))

const progressPercent = computed(() => {
  if (!task.value) return 0
  if (task.value.status === '已完成') return 100
  if (task.value.currentStep <= 0) return 0
  return Math.round((task.value.currentStep / task.value.steps.length) * 100)
})

function goBack() {
  router.push({ name: 'robot-detail', params: { id: robotId.value } })
}

function stepStatus(stepIndex: number, currentStep: number, isDone: boolean) {
  if (isDone) return 'done'
  if (currentStep === 0) return 'pending'
  if (stepIndex < currentStep - 1) return 'done'
  if (stepIndex === currentStep - 1) return 'active'
  return 'pending'
}
</script>

<template>
  <div v-if="!task || !robot" class="flex items-center justify-center py-20 text-muted-foreground">
    找不到此任務
  </div>

  <div v-else class="task-detail">
    <!-- Back -->
    <button class="back-btn" @click="goBack">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
      <span>返回 {{ robot.name }}</span>
    </button>

    <!-- Task Hero -->
    <Card class="task-hero" :class="task.status === '已完成' ? 'task-hero--done' : task.status === '執行中' ? 'task-hero--running' : ''">
      <div class="task-hero__accent"></div>
      <CardContent class="task-hero__body">
        <div class="task-hero__row">
          <div>
            <h2 class="task-hero__name">{{ task.name }}</h2>
            <div class="task-hero__meta">
              <span class="task-hero__code">{{ task.code }}</span>
              <span class="task-hero__robot">{{ robot.name }}</span>
              <span v-if="task.completedAt" class="task-hero__time">{{ task.completedAt }}</span>
            </div>
          </div>
          <div class="task-hero__badge" :class="task.status === '已完成' ? 'task-hero__badge--done' : task.status === '執行中' ? 'task-hero__badge--running' : 'task-hero__badge--pending'">
            <svg v-if="task.status === '已完成'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            {{ task.status }}
          </div>
        </div>

        <!-- Progress -->
        <div class="task-hero__progress-wrap">
          <div class="task-hero__progress-labels">
            <span>執行進度</span>
            <strong>{{ progressPercent }}%</strong>
          </div>
          <div class="task-hero__progress-track">
            <div class="task-hero__progress-fill" :class="task.status === '已完成' ? 'task-hero__progress-fill--done' : ''" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <div class="task-hero__progress-steps">
            {{ task.status === '已完成' ? task.steps.length : (task.currentStep > 0 ? task.currentStep : 0) }} / {{ task.steps.length }} 步驟
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Steps Timeline -->
    <div class="steps-card">
      <div class="steps-card__header">
        <h3 class="steps-card__title">指令步驟</h3>
      </div>
      <ol class="steps-timeline">
        <li
          v-for="(step, idx) in task.steps"
          :key="idx"
          class="step"
          :class="`step--${stepStatus(idx, task.currentStep, task.status === '已完成')}`"
        >
          <div class="step__rail">
            <div class="step__dot">
              <svg v-if="stepStatus(idx, task.currentStep, task.status === '已完成') === 'done'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
              <span v-else-if="stepStatus(idx, task.currentStep, task.status === '已完成') === 'active'" class="step__dot-inner"></span>
              <span v-else class="step__number">{{ idx + 1 }}</span>
            </div>
            <div v-if="idx < task.steps.length - 1" class="step__line"></div>
          </div>

          <div class="step__body">
            <div class="step__label-row">
              <span class="step__index">步驟 {{ idx + 1 }}</span>
              <Badge v-if="stepStatus(idx, task.currentStep, task.status === '已完成') === 'active'" variant="outline" class="step__status-badge step__status-badge--active">
                進行中
              </Badge>
              <Badge v-else-if="stepStatus(idx, task.currentStep, task.status === '已完成') === 'done'" variant="outline" class="step__status-badge step__status-badge--done">
                已完成
              </Badge>
            </div>
            <p class="step__text">{{ step }}</p>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<style scoped>
.task-detail {
  display: grid;
  gap: 1.25rem;
  max-width: 740px;
}

/* Back */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-muted-foreground);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  transition: color 0.15s ease;
  width: fit-content;
}

.back-btn:hover {
  color: var(--color-foreground);
}

/* Task Hero */
.task-hero {
  overflow: hidden;
}

.task-hero__accent {
  height: 4px;
  background: linear-gradient(90deg, #cbd5e1, #94a3b8);
}

.task-hero--running .task-hero__accent {
  background: linear-gradient(90deg, #6366f1, #818cf8, #a5b4fc);
}

.task-hero--done .task-hero__accent {
  background: linear-gradient(90deg, #16a34a, #22c55e, #4ade80);
}

.task-hero__body {
  padding: 1.5rem !important;
  display: grid;
  gap: 1.25rem;
}

.task-hero__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.task-hero__name {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-foreground);
  margin: 0;
}

.task-hero__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.35rem;
  flex-wrap: wrap;
}

.task-hero__code {
  font-family: ui-monospace, monospace;
  font-weight: 600;
  font-size: 0.75rem;
  color: var(--color-muted-foreground);
  background: var(--color-muted);
  padding: 0.12rem 0.45rem;
  border-radius: 0.25rem;
}

.task-hero__robot,
.task-hero__time {
  font-size: 0.8rem;
  color: var(--color-muted-foreground);
}

.task-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.3rem 0.75rem;
  border-radius: 999px;
  white-space: nowrap;
}

.task-hero__badge--running {
  background: #eef2ff;
  color: #4f46e5;
}

.task-hero__badge--done {
  background: #f0fdf4;
  color: #16a34a;
}

.task-hero__badge--pending {
  background: #f8fafc;
  color: #94a3b8;
}

/* Progress */
.task-hero__progress-wrap {
  display: grid;
  gap: 0.4rem;
}

.task-hero__progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.82rem;
  color: var(--color-muted-foreground);
}

.task-hero__progress-labels strong {
  color: var(--color-foreground);
}

.task-hero__progress-track {
  height: 8px;
  background: var(--color-muted);
  border-radius: 999px;
  overflow: hidden;
}

.task-hero__progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #a5b4fc, #6366f1);
  border-radius: 999px;
  transition: width 0.5s ease;
}

.task-hero__progress-fill--done {
  background: linear-gradient(90deg, #86efac, #22c55e);
}

.task-hero__progress-steps {
  font-size: 0.75rem;
  color: var(--color-muted-foreground);
  text-align: right;
}

/* Steps card */
.steps-card {
  border-radius: 0.75rem;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.steps-card__header {
  padding: 1rem 1.25rem 0;
}

.steps-card__title {
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--color-foreground);
  margin: 0;
}

.steps-timeline {
  list-style: none;
  padding: 1rem 1.25rem 1.25rem;
  margin: 0;
}

/* Step */
.step {
  display: flex;
  gap: 0.85rem;
}

.step__rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  width: 28px;
}

.step__dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 0.7rem;
  font-weight: 700;
  transition: all 0.25s ease;
}

.step--done .step__dot {
  background: #dcfce7;
  color: #16a34a;
}

.step--active .step__dot {
  background: #6366f1;
  color: white;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}

.step--pending .step__dot {
  background: var(--color-muted);
  color: var(--color-muted-foreground);
  border: 1.5px solid var(--color-border);
}

.step__dot-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
  animation: inner-pulse 2s ease-in-out infinite;
}

.step__number {
  font-size: 0.7rem;
}

.step__line {
  flex: 1;
  width: 2px;
  min-height: 0.75rem;
  margin: 0.2rem 0;
}

.step--done .step__line { background: #bbf7d0; }
.step--active .step__line { background: linear-gradient(to bottom, #818cf8 0%, var(--color-border) 100%); }
.step--pending .step__line { background: var(--color-border); }

.step__body {
  padding: 0.3rem 0 1rem;
  min-width: 0;
}

.step__label-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.step__index {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.step--done .step__index { color: #16a34a; }
.step--active .step__index { color: #4f46e5; }
.step--pending .step__index { color: var(--color-muted-foreground); opacity: 0.6; }

.step__status-badge {
  font-size: 0.65rem;
  padding: 0 0.4rem;
  height: 1.25rem;
}

.step__status-badge--active {
  background: #eef2ff;
  color: #4f46e5;
  border-color: #c7d2fe;
}

.step__status-badge--done {
  background: #f0fdf4;
  color: #16a34a;
  border-color: #bbf7d0;
}

.step__text {
  font-size: 0.88rem;
  margin: 0.2rem 0 0;
  line-height: 1.45;
}

.step--done .step__text { color: var(--color-muted-foreground); }
.step--active .step__text { color: var(--color-foreground); font-weight: 600; }
.step--pending .step__text { color: var(--color-muted-foreground); opacity: 0.7; }

@keyframes inner-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
