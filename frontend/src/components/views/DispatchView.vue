<script setup lang="ts">
import RobotCard from '@/components/RobotCard.vue'
import TaskList from '@/components/TaskList.vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

defineProps<{
  robots: Array<Record<string, any>>
  selectedRobot: Record<string, any>
  selectedRobotId: string
  filteredTasks: Array<Record<string, any>>
  confirmingTaskId?: string | null
}>()

const emit = defineEmits<{
  'select-robot': [id: string]
  'complete-task': [id: string]
  'cancel-task': [id: string]
  'confirm-task': [id: string]
  'emergency-stop': [id: string]
}>()
</script>

<template>
  <div class="dispatch-body">
    <aside class="anim-fade-in-left">
      <Card>
        <CardContent class="p-4">
          <h2 class="font-bold mb-3">機器人列表</h2>
          <div class="grid gap-3">
            <RobotCard
              v-for="robot in robots"
              :key="robot.id"
              :robot="robot"
              :active="robot.id === selectedRobotId"
              @select="(id) => emit('select-robot', id)"
            />
          </div>
        </CardContent>
      </Card>
    </aside>

    <section class="anim-fade-in-right anim-delay-1">
      <Card>
        <CardContent class="grid gap-4 p-4">
          <div class="panel__top">
            <div>
              <p class="eyebrow mb-1">目前選擇</p>
              <h2 class="font-bold">{{ selectedRobot.name }}</h2>
              <p class="text-muted-foreground text-sm">狀態：{{ selectedRobot.status }} • 電量 {{ selectedRobot.battery }}% • 目前任務：{{ selectedRobot.currentTask }}</p>
            </div>
            <div class="flex gap-2 items-center">
              <Button class="h-10 px-4 rounded-lg bg-destructive hover:bg-destructive/90 text-destructive-foreground font-bold" @click="emit('emergency-stop', selectedRobotId)">
                <span class="mr-1">⛔</span>
                緊急停止
              </Button>
            </div>
          </div>

          <h3 class="font-bold">任務清單</h3>

          <div>
            <TaskList
              :tasks="filteredTasks"
              :removing-task-id="confirmingTaskId"
              @complete-task="(id) => emit('complete-task', id)"
              @cancel-task="(id) => emit('cancel-task', id)"
              @confirm-task="(id) => emit('confirm-task', id)"
            />
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</template>

<style scoped>
.dispatch-body {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
}

.panel__top {
  display: grid;
  gap: 1rem;
}

@media (min-width: 768px) {
  .panel__top {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
  }
}

@media (max-width: 1024px) {
  .dispatch-body {
    grid-template-columns: 1fr;
  }
}
</style>
