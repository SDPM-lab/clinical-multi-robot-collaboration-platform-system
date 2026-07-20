<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

defineProps<{
  alert: Record<string, any>
  task: Record<string, any> | null
  alertSourceLabel: (source: string) => string
  robotNameMap: Record<string, string>
}>()

const emit = defineEmits<{
  close: []
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
  <div class="grid gap-4 anim-pop-in" style="max-width: 640px;">
    <header class="flex items-center flex-wrap gap-2">
      <Badge variant="outline" :class="alertTypeClass(alert.type)">{{ alert.type }}</Badge>
      <span class="flex items-center gap-1 font-semibold text-sm">
        <span
          class="alert-source__dot"
          :class="alert.source === 'console' ? 'alert-source__dot--console' : 'alert-source__dot--robot'"
        ></span>
        {{ alertSourceLabel(alert.source) }}
      </span>
      <Badge variant="outline" :class="levelClass(alert.level)">優先 {{ alert.level }}</Badge>
      <span class="text-muted-foreground ml-auto text-sm tabular-nums">{{ alert.time }}</span>
    </header>

    <h3 class="font-bold text-lg flex items-center gap-2 flex-wrap">
      <span v-if="alert.taskNo" class="task-no-badge">{{ alert.taskNo }}</span>
      {{ alert.title }}
    </h3>

    <section>
      <h4 class="text-sm uppercase text-primary font-bold tracking-wide mb-1">事件摘要</h4>
      <p class="text-foreground">{{ alert.detail }}</p>
    </section>

    <section>
      <h4 class="text-sm uppercase text-primary font-bold tracking-wide mb-1">詳細說明</h4>
      <p class="text-foreground">{{ alert.narrative }}</p>
    </section>

    <Card v-if="task" class="bg-muted">
      <CardContent class="p-4">
        <h4 class="text-sm uppercase text-primary font-bold tracking-wide mb-2">關聯任務資訊</h4>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div><span class="text-muted-foreground block">任務編號</span><strong>{{ task.taskNo }}</strong></div>
          <div><span class="text-muted-foreground block">任務標題</span><strong>{{ task.title }}</strong></div>
          <div><span class="text-muted-foreground block">指派機器人</span><strong>{{ robotNameMap[task.assignedTo] || task.assignedTo }}</strong></div>
          <div><span class="text-muted-foreground block">狀態</span><strong>{{ task.status }}</strong></div>
          <div><span class="text-muted-foreground block">時段</span><strong>{{ task.startTime }} ─ {{ task.due }}</strong></div>
          <div><span class="text-muted-foreground block">地點</span><strong>{{ task.location }}</strong></div>
          <div v-if="task.actions?.length"><span class="text-muted-foreground block">處理事項</span><strong>{{ task.actions.join('、') }}</strong></div>
          <div v-if="task.description" class="col-span-2"><span class="text-muted-foreground block">備註</span><strong>{{ task.description }}</strong></div>
        </div>
      </CardContent>
    </Card>

    <Alert v-else-if="alert.taskNo" variant="destructive" class="bg-amber-50 text-amber-800 border-amber-200">
      <AlertDescription>
        任務 {{ alert.taskNo }} 已不在現行清單中 (可能已歸檔)。
      </AlertDescription>
    </Alert>

    <div class="flex justify-end">
      <Button @click="emit('close')">關閉</Button>
    </div>
  </div>
</template>

<style scoped>
.alert-source__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.alert-source__dot--console { background: #0f172a; }
.alert-source__dot--robot { background: #38bdf8; }
</style>
