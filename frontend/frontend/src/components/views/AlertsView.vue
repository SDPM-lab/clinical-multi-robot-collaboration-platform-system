<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

defineProps<{
  filteredAlerts: Array<Record<string, any>>
  alertSourceOptions: Array<Record<string, any>>
  selectedAlertSource: string
  unreadAlertCount: number
  alertSourceLabel: (source: string) => string
}>()

const emit = defineEmits<{
  'select-source': [value: string]
  'mark-read': [id: string]
  'mark-all-read': []
  'open-detail': [alert: Record<string, any>]
}>()

function alertTypeClass(type: string) {
  const map: Record<string, string> = {
    '異常': 'bg-red-50 text-red-600 border-red-200',
    '警告': 'bg-amber-50 text-amber-600 border-amber-200',
    '完成': 'bg-emerald-50 text-emerald-600 border-emerald-200',
    '進行中': 'bg-blue-50 text-blue-600 border-blue-200',
    '資訊': 'bg-indigo-50 text-indigo-600 border-indigo-200',
  }
  return map[type] || 'bg-slate-100 text-slate-500 border-slate-200'
}

function levelClass(level: string) {
  const map: Record<string, string> = {
    '高': 'bg-red-50 text-red-600 border-red-200',
    '中': 'bg-amber-50 text-amber-600 border-amber-200',
    '低': 'bg-blue-50 text-blue-600 border-blue-200',
  }
  return map[level] || 'bg-slate-100 text-slate-500 border-slate-200'
}
</script>

<template>
  <div class="grid gap-4">
    <Card class="anim-fade-in-down">
      <CardContent class="flex justify-between items-center flex-wrap gap-4 p-4">
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="opt in alertSourceOptions"
            :key="opt.value"
            size="sm"
            :variant="selectedAlertSource === opt.value ? 'default' : 'outline'"
            class="font-semibold"
            @click="emit('select-source', opt.value)"
          >
            {{ opt.label }}
            <Badge
              variant="secondary"
              class="ml-1"
              :class="selectedAlertSource === opt.value ? 'bg-white/25' : 'bg-muted'"
            >{{ opt.count }}</Badge>
          </Button>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-muted-foreground text-sm">未讀 <strong class="text-destructive text-base">{{ unreadAlertCount }}</strong> 則</span>
          <Button
            size="sm"
            variant="outline"
            class="font-semibold"
            :disabled="unreadAlertCount === 0"
            @click="emit('mark-all-read')"
          >全部標為已讀</Button>
        </div>
      </CardContent>
    </Card>

    <div class="grid gap-2">
      <Card
        v-for="alert in filteredAlerts"
        :key="alert.id"
        class="alert-row anim-fade-in-up cursor-pointer"
        :class="{ 'alert-row--unread': !alert.read }"
        tabindex="0"
        role="button"
        @click="emit('open-detail', alert)"
        @keydown.enter.prevent="emit('open-detail', alert)"
        @keydown.space.prevent="emit('open-detail', alert)"
      >
        <CardContent class="grid gap-2 p-4">
          <div class="flex items-center flex-wrap gap-2 text-sm">
            <Badge variant="outline" :class="alertTypeClass(alert.type)">{{ alert.type }}</Badge>
            <span class="flex items-center gap-1 font-semibold">
              <span
                class="alert-source__dot"
                :class="alert.source === 'console' ? 'alert-source__dot--console' : 'alert-source__dot--robot'"
              ></span>
              {{ alertSourceLabel(alert.source) }}
            </span>
            <span class="text-muted-foreground ml-auto tabular-nums">{{ alert.time }}</span>
          </div>
          <h3 class="font-bold text-base flex items-center gap-2 flex-wrap">
            <span v-if="alert.taskNo" class="task-no-badge">{{ alert.taskNo }}</span>
            {{ alert.title }}
          </h3>
          <p class="text-foreground text-sm">{{ alert.detail }}</p>
          <footer class="flex items-center gap-2 mt-1">
            <Badge variant="outline" :class="levelClass(alert.level)">優先 {{ alert.level }}</Badge>
            <Button
              v-if="!alert.read"
              size="sm"
              variant="outline"
              class="font-semibold ml-auto"
              @click.stop="emit('mark-read', alert.id)"
            >標為已讀</Button>
            <span v-else class="text-muted-foreground text-sm font-semibold ml-auto">已讀</span>
            <span class="text-muted-foreground text-sm">點擊查看詳細</span>
          </footer>
        </CardContent>
      </Card>

      <Card v-if="filteredAlerts.length === 0">
        <CardContent class="text-center text-muted-foreground py-10">沒有符合條件的通知</CardContent>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.alert-row {
  border-left: 4px solid var(--color-border);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.alert-row:nth-child(1) { animation-delay: 0.05s; }
.alert-row:nth-child(2) { animation-delay: 0.1s; }
.alert-row:nth-child(3) { animation-delay: 0.15s; }
.alert-row:nth-child(4) { animation-delay: 0.2s; }
.alert-row:nth-child(5) { animation-delay: 0.25s; }
.alert-row:nth-child(6) { animation-delay: 0.3s; }
.alert-row:nth-child(7) { animation-delay: 0.35s; }
.alert-row:nth-child(8) { animation-delay: 0.4s; }

.alert-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.12);
}

.alert-row:focus-visible {
  outline: 3px solid #60a5fa;
  outline-offset: 3px;
}

.alert-row--unread {
  border-left-color: var(--color-primary);
  background: #f8fbff;
}

.alert-source__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.alert-source__dot--console { background: #0f172a; }
.alert-source__dot--robot { background: #38bdf8; }
</style>
