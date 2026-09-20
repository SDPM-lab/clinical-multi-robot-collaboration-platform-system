<script setup>
import { computed, reactive, ref } from 'vue'
import { Check, ChevronLeft, ChevronRight, X } from '@lucide/vue'
import {
  fleetStore,
  GRAPH_0_CHARGING_WAYPOINTS,
  ROBOT_CAPABILITY_OPTIONS,
  ROBOT_NAV_GRAPHS,
} from '@/stores/demoFleetStore.js'

const emit = defineEmits(['close', 'created'])
const steps = ['基本資料', 'ROS 2／Fleet 設定', '機器人能力', '電池與導航']
const currentStep = ref(0)
const errorMessage = ref('')
const nextNumber = Math.max(0, ...fleetStore.robots.value.map((robot) => Number(robot.id.replace(/\D/g, '')) || 0)) + 1
const suffix = String(nextNumber).padStart(2, '0')
const form = reactive({
  name: `Robot ${suffix}`,
  id: `R${suffix}`,
  model: 'Hospital AMR',
  manufacturer: '',
  serialNumber: '',
  thumbnailUrl: '/images/robot-thumbnail.png',
  fleetName: 'hospital_fleet',
  rosNamespace: `/robot_${suffix}`,
  fleetAdapter: 'rmf_demos_fleet_adapter',
  rosDomainId: '',
  connectionEndpoint: '',
  capabilities: ['藥品配送', '自動充電'],
  battery: 100,
  batteryCapacityWh: 960,
  minimumTaskBattery: 20,
  rechargeThreshold: 10,
  maxPayloadKg: '',
  maxSpeedMps: 0.7,
  footprintRadiusM: 0.35,
  navGraphIndex: 0,
  chargingWaypoint: 'charging_station_1',
})
const isLastStep = computed(() => currentStep.value === steps.length - 1)

const toggleCapability = (capability) => {
  const index = form.capabilities.indexOf(capability)
  if (index >= 0) form.capabilities.splice(index, 1)
  else form.capabilities.push(capability)
}

const nextStep = () => {
  errorMessage.value = ''
  if (currentStep.value < steps.length - 1) currentStep.value += 1
}

const submit = () => {
  const result = fleetStore.addRobot(form)
  if (!result.ok) {
    errorMessage.value = result.reason
    const fieldSteps = { name: 0, id: 0, rosNamespace: 1, navGraphIndex: 3, chargingWaypoint: 3, battery: 3, maxSpeedMps: 3, maxPayloadKg: 3, footprintRadiusM: 3 }
    currentStep.value = fieldSteps[result.field] ?? currentStep.value
    return
  }
  emit('created', result.robot)
}
</script>

