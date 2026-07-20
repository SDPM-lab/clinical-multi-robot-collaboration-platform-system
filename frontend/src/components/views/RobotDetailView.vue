<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import robotImg from '@/picture/機器人測試圖.png'
import { getRobotTasks } from '@/js/data/robotTasks.js'

const props = defineProps<{
  robots: Array<Record<string, any>>
}>()

const route = useRoute()
const router = useRouter()

const robot = computed(() =>
  props.robots.find(r => r.id === route.params.id) || null
)

const tasks = computed(() => getRobotTasks(route.params.id as string))

function goBack() {
  router.push({ name: 'robots' })
}

function openTask(taskId: string) {
  router.push({ name: 'robot-task-detail', params: { id: route.params.id, taskId } })
}

function isRobotOnline(r: Record<string, any>) {
  if (!r.lastUpdate) return false
  return Date.now() - new Date(r.lastUpdate).getTime() < 10000
}

function statusBadgeClass(status: string) {
  if (status === '待命' || status === '在線') return 'bg-emerald-50 text-emerald-600 border-emerald-200'
  if (status === '執行任務中') return 'bg-indigo-50 text-indigo-600 border-indigo-200'
  if (status === '忙碌') return 'bg-amber-50 text-amber-600 border-amber-200'
  if (status === '充電中') return 'bg-blue-50 text-blue-600 border-blue-200'
  if (status === '緊急停止') return 'bg-red-50 text-red-600 border-red-200'
  return 'bg-slate-100 text-slate-500 border-slate-200'
}

function taskStatusBadge(status: string) {
  if (status === '執行中') return { cls: 'task-badge--running', icon: '▶' }
  if (status === '已完成') return { cls: 'task-badge--done', icon: '✓' }
  return { cls: 'task-badge--pending', icon: '' }
}
</script>

