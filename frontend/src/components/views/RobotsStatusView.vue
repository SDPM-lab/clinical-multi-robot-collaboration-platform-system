<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Badge } from '@/components/ui/badge'
import robotImg from '@/picture/機器人測試圖.png'

defineProps<{
  robots: Array<Record<string, any>>
}>()

const router = useRouter()

function openDetail(robot: Record<string, any>) {
  router.push({ name: 'robot-detail', params: { id: robot.id } })
}

function isRobotOnline(robot: Record<string, any>) {
  if (!robot.lastUpdate) return false
  return Date.now() - new Date(robot.lastUpdate).getTime() < 10000
}

function statusBadgeClass(status: string) {
  if (status === '待命' || status === '在線') return 'bg-emerald-50 text-emerald-600 border-emerald-200'
  if (status === '執行任務中') return 'bg-indigo-50 text-indigo-600 border-indigo-200'
  if (status === '忙碌') return 'bg-amber-50 text-amber-600 border-amber-200'
  if (status === '充電中') return 'bg-blue-50 text-blue-600 border-blue-200'
  if (status === '緊急停止') return 'bg-red-50 text-red-600 border-red-200'
  return 'bg-slate-100 text-slate-500 border-slate-200'
}
</script>

<template>
  <div class="robots-grid">
    <div
      v-for="(robot, idx) in robots"
      :key="robot.id"
      class="robot-card anim-scale-in"
      :class="{ 'robot-card--disabled': !isRobotOnline(robot) }"
      :style="{ animationDelay: (idx * 0.08) + 's' }"
      :tabindex="isRobotOnline(robot) ? 0 : -1"
      :role="isRobotOnline(robot) ? 'button' : undefined"
      @click="isRobotOnline(robot) && openDetail(robot)"
      @keydown.enter.prevent="isRobotOnline(robot) && openDetail(robot)"
    >
      <div class="robot-card__accent" :class="isRobotOnline(robot) ? 'robot-card__accent--online' : 'robot-card__accent--offline'"></div>
      <div class="robot-card__body">
        <div class="robot-card__top">
          <div class="robot-avatar">
            <img :src="robotImg" :alt="robot.name" class="robot-avatar__img" />
            <span
              class="robot-avatar__dot"
              :class="isRobotOnline(robot) ? 'robot-avatar__dot--online' : 'robot-avatar__dot--offline'"
            ></span>
          </div>
          <div class="robot-card__info">
            <h3 class="robot-card__name">{{ robot.name }}</h3>
            <p class="robot-card__model">{{ robot.model }}</p>
          </div>
          <Badge variant="outline" :class="statusBadgeClass(robot.status)">{{ robot.modeText || robot.status }}</Badge>
        </div>

        <div class="robot-card__stats">
          <div class="robot-card__stat">
            <span class="robot-card__stat-label">電量</span>
            <div class="robot-card__battery">
              <div class="robot-card__battery-fill" :style="{ width: robot.battery + '%' }" :class="robot.battery < 30 ? 'battery--low' : robot.battery < 70 ? 'battery--mid' : 'battery--high'"></div>
            </div>
            <span class="robot-card__stat-value">{{ robot.battery }}%</span>
          </div>
          <div class="robot-card__stat">
            <span class="robot-card__stat-label">位置</span>
            <span class="robot-card__stat-value">{{ robot.location || '—' }}</span>
          </div>
        </div>

        <div class="robot-card__footer">
          <span class="robot-card__task-tag" :class="robot.currentTaskDetail?.taskNo !== '—' ? 'task-tag--active' : 'task-tag--idle'">
            {{ robot.currentTaskDetail?.taskNo !== '—' ? robot.currentTaskDetail.step : '無任務' }}
          </span>
          <svg class="robot-card__arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.robots-grid {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
}

.robot-card {
  position: relative;
  border-radius: 0.875rem;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}

.robot-card:not(.robot-card--disabled):hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.1);
  border-color: #a5b4fc;
}

.robot-card:not(.robot-card--disabled):focus-visible {
  outline: 3px solid #60a5fa;
  outline-offset: 2px;
}

.robot-card--disabled {
  opacity: 0.55;
  cursor: not-allowed;
  pointer-events: none;
}

.robot-card__accent {
  height: 4px;
}

.robot-card__accent--online {
  background: linear-gradient(90deg, #22c55e, #4ade80);
}

.robot-card__accent--offline {
  background: linear-gradient(90deg, #94a3b8, #cbd5e1);
}

.robot-card__body {
  padding: 1rem 1.15rem;
  display: grid;
  gap: 0.85rem;
}

.robot-card__top {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.robot-card__info {
  flex: 1;
  min-width: 0;
}

.robot-card__name {
  font-weight: 700;
  font-size: 0.95rem;
  line-height: 1.3;
  color: var(--color-foreground);
  margin: 0;
}

.robot-card__model {
  font-size: 0.75rem;
  color: var(--color-muted-foreground);
  margin: 0.1rem 0 0;
}

.robot-avatar {
  position: relative;
  width: 52px;
  height: 52px;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, #f0f4ff, #e8ecf4);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.robot-avatar__img {
  width: 30px;
  height: 30px;
  object-fit: contain;
}

.robot-avatar__dot {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 2.5px solid var(--color-background);
}

.robot-avatar__dot--online {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.robot-avatar__dot--offline {
  background: #94a3b8;
}

.robot-card__stats {
  display: grid;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
  background: var(--color-muted);
  border-radius: 0.5rem;
}

.robot-card__stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.robot-card__stat-label {
  color: var(--color-muted-foreground);
  font-weight: 600;
  width: 2.5rem;
  flex-shrink: 0;
}

.robot-card__stat-value {
  color: var(--color-foreground);
  font-weight: 600;
  font-size: 0.78rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.robot-card__battery {
  flex: 1;
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.robot-card__battery-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}

.battery--high { background: linear-gradient(90deg, #22c55e, #4ade80); }
.battery--mid  { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.battery--low  { background: linear-gradient(90deg, #ef4444, #f87171); }

.robot-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.robot-card__task-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
}

.task-tag--active {
  background: #eef2ff;
  color: #4338ca;
}

.task-tag--idle {
  background: #f1f5f9;
  color: #94a3b8;
}

.robot-card__arrow {
  color: var(--color-muted-foreground);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.robot-card:hover .robot-card__arrow {
  transform: translateX(3px);
  color: #6366f1;
}

@media (max-width: 768px) {
  .robots-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
}
</style>
