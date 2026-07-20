<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { STATUS_LABEL } from '@/js/data/taskMeta.js'

function statusClass(status: string) {
  if (status === 'process')  return 'bg-blue-50   text-blue-600   border-blue-200'
  if (status === 'complete') return 'bg-emerald-50 text-emerald-600 border-emerald-200'
  if (status === 'abort')    return 'bg-rose-50    text-rose-600   border-rose-200'
  if (status === 'timeout')  return 'bg-orange-50  text-orange-600 border-orange-200'
  return                            'bg-slate-50   text-slate-500  border-slate-200'
}

defineProps<{
  ganttChart: Record<string, any>
  ganttZoom: number
  ganttVisualScale: number
  zoomMin: number
  zoomMax: number
  historyTasks: Array<Record<string, any>>
  robotNameMap: Record<string, string>
}>()

const emit = defineEmits<{
  'zoom-in': []
  'zoom-out': []
  'zoom-reset': []
  'set-zoom': [value: number]
}>()
</script>

<template>
  <div class="grid gap-4">
    <Card class="anim-fade-in-up">
      <CardContent class="p-4">
        <div class="gantt-toolbar mb-3">
          <h2 class="font-bold mb-0">任務排程</h2>
          <div class="flex items-center gap-4 flex-wrap">
            <div class="flex items-center gap-2 zoom-slider-wrap">
              <span class="text-sm text-muted-foreground font-semibold">−</span>
              <input
                type="range"
                class="zoom-slider"
                :min="zoomMin"
                :max="zoomMax"
                step="0.25"
                :value="ganttZoom"
                @input="emit('set-zoom', +($event.target as HTMLInputElement).value)"
                aria-label="縮放"
              />
              <span class="text-sm text-muted-foreground font-semibold">+</span>
              <Badge
                variant="outline"
                class="zoom-label cursor-pointer"
                @click="emit('zoom-reset')"
                title="點擊重置"
              >{{ Math.round(ganttZoom * 100) }}%</Badge>
            </div>
            <div class="flex gap-3 flex-wrap">
              <span class="flex items-center gap-1 text-sm text-muted-foreground"><span class="legend-dot legend-dot--done"></span>完成</span>
              <span class="flex items-center gap-1 text-sm text-muted-foreground"><span class="legend-dot legend-dot--progress"></span>進行中</span>
              <span class="flex items-center gap-1 text-sm text-muted-foreground"><span class="legend-dot legend-dot--pending"></span>待處理</span>
              <span class="flex items-center gap-1 text-sm text-muted-foreground"><span class="legend-dot legend-dot--abort"></span>中斷</span>
              <span class="flex items-center gap-1 text-sm text-muted-foreground"><span class="legend-dot legend-dot--timeout"></span>超時</span>
            </div>
          </div>
        </div>

        <div v-if="ganttChart.rows.length === 0" class="text-center text-muted-foreground py-8">尚無可顯示的任務時段</div>

        <div v-else class="gantt-chart" :style="{ '--gantt-visual-scale': ganttVisualScale }">
          <div class="gantt-row gantt-row--axis">
            <div class="gantt-label"></div>
            <div class="gantt-track gantt-track--axis">
              <div
                v-for="tick in ganttChart.ticks"
                :key="tick.key"
                class="gantt-axis-mark"
                :class="{ 'gantt-axis-mark--minor': !tick.isMajor }"
                :style="{ left: tick.left + '%' }"
              >
                <span v-if="tick.label" class="gantt-axis-label">{{ tick.label }}</span>
              </div>
            </div>
          </div>

          <div v-for="row in ganttChart.rows" :key="row.robotId" class="gantt-row">
            <div class="gantt-label">{{ row.robotName }}</div>
            <div class="gantt-track">
              <div
                v-for="tick in ganttChart.ticks"
                :key="`grid-${row.robotId}-${tick.key}`"
                class="gantt-grid-line"
                :class="{ 'gantt-grid-line--minor': !tick.isMajor }"
                :style="{ left: tick.left + '%' }"
              ></div>
              <div
                v-for="bar in row.bars"
                :key="bar.id"
                class="gantt-bar"
                :class="{
                  'gantt-bar--done':     bar.status === 'complete',
                  'gantt-bar--progress': bar.status === 'process',
                  'gantt-bar--pending':  bar.status === 'idle',
                  'gantt-bar--abort':    bar.status === 'abort',
                  'gantt-bar--timeout':  bar.status === 'timeout',
                }"
                :style="{ left: bar.left + '%', width: bar.width + '%' }"
                :title="`${bar.taskNo} ${bar.title} (${bar.startTime} - ${bar.due})`"
              >
                <span class="gantt-bar-text">{{ bar.taskNo }} {{ bar.title }}</span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card class="anim-fade-in-up anim-delay-2">
      <CardContent class="p-4">
        <h2 class="font-bold mb-3">任務清單</h2>
        <div class="grid gap-3">
          <div v-for="(task, idx) in historyTasks" :key="task.id" class="flex justify-between items-center gap-2 anim-fade-in-left" :style="{ animationDelay: (idx * 0.06) + 's' }">
            <div>
              <h3 class="font-bold text-base flex items-center gap-2 flex-wrap mb-1">
                <span class="task-no-badge">{{ task.taskNo }}</span>
                {{ task.title }}
              </h3>
              <p class="text-muted-foreground text-sm mb-0">
                {{ robotNameMap[task.assignedTo] || task.assignedTo }}
                •
                <template v-if="task.startDate || task.startTime">
                  {{ task.startDate }} {{ task.startTime }}
                  <template v-if="task.status !== 'idle' && task.status !== 'process' && task.endDate">
                    → {{ task.endDate }} {{ task.endTime }}
                  </template>
                </template>
                <template v-else>未指定時間</template>
              </p>
            </div>
            <Badge
              variant="outline"
              :class="statusClass(task.status)"
            >{{ STATUS_LABEL[task.status] ?? task.status }}</Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.gantt-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.zoom-slider-wrap {
  min-width: 180px;
}

