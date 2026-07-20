<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { STATUS_LABEL, ITEM_LABEL, PLACE_LABEL } from '@/js/data/taskMeta.js'

defineProps<{
  tasks: Array<Record<string, any>>
  removingTaskId?: string | null
}>()

const emit = defineEmits<{
  'confirm-task': [id: string]
  'cancel-task':  [id: string]
  'remove-task':  [id: string]
}>()

function statusClass(status: string) {
  if (status === 'process')  return 'bg-blue-50   text-blue-600   border-blue-200'
  if (status === 'complete') return 'bg-emerald-50 text-emerald-600 border-emerald-200'
  if (status === 'abort')    return 'bg-rose-50    text-rose-600   border-rose-200'
  if (status === 'timeout')  return 'bg-orange-50  text-orange-600 border-orange-200'
  return                            'bg-slate-50   text-slate-500  border-slate-200'
}

function statusLabel(status: string) {
  return STATUS_LABEL[status] ?? status
}
</script>

<template>
  <div>
    <p v-if="tasks.length === 0" class="text-muted-foreground mb-2">目前沒有待辦任務，請新增指派。</p>

    <div class="grid gap-3">
      <Card
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        :class="{ 'task-card--removing': removingTaskId === task.id }"
      >
        <CardContent class="task-card__content p-4">
          <div class="min-w-0">
            <h4 class="font-bold text-base mb-2 flex items-center gap-2 flex-wrap">
              <span v-if="task.id" class="task-no-badge">{{ task.id }}</span>
              {{ task.title }}
            </h4>
            <p class="text-muted-foreground text-sm mb-1">預計開始：{{ task.startTime }}</p>
            <p v-if="task.place" class="text-muted-foreground text-sm mb-1">地點：{{ PLACE_LABEL[task.place] ?? task.place }}</p>
            <p v-if="task.items?.length" class="text-muted-foreground text-sm mb-1">
              處理事項：{{ task.items.map((i: string) => ITEM_LABEL[i] ?? i).join('、') }}
            </p>
<p v-if="task.description" class="text-muted-foreground mt-2 mb-0">{{ task.description }}</p>
          </div>

          <div class="task-card__actions">
            <Badge variant="outline" :class="statusClass(task.status)">{{ statusLabel(task.status) }}</Badge>
            <template v-if="task.status === 'idle' || task.status === 'process'">
              <Button variant="destructive" size="sm" @click="emit('cancel-task', task.id)">取消任務</Button>
            </template>
            <template v-else-if="task.status === 'complete'">
              <Button class="bg-emerald-500 hover:bg-emerald-600 text-white" size="sm" @click="emit('confirm-task', task.id)">標為完成</Button>
            </template>
            <template v-else>
              <p class="text-sm text-muted-foreground">任務已{{ STATUS_LABEL[task.status] ?? task.status }}</p>
              <Button variant="outline" size="sm" @click="emit('remove-task', task.id)">確認移除</Button>
            </template>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.task-card {
  animation: fadeInUp 0.4s ease both;
}

.task-card:nth-child(1) { animation-delay: 0.05s; }
.task-card:nth-child(2) { animation-delay: 0.12s; }
.task-card:nth-child(3) { animation-delay: 0.19s; }
.task-card:nth-child(4) { animation-delay: 0.26s; }
.task-card:nth-child(5) { animation-delay: 0.33s; }

.task-card--removing {
  animation: fadeOutDown 0.38s ease forwards;
}

.task-card__content {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.task-card__actions {
  display: grid;
  gap: 0.5rem;
  text-align: end;
  justify-items: end;
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .task-card__content {
    flex-direction: column;
  }

  .task-card__actions {
    flex-direction: row;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    text-align: start;
  }
}
</style>
