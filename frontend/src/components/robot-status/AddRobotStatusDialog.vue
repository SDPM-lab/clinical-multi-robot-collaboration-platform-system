<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Upload, X } from '@lucide/vue'
import { fleetStore } from '@/stores/demoFleetStore.js'
import { registerRobotAsset, unregisterRobotAsset } from '@/three/robot/robotModelAssets.js'
import { t } from '@/i18n/index.js'

const emit = defineEmits(['close', 'created'])
const nextNumber = Math.max(0, ...fleetStore.robots.value.map(robot => Number(robot.id.replace(/\D/g, '')) || 0)) + 1
const suffix = String(nextNumber).padStart(2, '0')
const form = reactive({ name: `Robot ${suffix}`, id: `R${suffix}`, floorId: 'floor1', currentLocation: '', serialNumber: '', battery: 100, motorTemperature: '' })
const file = ref(null)
const fileInput = ref(null)
const nameInput = ref(null)
const error = ref('')
const submitting = ref(false)

const close = () => { if (!submitting.value) emit('close') }
const closeOnEscape = event => { if (event.key === 'Escape') close() }
onMounted(() => { document.addEventListener('keydown', closeOnEscape); nameInput.value?.focus() })
onBeforeUnmount(() => document.removeEventListener('keydown', closeOnEscape))

function onFileChange(event) {
  file.value = event.target.files?.[0] || null
  error.value = ''
}