.zoom-slider {
  width: 120px;
  cursor: pointer;
  accent-color: var(--color-primary);
}

.zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  transition: background 0.2s ease;
}

.zoom-label:hover {
  background: #e0e7ff !important;
}

.legend-dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
}

.legend-dot--done    { background: #10b981; }
.legend-dot--progress { background: #3b82f6; }
.legend-dot--pending { background: #64748b; }
.legend-dot--abort   { background: #e11d48; }
.legend-dot--timeout { background: #ea580c; }

.gantt-chart {
  display: grid;
  gap: 0.5rem;
  overflow-x: auto;
  --gantt-visual-scale: 1;
  scroll-behavior: smooth;
}

.gantt-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 0.75rem;
  align-items: stretch;
  min-height: 42px;
  width: calc(100% * var(--gantt-visual-scale));
  min-width: 100%;
  animation: fadeInUp 0.35s ease both;
}

.gantt-row:nth-child(1) { animation-delay: 0.05s; }
.gantt-row:nth-child(2) { animation-delay: 0.1s; }
.gantt-row:nth-child(3) { animation-delay: 0.15s; }
.gantt-row:nth-child(4) { animation-delay: 0.2s; }
.gantt-row:nth-child(5) { animation-delay: 0.25s; }
.gantt-row:nth-child(6) { animation-delay: 0.3s; }

.gantt-row--axis { min-height: 28px; }

.gantt-label {
  font-weight: 600;
  color: var(--color-foreground);
  display: flex;
  align-items: center;
  font-size: 0.92rem;
  position: sticky;
  left: 0;
  background: var(--color-card);
  z-index: 2;
  padding-right: 0.5rem;
}

.gantt-track {
  position: relative;
  background: #f1f5f9;
  border-radius: calc(var(--radius) - 2px);
  min-height: 38px;
}

.gantt-track--axis {
  background: transparent;
  border-bottom: 1px solid #cbd5e1;
  min-height: 24px;
}

.gantt-axis-mark {
  position: absolute;
  top: 0;
  bottom: 0;
  transform: translateX(-50%);
  display: flex;
  align-items: flex-end;
}

.gantt-axis-mark--minor::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 1px;
  height: 6px;
  background: #cbd5e1;
}

.gantt-axis-label {
  font-size: 0.78rem;
  color: #475569;
  white-space: nowrap;
}

.gantt-grid-line {
  position: absolute;
  top: 4px;
  bottom: 4px;
  width: 1px;
  background: var(--color-border);
}

.gantt-grid-line--minor {
  background: #edf2f7;
  top: 12px;
  bottom: 12px;
}

.gantt-bar {
  position: absolute;
  top: 6px;
  bottom: 6px;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  padding: 0 0.6rem;
  color: #ffffff;
  font-size: 0.82rem;
  font-weight: 600;
  overflow: hidden;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
  transition: transform 0.2s ease;
  min-width: 6px;
}

.gantt-bar:hover { transform: translateY(-1px); }

.gantt-bar--done     { background: linear-gradient(135deg, #10b981, #059669); }
.gantt-bar--progress { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.gantt-bar--pending  { background: linear-gradient(135deg, #64748b, #475569); }
.gantt-bar--abort    { background: linear-gradient(135deg, #fb7185, #e11d48); }
.gantt-bar--timeout  { background: linear-gradient(135deg, #fb923c, #ea580c); }

.gantt-bar-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 768px) {
  .gantt-row {
    grid-template-columns: 80px 1fr;
  }

  .gantt-label {
    font-size: 0.78rem;
  }

  .zoom-slider-wrap {
    min-width: 140px;
  }

  .zoom-slider {
    width: 80px;
  }
}

@media (max-width: 480px) {
  .gantt-row {
    grid-template-columns: 60px 1fr;
  }

  .gantt-label {
    font-size: 0.72rem;
  }
}
</style>
