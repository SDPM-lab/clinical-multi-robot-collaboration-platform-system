<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { robotStateLabels } from '@/data/robotStatus.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { secondsToTime, timeToSeconds } from '@/stores/demoFleetStore.js'

const props = defineProps({
  robots: { type: Array, required: true },
  locations: { type: Array, required: true },
  destination: { type: String, default: '' },
  origin: { type: String, default: 'Pharmacy' },
  robotId: { type: String, default: 'R01' },
  date: { type: String, required: true },
})
const emit = defineEmits(['submit', 'update:destination', 'update:origin', 'update:robotId'])
const taskTypes = ['藥品配送', '檢體運送', '病房物資補充', '醫療廢棄物運送', '文件配送', '巡檢', '前往充電']
const priorities = [{ value: 'low', label: '低' }, { value: 'normal', label: '一般' }, { value: 'high', label: '高' }, { value: 'emergency', label: '緊急' }]
const durationOptions = [5, 10, 12, 15, 20, 30, 45, 60]
const notesOpen = ref(false)

const makeDefaults = () => ({
  type: '藥品配送', title: '藥品配送', robotId: props.robotId || 'R01',
  origin: props.origin || 'Pharmacy', destination: props.destination || 'Nurse Reception',
  date: props.date, startTime: '09:30:00', durationMinutes: 12,
  priority: 'normal', notes: '',
})
const form = reactive(makeDefaults())
const selectedRobot = computed(() => props.robots.find((robot) => robot.id === form.robotId))
const endTime = computed(() => secondsToTime(timeToSeconds(form.startTime) + Number(form.durationMinutes) * 60))
const availableTime = computed(() => selectedRobot.value?.id === 'R01' ? '10:12' : selectedRobot.value?.id === 'R02' ? '11:18' : '08:00')
const robotAvailability = computed(() => selectedRobot.value?.state === 'offline' ? '離線' : selectedRobot.value?.battery < 20 ? '低電量' : '可用')

watch(() => props.destination, (value) => { if (value && value !== form.destination) form.destination = value })
watch(() => props.origin, (value) => { if (value && value !== form.origin) form.origin = value })
watch(() => props.robotId, (value) => { if (value && value !== form.robotId) form.robotId = value })
watch(() => props.date, (value) => { form.date = value })
watch(() => form.destination, (value) => emit('update:destination', value))
watch(() => form.origin, (value) => emit('update:origin', value))
watch(() => form.robotId, (value) => emit('update:robotId', value), { immediate: true })
watch(() => form.type, (value) => { form.title = value })

const reset = () => {
  Object.assign(form, makeDefaults())
  notesOpen.value = false
}
const submit = () => emit('submit', {
  robotId: form.robotId, title: form.title, type: form.type,
  origin: form.origin, destination: form.destination, date: form.date,
  startTime: form.startTime, durationSeconds: Number(form.durationMinutes) * 60,
  priority: form.priority, notes: form.notes,
})
</script>

<template>
  <section class="task-panel" aria-label="建立任務">
    <header><strong>建立任務</strong><button type="button" aria-label="清除任務表單" @click="reset">×</button></header>
    <form @submit.prevent="submit">
      <div class="form-scroll task-form-grid">
        <label class="field"><span>任務類型</span><select v-model="form.type"><option v-for="type in taskTypes" :key="type" :value="type">{{ type }}</option></select></label>
        <label class="field"><span>任務名稱</span><input v-model.trim="form.title" required></label>

        <label class="field"><span>選擇機器人</span><select v-model="form.robotId"><option v-for="robot in robots" :key="robot.id" :value="robot.id">{{ robot.name }}・{{ robot.state === 'offline' ? '離線' : '可用' }}・{{ robot.battery }}%</option></select></label>
        <div v-if="selectedRobot" class="robot-summary">
          <div><i :style="{ backgroundColor: getRobotVisualTheme(selectedRobot.id).main }"></i><strong>{{ robotAvailability }}</strong><span>電量 {{ selectedRobot.battery }}%</span></div>
          <span>{{ selectedRobot.currentLocation }}</span>
          <small>待處理 {{ selectedRobot.queuedTasks }} 項・預計 {{ availableTime }} 可用</small>
          <em>{{ robotStateLabels[selectedRobot.state] }}</em>
        </div>

        <label class="field"><span>起點</span><select v-model="form.origin"><option v-for="location in locations" :key="location">{{ location }}</option></select></label>
        <label class="field"><span>目的地</span><select v-model="form.destination"><option v-for="location in locations" :key="location">{{ location }}</option></select></label>

        <label class="field"><span>排程日期</span><input v-model="form.date" type="date" required></label>
        <label class="field"><span>開始時間</span><input v-model="form.startTime" type="time" step="1" required></label>
        <label class="field"><span>預估時長</span><select v-model.number="form.durationMinutes"><option v-for="minutes in durationOptions" :key="minutes" :value="minutes">{{ minutes }} 分鐘</option></select></label>
        <div class="computed-time"><span>預計結束時間</span><strong>{{ endTime }}</strong></div>

        <fieldset class="priority-control"><legend>優先級</legend><div><button v-for="priority in priorities" :key="priority.value" type="button" :class="{ active: form.priority === priority.value }" @click="form.priority=priority.value">{{ priority.label }}</button></div></fieldset>
        <div class="computed-time"><span>任務狀態</span><strong>待建立</strong></div>

        <button v-if="!notesOpen" type="button" class="notes-toggle" @click="notesOpen=true">＋ 新增任務備註</button>
        <label v-else class="field notes-field"><span>任務備註</span><textarea v-model="form.notes" rows="3" placeholder="輸入交接方式或注意事項"></textarea></label>
      </div>
      <footer><button type="button" @click="reset">取消</button><button type="submit" class="create-button">建立任務</button></footer>
    </form>
  </section>