async function submit() {
  if (submitting.value) return
  if (!file.value) { error.value = t('robotStatus.modelRequired'); return }
  const id = form.id.trim()
  const candidate = {
    ...form,
    id,
    name: form.name.trim(),
    currentLocation: form.currentLocation.trim() || null,
    serialNumber: form.serialNumber.trim() || null,
    rosNamespace: `/robot_${id.replace(/^R/i, '').toLowerCase()}`,
    navGraphIndex: 0,
    chargingWaypoint: 'charging_station_1',
    model: file.value.name.replace(/\.glb$/i, ''),
    motorTemperature: form.motorTemperature === '' ? null : Number(form.motorTemperature),
    temperatureSource: form.motorTemperature === '' ? 'unavailable' : 'manual',
  }
  const validation = fleetStore.validateRobot(candidate)
  if (!validation.ok) { error.value = validation.field === 'id' ? t('robotStatus.idExists') : t('robotStatus.addFailed'); return }
  submitting.value = true
  let assetKey
  try {
    assetKey = await registerRobotAsset(file.value)
    const result = fleetStore.addRobot({ ...candidate, modelAssetKey: assetKey })
    if (!result.ok) throw new Error(result.reason)
    emit('created', result.robot)
  } catch {
    if (assetKey) unregisterRobotAsset(assetKey)
    error.value = t('robotStatus.modelInvalid')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="add-status-backdrop" @click.self="close">
    <section class="add-status-dialog" role="dialog" aria-modal="true" aria-labelledby="add-status-title">
      <header><h2 id="add-status-title">{{ t('robotStatus.addRobot') }}</h2><button type="button" :aria-label="t('robotStatus.close')" :disabled="submitting" @click="close"><X :size="18"/></button></header>
      <form @submit.prevent="submit">
        <div class="add-status-fields">
          <label><span>{{ t('robotStatus.name') }} *</span><input ref="nameInput" v-model.trim="form.name" required></label>
          <label><span>{{ t('robotStatus.id') }} *</span><input v-model.trim="form.id" required></label>
          <label><span>{{ t('robotStatus.floor') }}</span><select v-model="form.floorId"><option value="floor1">1F</option><option value="floor2">2F</option><option value="floor3">3F</option></select></label>
          <label><span>{{ t('robotStatus.location') }}</span><input v-model.trim="form.currentLocation" :placeholder="t('robotStatus.noLocation')"></label>
          <label><span>{{ t('robotStatus.serial') }}</span><input v-model.trim="form.serialNumber" :placeholder="t('robotStatus.noValue')"></label>
          <label><span>{{ t('robotStatus.battery') }} (%)</span><input v-model.number="form.battery" type="number" min="0" max="100" required></label>
          <label><span>{{ t('robotStatus.temperature') }} (°C)</span><input v-model="form.motorTemperature" type="number" min="0" max="150" :placeholder="t('robotStatus.noValue')"></label>
          <div class="add-status-readonly"><span>{{ t('robotStatus.connection') }}</span><strong>{{ t('robotStatus.connectionStates.disconnected') }}</strong></div>
          <div class="add-status-readonly"><span>{{ t('robotStatus.activeTaskId') }}</span><strong>{{ t('robotStatus.noValue') }}</strong></div>
          <label class="add-status-upload"><span>{{ t('robotStatus.modelFile') }} *</span><input ref="fileInput" type="file" accept=".glb,model/gltf-binary" @change="onFileChange"><span class="add-status-upload__button"><Upload :size="16"/>{{ file?.name || t('robotStatus.selectGlb') }}</span><small>{{ t('robotStatus.modelHint') }}</small></label>
        </div>
        <p v-if="error" class="add-status-error" role="alert">{{ error }}</p>
        <footer><button type="button" :disabled="submitting" @click="close">{{ t('robotStatus.cancel') }}</button><button type="submit" :disabled="submitting">{{ submitting ? t('robotStatus.loading') : t('robotStatus.create') }}</button></footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
.add-status-backdrop{position:fixed;z-index:1000;inset:0;display:grid;place-items:center;padding:20px;background:#24313c66;backdrop-filter:blur(5px)}
.add-status-dialog{box-sizing:border-box;width:min(570px,100%);max-height:min(780px,calc(100dvh - 40px));overflow:auto;color:var(--text-primary);background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:16px;box-shadow:0 24px 65px #17222e38;animation:dialog-pop 240ms cubic-bezier(.2,.8,.2,1) both}
header{display:flex;align-items:center;justify-content:space-between;padding:18px 22px 8px}h2{margin:0;font-size:19px}header button{display:grid;place-items:center;width:32px;height:32px;color:var(--text-secondary);background:transparent;border:0;border-radius:8px;cursor:pointer}
form{padding:8px 22px 20px}.add-status-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.add-status-fields label,.add-status-readonly{display:grid;align-content:start;gap:5px;min-width:0;color:var(--text-secondary);font-size:11px}.add-status-fields input,.add-status-fields select{box-sizing:border-box;width:100%;height:35px;padding:6px 9px;color:var(--text-primary);background:var(--search-background);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;font-size:12px}.add-status-readonly strong{display:flex;align-items:center;min-height:35px;color:var(--text-primary);font-size:12px;font-weight:500}.add-status-upload{grid-column:1/-1;position:relative}.add-status-upload input{position:absolute;width:1px;height:1px;opacity:0}.add-status-upload__button{display:flex;align-items:center;justify-content:center;gap:7px;min-height:44px;padding:6px 10px;overflow-wrap:anywhere;color:var(--theme-primary);background:var(--theme-primary-soft);border:1px dashed var(--theme-primary);border-radius:8px;cursor:pointer}.add-status-upload small{color:var(--text-muted);font-size:10px}.add-status-upload:focus-within .add-status-upload__button{outline:2px solid var(--theme-primary);outline-offset:2px}.add-status-error{margin:10px 0 0;color:var(--color-error);font-size:11px}footer{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}footer button{min-height:35px;padding:0 14px;color:var(--text-primary);background:transparent;border:1px solid var(--panel-border);border-radius:7px;cursor:pointer}footer button:last-child{color:#40271e;background:var(--theme-primary);border-color:var(--theme-primary)}footer button:disabled{opacity:.55;cursor:default}
@keyframes dialog-pop{from{opacity:0;transform:translateY(12px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}
@media(max-width:540px){.add-status-fields{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.add-status-dialog{animation:none}}
</style>
