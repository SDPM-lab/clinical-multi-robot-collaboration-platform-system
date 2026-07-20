<script setup>
import { onMounted, ref } from 'vue'
import { checkBackendHealth, createHospitalTask } from './services/taskApi'

const target = ref('ward_a')
const priority = ref(1)
const note = ref('')
const isSubmitting = ref(false)
const backendStatus = ref('檢查中...')
const resultMessage = ref('')
const errorMessage = ref('')

const taskTargets = [
  { label: '病房 A', value: 'ward_a' },
  { label: '病房 B', value: 'ward_b' },
  { label: '病房 C', value: 'ward_c' },
  { label: '病房 D', value: 'ward_d' },
  { label: '檢驗室', value: 'lab' },
  { label: '藥局', value: 'pharmacy' },
  { label: '護理站', value: 'nurse_station' },
  { label: '診間 1', value: 'consult_1' },
  { label: '診間 2', value: 'consult_2' },
  { label: '診間 3', value: 'consult_3' },
  { label: '抽血區', value: 'blood_draw' },
  { label: '處置室', value: 'procedure_room' },
  { label: '儲藏室', value: 'storage' }
]

async function loadBackendStatus() {
  try {
    const data = await checkBackendHealth()
    backendStatus.value = `${data.service} 正常運作`
  } catch (error) {
    backendStatus.value = '後端未連線'
  }
}

async function submitTask() {
  resultMessage.value = ''
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const payload = {
      target: target.value,
      priority: Number(priority.value),
      taskType: 'go_to_place',
      note: note.value || 'from vue'
    }

    const result = await createHospitalTask(payload)

    resultMessage.value = `任務已送出：${payload.target}，${result.message}`
  } catch (error) {
    errorMessage.value = error.message || '任務送出失敗'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  loadBackendStatus()
})
</script>

<template>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Open-RMF Hospital Dispatch</p>
      <h1>醫療機器人任務派送系統</h1>
      <p class="subtitle">
        透過 Vue 前端送出任務，交由 ASP.NET Core、ROS Bridge、Open-RMF 與派工節點完成多機器人派工。
      </p>
    </section>

    <section class="layout">
      <div class="card">
        <div class="card-header">
          <h2>新增任務</h2>
          <span class="status">{{ backendStatus }}</span>
        </div>

        <form class="task-form" @submit.prevent="submitTask">
          <label>
            任務目標
            <select v-model="target">
              <option
                v-for="item in taskTargets"
                :key="item.value"
                :value="item.value"
              >
                {{ item.label }}（{{ item.value }}）
              </option>
            </select>
          </label>

          <label>
            優先級
            <select v-model="priority">
              <option :value="1">1 - 一般</option>
              <option :value="2">2 - 重要</option>
              <option :value="3">3 - 緊急</option>
            </select>
          </label>

          <label>
            備註
            <textarea
              v-model="note"
              rows="3"
              placeholder="例如：送藥、送檢體、送病歷..."
            ></textarea>
          </label>

          <button type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? '派送中...' : '派送任務' }}
          </button>
        </form>

        <p v-if="resultMessage" class="message success">
          {{ resultMessage }}
        </p>

        <p v-if="errorMessage" class="message error">
          {{ errorMessage }}
        </p>
      </div>

      <div class="card flow-card">
        <h2>目前資料流</h2>
        <div class="flow">
          <div>Vue 前端</div>
          <span>↓</span>
          <div>ASP.NET Core API</div>
          <span>↓</span>
          <div>Python ROS Bridge</div>
          <span>↓</span>
          <div>/hospital_task_request</div>
          <span>↓</span>
          <div>Rule Dispatcher</div>
          <span>↓</span>
          <div>Open-RMF / Robot</div>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 56px;
  color: #eef3ff;
  background:
    radial-gradient(circle at 20% 10%, rgba(112, 88, 255, 0.35), transparent 32%),
    radial-gradient(circle at 82% 18%, rgba(0, 220, 255, 0.18), transparent 30%),
    linear-gradient(135deg, #050713 0%, #0d1021 52%, #050713 100%);
}

.hero {
  max-width: 920px;
  margin: 0 auto 32px;
}

.eyebrow {
  margin: 0 0 12px;
  color: #9edcff;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-weight: 700;
}

h1 {
  margin: 0;
  font-size: clamp(36px, 6vw, 68px);
  line-height: 1.05;
}

.subtitle {
  max-width: 780px;
  margin-top: 18px;
  color: #b9c4df;
  font-size: 18px;
  line-height: 1.8;
}

.layout {
  display: grid;
  grid-template-columns: minmax(320px, 1.1fr) minmax(280px, 0.9fr);
  gap: 24px;
  max-width: 1180px;
  margin: 0 auto;
}

.card {
  border: 1px solid rgba(158, 220, 255, 0.25);
  border-radius: 28px;
  padding: 28px;
  background: rgba(9, 13, 31, 0.78);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(16px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

h2 {
  margin: 0;
  font-size: 24px;
}

.status {
  padding: 8px 12px;
  border: 1px solid rgba(99, 255, 190, 0.28);
  border-radius: 999px;
  color: #9cffd4;
  background: rgba(99, 255, 190, 0.08);
  font-size: 13px;
}

.task-form {
  display: grid;
  gap: 18px;
}

label {
  display: grid;
  gap: 8px;
  color: #d9e2ff;
  font-weight: 700;
}

select,
textarea {
  width: 100%;
  border: 1px solid rgba(158, 220, 255, 0.22);
  border-radius: 16px;
  padding: 14px 16px;
  color: #f7f9ff;
  background: rgba(255, 255, 255, 0.07);
  outline: none;
  font: inherit;
}

select:focus,
textarea:focus {
  border-color: rgba(158, 220, 255, 0.8);
  box-shadow: 0 0 0 4px rgba(158, 220, 255, 0.12);
}

option {
  color: #111827;
}

button {
  border: none;
  border-radius: 18px;
  padding: 15px 20px;
  color: white;
  background: linear-gradient(135deg, #7d5cff, #00c8ff);
  font-size: 16px;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 0 16px 36px rgba(0, 200, 255, 0.18);
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.message {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 16px;
  line-height: 1.6;
}

.success {
  color: #a7ffd9;
  background: rgba(44, 255, 167, 0.1);
  border: 1px solid rgba(44, 255, 167, 0.24);
}

.error {
  color: #ffb7c2;
  background: rgba(255, 77, 109, 0.1);
  border: 1px solid rgba(255, 77, 109, 0.24);
}

.flow-card {
  align-self: start;
}

.flow {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.flow div {
  padding: 14px 16px;
  border: 1px solid rgba(158, 220, 255, 0.2);
  border-radius: 16px;
  color: #eaf2ff;
  background: rgba(255, 255, 255, 0.055);
}

.flow span {
  color: #7bdcff;
  text-align: center;
  font-weight: 900;
}

@media (max-width: 860px) {
  .page {
    padding: 28px;
  }

  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