</template>

<style scoped>
.task-panel{box-sizing:border-box;display:grid;grid-template-rows:auto minmax(0,1fr);width:100%;max-width:none;height:100%;min-height:0;padding:12px 16px 0;color:var(--text-primary);background:rgba(246,244,239,.78);border:1px solid rgba(255,255,255,.58);border-radius:12px;box-shadow:0 18px 45px rgba(66,59,48,.10);backdrop-filter:blur(22px) saturate(115%);-webkit-backdrop-filter:blur(22px) saturate(115%)}:global([data-theme='dark']) .task-panel{background:rgba(61,65,62,.88);border-color:rgba(255,255,255,.12)}
header{display:flex;align-items:center;justify-content:space-between;padding-bottom:7px;border-bottom:1px solid var(--glass-divider)}header strong{font-size:15px}header button{width:27px;height:27px;color:var(--text-muted);font-size:19px;background:transparent;border:0;border-radius:6px;cursor:pointer}header button:hover{background:var(--icon-button-hover)}form{display:grid;grid-template-rows:minmax(0,1fr) auto;min-height:0}.form-scroll{min-height:0;padding:8px 2px;overflow-y:auto;scrollbar-width:none}.form-scroll::-webkit-scrollbar{display:none}.task-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-content:start;gap:6px 14px}.field{display:grid;gap:4px;min-width:0;color:var(--text-secondary);font-size:11.5px}.field input,.field select,.field textarea{box-sizing:border-box;width:100%;min-width:0;height:32px;padding:5px 9px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;outline:0}.field textarea{height:auto;min-height:56px;resize:vertical}.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--search-border-active);box-shadow:0 0 0 3px var(--search-focus-ring)}
.robot-summary{position:relative;display:grid;grid-template-columns:auto 1fr;align-content:center;gap:3px 8px;min-width:0;padding:5px 9px;color:var(--text-secondary);font-size:11.5px;background:color-mix(in srgb,var(--accent-beige) 9%,transparent);border-left:2px solid var(--accent-beige);border-radius:4px 7px 7px 4px}.robot-summary>div{grid-column:1/-1;display:flex;align-items:center;gap:6px}.robot-summary i{width:7px;height:7px;border-radius:50%}.robot-summary>div span{margin-left:8px;color:var(--text-primary)}.robot-summary small{overflow:hidden;color:var(--text-muted);text-overflow:ellipsis;white-space:nowrap}.robot-summary em{justify-self:end;color:var(--text-muted);font-size:10px;font-style:normal}.computed-time{display:grid;gap:4px;color:var(--text-secondary);font-size:11.5px}.computed-time strong{display:flex;align-items:center;height:32px;color:var(--text-primary);font-size:13px;font-variant-numeric:tabular-nums}
.priority-control{margin:0;padding:0;border:0}.priority-control legend{margin-bottom:5px;color:var(--text-secondary);font-size:11.5px}.priority-control>div{display:grid;grid-template-columns:repeat(4,1fr);padding:2px;background:color-mix(in srgb,var(--progress-track) 74%,transparent);border-radius:7px}.priority-control button{height:29px;color:var(--text-secondary);font-size:11px;background:transparent;border:0;border-radius:5px;cursor:pointer}.priority-control button.active{color:var(--text-primary);background:var(--panel-bg-strong);box-shadow:0 2px 7px rgba(65,58,48,.09)}.notes-toggle{grid-column:1/-1;justify-self:start;padding:4px 0;color:var(--accent-orange);font-size:11.5px;background:transparent;border:0;cursor:pointer}.notes-field{grid-column:1/-1}footer{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin:0 -16px;padding:9px 16px 11px;background:color-mix(in srgb,var(--panel-bg-strong) 80%,transparent);border-top:1px solid var(--glass-divider);border-radius:0 0 12px 12px}footer button{min-width:64px;height:32px;padding:0 12px;color:var(--text-secondary);font-size:12px;background:transparent;border:1px solid var(--panel-border);border-radius:7px;cursor:pointer}.create-button{color:#fffaf2!important;background:var(--accent-orange)!important;border-color:transparent!important;box-shadow:0 6px 14px rgba(255,103,0,.18)}
</style>
