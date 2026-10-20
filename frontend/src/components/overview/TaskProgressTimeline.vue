<script setup>
import { overviewRobotColors } from '@/styles/overviewTheme.js'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, ChevronDown } from '@lucide/vue'

const props = defineProps({
  modelValue: { type: String, required: true },
  progressByRobot: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue'])
const open = ref(false)
const selectRoot = ref(null)
const robotKeys = computed(() => Object.keys(props.progressByRobot))
const progress = computed(() => props.progressByRobot[props.modelValue] || props.progressByRobot[robotKeys.value[0]])
const timelineKey = computed(() => `${props.modelValue}:${progress.value.taskId}`)
const choose = (key) => { emit('update:modelValue', key); open.value = false }
const robotColors = { robot01: overviewRobotColors[0], robot02: overviewRobotColors[1], robot03: overviewRobotColors[2] }
const closeOnOutsidePointer = (event) => {
  if (!selectRoot.value?.contains(event.target)) open.value = false
}
onMounted(() => document.addEventListener('pointerdown', closeOnOutsidePointer))
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeOnOutsidePointer))
</script>

<template>
  <aside class="task-progress-panel overview-tool-panel dashboard-panel-enter" aria-label="目前任務進度" @keydown.esc="open = false">
    <header>
      <div><h2>任務進度</h2><span>{{ progress.taskId }} · {{ progress.floor }}</span></div>
      <div ref="selectRoot" class="robot-select">
        <button type="button" :aria-expanded="open" aria-haspopup="listbox" @click="open = !open"><i :style="{background: robotColors[modelValue]}" :class="progress.robotState === 'busy' ? 'is-executing' : ''"></i>{{ progress.robotId }}<ChevronDown :size="13" /></button>
        <div v-if="open" class="robot-options" role="listbox">
          <button v-for="key in robotKeys" :key="key" type="button" role="option" :aria-selected="key === modelValue" @click="choose(key)"><i :style="{background: robotColors[key]}" :class="progressByRobot[key].robotState === 'busy' ? 'is-executing' : ''"></i>{{ progressByRobot[key].robotId }}</button>
        </div>
      </div>
    </header>
    <Transition name="route" mode="out-in" appear>
    <ol :key="timelineKey" class="progress-content" :style="{ '--stop-count': progress.steps.length }">
      <li v-for="(step, index) in progress.steps" :key="step.label" :class="`is-${step.status}`" :style="{ '--step-index': step.status === 'active' ? progress.steps.length - 1 : index - (progress.steps.slice(0, index).some((stop) => stop.status === 'active') ? 1 : 0) }">
        <span class="timeline-node"><Check v-if="step.status === 'completed'" :size="12" :stroke-width="2.5" /><i v-else-if="step.status === 'active'" class="active-pulse-dot"></i></span>
        <div><strong>{{ step.label }}</strong><span>{{ step.location }} · {{ step.statusLabel }}</span></div>
        <time>{{ step.time }}</time>
      </li>
    </ol>
    </Transition>
  </aside>
</template>