<template>
  <div v-if="!robot" class="flex items-center justify-center py-20 text-muted-foreground">
    找不到此機器人
  </div>

  <div v-else class="robot-detail">
    <!-- Back -->
    <button class="back-btn" @click="goBack">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
      <span>返回機器人列表</span>
    </button>

    <!-- Hero Card -->
    <div class="hero-card">
      <div class="hero-card__accent"></div>
      <div class="hero-card__body">
        <div class="hero-card__row">
          <div class="hero-card__identity">
            <div class="hero-avatar">
              <img :src="robotImg" :alt="robot.name" class="hero-avatar__img" />
              <span class="hero-avatar__dot" :class="isRobotOnline(robot) ? 'hero-avatar__dot--on' : 'hero-avatar__dot--off'"></span>
            </div>
            <div>
              <h2 class="hero-card__name">{{ robot.name }}</h2>
              <p class="hero-card__sub">{{ robot.model }} · {{ robot.rosName || robot.id }}</p>
            </div>
          </div>
          <div class="hero-card__right">
            <Badge variant="outline" :class="statusBadgeClass(robot.status)">{{ robot.modeText || robot.status }}</Badge>
            <div class="hero-conn">
              <span class="hero-conn__dot" :class="isRobotOnline(robot) ? 'hero-conn__dot--on' : 'hero-conn__dot--off'"></span>
              <span class="hero-conn__text" :class="isRobotOnline(robot) ? 'text-emerald-600' : 'text-slate-400'">
                {{ isRobotOnline(robot) ? '已連線' : '未連線' }}
              </span>
              <span v-if="robot.connectionIp" class="hero-conn__ip">{{ robot.connectionIp }}</span>
            </div>
          </div>
        </div>

        <!-- Stats -->
        <div class="hero-stats">
          <div class="hero-stat">
            <span class="hero-stat__label">電量</span>
            <div class="hero-stat__value-row">
              <strong>{{ robot.battery }}%</strong>
            </div>
            <Progress
              :model-value="robot.battery"
              class="mt-1 h-1.5"
              :class="robot.battery < 30 ? '[&>[data-slot=progress-indicator]]:bg-red-500' : robot.battery < 70 ? '[&>[data-slot=progress-indicator]]:bg-amber-500' : '[&>[data-slot=progress-indicator]]:bg-emerald-500'"
            />
          </div>
          <div class="hero-stat">
            <span class="hero-stat__label">目前位置</span>
            <strong>{{ robot.location || '—' }}</strong>
          </div>
          <div class="hero-stat">
            <span class="hero-stat__label">運行時間</span>
            <strong>{{ robot.uptime }}</strong>
          </div>
          <div class="hero-stat">
            <span class="hero-stat__label">目前版本</span>
            <strong>{{ robot.firmware || '—' }}</strong>
          </div>
          <div class="hero-stat">
            <span class="hero-stat__label">更新日期</span>
            <strong>{{ robot.lastMaintenance || '—' }}</strong>
          </div>
          <div class="hero-stat">
            <span class="hero-stat__label">訊號品質</span>
            <strong>{{ robot.signal }}</strong>
          </div>
        </div>
      </div>
    </div>

    <!-- Tasks -->
    <section class="task-section">
      <div class="task-section__header">
        <h3 class="task-section__title">指派任務</h3>
        <span class="task-section__count">{{ tasks.length }} 項</span>
      </div>

      <div v-if="tasks.length === 0" class="task-empty">
        <span>尚無指派任務</span>
      </div>

      <div v-else class="task-list">
        <div
          v-for="(task, idx) in tasks"
          :key="task.id"
          class="task-card anim-scale-in"
          :class="`task-card--${task.status === '執行中' ? 'running' : task.status === '已完成' ? 'done' : 'pending'}`"
          :style="{ animationDelay: (idx * 0.06) + 's' }"
          role="button"
          tabindex="0"
          @click="openTask(task.id)"
          @keydown.enter.prevent="openTask(task.id)"
        >
          <!-- Left accent -->
          <div class="task-card__left-accent"></div>

          <div class="task-card__body">
            <div class="task-card__top-row">
              <div class="task-card__title-group">
                <h4 class="task-card__name">{{ task.name }}</h4>
                <span class="task-card__code">{{ task.code }}</span>
              </div>
              <div class="task-card__badge" :class="taskStatusBadge(task.status).cls">
                <span v-if="taskStatusBadge(task.status).icon" class="task-card__badge-icon">{{ taskStatusBadge(task.status).icon }}</span>
                {{ task.status }}
              </div>
            </div>

            <div class="task-card__bottom-row">
              <span class="task-card__stage">
                <template v-if="task.status === '已完成'">
                  全部 {{ task.steps.length }} 個步驟已完成
                  <span v-if="task.completedAt" class="task-card__time">· {{ task.completedAt }}</span>
                </template>
                <template v-else-if="task.currentStep > 0">
                  步驟 {{ task.currentStep }}/{{ task.steps.length }}：{{ task.steps[task.currentStep - 1] }}
                </template>
                <template v-else>
                  共 {{ task.steps.length }} 個步驟
                </template>
              </span>
              <svg class="task-card__chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
            </div>

            <!-- Progress bar (only for running tasks) -->
            <div v-if="task.status === '執行中' && task.currentStep > 0" class="task-card__progress">
              <div class="task-card__progress-fill" :style="{ width: Math.round((task.currentStep / task.steps.length) * 100) + '%' }"></div>
            </div>
            <!-- Completed bar -->
            <div v-else-if="task.status === '已完成'" class="task-card__progress task-card__progress--done">
              <div class="task-card__progress-fill task-card__progress-fill--done" style="width: 100%"></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.robot-detail {
  display: grid;
  gap: 1.5rem;
  max-width: 860px;
}

/* Back button */
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

