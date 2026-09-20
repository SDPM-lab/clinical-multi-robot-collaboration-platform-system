<script setup>
import { computed, ref } from 'vue'
import TaskGantt from '@/components/dispatch/TaskGantt.vue'
import TaskForm from '@/components/dispatch/TaskForm.vue'
import HospitalMiniMap from '@/components/dispatch/HospitalMiniMap.vue'
import { locationDetails } from '@/data/demoActiveRoutes.js'
import { demoFleetStore } from '@/stores/demoFleetStore.js'

const destination = ref('Nurse Reception')
const origin = ref('Pharmacy')
const selectedDate = ref('2026-08-31')
const selectedRobotId = ref('R01')
const errorMessage = ref('')
const locations = Object.values(locationDetails).map((location) => location.label)

const handleSaveChanges = (changes, done) => {
  const result = demoFleetStore.moveTasks(changes)
  if (!result.ok) { done?.(result); return }
  errorMessage.value = changes.length ? `已儲存 ${changes.length} 項排程變更。` : ''
  done?.({ ok: true })
}
const handleCreateTask = (payload) => {
  const result = demoFleetStore.createTask(payload)
  errorMessage.value = result.ok ? '' : result.reason
}
const notification = computed(() => demoFleetStore.notification.value || errorMessage.value)
</script>

<template>
  <div class="task-dispatch-page">
    <TaskGantt v-model:date="selectedDate" :robots="demoFleetStore.robots.value" :tasks="demoFleetStore.tasks.value" @save-changes="handleSaveChanges" />
    <div class="dispatch-workspace">
      <TaskForm v-model:destination="destination" v-model:origin="origin" v-model:robot-id="selectedRobotId" :date="selectedDate" :robots="demoFleetStore.robots.value" :locations="locations" @submit="handleCreateTask" />
      <HospitalMiniMap :robots="demoFleetStore.robots.value" :robot-id="selectedRobotId" :origin="origin" :destination="destination" @select-destination="destination=$event" />
    </div>
    <Transition name="dispatch-toast"><div v-if="notification" class="dispatch-toast" role="status">{{ notification }}</div></Transition>
  </div>
</template>

<style scoped>
.task-dispatch-page{--navbar-height:62px;position:absolute;inset:0;box-sizing:border-box;display:grid;grid-template-rows:340px minmax(0,1fr);gap:12px;width:100%;height:100dvh;min-height:0;padding:calc(var(--navbar-height) + 10px) 18px 18px;overflow:hidden;background:var(--app-background)}.dispatch-workspace{display:grid;grid-template-columns:minmax(470px,.44fr) minmax(520px,.56fr);gap:12px;min-height:0;overflow:hidden}.dispatch-toast{position:fixed;z-index:80;right:28px;bottom:24px;max-width:360px;padding:11px 15px;color:var(--text-primary);font-size:12.5px;background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:11px;box-shadow:var(--dropdown-shadow)}.dispatch-toast-enter-active,.dispatch-toast-leave-active{transition:opacity .2s ease,transform .2s ease}.dispatch-toast-enter-from,.dispatch-toast-leave-to{opacity:0;transform:translateY(8px)}
.task-dispatch-page{padding-right:var(--app-page-gutter);padding-left:var(--app-page-gutter);background:transparent}
@media(max-width:1080px){.task-dispatch-page{padding-right:12px;padding-left:12px}.dispatch-workspace{grid-template-columns:470px minmax(520px,1fr);overflow-x:auto;overscroll-behavior:contain}}
@media(prefers-reduced-motion:reduce){.dispatch-toast-enter-active,.dispatch-toast-leave-active{transition:none}}
</style>