<template>
  <div class="drawer-backdrop" @click.self="emit('close')">
    <aside class="add-robot-drawer" aria-label="新增機器人">
      <header>
        <div><small>Fleet 管理</small><h2>新增機器人</h2></div>
        <button type="button" aria-label="關閉新增機器人" @click="emit('close')"><X :size="19" /></button>
      </header>

      <nav class="step-tabs" aria-label="新增機器人步驟">
        <button v-for="(step, index) in steps" :key="step" type="button" :class="{ 'is-active': currentStep === index, 'is-done': currentStep > index }" @click="currentStep=index">
          <span>{{ currentStep > index ? '✓' : index + 1 }}</span>{{ step }}
        </button>
      </nav>

      <form @submit.prevent="submit">
        <section v-if="currentStep === 0" class="form-section">
          <div class="thumbnail-preview"><img :src="form.thumbnailUrl" alt="robot.glb 產生的機器人縮圖"><span>來源：robot.glb</span></div>
          <label><span>機器人名稱 *</span><input v-model.trim="form.name" placeholder="Robot 04"></label>
          <label><span>Robot ID *</span><input v-model.trim="form.id" placeholder="R04"></label>
          <label><span>型號</span><input v-model.trim="form.model" placeholder="Hospital AMR"></label>
          <label><span>製造商</span><input v-model.trim="form.manufacturer" placeholder="未提供時顯示 —"></label>
          <label><span>序號</span><input v-model.trim="form.serialNumber" placeholder="未提供時顯示 —"></label>
          <label class="full-field"><span>Robot 圖示／模型</span><input v-model.trim="form.thumbnailUrl"><small>目前使用現有 robot.glb 產生的共用靜態縮圖。</small></label>
        </section>

        <section v-else-if="currentStep === 1" class="form-section">
          <div class="connection-notice"><i></i><div><strong>尚未連線</strong><span>建立資料不代表已成功連接 ROS 2。</span></div></div>
          <label><span>Fleet Name</span><input v-model.trim="form.fleetName"></label>
          <label><span>ROS Namespace *</span><input v-model.trim="form.rosNamespace" placeholder="/robot_04"></label>
          <label><span>Fleet Adapter</span><input v-model.trim="form.fleetAdapter"></label>
          <label><span>ROS Domain ID</span><input v-model.number="form.rosDomainId" type="number" min="0" placeholder="—"></label>
          <label class="full-field"><span>連線 Endpoint</span><input v-model.trim="form.connectionEndpoint" placeholder="尚未設定"></label>
        </section>

        <section v-else-if="currentStep === 2" class="capability-section">
          <p>選擇這台機器人可接受的任務。能力設定不會自動建立 ROS 2 連線。</p>
          <button v-for="capability in ROBOT_CAPABILITY_OPTIONS" :key="capability" type="button" :class="{ 'is-selected': form.capabilities.includes(capability) }" @click="toggleCapability(capability)">
            <span><Check v-if="form.capabilities.includes(capability)" :size="14" /></span>{{ capability }}
          </button>
        </section>

        <section v-else class="form-section navigation-section">
          <label><span>目前電量（%）</span><input v-model.number="form.battery" type="number" min="0" max="100"></label>
          <label><span>電池容量（Wh）</span><input v-model.number="form.batteryCapacityWh" type="number" min="0"></label>
          <label><span>最低任務電量（%）</span><input v-model.number="form.minimumTaskBattery" type="number" min="0" max="100"></label>
          <label><span>低電量充電門檻（%）</span><input v-model.number="form.rechargeThreshold" type="number" min="0" max="100"></label>
          <label><span>最大負載（kg）</span><input v-model.number="form.maxPayloadKg" type="number" min="0" placeholder="—"></label>
          <label><span>最大速度（m/s）</span><input v-model.number="form.maxSpeedMps" type="number" min="0" step="0.1"></label>
          <label><span>機器人半徑／Footprint（m）</span><input v-model.number="form.footprintRadiusM" type="number" min="0" step="0.05"></label>
          <label><span>Navigation Graph</span><select v-model.number="form.navGraphIndex"><option v-for="graph in ROBOT_NAV_GRAPHS" :key="graph.index" :value="graph.index">{{ graph.label }}</option></select></label>
          <label class="full-field"><span>Charging Waypoint</span><select v-model="form.chargingWaypoint"><option v-for="waypoint in GRAPH_0_CHARGING_WAYPOINTS" :key="waypoint">{{ waypoint }}</option></select><small>人物 Graph 1 不會出現在機器人選項中。</small></label>
        </section>

        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
        <footer>
          <button type="button" class="secondary" @click="currentStep === 0 ? emit('close') : currentStep--"><ChevronLeft v-if="currentStep > 0" :size="15" />{{ currentStep === 0 ? '取消' : '上一步' }}</button>
          <button v-if="!isLastStep" type="button" class="primary" @click="nextStep">下一步<ChevronRight :size="15" /></button>
          <button v-else type="submit" class="primary">建立機器人</button>
        </footer>
      </form>
    </aside>
  </div>
</template>

