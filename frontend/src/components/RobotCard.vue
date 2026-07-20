<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const props = defineProps<{
  robot: Record<string, any>
  active?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
}>()

const isOnline = computed(() => {
  if (!props.robot.lastUpdate) return false
  const last = new Date(props.robot.lastUpdate).getTime()
  return Date.now() - last < 10000
})

function statusClass(status: string) {
  if (status === '忙碌') return 'bg-amber-50 text-amber-600 border-amber-200'
  if (status === '待命' || status === '在線') return 'bg-emerald-50 text-emerald-600 border-emerald-200'
  if (status === '充電中') return 'bg-blue-50 text-blue-600 border-blue-200'
  if (status === '緊急停止') return 'bg-red-50 text-red-600 border-red-200'
  return 'bg-slate-100 text-slate-500 border-slate-200'
}
</script>

<template>
  <article
    class="robot-card cursor-pointer"
    :class="{ 'robot-card--active': active }"
    @click="emit('select', robot.id)"
    role="button"
  >
    <Card class="transition-all duration-200 hover:-translate-y-0.5">
      <CardContent class="p-3">
        <div class="flex justify-between items-start gap-2 mb-2">
          <div class="flex items-start gap-2">
            <span class="robot-dot" :class="isOnline ? 'robot-dot--online' : 'robot-dot--offline'"></span>
            <div>
              <h3 class="font-bold text-base mb-0.5">{{ robot.name }}</h3>
              <p class="text-muted-foreground text-sm mb-0.5">{{ robot.currentTask }}</p>
              <p v-if="robot.rosName" class="text-muted-foreground text-xs">ROS: {{ robot.rosName }}</p>
            </div>
          </div>
          <Badge variant="outline" :class="statusClass(robot.status)">{{ robot.modeText || robot.status }}</Badge>
        </div>
        <div class="flex justify-between text-muted-foreground text-sm">
          <span>電量 {{ robot.battery }}%</span>
          <span>{{ robot.location }}</span>
        </div>
      </CardContent>
    </Card>
  </article>
</template>

<style scoped>
.robot-card {
  animation: fadeInUp 0.4s ease both;
}

.robot-card:nth-child(1) { animation-delay: 0.05s; }
.robot-card:nth-child(2) { animation-delay: 0.12s; }
.robot-card:nth-child(3) { animation-delay: 0.19s; }
.robot-card:nth-child(4) { animation-delay: 0.26s; }
.robot-card:nth-child(5) { animation-delay: 0.33s; }

.robot-card--active :deep([data-slot="card"]) {
  background: #e0f2fe;
  border-color: #38bdf8;
}

.robot-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
}

.robot-dot--online {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
  animation: pulse-robot 2s ease-in-out infinite;
}

.robot-dot--offline {
  background: #94a3b8;
}

@keyframes pulse-robot {
  0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(34, 197, 94, 0.5); }
  50% { opacity: 0.7; box-shadow: 0 0 2px rgba(34, 197, 94, 0.2); }
}
</style>