<style scoped>
.task-progress-panel{--panel-delay:400ms;--task-completed:var(--text-secondary);--task-active:var(--overview-accent-text);--task-pending:var(--text-muted);--task-line:var(--info-divider);--task-error:var(--danger-coral);box-sizing:border-box;display:flex;flex-direction:column;min-height:0;height:100%;padding:20px;color:var(--text-primary);overflow:auto}
header{position:relative;z-index:4;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding-bottom:16px;border-bottom:1px solid var(--overview-divider)}header>div:first-child{display:grid;gap:6px}h2{margin:0;font-size:var(--info-title-size);font-weight:var(--info-title-weight);letter-spacing:var(--info-title-spacing);line-height:1.25}header span{color:var(--text-secondary);font-size:10px}.robot-select{position:relative}.robot-select>button,.robot-options button{display:flex;align-items:center;gap:7px;min-height:34px;padding:0 10px;color:var(--text-primary);font-size:11.5px;font-weight:600;white-space:nowrap;background:rgba(255,255,255,.5);border:1px solid var(--glass-border);border-radius:var(--radius-control);cursor:pointer}.robot-select i{width:6px;height:6px;background:var(--neutral-slate);border-radius:50%}.robot-select i.is-executing{box-shadow:0 0 0 0 var(--theme-primary-soft);animation:robot-state-pulse 1.7s ease-out infinite}.robot-options{position:absolute;top:40px;right:0;display:grid;width:128px;gap:3px;padding:6px;background:var(--info-background);border:1px solid var(--glass-border);border-radius:var(--radius-control);box-shadow:var(--info-shadow);backdrop-filter:var(--info-backdrop)}.robot-options button{border:0;background:transparent}.robot-options button:hover,.robot-options button[aria-selected=true]{background:var(--overview-accent-soft)}
ol{position:relative;display:grid;flex:1;grid-auto-rows:minmax(0,1fr);margin:14px 0 0;padding:0;list-style:none;min-height:0}
ol::before{position:absolute;top:calc(50% / var(--stop-count));bottom:calc(50% / var(--stop-count));left:10px;width:1.5px;background:var(--task-line);content:'';transform-origin:top;animation:line-grow 1050ms cubic-bezier(.22,.8,.3,1) 200ms both}
li{position:relative;display:grid;grid-template-columns:22px minmax(0,1fr) auto;align-items:center;gap:10px;min-height:42px}
li.is-completed:not(:last-child)::after{position:absolute;top:50%;height:100%;left:10px;width:1.5px;content:'';background:var(--task-completed);transform-origin:top;animation:line-grow 480ms ease-out calc(400ms + var(--step-index)*280ms) both}
.timeline-node{position:relative;z-index:1;display:grid;width:22px;height:22px;place-items:center;color:var(--neutral-slate);background:rgba(255,255,255,.64);border:1px solid var(--task-pending);border-radius:50%;animation:node-enter 350ms cubic-bezier(.2,1.5,.5,1) calc(350ms + var(--step-index)*280ms) both}
li>div{display:grid;gap:4px}li>div,time{animation:stop-enter 420ms ease-out calc(450ms + var(--step-index)*280ms) both}li strong{font-size:var(--info-body-size);font-weight:550;line-height:1.4}li>div span,time{color:var(--text-secondary);font-size:var(--info-meta-size);line-height:1.4}time{font-variant-numeric:tabular-nums}.is-completed .timeline-node{color:#fff;background:var(--task-completed);border-color:var(--task-completed)}.is-active .timeline-node{color:var(--task-active);background:var(--overview-accent-soft);border-color:rgba(var(--overview-accent-rgb),.66)}.is-active .timeline-node::before{position:absolute;inset:-1px;border:1.5px solid rgba(var(--overview-accent-rgb),.52);border-radius:50%;content:'';animation:active-node-ripple 1.55s ease-out infinite}.active-pulse-dot{width:6px;height:6px;background:var(--task-active);border-radius:50%;box-shadow:0 0 7px rgba(var(--overview-accent-rgb),.48)}.is-active strong,.is-active time{color:var(--overview-accent-text)}.is-active div span{color:var(--overview-accent-text)}.is-error .timeline-node{color:#fff;background:var(--task-error);border-color:var(--task-error)}
.route-enter-active{transition:opacity 250ms ease}.route-leave-active{transition:opacity 180ms ease}.route-enter-from,.route-leave-to{opacity:0}
@keyframes line-grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes stop-enter{from{opacity:0;transform:translateX(6px)}to{opacity:1;transform:none}}
@keyframes node-enter{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}
@keyframes active-node-ripple{0%{opacity:.85;transform:scale(.8)}75%,100%{opacity:0;transform:scale(1.7)}}
@keyframes robot-state-pulse{0%{box-shadow:0 0 0 0 rgba(var(--overview-accent-rgb),.3)}75%,100%{box-shadow:0 0 0 5px rgba(var(--overview-accent-rgb),0)}}
@media(prefers-reduced-motion:reduce){ol::before,li::after,.timeline-node,.is-active .timeline-node::before,.robot-select i.is-executing,li>div,time{animation:none}.route-enter-active,.route-leave-active{transition:none}}
h2{display:flex;align-items:center;gap:7px}h2 svg{flex:none;color:var(--theme-primary)}
</style>