<style scoped>
.drawer-backdrop{position:fixed;z-index:90;inset:0;background:rgba(43,44,42,.18);backdrop-filter:blur(3px)}.add-robot-drawer{position:absolute;top:0;right:0;display:grid;grid-template-rows:auto auto minmax(0,1fr);width:min(620px,92vw);height:100%;color:var(--text-primary);background:var(--panel-bg-strong);border-left:1px solid var(--panel-border);box-shadow:-24px 0 60px rgba(55,49,43,.16);backdrop-filter:blur(24px) saturate(112%)}header{display:flex;align-items:center;justify-content:space-between;padding:22px 24px 16px}header small{color:var(--text-muted);font-size:11.5px}h2{margin:3px 0 0;font-size:21px}header button{display:grid;width:34px;height:34px;place-items:center;color:var(--text-secondary);background:var(--icon-button-background);border:1px solid var(--icon-button-border);border-radius:9px;cursor:pointer}.step-tabs{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;padding:0 20px 14px;border-bottom:1px solid var(--glass-divider)}.step-tabs button{display:flex;align-items:center;justify-content:center;gap:5px;min-height:42px;padding:5px;color:var(--text-muted);font-size:11.5px;background:transparent;border:0;border-radius:7px;cursor:pointer}.step-tabs button span{display:grid;width:20px;height:20px;place-items:center;background:var(--progress-track);border-radius:50%;font-size:10px}.step-tabs button.is-active{color:var(--text-primary);background:color-mix(in srgb,var(--accent-orange) 10%,transparent)}.step-tabs button.is-active span,.step-tabs button.is-done span{color:#fffaf5;background:var(--accent-orange)}form{display:grid;grid-template-rows:minmax(0,1fr) auto auto;min-height:0}.form-section{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-content:start;gap:15px 16px;padding:22px 24px;overflow-y:auto}.form-section label{display:grid;gap:6px;color:var(--text-secondary);font-size:12px}.form-section input,.form-section select{box-sizing:border-box;width:100%;height:39px;padding:0 11px;color:var(--text-primary);background:var(--search-background);border:1px solid var(--icon-button-border);border-radius:7px;outline:0}.form-section input:focus,.form-section select:focus{border-color:var(--search-border-active);box-shadow:0 0 0 3px var(--search-focus-ring)}.form-section label small{color:var(--text-muted);font-size:10.5px;line-height:1.5}.full-field{grid-column:1/-1}.thumbnail-preview{grid-column:1/-1;display:flex;align-items:center;gap:15px;padding:12px;background:color-mix(in srgb,var(--accent-beige) 8%,transparent);border:1px solid var(--glass-divider);border-radius:10px}.thumbnail-preview img{width:72px;height:72px;object-fit:contain;background:rgba(235,237,234,.72);border-radius:8px}.thumbnail-preview span{color:var(--text-muted);font-size:11.5px}.connection-notice{grid-column:1/-1;display:flex;align-items:center;gap:10px;padding:11px 12px;background:rgba(216,138,72,.08);border:1px solid rgba(216,138,72,.2);border-radius:8px}.connection-notice i{width:8px;height:8px;background:#9b9d98;border-radius:50%}.connection-notice div{display:grid;gap:2px}.connection-notice strong{font-size:13px}.connection-notice span{color:var(--text-muted);font-size:11px}.capability-section{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-content:start;gap:9px;padding:22px 24px;overflow:auto}.capability-section p{grid-column:1/-1;margin:0 0 8px;color:var(--text-secondary);font-size:12px;line-height:1.6}.capability-section button{display:flex;align-items:center;gap:9px;min-height:42px;padding:0 11px;color:var(--text-secondary);text-align:left;background:var(--search-background);border:1px solid var(--icon-button-border);border-radius:8px;cursor:pointer}.capability-section button>span{display:grid;width:20px;height:20px;place-items:center;border:1px solid var(--glass-divider);border-radius:5px}.capability-section button.is-selected{color:var(--text-primary);border-color:rgba(239,136,61,.4);background:rgba(239,136,61,.09)}.capability-section button.is-selected>span{color:#fff;background:var(--accent-orange);border-color:transparent}.form-error{margin:0;padding:9px 24px;color:#ba594e;font-size:12px;background:rgba(199,101,91,.08)}footer{display:flex;justify-content:space-between;padding:14px 24px 20px;border-top:1px solid var(--glass-divider)}footer button{display:flex;align-items:center;justify-content:center;gap:5px;min-width:92px;height:36px;padding:0 14px;border-radius:7px;cursor:pointer}.secondary{color:var(--text-secondary);background:transparent;border:1px solid var(--icon-button-border)}.primary{color:#fffaf5;background:var(--accent-orange);border:1px solid transparent;box-shadow:0 7px 16px rgba(211,138,86,.2)}
@media(max-width:620px){.step-tabs button{font-size:0}.step-tabs button span{font-size:10px}.form-section{grid-template-columns:1fr}.full-field,.thumbnail-preview,.connection-notice{grid-column:auto}.capability-section{grid-template-columns:1fr}}
</style>