/* Hero card */
.hero-card {
  border-radius: 1rem;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.hero-card__accent {
  height: 4px;
  background: linear-gradient(90deg, #6366f1, #818cf8, #a5b4fc);
}

.hero-card__body {
  padding: 1.5rem;
  display: grid;
  gap: 1.25rem;
}

.hero-card__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.hero-card__identity {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.hero-avatar {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 1rem;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.hero-avatar__img {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.hero-avatar__dot {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2.5px solid var(--color-background);
}

.hero-avatar__dot--on {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.hero-avatar__dot--off {
  background: #94a3b8;
}

.hero-card__name {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-foreground);
  margin: 0;
}

.hero-card__sub {
  font-size: 0.82rem;
  color: var(--color-muted-foreground);
  margin: 0.15rem 0 0;
}

.hero-card__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.hero-conn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
}

.hero-conn__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.hero-conn__dot--on {
  background: #22c55e;
  animation: dot-pulse 2s ease-in-out infinite;
}

.hero-conn__dot--off {
  background: #94a3b8;
}

.hero-conn__text {
  font-weight: 600;
}

.hero-conn__ip {
  font-family: ui-monospace, monospace;
  font-size: 0.72rem;
  color: var(--color-muted-foreground);
}

/* Stats grid */
.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.hero-stat {
  padding: 0.75rem 0.85rem;
  background: var(--color-muted);
  border-radius: 0.625rem;
}

.hero-stat__label {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-muted-foreground);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 0.25rem;
}

.hero-stat strong {
  font-size: 0.95rem;
  color: var(--color-foreground);
}

/* Task section */
.task-section {
  display: grid;
  gap: 0.85rem;
}

.task-section__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.task-section__title {
  font-size: 1rem;
  font-weight: 800;
  color: var(--color-foreground);
  margin: 0;
}

.task-section__count {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-muted-foreground);
  background: var(--color-muted);
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
}

.task-empty {
  padding: 2rem;
  text-align: center;
  color: var(--color-muted-foreground);
  font-size: 0.88rem;
  background: var(--color-muted);
  border-radius: 0.75rem;
}

.task-list {
  display: grid;
  gap: 0.6rem;
}

/* Task card */
.task-card {
  display: flex;
  border-radius: 0.75rem;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.task-card:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
}

.task-card:focus-visible {
  outline: 3px solid #60a5fa;
  outline-offset: 2px;
}

.task-card--running:hover { border-color: #a5b4fc; }
.task-card--done:hover { border-color: #86efac; }
.task-card--pending:hover { border-color: #cbd5e1; }

.task-card__left-accent {
  width: 4px;
  flex-shrink: 0;
}

.task-card--running .task-card__left-accent { background: #6366f1; }
.task-card--done .task-card__left-accent { background: #22c55e; }
.task-card--pending .task-card__left-accent { background: #cbd5e1; }

.task-card__body {
  flex: 1;
  padding: 0.85rem 1rem;
  display: grid;
  gap: 0.4rem;
  min-width: 0;
}

.task-card__top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.task-card__title-group {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

.task-card__name {
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--color-foreground);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-card--done .task-card__name {
  color: var(--color-muted-foreground);
}

.task-card__code {
  font-family: ui-monospace, monospace;
  font-weight: 600;
  font-size: 0.68rem;
  color: var(--color-muted-foreground);
  background: var(--color-muted);
  padding: 0.1rem 0.4rem;
  border-radius: 0.25rem;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Status badge */
.task-card__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  white-space: nowrap;
  flex-shrink: 0;
}

.task-card__badge-icon {
  font-size: 0.65rem;
}

.task-badge--running {
  background: #eef2ff;
  color: #4f46e5;
}

.task-badge--done {
  background: #f0fdf4;
  color: #16a34a;
}

.task-badge--pending {
  background: #f8fafc;
  color: #94a3b8;
}

.task-card__bottom-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.task-card__stage {
  font-size: 0.78rem;
  color: var(--color-muted-foreground);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card__time {
  color: var(--color-muted-foreground);
  opacity: 0.7;
}

.task-card__chevron {
  color: var(--color-muted-foreground);
  opacity: 0.4;
  flex-shrink: 0;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.task-card:hover .task-card__chevron {
  opacity: 0.8;
  transform: translateX(2px);
}

.task-card__progress {
  height: 3px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.15rem;
}

.task-card__progress--done {
  background: #dcfce7;
}

.task-card__progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #a5b4fc, #6366f1);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.task-card__progress-fill--done {
  background: linear-gradient(90deg, #86efac, #22c55e);
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(34, 197, 94, 0.5); }
  50% { opacity: 0.6; box-shadow: 0 0 2px rgba(34, 197, 94, 0.15); }
}

@media (max-width: 640px) {
  .hero-stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-card__body {
    padding: 1rem;
  }

  .task-card__title-group {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}
</style>
